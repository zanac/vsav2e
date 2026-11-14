# The per-character endings

Vampire Savior 2 ends the same way for everybody (a scrolling text over pictures, and
one ending of its own for Jedah). Vampire Savior has an ending for each character —
pictures, animations and texts, in English and Japanese — and the PlayStation Darkstalkers
3 has the same ones. vsav2e plays Vampire Savior's ending for the 14 characters it has
(`00`-`0a`, `0c`-`0e`), then Vampire Savior 2's staff credits, ranking and game over;
Jedah and the three characters Vampire Savior does not have (Donovan, Huitzil, Pyron)
keep Vampire Savior 2's ending.

## How: the code moves, it is not rewritten

The two games are the same engine a year apart, so Vampire Savior's ending code is
copied from its decrypted program (`vsavd`, inside `vsav.zip`) into the program
extension and patched to run inside Vampire Savior 2. `tools/build/endings.py` does it
from a recipe, `tools/build/endings_recipe.py`, which lists what moves and every patch as
addresses and numbers (no data of the games). The recipe is made once by
`tools/dev/endings/gen_recipe.py` from an analysis that needs `capstone`:

1. **What the endings read.** MAME runs each character to the end of his ending and logs
   every read of the program ROM (`tools/dev/endings/tap.lua`; the logs of the 15
   characters are `tools/dev/endings/rom_reads.txt.gz`). This gives the data each
   ending uses and the code that reads it.
2. **What moves.** The ending mode (`0x21a20`), the 15 scripts (`0x8c8d2`-`0x91563`, a
   table by character at `0x21b06`), the text pager (`0xcd32`), the tilemap loaders
   (`0x1f034` scroll 1, `0x1f458` scroll 2, `0x1f856` scroll 3), a layer fill, the
   palette loaders (`0x1c130`), and the object classes the endings create that Vampire
   Savior 2 changed or dropped: pool 0 classes `40`-`4f` (pictures, characters, effects),
   pool 1 `31`, pool 3 `04`-`09` (palette animations, with their scripts and a table of
   palette bases inside their code), pool 4 `00`. The code is followed from its entry
   points (jump tables of words, tables of longs); a routine it calls that reads Vampire
   Savior data itself moves too.
3. **Where things are in Vampire Savior 2.** Both programs are disassembled and aligned
   instruction by instruction (unique windows of 8 instructions, extended both ways).
   This maps the routines the moved code calls to Vampire Savior 2's, and the RAM
   offsets from `a5` (some ranges moved: by `0x0e` around `-0x6190`, `0x12`, `0x80`
   around `0x7980`...). Every called routine is then checked instruction by instruction,
   immediates included: alike small routines (the palette fades) were first mapped one
   off. The object classes are matched through the class tables.
4. **Patches.** Absolute addresses in the moved code (code, data, RAM), `a5` offsets,
   object ids (a moved class gets a new number after Vampire Savior 2's own in its
   pool), pointers in the data (animation steps: the frame and the loop; frames: the
   shape; the tile animations of scroll 2: the tile block), pointers kept in the data
   parts of the moved code, the text durations (a table of longs at `0xcdd0` read with
   `movea.l (a0, d0.w)`), the language table (Japanese, then English for the three other
   languages).

## Graphics

- **Sprites.** A frame in the extension is drawn from the upper sprite bank (`roster.md`),
  and all the frames of the endings are drawn from sprite bank 1: their tiles
  (`0x10000`-`0x1ffff`, 5 000 of them) go to the upper bank at their own numbers, where
  Vampire Hunter 2's chips have nothing vsav2e draws.
