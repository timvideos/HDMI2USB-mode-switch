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

def assert_in(needle, haystack):
    assert needle in haystack, "%r not in %r" % (needle, haystack)

PathBase = namedtuple('PathBase', ['bus', 'address'])
class Path(PathBase):
    def __new__(cls, *args, **kw):
        r = PathBase.__new__(cls, *args, **kw)
        assert os.path.exists(r.path), "%r %r" % (r.path, r)
        return r

    @property
    def path(self):
        return '/dev/bus/usb/%03i/%03i' % (self.bus, self.address)

    def __str__(self):
        return self.path

    def __cmp__(self, other):
        if isinstance(other, Path):
            return cmp(self.path, other.path)
        return cmp(self.path, other)


Device = namedtuple('Device', ['path', 'vid', 'pid', 'did', 'serialno'])
#Device.__cmp__ = lambda a, b: cmp(a.path, b.path)

def find_usb_devices_libusb():
    class LibDevice(Device):
        def inuse(self, dev=None):
            try:
                if dev is None:
                    dev = usb.core.find(bus=self.path.bus, address=self.path.address)

                #config = dev.get_active_configuration()
                active = False
                for config in dev:
                    for i, inf in enumerate(config):
                        inf_active = dev.is_kernel_driver_active(inf.bInterfaceNumber)
                        active = active or inf_active
                return active
            except usb.core.USBError:
                return None

        def detach(self):
            # Detach any driver currently attached.
            dev = usb.core.find(bus=self.path.bus, address=self.path.address)

            if not self.inuse(dev):
                return True

            config = dev.get_active_configuration()
            for inf in config:
                if dev.is_kernel_driver_active(inf.bInterfaceNumber):
                    dev.detach_kernel_driver(inf.bInterfaceNumber)

    import usb
    if usb.__file__.endswith('.so'):
        logging.warning("Your python usb module is old.")
    import usb.util

    busses = usb.busses()

    devobjs = []
    for dev in usb.core.find(find_all=True):
        serialno = None
        if dev.iSerialNumber > 0:
            try:
                serialno = dev.serial_number
            except usb.USBError:
                pass

        devobjs.append(LibDevice(vid=dev.idVendor, pid=dev.idProduct, did=dev.bcdDevice, serialno=serialno, path=Path(bus=dev.bus, address=dev.address)))
    return devobjs

def find_usb_devices_lsusb():
    import re
    import subprocess

    FIND_SYS_CACHE.clear()

    # 'Bus 002 Device 002: ID 8087:0024 Intel Corp. Integrated Rate Matching Hub'
    lsusb_device_regex = re.compile(
        "Bus (?P<bus>[0-9]+) Device (?P<address>[0-9]+):"
        " ID (?P<vid>[0-9a-f]+):(?P<pid>[0-9a-f]+)")

    class LsusbDevice(Device):
        def __new__(cls, *args, **kw):
            syspaths = find_sys(kw['path'])
            syspaths.sort()

            # Get the did number from sysfs
            didpath = os.path.join(syspaths[0], "bcdDevice")
            if not os.path.exists(didpath):
                did = None
            else:
                did = open(didpath, "r").read().strip()

            # Get the did number from sysfs
            serialnopath = os.path.join(syspaths[0], "serial")
            if not os.path.exists(serialnopath):
                serialno = None
            else:
                serialno = open(serialnopath, "r").read().strip()

            d = Device.__new__(cls, *args, did=did, serialno=serialno, **kw)
            d.syspaths = syspaths
            return d

        def __repr__(self):
            if self.serialno:
                s = repr(self.serialno)
            else:
                s = self.path
            return "%s(%04x:%04x:%s %s)" % (
                self.__class__.__name__, self.vid, self.pid, self.did, s)

        def inuse(self):
            return bool(self.drivers())

        def drivers(self):
            drivers = {}
            for path in self.syspaths[1:]:
                driver_path = os.path.join(path, "driver")
                if os.path.exists(driver_path):
                    drivers[path] = os.readlink(driver_path)
            return tuple(set(d.split('/')[-1] for d in drivers.values()))

        def detach(self):
            for path in self.syspaths[1:]:
                driver_path = os.path.join(path, "driver")
                if os.path.exists(driver_path):
                    unbind_path = os.path.join(driver_path, "unbind")
                    assert os.path.exists(unbind_path), unbind_path
                    interface = os.path.split(path)[-1]
                    try:
                        open(unbind_path, "w").write(interface)
                    except PermissionError:
                        subprocess.check_call("bin/unbind-helper '%s' '%s'" % (unbind_path, interface), shell=True)

        def tty(self):
            ttys = []
            for path in self.syspaths:
                tty_path = os.path.join(path, "tty")
                if os.path.exists(tty_path):
                    names = list(os.listdir(tty_path))
                    assert len(names) == 1
                    ttys.append('/dev/'+names[0])
            return ttys


    devobjs = []
    output = subprocess.check_output('lsusb')
    for line in output.splitlines():
        line = line.decode('utf-8')
        bits = lsusb_device_regex.match(line)
        assert bits, repr(line)

        vid = int(bits.group('vid'), base=16)
        pid = int(bits.group('pid'), base=16)
        bus = int(bits.group('bus'), base=10)
        address = int(bits.group('address'), base=10)
        devobjs.append(LsusbDevice(
            vid=vid, pid=pid, path=Path(bus=bus, address=address),
            ))

    return devobjs

