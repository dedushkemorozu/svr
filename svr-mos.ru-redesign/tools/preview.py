#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preview.py — превью страниц WordPress 7.1.3 + Twenty Twenty-Five БЕЗ WordPress.

Собирает из файлов дизайн-системы (global-styles.json, header.html, footer.html,
page.html, page-no-title.html) и блочной разметки контента страницы HTML,
максимально близкий к тому, что отдаст WordPress, снимает скриншоты (Playwright)
и пишет отчёт о проблемах.

  python3 tools/preview.py --content page.html --template page --title "Заголовок" --out tmp/x/page
      → page.html, page-desktop.png (1440×900, full page), page-mobile.png (390×844, full page),
        page-report.json

Что портировано из ядра WP 7.1.3 (см. README.md рядом):
  * парсер блоков (WP_Block_Parser) и рендер дерева блоков;
  * layout support: is-layout-*, has-global-padding, is-content-justification-*, is-vertical, is-nowrap,
    wp-container-<block>-is-layout-<hash> c тем же хэшем, что считает WP (wp_unique_id_from_values),
    wp-container-content-* (дочерние размеры), CSS как wp_get_layout_style();
  * global styles: WP_Theme_JSON::get_stylesheet() — переменные пресетов, fluid typography (clamp как WP),
    root layout rules, body, элементы (+ :hover/:focus), стили блоков (только для блоков на странице,
    как wp_add_global_styles_for_blocks — ПОСЛЕ styles.css!), классы пресетов, styles.css;
    стили вариаций блоков (is-style-*--N) как block-style-variations.php;
  * block supports у динамических блоков (colors, typography, spacing, border, dimensions, shadow,
    align, className, anchor, aria-label), elements (wp-elements-*), position sticky, background image,
    fluid font-size в inline style, block visibility;
  * динамические блоки: template-part, post-title, post-content, site-logo, site-title, site-tagline,
    navigation (+ navigation-link/submenu, page-list fallback, оверлей и кнопка-гамбургер), image
    (+ lightbox), gallery, heading/list/paragraph (служебные классы), button;
  * wptexturize (упрощённо), wp_filter_content_tags (width/height/decoding/loading), skip-link.