- **Scroll layers.** They can't reach the upper sprite bank and Vampire Savior 2's
  graphics have half a megabyte free, while the endings need 1.4 MB of scroll tiles
  (most of the pictures are on scroll 3, 32x32 tiles). vsav2e has a **scroll bank**: 16
  MB of graphics after the 64 MB of sprites (`vs2e.29m`, `.31m`, `.33m`, `.35m`); while
  bits 0-2 of the word written to `0x8040c0` (unused on CPS2) are set, scroll 1-3 take
  their tiles from it. The ending mode sets them, and clears them before the credits.
  The tiles go there renumbered (scroll 3 first, then 2, then 1) and the tilemaps get the
  new numbers. The codes Vampire Savior 2's own code fills an empty layer with (`0020`,
  `4220`, `0600`) stay blank there. CPS2 scroll tiles start 8 MB into the graphics
  (`bank_scroll` 4 in MAME's CPS2 configuration).

## Hooks

- Each object pool used (0, 1, 3, 4): its runner (`moveq` / `move.b 2(a6)` / ... /
  `jsr (a0)`) calls a hook reading a longer class table.
- The ending mode (`jmp $205f8` at `0x791e`) jumps to a dispatcher: for a ported
  character it sets the scroll bank and runs the moved mode; when that mode reaches its
  step 4 (Vampire Savior's credits) the dispatcher clears the bank and continues at step
  `0x12` of Vampire Savior 2's ending, its staff credits.

## Music

The scripts ask for the music of the endings with `moveq #n, d0` / `jsr $21d66`, two
pieces by character (`0x25`-`0x2f`, `0x31`-`0x33`, `0x35`-`0x3f`, `0x42`-`0x44`).
Vampire Savior 2's sound program has other music under those numbers, or none, so:

- **The sequences are copied** from Vampire Savior's sound program (`vm3.01`, `vm3.02`)
  into vsav2e's, under new numbers (`0x50`-`0x6b`, free in Vampire Savior 2), and the
  `moveq` of the moved scripts get the new numbers (`tools/build/sound.py`,
  `tools/build/endings.py`). The sound program grows to 288 KB: the copies are in Z80
  banks 13-15 (`vs2e.02` is 160 KB).
- **The sender.** `0x21d66` keeps the number in `$c(a5)` and starts a delayed sender
  (`0x4d60`, case 2) that sends it. Vampire Savior 2's sender (`0x51a0`) sends its own
  ending music (`0x38`) in that case, so the moved routine jumps to a small sender of its
  own (the same code as Vampire Savior's case 2).
- **Instruments.** The two drivers are the same code. The instruments the endings use
  (logged from the Z80's reads in MAME, `tools/dev/endings/ztap.lua`: banks 0, 1, 5 and
  6) are Vampire Savior 2's but for three, so banks 1, 5 and 6 get copies (banks 16-18)
  with Vampire Savior's instruments; in a sequence of bank 13 or more `1f nn` picks bank
  nn through a small table. Their samples are all somewhere in vsav2e's 16 MB.
- **Sound effects.** The few the endings ask for (`0xe4`-`0xe8`, Zabel's and Sasquatch's)
  are the same sequences in Vampire Hunter 2, already copied for the three characters.

Things learnt:
- Sound number n plays the sequence of entry n + 1 of the table at `0x9001` (the driver
  reads `0x9006 + 4n`, after taking n modulo the word at `0x9000`): the MAME log of the
  Z80's reads through its bank window (`tools/dev/endings/btap.lua`) shows Demitri's
  ending, which asks for `0x26`, reading the sequence of entry `0x27`.
- Some entries point into the middle of other sequences: a sequence runs to the next
  one that starts after its last track, not to the next entry.
- A sequence that runs over the end of a 16 KB bank keeps its place in the window
  (the driver goes on in the next bank); two do.

Checked by recording each ending in both games with `tools/dev/libretro_run.c` (`AUDIO`
and `WATCH=618001,618003`, the number the 68000 writes to the QSound shared RAM) and
comparing the spectra of the two recordings from the request of each piece
(`tools/dev/endings/music_compare.py`): the same music, 0.8 to 1.0 of correlation over
3-second windows, against 0.5 or less between two different pieces.

## Program extension

The endings take 490 KB of the extension, which is 2 MB (`0x400000`-`0x5fffff`).

## Not done yet

- Donovan, Huitzil and Pyron: the PlayStation game's endings for them.

## Testing

`tools/dev/libretro_run.c` with the auto-win (`AUTOWIN`) reaches an ending in about 9000
frames. The 14 endings were compared with Vampire Savior's in MAME in English; B.B. Hood's
also in Japanese (the language byte `ff8093` set to 0).
