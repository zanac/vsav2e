#!/usr/bin/env python3
"""Captures the character select screen of the PlayStation Darkstalkers 3 for every one
of the 18 characters (big portrait, name, wheel), as PNGs for the vsav2e select screen.

The game is driven by tools/psx/psxrun with fixed pad inputs; the emulator is
deterministic, so the same inputs always land on the same characters. Each session goes
title -> ARCADE -> select screen, then moves the cursor; a picture is taken once the
portrait has slid in.

usage: capture_select.py psxrun pcsx_rearmed_libretro.so disc.cue output_directory
"""
import os, subprocess, sys, tempfile
from PIL import Image

# reaching the select screen: START on the title, START again, cross on ARCADE
BOOT_PRESSES = ['2600:start', '2800:start', '3000:b']

# (moves, first move frame, frames between moves, offset of the picture after each move,
#  characters seen at each picture (None = skip)); the first picture is taken just
#  before the first move
SESSIONS = [
    (['up'] * 3, 3800, 80, 70, ['demitri', 'victor', 'felicia', 'jedah']),
    (['left'] * 6, 3800, 80, 70, [None, 'morrigan', 'sasquatch', 'lilith', 'hsien-ko',
                                  'bb-hood', 'anakaris']),
    (['down'] * 3, 3800, 80, 70, [None, None, 'bishamon', 'huitzil']),
    (['right'] * 6, 3800, 80, 70, [None, None, None, 'q-bee', None, 'lord-raptor', None]),
    (['down'] * 3 + ['right'] * 4, 3800, 80, 70, [None, None, None, None, None, 'donovan',
                                                   'rikuo', None]),
]
# two characters the paths above never stop on: the moves of these sessions are
# timed differently (fast downs, then rights), with the picture 25 frames after a move
FAST_SESSIONS = [
    (3, 'jon-talbain', 1),      # 3 downs, then the picture after the 1st right
    (4, 'pyron', 0),            # 4 downs, the picture before the first right
]


def run(psxrun, core, cue, presses, shots, total_frames, directory):
    environment = dict(os.environ, DYNAREC='1', PRESS=';'.join(presses),
                       SHOTS=' '.join(map(str, shots)))
    subprocess.run([psxrun, core, cue, str(total_frames), directory], env=environment,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def save(directory, frame, name, output):
    picture = Image.open(os.path.join(directory, 'f%06d.ppm' % frame))
    picture.save(os.path.join(output, name + '.png'))
    print(name)


def main():
    psxrun, core, cue, output = sys.argv[1:5]
    os.makedirs(output, exist_ok=True)
    for moves, first, spacing, delay, names in SESSIONS:
        with tempfile.TemporaryDirectory() as work:
            presses = list(BOOT_PRESSES)
            shots = [first - 10]
            for index, move in enumerate(moves):
                frame = first + spacing * index
                presses.append('%d:%s' % (frame, move))
                shots.append(frame + delay)
            run(psxrun, core, cue, presses, shots, shots[-1] + 1, work)
            for frame, name in zip(shots, names):
                if name:
                    save(work, frame, name, output)
    for downs, name, rights_before_picture in FAST_SESSIONS:
        with tempfile.TemporaryDirectory() as work:
            presses = list(BOOT_PRESSES)
            frame = 3700
            for _ in range(downs):
                presses.append('%d:down' % frame)
                frame += 30
            frame += 40
            picture = frame - 10
            for index in range(rights_before_picture):
                presses.append('%d:right' % frame)
                picture = frame + 25
                frame += 40
            run(psxrun, core, cue, presses, [picture], picture + 1, work)
            save(work, picture, name, output)


if __name__ == '__main__':
    main()
