"""A small PNG reader (standard library only): 8-bit RGB, RGBA and palette images, not
interlaced. Enough for the screen captures the build reads."""
import struct
import zlib

SIGNATURE = b'\x89PNG\r\n\x1a\n'
COLOUR_TYPE_RGB = 2
COLOUR_TYPE_PALETTE = 3
COLOUR_TYPE_RGBA = 6
BYTES_PER_PIXEL = {COLOUR_TYPE_RGB: 3, COLOUR_TYPE_PALETTE: 1, COLOUR_TYPE_RGBA: 4}


def paeth(left, up, up_left):
    estimate = left + up - up_left
    distance_left, distance_up, distance_up_left = abs(estimate - left), abs(estimate - up), abs(estimate - up_left)
    if distance_left <= distance_up and distance_left <= distance_up_left:
        return left
    return up if distance_up <= distance_up_left else up_left


def read(path):
    """(width, height, rows): each row a list of (red, green, blue). path: a file, or the
    bytes of one"""
    data = path if isinstance(path, bytes) else open(path, 'rb').read()
    if data[:8] != SIGNATURE:
        raise ValueError('%s is not a PNG file' % path)
    position = 8
    compressed = b''
    palette = None
    while position < len(data):
        length, kind = struct.unpack_from('>I4s', data, position)
        body = data[position + 8:position + 8 + length]
        position += 12 + length
        if kind == b'IHDR':
            width, height, depth, colour_type, _, _, interlace = struct.unpack('>IIBBBBB', body)
            if depth != 8 or colour_type not in BYTES_PER_PIXEL or interlace:
                raise ValueError('%s: PNG format not supported' % path)
        elif kind == b'PLTE':
            palette = [tuple(body[index:index + 3]) for index in range(0, len(body), 3)]
        elif kind == b'IDAT':
            compressed += body
    pixel_bytes = BYTES_PER_PIXEL[colour_type]
    line_bytes = width * pixel_bytes
    raw = zlib.decompress(compressed)
    rows = []
    previous = bytearray(line_bytes)
    for y in range(height):
        start = y * (line_bytes + 1)
        filter_type = raw[start]
        line = bytearray(raw[start + 1:start + 1 + line_bytes])
        for x in range(line_bytes):
            left = line[x - pixel_bytes] if x >= pixel_bytes else 0
            up = previous[x]
            up_left = previous[x - pixel_bytes] if x >= pixel_bytes else 0
            if filter_type == 1:
                line[x] = (line[x] + left) & 0xff
            elif filter_type == 2:
                line[x] = (line[x] + up) & 0xff
            elif filter_type == 3:
                line[x] = (line[x] + (left + up) // 2) & 0xff
            elif filter_type == 4:
                line[x] = (line[x] + paeth(left, up, up_left)) & 0xff
        previous = line
        if colour_type == COLOUR_TYPE_PALETTE:
            rows.append([palette[index] for index in line])
        else:
            rows.append([tuple(line[x:x + 3]) for x in range(0, line_bytes, pixel_bytes)])
    return width, height, rows
