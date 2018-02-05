#!/usr/bin/env python

# FIXME: Make this work under Python 2 (maybe done)

import csv
import json
import os
import sys
import time
import urllib.request, urllib.parse, urllib.error


def ls_github(url):
    while True:
        data = json.loads(urllib.request.urlopen(url).read().decode())
        if "message" in data:
            print("Warning: {}".format(data["message"]))
            time.sleep(1)
            continue
        return data


from collections import namedtuple
_Version = namedtuple("Version", ("version", "commits", "hash"))


class Version(_Version):
    """
    >>> v = Version("v0.0.4-44-g0cd842f")
    >>> v
    Version(version='v0.0.4', commits=44, hash='0cd842f')
    >>> str(v)
    'v0.0.4-44-g0cd842f'
    """

    def __new__(cls, value):
        version, commits, githash = value.split('-')
        commits = int(commits)
        assert githash[0] == 'g'
        return _Version.__new__(cls, version, commits, githash[1:])

    def __str__(self):
        return "%s-%i-g%s" % self


import doctest
doctest.testmod()

import argparse


def parse_args():

    parser = argparse.ArgumentParser(description='Download prebuilt firmware')
    parser.add_argument(
        '--user', help='Github user to download from.', default="timvideos")
    parser.add_argument('--rev', help='Get a specific version.')
    parser.add_argument(
        '--platform',
        help=
        'Get for a specific platform (board + expansion boards configuration).'
    )
    parser.add_argument(
        '--board', help='Alias for --platform.', dest="platform")
    parser.add_argument(
        '--channel',
        help="Get latest version from in a specific channel ().",
        default="unstable")
    parser.add_argument('--tag', help='Alias for --channel.', dest="channel")
    parser.add_argument(
        '--latest',
        help="Get the latest version.",
        dest="channel",
        action="store_const",
        const="unstable")
    parser.add_argument(
        '--branch', help="Branch to download from.", default="master")
    parser.add_argument(
        '--target', help="Target to download from.", default="hdmi2usb")
    parser.add_argument(
        '--firmware', help="Firmware to download from.", default="firmware")
    parser.add_argument(
        '--arch',
        help="Soft-CPU architecture to download from.",
        default="lm32")

    args = parser.parse_args()
    assert args.platform
    assert args.rev or args.channel
    assert args.target

    return args


def get_url(args):

    details = {
        "owner": args.user,
        "repo": "HDMI2USB-firmware-prebuilt",
        "branch": args.branch,
    }
    archive_url = "https://api.github.com/repos/{owner}/{repo}/contents/archive/{branch}/".format(
        **details)

    return archive_url


def get_revs(archive_url):

    print("revs = ls_github(archive_url) {}".format(archive_url))
    revs = ls_github(archive_url)
    possible_revs = [Version(d['name']) for d in revs if d['type'] == 'dir']
    possible_revs.sort()

    return possible_revs


def get_rev(args, possible_revs):

    rev = args.rev
    if not rev:

        channel = args.channel
        if channel == "unstable":
            rev = possible_revs[-1]
        else:
            data = urllib.request.urlopen(
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vTmqEM-XXPW4oHrJMD7QrCeKOiq1CPng9skQravspmEmaCt04Kz4lTlQLFTyQyJhcjqzCc--eO2f11x/pub?output=csv"
            ).read()

            rev_names = {}
            for i in csv.reader(data.splitlines(), dialect='excel'):
                if not i:
                    continue
                if i[0] != "GitHub":
                    continue
                if len(i) != 6:
                    print("Skipping row %s" % i)
                    continue

                _, _, rev_str, name, conf, _ = i
                rev = Version(rev_str)
                assert rev in possible_revs
                assert name not in rev_names, "{} is listed multiple times!".format(
                    name)
                rev_names[name] = rev

            if channel not in rev_names:
                print("Did not find {} in {}".format(channel, rev_names))
                sys.exit(1)

            rev = rev_names[channel]

        print("Channel {} is at rev {}".format(channel, rev))
    else:
        rev = Version(rev)
        assert rev in possible_revs, "{} is not found in {}".format(
            rev, possible_revs)

    print("rev: {}".format(rev))

    return rev


