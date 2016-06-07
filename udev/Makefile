
# udev rules
install:
	@for RULE in *.rules; do \
		echo "Installing $$RULE to /etc/udev/rules.d/$$RULE"; \
		sudo cp $$RULE /etc/udev/rules.d/$$RULE; \
		sudo chmod 644 /etc/udev/rules.d/$$RULE; \
		sudo chown root:root /etc/udev/rules.d/$$RULE; \
	done
	sudo udevadm control --reload-rules

check:
	@for RULE in *.rules; do \
		echo -n "Checking $$RULE.."; \
		[ -e /etc/udev/rules.d/$$RULE ] || exit 1; \
		diff -u $$RULE /etc/udev/rules.d/$$RULE || exit 1; \
		echo " Good!"; \
	done

uninstall:
	for RULE in *.rules; do \
		sudo rm -f /etc/udev/rules.d/$$RULE; \
	done
	sudo rm -f /etc/udev/rules.d/52-hdmi2usb.rules

.DEFAULT_GOAL := check
