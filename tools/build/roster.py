"""Jon Talbain, Rikuo and Sasquatch: giving them back their sprites.

Vampire Savior 2 still has the three characters of Vampire Hunter 2 it left out: their
code, their moves and their animations are in the program, and they can be played. What
was removed is what they look like:

- every step of an animation holds a pointer to a *frame* (the list of the sprites that
  make one picture); in Vampire Savior 2 all the frame pointers of these characters point
  at one place past the end of their animations, where no frame is;
- their tiles are not in the graphics ROMs.

Vampire Hunter 2 has both. So for each character:

1. the animations of the two games are matched step by step (they are the same data but
   for the frame pointers and a few values);
2. the frames of Vampire Hunter 2, and the *shapes* they point to (where each sprite
   goes), are copied to the program extension at 0x400000;
3. each frame pointer of Vampire Savior 2 is set to the copy of its frame.

The tiles come from the sprite ROMs of Vampire Hunter 2, the upper half of vsav2e's
64 MB sprite space: a sprite whose Y has bit 12 set takes its tile from there. The
three places that start drawing a frame are hooked: for a frame of the extension they
set that bit in the word the game ORs into every sprite Y (`$18` of the object), draw,
and clear it.

The two types of frame these characters use:

    type 2, sprites with their own attributes     type 0, sprites that share them
    word   2                                      word   0
    word   room the frame takes in the list       word   number of sprites
    word   number of sprites - 1                  word   attributes
    long   pointer to the shape                   long   pointer to the shape
    for each sprite: word tile, word attributes   for each sprite: word tile

The shape is where each sprite goes: x and y (two words) for each one.
"""
import difflib
import struct

from build.extension import EXTENSION_START

PROGRAM_SIZE = 0x400000

FRAME_TYPE_SHARED_ATTRIBUTES = 0
FRAME_TYPE_OWN_ATTRIBUTES = 2
FRAME_HEADER_SIZE = 10
FRAME_MAXIMUM_SPRITES = 0x100

# For each character: the place its frame pointers were all set to in Vampire Savior 2
# (the end of its animations), and its frames in Vampire Hunter 2 (first byte, end).
CHARACTERS = (
    ('Jon Talbain', 0x137e7c, (0x12a310, 0x134fc0)),
    ('Rikuo', 0x1cf506, (0x1cc57e, 0x1d6638)),
    ('Sasquatch', 0x1d872e, (0x1df860, 0x1e6e30)),
)
# The animations of a character end where its frames start in Vampire Hunter 2; they are
# searched from this many bytes before where Vampire Savior 2's would start.
ANIMATIONS_SEARCH_MARGIN = 0x200

# The three places that jump to the routine drawing a frame, by its type. Each is
#     move.w (a0)+, d0              the frame type (a0: the frame)
#     move.w table(pc, d0.w), d0    the offset of its routine
#     jmp    table(pc, d0.w)
# and is reached either from the code that takes the frame of the object (a6) or from
# code that has a frame of its own in a0.
FRAME_DISPATCH_ADDRESSES = (0x199dc, 0x1a248, 0x1a262)
FRAME_DISPATCH_TYPE_AND_OFFSET = bytes.fromhex('3018303b')      # the two move.w (without the table)
FRAME_DISPATCH_JUMP = bytes.fromhex('4efb')

