"""The character select screen with all 18 characters.

Vampire Savior 2 shows 16 cells (15 characters and the random choice) on a tombstone; the
PlayStation Darkstalkers 3 has the same screen with 19: three more cells at the bottom
and some characters moved. vsav2e follows the PlayStation layout:

    Jedah                  .  .  .  J  .  .  .         J  Jedah     Q  Q-Bee
    Felicia, Talbain       .  .  F  .  T  .  .         F  Felicia   T  Jon Talbain
    Victor, Q-Bee, Zabel   .  V  .  Q  .  Z  .         V  Victor    Z  Zabel (Lord Raptor)
    Demitri ... Morrigan   D  .  B  .  L  .  M         D  Demitri   B  Bulleta (B.B. Hood)
    Anakaris ... Sasquatch .  A  .  H  .  S  .         L  Lilith    M  Morrigan
    Bishamon, Rikuo        .  .  b  .  R  .  .         A  Anakaris  H  Hsien-Ko
    Pyron                  .  .  .  P  .  .  .         S  Sasquatch b  Bishamon
    Huitzil, Donovan       .  .  h  .  d  .  .         R  Rikuo     P  Pyron
    random                 .  .  .  ?  .  .  .         h  Huitzil   d  Donovan

How the screen is made, and what changes:

- The tombstone is a scroll layer with 16 empty cells. The three new cells are drawn over
  it by one sprite, 6 x 3 tiles, whose picture comes from the PlayStation screen (same
  drawing, other colours: the colours are converted with a table).
- The faces are sprites: one frame (docs/roster.md) holds them all, each face with its
  own palette. vsav2e has a new frame in the program extension, so it is drawn from the
  upper sprite bank, where the faces of Jon Talbain, Rikuo and Sasquatch still are
  (Vampire Hunter 2's frame has them) and where the new tiles are written, in tiles that
  are empty.
- A face that moves to another cell does not fit it exactly; the PlayStation game trimmed
  them. The same pixels are trimmed here: a pixel of a moved face is kept when the
  PlayStation screen shows it. The trimmed faces are new tiles.
- Palettes: the screen loads 32 sprite palettes from one block. Three are free for the
  three faces: 0x16 and 0x19 are never used, 0x1d was the pink filling of three cells,
  which the new layout does not have. (0x17 and 0x1a look unused but take the second
  palette of the characters of players 1 and 2.) The new cells take palette 2, which no
  sprite of this screen uses; its colours in the block are read by other code, so they
  are left alone and the new ones are written over them once the block is loaded.
- The cursors: for each character id, a position (table at 0x6bc78) and three frames
  (player 1, player 2 and a third one), in three tables of 32 frame pointers. The new
  cells have the shape of the cells 29 pixels above them, so they use their frames.
- Moving the cursor: a table gives, for each character id and each of the 8 directions,
  the id the cursor goes to. It is made again from where the cells are.
- The random choice runs through a list of ids, now 18 long.
"""
import glob
import os
import struct

from build import png

# --- character ids -------------------------------------------------------------------

BULLETA, DEMITRI, TALBAIN, VICTOR, ZABEL, MORRIGAN, ANAKARIS, FELICIA = range(0x00, 0x08)
BISHAMON, RIKUO, SASQUATCH, RANDOM, QBEE, HSIENKO, LILITH, JEDAH = range(0x08, 0x10)
HUITZIL, PYRON, DONOVAN = 0x10, 0x11, 0x13
ADDED_CHARACTERS = (TALBAIN, RIKUO, SASQUATCH)

# --- the screen in the program of Vampire Savior 2 -----------------------------------

