"""The endings of Donovan, Huitzil and Pyron (docs/endings.md): the code, its data and the
way it is put into the program extension.

The code is tools/dev/new_endings.s, assembled into new_endings_code.py: a timeline engine
that draws pictures into the scroll layers, fades their palettes and scrolls the layers
frame by frame (the header format is described at the top of the .s file). Here each
ending's timeline is built from the pictures the user supplies (assets/endings/<name>/*.png,
RGBA layers of Saturn's screen 352x240, see tools/saturn/ending_layers.py). Without the
pictures an ending is not built and the character keeps Vampire Savior 2's own.
"""
import os
import struct
import sys
import tempfile
import zipfile

from build import new_endings_code as code
from build import story_text
from cps2 import quotes, sprite_rom

# vsav addresses (moved with the endings) or vsav2e addresses of what the code calls
MOVED = {'CREATE_TEXT': 0x21cce, 'MUSIC': 0x21d66, 'LEAVE': 0x21be6}
FIXED = {'ALLOC_FAR': 0x15702, 'ALLOC_NEAR': 0x15744, 'FADE_OUT': 0x12d0e}

# the layers: base of the tilemap, tile size, cells of the tilemap a column apart
LAYER_BASE = {1: 0x900000, 2: 0x908000, 3: 0x904000}
LAYER_TILE = {1: 8, 2: 16, 3: 32}
BLANK_CODE = {1: 0x0020, 2: 0x4220, 3: 0x0600}
PALETTE_RAM = 0x90c000
PAGE_BYTES = 32
GROUP_BYTES = 0x400                 # 32 pages for each of sprites, scroll 1, 2, 3
CPS_OFFSET = (16, -8)               # Saturn's screen -> CPS2's (352x240 -> 384x224)
SCREEN = (384, 224)
TRANSPARENT = (255, 0, 255)         # in the composed picture

# calibration of the scroll registers: value to put for the picture to be where Saturn has it
# measured: the screen shows (map x - scroll x, map y + scroll y + 239) for scroll 2 (its map is
# 1024 high; Vampire Savior's endings use x -64 and y 0x300, which puts row 0 at y -17)
SCROLL_ORIGIN = {2: (0, 0x311), 3: (0, 0x711)}
if os.environ.get('VSAV2E_SCROLL_ORIGIN'):                   # for calibrating: x2,y2,x3,y3
    _o = [int(v, 0) for v in os.environ['VSAV2E_SCROLL_ORIGIN'].split(',')]
    SCROLL_ORIGIN = {2: (_o[0], _o[1]), 3: (_o[2], _o[3])}


def cell_offset(layer, column, row):
    """byte offset of a tilemap entry in the layer's RAM (column-major blocks, see docs)"""
    if layer == 3:
        index = (row & 7) + ((column & 0x3f) << 3) + ((row & 0x38) << 6)
    elif layer == 2:
        index = (row & 0xf) + ((column & 0x3f) << 4) + ((row & 0x30) << 6)
    else:
        index = (row & 0x1f) + ((column & 0x3f) << 5) + ((row & 0x20) << 6)
    return 4 * index


class Blob:
    """data placed in the extension, one thing after the other; addresses are known as it grows"""

    def __init__(self, address):
        self.start = address
        self.data = bytearray()

    @property
    def here(self):
        return self.start + len(self.data)

    def add(self, data, even=True):
        address = self.here
        self.data += data
        if even and len(self.data) & 1:
            self.data += b'\0'
        return address


