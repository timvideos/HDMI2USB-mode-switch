
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

bin/unbind-helper:
	echo "Making setuid unbind helper program."
	gcc -std=c11 unbind-helper.c -o $@
	sudo chmod 755 $@
	sudo chown root:root $@
	sudo chmod u+s $@
	ls -l $@

test:
	echo $$PATH
	python hdmi2usb_test.py

root-test:
	sudo make test

clean:
	sudo rm bin/unbind-helper

all: bin/unbind-helper
