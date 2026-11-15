"""The voices of Jon Talbain, Rikuo and Sasquatch, and the music of Vampire Savior's endings.

The sound of a CPS2 game is a Z80 program (`.01` and `.02`, 256 KB together) driving the
QSound chip, which plays samples from 8 MB of ROM (`.11m`, `.12m`). The 68000 asks for a
sound by number, and that number is the index of a *sequence*; the numbers are the same
in Vampire Savior 2 and Vampire Hunter 2. The data of the Z80 program:

    0x3b02          word: address of the sample table
    0x3b04          8 words: address of each bank of instruments
    sample table    8 bytes per sample: its 64 KB bank in the sample ROM, start, loop
                    and end inside the bank (words, low byte first), a note
    instruments     4 bytes each: sample number (word, low byte first; the top bit is a
                    flag), a byte, number of its set of envelopes
    envelopes       8 bytes per set, at an address the code knows
    0x9001          the sequences: 4 bytes per entry (high byte first) with the place
                    of the sequence in the two files read as one; 0 for none. Sound
                    number n plays entry n + 1 (a log of the Z80's reads shows it).
    a sequence      a byte of flags, 16 words (high byte first) with the offset of each
                    track, the tracks. In a track `1f nn` picks the bank of instruments
                    and `08 nn` the instrument.

The program sees its first 32 KB at their addresses and the rest 16 KB at a time, at
0x8000 (bank 0 is the file from 0x8000). The tables above are in the first 32 KB.

Vampire Savior 2 has no sequence where Vampire Hunter 2 has the voices of the three
characters, and its sample ROMs do not have their samples. vsav2e:

- has 16 MB of samples, Vampire Hunter 2's two ROMs after its own (64 KB banks 0x80 to
  0xff);
- adds all the samples of Vampire Hunter 2 to the sample table (in those banks), its
  sets of envelopes that are new, and its eight banks of instruments as banks 8 to 15,
  pointing at the added samples and envelopes. The tables that grow are moved: the
  sample table stays where it is and runs over the envelopes, which go after it with the
  list of banks and the new banks, in the unused end of the first 32 KB;
- copies the sequences Vampire Savior 2 does not have (but for the music, which is long
  and not asked for) to the file from 0x38000, the start of bank 12, unused;
- changes `1f nn` so that in a sequence of bank 12 it picks bank nn + 8: the copied
  sequences then play with the instruments they were written for.

The endings of Vampire Savior (docs/endings.md) ask for its music. vsav2e copies those
sequences under new numbers (free in Vampire Savior 2) to banks 13 to 15, the end of a
sound program now 288 KB (the Z80 reaches 16 banks). Their instruments are Vampire
Savior 2's but for three that changed (in banks 1, 5 and 6): those banks get copies (as
far as the endings use them, banks 16-18) with Vampire Savior's instruments, and in a
sequence of bank 13 or more `1f nn` picks bank nn through a small table. Every sample
of those copies is somewhere in vsav2e's 16 MB of samples (Vampire Savior 2's or
Vampire Hunter 2's ROMs); the entries the copies add to the sample table point there.
The entries of Vampire Hunter 2's samples that are also in Vampire Savior 2's ROMs
point at Vampire Savior 2's copy: the table stays small enough for the first 32 KB.

The endings of Donovan, Huitzil and Pyron have no music in any arcade game: they play the
stage themes of Vampire Hunter 2 slowed and remixed (`stage_music.py`), copied after the
music of Vampire Savior's endings (or in bank 12 if one fits there).
"""
import struct

from . import stage_music

FIXED_AREA_END = 0x8000                 # the part the Z80 always sees
SAMPLE_TABLE_POINTER = 0x3b02
INSTRUMENT_BANK_POINTERS = 0x3b04
INSTRUMENT_BANKS = 8
SAMPLE_ENTRY_SIZE = 8
INSTRUMENT_ENTRY_SIZE = 4
ENVELOPE_ENTRY_SIZE = 8
MAXIMUM_ENVELOPE_SETS = 128             # an instrument gives the set in 7 bits
SEQUENCE_TABLE = 0x9001
SEQUENCE_TABLE_END = 0xb800
SEQUENCE_HEADER_SIZE = 33
SAMPLE_ROM_UPPER_HALF = 0x80            # 64 KB bank of the first sample of the added ROMs

