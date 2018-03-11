import os
import pytest
import shutil
import string
import tempfile
from tinyfpgab import TinyFPGAB

DATA = b'Thequickbrownfoxjumpsoverthelazydog'
DATA_4096 = ''.join(a + b + c
                    for a in string.ascii_uppercase
                    for b in string.ascii_lowercase
                    for c in string.digits)[:4096]


class FakeSerial(object):

    def __init__(self, read_data=b''):
        self.written = []  # str instance if data written, True if flush call
        self.read_data = read_data

    def write(self, data):
        assert isinstance(data, bytearray)
        self.written.append(data)

    def read(self, read_len):
        assert len(self.read_data) >= read_len
        data = self.read_data[:read_len]
        self.read_data = self.read_data[read_len:]
        return data

    def flush(self):
        self.written.append(True)

    def assert_written(self, parts):
        # insert True after each write (for flush calls)
        expected = []
        for part in parts:
            expected.append(part)
            expected.append(True)
        # test
        assert self.written == expected


@pytest.fixture(scope='module')
def bitstream_dir():
    # file content
    hexdata = '''
54 68
65 71 75 69 63 6b 62 72
6f 77 6e 66 6f 78 6a 75 6d 70 73 6f 76 65 72 74 68 65 6c 61 7a 79 64
6f 67
    '''.strip() + '\n\n'
    data = bytearray.fromhex(hexdata.replace(' ', '').replace('\n', ''))
    assert data == DATA
    # create temporary directory
    tmpdir = tempfile.mkdtemp()
    # create the files
    with open(os.path.join(tmpdir, 'bitstream.hex'), 'w') as f:
        f.write(hexdata)
    with open(os.path.join(tmpdir, 'bitstream.bin'), 'wb') as f:
        f.write(DATA)
    with open(os.path.join(tmpdir, 'bitstream.unknown'), 'w') as f:
        f.write('???')
    # give the temporary directory to test cases needing it
    yield tmpdir
    # delete temporary directory
    shutil.rmtree(tmpdir)


@pytest.mark.parametrize('method, serial_out, serial_in, expected', [
    ('sleep', '0101000000b9', '', None),
    ('wake', '0101000000ab', '', None),
    ('read_id', '01010004009f', '1f8401', '1f8401'),
    ('read_sts', '010100020005', '01', '01'),
    ('write_enable', '010100000006', '', None),
    ('write_disable', '010100000004', '', None),
    ('boot', '00', '', None),
])
def test_simple_cmds(method, serial_out, serial_in, expected):
    # prepare
    serial = FakeSerial(bytearray.fromhex(serial_in))
    fpga = TinyFPGAB(serial)
    if expected is not None:
        expected = bytearray.fromhex(expected)
    # run
    output = getattr(fpga, method)()
    # check
    assert output == expected
    assert not serial.read_data
    serial.assert_written([bytearray.fromhex(serial_out)])


@pytest.mark.parametrize('success_after', range(5))
def test_is_bootloader_active(success_after):
    # prepare
    calls = []
    fpga = TinyFPGAB(None)
    read_id = ['ABC'] * success_after + [b'\x1f\x84\x01']
    # patching methods
    fpga.wake = lambda *a: calls.append(('wake', a))
    fpga.read = lambda *a: calls.append(('read', a))
    fpga.read_id = lambda *a: calls.append(('read_id', a)) or read_id.pop(0)
    # run
    output = fpga.is_bootloader_active()
    # check
    assert output == (success_after < 6)
    expected_calls = [
        ('wake', ()),
        ('read', (0, 16)),
        ('wake', ()),
        ('read_id', ()),
    ] * min(success_after + 1, 6)
    assert calls == expected_calls


@pytest.mark.parametrize('length, serial_outs', [
    # reading 16 bytes at a time, so testing various lengths
    (5, ['01050006000b12345600']),
    (16, ['01050011000b12345600']),
    (17, ['01050011000b12345600',
          '01050002000b12346600']),
    (35, ['01050011000b12345600',
          '01050011000b12346600',
          '01050004000b12347600']),
])
def test_read(length, serial_outs):
    # prepare
    serial = FakeSerial(DATA[:length])
    fpga = TinyFPGAB(serial)
    # run
    output = fpga.read(0x123456, length)
    # check
    assert output == DATA[:length]
    assert not serial.read_data
    serial.assert_written([bytearray.fromhex(d) for d in serial_outs])


