"""Builds the vsav2e program from the original ones, step by step."""
import os
import struct
import zipfile

from cps2 import program, sprite_rom
from build import endings, names, roster, select_screen, sound, story_text, title_screen, versus_stage, win_quotes
from build.extension import EXTENSION_START, Extension

# The region is an immediate word in the boot code (`move.w #region, $90(a5)` at
# 0x10cc): 0 Japan, 2 USA, 4 Hispanic, 6 Oceania, 8 Asia, 0xa Europe, 0xc Brazil.
# It selects the language (English for Europe) and the warning screen.
REGION_WORD_ADDRESS = 0x10ce
REGION_EUROPE = 0x000a

# The language of the win quotes and endings is a byte of the operator settings (copied
# to $93(a5) at 0x1a5c by `move.b $8(a4), $93(a5)`): 0 Japanese, 2 English, 4 Spanish,
# 6 Portuguese, chosen in the service menu (7. CONFIGURATION, LANGUAGE). Europe's factory
# setting is English; Spanish and Portuguese show the English texts.
#
# The menu item (0xe57a) goes through the word $92(a5) (the high byte 0, the language
# low) from d1 = 2 to 4: English and Spanish. vsav2e offers Japanese and English: the
# lowest choice becomes 0, the highest 2, and the test that wraps below the lowest
# becomes signed (`bcc` -> `bpl`), as 0 - 2 is not below 0 unsigned.
LANGUAGE_MENU_PATCHES = (
    (0xe584, '7202', '7200'),           # moveq #2, d1         lowest choice: Japanese
    (0xe594, '6402', '6a02'),           # bcc.s -> bpl.s       below the lowest: wrap
    (0xe596, '7404', '7402'),           # moveq #4, d2         to the highest: English
    (0xe5a0, '0c420004', '0c420002'),   # cmpi.w #4, d2        above the highest: wrap
)

# The decrypted set carries the "Phoenix Edition" boot menu (code at 0xff000, called at
# 0x110c right after the region is set). It reads its own region choice from the EEPROM
# and writes it over $90(a5): with no choice stored that is 0, Japan. vsav2e has one
# region, so the call is removed (three `nop`).
PHOENIX_MENU_CALL_ADDRESS = 0x110c
PHOENIX_MENU_CALL_ORIGINAL = bytes.fromhex('4eb9000ff000')      # jsr $ff000
PHOENIX_MENU_CALL_REMOVED = bytes.fromhex('4e714e714e71')

# Factory settings: one 0x30-byte block per region from 0x2366 (offsets at 0x2358). The
# first byte is the coinage: Europe's is 9 (2 coins, 1 credit), Japan's 0 (1 coin,
# 1 credit); vsav2e keeps the Japanese coinage.
EUROPE_DEFAULT_COINAGE_ADDRESS = 0x2366 + 5 * 0x30
EUROPE_DEFAULT_COINAGE = 9
ONE_COIN_ONE_CREDIT = 0

# unused (0xff) space of the program ROM
FREE_SPACE_START = 0xebc00
FREE_SPACE_END = 0xff000


# the sprite ROMs of Vampire Hunter 2 that become vsav2e's upper sprite bank (the other
# four are the same chips as Vampire Savior 2's)
HUNTER_SPRITE_ROMS = ('vh2.13m', 'vh2.15m', 'vh2.17m', 'vh2.19m')


