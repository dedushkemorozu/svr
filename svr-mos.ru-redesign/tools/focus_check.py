"""Проверка видимости фокуса с клавиатуры на собранной странице превью: проходит Tab по всем элементам
и для каждого считает «индикатор» — свой outline или outline/рамку предка через :focus-within.
Запуск: python3 tools/focus_check.py tmp/audit/r4/home.html [ширина]"""
import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from playwright.sync_api import sync_playwright
from preview import PREP_JS, CHROME
html = sys.argv[1]; w = int(sys.argv[2]) if len(sys.argv) > 2 else 1440
JS = r'''() => { const el = document.activeElement; if (!el || el === document.body) return null;
  const cs = getComputedStyle(el); const own = cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0;
  let anc = null; for (let a = el.parentElement; a && a !== document.body; a = a.parentElement) { const s = getComputedStyle(a);
    if (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0) { anc = a.className.toString().split(' ').filter(c => c.startsWith('svr-'))[0] || a.tagName; break; } }
  const r = el.getBoundingClientRect();
  return {tag: el.tagName, text: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 40), own, ownColor: own ? cs.outlineColor : null, anc,
          visible: r.width > 0 && r.height > 0, fv: el.matches(':focus-visible')}; }'''
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, proxy={'server': 'http://127.0.0.1:9'})
    pg = b.new_page(viewport={'width': w, 'height': 900}, reduced_motion='reduce')
    pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith(('file:', 'data:')) else r.abort())
    pg.goto(pathlib.Path(html).resolve().as_uri()); pg.evaluate(PREP_JS)
    seen, bad, n = set(), [], 0
    for i in range(400):
        pg.keyboard.press('Tab')
        r = pg.evaluate(JS)
        if not r:
            continue
        key = json.dumps(r, ensure_ascii=False)
        n += 1
        if r['visible'] and not r['own'] and not r['anc']:
            bad.append(r)
        if i > 5 and pg.evaluate('document.activeElement === document.querySelector("a,button")'):
            break
    print('проверено фокусов:', n, 'без видимого индикатора:', len(bad))
    for x in bad[:20]:
        print('  ', x)
    b.close()
