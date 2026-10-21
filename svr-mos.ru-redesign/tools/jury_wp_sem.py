# Semantics/tap-target/min-font quick check at 390px (jury WP lens)
from playwright.sync_api import sync_playwright
BASE='/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign'
JS=r'''()=>{
 const vis=e=>{const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return r.width>0&&r.height>0&&cs.visibility!=='hidden'&&cs.display!=='none'};
 const h=[...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].filter(vis).map(e=>e.tagName);
 const cnt={}; h.forEach(t=>cnt[t]=(cnt[t]||0)+1);
 // heading level skips
 let skips=0; let prev=0; [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].forEach(e=>{const l=+e.tagName[1]; if(prev && l>prev+1) skips++; prev=l;});
 const lm={main:document.querySelectorAll('main').length, nav:document.querySelectorAll('nav').length, header:document.querySelectorAll('header').length, footer:document.querySelectorAll('footer').length};
 const tiny=[];document.querySelectorAll('a,button').forEach(a=>{if(!vis(a))return;const b=a.getBoundingClientRect();if((b.height<44||b.width<44)&&!a.closest('p,li,td,dd')) tiny.push(Math.round(b.width)+'x'+Math.round(b.height)+' '+(a.textContent.trim()||a.getAttribute('aria-label')||'').slice(0,26));});
 let small=0, smallMono=0; const tw=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT); let n; const seen=new Set();
 while((n=tw.nextNode())){const el=n.parentElement; if(!n.textContent.trim()||!el||seen.has(el)) continue; seen.add(el); if(el.closest('[aria-hidden="true"]')||!vis(el)) continue; const cs=getComputedStyle(el); const fs=parseFloat(cs.fontSize); if(fs>0&&fs<13){small++; if(/Fira/.test(cs.fontFamily)) smallMono++;}}
 const links=[...document.querySelectorAll('a')].filter(vis).length;
 const dupTel=[...document.querySelectorAll('a[href^="tel:"]')].length;
 return {h:cnt, skips, lm, tinyCount:tiny.length, tiny:tiny.slice(0,8), small, smallMono, links, dupTel};
}'''
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    for c in ['deep','blueprint','premium']:
        pg=b.new_page(viewport={'width':390,'height':844}, reduced_motion='reduce'); pg.goto(f'file://{BASE}/concepts/{c}/home.html'); pg.wait_for_timeout(500)
        print(c, pg.evaluate(JS)); pg.close()
    b.close()
