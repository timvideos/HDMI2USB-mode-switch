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


_DeviceBase = namedtuple(
    'DeviceBase', ['path', 'vid', 'pid', 'did', 'serialno'])


class DeviceBase(_DeviceBase):

    def __repr__(self):
        if self.serialno:
            s = repr(self.serialno)
        else:
            s = self.path
        return "%s(%04x:%04x:%s %s)" % (
            self.__class__.__name__, self.vid, self.pid, self.did, s)
