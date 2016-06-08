#!/usr/bin/env python3
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

import argparse

from collections import namedtuple

from . import boards


def args_parser(board, mode):
    """Create an parser for the arguments."""
    parser = argparse.ArgumentParser(description=__doc__)

    # , aliases=['--debug', '-d'])
    parser.add_argument(
        '--verbose',
        '-v',
        action='count',
        default=0,
        help='Output more information.')

    parser.add_argument(
        '--by-type',
        choices=boards.BOARD_TYPES,
        help='Find board with a given type.')

    parser.add_argument(
        '--by-mac',
        help='Find board with the given MAC address.')
    parser.add_argument(
        '--by-dna',
        help='Find board with the given Device DNA.')
    parser.add_argument(
        '--by-position',
        help="""\
Find board using a given position in the USB structure.

Example:
 1-2.3 - Bus 1, Port 2 (which is a hub), Port 3
 5-6.7.8 - Bus 5, Port 2 (which is a hub), Port 7 (which is a hub), Port 8 (which is a hub)

While this *should* be static across reboots, but sadly on some machines it isn't :(
""")  # noqa
    parser.add_argument(
        '--by-mode',
        help=argparse.SUPPRESS)  # help='Find board in a given mode.', )

    parser.add_argument(
        '--all',
        help="""\
Do operation on all boards, otherwise will error if multiple boards are found.
""")

    parser.add_argument(
        '--get-usbfs',
        action='store_true',
        help='Return the /dev/bus/usb path for a device.')
    parser.add_argument(
        '--get-sysfs',
        action='store_true',
        help='Return the /sys/bus/usb/devices path for a device.')
    parser.add_argument(
        '--get-state',
        action='store_true',
        help='Return the state the device is in. Possible states are: %r' %
        boards.BOARD_STATES)
    parser.add_argument(
        '--get-video-device',
        action='store_true',
        help='Get the primary video device path.')
    parser.add_argument(
        '--get-serial-device',
        action='store_true',
        help='Get the serial device path.')

    parser.add_argument(
        '--prefer-hardware-serial',
        help='Prefer the hardware serial port on the Atlys board.')

    parser.add_argument(
        '--mode',
        help='Switch mode to given state.',
        choices=boards.BOARD_STATES)
    # FPGA
    parser.add_argument(
        '--load-gateware',
        help='Load gateware onto the FPGA.')
    parser.add_argument(
        '--flash-gateware',
        help='Flash gateware onto the SPI flash which the FPGA boots from.')
    # Cypress FX2
    parser.add_argument(
        '--load-fx2-firmware',
        help='Load firmware file onto the Cypress FX2.')
    parser.add_argument(
        '--flash-fx2-eeprom',
        help='Flash the FX2 eeprom with data.')
    #
    parser.add_argument(
        '--load-lm32-firmware',
        help="""\
Load firmware file onto the lm32 Soft-Core running inside the FPGA.
""")

    parser.add_argument(
        '--timeout',
        help='How long to wait in seconds before giving up.',
        type=float)

    return parser


def find_boards(args):
    all_boards = boards.find_boards()

    # Filter out the boards we don't care about
    filtered_boards = []
    for board in all_boards:
        if args.verbose > 0:
            sys.stderr.write("%s in '%s' mode at %s\n" % (
                boards.BOARD_NAMES[board.type],
                board.state,
                board.dev.path,
            ))
            for sp in board.dev.syspaths:
                sys.stderr.write(" %s\n" % (sp,))

            if board.dev.inuse():
                sys.stderr.write(
                    " Board is currently used by drivers %s\n" %
                    (board.dev.drivers(),))

            if board.tty():
                sys.stderr.write(" Serial port at %s\n" %
                                 ", ".join(board.tty()))

        if args.by_type and args.by_type != board.type:
            if args.verbose > 0:
                sys.stderr.write(" Ignore as not type %s\n" % (args.by_type,))
            continue

        filtered_boards.append(board)

    return filtered_boards


