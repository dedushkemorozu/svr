"""Screenshots of concepts/deep/home.html: desktop 1440x900 full, mobile 390x844 full, plus extras."""
import sys
from playwright.sync_api import sync_playwright
D = '/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign/concepts/deep'
T = '/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign/tmp/deep'
url = 'file://' + D + '/home.html'
extra = 'extra' in sys.argv
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    for name, w, h in (('desktop', 1440, 900), ('mobile', 390, 844)):
        ctx = b.new_context(viewport={'width': w, 'height': h}, reduced_motion='reduce' if 'rm' in sys.argv else 'no-preference')
        pg = ctx.new_page()
        msgs = []
        pg.on('console', lambda m: msgs.append(m.text))
        pg.on('pageerror', lambda e: msgs.append(str(e)))
        pg.goto(url); pg.wait_for_load_state('networkidle')
        pg.evaluate("async()=>{for(let y=0;y<document.documentElement.scrollHeight;y+=400){window.scrollTo(0,y);await new Promise(r=>setTimeout(r,40));}window.scrollTo(0,0);}")
        pg.wait_for_timeout(900)
        sw = pg.evaluate('document.documentElement.scrollWidth'); ph = pg.evaluate('document.documentElement.scrollHeight')
        print(name, 'scrollWidth', sw, 'height', ph, 'console:', msgs[:5])
        broken = pg.evaluate("[...document.images].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.src.slice(-40))")
        if broken: print('BROKEN IMAGES', broken)
        pg.screenshot(path=f'{D}/{name}.png', full_page=True)
        pg.screenshot(path=f'{T}/{name}-fold.png')
        if extra and name == 'mobile':
            pg.evaluate("document.querySelector('.wp-block-navigation__responsive-container').classList.add('is-menu-open','has-modal-open')")
            pg.wait_for_timeout(300)
            pg.screenshot(path=f'{D}/mobile-menu.png')
        ctx.close()
    b.close()
