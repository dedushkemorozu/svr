"""Проверка мобильного меню: открытие, aria-expanded, фокус внутри, Esc, скриншот. python3 tools/menu_test.py 390,768"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pwlib import R, CHROME, LAUNCH, route_site, sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(**LAUNCH)
    for w in [int(x) for x in sys.argv[1].split(',')]:
        ctx = b.new_context(viewport={'width': w, 'height': 820})
        route_site(ctx)
        pg = ctx.new_page()
        pg.goto('https://svr-mos.ru/obj/', wait_until='networkidle')
        btn = pg.locator('.svr-nav .wp-block-navigation__responsive-container-open')
        vis = btn.is_visible()
        btn.click(); pg.wait_for_timeout(600)
        st = pg.evaluate('''() => { const c = document.querySelector('.svr-nav .wp-block-navigation__responsive-container');
          const r = c.getBoundingClientRect(); return { open: c.classList.contains('is-menu-open'), h: Math.round(r.height), w: Math.round(r.width),
          expanded: document.querySelector('.svr-nav .wp-block-navigation__responsive-container-open').getAttribute('aria-expanded'),
          focus: document.activeElement && (document.activeElement.className || document.activeElement.tagName), modal: c.getAttribute('aria-modal') || c.querySelector('[aria-modal]')?.getAttribute('aria-modal') }; }''')
        pg.screenshot(path=str(R / f'tmp/shots/menu_{w}.png'))
        for _ in range(12): pg.keyboard.press('Tab')
        inside = pg.evaluate("!!document.activeElement.closest('.wp-block-navigation__responsive-container')")
        pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
        closed = pg.evaluate("!document.querySelector('.svr-nav .wp-block-navigation__responsive-container').classList.contains('is-menu-open')")
        print(w, 'burger visible:', vis, st, 'focus trapped after 12 tabs:', inside, 'closed by Esc:', closed)
        ctx.close()
    b.close()
