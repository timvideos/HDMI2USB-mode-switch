# USB ID table

 * This page is published at https://github.com/timvideos/HDMI2USB/wiki/USB-IDs
 * [More information about the Opsis USB IDs can be found in the developer documentation](https://github.com/timvideos/HDMI2USB/wiki/USB-IDs/_edit).

### Primary USB IDs

| Board |    Mode        | Vendor ID | Product ID |
| -----:| --------------:|:---------:|:----------:|
| Opsis | Unconfigured   | 0x2A19    | 0x5440     |
| Opsis | Programming    | 0x2A19    | 0x5441     |
| Opsis | Operational    | 0x2A19    | 0x5442     |
| Atlys | Digilent Adept*| 0x1443    | 0x0007     |
| Atlys | Unconfigured   | 0x1D50    | 0x60b5     |
| Atlys | Programming    | 0x1D50    | 0x60b6     |
| Atlys | Operational    | 0x1D50    | 0x60b7     |

 *: Atlys running original shipping firmware enumerates as this.

For the Opsis, we use Numato Lab's USB ID (they are  the device's manufacture).
For the Atlys, the [Openmoko project](http://wiki.openmoko.org/wiki/USB_Product_IDs#Assigned.2FAllocated_Openmoko_USB_Product_IDs) has provided IDs.

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