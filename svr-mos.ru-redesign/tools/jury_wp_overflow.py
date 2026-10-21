# Find elements overflowing the viewport at given widths (jury WP lens)
import sys
from playwright.sync_api import sync_playwright
BASE='/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign'
c=sys.argv[1]; widths=[int(x) for x in sys.argv[2:]]
JS=r'''(W)=>{const out=[];document.querySelectorAll('body *').forEach(e=>{const r=e.getBoundingClientRect();if(r.width&&r.right>W+1){let p=e.parentElement,clipped=false;while(p&&p!==document.body){const cs=getComputedStyle(p);if(/hidden|clip/.test(cs.overflowX)){const pr=p.getBoundingClientRect(); if(pr.right<=W+1){clipped=true;break;}}p=p.parentElement;}if(!clipped)out.push((e.tagName+'.'+(typeof e.className==='string'?e.className:'')).slice(0,60)+' right='+Math.round(r.right)+' w='+Math.round(r.width));}});
const cs=getComputedStyle(document.body), hs=getComputedStyle(document.documentElement);
return {bodyOverflowX:cs.overflowX, htmlOverflowX:hs.overflowX, list:out.slice(0,12)}}'''
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    for w in widths:
        pg=b.new_page(viewport={'width':w,'height':900}, reduced_motion='reduce'); pg.goto(f'file://{BASE}/concepts/{c}/home.html'); pg.wait_for_timeout(500)
        print(w, pg.evaluate(JS, w)); pg.close()
    b.close()