SYS_ROOT = '/sys/bus/usb/devices'

def get_path_from_sysdir(dirpath):
    buspath = os.path.join(dirpath, 'busnum')
    devpath = os.path.join(dirpath, 'devnum')
    if not os.path.exists(buspath):
        logging.info("Skipping %s (no busnum)", dirname)
        return None
    if not os.path.exists(devpath):
        logging.info("Skipping %s (no devnum)", dirname)
        return None

    busnum = int(open(buspath, 'r').read().strip())
    devnum = int(open(devpath, 'r').read().strip())

    return Path(bus=busnum, address=devnum)

def create_sys_mapping():
    # 1-1.3.1  --> (Device)    bus-port.port.port
    # 1-0:1.0  --> (Interface) bus-port.port.port:config.interface
    # usb1     --> bus<number>

    devices = {}
    interfaces = {}

    dirs = list(sorted(os.listdir(SYS_ROOT)))
    for dirname in dirs:
        dirpath = os.path.join(SYS_ROOT, dirname)
        if ":" in dirname:
            continue
        path = get_path_from_sysdir(dirpath)
        assert path
        devices[dirpath] = path
        assert path not in interfaces
        interfaces[path] = [dirpath]

    for dirname in dirs:
        dirpath = os.path.join(SYS_ROOT, dirname)
        if ":" not in dirname:
            continue

        device, interface = dirname.split(':')
        if device.endswith('-0'):
            device = "usb%s" % (device[:-2])

        devpath = os.path.join(SYS_ROOT, device)
        assert os.path.exists(devpath)
        assert devpath in devices

        interfaces[devices[devpath]].append(dirpath)

    return interfaces


FIND_SYS_CACHE = {}
def find_sys(path, mapping=FIND_SYS_CACHE):
    if not mapping:
        mapping.update(create_sys_mapping())
    return mapping[path]


def test_libusb_and_lsusb_equal():
    libusb_devices = find_usb_devices_libusb()
    lsusb_devices = find_usb_devices_lsusb()
    for libobj, lsobj in zip(sorted(libusb_devices), sorted(lsusb_devices)):
        print("%s -- lib: %-40s ls: %-40s -- %-40s  drivers: %s" % (libobj.path, libobj, lsobj, find_sys(libobj.path)[0], lsobj.drivers()))
        assert libobj.vid == lsobj.vid, "%r == %r" % (libobj.vid, lsobj.vid)
        assert libobj.pid == lsobj.pid, "%r == %r" % (libobj.pid, lsobj.pid)
        if libobj.serialno:
            assert libobj.serialno == lsobj.serialno, "%r == %r" % (libobj.serialno, lsobj.serialno)
        assert libobj.path == lsobj.path, "%r == %r" % (libobj.path, lsobj.path)

        lsobj_inuse = lsobj.inuse()
        libobj_inuse = libobj.inuse()
        if libobj_inuse is not None:
            assert libobj_inuse == lsobj_inuse, "%r == %r" % (libobj_inuse, lsobj_inuse)


BOARD_TYPES = ['opsis', 'atlys']
BOARD_NAMES = {
    'atlys': "Digilent Atlys",
    'opsis': "Numato Opsis",
    }
BOARD_STATES = ['unconfigured', 'jtag', 'serial', 'eeprom', 'operational']

USBJTAG_MAPPING = {
    'hw_nexys': 'atlys',
    'hw_opsis': 'opsis',
    }
USBJTAG_RMAPPING = {v:k for k,v in USBJTAG_MAPPING.items()}
OPENOCD_MAPPING = {
    'atlys': "board/digilent_atlys.cfg",
    'opsis': "board/numato_opsis.cfg",
    }
OPENOCD_FLASHPROXY = {
    'opsis': 'flash_proxy/opsis/bscan_spi_xc6slx45t.bit',
    'atlys': 'flash_proxy/atlys/bscan_spi_xc6slx45.bit',
}

BoardBase = namedtuple("Board", ["dev", "type", "state"])
class Board(BoardBase):
    def tty(self):
        return self.dev.tty()


