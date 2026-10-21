"""Check overflow + capture fold/full at extra widths."""
from playwright.sync_api import sync_playwright
S='/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign'
URL='file://'+S+'/concepts/premium/home.html'
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    for w,h in ((360,740),(430,932),(820,1180),(1024,768),(1280,800),(1920,1080)):
        pg=b.new_page(viewport={'width':w,'height':h}, reduced_motion='reduce')
        pg.goto(URL); pg.wait_for_load_state('networkidle')
        H=pg.evaluate('document.documentElement.scrollHeight')
        for y in range(0,H+h,h//2): pg.evaluate(f'window.scrollTo(0,{y})'); pg.wait_for_timeout(40)
        pg.evaluate('window.scrollTo(0,0)'); pg.wait_for_timeout(300)
        # find elements overflowing viewport
        over=pg.evaluate("""()=>{const W=document.documentElement.clientWidth;const r=[];document.querySelectorAll('body *').forEach(e=>{const b=e.getBoundingClientRect();if(b.right>W+1&&b.width>0&&!e.closest('.svr-flow')&&!e.closest('.wp-block-navigation__responsive-container'))r.push(e.className.toString().slice(0,40)+' '+Math.round(b.right))});return r.slice(0,8)}""")
        print(w,'scrollW',pg.evaluate('document.documentElement.scrollWidth'),'H',H,over)
        pg.screenshot(path=f'{S}/tmp/premium/w{w}.png', full_page=True)
        pg.close()
    b.close()
