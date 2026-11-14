# Versus: the challenger picks the stage

In a match between two players (both started, or one joined in), the challenger picks the
stage on the select screen. After he has picked his character, his cursor stays on the
grid: the top of the screen shows SELECT STAGE and the name of the stage of the portrait
under the cursor, the stage where the one-player game fights that character. An attack
button picks it (or the end of the timer, ten seconds); the "?" portrait keeps the stage
the game picks at random. The game then goes on as usual (the speed menu, if the operator
allows it, then the VS screen).

The challenger is the player who joined last; when both started the match together, the
second of the two to pick a character.

| Portrait | Stage |
|---|---|
| Demitri | 00 Feast of the Damned |
| Jon Talbain | 02 Concrete Cave |
| Felicia, Huitzil | 04 Tower of Arrogance |
| Anakaris | 06 Red Thirst |
| Morrigan, Lilith | 08 Deserted Chateau |
| Bishamon | 0a Abaraya |
| Sasquatch, Hsien-Ko | 0c Vanity Paradise |
| B.B. Hood, Victor | 0e War Agony |
| Lord Raptor | 10 Forever Torment |
| Rikuo, Q-Bee | 12 Green Scream |
| Pyron | 14 Iron Horse, Iron Terror |
| Jedah | 16 Fetus of God |
| Donovan | 18 Revenger's Roost |
| ? | random |

The code and how the game does it: `tools/build/versus_stage.py`.

| What | Where (`vsav2`) |
|---|---|
| Stage | word `$100(a5)` (RAM `ff8100`), even, 0 to 0x18; set as the VS screen starts, read when the fight loads |
| Versus stage choice | `0x96c4`: a1 is the challenger (by `$8d(a5)`, bit 0 the player who joined last; 3 when both started, then by `$131(a5)`), stage = table `0xad2a` [character * 16 + random 0-15] |
| Players of the match | `$8d(a5)`: who pressed start for it (1, 2; 3 both together); `$ac(a5)`: who plays (0 on the select screen of a match started together); two players when `$8d \| $ac` is 3 (`0x1fc30`) |
| Select screen, a player | object ff8400 / ff8800: `$3` cell under the cursor (the character id; 0x0b "?"), `$382` character, `$4` phase (0 choosing, 2 speed menu, 4 done), `$26`/`$27` timer, `$39` frames before buttons count; cursor routine `0x1f5e6`, confirmation `0x1f65e` (d0: the buttons, they pick the colours) |
| Cursor object | class 07 kind 4, per frame `0x6c378`: follows the player's `$3` while his phase is 0 |
| Navigation | `0x1fe2c` joystick bits -> direction, `0x1588e` 8 bytes a cell: the cell in each direction |
| Stage names | frames of type 4 (letters), pointers at `0x2a0a96` + 2 * stage; letter A is tile 0x49b1 |
| VS screen | scene at `0x8a9c`: `$e(a5)` frames (0x3c, then 0x7f), ended early by `0x9526` (any button; for player 2 any input) |
| vsav2e's state | RAM ff83f0-ff83f8, unused by the game: see `versus_stage.py` |
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
