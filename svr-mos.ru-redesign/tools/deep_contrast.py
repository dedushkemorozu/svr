def lum(h):
    h=h.lstrip('#'); r,g,b=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    f=lambda c: c/12.92 if c<=0.03928 else ((c+0.055)/1.055)**2.4
    return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)
def cr(a,b):
    la,lb=lum(a),lum(b); hi,lo=max(la,lb),min(la,lb); return (hi+0.05)/(lo+0.05)
P={'abyss':'#020B18','deep':'#041A30','navy':'#072845','tide':'#0B3A5E','shallow':'#0D5683',
   'cyan':'#0EB8DA','azure':'#0089BF','glow':'#5FD6EE','ice':'#A6ECF8','foam':'#EAF6FA','mist':'#A3BDD0','haze':'#7F9BB3',
   'paper':'#E8F3F7','ink':'#0A2238','inksoft':'#3D5A70'}
import sys
pairs=[('foam','abyss'),('foam','deep'),('foam','navy'),('foam','tide'),('foam','shallow'),
('mist','deep'),('mist','navy'),('mist','tide'),('mist','abyss'),('haze','deep'),('haze','navy'),('haze','abyss'),
('cyan','deep'),('cyan','navy'),('cyan','tide'),('cyan','abyss'),('glow','deep'),('glow','navy'),('glow','tide'),('ice','deep'),('ice','tide'),
('deep','cyan'),('abyss','cyan'),('foam','azure'),('deep','glow'),
('ink','paper'),('inksoft','paper'),('azure','paper'),('ink','foam')]
for a,b in pairs: print(f"{a:8s} {P[a]} on {b:8s} {P[b]}: {cr(P[a],P[b]):5.2f}")