class Scenery:
    """the pictures, palettes and timeline of one ending, built up and written together"""

    def __init__(self, blob, scroll_bank, scroll_position, next_free):
        self.blob = blob
        self.bank = scroll_bank
        self.position = scroll_position
        self.next_free = next_free
        self.pages = {2: 0, 3: 0}            # palette pages used in each layer
        self.events = []                     # (frame, type, pointer, argument)
        self.channels = []                   # (first, last, block, levels, mode)

    def compose(self, layers):
        """Saturn's layers ((RGBA PNG path, brightness 0-1), drawn in order) as one CPS2
        screen on the transparent colour"""
        from PIL import Image
        screen = Image.new('RGB', SCREEN, TRANSPARENT)
        for path, brightness in layers:
            layer = Image.open(path).convert('RGBA')
            # a pixel is either drawn or not (Saturn's layers are not blended)
            solid = layer.split()[3].point(lambda alpha: 255 if alpha >= 128 else 0)
            rgb = layer.convert('RGB').point(lambda value: round(value * brightness))
            screen.paste(rgb, CPS_OFFSET, solid)
        return screen

    def picture(self, layer, layers, first_page=None, area=None, crop=None):
        """converts the layers to tiles of the scroll layer; returns (the cells to draw, the
        palette block). first_page: the palette page to start at (a picture that is
        never on the screen together with another may take its pages); area: (columns,
        rows) of cells to write, the cells without a tile as the blank code; crop: (column,
        row, columns, rows) of cells, only that part of the screen (a patch over a picture)"""
        from build import scroll_picture
        tile = LAYER_TILE[layer]
        image = self.compose(layers)
        first_column = first_row = 0
        if crop:
            first_column, first_row, columns, rows = crop
            image = image.crop((first_column * tile, first_row * tile,
                                (first_column + columns) * tile, (first_row + rows) * tile))
        converted = scroll_picture.convert(image, TRANSPARENT, tile=tile)
        if first_page is None:
            first_page = self.pages[layer]
            self.pages[layer] += len(converted.palettes)
        if first_page + len(converted.palettes) > 32:
            raise SystemExit('new endings: more than 32 palettes in scroll %d' % layer)
        # the tiles at the end of the scroll bank
        size = tile * tile // 2
        numbers = []
        for data in converted.tiles:
            self.position = self.next_free(self.position, layer)
            if self.position + size > 4 * len(self.bank[0]):
                raise SystemExit('new endings: the scroll bank is full')
            sprite_rom.write_raw(self.bank, self.position, data)
            numbers.append(self.position // size)
            self.position += size
        cells = bytearray()
        count = 0
        columns, rows = area or (converted.columns, converted.rows)
        for row in range(rows):
            for column in range(columns):
                cell = converted.cells[row][column] if row < converted.rows and column < converted.columns else None
                if cell is None:
                    if area is None:
                        continue
                    cells += struct.pack('>3H', cell_offset(layer, first_column + column, first_row + row), BLANK_CODE[layer], 0)
                else:
                    index, palette = cell
                    cells += struct.pack('>3H', cell_offset(layer, first_column + column, first_row + row), numbers[index],
                                         first_page + palette)
                count += 1
        address = self.blob.add(struct.pack('>H', count) + cells)
        # the palette block: source words, destination in palette RAM
        words = b''.join(struct.pack('>16H', *page) for page in converted.palette_words())
        source = self.blob.add(words)
        destination = PALETTE_RAM + GROUP_BYTES * layer + PAGE_BYTES * first_page
        block = self.blob.add(struct.pack('>IIH', source, destination, 16 * len(converted.palettes)))
        return address, block

    def draw(self, frame, layer, cells):
        self.events.append((frame, 0, cells, LAYER_BASE[layer]))

    def show_palette(self, frame, block):
        self.events.append((frame, 1, block, 0))

    def clear(self, frame, layer):
        self.events.append((frame, 2, BLANK_CODE[layer], LAYER_BASE[layer]))

    def fade(self, first, last, block, mode, start, end):
        """frames first..last: the palette shown from level `start` to `end` (0-15; as
        it is at 15 when mode is 0, at 0 when mode is 1)"""
        count = last - first + 1
        levels = bytes(round(start + (end - start) * i / max(count - 1, 1)) for i in range(count))
        self.channels.append((first, last, block, self.blob.add(levels), mode))

    def hold(self, first, last, block):
        """frames first..last: the palette as it is, written again every frame (the game's own
        palette loading writes over the pages now and then)"""
        if getattr(self, 'full', None) is None:
            self.full = self.blob.add(bytes([15]) * 4096)
        self.channels.append((first, last, block, self.full, 0))

    def scroll_table(self, frames, function):
        """words by frame from function(frame)"""
        return self.blob.add(b''.join(struct.pack('>H', function(frame) & 0xffff) for frame in range(frames)))

    def header(self, frames, tables_address, music):
        events = b''.join(struct.pack('>HHII', *event) for event in sorted(self.events, key=lambda e: e[0]))
        events += struct.pack('>HHII', 0xffff, 0, 0, 0)
        channels = b''.join(struct.pack('>HHIIH', first, last, block, levels, mode)
                            for first, last, block, levels, mode in self.channels)
        channels += struct.pack('>H', 0xffff)
        events_address = self.blob.add(events)
        channels_address = self.blob.add(channels)
        header = self.blob.add(struct.pack('>IIIIL', events_address, channels_address, tables_address,
                                           frames, music))
        # the next ending starts with no events or channels of its own so far
        self.events, self.channels, self.full = [], [], None
        return header


# --- Donovan: Anita asleep, the Dyrek blade fades in, a flash wakes her, the hand ---
DONOVAN_FRAMES = 2520
DONOVAN_MUSIC = 0x6e


def interpolate(points, frame):
    """linear between the (frame, value) points, held outside"""
    if frame <= points[0][0]:
        return points[0][1]
    for (f0, v0), (f1, v1) in zip(points, points[1:]):
        if frame <= f1:
            return v0 + (v1 - v0) * (frame - f0) / (f1 - f0)
    return points[-1][1]


# the glints on the blade: bank 7080 of Saturn's sprites cycles through 13 states; the first (0) is
# shown once, then these (frame less 1063, state) repeat every 74 frames (Saturn's frames 1403-1476)
SPARKLE_START = 1060
SPARKLE_LOOP = [(0, 1), (2, 2), (8, 3), (14, 4), (16, 5), (20, 6), (24, 7), (26, 8), (32, 1), (38, 2),
                (40, 9), (44, 3), (48, 10), (50, 5), (56, 7), (62, 8), (64, 11), (68, 1), (72, 12)]
SPARKLE_PERIOD = 74
SPARKLE_CELLS = (4, 2, 4, 1)         # column, row, columns, rows of the cells they cover (on scroll 3)
SPARKLE_PAGE = 28                    # the palette pages of the patches (the pictures use 16 and up)
FIGURE_FRAME = 1580


def sparkles(scenery, path, frames):
    """patches over the blade: the few cells they cover, redrawn with each state (the cells of
    the picture below, with the glint on them, so that the pictures need not be repeated)"""
    runs = [(SPARKLE_START, SPARKLE_START + 3, 0)]
    start = SPARKLE_START + 3
    while start < frames:
        for offset, state in SPARKLE_LOOP:
            runs.append((start + offset, None, state))
        start += SPARKLE_PERIOD
    runs = [(first, runs[i + 1][0] - 1 if i + 1 < len(runs) else frames - 1, state)
            for i, (first, _, state) in enumerate(runs)]
    patches = {}
    for first, last, state in runs:
        if first >= frames:
            break
        last = min(last, frames - 1)
        # a run that crosses the frame of the figure is cut there: its picture changes
        for part_first, part_last in ((first, min(last, FIGURE_FRAME - 1)), (max(first, FIGURE_FRAME), last)):
            if part_first > part_last:
                continue
            figure = part_first >= FIGURE_FRAME
            if (state, figure) not in patches:
                layers = [(path('figure'), 1)] if figure else []
                layers += [(path('awake'), 1), (path('blade'), 1), (path('sparkle%02d' % state), 1)]
                patches[state, figure] = scenery.picture(3, layers, first_page=SPARKLE_PAGE,
                                                         crop=SPARKLE_CELLS)
            cells, block = patches[state, figure]
            scenery.draw(part_first, 3, cells)
            scenery.hold(part_first, part_last, block)


def build_donovan(scenery, assets):
    path = lambda name: os.path.join(assets, name + '.png')
    frames = DONOVAN_FRAMES
    area = (13, 6)                      # the cells (32x32) the scenes cover (the picture sinks 39 pixels)
    scene = lambda *layers: scenery.picture(3, layers, first_page=16, area=area)   # the game writes the low pages
    for layer in (1, 2, 3):
        scenery.clear(0, layer)
    # Anita asleep fades in; the blade fades in (steps of its brightness); a flash wakes her
    cells, block = scene((path('asleep'), 1))
    scenery.draw(0, 3, cells)
    scenery.fade(0, 15, block, 0, 0, 15)
    scenery.hold(16, 479, block)
    steps = 8
    starts = [480 + step * 100 // (steps - 1) for step in range(steps)] + [950]
    for step in range(1, steps + 1):
        cells, block = scene((path('asleep'), 1), (path('blade'), step / steps))
        scenery.draw(starts[step - 1], 3, cells)
        scenery.hold(starts[step - 1], starts[step] - 1, block)
    # the flash (Saturn's frames 1290-1328 less 340): to white, the pose swaps, back
    scenery.fade(950, 960, block, 1, 0, 15)
    cells, block = scene((path('awake'), 1), (path('blade'), 1))
    scenery.draw(961, 3, cells)
    scenery.fade(961, 988, block, 1, 15, 0)
    scenery.hold(989, 1579, block)
    # Donovan's arm and face (Saturn's second background) appear behind the hand
    cells, block = scene((path('figure'), 1), (path('awake'), 1), (path('blade'), 1))
    scenery.draw(1580, 3, cells)
    scenery.hold(1580, frames - 1, block)
    sparkles(scenery, path, frames)
    # the hand comes in over everything, on scroll 2
    cells, block = scenery.picture(2, [(path('hand'), 1)], first_page=24)   # the game writes the low pages
    scenery.draw(1519, 2, cells)
    scenery.hold(1519, frames - 1, block)
    # the picture's height in pixels, from where it rests (measured in Saturn's captures; the
    # frames are Saturn's less 340, the start of the text)
    sink = [(0, -39), (160, -26), (360, -9), (560, 0), (1160, 0), (1260, 9), (1360, 17), (1460, 25),
            (1500, 29), (1560, 30)]
    arrive_x = [(0, 45), (1520, 45), (1530, 32), (1540, 24), (1550, 16), (1560, 8), (1570, 0)]
    arrive_y = [(0, 99), (1520, 99), (1530, 80), (1540, 64), (1550, 40), (1560, 16), (1570, 0)]
    if os.environ.get('VSAV2E_NO_SINK'):
        sink = [(0, 0)]
    ox2, oy2 = SCROLL_ORIGIN[2]
    ox3, oy3 = SCROLL_ORIGIN[3]
    tables = [
        scenery.scroll_table(frames, lambda f: ox2 - round(interpolate(arrive_x, f))),
        scenery.scroll_table(frames, lambda f: oy2 + round(interpolate(arrive_y, f))),
        scenery.scroll_table(frames, lambda f: ox3),
        scenery.scroll_table(frames, lambda f: oy3 + round(interpolate(sink, f))),
    ]
    # the four tables follow one another (the engine reads them so)
    return scenery.header(frames, tables[0], DONOVAN_MUSIC)


# --- Pyron: the throne slides in over a hell that turns into the galaxy ---
PYRON_MUSIC = 0x6d
PYRON_PAGES = [
    ['"So... it is a devil world."'],
    ['"The universe is space, having', 'different laws and chronology."'],
    ['"A very interesting world...', 'I must apologize..."'],
    ['"If its destruction were not to', 'be, it should have been mine."'],
    ['"There is nothing to', 'obtain from here..."'],
    ['"Perhaps I will head for', 'Andromeda next..."'],
]
PYRON_DURATIONS = [240, 280, 300, 280, 300, 460]          # Saturn's frames 1580-3440
PYRON_FRAMES = sum(PYRON_DURATIONS)


def build_pyron(scenery, assets):
    path = lambda name: os.path.join(assets, name + '.png')
    frames = PYRON_FRAMES
    area = (13, 5)                      # the cells (32x32) of the window: 416 x 160 pixels
    scene = lambda name: scenery.picture(3, [(path(name), 1)], first_page=16, area=area)
    for layer in (1, 2, 3):
        scenery.clear(0, layer)
    # the hell (Saturn's frame 2940-3000 less 1580: it fades to black, then the galaxy fades in)
    cells, block = scene('hell')
    scenery.draw(0, 3, cells)
    scenery.fade(0, 15, block, 0, 0, 15)
    scenery.hold(16, 1359, block)
    scenery.fade(1360, 1420, block, 0, 15, 0)
    cells, block = scene('galaxy')
    scenery.draw(1421, 3, cells)
    scenery.fade(1421, 1560, block, 0, 0, 15)
    scenery.hold(1561, frames - 1, block)
    # the throne, over it, on scroll 2
    cells, block = scenery.picture(2, [(path('throne'), 1)], first_page=24)
    scenery.draw(0, 2, cells)
    scenery.hold(0, frames - 1, block)
    # it slides in from the right (measured: 1/4 pixel a frame, then it eases to a stop)
    slide = [(0, 242), (860, 27), (940, 7), (980, 2), (1020, 0)]
    ox2, oy2 = SCROLL_ORIGIN[2]
    ox3, oy3 = SCROLL_ORIGIN[3]
    tables = [
        scenery.scroll_table(frames, lambda f: ox2 - round(interpolate(slide, f))),
        scenery.scroll_table(frames, lambda f: oy2),
        scenery.scroll_table(frames, lambda f: ox3),
        scenery.scroll_table(frames, lambda f: oy3),
    ]
    return scenery.header(frames, tables[0], PYRON_MUSIC)


# --- Huitzil: the damaged robot, the machines, the pilot, the city, each a picture that fades ---
HUITZIL_MUSIC = 0x6c
# (the font has no colon and no digits: the PlayStation's colons are full stops, 3600 seconds an hour)
HUITZIL_PAGES = [
    ['"Damage level over limit."'],
    ['"Unable to maintain present', 'form... Breaking down..."'],
    ['"Transmitting orders and program', 'code to an identical model..."'],
    ['Huitzil was damaged and finally', 'broke down after fighting.'],
    ['However, the command, "protect', 'the boy" was still operational.'],
    ['"Many unidentified robot units', 'approaching! Airspace breached!"'],
    ['"Who are they!?"'],
    ['"Our weapons are ineffective!', 'He cannot explain why!"'],
    ['"Perform maximum range scan', 'of area."'],
    ['"Classify all life forms as', 'enemy target or as protected."'],
    ['"Commence attack once', 'classifications are defined."'],
    ['"One hour until completion', 'of search..."'],
]
# Saturn's frames 1660-4720 (the text pages), then the picture stays until 4880
HUITZIL_DURATIONS = [240, 220, 260, 240, 360, 240, 240, 260, 240, 260, 240, 260]
HUITZIL_FRAMES = 4880 - 1660


def build_huitzil(scenery, assets):
    path = lambda name: os.path.join(assets, name + '.png')
    frames = HUITZIL_FRAMES
    area = (13, 5)
    # (picture, first frame, frames of fading in, last frame shown, frames of fading out): the
    # times are Saturn's frames less 1660 (measured on the brightness of its picture)
    shown = [('ship', 0, 15, 840, 20), ('machine', 861, 240, 1300, 20), ('face', 1321, 20, 2040, 20),
             ('city', 2061, 40, 3180, 40)]
    for layer in (1, 2, 3):
        scenery.clear(0, layer)
    for name, start, fade_in, end, fade_out in shown:
        cells, block = scenery.picture(3, [(path(name), 1)], first_page=12, area=area)
        scenery.draw(start, 3, cells)
        scenery.fade(start, start + fade_in, block, 0, 0, 15)
        scenery.hold(start + fade_in + 1, end - 1, block)
        scenery.fade(end, end + fade_out - 1, block, 0, 15, 0)
    ox2, oy2 = SCROLL_ORIGIN[2]
    ox3, oy3 = SCROLL_ORIGIN[3]
    tables = [scenery.scroll_table(frames, lambda f: ox2), scenery.scroll_table(frames, lambda f: oy2),
              scenery.scroll_table(frames, lambda f: ox3), scenery.scroll_table(frames, lambda f: oy3)]
    return scenery.header(frames, tables[0], HUITZIL_MUSIC)


# The English text of the PlayStation game (its endings have these pages; one page is a list of
# lines) and how long each page stays (frames; the timeline lasts as long as the pages).
DONOVAN_PAGES = [
    ['With Jedah defeated, the', "devil's dimension vanished."],
    ['"...wake...up...Anita..."'],
    ["Anita's soul was touched by", "Donovan's Dyrek Blade."],
    ['Waking from the nightmare, they', 'returned to the real world.'],
    ['"Anita... is your destiny also', 'a severe burden upon you?"'],
    ['"In that case, let\'s go', 'together."'],
    ['"Until the Darkstalkers are', 'defeated and the world is safe,"'],
    ['"I will look after your life...', 'in the name of mankind\'s blood."'],
    ['"You can decide the fate of your', 'life, after that has been done."'],
]
DONOVAN_DURATIONS = [240, 480, 240, 240, 240, 240, 240, 240, 360]

ENDINGS = {0x10: ('huitzil', build_huitzil), 0x11: ('pyron', build_pyron), 0x13: ('donovan', build_donovan)}
TEXTS = {0x10: (HUITZIL_PAGES, HUITZIL_DURATIONS), 0x11: (PYRON_PAGES, PYRON_DURATIONS), 0x13: (DONOVAN_PAGES, DONOVAN_DURATIONS)}
# Vampire Savior's text and duration tables: the master table of each language, the table
# of the durations (a word offset by character, then lists of words ended by 0)
TEXT_TABLES = (0x332216, 0x33c5e4)
DURATION_TABLES = (0xcde0, 0xcf72)
DURATION_POINTERS = 0xcdd0
CHARACTER_COUNT = quotes.CHARACTER_ID_COUNT


# the Japanese text engine spaces the letters 16 pixels apart, so the English text of the new endings
# (they have no Japanese one) is set again in the Japanese table: shorter lines, more pages
JAPANESE_LINE = 15


def narrow_pages(pages, durations, width=JAPANESE_LINE):
    """(pages, durations) with the words wrapped to `width` letters, two lines a page; each
    page's duration is shared among its new pages by their length"""
    new_pages, new_durations = [], []
    for page, duration in zip(pages, durations):
        lines, line = [], ''
        for word in ' '.join(page).split():
            if line and len(line) + 1 + len(word) > width:
                lines.append(line)
                line = word
            else:
                line = (line + ' ' + word) if line else word
        lines.append(line)
        groups = [lines[i:i + 2] for i in range(0, len(lines), 2)]
        total = sum(len(' '.join(group)) for group in groups)
        left = duration
        for number, group in enumerate(groups):
            share = left if number == len(groups) - 1 else round(duration * len(' '.join(group)) / total)
            new_pages.append(group)
            new_durations.append(share)
            left -= share
    return new_pages, new_durations


def place_texts(writer, layout, address, savior, characters):
    """new text and durations for `characters` ({id: (pages, durations)}) in both tables
    (Japanese ending text has none for them: they get the English one, in shorter lines);
    returns the end"""
    code_of = story_text.latin_codes(savior)
    encoded, encoded_japanese, durations_japanese = {}, {}, {}
    for character, (pages, durations) in characters.items():
        if len(pages) != len(durations):
            raise SystemExit('new endings: %d pages and %d durations' % (len(pages), len(durations)))
        encoded[character] = story_text.encode_text([pages], code_of, 32)[0]
        narrow_text, narrow_durations = narrow_pages(pages, durations)
        encoded_japanese[character] = story_text.encode_text([narrow_text], code_of, 32)[0]
        durations_japanese[character] = narrow_durations
    master_pointers, duration_pointers = [], []
    for language, table in enumerate(TEXT_TABLES):
        blocks, cache = [], {}
        for character, block in enumerate(quotes.read_master_table(savior, table)):
            if character in encoded:
                blocks.append((encoded_japanese if language == 0 else encoded)[character])
            else:
                if block not in cache:
                    try:
                        cache[block] = quotes.read_block(savior, block)
                    except struct.error:            # the last id has no text (its offset is not a block)
                        cache[block] = [[]]
                blocks.append(cache[block])
        data = quotes.encode_master_table(blocks)
        writer.put(address, data)
        master_pointers.append(address)
        address += len(data) + (len(data) & 1)
    for language, table in enumerate(DURATION_TABLES):
        offsets = struct.unpack_from('>%dH' % CHARACTER_COUNT, savior, table)
        lists = {}
        for character, offset in enumerate(offsets):
            words, position = [], table + offset
            while True:
                word = quotes.read_word(savior, position)
                if word == 0:
                    break
                words.append(word)
                position += 2
            lists[character] = tuple(words)
        for character, (pages, durations) in characters.items():
            lists[character] = tuple(durations_japanese[character] if language == 0 else durations)
        body, where = b'', {}
        for character in range(CHARACTER_COUNT):
            if lists[character] not in where:
                where[lists[character]] = 2 * CHARACTER_COUNT + len(body)
                body += struct.pack('>%dH' % (len(lists[character]) + 1), *lists[character], 0)
        data = struct.pack('>%dH' % CHARACTER_COUNT, *(where[lists[c]] for c in range(CHARACTER_COUNT))) + body
        writer.put(address, data)
        duration_pointers.append(address)
        address += len(data) + (len(data) & 1)
    writer.put(layout.language_table, struct.pack('>4I', master_pointers[0], master_pointers[1],
                                                  master_pointers[1], master_pointers[1]))
    writer.put(layout(DURATION_POINTERS), struct.pack('>4I', duration_pointers[0], duration_pointers[1],
                                                       duration_pointers[1], duration_pointers[1]))
    return address


# the pictures can also come in one archive in the assets folder (next to the folder they would be
# in): the paths in it are those of the repository, assets/saturn/endings/<ending>/<layer>.png
ARCHIVE = 'vsav2e_endings_assets.zip'
ARCHIVE_FOLDER = 'assets/saturn/endings/'


def pictures_folder(assets):
    """the folder with the pictures: `assets` itself, or the archive extracted to a temporary one,
    or None"""
    if assets and os.path.isdir(assets):
        return assets
    archive = os.path.normpath(os.path.join(assets or '', '..', '..', ARCHIVE))
    if not os.path.isfile(archive):
        return None
    folder = tempfile.mkdtemp(prefix='vsav2e_endings_')
    with zipfile.ZipFile(archive) as zipped:
        for name in zipped.namelist():
            if name.startswith(ARCHIVE_FOLDER) and name.endswith('.png'):
                target = os.path.join(folder, name[len(ARCHIVE_FOLDER):])
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, 'wb') as out:
                    out.write(zipped.read(name))
    return folder


def place(writer, layout, address, assets, scroll_bank, scroll_position, next_free, savior):
    """writes the code and the data of the endings whose pictures are in `assets` (a folder
    with one folder for each) at `address`; returns (the end, {character id: script
    address}, the scroll bank's next free position)"""
    scenery = Scenery(Blob(address + len(code.CODE) + (len(code.CODE) & 1)), scroll_bank,
                      scroll_position, next_free)
    headers = {}
    assets = pictures_folder(assets)
    for character, (name, build) in ENDINGS.items():
        folder = os.path.join(assets or '', name)
        if os.path.isdir(folder):
            headers[character] = build(scenery, folder)
    values = dict(FIXED)
    values.update({name: layout(vsav_address) for name, vsav_address in MOVED.items()})
    data = bytearray(code.CODE)
    for position, name in code.RELOCATIONS:
        data[position:position + 4] = struct.pack('>I', values[name])
    writer.put(address, bytes(data))
    writer.put(scenery.blob.start, bytes(scenery.blob.data))
    # the entry point of each ending: load its header and run the timeline
    entries = {}
    where = scenery.blob.here
    timeline = address + code.LABELS['timeline']
    for character, header in headers.items():
        stub = b'\x41\xf9' + struct.pack('>I', header) + b'\x4e\xf9' + struct.pack('>I', timeline)   # lea header.l, a0 / jmp timeline
        writer.put(where, stub)
        entries[character] = where
        where += len(stub)
    texts = {character: TEXTS[character] for character in headers}
    if texts:
        where = place_texts(writer, layout, (where + 1) & ~1, savior, texts)
    return where, entries, scenery.position
