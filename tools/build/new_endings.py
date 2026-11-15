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

    def picture(self, layer, layers, first_page=None, area=None):
        """converts the layers to tiles of the scroll layer; returns (the cells to draw, the
        palette block). first_page: the palette page to start at (a picture that is
        never on the screen together with another may take its pages); area: (columns,
        rows) of cells to write, the cells without a tile as the blank code"""
        from build import scroll_picture
        tile = LAYER_TILE[layer]
        converted = scroll_picture.convert(self.compose(layers), TRANSPARENT, tile=tile)
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
                    cells += struct.pack('>3H', cell_offset(layer, column, row), BLANK_CODE[layer], 0)
                else:
                    index, palette = cell
                    cells += struct.pack('>3H', cell_offset(layer, column, row), numbers[index],
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
        return self.blob.add(struct.pack('>IIIIL', events_address, channels_address, tables_address,
                                         frames, music))


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


def build_donovan(scenery, assets):
    path = lambda name: os.path.join(assets, name + '.png')
    frames = DONOVAN_FRAMES
    area = (13, 4)                      # the cells (32x32) the scenes cover: 416 x 128 pixels
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

ENDINGS = {0x13: ('donovan', build_donovan)}
TEXTS = {0x13: (DONOVAN_PAGES, DONOVAN_DURATIONS)}
# Vampire Savior's text and duration tables: the master table of each language, the table
# of the durations (a word offset by character, then lists of words ended by 0)
TEXT_TABLES = (0x332216, 0x33c5e4)
DURATION_TABLES = (0xcde0, 0xcf72)
DURATION_POINTERS = 0xcdd0
CHARACTER_COUNT = quotes.CHARACTER_ID_COUNT


def place_texts(writer, layout, address, savior, characters):
    """new text and durations for `characters` ({id: (pages, durations)}) in both tables
    (Japanese ending text has none for them: they get the English one); returns the end"""
    code_of = story_text.latin_codes(savior)
    encoded = {}
    for character, (pages, durations) in characters.items():
        if len(pages) != len(durations):
            raise SystemExit('new endings: %d pages and %d durations' % (len(pages), len(durations)))
        encoded[character] = story_text.encode_text([pages], code_of, 32)[0]
    master_pointers, duration_pointers = [], []
    for table in TEXT_TABLES:
        blocks, cache = [], {}
        for character, block in enumerate(quotes.read_master_table(savior, table)):
            if character in encoded:
                blocks.append(encoded[character])
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
    for table in DURATION_TABLES:
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
            lists[character] = tuple(durations)
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
        stub = b'\x41\xf9' + struct.pack('>I', header) + b'\x60\x00'      # lea header.l, a0 / bra.w
        stub += struct.pack('>h', timeline - (where + len(stub)))
        writer.put(where, stub)
        entries[character] = where
        where += len(stub)
    texts = {character: TEXTS[character] for character in headers}
    if texts:
        where = place_texts(writer, layout, (where + 1) & ~1, savior, texts)
    return where, entries, scenery.position