# Vampire Savior 2: the code that holds the address of the envelopes (`ld bc, nn`, the
# address is the two bytes after the opcode) and the one of the list of instrument banks
SAVIOR_ENVELOPES = 0x5bd8
ENVELOPE_ADDRESS_OPERANDS = (0x0d85, 0x129f)
BANK_LIST_ADDRESS_OPERANDS = (0x0d19,)       # (the other one is in the code below)
# `1f nn`: `ld a, (de)` / `inc de` / `ld bc, INSTRUMENT_BANK_POINTERS`
PICK_BANK_ADDRESS = 0x17d5
PICK_BANK_ORIGINAL = bytes.fromhex('1a1301043b')
# Vampire Hunter 2
HUNTER_ENVELOPES = 0x59a8

# the copied sequences
COPIED_SEQUENCES_START = 0x38000
COPIED_SEQUENCES_BANK = (COPIED_SEQUENCES_START - 0x8000) // 0x4000
ADDED_BANKS_FIRST = INSTRUMENT_BANKS    # Vampire Hunter 2's bank n is bank n + 8
# sequences longer than this are music
LONGEST_COPIED_SEQUENCE = 1100
# a track that only sets the tempo and ends: a sequence made of these plays nothing
SILENT_TRACK = bytes.fromhex('05036d2017')


def read_word(data, address):
    """a word of the Z80, low byte first"""
    return struct.unpack_from('<H', data, address)[0]


def sequence_places(sound):
    """the place of each sequence in the file, by entry (0: none; sound number n plays
    entry n + 1)"""
    places = [struct.unpack_from('>I', sound, address)[0]
              for address in range(SEQUENCE_TABLE, SEQUENCE_TABLE_END - 3, 4)]
    places[0] = 0       # the first entry is not a sequence
    return places


def sequence_data(sound, places, number):
    """The bytes of a sequence, or None: it runs to the next sequence in the file that
    starts after its last track (other sequences may start inside it: Vampire Savior has
    entries pointing into the middle of the music of some endings)."""
    start = places[number]
    if not start:
        return None
    last_track = start + max(struct.unpack_from('>16H', sound, start + 1))
    later = [place for place in places if place > last_track]
    end = min(later) if later else len(sound.rstrip(b'\x00')) + 1
    return bytes(sound[start:end])


def is_silent(sequence):
    return sequence[SEQUENCE_HEADER_SIZE:].replace(SILENT_TRACK, b'').strip(b'\x00') == b''


def table_end(sound, start, entry_size):
    """the end of a table followed by zeros"""
    used = len(bytes(sound[start:FIXED_AREA_END]).rstrip(b'\x00'))
    return start + (used + entry_size - 1) // entry_size * entry_size


SOUND_PROGRAM_SIZE_WITH_ENDINGS = 0x48000     # 16 banks of 16 KB after the first 32 KB
ENDING_MUSIC_START = 0x3c000                    # bank 13
BANK_SIZE = 0x4000
SAMPLE_BANK_SIZE = 0x10000
# Vampire Savior: the sample table ends where its envelopes start
SAVIOR1_ENVELOPES = 0x5a1a
# the banks of instruments the music of the endings uses, and how far (the Z80's reads in
# the 14 endings), where an instrument used differs from Vampire Savior 2's: bank 1 #3,
# bank 5 #59, bank 6 #39 (bank 0 is used too, up to #114, the same in both games)
SAVIOR1_BANKS_USED = {1: 71, 5: 60, 6: 40}
SAVIOR1_BANKS_FIRST = 2 * INSTRUMENT_BANKS      # their copies: banks 16, 17, 18
SOUND_ENTRY_OFFSET = 1                          # sound number n plays entry n + 1
FIRST_FREE_SEQUENCE = 0x50                      # the new numbers of that music start here
SOUND_PROGRAM_FIRST_FILE = 0x20000             # vs2e.01: the first 128 KB


