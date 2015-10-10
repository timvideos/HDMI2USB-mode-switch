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
    def __init__(self, *args, **kw):
        PathBase.__init__(self, *args, **kw)
        assert os.path.exists(self.path), "%r %r" % (self.path, self)

    @property
    def path(self):
        return '/dev/bus/usb/%03i/%03i' % (self.bus, self.address)

    def __str__(self):
        return self.path

    def __cmp__(self, other):
        if isinstance(other, Path):
            return cmp(self.path, other.path)
        return cmp(self.path, other)


Device = namedtuple('Device', ['path', 'vid', 'pid', 'serialno'])
Device.__str__ = lambda self: "Device(%04x:%04x %s)" % (self.vid, self.pid, [self.path, repr(self.serialno)][bool(self.serialno)])
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

        devobjs.append(LibDevice(vid=dev.idVendor, pid=dev.idProduct, serialno=serialno, path=Path(bus=dev.bus, address=dev.address)))
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
            return Device.__new__(cls, *args, serialno=None, **kw)

        @property
        def serialno(self):
            # Get the serialno number from the device and cache it.
            if not hasattr(self, "_serialno"):
                serialnopath = os.path.join(self.syspaths[0], "serial")
                if not os.path.exists(serialnopath):
                    self._serialno = None
                else:
                    self._serialno = open(serialnopath, "r").read().strip()
            return self._serialno

        @property
        def syspaths(self):
            if not hasattr(self, "_syspaths"):
                self._syspaths = find_sys(self.path)
            return self._syspaths

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
                    open(unbind_path, "w").write(interface)

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
        print "%s -- lib: %-40s ls: %-40s -- %-40s  drivers: %s" % (libobj.path, libobj, lsobj, find_sys(libobj.path)[0], lsobj.drivers())
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
BOARD_STATES = ['unconfigured', 'jtag', 'serial', 'operational']

USBJTAG_MAPPING = {
    'hw_nexys': 'atlys',
    'hw_opsis': 'opsis',
    }
USBJTAG_RMAPPING = {v:k for k,v in USBJTAG_MAPPING.items()}

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

    subprocess.check_call(cmdline)


# Parse the command line name
cmd = os.path.basename(sys.argv[0])
if cmd.endswith('.py'):
    cmd = cmd.rsplit('.', 1)[0]

BOARD, MODE = cmd.split('-', 1)
assert_in(BOARD, BOARD_TYPES+['hdmi2usb'])
POSSIBLE_MODES = ['find-board', 'mode-switch']
assert_in(MODE, POSSIBLE_MODES)

# Parse the arguments
import argparse
parser = argparse.ArgumentParser(description=__doc__)

parser.add_argument('--verbose', '-v', action='count', help='Output more information.') #, aliases=['--debug', '-d'])

if BOARD == "hdmi2usb":
    parser.add_argument('--by-type', help='Find board with a given type.', choices=BOARD_TYPES)

parser.add_argument('--by-mac', help='Find board with the given MAC address.')
parser.add_argument('--by-dna', help='Find board with the given Device DNA.')
parser.add_argument('--by-position', help="""Find board using a given position in the USB structure.
Example:
 1-2.3 - Bus 1, Port 2 (which is a hub), Port 3
 5-6.7.8 - Bus 5, Port 2 (which is a hub), Port 7 (which is a hub), Port 8 (which is a hub)

While this *should* be static across reboots, but sadly on some machines it isn't :(
""")
parser.add_argument('--by-mode', help=argparse.SUPPRESS) # help='Find board in a given mode.', )

parser.add_argument('--all', help='Do operation on all boards, otherwise will error if multiple boards are found.')

parser.add_argument('--get-usbfs', action='store_true', help='Return the /dev/bus/usb path for a device.')
parser.add_argument('--get-sysfs', action='store_true', help='Return the /sys/bus/usb/devices path for a device.')
parser.add_argument('--get-state', action='store_true', help='Return the state the device is in. Possible states are: %r' % BOARD_STATES)
parser.add_argument('--get-video-device', action='store_true', help='Get the primary video device path.')
parser.add_argument('--get-serial-device', action='store_true', help='Get the serial device path.')

parser.add_argument('--prefer-hardware-serial', help='Prefer the hardware serial port on the Atlys board.')

if MODE == 'mode-switch':
    parser.add_argument('--mode', help='Switch mode to given state.', choices=BOARD_STATES)
    parser.add_argument('--load-gateware', help='Load gateware onto the FPGA.')
    parser.add_argument('--load-fx2-firmware', help='Load firmware file onto the Cypress FX2.')
    parser.add_argument('--load-lm32-firmware', help='Load firmware file onto the lm32 Soft-Core running inside the FPGA.')

    parser.add_argument('--timeout', help='How long to wait in seconds before giving up.', type=float)

args = parser.parse_args()


if BOARD != "hdmi2usb":
    args.by_type = BOARD
if args.by_type:
    assert_in(args.by_type, BOARD_TYPES)