ICON_FRAME_POINTER = 0x2a17ba           # the frame with all the faces
ICON_FRAME = 0x2a6e52
HUNTER_ICON_FRAME = 0x2932d0            # the one of Vampire Hunter 2
CURSOR_FRAME_TABLES = (0x2a17be, 0x2a183e, 0x2a18be)
CURSOR_FRAME_TABLE_ENTRIES = 32
CURSOR_POSITION_TABLE = 0x6bc78         # for each id: x, y (words; y goes up)
NAVIGATION_TABLE = 0x1588e              # for each id: 8 ids, see DIRECTIONS
SELECT_PALETTES = 0x3baf3c              # 32 sprite palettes of 16 words
HUNTER_SELECT_PALETTES = 0x39af10
PALETTE_BYTES = 32

# the random choice: `cmpi.b #15, d0` then `move.b table(pc, d0.w), $382(a6)`
RANDOM_COUNT_ADDRESS = 0x1f8a0
RANDOM_COUNT_ORIGINAL = bytes.fromhex('0c00000f')
RANDOM_READ_ADDRESS = 0x1f8ac
RANDOM_READ_ORIGINAL = bytes.fromhex('1d7b00060382')
RANDOM_TABLE = 0x1f8b4
RANDOM_TABLE_LENGTH = 15

# The sprite palettes of a scene are a block of 32, loaded by two routines that end with
#     lea $90c000.l, a1         the sprite palettes
#     bra.w $1ae12              copy 32 palettes from a0 to a1
# The select screen's block is SELECT_PALETTES.
PALETTE_LOAD_ADDRESSES = (0x1ac9c, 0x1aeb6)
PALETTE_LOAD_ORIGINAL = bytes.fromhex('43f90090c000')
PALETTE_LOAD_ROUTINE = 0x1ae12
SPRITE_PALETTES = 0x90c000

# the origin of the faces' frame on the screen, and the screen in a PlayStation capture
FRAME_ORIGIN_X, FRAME_ORIGIN_Y = 192, 160
CAPTURE_OFFSET_X, CAPTURE_OFFSET_Y = -8, 8      # capture x = screen x - 8, y = screen y + 8

# --- the new layout ------------------------------------------------------------------

# In the frame of Vampire Savior 2 every face has its own palette: this is how its
# sprites are told apart. Palette 0x1d is the pink filling of three cells, not used in
# the new layout.
PALETTE_CHARACTER = {0x05: DONOVAN, 0x06: DEMITRI, 0x07: QBEE, 0x08: VICTOR, 0x09: ZABEL, 0x0a: MORRIGAN,
                     0x0b: ANAKARIS, 0x0c: FELICIA, 0x0d: BISHAMON, 0x0e: LILITH, 0x0f: BULLETA,
                     0x10: RANDOM, 0x11: PYRON, 0x12: HSIENKO, 0x13: HUITZIL, 0x14: JEDAH}
CELL_FILLING_PALETTE = 0x1d
# the three faces taken from Vampire Hunter 2's frame: palette there -> (id, free palette)
HUNTER_FACES = {0x07: (TALBAIN, 0x16), 0x0e: (RIKUO, 0x19), 0x0f: (SASQUATCH, 0x1d)}
NEW_CELLS_PALETTE = 0x02

# the faces that change cell, and by how many pixels (measured on the PlayStation screen)
MOVED_FACES = {QBEE: (-31, 17), LILITH: (3, -30), BULLETA: (-83, -14), PYRON: (0, 61),
               HUITZIL: (-52, 59), DONOVAN: (53, 58), RANDOM: (1, 29)}
# The order the faces are drawn in, the last one over the others where they touch.
# Pyron comes first: the faces of the cells next to his go over him.
DRAW_ORDER = (PYRON, HSIENKO, JEDAH, FELICIA, DEMITRI, VICTOR, ZABEL, MORRIGAN, ANAKARIS, BISHAMON, LILITH,
              QBEE, BULLETA, RANDOM, HUITZIL, DONOVAN, TALBAIN, RIKUO, SASQUATCH)

