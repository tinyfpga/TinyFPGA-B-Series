import serial
import array


def h(a):
    return ' '.join("%02X" % i for i in a)


class TinyFPGAB(object):
    def __init__(self, ser, progress = None):
        self.ser = ser

        if progress is None:
            self.progress = lambda x: x
        else:
            self.progress = progress

    def cmd(self, write_data, read_len):
        write_length_lo = len(write_data) & 0xFF
        write_length_hi = (len(write_data) >> 8) & 0xFF
        cmd_read_len = 0
        if (read_len > 0):
            cmd_read_len = read_len + 1
        read_length_lo = cmd_read_len & 0xFF
        read_length_hi = (cmd_read_len >> 8) & 0xFF
        cmd_write_string = array.array('B', [1, write_length_lo, write_length_hi, read_length_lo, read_length_hi] + list(write_data)).tostring()
        self.ser.write(cmd_write_string)
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
            read_value = self.cmd([0x0B, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF, 0], length)
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
        opcode = 0

        if length == (4 * 1024):
            opcode = 0x20

        elif length == (32 * 1024):
            opcode = 0x52

        elif length == (64 * 1024):
            opcode = 0xD8

        self.write_enable()
        self.cmd([opcode, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF], 0)
        self.wait_while_busy()



    def erase(self, addr, length):
        possible_lengths = [1, 4 * 1024, 32 * 1024, 64 * 1024]
        
        remaining_length = length
        current_addr = addr

        while remaining_length > 0:
            erase_length = max([p for p in possible_lengths if p <= remaining_length and current_addr % p == 0])
        
            if erase_length == 1:
                start_addr = current_addr & 0xfff000
                start_length = current_addr % (4 * 1024)
                
                
                end_addr = (current_addr + remaining_length)
                end_length = (4 * 1024) - (end_addr % (4 * 1024)) 
                end_read_data = []

                do_start = current_addr % (4 * 1024) != 0

                if do_start:
                    start_read_data = self.read(start_addr, start_length)

                do_end = (current_addr & 0xfff000) == ((current_addr + remaining_length - 1) & 0xfff000)

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
        self.cmd([0x02, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF] + list(data), 0)
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
            return False


    def boot(self):
        self.ser.write("\x00")

    def slurp(self, filename):
        if filename.endswith(".hex"):
            return (0x30000, [int(i, 16) for i in open(filename).read().split()])

        if filename.endswith(".mcs"):
            ih = IntelHex()
            ih.loadfile(filename, format='hex')
            return (0x00000, ih.tobinarray(start=0))



    def program_bitstream(self, addr, bitstream):
        self.progress("Waking up SPI flash")
        self.wake()

        self.read_sts()
        self.read(0, 16)

        self.progress(str(len(bitstream)) + " bytes to program")
        if self.program(addr, bitstream):
            self.boot()