# The two `move.w` become a call to the hook, which does what they did and, for a frame
# of the extension, runs the routine itself with the upper sprite bank selected: bit 12
# of the word the routines OR into every sprite Y, `$18` of the object.
SPRITE_Y_UPPER_BANK_BIT = 4         # bit 12 of the word at $18(a6) is bit 4 of its first byte
HOOK_CODE = bytes.fromhex(
    '2257'          # movea.l (a7), a1             the `jmp table(pc, d0.w)` we return to
    '10290003'      # move.b  3(a1), d0            its displacement
    '4880'          # ext.w   d0
    '43f10002'      # lea     2(a1, d0.w), a1      the table
    '3018'          # move.w  (a0)+, d0            the frame type
    '30310000'      # move.w  (a1, d0.w), d0       the offset of its routine
    'b1fc' + '%08x' % EXTENSION_START +     # cmpa.l #EXTENSION_START, a0
    '6202'          # bhi.s   extension_frame
    '4e75'          # rts                          to the jmp
    # extension_frame:
    '08ee' + '%04x' % SPRITE_Y_UPPER_BANK_BIT + '0018'      # bset #4, $18(a6)
    '588f'          # addq.l  #4, a7               not back to the jmp:
    '4eb10000'      # jsr     (a1, d0.w)           draw the frame from here
    '08ae' + '%04x' % SPRITE_Y_UPPER_BANK_BIT + '0018'      # bclr #4, $18(a6)
    '4e75')         # rts                          to the caller of the dispatch


def read_word(data, address):
    return struct.unpack_from('>H', data, address)[0]


def read_long(data, address):
    return struct.unpack_from('>I', data, address)[0]


def frame_sprites(program, frame):
    """the number of sprites of a frame, or None when there is no frame there"""
    frame_type = read_word(program, frame)
    if frame_type == FRAME_TYPE_OWN_ATTRIBUTES:
        sprites = read_word(program, frame + 4) + 1
    elif frame_type == FRAME_TYPE_SHARED_ATTRIBUTES:
        sprites = read_word(program, frame + 2)
    else:
        return None
    shape = read_long(program, frame + 6)
    if not 1 <= sprites <= FRAME_MAXIMUM_SPRITES or shape % 2 or shape + 4 * sprites > PROGRAM_SIZE:
        return None
    return sprites


def frame_size(program, frame):
    sprites = frame_sprites(program, frame)
    if read_word(program, frame) == FRAME_TYPE_OWN_ATTRIBUTES:
        return FRAME_HEADER_SIZE + 4 * sprites
    return FRAME_HEADER_SIZE + 2 * sprites


def split_at_frame_pointers(data, start, end, is_frame_pointer):
    """The data from start to end as a list of (bytes before a frame pointer, address of
    that frame pointer): one item per animation step."""
    steps = []
    step_start = address = start
    while address + 4 <= end:
        if is_frame_pointer(read_long(data, address)):
            steps.append((bytes(data[step_start:address]), address))
            address += 4
            step_start = address
        else:
            address += 2
    return steps


def match_animation_steps(savior_steps, hunter_steps):
    """{address of a frame pointer in Vampire Savior 2: address of the same one in
    Vampire Hunter 2}. Steps are matched by the data before their frame pointer; where a
    run of steps differs in both games by the same number of steps (a changed value),
    they are paired in order."""
    matcher = difflib.SequenceMatcher(None, [data for data, _ in savior_steps],
                                      [data for data, _ in hunter_steps], autojunk=False)
    pairs = {}
    for tag, savior_first, savior_last, hunter_first, hunter_last in matcher.get_opcodes():
        same_length = savior_last - savior_first == hunter_last - hunter_first
        if tag == 'equal' or (tag == 'replace' and same_length):
            for offset in range(savior_last - savior_first):
                pairs[savior_steps[savior_first + offset][1]] = hunter_steps[hunter_first + offset][1]
    return pairs


def copy_frames(hunter, frame_addresses, extension):
    """Copies frames of Vampire Hunter 2, with their shapes, to the extension.
    Returns {frame address in Vampire Hunter 2: address of the copy}."""
    # a shape has no length of its own: it is as long as the biggest frame that uses it
    shape_sprites = {}
    for frame in frame_addresses:
        shape = read_long(hunter, frame + 6)
        shape_sprites[shape] = max(shape_sprites.get(shape, 0), frame_sprites(hunter, frame))
    shape_copy = {shape: extension.add(hunter[shape:shape + 4 * sprites])
                  for shape, sprites in sorted(shape_sprites.items())}

    frame_copy = {}
    for frame in sorted(frame_addresses):
        record = bytearray(hunter[frame:frame + frame_size(hunter, frame)])
        struct.pack_into('>I', record, 6, shape_copy[read_long(hunter, frame + 6)])
        frame_copy[frame] = extension.add(record)
    return frame_copy


