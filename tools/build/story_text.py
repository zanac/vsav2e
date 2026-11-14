"""The texts written for Vampire Savior 2 (endings, Jedah's welcome), in English.

They use the same format as the win quotes (tools/cps2/quotes.py) and their own
language tables: 4 long pointers each (Japanese, English, Spanish, Portuguese), all to
the Japanese data in vsav2. A table here is small: a list of 16-bit offsets to blocks.

The English is ours (text/vsav2_story_en.py). Each letter needs the spacing bits of the
proportional font together with its tile; they are taken from Capcom's English quotes in
Vampire Savior, where every letter always has the same code.
"""
import collections
import struct

import vsav2_story_en
from cps2 import quotes

# vsav2 language tables and the blocks of each (in the order of the original table)
ENDINGS_LANGUAGE_TABLE = 0xf964
JEDAH_LANGUAGE_TABLE = 0xf974
ENGLISH, SPANISH, PORTUGUESE = 1, 2, 3

# vsav (Europe): every English master table (win quotes, two sets of dialogue, endings)
VSAV_ENGLISH_MASTER_TABLES = (0x3355a0, 0x33b130, 0x33c5e4, 0x33f2ee)


# the longest line of each text. The endings scroll with several lines on screen:
# 24-letter lines work, 29-letter ones crash the game. Capcom's own English lines never
# pass 30 letters.
ENDING_LINE_LENGTH = 24
DIALOGUE_LINE_LENGTH = 30


# The ending centres each line by moving its start left by (letters - 1) * 8 pixels
# (`asl.w #3, d0` at 0x8b246), right for the 16-pixel kanji but twice too much for the
# Western letters, which advance 8 pixels: the shift becomes `asl.w #2, d0`.
ENDING_CENTRING_SHIFT_ADDRESS = 0x8b246
ENDING_CENTRING_SHIFT_ORIGINAL = bytes.fromhex('e740')     # asl.w #3, d0
ENDING_CENTRING_SHIFT_WESTERN = bytes.fromhex('e540')      # asl.w #2, d0


def latin_codes(vsav_program):
    """ASCII character -> its 16-bit code (tile and spacing), learnt from all the
    English texts of Vampire Savior (win quotes, endings and the other two tables)"""
    seen = collections.defaultdict(collections.Counter)
    block_addresses = set()
    for master_table in VSAV_ENGLISH_MASTER_TABLES:
        block_count = quotes.read_word(vsav_program, master_table) // 2
        offsets = struct.unpack_from('>%dH' % block_count, vsav_program, master_table)
        block_addresses.update(master_table + offset for offset in offsets)
    for block_address in sorted(block_addresses):
        for quote in quotes.read_block(vsav_program, block_address):
            for line in quote:
                for code in line:
                    ascii_code = (code & quotes.TILE_MASK) - quotes.LATIN_TILE_OFFSET
                    if 0x20 <= ascii_code < 0x7f:
                        seen[chr(ascii_code)][code] += 1
    return {character: codes.most_common(1)[0][0] for character, codes in seen.items()}


def encode_text(blocks, code_of, maximum_line_length):
    """blocks of quotes of text lines -> blocks of quotes of code lines"""
    encoded = []
    for block in blocks:
        encoded_block = []
        for quote in block:
            for line in quote:
                if len(line) > maximum_line_length:
                    raise SystemExit('story text: line too long (%d): %r' % (len(line), line))
                missing = [c for c in line if c not in code_of]
                if missing:
                    raise SystemExit('story text: no letter %r in the font (%r)' % (missing[0], line))
            encoded_block.append([tuple(code_of[c] for c in line) for line in quote])
        encoded.append(encoded_block)
    return encoded


def check_same_shape(vsav2_program, table_address, blocks, name):
    """the English must have the original number of blocks, quotes and lines"""
    block_count = quotes.read_word(vsav2_program, table_address) // 2
    offsets = struct.unpack_from('>%dH' % block_count, vsav2_program, table_address)
    original = [quotes.read_block(vsav2_program, table_address + offset) for offset in offsets]
    shape = lambda all_blocks: [[len(quote) for quote in block] for block in all_blocks]
    if shape(original) != shape(blocks):
        raise SystemExit('story text: %s does not have the original lines' % name)


def apply(vsav2_program, vsav_program, free_space_address, free_space_end):
    """writes the English tables at free_space_address; returns the address after them"""
    code_of = latin_codes(vsav_program)
    end = ENDING_CENTRING_SHIFT_ADDRESS + len(ENDING_CENTRING_SHIFT_ORIGINAL)
    if vsav2_program[ENDING_CENTRING_SHIFT_ADDRESS:end] != ENDING_CENTRING_SHIFT_ORIGINAL:
        raise SystemExit('story text: unexpected code at the ending centring')
    vsav2_program[ENDING_CENTRING_SHIFT_ADDRESS:end] = ENDING_CENTRING_SHIFT_WESTERN
    for language_table, name, maximum_line_length, blocks in (
            (ENDINGS_LANGUAGE_TABLE, 'endings', ENDING_LINE_LENGTH,
             [vsav2_story_en.ENDING, vsav2_story_en.ENDING_JEDAH]),
            (JEDAH_LANGUAGE_TABLE, "Jedah's welcome", DIALOGUE_LINE_LENGTH,
             [vsav2_story_en.JEDAH_WELCOME, vsav2_story_en.JEDAH_WELCOME_TO_JEDAH])):
        japanese_table = struct.unpack_from('>I', vsav2_program, language_table)[0]
        check_same_shape(vsav2_program, japanese_table, blocks, name)
        data = quotes.encode_master_table(encode_text(blocks, code_of, maximum_line_length))
        if free_space_address + len(data) > free_space_end:
            raise SystemExit('story text: no room')
        vsav2_program[free_space_address:free_space_address + len(data)] = data
        for language in (ENGLISH, SPANISH, PORTUGUESE):
            struct.pack_into('>I', vsav2_program, language_table + 4 * language, free_space_address)
        free_space_address += len(data) + (len(data) & 1)
    return free_space_address
