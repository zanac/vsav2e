# Analysis: vsav2 + vhunt2

## The sets

| | vsav2 | vhunt2 |
|---|---|---|
| Program | 4 MB (`vs2j.03`-`.10`), CPS2 encrypted (`vsav2.key`) | 4 MB (`vh2j.03a`-`.10`) |
| Graphics | 32 MB (`vs2.13m`-`.20m`) | 32 MB (`vh2.13m`-`.20m`) |
| QSound samples | 8 MB (`vs2.11m`, `vs2.12m`) | 8 MB (`vh2.11m`, `vh2.12m`) |

The graphics are loaded `ROM_LOAD64_WORD` and unshuffled in 2 MB banks like MAME's
`cps2_gfx_decode` (`tools/analysis/gfx.py`). A 16x16 tile is 128 bytes; pen 15 is
transparent, so an empty tile is all `0xff`. A sprite's tile code is 18 bits
(`code + ((y & 0x6000) << 3)`): 262144 tiles, the 32 MB limit of the board.

Scroll layers on CPS2 (`cps2` config, banks 4/4/4): scroll1 8x8 code `c` is in 16x16 tile
`(c + 0x20000) >> 1`, scroll2 16x16 code `c` is tile `c + 0x10000`, scroll3 32x32 code `c`
is tiles `(c + 0x4000) * 4` to `+3`.

## Graphics: what differs

- `vs2.14m`, `.16m`, `.18m`, `.20m` (the upper 16 MB) are the same chips in both games; of
  the lower 16 MB, 26 MB in total are identical.
- Each game's own graphics are one contiguous block, tiles `0x52ef`-`0xff85`:
  - vhunt2: 40904 tiles (5.0 MB) not in vsav2;
  - vsav2: 43739 tiles (5.3 MB) not in vhunt2.
- In vhunt2 that block is exactly the three characters vsav2 lacks (from the tracer,
  tiles given to the nearest traced owner):

| Character (id) | Tiles | Size |
|---|---|---|
| Jon Talbain / Gallon (0x02) | 11545 | 1.41 MB |
| Rikuo / Aulbath (0x09) | 14066 | 1.72 MB |
| Sasquatch (0x0a) | 15293 | 1.87 MB |
| total | 40904 | 5.0 MB |

## What vsav2 could free

| What | Size | Note |
|---|---|---|
| Empty tiles in runs of 16 or more | 4144 tiles, 0.5 MB | largest at `0x3fa50` (1456), `0x1fbd0` (1073), `0x114dc` (808) |
| Duplicate tiles | 3090 tiles, 0.4 MB | hard to use: sprites use blocks of consecutive tiles |
| Endings | ~1-1.7 MB | per-character tiles only seen in that character's run to the ending |
| Intro and attract | up to ~2.6 MB | tiles seen only in attract mode; the title must stay |

About 4-4.6 MB against the 5.0 needed: within the original 32 MB only by cutting intro,
endings and some animation frames.

## Sound

8 MB of QSound samples, full in both. 64.8% of vhunt2's samples (32-byte blocks, any
alignment) also exist in vsav2; 2.8 MB do not (the three characters' voices and the
Vampire Hunter music instruments).

## RAM (both games)

| Address | What |
|---|---|
| `ff8782` | player 1 character id (poke it during the select screen to pick any character) |
| `ff8b82` | player 2 character id |
| `ff8450`, `ff8452` | player 1 vitality (288 full) |
| `ff8850`, `ff8852` | player 2 vitality |

Character ids: `0x00`-`0x0a`, `0x0c`-`0x19` (`0x0b` and from `0x1a` crash to attract).

## Routes

1. Original sizes (real CPS2): free ~5 MB (intro, endings, empty/duplicate tiles, some
   frames), copy the three characters there and rewrite their tile references in the
   program.
2. Extra graphics bank (mame2003-plus already has CPS2Turbo, y bit 12 selects the upper
   half of a 64 MB sprite ROM): vhunt2's block at the same offsets in the upper half and a
   hook setting the bit for the three characters' sprites; QSound needs a similar
   extension for the voices.
