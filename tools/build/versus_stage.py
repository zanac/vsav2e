"""In a versus match the challenger picks the stage, on the select grid.

When two players fight each other, Vampire Savior 2 picks the stage at random, from a
list that depends on the challenger's character (`0x96c4`: 16 stages for each character
in the table at `0xad2a`). The stage is the word `$100(a5)` (RAM `ff8100`), an even
number from 0 to 0x18, chosen as the VS screen starts.

vsav2e lets the challenger choose it with the portraits of the select screen: after he
has picked his character, his cursor stays on the grid and the top of the screen shows
"SELECT STAGE" and, under it, the name of the stage of the character under the cursor
(the stage where the one-player game fights that character). An attack button picks it; the "?" portrait keeps the
game's random stage. Then the game goes on as after any choice (the speed menu, if the
operator allows it, then the VS screen).

Who chooses: the player who joined last (`$8d(a5)`, the players who pressed start for
this match, is 1 or 2), or, when both started the match together (3), the one of the two
who picks his character last.

How it works, on the select screen (each player is an object at ff8400 or ff8800; the
fields used here: `$3` the cell under the cursor, `$382` the character, `$4` the phase,
0 while choosing; `$26`/`$27` the timer, seconds and frames; `$39` frames before the
buttons count; `$394`/`$396` the inputs now and the frame before):

- the confirmation of a character (`0x1f65e`, reached by an attack button or when the
  timer ends) of the chooser does not confirm yet: the character, its cell and the
  buttons pressed (they pick the colours) are saved, the timer starts again and the
  stage mode begins;
- in stage mode the cursor routine (`0x1f5e6`) moves `$3` only, so the cursor object
  (which follows `$3` while the phase is 0) shows the choice and the character stays;
- an attack button, or the end of the timer, saves the stage, puts the character back
  and runs the game's confirmation with the saved buttons;
- the names are shown by a stage name object (class 07, kind 0x1a: the object of the
  one-player map screen), given vsav2e's own work on each frame: it draws the frame of
  the cell in the stage mode state, and removes itself when the state is cleared;
- at the VS screen (`0x970a`) the chosen stage replaces the random one.

The state lives in RAM that the game does not use (ff83f0-ff83f8, a5 + 0x3f0).
"""
import struct

# RAM, as offsets from a5 (ff8000)
STATE = 0x3f0                           # byte: 0 none, 1 stage mode, 2 chosen
STAGE_CELL = 0x3f1                      # byte: the cell of the stage (the cursor's)
SAVED_CELL = 0x3f2                      # byte: the cell of the chooser's character
SAVED_CHARACTER = 0x3f3                 # byte: the chooser's character
SAVED_BUTTONS = 0x3f4                   # word: the buttons that picked the character
CHOSEN_STAGE = 0x3f6                    # word: the stage, or -1 for the random one
CHOOSER = 0x3f8                         # byte: the chooser, 0 player 1, 1 player 2

# the select screen: the cursor routine of a player, the confirmation of a character
CURSOR_ROUTINE = 0x1f5e6
CURSOR_ROUTINE_ORIGINAL = bytes.fromhex('532e00276610')    # subq.b #1, $27(a6) / bne.s
CURSOR_TIMER_SECOND = 0x1f5ec           # the routine after the frames of a second end
CURSOR_TIMER_RUNNING = 0x1f5fc          # and while they do not
CONFIRM = 0x1f65e
CONFIRM_ORIGINAL = bytes.fromhex('422e03c10c2e000b0003')   # clr.b $3c1(a6) / cmpi.b #$b, $3(a6)
CONFIRM_REST = 0x1f668
DIRECTIONS = 0x1fe2c                    # joystick bits -> the index of a direction
NAVIGATION_TABLE = 0x1588e              # for each cell, the cell in each direction
STAGE_SECONDS = 10
BUTTON_WAIT = 16                        # frames, so that the button of the character
                                        # does not pick a stage too
# the end of the versus stage choice: `move.w d0, $100(a5)` / `rts`
STAGE_CHOICE_END = 0x970a
STAGE_CHOICE_END_ORIGINAL = bytes.fromhex('3b4001004e75')