# The cursor of a character: the position and the frames another id had, moved down for
# the three new cells (which have the shape of the cells above them).
NEW_CELL_DROP = 29
CURSOR_SOURCE = {QBEE: (PYRON, 0), LILITH: (HUITZIL, 0), BULLETA: (DONOVAN, 0), PYRON: (RANDOM, 0),
                 HUITZIL: (BISHAMON, NEW_CELL_DROP), DONOVAN: (LILITH, NEW_CELL_DROP),
                 RANDOM: (RANDOM, NEW_CELL_DROP),
                 TALBAIN: (QBEE, 0), RIKUO: (LILITH, 0), SASQUATCH: (BULLETA, 0)}

# The cells: (column, x, y of the centre on the screen), for the cursor moves.
CELLS = {
    DEMITRI: (1, 108, 103),
    VICTOR: (2, 132, 88), ANAKARIS: (2, 138, 118),
    FELICIA: (3, 160, 72), BULLETA: (3, 163, 104), BISHAMON: (3, 166, 133), HUITZIL: (3, 166, 162),
    JEDAH: (4, 192, 58), QBEE: (4, 192, 89), HSIENKO: (4, 192, 119), PYRON: (4, 192, 147), RANDOM: (4, 192, 176),
    TALBAIN: (5, 223, 72), LILITH: (5, 220, 104), RIKUO: (5, 217, 133), DONOVAN: (5, 217, 162),
    ZABEL: (6, 251, 88), SASQUATCH: (6, 245, 118),
    MORRIGAN: (7, 275, 103),
}
CENTRE_COLUMN = 4
# the eight directions of the table, as (horizontal, vertical) steps
DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1))
NEIGHBOUR_MAXIMUM_DISTANCE = 40         # how far up or down the cell of the next column may be
SAME_ROW_DISTANCE = 24                  # for going round from one side to the other

# The new cells: a rectangle of the screen, in whole tiles.
NEW_CELLS_X, NEW_CELLS_Y = 144, 144
NEW_CELLS_COLUMNS, NEW_CELLS_ROWS = 6, 3
# PlayStation colour of the tombstone -> the arcade's (4 bits each of red, green, blue)
TOMBSTONE_COLOURS = {
    (0x30, 0x00, 0x10): 0x032, (0x50, 0x20, 0x30): 0x254, (0x60, 0x30, 0x40): 0x365,
    (0x70, 0x30, 0x40): 0x376, (0x70, 0x30, 0x50): 0x375, (0x80, 0x40, 0x60): 0x486,
    (0x90, 0x50, 0x70): 0x597, (0xa0, 0x50, 0x80): 0x5a8, (0xc0, 0x50, 0x90): 0x5a7,
    (0xd0, 0x50, 0xa0): 0x6b7, (0xf0, 0x60, 0xc0): 0x6c7,
    (0x40, 0x40, 0x90): 0x7d7,      # the shaded edge of a cell
    (0x70, 0x60, 0xf0): 0xaf7,      # the inside of a cell
}
CELL_INSIDE_COLOUR = 0xaf7

# Where the new tiles go: empty tiles of the upper bank, 16 to a row.
NEW_TILES_START = 0x1fc00
NEW_TILES_END = 0x20000
SPRITE_BANK = 0x10000                   # the faces are drawn from sprite bank 1
TILE_SIZE = 16
TRANSPARENT_PEN = 15


def read_word(data, address):
    return struct.unpack_from('>H', data, address)[0]


def read_long(data, address):
    return struct.unpack_from('>I', data, address)[0]


def read_frame(program, frame):
    """[(x, y, tile, attributes)] of a frame of sprites with their own attributes"""
    if read_word(program, frame) != 2:
        raise SystemExit('select screen: 0x%x is not a frame of sprites' % frame)
    sprites = read_word(program, frame + 4) + 1
    shape = read_long(program, frame + 6)
    return [struct.unpack_from('>hh', program, shape + 4 * index)
            + struct.unpack_from('>HH', program, frame + 10 + 4 * index) for index in range(sprites)]


