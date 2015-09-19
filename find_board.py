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

Device = namedtuple('Device', ['path', 'vid', 'pid', 'serial'])
Device.__str__ = lambda self: "Device(%04x:%04x %r)" % (self.vid, self.pid, self.serial)
#Device.__cmp__ = lambda a, b: cmp(a.path, b.path)

def find_usb_devices_libusb():
    import usb
    if usb.__file__.endswith('.so'):
        logging.warning("Your python usb module is old.")
    import usb.util

    busses = usb.busses()

    devobjs = []
    for dev in usb.core.find(find_all=True):
        path = '/dev/bus/usb/%03i/%03i' % (dev.bus, dev.address)
        assert os.path.exists(path), path

        serial = None
        if dev.iSerialNumber > 0:
            try:
                serial = dev.serial_number
            except usb.USBError:
                pass

        devobjs.append(Device(vid=dev.idVendor, pid=dev.idProduct, serial=serial, path=path))
    return devobjs

def find_usb_devices_lsusb():
    import re
    import subprocess

    # 'Bus 002 Device 002: ID 8087:0024 Intel Corp. Integrated Rate Matching Hub'
    lsusb_device_regex = re.compile(
        "Bus (?P<bus>[0-9]+) Device (?P<device>[0-9a-f]+):"
        " ID (?P<vid>[0-9a-f]+):(?P<pid>[0-9a-f]+)")
    # ' iSerial                 0 '
    # ' iSerial                 3 04c321e2df0e8bb2'
    lsusb_serial_regex = re.compile(
        r"^ *iSerial\s*[0-9]+ *(?P<serial>[0-9a-f]+)?$",
        re.MULTILINE) 

    class LsusbDevice(Device):
        @property
        def serial(self):
            # Get the serial number from the device and cache it.
            if not hasattr(self, "_serial"):
                output = subprocess.check_output('lsusb -D %s' % self.path, shell=True, stderr=subprocess.STDOUT)
                bits = lsusb_serial_regex.search(output)
                assert bits, repr(output)
                self._serial = bits.group("serial")
            return self._serial

    devobjs = []
    output = subprocess.check_output('lsusb')
    for line in output.splitlines():
        bits = lsusb_device_regex.match(line)
        assert bits, repr(line)
        path = "/dev/bus/usb/%s/%s" % (bits.group('bus'), bits.group('device'))
        assert os.path.exists(path), path
        vid = int(bits.group('vid'), base=16)
        pid = int(bits.group('pid'), base=16)
        devobjs.append(LsusbDevice(vid=vid, pid=pid, serial=None, path=path))

    return devobjs


libusb_devices = find_usb_devices_libusb()
lsusb_devices = find_usb_devices_lsusb()

for libobj, lsobj in zip(sorted(libusb_devices), sorted(lsusb_devices)):
    print "%s -- lib: %-40s ls: %-40s" % (libobj.path, libobj, lsobj)
    assert libobj.vid == lsobj.vid, "%r == %r" % (libobj.vid, lsobj.vid)
    assert libobj.pid == lsobj.pid, "%r == %r" % (libobj.pid, lsobj.pid)
    #assert libobj.did == lsobj.did, "%r == %r" % (libobj.did, lsobj.did)
    assert libobj.serial == lsobj.serial, "%r == %r" % (libobj.serial, lsobj.serial)
    assert libobj.path == lsobj.path, "%r == %r" % (libobj.path, lsobj.path)

        

