# Список картинок по страницам старого сайта с размерами (для переноса в WP)
import json, sys
from pathlib import Path
from PIL import Image

B = Path(r"C:\l1bot\svr-mos.ru-backup")
pages = json.loads((B / "data/pages.json").read_text(encoding="utf-8"))["pages"]
out = {}
for p in pages:
    rows = []
    for s in p["sections"]:
        for im in s["images"]:
            f = B / im["file"]
            try:
                w, h = Image.open(f).size
            except Exception as e:
                w = h = None
            rows.append({"url": im["url"], "file": im["file"], "w": w, "h": h, "kb": f.stat().st_size // 1024 if f.exists() else None,
                         "section": s["type"]})
    out[p["slug"]] = rows
old = {}
for f in sorted((B / "www-old").rglob("*")):
    if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".tif", ".tiff"):
        try:
            w, h = Image.open(f).size
        except Exception:
            w = h = None
        old[f.relative_to(B / "www-old").as_posix()] = [w, h, f.stat().st_size // 1024]
(B / "newsite/images.json").write_text(json.dumps({"pages": out, "www_old": old}, ensure_ascii=False, indent=1), encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")
for k, v in out.items():
    print("==", k)
    for r in v:
        print(f"   {r['w']}x{r['h']} {r['kb']}KB [{r['section']}] {r['url'][-70:]}")
print("== www-old")
for k, v in old.items():
    print(f"   {v[0]}x{v[1]} {v[2]}KB {k}")
