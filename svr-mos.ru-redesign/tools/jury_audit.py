# Jury audit: headings, alt, min font sizes, overflow, reduced motion, tap targets
import json, sys
from playwright.sync_api import sync_playwright
base = '/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign/concepts'
JS = r'''
() => {
  const r = {};
  r.h = [...document.querySelectorAll('h1,h2,h3,h4')].map(e => e.tagName + ':' + e.textContent.trim().replace(/\s+/g,' ').slice(0,60));
  r.imgNoAlt = [...document.querySelectorAll('img')].filter(i => !i.hasAttribute('alt')).length;
  r.imgs = document.querySelectorAll('img').length;
  r.scrollW = document.documentElement.scrollWidth;
  r.innerW = window.innerWidth;
  // min font size among visible text nodes
  const sizes = {};
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n; const small = [];
  while ((n = walker.nextNode())) {
    const t = n.textContent.trim(); if (!t) continue;
    const el = n.parentElement; if (!el) continue;
    if (el.closest('[aria-hidden="true"]')) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
    const rect = el.getBoundingClientRect(); if (rect.width === 0) continue;
    const fs = parseFloat(cs.fontSize);
    sizes[fs] = (sizes[fs]||0) + 1;
    if (fs < 12.5) small.push(fs + 'px ' + cs.fontFamily.split(',')[0] + ' | ' + t.slice(0,40));
  }
  r.sizes = sizes; r.small = small.slice(0,25); r.smallCount = small.length;
  // tap targets
  const tiny = [];
  document.querySelectorAll('a,button').forEach(a => {
    const b = a.getBoundingClientRect(); const cs = getComputedStyle(a);
    if (b.width === 0 || cs.display==='none' || cs.visibility==='hidden') return;
    if (b.height < 40 && !a.closest('p,li,td')) tiny.push(Math.round(b.width)+'x'+Math.round(b.height)+' '+(a.textContent.trim()||a.getAttribute('aria-label')||'').slice(0,30));
  });
  r.tinyTargets = tiny.slice(0,15);
  r.reducedMotionRules = [...document.styleSheets].flatMap(s => { try { return [...s.cssRules] } catch(e) { return [] } }).filter(x => x.media && /reduced-motion/.test(x.media.mediaText)).length;
  r.text = document.body.innerText;
  return r;
}
'''
out = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    for c in ['deep','blueprint','premium']:
        for w,h in [(360,780),(1440,900)]:
            pg = b.new_page(viewport={'width':w,'height':h})
            pg.goto(f'file://{base}/{c}/home.html'); pg.wait_for_timeout(800)
            r = pg.evaluate(JS)
            txt = r.pop('text')
            if w == 1440:
                open(f'/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign/tmp/jury/{c}_text.txt','w').write(txt)
            out[f'{c}@{w}'] = r
            pg.close()
    b.close()
for k,v in out.items():
    print('=====', k)
    print('scrollW', v['scrollW'], 'innerW', v['innerW'], 'imgs', v['imgs'], 'noalt', v['imgNoAlt'], 'RM rules', v['reducedMotionRules'])
    if k.endswith('1440'):
        print('headings:'); [print('  ', x) for x in v['h']]
    print('font sizes:', dict(sorted(((float(a),b) for a,b in v['sizes'].items()))))
    print('small(<12.5) count', v['smallCount']); [print('   ', s) for s in v['small'][:12]]
    print('tiny targets:', v['tinyTargets'][:10])
