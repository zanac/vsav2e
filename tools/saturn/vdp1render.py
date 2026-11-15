"""Draws the sprite layer of a VDP1 VRAM dump of the Saturn Vampire Savior (what satrun's VDUMPS
writes) as a picture, to check the textures and the palettes of the endings.

    vdp1render.py vdp1vram.bin vdp2cram.bin output.ppm [width height]

Only what the endings use: normal sprites in 16-colour banks (4 bits a pixel, 0 is transparent)
and 8-bit banks, with the horizontal and vertical flips, the local coordinates, and the polygons
as flat black. VDP2 (the background) is not drawn, the picture is black where nothing is.
"""
import struct
import sys


def rgb555(word):
    """a CRAM word (bit 0-4 red, 5-9 green, 10-14 blue) as 8-bit red, green, blue"""
    r, g, b = word & 31, (word >> 5) & 31, (word >> 10) & 31
    return (r << 3 | r >> 2, g << 3 | g >> 2, b << 3 | b >> 2)


def render(vram, cram, width=352, height=240):
    """returns the picture as a list of rows of (r, g, b) or None (nothing drawn)"""
    picture = [[None] * width for _ in range(height)]
    palette = [rgb555(w) for w in struct.unpack('>%dH' % (len(cram) // 2), cram)]
    local_x = local_y = 0
    for entry in range(0, 0x80000 // 32):
        ctrl, link, pmod, colr, srca, size, xa, ya = struct.unpack_from('>HHHHHHhh', vram, entry * 32)
        if ctrl & 0x8000:                        # end of the list
            break
        command = ctrl & 15
        if command == 10:                        # local coordinates
            local_x, local_y = xa, ya
        elif command == 4:                       # polygon: the flat black background
            for y in range(height):
                picture[y] = [(0, 0, 0)] * width
        elif command == 0:                       # normal sprite
            w, h = ((size >> 8) & 0x3f) * 8, size & 0xff
            mode = (pmod >> 3) & 7
            base = srca * 8
            for row in range(h):
                for col in range(w):
                    if mode == 0:                # 16 colours of a bank
                        byte = vram[base + (row * w + col) // 2]
                        pixel = byte >> 4 if col % 2 == 0 else byte & 15
                        index = (colr & 0x07f0) | pixel
                    else:                        # 256 colours
                        pixel = vram[base + row * w + col]
                        index = (colr & 0x0700) | pixel
                    if pixel == 0 and not pmod & 0x40:
                        continue
                    sx = col if not ctrl & 0x10 else w - 1 - col
                    sy = row if not ctrl & 0x20 else h - 1 - row
                    x, y = local_x + xa + sx, local_y + ya + sy
                    if 0 <= x < width and 0 <= y < height:
                        picture[y][x] = palette[index]
    return picture


def write_ppm(picture, path):
    with open(path, 'wb') as f:
        f.write(b'P6\n%d %d\n255\n' % (len(picture[0]), len(picture)))
        for row in picture:
            f.write(bytes(c for p in row for c in (p or (0, 0, 0))))


def main():
    vram, cram = open(sys.argv[1], 'rb').read(), open(sys.argv[2], 'rb').read()
    size = [int(a) for a in sys.argv[4:6]] or [352, 240]
    write_ppm(render(vram, cram, *size), sys.argv[3])


if __name__ == '__main__':
    main()
