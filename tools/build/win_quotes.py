"""English win quotes for Vampire Savior 2.

Capcom already translated them: the European Vampire Savior (`vsav`) holds every
language in one ROM. Twelve characters of Vampire Savior 2 have exactly the Japanese
quotes of Vampire Savior, so their English quotes are taken as they are. The step:

  1. reads the Japanese and English master tables of `vsav`;
  2. for each character id of `vsav2`, looks for the `vsav` character with the same
     Japanese quotes and takes its English block;
  3. gives Jon Talbain, Rikuo and Sasquatch (not selectable in vsav2, their ids share
     another character's block) their own English quotes from `vsav`;
  4. writes the new master table in free ROM space and points the English, Spanish and
     Portuguese entries of the language table at it.

Characters with quotes written for Vampire Savior 2 (Donovan, Huitzil, Pyron and the
boss) have no English in `vsav`: they keep the Japanese block until they are translated.
"""
import struct

from cps2 import quotes

# vsav2: the language table (4 long pointers) and its only, Japanese, master table
VSAV2_LANGUAGE_TABLE = 0xf954
ENGLISH, SPANISH, PORTUGUESE = 1, 2, 3

# vsav (Europe): the master tables of the win quotes
VSAV_JAPANESE_MASTER_TABLE = 0x32d196
VSAV_ENGLISH_MASTER_TABLE = 0x3355a0

# character ids (the same in vsav, vsav2 and vhunt2) of the three characters that only
# Vampire Savior and Vampire Hunter 2 have
ONLY_IN_SAVIOR_1 = {0x02: 'Jon Talbain', 0x09: 'Rikuo', 0x0a: 'Sasquatch'}


def apply(vsav2_program, vsav_program, free_space_address, free_space_end):
    """writes the English master table at free_space_address; returns the address after
    it and the ids of the characters still in Japanese"""
    language_table = struct.unpack_from('>4I', vsav2_program, VSAV2_LANGUAGE_TABLE)
    japanese_table_address = language_table[0]

    savior_japanese = [quotes.read_block(vsav_program, address) for address in
                       quotes.read_master_table(vsav_program, VSAV_JAPANESE_MASTER_TABLE)]
    savior_english = [quotes.read_block(vsav_program, address) for address in
                      quotes.read_master_table(vsav_program, VSAV_ENGLISH_MASTER_TABLE)]

    english_blocks, untranslated_ids = [], []
    block_cache = {}        # block address in vsav2 -> the quotes chosen for it
    for character_id, block_address in enumerate(
            quotes.read_master_table(vsav2_program, japanese_table_address)):
        if character_id in ONLY_IN_SAVIOR_1:
            english_blocks.append(savior_english[character_id])
            continue
        if block_address not in block_cache:
            japanese = quotes.read_block(vsav2_program, block_address)
            matches = [index for index, block in enumerate(savior_japanese) if block == japanese]
            if matches:
                block_cache[block_address] = savior_english[matches[0]]
            else:
                block_cache[block_address] = japanese
                untranslated_ids.append(character_id)
        english_blocks.append(block_cache[block_address])

    data = quotes.encode_master_table(english_blocks)
    if free_space_address + len(data) > free_space_end:
        raise SystemExit('win quotes: no room')
    vsav2_program[free_space_address:free_space_address + len(data)] = data
    for language in (ENGLISH, SPANISH, PORTUGUESE):
        struct.pack_into('>I', vsav2_program, VSAV2_LANGUAGE_TABLE + 4 * language, free_space_address)
    return free_space_address + len(data), untranslated_ids
