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
  are the same sequences in Vampire Hunter 2, already copied for the three characters,
  so they play with Vampire Hunter 2's instruments: the same samples, but five of them
  have other envelopes (bank 1 #3, #11, #42, #70, bank 5 #59). Giving the endings their
  own copies needs the places that ask for them, not found yet (they are not `moveq`
  before a call of the sound routines in the moved code).

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

### The music of Donovan, Huitzil and Pyron

Their endings exist only in the home games (PlayStation and Saturn: CD audio, far too big
for the sound ROMs), so there is no QSound music for them anywhere. Each of the three
plays a slow, heavier version of the music of its own stage in Vampire Hunter 2
(`tools/build/stage_music.py`, which also describes the format of a sequence):

| | Vampire Hunter 2 sound number | vsav2e sound number |
|---|---|---|
| Huitzil | `0x19` | `0x6c` |
| Pyron | `0x1a` | `0x6d` |
| Donovan | `0x1c` | `0x6e` |

(Found from the number the 68000 writes to the QSound shared RAM when each stage starts:
`WATCH=618001,618003` of `tools/dev/libretro_run.c`, with the character forced in both
players.) The changes, all with commands the sound program already has:

- tempo 0.6 of the original: the word after a track's `05` is what the driver takes off the
  length of every note each tick, so a smaller one is slower;
- the percussion (instruments whose sample does not loop) at 0.4 of its volume, but for
  the low drum all three use;
- the three highest tracks that sustain their notes are copied, an octave lower and a few
  cents out of tune, as new tracks in unused slots, so that the voices beat like a chorus.

The sequences are put after the copies of Vampire Hunter 2's: the one that fits in what is
left of bank 12 (reads `1f nn` as Vampire Hunter 2's bank nn), the others in banks 13-15,
where `1f nn` is rewritten to name Vampire Hunter 2's banks 8-15 itself (the remap table of
the bank pick routine has them as they are). Pyron's theme has a last track that jumps into
another track's code with the bank 29, which does not exist: it is dropped. Checked by
recording them (`tools/dev/stage_music_demo.py` makes the three versions of each theme,
original, slowed, remixed, with no voices or effects) and, in vsav2e, by the sound CPU's
RAM: the tempo and the slots of the music are the ones of the sequences, in bank 15 for
Donovan.

## How an ending works (the model for new ones)

Read from Vampire Savior's script of B.B. Hood (`0x8cd02`) and the routines it calls. An
ending is a step machine: the game mode calls the script of the character each frame
(the table of scripts at `0x21b06` of Vampire Savior, by character), which jumps on
the step number `$10(a5)` (a table of offsets, steps of two) and does that step's work
(wait `$12(a5)` frames, start a fade, put a tilemap, make an object) before moving to
the next. Where the ending needs Vampire Savior 2's code the moved code calls it at its
own address (`VALUE_PATCHES` of `endings_recipe.py`): Vampire Savior -> Vampire Savior 2

- fades of the palettes (`tst.b $7401(a5)`... `jsr $13a8`): `0x1463e` -> `0x12cea`,
  `0x14662` -> `0x12d0e`, `0x14686` -> `0x12d56`, `0x146aa` -> `0x12d7a`, `0x146ce` ->
  `0x12d9e` (and `0x146f2` -> `0x12de6`); the routine returns with d0 = 0 when the fade
  is finished, so a step calls it each frame and moves on when `$7401(a5)` is clear;
- the palettes of the three scroll layers of the character: `0x14f6a`, `0x14f7c`,
  `0x14f8e` -> `0x1365e`, `0x13670`, `0x13682`; the ending's own `0x21c26` calls them;
- object allocation (an object is a record at a4; `jsr` the allocator, `beq` if there is
  none, then `move.l #class, (a4)`, the fields `$10`/`$14` (x, y), `$1a` (attributes)):
  `0x16fba`, `0x16fd0`, `0x16fe6`, `0x16ffc` -> `0x15702`, `0x15718`, `0x1572e`, `0x15744`
  (one for each pool of objects); the classes (`recipe.MOVED_CLASSES`, in the table of
  each pool; the long `moveq #n` is the class number in the pool) are the moved ones;
- the tilemap loader `0x1f856` (moved: it is in the code ranges) takes d0 = the number of
  a block of 64 entries (`(code, attribute)` words) of the table at `0x384aa4` (256 bytes
  a block) and a1 = where to write them (the layer's map at `0x90xxxx`); the loader adds
  `0x600` to the code (the codes are relative to the start of the scroll 3 tiles in the
  graphics, and the build renumbers them in the scroll bank). A picture is made of
  blocks of 8x8 tiles, each in column order (see `tools/build/scroll_picture.py`);
- the ending music, `moveq #n, d0` then `jsr $21d66` (moved; it asks the number to the
  sound CPU through a sender of its own, `endings.py`): n is Vampire Savior's number of
  the music, replaced in the build with `sound.py`'s (for the new endings the number of
  the stage theme: Huitzil 0x6c, Pyron 0x6d, Donovan 0x6e);
- the end of the script jumps to `0x21be6` (moved), which leaves the ending for the
  staff credits.

The scroll registers that the scripts write are words of the ending's record:
`$22`-`$2c(a5)` (the position and the speed of the layers), `$32(a5)`, `$3a(a5)` (the
layers' own registers) and `$20(a5)` (the layers' display flags).

### Converting a picture: `tools/build/scroll_picture.py`

`convert(image)` cuts an image into cells of 32x32, gives them the fewest palettes of 16
colours, drops the tiles that repeat and gives back the tiles (512 bytes), the palettes
(16 words 0xfrgb) and the cells (tile, palette) as a tilemap in the hardware's column
order. The tile format was checked by decoding the pictures of Vampire Savior's endings
(the globe of B.B. Hood's ending comes out as it is). A new ending puts these tiles in the
scroll bank after the renumbered ones, its tilemap and its palettes in the extension,
and its own small step machine (written for the build) writes them into the layers with
the primitives above.

## Program extension

The endings take 490 KB of the extension, which is 2 MB (`0x400000`-`0x5fffff`).

## The new endings: Donovan, Pyron and Huitzil

Vampire Savior has no ending for Donovan, Huitzil and Pyron (the home versions do). They are
built from the Sega Saturn game's pictures and the PlayStation game's English text, by one
timeline engine written in assembly (`tools/dev/new_endings.s`, assembled by
`tools/dev/assemble_new_endings.py` into `tools/build/new_endings_code.py`, which is committed
so that the build needs no assembler) and the data `tools/build/new_endings.py` makes:

- the pictures are layers of the Saturn's screen (352x240 PNG with alpha) that
  `tools/saturn/ending_layers.py` writes from a dump of the Saturn emulator; they are not in
  the repository (the user supplies them): `assets/saturn/endings/donovan/{asleep,awake,blade,hand,figure,sparkle00-12}.png` (the sparkles: bank 7080 of frames 1400, 1403, 1405, 1411, 1417, 1419, 1423, 1427, 1429, 1443, 1451, 1467, 1475 of `donovan3`, by `ending_layers.py`; without them the blade has no glints), `.../pyron/{hell,galaxy,throne}.png`, `.../huitzil/{ship,machine,face,city}.png` (or, all in one, `assets/vsav2e_endings_assets.zip` with those paths)
  (override the folder with `VSAV2E_ENDING_ASSETS`). Without them the character keeps Vampire
  Savior 2's own ending and the build is unchanged;
- `scroll_picture.py` converts them (the Saturn's screen is put at +16, -8 on the CPS2's);
  the tiles go after the renumbered ones in the scroll bank, the palettes high in the
  palette pages (the game writes the low ones now and then), and each picture is written
  to a scroll layer at its frame (`new_endings.Scenery`);
- the timeline: events (draw cells, copy a palette, fill a layer) by frame, palette channels
  (fades to black or white, or a palette held: written again each frame) and four tables of
  the scroll registers (scroll 2: x, y; scroll 3: x, y). The text and its pages are the
  pager's (Vampire Savior's code): `place_texts` writes the English pages and the durations
  of each page (both languages) for the new characters;
- the frame (purple walls and the window) is Vampire Savior's object class 0x40 of the first
  pool (renumbered 0x7c), with the layers ordered scroll 1, 3, 2, then the objects (layer
  control `$32 = 0x0b4e`): the walls hide what is outside the window. Scroll 3 shows the
  scene (x - 0, y + 0x711: the picture is where the Saturn has it), scroll 2 the hand over it;
- the game's own variables: `$12(a5)` is read by the objects (do not use it as a counter);
  the engine keeps its state at `0xfe8-0xfec(a5)` and the real character at `0xff8(a5)`.

Donovan's scene: Anita asleep (fades in), the blade (eight steps of brightness, each a
composite of the two, because the cells of a layer cannot overlap), the flash that wakes her
(to white and back), then the hand rising over the blade and Donovan's arm and face behind
it. The glints on the blade are patches of four cells redrawn with each of the 13 states of
Saturn's bank 7080 (a 74-frame loop). Missing: the blade's 2 pixels after the flash, Donovan's
fade-in (his picture pops in), the order of the hand and the blade while the hand rises.

