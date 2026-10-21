# Forced-colors (Windows High Contrast) check of gradient/clip text and <mark> accents (jury WP lens)
from playwright.sync_api import sync_playwright
BASE='/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign'
JOBS={'premium':['.svr-steps','.svr-footer__statement'], 'deep':['.svr-steps, .svr-stages'], 'blueprint':['.cta']}
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    for c,sels in JOBS.items():
        ctx=b.new_context(viewport={'width':1440,'height':900}, reduced_motion='reduce', forced_colors='active', color_scheme='dark')
        pg=ctx.new_page(); pg.goto(f'file://{BASE}/concepts/{c}/home.html'); pg.wait_for_timeout(600)
        for i,s in enumerate(sels):
            el=pg.query_selector(s)
            if not el: print(c,'missing',s); continue
            el.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
            bb=el.bounding_box(); bb['y'] += pg.evaluate('window.scrollY')
            pg.screenshot(path=f'{BASE}/tmp/jury-wp/{c}-forced-el{i}.png', clip={'x':0,'y':max(0,bb['y']),'width':1440,'height':min(700,bb['height'])}, full_page=True)
            print(c,s,'ok')
        ctx.close()
    b.close()
