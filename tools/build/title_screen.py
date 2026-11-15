"""The title screen of the PlayStation Darkstalkers 3.

Vampire Savior 2's title is a logo made of three scroll layers (a blue band, the
outline, a glow) and of objects (the letters, the crown, the "2", the subtitle, eight
sparkles), arriving with a white flash. vsav2e shows Darkstalkers 3's instead, as the
PlayStation game shows it (measured frame by frame on the disc):

- one black frame, then the logo grows from the middle of the screen to its full size
  in 8 frames (it is drawn smaller: these 8 pictures are captures of the PlayStation
  screen, assets/psx/title/zoom1.png ... zoom8.png);
- from the last zoom picture, for 16 frames, the whole screen goes white step by step
  (16 of 255 more to each component on each frame, up to 248), then comes back at once;
- then the logo stands still on black (assets/psx/title/darkstalkers3.png).

The copyright line of the arcade stays at the bottom (it whitens with the rest), and the
INSERT COIN of the arcade, which the PlayStation does not have, comes with the still
logo, as in the arcade.

How it is done in the title scene (the routine of its states at 0x6b66, `$8(a5)` the
state):

- state 0, the game's set up: the blue band, loaded into the text layer (0x902000 and
  0x903000), becomes blank text there; the outline and glow layers are loaded but not
  shown (the layer control word `$32(a5)` shows the text layer only); the objects of the
  arcade's arrival are not created;
- states 2 and 4 are vsav2e's: the logo object is created and the arrival lasts 24
  frames (the game's states 2 to 8 made the arcade's arrival);
- state 10, the game's still title: the arcade's logo objects are not created; the
  INSERT COIN, the music and the copyright are the game's. It lasts as long as on the
  PlayStation before the demonstration starts.

The logo object is the stage name object (class 07, kind 0x1a), marked "TL" in a field
it does not use; its work on each frame picks the picture (an animation step), writes
the logo's palettes and does the flash. The pictures are sprite frames in the program
extension, their tiles in empty tiles of the upper sprite bank; the palettes are the
sprite palettes from LOGO_FIRST_PALETTE on, made for the logo from the captures (16
colours each, one per tile), and 16 versions of them, from normal to the whitest step.
"""
import os
import struct

from build import png

# --- the captures --------------------------------------------------------------------

LOGO_FILE = 'darkstalkers3.png'
ZOOM_FILES = ['zoom%d.png' % step for step in range(1, 9)]
CAPTURE_LOGO_ROWS = 203                 # below: the copyright line of the PlayStation
DARK = 8                                # a pixel no brighter than this is the black
# the PlayStation screen (364 x 240) on the arcade's (384 x 224): centred
CAPTURE_TO_SCREEN_X, CAPTURE_TO_SCREEN_Y = 10, -8

# --- the animation -------------------------------------------------------------------

ZOOM_FRAMES = 8
FLASH_FRAMES = 15
# The sprites on the screen are the ones the object gave the frame before (the sprite
# list is buffered), the palettes are the frame's own. On the PlayStation the flash adds
# 16 (of 255) to every component on each frame, saturating, from the last zoom picture
# on; its 15th step is shown twice. In 4-bit components: + 1 a frame. So, with c the
# object's frame: picture min(c, 8) (shown at c + 1), flash level c - 7 for c = 8 to 22,
# 15 at c = 23, then the colours back at c = 24.
FLASH_START = ZOOM_FRAMES
ARRIVAL_FRAMES = ZOOM_FRAMES + FLASH_FRAMES + 2
STILL_FRAMES = 368                      # the still logo, until the demonstration
LEVELS = 16                             # 0 normal, 1-15 the flash
FLASH_STEP = 16                         # what the flash adds on each frame (of 255)
FLASH_MAXIMUM = 248                     # the PlayStation's brightest component

# --- tiles, palettes ------------------------------------------------------------------

