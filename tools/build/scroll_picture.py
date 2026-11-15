"""A picture (an RGB image) as CPS2 scroll tiles: 32x32 tiles, 4 bits a pixel, with
palettes of 16 colours, as the pictures of the endings are (docs/endings.md).

The format of what comes out, checked against the pictures of Vampire Savior's endings:

- a tile is 512 bytes: 32 rows of 16 bytes; a row is four groups of 8 pixels, a group is
  four bytes, one for each bit of the pen (bit 0 first), the leftmost pixel in the top bit
  (`encode_tile`; the graphics ROM then shuffles these bytes: sprite_rom.write_raw);
- the tilemap of scroll 3 is made of words (tile code, attribute), four bytes an entry;
  the attribute has the palette in its low 5 bits and the flips in bits 5 (x) and 6 (y).
  Vampire Savior's tables list the entries of a block of 8x8 tiles one column after the
  other (entry n is column n // 8, row n % 8), as the hardware lays them out;
- a palette is 16 words, 0xfrgb: the top nibble the brightness (0xf: full), then four
  bits of red, green and blue; pen 15 of a scroll tile is transparent.

`convert` cuts a picture into cells of 32x32, gives the cells the fewest palettes it can
(each cell has at most 16 colours, the rarest being merged into the nearest if it has
more) and drops the tiles that repeat. `render` draws the result back, to look at it.
"""
from collections import Counter

TILE = 32
PENS = 16
TRANSPARENT_PEN = 15
MAX_PALETTES = 32                    # the palette is the low 5 bits of the attribute
FULL_BRIGHTNESS = 0xf000
FLIP_X, FLIP_Y = 0x20, 0x40


