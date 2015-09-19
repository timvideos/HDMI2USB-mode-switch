#!/usr/bin/env python
# vim: set ts=4 sw=4 et sts=4 ai:

"""
Tool to figure find the USB device that a board is available at.

This is a complicated process as the FX2 is software configurable and hence
could end up under many different VID:PID names based on what firmware is
currently loaded onto it.
"""

import os
from collections import namedtuple
import logging

PathBase = namedtuple('PathBase', ['bus', 'address'])
class Path(PathBase):
    def __init__(self, *args, **kw):
        PathBase.__init__(self, *args, **kw)
        assert os.path.exists(self.path)

    @property
    def path(self):
        return '/dev/bus/usb/%03x/%03x' % (self.bus, self.address)

    def __str__(self):
        return self.path

    def __cmp__(self, other):
        if isinstance(other, Path):
            return cmp(self.path, other.path)
        return cmp(self.path, other)


Device = namedtuple('Device', ['path', 'vid', 'pid', 'serial'])
Device.__str__ = lambda self: "Device(%04x:%04x %s)" % (self.vid, self.pid, [self.path, repr(self.serial)][bool(self.serial)])
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
        serial = None
        if dev.iSerialNumber > 0:
            try:
                serial = dev.serial_number
            except usb.USBError:
                pass

        devobjs.append(LibDevice(vid=dev.idVendor, pid=dev.idProduct, serial=serial, path=Path(bus=dev.bus, address=dev.address)))
    return devobjs

def find_usb_devices_lsusb():
    import re
    import subprocess

    # 'Bus 002 Device 002: ID 8087:0024 Intel Corp. Integrated Rate Matching Hub'
    lsusb_device_regex = re.compile(
        "Bus (?P<bus>[0-9]+) Device (?P<address>[0-9a-f]+):"
        " ID (?P<vid>[0-9a-f]+):(?P<pid>[0-9a-f]+)")
    # ' iSerial                 0 '
    # ' iSerial                 3 04c321e2df0e8bb2'
    # ' iSerial                 1 0000:00:1a.0'
    lsusb_serial_regex = re.compile(
        r"^ *iSerial\s*[0-9]+ *(?P<serial>[^ ]+)?$",
        re.MULTILINE)

    class LsusbDevice(Device):
        def __new__(cls, *args, **kw):
            return Device.__new__(cls, *args, serial=None, **kw)

        @property
        def serial(self):
            # Get the serial number from the device and cache it.
            if not hasattr(self, "_serial"):
                output = subprocess.check_output('lsusb -D %s' % (self.path,), shell=True, stderr=subprocess.STDOUT)
                bits = lsusb_serial_regex.search(output)
                assert bits, "%s %r\n%s" % (self.path, output, output)
                self._serial = bits.group("serial")
            return self._serial

        @property
        def syspaths(self):
            if not hasattr(self, "_syspaths"):
                self._syspaths = find_sys(self.path)
            return self._syspaths

        def inuse(self):
            return bool(self.drivers())

        def drivers(self):
            syspaths = os.path.join(self.syspaths)
            drivers = {}
            for path in syspaths[1:]:
                driver_path = os.path.join(path, "driver")
                if os.path.exists(driver_path):
                    drivers[path] = os.readlink(driver_path)
            return tuple(set(d.split('/')[-1] for d in drivers.values()))

        def detach(self):
            # echo -n %k:1.0 >/sys/bus/usb/drivers/cdc_acm/unbind
            pass

    devobjs = []
    output = subprocess.check_output('lsusb')
    for line in output.splitlines():
        bits = lsusb_device_regex.match(line)
        assert bits, repr(line)

        vid = int(bits.group('vid'), base=16)
        pid = int(bits.group('pid'), base=16)
        bus = int(bits.group('bus'), base=16)
        address = int(bits.group('address'), base=16)
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


def find_sys(path, mapping={}):
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
        assert libobj.serial == lsobj.serial, "%r == %r" % (libobj.serial, lsobj.serial)
        assert libobj.path == lsobj.path, "%r == %r" % (libobj.path, lsobj.path)

        lsobj_inuse = lsobj.inuse()
        libobj_inuse = libobj.inuse()
        if libobj_inuse is not None:
            assert libobj_inuse == lsobj_inuse, "%r == %r" % (libobj_inuse, lsobj_inuse)


test_libusb_and_lsusb_equal()


import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--no-modify', help="Don't modify the state of the system in any way.")

parser.add_argument('--mac', help='Find board with the given MAC address.')
parser.add_argument('--dna', help='Find board with the given Device DNA.')
parser.add_argument('--position', help="""Find board using a given position.
Example:
 1-2.3 - Bus 1, Port 2 (which is a hub), Port 3
 5-6.7.8 - Bus 5, Port 2 (which is a hub), Port 7 (which is a hub), Port 8 (which is a hub)
""")

parser.add_argument('--get-usbfs', help='Return the /dev/bus/usb path for a device.')
parser.add_argument('--get-sysfs', help='Return the /sys/bus/usb/devices path for a device.')
parser.add_argument('--get-video', help='Get the primary video device path.')
STATES = ['unconfigured', 'jtag', 'operational']
parser.add_argument('--get-state', help='Return the state the device is in. Possible states are: %r' % STATES)

parser.add_argument('--load-firmware', help='Load the firmware file onto the device.')

"""
# Digilent Atlys board with stock "Adept" firmware
# VID=

  - Digilent Atlys board loaded with Nero-USB JTAG firmware
  - Digilent Atlys board loaded with MakeStuff firmware
  - Digilent Atlys board loaded with HDMI2USB "unconfigured" firmware
  - Digilent Atlys board loaded with HDMI2USB "configured" firmware

  - Unconfigured Cypress FX2, could be a Numato Opsis

  - Numato Opsis board with no FX2 firmware loaded
  - Numato Opsis board loaded with Nero-USB JTAG firmware
  - Numato Opsis board loaded with MakeStuff firmware
  - Numato Opsis board loaded with HDMI2USB firmware

"""








