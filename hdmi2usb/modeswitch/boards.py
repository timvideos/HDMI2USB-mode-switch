#!/usr/bin/env python
# vim: set ts=4 sw=4 et sts=4 ai:

"""
Tool to figure find the USB device that a board is available at.

This is a complicated process as the FX2 is software configurable and hence
could end up under many different VID:PID names based on what firmware is
currently loaded onto it.
"""

import logging
import os
import os.path
import sys
import time
import subprocess

from collections import namedtuple

from . import lsusb as usbapi
from . import files


def assert_in(needle, haystack):
    assert needle in haystack, "%r not in %r" % (needle, haystack)


__filepath__ = os.path.dirname(__file__)
FIRMWARE_DIR = os.path.abspath(os.path.realpath(
    os.path.join(__filepath__, '..', 'firmware')))
assert os.path.exists(FIRMWARE_DIR)


def firmware_path(filepath):
    locations = ['']
    locations.append(os.getcwd())
    locations.append(FIRMWARE_DIR)

    for loc in locations:
        fullname = os.path.join(loc, filepath)
        fullname = os.path.abspath(os.path.realpath(fullname))
        if os.path.exists(fullname):
            return fullname

    assert False, "{} not found in {}".format(filepath, locations)


BOARD_TYPES = [
    'opsis',
    'atlys',
]
BOARD_NAMES = {
    'atlys': "Digilent Atlys",
    'opsis': "Numato Opsis",
}
BOARD_STATES = [
    'unconfigured',
    'jtag',
    'serial',
    'eeprom',
    'operational',
]
BOARD_FPGA = {
    'atlys': "6slx45csg324",
    'opsis': "6slx45tfgg484",
}

USBJTAG_MAPPING = {
    'hw_nexys': 'atlys',
    'hw_opsis': 'opsis',
}
USBJTAG_RMAPPING = {v: k for k, v in USBJTAG_MAPPING.items()}

OPENOCD_MAPPING = {
    'atlys': "board/digilent_atlys.cfg",
    'opsis': "board/numato_opsis.cfg",
}
OPENOCD_FLASHPROXY = {
    'opsis': firmware_path('spartan6/opsis/bscan_spi_xc6slx45t.bit'),
    'atlys': firmware_path('spartan6/atlys/bscan_spi_xc6slx45.bit'),
}

FX2_MODE_MAPPING = {
    'jtag': 'ixo-usb-jtag.hex',
    'serial': 'usb-uart.ihx',
    'eeprom': 'eeprom.ihx',
}


BoardBase = namedtuple("Board", ["dev", "type", "state"])


class Board(BoardBase):

    def tty(self):
        return self.dev.tty()


