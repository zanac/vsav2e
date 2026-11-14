"""The program extension of vsav2e: ROM from 0x400000, past the 4 MB of a CPS2 program.

A frame (docs/roster.md) stored here is drawn from the upper sprite bank: the frame hook
of `roster.py` selects it by the address of the frame.
"""

EXTENSION_START = 0x400000
EXTENSION_SIZE = 0x80000


class Extension:
    """the program ROM from 0x400000, filled from its start"""

    def __init__(self):
        self.data = bytearray(b'\xff' * EXTENSION_SIZE)
        self.used = 0

    def add(self, block):
        """stores a block (word aligned) and returns its address"""
        if self.used + len(block) > EXTENSION_SIZE:
            raise SystemExit('roster: the program extension is full')
        address = EXTENSION_START + self.used
        self.data[self.used:self.used + len(block)] = block
        self.used += len(block) + (len(block) & 1)
        return address

    def end(self):
        return EXTENSION_START + self.used