Pyron's scene (`pyron/{hell,galaxy,throne}.png`): the hell background (scroll 3) turns black and
the galaxy fades in; the throne (scroll 2) slides in from the right at a quarter pixel a frame.
The backgrounds are Saturn VDP2 layers, taken from emulator screenshots by
`tools/saturn/ending_background.py` (the window without the sprites); the throne is the sprite
bank 7020 (`ending_layers.py`). The throne is one frame: it does not animate on the Saturn either (the sprites and the
background are identical from frame 2580 to 2900 in the captures).

Huitzil's scene (`huitzil/{ship,machine,face,city}.png`): four full pictures of the window, taken from
screenshots with `ending_background.py` (no sprites masked) that fade in and out in turn on scroll 3
(the Saturn animates parts of them; here they are still). The font has no colon and no digits:
the PlayStation's colons became full stops and "3600 seconds" "one hour".

## Japanese text of the new endings

The Japanese text engine spaces letters 16 pixels apart, so the English text of Donovan,
Huitzil and Pyron (they have no Japanese one) is set again for the Japanese table: lines of
15 letters, two lines a page, each page's duration shared among its new pages by length
(`narrow_pages`). The ported endings use Vampire Savior's Japanese text.

## Music

Checked on the signal: the sound commands of each ending are written, and the recorded
audio (`AUDIO` of the runner) has music all through (RMS 700-1500 of 32768), a different one
for each of the three. Not listened to by ear.

## Not done yet

- The music of the three endings has not been listened to.

## Testing

`tools/dev/libretro_run.c` with the auto-win (`AUTOWIN`) reaches an ending in about 9000
frames. The 14 endings were compared with Vampire Savior's in MAME in English; B.B. Hood's
also in Japanese (the language byte `ff8093` set to 0); the new three, and six of the
ported, in Japanese too.
