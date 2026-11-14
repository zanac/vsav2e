"""Decoder of the sprite texture compression of the Sega Saturn Vampire Savior (Japan).

    vdp1lz.py file offset width [output]

decodes the chunk that starts at `offset` of `file` (an ENDATxx.DAT, for instance) and writes the
texture to `output` (or prints its size). `width` is the number of bytes of a row of the texture,
which the chunk does not hold: it only matters for the copies from the row above.

The format was read from the game's own code (routine at 0x0601606e, the command interpreter at
0x06017268, see docs/saturn.md) and checked against the VDP1 VRAM of the running game: the output
is identical to the texture, apart from 2-4 bytes of padding that the last command can leave after
the end of the texture (the real size is width * height of the sprite).

Format. Everything is big-endian and made of 16-bit words:

    word 0   header; the top nibble is not 0 for a compressed chunk (0 = stored as it is, the
             4 bytes of header being followed by the data)
    word 1   offset, from the end of this word, of the stream of words; bit 0 set = empty chunk
    bytes    the command stream (from the end of word 1 to the start of the word stream)
    words    the word stream (the literals)

Each command byte `c` produces words of the output:

    00-0f     c+1 words taken from the word stream
    10-bf     one word that is a repeat of an earlier word of the word stream: the one that is
              (c - 0x0f) words behind the last one taken
    c0-cf     the previous word of the output, c-0xc0+1 times
    d0-df     (c & 15) + 1 words copied from the output, starting `width` bytes behind
              (the row above)
    e0-ef     the same, starting `width + 2` bytes behind (the row above, one word to the left)
    f0-ff     the same, starting `width - 2` bytes behind (the row above, one word to the right)
"""
import struct
import sys


def decode(src, pos, width, limit=1 << 20):
    """returns the decoded bytes of the chunk at src[pos:], or None if there is nothing to decode"""
    head, skip = struct.unpack_from('>HH', src, pos)
    if head >> 12 == 0 or skip & 1:
        return None
    commands = pos + 4
    words = commands + skip           # the literals start where the commands end
    data = words
    out = bytearray()
    row = {0xd: width, 0xe: width + 2, 0xf: width - 2}
    while commands < words and len(out) < limit:
        c = src[commands]
        commands += 1
        if c <= 0x0f:                                   # literal words
            count = c + 1
            out += src[data:data + 2 * count]
            data += 2 * count
        elif c <= 0xbf:                                 # an earlier literal again
            back = 2 * (c - 0x0f)
            out += src[data - back:data - back + 2]
        elif c <= 0xcf:                                 # the last word of the output, repeated
            out += bytes(out[-2:]) * (c - 0xc0 + 1)
        else:                                           # words of the output at a row distance
            for _ in range((c & 15) + 1):
                start = len(out) - row[c >> 4]
                out += out[start:start + 2] if start >= 0 else b'\0\0'
    return bytes(out)


def main():
    path, offset, width = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 0)
    texture = decode(open(path, 'rb').read(), offset, width)
    if texture is None:
        sys.exit('nothing to decode at that offset')
    if len(sys.argv) > 4:
        open(sys.argv[4], 'wb').write(texture)
    print('%d bytes' % len(texture))


if __name__ == '__main__':
    main()
