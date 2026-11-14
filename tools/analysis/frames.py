"""Drawing sprite frames (docs/roster.md) from the graphics ROMs, to look at them.

    frames.py GFX.npy PROGRAM_SET FRAME_ADDRESS[,FRAME_ADDRESS...] GFXRAM_DUMP OUT.png

GFX.npy is the unshuffled 32 MB of sprite ROM (tools/analysis/gfx.py), GFXRAM_DUMP the
0x900000-0x92ffff dump of tools/trace/drive.lua (for the palettes). Only frames of type 2
(sprites with their own attributes), drawn from sprite bank 1 like the select screen.
"""
import struct
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, __file__.rsplit('/', 2)[0])
from cps2 import program

TILE_BYTES = 128
PALETTE_OFFSET = 0xc000         # the sprite palettes in the graphics RAM dump
TRANSPARENT_PEN = 15


def tile_pens(gfx, tile):
    """a 16x16 array of pens"""
    data = np.asarray(gfx[tile * TILE_BYTES:(tile + 1) * TILE_BYTES]).reshape(16, 2, 4)
    bits = np.unpackbits(data, axis=2, bitorder='big').reshape(16, 2, 4, 8)
    pens = bits[:, :, 0, :] + 2 * bits[:, :, 1, :] + 4 * bits[:, :, 2, :] + 8 * bits[:, :, 3, :]
    return pens.reshape(16, 16)


def palette_colours(gfxram, palette):
    """the 16 RGB colours of a sprite palette (CPS format: brightness, red, green, blue nibbles)"""
    colours = []
    for pen in range(16):
        word = struct.unpack_from('>H', gfxram, PALETTE_OFFSET + 32 * palette + 2 * pen)[0]
        bright = 0x0f + ((word >> 12) << 1)
        colours.append(tuple(((word >> shift) & 15) * 0x11 * bright // 0x2d for shift in (8, 4, 0)))
    return colours


def read_frame(code, frame):
    """[(x, y, tile, attributes)] of a type 2 frame"""
    sprites = struct.unpack_from('>H', code, frame + 4)[0] + 1
    shape = struct.unpack_from('>I', code, frame + 6)[0]
    return [struct.unpack_from('>hh', code, shape + 4 * index)
            + struct.unpack_from('>HH', code, frame + 10 + 4 * index) for index in range(sprites)]


def draw_frame(image, gfx, gfxram, sprites, origin_x, origin_y, bank=1):
    for x, y, tile, attributes in sprites:
        columns = ((attributes >> 8) & 15) + 1
        rows = ((attributes >> 12) & 15) + 1
        colours = palette_colours(gfxram, attributes & 0x1f)
        flip_x = attributes & 0x20
        for row in range(rows):
            for column in range(columns):
                code = (tile & ~0xf) + ((tile + column) & 0xf) + 0x10 * row + bank * 0x10000
                pens = tile_pens(gfx, code)
                if flip_x:
                    pens = pens[:, ::-1]
                left = origin_x + x + 16 * (columns - 1 - column if flip_x else column)
                top = origin_y + y + 16 * row
                for pixel_y in range(16):
                    for pixel_x in range(16):
                        pen = pens[pixel_y, pixel_x]
                        if pen != TRANSPARENT_PEN:
                            image.putpixel((left + pixel_x, top + pixel_y), colours[pen])


def main():
    gfx = np.load(sys.argv[1], mmap_mode='r')
    code = program.load_program(sys.argv[2])
    frames = [int(text, 16) for text in sys.argv[3].split(',')]
    gfxram = open(sys.argv[4], 'rb').read()
    image = Image.new('RGB', (256 * len(frames), 192), (40, 40, 60))
    for index, frame in enumerate(frames):
        draw_frame(image, gfx, gfxram, read_frame(code, frame), 256 * index + 128, 176)
    image.resize((image.width * 3, image.height * 3), Image.NEAREST).save(sys.argv[5])


if __name__ == '__main__':
    main()
