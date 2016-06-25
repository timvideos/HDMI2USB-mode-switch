#!/bin/bash
set -e
hdmi2usb-mode-switch --mode=serial -v
hdmi2usb-mode-switch --mode=jtag -v
hdmi2usb-mode-switch --mode=serial -v
hdmi2usb-mode-switch --mode=jtag -v
hdmi2usb-mode-switch --flash-gateware=$1 --verbose
