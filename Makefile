
# conda
CONDA_PACKAGES = openocd
PYTHON_PACKAGES = pyusb pycodestyle autopep8 setuptools-pep8
include conda.mk

# pypi upload
test-upload:
	python3 setup.py register -r pypitest
	python3 setup.py sdist upload -r pypitest

upload:
	python3 setup.py register -r pypi
	python3 setup.py sdist upload -r pypi

.PHONY: test-upload upload

# Unbind helper - needs to be setuid
bin/unbind-helper:
	@echo "Making setuid unbind helper program."
	gcc -Wall -std=c99 unbind-helper.c -o $@
	sudo chmod 755 $@
	sudo chown root:root $@
	sudo chmod u+s $@
	ls -l $@

unbind-helper:
	@make check-unbind-helper || make bin/unbind-helper

check-unbind-helper:
	@[ -e bin/unbind-helper ]
	@[ "$$(stat -c "%a %U" bin/unbind-helper)" = "4755 root" ]

clean-unbind-helper:
	if [ -e bin/unbind-helper ]; then sudo rm bin/unbind-helper; fi

.PHONY: unbind-helper check-unbind-helper clean-unbind-helper

# Useful python targets
version:
	python3 setup.py version

check:
	pycodestyle hdmi2usb --ignore=E402 --ignore=W503
	pycodestyle *.py

fix:
	autopep8 -v -r -i -a -a hdmi2usb

test:
	python3 -m "hdmi2usb.modeswitch.tests"
	python3 hdmi2usb/modeswitch/files.py hdmi2usb/firmware/spartan6/atlys/bscan_spi_xc6slx45.bit
	python3 setup.py test

root-test:
	sudo make test

# ???
read-dna:
	./hdmi2usb-mode-switch.py --verbose --mode=jtag
	which openocd
	openocd --file board/numato_opsis.cfg -c "init; xc6s_print_dna xc6s.tap; exit"

update-usb-ids:
	rm USB-IDs.md
	wget https://raw.githubusercontent.com/wiki/timvideos/HDMI2USB/USB-IDs.md -O USB-IDs.md
	git add USB-IDs.md
	git commit -m "Updating the USB-IDs.md file"

# Global rules
clean:
	make clean-conda
	make clean-unbind-helper
	git clean -d -x -f

install-deps:
	apt-get install posh

setup:
	if ! make check-conda; then \
		make -s conda; \
	fi
	if ! make check-unbind-helper; then \
		make -s unbind-helper; \
	fi
	@make --quiet config

config:
	@echo ""
	@echo "Set your path with;"
	@echo " export PATH=$(PWD)/bin:$(PWD)/conda/bin:\$$PATH"
	@echo ""

all:
	@echo "Checking setup...."
	@make --quiet setup
	@echo
	@echo "Running code checks...."
	@make --quiet check
	@echo
	@echo "Running tests...."
	@make --quiet test
	@echo
	@echo "Printing version info...."
	@make --quiet version
	@echo
	@make --quiet config

.PHONY: bin/unbind-helper
.DEFAULT_GOAL := all
