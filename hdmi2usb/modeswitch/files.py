#!/usr/bin/env python3
# vim: set ts=4 sw=4 et sts=4 ai:

"""
Functions for examining different file types.
"""

import struct


def assert_eq(a, b):
    assert a == b, "%s (%r) != %s (%r)" % (a, a, b, b)


class XilinxBitFile(object):
    """
    This page describes the format
    http://www.fpga-faq.com/FAQ_Pages/0026_Tell_me_about_bit_files.htm

    Field 1
    2 bytes     length 0x0009           (big endian)
    9 bytes     0f f0 0f f0 0f f0 0f f0 00
    2 bytes     00 01

    Field 3
    1 byte      key 0x61                (The letter "a")
    2 bytes     length 0x000a           (value depends on file name length)
    10 bytes    string design name "xform.ncd" (including a trailing 0x00)

    Field 4
    1 byte      key 0x62                (The letter "b")
    2 bytes     length 0x000c           (value depends on part name length)
    12 bytes    string part name "v1000efg860" (including a trailing 0x00)

    Field 4
    1 byte      key 0x63                (The letter "c")
    2 bytes     length 0x000b
    11 bytes    string date "2001/08/10" (including a trailing 0x00)

    Field 5
    1 byte      key 0x64                (The letter "d")
    2 bytes     length 0x0009
    9 bytes     string time "06:55:04"  (including a trailing 0x00)

    Field 6
    1 byte      key 0x65                (The letter "e")
    4 bytes     length 0x000c9090       (value depends on device type,
                                         and maybe design details)
    """

    header = struct.Struct(
        ">"   # big endian
        "H"   # h1, beshort == 0x0009
        "9s"  # 0f f0 0f f0 0f f0 0f f0 00
        "2s"  # h4, null byte
    )

    sfmt = struct.Struct(">ch")

    @classmethod
    def unpack_key(cls, f):
        d = f.read(cls.sfmt.size)
        key, slen = cls.sfmt.unpack(d)
        s = f.read(slen - 1)
        null = f.read(1)
        assert_eq(null, '\x00')
        return key, s

    def __init__(self, filename):
        try:
            assert filename.endswith('.bit'), "Filename should end in .bit"
            f = open(filename, 'rb')

            # Read the header
            data = f.read(self.header.size)
            (h1, h2, h3) = self.header.unpack_from(data)
            assert_eq(h1, 0x0009)
            assert_eq(h2, b'\x0f\xf0\x0f\xf0\x0f\xf0\x0f\xf0\x00')
            assert_eq(h3, b'\x00\x01')

            self.ncdname = None
            self.part = None
            self.date = None

            while True:
                key, value = self.unpack_key(f)
                if key == 'a':
                    self.ncdname = value
                elif key == 'b':  # Part type
                    self.part = value
                elif key == 'c':  # Build date
                    self.date = value
                elif key == 'd':  # Build time
                    self.date += " " + value
                    break

            assert self.ncdname
            assert self.part
            assert self.date
        except AssertionError as e:
            raise TypeError(e)

    def __str__(self):
        return "{}(ncdname={!r}, part={!r}, date={!r})".format(
            self.__class__.__name__, self.ncdname, self.part, self.date)


class XilinxBinFile(object):
    HEADER = b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xaa\x99Uf0\xa1\x00\x07'  # noqa

    def __init__(self, filename):
        if not filename.endswith('.bin'):
            raise TypeError("Filename should end in .bin")

        hdr = open(filename, 'rb').read(len(self.HEADER))
        if hdr != self.HEADER:
            raise TypeError("File doesn't start with required header.")


if __name__ == "__main__":
    import sys
    print(XilinxBitFile(sys.argv[1]))
