"""Аудит global-styles.json + styles.css (без сети, без WordPress).
1) JSON: структура {settings, styles}, ссылки var:preset|… → существующие slug'и (палитра/градиенты/размеры/отступы/шрифты TT5).
2) styles.css: синтаксис (tinycss2: ошибки разбора правил и деклараций, баланс скобок), запреты REST ('<'),
   var(--wp--preset--*) → существующие slug'и, var(--svr-*) → объявленные переменные.
3) Chromium: каждый селектор разбирается (querySelector в try), каждая декларация без var() — CSS.supports().
4) Эвристики: правила, способные задеть редактор/админку; анимации/transition вне prefers-reduced-motion;
   :focus-visible присутствует; outline:none без замены.
Запуск: python3 tools/audit_css.py [--json system/global-styles.json] [--css system/styles.css]"""
import argparse, json, pathlib, re, sys
import tinycss2

R = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument('--json', default=str(R / 'system/global-styles.json'))
ap.add_argument('--css', default=str(R / 'system/styles.css'))
args = ap.parse_args()

problems, notes = [], []
gs = json.loads(pathlib.Path(args.json).read_text(encoding='utf-8'))
css = pathlib.Path(args.css).read_text(encoding='utf-8')

# ---------- 1. JSON ----------
if set(gs) - {'settings', 'styles'}:
    problems.append('global-styles.json: лишние ключи верхнего уровня %s' % (set(gs) - {'settings', 'styles'}))
st = gs.get('settings', {})
slugs = {
    'color': {p['slug'] for p in st.get('color', {}).get('palette', {}).get('theme', [])},
    'gradient': {p['slug'] for p in st.get('color', {}).get('gradients', {}).get('theme', [])},
    'font-size': {p['slug'] for p in st.get('typography', {}).get('fontSizes', {}).get('theme', [])},
    'spacing': {p['slug'] for p in st.get('spacing', {}).get('spacingSizes', {}).get('theme', [])},
    # TT5 theme.json: fontFamilies не переопределяем — slug'и темы
    'font-family': {'manrope', 'fira-code', 'beiruti', 'literata', 'vollkorn', 'fira-sans', 'platypi', 'ysabeau-office', 'roboto-slab'},
}
if gs['styles'].get('css') is not None and gs['styles']['css'] != css:
    problems.append('styles.css внутри global-styles.json НЕ совпадает с system/styles.css — пересоберите build_system.py')


def walk(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, path + '/' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, path + '[%d]' % i)
    else:
        yield path, o


for path, v in walk(gs):
    if isinstance(v, str):
        for m in re.finditer(r'var:preset\|([a-z-]+)\|([a-z0-9-]+)', v):
            kind, slug = m.groups()
            if kind not in slugs:
                problems.append('JSON %s: неизвестный тип пресета %s' % (path, kind))
            elif slug not in slugs[kind]:
                problems.append('JSON %s: var:preset|%s|%s — slug не существует' % (path, kind, slug))
# дубли slug'ов
for kind, key in (('color', ('color', 'palette')), ('gradient', ('color', 'gradients')),
                  ('font-size', ('typography', 'fontSizes')), ('spacing', ('spacing', 'spacingSizes'))):
    lst = st.get(key[0], {}).get(key[1], {}).get('theme', [])
    s = [p['slug'] for p in lst]
    if len(s) != len(set(s)):
        problems.append('Дубли slug в %s: %s' % (kind, s))

# ---------- 2. CSS: синтаксис ----------
if '<' in css:
    problems.append('styles.css содержит "<" — REST /wp/v2/global-styles отклонит CSS с разметкой')
rules = tinycss2.parse_stylesheet(css, skip_comments=True, skip_whitespace=True)
selectors, decls, at_rules = [], [], []


def line_of(node):
    return getattr(node, 'source_line', '?')


