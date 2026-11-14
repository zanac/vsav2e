"""The per-character endings of Vampire Savior, in vsav2e (docs/endings.md).

Vampire Savior 2 has one ending for everybody; Vampire Savior has one for each character,
made of a script per character, object classes, pictures (sprites and scroll layers),
palettes and texts. That code is moved, as it is, from Vampire Savior's program (the
decrypted vsavd) into the program extension and patched so that it runs inside Vampire
Savior 2: tools/build/endings_recipe.py, made by tools/dev/endings/gen_recipe.py, lists
what moves and every patch (addresses and numbers only). This module applies it:

- the code ranges, then the data blocks, are copied to the extension; a moved address
  is patched to its new place, the other patches are values found by the analysis
  (Vampire Savior 2's address of a routine, its RAM offset, its number of a class);
- the sprite tiles of the moved frames go to the upper sprite bank at their own numbers
  (the frames are drawn from it because they are in the extension);
- the tiles of the scroll layers go to the scroll bank (16 MB after the sprites, which
  the scroll layers read instead of the normal graphics while the word at 0x8040c0 has
  bits 0-2 set) with new numbers, and the tilemaps get the new numbers;
- each object pool gets a longer class table with the moved classes after Vampire
  Savior 2's own, read by a hook in its object runner;
- the ending mode jumps to a dispatcher: characters 00-0a and 0c-0e (all but Jedah and
  the three characters Vampire Savior does not have) play Vampire Savior's ending, then
  Vampire Savior 2's staff credits; the others play Vampire Savior 2's ending.
"""
import struct

from build import endings_recipe as recipe
from cps2 import sprite_rom

# --- Vampire Savior 2: the object pools (class table, number of classes, object runner)
POOLS = {
    0: (0x6a51c, 0x7c, 0x6a4f0),
    1: (0x8b9a6, 0x3a, 0x8b97a),
    3: (0x939a6, 0x0b, 0x93974),
    4: (0x9885e, 0x07, 0x98832),
}
# in each runner:  moveq #0,d0 / move.b 2(a6),d0 / add.w d0,d0 / add.w d0,d0 /
#                  movea.l table(pc,d0.w),a0 / moveq #0,d0 / jsr (a0)
RUNNER_DISPATCH = bytes.fromhex('7000102e0002d040d040207b')
RUNNER_DISPATCH_END = bytes.fromhex('70004e90')
RUNNER_DISPATCH_SIZE = 18

# the game mode of the ending: `jmp $205f8` in the table of modes
ENDING_MODE_JUMP = 0x791e
SAVIOR2_ENDING = 0x205f8
SAVIOR2_CREDITS_STEP = 0x12             # $8(a5) of Vampire Savior 2's ending: staff credits
SAVIOR_MODULE = 0x21a20                 # Vampire Savior's ending mode (moved)
SAVIOR_END_STEP = 4                     # where Vampire Savior's ending leaves its script
JEDAH = 0x0f
RANDOM_CHOICE = 0x0b                    # no character: Vampire Savior's table repeats Zabel there

SCROLL_BANK_REGISTER = 0x8040c0
ALL_SCROLL_LAYERS = 7
SCROLL_BANK_CHIP_SIZE = 0x400000

# Vampire Savior's graphics: the scroll layers start 8 MB in (MAME's bank_scroll 4 for CPS2)
SAVIOR_GRAPHICS_CHIPS = (('vm3.13m', 'vm3.15m', 'vm3.17m', 'vm3.19m'),
                         ('vm3.14m', 'vm3.16m', 'vm3.18m', 'vm3.20m'))
HALF = 0x1000000
SCROLL_GRAPHICS_START = 0x800000
GRAPHICS_SIZE = 0x2000000
TILE_SIZE_OF_LAYER = {1: 64, 2: 128, 3: 512}
# codes Vampire Savior 2 fills empty layers with: they must stay blank in the scroll bank
BLANK_CODES = {1: 0x0020, 2: 0x4220, 3: 0x0600}

# moved code that adds a tile base to the codes it writes: the loaders of the tilemaps
# (addi.w #n, dN) store our new codes as they are; the layer fill at 0x14ffa writes
# 0x3810 + 1 (its only use, by Lord Raptor's script) to scroll 2
LOADER_ADDS = (0x1f498, 0x1f49c, 0x1f4a8, 0x1f4ac, 0x1f86c)
FILL_ADD = 0x15002
FILL_CODE = 0x3811


