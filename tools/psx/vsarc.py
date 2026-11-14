"""VS.ARC, the main archive of the PlayStation Darkstalkers 3.

It starts with a table of 8-byte entries (first sector, sector count), sectors of 2048
bytes, ended by an entry whose first sector is 0xffffffff."""
import struct

SECTOR_SIZE = 2048
END_OF_TABLE = 0xffffffff


def read_entries(archive):
    """the archive's files, as a list of bytes objects"""
    entries = []
    position = 0
    while True:
        first_sector, sector_count = struct.unpack_from('<II', archive, position)
        if first_sector == END_OF_TABLE:
            return entries
        start = first_sector * SECTOR_SIZE
        entries.append(archive[start:start + sector_count * SECTOR_SIZE])
        position += 8
