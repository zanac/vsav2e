"""Builds the vsav2e program from the original ones, step by step."""
import struct

from cps2 import program
from build import story_text, win_quotes

# The region is an immediate word in the boot code (`move.w #region, $90(a5)` at
# 0x10cc): 0 Japan, 2 USA, 4 Hispanic, 6 Oceania, 8 Asia, 0xa Europe, 0xc Brazil.
# It selects the language (English for Europe) and the warning screen.
REGION_WORD_ADDRESS = 0x10ce
REGION_EUROPE = 0x000a

# The language of the win quotes and endings is a byte of the operator settings (copied
# to $93(a5) at 0x1a5c by `move.b $8(a4), $93(a5)`): 0 Japanese, 2 English, 4 Spanish,
# 6 Portuguese. Vampire Savior 2 has no menu to change it, so the copy is replaced by
# `move.b #2, $93(a5)`: always English.
LANGUAGE_COPY_ADDRESS = 0x1a5c
LANGUAGE_COPY_ORIGINAL = bytes.fromhex('1b6c00080093')
LANGUAGE_ALWAYS_ENGLISH = bytes.fromhex('1b7c00020093')

# unused (0xff) space of the program ROM
FREE_SPACE_START = 0xebc00
FREE_SPACE_END = 0xff000


def build(rom_directory):
    """the vsav2e program (4 MB, as the 68000 sees it)"""
    # the decrypted set is the base: its code can be patched, and the result needs no
    # encryption key (it runs as a "Phoenix" set)
    vsav2e = bytearray(program.load_program('vsav2d', rom_directory))
    savior = program.load_program('vsav', rom_directory)

    struct.pack_into('>H', vsav2e, REGION_WORD_ADDRESS, REGION_EUROPE)

    end = LANGUAGE_COPY_ADDRESS + len(LANGUAGE_COPY_ORIGINAL)
    if vsav2e[LANGUAGE_COPY_ADDRESS:end] != LANGUAGE_COPY_ORIGINAL:
        raise SystemExit('unexpected code at the language copy: not the vsav2d program')
    vsav2e[LANGUAGE_COPY_ADDRESS:end] = LANGUAGE_ALWAYS_ENGLISH

    free_space, untranslated = win_quotes.apply(vsav2e, savior, FREE_SPACE_START, FREE_SPACE_END)
    print('win quotes: 0x%x-0x%x, still Japanese for character ids %s'
          % (FREE_SPACE_START, free_space, ', '.join('%02x' % i for i in untranslated)))
    story_end = story_text.apply(vsav2e, savior, free_space, FREE_SPACE_END)
    print('endings and Jedah: 0x%x-0x%x' % (free_space, story_end))
    return bytes(vsav2e)
