import json, sys
from PIL import Image, ImageDraw
media = json.load(open(sys.argv[1]))
ids = [int(x) for x in sys.argv[3].split(',')]
cell_w, cell_h = 360, 300
cols = 4
items = [m for m in media if m['id'] in ids]
rows = (len(items)+cols-1)//cols
sheet = Image.new('RGB', (cols*cell_w, rows*cell_h), (128,128,128))
d = ImageDraw.Draw(sheet)
for i, m in enumerate(items):
    im = Image.open(m['local']).convert('RGBA')
    im.thumbnail((cell_w-10, cell_h-30))
    x = (i%cols)*cell_w + 5; y = (i//cols)*cell_h + 5
    bg = Image.new('RGBA', im.size, (200,200,200,255))
    bg.alpha_composite(im)
    sheet.paste(bg.convert('RGB'), (x, y))
    d.text((x, y+cell_h-25), f"id {m['id']} {m['w']}x{m['h']}", fill=(0,0,0))
sheet.save(sys.argv[2])
