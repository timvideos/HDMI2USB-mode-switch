#!/usr/bin/env python3
# vim: set ts=4 sw=4 et sts=4 ai:

"""
Functions needed by hdmi2usb-mode-switch implemented using libusb.

This should be portable to Mac, Windows and Linux.
"""

import logging
import usb
if usb.__file__.endswith('.so'):
    logging.warning("Your python usb module is old.")
import usb.util

from hdmi2usb_common import *


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


Device = LibDevice


def find_usb_devices():
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
