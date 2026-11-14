#!/usr/bin/env python3
"""make_vsav2e.py ROM_DIRECTORY [OUTPUT_DIRECTORY]

Builds vsav2e.zip, the program of the English full-roster Vampire Savior 2, from the
MAME sets in ROM_DIRECTORY: vsav2.zip (with its decrypted clone vsav2d inside), vsav.zip
(Vampire Savior, Europe: the English texts) and, later, vhunt2.zip.

Work in progress: for now the zip holds the eight program chips only.
"""
import os
import sys
import zipfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'tools'))
sys.path.insert(0, os.path.join(HERE, 'text'))
from build import build
from cps2 import program

PROGRAM_CHIP_NAMES = ['vs2e.03', 'vs2e.04', 'vs2e.05', 'vs2e.06', 'vs2e.07', 'vs2e.08',
                      'vs2e.09', 'vs2e.10']


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    rom_directory = sys.argv[1]
    output_directory = sys.argv[2] if len(sys.argv) > 2 else '.'
    chips = program.split_program(build.build(rom_directory))
    output_path = os.path.join(output_directory, 'vsav2e.zip')
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in zip(PROGRAM_CHIP_NAMES, chips):
            archive.writestr(name, data)
            print('  %-8s %7d  %08x' % (name, len(data), zlib.crc32(data) & 0xffffffff))
    print('written', output_path)


if __name__ == '__main__':
    main()
