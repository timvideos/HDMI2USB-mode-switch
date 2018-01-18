import csv
import json
import os
import sys
import time
import urllib


def ls_github(url):
    while True:
        data = json.loads(urllib.urlopen(url).read())
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

parser = argparse.ArgumentParser(description='Download prebuilt firmware')
parser.add_argument('--user', help='Github user to download from.', default="timvideos")
parser.add_argument('--version', help='Get a specific version.')
parser.add_argument('--platform', help='Get for a specific platform (board + expansion boards configuration).')
parser.add_argument('--board', help='Alias for --platform.', dest="platform")
parser.add_argument('--channel', help="Get latest version from in a specific channel.", default="unstable")
parser.add_argument('--latest', help="Get the latest version.", dest="channel", action="store_const", const="unstable")
parser.add_argument('--branch', help="Branch to download from.", default="master")
parser.add_argument('--target', help="Target to download from.", default="hdmi2usb")
parser.add_argument('--firmware', help="Firmware to download from.", default="firmware")
parser.add_argument('--arch', help="Soft-CPU architecture to download from.", default="lm32")


args = parser.parse_args()
assert args.platform
assert args.version or args.channel
assert args.target

details = {
        "owner": args.user,
        "repo": "HDMI2USB-firmware-prebuilt",
        "branch": args.branch,
}
archive_url = "http://api.github.com/repos/{owner}/{repo}/contents/archive/{branch}/".format(**details)
versions = ls_github(archive_url)
possible_versions = [Version(d['name']) for d in versions if d['type'] == 'dir']
possible_versions.sort()

version = parser.version
if not version:

    channel = args.channel
    if channel == "unstable":
        version = possible_versions[-1]
    else:
        data = urllib.urlopen("https://docs.google.com/spreadsheets/d/e/2PACX-1vTmqEM-XXPW4oHrJMD7QrCeKOiq1CPng9skQravspmEmaCt04Kz4lTlQLFTyQyJhcjqzCc--eO2f11x/pub?output=csv").read()

        version_names = {}
        for i in csv.reader(data.splitlines(), dialect='excel'):
            if not i:
                continue
            if i[0] != "GitHub":
                continue
            if len(i) != 6:
                print("Skipping row %s" % i)
                continue

            _, _, version_str, name, conf, _ = i
            version = Version(version_str)
            assert version in possible_versions
            assert name not in version_names, "{} is listed multiple times!".format(name)
            version_names[name] = version_str

        if channel not in version_names:
            print("Did not find {} in {}".format(channel, version_names))
            sys.exit(1)

        version = version_names[channel]

    print("Channel {} is at version {}".format(channel, version))
else:
    assert version in possible_versions, "{} is not found in {}".format(version, possible_versions)

version_url = "{}{:s}/".format(archive_url, version)
platforms = ls_github(version_url)
possible_platforms = [d['name'] for d in platforms if d['type'] == 'dir']
print("Found platforms: {}".format(", ".join(possible_platforms)))

if args.platform not in possible_platforms:
    print("Did not find platform {} at version {} (found {})".format(args.platform, version, ", ".join(possible_platforms)))
    sys.exit(1)

targets_url = "{}{:s}/".format(version_url, args.platform)
targets = ls_github(targets_url)
possible_targets = [d['name'] for d in targets if d['type'] == 'dir']
print("Found targets: {}".format(", ".join(possible_targets)))

if args.target not in possible_targets:
    print("Did not find target {} for platform {} at version {} (found {})".format(args.target, args.platform, version, ", ".join(possible_targets)))
    sys.exit(1)

archs_url = "{}{:s}/".format(targets_url, args.target)
archs = ls_github(archs_url)
possible_archs = [d['name'] for d in archs if d['type'] == 'dir']
print("Found archs: {}".format(", ".join(possible_archs)))

if args.arch not in possible_archs:
    print("Did not find arch {} for target {} for platform {} at version {} (found {})".format(args.arch, args.target, args.platform, version, ", ".join(possible_firmwares)))
    sys.exit(1)

firmwares_url = "{}{:s}/".format(archs_url, args.arch)
firmwares = ls_github(firmwares_url)
possible_firmwares = [d['name'] for d in firmwares if d['type'] == 'file' and d['name'].endswith('.bin')]
print("Found firmwares: {}".format(", ".join(possible_firmwares)))

filename = None
for f in possible_firmwares:
    if f.endswith("{}.bin".format(args.firmware)):
        filename = f
        break

if not filename:
    print("Did not find firmware {} for target {} for platform {} at version {} (found {})".format(args.firmware, args.target, args.platform, version, ", ".join(possible_firmwares)))
    sys.exit(1)

image_url = "https://github.com/{user}/HDMI2USB-firmware-prebuilt/raw/master/archive/{branch}/{version}/{platform}/{target}/{arch}/{filename}".format(
    user=args.user, branch=args.branch, version=version, platform=args.platform, target=args.target, arch=args.arch, filename=filename)
print("Image URL: {}".format(image_url))

parts = os.path.splitext(filename)
out_filename = ".".join(list(parts[:-1]) + [str(version), args.platform, args.target, args.arch, parts[-1][1:]])
print("Downloading to: {}".format(out_filename))
urllib.urlretrieve(image_url, out_filename)
print("Done!")