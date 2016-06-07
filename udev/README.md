These udev rules do the following things;

 * Grant anyone on the system permission to access the HDMI2USB boards.
 * Make modem-manager ignore the serial ports.

The `MODE:="666"` part will grant the permissions.

The `ENV{ID_MM_DEVICE_IGNORE}="1"` part will make modem-manager ignore the
device.

 * `54-hdmi2usb-atlys.rules` - Rules for the Digilent Atlys board.
 * `54-hdmi2usb-cypress.rules` - Rules for an unconfigured Cypress FX2 (such as
   a Numato Opsis/Digilent Atlys in fail-safe mode).
 * `54-hdmi2usb-opsis.rules` - Rules for the Numato Opsis board.
 * `54-hdmi2usb-ixo-usb-jtag.rules` - Rules for the boards when loaded with
   ixo-usb-jtag.

# Examining udev data

```
udevadm info --attribute-walk --name=/dev/ttyACM0
udevadm test /sys/class/tty/ttyACM0 2>&1 | less
udevadm test /sys/class/video4linux/video0 2>&1 | less
```

Oracle has a bunch of helpful info at https://docs.oracle.com/cd/E37670_01/E41138/html/ch07s03.html 
