# USB ID table

 * This page is published at https://github.com/timvideos/HDMI2USB/wiki/USB-IDs
 * [More information about the Opsis USB IDs can be found in the developer documentation](https://opsis.hdmi2usb.tv/getting-started/usb-ids.html).

### Primary USB IDs

| Board |    Mode        | Vendor ID | Product ID | Device ID  |
| -----:| --------------:|:---------:|:----------:|:----------:|
| Opsis | Unconfigured   | 0x2A19    | 0x5440     | FIXME      |
| Opsis | Upgrade        | 0x2A19    | 0x5441     | 0x01       |
| Opsis | Operational    | 0x2A19    | 0x5442     | FIXME      |
| Atlys | Digilent Adept*| 0x1443    | 0x0007     | FIXME      |
| Atlys | Unconfigured   | 0x1D50    | 0x60b5     | 0x01       |
| Atlys | Upgrade        | 0x1D50    | 0x60b6     | 0x01       |
| Atlys | Operational    | 0x1D50    | 0x60b6     | 0x01       |

 *: Atlys running original shipping firmware enumerates as this.

For the Opsis, we use Numato Lab's USB ID (they are  the device's manufacture).
For the Atlys, the [Openmoko project](http://wiki.openmoko.org/wiki/USB_Product_IDs#Assigned.2FAllocated_Openmoko_USB_Product_IDs) has provided IDs.

### Developer IDs

Developer modes reuse a different DeviceID on the "Upgrade" PID+VID

| Board |    Mode        | Vendor ID | Product ID | Device ID  |
| -----:| --------------:|:---------:|:----------:|:----------:|
| Opsis | Test JTAG      | 0x2A19    | 0x5441     | 0x10       |
| Opsis | Test Serial    | 0x2A19    | 0x5441     | 0x11       |
| Opsis | Test Audio     | 0x2A19    | 0x5441     | 0x12       |
| Opsis | Test UVC       | 0x2A19    | 0x5441     | 0x13       |
| Atlys | Test JTAG      | 0x1D50    | 0x60b7     | 0x10       |
| Atlys | Test Serial    | 0x1D50    | 0x60b7     | 0x11       |
| Atlys | Test Audio     | 0x1D50    | 0x60b7     | 0x12       |
| Atlys | Test UVC       | 0x1D50    | 0x60b7     | 0x13       |
| MiniBoard | Unconfigured * | ??        | ???     | ???        |
| MiniBoard | Test Serial    | 0x1D50    | ???     | 0x11       |
| MiniBoard | Test Audio     | 0x1D50    | ???     | 0x12       |
| MiniBoard | Test UVC       | 0x1D50    | ???     | 0x13       |

### Other USB IDs

| Description                                   | Vendor ID | Product ID | Board |
| ---------------------------------------------:|:---------:|:----------:|:------|
|                 Cypress FX2 Unconfigured Boot | 0x04b4    | 0x8631     | any   |
|                     fx2lib CDC-Serial Example | 0x04b4    | 0x1004     | any   |
|                                  ixo-usb-jtag | 0x16C0    | 0x06AD     | any   |
|         *Reserved for Customer Designs (FX2)* | 0x2A19    | 0x5443     | Opsis |
|         *Reserved for Customer Designs (OTG)* | 0x2A19    | 0x5444     | Opsis |
|            Low Speed I/O TOFE Expansion board | 0x2A19    | 0x5445     | Opsis |
|              USB UART port on the Atlys board | 0x04e2    | ??????     | Atlys |


## Vendor IDs

| Vendor ID | Vendor Name                       | Description |
| --------- | --------------------------------- | ------------------------- |
|  0x04b4   | Cypress Semiconductor Corp.       | Makers of the Cypress FX2 chip used on the Opsis & Atlys board. |
|  0x04e2   | Exar                              | Creators of a crappy USB UART IC used on the Atlys board. |
|  0x1443   | Digilent                          | Manufacturers of the Atlys board. |
|  0x16C0   | Van Ooijen Technische Informatica | Original developers of ixo-usb-jtag. |
|  0x1D50   | OpenMoko, Inc.                    | Originally made phones but now have [donated their ID to open source projects](http://wiki.openmoko.org/wiki/USB_Product_IDs). |
|  0x2A19   | Numato Lab                        | Manufacturers of the Opsis board. |

-------

### Currently Unused USB Ids

| Vendor ID | Product ID | Current Description |
|:---------:|:----------:|:------|
|  0x1d50   | 0x60b8     | TimVideos' HDMI2USB (Soft+UTMI) - Unconfigured device        |
|  0x1d50   | 0x60b9     | TimVideos' HDMI2USB (Soft+UTMI) - Firmware upgrade           |
|  0x1d50   | 0x60ba     | TimVideos' HDMI2USB (Soft+UTMI) - HDMI/DVI Capture Device    |
|  0x1d50   | 0x60df     | Numato Opsis HDMI2USB board - unconfigured                   |
|  0x1d50   | 0x60e0     | Numato Opsis HDMI2USB board - JTAG Programming Mode          |
|  0x1d50   | 0x60e1     | Numato Opsis HDMI2USB board - User Mode                      |