Данные ядра (theme.json default+blocks+TT5, метаданные блоков, CSS блоков, шрифты TT5) лежат в
tools/wp-data/ и сняты с локальной копии WP 7.1.3 скриптом tools/wp_dump_data.php.
"""
import argparse
import copy
import hashlib
import html as htmllib
import json
import math
import re
import sys
import time
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REDESIGN = TOOLS.parent
SCRATCH = REDESIGN.parent
DATA = TOOLS / 'wp-data'
ASSETS = SCRATCH / 'preview-assets'
MEDIA_JSON = SCRATCH / 'media.json'
DEFAULT_SYSTEM = REDESIGN / 'system'
CACHE = REDESIGN / 'tmp' / 'preview-cache'
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
HOME_URL = 'https://svr-mos.ru'
UPLOADS_RE = re.compile(r'''(?:https?:)?//svr-mos\.ru/wp-content/uploads/[^\s"'()<>,&\\]+''')

# Страницы сайта из брифа (id → slug, заголовок). Нужны для core/page-list и проверки ссылок меню.
SITE_PAGES = {
    49: ('', 'Главная'), 50: ('obj', 'Наши объекты'), 51: ('elteza', 'ОАО «Элтеза»'),
    52: ('russkii', 'ОАО «Мясокомбинат «Рузский»'), 53: ('os3-marino', 'ОС3 Марьино-Саларьево (II этап)'),
    54: ('os2-marino', 'ОС2 Марьино-Саларьево (II этап)'), 55: ('prod', 'Наша продукция'),
    56: ('docs', 'Документы'), 57: ('rekvizit', 'Реквизиты компании'), 58: ('contact', 'Контакты'),
}

# Переводы ru_RU для строк, которые WP выводит на фронтенде.
T = {
    'Skip to content': 'Перейти к содержимому',
    'Open menu': 'Открыть меню',
    'Close menu': 'Закрыть меню',
    'Menu': 'Меню',
    'Close': 'Закрыть',
    'Enlarged images': 'Увеличенные изображения',
    'Previous': 'Предыдущее',
    'Next': 'Следующее',
    '%s submenu': 'Подменю %s',
}


# ─────────────────────────────────────────────────────────────────────────────
# PHP-совместимые утилиты
# ─────────────────────────────────────────────────────────────────────────────

def php_round(x, n=0):
    q = Decimal(1).scaleb(-n)
    return float(Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP))


def php_num(x):
    """Число → строка так, как это делает PHP 8 при конкатенации."""
    if isinstance(x, bool):
        return '1' if x else ''
    if isinstance(x, int):
        return str(x)
    x = float(x)
    if x.is_integer():
        return str(int(x))
    s = repr(x)
    if 'e' in s or 'E' in s:
        s = ('%.12f' % x).rstrip('0').rstrip('.')
    return s


def php_empty(v):
    return v is None or v is False or v == '' or v == 0 and not isinstance(v, str) or v == '0' or v == [] or v == {}


def php_is_numeric(v):
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return True
    return isinstance(v, str) and re.fullmatch(r'\s*[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?\s*', v) is not None


_KEBAB_RE = re.compile(r'[A-Z]+(?![a-z])|[A-Z]?[a-z\u00df-\u00f6\u00f8-\u00ff]+|\d+')


def kebab(s):
    """_wp_to_kebab_case (lodash kebabCase) — достаточно точная копия для слагов пресетов."""
    return '-'.join(_KEBAB_RE.findall(str(s).replace("'", ''))).lower()


def wp_json_encode(data):
    """json_encode() PHP с флагами по умолчанию (экранирует / и не-ASCII)."""
    return json.dumps(data, separators=(',', ':'), ensure_ascii=True).replace('/', '\\/')


def wp_unique_id_from_values(data, prefix=''):
    return prefix + hashlib.md5(wp_json_encode(data).encode()).hexdigest()[:8]


def get_path(d, path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        elif isinstance(cur, list) and isinstance(p, int) and 0 <= p < len(cur):
            cur = cur[p]
        else:
            return default
    return cur


def set_path(d, path, value):
    cur = d
    for p in path[:-1]:
        if not isinstance(cur.get(p), dict):
            cur[p] = {}
        cur = cur[p]
    cur[path[-1]] = value


def array_replace_recursive(base, inc):
    if isinstance(base, dict) and isinstance(inc, dict):
        out = dict(base)
        for k, v in inc.items():
            out[k] = array_replace_recursive(base[k], v) if k in base else copy.deepcopy(v)
        return out
    if isinstance(base, list) and isinstance(inc, list):
        out = list(base)
        for i, v in enumerate(inc):
            if i < len(out):
                out[i] = array_replace_recursive(out[i], v)
            else:
                out.append(copy.deepcopy(v))
        return out
    return copy.deepcopy(inc)


def esc_attr(v):
    v = str(v)
    v = re.sub(r'&(?!(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]*);)', '&amp;', v)
    return v.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;').replace("'", '&#039;')


def esc_attr_html5(v):
    """Экранирование значения так, как это делает WP_HTML_Tag_Processor::set_attribute()."""
    return htmllib.escape(str(v), quote=True).replace('&#x27;', '&apos;')


def esc_html(v):
    v = str(v)
    v = re.sub(r'&(?!(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]*);)', '&amp;', v)
    return v.replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#039;')


def convert_custom_properties(value):
    """'var:preset|color|x' → 'var(--wp--preset--color--x)' (WP_Theme_JSON::convert_custom_properties)."""
    if isinstance(value, str) and value.startswith('var:'):
        return 'var(--wp--' + value[4:].replace('|', '--') + ')'
    return value


def resolve_custom_css_format(tree):
    if isinstance(tree, dict):
        return {k: resolve_custom_css_format(v) for k, v in tree.items()}
    if isinstance(tree, list):
        return [resolve_custom_css_format(v) for v in tree]
    return convert_custom_properties(tree)


# ─────────────────────────────────────────────────────────────────────────────
# Мини-аналог WP_HTML_Tag_Processor
# ─────────────────────────────────────────────────────────────────────────────

_TAG_RE = re.compile(
    r'<(/)?([a-zA-Z][a-zA-Z0-9:._-]*)((?:\s+[^\s"\'>/=]+(?:\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s"\'=<>`]+))?)*)\s*(/)?>',
    re.S)
_ATTR_RE = re.compile(r'([^\s"\'>/=]+)(?:\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s"\'=<>`]+)))?', re.S)
RAW_TEXT = {'script', 'style', 'textarea', 'title'}
VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}


class Tag:
    __slots__ = ('start', 'end', 'name', 'closer', 'attr_start', 'attr_end', 'self_closing')

    def __init__(self, m):
        self.start, self.end = m.start(), m.end()
        self.closer = bool(m.group(1))
        self.name = m.group(2).lower()
        self.attr_start, self.attr_end = m.start(3), m.end(3)
        self.self_closing = bool(m.group(4))


def iter_tags(s, pos=0):
    n = len(s)
    i = pos
    while i < n:
        j = s.find('<', i)
        if j < 0:
            return
        if s.startswith('<!--', j):
            k = s.find('-->', j + 4)
            i = n if k < 0 else k + 3
            continue
        if s.startswith('<![CDATA[', j):
            k = s.find(']]>', j)
            i = n if k < 0 else k + 3
            continue
        if s.startswith('<!', j) or s.startswith('<?', j):
            k = s.find('>', j)
            i = n if k < 0 else k + 1
            continue
        m = _TAG_RE.match(s, j)
        if not m:
            i = j + 1
            continue
        t = Tag(m)
        yield t
        i = m.end()
        if not t.closer and t.name in RAW_TEXT:
            k = re.compile(r'</%s\s*>' % t.name, re.I).search(s, i)
            i = k.start() if k else n


def tag_attrs(s, t):
    src = s[t.attr_start:t.attr_end]
    out = []
    for m in _ATTR_RE.finditer(src):
        val = None
        for g in (2, 3, 4):
            if m.group(g) is not None:
                val = m.group(g)
                break
        out.append((m.group(1).lower(), val, t.attr_start + m.start(), t.attr_start + m.end()))
    return out


def get_attr(s, t, name):
    for n, v, _, _ in tag_attrs(s, t):
        if n == name:
            return htmllib.unescape(v) if v is not None else True
    return None


def set_attrs(s, t, updates):
    """Меняет/добавляет/удаляет (None) атрибуты тега t, возвращает новую строку."""
    attrs = tag_attrs(s, t)
    src = s[t.attr_start:t.attr_end]
    base = t.attr_start
    pieces = []
    for name, value in updates.items():
        found = [a for a in attrs if a[0] == name]
        if found:
            _, _, a, b = found[0]
            pieces.append((a - base, b - base, '' if value is None else '%s="%s"' % (name, esc_attr_html5(value))))
        elif value is not None:
            pieces.append((len(src), len(src), ' %s="%s"' % (name, esc_attr_html5(value))))
    for a, b, rep in sorted(pieces, key=lambda p: -p[0]):
        if rep == '' and a > 0 and src[a - 1:a].isspace():
            a -= 1
        src = src[:a] + rep + src[b:]
    return s[:t.attr_start] + src + s[t.attr_end:]


def tag_classes(s, t):
    c = get_attr(s, t, 'class')
    return c.split() if isinstance(c, str) else []


def add_classes(s, t, classes):
    cur = get_attr(s, t, 'class')
    cur_list = cur.split() if isinstance(cur, str) else []
    new = [c for c in classes if c and c not in cur_list]
    if not new:
        return s
    value = (cur.strip() + ' ' if isinstance(cur, str) and cur.strip() else '') + ' '.join(new)
    return set_attrs(s, t, {'class': value})


def first_tag(s, name=None, cls=None, start=0):
    for t in iter_tags(s, start):
        if t.closer:
            continue
        if name and t.name != name:
            continue
        if cls and cls not in tag_classes(s, t):
            continue
        return t
    return None


def add_class_first(s, classes, name=None):
    t = first_tag(s, name)
    return add_classes(s, t, classes) if t else s


def append_style_first(s, css):
    t = first_tag(s)
    if not t:
        return s
    st = get_attr(s, t, 'style')
    if isinstance(st, str) and st.strip():
        css = st + ('' if st.rstrip().endswith(';') else ';') + css
    return set_attrs(s, t, {'style': css})


# ─────────────────────────────────────────────────────────────────────────────
# Медиатека
# ─────────────────────────────────────────────────────────────────────────────

class Media:
    def __init__(self, path):
        self.items = json.loads(Path(path).read_text(encoding='utf-8')) if Path(path).exists() else []
        self.by_id = {m['id']: m for m in self.items}
        self.by_url = {m['url']: m for m in self.items}
        self.missing = set()

    @staticmethod
    def _norm(url):
        u = url.split('#')[0].split('?')[0]
        return re.sub(r'^(https?:)?//', 'https://', u)

    def resolve(self, url):
        """→ (запись медиатеки, (w, h) производного размера или None)."""
        u = self._norm(url)
        if u in self.by_url:
            return self.by_url[u], None
        m = re.match(r'^(.*?)-(\d+)x(\d+)(\.[A-Za-z0-9]+)$', u)
        if m and (m.group(1) + m.group(4)) in self.by_url:
            return self.by_url[m.group(1) + m.group(4)], (int(m.group(2)), int(m.group(3)))
        m = re.match(r'^(.*?)-(?:scaled|rotated)(\.[A-Za-z0-9]+)$', u)
        if m and (m.group(1) + m.group(2)) in self.by_url:
            return self.by_url[m.group(1) + m.group(2)], None
        return None, None

    def dims(self, url, attachment_id=None):
        entry, size = self.resolve(url)
        if entry is None and attachment_id in self.by_id:
            entry = self.by_id[attachment_id]
        if entry is None:
            return None
        if size:
            return size
        if entry.get('w') and entry.get('h'):
            return entry['w'], entry['h']
        return None

    def local_uri(self, entry):
        p = Path(entry['local'])
        return p.as_uri() if p.exists() else None

    def subsizes(self, entry):
        """Промежуточные размеры, которые WP сгенерировал бы при загрузке (в порядке метаданных)."""
        ow, oh = entry.get('w') or 0, entry.get('h') or 0
        out = []
        if not ow or not oh:
            return out
        base, ext = entry['url'].rsplit('.', 1)
        for name, dw, dh, crop in WP_IMAGE_SIZES:
            d = image_resize_dimensions(ow, oh, dw, dh, crop)
            if d:
                nw, nh, sx, sy, cw, ch = d
                out.append({'name': name, 'width': nw, 'height': nh, 'crop': (sx, sy, cw, ch),
                            'url': '%s-%dx%d.%s' % (base, nw, nh, ext)})
        return out

    def derived_uri(self, entry, size):
        """Локальная копия производного размера (генерируется Pillow в tmp/preview-cache)."""
        src = Path(entry['local'])
        if not src.exists():
            return None
        w, h = size
        spec = next((s for s in self.subsizes(entry) if s['width'] == w and s['height'] == h), None)
        name = Path(entry['url']).stem + '-%dx%d' % (w, h) + Path(entry['url']).suffix.lower()
        dst = CACHE / name
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            try:
                from PIL import Image
                CACHE.mkdir(parents=True, exist_ok=True)
                im = Image.open(src)
                ow, oh = im.size
                if spec:
                    sx, sy, cw, ch = spec['crop']
                    if (entry.get('w'), entry.get('h')) != (ow, oh) and entry.get('w'):
                        k = ow / float(entry['w'])
                        sx, sy, cw, ch = sx * k, sy * k, cw * k, ch * k
                else:
                    r = w / float(h)
                    if ow / float(oh) > r:
                        cw, ch = oh * r, oh
                    else:
                        cw, ch = ow, ow / r
                    sx, sy = (ow - cw) / 2, (oh - ch) / 2
                im = im.crop((int(sx), int(sy), int(sx + cw), int(sy + ch))).resize((w, h), Image.LANCZOS)
                if dst.suffix in ('.jpg', '.jpeg'):
                    im.convert('RGB').save(dst, quality=82)
                else:
                    im.save(dst)
            except Exception as e:  # noqa
                self.missing.add('%s (не удалось сделать размер %dx%d: %s)' % (entry['url'], w, h, e))
                return self.local_uri(entry)
        return dst.as_uri()

    def meta_sizes(self, entry):
        """Список размеров для srcset: подразмеры + оригинал (как wp_calculate_image_srcset)."""
        sizes = [{'width': s['width'], 'height': s['height'], 'url': s['url']} for s in self.subsizes(entry)]
        sizes.append({'width': entry.get('w'), 'height': entry.get('h'), 'url': entry['url']})
        return sizes

    def srcset(self, entry, src, size_array):
        iw, ih = int(size_array[0]), int(size_array[1])
        if iw < 1 or not entry.get('w'):
            return None
        src = self._norm(src)
        sources = {}
        order = []
        matched = False
        for im in self.meta_sizes(entry):
            is_src = False
            if not matched and src.endswith('/' + im['url'].rsplit('/', 1)[-1]):
                matched = is_src = True
            if im['width'] > 2048 and not is_src:
                continue
            if image_matches_ratio(iw, ih, im['width'], im['height']):
                if im['width'] in sources:
                    order.remove(im['width'])
                sources[im['width']] = im['url']
                if is_src:
                    order.insert(0, im['width'])
                else:
                    order.append(im['width'])
        if not matched or len(sources) < 2:
            return None
        return ', '.join('%s %dw' % (sources[w].replace(' ', '%20'), w) for w in order)

    def replace_urls(self, text):
        def rep(mo):
            url = mo.group(0)
            entry, size = self.resolve(url)
            if entry:
                uri = self.derived_uri(entry, size) if size else self.local_uri(entry)
                if uri:
                    return uri
            self.missing.add(url)
            return url
        return UPLOADS_RE.sub(rep, text)


WP_IMAGE_SIZES = [('thumbnail', 150, 150, True), ('medium', 300, 300, False), ('medium_large', 768, 0, False),
                  ('large', 1024, 1024, False), ('1536x1536', 1536, 1536, False), ('2048x2048', 2048, 2048, False)]


def wp_constrain_dimensions(cw, ch, mw=0, mh=0):
    if not mw and not mh:
        return cw, ch
    wr = hr = 1.0
    did_w = did_h = False
    if mw > 0 and cw > 0 and cw > mw:
        wr, did_w = mw / float(cw), True
    if mh > 0 and ch > 0 and ch > mh:
        hr, did_h = mh / float(ch), True
    smaller, larger = min(wr, hr), max(wr, hr)
    ratio = smaller if (int(php_round(cw * larger)) > mw or int(php_round(ch * larger)) > mh) else larger
    w = max(1, int(php_round(cw * ratio)))
    h = max(1, int(php_round(ch * ratio)))
    if did_w and w == mw - 1:
        w = mw
    if did_h and h == mh - 1:
        h = mh
    return w, h


def image_resize_dimensions(ow, oh, dw, dh, crop):
    if ow <= 0 or oh <= 0 or (dw <= 0 and dh <= 0):
        return None
    if not dh:
        if ow < dw:
            return None
    elif not dw:
        if oh < dh:
            return None
    elif ow < dw and oh < dh:
        return None
    if crop:
        ar = ow / float(oh)
        nw, nh = min(dw, ow), min(dh, oh)
        if not nw:
            nw = int(php_round(nh * ar))
        if not nh:
            nh = int(php_round(nw / ar))
        sr = max(nw / float(ow), nh / float(oh))
        cw, ch = php_round(nw / sr), php_round(nh / sr)
        sx, sy = math.floor((ow - cw) / 2), math.floor((oh - ch) / 2)
    else:
        cw, ch, sx, sy = ow, oh, 0, 0
        nw, nh = wp_constrain_dimensions(ow, oh, dw, dh)
    if abs(nw - ow) <= 1 and abs(nh - oh) <= 1:
        return None
    return int(nw), int(nh), int(sx), int(sy), int(cw), int(ch)


def image_matches_ratio(sw, sh, tw, th):
    if sw > tw:
        c = wp_constrain_dimensions(sw, sh, tw)
        e = (tw, th)
    else:
        c = wp_constrain_dimensions(tw, th, sw)
        e = (sw, sh)
    return abs(c[0] - e[0]) <= 1 and abs(c[1] - e[1]) <= 1


# ─────────────────────────────────────────────────────────────────────────────
# Fluid typography (block-supports/typography.php)
# ─────────────────────────────────────────────────────────────────────────────

def typography_value_and_unit(raw, coerce_to='', root=16):
    if raw is None or isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
        return None
    if php_empty(raw):
        return None
    if isinstance(raw, (int, float)) or php_is_numeric(raw):
        raw = php_num(float(raw)) + 'px'
    m = re.fullmatch(r'(\d*\.?\d+)([a-zA-Z]+|%)', raw)
    if not m:
        return None
    value, unit = float(m.group(1)), m.group(2)
    if unit not in ('rem', 'px', 'em'):
        return None
    if coerce_to == 'px' and unit in ('em', 'rem'):
        value *= root
        unit = coerce_to
    if unit == 'px' and coerce_to in ('em', 'rem'):
        value /= root
        unit = coerce_to
    if coerce_to in ('em', 'rem') and unit in ('em', 'rem'):
        unit = coerce_to
    return {'value': php_round(value, 3), 'unit': unit}


def computed_fluid_value(min_vw_raw, max_vw_raw, min_fs_raw, max_fs_raw, scale=1):
    min_fs = typography_value_and_unit(min_fs_raw)
    unit = min_fs['unit'] if min_fs else 'rem'
    max_fs = typography_value_and_unit(max_fs_raw, unit)
    if not max_fs or not min_fs:
        return None
    min_fs_rem = typography_value_and_unit(min_fs_raw, 'rem')
    max_vw = typography_value_and_unit(max_vw_raw, unit)
    min_vw = typography_value_and_unit(min_vw_raw, unit)
    if not min_vw or not max_vw:
        return None
    denom = max_vw['value'] - min_vw['value']
    if not denom:
        return None
    offset = php_num(php_round(min_vw['value'] / 100, 3)) + unit
    factor = 100 * ((max_fs['value'] - min_fs['value']) / denom)
    factor_scaled = php_round(factor * scale, 3) or 1
    target = php_num(min_fs_rem['value']) + min_fs_rem['unit'] + ' + ((1vw - %s) * %s)' % (offset, php_num(factor_scaled))
    return 'clamp(%s, %s, %s)' % (min_fs_raw, target, max_fs_raw)


def typography_font_size_value(preset, settings):
    """wp_get_typography_font_size_value()."""
    if 'size' not in preset or preset['size'] is None:
        return None
    size = preset['size']
    fluid_preset = preset.get('fluid')
    if fluid_preset is False or php_empty(size):
        return size
    typo = settings.get('typography') or {}
    if php_empty(typo.get('fluid')) and php_empty(fluid_preset):
        return size
    fluid = typo.get('fluid') if isinstance(typo.get('fluid'), dict) else {}
    layout = settings.get('layout') or {}
    min_vw = fluid.get('minViewportWidth', '320px')
    max_vw = layout['wideSize'] if layout.get('wideSize') and typography_value_and_unit(layout.get('wideSize')) else '1600px'
    if 'maxViewportWidth' in fluid:
        max_vw = fluid['maxViewportWidth']
    has_min = 'minFontSize' in fluid and typography_value_and_unit(fluid['minFontSize'])
    min_limit_raw = fluid['minFontSize'] if has_min else '14px'
    min_raw = fluid_preset.get('min') if isinstance(fluid_preset, dict) else None
    max_raw = fluid_preset.get('max') if isinstance(fluid_preset, dict) else None
    pref = typography_value_and_unit(size)
    if not pref or not pref.get('unit'):
        return size
    min_limit = typography_value_and_unit(min_limit_raw, pref['unit'])
    if min_limit and not min_raw and not max_raw:
        if pref['value'] <= min_limit['value']:
            return size
    if not max_raw:
        max_raw = php_num(pref['value']) + pref['unit']
    if not min_raw:
        px = pref['value'] if pref['unit'] == 'px' else pref['value'] * 16
        factor = min(max(1 - 0.075 * math.log(px, 2), 0.25), 0.75)
        calc_min = php_round(pref['value'] * factor, 3)
        if min_limit and calc_min <= min_limit['value']:
            min_raw = php_num(min_limit['value']) + min_limit['unit']
        else:
            min_raw = php_num(calc_min) + pref['unit']
    val = computed_fluid_value(min_vw, max_vw, min_raw, max_raw, 1)
    return val if val else size


# ─────────────────────────────────────────────────────────────────────────────
# Style engine (style-engine/class-wp-style-engine.php)
# ─────────────────────────────────────────────────────────────────────────────

SE = {
    'background': [
        dict(key='backgroundImage', prop='background-image', path=('background', 'backgroundImage'), func='url'),
        dict(key='backgroundPosition', prop='background-position', path=('background', 'backgroundPosition')),
        dict(key='backgroundRepeat', prop='background-repeat', path=('background', 'backgroundRepeat')),
        dict(key='backgroundSize', prop='background-size', path=('background', 'backgroundSize')),
        dict(key='backgroundAttachment', prop='background-attachment', path=('background', 'backgroundAttachment')),
        dict(key='gradient', prop='background-image', path=('background', 'gradient'),
             css_vars={'gradient': '--wp--preset--gradient--$slug'}, classnames={'has-background': True}),
    ],
    'color': [
        dict(key='text', prop='color', path=('color', 'text'), css_vars={'color': '--wp--preset--color--$slug'},
             classnames={'has-text-color': True, 'has-$slug-color': 'color'}),
        dict(key='background', prop='background-color', path=('color', 'background'),
             css_vars={'color': '--wp--preset--color--$slug'},
             classnames={'has-background': True, 'has-$slug-background-color': 'color'}),
        dict(key='gradient', prop='background', path=('color', 'gradient'),
             css_vars={'gradient': '--wp--preset--gradient--$slug'},
             classnames={'has-background': True, 'has-$slug-gradient-background': 'gradient'}),
    ],
    'border': [
        dict(key='color', prop='border-color', ind='border-%s-color', path=('border', 'color'),
             classnames={'has-border-color': True, 'has-$slug-border-color': 'color'}),
        dict(key='radius', prop='border-radius', ind='border-%s-radius', path=('border', 'radius'),
             css_vars={'border-radius': '--wp--preset--border-radius--$slug'}),
        dict(key='style', prop='border-style', ind='border-%s-style', path=('border', 'style')),
        dict(key='width', prop='border-width', ind='border-%s-width', path=('border', 'width')),
        dict(key='top', func='individual', path=('border', 'top'), css_vars={'color': '--wp--preset--color--$slug'}),
        dict(key='right', func='individual', path=('border', 'right'), css_vars={'color': '--wp--preset--color--$slug'}),
        dict(key='bottom', func='individual', path=('border', 'bottom'), css_vars={'color': '--wp--preset--color--$slug'}),
        dict(key='left', func='individual', path=('border', 'left'), css_vars={'color': '--wp--preset--color--$slug'}),
    ],
    'shadow': [
        dict(key='shadow', prop='box-shadow', path=('shadow',), css_vars={'shadow': '--wp--preset--shadow--$slug'}),
    ],
    'dimensions': [
        dict(key='aspectRatio', prop='aspect-ratio', path=('dimensions', 'aspectRatio'), classnames={'has-aspect-ratio': True}),
        dict(key='height', prop='height', path=('dimensions', 'height'), css_vars={'dimension': '--wp--preset--dimension--$slug'}),
        dict(key='minHeight', prop='min-height', path=('dimensions', 'minHeight'), css_vars={'dimension': '--wp--preset--dimension--$slug'}),
        dict(key='minWidth', prop='min-width', path=('dimensions', 'minWidth'), css_vars={'dimension': '--wp--preset--dimension--$slug'}),
        dict(key='objectFit', prop='object-fit', path=('dimensions', 'objectFit')),
        dict(key='width', prop='width', path=('dimensions', 'width'), css_vars={'dimension': '--wp--preset--dimension--$slug'}),
    ],
    'spacing': [
        dict(key='padding', prop='padding', ind='padding-%s', path=('spacing', 'padding'), css_vars={'spacing': '--wp--preset--spacing--$slug'}),
        dict(key='margin', prop='margin', ind='margin-%s', path=('spacing', 'margin'), css_vars={'spacing': '--wp--preset--spacing--$slug'}),
    ],
    'typography': [
        dict(key='fontSize', prop='font-size', path=('typography', 'fontSize'), css_vars={'font-size': '--wp--preset--font-size--$slug'},
             classnames={'has-$slug-font-size': 'font-size'}),
        dict(key='fontFamily', prop='font-family', path=('typography', 'fontFamily'), css_vars={'font-family': '--wp--preset--font-family--$slug'},
             classnames={'has-$slug-font-family': 'font-family'}),
        dict(key='fontStyle', prop='font-style', path=('typography', 'fontStyle')),
        dict(key='fontWeight', prop='font-weight', path=('typography', 'fontWeight')),
        dict(key='lineHeight', prop='line-height', path=('typography', 'lineHeight')),
        dict(key='textColumns', prop='column-count', path=('typography', 'textColumns')),
        dict(key='textDecoration', prop='text-decoration', path=('typography', 'textDecoration')),
        dict(key='textIndent', prop='text-indent', path=('typography', 'textIndent')),
        dict(key='textTransform', prop='text-transform', path=('typography', 'textTransform')),
        dict(key='letterSpacing', prop='letter-spacing', path=('typography', 'letterSpacing')),
        dict(key='writingMode', prop='writing-mode', path=('typography', 'writingMode')),
    ],
}
_SE_BY_GROUP_KEY = {(g, d['key']): d for g, defs in SE.items() for d in defs}


def _se_valid(v):
    return v == '0' or (not php_empty(v))


def _se_slug(value, prop_key):
    if isinstance(value, str) and ('var:preset|%s|' % prop_key) in value:
        return kebab(value[value.rfind('|') + 1:])
    return ''


def _se_css_var(value, css_vars):
    for prop_key, pattern in css_vars.items():
        slug = _se_slug(value, prop_key)
        if _se_valid(slug):
            return 'var(%s)' % pattern.replace('$slug', slug)
    return ''


def style_engine(styles, convert_vars_to_classnames=False):
    """wp_style_engine_get_styles() → (OrderedDict деклараций, [классы])."""
    decls = {}
    classes = []
    if not isinstance(styles, dict) or not styles:
        return decls, classes
    for group, defs in SE.items():
        if php_empty(styles.get(group)):
            continue
        for d in defs:
            value = get_path(styles, d['path'])
            if not _se_valid(value):
                continue
            # classnames
            if not php_empty(value) and d.get('classnames'):
                for cn, pk in d['classnames'].items():
                    if pk is True:
                        classes.append(cn)
                    else:
                        slug = _se_slug(value, pk)
                        if slug:
                            classes.append(cn.replace('$slug', slug))
            # declarations
            new = {}
            if d.get('func') == 'url':
                if isinstance(value, dict) and value.get('url'):
                    new[d['prop']] = "url('%s')" % value['url']
                elif isinstance(value, str):
                    new[d['prop']] = value
            elif d.get('func') == 'individual':
                if isinstance(value, dict):
                    side = d['path'][1]
                    for css_prop, v in value.items():
                        if php_empty(v):
                            continue
                        sd = _SE_BY_GROUP_KEY.get((d['path'][0], css_prop))
                        if sd and sd.get('ind'):
                            if isinstance(v, str) and 'var:' in v and not convert_vars_to_classnames and d.get('css_vars'):
                                v = _se_css_var(v, d['css_vars'])
                            new[sd['ind'] % side] = v
            elif isinstance(value, str) and 'var:' in value:
                if not convert_vars_to_classnames and d.get('css_vars'):
                    cv = _se_css_var(value, d['css_vars'])
                    if _se_valid(cv):
                        new[d['prop']] = cv
            elif isinstance(value, dict):
                if d.get('ind'):
                    for k, v in value.items():
                        if isinstance(v, str) and 'var:' in v and not convert_vars_to_classnames and d.get('css_vars'):
                            v = _se_css_var(v, d['css_vars'])
                        if _se_valid(v):
                            new[d['ind'] % kebab(k)] = v
            else:
                new[d['prop']] = value
            if new:
                if 'background-image' in new and 'background-image' in decls:
                    new['background-image'] = new['background-image'] + ', ' + decls['background-image']
                decls.update(new)
    seen = []
    for c in classes:
        if c not in seen:
            seen.append(c)
    return decls, seen


def _load_safe_css():
    try:
        return set(json.loads((DATA / 'safe-css.json').read_text(encoding='utf-8')))
    except Exception:
        return None


SAFE_CSS = _load_safe_css()


def css_prop_allowed(p):
    """safecss_filter_attr(): стиль-движок WP выбрасывает свойства не из белого списка (напр. box-sizing)."""
    return SAFE_CSS is None or p in SAFE_CSS or re.fullmatch(r'--[a-zA-Z0-9_-]+', p) is not None


def decls_to_css(decls):
    out = ''
    for p, v in decls.items():
        if v is None or not css_prop_allowed(p):
            continue
        v = str(v).strip() if not isinstance(v, (int, float)) else php_num(v)
        if v == '':
            continue
        out += '%s:%s;' % (p, v)
    return out


class CssStore:
    """Хранилище правил block-supports (WP_Style_Engine_CSS_Rules_Store): одинаковые селекторы сливаются."""

    def __init__(self):
        self.rules = {}  # (rules_group, selector) -> dict

    def add(self, selector, decls, rules_group=''):
        if not selector or not decls:
            return
        key = (rules_group or '', selector)
        bucket = self.rules.setdefault(key, {})
        for p, v in decls.items():
            if v is None or not css_prop_allowed(p):
                continue
            v = php_num(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v).strip()
            if v != '':
                bucket[p] = v

    def css(self):
        out = ''
        for (group, sel), decls in self.rules.items():
            body = ''.join('%s:%s;' % (p, v) for p, v in decls.items())
            if not body:
                continue
            rule = '%s{%s}' % (sel, body)
            out += ('%s{%s}' % (group, rule)) if group else rule
        return out


# ─────────────────────────────────────────────────────────────────────────────
# theme.json: данные, санитайз, слияние, генерация глобального CSS
# ─────────────────────────────────────────────────────────────────────────────

PRESETS_METADATA = [
    dict(path=('dimensions', 'aspectRatios'), prevent=('dimensions', 'defaultAspectRatios'), value_key='ratio',
         css_vars='--wp--preset--aspect-ratio--$slug', classes={}),
    dict(path=('color', 'palette'), prevent=('color', 'defaultPalette'), value_key='color',
         css_vars='--wp--preset--color--$slug',
         classes={'.has-$slug-color': 'color', '.has-$slug-background-color': 'background-color',
                  '.has-$slug-border-color': 'border-color'}),
    dict(path=('color', 'gradients'), prevent=('color', 'defaultGradients'), value_key='gradient',
         css_vars='--wp--preset--gradient--$slug', classes={'.has-$slug-gradient-background': 'background'}),
    dict(path=('color', 'duotone'), prevent=('color', 'defaultDuotone'), value_key=None, css_vars=None, classes={}),
    dict(path=('typography', 'fontSizes'), prevent=('typography', 'defaultFontSizes'), value_func='font_size',
         css_vars='--wp--preset--font-size--$slug', classes={'.has-$slug-font-size': 'font-size'}),
    dict(path=('typography', 'fontFamilies'), prevent=False, value_key='fontFamily',
         css_vars='--wp--preset--font-family--$slug', classes={'.has-$slug-font-family': 'font-family'}),
    dict(path=('spacing', 'spacingSizes'), prevent=('spacing', 'defaultSpacingSizes'), value_key='size',
         css_vars='--wp--preset--spacing--$slug', classes={}),
    dict(path=('shadow', 'presets'), prevent=('shadow', 'defaultPresets'), value_key='shadow',
         css_vars='--wp--preset--shadow--$slug', classes={}),
    dict(path=('border', 'radiusSizes'), prevent=False, value_key='size',
         css_vars='--wp--preset--border-radius--$slug', classes={}),
    dict(path=('dimensions', 'dimensionSizes'), prevent=False, value_key='size',
         css_vars='--wp--preset--dimension--$slug', classes={}),
]
ORIGINS = ['default', 'blocks', 'theme', 'custom']
CSS_ORIGINS = ['default', 'theme', 'custom']

PROPERTIES_METADATA = [
    ('aspect-ratio', ('dimensions', 'aspectRatio')), ('background', ('color', 'gradient')),
    ('background-color', ('color', 'background')), ('background-image', ('background', 'backgroundImage')),
    ('background-position', ('background', 'backgroundPosition')), ('background-repeat', ('background', 'backgroundRepeat')),
    ('background-size', ('background', 'backgroundSize')), ('background-attachment', ('background', 'backgroundAttachment')),
    ('border-radius', ('border', 'radius')), ('border-top-left-radius', ('border', 'radius', 'topLeft')),
    ('border-top-right-radius', ('border', 'radius', 'topRight')), ('border-bottom-left-radius', ('border', 'radius', 'bottomLeft')),
    ('border-bottom-right-radius', ('border', 'radius', 'bottomRight')), ('border-color', ('border', 'color')),
    ('border-width', ('border', 'width')), ('border-style', ('border', 'style')),
    ('border-top-color', ('border', 'top', 'color')), ('border-top-width', ('border', 'top', 'width')),
    ('border-top-style', ('border', 'top', 'style')), ('border-right-color', ('border', 'right', 'color')),
    ('border-right-width', ('border', 'right', 'width')), ('border-right-style', ('border', 'right', 'style')),
    ('border-bottom-color', ('border', 'bottom', 'color')), ('border-bottom-width', ('border', 'bottom', 'width')),
    ('border-bottom-style', ('border', 'bottom', 'style')), ('border-left-color', ('border', 'left', 'color')),
    ('border-left-width', ('border', 'left', 'width')), ('border-left-style', ('border', 'left', 'style')),
    ('color', ('color', 'text')), ('text-align', ('typography', 'textAlign')), ('column-count', ('typography', 'textColumns')),
    ('font-family', ('typography', 'fontFamily')), ('font-size', ('typography', 'fontSize')),
    ('font-style', ('typography', 'fontStyle')), ('font-weight', ('typography', 'fontWeight')),
    ('letter-spacing', ('typography', 'letterSpacing')), ('line-height', ('typography', 'lineHeight')),
    ('margin', ('spacing', 'margin')), ('margin-top', ('spacing', 'margin', 'top')),
    ('margin-right', ('spacing', 'margin', 'right')), ('margin-bottom', ('spacing', 'margin', 'bottom')),
    ('margin-left', ('spacing', 'margin', 'left')), ('min-height', ('dimensions', 'minHeight')),
    ('min-width', ('dimensions', 'minWidth')), ('outline-color', ('outline', 'color')),
    ('outline-offset', ('outline', 'offset')), ('outline-style', ('outline', 'style')),
    ('outline-width', ('outline', 'width')), ('padding', ('spacing', 'padding')),
    ('padding-top', ('spacing', 'padding', 'top')), ('padding-right', ('spacing', 'padding', 'right')),
    ('padding-bottom', ('spacing', 'padding', 'bottom')), ('padding-left', ('spacing', 'padding', 'left')),
    ('--wp--style--root--padding', ('spacing', 'padding')), ('--wp--style--root--padding-top', ('spacing', 'padding', 'top')),
    ('--wp--style--root--padding-right', ('spacing', 'padding', 'right')),
    ('--wp--style--root--padding-bottom', ('spacing', 'padding', 'bottom')),
    ('--wp--style--root--padding-left', ('spacing', 'padding', 'left')),
    ('text-decoration', ('typography', 'textDecoration')), ('text-shadow', ('typography', 'textShadow')),
    ('text-transform', ('typography', 'textTransform')), ('text-indent', ('typography', 'textIndent')),
    ('filter', ('filter', 'duotone')), ('box-shadow', ('shadow',)), ('height', ('dimensions', 'height')),
    ('width', ('dimensions', 'width')), ('writing-mode', ('typography', 'writingMode')),
]

ELEMENTS = {
    'link': 'a:where(:not(.wp-element-button))',
    'heading': 'h1, h2, h3, h4, h5, h6',
    'h1': 'h1', 'h2': 'h2', 'h3': 'h3', 'h4': 'h4', 'h5': 'h5', 'h6': 'h6',
    'button': '.wp-element-button, .wp-block-button__link',
    'caption': '.wp-element-caption, .wp-block-audio figcaption, .wp-block-embed figcaption, .wp-block-gallery figcaption, '
               '.wp-block-image figcaption, .wp-block-table figcaption, .wp-block-video figcaption',
    'cite': 'cite',
    'textInput': 'textarea, input:where([type=email],[type=number],[type=password],[type=search],[type=text],[type=tel],[type=url])',
    'select': 'select',
}
ELEMENT_CLASS_NAMES = {'button': 'wp-element-button', 'caption': 'wp-element-caption'}
ELEMENT_PSEUDO = {
    'link': [':link', ':any-link', ':visited', ':hover', ':focus', ':focus-visible', ':active'],
    'button': [':link', ':any-link', ':visited', ':hover', ':focus', ':focus-visible', ':active'],
}
BLOCK_PSEUDO = {
    'core/button': [':hover', ':focus', ':focus-visible', ':active'],
    'core/navigation-link': [':hover', ':focus', ':focus-visible', ':active'],
}
BLOCK_CUSTOM_STATES = {'core/navigation-link': ['-current']}
DEFAULT_VIEWPORTS = {'mobile': '480px', 'tablet': '782px'}

VALID_STYLES = {
    'background': {'backgroundImage': None, 'backgroundPosition': None, 'backgroundRepeat': None,
                   'backgroundSize': None, 'backgroundAttachment': None, 'gradient': None},
    'border': {'color': None, 'radius': None, 'style': None, 'width': None, 'top': None, 'right': None, 'bottom': None, 'left': None},
    'color': {'background': None, 'gradient': None, 'text': None},
    'dimensions': {'aspectRatio': None, 'height': None, 'minHeight': None, 'minWidth': None, 'width': None},
    'filter': {'duotone': None},
    'outline': {'color': None, 'offset': None, 'style': None, 'width': None},
    'shadow': None,
    'spacing': {'margin': None, 'padding': None, 'blockGap': None},
    'typography': {'fontFamily': None, 'fontSize': None, 'fontStyle': None, 'fontWeight': None, 'letterSpacing': None,
                   'lineHeight': None, 'textAlign': None, 'textColumns': None, 'textDecoration': None,
                   'textIndent': None, 'textShadow': None, 'textTransform': None, 'writingMode': None},
    'css': None,
}
VALID_SETTINGS = {
    'appearanceTools': None, 'useRootPaddingAwareAlignments': None,
    'background': {'backgroundImage': None, 'backgroundSize': None, 'gradient': None},
    'border': {'color': None, 'radius': None, 'radiusSizes': None, 'style': None, 'width': None},
    'color': {k: None for k in ['background', 'custom', 'customDuotone', 'customGradient', 'defaultDuotone',
                                'defaultGradients', 'defaultPalette', 'duotone', 'gradients', 'link', 'heading',
                                'button', 'caption', 'palette', 'text']},
    'custom': None,
    'dimensions': {k: None for k in ['aspectRatio', 'aspectRatios', 'defaultAspectRatios', 'dimensionSizes', 'height',
                                     'minHeight', 'minWidth', 'width']},
    'layout': {'contentSize': None, 'wideSize': None, 'allowEditing': None, 'allowCustomContentAndWideSize': None},
    'lightbox': {'enabled': True, 'allowEditing': True},
    'position': {'fixed': None, 'sticky': None},
    'blockVisibility': {'allowEditing': True},
    'spacing': {k: None for k in ['customSpacingSize', 'defaultSpacingSizes', 'spacingSizes', 'spacingScale',
                                  'blockGap', 'margin', 'padding', 'units']},
    'shadow': {'presets': None, 'defaultPresets': None},
    'typography': {k: None for k in ['fluid', 'customFontSize', 'defaultFontSizes', 'dropCap', 'fontFamilies', 'fontSizes',
                                     'fontStyle', 'fontWeight', 'letterSpacing', 'lineHeight', 'textAlign',
                                     'textColumns', 'textDecoration', 'textIndent', 'textTransform', 'writingMode']},
    'viewport': {'mobile': None, 'tablet': None},
}
APPEARANCE_TOOLS_OPT_INS = [
    ('background', 'backgroundImage'), ('background', 'backgroundSize'), ('background', 'gradient'),
    ('border', 'color'), ('border', 'radius'), ('border', 'style'), ('border', 'width'),
    ('color', 'link'), ('color', 'heading'), ('color', 'button'), ('color', 'caption'),
    ('dimensions', 'aspectRatio'), ('dimensions', 'height'), ('dimensions', 'minHeight'),
    ('dimensions', 'minWidth'), ('dimensions', 'width'), ('position', 'sticky'),
    ('spacing', 'blockGap'), ('spacing', 'margin'), ('spacing', 'padding'),
    ('typography', 'lineHeight'), ('typography', 'textColumns'),
]

LAYOUT_DEFINITIONS = {
    'default': {
        'className': 'is-layout-flow',
        'baseStyles': [
            (' > .alignleft', [('float', 'left'), ('margin-inline-start', '0'), ('margin-inline-end', '2em')]),
            (' > .alignright', [('float', 'right'), ('margin-inline-start', '2em'), ('margin-inline-end', '0')]),
            (' > .aligncenter', [('margin-left', 'auto !important'), ('margin-right', 'auto !important')]),
        ],
        'spacingStyles': [
            (' > :first-child', [('margin-block-start', '0')]),
            (' > :last-child', [('margin-block-end', '0')]),
            (' > *', [('margin-block-start', None), ('margin-block-end', '0')]),
        ],
    },
    'constrained': {
        'className': 'is-layout-constrained',
        'baseStyles': [
            (' > .alignleft', [('float', 'left'), ('margin-inline-start', '0'), ('margin-inline-end', '2em')]),
            (' > .alignright', [('float', 'right'), ('margin-inline-start', '2em'), ('margin-inline-end', '0')]),
            (' > .aligncenter', [('margin-left', 'auto !important'), ('margin-right', 'auto !important')]),
            (' > :where(:not(.alignleft):not(.alignright):not(.alignfull))',
             [('max-width', 'var(--wp--style--global--content-size)'), ('margin-left', 'auto !important'),
              ('margin-right', 'auto !important')]),
            (' > .alignwide', [('max-width', 'var(--wp--style--global--wide-size)')]),
        ],
        'spacingStyles': [
            (' > :first-child', [('margin-block-start', '0')]),
            (' > :last-child', [('margin-block-end', '0')]),
            (' > *', [('margin-block-start', None), ('margin-block-end', '0')]),
        ],
    },
    'flex': {
        'className': 'is-layout-flex', 'displayMode': 'flex',
        'baseStyles': [('', [('flex-wrap', 'wrap'), ('align-items', 'center')]), (' > :is(*, div)', [('margin', '0')])],
        'spacingStyles': [('', [('gap', None)])],
    },
    'grid': {
        'className': 'is-layout-grid', 'displayMode': 'grid',
        'baseStyles': [(' > :is(*, div)', [('margin', '0')])],
        'spacingStyles': [('', [('gap', None)])],
    },
}


def split_selector_list(selector):
    if ',' not in selector:
        return [selector.strip(' \t\n')]
    out, depth, cur, i, quote = [], 0, '', 0, None
    while i < len(selector):
        ch = selector[i]
        if quote:
            cur += ch
            if ch == '\\' and i + 1 < len(selector):
                cur += selector[i + 1]
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in '"\'':
            quote = ch
            cur += ch
        elif ch == '\\' and i + 1 < len(selector):
            cur += selector[i:i + 2]
            i += 2
            continue
        elif ch == '(':
            depth += 1
            cur += ch
        elif ch == ')':
            depth -= 1
            cur += ch
        elif ch == ',' and depth == 0:
            out.append(cur.strip(' \t\n'))
            cur = ''
        else:
            cur += ch
        i += 1
    if cur.strip(' \t\n') or not out:
        out.append(cur.strip(' \t\n'))
    return out


def append_to_selector(selector, to_append):
    if ',' not in selector:
        return selector.strip(' \t\n') + to_append
    return ', '.join(s + to_append for s in split_selector_list(selector))


def prepend_to_selector(selector, to_prepend):
    if ',' not in selector:
        return to_prepend + selector.strip(' \t\n')
    return ', '.join(to_prepend + s for s in split_selector_list(selector))


def scope_selector(scope, selector):
    if not scope or not selector:
        return selector
    out = []
    for outer in split_selector_list(scope):
        for inner in split_selector_list(selector):
            if outer and inner:
                out.append(outer + ' ' + inner)
            elif not outer:
                out.append(inner)
            else:
                out.append(outer)
    return ', '.join(out)


def block_style_variation_selector(variation, block_selector):
    cls = '.is-style-%s' % variation
    if not block_selector:
        return cls
    return ', '.join(re.sub(r'[^\s:]+', lambda m: m.group(0) + cls, part, count=1)
                     for part in split_selector_list(block_selector))


def block_style_variation_feature_selector(style_variation, feature_selector):
    name = style_variation.get('name') or (style_variation.get('path') or [None])[-1]
    if not name:
        return style_variation.get('selector') or feature_selector
    prefix = '.is-style-%s ' % name
    parts = [s[len(prefix):] if s.startswith(prefix) else s for s in split_selector_list(feature_selector)]
    return block_style_variation_selector(name, ', '.join(parts))


def element_selectors_for_block(root_selector):
    out = {}
    block_selectors = root_selector.split(',')
    for el, el_sel in ELEMENTS.items():
        parts = []
        for sel in block_selectors:
            if sel == el_sel:
                parts = [el_sel]
                break
            parts.append(prepend_to_selector(el_sel, sel + ' '))
        out[el] = ','.join(parts)
    return out


def to_ruleset(selector, decls):
    body = ''
    for name, value in decls:
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            value = php_num(value)
        if not isinstance(value, str):
            continue
        body += '%s: %s;' % (name, value)
    return '%s{%s}' % (selector, body) if decls else ''


def process_blocks_custom_css(css, selector):
    out = ''
    if not css:
        return out
    for part in css.split('&'):
        if not part:
            continue
        if '{' not in part:
            out += ':root :where(%s){%s}' % (selector.strip(), part.strip())
        else:
            bits = part.replace('}', '').split('{')
            if len(bits) != 2:
                continue
            nested, value = bits
            m = re.search(r'([>+~\s]*::[a-zA-Z-]+)', nested)
            pseudo = m.group(1) if m else ''
            if pseudo:
                nested = nested.replace(pseudo, '')
            part_sel = scope_selector(selector, nested) if nested.startswith(' ') else append_to_selector(selector, nested)
            out += ':root :where(%s)%s{%s}' % (part_sel, pseudo, value.strip())
    return out


def viewport_media_queries(viewport, include_desktop=False):
    def valid(v):
        return isinstance(v, str) and re.fullmatch(r'(?:\d+|\d*\.\d+)(?:px|em|rem)', v.strip())

    def px(v):
        v = v.strip()
        if v.endswith('rem'):
            return float(v[:-3]) * 16
        if v.endswith('em'):
            return float(v[:-2]) * 16
        return float(v[:-2])

    if not isinstance(viewport, dict):
        bp = dict(DEFAULT_VIEWPORTS)
    else:
        bp = {k: viewport[k].strip() for k in ('mobile', 'tablet') if valid(viewport.get(k))}
        if not bp:
            bp = dict(DEFAULT_VIEWPORTS)
        elif len(bp) == 2 and not px(bp['mobile']) < px(bp['tablet']):
            del bp['tablet']
    out = {}
    if 'mobile' in bp:
        out['@mobile'] = '@media (width <= %s)' % bp['mobile']
    if 'tablet' in bp:
        out['@tablet'] = ('@media (%s < width <= %s)' % (bp['mobile'], bp['tablet'])) if 'mobile' in bp \
            else '@media (width <= %s)' % bp['tablet']
    if include_desktop:
        out['@desktop'] = '@media (width > %s)' % (bp.get('tablet') or bp.get('mobile'))
    return out


class ThemeJSON:
    """Слитые данные theme.json (default + blocks + TT5 + пользовательские global styles) и генерация CSS."""

    def __init__(self, base, blocks_meta, user=None, warnings=None):
        self.blocks = blocks_meta
        self.warnings = warnings if warnings is not None else []
        self.removed = []
        data = copy.deepcopy(base)
        if user:
            data = self.merge(data, self.prepare_user(user))
        self.data = data
        self.settings = data.get('settings', {})
        self.styles = data.get('styles', {})
        self.viewports = viewport_media_queries(self.settings.get('viewport'))

    # ---- подготовка пользовательских данных (WP_Theme_JSON::__construct для origin=custom)
    def valid_variations(self):
        out = {}
        for name, meta in self.blocks.items():
            sv = meta.get('styleVariations') or {}
            if isinstance(sv, dict) and sv:
                out[name] = list(sv.keys())
        return out

    def prepare_user(self, user):
        user = copy.deepcopy(user)
        valid_vars = self.valid_variations()
        # styles.variations → styles.blocks.X.variations
        shared = get_path(user, ('styles', 'variations'))
        if isinstance(shared, dict) and shared:
            for block, names in valid_vars.items():
                for vn in names:
                    top = shared.get(vn, {})
                    blk = get_path(user, ('styles', 'blocks', block, 'variations', vn), {})
                    merged = array_replace_recursive(top, blk) if top or blk else {}
                    if merged:
                        set_path(user, ['styles', 'blocks', block, 'variations', vn], merged)
            for vn in shared:
                if not any(vn in v for v in valid_vars.values()):
                    self.removed.append('styles.variations.%s (вариация не зарегистрирована ни у одного блока)' % vn)
            del user['styles']['variations']
        out = {}
        for key in ('version', 'settings', 'styles', 'customTemplates', 'templateParts', 'title', 'slug',
                    'description', 'patterns', 'blockTypes'):
            if key in user:
                out[key] = user[key]
        for key in user:
            if key not in out and key not in ('isGlobalStylesUserThemeJSON', 'id', '_links', 'title'):
                self.removed.append('%s (неизвестный ключ верхнего уровня)' % key)
        if isinstance(out.get('styles'), dict):
            out['styles'] = self.sanitize_styles(out['styles'], valid_vars)
            out['styles'] = resolve_custom_css_format(out['styles'])
        if isinstance(out.get('settings'), dict):
            out['settings'] = self.sanitize_settings(out['settings'])
            out['settings'] = resolve_custom_css_format(out['settings'])
            st = out['settings']
            if st.get('appearanceTools') is True:
                for p in APPEARANCE_TOOLS_OPT_INS:
                    if get_path(st, p, 'unset prop') == 'unset prop':
                        set_path(st, list(p), True)
                st.pop('appearanceTools', None)
            nodes = [st] + [b for b in (st.get('blocks') or {}).values() if isinstance(b, dict)]
            for node in nodes:
                for pm in PRESETS_METADATA:
                    preset = get_path(node, pm['path'])
                    if preset is not None and (isinstance(preset, list) or not preset):
                        set_path(node, list(pm['path']), {'custom': preset})
        return out

    def _schema_style_node(self, block=None, top=False):
        return VALID_STYLES

    def _filter(self, tree, schema, path):
        if not isinstance(tree, dict):
            return tree
        out = {}
        for k, v in tree.items():
            if k not in schema:
                self.removed.append('.'.join(path + [k]))
                continue
            sch = schema[k]
            if isinstance(sch, bool):
                if isinstance(v, bool):
                    out[k] = v
                else:
                    self.removed.append('.'.join(path + [k]) + ' (ожидается true/false)')
                continue
            if isinstance(sch, dict):
                if not isinstance(v, (dict, list)):
                    self.removed.append('.'.join(path + [k]) + ' (ожидается объект)')
                    continue
                if isinstance(v, list):
                    out[k] = v
                    continue
                f = self._filter(v, sch, path + [k])
                if f:
                    out[k] = f
                continue
            out[k] = v
        return out

    def sanitize_styles(self, styles, valid_vars):
        vq = list(viewport_media_queries(None).keys())
        elem_schema = {}
        for el in ELEMENTS:
            s = dict(VALID_STYLES)
            for ps in ELEMENT_PSEUDO.get(el, []):
                s[ps] = VALID_STYLES
            for bp in vq:
                s[bp] = VALID_STYLES
            elem_schema[el] = s
        block_schema = {}
        for b in self.blocks:
            s = dict(VALID_STYLES)
            s['elements'] = elem_schema
            for bp in vq:
                s[bp] = dict(VALID_STYLES, elements=elem_schema)
                for ps in BLOCK_PSEUDO.get(b, []):
                    s[bp][ps] = VALID_STYLES
            for ps in BLOCK_PSEUDO.get(b, []):
                s[ps] = VALID_STYLES
            for cs in BLOCK_CUSTOM_STATES.get(b, []):
                s[cs] = dict(VALID_STYLES, **{ps: VALID_STYLES for ps in BLOCK_PSEUDO.get(b, [])})
            block_schema[b] = s
        var_style = dict(VALID_STYLES, blocks=block_schema, elements=elem_schema)
        for b in self.blocks:
            names = valid_vars.get(b, [])
            vs = {}
            user_vars = get_path(styles, ('blocks', b, 'variations'), {}) or {}
            for vn in user_vars:
                if vn in names:
                    vs[vn] = dict(var_style, **{bp: dict(VALID_STYLES, elements=elem_schema, blocks=block_schema) for bp in vq})
                    for ps in BLOCK_PSEUDO.get(b, []):
                        vs[vn][ps] = VALID_STYLES
                else:
                    self.removed.append('styles.blocks.%s.variations.%s (у блока нет такой зарегистрированной вариации'
                                        ' стиля — WP её выбросит; доступны: %s)' % (b, vn, ', '.join(names) or 'нет'))
            block_schema[b] = dict(block_schema[b], variations=vs)
        schema = dict(VALID_STYLES, blocks=block_schema, elements=elem_schema)
        for bname in (styles.get('blocks') or {}):
            if bname not in self.blocks:
                self.removed.append('styles.blocks.%s (блок не зарегистрирован)' % bname)
        return self._filter(styles, schema, ['styles'])

    def sanitize_settings(self, settings):
        ff = {'fontFamily': None, 'name': None, 'slug': None, 'fontFace': None}
        schema = dict(VALID_SETTINGS)
        schema['typography'] = dict(VALID_SETTINGS['typography'])
        schema['blocks'] = {b: {k: v for k, v in VALID_SETTINGS.items() if k not in ('viewport', 'blockVisibility')}
                            for b in self.blocks}
        out = self._filter(settings, schema, ['settings'])
        return out

    # ---- WP_Theme_JSON::merge
    def merge(self, base, inc):
        data = array_replace_recursive(base, inc)
        nodes = [('settings',)] + [('settings', 'blocks', b) for b in (get_path(inc, ('settings', 'blocks')) or {})]
        for node_path in nodes:
            units = get_path(inc, node_path + ('spacing', 'units'))
            if units is not None:
                set_path(data, list(node_path + ('spacing', 'units')), units)
            for pm in PRESETS_METADATA:
                for origin in ORIGINS:
                    path = node_path + pm['path'] + (origin,)
                    content = get_path(inc, path)
                    if content is None:
                        continue
                    set_path(data, list(path), copy.deepcopy(content))
        for sp in [('styles',)] + [('styles', 'blocks', b) for b in (get_path(inc, ('styles', 'blocks')) or {})]:
            bg = get_path(inc, sp + ('background', 'backgroundImage'))
            if bg is not None:
                set_path(data, list(sp + ('background', 'backgroundImage')), bg)
        return data

    # ---- пресеты
    def values_by_slug(self, node, pm, origins):
        per_origin = get_path(node, pm['path'], {}) or {}
        out = {}
        if not isinstance(per_origin, dict):
            return out
        for origin in origins:
            for preset in per_origin.get(origin) or []:
                if not isinstance(preset, dict) or 'slug' not in preset:
                    continue
                slug = kebab(preset['slug'])
                if pm.get('value_key') and pm['value_key'] in preset:
                    out[slug] = preset[pm['value_key']]
                elif pm.get('value_func') == 'font_size':
                    out[slug] = typography_font_size_value(preset, dict(self.settings, **node))
        return out

    def slugs(self, node, pm, origins):
        per_origin = get_path(node, pm['path'], {}) or {}
        out = []
        if not isinstance(per_origin, dict):
            return out
        for origin in origins:
            for preset in per_origin.get(origin) or []:
                if isinstance(preset, dict) and 'slug' in preset:
                    s = kebab(preset['slug'])
                    if s not in out:
                        out.append(s)
        return out

    def setting_nodes(self):
        nodes = [{'path': ('settings',), 'selector': ':root', 'selectors': {}}]
        for name in (self.settings.get('blocks') or {}):
            meta = self.blocks.get(name) or {}
            nodes.append({'path': ('settings', 'blocks', name), 'selector': meta.get('selector'),
                          'selectors': meta.get('selectors') or {}})
        return nodes

    def css_variables(self):
        css = ''
        for meta in self.setting_nodes():
            if not meta['selector']:
                continue
            node = get_path(self.data, meta['path'], {}) or {}
            by_sel = {meta['selector']: []}
            for pm in PRESETS_METADATA:
                if not pm['css_vars']:
                    continue
                vals = self.values_by_slug(node, pm, CSS_ORIGINS)
                if not vals:
                    continue
                fs = meta['selectors'].get(pm['path'][0]) if isinstance(meta['selectors'], dict) else None
                target = fs if isinstance(fs, str) else (fs.get('root') if isinstance(fs, dict) and isinstance(fs.get('root'), str) else meta['selector'])
                by_sel.setdefault(target, [])
                for slug, v in vals.items():
                    by_sel[target].append((pm['css_vars'].replace('$slug', slug), v))
            for k, v in self.flatten_custom(node.get('custom') or {}).items():
                by_sel[meta['selector']].append(('--wp--custom--' + k, v))
            for sel, decls in by_sel.items():
                css += to_ruleset(sel, decls)
        return css

    def flatten_custom(self, tree, prefix=''):
        out = {}
        for k, v in tree.items():
            nk = prefix + kebab(k).replace('/', '-').lower()
            if isinstance(v, dict):
                out.update(self.flatten_custom(v, nk + '--'))
            else:
                out[nk] = v
        return out

    def preset_classes(self):
        css = ''
        for meta in self.setting_nodes():
            if not meta['selector']:
                continue
            node = get_path(self.data, meta['path'], {}) or {}
            sel = '' if meta['selector'] in ('body', ':root') else meta['selector']
            for pm in PRESETS_METADATA:
                if not pm['classes']:
                    continue
                slugs = self.slugs(node, pm, CSS_ORIGINS)
                for cls, prop in pm['classes'].items():
                    for slug in slugs:
                        var = pm['css_vars'].replace('$slug', slug)
                        cn = cls.replace('$slug', slug)
                        css += to_ruleset(cn if not sel else ':where(%s)%s' % (sel, cn), [(prop, 'var(%s) !important' % var)])
        return css

    # ---- свойства стиля
    def property_value(self, styles, path):
        value = get_path(styles, path, '')
        if value is None or value == '':
            return ''
        if isinstance(value, dict) and 'ref' in value:
            ref = get_path(self.data, value['ref'].split('.'))
            if ref and (isinstance(ref, str) or isinstance(get_path(ref, ('url',)), str)):
                value = ref
        return value

    def compute_style_properties(self, styles, selector=None, use_root_padding=None):
        if not styles:
            return []
        decls = []
        dup = []
        for prop, path in PROPERTIES_METADATA:
            is_root_style = prop.startswith('--wp--style--root--')
            if is_root_style and (selector != 'body' or not use_root_padding):
                continue
            value = self.property_value(styles, path)
            if prop == '--wp--style--root--padding' and isinstance(value, str):
                continue
            if is_root_style and use_root_padding:
                dup.append(prop[len('--wp--style--root--'):])
            if prop == 'background-image':
                inp = {}
                if not php_empty(value):
                    inp['backgroundImage'] = value
                g = get_path(styles, ('background', 'gradient'))
                if not php_empty(g):
                    inp['gradient'] = g
                if inp:
                    d, _ = style_engine({'background': inp})
                    value = d.get('background-image')
            if php_empty(value) and selector != 'body' and get_path(styles, ('background', 'backgroundImage', 'id')):
                if prop == 'background-size':
                    value = 'cover'
                if prop == 'background-position':
                    value = '50% 50%' if get_path(styles, ('background', 'backgroundSize')) == 'contain' else None
            if (php_empty(value) and not php_is_numeric(value)) or isinstance(value, (dict, list)):
                continue
            if prop == 'font-size':
                value = typography_font_size_value({'size': value}, self.settings)
            if prop == 'aspect-ratio':
                decls.append(('min-height', 'unset'))
            decls.append((prop, value))
        for d in dup:
            for i, (n, _) in enumerate(decls):
                if n == d:
                    del decls[i]
                    break
        return decls

    # ---- узлы стилей
    def style_nodes(self, include_blocks=False):
        nodes = [{'path': ('styles',), 'selector': 'body'}]
        els = self.styles.get('elements') or {}
        for el, sel in ELEMENTS.items():
            if el not in els:
                continue
            nodes.append({'path': ('styles', 'elements', el), 'selector': sel})
            for ps in ELEMENT_PSEUDO.get(el, []):
                if ps in els[el]:
                    nodes.append({'path': ('styles', 'elements', el), 'selector': append_to_selector(sel, ps)})
        if include_blocks:
            nodes += self.block_nodes()
        return nodes

    def block_nodes(self, include_variations=False, styles_root=None):
        nodes = []
        data = styles_root if styles_root is not None else self.data
        blocks = get_path(data, ('styles', 'blocks')) or {}
        vq = self.viewports
        for name, node in blocks.items():
            meta = self.blocks.get(name) or {}
            selector = meta.get('selector')
            fsel = meta.get('selectors') or None
            elements = meta.get('elements') or {}
            variations = []
            if include_variations and isinstance(node.get('variations'), dict):
                for vn in node['variations']:
                    vsel = (meta.get('styleVariations') or {}).get(vn) if isinstance(meta.get('styleVariations'), dict) else None
                    if vsel is None:
                        vsel = block_style_variation_selector(vn, selector)
                    variations.append({'name': vn, 'path': ('styles', 'blocks', name, 'variations', vn), 'selector': vsel})
            base = {'name': name, 'path': ('styles', 'blocks', name), 'selector': selector, 'selectors': fsel,
                    'elements': elements, 'duotone': meta.get('duotone'), 'variations': variations, 'css': selector}
            nodes.append(base)
            for bp, mq in vq.items():
                if bp in node:
                    nodes.append(dict(base, path=('styles', 'blocks', name, bp), media_query=mq, duotone=None))
            for ps in BLOCK_PSEUDO.get(name, []):
                if ps in node and selector:
                    pfs = {}
                    for f, fs in (fsel or {}).items():
                        pfs[f] = {k: append_to_selector(v, ps) for k, v in fs.items()} if isinstance(fs, dict) else append_to_selector(fs, ps)
                    nodes.append(dict(base, path=('styles', 'blocks', name, ps), selector=append_to_selector(selector, ps),
                                      selectors=pfs, css=append_to_selector(selector, ps)))
            for cs in BLOCK_CUSTOM_STATES.get(name, []):
                st = (meta.get('states') or {}).get(cs) if isinstance(meta.get('states'), dict) else None
                if cs in node and st:
                    nodes.append(dict(base, path=('styles', 'blocks', name, cs), selector=st, css=st))
            for el in (node.get('elements') or {}):
                if el not in elements:
                    continue
                esel = elements[el]
                nodes.append({'path': ('styles', 'blocks', name, 'elements', el), 'selector': esel, 'block': name})
                for ps in ELEMENT_PSEUDO.get(el, []):
                    if ps in node['elements'][el]:
                        nodes.append({'path': ('styles', 'blocks', name, 'elements', el),
                                      'selector': append_to_selector(esel, ps), 'block': name})
        return nodes

    def feature_declarations(self, metadata, node):
        """get_feature_declarations_for_node(); node изменяется (удаляются вынесенные свойства)."""
        decls = {}
        sels = metadata.get('selectors')
        if not sels:
            return decls
        for feature, fsel in sels.items():
            if feature in ('root', 'css') or php_empty(node.get(feature)):
                continue
            if isinstance(fsel, dict):
                for sub, ssel in fsel.items():
                    if sub == 'root' or not isinstance(node.get(feature), dict) or php_empty(node[feature].get(sub)):
                        continue
                    nd = self.compute_style_properties({feature: {sub: node[feature][sub]}})
                    decls.setdefault(ssel, []).extend(nd)
                    del node[feature][sub]
            if isinstance(fsel, str) or (isinstance(fsel, dict) and fsel.get('root')):
                fs = fsel if isinstance(fsel, str) else fsel['root']
                nd = self.compute_style_properties({feature: node.get(feature)})
                decls.setdefault(fs, []).extend(nd)
                node.pop(feature, None)
        return decls

    def layout_styles(self, metadata, node=None, media_query=None, root_selector_mode=False):
        rules = ''
        block_type = None
        if metadata.get('name'):
            block_type = self.blocks.get(metadata['name'])
            if not block_supports_layout(block_type):
                return rules
        selector = metadata.get('selector') or ''
        has_gap = get_path(self.settings, ('spacing', 'blockGap')) is not None
        if node is None:
            node = get_path(self.data, metadata['path'], {}) or {}
        pattern = re.compile(r'^[a-zA-Z0-9\-\.\,\ *+>:\(\)]*$')
        gap = None
        if not has_gap:
            gap = '0.5em' if selector == 'body' else None
            if block_type:
                gap = get_path(block_type, ('supports', 'spacing', 'blockGap', '__experimentalDefault'))
        else:
            gap = self.property_value(node, ('spacing', 'blockGap'))
        if isinstance(gap, dict):
            if 'top' in gap and 'left' in gap:
                r, c = self.property_value(node, ('spacing', 'blockGap', 'top')), self.property_value(node, ('spacing', 'blockGap', 'left'))
                gap = r if r == c else '%s %s' % (r, c)
            else:
                gap = None
        if gap is not None and gap is not False and gap != '':
            for key, ld in LAYOUT_DEFINITIONS.items():
                if not has_gap and key not in ('flex', 'grid'):
                    continue
                for sub, sub_rules in ld['spacingStyles']:
                    if not pattern.match(sub):
                        continue
                    decls = [(p, v if isinstance(v, str) else gap) for p, v in sub_rules]
                    if not has_gap:
                        fmt = ':where(.%s%s)' % (ld['className'], sub) if selector == 'body' else ':where(%s.%s%s)' % (selector, ld['className'], sub)
                    else:
                        fmt = (':root :where(.%s)%s' % (ld['className'], sub)) if selector == 'body' else (':root :where(%s-%s)%s' % (selector, ld['className'], sub))
                    rules += to_ruleset(fmt, decls)
        if selector == 'body':
            lay = self.settings.get('layout') or {}
            for key, ld in LAYOUT_DEFINITIONS.items():
                if ld.get('displayMode'):
                    rules += to_ruleset('%s .%s' % (selector, ld['className']), [('display', ld['displayMode'])])
                for sub, sub_rules in ld['baseStyles']:
                    decls = []
                    for p, v in sub_rules:
                        if ('--global--content-size' in v or '--global--wide-size' in v) and 'contentSize' not in lay and 'wideSize' not in lay:
                            continue
                        decls.append((p, v))
                    rules += to_ruleset('.%s%s' % (ld['className'], sub), decls)
        if media_query and rules:
            rules = '%s{%s}' % (media_query, rules)
        return rules

    def styles_for_block(self, metadata):
        node = copy.deepcopy(get_path(self.data, metadata['path'], {}) or {})
        use_root_padding = self.settings.get('useRootPaddingAwareAlignments') is True
        selector = metadata['selector']
        feature_decls = self.feature_declarations(metadata, node)
        is_root = selector == 'body'
        media_query = metadata.get('media_query')
        block_name = metadata.get('name')
        if block_name == 'core/paragraph':
            ti = get_path(self.settings, ('blocks', 'core/paragraph', 'typography', 'textIndent')) or \
                get_path(self.settings, ('typography', 'textIndent')) or 'subsequent'
            if ti == 'all' and '.wp-block-paragraph + .wp-block-paragraph' in feature_decls:
                feature_decls['.wp-block-paragraph'] = feature_decls.pop('.wp-block-paragraph + .wp-block-paragraph')
        var_decls = {}
        var_css = {}
        if not media_query:
            for sv in metadata.get('variations') or []:
                vnode = copy.deepcopy(get_path(self.data, sv['path'], {}) or {})
                vfeat = self.feature_declarations(metadata, vnode)
                for fsel, nd in vfeat.items():
                    var_decls[block_style_variation_feature_selector(sv, fsel)] = nd
                var_decls[sv['selector']] = self.compute_style_properties(vnode)
                for ps in BLOCK_PSEUDO.get(block_name or '', []):
                    if ps in vnode:
                        var_decls.setdefault(append_to_selector(sv['selector'], ps), []).extend(
                            self.compute_style_properties(vnode[ps]))
                if vnode.get('css'):
                    var_css[sv['selector']] = process_blocks_custom_css(vnode['css'], sv['selector'])
                for bp, mq in self.viewports.items():
                    if isinstance(vnode.get(bp), dict):
                        d = self.compute_style_properties(vnode[bp])
                        if d:
                            var_css[sv['selector']] = var_css.get(sv['selector'], '') + '%s{%s}' % (
                                mq, to_ruleset(':root :where(%s)' % sv['selector'], d))
        is_el = 'elements' in metadata['path']
        cur_el = metadata['path'][-1] if is_el else None
        pseudo = None
        for ps in ELEMENT_PSEUDO.get(cur_el, []) if cur_el else []:
            if re.search(re.escape(ps) + r'(?!-)', selector):
                pseudo = ps
                break
        if pseudo and pseudo in node:
            decls = self.compute_style_properties(node[pseudo], selector, use_root_padding)
        else:
            decls = self.compute_style_properties(node, selector, use_root_padding)
        rules = ''
        duo = [d for d in decls if d[0] == 'filter' and d[1] != 'unset']
        decls = [d for d in decls if d[0] != 'filter']
        if is_root and any(d[0] in ('background-image', 'background') for d in decls):
            rules += to_ruleset('html', [('min-height', 'calc(100% - var(--wp-admin--admin-bar--height, 0px))')])
        if selector == '.wp-block-separator':
            names = [d[0] for d in decls]
            bg = next((d[1] for d in decls if d[0] == 'background-color'), None)
            if bg and 'border-color' not in names and 'color' not in names:
                decls.append(('color', bg))
        element_only = is_root or (cur_el and cur_el in ELEMENTS and cur_el not in ELEMENT_CLASS_NAMES and ELEMENTS[cur_el] == selector)
        rules += to_ruleset(selector if element_only else ':root :where(%s)' % selector, decls)
        if metadata.get('duotone') and duo:
            rules += to_ruleset(metadata['duotone'], duo)
        if not is_root and block_name:
            rules += self.layout_styles(metadata)
        for fsel, fd in feature_decls.items():
            rules += to_ruleset(':root :where(%s)' % fsel, fd)
        for vsel, vd in var_decls.items():
            rules += to_ruleset(':root :where(%s)' % vsel, vd)
            if vsel in var_css:
                rules += var_css[vsel]
        if node.get('css') and not is_root:
            cs = get_path(metadata, ('selectors', 'css'))
            if isinstance(cs, dict):
                cs = cs.get('root')
            rules += process_blocks_custom_css(node['css'], cs if isinstance(cs, str) else selector)
        if media_query and rules:
            rules = '%s{%s}' % (media_query, rules)
        return rules

    def root_layout_rules(self, root_meta):
        css = ''
        lay = self.settings.get('layout') or {}
        if 'contentSize' in lay or 'wideSize' in lay:
            cs = lay.get('contentSize', lay.get('wideSize'))
            ws = lay.get('wideSize', lay.get('contentSize'))
            css += ':root { --wp--style--global--content-size: %s;--wp--style--global--wide-size: %s; }' % (cs, ws)
        css += ':where(body) { margin: 0; }'
        if self.settings.get('useRootPaddingAwareAlignments') is True:
            css += ('.wp-site-blocks { padding-top: var(--wp--style--root--padding-top); padding-bottom: var(--wp--style--root--padding-bottom); }'
                    '.has-global-padding { padding-right: var(--wp--style--root--padding-right); padding-left: var(--wp--style--root--padding-left); }'
                    '.has-global-padding > .alignfull { margin-right: calc(var(--wp--style--root--padding-right) * -1); margin-left: calc(var(--wp--style--root--padding-left) * -1); }'
                    '.has-global-padding :where(:not(.alignfull.is-layout-flow) > .has-global-padding:not(.wp-block-block, .alignfull)) { padding-right: 0; padding-left: 0; }'
                    '.has-global-padding :where(:not(.alignfull.is-layout-flow) > .has-global-padding:not(.wp-block-block, .alignfull)) > .alignfull { margin-left: 0; margin-right: 0; }')
        css += ('.wp-site-blocks > .alignleft { float: left; margin-right: 2em; }'
                '.wp-site-blocks > .alignright { float: right; margin-left: 2em; }'
                '.wp-site-blocks > .aligncenter { justify-content: center; margin-left: auto; margin-right: auto; }')
        if get_path(self.settings, ('spacing', 'blockGap')) is not None:
            g = self.property_value(self.data, ('styles', 'spacing', 'blockGap'))
            g = php_num(g) if isinstance(g, (int, float)) else g
            css += (':where(.wp-site-blocks) > * { margin-block-start: %s; margin-block-end: 0; }'
                    ':where(.wp-site-blocks) > :first-child { margin-block-start: 0; }'
                    ':where(.wp-site-blocks) > :last-child { margin-block-end: 0; }'
                    ':root { --wp--style--block-gap: %s; }') % (g, g)
        css += self.layout_styles(root_meta)
        return css

    def global_stylesheet(self, custom_css, used_blocks):
        """global-styles-inline-css как в wp_enqueue_global_styles() для блочной темы."""
        css = self.css_variables()
        nodes = self.style_nodes(include_blocks=False)
        css += self.root_layout_rules(nodes[0])
        for meta in nodes:
            css += self.styles_for_block(meta)
        css += self.preset_classes()
        if custom_css:
            css += custom_css
        # wp_add_global_styles_for_blocks(): стили блоков — только для блоков на странице, ПОСЛЕ custom CSS.
        for meta in self.block_nodes():
            bname = meta.get('name') or meta.get('block')
            if not bname or not block_style_present(bname, used_blocks, self.blocks):
                continue
            if not meta.get('selector'):
                continue
            css += self.styles_for_block(meta)
        return css

    def variation_stylesheet(self, block_name, variation, instance):
        """Стили одного экземпляра вариации блока (wp_render_block_style_variation_support_styles)."""
        vdata = copy.deepcopy(get_path(self.styles, ('blocks', block_name, 'variations', variation)) or {})
        if not vdata:
            return ''
        elements = vdata.pop('elements', {}) or {}
        blocks = vdata.pop('blocks', {}) or {}
        set_path(blocks, [block_name, 'variations', instance], vdata)
        cls = 'is-style-' + instance
        tj = object.__new__(ThemeJSON)
        tj.blocks = dict(self.blocks)
        meta = dict(tj.blocks.get(block_name) or {})
        sv = dict(meta.get('styleVariations') or {}) if isinstance(meta.get('styleVariations'), dict) else {}
        sv[instance] = block_style_variation_selector(instance, meta.get('selector'))
        meta['styleVariations'] = sv
        tj.blocks[block_name] = meta
        tj.warnings = self.warnings
        tj.removed = []
        tj.data = {'version': 3, 'settings': dict(self.settings, spacing=dict(self.settings.get('spacing') or {}, blockGap=True)),
                   'styles': {'elements': elements, 'blocks': blocks}}
        tj.settings = tj.data['settings']
        tj.styles = tj.data['styles']
        tj.viewports = self.viewports
        out = ''
        scope = '.' + cls
        nodes = tj.style_nodes(include_blocks=False)[1:] + tj.block_nodes(include_variations=True)
        for n in nodes:
            n = dict(n)
            n['selector'] = scope_selector(scope, n['selector']) if n.get('selector') else n.get('selector')
            if n.get('selectors'):
                fs = {}
                for f, s in n['selectors'].items():
                    fs[f] = {k: scope_selector(scope, v) for k, v in s.items()} if isinstance(s, dict) else scope_selector(scope, s)
                n['selectors'] = fs
            if n.get('selector'):
                out += tj.styles_for_block(n)
        return out


def block_supports_layout(bt):
    if not bt:
        return False
    sup = bt.get('supports') or {}
    return bool(sup.get('layout') or sup.get('__experimentalLayout'))


def block_style_present(block_name, used_blocks, blocks_meta):
    if block_name not in used_blocks:
        return False
    if not block_name.startswith('core/'):
        return True
    meta = blocks_meta.get(block_name) or {}
    handle = 'wp-block-' + block_name[5:]
    return handle in (meta.get('styleHandles') or [])


# ─────────────────────────────────────────────────────────────────────────────
# Парсер блоков (WP_Block_Parser)
# ─────────────────────────────────────────────────────────────────────────────

BLOCK_TOKEN_RE = re.compile(
    r'<!--\s+(?P<closer>/)?wp:(?P<namespace>[a-z][a-z0-9_-]*/)?(?P<name>[a-z][a-z0-9_-]*)\s+'
    r'(?P<attrs>\{(?:(?:[^}]+|}+(?=})|(?!}\s+/?-->).)*+)?}\s+)?(?P<void>/)?-->', re.S)


class Block:
    __slots__ = ('name', 'attrs', 'inner_blocks', 'inner_html', 'inner_content', 'parent_layout')

    def __init__(self, name, attrs, inner_blocks=None, inner_html='', inner_content=None):
        self.name = name
        self.attrs = attrs if isinstance(attrs, dict) else {}
        self.inner_blocks = inner_blocks if inner_blocks is not None else []
        self.inner_html = inner_html
        self.inner_content = inner_content if inner_content is not None else []
        self.parent_layout = None


def parse_blocks(document, warnings=None):
    output, stack = [], []
    offset = 0
    n = len(document)

    def freeform(html):
        return Block(None, {}, [], html, [html])

    def add_inner(block, token_start, token_length, last_offset=None):
        parent = stack[-1]
        parent['block'].inner_blocks.append(block)
        html = document[parent['prev']:token_start]
        if html:
            parent['block'].inner_html += html
            parent['block'].inner_content.append(html)
        parent['block'].inner_content.append(None)
        parent['prev'] = last_offset if last_offset else token_start + token_length

    def add_from_stack(end=None):
        top = stack.pop()
        html = document[top['prev']:end] if end is not None else document[top['prev']:]
        if html:
            top['block'].inner_html += html
            top['block'].inner_content.append(html)
        if top['leading'] is not None:
            output.append(freeform(document[top['leading']:top['start']]))
        output.append(top['block'])

    while True:
        m = BLOCK_TOKEN_RE.search(document, offset)
        depth = len(stack)
        if not m:
            if depth == 0:
                if n - offset:
                    output.append(freeform(document[offset:]))
            else:
                if warnings is not None:
                    warnings.append('Блок %s не закрыт (нет <!-- /wp:... -->)' % stack[-1]['block'].name)
                while stack:
                    add_from_stack()
            break
        start, length = m.start(), m.end() - m.start()
        leading = offset if start > offset else None
        name = (m.group('namespace') or 'core/') + m.group('name')
        attrs = {}
        if m.group('attrs'):
            try:
                attrs = json.loads(m.group('attrs'))
            except Exception as e:
                if warnings is not None:
                    warnings.append('Невалидный JSON атрибутов блока %s: %s' % (name, e))
                attrs = {}
        if m.group('closer'):
            kind = 'closer'
        elif m.group('void'):
            kind = 'void'
        else:
            kind = 'opener'
        if kind == 'void':
            b = Block(name, attrs)
            if depth == 0:
                if leading is not None:
                    output.append(freeform(document[leading:start]))
                output.append(b)
            else:
                add_inner(b, start, length)
            offset = start + length
        elif kind == 'opener':
            stack.append({'block': Block(name, attrs), 'start': start, 'length': length,
                          'prev': start + length, 'leading': leading})
            offset = start + length
        else:
            if depth == 0:
                if warnings is not None:
                    warnings.append('Лишний закрывающий комментарий <!-- /wp:%s -->' % m.group('name'))
                output.append(freeform(document[offset:]))
                break
            if stack[-1]['block'].name != name and warnings is not None:
                warnings.append('Закрывающий <!-- /wp:%s --> не совпадает с открытым %s' % (name, stack[-1]['block'].name))
            if depth == 1:
                add_from_stack(start)
                offset = start + length
                continue
            top = stack.pop()
            html = document[top['prev']:start]
            top['block'].inner_html += html
            top['block'].inner_content.append(html)
            top['prev'] = start + length
            add_inner(top['block'], top['start'], top['length'], start + length)
            offset = start + length
    return output


# ─────────────────────────────────────────────────────────────────────────────
# wptexturize (упрощённо, ru_RU) и wp_filter_content_tags
# ─────────────────────────────────────────────────────────────────────────────

NO_TEXTURIZE = {'pre', 'code', 'kbd', 'style', 'script', 'tt', 'textarea'}


def _texturize_text(t):
    if not t.strip():
        return t
    t = t.replace('---', '\u2014').replace(' -- ', ' \u2014 ').replace('--', '\u2013').replace(' - ', ' \u2013 ')
    t = t.replace('...', '\u2026').replace(' (tm)', ' \u2122')
    t = re.sub(r'(?<=\w)\'(?=\w)', '\u2019', t)
    t = re.sub(r'(?:(?<=^)|(?<=[\s(\[{\-]))"(?=\S)', '\u00ab', t)
    t = t.replace('"', '\u00bb')
    t = re.sub(r'\b(\d[\d.,]*)x(\d[\d.,]*)\b', '\\1\u00d7\\2', t)
    return t


def wptexturize(s):
    out = []
    pos = 0
    skip = 0
    for t in iter_tags(s):
        text = s[pos:t.start]
        # комментарии внутри текста не трогаем
        out.append(_texturize_segment(text) if not skip else text)
        out.append(s[t.start:t.end])
        if t.name in NO_TEXTURIZE:
            if t.closer:
                skip = max(0, skip - 1)
            elif not t.self_closing:
                skip += 1
        pos = t.end
    tail = s[pos:]
    out.append(_texturize_segment(tail) if not skip else tail)
    return ''.join(out)


def _texturize_segment(text):
    parts = re.split(r'(<!--.*?-->|\[[^\]]*\])', text, flags=re.S)
    return ''.join(p if (p.startswith('<!--') or p.startswith('[')) else _texturize_text(p) for p in parts)


# ─────────────────────────────────────────────────────────────────────────────
# Рендерер
# ─────────────────────────────────────────────────────────────────────────────

class Renderer:
    def __init__(self, theme, blocks_meta, media, post, system, warnings):
        self.theme = theme
        self.blocks = blocks_meta
        self.media = media
        self.post = post            # dict: id, title, permalink, front, template
        self.system = system        # SystemFiles
        self.warnings = warnings
        self.store = CssStore()     # core-block-supports-inline-css
        self.variation_css = []     # block-style-variation-styles-inline-css
        self.used_blocks = set()
        self.uid = 0                # wp_unique_id()
        self.prefixed = {}          # wp_unique_prefixed_id()
        self.seen_nav_names = {}
        self.lightbox = False
        self.tp_stack = []
        self.content_images = 0
        self.unknown_blocks = set()
        self.global_styles = theme.styles

    # ---- служебное
    def unique_id(self, prefix=''):
        """wp_unique_id(): один глобальный счётчик на все префиксы."""
        self.uid += 1
        return '%s%d' % (prefix, self.uid)

    def unique_prefixed_id(self, prefix):
        """wp_unique_prefixed_id(): свой счётчик у каждого префикса."""
        self.prefixed[prefix] = self.prefixed.get(prefix, 0) + 1
        return '%s%d' % (prefix, self.prefixed[prefix])

    def warn(self, msg):
        if msg not in self.warnings:
            self.warnings.append(msg)

    def bt(self, name):
        return self.blocks.get(name) or {}

    def supports(self, name, path, default=None):
        return get_path(self.bt(name).get('supports') or {}, path, default)

    def skip_serialization(self, name, feature_set, feature=None):
        v = self.supports(name, (feature_set, '__experimentalSkipSerialization'), False)
        if isinstance(v, list):
            return feature in v
        return bool(v)

    def attrs_with_defaults(self, block):
        a = dict(self.bt(block.name).get('defaults') or {})
        a.update(block.attrs)
        return a

    # ---- block supports для динамических блоков (get_block_wrapper_attributes)
    def wrapper_attributes(self, name, attrs, extra=None):
        extra = extra or {}
        new = {'class': [], 'style': []}
        sup = self.bt(name).get('supports') or {}

        # align
        if sup.get('align') and attrs.get('align'):
            new['class'].append('align%s' % attrs['align'])
        # custom className
        if sup.get('customClassName', True) and isinstance(attrs.get('className'), str) and attrs['className'].strip():
            new['class'].append(attrs['className'].strip())
        # generated class
        if sup.get('className', True):
            new['class'].append(default_block_classname(name))
        # colors
        cs = sup.get('color', False)
        if cs and not (isinstance(cs, dict) and self.skip_serialization(name, 'color')):
            st = {}
            text_ok = cs is True or (isinstance(cs, dict) and (cs.get('text', True)))
            bg_ok = cs is True or (isinstance(cs, dict) and (cs.get('background', True)))
            if text_ok and not self.skip_serialization(name, 'color', 'text'):
                st['text'] = ('var:preset|color|%s' % attrs['textColor']) if 'textColor' in attrs else get_path(attrs, ('style', 'color', 'text'))
            if bg_ok and not self.skip_serialization(name, 'color', 'background'):
                st['background'] = ('var:preset|color|%s' % attrs['backgroundColor']) if 'backgroundColor' in attrs else get_path(attrs, ('style', 'color', 'background'))
            if isinstance(cs, dict) and cs.get('gradients') and not self.skip_serialization(name, 'color', 'gradients'):
                st['gradient'] = ('var:preset|gradient|%s' % attrs['gradient']) if 'gradient' in attrs else get_path(attrs, ('style', 'color', 'gradient'))
            d, c = style_engine({'color': {k: v for k, v in st.items() if v is not None}}, convert_vars_to_classnames=True)
            new['class'] += c
            if d:
                new['style'].append(decls_to_css(d))
        # typography
        ts = sup.get('typography') or {}
        if ts and not self.skip_serialization(name, 'typography'):
            st = {}
            sty = get_path(attrs, ('style', 'typography'), {}) or {}
            if ts.get('fontSize') and not self.skip_serialization(name, 'typography', 'fontSize'):
                if 'fontSize' in attrs:
                    st['fontSize'] = 'var:preset|font-size|%s' % attrs['fontSize']
                elif sty.get('fontSize') is not None:
                    st['fontSize'] = typography_font_size_value({'size': sty['fontSize']}, self.theme.settings)
            if ts.get('__experimentalFontFamily') and not self.skip_serialization(name, 'typography', 'fontFamily'):
                if 'fontFamily' in attrs:
                    st['fontFamily'] = 'var:preset|font-family|%s' % attrs['fontFamily']
                elif sty.get('fontFamily'):
                    st['fontFamily'] = preset_inline_value(sty['fontFamily'], 'font-family')
            for key, flag, prop in (('fontStyle', '__experimentalFontStyle', 'font-style'),
                                    ('fontWeight', '__experimentalFontWeight', 'font-weight'),
                                    ('textDecoration', '__experimentalTextDecoration', 'text-decoration'),
                                    ('textTransform', '__experimentalTextTransform', 'text-transform'),
                                    ('letterSpacing', '__experimentalLetterSpacing', 'letter-spacing')):
                if ts.get(flag) and not self.skip_serialization(name, 'typography', key) and key in sty:
                    st[key] = preset_inline_value(sty[key], prop)
            if ts.get('lineHeight') and not self.skip_serialization(name, 'typography', 'lineHeight') and 'lineHeight' in sty:
                st['lineHeight'] = sty['lineHeight']
            if ts.get('textColumns') and 'textColumns' in sty:
                st['textColumns'] = sty['textColumns']
            if ts.get('__experimentalWritingMode') and 'writingMode' in sty:
                st['writingMode'] = sty['writingMode']
            if ts.get('textIndent') and 'textIndent' in sty:
                st['textIndent'] = sty['textIndent']
            d, c = style_engine({'typography': st}, convert_vars_to_classnames=True)
            new['class'] += c
            if ts.get('textAlign') and not self.skip_serialization(name, 'typography', 'textAlign') and sty.get('textAlign'):
                new['class'].append('has-text-align-%s' % sty['textAlign'])
            if d:
                new['style'].append(decls_to_css(d))
        # border
        bs = sup.get('__experimentalBorder') or {}
        if bs and not self.skip_serialization(name, '__experimentalBorder'):
            st = {}
            sty = get_path(attrs, ('style', 'border'), {}) or {}
            if bs.get('color') and not self.skip_serialization(name, '__experimentalBorder', 'color'):
                if 'borderColor' in attrs:
                    st['color'] = 'var:preset|color|%s' % attrs['borderColor']
                elif sty.get('color'):
                    st['color'] = sty['color']
                for side in ('top', 'right', 'bottom', 'left'):
                    if isinstance(sty.get(side), dict):
                        st.setdefault(side, {}).update({k: v for k, v in sty[side].items()})
            if bs.get('radius') and sty.get('radius') is not None:
                st['radius'] = sty['radius']
            if bs.get('style') and sty.get('style'):
                st['style'] = sty['style']
            if bs.get('width') and sty.get('width') is not None:
                st['width'] = sty['width']
            d, c = style_engine({'border': st})
            dc, cc = style_engine({'border': {'color': st.get('color')}} if st.get('color') else {}, convert_vars_to_classnames=True)
            new['class'] += cc
            if d:
                new['style'].append(decls_to_css(d))
        # spacing
        ss = sup.get('spacing') or {}
        if ss and not self.skip_serialization(name, 'spacing'):
            st = {}
            sp = get_path(attrs, ('style', 'spacing'), {}) or {}
            if ss.get('padding') and not self.skip_serialization(name, 'spacing', 'padding') and sp.get('padding') is not None:
                st['padding'] = sp['padding']
            if ss.get('margin') and not self.skip_serialization(name, 'spacing', 'margin') and sp.get('margin') is not None:
                st['margin'] = sp['margin']
            d, _ = style_engine({'spacing': st})
            if d:
                new['style'].append(decls_to_css(d))
        # dimensions
        ds = sup.get('dimensions') or {}
        if ds and not self.skip_serialization(name, 'dimensions'):
            dim = get_path(attrs, ('style', 'dimensions'), {}) or {}
            st = {k: dim[k] for k in ('minHeight', 'height', 'width', 'minWidth') if ds.get(k) and dim.get(k) is not None}
            d, _ = style_engine({'dimensions': st})
            if d:
                new['style'].append(decls_to_css(d))
        # shadow
        if sup.get('shadow') and not self.skip_serialization(name, 'shadow') and get_path(attrs, ('style', 'shadow')):
            d, _ = style_engine({'shadow': get_path(attrs, ('style', 'shadow'))})
            if d:
                new['style'].append(decls_to_css(d))
        res = {}
        cls_new = ' '.join(c for c in new['class'] if c)
        sty_new = ' '.join(s for s in new['style'] if s)
        if sup.get('ariaLabel') and attrs.get('ariaLabel'):
            new_aria = attrs['ariaLabel']
        else:
            new_aria = None
        anchor = attrs.get('anchor') if sup.get('anchor') else None
        for key, newv in (('style', sty_new), ('class', cls_new), ('id', anchor), ('aria-label', new_aria)):
            ev = extra.get(key)
            if php_empty(newv) and php_empty(ev):
                continue
            if php_empty(newv):
                res[key] = ev
            elif php_empty(ev):
                res[key] = newv
            else:
                res[key] = '%s %s' % (ev, newv)
        for k, v in extra.items():
            if k not in ('style', 'class', 'id', 'aria-label'):
                res[k] = v
        return ' '.join('%s="%s"' % (k, esc_attr(v)) for k, v in res.items())

    # ---- render_block_data
    def prepare_block(self, block, parent):
        name = block.name
        # parent layout
        if parent is not None and isinstance(parent.attrs.get('layout'), dict):
            block.parent_layout = parent.attrs['layout']
        # gallery data-id
        if name == 'core/gallery':
            for ib in block.inner_blocks:
                if ib.name == 'core/image' and 'data-id' not in ib.attrs and 'id' in ib.attrs:
                    ib.attrs['data-id'] = str(ib.attrs['id'])
        # elements support
        self.elements_support(block)
        # block style variations
        self.variation_support(block)
        # custom css (style.css у блока)
        css = get_path(block.attrs, ('style', 'css'))
        if isinstance(css, str) and css.strip() and self.supports(name, ('customCSS',), True) and not re.search(r'</?\w+', css):
            cls = wp_unique_id_from_values(self._parsed_dict(block), 'wp-custom-css-')
            block.attrs['className'] = ((block.attrs.get('className') or '') + ' ' + cls).strip()
            self.variation_css.append(process_blocks_custom_css(css, '.' + cls))

    def _parsed_dict(self, b):
        return {'blockName': b.name, 'attrs': b.attrs,
                'innerBlocks': [self._parsed_dict(x) for x in b.inner_blocks],
                'innerHTML': b.inner_html, 'innerContent': b.inner_content}

    def elements_support(self, block):
        el = get_path(block.attrs, ('style', 'elements'))
        if not isinstance(el, dict) or not el or not self.blocks.get(block.name):
            return
        skip = {k: self.skip_serialization(block.name, 'color', k) for k in ('link', 'heading', 'button')}
        if all(skip.values()):
            return
        paths = {
            'button': [('button', 'color', 'text'), ('button', 'color', 'background'), ('button', 'color', 'gradient')],
            'link': [('link', 'color', 'text'), ('link', ':hover', 'color', 'text')],
            'heading': [(h, 'color', p) for h in ('heading', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6') for p in ('text', 'background', 'gradient')],
        }
        if not any(get_path(el, p) is not None for k, ps in paths.items() if not skip[k] for p in ps):
            return
        cls = self.unique_prefixed_id('wp-elements-')
        block.attrs['className'] = ((block.attrs.get('className') or '') + ' ' + cls).strip()
        types = {
            'button': ('.%s .wp-element-button, .%s .wp-block-button__link' % (cls, cls), None, None),
            'link': ('.%s a:where(:not(.wp-element-button))' % cls, '.%s a:where(:not(.wp-element-button)):hover' % cls, None),
            'heading': (', '.join('.%s h%d' % (cls, i) for i in range(1, 7)), None, ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']),
        }
        for t, (sel, hover, subs) in types.items():
            if skip[t]:
                continue
            obj = el.get(t)
            if isinstance(obj, dict):
                d, _ = style_engine(obj)
                self.store.add(sel, d)
                if hover and isinstance(obj.get(':hover'), dict):
                    d, _ = style_engine(obj[':hover'])
                    self.store.add(hover, d)
            for sub in subs or []:
                if isinstance(el.get(sub), dict):
                    d, _ = style_engine(el[sub])
                    self.store.add('.%s %s' % (cls, sub), d)

    def variation_support(self, block):
        cls = block.attrs.get('className')
        if not isinstance(cls, str) or 'is-style-' not in cls:
            return
        names = re.findall(r'\bis-style-(?!default)(\S+)\b', cls)
        for vn in names:
            data = get_path(self.theme.styles, ('blocks', block.name, 'variations', vn))
            if data:
                instance = self.unique_id(vn + '--')
                css = self.theme.variation_stylesheet(block.name, vn, instance)
                if css:
                    self.variation_css.append(css)
                    block.attrs['className'] = cls + ' is-style-' + instance
                break

    # ---- основной рендер
    def render_blocks(self, blocks, parent=None, context=None):
        return ''.join(self.render_block(b, parent, context or {}) for b in blocks)

    def render_block(self, block, parent=None, context=None):
        context = context or {}
        if block.name is None:
            return block.inner_html
        self.prepare_block(block, parent)
        name = block.name
        bt = self.blocks.get(name)
        if bt is None:
            self.warn('Неизвестный блок %s — выведен сохранённый HTML как есть' % name)
        self.used_blocks.add(name)
        child_ctx = dict(context)
        if bt:
            for key, attr in (bt.get('providesContext') or {}).items():
                child_ctx[key] = self.attrs_with_defaults(block).get(attr)
        if name == 'core/gallery':
            child_ctx['galleryId'] = hashlib.md5(block.inner_html.encode()).hexdigest()[:13]
        # контент: WP_Block::render() всегда сначала рендерит внутренние блоки (и для динамических тоже —
        # navigation потом рендерит детей ещё раз, поэтому счётчики wp_unique_id растут как в WP)
        content = ''
        idx = 0
        for chunk in block.inner_content:
            if chunk is None:
                content += self.render_block(block.inner_blocks[idx], block, child_ctx)
                idx += 1
            else:
                content += chunk
        # динамический рендер
        fn = DYNAMIC.get(name)
        if fn is not None:
            content = fn(self, self.attrs_with_defaults(block), content, block, child_ctx, context)
        elif bt and bt.get('dynamic') and name not in STATIC_OK:
            self.warn('Динамический блок %s не эмулируется — выведен сохранённый HTML' % name)
        # render_block фильтры (в порядке регистрации в WP)
        content = self.f_typography(content, block)
        content = self.f_elements_class(content, block)
        content = self.f_layout(content, block)
        content = self.f_position(content, block)
        content = self.f_dimensions(content, block)
        content = self.f_background(content, block)
        content = self.f_variation_class(content, block)
        content = self.f_visibility(content, block)
        content = self.f_custom_css_class(content, block)
        # render_block_{name}
        if name == 'core/paragraph' and content:
            content = add_class_first(content, ['wp-block-paragraph'], 'p')
        return content

    # ---- render_block фильтры
    def f_typography(self, content, block):
        fs = get_path(block.attrs, ('style', 'typography', 'fontSize'))
        if fs is None:
            return content
        fluid = typography_font_size_value({'size': fs}, self.theme.settings)
        if fluid and fluid != fs:
            return re.sub(r'font-size\s*:\s*' + re.escape(str(fs)) + r'\s*;?', 'font-size:' + esc_attr(fluid) + ';', content, count=1)
        return content

    def f_elements_class(self, content, block):
        cls = block.attrs.get('className')
        if not isinstance(cls, str) or 'wp-elements-' not in cls:
            return content
        m = next((c for c in cls.split() if c.startswith('wp-elements-')), None)
        return add_class_first(content, [m]) if m else content

    def f_variation_class(self, content, block):
        cls = block.attrs.get('className')
        if not isinstance(cls, str):
            return content
        m = re.search(r'\bis-style-(\S+?--\d+)\b', cls)
        return add_class_first(content, [m.group(0)]) if m else content

    def f_custom_css_class(self, content, block):
        cls = block.attrs.get('className')
        if not isinstance(cls, str):
            return content
        inst = [c for c in cls.split() if c.startswith('wp-custom-css-')]
        return add_class_first(content, inst) if inst else content

    def f_position(self, content, block):
        pos = get_path(block.attrs, ('style', 'position'))
        if not isinstance(pos, dict) or not self.supports(block.name, ('position',)):
            return content
        ptype = pos.get('type')
        if ptype not in ('sticky', 'fixed'):
            return content
        if ptype == 'sticky' and not get_path(self.theme.settings, ('position', 'sticky')):
            return content
        cls = self.unique_id('wp-container-')
        sel = '.' + cls
        for side in ('top', 'right', 'bottom', 'left'):
            v = pos.get(side)
            if v is not None:
                if side == 'top':
                    if v in ('0', 0):
                        v = '0px'
                    v = 'calc(%s + var(--wp-admin--admin-bar--position-offset, 0px))' % v
                self.store.add(sel, {side: v})
        self.store.add(sel, {'position': ptype, 'z-index': '10'})
        return add_class_first(content, [cls, 'is-position-' + ptype])

    def f_dimensions(self, content, block):
        if not self.supports(block.name, ('dimensions', 'aspectRatio')) or self.skip_serialization(block.name, 'dimensions', 'aspectRatio'):
            return content
        ar = get_path(block.attrs, ('style', 'dimensions', 'aspectRatio'))
        st = {}
        if ar and ar != 'auto':
            st = {'aspectRatio': ar, 'minHeight': 'unset', 'height': 'unset'}
        elif get_path(block.attrs, ('style', 'dimensions', 'minHeight')) is not None or 'minHeight' in block.attrs:
            st = {'aspectRatio': 'unset'}
        d, c = style_engine({'dimensions': st})
        if not d:
            return content
        content = append_style_first(content, decls_to_css(d))
        if ar and ar != 'auto':
            content = add_class_first(content, [x for x in c])
        return content

    def f_background(self, content, block):
        bg = get_path(block.attrs, ('style', 'background'))
        if not isinstance(bg, dict):
            return content
        has_img = self.supports(block.name, ('background', 'backgroundImage'))
        has_grad = self.supports(block.name, ('background', 'gradient'))
        if not has_img and not has_grad:
            return content
        st = {}
        if has_img and not self.skip_serialization(block.name, 'background', 'backgroundImage'):
            for k in ('backgroundImage', 'backgroundSize', 'backgroundPosition', 'backgroundRepeat', 'backgroundAttachment'):
                st[k] = bg.get(k)
            if not php_empty(st['backgroundImage']):
                st['backgroundSize'] = st['backgroundSize'] or 'cover'
                if st['backgroundSize'] == 'contain' and not st['backgroundPosition']:
                    st['backgroundPosition'] = '50% 50%'
        if has_grad and not self.skip_serialization(block.name, 'background', 'gradient'):
            st['gradient'] = bg.get('gradient')
        d, _ = style_engine({'background': {k: v for k, v in st.items() if v is not None}})
        if not d:
            return content
        content = append_style_first(content, decls_to_css(d))
        return add_class_first(content, ['has-background'])

    def f_visibility(self, content, block):
        vis = get_path(block.attrs, ('metadata', 'blockVisibility'))
        if vis is False:
            return ''
        if not isinstance(vis, dict) or not isinstance(vis.get('viewport'), dict):
            return content
        mqs = {k.lstrip('@'): v for k, v in viewport_media_queries(self.theme.settings.get('viewport'), True).items()}
        hidden = sorted(k for k, v in vis['viewport'].items() if v is False and k in mqs)
        if not hidden or not content:
            return content
        classes = []
        for h in hidden:
            c = 'wp-block-hidden-' + h
            classes.append(c)
            self.store.add('.' + c, {'display': 'none !important'}, mqs[h])
        return add_class_first(content, classes)

    def f_layout(self, content, block):
        """wp_render_layout_support_flag()."""
        name = block.name
        bt = self.blocks.get(name)
        if not bt:
            return content
        supports_layout = block_supports_layout(bt)
        style_attr = block.attrs.get('style') if isinstance(block.attrs.get('style'), dict) else {}
        if not supports_layout and not style_attr:
            return content
        child = style_attr.get('layout') if isinstance(style_attr.get('layout'), dict) else None
        outer = []
        if child:
            base_child = {k: v for k, v in child.items() if k in ('selfStretch', 'flexSize', 'columnStart', 'columnSpan', 'rowStart', 'rowSpan')}
            parent_layout = block.parent_layout or {}
            hash_in = {'layout': base_child if base_child else [],
                       'parentLayout': {k: v for k, v in parent_layout.items() if k in ('minimumColumnWidth', 'columnCount')} or []}
            ccls = wp_unique_id_from_values(hash_in, 'wp-container-content-')
            rules = child_layout_rules('.' + ccls, base_child, parent_layout)
            if rules:
                for r in rules:
                    self.store.add(r['selector'], r['declarations'], r.get('rules_group', ''))
                outer.append(ccls)
        if not first_tag(content):
            return content
        if not supports_layout:
            return add_class_first(content, outer) if outer else content
        fallback = get_path(bt, ('supports', 'layout', 'default')) or get_path(bt, ('supports', '__experimentalLayout', 'default')) or []
        used = block.attrs.get('layout') if 'layout' in block.attrs else fallback
        used = dict(used) if isinstance(used, dict) else {}
        if used.get('inherit') or used.get('contentSize'):
            used['type'] = 'constrained'
        used_for_hash = used if used else []
        classes = []
        if self.theme.settings.get('useRootPaddingAwareAlignments') and used.get('type') == 'constrained':
            classes.append('has-global-padding')
        battr_layout = block.attrs.get('layout') if isinstance(block.attrs.get('layout'), dict) else {}
        if battr_layout.get('orientation'):
            classes.append('is-' + sanitize_title(battr_layout['orientation']))
        if battr_layout.get('justifyContent'):
            classes.append('is-content-justification-' + sanitize_title(battr_layout['justifyContent']))
        if battr_layout.get('flexWrap') == 'nowrap':
            classes.append('is-nowrap')
        ltype = used.get('type', 'default')
        layout_classname = (LAYOUT_DEFINITIONS.get(ltype) or {}).get('className', '')
        if layout_classname:
            classes.append(layout_classname)
        # стили контейнера
        gap_value = sanitize_gap(get_path(style_attr, ('spacing', 'blockGap')))
        fallback_gap = get_path(bt, ('supports', 'spacing', 'blockGap', '__experimentalDefault'), '0.5em')
        block_spacing = style_attr.get('spacing') if 'spacing' in style_attr else None
        skip_gap = self.skip_serialization(name, 'spacing', 'blockGap')
        has_gap_support = get_path(self.theme.settings, ('spacing', 'blockGap')) is not None
        gstyles = self.global_styles
        var_gap = None
        cls_attr = block.attrs.get('className') if isinstance(block.attrs.get('className'), str) else ''
        if 'is-style-' in cls_attr:
            regs = self.bt(name).get('styleVariations')
            regs = list(regs.keys()) if isinstance(regs, dict) else []
            for c in cls_attr.split():
                if c.startswith('is-style-') and c[9:] != 'default' and c[9:] in regs:
                    var_gap = get_path(gstyles, ('blocks', name, 'variations', c[9:], 'spacing', 'blockGap'))
                    break
        ggap = var_gap if var_gap is not None else (get_path(gstyles, ('blocks', name, 'spacing', 'blockGap'))
                                                    if get_path(gstyles, ('blocks', name, 'spacing', 'blockGap')) is not None
                                                    else get_path(gstyles, ('spacing', 'blockGap')))
        if ggap is not None:
            fallback_gap = ggap
        hash_in = [used_for_hash, has_gap_support, gap_value, skip_gap, fallback_gap, block_spacing]
        ccls = wp_unique_id_from_values(hash_in, 'wp-container-' + sanitize_title(name) + '-is-layout-')
        rules = layout_style_rules('.' + ccls, used, has_gap_support, gap_value, skip_gap, fallback_gap, block_spacing)
        if rules:
            for r in rules:
                self.store.add(r['selector'], r['declarations'], r.get('rules_group', ''))
            classes.append(ccls)
        split = name.split('/')
        full = split[-1] if split[0] == 'core' else '-'.join(split)
        classes.append('wp-block-%s-%s' % (full, layout_classname))
        if outer:
            content = add_class_first(content, outer)
        # поиск обёртки внутренних блоков (как в WP 7.1)
        wrapper_cls = None
        first = block.inner_content[0] if block.inner_content else None
        if isinstance(first, str) and len(block.inner_content) > 1:
            stack = []
            for t in iter_tags(first):
                if t.closer:
                    if stack:
                        stack.pop()
                elif t.name not in VOID_TAGS:
                    stack.append(get_attr(first, t, 'class'))
            for c in reversed(stack):
                if isinstance(c, str) and c:
                    wrapper_cls = c
                    break
        target = None
        for t in iter_tags(content):
            if t.closer:
                continue
            if target is None:
                target = t
                if not wrapper_cls:
                    break
            c = get_attr(content, t, 'class')
            if wrapper_cls and isinstance(c, str) and wrapper_cls in c:
                target = t
                break
        else:
            if wrapper_cls:
                target = None
        if target is None:
            return content
        return add_classes(content, target, classes)


def sanitize_title(s):
    s = str(s).lower()
    s = re.sub(r'[^a-z0-9_\-\s/]', '', s)
    s = re.sub(r'[\s/]+', '-', s)
    return re.sub(r'-+', '-', s).strip('-')


def sanitize_gap(v):
    if isinstance(v, dict):
        return {k: (None if (not isinstance(x, (str, int, float)) or (x and re.search(r'[\\(&=}]|/\*', str(x)))) else x)
                for k, x in v.items()}
    if v and isinstance(v, str) and re.search(r'[\\(&=}]|/\*', v):
        return None
    return v


def default_block_classname(name):
    return 'wp-block-' + re.sub(r'^core-', '', name.replace('/', '-'))


def preset_inline_value(value, prop):
    if not isinstance(value, str) or 'var:preset|' not in value:
        return value
    idx = value.rfind('|')
    slug = value[idx + 1:]
    return 'var(--wp--preset--%s--%s)' % (prop, slug)


def _gap_css(value):
    if isinstance(value, str) and 'var:preset|spacing|' in value:
        return 'var(--wp--preset--spacing--%s)' % kebab(value[value.rfind('|') + 1:])
    return value


def child_layout_rules(selector, child, parent_layout):
    decls = {}
    ss = child.get('selfStretch')
    if ss in ('fixed', 'fixedNoShrink') and child.get('flexSize') is not None:
        decls['flex-basis'] = child['flexSize']
        if ss == 'fixedNoShrink':
            decls['flex-shrink'] = '0'
        decls['box-sizing'] = 'border-box'
    elif ss == 'fill':
        decls['flex-grow'] = '1'
    cs, cspan = child.get('columnStart'), child.get('columnSpan')
    if cs and cspan:
        decls['grid-column'] = '%s / span %s' % (cs, cspan)
    elif cs:
        decls['grid-column'] = str(cs)
    elif cspan:
        decls['grid-column'] = 'span %s' % cspan
    rs, rspan = child.get('rowStart'), child.get('rowSpan')
    if rs and rspan:
        decls['grid-row'] = '%s / span %s' % (rs, rspan)
    elif rs:
        decls['grid-row'] = str(rs)
    elif rspan:
        decls['grid-row'] = 'span %s' % rspan
    rules = []
    if decls:
        rules.append({'selector': selector, 'declarations': decls})
    mcw, cc = parent_layout.get('minimumColumnWidth'), parent_layout.get('columnCount')
    if (cspan or cs) and (mcw or not cc):
        span_n = float(cspan or 0)
        start_n = float(cs or 0)
        pcw = mcw or '12rem'
        m = re.match(r'^(\d*\.?\d+)([a-z]*)$', str(pcw))
        if m and m.group(2) in ('px', 'rem', 'em'):
            val, unit = float(m.group(1)), m.group(2)
        else:
            val, unit = 12.0, 'rem'
        if span_n and start_n:
            n = start_n + span_n - 1
        elif span_n:
            n = span_n
        else:
            n = start_n
        g = 24 if unit == 'px' else 1.5
        q = max(n * val + (n - 1) * g, val * 2 + g - 1)
        rules.append({'rules_group': '@container (max-width: %s%s )' % (php_num(q), unit), 'selector': selector,
                      'declarations': {'grid-column': '1/-1' if cspan and float(cspan) > 1 else 'auto', 'grid-row': 'auto'}})
    return rules


def layout_style_rules(selector, layout, has_gap_support, gap_value, skip_gap, fallback_gap, block_spacing):
    """wp_get_layout_style() без viewport-переопределений → список правил."""
    rules = []
    ltype = layout.get('type', 'default')

    def add(sel, decls):
        rules.append({'selector': sel, 'declarations': decls})

    if ltype in ('default', 'constrained'):
        if ltype == 'constrained':
            cs = layout.get('contentSize') or ''
            ws = layout.get('wideSize') or ''
            jc = layout.get('justifyContent') or 'center'
            all_max = cs or ws or 'var(--wp--style--global--content-size, none)'
            wide_max = ws or cs or 'var(--wp--style--global--wide-size, none)'
            all_max = str(all_max).split(';')[0]
            wide_max = str(wide_max).split(';')[0]
            ml = '0 !important' if jc == 'left' else 'auto !important'
            mr = '0 !important' if jc == 'right' else 'auto !important'
            if cs or ws:
                add(selector + ' > :where(:not(.alignleft):not(.alignright):not(.alignfull))',
                    {'max-width': all_max, 'margin-left': ml, 'margin-right': mr})
                add(selector + ' > .alignwide', {'max-width': wide_max})
                add(selector + ' .alignfull', {'max-width': 'none'})
            if block_spacing is not None:
                d, _ = style_engine({'spacing': block_spacing})
                if 'padding-right' in d:
                    pr = d['padding-right']
                    pr = '0px' if pr == '0' else pr
                    add(selector + ' > .alignfull', {'margin-right': 'calc(%s * -1)' % pr})
                if 'padding-left' in d:
                    pl = d['padding-left']
                    pl = '0px' if pl == '0' else pl
                    add(selector + ' > .alignfull', {'margin-left': 'calc(%s * -1)' % pl})
            if jc == 'left':
                add(selector + ' > :where(:not(.alignleft):not(.alignright):not(.alignfull))', {'margin-left': '0 !important'})
            if jc == 'right':
                add(selector + ' > :where(:not(.alignleft):not(.alignright):not(.alignfull))', {'margin-right': '0 !important'})
        if has_gap_support:
            g = gap_value.get('top') if isinstance(gap_value, dict) else gap_value
            if g is not None and not skip_gap:
                g = _gap_css(g)
                add(selector + ' > *', {'margin-block-start': '0', 'margin-block-end': '0'})
                add(selector + ' > * + *', {'margin-block-start': g, 'margin-block-end': '0'})
    elif ltype == 'flex':
        orient = layout.get('orientation', 'horizontal')
        jopts = {'left': 'flex-start', 'right': 'flex-end', 'center': 'center'}
        vopts = {'top': 'flex-start', 'center': 'center', 'bottom': 'flex-end'}
        if orient == 'horizontal':
            jopts['space-between'] = 'space-between'
            vopts['stretch'] = 'stretch'
        else:
            jopts['stretch'] = 'stretch'
            vopts['space-between'] = 'space-between'
        if layout.get('flexWrap') == 'nowrap':
            add(selector, {'flex-wrap': 'nowrap'})
        if has_gap_support and gap_value is not None:
            sides = ['top', 'left'] if isinstance(gap_value, dict) else ['top']
            vals = []
            for side in sides:
                pv = gap_value
                if isinstance(gap_value, dict):
                    fb = (fallback_gap.get(side) if side in fallback_gap else next(iter(fallback_gap.values()), None)) if isinstance(fallback_gap, dict) else fallback_gap
                    pv = gap_value.get(side) if gap_value.get(side) is not None else fb
                vals.append(str(_gap_css(pv)))
            g = ' '.join(vals).strip()
            if not skip_gap:
                add(selector, {'gap': g})
        if orient == 'horizontal':
            if layout.get('justifyContent') in jopts:
                add(selector, {'justify-content': jopts[layout['justifyContent']]})
            if layout.get('verticalAlignment') in vopts:
                add(selector, {'align-items': vopts[layout['verticalAlignment']]})
        else:
            add(selector, {'flex-direction': 'column'})
            if layout.get('justifyContent') in jopts:
                add(selector, {'align-items': jopts[layout['justifyContent']]})
            else:
                add(selector, {'align-items': 'flex-start'})
            if layout.get('verticalAlignment') in vopts:
                add(selector, {'justify-content': vopts[layout['verticalAlignment']]})
    elif ltype == 'grid':
        resp_gap = (fallback_gap.get('left') if 'left' in fallback_gap else next(iter(fallback_gap.values()), None)) if isinstance(fallback_gap, dict) else fallback_gap
        g = None
        if has_gap_support and gap_value is not None:
            sides = ['top', 'left'] if isinstance(gap_value, dict) else ['top']
            vals = []
            for side in sides:
                pv = gap_value
                if isinstance(gap_value, dict):
                    fb = (fallback_gap.get(side) if side in fallback_gap else next(iter(fallback_gap.values()), None)) if isinstance(fallback_gap, dict) else fallback_gap
                    pv = gap_value.get(side) if gap_value.get(side) is not None else fb
                vals.append(str(_gap_css(pv)))
            g = ' '.join(vals).strip()
            resp_gap = g
        if resp_gap in ('0', 0):
            resp_gap = '0px'
        auto = 'auto-fit' if layout.get('autoFit') else 'auto-fill'
        decls = {}
        cc, mcw = layout.get('columnCount'), layout.get('minimumColumnWidth')
        if cc and mcw:
            mx = 'max(min(%s, 100%%), (100%% - (%s * (%s - 1))) /%s)' % (mcw, resp_gap, cc, cc)
            decls['grid-template-columns'] = 'repeat(%s, minmax(%s, 1fr))' % (auto, mx)
        elif cc:
            decls['grid-template-columns'] = 'repeat(%s, minmax(0, 1fr))' % cc
        else:
            decls['grid-template-columns'] = 'repeat(%s, minmax(min(%s, 100%%), 1fr))' % (auto, mcw or '12rem')
        if not cc or mcw:
            decls['container-type'] = 'inline-size'
        add(selector, decls)
        if cc and layout.get('rowCount'):
            add(selector, {'grid-template-rows': 'repeat(%s, minmax(1rem, auto))' % layout['rowCount']})
        if has_gap_support and g is not None and not skip_gap:
            add(selector, {'gap': g})
    return rules


# ─────────────────────────────────────────────────────────────────────────────
# Динамические блоки
# ─────────────────────────────────────────────────────────────────────────────

STATIC_OK = {'core/cover', 'core/file', 'core/media-text', 'core/shortcode', 'core/block', 'core/video', 'core/search',
             'core/latest-posts', 'core/post-featured-image', 'core/icon', 'core/accordion', 'core/accordion-item',
             'core/details', 'core/footnotes', 'core/tabs', 'core/tab-panel', 'core/tab-list'}


def r_template_part(R, a, content, block, ctx, pctx):
    slug = a.get('slug')
    if not slug:
        return ''
    if slug in R.tp_stack:
        R.warn('Рекурсивная часть шаблона %s' % slug)
        return ''
    markup, src = R.system.part(slug)
    if markup is None:
        R.warn('Часть шаблона «%s» не найдена (%s) — WP выведет пусто' % (slug, src))
        return ''
    area = a.get('area')
    tp_defs = {p.get('name'): p.get('area') for p in (R.theme.data.get('templateParts') or []) if isinstance(p, dict)}
    if not area:
        area = tp_defs.get(slug) or ('header' if slug == 'header' else 'footer' if slug == 'footer' else 'uncategorized')
    R.tp_stack.append(slug)
    inner = R.render_blocks(parse_blocks(markup, R.warnings), None, {})
    R.tp_stack.pop()
    inner = wptexturize(inner)
    inner = R.filter_content_tags(inner, 'template_part_' + area)
    tag = a.get('tagName')
    if not tag or not re.fullmatch(r'[a-z0-9_-]+', tag):
        tag = {'header': 'header', 'footer': 'footer'}.get(area, 'div')
    return '<%s %s>%s</%s>' % (tag, R.wrapper_attributes(block.name, a), inner, tag)


def r_post_title(R, a, content, block, ctx, pctx):
    title = R.post.get('title') or ''
    if not title:
        return ''
    title = wptexturize(esc_html(title))
    tag = 'h2'
    if 'level' in a:
        tag = 'p' if a['level'] == 0 else 'h%d' % int(a['level'])
    if a.get('isLink'):
        rel = ' rel="%s"' % esc_attr(a['rel']) if a.get('rel') else ''
        title = '<a href="%s" target="%s"%s>%s</a>' % (esc_attr(R.post.get('permalink', HOME_URL + '/')), esc_attr(a.get('linkTarget', '_self')), rel, title)
    classes = []
    if a.get('textAlign'):
        classes.append('has-text-align-' + a['textAlign'])
    if get_path(a, ('style', 'elements', 'link', 'color', 'text')):
        classes.append('has-link-color')
    return '<%s %s>%s</%s>' % (tag, R.wrapper_attributes(block.name, a, {'class': ' '.join(classes)}), title, tag)


def r_post_content(R, a, content, block, ctx, pctx):
    if R.post.get('_in_content'):
        return ''
    R.post['_in_content'] = True
    if R.post.get('rendered') is not None:
        html = R.post['rendered']
    else:
        html = R.render_blocks(parse_blocks(R.post.get('content', ''), R.warnings), None, {})
        html = wptexturize(html)
        html = R.filter_content_tags(html, 'the_content')
    R.post['_in_content'] = False
    if not html:
        return ''
    tag = a.get('tagName') if isinstance(a.get('tagName'), str) and a['tagName'].lower() in ('div', 'main', 'section', 'article') else 'div'
    return '<%s %s>%s</%s>' % (tag, R.wrapper_attributes(block.name, a, {'class': 'entry-content'}), html, tag)


def r_site_logo(R, a, content, block, ctx, pctx):
    logo_id = R.post.get('logo_id')
    entry = R.media.by_id.get(logo_id) if logo_id else None
    if not entry:
        return ''
    w, h = entry.get('w') or 0, entry.get('h') or 0
    if a.get('width') and w and h:
        h = int(float(a['width']) / (float(w) / float(h)))
        w = int(a['width'])
    alt = R.post.get('logo_alt') or R.post.get('site_title', '')
    ss = R.media.srcset(entry, entry['url'], (w, h))
    extra_img = (' srcset="%s" sizes="(max-width: %dpx) 100vw, %dpx"' % (esc_attr(ss), w, w)) if ss else ''
    img = '<img width="%d" height="%d" src="%s" class="custom-logo" alt="%s" decoding="async"%s />' % (w, h, entry['url'], esc_attr(alt), extra_img)
    if a.get('isLink', True):
        cur = ' aria-current="page"' if R.post.get('front') else ''
        extra = ''
        if a.get('linkTarget') == '_blank':
            extra = ' aria-label="(Ссылка на главную, откроется в новой вкладке)" target="_blank"'
        logo = '<a href="%s/" class="custom-logo-link" rel="home"%s%s>%s</a>' % (HOME_URL, cur, extra, img)
    else:
        logo = img
    classes = '' if a.get('width') else 'is-default-size'
    return '<div %s>%s</div>' % (R.wrapper_attributes(block.name, a, {'class': classes}), logo)


def r_site_title(R, a, content, block, ctx, pctx):
    title = R.post.get('site_title') or ''
    if not title.strip():
        return ''
    tag = 'h1'
    classes = 'has-text-align-%s' % a['textAlign'] if a.get('textAlign') else ''
    if get_path(a, ('style', 'elements', 'link', 'color', 'text')):
        classes += ' has-link-color'
    if 'level' in a:
        tag = 'p' if a['level'] == 0 else 'h%d' % int(a['level'])
    if a.get('isLink', True):
        cur = ' aria-current="page"' if R.post.get('front') else ''
        inner = '<a href="%s" target="%s" rel="home"%s>%s</a>' % (HOME_URL, esc_attr(a.get('linkTarget') or '_self'), cur, esc_html(title))
    else:
        inner = esc_html(title)
    return '<%s %s>%s</%s>' % (tag, R.wrapper_attributes(block.name, a, {'class': classes.strip()}), inner, tag)


def r_site_tagline(R, a, content, block, ctx, pctx):
    tl = R.post.get('site_tagline') or ''
    if not tl:
        return ''
    tag = 'p'
    if a.get('level'):
        tag = 'h%d' % int(a['level'])
    classes = 'has-text-align-%s' % a['textAlign'] if a.get('textAlign') else ''
    return '<%s %s>%s</%s>' % (tag, R.wrapper_attributes(block.name, a, {'class': classes}), esc_html(tl), tag)


def r_heading(R, a, content, block, ctx, pctx):
    if not content:
        return content
    for t in iter_tags(content):
        if not t.closer and t.name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            return add_classes(content, t, ['wp-block-heading'])
    return content


def r_list(R, a, content, block, ctx, pctx):
    if not content:
        return content
    for t in iter_tags(content):
        if not t.closer and t.name in ('ol', 'ul'):
            return add_classes(content, t, ['wp-block-list'])
    return content


def r_button(R, a, content, block, ctx, pctx):
    tag = None
    tpos = None
    for t in iter_tags(content):
        if not t.closer and t.name in ('a', 'button'):
            tag, tpos = t.name, t
            break
    if tag is None:
        return content
    rest = content[tpos.end:]
    m = re.match(r'\s*(?:<!--.*?-->\s*)*</%s\s*>' % tag, rest, re.S)
    if m:
        return ''
    width = get_path(a, ('style', 'dimensions', 'width'))
    if width:
        resolved = width
        is_preset = isinstance(width, str) and width.startswith('var:preset|dimension|')
        slug = None
        if is_preset:
            slug = width[len('var:preset|dimension|'):]
            presets = get_path(R.theme.settings, ('blocks', 'core/button', 'dimensions', 'dimensionSizes')) or \
                get_path(R.theme.settings, ('dimensions', 'dimensionSizes')) or {}
            for origin in ('custom', 'theme', 'default'):
                for p in presets.get(origin) or []:
                    if p.get('slug') == slug:
                        resolved = p.get('size', width)
                        break
                else:
                    continue
                break
        t = first_tag(content, cls='wp-block-button')
        if t:
            existing = get_attr(content, t, 'style')
            existing = existing if isinstance(existing, str) else ''
            classes = ['has-custom-width']
            if str(resolved).endswith('%'):
                num = php_num(float(str(resolved)[:-1]))
                classes.append('wp-block-button__width')
                legacy = {'25%': 'wp-block-button__width-25', '50%': 'wp-block-button__width-50',
                          '75%': 'wp-block-button__width-75', '100%': 'wp-block-button__width-100'}
                if resolved in legacy:
                    classes.append(legacy[resolved])
                ws = '--wp--block-button--width: %s;' % num
            else:
                ws = 'width: %s;' % ('var(--wp--preset--dimension--%s)' % kebab(slug) if is_preset else width)
            content = add_classes(content, t, classes)
            t = first_tag(content, cls='wp-block-button')
            content = set_attrs(content, t, {'style': ws + (' ' + existing if existing else '')})
    return content


def r_image(R, a, content, block, ctx, pctx):
    if '<img' not in content.lower():
        return ''
    t = first_tag(content, 'img')
    if not t or not get_attr(content, t, 'src'):
        return ''
    if 'data-id' in a:
        content = set_attrs(content, t, {'data-id': a['data-id']})
    if not a.get('caption'):
        content = re.sub(r'<figcaption[^>]*>\s*(?:<!--.*?-->\s*)*</figcaption>', '', content, count=1, flags=re.S)
    link = a.get('linkDestination', 'none')
    lb = a.get('lightbox') if isinstance(a.get('lightbox'), dict) else None
    if lb is None:
        lb = get_path(R.theme.settings, ('blocks', 'core/image', 'lightbox'))
        if not isinstance(lb, dict) or 'enabled' not in lb:
            top = R.theme.settings.get('lightbox')
            lb = top if isinstance(top, dict) else lb
    if isinstance(lb, dict) and lb.get('enabled') is True and link == 'none':
        content = image_lightbox(R, content, a)
    return content


def image_lightbox(R, content, a):
    R.lightbox = True
    fig = first_tag(content, 'figure')
    key = hashlib.md5(content.encode()).hexdigest()[:13]
    if fig:
        content = add_classes(content, fig, ['wp-lightbox-container'])
        fig = first_tag(content, 'figure')
        content = set_attrs(content, fig, {'data-wp-interactive': 'core/image',
                                           'data-wp-context': '{"imageId":"%s"}' % key, 'data-wp-key': key})
    img = first_tag(content, 'img')
    if not img:
        return content
    content = set_attrs(content, img, {
        'data-wp-init': 'callbacks.setButtonStyles', 'data-wp-on--load': 'callbacks.setButtonStyles',
        'data-wp-on-window--resize': 'callbacks.setButtonStyles',
        'data-wp-on--pointerenter': 'actions.preloadImageWithDelay', 'data-wp-on--pointerdown': 'actions.preloadImage',
        'data-wp-on--pointerleave': 'actions.cancelPreload', 'data-wp-on--click': 'actions.showLightbox',
        'data-wp-class--hide': 'state.isContentHidden', 'data-wp-class--show': 'state.isContentVisible'})
    img = first_tag(content, 'img')
    button = ('<button\n\t\t\tclass="lightbox-trigger"\n\t\t\ttype="button"\n\t\t\taria-haspopup="dialog"\n'
              '\t\t\tdata-wp-bind--aria-label="state.thisImage.triggerButtonAriaLabel"\n'
              '\t\t\tdata-wp-init="callbacks.initTriggerButton"\n\t\t\tdata-wp-on--click="actions.showLightbox"\n'
              '\t\t\tdata-wp-style--right="state.thisImage.buttonRight"\n\t\t\tdata-wp-style--top="state.thisImage.buttonTop"\n\t\t>\n'
              '\t\t\t<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 12 12">\n'
              '\t\t\t\t<path fill="#fff" d="M2 0a2 2 0 0 0-2 2v2h1.5V2a.5.5 0 0 1 .5-.5h2V0H2Zm2 10.5H2a.5.5 0 0 1-.5-.5V8H0v2a2 2 0 0 0 2 2h2v-1.5ZM8 12v-1.5h2a.5.5 0 0 0 .5-.5V8H12v2a2 2 0 0 1-2 2H8Zm2-12a2 2 0 0 1 2 2v2h-1.5V2a.5.5 0 0 0-.5-.5H8V0h2Z" />\n'
              '\t\t\t</svg>\n\t\t</button>')
    return content[:img.end] + button + content[img.end:]


def r_gallery(R, a, content, block, ctx, pctx):
    t = first_tag(content)
    if not t:
        return content
    ucls = R.unique_id('wp-block-gallery-')
    content = add_classes(content, t, [ucls])
    fallback = 'var( --wp--style--gallery-gap-default, var( --gallery-block--gutter-size, var( --wp--style--block-gap, 0.5em ) ) )'
    gg = get_path(R.global_styles, ('blocks', 'core/gallery', 'spacing', 'blockGap'), fallback)
    sp = get_path(a, ('style', 'spacing'))
    gap = sp['blockGap'] if isinstance(sp, dict) and 'blockGap' in sp else gg
    if isinstance(gap, dict):
        gap = gap.get('left', fallback)
    gap = gap if isinstance(gap, str) else ''
    if gap and re.search(r'[\\(&=}]|/\*', gap) and not gap.startswith('var('):
        gap = None
    if isinstance(gap, str) and 'var:preset|spacing|' in gap:
        gap = 'var(--wp--preset--spacing--%s)' % kebab(gap[gap.rfind('|') + 1:])
    col = gap if gap not in (None, '') else fallback
    col = '0px' if col == '0' else col
    R.store.add('.wp-block-gallery.' + ucls, {'--wp--style--unstable-gallery-gap': col})
    return content


def r_post_featured_image(R, a, content, block, ctx, pctx):
    return ''


def r_page_list(R, a, content, block, ctx, pctx):
    items = ''
    in_nav = bool(ctx.get('_in_navigation'))
    for pid, (slug, title) in sorted(SITE_PAGES.items(), key=lambda x: x[1][1]):
        url = HOME_URL + '/' + (slug + '/' if slug else '')
        cur = pid == R.post.get('id')
        items += '<li class="wp-block-pages-list__item%s%s"><a class="wp-block-pages-list__item__link%s" href="%s"%s>%s</a></li>' % (
            ' wp-block-navigation-item' if in_nav else '', ' current-menu-item' if cur else '',
            ' wp-block-navigation-item__content' if in_nav else '', url, ' aria-current="page"' if cur else '', esc_html(title))
    if ctx.get('_in_navigation'):
        return items
    return '<ul %s>%s</ul>' % (R.wrapper_attributes(block.name, a, {'class': 'wp-block-page-list'}), items)


def r_navigation_link(R, a, content, block, ctx, pctx):
    if not a.get('label'):
        return ''
    if a.get('kind') == 'post-type' and a.get('id') and int(a['id']) not in SITE_PAGES:
        R.warn('Пункт меню «%s» ссылается на id %s, которого нет среди страниц сайта — WP его не выведет' % (a.get('label'), a.get('id')))
    inner = ''
    for ib in block.inner_blocks:
        inner += R.render_block(ib, block, ctx)
    has_sub = bool(inner.strip())
    active = bool(a.get('id')) and int(a.get('id') or 0) == R.post.get('id') and (a.get('kind', 'post-type') in ('post-type',))
    cls = ' wp-block-navigation-item' + (' has-child' if has_sub else '') + (' current-menu-item' if active else '')
    h = '<li %s><a class="wp-block-navigation-item__content" ' % R.wrapper_attributes(block.name, a, {'class': cls})
    if 'url' in a:
        h += ' href="%s"' % esc_attr(a['url'])
    if active:
        h += ' aria-current="page"'
    if a.get('opensInNewTab') is True:
        h += ' target="_blank"  '
    if a.get('rel'):
        h += ' rel="%s"' % esc_attr(a['rel'])
    elif a.get('nofollow'):
        h += ' rel="nofollow"'
    if a.get('title'):
        h += ' title="%s"' % esc_attr(a['title'])
    h += '><span class="wp-block-navigation-item__label">%s</span>' % a['label']
    if a.get('description'):
        h += '<span class="wp-block-navigation-item__description">%s</span>' % a['description']
    h += '</a>'
    if ctx.get('showSubmenuIcon') and has_sub:
        h += '<span class="wp-block-navigation__submenu-icon"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" focusable="false"><path d="M1.50002 4L6.00002 8L10.5 4" stroke-width="1.5"></path></svg></span>'
    if has_sub:
        h += '<ul class="wp-block-navigation__submenu-container">%s</ul>' % inner
    return h + '</li>'


def r_navigation_submenu(R, a, content, block, ctx, pctx):
    if not a.get('label'):
        return ''
    inner = ''
    for ib in block.inner_blocks:
        inner += R.render_block(ib, block, ctx)
    has_sub = bool(inner.strip())
    active = bool(a.get('id')) and int(a.get('id') or 0) == R.post.get('id')
    vis = 'click' if ctx.get('openSubmenusOnClick') else (ctx.get('submenuVisibility') or 'hover')
    show_icon = bool(ctx.get('showSubmenuIcon'))
    classes = ['wp-block-navigation-item']
    if has_sub:
        classes.append('has-child')
    if vis == 'click':
        classes.append('open-on-click')
    if vis == 'hover' and show_icon:
        classes.append('open-on-hover-click')
    if vis == 'always':
        classes.append('open-always')
    if active:
        classes.append('current-menu-item')
    label = a['label']
    h = '<li %s>' % R.wrapper_attributes(block.name, a, {'class': ' '.join(classes)})
    aria = T['%s submenu'] % re.sub(r'<[^>]+>', '', label)
    if vis != 'click':
        h += '<a class="wp-block-navigation-item__content"'
        if a.get('url'):
            h += ' href="%s"' % esc_attr(a['url'])
        if active:
            h += ' aria-current="page"'
        h += '><span class="wp-block-navigation-item__label">%s</span></a>' % label
        if show_icon:
            h += ('<button aria-label="%s" class="wp-block-navigation__submenu-icon wp-block-navigation-submenu__toggle" aria-expanded="false">'
                  '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" focusable="false"><path d="M1.50002 4L6.00002 8L10.5 4" stroke-width="1.5"></path></svg></button>') % esc_attr(aria)
    else:
        h += ('<button aria-label="%s" class="wp-block-navigation-item__content wp-block-navigation-submenu__toggle" aria-expanded="false">'
              '<span class="wp-block-navigation-item__label">%s</span></button><span class="wp-block-navigation__submenu-icon">'
              '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" focusable="false"><path d="M1.50002 4L6.00002 8L10.5 4" stroke-width="1.5"></path></svg></span>') % (esc_attr(aria), label)
    if has_sub:
        h += '<ul %s>%s</ul>' % ('class="wp-block-navigation__submenu-container wp-block-navigation-submenu"', inner)
    return h + '</li>'


NAV_LIST_ITEM_WRAP = {'core/site-title', 'core/site-logo', 'core/social-links'}


def r_navigation(R, a, content, block, ctx, pctx):
    inner_blocks = [b for b in block.inner_blocks if b.name]
    if not inner_blocks:
        if a.get('ref'):
            R.warn('core/navigation с ref=%s: меню из записи wp_navigation недоступно — показан список страниц (fallback)' % a.get('ref'))
        inner_blocks = [Block('core/page-list', {})]
    nav_ctx = dict(ctx)
    nav_ctx['_in_navigation'] = True
    is_responsive = (a.get('overlayMenu') and a.get('overlayMenu') != 'never') or bool(a.get('isResponsive'))
    has_submenus = any(b.name == 'core/navigation-submenu' for b in inner_blocks)
    open_click = (('click' if a.get('openSubmenusOnClick') else 'hover') if a.get('openSubmenusOnClick') is not None
                  else (a.get('submenuVisibility') or 'hover')) == 'click'
    is_interactive = (has_submenus and (open_click or bool(a.get('showSubmenuIcon')))) or is_responsive
    # классы
    lay = a.get('layout') if isinstance(a.get('layout'), dict) else {}
    jmap = {'left': 'items-justified-left', 'right': 'items-justified-right', 'center': 'items-justified-center',
            'space-between': 'items-justified-space-between'}
    layout_class = jmap.get(lay.get('justifyContent'), '')
    if lay.get('orientation') == 'vertical':
        layout_class += ' is-vertical'
    if lay.get('flexWrap') == 'nowrap':
        layout_class += ' no-wrap'
    colors = nav_colors(a)
    fonts_cls = ['has-%s-font-size' % a['fontSize']] if 'fontSize' in a else []
    fonts_style = ('font-size: %spx;' % a['customFontSize']) if 'fontSize' not in a and 'customFontSize' in a else ''
    td = get_path(a, ('style', 'typography', 'textDecoration'))
    classes = colors['css_classes'] + fonts_cls + (['is-responsive'] if is_responsive else []) + \
        ([layout_class] if layout_class else []) + (['has-text-decoration-%s' % td] if td else [])
    cls_str = ' '.join(classes)
    style = (a.get('styles') or '') + colors['inline_styles'] + fonts_style
    # внутренние блоки
    ul_attrs = R.wrapper_attributes(block.name, a, {'class': 'wp-block-navigation__container ' + cls_str, 'style': style})
    html = ''
    is_open = False
    for ib in inner_blocks:
        markup = R.render_block(ib, block, nav_ctx)
        if markup and ib.name in NAV_LIST_ITEM_WRAP:
            markup = '<li class="wp-block-navigation-item">' + markup + '</li>'
        is_li = first_tag(markup, 'li') is not None if ib.name != 'core/page-list' else bool(markup)
        if is_li and not is_open:
            is_open = True
            html += '<ul %s>' % ul_attrs
        if not is_li and is_open:
            is_open = False
            html += '</ul>'
        html += markup
    if is_open:
        html += '</ul>'
    # оверлей
    if is_responsive:
        modal = R.unique_id('modal-')
        hidden = a.get('overlayMenu') == 'always'
        rc = ['wp-block-navigation__responsive-container'] + (['hidden-by-default'] if hidden else []) + \
            [' '.join(colors['overlay_css_classes'])]
        oc = ['wp-block-navigation__responsive-container-open'] + (['always-shown'] if hidden else [])
        has_icon = a.get('hasIcon', True) is True
        icon = '<svg width="24" height="24" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 7.5h16v1.5H4z"></path><path d="M4 15h16v1.5H4z"></path></svg>'
        if a.get('icon') == 'menu':
            icon = '<svg width="24" height="24" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M5 5v1.5h14V5H5z"></path><path d="M5 12.8h14v-1.5H5v1.5z"></path><path d="M5 19h14v-1.5H5V19z"></path></svg>'
        close_icon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false"><path d="m13.06 12 6.47-6.47-1.06-1.06L12 10.94 5.53 4.47 4.47 5.53 10.94 12l-6.47 6.47 1.06 1.06L12 13.06l6.47 6.47 1.06-1.06L13.06 12Z"></path></svg>'
        open_label = 'aria-label="%s"' % T['Open menu'] if has_icon else ''
        close_label = 'aria-label="%s"' % T['Close menu'] if has_icon else ''
        d_open = d_cont = d_dialog = d_close = d_content = ''
        if is_interactive:
            d_open = '\n\t\t\t\tdata-wp-on--click="actions.openMenuOnClick"\n\t\t\t\tdata-wp-on--keydown="actions.handleMenuKeydown"\n\t\t\t'
            d_cont = ('\n\t\t\t\tdata-wp-class--has-modal-open="state.isMenuOpen"\n\t\t\t\tdata-wp-class--is-menu-open="state.isMenuOpen"\n'
                      '\t\t\t\tdata-wp-watch="callbacks.initMenu"\n\t\t\t\tdata-wp-on--keydown="actions.handleMenuKeydown"\n'
                      '\t\t\t\tdata-wp-on--focusout="actions.handleMenuFocusout"\n\t\t\t\ttabindex="-1"\n\t\t\t')
            d_dialog = '\n\t\t\t\tdata-wp-bind--aria-modal="state.ariaModal"\n\t\t\t\tdata-wp-bind--aria-label="state.ariaLabel"\n\t\t\t\tdata-wp-bind--role="state.roleAttribute"\n\t\t\t'
            d_close = '\n\t\t\t\tdata-wp-on--click="actions.closeMenuOnClick"\n\t\t\t'
            d_content = '\n\t\t\t\tdata-wp-watch="callbacks.focusFirstElement"\n\t\t\t'
        ov_style = ''
        if colors['overlay_inline_styles']:
            ov_style = 'style="%s"' % esc_attr(colors['overlay_inline_styles'])
        close_btn = '<button %s class="wp-block-navigation__responsive-container-close" %s>%s</button>' % (
            close_label, d_close, close_icon if has_icon else T['Close'])
        html = ('<button aria-haspopup="dialog" %s class="%s" %s>%s</button>\n'
                '\t\t\t\t<div class="%s" %s id="%s" %s>\n'
                '\t\t\t\t\t<div class="wp-block-navigation__responsive-close" tabindex="-1">\n'
                '\t\t\t\t\t\t<div class="wp-block-navigation__responsive-dialog" %s>\n'
                '\t\t\t\t\t\t\t%s\n'
                '\t\t\t\t\t\t\t<div class="wp-block-navigation__responsive-container-content" %s id="%s-content">\n'
                '\t\t\t\t\t\t\t\t%s\n\t\t\t\t\t\t\t\t\n'
                '\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</div>\n\t\t\t\t</div>') % (
            open_label, esc_attr(' '.join(oc).strip()), d_open, icon if has_icon else T['Menu'],
            esc_attr(' '.join(rc).strip()), ov_style, modal, d_cont, d_dialog, close_btn, d_content, modal, html)
    # имя/aria-label
    name = a.get('ariaLabel') or ''
    R.seen_nav_names[name] = R.seen_nav_names.get(name, 0) + 1
    if R.seen_nav_names[name] > 1:
        name = '%s %d' % (name, R.seen_nav_names[name])
    extra = {'class': cls_str, 'style': style}
    if name:
        extra['aria-label'] = name
    attrs = R.wrapper_attributes(block.name, a, extra)
    if is_responsive and is_interactive:
        attrs += ' \n\t\t data-wp-interactive="core/navigation" data-wp-context=\'%s\'' % json.dumps(
            {"overlayOpenedBy": {"click": False, "hover": False, "focus": False}, "type": "overlay", "roleAttribute": "",
             "ariaLabel": T['Menu']}, ensure_ascii=False, separators=(',', ':'))
    return '<nav %s>%s</nav>' % (attrs, html)


def nav_colors(a):
    c = {'css_classes': [], 'inline_styles': '', 'overlay_css_classes': [], 'overlay_inline_styles': ''}
    if 'customTextColor' in a or 'textColor' in a:
        c['css_classes'].append('has-text-color')
    if 'textColor' in a:
        c['css_classes'].append('has-%s-color' % a['textColor'])
    elif 'customTextColor' in a:
        c['inline_styles'] += 'color: %s;' % a['customTextColor']
    if 'customBackgroundColor' in a or 'backgroundColor' in a:
        c['css_classes'].append('has-background')
    if 'backgroundColor' in a:
        c['css_classes'].append('has-%s-background-color' % a['backgroundColor'])
    elif 'customBackgroundColor' in a:
        c['inline_styles'] += 'background-color: %s;' % a['customBackgroundColor']
    if 'customOverlayTextColor' in a or 'overlayTextColor' in a:
        c['overlay_css_classes'].append('has-text-color')
    if 'overlayTextColor' in a:
        c['overlay_css_classes'].append('has-%s-color' % a['overlayTextColor'])
    elif 'customOverlayTextColor' in a:
        c['overlay_inline_styles'] += 'color: %s;' % a['customOverlayTextColor']
    if 'customOverlayBackgroundColor' in a or 'overlayBackgroundColor' in a:
        c['overlay_css_classes'].append('has-background')
    if 'overlayBackgroundColor' in a:
        c['overlay_css_classes'].append('has-%s-background-color' % a['overlayBackgroundColor'])
    elif 'customOverlayBackgroundColor' in a:
        c['overlay_inline_styles'] += 'background-color: %s;' % a['customOverlayBackgroundColor']
    return c


def r_unsupported(R, a, content, block, ctx, pctx):
    R.warn('Блок %s (динамический) не эмулируется — ничего не выведено' % block.name)
    return '<!-- preview: %s не эмулируется -->' % block.name


DYNAMIC = {
    'core/template-part': r_template_part,
    'core/post-title': r_post_title,
    'core/post-content': r_post_content,
    'core/site-logo': r_site_logo,
    'core/site-title': r_site_title,
    'core/site-tagline': r_site_tagline,
    'core/heading': r_heading,
    'core/list': r_list,
    'core/button': r_button,
    'core/image': r_image,
    'core/gallery': r_gallery,
    'core/post-featured-image': r_post_featured_image,
    'core/page-list': r_page_list,
    'core/navigation': r_navigation,
    'core/navigation-link': r_navigation_link,
    'core/navigation-submenu': r_navigation_submenu,
    'core/query': r_unsupported, 'core/post-template': r_unsupported, 'core/comments': r_unsupported,
    'core/post-date': r_unsupported, 'core/post-author': r_unsupported, 'core/post-excerpt': r_unsupported,
    'core/pattern': r_unsupported, 'core/archives': r_unsupported, 'core/categories': r_unsupported,
    'core/latest-comments': r_unsupported, 'core/rss': r_unsupported, 'core/tag-cloud': r_unsupported,
    'core/calendar': r_unsupported, 'core/loginout': r_unsupported, 'core/query-title': r_unsupported,
}


def _filter_content_tags(self, html, context):
    """wp_filter_content_tags(): width/height у <img class="wp-image-N">, decoding, loading/fetchpriority."""
    out = []
    pos = 0
    for t in list(iter_tags(html)):
        if t.closer or t.name != 'img':
            continue
        tag_src = html[t.start:t.end]
        mm = re.search(r'\bwp-image-(\d+)\b', tag_src)
        new = tag_src
        tmp = new
        tt = first_tag(tmp, 'img')
        updates = {}
        if mm:
            aid = int(mm.group(1))
            src = get_attr(tmp, tt, 'src') or ''
            if get_attr(tmp, tt, 'width') is None and get_attr(tmp, tt, 'height') is None:
                dims = self.media.dims(src, aid)
                if dims:
                    updates['width'] = str(dims[0])
                    updates['height'] = str(dims[1])
        if get_attr(tmp, tt, 'decoding') is None:
            updates['decoding'] = 'async'
        if get_attr(tmp, tt, 'loading') is None and get_attr(tmp, tt, 'fetchpriority') is None:
            if context == 'the_content':
                self.content_images += 1
                if self.content_images > 3:
                    updates['loading'] = 'lazy'
                elif self.content_images == 1:
                    updates['fetchpriority'] = 'high'
            elif context.startswith('template_part_') and context != 'template_part_header':
                updates['loading'] = 'lazy'
        if mm and get_attr(tmp, tt, 'srcset') is None:
            entry, _ = self.media.resolve(get_attr(tmp, tt, 'src') or '')
            if entry is None:
                entry = self.media.by_id.get(int(mm.group(1)))
            w = updates.get('width') or get_attr(tmp, tt, 'width')
            h = updates.get('height') or get_attr(tmp, tt, 'height')
            if entry and w and h and str(w).isdigit() and str(h).isdigit():
                ss = self.media.srcset(entry, get_attr(tmp, tt, 'src') or '', (int(w), int(h)))
                if ss:
                    updates['srcset'] = ss
                    updates['sizes'] = '(max-width: %dpx) 100vw, %dpx' % (int(w), int(w))
        if updates.get('loading') == 'lazy' and updates.get('sizes') and not updates['sizes'].startswith('auto'):
            updates['sizes'] = 'auto, ' + updates['sizes']
        if updates:
            new = set_attrs(tmp, tt, updates)
        out.append(html[pos:t.start])
        out.append(new)
        pos = t.end
    out.append(html[pos:])
    return ''.join(out)


Renderer.filter_content_tags = _filter_content_tags


# ─────────────────────────────────────────────────────────────────────────────
# Файлы дизайн-системы
# ─────────────────────────────────────────────────────────────────────────────

class SystemFiles:
    def __init__(self, root, warnings, css_override=None, gs_override=None):
        self.root = Path(root) if root else None
        self.warnings = warnings
        self.css_override = css_override
        self.gs_override = gs_override

    def _find(self, names):
        for n in names:
            if self.root is None:
                break
            p = self.root / n
            if p.exists():
                return p
        return None

    def part(self, slug):
        p = self._find(['%s.html' % slug, 'parts/%s.html' % slug])
        if p:
            return p.read_text(encoding='utf-8'), str(p)
        fb = DATA / 'tt5' / ('%s-fallback.html' % slug)
        if fb.exists():
            self.warnings.append('Часть шаблона %s не найдена в %s — использована заглушка в стиле TT5' % (slug, self.root))
            return fb.read_text(encoding='utf-8'), str(fb)
        return None, str(self.root)

    def template(self, slug):
        if slug.endswith('.html') and Path(slug).exists():
            return Path(slug).read_text(encoding='utf-8')
        p = self._find(['%s.html' % slug, 'templates/%s.html' % slug])
        if p:
            return p.read_text(encoding='utf-8')
        fb = DATA / 'tt5' / ('%s.html' % slug)
        if fb.exists():
            self.warnings.append('Шаблон %s не найден в %s — использован шаблон TT5' % (slug, self.root))
            return fb.read_text(encoding='utf-8')
        raise SystemExit('Шаблон «%s» не найден ни в %s, ни среди шаблонов TT5' % (slug, self.root))

    def global_styles(self):
        p = Path(self.gs_override) if self.gs_override else self._find(['global-styles.json', 'theme.json'])
        if not p or not p.exists():
            self.warnings.append('global-styles.json не найден в %s — только стили темы TT5' % self.root)
            return None, None
        raw = json.loads(p.read_text(encoding='utf-8'))
        if isinstance(raw, dict) and 'settings' not in raw and 'styles' not in raw:
            for k in ('global_styles', 'globalStyles', 'data'):
                if isinstance(raw.get(k), dict):
                    raw = raw[k]
                    break
        user = {'version': raw.get('version', 3), 'settings': raw.get('settings') or {}, 'styles': raw.get('styles') or {}}
        for k in raw:
            if k not in ('version', 'settings', 'styles', 'isGlobalStylesUserThemeJSON', 'id', '_links', '$schema', 'title'):
                user[k] = raw[k]
        css_json = get_path(user, ('styles', 'css')) or ''
        css_file = Path(self.css_override) if self.css_override else self._find(['styles.css', 'global-styles.css'])
        css = css_json
        if self.css_override:
            css = Path(self.css_override).read_text(encoding='utf-8')
        elif css_file and css_file.exists():
            stripped = re.sub(r'/\*.*?\*/', '', css_json, flags=re.S).strip()
            file_css = css_file.read_text(encoding='utf-8')
            if not stripped:
                css = file_css
            elif file_css.strip() != css_json.strip():
                self.warnings.append('Есть и styles.css в global-styles.json, и файл %s — взят CSS из JSON '
                                     '(укажите --css, чтобы взять файл)' % css_file)
        if isinstance(user.get('styles'), dict):
            user['styles'].pop('css', None)
        return user, css


# ─────────────────────────────────────────────────────────────────────────────
# Сборка страницы
# ─────────────────────────────────────────────────────────────────────────────

def load_data():
    base = json.loads((DATA / 'theme-base.json').read_text(encoding='utf-8'))
    blocks = json.loads((DATA / 'blocks.json').read_text(encoding='utf-8'))
    return base, blocks


def font_face_css(theme, warnings):
    css = ''
    fams = get_path(theme.settings, ('typography', 'fontFamilies')) or {}
    seen = set()
    for origin in ('default', 'theme', 'custom'):
        for fam in fams.get(origin) or []:
            for face in fam.get('fontFace') or []:
                srcs = face.get('src') or []
                srcs = [srcs] if isinstance(srcs, str) else srcs
                urls = []
                for s in srcs:
                    base = s.split('/')[-1].split('?')[0]
                    local = DATA / 'fonts' / base
                    if local.exists():
                        urls.append("url('%s') format('woff2')" % local.as_uri())
                    elif 'manrope' in base.lower() and (ASSETS / 'fonts' / 'manrope-latin-wght-normal.woff2').exists():
                        urls.append("url('%s') format('woff2')" % (ASSETS / 'fonts' / 'manrope-latin-wght-normal.woff2').as_uri())
                    else:
                        warnings.append('Шрифт %s (%s) недоступен локально — в превью будет запасной шрифт' % (fam.get('name'), s))
                if not urls:
                    continue
                key = (face.get('fontFamily'), face.get('fontWeight'), face.get('fontStyle'), tuple(urls))
                if key in seen:
                    continue
                seen.add(key)
                ff = face.get('fontFamily', fam.get('name'))
                css += '@font-face{font-family:%s;font-style:%s;font-weight:%s;font-display:%s;src:%s;}\n' % (
                    ff, face.get('fontStyle', 'normal'), face.get('fontWeight', '400'), face.get('fontDisplay', 'fallback'), ', '.join(urls))
    return css


LIGHTBOX_OVERLAY = '''
		<div
			class="wp-lightbox-overlay zoom"
			aria-label="{dialog}"
			data-wp-interactive="core/image"
			data-wp-router-region='{{ "id": "core/image-overlay", "attachTo": "body" }}'
			data-wp-key="wp-lightbox-overlay"
			data-wp-context='{{}}'
			data-wp-bind--role="state.roleAttribute"
			data-wp-bind--aria-label="state.ariaLabel"
			data-wp-bind--aria-modal="state.ariaModal"
			data-wp-class--active="state.overlayEnabled"
			data-wp-class--show-closing-animation="state.overlayOpened"
			data-wp-on--keydown="actions.handleKeydown"
			data-wp-on--click="actions.hideLightbox"
			data-wp-bind--style="state.overlayStyles"
			tabindex="-1"
			>
				<button type="button" style="fill:{close_color}" class="wp-lightbox-close-button" data-wp-bind--aria-label="state.closeButtonAriaLabel">
					<span class="wp-lightbox-close-icon" data-wp-bind--hidden="!state.hasNavigationIcon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false"><path d="m13.06 12 6.47-6.47-1.06-1.06L12 10.94 5.53 4.47 4.47 5.53 10.94 12l-6.47 6.47 1.06 1.06L12 13.06l6.47 6.47 1.06-1.06L13.06 12Z"></path></svg></span>
					<span class="wp-lightbox-close-text" data-wp-bind--hidden="!state.hasNavigationText">{close}</span>
				</button>
				<button type="button" style="fill:{close_color}" class="wp-lightbox-navigation-button wp-lightbox-navigation-button-prev" data-wp-bind--hidden="!state.hasNavigation" data-wp-on--click="actions.showPreviousImage" data-wp-bind--aria-label="state.prevButtonAriaLabel">
					<span class="wp-lightbox-navigation-icon" data-wp-bind--hidden="!state.hasNavigationIcon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" focusable="false"><path d="M14.6 7l-1.2-1L8 12l5.4 6 1.2-1-4.6-5z"></path></svg></span>
					<span class="wp-lightbox-navigation-text" data-wp-bind--hidden="!state.hasNavigationText">{prev}</span>
				</button>
				<div class="lightbox-image-container">
					<figure data-wp-bind--class="state.selectedImage.figureClassNames" data-wp-bind--style="state.figureStyles">
						<img data-wp-bind--alt="state.selectedImage.alt" data-wp-bind--class="state.selectedImage.imgClassNames" data-wp-bind--style="state.imgStyles" data-wp-bind--src="state.selectedImage.currentSrc">
					</figure>
				</div>
				<div class="lightbox-image-container">
					<figure data-wp-bind--class="state.selectedImage.figureClassNames" data-wp-bind--style="state.figureStyles">
						<img data-wp-bind--alt="state.selectedImage.alt" data-wp-bind--class="state.selectedImage.imgClassNames" data-wp-bind--style="state.imgStyles" data-wp-bind--src="state.enlargedSrc" sizes="100vw">
					</figure>
				</div>
				<button type="button" style="fill:{close_color}" class="wp-lightbox-navigation-button wp-lightbox-navigation-button-next" data-wp-bind--hidden="!state.hasNavigation" data-wp-on--click="actions.showNextImage" data-wp-bind--aria-label="state.nextButtonAriaLabel">
					<span class="wp-lightbox-navigation-text" data-wp-bind--hidden="!state.hasNavigationText">{next}</span>
					<span class="wp-lightbox-navigation-icon" data-wp-bind--hidden="!state.hasNavigationIcon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" focusable="false"><path d="M10.6 6L9.4 7l4.6 5-4.6 5 1.2 1 5.4-6z"></path></svg></span>
				</button>
				<div data-wp-text="state.ariaLabel" aria-live="polite" aria-atomic="true" class="screen-reader-text"></div>
				<div class="scrim" style="background-color: {bg}" aria-hidden="true"></div>
		</div>
'''


def rendered_mode_css(R, html):
    """CSS для wp-container-* и прочих классов из content.rendered, чьих стилей в REST-ответе нет."""
    have = set()
    for (_, sel) in R.store.rules:
        for cls in re.findall(r'\.([A-Za-z0-9_-]+)', sel):
            have.add('.' + cls)
    for t in iter_tags(html):
        if t.closer:
            continue
        classes = tag_classes(html, t)
        for c in classes:
            m = re.match(r'wp-container-(.+?)-is-layout-[0-9a-f]+$', c)
            if m and ('.' + c) not in have:
                have.add('.' + c)
                sel = '.' + c
                lay = {}
                if 'is-layout-flex' in classes:
                    lay['type'] = 'flex'
                elif 'is-layout-grid' in classes:
                    lay['type'] = 'grid'
                elif 'is-layout-constrained' in classes:
                    lay['type'] = 'constrained'
                else:
                    lay['type'] = 'default'
                for cc in classes:
                    if cc.startswith('is-content-justification-'):
                        lay['justifyContent'] = cc[len('is-content-justification-'):]
                if 'is-vertical' in classes:
                    lay['orientation'] = 'vertical'
                if 'is-nowrap' in classes or m.group(1) == 'core-columns':
                    lay['flexWrap'] = 'nowrap'
                style = get_attr(html, t, 'style') or ''
                spacing = {}
                for side in ('left', 'right'):
                    mm = re.search(r'padding-%s\s*:\s*([^;]+)' % side, style)
                    if mm:
                        spacing.setdefault('padding', {})[side] = mm.group(1).strip()
                rules = layout_style_rules(sel, lay, False, None, False, '0.5em', spacing or None)
                if lay['type'] == 'grid':
                    rules = [{'selector': sel, 'declarations': {
                        'grid-template-columns': 'repeat(auto-fill, minmax(min(12rem, 100%), 1fr))', 'container-type': 'inline-size'}}]
                for r in rules:
                    R.store.add(r['selector'], r['declarations'], r.get('rules_group', ''))
                R.warn('rendered: CSS для .%s восстановлен по умолчаниям (gap/колонки/contentSize из блока неизвестны)' % c)
            elif re.match(r'wp-block-gallery-\d+$', c) and ('.' + c) not in have:
                have.add('.' + c)
                R.store.add('.wp-block-gallery.' + c, {'--wp--style--unstable-gallery-gap':
                            'var( --wp--style--gallery-gap-default, var( --gallery-block--gutter-size, var( --wp--style--block-gap, 0.5em ) ) )'})
            else:
                m2 = re.match(r'is-style-(.+)--\d+$', c)
                if m2:
                    block_name = None
                    for cc in classes:
                        if cc.startswith('wp-block-') and ('core/' + cc[9:]) in R.blocks:
                            block_name = 'core/' + cc[9:]
                            break
                    if block_name and get_path(R.theme.styles, ('blocks', block_name, 'variations', m2.group(1))):
                        R.variation_css.append(R.theme.variation_stylesheet(block_name, m2.group(1), c[9:]))
            if c.startswith('wp-block-') and ('core/' + c[9:]) in R.blocks:
                R.used_blocks.add('core/' + c[9:])
        if t.name == 'p':
            R.used_blocks.add('core/paragraph')


def raw_css_for_rendered(R, raw, rendered, theme, blocks, media, post, system, warnings):
    """--rendered + --raw: считает CSS block-supports по исходной разметке. Классы wp-container-* — хэши,
    они совпадают с WP; нумерованные классы (wp-elements-N, wp-block-gallery-N, wp-container-N) сопоставляются
    по порядку появления в content.rendered."""
    R2 = Renderer(theme, blocks, media, dict(post, rendered=None, content=raw), system, [])
    html2 = R2.render_blocks(parse_blocks(raw, []))
    mapping = {}
    for pat in (r'wp-elements-\d+', r'wp-block-gallery-\d+', r'wp-container-\d+'):
        a = list(dict.fromkeys(re.findall(r'\b%s\b' % pat, html2)))
        b = list(dict.fromkeys(re.findall(r'\b%s\b' % pat, rendered)))
        for x, y in zip(a, b):
            mapping[x] = y
    for (group, sel), decls in R2.store.rules.items():
        sel2 = re.sub(r'\b(wp-elements-\d+|wp-block-gallery-\d+|wp-container-\d+)\b', lambda m: mapping.get(m.group(1), m.group(1)), sel)
        if (group, sel2) not in R.store.rules:
            R.store.add(sel2, decls, group)
    R.used_blocks |= R2.used_blocks


def build_page(args, warnings):
    base, blocks = load_data()
    system = SystemFiles(args.system, warnings, args.css, args.global_styles)
    user, custom_css = system.global_styles()
    theme = ThemeJSON(base, blocks, user, warnings)
    seen_paths = set()
    for r in theme.removed:
        key = r.split(' (')[0]
        if key in seen_paths:
            continue
        seen_paths.add(key)
        warnings.append('global styles: WP отбросит %s' % r)
    if custom_css and re.search(r'</?\w+', custom_css):
        warnings.append('styles.css содержит HTML-теги (#</?\\w+#) — REST API WordPress отклонит такой CSS')
    media = Media(MEDIA_JSON)
    content = Path(args.content).read_text(encoding='utf-8') if args.content else ''
    post = {
        'id': args.page_id, 'title': args.title or '', 'permalink': args.permalink or (HOME_URL + '/'),
        'front': args.front, 'site_title': args.site_title, 'site_tagline': args.site_tagline,
        'logo_id': args.logo_id, 'logo_alt': args.logo_alt, 'content': content,
        'rendered': content if args.rendered else None,
    }
    R = Renderer(theme, blocks, media, post, system, warnings)
    tpl = system.template(args.template)
    if 'wp:post-content' not in tpl:
        warnings.append('В шаблоне %s нет core/post-content — контент страницы не будет показан' % args.template)
    body = R.render_blocks(parse_blocks(tpl, warnings))
    body = wptexturize(body)
    body = R.filter_content_tags(body, 'template')
    body = '<div class="wp-site-blocks">' + body + '</div>'
    # skip-link
    mt = first_tag(body, 'main')
    if mt:
        mid = get_attr(body, mt, 'id')
        if not isinstance(mid, str) or not mid:
            mid = 'wp--skip-link--target'
            body = set_attrs(body, mt, {'id': mid})
        body = '<a class="skip-link screen-reader-text" id="wp-skip-link" href="#%s">%s</a>' % (esc_attr(mid), T['Skip to content']) + body
    if args.rendered and args.raw:
        raw_css_for_rendered(R, Path(args.raw).read_text(encoding='utf-8'), content, theme, blocks, media, post, system, warnings)
    if args.rendered:
        rendered_mode_css(R, body)
    if R.lightbox:
        bgc = get_path(theme.styles, ('color', 'background')) or '#fff'
        tc = get_path(theme.styles, ('color', 'text')) or '#000'
        body += LIGHTBOX_OVERLAY.format(dialog=T['Enlarged images'], close=T['Close'], close_color=esc_attr(tc), bg=esc_attr(bgc),
                                        prev=T['Previous'], next=T['Next'])
    # стили
    used = set(R.used_blocks)
    gcss = theme.global_stylesheet(custom_css or '', used)
    vcss = ''.join(R.variation_css)
    bcss = R.store.css()
    block_css_path = Path(args.block_css) if args.block_css else (DATA / 'block-library.css')
    if not block_css_path.exists():
        block_css_path = ASSETS / 'wp-block-library.css'
        warnings.append('Нет tools/wp-data/block-library.css — использован preview-assets/wp-block-library.css')
    tt5_css = (DATA / 'tt5' / 'style.min.css').read_text(encoding='utf-8') if (DATA / 'tt5' / 'style.min.css').exists() else ''
    skip_css = (DATA / 'skip-link.min.css').read_text(encoding='utf-8') if (DATA / 'skip-link.min.css').exists() else ''
    fonts = font_face_css(theme, warnings)
    # body classes
    bc = []
    if args.front:
        bc.append('home')
    bc.append('wp-singular')
    tslug = Path(args.template).stem if args.template.endswith('.html') else args.template
    if tslug in ('page', 'index', 'singular'):
        bc.append('page-template-default')
    else:
        bc += ['page-template', 'page-template-' + sanitize_title(tslug)]
    bc += ['page', 'page-id-%d' % args.page_id]
    if args.parent_id:
        bc.append('parent-pageid-%d' % args.parent_id)
    if args.logo_id:
        bc.append('wp-custom-logo')
    bc += ['wp-embed-responsive', 'wp-theme-twentytwentyfive']
    if args.body_class:
        bc += args.body_class.split()
    if args.front:
        doc_title = '%s%s' % (args.site_title, (' – ' + args.site_tagline) if args.site_tagline else '')
    else:
        doc_title = '%s – %s' % (args.title or '', args.site_title)
    page = ('<!DOCTYPE html>\n<html lang="ru-RU">\n<head>\n<meta charset="UTF-8" />\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
            '<title>%s</title>\n'
            '<!-- preview.py: эмуляция WordPress 7.1.3 + Twenty Twenty-Five; шаблон %s -->\n'
            '<style id="wp-img-auto-sizes-contain-inline-css">img:is([sizes=auto i],[sizes^="auto," i]){contain-intrinsic-size:3000px 1500px}</style>\n'
            '<link rel="stylesheet" id="wp-block-library-css" href="%s" media="all" />\n'
            '<style id="global-styles-inline-css">\n%s\n</style>\n'
            '%s'
            '<style id="core-block-supports-inline-css">\n%s\n</style>\n'
            '<style id="wp-block-template-skip-link-inline-css">\n%s\n</style>\n'
            '<style id="twentytwentyfive-style-inline-css">\n%s\n</style>\n'
            '<style class="wp-fonts-local">\n%s</style>\n'
            '</head>\n<body class="%s">\n\n%s\n</body>\n</html>\n') % (
        esc_html(doc_title), esc_html(args.template), block_css_path.as_uri(), gcss,
        ('<style id="block-style-variation-styles-inline-css">\n%s\n</style>\n' % vcss) if vcss else '',
        bcss, skip_css, tt5_css, fonts, ' '.join(bc), body)
    page = media.replace_urls(page)
    for u in sorted(media.missing):
        warnings.append('Медиафайл не найден в media.json: %s' % u)
    stats = {'used_blocks': sorted(used), 'unique_ids': R.uid}
    return page, stats


# ─────────────────────────────────────────────────────────────────────────────
# Скриншоты и аудит
# ─────────────────────────────────────────────────────────────────────────────

AUDIT_JS = r'''
(opts) => {
  const doc = document.documentElement;
  const vw = doc.clientWidth;
  const res = {};
  const cv = document.createElement('canvas'); cv.width = cv.height = 1;
  const cx = cv.getContext('2d', {willReadFrequently: true});
  const rgba = (str) => {
    if (!str || str === 'transparent') return {r:0,g:0,b:0,a:0};
    cx.clearRect(0,0,1,1); cx.fillStyle = '#000'; cx.fillStyle = str;
    cx.fillRect(0,0,1,1); const d = cx.getImageData(0,0,1,1).data;
    return {r:d[0], g:d[1], b:d[2], a:d[3]/255};
  };
  const over = (f, b) => { const a = f.a + b.a*(1-f.a); if (!a) return {r:0,g:0,b:0,a:0};
    return {r:(f.r*f.a + b.r*b.a*(1-f.a))/a, g:(f.g*f.a + b.g*b.a*(1-f.a))/a, b:(f.b*f.a + b.b*b.a*(1-f.a))/a, a}; };
  const lum = (c) => { const f = (v) => { v/=255; return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); };
    return 0.2126*f(c.r) + 0.7152*f(c.g) + 0.0722*f(c.b); };
  const ratio = (a, b) => { const l1 = lum(a), l2 = lum(b); return (Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05); };
  const hex = (c) => '#' + [c.r,c.g,c.b].map(v => Math.round(v).toString(16).padStart(2,'0')).join('') + (c.a < 0.999 ? Math.round(c.a*255).toString(16).padStart(2,'0') : '');
  const visible = (el) => { const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.visibility === 'collapse') return false;
    return el.getClientRects().length > 0; };
  const sel = (el) => { const parts = []; let e = el, depth = 0;
    while (e && e.nodeType === 1 && e !== document.body && depth < 6) {
      let s = e.tagName.toLowerCase();
      if (e.id && !/^(modal-|wp--skip)/.test(e.id)) { parts.unshift(s + '#' + e.id); break; }
      const cls = [...e.classList].filter(c => !/^(wp-container-|wp-elements-|is-layout-|has-global-padding|wp-block-[a-z-]+-is-layout-|is-style-.*--\d+$)/.test(c)).slice(0, 3);
      if (cls.length) s += '.' + cls.join('.');
      const p = e.parentElement;
      if (p) { const same = [...p.children].filter(x => x.tagName === e.tagName); if (same.length > 1) s += ':nth-of-type(' + (same.indexOf(e)+1) + ')'; }
      parts.unshift(s); e = p; depth++; }
    return parts.join(' > '); };
  const txt = (el) => (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80);
  const skipEl = (el) => el.closest('.wp-lightbox-overlay');

  // горизонтальный скролл
  const se = document.scrollingElement;
  res.scroll = {scroll_width: se.scrollWidth, client_width: se.clientWidth, has_scroll: se.scrollWidth > se.clientWidth};
  if (opts.overflow) {
    const offenders = [];
    for (const el of document.body.querySelectorAll('*')) {
      if (skipEl(el)) continue;
      if (!visible(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.width <= 2 && r.height <= 2) continue;
      const ecs = getComputedStyle(el);
      if (ecs.clipPath && ecs.clipPath.startsWith('inset(50%')) continue;
      const left = r.left + scrollX, right = r.right + scrollX;
      if (right <= vw + 0.5 && left >= -0.5) continue;
      let clipped = false, fixed = getComputedStyle(el).position === 'fixed';
      for (let a = el.parentElement; a && a !== document.body && a !== doc && !fixed; a = a.parentElement) {
        const acs = getComputedStyle(a);
        if (acs.position === 'fixed') { fixed = true; break; }
        if (acs.overflowX !== 'visible' || acs.clipPath !== 'none' || /paint|strict|content/.test(acs.contain)) {
          const ar = a.getBoundingClientRect();
          if (ar.right + scrollX <= vw + 0.5 && ar.left + scrollX >= -0.5) { clipped = true; break; } }
      }
      if (clipped || fixed) continue;
      const p = el.parentElement; let parentOver = false;
      if (p && p !== document.body) { const pr = p.getBoundingClientRect(); parentOver = pr.right + scrollX > vw + 0.5 || pr.left + scrollX < -0.5; }
      offenders.push({selector: sel(el), left: Math.round(left), right: Math.round(right), width: Math.round(r.width), origin: !parentOver, text: txt(el).slice(0, 50)});
    }
    res.overflow_offenders = offenders.filter(o => o.origin).slice(0, 40);
    res.overflow_total = offenders.length;
  }
  if (!opts.full) return res;

  // картинки
  res.broken_images = []; res.images_without_alt = []; res.images_empty_alt = [];
  for (const img of document.images) {
    if (skipEl(img)) continue;
    const src = img.getAttribute('src');
    if (!src) { res.broken_images.push({selector: sel(img), src: null, reason: 'нет src'}); continue; }
    if (!img.complete || !img.naturalWidth) res.broken_images.push({selector: sel(img), src: src.slice(0, 160), reason: 'не загрузилась'});
    if (!img.hasAttribute('alt')) res.images_without_alt.push({selector: sel(img), src: src.slice(-80)});
    else if (img.getAttribute('alt').trim() === '' && !img.closest('a,button')) res.images_empty_alt.push({selector: sel(img), src: src.slice(-80), decorative_cover: img.classList.contains('wp-block-cover__image-background')});
  }
  // ссылки и кнопки
  const accName = (el) => {
    const al = el.getAttribute('aria-label'); if (al && al.trim()) return al.trim();
    const lb = el.getAttribute('aria-labelledby'); if (lb) { const t = lb.split(/\s+/).map(id => document.getElementById(id)).filter(Boolean).map(x => x.textContent).join(' ').trim(); if (t) return t; }
    const t = (el.textContent || '').replace(/\s+/g, ' ').trim(); if (t) return t;
    for (const i of el.querySelectorAll('img[alt]')) if (i.alt.trim()) return i.alt.trim();
    for (const s of el.querySelectorAll('svg title')) if (s.textContent.trim()) return s.textContent.trim();
    const ti = el.getAttribute('title'); if (ti && ti.trim()) return ti.trim();
    return '';
  };
  res.empty_links = []; res.links_without_href = [];
  for (const a of document.querySelectorAll('a')) {
    if (skipEl(a)) continue;
    const href = a.getAttribute('href');
    if (href === null || href.trim() === '' || href.trim() === '#') res.links_without_href.push({selector: sel(a), text: txt(a), href});
    if (!accName(a)) res.empty_links.push({selector: sel(a), href, visible: visible(a)});
  }
  res.empty_buttons = [];
  for (const b of document.querySelectorAll('button')) {
    if (skipEl(b) || b.classList.contains('lightbox-trigger')) continue;
    if (!accName(b)) res.empty_buttons.push({selector: sel(b), visible: visible(b)});
  }
  // заголовки
  const hs = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].filter(h => !skipEl(h));
  res.h1 = hs.filter(h => h.tagName === 'H1').map(h => ({text: txt(h), visible: visible(h)}));
  res.heading_outline = hs.map(h => ({level: +h.tagName[1], text: txt(h).slice(0, 60), visible: visible(h)}));
  res.heading_level_skips = [];
  let prev = 0;
  for (const h of res.heading_outline) { if (prev && h.level > prev + 1) res.heading_level_skips.push({from: prev, to: h.level, text: h.text}); prev = h.level; }
  // дубли id
  const ids = {}; for (const e of document.querySelectorAll('[id]')) ids[e.id] = (ids[e.id] || 0) + 1;
  res.duplicate_ids = Object.entries(ids).filter(([k, v]) => v > 1).map(([k, v]) => ({id: k, count: v}));
  // анимации
  try { const an = document.getAnimations(); res.animations = {running: an.length, infinite: an.filter(a => { const t = a.effect && a.effect.getTiming && a.effect.getTiming(); return t && t.iterations === Infinity; }).length}; } catch (e) { res.animations = null; }

  // контраст
  const layersCache = new Map();
  const bgCandidates = (el) => {
    // список возможных цветов фона под элементом (с учётом градиентов) + флаг «картинка»
    const layers = []; let image = false;
    for (let e = el; e; e = e.parentElement) {
      const cs = getComputedStyle(e);
      for (const ps of ['::after', '::before']) {
        const pcs = getComputedStyle(e, ps);
        if (pcs.content && pcs.content !== 'none' && (pcs.position === 'absolute' || pcs.position === 'fixed') && e !== el) {
          const er = e.getBoundingClientRect(), pw = parseFloat(pcs.width), ph = parseFloat(pcs.height);
          const covers = pw >= er.width * 0.9 && ph >= er.height * 0.9;
          const pc = rgba(pcs.backgroundColor); if (pc.a > 0 && covers) layers.push({kind: 'color', c: pc});
        }
      }
      const bi = cs.backgroundImage;
      // узкий неповторяющийся градиент (подчёркивание 100% 2px и т.п.) под текстом не лежит — не фон
      const er0 = e.getBoundingClientRect();
      const pxv = (v, full) => v.endsWith('px') ? parseFloat(v) : (v.endsWith('%') ? parseFloat(v) / 100 * full : full);
      const thinDeco = bi && bi !== 'none' && !/url\(/.test(bi) &&
        cs.backgroundRepeat.split(',').every(r => /no-repeat/.test(r)) &&
        cs.backgroundSize.split(',').every(s => { const m = s.trim().split(/\s+/); const w = m[0] || 'auto', h = m[1] || 'auto';
          return pxv(h, er0.height) < er0.height * 0.4 || pxv(w, er0.width) < er0.width * 0.4; });
      if (bi && bi !== 'none' && !thinDeco) {
        if (/url\(/.test(bi)) image = true;
        const stops = [...bi.matchAll(/(rgba?\([^)]*\)|color\([^)]*\)|oklab\([^)]*\)|oklch\([^)]*\)|#[0-9a-fA-F]{3,8}\b)/g)].map(m => rgba(m[0]));
        if (stops.length) layers.push({kind: 'grad', stops});
      }
      const bc = rgba(cs.backgroundColor);
      if (bc.a > 0) layers.push({kind: 'color', c: bc});
      if (bc.a >= 0.999) break;
    }
    let cands = [{r:255,g:255,b:255,a:1}];
    for (let i = layers.length - 1; i >= 0; i--) {
      const L = layers[i];
      if (L.kind === 'color') cands = cands.map(b => over(L.c, b));
      else { const n = []; for (const b of cands) for (const s of L.stops) n.push(over(s, b)); cands = n.slice(0, 24); }
    }
    return {cands, image};
  };
  const low = []; const uncertain = []; const seenC = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const done = new Set();
  let node;
  while ((node = walker.nextNode())) {
    if (!node.nodeValue.trim()) continue;
    const el = node.parentElement; if (!el || done.has(el)) continue; done.add(el);
    if (el.closest('svg,script,style,noscript,title,option,.wp-lightbox-overlay')) continue;
    if (!visible(el)) continue;
    const cs = getComputedStyle(el);
    const range = document.createRange(); range.selectNodeContents(node);
    const tr = range.getBoundingClientRect();
    if (tr.width < 1 || tr.height < 1) continue;
    if (tr.right + scrollX < 0 || tr.bottom + scrollY < 0) continue;
    let hidden = false, op = 1;
    for (let a = el; a && a !== doc; a = a.parentElement) {
      const acs = getComputedStyle(a); op *= parseFloat(acs.opacity);
      if (op < 0.02) { hidden = true; break; }
      // сам элемент тоже может обрезать свой текст (приём image replacement: text-indent + overflow:hidden)
      if (acs.overflowX !== 'visible' || acs.overflowY !== 'visible' || acs.clipPath !== 'none') {
        const ar = a.getBoundingClientRect();
        if (ar.width < 2 || ar.height < 2 || tr.right <= ar.left || tr.left >= ar.right || tr.bottom <= ar.top || tr.top >= ar.bottom) { hidden = true; break; }
      }
    }
    if (hidden) continue;
    let fg = rgba(cs.color); if (fg.a <= 0.01) continue;
    fg = {r: fg.r, g: fg.g, b: fg.b, a: fg.a * op};
    const {cands, image} = bgCandidates(el);
    let worst = 99, worstBg = cands[0];
    for (const b of cands) { const r = ratio(over(fg, b), b); if (r < worst) { worst = r; worstBg = b; } }
    const fs = parseFloat(cs.fontSize), fw = parseInt(cs.fontWeight) || 400;
    const large = fs >= 24 || (fs >= 18.66 && fw >= 700);
    const item = {selector: sel(el), text: node.nodeValue.replace(/\s+/g, ' ').trim().slice(0, 60), ratio: Math.round(worst * 100) / 100,
      fg: hex(fg), bg: hex(worstBg), font_size: Math.round(fs * 10) / 10, font_weight: fw, large, aa_fail: worst < (large ? 3 : 4.5), bg_has_gradient: cands.length > 1};
    const key = item.selector + '|' + item.fg + '|' + item.bg;
    if (seenC.has(key)) continue; seenC.add(key);
    if (image) { if (uncertain.length < 60) uncertain.push(Object.assign(item, {reason: 'фон — картинка, контраст оценён по цвету под ней'})); continue; }
    if (worst < 4.5) low.push(item);
  }
  low.sort((a, b) => a.ratio - b.ratio);
  res.low_contrast = low.slice(0, 200);
  res.contrast_uncertain = uncertain;
  return res;
}
'''

PREP_JS = r'''
async () => {
  for (const img of document.querySelectorAll('img[loading="lazy"]')) img.loading = 'eager';
  const imgs = [...document.images].filter(i => i.getAttribute('src'));
  await Promise.race([
    Promise.all(imgs.map(i => i.complete ? null : new Promise(r => { i.addEventListener('load', r, {once: true}); i.addEventListener('error', r, {once: true}); }))),
    new Promise(r => setTimeout(r, 8000))]);
  if (document.fonts && document.fonts.ready) await document.fonts.ready;
  return {fonts: [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family + ' ' + f.weight)};
}
'''

UNCLIP_CSS = 'html,body{overflow-x:visible!important;overflow:visible!important;}'

MAX_SHOT_H = 16000  # больше — предел текстуры Chromium (16384): ниже окно не рисуется, снимаем частями

UNSTICK_JS = '''() => { let n = 0; for (const el of document.querySelectorAll('*')) {
  if (getComputedStyle(el).position === 'sticky') { el.style.setProperty('position', 'relative', 'important');
    for (const k of ['top', 'bottom', 'left', 'right']) el.style.setProperty(k, 'auto', 'important'); n++; } } return n; }'''


def tiled_shot(page, path, vp, h, tile=8000):
    """Очень длинная страница: окно высотой tile, прокрутка кусками и склейка. Липкие элементы на время съёмки
    переводятся в relative (в потоке документа то же место), чтобы каждый кусок совпадал с full-page рендером."""
    from PIL import Image
    import io
    page.set_viewport_size({'width': vp['width'], 'height': tile})
    page.wait_for_timeout(250)
    page.evaluate(UNSTICK_JS)
    page.evaluate(PREP_JS)
    h = page.evaluate('Math.ceil(Math.max(document.documentElement.scrollHeight, document.body.scrollHeight))')
    canvas = Image.new('RGB', (vp['width'], h))
    y = 0
    while y < h:
        page.evaluate('(y) => window.scrollTo(0, y)', y)
        page.wait_for_timeout(200)
        page.evaluate(DECODE_JS)
        sy = page.evaluate('window.scrollY')  # у последнего куска прокрутка упирается в низ документа
        shot = Image.open(io.BytesIO(page.screenshot(full_page=False, animations='disabled'))).convert('RGB')
        canvas.paste(shot.crop((0, y - sy, vp['width'], min(tile, h - sy))), (0, y))
        y = max(sy + tile, y + 1)
    canvas.save(path)
    page.reload(wait_until='load')  # вернуть липкость и исходный размер окна для аудита
    page.set_viewport_size(vp)
    page.evaluate(PREP_JS)
    page.wait_for_timeout(150)


DECODE_JS = 'async () => { await Promise.all([...document.images].filter(i => i.getAttribute("src")).map(i => i.decode().catch(() => null))); }'


def full_page_shot(page, path, vp):
    """Full-page снимок без пропавших картинок.
    Штатный full_page=True в Chromium нестабилен: при пересчёте размеров для съёмки уже загруженные картинки
    с srcset иногда не успевают отрисоваться (на мобильной главной пропадали рендеры продукции примерно в половине
    запусков). Поэтому окно растягивается на всю высоту документа, картинки ждутся и декодируются, снимается окно
    целиком, затем исходный размер окна восстанавливается."""
    h = page.evaluate('Math.ceil(Math.max(document.documentElement.scrollHeight, document.body.scrollHeight))')
    if h > MAX_SHOT_H:
        return tiled_shot(page, path, vp, h)
    page.set_viewport_size({'width': vp['width'], 'height': max(h, vp['height'])})
    page.wait_for_timeout(250)
    page.evaluate(PREP_JS)
    page.evaluate(DECODE_JS)
    h2 = page.evaluate('Math.ceil(Math.max(document.documentElement.scrollHeight, document.body.scrollHeight))')
    if h2 > h:  # высота могла измениться после догрузки картинок
        page.set_viewport_size({'width': vp['width'], 'height': h2})
        page.wait_for_timeout(200)
        page.evaluate(DECODE_JS)
    page.wait_for_timeout(100)
    page.screenshot(path=path, full_page=False, animations='disabled')
    page.set_viewport_size(vp)
    page.wait_for_timeout(150)


def open_menu_js():
    return r'''
() => {
  const c = document.querySelector('.wp-block-navigation__responsive-container');
  if (!c) return false;
  c.classList.add('is-menu-open', 'has-modal-open');
  const d = c.querySelector('.wp-block-navigation__responsive-dialog');
  if (d) { d.setAttribute('aria-modal', 'true'); d.setAttribute('role', 'dialog'); d.setAttribute('aria-label', '%s'); }
  document.documentElement.classList.add('has-modal-open');
  return true;
}''' % T['Menu']


def shoot_and_audit(html_path, prefix, args, warnings):
    from playwright.sync_api import sync_playwright
    report = {}
    failed = []
    url = Path(html_path).resolve().as_uri()
    with sync_playwright() as p:
        # proxy-«тупик»: даже если маршрут не перехватит запрос, наружу (в т.ч. на svr-mos.ru) он не уйдёт
        browser = p.chromium.launch(executable_path=CHROME, args=['--font-render-hinting=none', '--disable-gpu'],
                                    proxy={'server': 'http://127.0.0.1:9'})

        def mk(vp, mobile=False):
            ctx = browser.new_context(viewport=vp, device_scale_factor=args.scale, reduced_motion=args.motion,
                                      locale='ru-RU', has_touch=mobile)
            page = ctx.new_page()

            def route(r):
                u = r.request.url
                if u.startswith('file:') or u.startswith('data:') or u.startswith('about:') or u.startswith('blob:'):
                    return r.continue_()
                failed.append({'url': u[:200], 'reason': 'внешний запрос заблокирован (нет сети)'})
                return r.abort()
            page.route('**/*', route)
            def on_failed(req):
                if not req.url.startswith('file:'):
                    return
                # ERR_ABORTED у существующего файла — браузер отменил кандидат srcset при смене размера окна, не ошибка
                if (req.failure or '').endswith('ERR_ABORTED'):
                    from urllib.parse import unquote, urlparse
                    if Path(unquote(urlparse(req.url).path)).is_file():
                        return
                failed.append({'url': req.url[:200], 'reason': req.failure or 'failed'})
            page.on('requestfailed', on_failed)
            page.on('pageerror', lambda e: warnings.append('JS-ошибка на странице: %s' % e))
            page.goto(url, wait_until='load')
            page.evaluate(PREP_JS)
            page.wait_for_timeout(150)
            return ctx, page

        # desktop
        ctx, page = mk({'width': 1440, 'height': 900})
        full_page_shot(page, prefix + '-desktop.png', {'width': 1440, 'height': 900})
        report['desktop'] = page.evaluate(AUDIT_JS, {'overflow': True, 'full': True})
        ctx.close()
        # mobile
        ctx, page = mk({'width': 390, 'height': 844}, mobile=True)
        full_page_shot(page, prefix + '-mobile.png', {'width': 390, 'height': 844})
        report['mobile'] = page.evaluate(AUDIT_JS, {'overflow': True, 'full': True})
        page.add_style_tag(content=UNCLIP_CSS)
        page.wait_for_timeout(50)
        report['mobile_unclipped'] = page.evaluate(AUDIT_JS, {'overflow': True, 'full': False})
        if args.menu:
            page.reload(wait_until='load')
            page.evaluate(PREP_JS)
            ok = page.evaluate(open_menu_js())
            if ok:
                page.wait_for_timeout(300)
                page.screenshot(path=prefix + '-mobile-menu.png', full_page=False, animations='disabled')
                report['mobile_menu'] = page.evaluate(AUDIT_JS, {'overflow': False, 'full': True})
            else:
                warnings.append('--menu: на странице нет оверлей-меню core/navigation')
        ctx.close()
        # доп. ширины
        widths = {}
        for w in args.check_widths:
            ctx, page = mk({'width': w, 'height': 900}, mobile=w < 782)
            page.add_style_tag(content=UNCLIP_CSS)
            page.wait_for_timeout(50)
            r = page.evaluate(AUDIT_JS, {'overflow': True, 'full': False})
            widths[str(w)] = {'scroll_width': r['scroll']['scroll_width'], 'client_width': r['scroll']['client_width'],
                              'has_scroll': r['scroll']['has_scroll'], 'offenders': r.get('overflow_offenders', [])[:10]}
            ctx.close()
        browser.close()
    report['widths'] = widths
    seen = set()
    report['failed_requests'] = [f for f in failed if not (f['url'] in seen or seen.add(f['url']))]
    return report


def summarize(raw, warnings, stats, args):
    d, m, mu = raw.get('desktop', {}), raw.get('mobile', {}), raw.get('mobile_unclipped', {})

    def merge_lists(key):
        out, seen = [], set()
        for vp, src in (('desktop', d), ('mobile', m)):
            for it in src.get(key, []) or []:
                k = json.dumps(it, sort_keys=True, ensure_ascii=False)
                if k in seen:
                    continue
                seen.add(k)
                out.append(dict(it, viewport=vp))
        return out

    low = []
    seen = {}
    for vp, src in (('desktop', d), ('mobile', m)):
        for it in src.get('low_contrast', []) or []:
            k = (it['selector'], it['fg'], it['bg'])
            if k in seen:
                seen[k]['viewport'] = 'both'
                continue
            item = dict(it, viewport=vp)
            seen[k] = item
            low.append(item)
    low.sort(key=lambda x: x['ratio'])
    rep = {
        'tool': 'preview.py (эмуляция WordPress 7.1.3 + Twenty Twenty-Five)',
        'input': {'content': str(args.content), 'template': args.template, 'title': args.title, 'system': str(args.system),
                  'rendered': args.rendered, 'page_id': args.page_id, 'motion': args.motion},
        'files': {'html': args.out + '.html', 'desktop': args.out + '-desktop.png', 'mobile': args.out + '-mobile.png'},
        'mobile_horizontal_scroll': {
            'has_scroll': bool(m.get('scroll', {}).get('has_scroll')),
            'scroll_width': m.get('scroll', {}).get('scroll_width'),
            'client_width': m.get('scroll', {}).get('client_width'),
            'has_scroll_without_overflow_clip': bool(mu.get('scroll', {}).get('has_scroll')),
            'scroll_width_without_overflow_clip': mu.get('scroll', {}).get('scroll_width'),
            'offenders': mu.get('overflow_offenders', []),
            'offenders_total': mu.get('overflow_total', 0),
            'note': 'offenders считаются с отключённым overflow у html/body: body{overflow-x:clip} не должен маскировать ошибки',
        },
        'desktop_horizontal_scroll': {'has_scroll': bool(d.get('scroll', {}).get('has_scroll')),
                                      'scroll_width': d.get('scroll', {}).get('scroll_width'),
                                      'offenders': d.get('overflow_offenders', [])[:20]},
        'broken_images': merge_lists('broken_images'),
        'failed_requests': raw.get('failed_requests', []),
        'empty_links': merge_lists('empty_links'),
        'links_without_href': merge_lists('links_without_href'),
        'empty_buttons': merge_lists('empty_buttons'),
        'h1_count': {'desktop': len(d.get('h1', [])), 'mobile': len(m.get('h1', [])),
                     'desktop_visible': len([h for h in d.get('h1', []) if h.get('visible')]),
                     'texts': [h['text'] for h in d.get('h1', [])]},
        'low_contrast': low,
        'low_contrast_aa_fail': [x for x in low if x.get('aa_fail')],
        'contrast_uncertain': (d.get('contrast_uncertain') or [])[:30],
        'images_without_alt': merge_lists('images_without_alt'),
        'images_empty_alt': merge_lists('images_empty_alt'),
        'duplicate_ids': d.get('duplicate_ids', []),
        'heading_outline': d.get('heading_outline', []),
        'heading_level_skips': d.get('heading_level_skips', []),
        'animations': {'desktop': d.get('animations'), 'mobile': m.get('animations')},
        'widths': raw.get('widths', {}),
        'warnings': warnings,
        'used_blocks': stats.get('used_blocks', []),
    }
    if 'mobile_menu' in raw:
        rep['mobile_menu'] = {'file': args.out + '-mobile-menu.png',
                              'low_contrast': raw['mobile_menu'].get('low_contrast', [])[:30]}
    rep['summary'] = {
        'mobile_horizontal_scroll': rep['mobile_horizontal_scroll']['has_scroll'] or rep['mobile_horizontal_scroll']['has_scroll_without_overflow_clip'],
        'broken_images': len(rep['broken_images']),
        'failed_requests': len(rep['failed_requests']),
        'empty_links': len(rep['empty_links']),
        'links_without_href': len(rep['links_without_href']),
        'empty_buttons': len(rep['empty_buttons']),
        'h1_count': rep['h1_count']['desktop'],
        'low_contrast_below_4_5': len(low),
        'low_contrast_aa_fail': len(rep['low_contrast_aa_fail']),
        'images_without_alt': len(rep['images_without_alt']),
        'duplicate_ids': len(rep['duplicate_ids']),
        'warnings': len(warnings),
        'widths_with_scroll': [w for w, v in rep['widths'].items() if v.get('has_scroll')],
    }
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description='Превью страницы WordPress 7.1.3 + TT5 без WordPress')
    ap.add_argument('--content', required=True, help='файл с блочной разметкой контента (или content.rendered при --rendered)')
    ap.add_argument('--template', default='page', help='page | page-no-title | другой slug шаблона | путь к .html')
    ap.add_argument('--title', default='', help='заголовок страницы (core/post-title, <title>)')
    ap.add_argument('--out', required=True, help='префикс выходных файлов')
    ap.add_argument('--system', default=str(DEFAULT_SYSTEM), help='папка дизайн-системы (global-styles.json, header.html, footer.html, page.html…)')
    ap.add_argument('--rendered', action='store_true', help='на входе готовый HTML (content.rendered из REST)')
    ap.add_argument('--raw', default=None, help='при --rendered: исходная блочная разметка (content.raw), чтобы точно '
                                                'восстановить CSS wp-container-*/wp-elements-*')
    ap.add_argument('--page-id', type=int, default=0, help='id страницы (body .page-id-N, текущий пункт меню)')
    ap.add_argument('--parent-id', type=int, default=0, help='id родительской страницы (body .parent-pageid-N, как в WP)')
    ap.add_argument('--front', action='store_true', help='это главная страница (класс home, aria-current у логотипа/названия)')
    ap.add_argument('--permalink', default='', help='URL страницы (для post-title isLink)')
    ap.add_argument('--site-title', default='СВР', help='название сайта (core/site-title, <title>)')
    ap.add_argument('--site-tagline', default='', help='описание сайта (core/site-tagline)')
    ap.add_argument('--logo-id', type=int, default=7, help='id логотипа в медиатеке (core/site-logo); 0 — нет логотипа')
    ap.add_argument('--logo-alt', default='', help='alt логотипа core/site-logo (по умолчанию — название сайта)')
    ap.add_argument('--css', default=None, help='файл styles.css (переопределяет styles.css из global-styles.json)')
    ap.add_argument('--global-styles', default=None, help='путь к global-styles.json (по умолчанию <system>/global-styles.json)')
    ap.add_argument('--block-css', default=None, help='CSS блоков WP (по умолчанию tools/wp-data/block-library.css из WP 7.1.3)')
    ap.add_argument('--body-class', default='', help='дополнительные классы body')
    ap.add_argument('--motion', choices=['reduce', 'no-preference'], default='reduce',
                    help='prefers-reduced-motion при съёмке (reduce — показывает финальные состояния анимаций)')
    ap.add_argument('--menu', action='store_true', help='дополнительно снять мобильное меню открытым (<out>-mobile-menu.png)')
    ap.add_argument('--check-widths', default='', help='доп. ширины для проверки горизонтального скролла, напр. 320,360,768,1024')
    ap.add_argument('--scale', type=float, default=1, help='device scale factor скриншотов')
    ap.add_argument('--no-shots', action='store_true', help='только собрать HTML (без браузера)')
    args = ap.parse_args(argv)
    args.check_widths = [int(x) for x in args.check_widths.split(',') if x.strip()]
    if not args.page_id:
        args.page_id = 49 if args.front else 1000
    if not args.logo_alt:
        args.logo_alt = args.site_title
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    args.out = str(out)
    warnings = []
    t0 = time.time()
    page, stats = build_page(args, warnings)
    html_path = args.out + '.html'
    Path(html_path).write_text(page, encoding='utf-8')
    raw = {}
    if not args.no_shots:
        raw = shoot_and_audit(html_path, args.out, args, warnings)
    rep = summarize(raw, warnings, stats, args)
    rep['elapsed_sec'] = round(time.time() - t0, 2)
    Path(args.out + '-report.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
    s = rep['summary']
    print('HTML:    %s' % html_path)
    if not args.no_shots:
        print('Desktop: %s-desktop.png\nMobile:  %s-mobile.png' % (args.out, args.out))
        if args.menu:
            print('Menu:    %s-mobile-menu.png' % args.out)
    print('Report:  %s-report.json' % args.out)
    print('Итог: гориз.скролл на мобиле=%s, битых картинок=%d, пустых ссылок=%d, h1=%d, контраст<4.5: %d (AA-fail %d), '
          'без alt=%d, предупреждений=%d' % (s['mobile_horizontal_scroll'], s['broken_images'], s['empty_links'],
                                             s['h1_count'], s['low_contrast_below_4_5'], s['low_contrast_aa_fail'],
                                             s['images_without_alt'], s['warnings']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
