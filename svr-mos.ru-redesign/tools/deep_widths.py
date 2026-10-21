from playwright.sync_api import sync_playwright
D='/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign'
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    for w in (360,414,600,820,1024,1280,1920):
        pg=b.new_page(viewport={'width':w,'height':900})
        pg.goto('file://'+D+'/concepts/deep/home.html'); pg.wait_for_timeout(300)
        sw=pg.evaluate('document.documentElement.scrollWidth')
        wide=pg.evaluate("""[...document.querySelectorAll('body *')].filter(e=>{const r=e.getBoundingClientRect();return r.right>innerWidth+1 && !e.closest('.svr-current,.svr-hero__fx,.svr-wave__fx,.svr-contact__fx,.wp-block-navigation__responsive-container,.svr-prod-cta,svg')}).slice(0,5).map(e=>e.className.baseVal??e.className)""")
        print(w, sw, wide)
        if w in (820,1024): pg.screenshot(path=f'{D}/tmp/deep/w{w}.png', full_page=False)
        pg.close()
    b.close()
