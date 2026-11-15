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
  Vampire Savior 2's staff credits; the others play Vampire Savior 2's ending;
- the scripts ask for the music of Vampire Savior's endings (`moveq #n, d0` before a call
  of its sound request routine): n becomes the number tools/build/sound.py gave that music.
"""
import struct

from build import endings_recipe as recipe
from build import new_endings
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


def _reserved():
    """the byte ranges of the bank that the blank tile codes of the layers point at"""
    return [(code * TILE_SIZE_OF_LAYER[layer], (code + 1) * TILE_SIZE_OF_LAYER[layer])
            for layer, code in BLANK_CODES.items()]


def next_free(position, layer):
    """the first place from `position` where a tile of the layer fits, clear of the blank codes"""
    size = TILE_SIZE_OF_LAYER[layer]
    while True:
        position = (position + size - 1) // size * size
        clash = [end for start, end in _reserved() if start < position + size and position < end]
        if not clash:
            return position
        position = max(clash)


def scroll_layout():
    """(layer, Vampire Savior code) -> its number in the scroll bank (scroll 3 first, 32x32,
    then 2, then 1, around the blank codes), and the byte offset after the last tile"""
    wanted = {(layer, code) for _, layer, code, _ in recipe.SCROLL_ENTRIES} | {(2, FILL_CODE)}
    numbers = {}
    position = 0
    for layer in (3, 2, 1):
        size = TILE_SIZE_OF_LAYER[layer]
        for code in sorted(code for (wanted_layer, code) in wanted if wanted_layer == layer):
            position = next_free(position, layer)
            numbers[(layer, code)] = position // size
            position += size
    return numbers, position


def scroll_numbers():
    numbers, position = scroll_layout()
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


# --- music: Vampire Savior's routine that sends a sound request (number in d0), and the
# numbers of the music of its endings (two pieces by character, 0x30 and 0x34 are not used)
SAVIOR_SOUND_REQUEST = 0x21d66
# It keeps the number in $c(a5) and starts the sender `moveq #2, d0` / `jmp $4d60`, whose
# case 2 sends that number. Vampire Savior 2's sender (0x51a0) sends its own ending music
# (0x38) in case 2, so the moved routine jumps to a sender of its own instead.
SOUND_REQUEST_SENDER_CALL = 0x21d76                 # in Vampire Savior's routine
SAVIOR2_SENDER_CALL = bytes.fromhex('70024ef9000051a0')   # what it is once moved
SAVIOR2_SOUND_OFF = 0xa6            # $a6(a5) set: no sound (Vampire Savior 2's sender too)
SAVIOR2_SAVE_REGISTERS = 0x330e
SAVIOR2_RESTORE_REGISTERS = 0x3306
SAVIOR2_SEND_SOUND = 0x31da         # d1: the number
ENDING_MUSIC = sorted(set(range(0x25, 0x34)) - {0x30} | set(range(0x35, 0x40)) | {0x42, 0x43, 0x44})


def music_requests(savior_program):
    """the `moveq #n, d0` of the moved code followed by a call of (jsr) or a jump to (jmp)
    the sound request routine, with n one of the ending music: [(address, n)]"""
    calls = (b'\x4e\xb9' + struct.pack('>I', SAVIOR_SOUND_REQUEST),
             b'\x4e\xf9' + struct.pack('>I', SAVIOR_SOUND_REQUEST))
    found = []
    for first, last in recipe.CODE_RANGES:
        for address in range(first, last - 6, 2):
            if (savior_program[address] == 0x70 and savior_program[address + 1] in ENDING_MUSIC
                    and bytes(savior_program[address + 2:address + 8]) in calls):
                found.append((address, savior_program[address + 1]))
    return found


# --- the characters of the endings that are not Vampire Savior's ------------------------

FIRST_NEW_ID = 0x10
# The new endings borrow another character's tables (palettes, animations) for the ending
# mode's own set up: $130(a5), the character, holds DONOR during the ending and the real
# one is kept here (a byte of RAM nothing uses); the text pager and the script lookup read it.
DONOR = 0x00
REAL_CHARACTER = 0x0ff8
CHARACTER_READS = (0x21ac8, 0xcd9c)       # moved `move.b $130(a5), d0`
CHARACTER_READ = bytes.fromhex('102d0130')
SCRIPT_TABLE = 0x21b06                  # Vampire Savior's scripts by character (moved)
SCRIPT_LOOKUP = 0x21ace                 # in the moved mode: movea.l table(pc,d0.w),a0 / jsr (a0)
SCRIPT_LOOKUP_ORIGINAL = bytes.fromhex('207b00364e90')
NO_SCRIPT = 0x8cdf0                     # an rts in the moved scripts: no ending
SCRIPT_HOOK_SIZE = 0x1e


def script_hook(old_table, new_table):
    """d0 = the character * 4: the script's address into a0 (the old table below 0x10, the
    new one from there), then jumps to it (the call returns to the mode)"""
    return (bytes.fromhex('0c40' '0040')                      # cmpi.w  #0x40, d0
            + bytes.fromhex('650c')                           # bcs.s   old
            + bytes.fromhex('0440' '0040')                    # subi.w  #0x40, d0
            + b'\x41\xf9' + struct.pack('>I', new_table)      # lea     new, a0
            + bytes.fromhex('6006')                           # bra.s   fetch
            + b'\x41\xf9' + struct.pack('>I', old_table)      # old: lea old, a0
            + bytes.fromhex('2070' '0000')                    # fetch: movea.l (a0, d0.w), a0
            + bytes.fromhex('4ed0'))                          # jmp     (a0)


def write_dispatcher(writer, address, layout, new_characters):
    """the ending mode's entry (see the module's description); returns the end"""
    bank = struct.pack('>I', SCROLL_BANK_REGISTER)
    code = bytearray()
    fixups = []                                   # (position of a displacement byte, label)
    labels = {}

    def branch(opcode, label):
        code.extend([opcode, 0])
        fixups.append((len(code) - 1, label))

    code += bytes.fromhex('7000' '102d0130')                  # moveq #0, d0 / move.b $130(a5), d0
    code += bytes.fromhex('4a6d0008')                         # tst.w   $8(a5)
    branch(0x66, 'later')                                     # bne.s   later
    code += bytes.fromhex('1b40%04x' % REAL_CHARACTER)        # move.b  d0, real_character(a5)
    branch(0x60, 'classify')                                  # bra.s   classify
    labels['later'] = len(code)
    code += bytes.fromhex('102d%04x' % REAL_CHARACTER)        # move.b  real_character(a5), d0
    labels['classify'] = len(code)
    code += bytes.fromhex('0c00%04x' % 0x0f)                  # cmpi.b  #JEDAH, d0
    branch(0x65, 'low')                                       # bcs.s   low
    for character in new_characters:
        code += bytes.fromhex('0c00%04x' % character)         # cmpi.b  #character, d0
        branch(0x67, 'check')                                 # beq.s   check
    branch(0x60, 'savior2')                                   # bra.s   savior2
    labels['low'] = len(code)
    code += bytes.fromhex('0c00%04x' % RANDOM_CHOICE)         # cmpi.b  #RANDOM_CHOICE, d0
    branch(0x67, 'savior2')                                   # beq.s   savior2
    labels['check'] = len(code)
    code += bytes.fromhex('0c6d%04x0008' % SAVIOR_END_STEP)   # cmpi.w  #SAVIOR_END_STEP, $8(a5)
    branch(0x65, 'ported')                                    # bcs.s   ported
    branch(0x66, 'savior2')                                   # bne.s   savior2     Savior 2's credits
    code += b'\x42\x79' + bank                                # clr.w   scroll bank
    code += bytes.fromhex('1b6d%04x0130' % REAL_CHARACTER)    # move.b  real_character(a5), $130(a5)
    code += bytes.fromhex('3b7c%04x0008' % SAVIOR2_CREDITS_STEP)   # move.w #credits, $8(a5)
    branch(0x60, 'savior2')                                   # bra.s   savior2
    labels['ported'] = len(code)
    code += bytes.fromhex('4a6d0008')                         # tst.w   $8(a5)
    branch(0x66, 'enter')                                     # bne.s   enter
    code += bytes.fromhex('0c00%04x' % FIRST_NEW_ID)          # cmpi.b  #FIRST_NEW_ID, d0
    branch(0x65, 'enter')                                     # bcs.s   enter
    code += bytes.fromhex('1b7c%04x0130' % DONOR)             # move.b  #DONOR, $130(a5)   (step 0 of a new ending)
    labels['enter'] = len(code)
    code += bytes.fromhex('33fc%04x' % ALL_SCROLL_LAYERS) + bank   # move.w #7, scroll bank
    code += b'\x4e\xf9' + struct.pack('>I', layout(SAVIOR_MODULE))  # jmp  the moved mode
    labels['savior2'] = len(code)
    code += b'\x4e\xf9' + struct.pack('>I', SAVIOR2_ENDING)   # jmp     Savior 2's
    for position, label in fixups:
        code[position] = labels[label] - (position + 1)
    writer.put(address, bytes(code))
    return address + len(code) + (len(code) & 1)


class ExtensionWriter:
    def __init__(self, extension, base):
        self.data = extension
        self.base = base

    def put(self, address, data):
        offset = address - self.base
        if offset + len(data) > len(self.data):
            raise SystemExit('endings: the program extension is full')
        self.data[offset:offset + len(data)] = data


def apply(vsav2e, savior_program, savior_archive, extension, extension_base, start, upper_bank, music,
          assets=None):
    """Moves the endings into vsav2e (a bytearray: the 4 MB program) and the extension (a
    bytearray from extension_base; the endings go from start). upper_bank: the four chips
    of the upper sprite bank (SpriteRoms). music: Vampire Savior's number of each piece of
    the ending music -> vsav2e's. Returns (end of the extension used, the four
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

    # the music: vsav2e's numbers
    requests = music_requests(savior_program)
    if {number for _, number in requests} != set(ENDING_MUSIC):
        raise SystemExit('endings: unexpected requests of the ending music')
    for address, number in requests:
        writer.put(layout(address) + 1, bytes([music[number]]))
    sender = (layout.end + 1) & ~1
    long = lambda value: struct.pack('>I', value)
    writer.put(sender, bytes.fromhex('4a2d%04x' '661c' % SAVIOR2_SOUND_OFF)   # tst.b $a6(a5) / bne.s done
               + b'\x4e\xb9' + long(SAVIOR2_SAVE_REGISTERS)                # jsr     save
               + bytes.fromhex('7200' '122d000c' '7400' '7600')              # moveq #0,d1 / move.b $c(a5),d1 / d2, d3 = 0
               + b'\x4e\xb9' + long(SAVIOR2_SEND_SOUND)                     # jsr     send
               + b'\x4e\xf9' + long(SAVIOR2_RESTORE_REGISTERS)              # jmp     restore and return
               + b'\x4e\x75')                                               # done: rts
    call = layout(SOUND_REQUEST_SENDER_CALL)
    if bytes(extension[call - extension_base:call - extension_base + 8]) != SAVIOR2_SENDER_CALL:
        raise SystemExit('endings: unexpected code in the moved sound request routine')
    writer.put(call, b'\x4e\xf9' + long(sender) + b'\x4e\x71')           # jmp sender / nop

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
    place = sender + 0x24
    for pool, classes in recipe.MOVED_CLASSES.items():
        place = runner_hook(vsav2e, writer, place, pool, [layout(entry) for _, entry in classes])

    # the endings of the characters Vampire Savior has none for
    place, new_scripts, scroll_end = new_endings.place(writer, layout, (place + 1) & ~1, assets, scroll_bank,
                                                       scroll_layout()[1], next_free, savior_program)

    # the ending mode
    dispatcher = place
    place = write_dispatcher(writer, dispatcher, layout, sorted(new_scripts))
    # the scripts of the characters Vampire Savior has no ending for: a table by character
    # (from id 0x10) read by a hook where the moved mode looks the script up (only when the
    # build has pictures for some of them)
    if new_scripts:
        hook = place
        table = hook + SCRIPT_HOOK_SIZE
        place = table + 4 * (max(new_scripts) - FIRST_NEW_ID + 1)
        old_lookup = layout(SCRIPT_LOOKUP)
        if bytes(extension[old_lookup - extension_base:old_lookup - extension_base + 6]) != SCRIPT_LOOKUP_ORIGINAL:
            raise SystemExit('endings: unexpected code in the moved ending mode')
        for address in CHARACTER_READS:
            read = layout(address)
            if bytes(extension[read - extension_base:read - extension_base + 4]) != CHARACTER_READ:
                raise SystemExit('endings: unexpected code at 0x%x' % address)
            writer.put(read + 2, struct.pack('>H', REAL_CHARACTER))
        writer.put(old_lookup, b'\x4e\xb9' + struct.pack('>I', hook))         # jsr hook
        writer.put(hook, script_hook(layout(SCRIPT_TABLE), table))
        for character in range(FIRST_NEW_ID, max(new_scripts) + 1):
            writer.put(table + 4 * (character - FIRST_NEW_ID),
                       struct.pack('>I', new_scripts.get(character) or layout(NO_SCRIPT)))
    original = b'\x4e\xf9' + struct.pack('>I', SAVIOR2_ENDING)
    if vsav2e[ENDING_MODE_JUMP:ENDING_MODE_JUMP + 6] != original:
        raise SystemExit('endings: unexpected code at the ending mode')
    vsav2e[ENDING_MODE_JUMP:ENDING_MODE_JUMP + 6] = b'\x4e\xf9' + struct.pack('>I', dispatcher)
    return place, scroll_bank