TILE_SIZE = 16
TRANSPARENT_PEN = 15
COLOURS_PER_PALETTE = 15
LOGO_FIRST_PALETTE = 0x08
LOGO_PALETTES = 16                      # sprite palettes 0x08-0x17
SPRITE_PALETTE_RAM = 0x90c000
PALETTE_BYTES = 32
# Empty tiles of the upper sprite bank (beside the ones the select screen takes, from
# 0x1fc00): long runs, at the end of graphics.
FREE_TILE_RUNS = ((0x114dc, 0x11804), (0x14078, 0x14200))
UPPER_BANK_END = 0x20000

# where the logo object is: the middle of the screen (x), its y; a sprite of the frames
# is at its screen position minus these
LOGO_X, LOGO_Y = 0xc0, 0x70
FRAME_ORIGIN_X, FRAME_ORIGIN_Y = 192, 128

# --- the code of the title scene ------------------------------------------------------

STATES_ROUTINE = 0x6b66
STATES_ROUTINE_ORIGINAL = bytes.fromhex('302d0008323b00064efb1002')
STATES_TABLE = 0x6b72
BAND_LOADS = (0x6bd0, 0x6bde)           # `jsr $1dbb6`, a1 = 0x902000 and 0x903000
BAND_LOAD_ORIGINAL = bytes.fromhex('4eb90001dbb6')
LAYER_CONTROL = 0x6b88                  # `move.w #$2d0e, $32(a5)`
LAYER_CONTROL_ORIGINAL = bytes.fromhex('3b7c2d0e0032')
LAYER_CONTROL_TEXT_ONLY = bytes.fromhex('3b7c2d020032')
ARRIVAL_OBJECTS = (0x6c10, 0x6c70)      # the creation of the arcade's arrival objects
STILL_OBJECTS = (0x6ce6, 0x6d76)        # and of its still logo
OBJECTS_ORIGINAL = bytes.fromhex('4eb900015702')
STILL_TIME = 0x6ccc                     # `move.w #$1e0, $a(a5)`
STILL_TIME_ORIGINAL = bytes.fromhex('3b7c01e0000a')
COPYRIGHT_ROUTINE = 0x6de2
ALLOCATE_OBJECT = 0x15702
REGISTER_FOR_DRAWING = 0x13c3a
NAME_OBJECT_KIND = 0x0100071a
NAME_OBJECT_STATE_TABLE = 0x6c68a       # the name object's own work, by its state
MARK_FIELD, TITLE_MARK = 0x40, 0x544c   # "TL"
COUNTER_FIELD = 0x42                    # frames since the logo came
SCENE_FIELD = 0x44                      # the scene it belongs to: `$4(a5)`
SAVED_FIELD = 0x60                      # the copyright palette and the backdrop colour
COPYRIGHT_PALETTE = 0x90c7e0            # text layer palette 0x1f
BACKDROP = 0x90dffe                     # colour 4095: the screen where nothing is drawn
BLANK_TEXT = 0x00200000                 # a text layer cell with the space character
PALETTE_PAGE = 0x90c0                   # `$20(a5)`, as the game's state 2 sets it
# The INSERT COIN of the arcade (an object at fff200, class 03 kind 0x10) is where the
# "3" of the logo is: the logo object moves it down, under the logo (its y goes up).
INSERT_COIN_OBJECT = 0x7200             # from a5
INSERT_COIN_KIND = 0x0310               # class and kind (the byte before them changes)
INSERT_COIN_Y = 0xe1


