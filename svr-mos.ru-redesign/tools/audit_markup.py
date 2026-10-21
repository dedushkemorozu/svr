"""Аудит блочной разметки (шаблоны, части шаблона, сниппеты components.md, demo-content) без WordPress.
Проверяет: баланс комментариев блоков и JSON атрибутов; className/align/fontSize/anchor/level/id ↔ HTML обёртки;
ссылки (https://svr-mos.ru/<slug>/, tel:, mailto:, якоря, PDF); телефон; картинки ↔ media.json (id, URL, alt);
RichText без <span>/<br>/<b>/<i>/<small>; h1 (в шапке/подвале — ни одного); классы svr-* ↔ styles.css.
Валидность для редактора (isValid) проверяет tools/validate_blocks.py на локальном стенде WP.
Запуск: python3 tools/audit_markup.py [файлы… | components.md]"""
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from preview import parse_blocks  # noqa: E402

R = pathlib.Path(__file__).resolve().parent.parent
SYS = R / 'system'
MEDIA = {m['id']: m for m in json.loads((R.parent / 'media.json').read_text(encoding='utf-8'))}
SLUGS = {'', 'obj', 'elteza', 'russkii', 'os3-marino', 'os2-marino', 'prod', 'docs', 'rekvizit', 'contact',
         'prod/stanciya-dozirovaniya', 'prod/reaktor-trehkamernyj', 'prod/reaktor-odnokamernyj', 'prod/ustanovka-obezzarazhivaniya', 'prod/kns'}
ANCHORS = {'etapy', 'produkciya', 'obekty', 'dokumenty', 'kontakty', 'poz-01', 'poz-02', 'poz-03', 'poz-04', 'poz-05'}
PHONE_HREF, PHONE_TXT, MAIL = 'tel:+79652808090', '8 965 280-80-90', 'mailto:info@svr-mos.ru'
PDF = 'https://svr-mos.ru/wp-content/uploads/2026/10/svr-deklaraciya-eac.pdf'
CSS = (SYS / 'styles.css').read_text(encoding='utf-8')
CSS_CLASSES = set(re.findall(r'\.(svr-[a-z0-9_-]+)', CSS))
RICH = {'core/paragraph', 'core/heading', 'core/list-item', 'core/table', 'core/button'}
# блоки, у которых обёртка — первый тег собственного HTML, и в нём должны быть классы атрибутов
STATIC = {'core/group', 'core/columns', 'core/column', 'core/heading', 'core/paragraph', 'core/list', 'core/image',
          'core/buttons', 'core/button', 'core/table', 'core/gallery', 'core/file'}
TAG_RE = re.compile(r'<([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>')


def first_tag(html):
    m = TAG_RE.search(html)
    return (m.group(1).lower(), m.group(2)) if m else (None, '')


def attr(attrs_str, name):
    m = re.search(r'\b%s\s*=\s*"([^"]*)"' % name, attrs_str)
    return m.group(1) if m else None


