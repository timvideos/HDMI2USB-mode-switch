#!/bin/bash
set -e
./hdmi2usb-mode-switch.py --mode=serial -v
./hdmi2usb-mode-switch.py --mode=jtag -v
./hdmi2usb-mode-switch.py --mode=serial -v
./hdmi2usb-mode-switch.py --mode=jtag -v
./hdmi2usb-mode-switch.py --flash-gateware=$1 --verbose
