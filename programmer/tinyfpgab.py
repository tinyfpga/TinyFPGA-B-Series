#!/usr/bin/env python2

import array


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
        for i in range(0, 3):
            self.wake()
            self.read(0, 16)
            self.wake()
            devid = self.read_id()
            expected_devid = [0x1F, 0x84, 0x01]
            if devid == expected_devid:
                return True
            else:
                import time
                time.sleep(0.05)
        return False

    def cmd(self, write_data, read_len):
        write_length_lo = len(write_data) & 0xFF
        write_length_hi = (len(write_data) >> 8) & 0xFF
        cmd_read_len = 0
        if (read_len > 0):
            cmd_read_len = read_len + 1
        read_length_lo = cmd_read_len & 0xFF
        read_length_hi = (cmd_read_len >> 8) & 0xFF
        cmd_write_string = array.array('B', [
            1, write_length_lo, write_length_hi,
            read_length_lo, read_length_hi] + list(write_data)
        ).tostring()
        self.ser.write(cmd_write_string)
        self.ser.flush()
        cmd_read_string = self.ser.read(read_len)
        return array.array('B', cmd_read_string).tolist()

    def sleep(self):
        self.cmd([0xB9], 0)

    def wake(self):
        self.cmd([0xAB], 0)

    def read_id(self):
        return self.cmd([0x9F], 3)

    def read_sts(self):
        return self.cmd([0x05], 1)

    def read(self, addr, length):
        if length <= 16:
            read_value = self.cmd(
                [0x0B,
                 (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF,
                 0],
                length)
            self.progress(length)
            return read_value

        else:
            return_data = []

            remaining_length = length
            current_addr = addr

            while remaining_length > 0:
                read_length = min(16, remaining_length)
                return_data.extend(self.read(current_addr, read_length))
                current_addr += read_length
                remaining_length -= read_length

            return return_data

    def write_enable(self):
        self.cmd([0x06], 0)

    def write_disable(self):
        self.cmd([0x04], 0)

    def wait_while_busy(self):
        while (self.read_sts()[0] & 1):
            pass

    def _erase(self, addr, length):
        if length == (4 * 1024):
            opcode = 0x20

        elif length == (32 * 1024):
            opcode = 0x52

        else:
            assert length == (64 * 1024)
            opcode = 0xD8

        self.write_enable()
        self.cmd(
            [opcode,
             (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF],
            0)
        self.wait_while_busy()

    def erase(self, addr, length):
        possible_lengths = [1, 4 * 1024, 32 * 1024, 64 * 1024]

        remaining_length = length
        current_addr = addr

        while remaining_length > 0:
            erase_length = max(
                p for p in possible_lengths
                if p <= remaining_length and current_addr % p == 0)

            if erase_length == 1:
                start_addr = current_addr & 0xfff000
                start_length = current_addr % (4 * 1024)

                end_addr = (current_addr + remaining_length)
                end_length = (4 * 1024) - (end_addr % (4 * 1024))
                end_read_data = []

                do_start = current_addr % (4 * 1024) != 0

                if do_start:
                    start_read_data = self.read(start_addr, start_length)

                current_block_start = current_addr & 0xfff000
                last_block_start = (current_addr + remaining_length) & 0xfff000
                do_end = current_block_start == last_block_start

                if do_end:
                    end_read_data = self.read(end_addr, end_length)

                self._erase(start_addr, 4 * 1024)

                if do_start:
                    self.write(start_addr, start_read_data)

                if do_end:
                    self.write(end_addr, end_read_data)
                    remaining_length = 0

                else:
                    erase_length = (4 * 1024) - start_length
                    remaining_length -= erase_length
                    current_addr += erase_length

            else:
                self.progress(erase_length)
                self._erase(current_addr, erase_length)
                remaining_length -= erase_length
                current_addr += erase_length

    # don't use this directly, use the public "write" function instead
    def _write(self, addr, data):
        self.write_enable()
        self.cmd(
            [0x02,
             (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF
             ] + list(data),
            0)

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
        remaining_length = len(data)
        current_addr = addr
        offset = 0

        while remaining_length > 0:
            dist_to_256_byte_boundary = 256 - (current_addr & 0xff)
            write_length = min(16, remaining_length, dist_to_256_byte_boundary)
            self._write(current_addr, data[offset:offset + write_length])
            current_addr += write_length
            offset += write_length
            remaining_length -= write_length

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

            print "len: %06x %06x" % (len(data), len(read_back))
            for i in range(min(len(data), len(read_back))):
                if read_back[i] != data[i]:
                    print "diff %06x: %02x %02x" % (i, data[i], read_back[i])

            return False

    def boot(self):
        self.ser.write("\x00")
        self.ser.flush()

    def slurp(self, filename):
        if filename.endswith(".hex"):
            return (0x30000, [int(i, 16)
                              for i in open(filename).read().split()])

        if filename.endswith(".bin"):
            return (0x30000, list(bytearray(open(filename, 'rb').read())))

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
    import traceback
    import argparse
    import serial
    from serial.tools.list_ports import comports

    p = argparse.ArgumentParser()

    p.add_argument("-l", "--list", action="store_true",
                   help="list connected and active TinyFPGA B-series boards")
    p.add_argument("-p", "--program", type=str,
                   help="program TinyFPGA board with the given bitstream")
    p.add_argument("-b", "--boot", action="store_true",
                   help="command the TinyFPGA B-series board to exit the "
                        "bootloader and load the user configuration")
    p.add_argument("-c", "--com", type=str, help="serial port name")

    args = p.parse_args()

    print ""
    print "    TinyFPGA B-series Programmer CLI"
    print "    --------------------------------"

    active_boards = [p[0] for p in comports() if ("1209:2100" in p[2])]

    active_port = None

    if args.com is not None:
        active_port = args.com
    elif len(active_boards) > 0:
        active_port = active_boards[0]

    if args.list:
        print "    Boards with active bootloaders:"
        for p in active_boards:
            print "        " + p
        if len(active_boards) == 0:
            print "        No active bootloaders found.  Check USB connections"
            print "        and press reset button to activate bootloader."

    if args.program is not None:
        if active_port is None:
            print "    No port was specified and no active bootloaders found."
            print "    Activate bootloader by pressing the reset button."
            sys.exit()

        print "    Programming " + active_port + " with " + args.program

        def progress(info):
            if isinstance(info, str):
                print "    " + info

        with serial.Serial(active_port, 115200, timeout=0.2,
                           writeTimeout=0.2) as ser:
            fpga = TinyFPGAB(ser, progress)

            (addr, bitstream) = fpga.slurp(args.program)

            fpga.is_bootloader_active()

            try:
                fpga.program_bitstream(addr, bitstream)
            except:
                program_failure = True
                traceback.print_exc()

    if args.boot:
        if active_port is None:
            print "    No port was specified and no active bootloaders found."
            print "    Activate bootloader by pressing the reset button."
            sys.exit()

        print "    Booting " + active_port

        with serial.Serial(active_port, 10000000, timeout=0.1,
                           writeTimeout=0.1) as ser:
            fpga = TinyFPGAB(ser, None)
            fpga.boot()
