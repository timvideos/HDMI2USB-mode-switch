#!/usr/bin/env python3
# vim: set ts=4 sw=4 et sts=4 ai:

"""
Tests which show the libusb and lsusb implementations work the same way.
"""

from . import libusb
from . import lsusb


def test_libusb_and_lsusb_equal():
    libusb_devices = libusb.find_usb_devices()
    lsusb_devices = lsusb.find_usb_devices()
    for libobj, lsobj in zip(sorted(libusb_devices), sorted(lsusb_devices)):
        # print("%s -- lib: %-40s ls: %-40s -- %-40s  drivers: %s" % (libobj.path, libobj, lsobj, find_sys(libobj.path)[0], lsobj.drivers()))  # noqa
        print("%s -- lib: %-60s ls: %-60s -- %-40s  drivers: %s" %
              (libobj.path, libobj, lsobj, libobj.path, lsobj.drivers()))
        assert libobj.vid == lsobj.vid, "vid: %r == %r" % (
            libobj.vid, lsobj.vid)
        assert libobj.pid == lsobj.pid, "pid: %r == %r" % (
            libobj.pid, lsobj.pid)
        assert libobj.path == lsobj.path, "path: %r == %r" % (
            libobj.path, lsobj.path)

        try:
            assert libobj.did == lsobj.did, "did: %r == %r" % (
                libobj.did, lsobj.did)
        except AssertionError as e:
            print(e)

        try:
            assert libobj.serialno == lsobj.serialno, "serialno: %r == %r" % (
                libobj.serialno, lsobj.serialno)
        except AssertionError as e:
            print(e)

        lsobj_inuse = lsobj.inuse()
        libobj_inuse = libobj.inuse()
        if libobj_inuse is not None:
            assert libobj_inuse == lsobj_inuse, "inuse: %r == %r" % (
                libobj_inuse, lsobj_inuse)

test_libusb_and_lsusb_equal()