def sprite_size(attributes):
    """(columns, rows) of tiles"""
    return ((attributes >> 8) & 15) + 1, ((attributes >> 12) & 15) + 1


# --- the PlayStation screen ----------------------------------------------------------

class PlayStationScreen:
    """The select screen of the PlayStation game without its cursor: for each pixel, the
    colour most of the captures have (each capture has the cursor on another cell)."""

    def __init__(self, captures_directory):
        paths = sorted(glob.glob(os.path.join(captures_directory, '*.png')))
        if len(paths) < 3:
            raise SystemExit('select screen: the PlayStation captures are missing from %s' % captures_directory)
        self.captures = [png.read(path)[2] for path in paths]
        self.cache = {}

    def colour(self, screen_x, screen_y):
        """the colour at a place of the arcade screen"""
        key = (screen_x, screen_y)
        if key not in self.cache:
            x, y = screen_x + CAPTURE_OFFSET_X, screen_y + CAPTURE_OFFSET_Y
            count = {}
            for capture in self.captures:
                count[capture[y][x]] = count.get(capture[y][x], 0) + 1
            self.cache[key] = max(count, key=count.get)
        return self.cache[key]


# --- new tiles -----------------------------------------------------------------------

class TileAllocator:
    """Gives out blocks of the empty tiles. A sprite of several tiles needs them side by
    side in one row of 16 and in the rows below, so blocks are laid on shelves."""

    def __init__(self, sprite_roms):
        self.sprite_roms = sprite_roms
        self.shelf_tile = NEW_TILES_START
        self.shelf_rows = 0
        self.column = 0

    def allocate(self, columns, rows):
        if self.column + columns > 16:
            self.shelf_tile += 0x10 * self.shelf_rows
            self.shelf_rows = 0
            self.column = 0
        tile = self.shelf_tile + self.column
        self.column += columns
        self.shelf_rows = max(self.shelf_rows, rows)
        if tile + 0x10 * (rows - 1) + columns > NEW_TILES_END:
            raise SystemExit('select screen: no empty tiles left')
        for row in range(rows):
            for column in range(columns):
                if not self.sprite_roms.is_blank(tile + 0x10 * row + column):
                    raise SystemExit('select screen: tile 0x%x is not empty' % (tile + 0x10 * row + column))
        return tile


def trimmed_face(sprite_roms, screen, sprite, screen_x, screen_y):
    """The pens of a face sprite at its new place, without the pixels the PlayStation
    screen does not show: for each pen, the colour most of its pixels have there is the
    colour of that pen, and the pixels of another colour are cut."""
    _, _, tile, attributes = sprite
    columns, rows = sprite_size(attributes)
    pens = sprite_roms.read_block(SPRITE_BANK + tile, columns, rows)
    colours_of_pen = {}
    for y, line in enumerate(pens):
        for x, pen in enumerate(line):
            if pen != TRANSPARENT_PEN:
                colour = screen.colour(screen_x + x, screen_y + y)
                count = colours_of_pen.setdefault(pen, {})
                count[colour] = count.get(colour, 0) + 1
    colour_of_pen = {pen: max(count, key=count.get) for pen, count in colours_of_pen.items()}
    return [[pen if pen != TRANSPARENT_PEN and screen.colour(screen_x + x, screen_y + y) == colour_of_pen[pen]
             else TRANSPARENT_PEN for x, pen in enumerate(line)] for y, line in enumerate(pens)]


def new_cells_picture(screen):
    """(pens, palette words) of the rectangle with the three new cells. What is not a
    colour of the tombstone is a face: there the cell is filled with its inside colour."""
    colours = sorted(set(TOMBSTONE_COLOURS.values()))
    if len(colours) > TRANSPARENT_PEN:
        raise SystemExit('select screen: too many colours in the new cells')
    pen_of_colour = {colour: pen for pen, colour in enumerate(colours)}
    pens = [[pen_of_colour[TOMBSTONE_COLOURS.get(screen.colour(NEW_CELLS_X + x, NEW_CELLS_Y + y), CELL_INSIDE_COLOUR)]
             for x in range(NEW_CELLS_COLUMNS * TILE_SIZE)] for y in range(NEW_CELLS_ROWS * TILE_SIZE)]
    palette = colours + [0] * (16 - len(colours))
    palette[15] = NEW_CELLS_PALETTE         # like the game's palettes: the last word is the number
    return pens, palette


