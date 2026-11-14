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
half. The four chips that differ (`vh2.13m`, `.15m`, `.17m`, `.19m`) go in `vsav2e.zip`
as they are; the other four are Vampire Savior 2's, loaded twice.

## Hardware

Neither fits a CPS2 board: the sprite space is full (32 MB) and so is the program space
(4 MB, then the object output registers at `0x400000`). vsav2e runs on a CPS2 with the
two bigger ROM spaces of CPS2Turbo (Zero800's hardware for Street Fighter Zero 3 Mix,
already in mame2003-plus), and nothing else of it:

- program ROM up to `0x5fffff`. The game never uses the object output at `0x400000`,
  only its mirror at `0xfffff0`;
- 64 MB of sprite ROM, bit 12 of the sprite Y selecting the upper half.

mame2003-plus: `MACHINE_DRIVER( vsav2e )` in `src/drivers/cps2.c` (branch `vsav2e` of the
fork).

On a stock CPS2 (MAME's `vsav2d`, `tools/dev/install_for_mame.py`) the build still runs:
only the three characters are wrong there.

## Testing

MAME cannot run the extended set, so it is tested in the mame2003-plus core with
`tools/dev/libretro_run.c`, a small libretro frontend with no display: inputs,
screenshots and memory writes by frame, like `tools/trace/drive.lua`. The memory writes
(to pick a character, to win a match) need a core built with
`tools/dev/mame2003plus-dev-memory.patch`, which is for development only.

```
cc -O2 -o libretro_run tools/dev/libretro_run.c -ldl
OUT=work/talbain_ SHOTS="1700 2000 2600" PRESS="900:coin;1000:start;1330:b1;1400:b1" \
POKES="1300-1800:ff8782:02" MASH=1900 AUTOWIN=1700 \
./libretro_run mame2003_plus_libretro.so roms/vsav2e.zip 3000
```

`roms/` holds `vsav2e.zip` and its parent `vsav2.zip` (MAME's, with `vsav2d/phoenix.key`
inside).

## Not done yet

- The select screen: the three characters can only be reached by writing their id.
- Sound: Vampire Savior 2's QSound ROMs lack their voices (2.8 MB of Vampire Hunter 2's
  samples are not in them).
- The names on screen are the Japanese ones (Gallon, Aulbath; also Zabel, Bulleta,
  Phobos...).