class SampleTable:
    """the sample table of vsav2e: Vampire Savior 2's entries first, then the others,
    each entry once; the data of an entry is in the sample ROMs given (vsav2e's 16 MB)"""

    def __init__(self, entries, roms):
        self.entries = [bytes(entry) for entry in entries]
        self.roms = roms
        self.index = {}
        for number, entry in enumerate(self.entries):
            self.index.setdefault(self.signature(entry), number)

    def data(self, entry):
        start, end = read_word(entry, 1), read_word(entry, 5)
        base = entry[0] * SAMPLE_BANK_SIZE
        return bytes(self.roms[base + start:base + end])

    def signature(self, entry):
        """what makes two entries sound the same: the data, the loop, the note"""
        start, loop = read_word(entry, 1), read_word(entry, 3)
        return self.data(entry), (loop - start) & 0xffff, entry[7]

    def number(self, entry):
        """the number of an entry that sounds like this one, added if there is none"""
        signature = self.signature(entry)
        if signature not in self.index:
            self.index[signature] = len(self.entries)
            self.entries.append(bytes(entry))
        return self.index[signature]


def moved_entry(entry, address, length):
    """a sample table entry like this one, for its data copied to an address of the 16 MB
    of samples"""
    bank, start = address // SAMPLE_BANK_SIZE, address % SAMPLE_BANK_SIZE
    loop_offset = (read_word(entry, 3) - read_word(entry, 1)) & 0xffff
    return (bytes([bank]) + struct.pack('<HHH', start, (start + loop_offset) & 0xffff, (start + length) & 0xffff)
            + bytes(entry[7:8]))


def swap_pairs(data):
    """the sample ROM files have the bytes of each word swapped (ROM_LOAD16_WORD_SWAP)"""
    swapped = bytearray(len(data))
    swapped[0::2], swapped[1::2] = data[1::2], data[0::2]
    return swapped


def free_sequence_numbers(sound, count, taken):
    """sound numbers whose entry has no sequence (or a silent one) in a sound program and
    is not taken, after the numbers the games use"""
    places = sequence_places(sound)
    numbers = []
    for number in range(FIRST_FREE_SEQUENCE, len(places) - SOUND_ENTRY_OFFSET):
        entry = number + SOUND_ENTRY_OFFSET
        if entry in taken:
            continue
        if places[entry] and not is_silent(sequence_data(sound, places, entry)):
            continue
        numbers.append(number)
        if len(numbers) == count:
            return numbers
    raise SystemExit('sound: not enough free sequence numbers')


def remix_theme(hunter, sequence):
    """a stage theme of Vampire Hunter 2 as the endings play it"""
    return stage_music.drop_stray_track(stage_music.remix(hunter, sequence))