# --- the frame of the faces ----------------------------------------------------------

def build_icon_frame(vsav2e, hunter, extension, sprite_roms, screen):
    """Writes the new tiles and the new frame, and makes the screen use it."""
    allocator = TileAllocator(sprite_roms)
    sprites = []            # (x, y, tile, attributes), the first one drawn first

    cells_pens, cells_palette = new_cells_picture(screen)
    cells_tile = allocator.allocate(NEW_CELLS_COLUMNS, NEW_CELLS_ROWS)
    sprite_roms.write_block(cells_tile, NEW_CELLS_COLUMNS, NEW_CELLS_ROWS, cells_pens)
    sprites.append((NEW_CELLS_X - FRAME_ORIGIN_X, NEW_CELLS_Y - FRAME_ORIGIN_Y, cells_tile & 0xffff,
                    (NEW_CELLS_ROWS - 1) << 12 | (NEW_CELLS_COLUMNS - 1) << 8 | NEW_CELLS_PALETTE))

    faces = {}              # character id -> its sprites
    for sprite in read_frame(vsav2e, ICON_FRAME):
        x, y, tile, attributes = sprite
        palette = attributes & 0x1f
        if palette == CELL_FILLING_PALETTE:
            continue
        character = PALETTE_CHARACTER[palette]
        if character in MOVED_FACES:
            if attributes & 0x60:
                raise SystemExit('select screen: a flipped face sprite is not expected')
            move_x, move_y = MOVED_FACES[character]
            x, y = x + move_x, y + move_y
            columns, rows = sprite_size(attributes)
            pens = trimmed_face(sprite_roms, screen, sprite, FRAME_ORIGIN_X + x, FRAME_ORIGIN_Y + y)
            new_tile = allocator.allocate(columns, rows)
            sprite_roms.write_block(new_tile, columns, rows, pens)
            tile = new_tile & 0xffff
        faces.setdefault(character, []).append((x, y, tile, attributes))
    for x, y, tile, attributes in read_frame(hunter, HUNTER_ICON_FRAME):
        if attributes & 0x1f in HUNTER_FACES and attributes & 0x1f != CELL_FILLING_PALETTE:
            character, palette = HUNTER_FACES[attributes & 0x1f]
            faces.setdefault(character, []).append((x, y, tile, (attributes & ~0x1f) | palette))
    missing = [character for character in CELLS if character not in faces]
    if missing:
        raise SystemExit('select screen: no face for the ids %s' % missing)
    for character in DRAW_ORDER:
        sprites.extend(faces[character])

    shape = extension.add(b''.join(struct.pack('>hh', x, y) for x, y, _, _ in sprites))
    room = sum(columns * rows for columns, rows in (sprite_size(attributes) for _, _, _, attributes in sprites))
    frame = extension.add(struct.pack('>HHHI', 2, room, len(sprites) - 1, shape)
                          + b''.join(struct.pack('>HH', tile, attributes) for _, _, tile, attributes in sprites))
    if read_long(vsav2e, ICON_FRAME_POINTER) != ICON_FRAME:
        raise SystemExit('select screen: unexpected frame of the faces')
    struct.pack_into('>I', vsav2e, ICON_FRAME_POINTER, frame)

    # palettes: the three faces of Vampire Hunter 2 and the new cells
    for hunter_palette, (_, palette) in HUNTER_FACES.items():
        source = HUNTER_SELECT_PALETTES + PALETTE_BYTES * hunter_palette
        colours = bytearray(hunter[source:source + PALETTE_BYTES])
        struct.pack_into('>H', colours, PALETTE_BYTES - 2, palette)
        vsav2e[SELECT_PALETTES + PALETTE_BYTES * palette:SELECT_PALETTES + PALETTE_BYTES * (palette + 1)] = colours
    return len(sprites), allocator.shelf_tile + 0x10 * allocator.shelf_rows, cells_palette


