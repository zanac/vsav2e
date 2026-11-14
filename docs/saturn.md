# The Sega Saturn Vampire Savior (Japan)

The Saturn is the only home version besides the PlayStation one that has Donovan, Huitzil
and Pyron, and it runs the arcade animation more faithfully (it needs Capcom's 4 MB RAM
cartridge). It is Japan only (T-1229G, 1998), so every text of it is Japanese; the English
texts of vsav2e come from the PlayStation version (see `psx.md`).

This note is about what the disc holds and how the three endings were captured from it.
Nothing extracted from the disc is in the repository.

## The disc

Track 1 is an ordinary ISO 9660 data track (MODE1/2352); the other 18 are the CD audio
(music). The files of the endings:

| File | What |
|---|---|
| `END10.BG`, `END11.BG`, `END13.BG` | background of the ending of Huitzil (`10`), Pyron (`11`) and Donovan (`13`); the other `ENDxx.BG` are the other characters, `END18.BG` is the staff roll. A compressed format that starts with `TK` |
| `ENDAT10.DAT`, `ENDAT11.DAT`, `ENDAT13.DAT` | a table of 17 offsets, then the pictures, their palettes (4 x 0x400 bytes) and the text of the ending; `ENDATCMN.DAT` is the part all share |
| `ENDANITA.DAT` | the picture of Anita of Donovan's ending |
| `ENDING.PRG` | the program of the endings (SH-2) |

The character numbers are those of the arcade game, so the same as in `endings.md`
(`13` Donovan, `10` Huitzil, `11` Pyron).

The pictures of the endings are not bitmaps in VDP2: while an ending runs, the VDP2 memory
does not change at all and the picture is made of VDP1 sprites whose texture goes to
VDP1 VRAM at 0x30000-0x36000 (8-24 KB, replaced at every new picture). That is why the
captures are the practical way to get them: the picture window is 224 x 128 pixels of a
352 x 240 screen, drawn as they are (the dither of the picture is part of it).

## Running it: tools/saturn

`satrun.c` is `tools/psx/psxrun.c` for Beetle Saturn (same environment variables: `PRESS`,
`SHOTS`, `DUMPS`, `VDUMPS`, `POKES`, `STATE_SAVE`, `STATE_LOAD`). It sets the core option
that inserts the 4 MB RAM cartridge, which the game needs (without it the game shows a
warning in Japanese and stops).

- Core: https://github.com/libretro/beetle-saturn-libretro (`make`), with
  `beetle-saturn-vdp.patch` applied so that it hands out the VDP2 VRAM/CRAM/registers and
  the VDP1 VRAM (`VDUMPS`).
- BIOS: a Japanese one in `SYSDIR`, named `sega_101.bin` (Saturn 1.01 (J)). The BIOS is not in
  the repository.
- Build: `gcc -O2 -Wall -o satrun tools/saturn/satrun.c -ldl`
- The speed is about 60 frames a second when nothing else runs, a full capture takes some
  six minutes (the game is a long arcade run).

Session: the START of the title at frame 3400 (the logo of Capcom and the opening come
first), then the mode menu and the character select (arcade mode) around frame 4200.

## RAM

The offsets below are indexes into the work RAM array that the core hands out (`satrun` writes
there): 2 MB, low RAM first, then high RAM, and every 16-bit word stored the other way round
(little-endian), so the Saturn address of a byte is `0x06000000 + (offset - 0x100000)` with
bit 0 flipped. Example: `ENDING.PRG` sits at offset `0x174000`, that is `0x06074000`.
The files other than `ENDING.PRG` are not in the work RAM: the game loads them into the 4 MB
RAM cartridge, which the core does not hand out.

| Offset | What |
|---|---|
| `194126` and 7 more (`capture_endings.py`) | the character under the cursor of the select screen (arcade ids): writing the id there while the cross button is pressed picks it, also the characters that are not on the screen |
| `19446c`, `19446e` | vitality of player 2 (and the copy the bar shows); `0x90` is full, the first blow wins a round if it is 0 |
| `194184`, `194186` | vitality of player 1 (`0xdc` for Donovan); writing 1 empties its bar, so keeping it at its maximum makes it unbeatable |
| `1940d0` | a counter that goes down slowly with the round (not the clock the bar shows) |

## The texture compression (found)

The textures of the sprites of the endings are not stored as they sit in the VDP1 VRAM: `ENDATxx.DAT`
holds them compressed with a small LZ made of 16-bit words, which the game expands while it
uploads them (the queue of uploads is filled by the routine at `0x06012286`, the expansion is
`0x0601606e`/`0x06017268`). `tools/saturn/vdp1lz.py` is the decoder and its docstring describes the
format (a header, a command stream, a stream of literal words; commands for literals, earlier
literals, a repeat of the last word and copies from the row above). Checked against the VDP1 VRAM
of the running game: the same bytes (2-4 bytes of padding after the end of a texture aside).

How it was found: `PCHIST` of `satrun` lists the executed addresses between two frames, and the
core of `beetle-saturn-vdp.patch` also counts which code reads the cartridge RAM (entries 2 and 3
of the histogram, for CPU 0 and 1, in the same file). The loops that read the cartridge RAM but are
not the CD driver, a memset or a copy led to the sprite engine at `0x06012340`-`0x06012740` and from
there to the uploader. What is still to decode is how the sprites are put together: the chunks of
`ENDATxx.DAT` are listed by 16-byte entries (position, size) that the sprite engine reads, the width
of a texture comes from there. `END*.BG` (a header `TK`) was not seen being read in the endings
and keeps its own format.

## The endings

`tools/saturn/capture_endings.py` replays the whole session (it is deterministic): the
character is poked on the select screen and the vitality of player 2 kept at 0. Donovan
wins every fight; Huitzil and Pyron are beaten by the last one (Jedah), so for them that
fight is saved and replayed with random attacks (seed 1) until it is won. The ending
starts with the fight's bonus screen, then:

- **Donovan** (state frame 300-1500, 9 pictures of the text): Anita asleep, the blade
  Dyrek, Donovan's hand.
- **Huitzil** (frames 1660-4860 of the second pass): the broken robot Phobos, the robots,
  the soldier and the beam on the city.
- **Pyron** (frames from 1900): his hand and the galaxy.

After each one the staff roll, the same for all (`END18.BG`).
