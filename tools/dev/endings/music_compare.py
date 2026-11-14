"""Compares the music of the endings of vsav2e with Vampire Savior's, from two recordings
of tools/dev/libretro_run.c (AUDIO: 16-bit stereo at 48 kHz) and their WATCH logs of the
sound requests (WATCH=618001,618003: the number the 68000 writes to the QSound shared RAM).

    music_compare.py VSAV_RAW VSAV_WATCH VSAV2E_RAW VSAV2E_WATCH

For each piece of ending music (Vampire Savior's numbers 0x25-0x44 and vsav2e's 0x50-0x6b,
in the order they are asked for), the two recordings are cut from the frame of the request
and compared every 3 seconds: the correlation of their spectra (32 bands, log), 1.0 for the
same sound. Needs numpy.
"""
import sys

import numpy

RATE = 48000
FRAMES_PER_SECOND = 59.637
HOP = 1024
SAVIOR_MUSIC = range(0x25, 0x45)
VSAV2E_MUSIC = range(0x50, 0x6c)


def features(raw_path):
    sound = numpy.fromfile(raw_path, dtype=numpy.int16).reshape(-1, 2).astype(float).mean(1)
    size = 2048
    windows = numpy.lib.stride_tricks.sliding_window_view(sound, size)[::HOP] * numpy.hanning(size)
    spectra = numpy.abs(numpy.fft.rfft(windows, axis=1))
    edges = numpy.geomspace(2, size // 2, 33).astype(int)
    return numpy.log1p(numpy.stack([spectra[:, edges[k]:edges[k + 1] + 1].sum(1) for k in range(32)], 1))


def requests(watch_path, numbers):
    """[(frame, number)] of the requests of ending music"""
    found = []
    for line in open(watch_path):
        _, frame, high, low = line.split()
        number = int(high, 16) << 8 | int(low, 16)
        if number in numbers:
            found.append((int(frame.rstrip(':')), number))
    return found


def compare(savior, vsav2e, savior_frame, vsav2e_frame, seconds):
    steps = HOP / RATE
    length = int(3 / steps)
    scores = []
    for start in numpy.arange(0, seconds, 3):
        a = int((savior_frame / FRAMES_PER_SECOND + start) / steps)
        b = int((vsav2e_frame / FRAMES_PER_SECOND + start) / steps)
        x, y = savior[a:a + length], vsav2e[b:b + length]
        if len(x) < length or len(y) < length:
            break
        x = (x - x.mean()) / x.std()
        y = (y - y.mean()) / y.std()
        scores.append((x * y).mean())
    return scores


def main():
    savior_raw, savior_watch, vsav2e_raw, vsav2e_watch = sys.argv[1:5]
    savior, vsav2e = features(savior_raw), features(vsav2e_raw)
    savior_requests = requests(savior_watch, SAVIOR_MUSIC)
    vsav2e_requests = requests(vsav2e_watch, VSAV2E_MUSIC)
    for index, ((frame1, number1), (frame2, number2)) in enumerate(zip(savior_requests, vsav2e_requests)):
        # a piece lasts until the next request (or 20 seconds for the last one)
        if index + 1 < len(savior_requests):
            seconds = (savior_requests[index + 1][0] - frame1) / FRAMES_PER_SECOND - 1
        else:
            seconds = 20
        scores = compare(savior, vsav2e, frame1, frame2, seconds)
        print('0x%02x / 0x%02x: %s' % (number1, number2, ' '.join('%.2f' % score for score in scores)))


if __name__ == '__main__':
    main()
