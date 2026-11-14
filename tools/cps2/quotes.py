"""The text format of Vampire Savior's win quotes (and endings), shared by Vampire
Savior (`vsav`), Vampire Savior 2 (`vsav2`) and Vampire Hunter 2 (`vhunt2`).

Layout in the program ROM, from the top down:

  language table   4 long pointers (Japanese, English, Spanish, Portuguese), each to a
                   master table. The language comes from the board's region. In vsav2
                   and vhunt2 all four point at the Japanese master table.
  master table     one 16-bit offset per character id (33 ids), measured from the start
                   of the master table, to that character's block. Characters that are
                   not in the game share another character's block.
  block            16-bit offsets, measured from the start of the block, to each quote;
                   the first offset is also the size of the offset list plus 2, because
                   a zero word closes the list. 16 win quotes per character.
  quote            lines; each line is a 16-bit character count followed by that many
                   16-bit character codes; a zero count ends the quote.

A character code's low 9 bits are the tile of the letter. Latin text uses ASCII + 0xa0
(space is 0xc0, 'a' is 0x101); the upper bits (0x2000, 0x3000) are the letter's spacing
in the proportional font and must be kept. Japanese text uses other tiles of the same
font, with 0x1020 as its space.
"""
import struct

CHARACTER_ID_COUNT = 33
QUOTES_PER_CHARACTER = 16
LATIN_TILE_OFFSET = 0xa0
TILE_MASK = 0x1ff


def read_word(program, address):
    return struct.unpack_from('>H', program, address)[0]


def read_quote(program, address):
    """the lines of the quote at address (tuples of character codes)"""
    lines = []
    while True:
        character_count = read_word(program, address)
        address += 2
        if character_count == 0:
            return lines
        lines.append(struct.unpack_from('>%dH' % character_count, program, address))
        address += 2 * character_count


def read_block(program, block_address):
    """the quotes of one character's block"""
    quote_count = (read_word(program, block_address) - 2) // 2
    offsets = struct.unpack_from('>%dH' % quote_count, program, block_address)
    return [read_quote(program, block_address + offset) for offset in offsets]


def read_master_table(program, table_address):
    """block address of every character id"""
    offsets = struct.unpack_from('>%dH' % CHARACTER_ID_COUNT, program, table_address)
    return [table_address + offset for offset in offsets]


def encode_quote(lines):
    data = b''
    for line in lines:
        data += struct.pack('>H%dH' % len(line), len(line), *line)
    return data + b'\x00\x00'


def encode_block(quotes):
    """a block: the offset list, its closing zero word, then the quotes"""
    header_size = 2 * len(quotes) + 2
    offsets, body = [], b''
    for quote in quotes:
        offsets.append(header_size + len(body))
        body += encode_quote(quote)
    return struct.pack('>%dH' % len(quotes), *offsets) + b'\x00\x00' + body


def encode_master_table(blocks_by_character_id):
    """a master table followed by its blocks; characters given the same list of quotes
    (the same object) share one block"""
    table_size = 2 * len(blocks_by_character_id)
    offsets, body, offset_of_block = [], b'', {}
    for quotes in blocks_by_character_id:
        key = id(quotes)
        if key not in offset_of_block:
            offset_of_block[key] = table_size + len(body)
            body += encode_block(quotes)
        offsets.append(offset_of_block[key])
    if table_size + len(body) > 0x10000:
        raise ValueError('the blocks do not fit the 16-bit offsets of a master table')
    return struct.pack('>%dH' % len(offsets), *offsets) + body


def line_text(line):
    """a line as text, for listings (non-Latin codes shown as <hex>)"""
    text = ''
    for code in line:
        ascii_code = (code & TILE_MASK) - LATIN_TILE_OFFSET
        text += chr(ascii_code) if 0x20 <= ascii_code < 0x7f else '<%x>' % code
    return text
