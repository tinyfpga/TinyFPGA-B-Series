[<img src="https://travis-ci.org/tinyfpga/TinyFPGA-B-Series.svg?branch=master" />](https://travis-ci.org/tinyfpga/TinyFPGA-B-Series)

# TinyFPGA B2 Board
The TinyFPGA B2 board is a tiny FPGA board with a low cost per logic element and convenient USB bitstream programming capability.  It measures just 18mm x 36mm and is a perfect fit for breadboards.  

# TinyFPGA BX Repo has Moved
If you are looking for the TinyFPGA BX design files and examples, it is in a seperate repository: [TinyFPGA BX GitHub Repo](https://github.com/tinyfpga/TinyFPGA-BX).

## Features
The heart of the B-series boards is either a ICE40LP4K or ICE40LP8K FPGA from Lattice.  For full details on the ICE40 series of FPGAs you can read the [ICE40 Family Handbook](http://www.latticesemi.com/~/media/LatticeSemi/Documents/Handbooks/iCE40FamilyHandbook.pdf).

### FPGA Feature Summary
|                  | TinyFPGA B1 | TinyFPGA B2 |
|------------------|:-----------:|:-----------:|
| FPGA Chip        |  ICE40LP4K  |  ICE40LP8K  |
| Logic Cells      |    3,520    |    7,680    |
| Block RAM Bits   |   80 KBit   |   128 KBit  |
| Phase Lock Loops |      1      |      1      |
| User IO Pins     |     23      |     23      |

### Common Features
+ Small form-factor that is breadboard friendly; plenty of space on either side for connecting jumpers or components.
+ Built-in USB interface for programming new FPGA bitstreams and user data to flash.
+ [4MBit of SPI Flash](http://datasheet.octopart.com/AT25SF041-SSHD-B-Adesto-Technologies-datasheet-62342976.pdf)
  + Bootloader bitstream takes up about 1MBit, user design bitstream will take another 1MBit, the rest is free to use for other purposes.
+ 3.3v and 1.2v Regulators
  + [3.3v LDO regulator](http://datasheet.octopart.com/MIC5504-3.3YM5-TR-Micrel-datasheet-61114938.pdf) can supply up to 300ma of current.  This leaves some headroom for user peripherals.
  + [1.2v LDO regulator](http://datasheet.octopart.com/MIC5365-1.2YC5-TR-Microchip-datasheet-8324343.pdf) can supply up to 150ma of current.  More headroom for user peripherals.
+ [Ultra Low-Power 16MHz MEMs Oscillator](http://www.mouser.com/ds/2/268/20005625A-1022977.pdf)
  + Consumes 1.3ma power when active.  
  + 50ppm stability

## Building your own TinyFPGA B1 or B2 Boards
It is possible to build the TinyFPGA B-Series boards by hand in a home lab.  However, it uses tiny 0402 surface mount capacitors and resistors and the ICE40 FPGAs used are in a 81 ball BGA package with 0.4mm pitch between the balls.  It is a challenging undertaking and will most likely result in some bad assembled boards along with the good.  I have used the following with success to hand assemble the prototype boards:
+ Parts for the TinyFPGA [B1](https://octopart.com/bom-tool/v110mo4B) or [B2](https://octopart.com/bom-tool/D9LH87Em)
+ [Lead-Free Solder Paste](https://www.amazon.com/gp/product/B00HKK6XHC)
+ [Stainless Steel Solder Paste Squeegee](http://dirtypcbs.com/store/details/14/solder-paste-squeegee)
+ [TinyFPGA B-Series Solder Paste Stencil](https://www.oshstencils.com)
  + You'll need to generate the gerber files and upload the solder paste layer.  You will want the stainless steel stencil, I do not believe the polymide will work with the fine pitch BGA package.
+ [TinyFPGA B-Series PCBs](https://oshpark.com/shared_projects/jGc1k4QL)
  + These boards require tighter tolerances than OSH Park advertises.  However, I have gotten lucky with some boards from OSH Park for this project and they have worked well.
+ [Precision Tweezers](https://www.amazon.com/Precision-Anti-static-Marrywindix-Electronics-Jewelry-making/dp/B00DVIEJ14) for placing parts on the board
+ Some sort of magnifying tool for placing parts ([magnifying glasses](https://www.amazon.com/dp/B01H8808H6), [magnifying lamp](https://www.amazon.com/Brightech-LightView-SuperBright-Magnifier-Adjustable/dp/B00UW2IRJ2), microscope)
+ [Reflow Oven](http://www.whizoo.com/)
  + I was using an electric griddle to reflow the A-series boards and it worked well enough.  However I didn't bother trying that with the micro BGA package on the B-series boards and I got a reflow oven kit.  This particular kit is excellent.
+ [Lattice FPGA Programmer](https://www.ebay.com/sch/i.html?_productid=533163279) or [Arduino board](https://www.arduino.cc/)
  + You will need this to load the bootloader onto the SPI Flash.  Once the bootloader is installed you can use the Python-based programmer application to program the board over USB.
  + Look in the [`programmer_arduino`](programmer_arduino) folder to load the bootloader onto the SPI Flash using an Arduino.

## Buy TinyFPGA B1 or B2 Boards
If you don't want to go through the hassle of ordering parts, tools, and supplies and assembling the boards yourself you can order professionally assembled and tested boards from [Tindie](https://www.tindie.com/stores/tinyfpga/) or the [TinyFPGA Store](http://store.tinyfpga.com).  These boards are not hobbyist-made, they are fabricated and assembled in a professional PCB fab that manufactures and assembles many other consumer, industrial and military electronics.  They go through an automated testing and programming process to ensure the board is healthy and ready to program over USB.

## Project Directory Structure
### board
This contains a [KiCad](http://kicad-pcb.org/) project with the schematic and layout of the B-series boards.  The board is designed with 4/4mil track size/spacing and 0.2mm hole size.  BOM lists for B1 and B2 boards are available here as well.

### bootloader
FPGA boards with USB bitstream programming capability typically use an expensive USB interface chip to provide this functionality.  The TinyFPGA B-series implement the USB bitstream programming capability within the FPGA itself.  This directory contains the verilog code that implements this bootloader.  The code is organized as an [iCEcube2](http://www.latticesemi.com/iCEcube2) project.  The bootloader itself works in the same way an Arduino bootloader works.  It is the first design to boot on the FPGA, if it is connected to a USB host it waits for a new bitstream to be programmed to the SPI flash, then reboots the FPGA to load the user design from flash.  If the board is not connected to a USB host or if there is no programmer application running on the host then the bootloader will quickly timeout and load the user design.  The bootloader does not consume any FPGA resources while the user design is loaded.

### programmer
The bootloader uses a simple protocol over a generic USB serial interface.  This directory contains a Python module for interfacing with the bootloader as well as a friendly Python GUI application for selecting and programming bitstreams.

### template
This is a template iCEcube2 project for developing your own designs to program onto the board.  It takes care of pin and clock constraints.  Just edit the TinyFPGA_B.v file to add your designs module(s).

## Project Log
For more information on the development and production of the B-Series please read and follow the [TinyFPGA B-Series Project Page](https://hackaday.io/project/26848-tinyfpga-b-series) at hackaday.io.

## License
The TinyFPGA B-Series project is an open source project licensed under GPLv3.  Please see the included LICENSE file for details.  If you do wish to distribute boards derived from this open source hardware project then you must also release the source files for the boards under GPLv3.  You are free to do this, but please improve upon the original design and provide a tangible benefit for users of the board.
