"""Prototype: Vampire Savior's per-character endings in vsav2e.

port(vsav2e, extension_bytes, extension_used, upper_chips) patches the built images.
"""
import sys, struct, pickle, collections, re
sys.path.insert(0, '/tmp/claude-0/vs/end')
sys.path.insert(0, '/home/claude/vsav2e/tools')
import xlink
from xlink import P, W, L, decode, AM_REGI_DISP, AM_ABS_SHORT, AM_ABS_LONG, AM_IMM, AM_PCI_DISP, AM_PCI_INDEX, AM_BRANCH, REG_A5
from cps2 import program

V2 = program.load_program('vsav2d', '/tmp/claude-0/vs/t')
pair, AMAP = pickle.load(open('/tmp/claude-0/vs/end/align2.pkl', 'rb'))
A5MAP_RAW = pickle.load(open('/tmp/claude-0/vs/end/a5map.pkl', 'rb'))
READS = pickle.load(open('/tmp/claude-0/vs/end/reads.pkl', 'rb'))
A5MAP = {k: c.most_common(1)[0][0] for k, c in A5MAP_RAW.items()}
# entries the alignment missed (checked by hand)
AMAP_BY_HAND = {0x12a32: 0x110ba, 0x7d240: 0x8b97a}
AMAP.update(AMAP_BY_HAND)
_A5_KNOWN = sorted(A5MAP)


def a5_offset(d):
    """vsav2's a5 offset for vsav's d: known, or between two known ones moved alike"""
    if d in A5MAP:
        return A5MAP[d], True
    import bisect
    i = bisect.bisect(_A5_KNOWN, d)
    if 0 < i < len(_A5_KNOWN):
        lo, hi = _A5_KNOWN[i - 1], _A5_KNOWN[i]
        if A5MAP[lo] - lo == A5MAP[hi] - hi and hi - lo < 0x40:
            return d + A5MAP[lo] - lo, True
    return d, False

# ---------------------------------------------------------------- what moves
POOL_TABLES = {   # pool: (vsav table, vsav2 table, vsav classes, vsav2 classes, vsav2 runner)
    0: (0x5e556, 0x6a51c, 0x72, 0x7c, 0x6a4f0),
    1: (0x7d26c, 0x8b9a6, 0x3a, 0x3a, 0x8b97a),
    2: (0x80aac, 0x8f1d6, 0x40, 0x40, 0x8f1aa),
    3: (0x8476a, 0x939a6, 0x0b, 0x0b, 0x93974),
    4: (0x89014, 0x9885e, 0x07, 0x07, 0x98832),
}
ALLOCATORS = {0x16fba: 0, 0x16fd0: 1, 0x16fe6: 2, 0x16ffc: 3, 0x17012: 4}
# object classes the endings use whose code reads Vampire Savior data: they move too,
# as new classes after vsav2's own in each pool
MOVED_CLASSES = {0: list(range(0x40, 0x50)), 1: [0x31], 3: list(range(0x04, 0x0a)), 4: [0x00]}


def class_entry(pool, c):
    return struct.unpack('>I', P[POOL_TABLES[pool][0] + 4 * c:POOL_TABLES[pool][0] + 4 * c + 4])[0]


def class_range(pool, c):
    """the code of a class: from its entry to the next entry above it"""
    entries = sorted(set(struct.unpack('>%dI' % POOL_TABLES[pool][2], P[POOL_TABLES[pool][0]:POOL_TABLES[pool][0] + 4 * POOL_TABLES[pool][2]])))
    s = class_entry(pool, c)
    later = [e for e in entries if e > s]
    return (s, min(later) if later else s + 0x400)


CLASS_RANGES = []
for _pool, _classes in MOVED_CLASSES.items():
    for _c in _classes:
        CLASS_RANGES.append(class_range(_pool, _c))
# merge touching class ranges
CLASS_RANGES.sort()
_merged = []
for _s, _e in CLASS_RANGES:
    if _merged and _s <= _merged[-1][1]:
        _merged[-1][1] = max(_merged[-1][1], _e)
    else:
        _merged.append([_s, _e])
