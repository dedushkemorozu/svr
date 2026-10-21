"""Screenshots of concepts/premium/home.html. usage: premium_shot.py [outdir] [--extra]"""
import sys
from playwright.sync_api import sync_playwright
S = '/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad'
D = S + '/redesign/concepts/premium'
out = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else D
extra = '--extra' in sys.argv
URL = 'file://' + D + '/home.html'
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    for name, vp in (('desktop', {'width': 1440, 'height': 900}), ('mobile', {'width': 390, 'height': 844})):
        ctx = b.new_context(viewport=vp, reduced_motion='reduce')
        pg = ctx.new_page()
        pg.goto(URL); pg.wait_for_load_state('networkidle')
        # trigger loading="lazy" images (as a real visitor scrolling would)
        h = pg.evaluate('document.documentElement.scrollHeight')
        for y in range(0, h + vp['height'], vp['height'] // 2):
            pg.evaluate(f'window.scrollTo(0,{y})'); pg.wait_for_timeout(60)
        pg.evaluate('window.scrollTo(0,0)')
        pg.wait_for_function('Array.from(document.images).every(i => i.complete)')
        pg.wait_for_timeout(500)
        sw = pg.evaluate('document.documentElement.scrollWidth')
        print(name, 'scrollWidth', sw, 'height', pg.evaluate('document.documentElement.scrollHeight'))
        pg.screenshot(path=f'{out}/{name}.png', full_page=True)
        if extra:
            pg.screenshot(path=f'{out}/{name}-fold.png')
            if name == 'mobile':
                pg.evaluate("document.querySelector('.wp-block-navigation__responsive-container').classList.add('is-menu-open','has-modal-open')")
                pg.wait_for_timeout(200)
                pg.screenshot(path=f'{out}/mobile-menu.png')
        ctx.close()
        if extra:
            from PIL import Image
            im = Image.open(f'{out}/{name}.png')
            step = 1100 if name == 'desktop' else 1400
            n = 0
            for top in range(0, im.height, step):
                im.crop((0, top, im.width, min(im.height, top + step))).save(f'{out}/{name}-s{n}.png'); n += 1
            print(name, 'slices', n)
    b.close()
