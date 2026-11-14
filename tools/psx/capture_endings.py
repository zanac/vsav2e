#!/usr/bin/env python3
"""Captures the endings of Donovan, Huitzil and Pyron in the PlayStation Darkstalkers 3
(the three characters Vampire Savior does not have), one PNG every 20 frames.

The game is driven by tools/psx/psxrun: title -> ARCADE, the character is poked into RAM
on the select screen (1c1112: the arcade ids, 0x13 Donovan, 0x10 Huitzil, 0x11 Pyron),
the vitality of the two players is poked so that player 1 wins, and cross is pressed
every 128 frames until the last fight is won; nothing is pressed during the ending,
which goes on by itself. The emulator is deterministic: the same inputs always
give the same matches, so the frames below are fixed (they were found on contact sheets
of a whole run). Pyron's run crashes the recompiler: it uses the interpreter.

The first pictures have the initials of the score ranking in the top left corner
(the game asks for them while the ending plays).

usage: capture_endings.py psxrun pcsx_rearmed_libretro.so disc.cue output_directory
"""
import os, subprocess, sys, tempfile
from PIL import Image

CHARACTER_ADDRESS = 0x1c1112
PRESS_SPACING = 128
# the cheat: player 1 keeps full vitality (0x120, both words) and player 2 is kept at 1, on
# every frame from the first fight on (player 1 then wins every match, by knockout or on
# time)
VITALITY_POKES = [(0x1c1228, 1), (0x1c1229, 0), (0x1c122a, 1), (0x1c122b, 0),
                  (0x1c0e54, 0x20), (0x1c0e55, 1), (0x1c0e56, 0x20), (0x1c0e57, 1)]
LAST_POKED_FRAME = 130000
PICTURE_SPACING = 20
# name: (character id, recompiler, last frame a button is pressed, first and last frame
# of the ending)
ENDINGS = {
    'donovan': (0x13, True, 82100, 82100, 84800),
    'huitzil': (0x10, True, 102450, 102500, 105800),
    'pyron': (0x11, False, 73700, 73700, 75800),
}


def capture(psxrun, core, cue, name, output):
    character, recompiler, last_press, first, last = ENDINGS[name]
    presses = ['2600:start', '2800:start', '3000:b']
    presses += ['%d:b' % frame for frame in range(3200, last_press, PRESS_SPACING)]
    shots = range(first, last + 1, PICTURE_SPACING)
    pokes = ['3100-5200:%x:%x' % (CHARACTER_ADDRESS, character)]
    for address, value in VITALITY_POKES:
        pokes.append('5300-%d:%x:%x' % (LAST_POKED_FRAME, address, value))
    environment = dict(os.environ, DYNAREC='1' if recompiler else '0', PRESS=';'.join(presses),
                       POKES=';'.join(pokes),
                       SHOTS=' '.join(map(str, shots)))
    os.makedirs(os.path.join(output, name), exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        subprocess.run([psxrun, core, cue, str(last + 1), work], env=environment,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for frame in shots:
            picture = Image.open(os.path.join(work, 'f%06d.ppm' % frame))
            picture.save(os.path.join(output, name, 'f%06d.png' % frame))
    print(name, len(shots), 'pictures')


def main():
    psxrun, core, cue, output = sys.argv[1:5]
    for name in ENDINGS:
        capture(psxrun, core, cue, name, output)


if __name__ == '__main__':
    main()