def audit(src, label, used_classes, issues, ctx):
    warns = []
    blocks = parse_blocks(src, warns)
    for w in warns:
        issues.append('%s: %s' % (label, w))
    # JSON в комментариях: каждый открывающий/void комментарий должен разбираться
    for m in re.finditer(r'<!--\s+wp:([a-z0-9/-]+)\s+(\{.*?\})\s+(/?)-->', src, re.S):
        try:
            json.loads(m.group(2))
        except Exception as e:
            issues.append('%s: битый JSON у wp:%s — %s' % (label, m.group(1), e))
    if src.count('<!-- wp:') - len(re.findall(r'<!-- wp:[^>]*/-->', src)) != src.count('<!-- /wp:'):
        issues.append('%s: число открывающих и закрывающих комментариев блоков не совпадает' % label)

    def walk(bs, parent=None):
        for b in bs:
            if not b.name:
                if b.inner_html.strip():
                    issues.append('%s: свободный HTML вне блоков: %r' % (label, b.inner_html.strip()[:60]))
                continue
            own = ''.join(c for c in b.inner_content if c is not None)
            a = b.attrs
            cls_attr = a.get('className', '')
            for c in cls_attr.split():
                if c.startswith('svr-'):
                    used_classes.setdefault(c, set()).add(label)
            if b.name == 'core/html':  # классы внутри произвольного HTML/SVG
                for cl in re.findall(r'\bclass="([^"]*)"', own):
                    for c in cl.split():
                        if c.startswith('svr-'):
                            used_classes.setdefault(c, set()).add(label)
            if b.name in STATIC and own.strip():
                tag, tattrs = first_tag(own)
                if b.name == 'core/button':
                    tag, tattrs = first_tag(own)  # div.wp-block-button
                classes = (attr(tattrs, 'class') or '').split()
                for c in cls_attr.split():
                    if c not in classes:
                        issues.append('%s: %s className «%s» нет в классах обёртки <%s class="%s">' % (label, b.name, c, tag, ' '.join(classes)))
                for c in classes:
                    if c.startswith('svr-') and c not in cls_attr.split() and b.name != 'core/image':
                        issues.append('%s: %s класс «%s» в HTML, но не в className' % (label, b.name, c))
                if a.get('align') and 'align' + a['align'] not in classes:
                    issues.append('%s: %s align:%s без класса align%s' % (label, b.name, a['align'], a['align']))
                if not a.get('align') and any(c in ('alignwide', 'alignfull') for c in classes):
                    issues.append('%s: %s класс align* без атрибута align' % (label, b.name))
                if a.get('fontSize') and 'has-%s-font-size' % a['fontSize'] not in classes:
                    issues.append('%s: %s fontSize:%s без has-%s-font-size' % (label, b.name, a['fontSize'], a['fontSize']))
                if a.get('anchor') and attr(tattrs, 'id') != a['anchor']:
                    issues.append('%s: %s anchor:%s ≠ id=%s' % (label, b.name, a['anchor'], attr(tattrs, 'id')))
                if b.name == 'core/group':
                    want = a.get('tagName', 'div')
                    if tag != want:
                        issues.append('%s: group tagName %s, а тег <%s>' % (label, want, tag))
                if b.name == 'core/heading':
                    want = 'h%d' % a.get('level', 2)
                    if tag != want:
                        issues.append('%s: heading level %s, а тег <%s>' % (label, a.get('level', 2), tag))
                if b.name == 'core/column' and a.get('width') and 'flex-basis:%s' % a['width'] not in (attr(tattrs, 'style') or ''):
                    issues.append('%s: column width %s без style flex-basis' % (label, a['width']))
                if b.name == 'core/image':
                    img = re.search(r'<img\b([^>]*)>', own)
                    if img:
                        ia = img.group(1)
                        iid = a.get('id')
                        if iid is not None and 'wp-image-%s' % iid not in (attr(ia, 'class') or ''):
                            issues.append('%s: image id %s без класса wp-image-%s' % (label, iid, iid))
                        if iid in MEDIA and attr(ia, 'src') != MEDIA[iid]['url']:
                            issues.append('%s: image id %s src=%s ≠ media.json %s' % (label, iid, attr(ia, 'src'), MEDIA[iid]['url']))
                        if iid not in MEDIA:
                            issues.append('%s: image id %s нет в media.json' % (label, iid))
                        if iid in (8, 9, 10):
                            issues.append('%s: image id %s — по spec не используется' % (label, iid))
                        if attr(ia, 'alt') is None or not attr(ia, 'alt').strip():
                            issues.append('%s: image id %s без alt' % (label, iid))
                        if a.get('sizeSlug') and 'size-%s' % a['sizeSlug'] not in classes:
                            issues.append('%s: image sizeSlug %s без size-%s' % (label, a['sizeSlug'], a['sizeSlug']))
            if b.name in RICH:
                for bad in re.findall(r'<(span|br|b|i|small|font|u|div)\b', own if b.name != 'core/button' else re.sub(r'^<div[^>]*>|</div>\s*$', '', own.strip())):
                    if b.name == 'core/table' and bad == 'div':
                        continue
                    issues.append('%s: %s содержит <%s> (RichText выбросит)' % (label, b.name, bad))
            if b.name == 'core/site-title' and a.get('level', 1) == 1:
                issues.append('%s: core/site-title уровня h1 (по умолчанию level 1!) — задать level:0' % label)
            if b.name == 'core/navigation-link':
                url = a.get('url', '')
                if not re.fullmatch(r'https://svr-mos\.ru/(%s)/?' % '|'.join(s for s in SLUGS if s), url):
                    issues.append('%s: navigation-link url %s' % (label, url))
            walk(b.inner_blocks, b)

    walk(blocks)
    # ссылки
    for m in re.finditer(r'href="([^"]*)"', src):
        h = m.group(1)
        ok = (h in (PHONE_HREF, MAIL, PDF) or re.fullmatch(r'https://svr-mos\.ru/(?:(%s)/)?(#[a-z0-9-]+)?' % '|'.join(s for s in SLUGS if s), h)
              or (h.startswith('#') and h[1:] in ANCHORS) or h.startswith('https://yandex.ru/maps/?text='))
        if not ok:
            issues.append('%s: подозрительная ссылка href="%s"' % (label, h))
        if h.startswith('#') and h[1:] in ANCHORS and ctx.get('anchors') is not None:
            ctx['anchor_refs'].add(h[1:])
        if h.startswith('tel:') and h != PHONE_HREF:
            issues.append('%s: неверный tel: %s' % (label, h))
    for m in re.finditer(r'<a\b[^>]*href="tel:[^"]*"[^>]*>(.*?)</a>', src, re.S):
        t = re.sub(r'<[^>]+>', '', m.group(1)).replace('&nbsp;', ' ').strip()
        if PHONE_TXT not in t and t != 'Позвонить':  # короткая надпись в CTA-листе — по spec §5.2
            issues.append('%s: текст ссылки tel: «%s» без номера %s' % (label, t, PHONE_TXT))
    for m in re.finditer(r'\b(?:8|\+7)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}\b', re.sub(r'<[^>]+>', ' ', src)):
        if re.sub(r'\D', '', m.group(0))[-10:] != '9652808090':
            issues.append('%s: чужой номер телефона в тексте: %s' % (label, m.group(0)))
    if ctx.get('anchors') is not None:
        ctx['anchors'].update(re.findall(r'\bid="([a-z0-9-]+)"', src))
    h1 = len(re.findall(r'<h1\b', src)) + len(re.findall(r'wp:post-title \{[^}]*"level":1', src))
    return blocks, h1