def cps_colour(red, green, blue):
    """an 8-bit colour as the 4 bits of each component of a CPS colour"""
    return tuple(min(15, (component * 15 + 127) // 255) for component in (red, green, blue))


def colour_word(colour):
    red, green, blue = colour
    return 0xf000 | red << 8 | green << 4 | blue


def whiter(value, level):
    """a 4-bit component at a level of the flash: the PlayStation adds FLASH_STEP per
    level to the 8-bit component, up to FLASH_MAXIMUM"""
    flashed = min(FLASH_MAXIMUM, value * 17 + FLASH_STEP * level) if level else value * 17
    return (flashed * 15 + 127) // 255


def read_picture(data, flash=0):
    """the logo of a capture, on the screen: {(x, y): colour}, the black left out. flash:
    what the PlayStation's flash had added to each component in the capture"""
    width, height, rows = png.read(data)
    picture = {}
    for y in range(min(height, CAPTURE_LOGO_ROWS)):
        for x, pixel in enumerate(rows[y]):
            red, green, blue = (max(0, component - flash) for component in pixel)
            if max(red, green, blue) > DARK:
                picture[x + CAPTURE_TO_SCREEN_X, y + CAPTURE_TO_SCREEN_Y] = cps_colour(red, green, blue)
    return picture


def picture_tiles(picture):
    """the tiles of a picture: {(left, top): [16 rows of 16 colours or None]}"""
    tiles = {}
    for (x, y), colour in picture.items():
        left, top = x - x % TILE_SIZE, y - y % TILE_SIZE
        tile = tiles.setdefault((left, top), [[None] * TILE_SIZE for _ in range(TILE_SIZE)])
        tile[y - top][x - left] = colour
    return tiles


def distance(first, second):
    return sum((a - b) ** 2 for a, b in zip(first, second))


def median_cut(counts, wanted):
    """at most `wanted` colours for the colours in counts ({colour: pixels})"""
    boxes = [list(counts.items())]
    while len(boxes) < wanted:
        splittable = [box for box in boxes if len(box) > 1]
        if not splittable:
            break
        box = max(splittable, key=lambda box: sum(count for _, count in box))
        spans = [max(colour[c] for colour, _ in box) - min(colour[c] for colour, _ in box) for c in range(3)]
        component = spans.index(max(spans))
        box.sort(key=lambda item: item[0][component])
        total, running = sum(count for _, count in box), 0
        for index, (_, count) in enumerate(box):
            running += count
            if running * 2 >= total:
                break
        index = max(1, min(index, len(box) - 1))
        boxes.remove(box)
        boxes += [box[:index], box[index:]]
    palette = []
    for box in boxes:
        total = sum(count for _, count in box)
        palette.append(tuple((sum(colour[c] * count for colour, count in box) + total // 2) // total
                             for c in range(3)))
    return palette


def make_palettes(tile_counts):
    """LOGO_PALETTES palettes for the tiles (each {colour: pixels}), and the palette of
    each tile: tiles of like colours are grouped (by their mean colour), each group gets
    the colours of its pixels, and every tile then takes the palette it fits best"""
    means = []
    for counts in tile_counts:
        total = sum(counts.values())
        means.append(tuple(sum(colour[c] * count for colour, count in counts.items()) / total for c in range(3)))
    # the groups: k-means from tiles far apart
    centres = [means[0]]
    while len(centres) < LOGO_PALETTES:
        centres.append(max(means, key=lambda mean: min(distance(mean, centre) for centre in centres)))
    for _ in range(8):
        groups = [min(range(len(centres)), key=lambda g: distance(mean, centres[g])) for mean in means]
        for g in range(len(centres)):
            members = [means[t] for t in range(len(means)) if groups[t] == g]
            if members:
                centres[g] = tuple(sum(m[c] for m in members) / len(members) for c in range(3))
    nearest_cache = {}

    def nearest(colour, palette_index):
        key = colour, palette_index
        if key not in nearest_cache:
            palette = palettes[palette_index]
            nearest_cache[key] = min(range(len(palette)), key=lambda pen: distance(colour, palette[pen]))
        return nearest_cache[key]

    def error(counts, palette_index):
        palette = palettes[palette_index]
        return sum(distance(colour, palette[nearest(colour, palette_index)]) * count
                   for colour, count in counts.items())

    for _ in range(4):
        palettes = []
        for g in range(LOGO_PALETTES):
            counts = {}
            for t, counts_of_tile in enumerate(tile_counts):
                if groups[t] == g:
                    for colour, count in counts_of_tile.items():
                        counts[colour] = counts.get(colour, 0) + count
            palettes.append(median_cut(counts, COLOURS_PER_PALETTE) if counts else [(0, 0, 0)])
        nearest_cache.clear()
        groups = [min(range(LOGO_PALETTES), key=lambda p: error(counts, p)) for counts in tile_counts]
    return palettes, groups, nearest


class TileAllocator:
    """single empty tiles of the upper bank, from the end of the select screen's and in
    the runs of FREE_TILE_RUNS"""

    def __init__(self, sprite_roms, first_free_tile):
        self.sprite_roms = sprite_roms
        self.tiles = [tile for start, end in ((first_free_tile, UPPER_BANK_END),) + FREE_TILE_RUNS
                      for tile in range(start, end)]
        self.next = 0

    def allocate(self):
        while self.next < len(self.tiles):
            tile = self.tiles[self.next]
            self.next += 1
            if self.sprite_roms.is_blank(tile):
                return tile
        raise SystemExit('title screen: no empty tiles left')


def read_captures(title_directory):
    """{name: the bytes of the PNG} of the captures in the title folder (assets/psx/title)"""
    names = ZOOM_FILES + [LOGO_FILE]
    missing = [name for name in names if not os.path.exists(os.path.join(title_directory, name))]
    if missing:
        raise SystemExit('title screen: %s has no %s' % (title_directory, ', '.join(missing)))
    return {name: open(os.path.join(title_directory, name), 'rb').read() for name in names}


def build_pictures(extension, sprite_roms, first_free_tile, title_directory):
    """writes the tiles, the frames and the palette table; returns (steps, palettes table,
    blend table) addresses in the extension and the count of tiles"""
    captures = read_captures(title_directory)
    # the last zoom picture is captured with the first step of the flash
    pictures = [read_picture(captures[name], FLASH_STEP if name == ZOOM_FILES[-1] else 0)
                for name in ZOOM_FILES + [LOGO_FILE]]
    tiled = [picture_tiles(picture) for picture in pictures]
    keys, tile_counts = [], []
    for step, tiles in enumerate(tiled):
        for position, tile in sorted(tiles.items()):
            counts = {}
            for row in tile:
                for colour in row:
                    if colour is not None:
                        counts[colour] = counts.get(colour, 0) + 1
            keys.append((step, position))
            tile_counts.append(counts)
    palettes, groups, nearest = make_palettes(tile_counts)

    allocator = TileAllocator(sprite_roms, first_free_tile)
    written = {}                        # pens -> tile
    sprites_of_step = [[] for _ in tiled]
    for (step, (left, top)), group in zip(keys, groups):
        tile = tiled[step][left, top]
        pens = tuple(tuple(TRANSPARENT_PEN if colour is None else nearest(colour, group) for colour in row)
                     for row in tile)
        if pens not in written:
            code = allocator.allocate()
            sprite_roms.write_tile(code, [list(row) for row in pens])
            written[pens] = code
        sprites_of_step[step].append((left - FRAME_ORIGIN_X, top - FRAME_ORIGIN_Y, written[pens] & 0xffff,
                                      LOGO_FIRST_PALETTE + group))

    steps = []
    for sprites in sprites_of_step:
        shape = extension.add(b''.join(struct.pack('>hh', x, y) for x, y, _, _ in sprites))
        frame = extension.add(struct.pack('>HHHI', 2, len(sprites), len(sprites) - 1, shape)
                              + b''.join(struct.pack('>HH', tile, attributes) for _, _, tile, attributes in sprites))
        steps.append(struct.pack('>II', 0, frame))
    steps_address = extension.add(b''.join(steps))

    table = bytearray()
    for level in range(LEVELS):
        for palette in palettes:
            words = [colour_word(tuple(whiter(value, level) for value in colour)) for colour in palette]
            words += [0] * (16 - len(words))
            table += struct.pack('>16H', *words)
    palettes_address = extension.add(bytes(table))
    blend_address = extension.add(bytes(whiter(value, level) for level in range(LEVELS) for value in range(16)))
    return steps_address, palettes_address, blend_address, len(written)


def routines(steps, palettes, blend):
    """the code, one block: the states routine, the text clearing, the logo object's
    work (the returned offsets of the last two)"""
    palette_bytes = LOGO_PALETTES * PALETTE_BYTES
    palette_ram = SPRITE_PALETTE_RAM + LOGO_FIRST_PALETTE * PALETTE_BYTES
    states = bytes.fromhex(
        '302d0008'                                      # move.w  $8(a5), d0       the state
        '6750'                                          # beq.s   game             0: the game's
        '0c40000a'                                      # cmpi.w  #10, d0
        '644a'                                          # bcc.s   game             10, 12: the game's
        '0c400002'                                      # cmpi.w  #2, d0
        '6636'                                          # bne.s   arriving
        # state 2: the logo object, the copyright line, the arrival's time
        '3b7c%04x0020' % PALETTE_PAGE +                 # move.w  #page, $20(a5)
        '4eb9%08x' % ALLOCATE_OBJECT +                  # jsr     allocate
        '6716'                                          # beq.s   no_object
        '28bc%08x' % NAME_OBJECT_KIND +                 # move.l  #kind, (a4)
        '397c%04x%04x' % (TITLE_MARK, MARK_FIELD) +     # move.w  #"TL", MARK(a4)
        '426c%04x' % COUNTER_FIELD +                    # clr.w   COUNTER(a4)
        '396d0004%04x' % SCENE_FIELD +                  # move.w  $4(a5), SCENE(a4)
        # no_object:
        '4eb8%04x' % COPYRIGHT_ROUTINE +                # jsr     copyright
        '3b7c%04x000a' % ARRIVAL_FRAMES +               # move.w  #frames, $a(a5)
        '3b7c00040008'                                  # move.w  #4, $8(a5)
        '4e75'                                          # rts
        # arriving: state 4, then the game's still title (10)
        '536d000a'                                      # subq.w  #1, $a(a5)
        '6606'                                          # bne.s   done
        '3b7c000a0008'                                  # move.w  #10, $8(a5)
        # done:
        '4e75'                                          # rts
        # game: the instructions the jump replaced
        '41f8%04x' % STATES_TABLE +                     # lea     table, a0
        '32300000'                                      # move.w  0(a0, d0.w), d1
        '4ef01000')                                     # jmp     0(a0, d1.w)
    clear_text = bytes.fromhex(
        '303c03ff'                                      # move.w  #$3ff, d0        0x1000 bytes
        '22fc%08x' % BLANK_TEXT +                       # move.l  #blank, (a1)+
        '51c8fff8'                                      # dbra    d0, (back)
        '4e75')                                         # rts
    frame = bytes.fromhex(
        '0c6e%04x%04x' % (TITLE_MARK, MARK_FIELD) +     # cmpi.w  #"TL", MARK(a6)
        '66000126'                                      # bne.w   name_object
        '302d0004'                                      # move.w  $4(a5), d0       still its scene?
        'b06e%04x' % SCENE_FIELD +                      # cmp.w   SCENE(a6), d0
        '670c'                                          # beq.s   work
        '426e%04x' % MARK_FIELD +                       # clr.w   MARK(a6)
        '1d7c00040004'                                  # move.b  #4, $4(a6)       destroy
        '4e75'                                          # rts
        # work:
        '48e73f20'                                      # movem.l d2-d7/a2, -(a7)
        '342e%04x' % COUNTER_FIELD +                    # move.w  COUNTER(a6), d2
        # the picture: zoom d2 for the first frames, then the logo
        '72%02x' % ZOOM_FRAMES +                        # moveq   #zoom frames, d1
        'b441'                                          # cmp.w   d1, d2
        '6402'                                          # bcc.s   picture
        '3202'                                          # move.w  d2, d1
        # picture:
        'e749'                                          # lsl.w   #3, d1           8 bytes a step
        '41f9%08x' % steps +                            # lea     steps, a0
        'd0c1'                                          # adda.w  d1, a0
        '2d48001c'                                      # move.l  a0, $1c(a6)
        '3d7c%04x0010' % LOGO_X +                       # move.w  #x, $10(a6)
        '3d7c%04x0014' % LOGO_Y +                       # move.w  #y, $14(a6)
        # the level of the flash: d2 - 7 from frame 8 to 22, 15 at frame 23, else 0
        '7600'                                          # moveq   #0, d3
        '3002'                                          # move.w  d2, d0
        '5f40'                                          # subq.w  #7, d0
        '6f10'                                          # ble.s   level_set
        '0c40%04x' % (FLASH_FRAMES + 1) +               # cmpi.w  #flash frames + 1, d0
        '620a'                                          # bhi.s   level_set
        '0c40%04x' % FLASH_FRAMES +                     # cmpi.w  #flash frames, d0
        '6302'                                          # bls.s   level
        '70%02x' % FLASH_FRAMES +                       # moveq   #flash frames, d0
        # level:
        '3600'                                          # move.w  d0, d3
        # level_set: at the flash's first frame the copyright and backdrop colours are kept
        '0c42%04x' % FLASH_START +                      # cmpi.w  #flash start, d2
        '6618'                                          # bne.s   logo_palettes
        '41f9%08x' % COPYRIGHT_PALETTE +                # lea     copyright, a0
        '43ee%04x' % SAVED_FIELD +                      # lea     SAVED(a6), a1
        '7e0f'                                          # moveq   #15, d7
        '32d8'                                          # move.w  (a0)+, (a1)+
        '51cffffc'                                      # dbra    d7, (back)
        '32b9%08x' % BACKDROP +                         # move.w  backdrop, (a1)
        # logo_palettes: the logo's palettes at the level
        '3003'                                          # move.w  d3, d0
        'c0fc%04x' % palette_bytes +                    # mulu.w  #bytes, d0
        '41f9%08x' % palettes +                         # lea     palettes, a0
        'd1c0'                                          # adda.l  d0, a0
        '43f9%08x' % palette_ram +                      # lea     palette RAM, a1
        '3e3c%04x' % (palette_bytes // 2 - 1) +         # move.w  #words - 1, d7
        '32d8'                                          # move.w  (a0)+, (a1)+
        '51cffffc'                                      # dbra    d7, (back)
        '4a43'                                          # tst.w   d3
        '672c'                                          # beq.s   not_flashing
        # the copyright and the backdrop at the level, from the kept colours
        '45f9%08x' % blend +                            # lea     blend, a2
        'e94b'                                          # lsl.w   #4, d3           16 bytes a level
        'd4c3'                                          # adda.w  d3, a2
        '41ee%04x' % SAVED_FIELD +                      # lea     SAVED(a6), a0
        '43f9%08x' % COPYRIGHT_PALETTE +                # lea     copyright, a1
        '7e0f'                                          # moveq   #15, d7
        '3018'                                          # move.w  (a0)+, d0
        '6152'                                          # bsr.s   whiten
        '32c0'                                          # move.w  d0, (a1)+
        '51cffff8'                                      # dbra    d7, (back)
        '3010'                                          # move.w  (a0), d0
        '6148'                                          # bsr.s   whiten
        '33c0%08x' % BACKDROP +                         # move.w  d0, backdrop
        '601e'                                          # bra.s   count
        # not_flashing: after the flash's last frame, the kept colours back
        '0c42%04x' % (ARRIVAL_FRAMES - 1) +             # cmpi.w  #arrival - 1, d2
        '6618'                                          # bne.s   count
        '41ee%04x' % SAVED_FIELD +                      # lea     SAVED(a6), a0
        '43f9%08x' % COPYRIGHT_PALETTE +                # lea     copyright, a1
        '7e0f'                                          # moveq   #15, d7
        '32d8'                                          # move.w  (a0)+, (a1)+
        '51cffffc'                                      # dbra    d7, (back)
        '33d0%08x' % BACKDROP +                         # move.w  (a0), backdrop
        # count:
        '0c427fff'                                      # cmpi.w  #$7fff, d2
        '6404'                                          # bcc.s   counted
        '526e%04x' % COUNTER_FIELD +                    # addq.w  #1, COUNTER(a6)
        # counted: INSERT COIN under the logo
        '0c6d%04x%04x' % (INSERT_COIN_KIND, INSERT_COIN_OBJECT + 2) +  # cmpi.w #kind, object + 2(a5)
        '6606'                                          # bne.s   restore
        '3b7c%04x%04x' % (INSERT_COIN_Y, INSERT_COIN_OBJECT + 0x14) +  # move.w #y, object y(a5)
        # restore:
        '4cdf04fc'                                      # movem.l (a7)+, d2-d7/a2
        '4ef9%08x' % REGISTER_FOR_DRAWING +             # jmp     register for drawing
        # whiten: d0 a colour, a2 the level's row of the blend table; d0 whiter
        '7800'                                          # moveq   #0, d4
        '7c02'                                          # moveq   #2, d6           red, green, blue
        'e958'                                          # rol.w   #4, d0
        'e94c'                                          # lsl.w   #4, d4
        'e958'                                          # rol.w   #4, d0
        '3a00'                                          # move.w  d0, d5
        '0245000f'                                      # andi.w  #$f, d5
        '88325000'                                      # or.b    0(a2, d5.w), d4
        '51cefff0'                                      # dbra    d6, (back)
        '0044f000'                                      # ori.w   #$f000, d4       full brightness
        '3004'                                          # move.w  d4, d0
        '4e75'                                          # rts
        # name_object: the stage name object's own work, as the game does it
        '102e0005'                                      # move.b  $5(a6), d0
        '43f9%08x' % NAME_OBJECT_STATE_TABLE +          # lea     table, a1
        '32310000'                                      # move.w  0(a1, d0.w), d1
        '4ef11000')                                     # jmp     0(a1, d1.w)
    return states + clear_text + frame, len(states), len(states) + len(clear_text)


def patch(vsav2e, address, original, replacement):
    if vsav2e[address:address + len(original)] != original:
        raise SystemExit('title screen: unexpected code at 0x%x' % address)
    nops = b'\x4e\x71' * ((len(original) - len(replacement)) // 2)
    vsav2e[address:address + len(original)] = replacement + nops


def branch(source, target):
    """bra.w from source to target"""
    return b'\x60\x00' + struct.pack('>h', target - (source + 2))


def apply(vsav2e, extension, sprite_roms, first_free_tile, title_directory, free_space_start, free_space_end):
    """Gives vsav2e the PlayStation title. Returns (the first free address of the
    program, the address of the logo object's work: the name object's work goes there)."""
    steps, palettes, blend, tiles = build_pictures(extension, sprite_roms, first_free_tile, title_directory)
    code, clear_offset, frame_offset = routines(steps, palettes, blend)
    address = free_space_start + (free_space_start & 1)
    if address + len(code) > free_space_end:
        raise SystemExit('title screen: no room for the routines')
    vsav2e[address:address + len(code)] = code

    jump = b'\x4e\xf9' + struct.pack('>I', address)
    patch(vsav2e, STATES_ROUTINE, STATES_ROUTINE_ORIGINAL, jump)
    for load in BAND_LOADS:
        patch(vsav2e, load, BAND_LOAD_ORIGINAL, b'\x4e\xb9' + struct.pack('>I', address + clear_offset))
    patch(vsav2e, LAYER_CONTROL, LAYER_CONTROL_ORIGINAL, LAYER_CONTROL_TEXT_ONLY)
    for start, end in (ARRIVAL_OBJECTS, STILL_OBJECTS):
        patch(vsav2e, start, OBJECTS_ORIGINAL, branch(start, end))
    patch(vsav2e, STILL_TIME, STILL_TIME_ORIGINAL, bytes.fromhex('3b7c%04x000a' % STILL_FRAMES))
    print('title screen: %d tiles, routines 0x%x-0x%x' % (tiles, address, address + len(code)))
    return address + len(code), address + frame_offset