def get_rev_url(archive_url, rev):

    rev_url = "{}{:s}/".format(archive_url, str(rev))

    return rev_url


def get_platforms(args, rev_url):

    platforms = ls_github(rev_url)
    possible_platforms = [d['name'] for d in platforms if d['type'] == 'dir']
    print("Found platforms: {}".format(", ".join(possible_platforms)))

    if args.platform not in possible_platforms:
        print("Did not find platform {} at rev {} (found {})".format(
            args.platform, rev, ", ".join(possible_platforms)))
        sys.exit(1)

    return possible_platforms


def get_targets_url(args, rev_url):

    targets_url = "{}{:s}/".format(rev_url, args.platform)

    return targets_url


def get_targets(args, rev, targets_url):

    targets = ls_github(targets_url)
    possible_targets = [d['name'] for d in targets if d['type'] == 'dir']
    print("Found targets: {}".format(", ".join(possible_targets)))

    if args.target not in possible_targets:
        print("Did not find target {} for platform {} at rev {} (found {})".
              format(args.target, args.platform, rev,
                     ", ".join(possible_targets)))
        sys.exit(1)

    return possible_targets


def get_archs_url(args, targets_url):

    archs_url = "{}{:s}/".format(targets_url, args.target)

    return archs_url


def get_archs(args, archs_url):

    archs = ls_github(archs_url)
    possible_archs = [d['name'] for d in archs if d['type'] == 'dir']
    print("Found archs: {}".format(", ".join(possible_archs)))

    if args.arch not in possible_archs:
        print(
            "Did not find arch {} for target {} for platform {} at rev {} (found {})".
            format(args.arch, args.target, args.platform, rev,
                   ", ".join(possible_archs)))
        sys.exit(1)

    return possible_archs


def get_firmwares_url(args, archs_url):

    firmwares_url = "{}{:s}/".format(archs_url, args.arch)

    return firmwares_url


def get_firmwares(args, firmwares_url):

    firmwares = ls_github(firmwares_url)
    possible_firmwares = [
        d['name'] for d in firmwares
        if d['type'] == 'file' and d['name'].endswith('.bin')
    ]
    print("Found firmwares: {}".format(", ".join(possible_firmwares)))

    return possible_firmwares


def get_filename(args, possible_firmwares):

    filename = None
    for f in possible_firmwares:
        if f.endswith("{}.bin".format(args.firmware)):
            filename = f
            break

    if not filename:
        print(
            "Did not find firmware {} for target {} for platform {} at rev {} (found {})".
            format(args.firmware, args.target, args.platform, rev,
                   ", ".join(possible_firmwares)))
        sys.exit(1)

    return filename


def get_image_url(args, rev, filename):

    image_url = "https://github.com/{user}/HDMI2USB-firmware-prebuilt/raw/master/archive/{branch}/{rev}/{platform}/{target}/{arch}/{filename}".format(
        user=args.user,
        branch=args.branch,
        rev=rev,
        platform=args.platform,
        target=args.target,
        arch=args.arch,
        filename=filename)
    print("Image URL: {}".format(image_url))

    return image_url


def download(args, rev, filename, image_url):

    parts = os.path.splitext(filename)
    out_filename = ".".join(
        list(parts[:-1]) +
        [str(rev), args.platform, args.target, args.arch, parts[-1][1:]])
    print("Downloading to: {}".format(out_filename))
    urllib.request.urlretrieve(image_url, out_filename)

    return True


def main():

    args = parse_args()

    archive_url = get_url(args)
    possible_revs = get_revs(archive_url)
    print(possible_revs)
    rev = get_rev(args, possible_revs)
    rev_url = get_rev_url(archive_url, rev)

    possible_platforms = get_platforms(args, rev_url)

    targets_url = get_targets_url(args, rev_url)
    possible_targets = get_targets(args, rev, targets_url)

    archs_url = get_archs_url(args, targets_url)
    possible_archs = get_archs(args, archs_url)

    firmwares_url = get_firmwares_url(args, archs_url)
    possible_firmwares = get_firmwares(args, firmwares_url)

    filename = get_filename(args, possible_firmwares)
    image_url = get_image_url(args, rev, filename)

    ret = download(args, rev, filename, image_url)

    print("Done!")

    return


if __name__ == "__main__":
    main()
