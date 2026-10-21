"""Нарезка полного скриншота на куски: python3 tools/slice_shot.py file.png [высота куска]"""
import sys
from PIL import Image
f = sys.argv[1]; hh = int(sys.argv[2]) if len(sys.argv) > 2 else 1100
im = Image.open(f); w, h = im.size
for k, y in enumerate(range(0, h, hh)):
    im.crop((0, y, w, min(h, y + hh))).save(f.replace('.png', f'_s{k}.png'))
print(w, h, (h + hh - 1) // hh)
