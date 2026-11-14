"""Checks the vsav -> vsav2 address of every routine the moved code calls: the routines
must be the same instruction by instruction (immediates included; absolute addresses
and a5 offsets compared through the maps). Wrong ones are searched again."""
import re, sys, pickle, collections
sys.path.insert(0, '/tmp/claude-0/vs/end')
from fmap import listing
A = listing('vsavd'); B = listing('vsav2d')
ia = {a: i for i, (a, _, _) in enumerate(A)}
ib = {a: i for i, (a, _, _) in enumerate(B)}
ADDR = re.compile(r'\$[0-9a-f]{5,}')
A5 = re.compile(r'(-?)\$([0-9a-f]+)\(a5')
def strict(s, a5map=None):
    s = ADDR.sub('A', s)
    if a5map is not None:
        def f(m):
            d = int(m.group(2), 16) * (-1 if m.group(1) else 1)
            d = a5map.get(d, d)
            return ('-$%x' % -d if d < 0 else '$%x' % d) + '(a5'
        s = A5.sub(f, s)
    return s
def body(L, i, n=24):
    out = []
    for k in range(i, min(i + n, len(L))):
        out.append(L[k][1])
        if L[k][1].startswith(('rts', 'jmp', 'bra', 'rte')): break
    return out
_index = None
def index_b(n):
    global _index
    if _index is None:
        _index = collections.defaultdict(list)
        for j in range(len(B)):
            _index[tuple(strict(x) for x in body(B, j, 6))].append(B[j][0])
    return _index
def check(v, mapped, a5map):
    i = ia.get(v)
    if i is None: return None, 'not an instruction'
    ba = [strict(x, a5map) for x in body(A, i)]
    if mapped is not None and mapped in ib:
        bb = [strict(x) for x in body(B, ib[mapped])]
        if ba == bb: return mapped, 'ok'
    # search
    cands = index_b(6).get(tuple(strict(x, a5map) for x in body(A, i, 6)), [])
    good = [c for c in cands if [strict(x) for x in body(B, ib[c])] == ba]
    if len(good) == 1: return good[0], 'fixed'
    return None, 'ambiguous %d' % len(good) if good else 'not found'
