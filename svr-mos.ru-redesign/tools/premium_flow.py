"""Generate the 'turbulent -> laminar' flow-lines SVG (signature device of the premium concept).
Left: dim, crossing, turbulent streamlines (wastewater). Right: calm parallel bundle (clean water).
Catmull-Rom splines encoded with S-commands (exact, compact). Output: inline <svg> (aria-hidden)."""
import math, random, sys
W, H = 1440, 420
PTS = 36  # x-step 40

def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)

def line_points(i, n, seed=7):
    rnd = random.Random(seed * 1000 + i)
    t = i / (n - 1)
    yl = 40 + t * 340
    yr = 262 + (t - 0.5) * 64
    ph = [rnd.uniform(0, 2 * math.pi) for _ in range(3)]
    fr = [rnd.uniform(1.4, 2.2), rnd.uniform(2.6, 3.8), rnd.uniform(4.5, 6.0)]
    am = [rnd.uniform(18, 30), rnd.uniform(8, 14), rnd.uniform(3, 6)]
    out = []
    for k in range(PTS + 1):
        u = k / PTS
        s = smooth(0.18, 0.82, u)
        base = yl + (yr - yl) * s
        turb = (1 - s) ** 1.6
        y = base + turb * sum(a * math.sin(2 * math.pi * f * u + p) for a, f, p in zip(am, fr, ph))
        y += s * 7 * math.sin(2 * math.pi * 0.9 * u + 0.4)
        out.append((round(u * W), y))
    return out

def f(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s

def to_path(p):
    d = f"M{p[0][0]} {f(p[0][1])}"
    for i in range(len(p) - 1):
        p0 = p[i - 1] if i else p[i]; p1 = p[i]; p2 = p[i + 1]; p3 = p[i + 2] if i + 2 < len(p) else p2
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        if i == 0:
            c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
            d += f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {p2[0]} {f(p2[1])}"
        else:
            d += f"S{f(c2[0])} {f(c2[1])} {p2[0]} {f(p2[1])}"
    return d

def svg(n=26, idp="fl", cls="svr-flow__svg"):
    paths = "".join(
        f'<path d="{to_path(line_points(i, n))}"{" stroke-width=\"1.5\"" if i % 5 == 2 else ""} vector-effect="non-scaling-stroke"/>'
        for i in range(n))
    return (
        f'<svg class="{cls}" viewBox="0 0 {W} {H}" preserveAspectRatio="none" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg">'
        f'<defs>'
        f'<linearGradient id="{idp}-g" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{W}" y2="0">'
        f'<stop offset="0" stop-color="#3B5F8C" stop-opacity=".2"/>'
        f'<stop offset=".42" stop-color="#2D7DB4" stop-opacity=".42"/>'
        f'<stop offset=".72" stop-color="#0EB8DA" stop-opacity=".85"/>'
        f'<stop offset="1" stop-color="#9BE8F8"/></linearGradient>'
        f'<linearGradient id="{idp}-s" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="320" y2="0">'
        f'<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".55" stop-color="#D8F8FF"/>'
        f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<g id="{idp}-p" fill="none" stroke-linecap="round">{paths}</g>'
        f'<mask id="{idp}-m" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><use href="#{idp}-p" stroke="#fff"/></mask>'
        f'</defs>'
        f'<use href="#{idp}-p" stroke="url(#{idp}-g)"/>'
        f'<g mask="url(#{idp}-m)"><rect class="svr-flow__sweep" x="-320" y="0" width="320" height="{H}" fill="url(#{idp}-s)"/></g>'
        f'</svg>')

if __name__ == "__main__":
    s = svg()
    print(len(s), file=sys.stderr)
    print(s)
