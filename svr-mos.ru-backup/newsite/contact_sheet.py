# Контактный лист картинок для просмотра: python -I contact_sheet.py out.jpg file1 file2 ...
import sys
from PIL import Image, ImageDraw

out, files = sys.argv[1], sys.argv[2:]
W, H, cols = 360, 240, 4
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (cols * W, rows * (H + 18)), "white")
d = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    im = Image.open(f).convert("RGB")
    im.thumbnail((W - 6, H - 6))
    x, y = (i % cols) * W, (i // cols) * (H + 18)
    sheet.paste(im, (x + 3, y + 3))
    d.text((x + 4, y + H), f"{i}: {f.replace(chr(92), '/').split('/')[-1][:40]}", fill="black")
sheet.save(out, quality=85)
