import sys
from playwright.sync_api import sync_playwright
src, out, w, h = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
full = len(sys.argv) > 5 and sys.argv[5] == 'full'
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    pg = b.new_page(viewport={'width': w, 'height': h})
    pg.goto('file://' + src); pg.wait_for_timeout(400)
    pg.screenshot(path=out, full_page=full)
    b.close()
