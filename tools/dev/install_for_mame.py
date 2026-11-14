#!/usr/bin/env python3
"""install_for_mame.py vsav2e.zip ROM_DIRECTORY TEST_DIRECTORY

Development helper: lays vsav2e's program out as MAME's `vsav2d` set so that a stock
MAME can run it (`mame vsav2d -rompath TEST_DIRECTORY`; MAME only warns about the
checksums). It copies vsav2.zip from ROM_DIRECTORY into TEST_DIRECTORY with the program
chips replaced.
"""
import os
import sys
import zipfile

# the name each vsav2e chip takes inside MAME's vsav2.zip to be loaded by `vsav2d`
MAME_NAME = {'vs2e.03': 'vsav2d/vs2j_d.03', 'vs2e.04': 'vsav2d/vs2j_d.04', 'vs2e.05': 'vs2j.05',
             'vs2e.06': 'vs2j.06', 'vs2e.07': 'vs2j.07', 'vs2e.08': 'vs2j.08',
             'vs2e.09': 'vs2j.09', 'vs2e.10': 'vs2j.10'}


def main():
    built_zip, rom_directory, test_directory = sys.argv[1:4]
    os.makedirs(test_directory, exist_ok=True)
    built = zipfile.ZipFile(built_zip)
    # what a stock CPS2 cannot load (the program extension, the second sprite bank) is
    # left out: everything but the three added characters works without it
    replaced = {MAME_NAME[name]: built.read(name) for name in built.namelist() if name in MAME_NAME}
    original = zipfile.ZipFile(os.path.join(rom_directory, 'vsav2.zip'))
    with zipfile.ZipFile(os.path.join(test_directory, 'vsav2.zip'), 'w', zipfile.ZIP_DEFLATED) as out:
        for name in original.namelist():
            out.writestr(name, replaced.get(name, original.read(name)))


if __name__ == '__main__':
    main()
