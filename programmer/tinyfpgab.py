#!/usr/bin/env python2

import struct
import time


def h(a):
    return ' '.join("%02X" % i for i in a)


class TinyFPGAB(object):
    def __init__(self, ser, progress=None):
        self.ser = ser
        self.spinner = 0
        if progress is None:
            self.progress = lambda x: x
        else:
            self.progress = progress

    def is_bootloader_active(self):
        for i in range(3):
            self.wake()
            self.read(0, 16)
            self.wake()
            devid = self.read_id()
            expected_devid = '\x1f\x84\x01'
            if devid == expected_devid:
                return True
            time.sleep(0.05)
        return False

    def cmd(self, opcode, addr=None, data='', read_len=0):
        assert isinstance(data, str)
        cmd_read_len = read_len + 1 if read_len else 0
        addr = '' if addr is None else struct.pack('>I', addr)[1:]
        write_string = chr(opcode) + addr + data
        cmd_write_string = '\x01{}{}'.format(
            struct.pack('<HH', len(write_string), cmd_read_len),
            write_string,
        )
        self.ser.write(cmd_write_string)
        self.ser.flush()
        return self.ser.read(read_len)

    def sleep(self):
        self.cmd(0xb9)

    def wake(self):
        self.cmd(0xab)

    def read_id(self):
        return self.cmd(0x9f, read_len=3)

    def read_sts(self):
        return self.cmd(0x05, read_len=1)

    def read(self, addr, length):
        data = ''
        while length > 0:
            read_length = min(16, length)
            data += self.cmd(0x0b, addr, '\x00', read_len=read_length)
            self.progress(read_length)
            addr += read_length
            length -= read_length
        return data

    def write_enable(self):
        self.cmd(0x06)

    def write_disable(self):
        self.cmd(0x04)

    def wait_while_busy(self):
        while ord(self.read_sts()) & 1:
            pass

    def _erase(self, addr, length):
        opcode = {
            4 * 1024: 0x20,
            32 * 1024: 0x52,
            64 * 1024: 0xd8,
        }[length]
        self.write_enable()
        self.cmd(opcode, addr)
        self.wait_while_busy()

    def erase(self, addr, length):
        possible_lengths = (1, 4 * 1024, 32 * 1024, 64 * 1024)

        while length > 0:
            erase_length = max(p for p in possible_lengths
                               if p <= length and addr % p == 0)

            if erase_length == 1:
                # there are no opcode to erase that much
                # either we want to erase up to multiple of 0x1000
                # or we want to erase up to length

                # start_addr                            end_addr
                # v                                     v
                # +------------------+------------------+----------------+
                # |       keep       |      erase       |      keep      |
                # +------------------+------------------+----------------+
                #  <- start_length -> <- erase_length -> <- end_length ->

                start_addr = addr & 0xfff000
                start_length = addr & 0xfff
                erase_length = min(0x1000 - start_length, length)
                end_addr = start_addr + start_length + erase_length
                end_length = start_addr + 0x1000 - end_addr

                # read data we need to restore later
                if start_length:
                    start_read_data = self.read(start_addr, start_length)
                if end_length:
                    end_read_data = self.read(end_addr, end_length)

                # erase the block
                self._erase(start_addr, 0x1000)

                # restore data
                if start_length:
                    self.write(start_addr, start_read_data)
                if end_length:
                    self.write(end_addr, end_read_data)

            else:
                # there is an opcode to erase that much data
                self.progress(erase_length)
                self._erase(addr, erase_length)

            # update
            length -= erase_length
            addr += erase_length

    # don't use this directly, use the public "write" function instead
    def _write(self, addr, data):
        self.write_enable()
        self.cmd(0x02, addr, data)

        # FIXME: this is a workaround for a bug in the bootloader verilog.  if
        #        the status register read comes too early, then it corrupts the
        #        SPI flash write in progress.  this busy loop waits long enough
        #        such that the write data has finished and data corruption is
        #        no longer possible.
        import timeit
        t = timeit.default_timer()
        while timeit.default_timer() - t < 0.000060:
            self.spinner = (self.spinner + 1) & 0xff

        self.wait_while_busy()
        self.progress(len(data))

    def write(self, addr, data):
        while data:
            dist_to_256_byte_boundary = 256 - (addr & 0xff)
            write_length = min(16, len(data), dist_to_256_byte_boundary)
            self._write(addr, data[:write_length])
            data = data[write_length:]
            addr += write_length

    def program(self, addr, data):
        self.progress("Erasing designated flash pages")
        self.erase(addr, len(data))

        self.progress("Writing bitstream")
        self.write(addr, data)

        self.progress("Verifying bitstream")
        read_back = self.read(addr, len(data))

        if read_back == data:
            self.progress("Success!")
            return True
        else:
            self.progress("Verification Failed!")
            print (read_back, data)

            print "len: {:06x} {:06x}".format(len(data), len(read_back))
            for i in range(min(len(data), len(read_back))):
                if read_back[i] != data[i]:
                    print "diff {:06x}: {:02x} {:02x}".format(
                        i, ord(data[i]), ord(read_back[i]))

            return False

    def boot(self):
        self.ser.write("\x00")
        self.ser.flush()

    def slurp(self, filename):
        with open(filename, 'rb') as f:
            bitstream = f.read()
        if filename.endswith('.hex'):
            bitstream = ''.join(chr(int(i, 16)) for i in bitstream.split())
        elif not filename.endswith('.bin'):
            raise ValueError('Unknown bitstream extension')
        return (0x30000, bitstream)

    def program_bitstream(self, addr, bitstream):
        self.progress("Waking up SPI flash")
        self.wake()

        self.read_sts()
        self.read(0, 16)

        self.progress(str(len(bitstream)) + " bytes to program")
        if self.program(addr, bitstream):
            self.boot()
            return True

        # FIXME: printing out this spinner ensures the busy loop in _write is
        #        not optimized away
        print "Your lucky number: " + str(self.spinner)

        return False


