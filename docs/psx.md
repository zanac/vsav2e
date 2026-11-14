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


## Running the game: tools/psx/psxrun.c

A small scriptable libretro frontend (no window, no sound) around PCSX-ReARMed, whose
built-in HLE BIOS means no Sony BIOS is needed. Inputs, pictures, RAM dumps and RAM pokes
are given per frame in environment variables (see the comment at the top of the file).
Build: `gcc -O2 -Wall -o psxrun tools/psx/psxrun.c -ldl`; the core is
`pcsx_rearmed_libretro.so` from https://github.com/libretro/pcsx_rearmed
(`make -f Makefile.libretro`). The interpreter is used by default (`DYNAREC=1` turns the
recompiler on; it crashed once while RAM was being poked).

Session used so far: START at frame 2600 and 2800 (title, ARCADE), cross from 3000 every
200 frames (character, mode, ...): the first fight (Demitri against Victor) starts around
frame 5050.

## RAM (US version, also the GameShark codes)

| Address (RAM offset) | What |
|---|---|
| `1c0e54`, `1c0e56` | player 1 vitality (`0x120` full) |
| `1c1228`, `1c122a` | player 2 vitality |
| `1c1112` / `1c14e6` | player 1 / player 2 character |
| `1c1d70`-`1c1d76` | endings and portraits seen (all `ffff`, `3fff` at `1c1d72`, unlock them in COLLECTION) |
| `1c1d78` | `3` enables the DX and EX option modes |

## Win quotes

The win quote after a match is drawn in a proportional font (e.g. Victor: "I used to be
just bits and pieces, now it's your turn!"), but the sentence is in RAM in no simple form:
no ASCII, and no sequence with the same letter pattern (any one-to-one encoding, 8, 16 or
32 bits per letter, with or without spaces). So it is probably a pre-rendered picture
loaded from the disc for each quote, which would make the PlayStation a source to read
(screenshots) rather than to extract.