def build(rom_directory, psx_directory):
    """vsav2e as (the 4 MB of the CPS2 program space as the 68000 sees it, the program
    extension at 0x400000, the four chips of the upper sprite bank that are not Vampire
    Savior 2's, the 256 KB sound program). psx_directory holds the PlayStation captures:
    select/ (the select screen) and title/ (the title screen)."""
    # the decrypted set is the base: its code can be patched, and the result needs no
    # encryption key (it runs as a "Phoenix" set)
    vsav2e = bytearray(program.load_program('vsav2d', rom_directory))
    savior = program.load_program('vsav', rom_directory)
    hunter = program.load_program('vhunt2', rom_directory)

    struct.pack_into('>H', vsav2e, REGION_WORD_ADDRESS, REGION_EUROPE)

    for address, original, patched in LANGUAGE_MENU_PATCHES:
        original, patched = bytes.fromhex(original), bytes.fromhex(patched)
        if vsav2e[address:address + len(original)] != original:
            raise SystemExit('unexpected code at the language menu 0x%x' % address)
        vsav2e[address:address + len(patched)] = patched

    end = PHOENIX_MENU_CALL_ADDRESS + len(PHOENIX_MENU_CALL_ORIGINAL)
    if vsav2e[PHOENIX_MENU_CALL_ADDRESS:end] != PHOENIX_MENU_CALL_ORIGINAL:
        raise SystemExit('unexpected code at the Phoenix menu call')
    vsav2e[PHOENIX_MENU_CALL_ADDRESS:end] = PHOENIX_MENU_CALL_REMOVED

    if vsav2e[EUROPE_DEFAULT_COINAGE_ADDRESS] != EUROPE_DEFAULT_COINAGE:
        raise SystemExit('unexpected factory settings for Europe')
    vsav2e[EUROPE_DEFAULT_COINAGE_ADDRESS] = ONE_COIN_ONE_CREDIT

    free_space, untranslated = win_quotes.apply(vsav2e, savior, FREE_SPACE_START, FREE_SPACE_END)
    print('win quotes: 0x%x-0x%x, still Japanese for character ids %s'
          % (FREE_SPACE_START, free_space, ', '.join('%02x' % i for i in untranslated)))
    story_end = story_text.apply(vsav2e, savior, free_space, FREE_SPACE_END)
    print('endings and Jedah: 0x%x-0x%x' % (free_space, story_end))
    names.apply(vsav2e)

    extension = Extension()
    roster_end = roster.apply(vsav2e, hunter, extension, story_end, FREE_SPACE_END)
    print('frame hook: 0x%x-0x%x' % (story_end, roster_end))

    with zipfile.ZipFile(os.path.join(rom_directory, 'vhunt2.zip')) as hunter_archive:
        upper_bank = sprite_rom.SpriteRoms([hunter_archive.read(name) for name in HUNTER_SPRITE_ROMS])
    select_end, select_tiles_end = select_screen.apply(vsav2e, hunter, extension, upper_bank,
                                                       os.path.join(psx_directory, 'select'),
                                                       roster_end, FREE_SPACE_END)
    print('select screen routines: 0x%x-0x%x' % (roster_end, select_end))
    title_end, logo_work = title_screen.apply(vsav2e, extension, upper_bank, select_tiles_end,
                                              os.path.join(psx_directory, 'title'), select_end, FREE_SPACE_END)
    versus_end = versus_stage.apply(vsav2e, extension, title_end, FREE_SPACE_END, logo_work)
    print('versus stage choice: 0x%x-0x%x' % (title_end, versus_end))

    # the endings: Vampire Savior's code, from its decrypted program
    savior_code = program.load_program('vsavd', rom_directory)
    endings_start = (extension.end() + 0xff) & ~0xff
    # the sound: Vampire Hunter 2's voices, Vampire Savior's ending music (new numbers)
    games = {}
    for game, prefix in (('vsav2', 'vs2'), ('vhunt2', 'vh2'), ('vsav', 'vm3')):
        with zipfile.ZipFile(os.path.join(rom_directory, game + '.zip')) as archive:
            games[game] = (archive.read(prefix + '.01') + archive.read(prefix + '.02'),
                           archive.read(prefix + '.11m') + archive.read(prefix + '.12m'))
    sound_program, music, stage_themes = sound.apply(games['vsav2'][0], games['vhunt2'][0], games['vsav2'][1],
                                                      games['vhunt2'][1], games['vsav'][0], games['vsav'][1],
                                                      endings.ENDING_MUSIC)
    with zipfile.ZipFile(os.path.join(rom_directory, 'vsav.zip')) as savior_archive:
        endings_end, scroll_bank = endings.apply(vsav2e, savior_code, savior_archive, extension.data,
                                                 EXTENSION_START, endings_start, upper_bank, music)
    extension.used = endings_end - EXTENSION_START
    print('endings: 0x%x-0x%x' % (endings_start, endings_end))
    print('program extension: 0x%x-0x%x' % (EXTENSION_START, extension.end()))

    return (bytes(vsav2e), bytes(extension.data), [bytes(chip) for chip in upper_bank.chips],
            [bytes(chip) for chip in scroll_bank], sound_program)
