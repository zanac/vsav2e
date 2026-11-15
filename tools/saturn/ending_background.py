#!/usr/bin/env python3
"""ending_background.py: the picture window of the Sega Saturn ending screen without the sprites.

    ending_background.py DUMP_DIRECTORY SCREENSHOT.ppm FRAME BANKS OUTPUT.png [window x0,y0,x1,y1]

The backgrounds of the endings (the hell and the galaxy of Pyron, the arm of Donovan) are
Saturn VDP2 layers, which `ending_layers.py` does not draw. This takes them from a screenshot of
the emulator instead: the pixels of the window (64,24)-(288,152) that the sprites of the colour
banks BANKS (hexadecimal, comma separated; `ending_layers.py` lists the same names) do not
cover, made opaque (black as well), in a 352 x 240 RGBA picture like the other layers. The
pixels under the sprites are transparent, and a pixel next to a sprite is dropped too (the edge
of a sprite is mixed with what is under it).
"""
import os
import sys

from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ending_layers


def background(dump_directory, screenshot, frame, banks, window=(64, 24, 288, 152)):
    shot = Image.open(screenshot).convert('RGB')
    covered = ending_layers.layer(dump_directory, frame, banks).split()[3].filter(ImageFilter.MaxFilter(3))
    out = Image.new('RGBA', shot.size, (0, 0, 0, 0))
    mask, source, target = covered.load(), shot.load(), out.load()
    for y in range(window[1], window[3]):
        for x in range(window[0], window[2]):
            if mask[x, y] == 0:
                target[x, y] = source[x, y] + (255,)
    return out


def main():
    if len(sys.argv) < 6:
        sys.exit(__doc__)
    dump_directory, screenshot, frame, banks, output = sys.argv[1:6]
    window = tuple(int(v) for v in sys.argv[6].split(',')) if len(sys.argv) > 6 else (64, 24, 288, 152)
    background(dump_directory, screenshot, int(frame), [int(b, 16) for b in banks.split(',')], window).save(output)


if __name__ == '__main__':
    main()