def restore_character(vsav2e, hunter, extension, name, stripped_pointer, hunter_frames):
    """Points every stripped frame pointer of a character at a copy of its frame.
    Returns (frame pointers set, frames copied)."""
    frames_start, frames_end = hunter_frames
    savior_end = stripped_pointer
    savior_start = vsav2e.find(struct.pack('>I', stripped_pointer))
    savior_steps = split_at_frame_pointers(vsav2e, savior_start, savior_end,
                                           lambda value: value == stripped_pointer)
    hunter_start = frames_start - (savior_end - savior_start) - ANIMATIONS_SEARCH_MARGIN

    def is_hunter_frame(value):
        # other values of an animation step can fall in the range of the frames
        return (frames_start <= value < frames_end and value % 2 == 0
                and frame_sprites(hunter, value) is not None)

    hunter_steps = split_at_frame_pointers(hunter, hunter_start, frames_start, is_hunter_frame)
    # the first step of each list starts with data that is not of this character
    savior_steps[0] = (b'', savior_steps[0][1])
    hunter_steps[0] = (b'', hunter_steps[0][1])

    pairs = match_animation_steps(savior_steps, hunter_steps)
    unmatched = [address for _, address in savior_steps if address not in pairs]
    if unmatched:
        raise SystemExit('roster: %s, %d animation steps not found in Vampire Hunter 2 (first at 0x%x)'
                         % (name, len(unmatched), unmatched[0]))

    frame_of = {savior_pointer: read_long(hunter, hunter_pointer)
                for savior_pointer, hunter_pointer in pairs.items()}
    frame_copy = copy_frames(hunter, set(frame_of.values()), extension)
    for savior_pointer, frame in frame_of.items():
        struct.pack_into('>I', vsav2e, savior_pointer, frame_copy[frame])
    return len(frame_of), len(frame_copy)


def hook_frame_dispatch(vsav2e, hook_address):
    """writes the hook and makes the three frame dispatch routines call it"""
    vsav2e[hook_address:hook_address + len(HOOK_CODE)] = HOOK_CODE
    call = b'\x4e\xb9' + struct.pack('>I', hook_address)        # jsr hook
    for address in FRAME_DISPATCH_ADDRESSES:
        jump = address + len(call)
        if (vsav2e[address:address + 4] != FRAME_DISPATCH_TYPE_AND_OFFSET
                or vsav2e[jump:jump + 2] != FRAME_DISPATCH_JUMP
                or vsav2e[address + 4:address + 6] != bytes([0, vsav2e[jump + 3] + 4])):
            # (the two tables must be one: the jmp is 4 bytes further, so its
            # displacement is 4 less)
            raise SystemExit('roster: unexpected code at the frame dispatch 0x%x' % address)
        vsav2e[address:address + len(call)] = call
    return hook_address + len(HOOK_CODE)


def apply(vsav2e, hunter, extension, free_space_start, free_space_end):
    """Restores the three characters in the vsav2e program (a bytearray), with their
    frames in the program extension. Returns the first free address after the hook."""
    if free_space_start + len(HOOK_CODE) > free_space_end:
        raise SystemExit('roster: no room for the frame hook')
    free_space = hook_frame_dispatch(vsav2e, free_space_start + (free_space_start & 1))
    for name, stripped_pointer, hunter_frames in CHARACTERS:
        pointers, frames = restore_character(vsav2e, hunter, extension, name, stripped_pointer, hunter_frames)
        print('roster: %-11s %4d frame pointers, %3d frames' % (name, pointers, frames))
    return free_space
