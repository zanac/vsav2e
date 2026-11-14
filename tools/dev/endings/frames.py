import pickle, struct, sys, collections
sys.path.insert(0, '/home/claude/vsav2e/tools')
from cps2 import program
p = program.load_program('vsavd', '/tmp/claude-0/vs/t')
r = pickle.load(open('reads.pkl', 'rb'))
W = lambda a: struct.unpack('>H', p[a:a+2])[0]
L = lambda a: struct.unpack('>I', p[a:a+4])[0]
frames = sorted(r[0x1afae])
def tiles_of(f):
    t = W(f); out = []
    if t == 2:
        n = W(f + 4) + 1
        for k in range(n):
            tile, attr = struct.unpack('>HH', p[f + 10 + 4*k:f + 14 + 4*k])
            out.append((tile, attr))
    elif t == 0:
        n = W(f + 2); attr = W(f + 4)
        for k in range(n): out.append((W(f + 10 + 2*k), attr))
    return t, out
def expand(tile, attr):
    for rr in range(((attr >> 12) & 15) + 1):
        for cc in range(((attr >> 8) & 15) + 1):
            yield (tile & ~15) + ((tile + cc) & 15) + 16 * rr
if __name__ == '__main__':
    exec(open('tiles.py').read().split('tot = set()')[0])
    obs = set()
    for idn in '00 01 02 03 04 05 06 07 08 09 0a 0c 0d 0e 0f'.split():
        obs |= ending_tiles('/tmp/claude-0/vs/el_%s/objlog.bin' % idn)[1]
    types = collections.Counter(); banks = collections.Counter(); frame_bank = {}
    for f in frames:
        t, recs = tiles_of(f); types[t] += 1
        if not recs: continue
        words = {x for tile, attr in recs for x in expand(tile, attr)}
        fit = [b for b in range(4) if {(w + (b << 16)) & 0x3ffff for w in words if gfx[(w + (b << 16)) & 0x3ffff].min() != 0xff} <= obs]
        frame_bank[f] = fit; banks[tuple(fit)] += 1
    print(types); print(banks)
    pickle.dump(frame_bank, open('frame_bank.pkl', 'wb'))
