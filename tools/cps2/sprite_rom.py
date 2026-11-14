"""Reading and writing 16x16 tiles in the sprite ROMs of a CPS2 set.

Four chips (`.13m`, `.15m`, `.17m`, `.19m`, 4 MB each) hold the first 16 MB of graphics,
tiles 0 to 0x1ffff. They are read together, two bytes from each in turn
(`ROM_LOAD64_WORD` in MAME), which gives 8-byte words; inside every 2 MB the words are
stored in a shuffled order (`unshuffle()` in MAME's `cps2_gfx_decode`). Once in order, a
tile is 128 bytes: 16 rows of 8 bytes, the left 8 pixels then the right 8, each as four
bytes of bit planes (weights 1, 2, 4, 8; the leftmost pixel is the high bit). Pen 15 is
transparent.
"""

TILE_SIZE = 16
TRANSPARENT_PEN = 15
WORD_BYTES = 8
WORDS_PER_TILE = 16
BANK_WORDS = 0x200000 // WORD_BYTES     # words in one 2 MB shuffled bank
CHIPS = 4
TILE_COUNT = 0x20000


def shuffled_word(index):
    """Where the word `index` of an unshuffled 2 MB bank is in the ROM.

    MAME's unshuffle() of a block unshuffles its two halves, then swaps the second
    quarter of the block with the third. So the word at a position comes from the left
    half for the first and third quarters and from the right half for the others."""
    block_start = 0
    block_size = BANK_WORDS
    position = index
    while block_size > 2:
        half = block_size // 2
        quarter = half // 2
        if position < quarter:
            pass                                    # left half, same position
        elif position < half:
            block_start += half                     # right half
            position -= quarter
        elif position < half + quarter:
            position -= quarter                     # left half
        else:
            block_start += half                     # right half
            position -= half
        block_size = half
    return block_start + position


class SpriteRoms:
    """the four chips of 16 MB of sprite ROM, as bytearrays in address order"""

    def __init__(self, chips):
        if len(chips) != CHIPS:
            raise ValueError('four chips are needed')
        self.chips = [bytearray(chip) for chip in chips]

    def _word_offset(self, tile, row):
        """offset, inside each chip, of the two bytes it holds of a tile row"""
        word = tile * WORDS_PER_TILE + row
        bank_start = word - word % BANK_WORDS
        return 2 * (bank_start + shuffled_word(word % BANK_WORDS))

    def read_tile(self, tile):
        """16 rows of 16 pens"""
        rows = []
        for row in range(TILE_SIZE):
            offset = self._word_offset(tile, row)
            row_bytes = b''.join(bytes(chip[offset:offset + 2]) for chip in self.chips)
            pens = []
            for half in (row_bytes[0:4], row_bytes[4:8]):
                for bit in range(7, -1, -1):
                    pens.append(sum(((half[plane] >> bit) & 1) << plane for plane in range(4)))
            rows.append(pens)
        return rows

    def write_tile(self, tile, rows):
        for row, pens in enumerate(rows):
            row_bytes = bytearray(WORD_BYTES)
            for x, pen in enumerate(pens):
                for plane in range(4):
                    if (pen >> plane) & 1:
                        row_bytes[4 * (x // 8) + plane] |= 0x80 >> (x % 8)
            offset = self._word_offset(tile, row)
            for index, chip in enumerate(self.chips):
                chip[offset:offset + 2] = row_bytes[2 * index:2 * index + 2]

    def is_blank(self, tile):
        return all(pen == TRANSPARENT_PEN for row in self.read_tile(tile) for pen in row)

    def read_block(self, tile, columns, rows):
        """The pens of a sprite of columns x rows tiles: the tile numbers go up by one
        along a row, staying in the same sixteen, and by 0x10 from a row to the next."""
        pens = [[] for _ in range(rows * TILE_SIZE)]
        for row in range(rows):
            for column in range(columns):
                code = (tile & ~0xf) + ((tile + column) & 0xf) + 0x10 * row
                for y, tile_row in enumerate(self.read_tile(code)):
                    pens[row * TILE_SIZE + y].extend(tile_row)
        return pens

    def write_block(self, tile, columns, rows, pens):
        for row in range(rows):
            for column in range(columns):
                code = (tile & ~0xf) + ((tile + column) & 0xf) + 0x10 * row
                self.write_tile(code, [line[column * TILE_SIZE:(column + 1) * TILE_SIZE]
                                       for line in pens[row * TILE_SIZE:(row + 1) * TILE_SIZE]])


def _raw_offset(byte_offset):
    """where an 8-byte word of the unshuffled graphics is, in each of the four chips"""
    word = byte_offset // WORD_BYTES
    bank_start = word - word % BANK_WORDS
    return 2 * (bank_start + shuffled_word(word % BANK_WORDS))


def read_raw(chips, byte_offset, length):
    """bytes of the graphics as MAME sees them once unshuffled (a 16x16 tile is 128 bytes,
    an 8x8 one 64, a 32x32 one 512), from four chips of 16 MB; offset and length are
    multiples of 8"""
    out = bytearray()
    for offset in range(byte_offset, byte_offset + length, WORD_BYTES):
        position = _raw_offset(offset)
        for chip in chips:
            out += chip[position:position + 2]
    return bytes(out)


def write_raw(chips, byte_offset, data):
    """the other way round: writes unshuffled bytes into four chips (bytearrays)"""
    for index in range(0, len(data), WORD_BYTES):
        position = _raw_offset(byte_offset + index)
        for chip_index, chip in enumerate(chips):
            chip[position:position + 2] = data[index + 2 * chip_index:index + 2 * chip_index + 2]
