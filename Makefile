
# conda
export PATH := $(shell pwd)/conda/bin:$(PATH)
conda:
	wget -c https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
	chmod a+x Miniconda3-latest-Linux-x86_64.sh
	./Miniconda3-latest-Linux-x86_64.sh -p $@ -b
	conda config --set always_yes yes --set changeps1 no
	conda update -q conda
	conda config --add channels timvideos
	conda install openocd
	pip install pyusb
	pip install pep8
	pip install autopep8
	python setup.py develop

clean-conda:
	rm -rf Miniconda3-latest-Linux-x86_64.sh
	rm -rf conda

# Unbind helper - needs to be setuid
bin/unbind-helper:
	echo "Making setuid unbind helper program."
	gcc -std=c11 unbind-helper.c -o $@
	sudo chmod 755 $@
	sudo chown root:root $@
	sudo chmod u+s $@
	ls -l $@

unbind-helper:
	make bin/unbind-helper

clean-unbind-helper:
	sudo rm bin/unbind-helper

# udev rules
install-udev:
	sudo cp 52-hdmi2usb.rules /etc/udev/rules.d/
	sudo chmod 644 /etc/udev/rules.d/52-hdmi2usb.rules
	sudo chown root:root /etc/udev/rules.d/52-hdmi2usb.rules

uninstall-udev:
	sudo rm /etc/udev/rules.d/52-hdmi2usb.rules

# Useful python targets
version:
	python setup.py version

check:
	pep8 hdmi2usb --ignore=E402
	pep8 *.py

fix:
	autopep8 -v -r -i -a -a hdmi2usb

test:
	python setup.py test

root-test:
	sudo make test

# ???
read-dna:
	./hdmi2usb-mode-switch.py --verbose --mode=jtag
	which openocd
	openocd --file board/numato_opsis.cfg -c "init; xc6s_print_dna xc6s.tap; exit"

