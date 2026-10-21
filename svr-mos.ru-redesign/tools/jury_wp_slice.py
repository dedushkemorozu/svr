# Slice full-page screenshots into viewable chunks for jury review (WP/a11y lens)
import sys, os
from PIL import Image
base = '/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign'
out = base + '/tmp/jury-wp'
for c in ['deep', 'blueprint', 'premium']:
    for kind, step in [('desktop', 1100), ('mobile', 1400)]:
        im = Image.open(f'{base}/concepts/{c}/{kind}.png').convert('RGB')
        w, h = im.size
        i = 0
        y = 0
        while y < h:
            crop = im.crop((0, y, w, min(h, y + step)))
            crop.save(f'{out}/{c}-{kind}-{i:02d}.png')
            y += step
            i += 1
        print(c, kind, i)
