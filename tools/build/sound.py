"""The voices of Jon Talbain, Rikuo and Sasquatch.

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
    0x9001          the sequences: for each number, 4 bytes (high byte first) with the
                    place of the sequence in the two files read as one; 0 for none
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
- changes `1f nn` so that in a sequence of bank 12 or more it picks bank nn + 8: the
  copied sequences then play with the instruments they were written for.
"""
import struct

SOUND_PROGRAM_SIZE = 0x40000
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
    """the place of each sequence in the file, by number (0: none)"""
    places = [struct.unpack_from('>I', sound, address)[0]
              for address in range(SEQUENCE_TABLE, SEQUENCE_TABLE_END - 3, 4)]
    places[0] = 0       # the first entry is not a sequence
    return places


def sequence_data(sound, places, number):
    """The bytes of a sequence, or None: it runs to the next sequence in the file."""
    start = places[number]
    if not start:
        return None
    later = [place for place in places if place > start]
    end = min(later) if later else len(sound.rstrip(b'\x00')) + 1
    return bytes(sound[start:end])


def is_silent(sequence):
    return sequence[SEQUENCE_HEADER_SIZE:].replace(SILENT_TRACK, b'').strip(b'\x00') == b''


def table_end(sound, start, entry_size):
    """the end of a table followed by zeros"""
    used = len(bytes(sound[start:FIXED_AREA_END]).rstrip(b'\x00'))
    return start + (used + entry_size - 1) // entry_size * entry_size


def apply(savior, hunter):
    """Returns the sound program of vsav2e (256 KB) from the two games' (`.01` + `.02`)."""
    sound = bytearray(savior)

    # --- samples: Vampire Hunter 2's after Vampire Savior 2's
    savior_samples = read_word(savior, SAMPLE_TABLE_POINTER)
    if SAVIOR_ENVELOPES <= savior_samples or any(savior[SAVIOR_ENVELOPES + 0x248:FIXED_AREA_END]):
        raise SystemExit('sound: unexpected layout of the Vampire Savior 2 program')
    savior_sample_count = (SAVIOR_ENVELOPES - savior_samples) // SAMPLE_ENTRY_SIZE
    hunter_samples = read_word(hunter, SAMPLE_TABLE_POINTER)
    hunter_sample_count = (HUNTER_ENVELOPES - hunter_samples) // SAMPLE_ENTRY_SIZE
    added_samples = bytearray(hunter[hunter_samples:HUNTER_ENVELOPES])
    for entry in range(0, len(added_samples), SAMPLE_ENTRY_SIZE):
        added_samples[entry] |= SAMPLE_ROM_UPPER_HALF

    # --- envelopes: after the samples; Vampire Hunter 2's sets that are not there are added
    savior_envelopes_end = table_end(savior, SAVIOR_ENVELOPES, ENVELOPE_ENTRY_SIZE)
    envelopes = [bytes(savior[address:address + ENVELOPE_ENTRY_SIZE])
                 for address in range(SAVIOR_ENVELOPES, savior_envelopes_end, ENVELOPE_ENTRY_SIZE)]
    hunter_envelope_number = {}         # Vampire Hunter 2's set -> its number in vsav2e
    hunter_envelopes_end = table_end(hunter, HUNTER_ENVELOPES, ENVELOPE_ENTRY_SIZE)
    for number, address in enumerate(range(HUNTER_ENVELOPES, hunter_envelopes_end, ENVELOPE_ENTRY_SIZE)):
        envelope = bytes(hunter[address:address + ENVELOPE_ENTRY_SIZE])
        if envelope not in envelopes:
            envelopes.append(envelope)
        hunter_envelope_number[number] = envelopes.index(envelope)
    if len(envelopes) > MAXIMUM_ENVELOPE_SETS:
        raise SystemExit('sound: too many sets of envelopes')

    # --- instruments: Vampire Hunter 2's banks, with the numbers of the added samples and sets
    hunter_banks = [read_word(hunter, INSTRUMENT_BANK_POINTERS + 2 * bank) for bank in range(INSTRUMENT_BANKS)]
    hunter_bank_ends = hunter_banks[1:] + [hunter_samples]
    added_banks = []
    for start, end in zip(hunter_banks, hunter_bank_ends):
        bank = bytearray(hunter[start:end])
        for entry in range(0, len(bank), INSTRUMENT_ENTRY_SIZE):
            sample = read_word(bank, entry)
            struct.pack_into('<H', bank, entry, (sample & 0x8000) | ((sample & 0x7fff) + savior_sample_count))
            envelope = bank[entry + 3]
            # (an instrument that is not used may name a set that does not exist)
            bank[entry + 3] = (envelope & 0x80) | hunter_envelope_number.get(envelope & 0x7f, envelope & 0x7f)
        added_banks.append(bank)

    # --- the new layout of the end of the fixed area
    address = savior_samples + savior_sample_count * SAMPLE_ENTRY_SIZE
    sound[address:address + len(added_samples)] = added_samples
    address += len(added_samples)
    envelopes_address = address
    sound[address:address + ENVELOPE_ENTRY_SIZE * len(envelopes)] = b''.join(envelopes)
    address += ENVELOPE_ENTRY_SIZE * len(envelopes)
    bank_list_address = address
    address += 2 * (INSTRUMENT_BANKS + len(added_banks))
    bank_addresses = [read_word(savior, INSTRUMENT_BANK_POINTERS + 2 * bank) for bank in range(INSTRUMENT_BANKS)]
    for bank in added_banks:
        bank_addresses.append(address)
        sound[address:address + len(bank)] = bank
        address += len(bank)
    sound[bank_list_address:bank_list_address + 2 * len(bank_addresses)] = struct.pack(
        '<%dH' % len(bank_addresses), *bank_addresses)

    # `1f nn` in a copied sequence
    pick_bank_routine = bytes.fromhex(
        'dd7e01'        # ld   a, (ix+1)        the bank the track is read from
        'fe%02x'        # cp   COPIED_SEQUENCES_BANK
        '1a'            # ld   a, (de)          nn
        '13'            # inc  de
        '3802'          # jr   c, +2            not a copied sequence
        'c6%02x'        # add  a, ADDED_BANKS_FIRST
        '01%02x%02x'    # ld   bc, the list of banks
        'c9'            # ret
        % (COPIED_SEQUENCES_BANK, ADDED_BANKS_FIRST, bank_list_address & 0xff, bank_list_address >> 8))
    pick_bank_address = address
    address += len(pick_bank_routine)
    if address > FIXED_AREA_END:
        raise SystemExit('sound: the tables do not fit in the first 32 KB')
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

    # --- sequences
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
        if place + len(sequence) > SOUND_PROGRAM_SIZE:
            raise SystemExit('sound: no room for the sequences')
        sound[place:place + len(sequence)] = sequence
        struct.pack_into('>I', sound, SEQUENCE_TABLE + 4 * number, place)
        place += len(sequence)
        copied.append(number)

    print('sound: %d + %d samples, %d sets of envelopes, tables to 0x%x, %d sequences copied (0x%x-0x%x)'
          % (savior_sample_count, hunter_sample_count, len(envelopes), address, len(copied),
             COPIED_SEQUENCES_START, place))
    return bytes(sound)
