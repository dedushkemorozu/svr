#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка пакета импорта WordPress + WooCommerce из резервной копии rida-art.ru.

Запуск (после backup.py):
    python -I -X utf8 build_woocommerce_import.py
    python -I -X utf8 build_woocommerce_import.py --site-url https://example.ru

Источники: data/products.json, data/catalogs.json, data/pages.json.
Результат:  import-woocommerce/ (CSV товаров, CSV категорий, XML страниц, картинки, редиректы, список вопросов).
Только стандартная библиотека Python.
"""
import argparse
import csv
import html
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\l1bot\rida-art.ru-backup")
OUT = ROOT / "import-woocommerce"

ap = argparse.ArgumentParser()
ap.add_argument("--site-url", default="https://rida-art.ru", help="адрес нового сайта (для ссылок на картинки)")
ap.add_argument("--images-base-url", default=None,
                help="адрес папки с картинками товаров на новом сайте "
                     "(по умолчанию <site-url>/wp-content/uploads/rida-import/products)")
args = ap.parse_args()
SITE = args.site_url.rstrip("/")
PRODUCT_IMG_BASE = (args.images_base_url or f"{SITE}/wp-content/uploads/rida-import/products").rstrip("/")
PAGE_IMG_BASE = f"{SITE}/wp-content/uploads/rida-import/pages"

PLACEHOLDERS = {"Краткое описание товара", "Полное описание товара"}
COLOR_RE = re.compile(r"(голуб|желт|бел|фиолет|фисташ|розов|лилов|зелен|зелён|бирюз|красн|син|оранж|сер|корич|черн|чёрн|беж)", re.I)

# (старая страница-каталог, название, новый slug, родитель)
CATS = [
    ("new", "Новинки", "new", None),
    ("angels", "Ангелы", "angels", None),
    ("houses", "Домики", "houses", None),
    ("mayak", "Маяки", "mayak", None),
    ("birds", "Птицы", "birds", None),
    ("horse", "Лошадки", "horse", None),
    ("mush", "Грибы", "mush", None),
    ("nabory", "Наборы", "nabory", None),
    ("spring", "Весенняя и пасхальная коллекция", "spring", None),
    ("page97", "Пасхальные стеклянные яйца с росписью", "easter-glass-eggs", "spring"),
    ("page98", "Пасхальные деревянные яйца с росписью", "easter-wooden-eggs", "spring"),
    ("page99", "Пасхальные ангелы", "easter-angels", "spring"),
    ("page100", "Пасхальные подвески", "easter-pendants", "spring"),
    ("page101", "Пасхальные наборы", "easter-sets", "spring"),
    ("new_year", "Новогодние подарки", "new-year", None),
]
CAT_BY_OLD = {c[0]: c for c in CATS}
CAT_BY_SLUG = {c[2]: c for c in CATS}

# (старый slug страницы, заголовок в WP, slug в WP, статус)
PAGES = [
    ("brand", "О нас", "brand", "publish"),
    ("korporativ", "Корпоративные подарки", "korporativ", "publish"),
    ("delivery-payment", "Доставка и оплата", "delivery-payment", "publish"),
    ("terms", "Оферта", "terms", "publish"),
    ("privacy-policy", "Политика конфиденциальности", "privacy-policy", "publish"),
    ("contacts", "Контакты", "contacts", "publish"),
    ("index", "Главная", "home", "draft"),
]

REVIEW = []   # строки для review.csv: id, название, тема, что сделано / что проверить


def review(id_, title, topic, note):
    REVIEW.append({"id": id_, "title": title, "topic": topic, "note": note})


def write_csv(path, header, rows, bom=False):
    with open(path, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def text_to_html(text):
    """Простой текст -> HTML: пустая строка = абзац, перевод строки = <br>."""
    text = (text or "").strip()
    if not text:
        return ""
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    return "\n".join("<p>" + html.escape(p.strip()).replace("\n", "<br>\n") + "</p>" for p in paras)


def cap(s):
    s = (s or "").strip()
    return s[:1].upper() + s[1:]


# ----------------------------------------------------------------------------
# Данные
# ----------------------------------------------------------------------------
pj = json.loads((ROOT / "data/products.json").read_text(encoding="utf-8"))
products = pj["products"]
params = {p["goodsId"]: p for p in pj["api_params"] if p["values"]}
catalogs = {c["page"]: c for c in json.loads((ROOT / "data/catalogs.json").read_text(encoding="utf-8"))["catalogs"]}
pages = {p["slug"]: p for p in json.loads((ROOT / "data/pages.json").read_text(encoding="utf-8"))["pages"]}

HAND_WRITTEN = {"README.md", "install_on_server.sh"}   # написаны вручную — при пересборке не трогаем
if OUT.exists():
    for item in OUT.iterdir():
        if item.name in HAND_WRITTEN:
            continue
        shutil.rmtree(item) if item.is_dir() else item.unlink()
(OUT / "uploads/rida-import/products").mkdir(parents=True)
(OUT / "uploads/rida-import/pages").mkdir(parents=True)

for old, name, slug, parent in CATS:   # названия категорий должны совпадать с заголовками старых каталогов
    h = (catalogs.get(old) or {}).get("heading")
    if h and h != name and old not in ("mush", "new_year"):
        print(f"! название каталога {old}: на сайте {h!r}, в пакете {name!r}")

# ----------------------------------------------------------------------------
# Товары
# ----------------------------------------------------------------------------
HEADER = ["ID", "Type", "SKU", "Name", "Published", "Is featured?", "Visibility in catalog", "Short description",
          "Description", "Date sale price starts", "Date sale price ends", "Tax status", "Tax class", "In stock?",
          "Stock", "Low stock amount", "Backorders allowed?", "Sold individually?", "Weight (kg)", "Length (cm)",
          "Width (cm)", "Height (cm)", "Allow customer reviews?", "Purchase note", "Sale price", "Regular price",
          "Categories", "Tags", "Shipping class", "Images", "Download limit", "Download expiry days", "Parent",
          "Grouped products", "Upsells", "Cross-sells", "External URL", "Button text", "Position",
          "Attribute 1 name", "Attribute 1 value(s)", "Attribute 1 visible", "Attribute 1 global",
          "Attribute 1 default", "Meta: _rida_old_url"]


def row(**kw):
    unknown = set(kw) - set(HEADER)
    assert not unknown, unknown
    return [kw.get(h, "") for h in HEADER]


def cat_path(old_slug):
    c = CAT_BY_OLD[old_slug]
    return f"{CAT_BY_SLUG[c[3]][1]} > {c[1]}" if c[3] else c[1]


def stock_fields(qty):
    """Остаток из конструктора -> (В наличии?, Количество)."""
    if qty is None or qty == "":
        return 1, ""
    n = int(qty)
    return (1 if n > 0 else 0), n


rows_cdn, rows_local = [], []
excluded, drafted, assigned_counts = [], [], {}
img_copied = 0

for p in products:
    sku, title = p["id"], p["title"].strip()
    imgs = p["images"]
    # тестовые товары: 1 ₽, без фото, без описания, ни в одном каталоге
    if (p["price"] or 0) <= 1 and not imgs and not p["description"]:
        excluded.append(p)
        review(sku, title, "не импортирован", "тестовый товар (цена 1 ₽, без фото и описания, нет в каталогах)")
        continue

    short_txt = "" if p["description"] in PLACEHOLDERS else p["description"]
    short_html = "" if p["description"] in PLACEHOLDERS else p["description_html"].strip()
    if p["description"] in PLACEHOLDERS:
        review(sku, title, "описание", "в конструкторе стояла заглушка «Краткое описание товара» — не импортирована")
    full = (p["api_description_full"] or "").strip()
    if full in PLACEHOLDERS or full == short_txt.strip():
        full = ""
    # «полное описание» из конструктора иногда просто повторяет название — такое не переносим
    if full and (full.lower() in title.lower() or full.lower() in short_txt.lower()):
        full = ""
    long_html = text_to_html(full)
    if full and not short_txt:
        review(sku, title, "описание", f"«полное описание» из конструктора ({full!r}) на сайте не показывалось; "
                                        "импортировано в поле Description")
    elif full:
        review(sku, title, "описание", f"«полное описание» из конструктора ({full!r}) на сайте не показывалось; "
                                        "импортировано в поле Description, краткое — в Short description")

    cats = [cat_path(x["slug"]) for x in p["listed_on"] if x["slug"] in CAT_BY_OLD]
    for x in p["listed_on"]:
        if x["slug"] not in CAT_BY_OLD:
            review(sku, title, "категория", f"каталог {x['slug']} не сопоставлен с категорией")
    published = 1
    if not cats:
        published = -1
        drafted.append(p)
        review(sku, title, "черновик", "товар открывался только по прямой ссылке (не входил ни в один каталог) — "
                                       "импортирован как ЧЕРНОВИК без категории; проверьте и опубликуйте")
    for c in cats:
        assigned_counts[c] = assigned_counts.get(c, 0) + 1

    # картинки: основной файл с карточки; копия с понятным именем для варианта «загрузить на свой сервер»
    cdn_urls, local_urls = [], []
    for n, im in enumerate(imgs, 1):
        src = ROOT / im["file"]
        ext = src.suffix.lower()
        name = f"{sku}-{n}{ext}"
        shutil.copy2(src, OUT / "uploads/rida-import/products" / name)
        img_copied += 1
        cdn_urls.append(im["url"])
        local_urls.append(f"{PRODUCT_IMG_BASE}/{name}")

    old_price, price = p["price_old"], p["price"]
    regular, sale = (old_price, price) if old_price else (price, "")
    in_stock, stock = stock_fields(p["quantity"])
    if p["quantity"] == "0":
        review(sku, title, "остаток", "остаток в конструкторе = 0 → в WooCommerce «нет в наличии»")

    variants = p["variants"]
    common = dict(SKU=sku, Name=title, Published=published, **{"Is featured?": 0, "Visibility in catalog": "visible",
                  "Short description": short_html, "Description": long_html, "Allow customer reviews?": 1,
                  "Categories": ", ".join(cats), "Meta: _rida_old_url": f"/product-{sku}"})
    if not variants:
        r = dict(common, Type="simple", **{"In stock?": in_stock, "Stock": stock, "Backorders allowed?": 0,
                 "Sold individually?": 0, "Regular price": regular, "Sale price": sale})
        rows_cdn.append(row(**dict(r, Images=", ".join(cdn_urls))))
        rows_local.append(row(**dict(r, Images=", ".join(local_urls))))
        continue

    # вариативный товар
    prm = params.get(sku)
    if not prm:
        review(sku, title, "варианты", "есть варианты, но нет описания параметра — импортирован без вариантов")
        r = dict(common, Type="simple", **{"In stock?": in_stock, "Stock": stock, "Regular price": regular})
        rows_cdn.append(row(**dict(r, Images=", ".join(cdn_urls))))
        rows_local.append(row(**dict(r, Images=", ".join(local_urls))))
        continue
    vals = {v["id"]: cap(v["title"]) for v in prm["values"]}
    is_color = all(COLOR_RE.search(v) for v in vals.values())
    attr_name = "Цвет" if is_color else cap(prm["title"])
    if attr_name != prm["title"]:
        review(sku, title, "варианты", f"параметр «{prm['title']}» переименован в «{attr_name}»")
    parent = dict(common, Type="variable", **{"In stock?": 1, "Attribute 1 name": attr_name,
                  "Attribute 1 value(s)": ", ".join(vals.values()), "Attribute 1 visible": 1, "Attribute 1 global": 0})
    rows_cdn.append(row(**dict(parent, Images=", ".join(cdn_urls))))
    rows_local.append(row(**dict(parent, Images=", ".join(local_urls))))
    for v in sorted(variants, key=lambda x: x["paramsInfo"][0]["valueId"]):
        vid = v["paramsInfo"][0]["valueId"]
        vin, vstock = stock_fields(v["quantity"])
        vreg, vsale = (v["priceOld"], v["price"]) if v["priceOld"] else (v["price"], "")
        vr = row(Type="variation", SKU=v["id"], Name=f"{title} - {vals[vid]}", Published=1,
                 **{"Visibility in catalog": "visible", "In stock?": vin, "Stock": vstock, "Backorders allowed?": 0,
                    "Regular price": vreg, "Sale price": vsale, "Parent": sku, "Attribute 1 name": attr_name,
                    "Attribute 1 value(s)": vals[vid], "Attribute 1 visible": 1, "Attribute 1 global": 0,
                    "Description": text_to_html(v["description"]), "Meta: _rida_old_url": f"/product-{sku}"})
        rows_cdn.append(vr)
        rows_local.append(vr)

write_csv(OUT / "products_import.csv", HEADER, rows_cdn)
write_csv(OUT / "products_import_local-images.csv", HEADER, rows_local)

# повторяющиеся названия — возможно, это один товар в разных вариантах
by_title = {}
for p in products:
    by_title.setdefault(p["title"].strip(), []).append(p["id"])
for t, ids in by_title.items():
    if len(ids) > 1 and not any(i in {e["id"] for e in excluded} for i in ids):
        review(", ".join(ids), t, "дубли названий", f"{len(ids)} товаров с одинаковым названием — возможно, это "
                                                    "варианты одного изделия (цвет/размер); при желании объедините в вариативный товар")
no_desc = [p["id"] for p in products if p not in excluded and not (p["description"] and p["description"] not in PLACEHOLDERS)
           and not (p["api_description_full"] and p["api_description_full"] not in PLACEHOLDERS)]
review(", ".join(no_desc), "(" + str(len(no_desc)) + " товаров)", "нет описания", "описаний нет ни в кратком, ни в полном поле — "
       "нужно написать (важно для SEO)")

# ----------------------------------------------------------------------------
# Категории
# ----------------------------------------------------------------------------
write_csv(OUT / "categories.csv", ["name", "slug", "parent_slug", "old_url", "products_imported"],
          [[name, slug, parent or "", f"/{old}", sum(v for k, v in assigned_counts.items() if k.split(" > ")[-1] == name)]
           for old, name, slug, parent in CATS])
sh = ["#!/usr/bin/env bash",
      "# Создаёт категории WooCommerce с нужными адресами (slug). Запустить ОДИН раз из папки сайта ДО импорта товаров:",
      "#   cd /путь/к/wordpress && bash create_categories.sh",
      "set -e"]
for old, name, slug, parent in CATS:
    if not parent:
        sh.append(f'wp term create product_cat "{name}" --slug={slug}')
sh.append('SPRING=$(wp term list product_cat --slug=spring --field=term_id)')
for old, name, slug, parent in CATS:
    if parent:
        sh.append(f'wp term create product_cat "{name}" --slug={slug} --parent="$SPRING"')
(OUT / "create_categories.sh").write_text("\n".join(sh) + "\n", encoding="utf-8", newline="\n")

# ----------------------------------------------------------------------------
# Страницы (WXR для Инструменты → Импорт → WordPress)
# ----------------------------------------------------------------------------
HEAD_RE = re.compile(r"<h([1-6])>(.*?)</h\1>", re.S)
OLD_CAT_PATHS = {f"/{old}": f"/product-category/{slug}/" for old, _, slug, _ in CATS}


def cdata(s):
    return "<![CDATA[" + s.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def page_content(slug, wp_title):
    out, copied = [], []
    for sec in pages[slug]["sections"]:
        h = sec["html"]
        seen = set()

        def drop_dups(m):
            key = (m.group(1), re.sub(r"\s+", " ", m.group(2)).strip())
            if key in seen:
                return ""
            seen.add(key)
            return m.group(0)
        h = HEAD_RE.sub(drop_dups, h)
        # заголовок, повторяющий заголовок страницы, тема WordPress выводит сама
        m = HEAD_RE.search(h)
        if m and m.group(1) == "2" and re.sub(r"\s+", " ", m.group(2)).strip() in (wp_title, pages[slug]["title"]) and slug != "index":
            h = h.replace(m.group(0), "", 1)
        if slug == "index":
            h = h.replace("<h1>", "<h2>").replace("</h1>", "</h2>")

        def img(m):
            url = html.unescape(m.group(1))
            f = ROOT / ("assets/" + re.sub(r"^https?://", "", url))
            if not f.exists():
                review(slug, wp_title, "страница", f"картинка не найдена: {url}")
                return m.group(0)
            name = f.name
            shutil.copy2(f, OUT / "uploads/rida-import/pages" / name)
            copied.append(name)
            return f'<img src="{PAGE_IMG_BASE}/{name}" alt="{html.escape(wp_title)}">'
        h = re.sub(r'<img src="([^"]+)" alt="[^"]*">', img, h)

        def link(m):
            href = m.group(1)
            path = re.sub(r"^https?://(www\.)?rida-art\.ru", "", href) or "/"
            return f'<a href="{OLD_CAT_PATHS.get(path.rstrip("/"), href)}">'
        h = re.sub(r'<a href="([^"]*)">', link, h)
        out.append(re.sub(r"\n{3,}", "\n\n", h).strip())
    return "\n\n".join(x for x in out if x)


now = datetime.now()
items = []
for n, (old, wp_title, wp_slug, status) in enumerate(PAGES, 1):
    content = page_content(old, wp_title)
    txt = pages[old]["text"]
    if re.search(r"\(наименование организации\)|\(название компании\)|Название организации, ИП", txt):
        review(old, wp_title, "юридический текст", "в тексте остались НЕЗАПОЛНЕННЫЕ места шаблона "
               "(«(наименование организации)», «Название организации, ИП:» и т. п.) — заполните реквизиты продавца до публикации")
    if status == "draft":
        review(old, wp_title, "страница", "главная импортирована как ЧЕРНОВИК-заготовка (текст «О мастерской» и контакты); "
               "оформление зависит от темы — соберите главную в редакторе")
    items.append(f"""<item>
