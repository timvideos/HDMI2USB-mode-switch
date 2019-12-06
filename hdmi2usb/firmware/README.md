## DFU bootloader firmware

HDMI2USB-mode-switch includes a precompiled DFU-capable bootloader.
It is automatically used when flashing the FX2 firmware to EEPROM.
The bootloader firmware is located in `hdmi2usb/firmware/boot-dfu.ihex`,
It is the boot-dfu firmware provided by
[libfx2](https://github.com/whitequark/libfx2), revision v0.8-0-g3adb4fc,
compiled with SDCC 3.9.0.

## HDMI2USB firmware

HDMI2USB firmware for the FX2 chip can be found
[here](https://github.com/timvideos/HDMI2USB-fx2-firmware).
Instructions for building firmware can be found in the README in that
repository. The top-level Makefile provides targets for loading firmware into
RAM (`make load-fx2`) or flash to EEPROM (`make flash-fx2`).

This can be also done manually with `hdmi2usb-mode-switch`.
To load IHEX file into RAM:

```
hdmi2usb-mode-switch --load-fx2-firmware path/to/hdmi2usb.ihex
```

To flash firmware in DFU format to EEPROM:

```
hdmi2usb-mode-switch --flash-fx2-eeprom path/to/hdmi2usb.dfu
```

To convert between IHEX and DFU format, the the `fx2tool` provided by [libfx2](https://github.com/whitequark/libfx2) can be used:

```
fx2tool dfu path/to/hdmi2usb.ihex hdmi2usb.dfu
```