def to_nibbles(pixel):
    """the colour as the three 4-bit components the hardware has"""
    return tuple((component * 15 + 127) // 255 for component in pixel[:3])


def from_nibbles(colour):
    return tuple(component * 17 for component in colour)


def encode_tile(pens):
    """the rows of pens of a tile (32x32 or 16x16) -> its bytes (512 or 128)"""
    out = bytearray()
    for row in pens:
        for group in range(len(row) // 8):
            planes = [0, 0, 0, 0]
            for bit in range(8):
                pen = row[8 * group + bit]
                for plane in range(4):
                    planes[plane] |= ((pen >> plane) & 1) << (7 - bit)
            out += bytes(planes)
    return bytes(out)


def decode_tile(data, size=TILE):
    """the other way round: `size` rows of `size` pens"""
    rows = []
    stride = size // 2
    for y in range(size):
        row = []
        for group in range(size // 8):
            planes = data[stride * y + 4 * group:stride * y + 4 * group + 4]
            for bit in range(8):
                row.append(sum(((planes[plane] >> (7 - bit)) & 1) << plane for plane in range(4)))
        rows.append(row)
    return rows


def palette_word(colour):
    red, green, blue = colour
    return FULL_BRIGHTNESS | red << 8 | green << 4 | blue


def reduce_colours(counts, wanted):
    """counts ({colour: pixels}) with the rarest colours merged into the nearest until
    `wanted` are left: {colour: the colour that stands for it}"""
    stand_for = {colour: colour for colour in counts}
    live = dict(counts)
    while len(live) > wanted:
        rare = min(live, key=lambda colour: (live[colour], colour))
        near = min((other for other in live if other != rare),
                   key=lambda other: sum((a - b) ** 2 for a, b in zip(rare, other)))
        live[near] += live.pop(rare)
        for colour, target in stand_for.items():
            if target == rare:
                stand_for[colour] = near
    return stand_for


class Picture:
    """the result: palettes (lists of colours, each 16 at most), tiles (512 bytes each),
    cells (columns x rows of (tile, palette)), the size in cells"""

    def __init__(self, columns, rows, tile=TILE):
        self.tile = tile
        self.columns = columns
        self.rows = rows
        self.palettes = []
        self.tiles = []
        self.cells = [[None] * columns for _ in range(rows)]

    def palette_words(self):
        """each palette as 16 words (the unused pens black)"""
        return [[palette_word(colour) for colour in palette] + [palette_word((0, 0, 0))] * (PENS - len(palette))
                for palette in self.palettes]

    def tilemap(self, first_tile=0, first_palette=0, transparent_cell=None):
        """[(code, attribute)] column after column (the order of the hardware's map)"""
        entries = []
        for column in range(self.columns):
            for row in range(self.rows):
                cell = self.cells[row][column]
                if cell is None:
                    entries.append(transparent_cell)
                else:
                    tile, palette = cell
                    entries.append((first_tile + tile, first_palette + palette))
        return entries


def convert(image, transparent=None, max_palettes=MAX_PALETTES, tile=TILE):
    """image: a PIL image (any size; the cells at the right and bottom edge are padded with
    black). `transparent`: an RGB colour whose pixels become the transparent pen (15), or
    None. A cell that has only the transparent colour has no tile (its cell is None)."""
    image = image.convert('RGB')
    columns = (image.width + tile - 1) // tile
    rows = (image.height + tile - 1) // tile
    pixels = image.load()
    clear = to_nibbles(transparent) if transparent is not None else None
    limit = PENS - 1 if clear is not None else PENS

    # the colours of each cell (after reducing them to 16 at most)
    cells = {}
    for row in range(rows):
        for column in range(columns):
            grid = []
            for y in range(tile):
                line = []
                for x in range(tile):
                    px, py = column * tile + x, row * tile + y
                    line.append(to_nibbles(pixels[px, py]) if px < image.width and py < image.height else (0, 0, 0))
                grid.append(line)
            counts = Counter(colour for line in grid for colour in line if colour != clear)
            stand_for = reduce_colours(counts, limit)
            cells[row, column] = ([[colour if colour == clear else stand_for[colour] for colour in line]
                                   for line in grid], set(stand_for.values()))

    # the palettes: the cells with the most colours first, each into the palette it grows least
    palettes = []                           # sets of colours
    placed = {}
    for key in sorted(cells, key=lambda key: -len(cells[key][1])):
        colours = cells[key][1]
        best = None
        for index, palette in enumerate(palettes):
            growth = len(colours - palette)
            if len(palette) + growth <= limit and (best is None or growth < best[0]):
                best = (growth, index)
        if best is None:
            palettes.append(set())
            best = (0, len(palettes) - 1)
            if len(palettes) > max_palettes:
                raise SystemExit('scroll picture: needs more than %d palettes' % max_palettes)
        palettes[best[1]] |= colours
        placed[key] = best[1]

    picture = Picture(columns, rows, tile)
    index_of = []
    for palette in palettes:
        ordered = sorted(palette, key=lambda colour: (sum(colour), colour))
        if clear is not None:
            # the colours, then the transparent colour as pen 15
            ordered += [(0, 0, 0)] * (TRANSPARENT_PEN - len(ordered)) + [clear]
        picture.palettes.append(ordered)
        index_of.append({colour: pen for pen, colour in enumerate(ordered)
                         if pen != TRANSPARENT_PEN or clear is None})
    # tiles
    seen = {}
    for (row, column), (grid, colours) in sorted(cells.items()):
        palette = placed[row, column]
        pens = [[TRANSPARENT_PEN if colour == clear else index_of[palette][colour] for colour in line]
                for line in grid]
        if clear is not None and all(pen == TRANSPARENT_PEN for line in pens for pen in line):
            continue
        data = encode_tile(pens)
        key = (data, palette)
        if key not in seen:
            seen[key] = len(picture.tiles)
            picture.tiles.append(data)
        picture.cells[row][column] = (seen[key], palette)
    return picture


def render(picture, background=(0, 0, 0)):
    """the picture as a PIL image, from its tiles, palettes and cells"""
    from PIL import Image
    image = Image.new('RGB', (picture.columns * picture.tile, picture.rows * picture.tile), background)
    for row in range(picture.rows):
        for column in range(picture.columns):
            cell = picture.cells[row][column]
            if cell is None:
                continue
            tile, palette = cell
            colours = picture.palettes[palette]
            for y, line in enumerate(decode_tile(picture.tiles[tile], picture.tile)):
                for x, pen in enumerate(line):
                    if pen == TRANSPARENT_PEN and len(colours) == PENS:
                        continue
                    if pen < len(colours):
                        image.putpixel((column * picture.tile + x, row * picture.tile + y), from_nibbles(colours[pen]))
    return image


if __name__ == '__main__':
    import sys
    from PIL import Image
    if len(sys.argv) < 3:
        sys.exit('usage: scroll_picture.py PICTURE.png PREVIEW.png [R,G,B of the transparent colour]')
    clear = tuple(int(part) for part in sys.argv[3].split(',')) if len(sys.argv) > 3 else None
    result = convert(Image.open(sys.argv[1]), clear)
    print('%d x %d cells, %d tiles, %d palettes' % (result.columns, result.rows, len(result.tiles), len(result.palettes)))
    render(result).save(sys.argv[2])