def find_hdmi2usb_boards(args):
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
            all_boards.append(Board(dev=device, type="opsis", state="jtag"))

        # The production Numato Opsis will boot in this mode by default.
        # http://opsis.hdmi2usb.tv/getting-started/usb-ids.html#hdmi2usb.tv-mode
        # Bus 003 Device 091: ID 2a19:5441 Numato Opsis (HDMI2USB.tv mode)
        elif device.vid == 0x2A19 and device.pid == 0x5442:
            all_boards.append(Board(dev=device, type="opsis", state="operational"))

        # fx2lib CDC-ACM example
        # Bus 003 Device 091: ID 04b4:1004 Cypress Semiconductor Corp.
        # [1477170.025176] usb 3-4.4: Product: There
        # [1477170.025178] usb 3-4.4: Manufacturer: Hi
        # [1477170.025179] usb 3-4.4: SerialNumber: ffff001ec0f1419b
        elif device.vid == 0x04b4 and device.pid == 0x1004:
            all_boards.append(Board(dev=device, type="opsis", state="serial"))

        # Boards loaded with the ixo-usb-jtag firmware from mithro's repo
        # https://github.com/mithro/ixo-usb-jtag
        # Bus 003 Device 090: ID 16c0:06ad Van Ooijen Technische Informatica 
        elif device.vid == 0x16c0 and device.pid == 0x06ad:
            if device.serialno not in USBJTAG_MAPPING:
                logging.warn("Unknown usb-jtag device! %r (%s)", device.serialno, device)
                continue
            all_boards.append(Board(dev=device, type=USBJTAG_MAPPING[device.serialno], state="jtag"))

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

    # Filter out the boards we don't care about
    filtered_boards = []
    for board in all_boards:
        if args.verbose > 0:
            sys.stderr.write("%s in '%s' mode at %s\n" % (
                BOARD_NAMES[board.type],
                board.state,
                board.dev.path,
                ))
            for sp in board.dev.syspaths:
                sys.stderr.write(" %s\n" % (sp,))

            if board.dev.inuse():
                sys.stderr.write(" Board is currently used by drivers %s\n" % (board.dev.drivers(),))

            if board.tty():
                sys.stderr.write(" Serial port at %s\n" % ", ".join(board.tty()))

        if args.by_type and args.by_type != board.type:
            if args.verbose > 0:
                sys.stderr.write(" Ignore as not type %s\n" % (args.by_type,))
            continue

        filtered_boards.append(board)

    return filtered_boards

boards = find_hdmi2usb_boards(args)
if not args.all:
    assert len(boards) == 1

MYDIR=os.path.dirname(os.path.abspath(__file__))
if args.verbose:
    sys.stderr.write("My root dir: %s\n" % MYDIR)

if MODE == 'mode-switch':
    for board in boards:
        # Load gateware onto the FPGA
        if args.load_gateware:
            assert args.mode in ("jtag", None)
            raise NotImplemented("Not yet finished...")

        # Load firmware onto the fx2
        elif args.load_fx2_firmware:
            assert args.mode == None
            print "fxload something...."
            raise NotImplemented("Not yet finished...")

        # Load firmware onto the lm32
        elif args.load_lm32_firmware:
            if board.type == "opsis":
                assert board.state == "serial"
            assert board.tty
            print "flterm something...."
            raise NotImplemented("Not yet finished...")

        # Else just switch modes
        elif args.mode:
            newmode = args.mode
            if newmode == "jtag":
                firmware = os.path.join(
                    "fx2-firmware",
                    board.type,
                    "ixo-usb-jtag.hex")

            elif newmode == "serial":
                assert board.type == "opsis", "serial mode only valid on the opsis."
                firmware = os.path.join(
                    "fx2-firmware",
                    board.type,
                    "usb-uart.ihx"
                    )
            elif newmode == "operational":
                raise NotImplemented("Not yet finished...")

            if args.verbose:
                sys.stderr.write("Going from %s to %s\n" % (board.state, newmode))
                sys.stderr.write("Using firmware %s\n" % firmware)

            if board.state != newmode:
                old_board = board
                load_fx2(old_board, firmware, verbose=args.verbose)

                starttime = time.time()
                while True:
                    boards = find_hdmi2usb_boards(args)

                    found_board = None
                    for new_board in boards:
                        print "%s %s" % (new_board, old_board)
                        if new_board.type == old_board.type:
                            if new_board.state == old_board.state:
                                continue
                            assert new_board.state == newmode
                            found_board = new_board
                            break
                    else:
                        time.sleep(1)

                    if found_board:
                        break

                    if args.timeout and starttime - time.time() > args.timeout:
                        raise SystemError("Timeout!")
        
        # Invalid configuration...
        else:
            raise SystemError("Need to specify --load-XXX or --mode")

    boards = find_hdmi2usb_boards(args)

for board in boards:
    if not (args.get_usbfs or args.get_sysfs or args.get_video_device or args.get_serial_device):
        print "Found %s boards." % len(boards)
        break

    if args.get_usbfs:
        print board.dev.path

    if args.get_sysfs:
        print "\n".join(board.dev.syspaths)

    if args.get_state:
        print board.state

    if args.get_video_device:
        assert board.state == "operational"
        print "???"

    if args.get_serial_device:
        print board.tty()[0]


"""
        if board.state == "unconfigured":
            sys.stderr.write(" Configure with 'fxload -t fx2lp -D %s -I %s'\n" % (
                ))
"""
