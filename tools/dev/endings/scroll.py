"""Scroll tiles of the ending maps (from the tap reads) and whether vsav2 has them."""
import pickle, struct, sys, numpy as np, collections
sys.path.insert(0, '/home/claude/vsav2e/tools')
from cps2 import program
p = program.load_program('vsavd', '/tmp/claude-0/vs/t')
r = pickle.load(open('reads.pkl', 'rb'))
W = lambda a: struct.unpack('>H', p[a:a+2])[0]
vs = np.load('/tmp/claude-0/vs/vsav_gfx.npy', mmap_mode='r')
v2 = np.load('/tmp/claude-0/vs/vsav2_gfx_u.npy', mmap_mode='r')
def blocks(arr, size):
    a = arr.reshape(-1, size)
    return {a[i].tobytes(): i for i in range(len(a) - 1, -1, -1)}
# loader: (pc reading block entries, entry stride words per tile pair, offset added, layer size)
used = collections.defaultdict(set)
# 1f458: blocks at 376424, entries (code, attr) pairs read at 1f494/1f4a4 (movem d0-d3)
for pc, off, size in ((0x1f494, 0x3800, 128), (0x1f4a4, 0x3800, 128)):
    for a in r.get(pc, ()):
        if (a - 0x376424) % 8 == 0: used[size].add(W(a) + off)
for pc in (0x1f06e, 0x1f07e, 0x1f090, 0x1f0a2, 0x1f0b4, 0x1f0c6, 0x1f0d8, 0x1f0ea):
    for a in r.get(pc, ()):
        if (a - 0x35c824) % 4 == 0: used['s3'].add(W(a))
for a in r.get(0x1f868, ()):
    if (a - 0x384aa4) % 4 == 0: used['s1'].add(W(a) + 0x600)
print({k: len(v) for k, v in used.items()})
for key, size in ((128, 128), ('s3', 512), ('s1', 64)):
    codes = used[key]
    b2 = blocks(v2, size)
    found = 0; blank = 0; miss = []
    for c in codes:
        t = vs[c * size:(c + 1) * size].tobytes()
        if set(t) == {0xff}: blank += 1
        elif t in b2: found += 1
        else: miss.append(c)
    print(key, 'codes', len(codes), 'blank', blank, 'in vsav2', found, 'missing', len(miss))
# per ending and alignment check for scroll3
codes = used['s3']
a2 = v2.reshape(-1, 128)
idx = {a2[i].tobytes(): [] for i in range(0)}
from collections import defaultdict
first = defaultdict(list)
for i in range(len(a2)): first[a2[i].tobytes()].append(i)
ok = 0
for c in codes:
    t = vs[c*512:(c+1)*512].tobytes()
    cands = first.get(t[:128], [])
    if any(v2[i*128:i*128+512].tobytes() == t for i in cands): ok += 1
print('scroll3 tiles found at any 128-byte position', ok, 'of', len(codes))
