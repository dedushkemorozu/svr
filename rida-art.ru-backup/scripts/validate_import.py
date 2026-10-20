#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка пакета import-woocommerce: читает файлы с диска и сверяет с резервной копией.
Запуск: python -I -X utf8 validate_import.py
"""
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(r"C:\l1bot\rida-art.ru-backup")
IMP = ROOT / "import-woocommerce"
errors, notes = [], []


def err(msg):
    errors.append(msg)


def read_csv(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


for name in ("README.md", "install_on_server.sh", "create_categories.sh", "products_import.csv",
             "products_import_local-images.csv", "categories.csv", "pages_import.xml", "redirects.csv", "review.csv"):
    if not (IMP / name).is_file():
        err(f"в пакете нет файла {name}")
for sh in IMP.glob("*.sh"):
    if b"\r" in sh.read_bytes():
        err(f"{sh.name}: переводы строк CRLF — bash на сервере не запустит")
    if not sh.read_bytes().startswith(b"#!/usr/bin/env bash"):
        err(f"{sh.name}: нет строки #!/usr/bin/env bash")

products = json.loads((ROOT / "data/products.json").read_text(encoding="utf-8"))["products"]
P = {p["id"]: p for p in products}
cats = read_csv(IMP / "categories.csv")
cat_names = {c["name"]: c for c in cats}
cat_slugs = {c["slug"] for c in cats}

# ---- products CSV ---------------------------------------------------------
rows = read_csv(IMP / "products_import.csv")
rows_l = read_csv(IMP / "products_import_local-images.csv")
if len(rows) != len(rows_l):
    err("CDN- и local-CSV разной длины")
types = [r["Type"] for r in rows]
notes.append(f"строк: {len(rows)} = simple {types.count('simple')} + variable {types.count('variable')} + variation {types.count('variation')}")
skus = [r["SKU"] for r in rows]
if len(skus) != len(set(skus)):
    err("повторяющиеся SKU: " + ", ".join(s for s in set(skus) if skus.count(s) > 1))
variable = {r["SKU"]: r for r in rows if r["Type"] == "variable"}
imported = {r["SKU"] for r in rows if r["Type"] in ("simple", "variable")}
missing = [i for i in P if i not in imported]
notes.append(f"товаров из копии не вошло в CSV: {len(missing)} ({', '.join(missing)})")
for r in rows:
    t, sku = r["Type"], r["SKU"]
    if not r["Name"].strip():
        err(f"{sku}: пустое название")
    if t in ("simple", "variable"):
        src = P.get(sku)
        if not src:
            err(f"{sku}: нет такого товара в копии"); continue
        if r["Name"] != src["title"].strip():
            err(f"{sku}: название отличается от копии")
        if r["Published"] not in ("1", "-1"):
            err(f"{sku}: Published={r['Published']}")
        if t == "simple":
            reg = r["Regular price"]
            if not re.fullmatch(r"\d+", reg or ""):
                err(f"{sku}: цена {reg!r}")
            elif src["price_old"]:
                if int(reg) != src["price_old"] or int(r["Sale price"]) != src["price"]:
                    err(f"{sku}: скидка перепутана")
            elif int(reg) != src["price"]:
                err(f"{sku}: цена {reg} != {src['price']}")
            if r["Sale price"] and int(r["Sale price"]) >= int(reg):
                err(f"{sku}: sale >= regular")
        urls = [u.strip() for u in r["Images"].split(",") if u.strip()]
        if urls != [i["url"] for i in src["images"]]:
            err(f"{sku}: список фото (CDN) не совпадает с копией")
        for c in [x.strip() for x in r["Categories"].split(",") if x.strip()]:
            leaf = c.split(" > ")[-1]
            if leaf not in cat_names:
                err(f"{sku}: неизвестная категория {c!r}")
            elif " > " in c and c.split(" > ")[0] != next(x["name"] for x in cats if x["slug"] == cat_names[leaf]["parent_slug"]):
                err(f"{sku}: неверный родитель в {c!r}")
        if r["Published"] == "1" and not r["Categories"]:
            err(f"{sku}: опубликован без категории")
    else:
        parent = variable.get(r["Parent"])
        if not parent:
            err(f"вариация {sku}: нет родителя {r['Parent']!r}"); continue
        if r["Attribute 1 value(s)"] not in [v.strip() for v in parent["Attribute 1 value(s)"].split(",")]:
            err(f"вариация {sku}: значение {r['Attribute 1 value(s)']!r} не входит в атрибут родителя")
        if r["Attribute 1 name"] != parent["Attribute 1 name"]:
            err(f"вариация {sku}: имя атрибута отличается от родителя")
        if not re.fullmatch(r"\d+", r["Regular price"] or ""):
            err(f"вариация {sku}: цена {r['Regular price']!r}")
for sku, r in variable.items():
    n = sum(1 for x in rows if x["Parent"] == sku)
    if n != len(P[sku]["variants"]) or n != len([v for v in r["Attribute 1 value(s)"].split(",")]):
        err(f"{sku}: вариаций {n}, в копии {len(P[sku]['variants'])}, значений атрибута {len(r['Attribute 1 value(s)'].split(','))}")

# local-версия отличается только колонкой Images и ссылается на существующие файлы
for a, b in zip(rows, rows_l):
    for k in a:
        if k != "Images" and a[k] != b[k]:
            err(f"{a['SKU']}: CSV различаются в колонке {k}")
    if b["Images"]:
        for u in b["Images"].split(", "):
            if not (IMP / "uploads/rida-import/products" / u.rsplit("/", 1)[-1]).exists():
                err(f"{b['SKU']}: нет файла для {u}")
n_img = len(list((IMP / "uploads/rida-import/products").iterdir()))
if n_img != sum(len(P[s]["images"]) for s in imported):
    err(f"файлов в uploads/products {n_img}, ожидалось {sum(len(P[s]['images']) for s in imported)}")
for f in (IMP / "uploads/rida-import/products").iterdir():
    h = f.read_bytes()[:3]
    if f.suffix.lower() in (".jpeg", ".jpg") and h != b"\xff\xd8\xff":
        err(f"не JPEG: {f.name}")

# ---- состав категорий -----------------------------------------------------
catalogs = {c["page"]: c for c in json.loads((ROOT / "data/catalogs.json").read_text(encoding="utf-8"))["catalogs"]}
by_cat = {}
for r in rows:
    if r["Type"] in ("simple", "variable"):
        for c in [x.strip() for x in r["Categories"].split(",") if x.strip()]:
            by_cat.setdefault(c.split(" > ")[-1], set()).add(r["SKU"])
old_of = {"Новинки": "new", "Ангелы": "angels", "Домики": "houses", "Маяки": "mayak", "Птицы": "birds", "Лошадки": "horse",
          "Грибы": "mush", "Наборы": "nabory", "Пасхальные стеклянные яйца с росписью": "page97",
          "Пасхальные деревянные яйца с росписью": "page98", "Пасхальные ангелы": "page99",
          "Пасхальные подвески": "page100", "Пасхальные наборы": "page101"}
for name, old in old_of.items():
    expect = set(catalogs[old]["goods_ids"]) & set(imported)
    if by_cat.get(name, set()) != expect:
        err(f"категория {name}: в CSV {len(by_cat.get(name, ()))}, в каталоге {old} {len(expect)}")
notes.append("состав категорий: " + ", ".join(f"{n}={len(by_cat.get(n, ()))}" for n in old_of))

# ---- страницы (WXR) -------------------------------------------------------
ns = {"wp": "http://wordpress.org/export/1.2/", "content": "http://purl.org/rss/1.0/modules/content/"}
tree = ET.parse(IMP / "pages_import.xml")
items = tree.getroot().findall("./channel/item")
notes.append(f"страниц в XML: {len(items)}: " + ", ".join(f"{i.find('wp:post_name', ns).text}[{i.find('wp:status', ns).text}]" for i in items))
for it in items:
    slug = it.find("wp:post_name", ns).text
    body = it.find("content:encoded", ns).text or ""
    if len(body) < 100:
        err(f"страница {slug}: подозрительно короткое содержимое ({len(body)})")
    for u in re.findall(r'src="[^"]*/rida-import/pages/([^"]+)"', body):
        if not (IMP / "uploads/rida-import/pages" / u).exists():
            err(f"страница {slug}: нет файла {u}")
    if "selstorage.ru" in body:
        err(f"страница {slug}: осталась ссылка на старое хранилище")
    if re.search(r"<(script|iframe)", body, re.I):
        err(f"страница {slug}: скрипт/iframe в содержимом")

# ---- redirects / review ---------------------------------------------------
red = read_csv(IMP / "redirects.csv")
for r in red:
    if r["target_type"] == "product_by_sku" and r["target"] not in imported:
        err(f"редирект {r['old_path']}: товара {r['target']} нет в импорте")
    if r["target_type"] == "product_category" and r["target"] not in cat_slugs:
        err(f"редирект {r['old_path']}: категории {r['target']} нет")
notes.append(f"редиректов: {len(red)}; строк в review.csv: {len(read_csv(IMP / 'review.csv'))}")

print("\n".join("· " + n for n in notes))
if errors:
    print(f"\nОШИБОК: {len(errors)}")
    print("\n".join("  ✗ " + e for e in errors[:60]))
    sys.exit(1)
print("\nОШИБОК НЕТ: файлы импорта согласованы с резервной копией")