CODE_RANGES = [(0xcd32, 0xcde0), (0x14ffa, 0x1502e), (0x1f034, 0x1f0fe), (0x1f458, 0x1f4b8), (0x1f856, 0x1f87e),
               (0x21a20, 0x21db0), (0x8c8d2, 0x91564)] + [tuple(m) for m in _merged]
ENTRIES = ([0xcd32, 0x14ffa, 0x1f034, 0x1f458, 0x1f856, 0x21a20]
           + [class_entry(p_, c_) for p_, cs_ in MOVED_CLASSES.items() for c_ in cs_]
           + list(struct.unpack('>16I', P[0x21b06:0x21b46])))


def in_ranges(a, ranges):
    return any(s <= a < e for s, e in ranges)


def class_map():
    """(pool, vsav class) -> vsav2e class"""
    out = {}
    for pool, (tv, t2, n, nb, runner) in POOL_TABLES.items():
        A = struct.unpack('>%dI' % n, P[tv:tv + 4 * n])
        B = struct.unpack('>%dI' % nb, V2[t2:t2 + 4 * nb])
        moved = MOVED_CLASSES.get(pool, [])
        for c in range(n):
            if c in moved:
                out[(pool, c)] = nb + moved.index(c)
            elif A[c] in AMAP and AMAP[A[c]] in B:
                out[(pool, c)] = B.index(AMAP[A[c]])
    return out


# ---------------------------------------------------------------- data blocks
# texts of the endings (master tables, quotes format): Japanese and English
TEXT_JAPANESE = (0x332216, 0x334586)
TEXT_ENGLISH = (0x33c5e4, 0x33f2ee)
LANGUAGE_TABLE = 0x112dc         # 4 longs: Japanese, English, Spanish, Portuguese
# the tilemap loaders add id * stride to their bases: their tables move as one block
EXPLICIT_DATA = [TEXT_JAPANESE, TEXT_ENGLISH, (0x35ac24, 0x38a7c6), (0xcde0, 0xd0c0)]
# how long each page of text stays: 4 longs (by language) at 0xcdd0, to tables at 0xcde0-0xd0c0
TEXT_DURATIONS = 0xcdd0

def data_blocks(code_refs):
    """vsav data to copy: what the endings read, plus what the moved code points at"""
    points = set()
    for pc, s in READS.items():
        for a in s:
            if a >= 0x100000 or 0xb7000 <= a < 0xb8000 or 0xcde0 <= a < 0xd0c0:
                points.add(a)
    points |= {v for v in code_refs if v >= 0x100000 and v < 0x400000 or 0xb7000 <= v < 0xb8000 or 0xcde0 <= v < 0xd0c0}
    for s, e in EXPLICIT_DATA:
        points |= {s, e - 2}
    blocks = []
    for a in sorted(points):
        if blocks and a - blocks[-1][1] <= 0x8000:
            blocks[-1][1] = a + 2
        else:
            blocks.append([a, a + 2])
    for b in blocks:
        b[1] += 0x20                         # the end of the last structure read
        b[0] &= ~1
    spans = sorted([list(b) for b in blocks] + [list(x) for x in EXPLICIT_DATA])
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [tuple(b) for b in merged]


# ---------------------------------------------------------------- relocation
EXT = {AM_ABS_LONG: 4, AM_ABS_SHORT: 2, AM_REGI_DISP: 2, AM_PCI_DISP: 2, AM_PCI_INDEX: 2, 7: 2}


def operand_layout(ins):
    """[(operand, offset of its extension words in the instruction)]"""
    pos = 2
    out = []
    m = ins.mnemonic
    if m.startswith('movem'):
        pos += 2                         # the register mask word
    for op in ins.operands:
        size = 0
        if op.address_mode == AM_IMM:
            size = 4 if m.endswith('.l') else 2
            if m.startswith(('moveq', 'addq', 'subq', 'trap')) or (m.startswith(('lsl', 'lsr', 'asl', 'asr', 'rol', 'ror', 'roxl', 'roxr'))):
                size = 0                 # the value is in the opcode
        elif op.address_mode in EXT:
            size = EXT[op.address_mode]
        elif op.address_mode == AM_BRANCH:
            size = 0 if ins.size == 2 else ins.size - 2
        out.append((op, pos, size))
        pos += size
    return out


