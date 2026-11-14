# Versus: the challenger picks the stage

In a match between two players (both started, or one joined in), the VS screen shows
SELECT STAGE at the top and a stage name at the bottom. The challenger, the player who
joined last, goes through the stages with left and right; the first choice, RANDOM, keeps
the stage the game picks. The VS screen lasts five seconds in a versus match and an
attack button of either player ends it, with the stage shown.

The code and how the game does it: `tools/build/versus_stage.py`.

| What | Where (`vsav2`) |
|---|---|
| Stage | word `$100(a5)` (RAM `ff8100`), even, 0 to 0x18; set as the VS screen starts, read when the fight loads |
| Versus stage choice | `0x96c4`: a1 is the challenger (by `$8d(a5)`, bit 0 the player who joined last; 3 when both started, then by `$131(a5)`), stage = table `0xad2a` [character * 16 + random 0-15] |
| Stage names | frames of type 4 (letters), pointers at `0x2a0a96` + 2 * stage; letter A is tile 0x49b1 |
| VS screen | scene at `0x8a9c`: `$e(a5)` frames (0x3c, then 0x7f), ended early by `0x9526` (any button; for player 2 any input) |
| Players' input | `$58(a5)`/`$5a(a5)` player 1 now/before, `$5c`/`$5e` player 2; in a player object, `$394` now and `$396` before (bit 0 right, bit 1 left) |
| Players together | `$ac(a5)`: bit 0 player 1, bit 1 player 2 |

The 13 stages, all checked in a versus match:

| Stage | Name |
|---|---|
| 00 | Feast of the Damned |
| 02 | Concrete Cave |
| 04 | Tower of Arrogance |
| 06 | Red Thirst |
| 08 | Deserted Chateau |
| 0a | Abaraya |
| 0c | Vanity Paradise |
| 0e | War Agony |
| 10 | Forever Torment |
| 12 | Green Scream |
| 14 | Iron Horse, Iron Terror |
| 16 | Fetus of God |
| 18 | Revenger's Roost |