def load_new_cells_palette(vsav2e, palette, free_space_start, free_space_end):
    """The palette of the new cells is not in the block the screen loads: a routine
    writes it over palette 2 after the block. Returns the first free address."""
    routine = bytes.fromhex(
        '43f9' + '%08x' % SPRITE_PALETTES +         # lea     the sprite palettes, a1
        'b1fc' + '%08x' % SELECT_PALETTES +         # cmpa.l  #the block of the select screen, a0
        '6706'                                      # beq.s   select_screen
        '4ef9' + '%08x' % PALETTE_LOAD_ROUTINE +    # jmp     load the 32 palettes
        # select_screen:
        '4eb9' + '%08x' % PALETTE_LOAD_ROUTINE +    # jsr     load the 32 palettes
        '43f9' + '%08x' % (SPRITE_PALETTES + PALETTE_BYTES * NEW_CELLS_PALETTE) +   # lea the cells' palette, a1
        '41fa0012'      # lea     colours(pc), a0
        '7e0f'          # moveq   #15, d7
        '3018'          # move.w  (a0)+, d0
        '0040f000'      # ori.w   #$f000, d0         full brightness, like the routine does
        '32c0'          # move.w  d0, (a1)+
        '51cffff6'      # dbra    d7, the move.w
        '4e75')         # rts
    address = free_space_start + (free_space_start & 1)
    end = address + len(routine) + PALETTE_BYTES
    if end > free_space_end:
        raise SystemExit('select screen: no room for the palette routine')
    vsav2e[address:end] = routine + struct.pack('>16H', *palette)
    for load_address in PALETTE_LOAD_ADDRESSES:
        if vsav2e[load_address:load_address + 6] != PALETTE_LOAD_ORIGINAL:
            raise SystemExit('select screen: unexpected code at the palette load 0x%x' % load_address)
        vsav2e[load_address:load_address + 6] = b'\x4e\xf9' + struct.pack('>I', address)     # jmp routine
    return end


# --- the cursor ----------------------------------------------------------------------

def move_cursors(vsav2e):
    """the position and the three frames of the cursor, for the ids that changed cell"""
    positions = {character: struct.unpack_from('>HH', vsav2e, CURSOR_POSITION_TABLE + 4 * character)
                 for character in range(CURSOR_FRAME_TABLE_ENTRIES)}
    frames = [{character: read_long(vsav2e, table + 4 * character)
               for character in range(CURSOR_FRAME_TABLE_ENTRIES)} for table in CURSOR_FRAME_TABLES]
    for character, (source, drop) in CURSOR_SOURCE.items():
        x, y = positions[source]
        if (x, y) == (0, 0):
            raise SystemExit('select screen: no cursor position for id 0x%x' % source)
        struct.pack_into('>HH', vsav2e, CURSOR_POSITION_TABLE + 4 * character, x, y - drop)
        for table, table_frames in zip(CURSOR_FRAME_TABLES, frames):
            struct.pack_into('>I', vsav2e, table + 4 * character, table_frames[source])


