"""The endings of Donovan, Huitzil and Pyron play a slow, heavier version of the music of
their stage in Vampire Hunter 2.

Vampire Hunter 2's stages are not in vsav2e (the three fight on Vampire Savior 2's), and
the endings are the PlayStation game's: no QSound music exists for them anywhere, and the
PlayStation and Saturn ones are CD audio. So the ending of each of the three asks for its
character's stage theme of Vampire Hunter 2 (sound numbers 0x19 Huitzil, 0x1a Pyron, 0x1c
Donovan: found from the number the 68000 asks for when their stage starts), changed
here with the commands the sound program already has:

- the tempo is 0.6 of the original (the word after the track's `05` command: the driver
  takes that much off the length of every note each tick, so less is slower);
- the percussion (instruments whose sample does not loop) is played at 0.4 of its
  volume, but for the low drum (instrument 10 of bank 0) that all the three themes use;
- the three highest tracks that sustain their notes are copied, an octave lower
  (`0b f4`) and a little out of tune (`0c 0a`), as new tracks in unused slots, at 0.9 of
  their volume: the two voices beat, like a chorus.

The format of a sequence (from the driver's code, the commands are the 32 first bytes):

    a note   the bytes from 0x20 on: top 3 bits the length, low 5 the pitch (0: a rest)
    04 nn    flags of the track (octave halves, dotted lengths)     05 hh ll  the tempo
    06 vv    volume          07 nn  envelope       08 nn  instrument of the bank
    09 nn    octave          0b nn  transposition in semitones     0c nn  fine tuning
    0e-15    loops (a count and a 2-byte jump)     16 hh ll  jump, relative to the next byte
    17       end of the track   18, 19, 1a-1e: pan, sets of the envelope, effects
    1f nn    bank of instruments
"""
import struct

# the operand bytes each command takes
OPERANDS = {0x00: 0, 0x01: 0, 0x02: 0, 0x03: 0, 0x04: 1, 0x05: 2, 0x06: 1, 0x07: 1, 0x08: 1,
            0x09: 1, 0x0a: 1, 0x0b: 1, 0x0c: 1, 0x0d: 1, 0x0e: 3, 0x0f: 3, 0x10: 3, 0x11: 3,
            0x12: 3, 0x13: 3, 0x14: 3, 0x15: 3, 0x16: 2, 0x17: 0, 0x18: 1, 0x19: 1, 0x1a: 1,
            0x1b: 1, 0x1c: 1, 0x1d: 1, 0x1e: 1, 0x1f: 1}
TEMPO, VOLUME, INSTRUMENT, OCTAVE, TRANSPOSE, TUNING, END, BANK = 0x05, 0x06, 0x08, 0x09, 0x0b, 0x0c, 0x17, 0x1f

# the stage themes of Vampire Hunter 2, by character (Vampire Savior's numbering)
THEMES = {'huitzil': 0x19, 'pyron': 0x1a, 'donovan': 0x1c}

TEMPO_FACTOR = 0.6
PERCUSSION_VOLUME = 0.4
KEPT_PERCUSSION = 10            # instrument of bank 0: the low drum
DOUBLED_TRACKS = 3
DOUBLE_VOLUME = 0.9
OCTAVE_DOWN = 0xf4              # -12 semitones, as a signed byte
FINE_TUNING = 0x0a              # a few cents
SEQUENCE_HEADER_SIZE = 33       # flags, 16 words: the offset of each track

SAMPLE_TABLE_POINTER = 0x3b02
BANK_POINTERS = 0x3b04
SAMPLE_ENTRY_SIZE = 8


def events(track):
    """[(position, byte, operands)] of a track"""
    result = []
    position = 0
    while position < len(track):
        byte = track[position]
        count = OPERANDS[byte] if byte < 0x20 else 0
        result.append((position, byte, bytes(track[position + 1:position + 1 + count])))
        position += 1 + count
    return result


def track_offsets(sequence):
    return struct.unpack_from('>16H', sequence, 1)


def split_tracks(sequence):
    """[(slot, offset, end)] of the tracks that have code of their own: the unused slots
    point to two-byte tracks (a rest and the end) that share the bytes of the next one"""
    offsets = track_offsets(sequence)
    starts = sorted(set(offset for offset in offsets if offset))
    tracks = []
    for slot, offset in enumerate(offsets):
        if not offset:
            continue
        later = [start for start in starts if start > offset]
        end = min(later) if later else len(sequence)
        if end - offset > 4:
            tracks.append((slot, offset, end))
    return tracks


def is_one_shot(program, bank, number):
    """True if the sample of an instrument does not loop (a drum, a pluck)"""
    table = struct.unpack_from('<H', program, SAMPLE_TABLE_POINTER)[0]
    pointer = struct.unpack_from('<H', program, BANK_POINTERS + 2 * bank)[0]
    sample = struct.unpack_from('<H', program, pointer + 4 * number)[0] & 0x7fff
    start, loop, end = struct.unpack_from('<3H', program, table + SAMPLE_ENTRY_SIZE * sample + 1)
    return end - loop < 64


