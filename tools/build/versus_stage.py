"""In a versus match the challenger picks the stage.

When two players fight each other, Vampire Savior 2 picks the stage at random, from a
list that depends on the challenger's character (`0x96c4`: 16 stages for each character
in the table at `0xad2a`). The stage is the word `$100(a5)` (RAM `ff8100`), an even
number from 0 to 0x18; it is chosen as the VS screen starts and read when the fight
loads, so it can still change while the VS screen is shown.

vsav2e lets the challenger (the player who joined last: the one the game takes the
stage list of) choose it on the VS screen: left and right go through the stages, and the
first choice, RANDOM, keeps the game's own random stage.

How it is shown: the map screen of a one-player game has an object that shows the name
of the next stage (class 07, kind 0x1a; it draws `$1c`, which points to an animation
step, with the frame pointer at offset 4). vsav2e creates one on the VS screen, marked
with a word in the object, and gives it its own work on each frame (`$ac(a5)` is 3 when
two players play, so a stale mark in the 1-player map screen does nothing): read the
challenger's joystick, set the stage, show its name. The names are frames of letters
(type 4: for each letter tile, attributes, x, y), written to the program extension: the
game's names, with "SELECT STAGE" above, and "RANDOM".

The VS screen lasts about two seconds, and any input of player 2 ends it (the game
tests player 2's joystick too: `andi.w #$7700, d0` at 0x95c0 masks the wrong register).
In a versus match vsav2e shows it for five seconds and ends it early on an attack button
only, which also confirms the stage.
"""
import struct

# the end of the versus stage choice: `move.w d0, $100(a5)` / `rts`; a1 is the challenger
STAGE_CHOICE_END = 0x970a
STAGE_CHOICE_END_ORIGINAL = bytes.fromhex('3b4001004e75')
# the work on each frame of the stage name object: `move.b $5(a6), d0` then
# `move.w table(pc, d0.w), d1` / `jmp table(pc, d1.w)`
NAME_OBJECT_FRAME = 0x6c67e
NAME_OBJECT_FRAME_ORIGINAL = bytes.fromhex('102e0005323b00064efb1002')
NAME_OBJECT_STATE_TABLE = 0x6c68a
NAME_OBJECT_KIND = 0x0100071a           # active, class 07, kind 0x1a
ALLOCATE_OBJECT = 0x15702               # a4 = a free object; Z set when there is none
REGISTER_FOR_DRAWING = 0x13c3a

STAGE_NAME_FRAMES = 0x2a0a96            # frame pointer of stage s at + 2 * s
STAGES = tuple(range(0x00, 0x1a, 2))    # all 13 work in a versus match

# the letters: tile 0x49b1 is A (stored minus 0x4200, as type 4 frames do)
LETTER_A = 0x07b1
LETTER_STEP = 14                        # x from a letter to the next
SPACE_STEP = 22
LINE_HEIGHT = 16
FRAME_TYPE_TILES = 4

# the object: fields of vsav2e's own (the stage name object does not use them)
MARK_FIELD, MARK = 0x40, 0x5354         # "ST"
RANDOM_STAGE_FIELD = 0x42               # word: the game's random stage
CHOICE_FIELD = 0x44                     # byte: 0 random, n stage STAGES[n - 1]
CHALLENGER_FIELD = 0x46                 # word: the challenger's player object
# where the name is shown (x is set by the object's start: 0xf0, the middle of the
# screen): the line of the name is at the bottom, "SELECT STAGE" at the top
NAME_Y = 0x18
NAME_LINE_Y = -8
HEADER_Y = -202

# the VS screen: its second part shows the portraits for $e(a5) frames, set by
# `move.w #$7f, $e(a5)` at 0x8ac4, and ends early when the routine at 0x9526 finds a
# button pressed (`jsr $9526` at 0x8aac and 0x8b16, then `bne`)
VS_TIME_ADDRESS = 0x8ac4
VS_TIME_ORIGINAL = bytes.fromhex('3b7c007f000e')
VS_TIME_VERSUS = 300
VS_SKIP_CALLS = (0x8aac, 0x8b16)
VS_SKIP_ORIGINAL = bytes.fromhex('4eb900009526')
VS_SKIP_ROUTINE = 0x9526
# a5 offsets of the players' inputs: now and the frame before
PLAYER_1_INPUT, PLAYER_1_INPUT_BEFORE = 0x58, 0x5a
PLAYER_2_INPUT, PLAYER_2_INPUT_BEFORE = 0x5c, 0x5e
ATTACK_BUTTONS = 0x7700

# joystick bits of the players' input words ($394 now, $396 the frame before)
INPUT_NOW, INPUT_BEFORE = 0x394, 0x396
RIGHT_BIT, LEFT_BIT = 0, 1


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


