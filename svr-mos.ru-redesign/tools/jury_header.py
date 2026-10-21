# Screenshot headers/first screens at intermediate widths
from playwright.sync_api import sync_playwright
base = '/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign'
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    for c in ['blueprint']:
        for w in [640, 820]:
            pg = b.new_page(viewport={'width':w,'height':900})
            pg.goto(f'file://{base}/concepts/{c}/home.html'); pg.wait_for_timeout(1500)
            pg.screenshot(path=f'{base}/tmp/jury/{c}_w{w}.png')
            pg.close()
    b.close()