# the stage name object: its work on each frame starts with `move.b $5(a6), d0` then
# `move.w table(pc, d0.w), d1` / `jmp table(pc, d1.w)`
NAME_OBJECT_FRAME = 0x6c67e
NAME_OBJECT_FRAME_ORIGINAL = bytes.fromhex('102e0005323b00064efb1002')
NAME_OBJECT_STATE_TABLE = 0x6c68a
NAME_OBJECT_KIND = 0x0100071a           # active, class 07, kind 0x1a
ALLOCATE_OBJECT = 0x15702               # a4 = a free object; Z set when there is none
REGISTER_FOR_DRAWING = 0x13c3a
MARK_FIELD, MARK = 0x40, 0x5354         # "ST": a field the object does not use
# where the object is: x, the middle of the text; y (the records' y are from it)
NAME_X = 0xc0
NAME_Y = 0x18

STAGE_NAME_FRAMES = 0x2a0a96            # frame pointer of stage s at + 2 * s
RANDOM = -1
CELLS = 0x14
RANDOM_CELL = 0x0b
# the stage of each portrait: the stage where the character is fought in the
# one-player game of Vampire Savior 2 (vhunt2 for Talbain, Rikuo and Sasquatch)
STAGE_OF_CHARACTER = {
    0x00: 0x0e,     # Bulleta (B.B. Hood)   War Agony
    0x01: 0x00,     # Demitri               Feast of the Damned
    0x02: 0x02,     # Jon Talbain           Concrete Cave
    0x03: 0x0e,     # Victor                War Agony
    0x04: 0x10,     # Zabel (Lord Raptor)   Forever Torment
    0x05: 0x08,     # Morrigan              Deserted Chateau
    0x06: 0x06,     # Anakaris              Red Thirst
    0x07: 0x04,     # Felicia               Tower of Arrogance
    0x08: 0x0a,     # Bishamon              Abaraya
    0x09: 0x12,     # Rikuo                 Green Scream
    0x0a: 0x0c,     # Sasquatch             Vanity Paradise
    0x0c: 0x12,     # Q-Bee                 Green Scream
    0x0d: 0x0c,     # Hsien-Ko              Vanity Paradise
    0x0e: 0x08,     # Lilith                Deserted Chateau
    0x0f: 0x16,     # Jedah                 Fetus of God
    0x10: 0x04,     # Huitzil               Tower of Arrogance
    0x11: 0x14,     # Pyron                 Iron Horse, Iron Terror
    0x13: 0x18,     # Donovan               Revenger's Roost
}

# the letters: tile 0x49b1 is A (stored minus 0x4200, as type 4 frames do)
LETTER_A = 0x07b1
LETTER_STEP = 14                        # x from a letter to the next
WORD_GAP = 16                           # a wider step than this starts a new word
SPACE_STEP = 22                         # x from the last letter of a word to the next
LINE_HEIGHT = 16
FRAME_TYPE_TILES = 4
# the text is at the top of the screen, between the speed badges of the players (the
# portraits of the grid start below it): "SELECT STAGE", then the name of the stage
# in one or two lines. A record's y is the top of its letter minus 216.
SCREEN_Y_OFFSET = 216
HEADER_TOP = 2
NAME_TOP = 19
MAX_LINE_WIDTH = 190


def encode_line(text):
    """a line of text as a list of (x, tile)"""
    line, x = [], 0
    for character in text:
        if character == ' ':
            x += SPACE_STEP - LETTER_STEP
            continue
        line.append((x, LETTER_A + ord(character) - ord('A')))
        x += LETTER_STEP
    return line


def line_width(line):
    return line[-1][0] - line[0][0] + LETTER_STEP


