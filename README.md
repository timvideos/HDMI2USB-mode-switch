# HDMI2USB-mode-switch

Helper tool to figuring out the state and information about HDMI2USB boards and
managing the firmware on them.

Run `make conda` to setup a conda environment with everything you need, good
for development and testing.

Run `python3 setup.py install` if you want to install on your system.

Make sure you install the udev rules [from this
repository](https://github.com/litex-hub/litex-buildenv-udev). Chances are you
want to put them in `/etc/udev/rules.d/` and run these commands to reload your
udev rules:

    $ sudo udevadm control --reload-rules
    $ sudo udevadm trigger

Before sending a pull request, make sure `make test` and `make check` pass.

There are three ways to run `hdmi2usb-mode-switch`:

 1. As root
 1. Install the
 [unbind-helper](https://github.com/timvideos/HDMI2USB-mode-switch/blob/master/unbind-helper.c)
 as a setuid binary
 1. Install the
 [udev-rules](https://github.com/litex-hub/litex-buildenv-udev)
 which sets the permissions of the unbind to the `video` group.
