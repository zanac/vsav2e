"""Plays the Sega Saturn Vampire Savior (Japan) in arcade mode with a cheat and captures the
endings of Donovan, Huitzil and Pyron, the three characters that only the home versions have.

    capture_endings.py satrun core.so disc.cue system_directory output_directory [name ...]

satrun is tools/saturn/satrun.c, core.so is Beetle Saturn (see docs/saturn.md), the system
directory holds the Japanese BIOS as sega_101.bin. The pictures are written as
output_directory/<name>/fNNNNNN.ppm (352 x 240, one every 20 frames of the ending, from
the first frame of the fight that decides it).

The session is deterministic, so a second run gives the same pictures. How it gets there:

 * boot: START at the title (frames 3400-4000), then the cross button on the character
   select, with the character id poked into the cursor (the id is also kept in 8 copies,
   see CURSOR_COPIES) from frame 4400 to 4480, so that the game takes it for the choice;
 * the fights: the vitality of player 2 (RAM 0x19446c, and 0x19446e for the bar) is kept
   at 0, so that the first blow wins a round;
 * the last fight (against Jedah) is the one a poor fighter can lose, so for Huitzil and
   Pyron the game is saved at its start and played again with random attacks (seed 1)
   until it is won. Donovan wins it in the first pass.
"""
import os
import random
import subprocess
import sys

CHARACTERS = {'donovan': 0x13, 'huitzil': 0x10, 'pyron': 0x11}

# RAM offsets (work RAM, low RAM first) of the copies of the character under the cursor
CURSOR_COPIES = [0x194126, 0x1943b7, 0x199493, 0x199537, 0x1995db, 0x1996bc, 0x19b7cf, 0x19b873]
# vitality of player 2 (the right-hand fighter) and its copy that the bar shows
P2_VITALITY = [0x19446c, 0x19446e]
# vitality of player 1 and its copy that the bar shows (full at 0xdc for Donovan); not used
# by the captures, it is how to make player 1 unbeatable
P1_VITALITY = [0x194184, 0x194186]

FIGHT_START = 5800                      # first frame at which the first fight is under way
LAST_FIGHT_STATE = 14100                # frame of the saved state before the fight against Jedah
DONOVAN_STATE = 14000                   # the same for Donovan, who wins it at once
FIRST_PICTURE, PICTURE_STEP = 1200, 20  # of the second pass (the ending of Huitzil and Pyron)


def run(satrun, core, disc, system, directory, frames, press, pokes, shots='', state_load=None,
        state_save=None):
    """one session of satrun"""
    os.makedirs(directory, exist_ok=True)
    env = dict(os.environ, SYSDIR=system, PRESS=press, POKES=pokes, SHOTS=shots)
    if state_load:
        env['STATE_LOAD'] = state_load
    if state_save:
        env['STATE_SAVE'] = state_save
    subprocess.run([satrun, core, disc, str(frames), directory], env=env, check=True)


def menu_presses():
    """START through the title and the cross button on the three screens of the character select"""
    presses = ['%d:start' % frame for frame in range(3400, 4001, 240)]
    return presses + ['4500:b', '4900:b', '5300:b']


def fight_presses(last, step=24):
    """the attacks of the first pass: punch, button, forward"""
    presses = []
    for frame in range(FIGHT_START, last + 1, step):
        presses += ['%d:y' % frame, '%d:b' % (frame + 8), '%d:right' % (frame + 14)]
    return presses


def fight_presses_varied(last):
    """the attacks of the pass that is saved for Huitzil and Pyron (a pattern of 5 blows)"""
    presses = []
    for frame in range(FIGHT_START, last + 1, 40):
        presses += ['%d:y' % frame, '%d:b' % (frame + 6), '%d:x' % (frame + 12),
                    '%d:a' % (frame + 18), '%d:right:14' % (frame + 24)]
    return presses


def retry_presses(seed, frames):
    """random attacks for the second pass of the last fight, as a list of PRESS events"""
    generator = random.Random(seed)
    buttons = ['y', 'b', 'x', 'a', 'l', 'r']
    presses, frame = [], 30
    while frame < frames:
        if generator.random() < .6:
            presses.append('%d:right:%d' % (frame, generator.randint(8, 30)))
        else:
            presses.append('%d:left:%d' % (frame, generator.randint(4, 12)))
        for _ in range(generator.randint(1, 3)):
            presses.append('%d:%s:4' % (frame + generator.randint(0, 20), generator.choice(buttons)))
        if generator.random() < .15:
            presses.append('%d:up:4' % (frame + 5))
        frame += generator.randint(25, 45)
    return presses


def poke(addresses, value, first, last):
    return ['%d-%d:%x:%02x' % (first, last, address, value) for address in addresses]


def cursor_pokes(character):
    return poke(CURSOR_COPIES, character, 4400, 4480)


def main():
    satrun, core, disc, system, output = sys.argv[1:6]
    names = sys.argv[6:] or list(CHARACTERS)
    for name in names:
        character = CHARACTERS[name]
        out = os.path.join(output, name)
        state = os.path.join(out, 'before_jedah.state')
        if name == 'donovan':
            # one pass: the state is saved a little before the ending, which is then played
            last = DONOVAN_STATE + 1
            press = menu_presses() + fight_presses(last)
            pokes = cursor_pokes(character) + poke(P2_VITALITY, 0, 5700, last)
            run(satrun, core, disc, system, out, last, ';'.join(press), ';'.join(pokes),
                state_save='%d:%s' % (DONOVAN_STATE, state))
            frames = 1800
            run(satrun, core, disc, system, out, frames + 1, '', '',
                shots=' '.join(str(f) for f in range(300, frames + 1, 20)), state_load=state)
        else:
            # first pass: the game up to the fight against Jedah
            last = LAST_FIGHT_STATE + 1
            press = menu_presses() + fight_presses_varied(last)
            pokes = cursor_pokes(character) + poke(P2_VITALITY, 0, 5700, last)
            run(satrun, core, disc, system, out, last, ';'.join(press), ';'.join(pokes),
                state_save='%d:%s' % (LAST_FIGHT_STATE, state))
            # second pass: that fight again, with random attacks, and the ending
            frames = 5000
            run(satrun, core, disc, system, out, frames + 1, ';'.join(retry_presses(1, frames)),
                ';'.join(poke(P2_VITALITY, 0, 0, frames)),
                shots=' '.join(str(f) for f in range(FIRST_PICTURE, frames + 1, PICTURE_STEP)),
                state_load=state)
        os.remove(state)


if __name__ == '__main__':
    main()