def snippets_from_md(md):
    return [(m.start(), m.group(1)) for m in re.finditer(r'```html\n(.*?)```', md, re.S)]


def main():
    args = sys.argv[1:] or [str(SYS / n) for n in ('header.html', 'footer.html', 'page.html', 'page-no-title.html', '404.html', 'components.md')]
    issues, used = [], {}
    for f in args:
        p = pathlib.Path(f)
        text = p.read_text(encoding='utf-8')
        if p.suffix == '.md':
            heads = [(m.start(), m.group(1)) for m in re.finditer(r'^### (\d\d)\.', text, re.M)]
            for pos, sn in snippets_from_md(text):
                num = [h for s, h in heads if s < pos]
                label = '%s#%s' % (p.name, num[-1] if num else '?')
                ctx = {'anchors': set(), 'anchor_refs': set()}
                _, h1 = audit(sn, label, used, issues, ctx)
                if h1 > 1:
                    issues.append('%s: h1 больше одного (%d)' % (label, h1))
        else:
            ctx = {'anchors': None}
            _, h1 = audit(text, p.name, used, issues, ctx)
            if p.name in ('header.html', 'footer.html') and h1:
                issues.append('%s: в части шаблона есть h1 (%d)' % (p.name, h1))
            if p.name not in ('header.html', 'footer.html') and h1 > 1:
                issues.append('%s: h1 больше одного (%d)' % (p.name, h1))
            print('%s: h1=%d' % (p.name, h1))
    # классы: используемые без стилей / стили без использования (по всем переданным файлам)
    no_css = sorted(c for c in used if c not in CSS_CLASSES)
    print('\nКлассов svr-* в разметке: %d; в styles.css: %d' % (len(used), len(CSS_CLASSES)))
    print('Без стилей в styles.css:', ', '.join('%s (%s)' % (c, ', '.join(sorted(used[c]))[:80]) for c in no_css) or '—')
    dead = sorted(c for c in CSS_CLASSES if c not in used)
    print('В styles.css, но нет в разметке:', ', '.join(dead) or '—')
    print('\n== ISSUES (%d) ==' % len(issues))
    for i in issues:
        print(' -', i)
    return 1 if issues else 0


if __name__ == '__main__':
    sys.exit(main())
