# The full roster: Jon Talbain, Rikuo and Sasquatch

## What Vampire Savior 2 still has

The three characters only Vampire Hunter 2 lets you pick (ids `02`, `09`, `0a`) are still
in Vampire Savior 2's program: writing the id to `ff8782` on the select screen starts a
match with one of them, with its name, its moves and its hit boxes, and the same match
runs in both games. They are invisible. Two things were removed:

- the **frames**. An animation is a list of steps (in the object, `$1c(a6)` points to the
  current one); the long at offset 4 of a step points to its frame, the list of sprites of
  one picture. In Vampire Savior 2 every frame pointer of the three characters points to
  the end of the character's animations (`0x137e7c`, `0x1cf506`, `0x1d872e`), where the
  word `000a` is read as a frame type that draws nothing. 1893 + 1700 + 1677 pointers.
- the **tiles**: each game has its own block of sprite tiles, `0x52ef`-`0xff85`
  (`docs/analysis.md`); Vampire Hunter 2's is these three characters.

The portraits (select screen, VS screen, win screen), the palettes and the win quotes of
Vampire Savior are still there.

## Frames

```
type 2, sprites with their own attributes     type 0, sprites that share them
word   2                                      word   0
word   room the frame takes in the list       word   number of sprites
word   number of sprites - 1                  word   attributes
long   pointer to the shape                   long   pointer to the shape
for each sprite: word tile, word attributes   for each sprite: word tile
```

The shape gives x and y (two words) for each sprite. Other types exist (4, 6 and 8 draw
from sprite bank 1, 12 is a list of frames with offsets, 10 draws nothing); the three
characters only use 0 and 2.

Three places read the type and jump to its routine through a table (`0x199dc`,
`0x1a248`, `0x1a262` in `vsav2`): the normal one, and two that draw with other position
rules. They are reached from the code that takes the frame of an object and from code
that already has a frame in `a0` (type 12, and `0x197d2`). Every routine builds the
sprite as x `OR $1a(a6)`, y `OR $18(a6)`: the object's words with the priority and the
sprite bank bits.

In Vampire Hunter 2 a character's data is laid out as animations, then frames, then
other tables; its frames are at `0x12a310`-`0x134fc0` (Jon Talbain), `0x1cc57e`-`0x1d6638`
(Rikuo), `0x1df860`-`0x1e6e30` (Sasquatch): 741, 767 and 687 frames used.

## What vsav2e does (`tools/build/roster.py`)

1. Matches the animation steps of the two games. The data is the same but for the
   pointers and a few steps Vampire Savior 2 dropped, so the steps are compared by the
   bytes before their frame pointer (`difflib`); all the pointers find their step.
2. Copies the frames and their shapes to a **program extension at `0x400000`**
   (`vs2e.10x`, about 200 KB used) and sets the frame pointers.
3. Hooks the three dispatch places: for a frame above `0x400000` the hook sets bit 12 of
   `$18(a6)`, calls the routine and clears the bit.

The tiles are not copied: the sprite ROMs of Vampire Hunter 2 are the **upper half of a
64 MB sprite space**, at the same tile numbers, and bit 12 of a sprite's Y selects that
half. The four chips that differ (`vh2.13m`, `.15m`, `.17m`, `.19m`) go in `vsav2e.zip` as
`vs2e.21m`, `.23m`, `.25m`, `.27m`, with the new tiles of the select screen in tiles that
were empty (from `0x1fc00`); the other four are Vampire Savior 2's, loaded twice.

## Hardware

Neither fits a CPS2 board: the sprite space is full (32 MB) and so is the program space
(4 MB, then the object output registers at `0x400000`). vsav2e runs on a CPS2 with the
two bigger ROM spaces of CPS2Turbo (Zero800's hardware for Street Fighter Zero 3 Mix,
already in mame2003-plus), and nothing else of it:

- program ROM up to `0x5fffff`. The game never uses the object output at `0x400000`,
  only its mirror at `0xfffff0`;
- 64 MB of sprite ROM, bit 12 of the sprite Y selecting the upper half;
- 16 MB of QSound samples (the chip addresses 256 banks of 64 KB; CPS2 games use half).

And two things of its own, for the endings (`docs/endings.md`): the program extension is
2 MB, and a scroll bank of 16 MB of graphics after the sprites, which the scroll layers
read while bits 0-2 of the word written to `0x8040c0` are set.

mame2003-plus: `MACHINE_DRIVER( vsav2e )` in `src/drivers/cps2.c` (branch `vsav2e` of the
fork).

