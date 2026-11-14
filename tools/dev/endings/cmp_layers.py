import struct, collections, sys
sys.path.insert(0, '/tmp/claude-0/vs/end')
import port
p = port.Port(); g = port.Graphics(p)
codes = g.scroll_codes() + [(2, None, 0x3811)]
new = {}
reserved = [(code * size, code * size + size) for code, size in port.BLANK_CODES]
pos = 0
for layer, size in ((3, 512), (2, 128), (1, 64)):
    for c in sorted({c for l, a, c in codes if l == layer}):
        while True:
            pos = (pos + size - 1) // size * size
            clash = [e for s, e in reserved if s < pos + size and pos < e]
            if not clash: break
            pos = max(clash)
        new[(layer, c)] = pos // size; pos += size
inv = {(l, n): c for (l, c), n in new.items()}
u = open(sys.argv[1], 'rb').read(); w = open(sys.argv[1].replace('gfxram', 'wram'), 'rb').read()
regs = struct.unpack('>4H', w[0x8018:0x8020])
for layer, reg in ((1, regs[0]), (2, regs[1]), (3, regs[2])):
    base = (reg << 8) - 0x900000
    t = struct.unpack('>8192H', u[base:base + 0x4000])
    c = collections.Counter(t[0::2])
    unknown = collections.Counter(x for x in t[0::2] if (layer, x) not in inv)
    print('layer', layer, 'base %06x' % (reg << 8), 'distinct', len(c), 'not ours', sum(unknown.values()), unknown.most_common(5))
