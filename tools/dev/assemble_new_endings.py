#!/usr/bin/env python3
"""assemble_new_endings.py: new_endings.s -> tools/build/new_endings_code.py

The endings of Donovan, Huitzil and Pyron are written in 68000 assembly (tools/dev/new_endings.s)
and the build, which must not need an assembler, takes the bytes from the Python module this
writes. The code is position independent but for the addresses of routines of the game and
of the data the build places (the names in EXTERNALS): each is assembled with a distinctive
number, and the places where that number appears become the relocations the build fills.

    python3 tools/dev/assemble_new_endings.py          needs GNU binutils for the 68000
                                                       (m68k-linux-gnu-as and -objcopy)
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, 'new_endings.s')
OUTPUT = os.path.join(HERE, '..', 'build', 'new_endings_code.py')


def external_names(source):
    """the names the source declares with `.extern_name NAME` lines in its header"""
    return re.findall(r'^\s*\|\s*EXTERNAL\s+(\w+)', source, re.M)


def assemble(source_path, defsyms):
    with tempfile.TemporaryDirectory() as work:
        obj, binary = os.path.join(work, 'a.o'), os.path.join(work, 'a.bin')
        command = ['m68k-linux-gnu-as', '-m68000', '-o', obj, source_path]
        for name, value in defsyms.items():
            command += ['--defsym', '%s=%d' % (name, value)]
        subprocess.run(command, check=True)
        subprocess.run(['m68k-linux-gnu-objcopy', '-O', 'binary', obj, binary], check=True)
        symbols = subprocess.run(['m68k-linux-gnu-nm', obj], check=True, capture_output=True, text=True).stdout
        labels = {}
        for line in symbols.splitlines():
            parts = line.split()
            if len(parts) == 3 and parts[1] in 'tT':
                labels[parts[2]] = int(parts[0], 16)
        return open(binary, 'rb').read(), labels


def main():
    source = open(SOURCE).read()
    names = external_names(source)
    sentinels = {name: 0x7e000000 + (index << 16) + 0x0101 for index, name in enumerate(names)}
    code, labels = assemble(SOURCE, sentinels)
    relocations = []
    for name, value in sentinels.items():
        pattern = value.to_bytes(4, 'big')
        position = code.find(pattern)
        while position >= 0:
            relocations.append((position, name))
            position = code.find(pattern, position + 1)
    relocations.sort()
    with open(OUTPUT, 'w') as out:
        out.write('"""The endings of Donovan, Huitzil and Pyron, assembled from tools/dev/new_endings.s by\n')
        out.write('tools/dev/assemble_new_endings.py (do not edit). RELOCATIONS: where the build writes the\n')
        out.write('address of each external (a long); LABELS: the offsets of the entry points."""\n\n')
        out.write('CODE = bytes.fromhex(\n')
        hexa = code.hex()
        for start in range(0, len(hexa), 96):
            out.write("    '%s'\n" % hexa[start:start + 96])
        out.write(')\n\n')
        out.write('RELOCATIONS = %r\n\n' % relocations)
        out.write('LABELS = %r\n' % {k: v for k, v in sorted(labels.items()) if not k.startswith('.')})
    print('%d bytes, %d relocations, labels: %s' % (len(code), len(relocations), ', '.join(sorted(labels))))


if __name__ == '__main__':
    main()