class Port:
    def __init__(self):
        global CODE_RANGES
        # routines the moved code calls that read Vampire Savior data themselves (or
        # through what they call) move too, until none is left
        while True:
            self.seen, self.word_tables, self.long_tables = xlink.trace(ENTRIES, CODE_RANGES)
            extra = self.impure_targets()
            if not extra:
                break
            CODE_RANGES = CODE_RANGES + extra
            for s, e in extra:
                ENTRIES.append(s)
        self.long_tables[TEXT_DURATIONS] = 4
        self.classes = class_map()
        self.warnings = []

    def impure_targets(self):
        """[(start, end)] of the called routines outside the moved code that reach
        absolute data of Vampire Savior (0x100000-0x3fffff)"""
        targets = set()
        for a, ins in self.seen.items():
            if ins.mnemonic in ('jsr', 'jmp') and ins.operands[0].address_mode == AM_ABS_LONG:
                v = ins.operands[0].imm
                if v < 0x100000 and not in_ranges(v, CODE_RANGES) and v not in AMAP_BY_HAND:
                    targets.add(v)
        import purity
        out = []
        for t in sorted(targets):
            seen, data = purity.refs(t)
            if data:
                lo = min(seen); hi = max(a + ins.size for a, ins in seen.items())
                out.append((lo, (hi + 1) & ~1))
                print('moving routine %06x-%06x (reads data)' % (lo, hi))
        # merge with each other (not with the existing ranges: those are traced already)
        out.sort()
        merged = []
        for a, b in out:
            if merged and a <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        return [tuple(m) for m in merged if not any(s <= m[0] and m[1] <= e for s, e in CODE_RANGES)]

    def code_refs(self):
        refs = set()
        for a, ins in self.seen.items():
            for op in ins.operands:
                if op.address_mode in (AM_ABS_LONG, AM_IMM):
                    refs.add(op.imm & 0xffffffff)
        for t, n in self.long_tables.items():
            refs |= {L(t + 4 * k) for k in range(n)}
        return refs

    def layout(self, base):
        """places the code ranges then the data blocks from base; returns the end"""
        self.place = []                  # (vsav start, vsav end, new start)
        a = base
        for s, e in CODE_RANGES:
            self.place.append((s, e, a)); a += (e - s + 1) & ~1
        self.code_end = a
        self.blocks = data_blocks(self.code_refs())
        for s, e in self.blocks:
            a = (a + 1) & ~1
            self.place.append((s, e, a)); a += e - s
        self.language_table_address = a
        return a + 16

    def language_table(self):
        jp = self.new_address(TEXT_JAPANESE[0]); en = self.new_address(TEXT_ENGLISH[0])
        return struct.pack('>4I', jp, en, en, en)

    def new_address(self, v):
        if v == LANGUAGE_TABLE:
            return self.language_table_address
        for s, e, n in self.place:
            if s <= v < e:
                return n + v - s
        return None

    def verified(self, v, where, context):
        """the vsav2 address of the vsav routine at v, checked instruction by instruction"""
        import verify
        if not hasattr(self, '_verified'):
            self._verified = {}
        if v not in self._verified:
            if v in AMAP_BY_HAND:
                self._verified[v] = AMAP_BY_HAND[v]
            else:
                r, status = verify.check(v, AMAP.get(v), A5MAP)
                if r is None:
                    self.warnings.append('%06x: %06x has no vsav2 routine (%s) %s' % (where, v, status, context))
                    r = AMAP[v]
                self._verified[v] = r
        return self._verified[v]

    def relocate_long(self, v, where, context=''):
        n = self.new_address(v)
        if n is not None:
            return n
        if v < 0x100000 and v in AMAP:
            return self.verified(v, where, context)
        if 0xff0000 <= v <= 0xffffff:
            d = v - 0xff8000
            return 0xff8000 + A5MAP.get(d, d)
        if 0x400 <= v < 0x400000:
            self.warnings.append('%06x: %08x unmapped %s' % (where, v, context))
        return v

    def patch_code(self, image, image_base):
        """copies the code ranges into image (bytearray at image_base) and relocates them"""
        def put(addr_vsav, size, value):
            n = self.new_address(addr_vsav) - image_base
            image[n:n + size] = value.to_bytes(size, 'big')

        for s, e, n in self.place[:len(CODE_RANGES)]:
            image[n - image_base:n - image_base + e - s] = P[s:e]

        last_alloc = None
        for a in sorted(self.seen):
            ins = self.seen[a]
            raw = P[a:a + ins.size]
            m = ins.mnemonic
            if m in ('jsr', 'jmp') and ins.operands[0].address_mode == AM_ABS_LONG:
                if ins.operands[0].imm in ALLOCATORS:
                    last_alloc = ALLOCATORS[ins.operands[0].imm]
            for op, pos, size in operand_layout(ins):
                am = op.address_mode
                if am == AM_ABS_LONG:
                    v = op.imm & 0xffffffff
                    assert int.from_bytes(raw[pos:pos + 4], 'big') == v, ('abs', hex(a), ins.mnemonic, ins.op_str)
                    put(a + pos, 4, self.relocate_long(v, a, ins.mnemonic + ' ' + ins.op_str) & 0xffffffff)
                elif am == AM_IMM and size == 4:
                    v = op.imm & 0xffffffff
                    assert int.from_bytes(raw[pos:pos + 4], 'big') == v, ('imm', hex(a), ins.mnemonic, ins.op_str)
                    if (v >> 24) == 1 and m == 'move.l' and '(a4)' in ins.op_str:
                        # an object: 01 xx class kind
                        cls = (v >> 8) & 0xff
                        pool = last_alloc if last_alloc is not None else 0
                        nc = self.classes.get((pool, cls))
                        if nc is None:
                            self.warnings.append('%06x: object %08x pool %d: no class' % (a, v, pool))
                        else:
                            put(a + pos, 4, (v & 0xffff00ff) | (nc << 8))
                    elif self.new_address(v) is not None or m.startswith(('movea', 'lea', 'pea', 'cmpa', 'adda', 'suba')):
                        put(a + pos, 4, self.relocate_long(v, a, ins.mnemonic + ' ' + ins.op_str))
                    elif 0x100000 <= v < 0x400000:
                        self.warnings.append('%06x: immediate %08x left as it is (%s %s)' % (a, v, m, ins.op_str))
                elif am == AM_REGI_DISP and op.mem.base_reg == REG_A5:
                    d = op.mem.disp
                    assert struct.unpack('>h', raw[pos:pos + 2])[0] == d, ('a5', hex(a), ins.op_str)
                    nd, known = a5_offset(d)
                    if not known:
                        self.warnings.append('%06x: a5 %x not in the map (%s %s)' % (a, d & 0xffff, m, ins.op_str))
                    put(a + pos, 2, nd & 0xffff)
                elif am == AM_ABS_SHORT:
                    v = op.imm & 0xffff
                    self.warnings.append('%06x: absolute short %04x (%s %s)' % (a, v, m, ins.op_str))
                elif am in (AM_PCI_DISP, AM_PCI_INDEX, AM_BRANCH) or m.startswith('db'):
                    t = xlink.branch_target(ins)
                    if t is not None and not in_ranges(t, CODE_RANGES) and am != AM_ABS_LONG:
                        # a pc-relative reference that leaves the moved code
                        if not (m in ('jsr', 'jmp') and am == AM_ABS_LONG):
                            self.warnings.append('%06x: pc-relative to %06x outside (%s %s)' % (a, t, m, ins.op_str))
        # pointers kept in the data parts of the moved code (scripts of the palette
        # animations of pool 3): longs there whose value is inside the moved code
        covered = set()
        for a, ins in self.seen.items():
            covered.update(range(a, a + ins.size))
        for t, n in self.long_tables.items():
            covered.update(range(t, t + 4 * n))
        for s, e in CODE_RANGES:
            a = s
            while a < e - 3:
                if a in covered or a + 2 in covered:
                    a += 2; continue
                v = L(a)
                if v % 2 == 0 and in_ranges(v, CODE_RANGES):
                    put(a, 4, self.new_address(v)); a += 4
                else:
                    a += 2
        # long tables (code or data pointers)
        for t, n in self.long_tables.items():
            for k in range(n):
                v = L(t + 4 * k)
                if self.new_address(v) is not None or v in AMAP or 0xff0000 <= v:
                    put(t + 4 * k, 4, self.relocate_long(v, t + 4 * k, 'long table'))


