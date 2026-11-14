# Darkstalkers 3 (PlayStation, SLUS-00745): source of the English texts

The disc image stays outside the repository (it is far over GitHub's 100 MB limit); the
build reads it from a path given on the command line, and only the pieces we take from it
go into the repository.

## Disc

One MODE2/2352 data track, ISO 9660. Files:

| File | Size | What |
|---|---|---|
| `SLUS_007.45` | 514048 | the executable; has the font test strings and a few menu strings in ASCII |
| `VS.ARC` | 86984704 | main archive of the game data |
| `COL/ART01.BMP`-`ART32.BMP` | 308278 each | gallery artwork (plain BMP) |
| `OPENING.XA`, `END1-5.XA`, `WIN1-4.XA`, `BGM1-6.XA`, `INNER*.XA`, `DUM*.XA` | | XA audio (music, voices) |
| `CAPCOM15.STR` | | logo movie |

## VS.ARC

Starts with a table of 8-byte entries `(first sector, sector count)`, sectors of 2048
bytes, ended by `(0xffffffff, 0)`: 393 files.

What is where so far:

- Entries 2, 236, 237, 300: menu strings in plain ASCII (`HANDI CAP`, `PRESS START BUTTON
  TO EXIT`, the options and collection menus with the character names in capitals:
  `J.TALBAIN`, `L.RAPTER`, `RIKUO`, `SHADOW`, `MARIONETTE`, ...). `SLUS_007.45` has the
  internal names list (`AULBATH`, `GALLON`, `HUITZIL`, `BULLETA`, ...).
- Entries from 38 on come in groups of four of about 280 sectors, one group per character:
  tables of pointers into RAM (`0x800b....`, `0x8014....`) and data.
- Win quotes and endings are not in the archive as text in any simple form: an
  offset-independent search (differences between consecutive bytes, as 8-bit and as 16-bit
  little and big endian) for common English words finds only the menu strings. They are
  compressed, or drawn from pre-rendered images.