class Layout:
    """where each moved range is"""

    def __init__(self, start):
        self.places = []
        address = start
        for first, end in recipe.CODE_RANGES:
            self.places.append((first, end, address))
            address += (end - first + 1) & ~1
        for first, end in recipe.DATA_BLOCKS:
            address = (address + 1) & ~1
            self.places.append((first, end, address))
            address += end - first
        self.language_table = address
        self.end = address + 16

    def __call__(self, savior_address):
        if savior_address == recipe.LANGUAGE_TABLE:
            return self.language_table
        for first, end, address in self.places:
            if first <= savior_address < end:
                return address + savior_address - first
        raise SystemExit('endings: 0x%x did not move' % savior_address)


def savior_graphics(archive):
    """read(offset, length): Vampire Savior's 32 MB of graphics, unshuffled"""
    halves = [[archive.read(name) for name in names] for names in SAVIOR_GRAPHICS_CHIPS]

    def read(offset, length):
        offset %= GRAPHICS_SIZE
        return sprite_rom.read_raw(halves[offset // HALF], offset % HALF, length)
    return read


def scroll_numbers():
    """(layer, Vampire Savior code) -> its number in the scroll bank, and the bank's
    byte offset of each: scroll 3 first (32x32), then 2, then 1, around the blank codes"""
    wanted = {(layer, code) for _, layer, code, _ in recipe.SCROLL_ENTRIES} | {(2, FILL_CODE)}
    reserved = [(code * TILE_SIZE_OF_LAYER[layer], (code + 1) * TILE_SIZE_OF_LAYER[layer])
                for layer, code in BLANK_CODES.items()]
    numbers = {}
    position = 0
    for layer in (3, 2, 1):
        size = TILE_SIZE_OF_LAYER[layer]
        for code in sorted(code for (wanted_layer, code) in wanted if wanted_layer == layer):
            while True:
                position = (position + size - 1) // size * size
                clash = [end for start, end in reserved if start < position + size and position < end]
                if not clash:
                    break
                position = max(clash)
            numbers[(layer, code)] = position // size
            position += size
    if position > 4 * SCROLL_BANK_CHIP_SIZE:
        raise SystemExit('endings: the scroll bank is full')
    return numbers


def runner_hook(vsav2e, extension, place, pool, table_entries):
    """a class table and a hook for one object pool; returns where the next thing goes"""
    table, classes, runner = POOLS[pool]
    entries = bytearray(vsav2e[table:table + 4 * classes])
    for entry in table_entries:
        entries += struct.pack('>I', entry)
    table_address = place
    extension.put(table_address, entries)
    hook = table_address + len(entries)
    extension.put(hook, bytes.fromhex(
        '7000'          # moveq   #0, d0
        '102e0002'      # move.b  2(a6), d0       the class
        'd040'          # add.w   d0, d0
        'd040'          # add.w   d0, d0
        '41f9') + struct.pack('>I', table_address) + bytes.fromhex(   # lea table, a0
        '20700000'      # movea.l 0(a0, d0.w), a0
        '7000'          # moveq   #0, d0
        '4ed0'))        # jmp     (a0)            its routine returns to the runner
    hook_end = hook + 24
    site = vsav2e.find(RUNNER_DISPATCH, runner, runner + 0x40)
    if site < 0 or vsav2e[site + 14:site + RUNNER_DISPATCH_SIZE] != RUNNER_DISPATCH_END:
        raise SystemExit('endings: unexpected code in the object runner 0x%x' % runner)
    vsav2e[site:site + RUNNER_DISPATCH_SIZE] = (b'\x4e\xb9' + struct.pack('>I', hook)      # jsr hook
                                                + b'\x4e\x71' * 6)                      # nop
    return hook_end


class ExtensionWriter:
    def __init__(self, extension, base):
        self.data = extension
        self.base = base

    def put(self, address, data):
        offset = address - self.base
        if offset + len(data) > len(self.data):
            raise SystemExit('endings: the program extension is full')
        self.data[offset:offset + len(data)] = data


def apply(vsav2e, savior_program, savior_archive, extension, extension_base, start, upper_bank):
    """Moves the endings into vsav2e (a bytearray: the 4 MB program) and the extension (a
    bytearray from extension_base; the endings go from start). upper_bank: the four chips
    of the upper sprite bank (SpriteRoms). Returns (end of the extension used, the four
    chips of the scroll bank)."""
    writer = ExtensionWriter(extension, extension_base)
    layout = Layout(start)

    # code and data as they are
    for first, end, address in layout.places:
        writer.put(address, savior_program[first:end])
    texts = struct.pack('>4I', layout(recipe.TEXT_JAPANESE), layout(recipe.TEXT_ENGLISH),
                        layout(recipe.TEXT_ENGLISH), layout(recipe.TEXT_ENGLISH))
    writer.put(layout.language_table, texts)

    # patches
    for address, size, value in recipe.VALUE_PATCHES:
        writer.put(layout(address), value.to_bytes(size, 'big'))
    for address, target in recipe.MOVED_POINTERS:
        if struct.unpack('>I', savior_program[address:address + 4])[0] != target:
            raise SystemExit('endings: unexpected pointer at 0x%x of Vampire Savior' % address)
        writer.put(layout(address), struct.pack('>I', layout(target)))

    # sprite tiles: at their own numbers in the upper bank
    graphics = savior_graphics(savior_archive)
    for first, last in recipe.SPRITE_TILES:
        for tile in range(first, last + 1):
            sprite_rom.write_raw(upper_bank.chips, (tile & 0x1ffff) * 128, graphics(tile * 128, 128))

    # scroll tiles: renumbered in the scroll bank
    scroll_bank = [bytearray(b'\xff' * SCROLL_BANK_CHIP_SIZE) for _ in range(4)]
    numbers = scroll_numbers()
    for (layer, code), number in numbers.items():
        size = TILE_SIZE_OF_LAYER[layer]
        sprite_rom.write_raw(scroll_bank, number * size, graphics(SCROLL_GRAPHICS_START + code * size, size))
    for address, layer, code, added in recipe.SCROLL_ENTRIES:
        writer.put(layout(address), struct.pack('>H', (numbers[(layer, code)] - added) & 0xffff))
    for address in LOADER_ADDS:
        writer.put(layout(address) + 2, b'\x00\x00')
    writer.put(layout(FILL_ADD) + 2, struct.pack('>H', numbers[(2, FILL_CODE)] - (FILL_CODE - 0x3810)))

    # object pools
    place = (layout.end + 1) & ~1
    for pool, classes in recipe.MOVED_CLASSES.items():
        place = runner_hook(vsav2e, writer, place, pool, [layout(entry) for _, entry in classes])

    # the ending mode
    dispatcher = place
    bank = struct.pack('>I', SCROLL_BANK_REGISTER)
    writer.put(dispatcher, bytes.fromhex(
        '7000'                  # 00 moveq   #0, d0
        '102d0130'              # 02 move.b  $130(a5), d0        the character
        '0c0000%02x' '642c'       # 06 cmpi.b  #JEDAH, d0 / bcc savior2
        '0c0000%02x' '6726'       # 0c cmpi.b  #RANDOM_CHOICE, d0 / beq savior2
        '0c6d%04x0008' '6510'   # 12 cmpi.w  #SAVIOR_END_STEP, $8(a5) / bcs ported
        '661c'                  # 1a bne     savior2             Savior 2's credits and after
        % (JEDAH, RANDOM_CHOICE, SAVIOR_END_STEP))
        + b'\x42\x79' + bank                                    # 1c clr.w   scroll bank
        + bytes.fromhex('3b7c%04x0008' % SAVIOR2_CREDITS_STEP)  # 22 move.w  #credits, $8(a5)
        + bytes.fromhex('600e')                                 # 28 bra     savior2
        # ported:
        + bytes.fromhex('33fc%04x' % ALL_SCROLL_LAYERS) + bank  # 2a move.w  #7, scroll bank
        + b'\x4e\xf9' + struct.pack('>I', layout(SAVIOR_MODULE))  # 32 jmp   the moved mode
        # savior2:
        + b'\x4e\xf9' + struct.pack('>I', SAVIOR2_ENDING))      # 38 jmp     Savior 2's
    place = dispatcher + 0x3e
    original = b'\x4e\xf9' + struct.pack('>I', SAVIOR2_ENDING)
    if vsav2e[ENDING_MODE_JUMP:ENDING_MODE_JUMP + 6] != original:
        raise SystemExit('endings: unexpected code at the ending mode')
    vsav2e[ENDING_MODE_JUMP:ENDING_MODE_JUMP + 6] = b'\x4e\xf9' + struct.pack('>I', dispatcher)
    return place, scroll_bank
