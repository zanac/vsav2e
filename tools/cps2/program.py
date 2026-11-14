"""Loading the 68000 program of a CPS2 set from its MAME zip.

The program chips (`.03` to `.10`, 512 KB each) are stored byte-swapped
(`ROM_LOAD16_WORD_SWAP` in MAME): swapping every pair of bytes gives the program as the
68000 sees it, big endian. On a real board the opcodes are encrypted and the data is
not, so texts and tables can be read from these files as they are; code can only be
read from the decrypted ("Phoenix", `...d`) sets or from MAME's decrypted opcodes.
"""
import os
import zipfile

# set name -> the program chips in address order (path inside the zip of the parent set)
PROGRAM_CHIPS = {
    # Vampire Savior 2 (Japan): the game we translate
    'vsav2': ['vs2j.03', 'vs2j.04', 'vs2j.05', 'vs2j.06', 'vs2j.07', 'vs2j.08', 'vs2j.09', 'vs2j.10'],
    # Vampire Savior 2, decrypted ("Phoenix"): code that can be read and patched
    'vsav2d': ['vsav2d/vs2j_d.03', 'vsav2d/vs2j_d.04', 'vs2j.05', 'vs2j.06', 'vs2j.07', 'vs2j.08',
               'vs2j.09', 'vs2j.10'],
    # Vampire Hunter 2 (Japan): has the three characters vsav2 lacks
    'vhunt2': ['vh2j.03a', 'vh2j.04a', 'vh2j.05', 'vh2j.06', 'vh2j.07', 'vh2j.08', 'vh2j.09', 'vh2j.10'],
    # Vampire Savior (Europe): Capcom's own English texts for the Savior roster
    'vsav': ['vm3e.03d', 'vm3e.04d', 'vm3.05a', 'vm3.06a', 'vm3.07b', 'vm3.08a', 'vm3.09b', 'vm3.10b'],
    # its decrypted clone (Phoenix Edition): the code of the first 1 MB can be read
    'vsavd': ['vsavd/vm3ed.03d', 'vsavd/vm3ed.04d', 'vm3.05a', 'vm3.06a', 'vm3.07b', 'vm3.08a', 'vm3.09b',
              'vm3.10b'],
    # Vampire Savior (Japan): the Japanese texts the English ones translate
    'vsavj': ['vsavj/vm3j.03d', 'vsavj/vm3j.04d', 'vsavj/vm3j.05a', 'vsavj/vm3j.06b',
              'vsavj/vm3j.07b', 'vsavj/vm3j.08a', 'vsavj/vm3j.09b', 'vsavj/vm3j.10b'],
    # Night Warriors (Europe): English texts for Donovan, Huitzil and Pyron
    'nwarr': ['vphe.03f', 'vphe.04c', 'vphe.05d', 'vphe.06c', 'vphe.07b', 'vphe.08b', 'vphe.09b', 'vphe.10b'],
    # Vampire Hunter (Japan): the Japanese texts of Night Warriors
    'vhuntj': ['vhuntj/vphj.03f', 'vhuntj/vphj.04c', 'vhuntj/vphj.05d', 'vhuntj/vphj.06c',
               'vhuntj/vphj.07b', 'vhuntj/vphj.08b', 'vhuntj/vphj.09b', 'vhuntj/vphj.10b'],
}
# the zip each set is read from (clones live in their parent's zip)
PARENT_ZIP = {'vsav2': 'vsav2', 'vsav2d': 'vsav2', 'vhunt2': 'vhunt2', 'vsav': 'vsav', 'vsavd': 'vsav', 'vsavj': 'vsav',
              'nwarr': 'nwarr', 'vhuntj': 'nwarr'}


def swap_byte_pairs(data):
    swapped = bytearray(len(data))
    swapped[0::2] = data[1::2]
    swapped[1::2] = data[0::2]
    return bytes(swapped)


def load_program(set_name, rom_directory=None):
    """the 4 MB program of a set as the 68000 sees it"""
    rom_directory = rom_directory or os.environ.get('VS_ROMS', 'roms')
    archive = zipfile.ZipFile(os.path.join(rom_directory, PARENT_ZIP[set_name] + '.zip'))
    return b''.join(swap_byte_pairs(archive.read(chip)) for chip in PROGRAM_CHIPS[set_name])


def split_program(program_bytes):
    """the eight 512 KB chips of a program, byte-swapped back for the ROM files"""
    chip_size = 0x80000
    return [swap_byte_pairs(program_bytes[start:start + chip_size])
            for start in range(0, len(program_bytes), chip_size)]