def handle_rules(rules, ctx):
    for r in rules:
        if r.type == 'error':
            problems.append('CSS строка %s: ошибка разбора: %s' % (line_of(r), r.message))
        elif r.type == 'qualified-rule':
            sel = tinycss2.serialize(r.prelude).strip()
            selectors.append((sel, line_of(r), ctx))
            if r.content is None:
                continue
            body = tinycss2.parse_blocks_contents(r.content, skip_comments=True, skip_whitespace=True)
            for d in body:
                if d.type == 'error':
                    problems.append('CSS строка %s (%s): ошибка декларации: %s' % (line_of(d), sel[:60], d.message))
                elif d.type == 'declaration':
                    val = tinycss2.serialize(d.value).strip()
                    if not val:
                        problems.append('CSS строка %s: пустое значение %s' % (line_of(d), d.name))
                    decls.append((d.name, val, d.important, sel, line_of(d), ctx))
                elif d.type in ('qualified-rule', 'at-rule'):
                    problems.append('CSS строка %s: вложенное правило (CSS nesting) в %s — проверьте поддержку' % (line_of(d), sel[:60]))
        elif r.type == 'at-rule':
            pre = tinycss2.serialize(r.prelude).strip()
            at_rules.append((r.lower_at_keyword, pre, line_of(r), ctx))
            if r.lower_at_keyword in ('media', 'supports', 'container', 'layer'):
                if r.content is None:
                    problems.append('CSS строка %s: @%s без блока' % (line_of(r), r.lower_at_keyword))
                    continue
                inner = tinycss2.parse_rule_list(r.content, skip_comments=True, skip_whitespace=True)
                handle_rules(inner, ctx + ['@%s %s' % (r.lower_at_keyword, pre)])
            elif r.lower_at_keyword == 'keyframes':
                pass
            elif r.lower_at_keyword in ('font-face', 'import'):
                problems.append('CSS строка %s: @%s запрещён (шрифты даёт TT5; внешние ресурсы не подключаем)' % (line_of(r), r.lower_at_keyword))
            else:
                notes.append('CSS строка %s: @%s %s' % (line_of(r), r.lower_at_keyword, pre[:60]))


handle_rules(rules, [])

# var(--wp--preset--…) и var(--svr-…)
for m in re.finditer(r'--wp--preset--(color|gradient|font-size|spacing|font-family)--([a-z0-9-]+)', css):
    kind, slug = m.groups()
    if slug not in slugs[kind]:
        problems.append('styles.css: --wp--preset--%s--%s — slug не существует' % (kind, slug))
declared = set(re.findall(r'(--svr-[a-z0-9-]+)\s*:', css))
used = set(re.findall(r'var\((--svr-[a-z0-9-]+)', css))
for u in sorted(used - declared):
    # --svr-ico задаётся модификаторами .svr-ic-*, --svr-grid-* переопределяются — всё это «объявлено» через ':'
    problems.append('styles.css: var(%s) используется, но нигде не объявлена' % u)
for d in sorted(declared - used):
    notes.append('styles.css: переменная %s объявлена, но не используется' % d)

# ---------- 4. Эвристики ----------
motion_props = ('animation', 'animation-name', 'transition', 'transition-property')
for name, val, imp, sel, ln, ctx in decls:
    in_rm = any('prefers-reduced-motion:no-preference' in c.replace(' ', '') for c in ctx)
    in_print = any(c.startswith('@media print') for c in ctx)
    if name in motion_props and not in_rm and not in_print and val not in ('none', 'none!important'):
        problems.append('CSS строка %s: %s:%s вне @media (prefers-reduced-motion:no-preference) — %s' % (ln, name, val[:40], sel[:60]))
    if name in ('outline', 'outline-style') and val in ('none', '0') and ':focus-visible' in sel:
        notes.append('CSS строка %s: outline:none на %s — убедитесь, что фокус показан иначе (focus-within у карточки)' % (ln, sel[:70]))
    if name == 'scroll-behavior' and val == 'smooth' and not in_rm:
        problems.append('CSS строка %s: scroll-behavior:smooth вне no-preference' % ln)
    if name in ('backdrop-filter', '-webkit-backdrop-filter', 'filter', 'transform', 'contain') and re.search(r'(^|[\s,])\.svr-header(\s*$|[\s,{])', sel) and '::' not in sel:
        problems.append('CSS строка %s: %s на .svr-header создаёт containing block для position:fixed (оверлей меню схлопнется)' % (ln, name))
    if name == 'animation' and 'infinite' in val:
        notes.append('бесконечная анимация: %s { %s }' % (sel[:60], val[:50]))