def test_wait_while_busy():
    # prepare
    serial = FakeSerial(bytearray.fromhex('0101010100'))
    fpga = TinyFPGAB(serial)
    # run
    assert fpga.wait_while_busy() is None
    # check
    assert not serial.read_data
    serial.assert_written([bytearray.fromhex('010100020005')] * 5)


@pytest.mark.parametrize('offset, length, block_len, serial_outs', [
    # well aligned, one block
    (0x123000, 0x1000, 0x1000, ['010400000020123000']),
    (0x120000, 0x8000, 0x8000, ['010400000052120000']),
    (0x120000, 0x10000, 0x10000, ['0104000000d8120000']),
    # well aligned, several blocks
    (0x123000, 0x2000, 0x1000, ['010400000020123000',
                                '010400000020124000']),
    (0x123000, 0x8000, 0x1000, ['010400000020123000',
                                '010400000020124000',
                                '010400000020125000',
                                '010400000020126000',
                                '010400000020127000',
                                '010400000020128000',
                                '010400000020129000',
                                '01040000002012a000']),
    # within the block, erase start of block
    (0x123000, 0xff0, 0x1000, ['010400000020123000']),
    # within the block, erase end of block
    (0x123010, 0xff0, 0x1000, ['010400000020123000']),
    # within the block, erase middle of block
    (0x123008, 0xff0, 0x1000, ['010400000020123000']),
    # several block, not aligned
    (0x123010, 0x2fe0, 0x1000, ['010400000020123000',
                                '010400000020124000',
                                '010400000020125000'])
])
def test_erase(offset, length, block_len, serial_outs):
    # prepare
    calls = []
    serial = FakeSerial()
    fpga = TinyFPGAB(serial)
    fpga.write_enable = lambda: None  # patch write_enable
    fpga.wait_while_busy = lambda: None  # patch wait_while_busy
    fpga.read = lambda *a: calls.append(('read', a)) \
        or DATA_4096[a[0] % 4096:][:a[1]]
    fpga.write = lambda *a: calls.append(('write', a))
    # run
    assert fpga.erase(offset, length) is None
    # check
    assert not serial.read_data
    serial.assert_written([bytearray.fromhex(d) for d in serial_outs])
    expected_calls = []
    restore_first_block = None
    if offset % block_len > 0:  # restore start of first block
        restore_offset = offset & ~(block_len - 1)
        restore_len = offset % block_len
        expected_calls.append((
            'read', (restore_offset, restore_len)))
        expected_calls.append((
            'write', (restore_offset, DATA_4096[:restore_len])))
        restore_first_block = restore_offset
    if (offset + length) % block_len > 0:  # restore end of last block
        restore_offset = offset + length
        restore_len = block_len - (restore_offset % block_len)
        read_call = ('read', (restore_offset, restore_len))
        if restore_first_block == ((offset + length) & ~(block_len - 1)):
            # restore before and after erase in same block
            expected_calls.insert(1, read_call)  # 2nd read before 1st write
        else:
            expected_calls.append(read_call)  # 2nd read after 1st write
        expected_calls.append((
            'write', (restore_offset, DATA_4096[restore_offset % block_len:])))
    assert calls == expected_calls


@pytest.mark.parametrize('offset, length, serial_outs', [
    # witting 16 bytes at a time, so testing various length
    (0x123400, 5, ['0109000000021234005468657175']),
    (0x123400, 16, ['011400000002123400546865717569636b62726f776e666f78']),
    (0x123400, 17, ['011400000002123400546865717569636b62726f776e666f78',
                    '0105000000021234106a']),
    (0x123400, 35, ['011400000002123400546865717569636b62726f776e666f78',
                    '0114000000021234106a756d70736f7665727468656c617a79',
                    '010700000002123420646f67']),
    # specific case: write cannot cross 256 bytes boundaries
    (0x1234fd, 5, ['0107000000021234fd546865',
                   '0106000000021235007175']),
])
def test_write(offset, length, serial_outs):
    # prepare
    serial = FakeSerial()
    fpga = TinyFPGAB(serial)
    fpga.write_enable = lambda: None  # patch write_enable
    fpga.wait_while_busy = lambda: None  # patch wait_while_busy
    data = DATA[:length]
    # run
    assert fpga.write(offset, data) is None
    # check
    assert not serial.read_data
    serial.assert_written([bytearray.fromhex(d) for d in serial_outs])