def main():
    # Parse the command line name
    cmd = os.path.basename(sys.argv[0])
    if cmd.endswith('.py'):
        cmd = cmd.rsplit('.', 1)[0]

    board, mode = cmd.split('-', 1)
    boards.assert_in(board, boards.BOARD_TYPES + ['hdmi2usb'])
    POSSIBLE_MODES = ['find-board', 'mode-switch', 'manage-firmware']
    boards.assert_in(mode, POSSIBLE_MODES)

    args = args_parser(mode, board).parse_args()

    if board != "hdmi2usb":
        args.by_type = board
    if args.by_type:
        boards.assert_in(args.by_type, boards.BOARD_TYPES)

    found_boards = find_boards(args)
    if not args.all:
        assert len(found_boards) == 1, found_boards

    MYDIR = os.path.dirname(os.path.abspath(__file__))
    if args.verbose:
        sys.stderr.write("My root dir: %s\n" % MYDIR)

    if mode == 'mode-switch':
        assert len(found_boards) == 1
        for board in found_boards:
            if (args.load_gateware or args.flash_gateware) and not args.mode:
                args.mode = 'jtag'

            # Switch modes
            if args.mode:
                newmode = args.mode
                if newmode == "jtag":
                    # Works on all boards
                    pass

                elif newmode in ("serial", "eeprom"):
                    assert board.type == "opsis", (
                        "{} mode only valid on the opsis.".format(newmode))

                elif newmode == "operational":
                    raise NotImplemented("Not yet finished...")
                else:
                    raise NotImplemented("Unknown mode {}".format(newmode))

                if board.state != newmode:
                    if args.verbose:
                        sys.stderr.write("Going from %s to %s\n" %
                                         (board.state, newmode))

                    old_board = board
                    boards.load_fx2(old_board, mode=newmode,
                                    verbose=args.verbose)

                    starttime = time.time()
                    while True:
                        found_boards = find_boards(args)

                        found_board = None
                        for new_board in found_boards:
                            if new_board.type == old_board.type:
                                if new_board.state == old_board.state:
                                    continue
                                assert new_board.state == newmode
                                found_board = new_board
                                break
                        else:
                            time.sleep(1)

                        if found_board:
                            board = found_board
                            break

                        if (args.timeout and starttime -
                                time.time() > args.timeout):
                            raise SystemError("Timeout!")

                    if args.verbose:
                        sys.stderr.write("Board was %r\n" % (old_board,))
                        sys.stderr.write("Board now %r\n" % (board,))
                else:
                    if args.verbose:
                        sys.stderr.write(
                            "Board already in required mode (%s)\n" %
                            (board.state,))

            # Load firmware onto the fx2
            if args.load_fx2_firmware:
                boards.load_fx2(board, filename=args.load_fx2_firmware,
                                verbose=args.verbose)

            # Load gateware onto the FPGA
            elif args.load_gateware:
                boards.load_fpga(board, args.load_gateware,
                                 verbose=args.verbose)

            elif args.flash_gateware:
                boards.flash_fpga(board, args.flash_gateware,
                                  verbose=args.verbose)

            # Load firmware onto the lm32
            elif args.load_lm32_firmware:
                if board.type == "opsis":
                    assert board.state == "serial"
                assert board.tty
                print("flterm something....")
                raise NotImplemented("Not yet finished...")

        found_boards = find_boards(args)

    for board in found_boards:
        if not (args.get_usbfs or
                args.get_sysfs or
                args.get_video_device or
                args.get_serial_device):
            print("Found %s boards." % len(found_boards))
            break

        if args.get_usbfs:
            print(board.dev.path)

        if args.get_sysfs:
            print("\n".join(board.dev.syspaths))

        if args.get_state:
            print(board.state)

        if args.get_video_device:
            assert board.state == "operational"
            print("???")

        if args.get_serial_device:
            print(board.tty()[0])