On a stock CPS2 (MAME's `vsav2d`, `tools/dev/install_for_mame.py`) the build only runs
up to the select screen, whose faces are a frame of the extension: MAME is still good for
the attract mode and for tracing code that does not depend on the extension.

## Testing

MAME cannot run the extended set, so it is tested in the mame2003-plus core with
`tools/dev/libretro_run.c`, a small libretro frontend with no display: inputs,
screenshots, memory writes and memory dumps by frame, like `tools/trace/drive.lua`, for
both players. Writing and dumping memory (to pick a character, to win a match, to look at
the sprite list and the palettes) need a core built with
`tools/dev/mame2003plus-dev-memory.patch`, which is for development only.

```
cc -O2 -o libretro_run tools/dev/libretro_run.c -ldl
OUT=work/talbain_ SHOTS="1700 2000 2600" PRESS="900:coin;1000:start;1330:b1;1400:b1" \
POKES="1300-1800:ff8782:02" MASH=1900 AUTOWIN=1700 \
./libretro_run mame2003_plus_libretro.so roms/vsav2e.zip 3000
```

`roms/` holds `vsav2e.zip` and its parent `vsav2.zip` (MAME's, with `vsav2d/phoenix.key`
inside).

## The select screen

All 18 characters and the random choice, laid out like the PlayStation Darkstalkers 3's
screen: `tools/build/select_screen.py` explains the screen and each change (the new
cells, the faces and their palettes, the cursors, the cursor moves, the random choice).
What it needs to know about the game:

| What | Where (`vsav2`) |
|---|---|
| Frame with all the faces | `0x2a6e52`, pointed to by `0x2a17ba`; Vampire Hunter 2's is at `0x2932d0` in its program |
| Cursor frames | three tables of 32 pointers by character id: `0x2a17be` (player 1), `0x2a183e` (player 2), `0x2a18be` |
| Cursor position | `0x6bc78`: x, y words by id (y goes up) |
| Cursor moves | `0x1588e`: 8 ids by id, for right, left, down, up, right-down, left-down, right-up, left-up; the joystick bits pick the column through the table at `0x1fe2c` |
| Random choice | list of 15 ids at `0x1f8b4`, read at `0x1f8ac` |
| Sprite palettes | block of 32 at `0x3baf3c` (scene 1 of the blocks from `0x3bab3c`, 0x400 apart), loaded at `0x1ac9c` and `0x1aeb6` |

Character ids: `00` Bulleta (B.B. Hood), `01` Demitri, `02` Gallon (Jon Talbain), `03`
Victor, `04` Zabel (Lord Raptor), `05` Morrigan, `06` Anakaris, `07` Felicia, `08`
Bishamon, `09` Aulbath (Rikuo), `0a` Sasquatch, `0b` the random choice, `0c` Q-Bee, `0d`
Lei-Lei (Hsien-Ko), `0e` Lilith, `0f` Jedah, `10` Phobos (Huitzil), `11` Pyron, `12` a dark
Gallon, `13` Donovan.

Sprite palettes on this screen: `01` texts, `03` the speed choice, `04` the name, `05`-`14`
the faces, `15` and `17` player 1's character (main and second palette), `18` and `1a`
player 2's, `1b` and `1c` the two portraits, `1e` and `1f` the cursors. `16` and `19` were
free; `1d` was the pink filling of three cells; `00` and `02` are loaded but not drawn
with (their colours in the block are also read by other code).

The three new cells come from the PlayStation screen (`assets/psx/select/*.png`, one
capture per character): the tombstone is the same drawing in other colours, 8 pixels to
the left and 8 down in the captures.

## Names

Jon Talbain, Rikuo, Lord Raptor, B.B. Hood, Hsien-Ko and Huitzil have their Western
names on the select and VS screens, in the score ranking, over the vitality bars and
under the faces of the "Master of" list in the credits: `tools/build/names.py` (Capcom's
own graphics, still in the game). The default records (score ranking, "Master of") and
the service menu's game data use the Western initials too: BBH, TAL, RAP, RIK, HSI,
HUI instead of BUL, GAL, ZAB, AUL, LEI, PHO.

## Sound

`tools/build/sound.py` explains the sound program (sequences, instruments, samples) and
what is added. In short: the number the 68000 asks a sound with is the same in the two
games, and Vampire Savior 2 simply has no sequence for the three characters' voices; 121
sequences of Vampire Hunter 2 are copied (all the ones Vampire Savior 2 lacks but the
music), with Vampire Hunter 2's instruments as eight more banks and its two sample ROMs
as a second 8 MB of QSound samples (`vh2.11m`, `vh2.12m`, in `vsav2e.zip` as they are).
The music of Vampire Savior's endings is copied too, after them (`docs/endings.md`).

Checked by recording the sound of the same match with the new and the old sound program
(`AUDIO` of `tools/dev/libretro_run.c`; the runs are identical frame by frame): for the
three characters the two recordings differ only where a voice is added, and the added
sound of Jon Talbain's entrance is the one Vampire Hunter 2 plays at the same moment; for
another character the recordings are the same to the sample.

## Not done yet

- Vampire Hunter 2's music is not copied (the three characters fight on Vampire Savior
  2's stages, with their music), but for the three stage themes the endings of Donovan,
  Huitzil and Pyron will play, slowed and remixed (`tools/build/stage_music.py`).