if __name__ == '__main__':
    import sys
    import argparse
    import serial
    from serial.tools.list_ports import comports

    parser = argparse.ArgumentParser()

    parser.add_argument("-l", "--list", action="store_true",
                        help="list connected and active TinyFPGA B-series "
                             "boards")
    parser.add_argument("-p", "--program", type=str,
                        help="program TinyFPGA board with the given bitstream")
    parser.add_argument("-b", "--boot", action="store_true",
                        help="command the TinyFPGA B-series board to exit the "
                             "bootloader and load the user configuration")
    parser.add_argument("-c", "--com", type=str, help="serial port name")

    args = parser.parse_args()

    print ""
    print "    TinyFPGA B-series Programmer CLI"
    print "    --------------------------------"

    active_boards = [p[0] for p in comports() if ("1209:2100" in p[2])]

    # find port to use
    active_port = None
    if args.com is not None:
        active_port = args.com
    elif not active_boards:
        print "    No port was specified and no active bootloaders found."
        print "    Activate bootloader by pressing the reset button."
        sys.exit(1)
    elif len(active_boards) == 1:
        print "    Only one board with active bootloader, using it."
        active_port = active_boards[0]
    else:
        print "    Please choose a board with the -c option."

    # list boards
    if args.list or active_port is None:
        print "    Boards with active bootloaders:"
        for p in active_boards:
            print "        " + p
        if len(active_boards) == 0:
            print "        No active bootloaders found.  Check USB connections"
            print "        and press reset button to activate bootloader."

    # program the flash memory
    elif args.program is not None:
        print "    Programming " + active_port + " with " + args.program

        def progress(info):
            if isinstance(info, str):
                print "    " + info

        with serial.Serial(active_port, 115200, timeout=0.2,
                           writeTimeout=0.2) as ser:
            fpga = TinyFPGAB(ser, progress)
            (addr, bitstream) = fpga.slurp(args.program)
            if not fpga.is_bootloader_active():
                print "    Bootloader not active"
                sys.exit(1)
            if not fpga.program_bitstream(addr, bitstream):
                sys.exit(1)

    # boot the FPGA
    if args.boot:
        print "    Booting " + active_port
        with serial.Serial(active_port, 115200, timeout=0.2,
                           writeTimeout=0.2) as ser:
            fpga = TinyFPGAB(ser)
            fpga.boot()
