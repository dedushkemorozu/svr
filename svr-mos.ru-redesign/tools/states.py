"""Скриншоты состояний focus-visible/hover ключевых компонентов (1440)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pwlib import R, CHROME, LAUNCH, route_site, sync_playwright
from PIL import Image
CASES = [('focus', '.svr-sheet__name a'), ('focus', '.svr-obj h3 a'), ('focus', '.svr-tb__v a'), ('focus', '.svr-hero .wp-block-button__link'),
         ('focus', '.svr-nav .wp-block-navigation-item__content'), ('hover', '.svr-sheet:nth-child(2)'), ('hover', '.svr-obj:nth-child(2)'),
         ('focus', '.svr-btn--ghost .wp-block-button__link'), ('hover', '.svr-head .svr-btn--ghost .wp-block-button__link'), ('focus', '.svr-phone a')]
with sync_playwright() as p:
    b = p.chromium.launch(**LAUNCH)
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}, reduced_motion='reduce'); route_site(ctx)
    pg = ctx.new_page(); pg.goto('https://svr-mos.ru/', wait_until='networkidle')
    tiles = []
    for k, (kind, sel) in enumerate(CASES):
        el = pg.locator(sel).first
        el.scroll_into_view_if_needed(); pg.wait_for_timeout(200)
        if kind == 'focus':
            pg.mouse.move(0, 0); el.focus()
        else:
            el.hover()
        pg.wait_for_timeout(450)
        box = el.evaluate("e => { const c = e.closest('.svr-sheet,.svr-obj,.svr-tb,.wp-block-buttons,.svr-nav,.svr-contacts__cell') || e; const r = c.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }")
        x, y, w, h = box; pad = 20
        clip = {'x': max(0, x - pad), 'y': max(0, y - pad), 'width': min(1440, w + 2 * pad), 'height': min(900, h + 2 * pad)}
        f = R / f'tmp/shots/state_{k}.png'; pg.screenshot(path=str(f), clip=clip); tiles.append(f)
        pg.evaluate('document.activeElement && document.activeElement.blur()')
    ims = [Image.open(t) for t in tiles]
    W = max(i.width for i in ims); H = sum(i.height + 10 for i in ims)
    sheet = Image.new('RGB', (W, H), (40, 0, 0)); y = 0
    for i in ims: sheet.paste(i, (0, y)); y += i.height + 10
    sheet.save(R / 'tmp/shots/states.png'); print(sheet.size)
    b.close()
