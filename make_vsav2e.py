#!/usr/bin/env python3
"""make_vsav2e.py ROM_DIRECTORY [OUTPUT_DIRECTORY]

Builds vsav2e.zip, Darkstalkers 3: the English full-roster Vampire Savior 2, from the MAME sets in
ROM_DIRECTORY: vsav2.zip (with its decrypted clone vsav2d inside), vsav.zip (Vampire
Savior, Europe: the English texts) and vhunt2.zip (Vampire Hunter 2: Jon Talbain, Rikuo
and Sasquatch).

The zip holds what vsav2e has more than its parent vsav2: the program (eight chips and
the extension at 0x400000), four sprite ROMs (the ones of Vampire Hunter 2 that differ
from Vampire Savior 2's, with the new tiles of the select screen in their empty space),
the sound program and the two sample ROMs of Vampire Hunter 2, copied as they are.

The select screen is laid out like the PlayStation Darkstalkers 3's and takes its three
new cells from captures of it: assets/psx/select/*.png, next to this script. The title
screen is the PlayStation one, from the captures in assets/psx/title/.
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
PROGRAM_EXTENSION_NAME = 'vs2e.10x'
# the upper sprite bank: Vampire Hunter 2's vh2.13m, .15m, .17m and .19m, changed
UPPER_SPRITE_BANK_NAMES = ['vs2e.21m', 'vs2e.23m', 'vs2e.25m', 'vs2e.27m']
SOUND_PROGRAM_NAMES = ['vs2e.01', 'vs2e.02']
# the second 8 MB of QSound samples: Vampire Hunter 2's
HUNTER_SAMPLE_ROMS = ['vh2.11m', 'vh2.12m']
PSX_DIRECTORY = os.path.join(HERE, 'assets', 'psx')


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    rom_directory = sys.argv[1]
    output_directory = sys.argv[2] if len(sys.argv) > 2 else '.'
    main_program, extension, upper_sprite_bank, sound_program = build.build(rom_directory, PSX_DIRECTORY)
    files = list(zip(PROGRAM_CHIP_NAMES, program.split_program(main_program)))
    files.append((PROGRAM_EXTENSION_NAME, program.swap_byte_pairs(extension)))
    files.extend(zip(UPPER_SPRITE_BANK_NAMES, upper_sprite_bank))
    half = len(sound_program) // 2
    files.extend(zip(SOUND_PROGRAM_NAMES, (sound_program[:half], sound_program[half:])))
    with zipfile.ZipFile(os.path.join(rom_directory, 'vhunt2.zip')) as hunter_archive:
        for name in HUNTER_SAMPLE_ROMS:
            files.append((name, hunter_archive.read(name)))

    output_path = os.path.join(output_directory, 'vsav2e.zip')
    # the zip is written in full before anything is printed, so that a closed output
    # pipe (`... | head`) cannot leave it half written
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files:
            archive.writestr(name, data)
    for name, data in files:
        print('  %-8s %7d  %08x' % (name, len(data), zlib.crc32(data) & 0xffffffff))
    print('written', output_path)


if __name__ == '__main__':
    main()