if __name__ == '__main__':
    port = Port()
    end = port.layout(0x480000)
    print('code', hex(port.code_end - 0x480000), 'all', hex(end - 0x480000))
    for s, e in port.blocks:
        print('  data %06x-%06x %6x' % (s, e, e - s))
    image = bytearray(0x200000)
    port.patch_code(image, 0x400000)
    c = collections.Counter(w.split(':')[1].split()[0] if ': a5' not in w else 'a5' for w in port.warnings)
    for w in port.warnings: print(w)


# ================================================================ data, graphics, hooks
import numpy as np
VSAV_GFX = np.load('/tmp/claude-0/vs/vsav_gfx.npy', mmap_mode='r')    # unshuffled, 32 MB

# pointer fields of the animation data, found by the code that reads them
STEP_FRAME_READERS = (0x1afaa, 0x1b7f4)      # movea.l 4(a0), a0: the frame of a step
STEP_LOOP_READERS = (0x1504e, 0x151a0)
# tile animations of scroll 2 (16-byte steps): the tile block of a step
TILE_STEP_BLOCK_READERS = (0x15206,)               # movea.l 8(a0), a0: the step a loop goes back to
FRAME_TYPE_READERS = (0x1afae, 0x1b7f8)              # move.w (a0)+, d0: the type of a frame

