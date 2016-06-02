#!/usr/bin/env python3
# vim: set ts=4 sw=4 et sts=4 ai:

"""
Tests which show the libusb and lsusb implementations work the same way.
"""

import hdmi2usb_libusb
import hdmi2usb_lsusb

def test_libusb_and_lsusb_equal():
    libusb_devices = hdmi2usb_libusb.find_usb_devices()
    lsusb_devices = hdmi2usb_lsusb.find_usb_devices()
    for libobj, lsobj in zip(sorted(libusb_devices), sorted(lsusb_devices)):
        print "%s -- lib: %-40s ls: %-40s -- %-40s  drivers: %s" % (libobj.path, libobj, lsobj, find_sys(libobj.path)[0], lsobj.drivers())
        assert libobj.vid == lsobj.vid, "%r == %r" % (libobj.vid, lsobj.vid)
        assert libobj.pid == lsobj.pid, "%r == %r" % (libobj.pid, lsobj.pid)
        if libobj.serial:
            assert libobj.serial == lsobj.serial, "%r == %r" % (libobj.serial, lsobj.serial)
        assert libobj.path == lsobj.path, "%r == %r" % (libobj.path, lsobj.path)

        lsobj_inuse = lsobj.inuse()
        libobj_inuse = libobj.inuse()
        if libobj_inuse is not None:
            assert libobj_inuse == lsobj_inuse, "%r == %r" % (libobj_inuse, lsobj_inuse)
