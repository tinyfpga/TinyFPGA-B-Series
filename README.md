# TinyFPGA B-Series
The TinyFPGA B-Series boards are tiny FPGA boards with a low cost per logic element and convenient USB bitstream programming capability.  They measure just 18mm x 36mm and are a perfect fit for breadboards.  

## Directory Structure
### board
This contains a [KiCad](http://kicad-pcb.org/) project with the schematic and layout of the B-series boards.  The board is designed with 4/4mil track size/spacing and 0.2mm hole size.  BOM lists for B1 and B2 boards are available here as well.

### bootloader
FPGA boards with USB bitstream programming capability typically use an expensive USB interface chip to provide this functionality.  The TinyFPGA B-series implement the USB bitstream programming capability within the FPGA itself.  This directory contains the verilog code that implements this bootloader.  The code is organized as an [iCEcube2](http://www.latticesemi.com/iCEcube2) project.  The bootloader itself works in the same way an Arduino bootloader works.  It is the first design to boot on the FPGA, if it is connected to a USB host it waits for a new bitstream to be programmed to the SPI flash, then reboots the FPGA to load the user design from flash.  If the board is not connected to a USB host or if there is no programmer application running on the host then the bootloader will quickly timeout and load the user design.  The bootloader does not consume any FPGA resources while the user design is loaded.

### programmer
The bootloader uses a simple protocol over a generic USB serial interface.  This directory contains a Python module for interfacing with the bootloader as well as a friendly Python GUI application for selecting and programming bitstreams.

## License
The TinyFPGA B-Series project is an open source project licensed under GPLv3.  Please see the included LICENSE file for details.  If you do wish to distribute boards derived from this open source hardware project then you must also release the source files for the boards under GPLv3.  You are free to do this, but please improve upon the original design and provide a tangible benefit for users of the board.