SCROLL_BANK_REGISTER = 0x8040c0              # vsav2e: bit 0-2 scroll 1-3 tiles from the scroll bank
SCROLL_BANK_SIZE = 0x1000000
SCROLL_GFX_START = 0x800000
BLANK_CODES = ((0x0020, 64), (0x4220, 128), (0x0600, 512))     # scroll 1, 2, 3


def long_fields(readers):
    out = set()
    for pc in readers:
        s = READS.get(pc, set())
        out |= {a for a in s if a + 2 in s and a % 2 == 0}
    return out


def raw_write(chips, offset, data):
    """writes unshuffled graphics bytes (8-byte words) into 4 chips of 16 MB"""
    from cps2 import sprite_rom
    for k in range(0, len(data), 8):
        word = (offset + k) // 8
        bank = word - word % sprite_rom.BANK_WORDS
        o = 2 * (bank + sprite_rom.shuffled_word(word % sprite_rom.BANK_WORDS))
        for i, chip in enumerate(chips):
            chip[o:o + 2] = data[k + 2 * i:k + 2 * i + 2]


class Graphics:
    def __init__(self, port):
        self.port = port

    def sprite_tiles(self):
        """tiles of the moved frames (all drawn from sprite bank 1): their numbers"""
        tiles = set()
        frames = set()
        for pc in FRAME_TYPE_READERS:
            frames |= {f for f in READS.get(pc, set()) if f % 2 == 0}
        for f in frames:
            t = W(f)
            if t == 2:
                n = W(f + 4) + 1
                recs = [struct.unpack('>HH', P[f + 10 + 4 * k:f + 14 + 4 * k]) for k in range(n)]
            elif t == 0:
                n = W(f + 2); attr = W(f + 4)
                recs = [(W(f + 10 + 2 * k), attr) for k in range(n)]
            else:
                continue
            for tile, attr in recs:
                for r in range(((attr >> 12) & 15) + 1):
                    for c in range(((attr >> 8) & 15) + 1):
                        tiles.add(0x10000 + (tile & ~15) + ((tile + c) & 15) + 16 * r)
        return tiles

    def scroll_codes(self):
        """(layer, entry address in vsav, vsav code) of the tilemap blocks the endings use"""
        out = []
        for pcs, base, step, offset, layer in (
                # the loader decides the layer: 0x1f034 fills scroll 1 (8x8), 0x1f458 scroll 2,
                # 0x1f856 scroll 3 (32x32) in every script
                ((0x1f06e, 0x1f07e, 0x1f090, 0x1f0a2, 0x1f0b4, 0x1f0c6, 0x1f0d8, 0x1f0ea), 0x35c824, 4, 0, 1),
                ((0x1f494, 0x1f4a4), 0x376424, 4, 0x3800, 2),
                ((0x1f868,), 0x384aa4, 4, 0x600, 3)):
            entries = set()
            for pc in pcs:
                entries |= {a for a in READS.get(pc, set()) if a >= base and (a - base) % step == 0}
            out += [(layer, a, (W(a) + offset) & 0xffff, 0) for a in sorted(entries)]
        # tile blocks of the scroll 2 animations (0x15182): 3 words, then (code, attribute);
        # vsav2's copy of the routine adds 0x4200 to the code, Vampire Savior's 0x3800
        blocks = READS.get(0x1520a, set())
        for a in sorted(READS.get(0x15214, set())):
            start = max([b for b in blocks if b <= a], default=None)
            if start is not None and (a - start - 6) % 4 == 0:
                out.append((2, a, (W(a) + 0x3800) & 0xffff, 0x4200))
        return out


