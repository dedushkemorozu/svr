"""Нарезка длинного full-page скриншота на куски для просмотра: python3 tools/slice_png.py file.png [высота куска] [ширина вывода]"""
import sys
from pathlib import Path
from PIL import Image

src = Path(sys.argv[1])
h = int(sys.argv[2]) if len(sys.argv) > 2 else 1100
outw = int(sys.argv[3]) if len(sys.argv) > 3 else 0
im = Image.open(src)
W, H = im.size
out = []
for i, y in enumerate(range(0, H, h)):
    part = im.crop((0, y, W, min(H, y + h)))
    if outw and W > outw:
        part = part.resize((outw, round(part.height * outw / W)), Image.LANCZOS)
    p = src.with_name(src.stem + '-s%02d.png' % i)
    part.save(p)
    out.append(str(p))
print('\n'.join(out))
