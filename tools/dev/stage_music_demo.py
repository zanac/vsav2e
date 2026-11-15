#!/usr/bin/env python3
"""stage_music_demo.py ROM_DIRECTORY CORE.so LIBRETRO_RUN OUTPUT_DIRECTORY

Records the stage themes of Huitzil, Pyron and Donovan (Vampire Hunter 2) three ways, with no
voices or effects, to listen to and compare: `1_original`, `2_slowed` (the tempo only) and
`3_slowed_remix` (what the endings play: tools/build/stage_music.py). Needs ffmpeg, the
libretro core (mame2003-plus) and `libretro_run` (tools/dev/libretro_run.c).

How: a copy of `vhunt2.zip` whose sound program has nothing but the three themes (every
other entry of the sequence table is cleared, so the voices and effects are silent), the
themes put where the other music was; a match against each character with the opponent
forced to the same one (the stage, and so its theme, is the opponent's), recorded from the
start of the stage. The numbers of the themes (0x19, 0x1a, 0x1c) are the ones the 68000
sends when those stages start.
"""
import os
import struct
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from build import sound, stage_music

CHARACTERS = {'huitzil': 0x10, 'pyron': 0x11, 'donovan': 0x13}
FRAMES = 7500                    # 125 s at 60 frames a second
SAMPLE_RATE = 48000
SECONDS = 90


def build_zip(rom_directory, path, mode):
    """vhunt2.zip with only the stage themes, original, slowed or remixed"""
    source = os.path.join(rom_directory, 'vhunt2.zip')
    with zipfile.ZipFile(source) as archive:
        halves = archive.read('vh2.01'), archive.read('vh2.02')
    program = bytearray(halves[0] + halves[1])
    original = bytes(program)
    places = sound.sequence_places(original)
    # the music of the other stages is not played here: its place is free for the themes
    place = places[11]
    for number in stage_music.THEMES.values():
        entry = number + sound.SOUND_ENTRY_OFFSET
        theme = sound.sequence_data(original, places, entry)
        if mode == 'slowed':
            theme = stage_music.slowed(theme)
        elif mode == 'remix':
            theme = sound_remix(original, theme)
        program[place:place + len(theme)] = theme
        struct.pack_into('>I', program, sound.SEQUENCE_TABLE + 4 * entry, place)
        place += len(theme) + 16
    keep = {number + sound.SOUND_ENTRY_OFFSET for number in stage_music.THEMES.values()}
    for entry in range(1, (sound.SEQUENCE_TABLE_END - sound.SEQUENCE_TABLE) // 4):
        if entry not in keep:
            struct.pack_into('>I', program, sound.SEQUENCE_TABLE + 4 * entry, 0)
    with zipfile.ZipFile(source) as archive, zipfile.ZipFile(path, 'w', zipfile.ZIP_STORED) as out:
        for info in archive.infolist():
            data = archive.read(info.filename)
            if info.filename == 'vh2.01':
                data = bytes(program[:len(halves[0])])
            elif info.filename == 'vh2.02':
                data = bytes(program[len(halves[0]):])
            out.writestr(info.filename, data)


def sound_remix(original, theme):
    return sound.remix_theme(original, theme)


def record(core, runner, zip_path, character, raw_path):
    environment = dict(os.environ, AUDIO=raw_path, SYSTEM_DIR=os.path.dirname(raw_path),
                       POKES='1000-1700:ff8782:%x;1000-1700:ff8b82:%x' % ((CHARACTERS[character],) * 2),
                       PRESS='600:coin;700:start;1030:b1;1100:b1')
    subprocess.run([runner, core, zip_path, str(FRAMES)], env=environment, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def to_mp3(raw_path, mp3_path):
    """the music starts when the sound first rises above silence"""
    import numpy as np
    samples = np.fromfile(raw_path, dtype='<i2').reshape(-1, 2).astype(float).mean(1)
    envelope = np.abs(samples[:len(samples) // 4800 * 4800]).reshape(-1, 4800).mean(1)
    start = max(0.0, np.argmax(envelope > 200) / 10 - 0.2)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', str(SAMPLE_RATE), '-ac', '2',
                    '-ss', str(start), '-t', str(SECONDS), '-i', raw_path, '-codec:a', 'libmp3lame',
                    '-b:a', '128k', mp3_path], check=True)


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    rom_directory, core, runner, output = sys.argv[1:]
    os.makedirs(output, exist_ok=True)
    for label, mode in (('1_original', 'original'), ('2_slowed', 'slowed'), ('3_slowed_remix', 'remix')):
        work = os.path.join(output, mode)
        os.makedirs(work, exist_ok=True)
        zip_path = os.path.join(work, 'vhunt2.zip')
        build_zip(rom_directory, zip_path, mode)
        for character in CHARACTERS:
            raw = os.path.join(work, character + '.raw')
            record(core, os.path.abspath(runner), zip_path, character, raw)
            to_mp3(raw, os.path.join(output, '%s_%s.mp3' % (character, label)))
            os.remove(raw)


if __name__ == '__main__':
    main()