def cursor_target(character, horizontal, vertical):
    """The id the cursor goes to from a cell.

    Up and down follow the column; from its end they go to the next column towards the
    centre. Left and right go to the next column, to the cell just below (or just above
    when the direction is a diagonal upwards or there is none below); from the side of
    the picture they go round to the other side of the same row."""
    column, x, y = CELLS[character]

    def nearest(candidates):
        return min(candidates, key=lambda other: abs(CELLS[other][2] - y)) if candidates else None

    def in_column(wanted_column, direction, maximum_distance):
        return nearest([other for other, (other_column, _, other_y) in CELLS.items()
                        if other_column == wanted_column and 0 < (other_y - y) * direction <= maximum_distance])

    if horizontal == 0:
        target = in_column(column, vertical, 1000)
        if target is None and column != CENTRE_COLUMN:
            target = in_column(column + (1 if column < CENTRE_COLUMN else -1), vertical, NEIGHBOUR_MAXIMUM_DISTANCE)
        return character if target is None else target

    below = in_column(column + horizontal, 1, NEIGHBOUR_MAXIMUM_DISTANCE)
    above = in_column(column + horizontal, -1, NEIGHBOUR_MAXIMUM_DISTANCE)
    target = (above or below) if vertical < 0 else (below or above)
    if target is None:
        same_row = [other for other, (_, _, other_y) in CELLS.items()
                    if other != character and abs(other_y - y) <= SAME_ROW_DISTANCE]
        # the farthest cell on the other side
        target = max(same_row, key=lambda other: (x - CELLS[other][1]) * horizontal) if same_row else character
    return target


def write_navigation(vsav2e):
    for character in CELLS:
        targets = bytes(cursor_target(character, horizontal, vertical) for horizontal, vertical in DIRECTIONS)
        vsav2e[NAVIGATION_TABLE + 8 * character:NAVIGATION_TABLE + 8 * character + 8] = targets


def extend_random_choice(vsav2e, free_space_start, free_space_end):
    """The random choice takes its ids from a table of 15 next to the code; the longer
    table goes with a small routine that reads it. Returns the first free address."""
    if (vsav2e[RANDOM_COUNT_ADDRESS:RANDOM_COUNT_ADDRESS + 4] != RANDOM_COUNT_ORIGINAL
            or vsav2e[RANDOM_READ_ADDRESS:RANDOM_READ_ADDRESS + 6] != RANDOM_READ_ORIGINAL):
        raise SystemExit('select screen: unexpected code at the random choice')
    table = bytes(vsav2e[RANDOM_TABLE:RANDOM_TABLE + RANDOM_TABLE_LENGTH]) + bytes(ADDED_CHARACTERS)
    routine = bytes.fromhex(
        '2f08'          # move.l  a0, -(a7)
        '41fa000c'      # lea     table(pc), a0
        '1d7000000382'  # move.b  (a0, d0.w), $382(a6)       the id of the player
        '205f'          # movea.l (a7)+, a0
        '4e75')         # rts
    address = free_space_start + (free_space_start & 1)
    end = address + len(routine) + len(table)
    if end > free_space_end:
        raise SystemExit('select screen: no room for the random choice')
    vsav2e[address:end] = routine + table
    vsav2e[RANDOM_COUNT_ADDRESS + 3] = len(table)
    vsav2e[RANDOM_READ_ADDRESS:RANDOM_READ_ADDRESS + 6] = b'\x4e\xb9' + struct.pack('>I', address)   # jsr routine
    return end


def apply(vsav2e, hunter, extension, sprite_roms, captures_directory, free_space_start, free_space_end):
    """Changes the select screen in the vsav2e program (a bytearray); the new frame goes
    to the program extension and the new tiles to sprite_roms, the upper sprite bank.
    Returns the first free address of the program and the first tile after the new ones."""
    screen = PlayStationScreen(captures_directory)
    sprites, tiles_end, cells_palette = build_icon_frame(vsav2e, hunter, extension, sprite_roms, screen)
    print('select screen: %d sprites, new tiles 0x%x-0x%x' % (sprites, NEW_TILES_START, tiles_end))
    move_cursors(vsav2e)
    write_navigation(vsav2e)
    free_space = extend_random_choice(vsav2e, free_space_start, free_space_end)
    return load_new_cells_palette(vsav2e, cells_palette, free_space, free_space_end), tiles_end
