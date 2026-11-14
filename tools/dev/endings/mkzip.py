"""builds vsav2e with the ported endings into /tmp/claude-0/vs/lr/roms_end/vsav2e.zip"""
import sys, os, zipfile, io, contextlib
sys.path.insert(0, '/home/claude/vsav2e/tools'); sys.path.insert(0, '/home/claude/vsav2e/text')
sys.path.insert(0, '/tmp/claude-0/vs/end')
from build import build, extension as extmod
from cps2 import program
import port
ROMS = '/tmp/claude-0/vs/t'
log = io.StringIO()
with contextlib.redirect_stdout(log):
    import build.build as bb
    # capture the extension object: rebuild with the module's own steps
    main, ext, upper, sound = bb.build(ROMS, '/home/claude/vsav2e/assets/psx')
used = len(ext.rstrip(b'\xff'))
EXT_SIZE = 0x200000
extension = bytearray(ext) + bytearray(b'\xff' * (EXT_SIZE - len(ext)))
vsav2e = bytearray(main)
upper = [bytearray(c) for c in upper]
start = (0x400000 + used + 0xff) & ~0xff
end, scroll_chips, p = port.apply(vsav2e, extension, 0x400000, start, upper)
print('endings: 0x%x-0x%x' % (start, end))
for w in p.warnings[:40]: print('  ', w)
out = '/tmp/claude-0/vs/lr/roms_end'; os.makedirs(out, exist_ok=True)
files = list(zip(['vs2e.03', 'vs2e.04', 'vs2e.05', 'vs2e.06', 'vs2e.07', 'vs2e.08', 'vs2e.09', 'vs2e.10'], program.split_program(bytes(vsav2e))))
files.append(('vs2e.10x', program.swap_byte_pairs(bytes(extension))))
files += list(zip(['vs2e.21m', 'vs2e.23m', 'vs2e.25m', 'vs2e.27m'], [bytes(c) for c in upper]))
files += list(zip(['vs2e.29m', 'vs2e.31m', 'vs2e.33m', 'vs2e.35m'], [bytes(c) for c in scroll_chips]))
half = len(sound) // 2
files += [('vs2e.01', sound[:half]), ('vs2e.02', sound[half:])]
with zipfile.ZipFile(os.path.join(ROMS, 'vhunt2.zip')) as h:
    files += [(n, h.read(n)) for n in ('vh2.11m', 'vh2.12m')]
with zipfile.ZipFile(os.path.join(out, 'vsav2e.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
    for n, d in files: z.writestr(n, d)
for f in ('vsav2.zip', 'vhunt2.zip'):
    if not os.path.exists(os.path.join(out, f)): os.symlink(os.path.join(ROMS, f), os.path.join(out, f))
print('written')