<title>{html.escape(wp_title)}</title>
<link>{SITE}/{wp_slug}/</link>
<pubDate>{now:%a, %d %b %Y %H:%M:%S} +0000</pubDate>
<dc:creator>{cdata('admin')}</dc:creator>
<guid isPermaLink="false">{SITE}/?page_id={9000 + n}</guid>
<description></description>
<content:encoded>{cdata(content)}</content:encoded>
<excerpt:encoded>{cdata('')}</excerpt:encoded>
<wp:post_id>{9000 + n}</wp:post_id>
<wp:post_date>{cdata(now.strftime('%Y-%m-%d %H:%M:%S'))}</wp:post_date>
<wp:post_date_gmt>{cdata(now.strftime('%Y-%m-%d %H:%M:%S'))}</wp:post_date_gmt>
<wp:comment_status>{cdata('closed')}</wp:comment_status>
<wp:ping_status>{cdata('closed')}</wp:ping_status>
<wp:post_name>{cdata(wp_slug)}</wp:post_name>
<wp:status>{cdata(status)}</wp:status>
<wp:post_parent>0</wp:post_parent>
<wp:menu_order>0</wp:menu_order>
<wp:post_type>{cdata('page')}</wp:post_type>
<wp:post_password>{cdata('')}</wp:post_password>
<wp:is_sticky>0</wp:is_sticky>
</item>""")
wxr = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:wfw="http://wellformedweb.org/CommentAPI/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:wp="http://wordpress.org/export/1.2/">
<channel>
<title>Рида Арт</title>
<link>{SITE}</link>
<description>Мастерская сказочных игрушек</description>
<pubDate>{now:%a, %d %b %Y %H:%M:%S} +0000</pubDate>
<language>ru-RU</language>
<wp:wxr_version>1.2</wp:wxr_version>
<wp:base_site_url>{SITE}</wp:base_site_url>
<wp:base_blog_url>{SITE}</wp:base_blog_url>
{chr(10).join(items)}
</channel>
</rss>
"""
(OUT / "pages_import.xml").write_text(wxr, encoding="utf-8")

