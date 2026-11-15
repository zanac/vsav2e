#!/usr/bin/env python3
"""release.py OUTPUT_DIRECTORY [VERSION]

Makes the build kit of a release: one zip with the portable build script and everything it
needs except the material taken from the home games (assets/) and the ROM sets, which the
person who builds supplies; plus `vsav2e.checksums.txt` of the chips a full build gives, if
`--checksums FILE` names the file a build wrote (make_vsav2e.py writes it next to vsav2e.zip).

    tools/release.py dist 1.0 --checksums out/vsav2e.checksums.txt

The kit needs only Python 3.8 or later and Pillow; no assembler (the assembled code is in
tools/build/new_endings_code.py as hex) and no MAME.
"""
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# not in the kit: the game's pictures (the person who builds puts them in assets/), the repository's screenshots
EXCLUDED = ('assets/', 'screenshots/', 'tools/dev/mame2003plus-dev-memory.patch')

BUILD_TEXT = """vsav2e build kit {version}
==========================

What you need
  * Python 3.8 or later and Pillow (pip install -r requirements.txt)
  * the MAME sets vsav2.zip (with vsav2d inside), vsav.zip (with vsavd inside) and
    vhunt2.zip in one folder: your own dumps, they are not in this kit
  * assets/ as in the repository (they come from the home games, so they are not in this
    kit either): assets/psx/select/*.png, assets/vsav2e_title_assets.zip and, for the
    new endings of Donovan, Huitzil and Pyron, assets/vsav2e_endings_assets.zip (without
    it those three keep Vampire Savior 2's endings)

Build (the same on Linux, macOS and Windows)
  python3 make_vsav2e.py ROM_FOLDER OUTPUT_FOLDER

It writes OUTPUT_FOLDER/vsav2e.zip and OUTPUT_FOLDER/vsav2e.checksums.txt. The build is
deterministic: with the same inputs the checksums are the same as in vsav2e.checksums.txt
of this kit (a full build, with all the assets), so you can tell that your zip is right.
Put vsav2e.zip in MAME's rom folder (or the mame2003-plus core's) next to vsav2.zip.
"""


def tracked_files():
    names = subprocess.check_output(['git', '-C', HERE, 'ls-files'], text=True).split('\n')
    return [name for name in names if name and not name.startswith(EXCLUDED)]


def main():
    arguments = sys.argv[1:]
    checksums = None
    if '--checksums' in arguments:
        index = arguments.index('--checksums')
        checksums = arguments[index + 1]
        del arguments[index:index + 2]
    if not arguments:
        sys.exit(__doc__)
    output = arguments[0]
    version = arguments[1] if len(arguments) > 1 else 'dev'
    os.makedirs(output, exist_ok=True)
    path = os.path.join(output, 'vsav2e-build-kit-%s.zip' % version)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as kit:
        for name in tracked_files():
            kit.write(os.path.join(HERE, name), 'vsav2e/' + name)
        kit.writestr('vsav2e/requirements.txt', 'Pillow\n')
        kit.writestr('vsav2e/BUILD.txt', BUILD_TEXT.format(version=version))
        if checksums:
            kit.write(checksums, 'vsav2e/vsav2e.checksums.txt')
    print('written', path)


if __name__ == '__main__':
    main()