@pytest.mark.parametrize('success', [True, False])
def test_program(success):
    # prepare
    calls = []
    fpga = TinyFPGAB(None, lambda *a: calls.append(('progress', a)))
    # patching methods
    fpga.erase = lambda *a: calls.append(('erase', a))
    fpga.write = lambda *a: calls.append(('write', a))
    if success:
        fpga.read = lambda *a: calls.append(('read', a)) or DATA
    else:
        fpga.read = lambda *a: calls.append(('read', a)) or 'This is a fail'
    # run
    output = fpga.program(0x123456, DATA)
    # check
    assert output == success
    expected_calls = [
        ('progress', ('Erasing designated flash pages', )),
        ('erase', (0x123456, 35)),
        ('progress', ('Writing bitstream', )),
        ('write', (0x123456, DATA)),
        ('progress', ('Verifying bitstream', )),
        ('read', (0x123456, 35)),
    ]

    if success:
        expected_calls.extend([
            ('progress', ('Success!',)),
        ])
    else:
        expected_calls.extend([
            ('progress', ('Need to rewrite some pages...',)),
            ('progress', ('len: 000023 00000e',)),
            ('progress', ('rewriting page 123456',)),
            ('erase', (1193046, 35)),
            ('write', (1193046, b'Thequickbrownfoxjumpsoverthelazydog')),
            ('read', (1193046, 35)),
            ('erase', (1193046, 35)),
            ('write', (1193046, b'Thequickbrownfoxjumpsoverthelazydog')),
            ('read', (1193046, 35)),
            ('erase', (1193046, 35)),
            ('write', (1193046, b'Thequickbrownfoxjumpsoverthelazydog')),
            ('read', (1193046, 35)),
            ('erase', (1193046, 35)),
            ('write', (1193046, b'Thequickbrownfoxjumpsoverthelazydog')),
            ('read', (1193046, 35)),
            ('erase', (1193046, 35)),
            ('write', (1193046, b'Thequickbrownfoxjumpsoverthelazydog')),
            ('read', (1193046, 35)),
            ('erase', (1193046, 35)),
            ('write', (1193046, b'Thequickbrownfoxjumpsoverthelazydog')),
            ('read', (1193046, 35)),
            ('progress', ('Verification Failed!',)),
        ])

    assert calls == expected_calls


@pytest.mark.parametrize('ext', ['hex', 'bin', 'unknown'])
def test_slurp(bitstream_dir, ext):
    # prepare
    fpga = TinyFPGAB(None)
    filename = os.path.join(bitstream_dir, 'bitstream.{}'.format(ext))
    expected = (0x30000, DATA)
    # run
    if ext == 'unknown':
        with pytest.raises(ValueError):
            fpga.slurp(filename)
    else:
        output = fpga.slurp(filename)
        # check
        assert output == expected


@pytest.mark.parametrize('success', [True, False])
def test_program_bitstream(success):
    # prepare
    calls = []
    fpga = TinyFPGAB(None, lambda *a: calls.append(('progress', a)))
    # patching methods
    fpga.wake = lambda *a: calls.append(('wake', a))
    fpga.read_sts = lambda *a: calls.append(('read_sts', a))
    fpga.read = lambda *a: calls.append(('read', a))
    if success:
        fpga.program = lambda *a: calls.append(('program', a)) or True
    else:
        fpga.program = lambda *a: calls.append(('program', a)) or False
    fpga.boot = lambda *a: calls.append(('boot', a))
    # run
    output = fpga.program_bitstream(0x123456, DATA)
    # check
    assert output == success
    expected_calls = [
        ('progress', ('Waking up SPI flash', )),
        ('progress', ('35 bytes to program', )),
        ('program', (0x123456, DATA)),
    ]
    if success:
        expected_calls.append(('boot', ()))
    assert calls == expected_calls
