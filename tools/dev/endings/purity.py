"""data references of a vsav routine: its own instructions, local branches and bsr, no tables, no jsr"""
import sys; sys.path.insert(0,'/tmp/claude-0/vs/end')
import xlink
from xlink import decode, branch_target
def refs(t, limit=0x1000):
    seen = {}; todo = [t]; out = set()
    while todo:
        a = todo.pop()
        while a not in seen and t - limit <= a < t + limit:
            ins = decode(a)
            if ins is None: break
            seen[a] = ins
            m = ins.mnemonic.split('.')[0]
            for op in ins.operands:
                if op.address_mode == 17 or (op.address_mode == 18 and ins.mnemonic.startswith(('lea', 'movea', 'pea', 'adda'))):
                    v = op.imm & 0xffffffff
                    if 0x100000 <= v < 0x400000: out.add((a, v))
            if m in ('bra', 'bsr', 'bhi', 'bls', 'bcc', 'bcs', 'bne', 'beq', 'bvc', 'bvs', 'bpl', 'bmi', 'bge', 'blt', 'bgt', 'ble') or m.startswith('db'):
                tt = branch_target(ins)
                if tt is not None: todo.append(tt)
            if m in ('rts', 'rte', 'jmp', 'bra'): break
            a += ins.size
    return seen, out
if __name__ == '__main__':
    for x in sys.argv[1:]:
        s, o = refs(int(x, 16))
        print(x, len(s), sorted(('%x:%x' % p) for p in o)[:10])
