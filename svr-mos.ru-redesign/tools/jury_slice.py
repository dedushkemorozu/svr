# Slice full-page screenshots for jury review
import sys, os
from PIL import Image
base = '/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign'
out = os.path.join(base, 'tmp/jury')
for c in ['deep', 'blueprint', 'premium']:
    d = Image.open(f'{base}/concepts/{c}/desktop.png').convert('RGB')
    W, H = d.size
    step = 1000
    i = 0
    for y in range(0, H, step):
        d.crop((0, y, W, min(H, y + step))).save(f'{out}/{c}_d{i:02d}.png')
        i += 1
    m = Image.open(f'{base}/concepts/{c}/mobile.png').convert('RGB')
    W, H = m.size
    # place 3 strips of 1300px side by side
    strip = 1300
    strips = [m.crop((0, y, W, min(H, y + strip))) for y in range(0, H, strip)]
    j = 0
    for k in range(0, len(strips), 3):
        group = strips[k:k + 3]
        canvas = Image.new('RGB', (W * 3 + 40, strip), (255, 0, 255))
        for n, s in enumerate(group):
            canvas.paste(s, (n * (W + 20), 0))
        canvas.save(f'{out}/{c}_m{j:02d}.png')
        j += 1
    print(c, 'desktop slices', i, 'mobile sheets', j)
