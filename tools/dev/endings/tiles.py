# Count the sprite tiles of each Vampire Savior ending (mode ff8004=0a, sub ff8006=02)
import struct, sys, numpy as np, os
R = 8212
missing = np.load('/tmp/claude-0/vs/vsav_missing.npy')
gfx = np.load('/tmp/claude-0/vs/vsav_gfx.npy', mmap_mode='r').reshape(-1, 128)
def ending_tiles(path):
    d = open(path, 'rb').read(); tiles = set(); frames = 0
    for i in range(len(d) // R):
        r = d[i*R:(i+1)*R]
        mode, sub = struct.unpack('>HH', r[8:10] + r[12:14])[0], struct.unpack('>H', r[12:14])[0]
        mode = struct.unpack('>H', r[8:10])[0]
        if mode != 0x0a or sub != 0x02: continue
        frames += 1
        w = struct.unpack('>4096H', r[20:])
        for s in range(1024):
            x, y, code, attr = w[4*s:4*s+4]
            if attr & 0xff00 == 0xff00: break
            code += (y & 0x6000) << 3
            cols = ((attr >> 8) & 15) + 1; rows = ((attr >> 12) & 15) + 1
            for rr in range(rows):
                for cc in range(cols):
                    tiles.add((code & ~0xf) + ((code + cc) & 0xf) + rr * 16 & 0x3ffff)
    return frames, tiles
tot = set(); totm = set()
for idn in sys.argv[1:]:
    p = '/tmp/claude-0/vs/el_%s/objlog.bin' % idn
    if not os.path.exists(p): continue
    fr, t = ending_tiles(p)
    t = {c for c in t if gfx[c].min() != 0xff}  # skip fully transparent
    m = {c for c in t if missing[c]}
    tot |= t; totm |= m
    print(idn, 'frames', fr*4, 'tiles', len(t), 'missing', len(m), 'range %x-%x' % (min(m), max(m)) if m else '')
print('total', len(tot), 'missing', len(totm), 'bytes', len(totm) * 128)