def load_fx2(board, filename, verbose=False):
    if board.dev.inuse():
        if verbose:
            sys.stderr.write("Detaching drivers from board.\n")
        board.dev.detach()

    filepath = os.path.abspath(filename)
    assert os.path.exists(filepath), filepath

    cmdline = "fxload -t fx2lp".split()
    cmdline += ["-D", str(board.dev.path)]
    cmdline += ["-I", filepath]
    if verbose:
        cmdline += ["-v",]

    if verbose:
        sys.stderr.write("Running %r\n" % " ".join(cmdline))

    try:
        output = subprocess.check_output(cmdline, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        if not b"can't modify CPUCS: Protocol error\n" in e.stdout:
            print(e.stdout)
            raise


def flash_fx2(board, filename, verbose=False):
    assert board.state == "eeprom", board
    assert not board.dev.inuse()

    assert board.type == "opsis", "Only support flashing the Opsis for now (not %s)." % board.type


def load_fpga(board, filename, verbose=False):
    assert board.state == "jtag", board
    assert not board.dev.inuse()
    assert board.type in OPENOCD_MAPPING

    filepath = os.path.abspath(filename)
    assert os.path.exists(filepath), filepath

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
    assert board.type == "opsis", "Only support flashing the Opsis for now (not %s)." % board.type

    filepath = os.path.abspath(filename)
    assert os.path.exists(filepath), filepath

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

    #script += ["flash read_bank 0 backup.bit 0 0x01000000"]

    script += [
        #"jtagspi_program {} 0x{:x}".format(data, address),
        #"fpga_program",
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
    for device in find_usb_devices_lsusb():
        # Digilent Atlys board with stock "Adept" firmware
        # Bus 003 Device 019: ID 1443:0007 Digilent Development board JTAG
        if device.vid == 0x1443 and device.pid == 0x0007:
            all_boards.append(Board(dev=device, type="atlys", state="unconfigured"))

        # The Numato Opsis will boot in the following mode when the EEPROM is not
        # set up correctly.
        # http://opsis.hdmi2usb.tv/getting-started/usb-ids.html#failsafe-mode
        # Bus 003 Device 091: ID 04b4:8613 Cypress Semiconductor Corp. CY7C68013 EZ-USB FX2 USB 2.0 Development Kit
        elif device.vid == 0x04b4 and device.pid == 0x8613:
            all_boards.append(Board(dev=device, type="opsis", state="unconfigured"))

        # The preproduction Numato Opsis shipped to Champions will boot into this
        # mode by default.
        # The production Numato Opsis will fallback to booting in the following
        # mode when the FPGA doesn't have EEPROM emulation working.
        # http://opsis.hdmi2usb.tv/getting-started/usb-ids.html#unconfigured-mode
        # Bus 003 Device 091: ID 2a19:5440 Numato Opsis (Unconfigured Mode)
        elif device.vid == 0x2A19 and device.pid == 0x5440:
            all_boards.append(Board(dev=device, type="opsis", state="unconfigured"))

        # The production Numato Opsis will boot in this mode when SW1 is held
        # during boot, or when held for 5 seconds with correctly configured FPGA
        # gateware.
        # http://opsis.hdmi2usb.tv/getting-started/usb-ids.html#usb-jtag-and-usb-uart-mode
        # Bus 003 Device 091: ID 2a19:5441 Numato Opsis (JTAG and USB Mode)
        elif device.vid == 0x2A19 and device.pid == 0x5441:
            if device.did == '0001':
                all_boards.append(Board(dev=device, type="opsis", state="jtag"))
            elif device.did == '0002':
                all_boards.append(Board(dev=device, type="opsis", state="eeprom"))
            elif device.did == '0003':
                all_boards.append(Board(dev=device, type="opsis", state="serial"))
            else:
                assert False, "Unknown mode: %s" % device.did

        # The production Numato Opsis will boot in this mode by default.
        # http://opsis.hdmi2usb.tv/getting-started/usb-ids.html#hdmi2usb.tv-mode
        # Bus 003 Device 091: ID 2a19:5441 Numato Opsis (HDMI2USB.tv mode)
        elif device.vid == 0x2A19 and device.pid == 0x5442:
            all_boards.append(Board(dev=device, type="opsis", state="operational"))

        # Boards loaded with the ixo-usb-jtag firmware from mithro's repo
        # https://github.com/mithro/ixo-usb-jtag
        # Bus 003 Device 090: ID 16c0:06ad Van Ooijen Technische Informatica 
        elif device.vid == 0x16c0 and device.pid == 0x06ad:
            if device.did == '0001':
                if device.serialno not in USBJTAG_MAPPING:
                    logging.warn("Unknown usb-jtag device! %r (%s)", device.serialno, device)
                    continue
                all_boards.append(Board(dev=device, type=USBJTAG_MAPPING[device.serialno], state="jtag"))
            elif device.did == 'ff00':
                all_boards.append(Board(dev=device, type='opsis', state="jtag"))
            else:
                    logging.warn("Unknown usb-jtag device version! %r (%s)", device.did, device)
                    continue

    # FIXME: This is a horrible hack!?@
    # Patch the Atlys board so the exart_uart is associated with it.
    if exart_uarts:
        atlys_boards = [b for b in all_boards if b.type == "atlys"]
        sys.stderr.write(" Found exart-uarts at %s associating with Atlys at %s\n" % (
            exart_uarts, atlys_boards))
        assert len(exart_uarts) == len(atlys_boards)
        assert len(atlys_boards) == 1

        def extra_tty(uart=exart_uarts[0], board=atlys_boards[0], prefer=args.prefer_hardware_serial):
            if prefer:
                return uart.tty + board.dev.tty
            else:
                return board.dev.tty + uart.tty

        atlys_boards[0].tty = extra_tty

    return all_boards