def track_facts(body):
    """(bank, instrument, place of the first volume operand, mean pitch) of a track"""
    bank = instrument = volume_at = None
    pitches = []
    octave = 0
    for position, byte, operands in events(body):
        if byte == BANK:
            bank = operands[0]
        elif byte == INSTRUMENT and instrument is None:
            instrument = operands[0]
        elif byte == VOLUME and volume_at is None:
            volume_at = position + 1
        elif byte == OCTAVE:
            octave = operands[0] & 7
        elif byte >= 0x20 and byte & 0x1f:
            pitches.append(12 * octave + (byte & 0x1f))
    return bank, instrument, volume_at, sum(pitches) / len(pitches) if pitches else 0


def slowed(sequence, factor=TEMPO_FACTOR):
    """the sequence with its tempo multiplied by `factor` (the word after the `05` of the
    first track that has one)"""
    sequence = bytearray(sequence)
    for slot, offset, end in split_tracks(sequence):
        tempo = [position for position, byte, _ in events(sequence[offset:end]) if byte == TEMPO]
        if tempo:
            at = offset + tempo[0] + 1
            struct.pack_into('>H', sequence, at, round(struct.unpack_from('>H', sequence, at)[0] * factor))
            return bytes(sequence)
    raise SystemExit('stage music: a theme with no tempo')


def remix(hunter, sequence):
    """the slow, heavier version of a stage theme of Vampire Hunter 2 (`hunter`: its sound
    program; `sequence`: the theme). The instruments are still Vampire Hunter 2's banks."""
    sequence = bytearray(slowed(sequence))
    tracks = split_tracks(sequence)
    # the percussion softer (in place); the tracks that sustain their notes are collected
    sustained = []
    for slot, offset, end in tracks:
        bank, instrument, volume_at, mean = track_facts(bytes(sequence[offset:end]))
        if bank is None or instrument is None:
            continue
        one_shot = is_one_shot(hunter, bank, instrument)
        if one_shot and instrument != KEPT_PERCUSSION and volume_at is not None:
            sequence[offset + volume_at] = round(sequence[offset + volume_at] * PERCUSSION_VOLUME)
        if not one_shot:
            sustained.append((mean, bytes(sequence[offset:end])))
    # the highest ones, copied an octave lower
    copies = []
    seen = set()
    for mean, body in sorted(sustained, reverse=True):
        if len(copies) == DOUBLED_TRACKS:
            break
        if body in seen:
            continue        # (two tracks that are the same: one copy)
        seen.add(body)
        body = bytearray(body)
        volume_at = track_facts(bytes(body))[2]
        if volume_at is not None:
            body[volume_at] = round(body[volume_at] * DOUBLE_VOLUME)
        copies.append(bytes([TRANSPOSE, OCTAVE_DOWN, TUNING, FINE_TUNING]) + bytes(body))
    # a track in each unused slot (or one of the two-byte tracks)
    offsets = list(track_offsets(sequence))
    own = set(slot for slot, _, _ in tracks)
    free = [slot for slot in range(16) if slot not in own]
    if len(free) < len(copies):
        raise SystemExit('stage music: no free track slot')
    for slot, copy in zip(free, copies):
        offsets[slot] = len(sequence)
        sequence += copy
    struct.pack_into('>16H', sequence, 1, *offsets)
    return bytes(sequence)


def drop_stray_track(sequence):
    """Pyron's theme has a last track that jumps into another one's code with a bank of
    instruments (29) that does not exist: it plays nothing sensible. It is made one of the
    two-byte tracks."""
    offsets = list(track_offsets(sequence))
    sequence = bytearray(sequence)
    for slot in range(16):
        offset = offsets[slot]
        body = bytes(sequence[offset:offset + 12])
        if offset and any(byte == BANK and operands[0] >= 2 * 8 for _, byte, operands in events(body)[:6]):
            offsets[slot] = offsets[slot - 1]
    struct.pack_into('>16H', sequence, 1, *offsets)
    return bytes(sequence)


def with_banks_added(sequence, added):
    """the sequence with `1f nn` changed to `1f nn + added` in every track (the banks of
    Vampire Hunter 2's instruments are 8 to 15 in vsav2e's sound program)"""
    sequence = bytearray(sequence)
    offsets = track_offsets(sequence)
    starts = sorted(set(offset for offset in offsets if offset))
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(sequence)
        for position, byte, operands in events(sequence[start:end]):
            if byte == BANK and operands[0] < 8:
                sequence[start + position + 1] = operands[0] + added
    return bytes(sequence)
