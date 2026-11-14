"""External references of a vsav code range, and their vsav2 matches."""
import sys, re
sys.path.insert(0, '/tmp/claude-0/vs/end')
from fmap import listing, windows, W
A = listing('vsavd'); B = listing('vsav2d')
pos = {a: i for i, (a, _, _) in enumerate(A)}
bidx = windows(B)
import pickle
sys.path.insert(0, '/home/claude/vsav2e/tools')
from cps2 import program
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
p = program.load_program('vsavd', '/tmp/claude-0/vs/t')
def match(addr, w=W):
    i = pos.get(addr)
    if i is None: return None
    for ww in (W,):
        key = '|'.join(x[1] for x in A[i:i + ww])
        r = bidx.get(key)
        if r: return r
    return []
def dis(start, end):
    a = start
    while a < end:
        n = a
        for ins in md.disasm(p[a:end], a):
            yield ins; n = ins.address + ins.size
        a = n + 2 if n > a else a + 2
def refs(start, end):
    out = {}
    for ins in dis(start, end):
        for m in re.finditer(r'\$([0-9a-f]+)', ins.op_str):
            v = int(m.group(1), 16)
            if (v >= 0x400 and not (start <= v < end) and ('.l' in ins.op_str or '#$' in ins.op_str or ins.mnemonic in ('jsr','jmp','bsr','bra'))
                    and v < 0x900000):
                out.setdefault(v, []).append(ins.address)
    return out
if __name__ == '__main__':
    s, e = int(sys.argv[1], 16), int(sys.argv[2], 16)
    r = refs(s, e)
    for v in sorted(r):
        m = match(v) if v < 0x100000 else None
        print('%06x  uses %3d  vsav2 %s' % (v, len(r[v]), m if m is None else ' '.join('%06x' % x for x in m[:3])))
_idx = {}
def match_flex(addr, sizes=(16, 12, 8, 6, 5, 4)):
    """vsav2 address of the vsav code at addr: the longest window with one match"""
    i = pos.get(addr)
    if i is None: return None
    for w in sizes:
        if w not in _idx:
            d = {}
            for j in range(len(B) - w):
                d.setdefault('|'.join(x[1] for x in B[j:j + w]), []).append(B[j][0])
            _idx[w] = d
        r = _idx[w].get('|'.join(x[1] for x in A[i:i + w]), [])
        if len(r) == 1: return r[0], w
        if r and w == sizes[-1]: return r, w
    return None
