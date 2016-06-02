
import array
import usb.core
import usb.util


VC_EEPROM=0xB1
READ_EEPROM=0xC0
WRITE_EEPROM=0x40

def get_eeprom(dev, addr, amount):
    data = array.array('B')
    while len(data) < amount:
        transfer_size = min(64, amount-len(data))

        result = dev.ctrl_transfer(READ_EEPROM, VC_EEPROM, addr+len(data), 0, transfer_size)
        assert len(result) == transfer_size, "len(result) %i == %i" % (len(result), transfer_size)

        data += result

    return data

def set_eeprom(dev, addr, data):
    offset = 0
    while offset < len(data):
        transfer_size = min(32, len(data)-offset)
        result = dev.ctrl_transfer(WRITE_EEPROM, VC_EEPROM, addr+offset, 0, data[offset:offset+transfer_size])
        assert result == transfer_size, "result %i == %i" % (result, transfer_size)
        offset += transfer_size

def get_dev():
    # find our device
    dev = usb.core.find(idVendor=0x2A19, idProduct=0x5441)

    # was it found?
    if dev is None:
        raise ValueError('Device not found')

    dev.set_configuration()
    return dev


import argparse
import time

dev = get_dev()
current_eeprom_data = get_eeprom(dev, 0, 256)

old_eeprom_data = bytes(current_eeprom_data)
new_eeprom_data = bytes(current_eeprom_data)

print(repr(old_eeprom_data))
print(repr(new_eeprom_data))

if old_eeprom_data != new_eeprom_data:
    set_eeprom(dev, 0, new_eeprom_data)

s.check()