def apply(savior, hunter, savior_samples, hunter_samples, savior1, savior1_samples, ending_music):
    """Returns (the sound program of vsav2e, 288 KB; Vampire Savior's numbers of the ending
    music -> vsav2e's; the numbers of the stage themes of Huitzil, Pyron and Donovan, by name).
    savior, hunter, savior1: the sound programs (`.01` + `.02`) of Vampire Savior 2,
    Vampire Hunter 2 and Vampire Savior; *_samples their sample ROM files (`.11m` + `.12m`).
    ending_music: Vampire Savior's numbers of the music its endings ask for. (The sound
    effects they ask for are Vampire Hunter 2's too, the same sequences: copied above.)"""
    sound = bytearray(savior) + bytearray(SOUND_PROGRAM_SIZE_WITH_ENDINGS - len(savior))
    # the samples as the QSound chip sees them
    samples_16mb = bytes(swap_pairs(savior_samples) + swap_pairs(hunter_samples))
    savior1_samples = swap_pairs(savior1_samples)

    # --- the sample table: Vampire Savior 2's, then Vampire Hunter 2's that are not the same
    savior_table = read_word(savior, SAMPLE_TABLE_POINTER)
    if SAVIOR_ENVELOPES <= savior_table or any(savior[SAVIOR_ENVELOPES + 0x248:FIXED_AREA_END]):
        raise SystemExit('sound: unexpected layout of the Vampire Savior 2 program')
    savior_sample_count = (SAVIOR_ENVELOPES - savior_table) // SAMPLE_ENTRY_SIZE
    table = SampleTable([savior[savior_table + SAMPLE_ENTRY_SIZE * k:savior_table + SAMPLE_ENTRY_SIZE * (k + 1)]
                         for k in range(savior_sample_count)], samples_16mb)
    hunter_table = read_word(hunter, SAMPLE_TABLE_POINTER)
    hunter_sample_count = (HUNTER_ENVELOPES - hunter_table) // SAMPLE_ENTRY_SIZE
    hunter_number = {}
    for k in range(hunter_sample_count):
        entry = bytearray(hunter[hunter_table + SAMPLE_ENTRY_SIZE * k:hunter_table + SAMPLE_ENTRY_SIZE * (k + 1)])
        entry[0] |= SAMPLE_ROM_UPPER_HALF
        hunter_number[k] = table.number(entry)

    found_samples = {}

    def find_sample(data):
        """an address of the 16 MB of samples with this data, inside one 64 KB bank"""
        if data not in found_samples:
            found = samples_16mb.find(data)
            while found >= 0 and found // SAMPLE_BANK_SIZE != (found + len(data) - 1) // SAMPLE_BANK_SIZE:
                found = samples_16mb.find(data, found + 1)
            if found < 0:
                raise SystemExit('sound: a sample of Vampire Savior is in no sample ROM of vsav2e')
            found_samples[data] = found
        return found_samples[data]

    # --- envelopes: Vampire Savior 2's, then the sets of the others that are not there
    savior_envelopes_end = table_end(savior, SAVIOR_ENVELOPES, ENVELOPE_ENTRY_SIZE)
    envelopes = [bytes(savior[address:address + ENVELOPE_ENTRY_SIZE])
                 for address in range(SAVIOR_ENVELOPES, savior_envelopes_end, ENVELOPE_ENTRY_SIZE)]

    def envelope_number(program, envelopes_address, number):
        envelope = bytes(program[envelopes_address + ENVELOPE_ENTRY_SIZE * number:
                                 envelopes_address + ENVELOPE_ENTRY_SIZE * (number + 1)])
        if envelope not in envelopes:
            envelopes.append(envelope)
        return envelopes.index(envelope)

    # --- instruments: Vampire Hunter 2's banks, with vsav2e's numbers of samples and sets
    def bank_ranges(program, table_address):
        starts = [read_word(program, INSTRUMENT_BANK_POINTERS + 2 * bank) for bank in range(INSTRUMENT_BANKS)]
        return list(zip(starts, starts[1:] + [table_address]))

    added_banks = []
    for start, end in bank_ranges(hunter, hunter_table):
        bank = bytearray(hunter[start:end])
        for entry in range(0, len(bank), INSTRUMENT_ENTRY_SIZE):
            sample = read_word(bank, entry)
            # (an instrument that is not used may name a sample or a set that does not exist)
            number = hunter_number.get(sample & 0x7fff, (sample & 0x7fff) + savior_sample_count)
            struct.pack_into('<H', bank, entry, (sample & 0x8000) | number)
            # (a set past the end of the table is what the game reads there: zeros)
            envelope = bank[entry + 3] & 0x7f
            bank[entry + 3] = (bank[entry + 3] & 0x80) | envelope_number(hunter, HUNTER_ENVELOPES, envelope)
        added_banks.append(bank)

    # Vampire Savior's banks 0, 1, 5 as far as the endings use them: Vampire Savior 2's
    # instruments, but Vampire Savior's where the two differ
    savior1_table = read_word(savior1, SAMPLE_TABLE_POINTER)
    savior1_banks = bank_ranges(savior1, savior1_table)
    savior2_banks = bank_ranges(savior, savior_table)
    copied_banks = {}
    for bank_number, length in SAVIOR1_BANKS_USED.items():
        start1, start2 = savior1_banks[bank_number][0], savior2_banks[bank_number][0]
        bank = bytearray(savior[start2:start2 + INSTRUMENT_ENTRY_SIZE * length])
        for index in range(length):
            instrument1 = savior1[start1 + INSTRUMENT_ENTRY_SIZE * index:start1 + INSTRUMENT_ENTRY_SIZE * (index + 1)]
            sample1 = read_word(instrument1, 0)
            entry1 = savior1[savior1_table + SAMPLE_ENTRY_SIZE * (sample1 & 0x7fff):
                             savior1_table + SAMPLE_ENTRY_SIZE * ((sample1 & 0x7fff) + 1)]
            start, end = read_word(entry1, 1), read_word(entry1, 5)
            data = bytes(savior1_samples[entry1[0] * SAMPLE_BANK_SIZE + start:entry1[0] * SAMPLE_BANK_SIZE + end])
            number = table.number(moved_entry(entry1, find_sample(data), len(data)))
            envelope = envelope_number(savior1, SAVIOR1_ENVELOPES, instrument1[3] & 0x7f)
            instrument = (struct.pack('<H', (sample1 & 0x8000) | number) + bytes([instrument1[2]])
                          + bytes([(instrument1[3] & 0x80) | envelope]))
            bank[INSTRUMENT_ENTRY_SIZE * index:INSTRUMENT_ENTRY_SIZE * (index + 1)] = instrument
        copied_banks[bank_number] = bank
    if len(envelopes) > MAXIMUM_ENVELOPE_SETS:
        raise SystemExit('sound: too many sets of envelopes')
    # the 128 sets an instrument can name: the ones past the end of the table read zeros,
    # as in the three games (Vampire Hunter 2 has instruments naming set 127)
    used_envelope_sets = len(envelopes)
    envelopes += [bytes(ENVELOPE_ENTRY_SIZE)] * (MAXIMUM_ENVELOPE_SETS - len(envelopes))

    # --- the new layout of the end of the fixed area
    address = savior_table
    for entry in table.entries:
        sound[address:address + SAMPLE_ENTRY_SIZE] = entry
        address += SAMPLE_ENTRY_SIZE
    envelopes_address = address
    sound[address:address + ENVELOPE_ENTRY_SIZE * len(envelopes)] = b''.join(envelopes)
    address += ENVELOPE_ENTRY_SIZE * len(envelopes)
    bank_count = SAVIOR1_BANKS_FIRST + len(copied_banks)
    bank_list_address = address
    address += 2 * bank_count
    bank_addresses = [read_word(savior, INSTRUMENT_BANK_POINTERS + 2 * bank) for bank in range(INSTRUMENT_BANKS)]
    for bank in added_banks + [copied_banks[number] for number in sorted(copied_banks)]:
        bank_addresses.append(address)
        sound[address:address + len(bank)] = bank
        address += len(bank)
    sound[bank_list_address:bank_list_address + 2 * len(bank_addresses)] = struct.pack(
        '<%dH' % len(bank_addresses), *bank_addresses)
    # banks for the sequences of bank 13 and after: Vampire Savior's copies, or Vampire Savior 2's
    remap_address = address
    remap = bytes(SAVIOR1_BANKS_FIRST + sorted(copied_banks).index(bank) if bank in copied_banks else bank
                  for bank in range(INSTRUMENT_BANKS))
    # (a sequence of Vampire Hunter 2 in these banks names its banks 8 to 15 itself: stage_music.py)
    remap += bytes(range(INSTRUMENT_BANKS, ADDED_BANKS_FIRST + INSTRUMENT_BANKS))
    sound[address:address + len(remap)] = remap
    address += len(remap)

    # `1f nn`: the bank of instruments, by the bank the track is read from
    list_low, list_high = bank_list_address & 0xff, bank_list_address >> 8
    # (Vampire Savior 2's own sequences, the most common case, take the shortest path: every
    # cycle the driver spends here moves its notes a little against the timer)
    if (ENDING_MUSIC_START - 0x8000) // BANK_SIZE != COPIED_SEQUENCES_BANK + 1:
        raise SystemExit('sound: the bank pick routine expects the ending music right after bank 12')
    pick_bank_routine = bytes.fromhex(
        'dd7e01'            # 00 ld   a, (ix+1)        the bank the track is read from
        'fe%02x'            # 03 cp   COPIED_SEQUENCES_BANK
        '3006'              # 05 jr   nc, later        (flags kept below)
        '1a'                # 07 ld   a, (de)          nn: Vampire Savior 2's sequence
        '13'                # 08 inc  de
        # done:
        '01%02x%02x'        # 09 ld   bc, the list of banks
        'c9'                # 0c ret
        # later:
        '1a'                # 0d ld   a, (de)          nn
        '13'                # 0e inc  de
        '2004'              # 0f jr   nz, savior1      bank 13 or more
        'c6%02x'            # 11 add  a, ADDED_BANKS_FIRST   bank 12: Vampire Hunter 2's
        '18f4'              # 13 jr   done
        # savior1:
        'e5'                # 15 push hl
        '21%02x%02x'        # 16 ld   hl, remap
        '85'                # 19 add  a, l
        '6f'                # 1a ld   l, a
        '3001'              # 1b jr   nc, +1
        '24'                # 1d inc  h
        '7e'                # 1e ld   a, (hl)
        'e1'                # 1f pop  hl
        '18e7'              # 20 jr   done
        % (COPIED_SEQUENCES_BANK, list_low, list_high, ADDED_BANKS_FIRST,
           remap_address & 0xff, remap_address >> 8))
    pick_bank_address = address
    address += len(pick_bank_routine)
    if address > FIXED_AREA_END:
        raise SystemExit('sound: the tables do not fit in the first 32 KB (0x%x)' % address)
    sound[pick_bank_address:pick_bank_address + len(pick_bank_routine)] = pick_bank_routine
    if sound[PICK_BANK_ADDRESS:PICK_BANK_ADDRESS + 5] != PICK_BANK_ORIGINAL:
        raise SystemExit('sound: unexpected code at the choice of the instrument bank')
    sound[PICK_BANK_ADDRESS:PICK_BANK_ADDRESS + 5] = (b'\xcd' + struct.pack('<H', pick_bank_address)      # call
                                                      + b'\x00\x00')                                    # nop, nop

    for operand in ENVELOPE_ADDRESS_OPERANDS:
        if read_word(sound, operand) != SAVIOR_ENVELOPES:
            raise SystemExit('sound: unexpected code at 0x%x' % operand)
        struct.pack_into('<H', sound, operand, envelopes_address)
    for operand in BANK_LIST_ADDRESS_OPERANDS:
        if read_word(sound, operand) != INSTRUMENT_BANK_POINTERS:
            raise SystemExit('sound: unexpected code at 0x%x' % operand)
        struct.pack_into('<H', sound, operand, bank_list_address)

    # --- sequences of Vampire Hunter 2 that Vampire Savior 2 does not have
    savior_places = sequence_places(savior)
    hunter_places = sequence_places(hunter)
    if any(sound[COPIED_SEQUENCES_START:]):
        raise SystemExit('sound: the place of the copied sequences is not empty')
    place = COPIED_SEQUENCES_START
    copied = []
    for number in range(1, len(hunter_places)):
        sequence = sequence_data(hunter, hunter_places, number)
        if sequence is None or is_silent(sequence) or len(sequence) > LONGEST_COPIED_SEQUENCE:
            continue
        existing = sequence_data(savior, savior_places, number)
        if existing is not None and not is_silent(existing):
            continue
        if place + len(sequence) > ENDING_MUSIC_START:
            raise SystemExit('sound: no room for the sequences')
        sound[place:place + len(sequence)] = sequence
        struct.pack_into('>I', sound, SEQUENCE_TABLE + 4 * number, place)
        place += len(sequence)
        copied.append(number)

    # --- the music of Vampire Savior's endings, under new numbers. A sequence keeps its
    # place inside the 16 KB window when it runs over the end of a bank in Vampire Savior
    # (the driver goes on in the next bank: it then does exactly the same); the others go
    # where they fit, inside one bank.
    savior1_places = sequence_places(savior1)
    new_numbers = dict(zip(sorted(ending_music), free_sequence_numbers(savior, len(ending_music), copied)))
    entry = {number: number + SOUND_ENTRY_OFFSET for number in list(new_numbers) + list(new_numbers.values())}
    sequences = {number: sequence_data(savior1, savior1_places, entry[number]) for number in new_numbers}

    free = [[ENDING_MUSIC_START, SOUND_PROGRAM_SIZE_WITH_ENDINGS]]

    def window_offset(address):
        return (address - 0x8000) % BANK_SIZE

    def take(start, length):
        for gap in free:
            if gap[0] <= start and start + length <= gap[1]:
                free.remove(gap)
                free.extend(part for part in ([gap[0], start], [start + length, gap[1]]) if part[1] > part[0])
                free.sort()
                return start
        return None

    def crosses(address, length):
        return window_offset(address) + length > BANK_SIZE

    placed = {}
    for number, sequence in sorted(sequences.items(), key=lambda item: item[1] is None or not crosses(
            savior1_places[entry[item[0]]], len(item[1]))):
        if sequence is None:
            continue        # (Vampire Savior has none: silence, like the free number)
        if crosses(savior1_places[entry[number]], len(sequence)):
            candidates = [bank_start + window_offset(savior1_places[entry[number]])
                          for bank_start in range(ENDING_MUSIC_START, SOUND_PROGRAM_SIZE_WITH_ENDINGS, BANK_SIZE)]
        else:
            candidates = sorted(set(gap[0] for gap in free) | set(
                (gap[0] - 0x8000) // BANK_SIZE * BANK_SIZE + BANK_SIZE + 0x8000 for gap in free))
            candidates = [start for start in candidates if not crosses(start, len(sequence))]
        for music_address in candidates:
            if take(music_address, len(sequence)) is not None:
                break
        else:
            raise SystemExit('sound: no room for the music of the endings')
        sound[music_address:music_address + len(sequence)] = sequence
        struct.pack_into('>I', sound, SEQUENCE_TABLE + 4 * entry[new_numbers[number]], music_address)
        placed[number] = music_address
    music_end = max(placed[number] + len(sequences[number]) for number in placed)

    # --- the stage themes of Vampire Hunter 2, slow and heavier, for the endings of the three
    # characters that have none (stage_music.py). Bank 12 reads `1f nn` as Vampire Hunter 2's
    # bank nn (what is left of it is after the sequences copied above); a sequence that goes
    # in the banks after it names its banks 8 to 15 itself.
    theme_taken = set(copied) | {number + SOUND_ENTRY_OFFSET for number in new_numbers.values()}
    theme_numbers = dict(zip(stage_music.THEMES, free_sequence_numbers(savior, len(stage_music.THEMES), theme_taken)))
    hunter_themes = {}
    for character, number in stage_music.THEMES.items():
        theme = remix_theme(hunter, sequence_data(hunter, hunter_places, number + SOUND_ENTRY_OFFSET))
        hunter_themes[character] = theme
    bank12_free = [place, ENDING_MUSIC_START]
    theme_places = {}
    for character, theme in sorted(hunter_themes.items(), key=lambda item: -len(item[1])):
        if bank12_free[0] + len(theme) <= bank12_free[1]:
            theme_address = bank12_free[0]
            bank12_free[0] += len(theme)
        else:
            theme = stage_music.with_banks_added(theme, ADDED_BANKS_FIRST)
            theme_address = next((gap[0] for gap in free if gap[1] - gap[0] >= len(theme)), None)
            if theme_address is None or take(theme_address, len(theme)) is None:
                raise SystemExit('sound: no room for the stage themes')
        sound[theme_address:theme_address + len(theme)] = theme
        struct.pack_into('>I', sound, SEQUENCE_TABLE + 4 * (theme_numbers[character] + SOUND_ENTRY_OFFSET), theme_address)
        theme_places[character] = (theme_address, len(theme))

    print('sound: %d samples (%d Vampire Savior 2), %d sets of envelopes, tables to 0x%x, %d sequences copied '
          '(0x%x-0x%x), %d of the endings (0x%x-0x%x), 3 stage themes %s (%d bytes free)'
          % (len(table.entries), savior_sample_count, used_envelope_sets, address, len(copied),
             COPIED_SEQUENCES_START, place, len(ending_music), ENDING_MUSIC_START, music_end,
             ', '.join('%s 0x%x-0x%x' % (name, start, start + length) for name, (start, length) in theme_places.items()),
             sum(gap[1] - gap[0] for gap in free) + bank12_free[1] - bank12_free[0]))
    return bytes(sound), new_numbers, theme_numbers
