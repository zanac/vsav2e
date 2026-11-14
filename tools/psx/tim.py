"""Reading PlayStation TIM images (the texture format of the PS1 SDK).

A TIM file is:
    u32 magic        0x00000010
    u32 flags        bits 0-2 pixel mode (0 = 4 bpp, 1 = 8 bpp, 2 = 15 bpp, 3 = 24 bpp),
                     bit 3 a colour lookup table (palette) follows
    [CLUT block]     u32 block size, u16 x, u16 y, u16 colours per row, u16 rows,
                     then the 15-bit colours
    image block      u32 block size, u16 x, u16 y, u16 width in 16-bit units, u16 height,
                     then the pixels

Colours are 15-bit BGR (bit 15 is the semi-transparency flag); colour 0x0000 is drawn as
transparent by the GPU.
"""
import struct

TIM_MAGIC = 0x10
BITS_PER_PIXEL = {0: 4, 1: 8, 2: 16, 3: 24}


def bgr555_to_rgba(colour):
    red = (colour & 0x1f) << 3
    green = ((colour >> 5) & 0x1f) << 3
    blue = ((colour >> 10) & 0x1f) << 3
    alpha = 0 if colour == 0 else 255
    return (red, green, blue, alpha)


class Tim:
    """one decoded TIM: its palettes, its size and its pixels (palette indexes, or
    colours for the 16 and 24 bpp modes)"""

    def __init__(self, data, offset=0):
        magic, flags = struct.unpack_from('<II', data, offset)
        if magic != TIM_MAGIC or (flags & ~0xf) or (flags & 7) not in BITS_PER_PIXEL:
            raise ValueError('not a TIM')
        self.bits_per_pixel = BITS_PER_PIXEL[flags & 7]
        position = offset + 8
        self.palettes = []
        if flags & 8:
            block_size, _, _, colours_per_row, rows = struct.unpack_from('<IHHHH', data, position)
            colours = struct.unpack_from('<%dH' % (colours_per_row * rows), data, position + 12)
            self.palettes = [colours[row * colours_per_row:(row + 1) * colours_per_row]
                             for row in range(rows)]
            position += block_size
        block_size, self.vram_x, self.vram_y, width_units, self.height = \
            struct.unpack_from('<IHHHH', data, position)
        if block_size != 12 + width_units * 2 * self.height or self.height == 0:
            raise ValueError('bad image block')
        self.width = width_units * 16 // self.bits_per_pixel
        self.pixel_bytes = data[position + 12:position + block_size]
        self.size = position + block_size - offset   # bytes the TIM takes in the file

    def pixel_indexes(self):
        """rows of palette indexes (4 and 8 bpp)"""
        rows = []
        stride = len(self.pixel_bytes) // self.height
        for y in range(self.height):
            line = self.pixel_bytes[y * stride:(y + 1) * stride]
            if self.bits_per_pixel == 4:
                rows.append([value for byte in line for value in (byte & 15, byte >> 4)])
            else:
                rows.append(list(line))
        return rows

    def to_rgba_rows(self, palette_number=0):
        """rows of (r, g, b, a) tuples"""
        if self.bits_per_pixel in (4, 8):
            palette = [bgr555_to_rgba(c) for c in self.palettes[palette_number]] \
                if self.palettes else [(v * 17, v * 17, v * 17, 255) for v in range(256)]
            return [[palette[i] if i < len(palette) else (0, 0, 0, 0) for i in row]
                    for row in self.pixel_indexes()]
        stride = len(self.pixel_bytes) // self.height
        if self.bits_per_pixel == 16:
            return [[bgr555_to_rgba(struct.unpack_from('<H', self.pixel_bytes, y * stride + 2 * x)[0])
                     for x in range(self.width)] for y in range(self.height)]
        return [[tuple(self.pixel_bytes[y * stride + 3 * x:y * stride + 3 * x + 3]) + (255,)
                 for x in range(self.width)] for y in range(self.height)]


def find_tims(data):
    """every TIM inside a block of data: [(offset, Tim)]"""
    found = []
    position = 0
    while True:
        position = data.find(b'\x10\x00\x00\x00', position)
        if position < 0 or position + 20 > len(data):
            return found
        try:
            tim = Tim(data, position)
            found.append((position, tim))
            position += tim.size
        except (ValueError, struct.error):
            position += 4
