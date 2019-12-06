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
import re

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


def poll_until(condition, timeout_sec, dt=0.1):
    start_time = time.time()
    satisfied = condition()
    while not satisfied and (time.time() - start_time) < timeout_sec:
        satisfied = condition()
        time.sleep(dt)
    return satisfied


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
BOARD_FLASH_MAP = {
    # https://github.com/timvideos/HDMI2USB-litex-firmware/blob/master/targets/atlys/base.py#L205-L215
    'atlys': {'gateware': 0x0, 'bios': 0x00200000, 'firmware': 0x00208000},
    # https://github.com/timvideos/HDMI2USB-litex-firmware/blob/master/targets/opsis/base.py#L256-L266
    'opsis': {'gateware': 0x0, 'bios': 0x00200000, 'firmware': 0x00208000},
    # https://github.com/timvideos/HDMI2USB-litex-firmware/blob/master/targets/mimasv2/base.py#L208-L220
    'mimasv2': {'gateware': 0x0, 'bios': 0x00080000, 'firmware': 0x00088000},
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


def detach_board_drivers(board, verbose=False):
    if board.dev.inuse():
        if verbose:
            sys.stderr.write("Detaching drivers from board.\n")
        board.dev.detach()


def load_fx2(board, mode=None, filename=None, verbose=False):
    if mode is not None:
        assert filename is None
        filename = firmware_path(
            'fx2/{}/{}'.format(board.type, FX2_MODE_MAPPING[mode]))

    detach_board_drivers(board, verbose=verbose)

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

    env = os.environ.copy()
    env['PATH'] = env['PATH'] + ':/usr/sbin:/sbin'

    try:
        output = subprocess.check_output(
            cmdline, stderr=subprocess.STDOUT, env=env)
        if verbose > 2:
            sys.stderr.write(output.decode('utf-8'))
    except subprocess.CalledProcessError as e:
        if b"can't modify CPUCS: Protocol error\n" not in e.output:
            print(e.output)
            raise


def load_fx2_dfu_bootloader(board, verbose=False, filename='boot-dfu.ihex'):
    """
    Loads bootloader firmware onto given board and updates the board to point
    to correct device. The device is identified using previous SysFs path of
    the device, which should be guaranteed not to change.
    """
    # use current sysfs path to later identify the bootloader after enumeration
    dev_syspath = sorted(board.dev.syspaths)[0]
    # because the sysfs path does not dissappear after loading new firmware,
    # we also have to make sure that the device path (/dev/bus/usb/xxx/xxx)
    # is different to ensure that we are dealing with a new device
    previous_dev_path = board.dev.path

    def is_bootloader(dev):
        is_new_dev = dev.path != previous_dev_path
        same_syspath = dev_syspath in dev.syspaths
        return is_new_dev and same_syspath

    def find_bootloader():
        devices = filter(is_bootloader, usbapi.find_usb_devices())
        return list(devices)

    load_fx2(board, filename=filename, verbose=verbose)

    # wait for the new device to enumerate
    devices_found = poll_until(condition=find_bootloader, timeout_sec=3)

    assert len(devices_found) > 0, 'Bootloader not found'
    assert len(devices_found) == 1, 'More than one bootloader found'

    board = Board(dev=devices_found[0], type=board.type, state='dfu-boot')
    return board


def flash_fx2(board, filename, verbose=False):
    assert filename.endswith('.dfu'), 'Firmware file must be in DFU format.'

    detach_board_drivers(board, verbose=verbose)

    filepath = firmware_path(filename)
    assert os.path.exists(filepath), filepath

    sys.stderr.write("Using FX2 firmware %s\n" % filename)

    cmdline = ["dfu-util", "-D", filepath]
    if verbose:
        cmdline += ["-v", ]

    if verbose:
        sys.stderr.write("Running %r\n" % " ".join(cmdline))

    env = os.environ.copy()
    env['PATH'] = env['PATH'] + ':/usr/sbin:/sbin'

    output = subprocess.run(cmdline, stderr=subprocess.STDOUT, env=env)


class OpenOCDError(subprocess.CalledProcessError):
    def __init__(
            self, msg, fatal_errors, retry_errors, returncode, cmd, output):
        subprocess.CalledProcessError.__init__(
            self, returncode, cmd, output)

        fatal = ""
        if fatal_errors:
            fatal = "\n".join(
                ["\nFound fatal errors: "] + [" - " + f for f in fatal_errors]
            )
            retry += "\n"

        retry = ""
        if retry_errors:
            retry = "\n".join(
                ["\nFound retry errors: "] + [" - " + f for f in retry_errors]
            )

        self.message = """\
OpenOCD run failure: {msg}.
{fatal}{retry}
OpenOCD command line resulted in {returncode}
-----
{cmd}
-----

OpenOCD output:
-----
{output}
-----
""".format(msg=msg, retry=retry, fatal=fatal, returncode=returncode, cmd=cmd,
           output=output)

    def __str__(self):
        return self.message


class OpenOCDRetryError(OpenOCDError):
    pass


def _openocd_script(board, script, verbose=False):
    assert board.state == "jtag", board
    assert not board.dev.inuse()
    assert board.type in OPENOCD_MAPPING
    if verbose > 1:
        sys.stderr.write(
            "Using OpenOCD script:\n{}\n".format(";\n".join(script)))

    cmdline = ["openocd"]
    cmdline += ["-f", OPENOCD_MAPPING[board.type]]
    cmdline += ["-c", "; ".join(script)]
    if verbose > 1:
        cmdline += ["--debug={}".format(verbose - 2)]

    if verbose:
        sys.stderr.write("Running %r\n" % cmdline)

    p = subprocess.Popen(
        cmdline,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    if not verbose:
        output, _ = p.communicate()
        output = output.decode('utf-8')
    else:
        output = []
        while True:
            output.append(p.stdout.readline().decode('utf-8'))
            sys.stdout.write(output[-1])
            if p.poll() is not None:
                break
        output = "".join(output)

    # Look for common errors in the OpenOCD output
    retry_strings = [
        # DNA Failed to read correctly if this error is seen.
        "DNA = [01]+ \\(0x18181818.*\\)",

        # JTAG Errors
        "Info : TAP xc6s.tap does not have IDCODE",
        "Warn : Bypassing JTAG setup events due to errors",
        "Error: Trying to use configured scan chain anyway...",
    ]
    retry_error_msgs = set()
    for msg in retry_strings:
        found = re.search(msg, output)
        if not found:
            continue
        retry_error_msgs.add(found.group(0))

    # Look for common errors in the OpenOCD output
    fatal_strings = [
        # FIXME: Put something here.
    ]
    fatal_error_msgs = set()
    for msg in fatal_strings:
        found = re.search(msg, output)
        if not found:
            continue
        fatal_error_msgs.add(found.group(0))

    if p.returncode == 0 and not retry_error_msgs.union(fatal_error_msgs):
        return

    if fatal_error_msgs:
        msg = "Fatal error!"
        openocd_error = OpenOCDError
    else:
        msg = "Error which means we should retry..."
        openocd_error = OpenOCDRetryError

    raise openocd_error(
        msg,
        fatal_error_msgs,
        retry_error_msgs,
        p.returncode,
        cmdline,
        output,
    )


def _openocd_flash(board, filepath, location, verbose=False):
    assert board.type in OPENOCD_FLASHPROXY
    proxypath = os.path.abspath(OPENOCD_FLASHPROXY[board.type])
    assert os.path.exists(proxypath), proxypath

    script = ["init"]
    script += ["xc6s_print_dna xc6s.tap"]
    script += ["jtagspi_init 0 {}".format(proxypath)]

    if verbose > 1:
        script += ["flash banks"]
        script += ["flash list"]
    if verbose > 2:
        script += ["flash info 0"]

    # script += ["flash read_bank 0 backup.bit 0 0x01000000"]

    script += [
        "jtagspi_program {} 0x{:x}".format(filepath, location),
        "exit"
    ]

    try:
        return _openocd_script(board, script, verbose=verbose)
    finally:
        print("After flashing, the board will need to be power cycled.")


def reset_gateware(board, verbose=False):
    script = ["init"]
    script += ["xc6s_print_dna xc6s.tap"]
    script += ["reset halt"]
    script += ["exit"]

    return _openocd_script(board, script, verbose=verbose)


def load_gateware(board, filename, verbose=False):
    filepath = firmware_path(filename)
    assert os.path.exists(filepath), filepath
    assert filename.endswith(".bit"), "Loading requires a .bit file"
    xfile = files.XilinxBitFile(filepath)
    assert xfile.part == BOARD_FPGA[board.type], (
        "Bit file must be for {} (not {})".format(
            BOARD_FPGA[board.type], xfile.part))

    script = ["init"]
    script += ["xc6s_print_dna xc6s.tap"]
    script += ["pld load 0 {}".format(filepath)]
    script += ["reset halt"]
    script += ["exit"]

    return _openocd_script(board, script, verbose=verbose)


def flash_gateware(board, filename, verbose=False):
    filepath = firmware_path(filename)
    assert os.path.exists(filepath), filepath
    assert filename.endswith(".bin"), "Flashing requires a Xilinx .bin file"
    xfile = files.XilinxBinFile(filepath)

    _openocd_flash(
        board,
        filepath,
        BOARD_FLASH_MAP[board.type]['gateware'],
        verbose=verbose)


def flash_bios(board, filename, verbose=False):
    filepath = firmware_path(filename)
    assert os.path.exists(filepath), filepath
    assert filename.endswith(".bin"), "Flashing requires a .bin file"
    # FIXME: Bios files have the CRC at the end, should check that here.

    _openocd_flash(
        board,
        filepath,
        BOARD_FLASH_MAP[board.type]['bios'],
        verbose=verbose)


def flash_firmware(board, filename, verbose=False):
    assert board.state == "jtag", board
    assert not board.dev.inuse()
    assert board.type in OPENOCD_MAPPING

    if filename is not None:
        filepath = firmware_path(filename)
        assert os.path.exists(filepath), filepath
        assert filename.endswith(".fbi"), "Flashing requires a .fbi file"
        fbifile = files.FlashBootImageFile(filepath)
    else:
        filepath = firmware_path("zero.bin")

    _openocd_flash(
        board,
        filepath,
        BOARD_FLASH_MAP[board.type]['firmware'],
        verbose=verbose)


flash_image = flash_gateware


def find_boards(prefer_hardware_serial=True, verbose=False):
    all_boards = []
    exart_uarts = []
    for device in usbapi.find_usb_devices():
        if False:
            pass

        # https://github.com/timvideos/HDMI2USB/wiki/USB-IDs
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

        # Digilent Atlys board JTAG/firmware upgrade mode with Openmoko ID.
        # Device ID 0x10 indicates test JTAG mode, 0x11 indicates test Serial,
        # 0x12 indicates test Audio and 0x13 indicates test UVC.
        # Bus 003 Device 019: ID 1d50:60b6
        elif device.vid == 0x1d50 and device.pid == 0x60b6:
            if device.did == '0001':
                all_boards.append(
                    Board(dev=device, type="atlys", state="jtag"))
            elif device.did == '0010':
                all_boards.append(
                    Board(dev=device, type="atlys", state="test-jtag"))
            elif device.did == '0011':
                all_boards.append(
                    Board(dev=device, type="atlys", state="test-serial"))
            elif device.did == '0012':
                all_boards.append(
                    Board(dev=device, type="atlys", state="test-audio"))
            elif device.did == '0013':
                all_boards.append(
                    Board(dev=device, type="atlys", state="test-uvc"))
            else:
                all_boards.append(
                    Board(dev=device, type="atlys", state="test-???"))

        # Digilent Atlys board in operational mode with Openmoko ID.
        # Bus 003 Device 019: ID 1d50:60b7
        elif device.vid == 0x1d50 and device.pid == 0x60b7:
            all_boards.append(
                Board(dev=device, type="atlys", state="operational"))

        elif device.vid == 0x04e2 and device.pid == 0x1410:
            exart_uarts.append(device)

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
            elif device.did == '0011':
                all_boards.append(
                    Board(dev=device, type="opsis", state="test-serial"))
            elif device.did == '0012':
                all_boards.append(
                    Board(dev=device, type="opsis", state="test-audio"))
            elif device.did == '0013':
                all_boards.append(
                    Board(dev=device, type="opsis", state="test-uvc"))
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
                all_boards.append(Board(
                    dev=device, type=USBJTAG_MAPPING[device.serialno],
                    state="jtag"))
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
    atlys_boards = [b for b in all_boards if b.type == "atlys"]
    if exart_uarts and atlys_boards:
        if verbose:
            sys.stderr.write(
                " Found exart-uarts at %s associating with Atlys at %s\n" %
                (exart_uarts, atlys_boards))
        assert len(exart_uarts) == len(atlys_boards), repr(
            (exart_uarts, atlys_boards))
        assert len(atlys_boards) == 1

        def extra_tty(
                uart=exart_uarts[0],
                board=atlys_boards[0],
                prefer=prefer_hardware_serial):
            if prefer:
                return uart.tty() + board.dev.tty()
            else:
                return board.dev.tty() + uart.tty()

        atlys_boards[0].tty = extra_tty

    return all_boards
