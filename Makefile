
bin/unbind-helper:
	echo "Making setuid unbind helper program."
	gcc -std=c11 unbind-helper.c -o $@
	sudo chmod 755 $@
	sudo chown root:root $@
	sudo chmod u+s $@
	ls -l $@

clean:
	sudo rm bin/unbind-helper

all: bin/unbind-helper
