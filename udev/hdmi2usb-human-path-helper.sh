#!/bin/sh

if [ x"$1" = xtest ]; then
	if [ x"$SHELL" = x ]; then
		SHELL=/bin/sh
	fi
	# DEVPATH=/devices/pci0000:00/0000:00:1c.7/0000:08:00.0/usb3/3-4/3-4.3/3-4.3:1.2/tty/ttyACM0
	# ID_PATH=pci-0000:08:00.0-usb-0:4.3:1.2
	# ID_PATH_HUMAN=usb.bus0.port4-hub.port3
	$SHELL $0 /devices/pci0000:00/0000:00:1c.7/0000:08:00.0/usb3/3-4/3-4.3/3-4.3:1.2/tty/ttyACM0

	# DEVPATH=/devices/pci0000:00/0000:00:1c.7/0000:08:00.0/usb3/3-3/3-3:1.2/tty/ttyACM0
	# ID_PATH=pci-0000:08:00.0-usb-0:3:1.2
	# ID_PATH_HUMAN=usb.bus0.port3
	$SHELL $0 /devices/pci0000:00/0000:00:1c.7/0000:08:00.0/usb3/3-3/3-3:1.2/tty/ttyACM0

	# DEVPATH=/devices/pci0000:00/0000:00:1c.7/0000:08:00.0/usb3/3-4/3-4.4
	$SHELL $0 /devices/pci0000:00/0000:00:1c.7/0000:08:00.0/usb3/3-4/3-4.4

	exit
fi

/bin/echo $@ | /bin/sed \
	-e's~^.*/usb.*/\([^/:]*:[^/:]*\)/.*$~\1~' \
	-e's~^.*/usb.*/\([^/]\+\)$~\1~' \
	-e's/:[0-9.]\+$//' \
	-e's/^\([0-9]\+\)-\([0-9]\+\)/ID_PATH_HUMAN=usb.bus\1.port\2/' \
	-e's/\.\([0-9]\+\)/-hub.port\1/g'
