"""scrollWidth === innerWidth на всех страницах и ширинах (без опоры на overflow-x:clip: правило отключается)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pwlib import CHROME, LAUNCH, route_site, sync_playwright
PAGES = ['/', '/obj/', '/elteza/', '/russkii/', '/os3-marino/', '/os2-marino/', '/prod/', '/docs/', '/rekvizit/', '/contact/', '/nety-takoy/']
W = [320, 360, 375, 390, 414, 430, 600, 640, 768, 782, 820, 1024, 1199, 1200, 1280, 1440]
bad = 0
with sync_playwright() as p:
    b = p.chromium.launch(**LAUNCH)
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}); route_site(ctx)
    pg = ctx.new_page()
    for path in PAGES:
        pg.goto('https://svr-mos.ru' + path, wait_until='networkidle')
        pg.add_style_tag(content='body{overflow-x:visible!important}')
        res = []
        for w in W:
            pg.set_viewport_size({'width': w, 'height': 900}); pg.wait_for_timeout(120)
            r = pg.evaluate('''() => { const sw = document.documentElement.scrollWidth; if (sw <= innerWidth) return null;
              const el = [...document.querySelectorAll('body *')].filter(e => !e.closest('svg') && e.getBoundingClientRect().right > innerWidth + 1).slice(0,3)
                .map(e => e.tagName + '.' + String(e.className).slice(0,40)); return sw + ' ' + el.join(' ; '); }''')
            if r: res.append(f'{w}:{r}'); bad += 1
        h1 = pg.evaluate("document.querySelectorAll('h1').length")
        print(path, 'h1=' + str(h1), 'OK' if not res else res)
    b.close()
print('overflow cases:', bad)