def letters_frame(header, name_lines):
    """A type 4 frame: the header line at the top of the screen, the lines of the name
    at the bottom (the last one at NAME_LINE_Y), each centred. A line is a list of
    (x, tile)."""
    placed = [(header, HEADER_Y)] + [(line, NAME_LINE_Y - LINE_HEIGHT * (len(name_lines) - 1 - index))
                                     for index, line in enumerate(name_lines)]
    records = []
    for line, y in placed:
        left = line[0][0]
        width = line[-1][0] - left + LETTER_STEP
        for x, tile in line:
            records.append(struct.pack('>HHhh', tile, 0, x - left - width // 2, y))
    return struct.pack('>HHH', FRAME_TYPE_TILES, len(records), len(records) - 1) + b''.join(records)


def stage_name_lines(vsav2e, stage):
    """the lines of the game's name of a stage, as lists of (x, tile)"""
    frame = struct.unpack_from('>I', vsav2e, STAGE_NAME_FRAMES + 2 * stage)[0]
    if struct.unpack_from('>H', vsav2e, frame)[0] != FRAME_TYPE_TILES:
        raise SystemExit('versus stage: no name for stage 0x%x' % stage)
    count = struct.unpack_from('>H', vsav2e, frame + 4)[0] + 1
    lines = {}
    for index in range(count):
        tile, _, x, y = struct.unpack_from('>HHhh', vsav2e, frame + 6 + 8 * index)
        lines.setdefault(y, []).append((x, tile))
    return [sorted(lines[y]) for y in sorted(lines)]


def apply(vsav2e, extension, free_space_start, free_space_end):
    """Adds the stage choice to the vsav2e program (a bytearray); the frames go to the
    program extension. Returns the first free address of the program."""
    # an animation step for each choice: 4 bytes, then the frame pointer
    steps = []
    for choice in range(len(STAGES) + 1):
        header = encode_line('SELECT STAGE')
        if choice == 0:
            frame = letters_frame(header, [encode_line('RANDOM')])
        else:
            frame = letters_frame(header, stage_name_lines(vsav2e, STAGES[choice - 1]))
        steps.append(struct.pack('>I', 0) + struct.pack('>I', extension.add(frame)))
    steps_address = extension.add(b''.join(steps))
    stages_address = extension.add(bytes(STAGES))

    choice_count = len(STAGES) + 1
    frame_routine = bytes.fromhex(
        '0c6e%04x%04x' % (MARK, MARK_FIELD) +          # cmpi.w  #MARK, MARK(a6)
        '6670'                                          # bne.s   original
        '0c2d0003' '00ac'                               # cmpi.b  #3, $ac(a5)      two players
        '6668'                                          # bne.s   original
        '306e%04x' % CHALLENGER_FIELD +                 # movea.w challenger(a6), a0
        '3028%04x' % INPUT_BEFORE +                     # move.w  before(a0), d0
        '4640'                                          # not.w   d0
        'c068%04x' % INPUT_NOW +                        # and.w   now(a0), d0       just pressed
        '7200'                                          # moveq   #0, d1
        '122e%04x' % CHOICE_FIELD +                     # move.b  choice(a6), d1
        '0800%04x' % RIGHT_BIT +                        # btst    #right, d0
        '670a'                                          # beq.s   not_right
        '5241'                                          # addq.w  #1, d1
        '0c41%04x' % choice_count +                     # cmpi.w  #count, d1
        '6502'                                          # bcs.s   not_right
        '7200'                                          # moveq   #0, d1
        # not_right:
        '0800%04x' % LEFT_BIT +                         # btst    #left, d0
        '6706'                                          # beq.s   not_left
        '5341'                                          # subq.w  #1, d1
        '6a02'                                          # bpl.s   not_left
        '72%02x' % (choice_count - 1) +                 # moveq   #count - 1, d1
        # not_left:
        '1d41%04x' % CHOICE_FIELD +                     # move.b  d1, choice(a6)
        '342e%04x' % RANDOM_STAGE_FIELD +               # move.w  random(a6), d2
        '4a41'                                          # tst.w   d1
        '670c'                                          # beq.s   stage_set
        '41f9%08x' % stages_address +                   # lea     stages, a0
        '7400'                                          # moveq   #0, d2
        '143010ff'                                      # move.b  -1(a0, d1.w), d2
        # stage_set:
        '3b420100'                                      # move.w  d2, $100(a5)
        'e741'                                          # asl.w   #3, d1            8 bytes a step
        '41f9%08x' % steps_address +                    # lea     steps, a0
        '41f01000'                                      # lea     0(a0, d1.w), a0
        '2d48001c'                                      # move.l  a0, $1c(a6)
        '3d7c%04x0014' % NAME_Y +                       # move.w  #y, $14(a6)
        '4ef9%08x' % REGISTER_FOR_DRAWING +             # jmp     register for drawing
        # original:
        '102e0005'                                      # move.b  $5(a6), d0
        '43f9%08x' % NAME_OBJECT_STATE_TABLE +          # lea     table, a1
        '32310000'                                      # move.w  0(a1, d0.w), d1
        '4ef11000')                                     # jmp     0(a1, d1.w)
    spawn_routine = bytes.fromhex(
        '3b400100'                                      # move.w  d0, $100(a5)     as the game did
        '4eb9%08x' % ALLOCATE_OBJECT +                  # jsr     allocate
        '6718'                                          # beq.s   done
        '28bc%08x' % NAME_OBJECT_KIND +                 # move.l  #kind, (a4)
        '397c%04x%04x' % (MARK, MARK_FIELD) +           # move.w  #MARK, MARK(a4)
        '3940%04x' % RANDOM_STAGE_FIELD +               # move.w  d0, random(a4)
        '422c%04x' % CHOICE_FIELD +                     # clr.b   choice(a4)
        '3949%04x' % CHALLENGER_FIELD +                 # move.w  a1, challenger(a4)
        # done:
        '4e75')                                         # rts

    vs_time_routine = bytes.fromhex(
        '3b7c007f000e'                                  # move.w  #$7f, $e(a5)     as the game did
        '0c2d0003' '00ac'                               # cmpi.b  #3, $ac(a5)
        '6606'                                          # bne.s   done
        '3b7c%04x000e' % VS_TIME_VERSUS +               # move.w  #versus time, $e(a5)
        # done:
        '4e75')                                         # rts
    vs_skip_routine = bytes.fromhex(
        '0c2d0003' '00ac'                               # cmpi.b  #3, $ac(a5)
        '6706'                                          # beq.s   versus
        '4ef9%08x' % VS_SKIP_ROUTINE +                  # jmp     the game's test
        # versus:
        '302d%04x' % PLAYER_1_INPUT_BEFORE +            # move.w  before(a5), d0
        '4640'                                          # not.w   d0
        'c06d%04x' % PLAYER_1_INPUT +                   # and.w   now(a5), d0
        '322d%04x' % PLAYER_2_INPUT_BEFORE +            # move.w  before(a5), d1
        '4641'                                          # not.w   d1
        'c26d%04x' % PLAYER_2_INPUT +                   # and.w   now(a5), d1
        '8041'                                          # or.w    d1, d0
        '0240%04x' % ATTACK_BUTTONS +                   # andi.w  #buttons, d0      Z: none
        '4e75')                                         # rts

    routines = [frame_routine, spawn_routine, vs_time_routine, vs_skip_routine]
    addresses = []
    address = free_space_start + (free_space_start & 1)
    for routine in routines:
        addresses.append(address)
        address += len(routine)
    end = address
    if end > free_space_end:
        raise SystemExit('versus stage: no room for the routines')
    for routine, routine_address in zip(routines, addresses):
        vsav2e[routine_address:routine_address + len(routine)] = routine
    frame_address, spawn_address, vs_time_address, vs_skip_address = addresses

    if vsav2e[VS_TIME_ADDRESS:VS_TIME_ADDRESS + 6] != VS_TIME_ORIGINAL:
        raise SystemExit('versus stage: unexpected code at the VS screen time')
    vsav2e[VS_TIME_ADDRESS:VS_TIME_ADDRESS + 6] = b'\x4e\xb9' + struct.pack('>I', vs_time_address)
    for call in VS_SKIP_CALLS:
        if vsav2e[call:call + 6] != VS_SKIP_ORIGINAL:
            raise SystemExit('versus stage: unexpected code at the VS screen skip 0x%x' % call)
        vsav2e[call:call + 6] = b'\x4e\xb9' + struct.pack('>I', vs_skip_address)

    if vsav2e[STAGE_CHOICE_END:STAGE_CHOICE_END + 6] != STAGE_CHOICE_END_ORIGINAL:
        raise SystemExit('versus stage: unexpected code at the stage choice')
    vsav2e[STAGE_CHOICE_END:STAGE_CHOICE_END + 6] = b'\x4e\xf9' + struct.pack('>I', spawn_address)
    if vsav2e[NAME_OBJECT_FRAME:NAME_OBJECT_FRAME + 12] != NAME_OBJECT_FRAME_ORIGINAL:
        raise SystemExit('versus stage: unexpected code at the stage name object')
    vsav2e[NAME_OBJECT_FRAME:NAME_OBJECT_FRAME + 12] = (b'\x4e\xf9' + struct.pack('>I', frame_address)
                                                        + b'\x4e\x71' * 3)
    return end
