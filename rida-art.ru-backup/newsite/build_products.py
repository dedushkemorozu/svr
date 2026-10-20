# -*- coding: utf-8 -*-
"""Готовит JSON для WooCommerce REST API (/wc/v3/products/batch) из резервной копии.

Запуск: python -I -X utf8 newsite/build_products.py
Результат: newsite/out/products_batch_NN.json, newsite/out/variations.json
"""
import csv
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from product_copy import COPY, MATERIAL, SIZE, DRAFT, SKIP, EXTRA_CATS, FEATURED  # noqa: E402

OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)

CAT_SLUG = {
    'Новинки': 'new', 'Ангелы': 'angels', 'Домики': 'houses', 'Маяки': 'mayak',
    'Птицы': 'birds', 'Лошадки': 'horse', 'Грибы': 'mush', 'Наборы': 'nabory',
    'Весенняя и пасхальная коллекция': 'spring',
    'Пасхальные стеклянные яйца с росписью': 'easter-glass-eggs',
    'Пасхальные деревянные яйца с росписью': 'easter-wooden-eggs',
    'Пасхальные ангелы': 'easter-angels',
    'Пасхальные подвески': 'easter-pendants',
    'Пасхальные наборы': 'easter-sets',
}

TR = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
              ['a', 'b', 'v', 'g', 'd', 'e', 'e', 'zh', 'z', 'i', 'y', 'k', 'l', 'm', 'n', 'o', 'p',
               'r', 's', 't', 'u', 'f', 'h', 'ts', 'ch', 'sh', 'sch', '', 'y', '', 'e', 'yu', 'ya']))


def slugify(s):
    out = []
    for ch in s.lower():
        if ch in TR:
            out.append(TR[ch])
        elif ch.isascii() and ch.isalnum():
            out.append(ch)
        else:
            out.append('-')
    slug = '-'.join(p for p in ''.join(out).split('-') if p)
    return slug[:70].rstrip('-')


def main():
    data = json.load(open(os.path.join(ROOT, 'data', 'products.json'), encoding='utf-8'))
    prods = {p['id']: p for p in data['products']}
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'import-woocommerce', 'products_import.csv'),
                                    encoding='utf-8-sig')))
    parents = [r for r in rows if r['Type'] in ('simple', 'variable')]
    variations = [r for r in rows if r['Type'] == 'variation']

    cat_ids = json.load(open(os.path.join(OUT, 'category_ids.json'), encoding='utf-8'))
    used_slugs = set()
    items = []
    for r in parents:
        sku = r['SKU']
        if sku in SKIP:
            continue
        name, short, body = COPY[sku]
        p = prods[sku]
        slugs = []
        for c in [c.strip() for c in r['Categories'].split(',') if c.strip()]:
            leaf = c.split('>')[-1].strip()
            slugs.append(CAT_SLUG[leaf])
        slugs += EXTRA_CATS.get(sku, [])
        slugs = list(dict.fromkeys(slugs))

        # Фото: первым ставим «почти квадратное», чтобы карточки в сетке были ровными
        imgs = list(p['images'])

        def squareness(im):
            w, h = Image.open(os.path.join(ROOT, im['file'])).size
            return abs(1 - w / h)
        imgs.sort(key=squareness)
        if imgs and squareness(p['images'][0]) < 0.2:
            imgs = list(p['images'])
        # Общий текст про ручную роспись выводит шаблон карточки, здесь — только своё
        images = [{'src': im['url'], 'alt': name} for im in imgs]

        details = [f'<li>Материал: {MATERIAL.get(sku, "дерево")}, ручная роспись</li>']
        if sku in SIZE:
            details.append(f'<li>Высота: {SIZE[sku]}</li>')
        description = f'<p>{body}</p><ul>' + ''.join(details) + '</ul>'

        slug = slugify(name)
        while slug in used_slugs:
            slug += '-2'
        used_slugs.add(slug)

        item = {
            'name': name,
            'slug': slug,
            'type': r['Type'],
            'status': 'draft' if sku in DRAFT else 'publish',
            'featured': sku in FEATURED,
            'sku': sku,
            'short_description': f'<p>{short}</p>',
            'description': description,
            'categories': [{'id': cat_ids[s]} for s in slugs],
            'images': images,
        }
        if r['Type'] == 'simple':
            item['regular_price'] = r['Regular price']
            if r['Sale price']:
                item['sale_price'] = r['Sale price']
            if r['In stock?'] == '0':
                item['stock_status'] = 'outofstock'
            if r['Stock']:
                item['manage_stock'] = True
                item['stock_quantity'] = int(r['Stock'])
        else:
            opts = [o.strip() for o in r['Attribute 1 value(s)'].split(',')]
            item['attributes'] = [{'name': r['Attribute 1 name'], 'options': opts,
                                   'visible': True, 'variation': True}]
            item['default_attributes'] = [{'name': r['Attribute 1 name'], 'option': opts[0]}]
        items.append(item)

    # Порядок: сначала хиты и новинки
    for n in range(0, len(items), 8):
        json.dump({'create': items[n:n + 8]}, open(os.path.join(OUT, f'products_batch_{n // 8:02d}.json'), 'w',
                                                    encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    var = {}
    for r in variations:
        parent = r['Parent']
        v = {'sku': r['SKU'], 'regular_price': r['Regular price'],
             'attributes': [{'name': r['Attribute 1 name'], 'option': r['Attribute 1 value(s)']}]}
        if r['In stock?'] == '0':
            v['stock_status'] = 'outofstock'
        if r['Stock']:
            v['manage_stock'] = True
            v['stock_quantity'] = int(r['Stock'])
        var.setdefault(parent, []).append(v)
    json.dump(var, open(os.path.join(OUT, 'variations.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    print(len(items), 'products;', sum(len(v) for v in var.values()), 'variations')
    print('missing copy:', [r['SKU'] for r in parents if r['SKU'] not in COPY and r['SKU'] not in SKIP])


if __name__ == '__main__':
    main()
