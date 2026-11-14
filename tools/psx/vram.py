"""Viewing a PlayStation VRAM dump (1024 x 512 16-bit words, from psxrun VDUMPS).

The VRAM holds the frame buffers and the textures. Textures are 4 or 8 bits per pixel,
packed in the 16-bit words, and use a palette (CLUT) of 16 or 256 colours that is itself
a row of 16-bit colours somewhere in VRAM.
"""
import numpy as np

VRAM_WIDTH, VRAM_HEIGHT = 1024, 512


def load(path):
    return np.frombuffer(open(path, 'rb').read(), '<u2').reshape(VRAM_HEIGHT, VRAM_WIDTH)


def colours_to_rgb(words):
    """15-bit BGR words -> an RGB array (colour 0 shown as black)"""
    red = (words & 0x1f) << 3
    green = ((words >> 5) & 0x1f) << 3
    blue = ((words >> 10) & 0x1f) << 3
    return np.stack([red, green, blue], axis=-1).astype(np.uint8)


def as_direct_colour(vram):
    """the whole VRAM read as 15-bit colours: frame buffers look right, textures do not"""
    return colours_to_rgb(vram)


def texture_indexes(vram, x_words, y, width_words, height, bits_per_pixel):
    """the palette indexes of a texture rectangle (x and width in 16-bit words)"""
    words = vram[y:y + height, x_words:x_words + width_words]
    if bits_per_pixel == 4:
        nibbles = [(words >> shift) & 15 for shift in (0, 4, 8, 12)]
        return np.stack(nibbles, axis=-1).reshape(height, width_words * 4)
    bytes_ = [(words & 0xff), (words >> 8)]
    return np.stack(bytes_, axis=-1).reshape(height, width_words * 2)


def palette_at(vram, x, y, colours):
    """a CLUT: `colours` 16-bit colours starting at (x, y)"""
    return vram[y, x:x + colours]
