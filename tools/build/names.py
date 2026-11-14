"""The names of the characters on screen, as the Western versions of Darkstalkers have them.

Six characters have a Japanese name and a Western one:

    Bulleta  -> B.B. Hood        Gallon  -> Jon Talbain     Zabel  -> Lord Raptor
    Aulbath  -> Rikuo            Lei-Lei -> Hsien-Ko        Phobos -> Huitzil

Vampire Savior had both and chose by region; Vampire Savior 2 dropped the choice but
kept Capcom's graphics of the Western names, in each of the three places where names are
drawn. vsav2e points those places at them:

- the select and VS screens: a table of 32 animation steps by character id at 0x2a08de,
  each step 4 bytes and its frame pointer the long at 0x2a08e2 + 4 * id (the frames are
  at 0x2a643c-0x2a6570; the Western ones, from 0x2a651c, are not used);
- the score ranking: the same kind of table at 0x2a0862 (frames 0x2a730e-0x2a7426, the
  Western ones from 0x2a73ee);
- the names over the vitality bars: 32 records of 8 bytes at 0x9910e, by id: tile (in
  the font of tiles 0x14680-0x147ff, minus 0x4200), attributes (width in tiles), x and
  y. A wider or narrower name also gets the x that centres it, like the others of its
  width.

The table entries of the ids that are not characters (the random choice, a dark Gallon,
the copies from 0x14) repeat the characters', so every entry is changed by its value.

Capcom spelt Lord Raptor "L.Rapter" in these graphics, and the select screen has
"BabyBonnieHood" where the other two places have "B.B.Hood".
"""
import struct

SELECT_NAME_FRAMES = 0x2a08e2
RANKING_NAME_FRAMES = 0x2a0862
TABLE_ENTRIES = 32

# Japanese name frame -> Western name frame
SELECT_NAMES = {
    0x2a643c: 0x2a6562,     # Bulleta  -> BabyBonnieHood
    0x2a6458: 0x2a651c,     # Gallon   -> J.Talbain
    0x2a6474: 0x2a652a,     # Zabel    -> L.Rapter
    0x2a64ba: 0x2a6538,     # Aulbath  -> Rikuo
    0x2a64f2: 0x2a6554,     # Lei-Lei  -> Hsien-Ko
    0x2a64d6: 0x2a6546,     # Phobos   -> Huitzil
}
RANKING_NAMES = {
    0x2a730e: 0x2a744a,     # BULLETA  -> B.B.HOOD
    0x2a732a: 0x2a73ee,     # GALLON   -> J.TALBAIN
    0x2a7346: 0x2a73fc,     # ZABEL    -> L.RAPTER
    0x2a738c: 0x2a740a,     # AULBATH  -> RIKUO
    0x2a73c4: 0x2a7426,     # LEI-LEI  -> HSIEN-KO
    0x2a73a8: 0x2a7418,     # PHOBOS   -> HUITZIL
}

VITALITY_NAMES = 0x9910e
VITALITY_RECORD_SIZE = 8
# Japanese name tile -> (Western name tile, width in tiles)
VITALITY_NAME_TILES = {
    0x048a: (0x04b3, 3),    # Bulleta  -> B.B.Hood
    0x049c: (0x04ad, 3),    # Gallon   -> J.Talbain
    0x049e: (0x048d, 3),    # Zabel    -> L.Rapter
    0x04dd: (0x054e, 2),    # Aulbath  -> Rikuo
    0x04a4: (0x04ed, 3),    # Lei-Lei  -> Hsien-Ko
    0x04ab: (0x04b6, 2),    # Phobos   -> Huitzil
}
# the x of a name, by its width in tiles: centred on the place of the name
VITALITY_NAME_X = {2: -16, 3: -24}


def replace_frame_pointers(vsav2e, table, replacements):
    changed = 0
    for entry in range(TABLE_ENTRIES):
        address = table + 4 * entry
        frame = struct.unpack_from('>I', vsav2e, address)[0]
        if frame in replacements:
            struct.pack_into('>I', vsav2e, address, replacements[frame])
            changed += 1
    return changed


def apply(vsav2e):
    """Changes the names in the vsav2e program (a bytearray)."""
    select = replace_frame_pointers(vsav2e, SELECT_NAME_FRAMES, SELECT_NAMES)
    ranking = replace_frame_pointers(vsav2e, RANKING_NAME_FRAMES, RANKING_NAMES)
    vitality = 0
    for entry in range(TABLE_ENTRIES):
        address = VITALITY_NAMES + VITALITY_RECORD_SIZE * entry
        tile, attributes, x, y = struct.unpack_from('>HHhh', vsav2e, address)
        if tile in VITALITY_NAME_TILES:
            new_tile, width = VITALITY_NAME_TILES[tile]
            attributes = (attributes & ~0x0f00) | (width - 1) << 8
            struct.pack_into('>HHhh', vsav2e, address, new_tile, attributes, VITALITY_NAME_X[width], y)
            vitality += 1
    if not (select and ranking and vitality):
        raise SystemExit('names: a table of names was not found')
    print('names: %d select screen entries, %d ranking entries, %d vitality bar entries'
          % (select, ranking, vitality))
