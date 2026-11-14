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
bytes, ended by `(0xffffffff, 0)`: 393 files. No readable English text appears in the
archive as plain ASCII, so the texts are in a custom encoding or compressed: next step.
