#!/usr/bin/env python3
# vim: set ts=4 sw=4 et sts=4 ai:

from setuptools import find_packages
from setuptools import setup
import sys

import versioneer


if sys.version_info[:3] < (3, 3):
    raise SystemExit("You need Python 3.3+")


setup(
    name="hdmi2usb.modeswitch",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description=(
        "Module and command line tool for control the mode of HDMI2USB "
        "devices."
    ),
    long_description=open("README.md").read(),
    author="TimVideos' HDMI2USB project",
    author_email="hdmi2usb@googlegroups.com",
    url="https://hdmi2usb.tv",
    download_url="https://github.com/timvideos/HDMI2USB-mode-switch",
    license="Apache 2.0",
    platforms=["Any"],
    keywords="HDL ASIC FPGA hardware design",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",  # noqa
    ],
    packages=find_packages(),
# FIXME: Populate this with information?
#    package_data={},
#    data_files=[
#        ('/lib/firmware/hdmi2usb', os.walk('hdmi2usb/firmware/'),
#        ('/usr/bin/', build?(unbind-helper)),
#        ('/etc/udev/rules.d/', os.listdir(udev,
#            "*-hdmi2usb-*.rules", "hdmi2usb-*.sh"),
#    ],
    include_package_data=True,
    entry_points={
        "console_scripts": [x+"=hdmi2usb.modeswitch.cli:main" for x in (
            "hdmi2usb-find-board", "hdmi2usb-mode-switch",
            "hdmi2usb-manage-firmware",
            "opsis-find-board", "opsis-mode-switch", "opsis-manage-firmware",
            "atlys-find-board", "atlys-mode-switch", "atlys-manage-firmware",
        )],
    },
)
