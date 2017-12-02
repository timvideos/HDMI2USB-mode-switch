#!/bin/bash

if [ "`whoami`" = "root" ]
then
    echo "Running the script as root is not permitted"
    exit 1
fi

CALLED=$_
[[ "${BASH_SOURCE[0]}" != "${0}" ]] && SOURCED=1 || SOURCED=0

SCRIPT_SRC=$(realpath ${BASH_SOURCE[0]})
SCRIPT_DIR=$(dirname $SCRIPT_SRC)
TOP_DIR=$(realpath $SCRIPT_DIR/..)

if [ $SOURCED = 1 ]; then
        echo "You must run this script, rather then try to source it."
        echo "$SCRIPT_SRC"
        return
fi

if [ -z "$PLATFORM" ]; then
        echo "You must set the platform you want to get firmware for."
	echo ""
	echo "PLATFORM=atlys TRACK=unstable ./download-firmware.sh"
        exit 1
fi

if command -v curl >/dev/null ; then
	:
else
	echo "Downloading needs the curl tool."
	echo
	echo "On Debian/Ubuntu try 'sudo apt-get install curl'."
	echo
	exit 1
fi
if command -v svn >/dev/null ; then
	:
else
	echo "Downloading needs the svn tool."
	echo
	echo "On Debian/Ubuntu try 'sudo apt-get install subversion'."
	echo
	exit 1
fi

: ${GITHUB_USER:=timvideos}
: ${GITHUB_REPO:=HDMI2USB-firmware-prebuilt}
: ${TRACK:=unstable}

set -e

echo ""
echo " Repository: $GITHUB_USER/$GITHUB_REPO"
echo "   Platform: $PLATFORM"
echo "      Track: $TRACK"
LINK_VALUE="$(curl -s https://raw.githubusercontent.com/$GITHUB_USER/$GITHUB_REPO/master/$PLATFORM/firmware/$TRACK | sed -e's-^../../--')"
GITHUB_URL="https://github.com/$GITHUB_USER/$GITHUB_REPO"

GITHUB_TRACK_URL="https://github.com/$GITHUB_USER/$GITHUB_REPO/tree/master/$LINK_VALUE"
GITSVN_TRACK_URL="$GITHUB_URL/trunk/$LINK_VALUE"

VERSION="$(echo $LINK_VALUE | sed -e's-^.*/\(v[^/]*\)/.*$-\1-')"
if [ -z "VERSION" ]; then
	echo "Failed to get track version, please check internet connection."
	exit 1
fi

TARGET_DIR="$PWD/firmware/$PLATFORM/$VERSION"
TRACK_DIR="$PWD/firmware/$PLATFORM/$TRACK"

echo ""
echo " Track $TRACK is at $VERSION"
echo ""
echo " Downloading"
echo "  from '$GITHUB_TRACK_URL'"
echo "    to '$TARGET_DIR'"
echo "---------------------------------------"
mkdir -p $TARGET_DIR
# archive/master/v0.0.3-696-g2f815c1/minispartan6/base/lm32
svn export --force $GITSVN_TRACK_URL $TARGET_DIR | grep -v "^Export"

SHA256SUM_FILE="sha256sum.txt"
(
	cd $TARGET_DIR
	echo ""
	echo "Checking sha256sum of downloaded files in '$TARGET_DIR'..."
	sha256sum -c $SHA256SUM_FILE
	echo ""
)

echo "Linking $TARGET_DIR to $TRACK_DIR"
ln -sf -T $TARGET_DIR/ $TRACK_DIR

echo "---------------------------------------"
echo ""
echo "New firmware for $PLATFORM in $TRACK_DIR"
echo ""