def load_fx2(board, mode=None, filename=None, verbose=False):
    if mode is not None:
        assert filename is None
        filename = firmware_path(
            'fx2/{}/{}'.format(board.type, FX2_MODE_MAPPING[mode]))

    if board.dev.inuse():
        if verbose:
            sys.stderr.write("Detaching drivers from board.\n")
        board.dev.detach()

    filepath = firmware_path(filename)
    assert os.path.exists(filepath), filepath

    sys.stderr.write("Using FX2 firmware %s\n" % filename)

    cmdline = "fxload -t fx2lp".split()
    cmdline += ["-D", str(board.dev.path)]
    cmdline += ["-I", filepath]
    if verbose:
        cmdline += ["-v", ]

    if verbose:
        sys.stderr.write("Running %r\n" % " ".join(cmdline))

    try:
        output = subprocess.check_output(cmdline, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        if b"can't modify CPUCS: Protocol error\n" not in e.stdout:
            print(e.stdout)
            raise


def flash_fx2(board, filename, verbose=False):
    assert board.state == "eeprom", board
    assert not board.dev.inuse()

    assert board.type == "opsis", (
        "Only support flashing the Opsis for now (not %s)." % board.type)


def load_fpga(board, filename, verbose=False):
    assert board.state == "jtag", board
    assert not board.dev.inuse()
    assert board.type in OPENOCD_MAPPING

    filepath = firmware_path(filename)
    assert os.path.exists(filepath), filepath
    assert filename.endswith(".bit"), "Loading requires a .bit file"
    xfile = files.XilinxBitFile(filepath)
    assert xfile.part == BOARD_FPGA[board.type], (
        "Bit file must be for {} (not {})".format(
            BOARD_FPGA[board.type], xfile.part))

    script = ["init"]
    if verbose:
        script += ["xc6s_print_dna xc6s.tap"]

    script += ["pld load 0 {}".format(filepath)]
    script += ["exit"]

    cmdline = ["openocd"]
    cmdline += ["-f", OPENOCD_MAPPING[board.type]]
    cmdline += ["-c", "; ".join(script)]

    if verbose == 0:
        subprocess.check_output(cmdline, stderr=subprocess.STDOUT)
    else:
        if verbose > 1:
            cmdline += ["--debug={}".format(verbose - 2)]
        sys.stderr.write("Running %r\n" % cmdline)
        subprocess.check_call(cmdline)


def flash_fpga(board, filename, verbose=False):
    assert board.state == "jtag", board
    assert not board.dev.inuse()
    assert board.type in OPENOCD_MAPPING

    filepath = firmware_path(filename)
    assert os.path.exists(filepath), filepath
    assert filename.endswith(".bin"), "Flashing requires a .bin file"
    xfile = files.XilinxBinFile(filepath)

    assert board.type in OPENOCD_FLASHPROXY
    proxypath = os.path.abspath(OPENOCD_FLASHPROXY[board.type])
    assert os.path.exists(proxypath), proxypath

    script = ["init"]
    if verbose:
        script += ["xc6s_print_dna xc6s.tap"]

    script += ["jtagspi_init 0 {}".format(proxypath)]

    if verbose > 1:
        script += ["flash banks"]
        script += ["flash list"]
    if verbose > 2:
        script += ["flash info 0"]

    # script += ["flash read_bank 0 backup.bit 0 0x01000000"]

    script += [
        "jtagspi_program {} 0x{:x}".format(filepath, 0),
        "exit"
    ]

    cmdline = ["openocd"]

    cmdline += ["-f", OPENOCD_MAPPING[board.type]]
    cmdline += ["-c", "; ".join(script)]

    if verbose == 0:
        subprocess.check_output(cmdline, stderr=subprocess.STDOUT)
    else:
        if verbose > 1:
            cmdline += ["--debug={}".format(verbose - 2)]
        sys.stderr.write("Running %r\n" % cmdline)
        subprocess.check_call(cmdline)


def find_boards():
    all_boards = []
    exart_uarts = []
    for device in usbapi.find_usb_devices():
        if False:
            pass

        # Digilent Atlys
        # --------------------------
        # Digilent Atlys board with stock "Adept" firmware
        # Bus 003 Device 019: ID 1443:0007 Digilent Development board JTAG
        if device.vid == 0x1443 and device.pid == 0x0007:
            all_boards.append(
                Board(dev=device, type="atlys", state="unconfigured"))

        # Digilent Atlys board unconfigured mode with Openmoko ID
        # Bus 003 Device 019: ID 1d50:60b5
        elif device.vid == 0x1d50 and device.pid == 0x60b5:
            all_boards.append(
                Board(dev=device, type="atlys", state="unconfigured"))

        # Digilent Atlys board JTAG/firmware upgrade mode with Openmoko ID
        # Bus 003 Device 019: ID 1d50:60b6
        elif device.vid == 0x1d50 and device.pid == 0x60b6:
            all_boards.append(
                Board(dev=device, type="atlys", state="jtag"))

        # Digilent Atlys board JTAG/firmware upgrade mode with Openmoko ID
        # Bus 003 Device 019: ID 1d50:60b7
        elif device.vid == 0x1d50 and device.pid == 0x60b7:
            all_boards.append(
                Board(dev=device, type="atlys", state="operational"))

        # Numato Opsis
        # --------------------------
        # The Numato Opsis will boot in the following mode when the EEPROM is
        # not set up correctly.
        # http://opsis.hdmi2usb.tv/getting-started/usb-ids.html#failsafe-mode
        # Bus 003 Device 091: ID 04b4:8613 Cypress Semiconductor Corp.
        # CY7C68013 EZ-USB FX2 USB 2.0 Development Kit
        elif device.vid == 0x04b4 and device.pid == 0x8613:
            all_boards.append(
                Board(dev=device, type="opsis", state="unconfigured"))

        # The preproduction Numato Opsis shipped to Champions will boot into
        # this mode by default.
        # The production Numato Opsis will fallback to booting in the following
        # mode when the FPGA doesn't have EEPROM emulation working.
        # http://opsis.hdmi2usb.tv/getting-started/usb-ids.html#unconfigured-mode
        # Bus 003 Device 091: ID 2a19:5440 Numato Opsis (Unconfigured Mode)
        elif device.vid == 0x2A19 and device.pid == 0x5440:
            all_boards.append(
                Board(dev=device, type="opsis", state="unconfigured"))

        # The production Numato Opsis will boot in this mode when SW1 is held
        # during boot, or when held for 5 seconds with correctly configured
        # FPGA gateware.
        # http://opsis.hdmi2usb.tv/getting-started/usb-ids.html#usb-jtag-and-usb-uart-mode
        # Bus 003 Device 091: ID 2a19:5441 Numato Opsis (JTAG and USB Mode)
        elif device.vid == 0x2A19 and device.pid == 0x5441:
            if device.did == '0001':
                all_boards.append(
                    Board(dev=device, type="opsis", state="jtag"))
            elif device.did == '0002':
                all_boards.append(
                    Board(dev=device, type="opsis", state="eeprom"))
            elif device.did == '0003':
                all_boards.append(
                    Board(dev=device, type="opsis", state="serial"))
            else:
                assert False, "Unknown mode: %s" % device.did

        # The production Numato Opsis will boot in this mode by default.
        # http://opsis.hdmi2usb.tv/getting-started/usb-ids.html#hdmi2usb.tv-mode
        # Bus 003 Device 091: ID 2a19:5441 Numato Opsis (HDMI2USB.tv mode)
        elif device.vid == 0x2A19 and device.pid == 0x5442:
            all_boards.append(
                Board(dev=device, type="opsis", state="operational"))

        # ixo-usb-jtag
        # --------------------------
        # Boards loaded with the ixo-usb-jtag firmware from mithro's repo
        # https://github.com/mithro/ixo-usb-jtag
        # Bus 003 Device 090: ID 16c0:06ad Van Ooijen Technische Informatica
        elif device.vid == 0x16c0 and device.pid == 0x06ad:
            if device.did in ('0001', '0004'):
                if device.serialno not in USBJTAG_MAPPING:
                    logging.warn("Unknown usb-jtag device! %r (%s)",
                                 device.serialno, device)
                    continue
                all_boards.append(Board(dev=device, type=USBJTAG_MAPPING[
                                  device.serialno], state="jtag"))
            elif device.did == 'ff00':
                all_boards.append(
                    Board(dev=device, type='opsis', state="jtag"))
            else:
                logging.warn(
                    "Unknown usb-jtag device version! %r (%s)",
                    device.did,
                    device)
                continue

    # FIXME: This is a horrible hack!?@
    # Patch the Atlys board so the exar_uart is associated with it.
    if exart_uarts:
        atlys_boards = [b for b in all_boards if b.type == "atlys"]
        sys.stderr.write(
            " Found exart-uarts at %s associating with Atlys at %s\n" %
            (exart_uarts, atlys_boards))
        assert len(exart_uarts) == len(atlys_boards)
        assert len(atlys_boards) == 1

        def extra_tty(
                uart=exart_uarts[0],
                board=atlys_boards[0],
                prefer=args.prefer_hardware_serial):
            if prefer:
                return uart.tty + board.dev.tty
            else:
                return board.dev.tty + uart.tty

        atlys_boards[0].tty = extra_tty

    return all_boards