# Селекторы, которые могут задеть редактор/админку (styles.css грузится и в iframe редактора)
risky = []
for sel, ln, ctx in selectors:
    for part in sel.split(','):
        p = part.strip()
        if re.fullmatch(r'(html|body|\*|:root|::selection|button|input|a|img|svg|h[1-6](\s*,\s*h[1-6])*|p|ul|li|table)(::?[a-z-]+)?', p):
            risky.append('%s (строка %s)' % (p, ln))
if risky:
    notes.append('Глобальные селекторы (действуют и в холсте редактора): ' + '; '.join(risky))
if not any(':focus-visible' in s for s, _, _ in selectors):
    problems.append('styles.css: нет стилей :focus-visible')
if not any('prefers-reduced-motion' in a[1] for a in at_rules if a[0] == 'media'):
    problems.append('styles.css: нет @media (prefers-reduced-motion)')

# ---------- 3. Chromium ----------
from playwright.sync_api import sync_playwright
JS = r'''([sels, decls]) => {
  const badSel = [], badDecl = [];
  for (const [s, ln] of sels) {
    // псевдоэлементы querySelector не принимает — проверяем через CSSStyleSheet
    try { const sh = new CSSStyleSheet(); sh.replaceSync(s + '{}'); if (!sh.cssRules.length) badSel.push([s, ln]); }
    catch (e) { badSel.push([s, ln]); }
  }
  for (const [p, v, ln, sel] of decls) {
    if (/var\(|env\(/.test(v)) continue;
    if (p.startsWith('--')) continue;
    if (!CSS.supports(p, v)) badDecl.push([p, v, ln, sel]);
  }
  return { badSel, badDecl };
}'''
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
                           proxy={'server': 'http://127.0.0.1:9'})
    pg = b.new_page()
    pg.set_content('<!doctype html><html><body></body></html>')
    res = pg.evaluate(JS, [[[s, ln] for s, ln, _ in selectors], [[n, v, ln, s] for n, v, imp, s, ln, _ in decls]])
    # Весь лист целиком: сколько правил принял Chromium
    total = pg.evaluate('''(css) => { const sh = new CSSStyleSheet(); sh.replaceSync(css);
        let n = 0; const cnt = rs => { for (const r of rs) { n++; if (r.cssRules) cnt(r.cssRules); } }; cnt(sh.cssRules); return n; }''', css)
    b.close()
for s, ln in res['badSel']:
    problems.append('Chromium не принял селектор (строка %s): %s' % (ln, s[:120]))
for p, v, ln, sel in res['badDecl']:
    if p.startswith(('-webkit-', '-moz-', '-ms-')):
        notes.append('вендорная декларация (для других движков, Chromium её не знает) строка %s: %s:%s' % (ln, p, v[:60]))
        continue
    problems.append('Chromium не поддерживает декларацию (строка %s): %s:%s  [%s]' % (ln, p, v[:80], sel[:60]))

print('selectors: %d, declarations: %d, at-rules: %d, CSSOM rules in Chromium: %d, CSS bytes: %d' % (
    len(selectors), len(decls), len(at_rules), total, len(css.encode())))
print('\n== PROBLEMS (%d) ==' % len(problems))
for p in problems:
    print(' -', p)
print('\n== NOTES (%d) ==' % len(notes))
for n in notes:
    print(' *', n)
sys.exit(1 if problems else 0)
