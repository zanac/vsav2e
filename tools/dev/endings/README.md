# Endings port: working prototype

Work in progress: bringing Vampire Savior's per-character endings into vsav2e. These
scripts are the prototype; they still use absolute paths of the development machine
(`/tmp/claude-0/vs/...`) and need `capstone` and `numpy`. The build (`make_vsav2e.py`)
does not use them yet.

## How it works

The ending code of Vampire Savior (the decrypted `vsavd` program) is moved into the
program extension and relocated, instead of being rewritten:

1. `tap.lua` + `endtap.sh`: MAME runs each character to its ending and logs every program
   ROM read (instruction address, data address) while the ending plays.
   `rom_reads.txt.gz` holds the logs of the 15 characters (`id pc address`, hex).
2. `fmap.py`, `align2.py`: both programs are disassembled and aligned instruction by
   instruction (unique 8-instruction windows, extended both ways). This gives a map of
   vsav addresses to vsav2 addresses and a map of the RAM offsets from a5 (some ranges
   moved by 0x0e, 0x12, 0x80...).
3. `verify.py`: every vsav routine the moved code calls is checked against its vsav2
   address instruction by instruction (immediates included); a wrong one is searched
   again. Small routines that look alike were mapped one off without this.
4. `purity.py`: a called routine that reads Vampire Savior data itself (absolute
   addresses 0x100000-0x3fffff) is moved too instead of being mapped.
5. `xlink.py`: recursive disassembly of the moved code from its entry points (jump
   tables of words, tables of longs).
6. `port.py`: lays out code and data in the extension and relocates: absolute code and
   data addresses, a5 offsets, object ids (classes renumbered: the classes the endings
   need move to new numbers after vsav2's own in each pool, with a hook in each pool's
   object runner reading a longer class table), pointers in animation steps and frames,
   pointers kept in the data parts of the moved code. Graphics: the sprite tiles of the
   moved frames go to the upper sprite bank at their own numbers; the tiles of the
   scroll layers are renumbered into the scroll bank (driver: 16 MB after the sprites,
   selected by bits 0-2 of the word at 0x8040c0). The game mode of the ending jumps to a
   dispatcher: characters 00-0a and 0c-0e play Vampire Savior's ending, then Savior 2's
   staff credits; the others play Savior 2's ending.
7. `mkzip.py`: builds a test vsav2e.zip with the endings.

Status: B.B. Hood's ending plays like the arcade one, then the credits, ranking and
attract mode. Other characters are being checked.

Things learnt:
- CPS2 scroll tiles start 8 MB into the graphics (`bank_scroll` 4 in MAME's CPS2 config).
- The text duration tables of the endings are reached through a table of longs at
  0xcdd0 that the code reads with `movea.l (a0, d0.w)`, not pc-relative.
- Pool 3 class 04 animates palettes from scripts kept inside its own code, with a table
  of palette bases in the code.
