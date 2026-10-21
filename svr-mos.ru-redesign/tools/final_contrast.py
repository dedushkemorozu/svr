"""Контраст WCAG 2.x для итоговой палитры и fluid-формулы шкал (360→1440)."""
def lum(h):
    h = h.lstrip('#'); r, g, b = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
def cr(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True); return (la + 0.05) / (lb + 0.05)
P = dict(base='#071B2F', contrast='#E8F1F8', a1='#0EB8DA', a2='#0089BF', a3='#7FDCF2', a4='#A9BFD3',
         a5='#0B2540', a6='#04111F', s2='#0F2D4D', muted='#8AA5BD', line='#163A5C', ls='#24527A',
         paper='#DCE7EF', pink='#0B2540', pmut='#3D5872', pacc='#006E9C', mid='#061628')
pairs = [('contrast','base'),('contrast','a6'),('contrast','a5'),('contrast','s2'),('contrast','mid'),
 ('a4','base'),('a4','a6'),('a4','a5'),('a4','s2'),
 ('muted','base'),('muted','a6'),('muted','a5'),('muted','s2'),
 ('a1','base'),('a1','a6'),('a1','a5'),('a1','s2'),('a3','base'),('a3','a5'),('a3','a6'),
 ('a6','a1'),('a6','a3'),('a2','base'),('contrast','a2'),
 ('pink','paper'),('pmut','paper'),('pacc','paper'),('a1','paper'),
 ('line','base'),('ls','base'),('ls','a6'),('a1','a6')]
for a, b in pairs:
    print(f'{a:9s} {P[a]} / {b:6s} {P[b]}  {cr(P[a],P[b]):5.2f}')
print()
def fl(mn, mx, v0=360, v1=1440):
    slope = (mx - mn) / (v1 - v0); icp = mn - slope * v0
    return f'clamp({mn/16:g}rem, {icp/16:.4f}rem + {slope*100:.4f}vw, {mx/16:g}rem)'
for name, mn, mx in [('small',14,15),('medium',16,17),('large',17,20),('x-large',19,24),('xx-large',32,56),
                     ('hero',36,76),('display',48,120),('phone',32,64)]:
    print(name, mn, mx, fl(mn, mx), [round(mn + (mx-mn)*(v-360)/1080,1) for v in (360,390,768,1024,1280,1440)])
def sp(mn, mx, v0=360, v1=1440):
    slope = (mx - mn) / (v1 - v0); icp = mn - slope * v0
    return f'clamp({mn}px, {icp:.2f}px + {slope*100:.3f}vw, {mx}px)'
for n, mn, mx in [(50,24,40),(60,40,64),(70,64,112),(80,96,160)]:
    print('spacing', n, sp(mn, mx))
