"""Recursive disassembler and relocator: moves 68000 code of vsav into vsav2e.

trace(entries, ranges): follows the code from the entry points, inside the given vsav
ranges only (calls outside are external references). Returns the instructions found
and the jump tables (word offsets) and long tables (code pointers) met on the way.
"""
import re, struct, sys, pickle, collections
sys.path.insert(0, '/home/claude/vsav2e/tools')
from cps2 import program
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000

md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
md.detail = True
P = program.load_program('vsavd', '/tmp/claude-0/vs/t')
W = lambda a: struct.unpack('>H', P[a:a + 2])[0]
L = lambda a: struct.unpack('>I', P[a:a + 4])[0]
SW = lambda a: struct.unpack('>h', P[a:a + 2])[0]

AM_REGI_DISP, AM_AREGIX, AM_PCI_DISP, AM_PCI_INDEX, AM_ABS_SHORT, AM_ABS_LONG, AM_IMM, AM_BRANCH = 6, 7, 11, 12, 16, 17, 18, 19
REG_A5 = 14

BRANCHES = {'bra', 'bsr', 'jmp', 'jsr', 'bhi', 'bls', 'bcc', 'bcs', 'bne', 'beq', 'bvc', 'bvs', 'bpl', 'bmi', 'bge', 'blt', 'bgt', 'ble'}
ENDS = {'rts', 'rte', 'jmp', 'bra', 'rtr'}


def decode(a):
    for ins in md.disasm(P[a:a + 10], a, 1):
        return ins
    return None


def branch_target(ins):
    m = re.search(r'\$([0-9a-f]+)', ins.op_str)
    return int(m.group(1), 16) if m else None


def trace(entries, ranges):
    inside = lambda a: any(s <= a < e for s, e in ranges)
    seen = {}
    word_tables = {}        # table address -> list of entry addresses (word offsets from table)
    long_tables = {}        # table address -> number of longs
    todo = list(entries)
    pending_tables = []     # (table, kind)
    while todo or pending_tables:
        while todo:
            a = todo.pop()
            while inside(a) and a not in seen:
                ins = decode(a)
                if ins is None:
                    raise SystemExit('undecodable at %06x' % a)
                seen[a] = ins
                m = ins.mnemonic
                ops = ins.operands
                # jump tables: move.w tbl(pc, dN.w), dM / jmp|jsr tbl(pc, dM.w)
                if m in ('jmp', 'jsr') and ops and ops[0].address_mode == AM_PCI_INDEX:
                    t = branch_target(ins)
                    pending_tables.append((t, 'word'))
                elif m == 'movea.l' and ops[0].address_mode == AM_PCI_INDEX:
                    pending_tables.append((branch_target(ins), 'long'))
                elif m == 'move.l' and ops[0].address_mode == AM_PCI_INDEX:
                    pending_tables.append((branch_target(ins), 'long?'))
                if m.split('.')[0] in BRANCHES or m.startswith('db'):
                    if ops and ops[-1].address_mode in (AM_BRANCH, AM_ABS_LONG, AM_PCI_DISP):
                        t = branch_target(ins) if ops[-1].address_mode != AM_ABS_LONG else ops[-1].imm
                        if t is not None and inside(t):
                            todo.append(t)
                if m.split('.')[0] in ENDS:
                    break
                a += ins.size
        # resolve tables after the code that is reachable so far
        while pending_tables:
            t, kind = pending_tables.pop()
            if t in word_tables or t in long_tables:
                continue
            if kind == 'word':
                entries_ = []
                k = 0
                limit = None
                while True:
                    pos = t + 2 * k
                    if limit is not None and pos >= limit:
                        break
                    if pos in seen:
                        break
                    off = SW(pos)
                    target = t + off
                    if off <= 0 or not inside(target) or off % 2:
                        break
                    entries_.append(target)
                    limit = target if limit is None else min(limit, target)
                    todo.append(target)
                    k += 1
                word_tables[t] = entries_
            else:
                n = 0
                while True:
                    pos = t + 4 * n
                    if pos in seen:
                        break
                    v = L(pos)
                    if not (0x400 <= v < 0x400000) or v % 2:
                        break
                    if inside(v):
                        todo.append(v)
                    n += 1
                long_tables[t] = n
    return seen, word_tables, long_tables


if __name__ == '__main__':
    pass
