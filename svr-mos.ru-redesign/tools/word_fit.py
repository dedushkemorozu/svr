"""Проверка: ни одно слово в заголовках/названиях не шире своего блока (иначе break-word рвёт его посреди).
python3 tools/word_fit.py <page.html превью> [ширины через запятую] [селектор]"""
import sys, os
from playwright.sync_api import sync_playwright
f = sys.argv[1]; widths = [int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else '320,360,375,390,414,600,768,800,1024,1280,1440').split(',')]
sel = sys.argv[3] if len(sys.argv) > 3 else 'h1,h2,h3,.svr-sheet__name,.svr-tb__v,.svr-chips li,.svr-works li,.svr-matrix th,td,.svr-lead,.svr-label,p'
JS = '''(sel) => { const out = []; const m = document.createElement('span'); m.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;left:-9999px;top:0'; document.body.appendChild(m);
  for (const el of document.querySelectorAll(sel)) { if (!el.offsetParent && getComputedStyle(el).position !== 'fixed') continue;
    const cs = getComputedStyle(el); const w = el.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight); if (w <= 0) continue;
    m.style.font = cs.font; m.style.letterSpacing = cs.letterSpacing; m.style.textTransform = cs.textTransform; m.style.fontVariant = cs.fontVariant;
    for (const word of (el.innerText || '').split(/[\\s]+/)) { if (word.length < 4) continue; m.textContent = word; const ww = m.getBoundingClientRect().width;
      if (ww > w + 0.5) out.push([el.tagName + '.' + (el.className || '').toString().split(' ')[0], word, Math.round(ww), Math.round(w)]); } }
  m.remove(); return out; }'''
bad = 0
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome', proxy={'server': 'http://127.0.0.1:9'})
    for w in widths:
        pg = b.new_page(viewport={'width': w, 'height': 900}, reduced_motion='reduce')
        pg.goto('file://' + os.path.abspath(f)); pg.wait_for_timeout(500)
        r = pg.evaluate(JS, sel)
        if r: bad += len(r); print(w, r[:8])
        pg.close()
    b.close()
print('word-fit:', 'OK' if not bad else f'{bad} слов шире блока')
