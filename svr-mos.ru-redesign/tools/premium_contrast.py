# WCAG 2.x contrast ratios for the "premium" palette
def lum(h):
    h=h.lstrip('#'); r,g,b=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    f=lambda c: c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4
    return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)
def cr(a,b):
    la,lb=sorted([lum(a),lum(b)],reverse=True); return (la+0.05)/(lb+0.05)
P=dict(abyss='#040B1A',deep='#061430',navy='#0A1D3D',surface='#10284F',line='#1F3D66',
       cyan='#0EB8DA',blue='#0089BF',aqua='#7FDCF2',ice='#EEF5FB',mist='#A7B9D0',steel='#8399B6',
       paper='#E3ECF3',ink='#0B1B33')
pairs=[('ice','abyss'),('ice','deep'),('ice','navy'),('ice','surface'),
       ('mist','deep'),('mist','navy'),('mist','surface'),('mist','abyss'),
       ('steel','deep'),('steel','navy'),('steel','abyss'),('steel','surface'),
       ('aqua','deep'),('aqua','navy'),('aqua','surface'),
       ('cyan','deep'),('cyan','navy'),('cyan','surface'),('cyan','abyss'),
       ('blue','deep'),('blue','navy'),('blue','abyss'),
       ('ink','cyan'),('ink','aqua'),('ink','paper'),('ice','blue'),('line','navy'),('line','deep')]
import sys
for a,b in pairs:
    print(f"{a:8s} {P[a]} on {b:8s} {P[b]}: {cr(P[a],P[b]):5.2f}")