def letters_frame(lines):
    """A type 4 frame of lines of text (lists of (x, tile)), each centred, one under
    the other from the top of the screen: the first line at HEADER_TOP, the others from
    NAME_TOP."""
    records = []
    for index, line in enumerate(lines):
        top = HEADER_TOP if index == 0 else NAME_TOP + LINE_HEIGHT * (index - 1)
        left = line[0][0]
        width = line_width(line)
        for x, tile in line:
            records.append(struct.pack('>HHhh', tile, 0, x - left - width // 2, top - SCREEN_Y_OFFSET))
    return struct.pack('>HHH', FRAME_TYPE_TILES, len(records), len(records) - 1) + b''.join(records)


def stage_name_words(vsav2e, stage):
    """the words of the game's name of a stage, each a list of (x, tile) from x 0"""
    frame = struct.unpack_from('>I', vsav2e, STAGE_NAME_FRAMES + 2 * stage)[0]
    if struct.unpack_from('>H', vsav2e, frame)[0] != FRAME_TYPE_TILES:
        raise SystemExit('versus stage: no name for stage 0x%x' % stage)
    count = struct.unpack_from('>H', vsav2e, frame + 4)[0] + 1
    lines = {}
    for index in range(count):
        tile, _, x, y = struct.unpack_from('>HHhh', vsav2e, frame + 6 + 8 * index)
        lines.setdefault(y, []).append((x, tile))
    words = []
    for y in sorted(lines):
        previous_x = None
        for x, tile in sorted(lines[y]):
            if previous_x is None or x - previous_x > WORD_GAP:
                words.append([])
                start = x
            words[-1].append((x - start, tile))
            previous_x = x
    return words


def wrap(words):
    """the words in lines of at most MAX_LINE_WIDTH"""
    lines = []
    for word in words:
        if lines:
            x = lines[-1][-1][0] + SPACE_STEP
            joined = lines[-1] + [(x + word_x, tile) for word_x, tile in word]
            if line_width(joined) <= MAX_LINE_WIDTH:
                lines[-1] = joined
                continue
        lines.append(list(word))
    return lines


def select_routines(stage_of_cell):
    """The routines of the select screen, one block: the cursor routine's hook (at the
    start), the confirmation's hook (at the returned offset)."""
    cursor_hook = bytes.fromhex(
        # the chooser in stage mode goes to stage_mode, the others to the game's routine
        '0c2d0001%04x' % STATE +                        # cmpi.b  #1, STATE(a5)
        '660a'                                          # bne.s   game
        '102e0381'                                      # move.b  $381(a6), d0     the player
        'b02d%04x' % CHOOSER +                          # cmp.b   CHOOSER(a5), d0
        '6712'                                          # beq.s   stage_mode
        # game: the instructions the jump replaced
        '532e0027'                                      # subq.b  #1, $27(a6)
        '6606'                                          # bne.s   running
        '4ef9%08x' % CURSOR_TIMER_SECOND +              # jmp     second
        # running:
        '4ef9%08x' % CURSOR_TIMER_RUNNING +             # jmp     running
        # stage_mode: the timer, as the game's
        '532e0027'                                      # subq.b  #1, $27(a6)
        '660c'                                          # bne.s   timer_done
        '1d7c003c0027'                                  # move.b  #60, $27(a6)
        '532e0026'                                      # subq.b  #1, $26(a6)
        '6b52'                                          # bmi.s   choose
        # timer_done:
        '4a2e0039'                                      # tst.b   $39(a6)
        '6704'                                          # beq.s   no_wait
        '532e0039'                                      # subq.b  #1, $39(a6)
        # no_wait: the inputs just pressed
        '302e0396'                                      # move.w  $396(a6), d0
        '4640'                                          # not.w   d0
        'c06e0394'                                      # and.w   $394(a6), d0
        '3400'                                          # move.w  d0, d2
        '4a2e0039'                                      # tst.b   $39(a6)
        '6606'                                          # bne.s   move
        '02407700'                                      # andi.w  #$7700, d0       attack buttons
        '6630'                                          # bne.s   choose
        # move: the joystick, as the game's routine
        '0242000f'                                      # andi.w  #$f, d2
        '41f9%08x' % DIRECTIONS +                       # lea     directions, a0
        '7200'                                          # moveq   #0, d1
        '12302000'                                      # move.b  0(a0, d2.w), d1
        '6b16'                                          # bmi.s   show
        '7000'                                          # moveq   #0, d0
        '102e0003'                                      # move.b  $3(a6), d0
        'e748'                                          # lsl.w   #3, d0           8 cells a row
        '207c%08x' % NAVIGATION_TABLE +                 # movea.l #navigation, a0
        'd0c0'                                          # adda.w  d0, a0
        '1d7010000003'                                  # move.b  0(a0, d1.w), $3(a6)
        # show: the cell for the name object
        '1b6e0003%04x' % STAGE_CELL +                   # move.b  $3(a6), STAGE_CELL(a5)
        '4e75'                                          # rts
        # choose: the stage of the cell; the character back; the game's confirmation
        '7000'                                          # moveq   #0, d0
        '102e0003'                                      # move.b  $3(a6), d0
        '41f9%08x' % stage_of_cell +                    # lea     stage_of_cell, a0
        '10300000'                                      # move.b  0(a0, d0.w), d0
        '4880'                                          # ext.w   d0               -1: random
        '3b40%04x' % CHOSEN_STAGE +                     # move.w  d0, CHOSEN_STAGE(a5)
        '1b7c0002%04x' % STATE +                        # move.b  #2, STATE(a5)
        '1d6d%04x0003' % SAVED_CELL +                   # move.b  SAVED_CELL(a5), $3(a6)
        '1d6d%04x0382' % SAVED_CHARACTER +              # move.b  SAVED_CHARACTER(a5), $382(a6)
        '302d%04x' % SAVED_BUTTONS +                    # move.w  SAVED_BUTTONS(a5), d0
        # confirm: the instructions the jump replaced
        '422e03c1'                                      # clr.b   $3c1(a6)
        '0c2e000b0003'                                  # cmpi.b  #$b, $3(a6)
        '4ef9%08x' % CONFIRM_REST)                      # jmp     the confirmation
    confirm_hook = bytes.fromhex(
        # two players: $8d | $ac is 3 (the test of the select screen at 0x1fc30)
        '142d008d'                                      # move.b  $8d(a5), d2
        '842d00ac'                                      # or.b    $ac(a5), d2
        '0c020003'                                      # cmpi.b  #3, d2
        '66e2'                                          # bne.s   confirm
        '4a2d%04x' % STATE +                            # tst.b   STATE(a5)
        '66dc'                                          # bne.s   confirm          chosen already
        '122e0381'                                      # move.b  $381(a6), d1     the player
        '142d008d'                                      # move.b  $8d(a5), d2      who joined
        '0c020001'                                      # cmpi.b  #1, d2
        '671a'                                          # beq.s   player_1_joined
        '0c020002'                                      # cmpi.b  #2, d2
        '671a'                                          # beq.s   player_2_joined
        # both started: the chooser is the second to pick, when the other has picked
        '41ed0400'                                      # lea     $400(a5), a0     the other player
        '4a01'                                          # tst.b   d1
        '6604'                                          # bne.s   other
        '41ed0800'                                      # lea     $800(a5), a0
        # other:
        '4a280004'                                      # tst.b   $4(a0)           its phase
        '67b6'                                          # beq.s   confirm
        '600a'                                          # bra.s   chooser
        # player_1_joined:
        '4a01'                                          # tst.b   d1
        '66b0'                                          # bne.s   confirm
        '6004'                                          # bra.s   chooser
        # player_2_joined:
        '4a01'                                          # tst.b   d1
        '67aa'                                          # beq.s   confirm
        # chooser: the stage mode starts
        '1b7c0001%04x' % STATE +                        # move.b  #1, STATE(a5)
        '1b41%04x' % CHOOSER +                          # move.b  d1, CHOOSER(a5)
        '1b6e0003%04x' % SAVED_CELL +                   # move.b  $3(a6), SAVED_CELL(a5)
        '1b6e0003%04x' % STAGE_CELL +                   # move.b  $3(a6), STAGE_CELL(a5)
        '1b6e0382%04x' % SAVED_CHARACTER +              # move.b  $382(a6), SAVED_CHARACTER(a5)
        '3b40%04x' % SAVED_BUTTONS +                    # move.w  d0, SAVED_BUTTONS(a5)
        '1d7c%04x0026' % STAGE_SECONDS +                # move.b  #seconds, $26(a6)
        '1d7c003c0027'                                  # move.b  #60, $27(a6)
        '1d7c%04x0039' % BUTTON_WAIT +                  # move.b  #wait, $39(a6)
        '4eb9%08x' % ALLOCATE_OBJECT +                  # jsr     allocate
        '670c'                                          # beq.s   done
        '28bc%08x' % NAME_OBJECT_KIND +                 # move.l  #kind, (a4)
        '397c%04x%04x' % (MARK, MARK_FIELD) +           # move.w  #MARK, MARK(a4)
        # done:
        '4e75')                                         # rts
    return cursor_hook + confirm_hook, len(cursor_hook)


def name_frame_routine(steps):
    """The stage name object's work on each frame."""
    return bytes.fromhex(
        '0c6e%04x%04x' % (MARK, MARK_FIELD) +           # cmpi.w  #MARK, MARK(a6)
        '6638'                                          # bne.s   game
        '4a2d%04x' % STATE +                            # tst.b   STATE(a5)
        '6726'                                          # beq.s   remove
        '7200'                                          # moveq   #0, d1
        '122d%04x' % STAGE_CELL +                       # move.b  STAGE_CELL(a5), d1
        'e749'                                          # lsl.w   #3, d1           8 bytes a step
        '41f9%08x' % steps +                            # lea     steps, a0
        'd0c1'                                          # adda.w  d1, a0
        '2d48001c'                                      # move.l  a0, $1c(a6)      the step drawn
        '3d7c%04x0010' % NAME_X +                       # move.w  #x, $10(a6)
        '3d7c%04x0014' % NAME_Y +                       # move.w  #y, $14(a6)
        '4ef9%08x' % REGISTER_FOR_DRAWING +             # jmp     register for drawing
        # remove:
        '426e%04x' % MARK_FIELD +                       # clr.w   MARK(a6)
        '1d7c00040004'                                  # move.b  #4, $4(a6)       destroy
        '4e75'                                          # rts
        # game: the instructions the jump replaced
        '102e0005'                                      # move.b  $5(a6), d0
        '43f9%08x' % NAME_OBJECT_STATE_TABLE +          # lea     table, a1
        '32310000'                                      # move.w  0(a1, d0.w), d1
        '4ef11000')                                     # jmp     0(a1, d1.w)


STAGE_APPLY_ROUTINE = bytes.fromhex(
    '0c2d0002%04x' % STATE +                            # cmpi.b  #2, STATE(a5)
    '660a'                                              # bne.s   set
    '4a6d%04x' % CHOSEN_STAGE +                         # tst.w   CHOSEN_STAGE(a5)
    '6b04'                                              # bmi.s   set              random
    '302d%04x' % CHOSEN_STAGE +                         # move.w  CHOSEN_STAGE(a5), d0
    # set:
    '422d%04x' % STATE +                                # clr.b   STATE(a5)
    '3b400100'                                          # move.w  d0, $100(a5)     as the game did
    '4e75')                                             # rts


def patch(vsav2e, address, original, replacement):
    if vsav2e[address:address + len(original)] != original:
        raise SystemExit('versus stage: unexpected code at 0x%x' % address)
    nops = b'\x4e\x71' * ((len(original) - len(replacement)) // 2)
    vsav2e[address:address + len(original)] = replacement + nops


def jump(target):
    return b'\x4e\xf9' + struct.pack('>I', target)


def apply(vsav2e, extension, free_space_start, free_space_end):
    """Adds the stage choice to the vsav2e program (a bytearray); the frames go to the
    program extension. Returns the first free address of the program."""
    header = encode_line('SELECT STAGE')
    frames = {RANDOM: extension.add(letters_frame([header, encode_line('RANDOM')]))}
    for stage in sorted(set(STAGE_OF_CHARACTER.values())):
        frames[stage] = extension.add(letters_frame([header] + wrap(stage_name_words(vsav2e, stage))))
    # for each cell: an animation step (4 bytes, then the frame pointer), the stage
    stage_of_cell = [STAGE_OF_CHARACTER.get(cell, RANDOM) for cell in range(CELLS)]
    steps = extension.add(b''.join(struct.pack('>II', 0, frames[stage]) for stage in stage_of_cell))
    stages = extension.add(bytes(stage & 0xff for stage in stage_of_cell))

    select, confirm_offset = select_routines(stages)
    routines = [select, name_frame_routine(steps), STAGE_APPLY_ROUTINE]
    addresses = []
    address = free_space_start + (free_space_start & 1)
    for routine in routines:
        addresses.append(address)
        address += len(routine)
    if address > free_space_end:
        raise SystemExit('versus stage: no room for the routines')
    for routine, routine_address in zip(routines, addresses):
        vsav2e[routine_address:routine_address + len(routine)] = routine
    select_address, name_frame_address, stage_apply_address = addresses

    patch(vsav2e, CURSOR_ROUTINE, CURSOR_ROUTINE_ORIGINAL, jump(select_address))
    patch(vsav2e, CONFIRM, CONFIRM_ORIGINAL, jump(select_address + confirm_offset))
    patch(vsav2e, NAME_OBJECT_FRAME, NAME_OBJECT_FRAME_ORIGINAL, jump(name_frame_address))
    patch(vsav2e, STAGE_CHOICE_END, STAGE_CHOICE_END_ORIGINAL, jump(stage_apply_address))
    return address