def apply(vsav2e, extension, extension_base, start, upper_chips):
    """vsav2e: bytearray (4 MB program); extension: bytearray from extension_base.
    Returns (end of the extension used, scroll bank chips)."""
    port = Port()
    end = port.layout(start)
    port.patch_code(extension, extension_base)
    ext = lambda a: a - extension_base
    # data blocks
    for s, e, n in port.place[len(CODE_RANGES):]:
        extension[ext(n):ext(n) + e - s] = P[s:e]
    extension[ext(port.language_table_address):ext(port.language_table_address) + 16] = port.language_table()
    fixed = set()
    def fix(a):
        v = L(a); nv = port.new_address(v)
        if nv is None:
            port.warnings.append('data %06x: pointer %08x outside the copied data' % (a, v)); return
        n = port.new_address(a)
        extension[ext(n):ext(n) + 4] = nv.to_bytes(4, 'big'); fixed.add(a)
    for a in long_fields(STEP_FRAME_READERS) | long_fields(STEP_LOOP_READERS) | long_fields(TILE_STEP_BLOCK_READERS):
        fix(a)
    frames = set()
    for pc in FRAME_TYPE_READERS:
        frames |= {f for f in READS.get(pc, set()) if f % 2 == 0}
    for f in frames:
        if W(f) in (0, 2):
            fix(f + 6)
    # graphics: sprite tiles at their own numbers in the upper bank
    g = Graphics(port)
    tiles = g.sprite_tiles()
    for t in tiles:
        raw_write(upper_chips, t * 128, bytes(VSAV_GFX[t * 128:(t + 1) * 128]))
    # scroll tiles: renumbered into the scroll bank
    scroll_chips = [bytearray(b'\xff' * 0x400000) for _ in range(4)]
    codes = g.scroll_codes()
    # the layer fill at 0x14ffa writes code 0x3810 + d0 (d0 = 1, its only use) to scroll 2
    FILL_ADDI = 0x15002
    codes_all = codes + [(2, None, 0x3811, 0)]
    new_code = {}
    # the codes vsav2's own code fills empty layers with must stay blank in the bank
    reserved = [(code * size, code * size + size) for code, size in BLANK_CODES]
    position = 0
    for layer, size in ((3, 512), (2, 128), (1, 64)):
        for c in sorted({c for l, a, c, bias in codes_all if l == layer}):
            while True:
                position = (position + size - 1) // size * size
                clash = [e for s, e in reserved if s < position + size and position < e]
                if not clash:
                    break
                position = max(clash)
            new_code[(layer, c)] = position // size
            # CPS2 scroll tiles start 8 MB into the graphics (bank_scroll 4 in MAME)
            source = (SCROLL_GFX_START + c * size) % len(VSAV_GFX)     # MAME wraps the codes
            raw_write(scroll_chips, position, bytes(VSAV_GFX[source:source + size]))
            position += size
    assert position <= SCROLL_BANK_SIZE
    for layer, a, c, bias in codes:
        n = port.new_address(a)
        extension[ext(n):ext(n) + 2] = ((new_code[(layer, c)] - bias) & 0xffff).to_bytes(2, 'big')
    n = port.new_address(FILL_ADDI)
    assert extension[ext(n):ext(n) + 4] == bytes.fromhex('06403810')
    extension[ext(n) + 2:ext(n) + 4] = (new_code[(2, 0x3811)] - 1).to_bytes(2, 'big')
    # the loaders store the codes as they are
    for addi in (0x1f498, 0x1f49c, 0x1f4a8, 0x1f4ac, 0x1f86c):
        n = port.new_address(addi)
        assert extension[ext(n)] == 0x06 and extension[ext(n) + 1] & 0xf8 == 0x40, hex(addi)
        extension[ext(n) + 2:ext(n) + 4] = b'\x00\x00'
    # each pool: a table with the moved classes after vsav2's, read by a hook in its runner
    import os
    RUNNER_CODE = bytes.fromhex('7000102e0002d040d040207b0012' '70004e90')
    for pool, classes in MOVED_CLASSES.items():
        tv, t2, n, nb, runner = POOL_TABLES[pool]
        table = bytearray(vsav2e[t2:t2 + 4 * nb])
        for c in classes:
            table += port.new_address(class_entry(pool, c)).to_bytes(4, 'big')
        table_address = (end + 1) & ~1
        extension[ext(table_address):ext(table_address) + len(table)] = table
        end = table_address + len(table)
        hook = end
        code = bytes.fromhex('7000' '102e0002' 'd040' 'd040' '41f9') + table_address.to_bytes(4, 'big') + bytes.fromhex(
            '20700000' '7000' '4ed0')
        #   moveq #0,d0 / move.b 2(a6),d0 / add.w d0,d0 x2 / lea table,a0 / movea.l 0(a0,d0.w),a0 / moveq #0,d0 / jmp (a0)
        extension[ext(hook):ext(hook) + len(code)] = code
        end += len(code)
        site = runner + vsav2e[runner:runner + 0x40].find(bytes.fromhex('7000102e0002d040d040207b'))
        assert site > runner and vsav2e[site + 14:site + 18] == bytes.fromhex('70004e90'), hex(runner)
        if str(pool) not in os.getenv('NO_RUNNER', ''):
            vsav2e[site:site + 18] = b'\x4e\xb9' + hook.to_bytes(4, 'big') + b'\x4e\x71' * 6
    # the ending mode: ported characters run Vampire Savior's ending, then Savior 2's credits
    dispatcher = (end + 1) & ~1
    savior2_ending = 0x205f8
    module = port.new_address(0x21a20)
    bank = SCROLL_BANK_REGISTER.to_bytes(4, 'big')
    code = (bytes.fromhex('7000' '102d0130'            # 00 moveq #0,d0 / move.b $130(a5),d0
                          '0c00000f' '642c'           # 06 cmpi.b #$0f,d0 / bcc savior2
                          '0c00000b' '6726'           # 0c cmpi.b #$0b,d0 / beq savior2
                          '0c6d00040008' '6510'       # 12 cmpi.w #4,$8(a5) / bcs ported
                          '661c')                     # 1a bne savior2: Savior 2's credits and after
            + bytes.fromhex('4279') + bank                                        # 1c clr.w bank
            + bytes.fromhex('3b7c00120008')                                       # 22 move.w #$12,$8(a5)
            + bytes.fromhex('600e')                                               # 28 bra savior2
            # 2a ported:
            + bytes.fromhex('33fc0007') + bank                                    # 2a move.w #7,bank
            + b'\x4e\xf9' + module.to_bytes(4, 'big')                            # 32 jmp module
            # 38 savior2:
            + b'\x4e\xf9' + savior2_ending.to_bytes(4, 'big'))
    extension[ext(dispatcher):ext(dispatcher) + len(code)] = code
    end = dispatcher + len(code)
    assert vsav2e[0x791e:0x7924] == bytes.fromhex('4ef9000205f8')
    if not os.getenv('NO_DISPATCH'): vsav2e[0x791e:0x7924] = b'\x4e\xf9' + dispatcher.to_bytes(4, 'big')
    return end, scroll_chips, port
