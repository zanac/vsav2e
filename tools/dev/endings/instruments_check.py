"""Checks every instrument the endings read in Vampire Savior (the ztap.lua logs,
ez_*/zreads.txt) against what vsav2e plays: the same sample data, loop, note, flags and
envelope, through the bank remap of banks 13 and up; then the same instruments through
Vampire Hunter 2's banks (bank + 8), as the effects 0xe4-0xe8 play them. Paths of the
development machine."""
import sys,zipfile,struct,glob,collections; sys.path.insert(0,'/home/claude/vsav2e/tools')
from build import sound as S
rd=S.read_word
z=zipfile.ZipFile('/tmp/claude-0/vs/t/vsav.zip'); V=z.read('vm3.01')+z.read('vm3.02'); VS=bytes(S.swap_pairs(z.read('vm3.11m')+z.read('vm3.12m')))
e=zipfile.ZipFile('/tmp/claude-0/vs/lr/roms_b/vsav2e.zip'); E=e.read('vs2e.01')+e.read('vs2e.02')
a=zipfile.ZipFile('/tmp/claude-0/vs/t/vsav2.zip'); b=zipfile.ZipFile('/tmp/claude-0/vs/t/vhunt2.zip')
ES=bytes(S.swap_pairs(a.read('vs2.11m')+a.read('vs2.12m'))+S.swap_pairs(b.read('vh2.11m')+b.read('vh2.12m')))
vt=rd(V,0x3b02); vb=[rd(V,0x3b04+2*k) for k in range(7)]+[vt]
et=rd(E,0x3b02); elist=rd(E,0x0d19); eenv=rd(E,0x0d85)
call=rd(E,0x17d6); remap_addr=rd(E,call+0x17); remap=list(E[remap_addr:remap_addr+8])
def resolve(p,roms,tab,env,bankaddr,i):
  x=bankaddr+4*i; n=rd(p,x)&0x7fff; s=p[tab+8*n:tab+8*n+8]
  data=roms[s[0]*0x10000+rd(s,1):s[0]*0x10000+rd(s,5)]
  ev=p[env+8*(p[x+3]&0x7f):env+8*(p[x+3]&0x7f)+8]
  return dict(data=data,loop=(rd(s,3)-rd(s,1))&0xffff,note=s[7],flag=rd(p,x)&0x8000,b2=p[x+2],eflag=p[x+3]&0x80,env=bytes(ev))
print('remap', remap)
allused=collections.defaultdict(set); env_reads=set(); samp_reads=set()
for f in sorted(glob.glob('/tmp/claude-0/vs/ez_*/zreads.txt')):
  cid=f.split('ez_')[1][:2]; used=collections.defaultdict(set)
  for l in open(f):
    x=int(l,16)
    for k in range(7):
      if vb[k]<=x<vb[k+1]: used[k].add((x-vb[k])//4)
    if vt<=x<0x5a1a: samp_reads.add((x-vt)//8)
    if 0x5a1a<=x<0x5e00: env_reads.add((x-0x5a1a)//8)
  bad=[]
  for k,ids in used.items():
    allused[k]|=ids
    for i in ids:
      r1=resolve(V,VS,vt,0x5a1a,vb[k],i)
      r2=resolve(E,ES,et,eenv,rd(E,elist+2*remap[k]),i)
      diff=[f2 for f2 in r1 if r1[f2]!=r2[f2]]
      if diff: bad.append((k,i,diff))
  print(cid, {k:len(v) for k,v in sorted(used.items())}, 'mismatches:', bad or 'none')
print('union', {k:(min(v),max(v),len(v)) for k,v in sorted(allused.items())})
print('sample entries read', len(samp_reads), 'envelope sets read', sorted(env_reads))
print('-- the same instruments through Vampire Hunter 2 banks (bank + 8), as the effects e4-e8 play them')
for k,ids in sorted(allused.items()):
  for i in sorted(ids):
    r1=resolve(V,VS,vt,0x5a1a,vb[k],i); r2=resolve(E,ES,et,eenv,rd(E,elist+2*(k+8)),i)
    d=[f2 for f2 in r1 if r1[f2]!=r2[f2]]
    if d: print(' bank',k,'#',i,d)
