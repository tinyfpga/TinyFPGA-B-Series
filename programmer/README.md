# Programmer

## Directory Structure

The programmer Python code is organized in a Python package.  The actual code for the programmer is located in the `tinyfpgab` directory in the `__init__.py` and `__main__.py` files.  The `setup.py` script is specific to the Python packaging system and should be be executed directly.  If you want to learn more about Python packaging take a look at the [Python packaging documentation](http://python-packaging.readthedocs.io/en/latest/minimal.html).  If you just want to run the programmer on the command-line, the best way is to install it using pip: `pip install tinyfpgab`.  The programmer script will then be added to your `PATH` variable as `tinyfpgab`.

## GUI

The GUI has been moved to the [TinyFPGA Programmer Application repo][gui-repo].
However, the `tinyfpgab` module can be used on its own with a command-line
interface:

[gui-repo]: https://github.com/tinyfpga/TinyFPGA-Programmer-Application


## CLI Installation

Install the commandline tool via Python's pip tool:
```
> pip install tinyfpgab
```

## CLI Usage
```
> tinyfpgab --help
usage: tinyfpgab [-h] [-l] [-p PROGRAM] [-b] [-c COM] [-d DEVICE] [-a ADDR]

optional arguments:
  -h, --help            show this help message and exit
  -l, --list            list connected and active TinyFPGA B-series boards
  -p PROGRAM, --program PROGRAM
                        program TinyFPGA board with the given bitstream
  -b, --boot            command the TinyFPGA B-series board to exit the
                        bootloader and load the user configuration
  -c COM, --com COM     serial port name
  -d DEVICE, --device DEVICE
                        device id (vendor:product); default is TinyFPGA-B
                        (1209:2100)
  -a ADDR, --addr ADDR  force the address to write the bitstream to
```

You can list valid ports with the `--list` option:

```
> tinyfpgab --list

    TinyFPGA B-series Programmer CLI
    --------------------------------
    Boards with active bootloaders:
        COM24

```

You can use the `--com` option to specify a specific port.  If you don't specify a port, it will use the first one in the list:

```
> tinyfpgab --program ..\icestorm_template\TinyFPGA_B.bin

    TinyFPGA B-series Programmer CLI
    --------------------------------
    Programming COM24 with ..\icestorm_template\TinyFPGA_B.bin
    Waking up SPI flash
    135100 bytes to program
    Erasing designated flash pages
    Writing bitstream
    Verifying bitstream
    Success!

```


## Testing

The tests can be run with [tox](https://tox.readthedocs.io/): just run the `tox` command.  If you don't have `tox` installed, read the tox documentation and install it first.

The code coverage will be generated as HTML pages in the `htmlcov` directory.
