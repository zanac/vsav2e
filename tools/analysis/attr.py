import numpy as np, glob, os, collections, sys
def runs(game):
    out=[]
    for d in sorted(glob.glob(os.path.join(os.environ.get('VS_WORK','work'),'fc_%s_*'%game))):
        try:
            r1=open(d+'/ram_2400.bin','rb').read(); r2=open(d+'/ram_4000.bin','rb').read()
        except FileNotFoundError: continue
        a,b=r1[0x8782],r1[0x8b82]
        if a==0 and b==0 and os.path.basename(d).endswith('0b'): continue
        ids={a,b,r2[0x8782],r2[0x8b82]}
        S=set(); B=set()
        for line in open(d+'/bins.txt'):
            p=line.split()
            fr=int(p[0])
            if fr<1700 or fr>4000: continue
            (S if p[1]=='S' else B).update(int(x,16) for x in p[2:])
        out.append((d,ids,S,B))
    return out
def attribute(game, kind='S'):
    R=runs(game)
    cand={}
    for d,ids,S,B in R:
        for t in (S if kind=='S' else B):
            cand[t]=cand[t]&ids if t in cand else set(ids)
    owner=np.full(262144,-1,np.int16)   # -1 unseen, -2 common, -3 ambiguous
    for t,c in cand.items():
        owner[t]= list(c)[0] if len(c)==1 else (-2 if not c else -3)
    return owner, R
def fill(owner):
    """unseen tiles between two tiles of the same owner take that owner"""
    o=owner.copy(); last=-1; lastv=None
    idx=np.where(owner>=0)[0]
    for i,j in zip(idx[:-1],idx[1:]):
        if owner[i]==owner[j] and j-i<=256: o[i+1:j]=np.where(o[i+1:j]==-1,owner[i],o[i+1:j])
    return o

def attribute2(game, kind='S'):
    R=runs(game)
    runs_of=collections.defaultdict(list)
    for k,(d,ids,S,B) in enumerate(R):
        for t in (S if kind=='S' else B): runs_of[t].append(k)
    with_id=collections.Counter()
    for d,ids,S,B in R:
        for i in ids: with_id[i]+=1
    owner=np.full(262144,-1,np.int16)
    for t,rs in runs_of.items():
        inter=set.intersection(*[set(R[k][1]) for k in rs])
        if not inter: owner[t]=-2; continue
        best=max(inter,key=lambda c: len(rs)/with_id[c])
        sc=len(rs)/with_id[best]
        owner[t]=best if sc>=0.5 else -3
    return owner,R
