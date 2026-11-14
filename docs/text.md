# Texts: where they are and how vsav2e gets them in English

## One ROM, four languages

Vampire Savior (`vsav` and its regional clones) holds Japanese, English, Spanish and
Portuguese in the same program; Vampire Savior 2 and Vampire Hunter 2 were built from it
and kept the machinery, but only the Japanese data.

| What | vsav2 | Notes |
|---|---|---|
| Region | `move.w #region, $90(a5)` at `0x10cc` (RAM `ff8090`) | 0 Japan, 2 USA, 4 Hispanic, 6 Oceania, 8 Asia, 0xa Europe, 0xc Brazil. An immediate in the code, so it is encrypted in the original set: vsav2e is built on the decrypted `vsav2d`. Changing it already gives the region's warning screen and system messages (all seven are still in the ROM). |
| Language | `$93(a5)` (RAM `ff8093`), copied from the operator settings at `0x1a5c` | 0 Japanese, 2 English, 4 Spanish, 6 Portuguese. vsav2e forces 2. |
| Win quotes | language table at `0xf954` (4 long pointers, all to `0x9ca24`), used at `0xb146` | format in `tools/cps2/quotes.py` |

## Win quotes

Master tables of `vsav` (Europe): Japanese `0x32d196`, English `0x3355a0` (Spanish and
Portuguese follow the same layout further on). 33 character ids, 16 quotes each.

Twelve characters of vsav2 have exactly Vampire Savior's Japanese quotes, so the English
ones are copied as they are (`tools/build/win_quotes.py`); ids `02`, `09`, `0a` (Jon
Talbain, Rikuo, Sasquatch) get their Vampire Savior quotes too, ready for the full
roster. Ids `10`, `11`, `13` (Huitzil, Pyron, Donovan) have quotes written for Vampire
Savior 2, never translated by Capcom for the arcade: the English is ours, in
`text/vsav2_win_quotes_en.py` (same number of lines as each Japanese quote; the font has
no digits, no `:` and no Q, X, Z).

The proportional Latin font of the quotes is still in vsav2's graphics: the English
quotes display correctly with no graphics change.

Vampire Hunter 2's quotes match none of Vampire Savior's.

## Endings and Jedah's welcome

Vampire Savior 2 replaced the per-character endings with one scrolling ending (plus one
for Jedah) and gave Jedah a speech before the last fight. Language tables (4 long
pointers, all to the Japanese data): `0xf964` endings (2 blocks: 18 and 11 one-line
quotes), `0xf974` Jedah (2 blocks of 4 quotes). They were never translated by Capcom:
the English is ours, in `text/vsav2_story_en.py`, written by `tools/build/story_text.py`.

- The kanji font is sprite tiles `0x14200 + code` (how the Japanese was read: rendered
  from the graphics ROM).
- With a Western language the game shows these texts in its Western style by itself
  (proportional spacing, light blue).
- Ending lines hold at most 24 letters: with 29 the game crashes (several lines are on
  screen at once; the limit is somewhere in between). Other lines at most 30.
- The ending renderer (object code at `0x8b1fc`) starts each line (letters - 1) * 8
  pixels left of the centre (`asl.w #3, d0` at `0x8b246`): right for the 16-pixel kanji,
  twice too much for the Western letters, which advance 8 pixels. vsav2e makes it
  `asl.w #2, d0`, so the lines are centred.

## Region: what else it changes

- The decrypted set has the "Phoenix Edition" boot menu (code at `0xff000`, called at
  `0x110c`): it reads a region choice from the EEPROM and writes it over `$90(a5)`, so
  the region set at `0x10cc` was lost (0, Japan, with nothing stored). vsav2e removes
  the call.
- Factory settings: one 0x30-byte block per region from `0x2366` (offsets at `0x2358`),
  ending with a date and a 12-letter name that differs per region, so a change of
  region rewrites the EEPROM. Byte 0 is the coinage (Japan, Oceania, Asia: 1 coin 1
  credit; USA, Europe: 2 coins 1 credit), byte 8 the language. vsav2e sets Europe's
  coinage to 1 coin 1 credit.

## Checked on screen

Warning, attract mode, title, character select, VS screen, fight (HUD, READY, FIGHT,
K.O., PERFECT, bonus), win quotes, continue, game over, score ranking, both endings,
credits: no Japanese left, and nothing Japanese is drawn in the graphics. Character
ids for tests: `0f` Jedah, `10` Huitzil, `11` Pyron, `13` Donovan; `12` is a dark
Talbain still in the game.

Not seen on screen: Jedah's welcome when the player is Jedah (second block of
`0xf974`); in a Jedah against Jedah game the fight starts with no speech.
