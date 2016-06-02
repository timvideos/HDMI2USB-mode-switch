
#define _GNU_SOURCE

#include <fcntl.h>
#include <limits.h>
#include <linux/limits.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>


#define ARRAY_SIZE(arr) (sizeof(arr) / sizeof((arr)[0]))

bool prefix(const char *pre, const char *str) {
	return strncmp(pre, str, strlen(pre)) == 0;
}

bool suffix(const char *suf, const char *str) {
	if (!str || !suf)
		return 0;
	size_t lenstr = strlen(str);
	size_t lensuf = strlen(suf);
	if (lensuf >  lenstr)
		return 0;
	return strncmp(str + lenstr - lensuf, suf, lensuf) == 0;
}

const char* paths[] = {
	"/sys/bus/usb/drivers/uvcvideo",
	"/sys/bus/usb/drivers/cdc_acm",
	"/sys/bus/usb/drivers/usbtest",
};

int main ( int argc, char **argv ) {
	int f = 0;
	size_t w = 0;

	if (argc != 3) {
		printf("Must give 2 arguments not %i\n", argc-1);
		return -1;
	}

	// Resolve the path fully
	char *ptr = canonicalize_file_name(argv[1]);
	if (!ptr) {
		printf("realpath failed on %s\n", argv[1]);
		return -1;
	}

	// Make sure we are unbinding from an approved driver
	bool found = false;
	for (size_t i = 0; i < ARRAY_SIZE(paths); i++) {
		if (prefix(paths[i], ptr)) {
			found = true;
			break;
		}
	}
	if (!found) {
		printf("%s should be under\n", ptr);
		for (size_t i = 0; i < ARRAY_SIZE(paths); i++) {
			printf("  %s\n", paths[i]);
		}
		return -1;
	}

	// Should be unbinding...
	if (!suffix("/unbind", ptr)) {
		printf("%s should end in /unbind\n", ptr);
		return -1;
	}

	// FIXME: Should check that the original user has permission to this
	// USB device.

	// Do the actual unbind
	f = open(ptr, O_WRONLY);
	w = write(f, argv[2], strlen(argv[2]));
	close(f);
	if (w != strlen(argv[2])) {
		printf("Write to %s failed\n", ptr);
		return -1;
	}
	return 0;
}
