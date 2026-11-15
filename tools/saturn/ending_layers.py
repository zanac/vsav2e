#!/usr/bin/env python3
"""ending_layers.py: pictures of an ending of the Sega Saturn Vampire Savior, one layer each.

    ending_layers.py DUMP_DIRECTORY OUTPUT_DIRECTORY NAME=FRAME:BANK[,BANK...] ...

DUMP_DIRECTORY holds what satrun's VDUMPS writes (vdp1vram_NNNNNN.bin, vdp2cram_NNNNNN.bin, see
docs/saturn.md). Each NAME=FRAME:BANKS draws the sprites of the colour banks (hexadecimal, as
`vdp1render.py` lists them: 7040) of that frame into OUTPUT_DIRECTORY/NAME.png, a 352 x 240 picture
with a transparent background: the screen of the Saturn, so every layer has the coordinates of
the game, and the layers can be put together again. Example (Donovan's ending, docs/endings.md):

    ending_layers.py vdump/donovan assets/saturn/donovan asleep=1260:7040,7030 blade=1260:7020
"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vdp1render


def layer(dump_directory, frame, banks):
    """the sprites of `banks` at `frame` as an RGBA picture"""
    def read(name):
        return open(os.path.join(dump_directory, '%s_%06d.bin' % (name, frame)), 'rb').read()
    pixels = vdp1render.render(read('vdp1vram'), read('vdp2cram'), only_banks=banks)
    image = Image.new('RGBA', (len(pixels[0]), len(pixels)), (0, 0, 0, 0))
    for y, row in enumerate(pixels):
        for x, colour in enumerate(row):
            if colour:
                image.putpixel((x, y), colour + (255,))
    return image


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    dump_directory, output = sys.argv[1:3]
    os.makedirs(output, exist_ok=True)
    for argument in sys.argv[3:]:
        name, wanted = argument.split('=')
        frame, banks = wanted.split(':')
        layer(dump_directory, int(frame), [int(bank, 16) for bank in banks.split(',')]).save(
            os.path.join(output, name + '.png'))


if __name__ == '__main__':
    main()
