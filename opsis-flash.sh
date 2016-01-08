#!/bin/bash
set -e
./hdmi2usb-mode-switch.py --mode=jtag
./hdmi2usb-mode-switch.py --mode=serial
./hdmi2usb-mode-switch.py --flash-gateware=spiflash/opsis_hdmi2usb-hdmi2usbsoc-opsis.bin --verbose
