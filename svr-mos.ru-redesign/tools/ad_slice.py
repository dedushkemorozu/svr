"""Нарезка полностраничных скриншотов концепций для арт-директора."""
import sys, os
from PIL import Image
ROOT = '/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign'
OUT = ROOT + '/tmp/ad'
os.makedirs(OUT, exist_ok=True)
for key in ['blueprint', 'premium', 'deep']:
    for name, chunk, scale in [('desktop', 1300, 0.62), ('mobile', 1500, 0.8)]:
        im = Image.open(f'{ROOT}/concepts/{key}/{name}.png').convert('RGB')
        w, h = im.size
        n = 0
        for y in range(0, h, chunk):
            part = im.crop((0, y, w, min(h, y + chunk)))
            part = part.resize((int(part.width * scale), int(part.height * scale)), Image.LANCZOS)
            part.save(f'{OUT}/{key}_{name}_{n:02d}.png')
            n += 1
        print(key, name, n)
