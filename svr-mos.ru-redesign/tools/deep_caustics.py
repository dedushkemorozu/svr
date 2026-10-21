"""Generate a tileable caustic-network SVG (bright light net between rounded dark cells).
Usage: python3 deep_caustics.py out.svg [seed] [n] [size]"""
import random, sys, math
out = sys.argv[1]
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
N = int(sys.argv[3]) if len(sys.argv) > 3 else 26
S = int(sys.argv[4]) if len(sys.argv) > 4 else 480
random.seed(seed)
# jittered grid for even cell sizes
pts = []
g = math.ceil(math.sqrt(N))
cell = S / g
for i in range(g):
    for j in range(g):
        if len(pts) >= N: break
        pts.append(((i + 0.15 + random.random()*0.7) * cell, (j + 0.15 + random.random()*0.7) * cell))
ins = [1.5 + random.random()*2.2 for _ in pts]
allp = [(x+dx*S, y+dy*S) for (x,y) in pts for dx in (-1,0,1) for dy in (-1,0,1)]
site_ins = {(x+dx*S, y+dy*S): ins[i] for i,(x,y) in enumerate(pts) for dx in (-1,0,1) for dy in (-1,0,1)}

def clip(poly, a, b, c):
    # keep a*x+b*y <= c
    res = []
    n = len(poly)
    for k in range(n):
        p, q = poly[k], poly[(k+1) % n]
        fp = a*p[0]+b*p[1]-c; fq = a*q[0]+b*q[1]-c
        if fp <= 0: res.append(p)
        if (fp < 0) != (fq < 0) and fp != fq:
            t = fp/(fp-fq); res.append((p[0]+t*(q[0]-p[0]), p[1]+t*(q[1]-p[1])))
    return res

def cellpoly(site):
    sx, sy = site
    R = S*0.9
    poly = [(sx-R, sy-R), (sx+R, sy-R), (sx+R, sy+R), (sx-R, sy+R)]
    for o in allp:
        if o == site: continue
        ox, oy = o
        if abs(ox-sx) > R or abs(oy-sy) > R: continue
        a, b = ox-sx, oy-sy
        c = (ox*ox+oy*oy - sx*sx - sy*sy)/2
        poly = clip(poly, a, b, c)
        if not poly: break
    return poly

def inset(poly, d):
    # move each edge inward by d (approx via centroid scaling per vertex)
    cx = sum(p[0] for p in poly)/len(poly); cy = sum(p[1] for p in poly)/len(poly)
    res = []
    for (x,y) in poly:
        vx, vy = x-cx, y-cy; L = math.hypot(vx,vy) or 1
        k = max(0.2, (L-d)/L)
        res.append((cx+vx*k, cy+vy*k))
    return res

def smooth(poly):
    # quadratic curves through edge midpoints, corners as control points
    n = len(poly)
    mids = [((poly[k][0]+poly[(k+1)%n][0])/2, (poly[k][1]+poly[(k+1)%n][1])/2) for k in range(n)]
    d = f"M{mids[-1][0]:.1f} {mids[-1][1]:.1f}"
    for k in range(n):
        cx, cy = poly[k]; mx, my = mids[k]
        d += f"Q{cx:.1f} {cy:.1f} {mx:.1f} {my:.1f}"
    return d + "Z"

paths = []
for site in allp:
    x, y = site
    if -S*0.35 < x < S*1.35 and -S*0.35 < y < S*1.35:
        poly = cellpoly(site)
        if len(poly) < 3: continue
        poly = inset(poly, site_ins[site])
        paths.append(smooth(poly))

svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='{S}' height='{S}' viewBox='0 0 {S} {S}'>"
       f"<defs><filter id='b' filterUnits='userSpaceOnUse' x='-40' y='-40' width='{S+80}' height='{S+80}'><feGaussianBlur stdDeviation='1.7'/></filter>"
       f"<mask id='m' maskUnits='userSpaceOnUse' x='-40' y='-40' width='{S+80}' height='{S+80}'><rect x='-40' y='-40' width='{S+80}' height='{S+80}' fill='white'/><path fill='black' d='{''.join(paths)}'/></mask></defs>"
       f"<g filter='url(#b)'><rect x='-40' y='-40' width='{S+80}' height='{S+80}' fill='#BDF4FF' mask='url(#m)'/></g></svg>")
open(out, 'w').write(svg)
print(len(svg), 'bytes', len(paths), 'cells')
