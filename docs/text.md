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
roster. Ids `10`, `11`, `13` have quotes written for Vampire Savior 2 and are still
Japanese: to translate (the PlayStation game shows them in English).

The proportional Latin font of the quotes is still in vsav2's graphics: the English
quotes display correctly with no graphics change.

Vampire Hunter 2's quotes match none of Vampire Savior's.

## Not done yet

Endings (same text format, blocks found next to the quotes), the three untranslated
characters, the Japanese in graphics (if any), the remaining system text.
