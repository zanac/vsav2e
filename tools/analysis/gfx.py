import os, zipfile, numpy as np
def load(game):
    z=zipfile.ZipFile(os.path.join(os.environ.get('VS_ROMS','roms'),'%s.zip'%game))
    p={'vsav2':'vs2','vhunt2':'vh2'}[game]
    g=np.zeros(0x2000000,np.uint8)
    for base,names in ((0,(13,15,17,19)),(0x1000000,(14,16,18,20))):
        for k,n in enumerate(names):
            d=np.frombuffer(z.read('%s.%dm'%(p,n)),np.uint8)
            # ROM_LOAD64_WORD: 2 bytes every 8 at offset 2k
            v=g[base:base+0x1000000].reshape(-1,8)
            v[:,2*k:2*k+2]=d.reshape(-1,2)
    return g

def _perm(n):
    idx=list(range(n))
    def un(lo,ln):
        if ln==2: return
        h=ln//2
        un(lo,h); un(lo+h,h)
        for i in range(h//2):
            a,b=lo+h//2+i, lo+h+i
            idx[a],idx[b]=idx[b],idx[a]
    un(0,n)
    return np.array(idx)

def unshuffle(g):
    """MAME cps2_gfx_decode: unshuffle 64-bit words in 2 MB banks"""
    w=g.view(np.uint64).copy()
    p=_perm(0x200000//8)
    out=np.empty_like(w)
    for b in range(0,len(w),len(p)):
        out[b:b+len(p)]=w[b:b+len(p)][p]
    return out.view(np.uint8)
