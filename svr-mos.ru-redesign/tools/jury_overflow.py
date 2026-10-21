# Find elements overflowing the viewport at narrow widths
from playwright.sync_api import sync_playwright
base = '/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign/concepts'
JS = r'''
() => { const W = document.documentElement.clientWidth; const res = [];
 document.querySelectorAll('body *').forEach(e => { const b = e.getBoundingClientRect();
   if (b.right > W + 0.5 && b.width > 0) { const cs = getComputedStyle(e);
     res.push(e.tagName + '.' + (e.className && e.className.baseVal === undefined ? e.className : '').toString().slice(0,60) + ' right=' + b.right.toFixed(1) + ' w=' + b.width.toFixed(1)); } });
 return {W, sw: document.documentElement.scrollWidth, res: res.slice(0,15)}; }
'''
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    for c in ['deep','blueprint','premium']:
        for w in [320, 360, 375, 414, 768, 1024]:
            pg = b.new_page(viewport={'width':w,'height':800})
            pg.goto(f'file://{base}/{c}/home.html'); pg.wait_for_timeout(500)
            r = pg.evaluate(JS)
            if r['sw'] > r['W']:
                print(c, w, 'scrollWidth', r['sw'], 'client', r['W']); [print('   ', x) for x in r['res']]
            else:
                print(c, w, 'ok')
            pg.close()
    b.close()
