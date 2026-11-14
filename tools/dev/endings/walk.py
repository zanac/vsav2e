"""Walks the ending picture data of vsav: table 0x28e0cc -> lists -> steps -> frames."""
import sys, struct
sys.path.insert(0, '/home/claude/vsav2e/tools')
from cps2 import program
p = program.load_program('vsavd', '/tmp/claude-0/vs/t')
w = lambda a: struct.unpack('>H', p[a:a + 2])[0]
l = lambda a: struct.unpack('>I', p[a:a + 4])[0]
TABLE = 0x28e0cc
def lists():
    out = {}
    for c in range(16):
        base = TABLE + w(TABLE + 2 * c)
        offs = []
        while w(base + 2 * len(offs)): offs.append(w(base + 2 * len(offs)))
        out[c] = (base, [base + o for o in offs])
    return out
def steps(a):
    """yields step addresses of one animation (8-byte steps)"""
    seen = set()
    while a not in seen:
        seen.add(a); yield a
        f = p[a + 1]
        if f & 0x80: a = l(a + 8)
        elif f & 0x40: return
        else: a += 8
if __name__ == '__main__':
    frames = set(); stepset = set()
    for c, (base, ls) in lists().items():
        n = 0
        for s in ls:
            for st in steps(s):
                stepset.add(st); frames.add(l(st + 4)); n += 1
        print('%x list %06x anims %d steps %d' % (c, base, len(ls), n))
    print('steps %06x-%06x' % (min(stepset), max(stepset)), 'frames', len(frames), '%06x-%06x' % (min(frames), max(frames)))
    types = {}
    for f in frames: types.setdefault(w(f), []).append(f)
    print({t: len(v) for t, v in types.items()})
