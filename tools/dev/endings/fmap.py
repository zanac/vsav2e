"""Maps code addresses of vsav (decrypted) to vsav2 by matching normalised instruction windows."""
import sys, re, pickle, os
sys.path.insert(0, '/home/claude/vsav2e/tools')
from cps2 import program
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
CODE_END = 0x100000
ABS = re.compile(r'\$[0-9a-f]{4,}')
def norm(ins):
    s = ins.op_str
    if ins.mnemonic in ('bra', 'bsr', 'jmp', 'jsr') or ins.mnemonic.startswith('b') or ins.mnemonic.startswith('db') or '(pc' in s:
        s = ABS.sub('A', s)           # targets differ between the games
    else:
        s = re.sub(r'#\$([0-9a-f]{5,})', '#A', s)
        s = re.sub(r'\$([0-9a-f]{5,})\.l', 'A', s)
    return ins.mnemonic + ' ' + s
def listing(game):
    cache = '/tmp/claude-0/vs/end/%s.lst' % game
    if os.path.exists(cache): return pickle.load(open(cache, 'rb'))
    p = program.load_program(game, '/tmp/claude-0/vs/t')
    out = []; a = 0
    while a < CODE_END:
        n = a
        for ins in md.disasm(p[a:CODE_END], a):
            out.append((ins.address, norm(ins), ins.size)); n = ins.address + ins.size
        a = n + 2 if n > a else a + 2
    pickle.dump(out, open(cache, 'wb')); return out
W = 12
def windows(lst):
    idx = {}
    for i in range(len(lst) - W):
        key = '|'.join(x[1] for x in lst[i:i + W])
        idx.setdefault(key, []).append(lst[i][0])
    return idx
if __name__ == '__main__':
    a = listing('vsavd'); b = listing('vsav2d')
    print(len(a), len(b))