# противоречия в контактах
c_home = pages["index"]["text"]
c_page = pages["contacts"]["text"]
if "10:00—18:00" in c_home and "10:00—19:00" in c_page:
    review("contacts / index", "Контакты", "противоречие", "часы работы: на главной «Пн—Пт 10:00—18:00», на странице "
           "«Контакты» «Пн—Пт 10:00—19:00» — уточните и исправьте")

# ----------------------------------------------------------------------------
# Редиректы и список вопросов
# ----------------------------------------------------------------------------
ex_ids = {e["id"] for e in excluded}
red = []
for p in products:
    red.append([f"/product-{p['id']}", "gone" if p["id"] in ex_ids else "product_by_sku", "" if p["id"] in ex_ids else p["id"],
                "тестовый товар не импортирован" if p["id"] in ex_ids else ""])
for old, name, slug, parent in CATS:
    red.append([f"/{old}", "product_category", slug, ""])
red += [["/catalog_main", "shop", "", "страница-список разделов; заменяется магазином"],
        ["/returns", "page", "returns", "в старом сайте страницы не было (404) — создать «Обмен и возврат»"],
        ["/action", "gone", "", "на старом сайте файл из нулей — страница пустая"]]
write_csv(OUT / "redirects.csv", ["old_path", "target_type", "target", "note"], red)
write_csv(OUT / "review.csv", ["id", "title", "topic", "note"], [[r["id"], r["title"], r["topic"], r["note"]] for r in REVIEW])

print(f"Товаров в CSV: {len([r for r in rows_cdn if r[HEADER.index('Type')] != 'variation'])} "
      f"(+{len([r for r in rows_cdn if r[HEADER.index('Type')] == 'variation'])} вариаций); исключено {len(excluded)}; "
      f"черновиков {len(drafted)}; картинок скопировано {img_copied}; страниц {len(PAGES)}; вопросов в review: {len(REVIEW)}")
