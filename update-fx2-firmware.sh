#!/bin/bash

set +x
set +e

TOP=$PWD

cd build

#### ixo-usb-jtag for JTAG operation
(
	if [ ! -d ixo-usb-jtag ]; then
		git clone git://github.com/mithro/ixo-usb-jtag.git
		cd ixo-usb-jtag
	else
		cd ixo-usb-jtag
		git pull
	fi

	fakeroot ./debian/rules binary
	cp ./output/hw_opsis.hex $TOP/fx2-firmware/atlys/ixo-usb-jtag.hex
	cp ./output/hw_opsis.hex $TOP/fx2-firmware/opsis/ixo-usb-jtag.hex

	cd $TOP
	git add fx2-firmware/atlys/ixo-usb-jtag.hex
	git add fx2-firmware/opsis/ixo-usb-jtag.hex
)

#### fx2lib firmware for USB serial operation
(
	if [ ! -d fx2lib ]; then
		git clone git://github.com/mithro/fx2lib.git
		git checkout cdc-usb-serialno-from-eeprom
		cd fx2lib
	else
		cd fx2lib
		git pull
	fi

	make
	cp examples/cdc/to-uart/build/cdc-acm-to-uart.ihx $TOP/fx2-firmware/opsis/usb-uart.ihx
	cd $TOP
	git add fx2-firmware/opsis/usb-uart.ihx
)

