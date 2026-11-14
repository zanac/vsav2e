"""Aligns vsav (decrypted) and vsav2 code: unique 8-instruction windows as anchors,
extended both ways while the normalised instructions agree.
Output: amap (vsav instruction address -> vsav2), pairs (vsav index, vsav2 index)."""
import sys, re, pickle, collections
sys.path.insert(0, '/tmp/claude-0/vs/end')
from fmap import listing
A = listing('vsavd'); B = listing('vsav2d')
A5 = re.compile(r'-?\$[0-9a-f]+\(a5')
def key(s):
    return A5.sub('X(a5', re.sub(r'#\$[0-9a-f]+', '#I', s))
ka = [key(x[1]) for x in A]; kb = [key(x[1]) for x in B]
W = 8
def grams(k):
    c = collections.defaultdict(list)
    for i in range(len(k) - W): c[hash(tuple(k[i:i + W]))].append(i)
    return c
ga, gb = grams(ka), grams(kb)
pair = {}
for h, la in ga.items():
    lb = gb.get(h)
    if lb and len(la) == 1 and len(lb) == 1:
        i, j = la[0], lb[0]
        if i in pair: continue
        # extend
        s, t = i, j
        while s > 0 and t > 0 and ka[s - 1] == kb[t - 1] and (s - 1) not in pair: s -= 1; t -= 1
        while s < len(ka) and t < len(kb) and ka[s] == kb[t]:
            if s in pair: break
            pair[s] = t; s += 1; t += 1
amap = {A[i][0]: B[j][0] for i, j in pair.items()}
pickle.dump((pair, amap), open('/tmp/claude-0/vs/end/align2.pkl', 'wb'))
print(len(amap), 'of', len(A))
