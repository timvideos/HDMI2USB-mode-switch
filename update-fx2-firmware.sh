#!/bin/bash

if [ ! -d ixo-usb-jtag ]; then
	git clone git://github.com/mithro/ixo-usb-jtag.git
	cd ixo-usb-jtag
else
	cd ixo-usb-jtag
	git pull
fi

fakeroot ./debian/rules binary
cp ./output/hw_opsis.hex ../fx2-firmware/atlys/ixo-usb-jtag.hex
cp ./output/hw_opsis.hex ../fx2-firmware/opsis/ixo-usb-jtag.hex
cd ..

git add fx2-firmware/atlys/ixo-usb-jtag.hex
git add fx2-firmware/opsis/ixo-usb-jtag.hex
