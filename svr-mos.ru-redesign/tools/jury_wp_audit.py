# Jury (WP tech lead / a11y / perf lens) audit of concept mockups.
# Checks: running animations (normal vs reduced motion), paint activity over time,
# image upscaling of low-res photos, overflow at intermediate widths, focus outline,
# computed-colour contrast against nearest solid background, forced-colors rendering.
import json, sys, os, re
from playwright.sync_api import sync_playwright

BASE = '/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign'
OUT = BASE + '/tmp/jury-wp'
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
CONCEPTS = sys.argv[1:] or ['deep', 'blueprint', 'premium']

ANIM_JS = r'''() => {
  const a = document.getAnimations();
  const running = a.filter(x => x.playState === 'running');
  const inf = running.filter(x => { try { return x.effect.getComputedTiming().iterations === Infinity } catch(e) { return false } });
  const names = {};
  running.forEach(x => { const n = x.animationName || x.constructor.name; names[n] = (names[n]||0)+1; });
  const trans = a.filter(x => x.constructor.name === 'CSSTransition').length;
  // targets inside inline SVG (not compositor-friendly in many engines)
  const svgT = running.filter(x => x.effect && x.effect.target && x.effect.target instanceof SVGElement && !(x.effect.target instanceof SVGSVGElement)).length;
  return {total: a.length, running: running.length, infinite: inf.length, svgChildTargets: svgT, names};
}'''

IMG_JS = r'''() => [...document.images].map(i => {
  const r = i.getBoundingClientRect();
  const cs = getComputedStyle(i);
  return {src: i.currentSrc.split('/').pop().slice(0,40), nw: i.naturalWidth, nh: i.naturalHeight,
          w: Math.round(r.width), h: Math.round(r.height), fit: cs.objectFit,
          scale: i.naturalWidth ? +(r.width / i.naturalWidth).toFixed(2) : 0,
          scaleH: i.naturalHeight ? +(r.height / i.naturalHeight).toFixed(2) : 0,
          alt: i.getAttribute('alt')};
})'''

CONTRAST_JS = r'''() => {
  function parse(c){ const m = c.match(/rgba?\(([^)]+)\)/); if(!m) return null; const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return {r:p[0],g:p[1],b:p[2],a: p.length>3?p[3]:1}; }
  function lum(c){ const f = v => { v/=255; return v<=0.03928? v/12.92 : Math.pow((v+0.055)/1.055,2.4) }; return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b); }
  function blend(top, bot){ const a = top.a; return {r: top.r*a+bot.r*(1-a), g: top.g*a+bot.g*(1-a), b: top.b*a+bot.b*(1-a), a:1}; }
  function bgOf(el){
    const stack = []; let e = el; let gradient = false;
    while (e && e.nodeType === 1) {
      const cs = getComputedStyle(e);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') gradient = true;
      const c = parse(cs.backgroundColor);
      if (c && c.a > 0) { stack.push(c); if (c.a >= 1) break; }
      e = e.parentElement;
    }
    let base = {r:255,g:255,b:255,a:1};
    if (stack.length && stack[stack.length-1].a >= 1) base = stack.pop();
    else { const bc = parse(getComputedStyle(document.body).backgroundColor); if (bc && bc.a) base = bc; }
    for (let i = stack.length-1; i>=0; i--) base = blend(stack[i], base);
    return {bg: base, gradient};
  }
  const res = []; const seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())) {
    const t = n.textContent.trim(); if (!t) continue;
    const el = n.parentElement; if (!el || seen.has(el)) continue; seen.add(el);
    if (el.closest('[aria-hidden="true"],svg,script,style')) continue;
    const cs = getComputedStyle(el);
    if (cs.display==='none'||cs.visibility==='hidden') continue;
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
    if (el.closest('.wp-block-navigation__responsive-container') && !el.closest('.is-menu-open') && r.width===0) continue;
    let fg = parse(cs.webkitTextFillColor && cs.webkitTextFillColor !== cs.color && !/0\)$/.test(cs.webkitTextFillColor) ? cs.webkitTextFillColor : cs.color);
    const clipText = cs.webkitBackgroundClip === 'text' || cs.backgroundClip === 'text';
    if (!fg) continue;
    let op = 1; let x = el; while (x && x.nodeType===1){ op *= +getComputedStyle(x).opacity; x = x.parentElement; }
    const {bg, gradient} = bgOf(el);
    const f2 = fg.a < 1 ? blend(fg, bg) : fg;
    const fin = op < 1 ? blend({...f2, a: op}, bg) : f2;
    const L1 = lum(fin), L2 = lum(bg);
    const ratio = (Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05);
    const fs = parseFloat(cs.fontSize), fw = +cs.fontWeight;
    const large = fs >= 24 || (fs >= 18.66 && fw >= 700);
    if (ratio < (large ? 3 : 4.5) || clipText) res.push({t: t.slice(0,46), ratio: +ratio.toFixed(2), fs, fw, large, clipText, gradientBehind: gradient,
      fg: cs.color, bg: `rgb(${bg.r|0},${bg.g|0},${bg.b|0})`, op: +op.toFixed(2), cls: (el.className && el.className.baseVal===undefined ? el.className : '').toString().slice(0,40)});
  }
  return res;
}'''

FOCUS_JS = r'''() => { const e = document.activeElement; if (!e) return null; const cs = getComputedStyle(e);
  const r = e.getBoundingClientRect();
  return {tag: e.tagName, txt: (e.textContent||e.getAttribute('aria-label')||'').trim().slice(0,30), outline: cs.outlineStyle+' '+cs.outlineWidth+' '+cs.outlineColor, offset: cs.outlineOffset, shadow: cs.boxShadow.slice(0,40), w: Math.round(r.width), h: Math.round(r.height), visible: r.width>0 && r.height>0}; }'''

HEADER_JS = r'''() => {
  const sw = document.documentElement.scrollWidth;
  const hdr = document.querySelector('header') ;
  const hr = hdr ? hdr.getBoundingClientRect() : null;
  const nav = [...document.querySelectorAll('.wp-block-navigation-item__content, nav a')].filter(a => { const r = a.getBoundingClientRect(); const cs = getComputedStyle(a); return r.width>0 && r.height>0 && cs.visibility!=='hidden' && r.top < 140; });
  const tops = [...new Set(nav.map(a => Math.round(a.getBoundingClientRect().top)))];
  const burger = [...document.querySelectorAll('.wp-block-navigation__responsive-container-open, button[aria-label*="еню"], .burger, .hdr__burger')].filter(b => b.getBoundingClientRect().width>0).length;
  return {scrollW: sw, headerH: hr ? Math.round(hr.height) : null, visibleNavLinksTop: nav.length, navRows: tops.length, burger};
}'''


def paint_count(page, ms=3000):
    """Count Paint / composite events via CDP tracing for `ms` milliseconds."""
    cdp = page.context.new_cdp_session(page)
    events = []
    cdp.on('Tracing.dataCollected', lambda p: events.extend(p['value']))
    done = {'v': False}
    cdp.on('Tracing.tracingComplete', lambda p: done.__setitem__('v', True))
    cdp.send('Tracing.start', {'categories': 'devtools.timeline,disabled-by-default-devtools.timeline', 'transferMode': 'ReportEvents'})
    page.wait_for_timeout(ms)
    cdp.send('Tracing.end')
    for _ in range(100):
        if done['v']:
            break
        page.wait_for_timeout(100)
    names = {}
    dur = {}
    for e in events:
        n = e.get('name')
        if n in ('Paint', 'PaintImage', 'Layout', 'UpdateLayoutTree', 'RasterTask', 'CompositeLayers', 'PrePaint', 'Layerize'):
            names[n] = names.get(n, 0) + 1
            dur[n] = dur.get(n, 0) + e.get('dur', 0) / 1000.0
    return {k: (names[k], round(dur.get(k, 0), 1)) for k in sorted(names)}


def main():
    report = {}
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME)
        for c in CONCEPTS:
            url = f'file://{BASE}/concepts/{c}/home.html'
            R = report[c] = {}
            # 1. animations normal vs reduced, paint activity at top (desktop + mobile)
            for label, vp in [('desktop', (1440, 900)), ('mobile', (390, 844))]:
                for rm in ['no-preference', 'reduce']:
                    ctx = b.new_context(viewport={'width': vp[0], 'height': vp[1]}, reduced_motion=rm)
                    pg = ctx.new_page()
                    pg.goto(url)
                    pg.wait_for_timeout(2500)
                    R[f'anim_{label}_{rm}'] = pg.evaluate(ANIM_JS)
                    R[f'paint_{label}_{rm}'] = paint_count(pg, 3000)
                    if rm == 'no-preference' and label == 'desktop':
                        # scroll through to load lazy images, then measure image scaling
                        h = pg.evaluate('document.documentElement.scrollHeight')
                        for y in range(0, h, 700):
                            pg.evaluate(f'window.scrollTo(0,{y})'); pg.wait_for_timeout(60)
                        pg.wait_for_timeout(500)
                        R['img_desktop'] = pg.evaluate(IMG_JS)
                        pg.evaluate('window.scrollTo(0,0)'); pg.wait_for_timeout(300)
                        R['contrast_desktop'] = pg.evaluate(CONTRAST_JS)
                        # focus sequence
                        foc = []
                        for i in range(9):
                            pg.keyboard.press('Tab'); pg.wait_for_timeout(80)
                            foc.append(pg.evaluate(FOCUS_JS))
                        R['focus'] = foc
                    if rm == 'no-preference' and label == 'mobile':
                        h = pg.evaluate('document.documentElement.scrollHeight')
                        for y in range(0, h, 700):
                            pg.evaluate(f'window.scrollTo(0,{y})'); pg.wait_for_timeout(50)
                        pg.wait_for_timeout(400)
                        R['img_mobile'] = pg.evaluate(IMG_JS)
                        pg.evaluate('window.scrollTo(0,0)'); pg.wait_for_timeout(300)
                        R['contrast_mobile'] = pg.evaluate(CONTRAST_JS)
                    ctx.close()
            # 2. intermediate widths: overflow + header behaviour
            R['widths'] = {}
            for w in [320, 360, 600, 640, 700, 782, 820, 900, 1024, 1100, 1180, 1280]:
                ctx = b.new_context(viewport={'width': w, 'height': 900}, reduced_motion='reduce')
                pg = ctx.new_page(); pg.goto(url); pg.wait_for_timeout(500)
                R['widths'][w] = pg.evaluate(HEADER_JS)
                if w in (640, 820, 1100):
                    pg.screenshot(path=f'{OUT}/{c}-w{w}-top.png', clip={'x': 0, 'y': 0, 'width': w, 'height': 260})
                ctx.close()
            # 3. forced colors (Windows High Contrast) hero render
            for label, vp in [('desktop', (1440, 900)), ('mobile', (390, 844))]:
                ctx = b.new_context(viewport={'width': vp[0], 'height': vp[1]}, reduced_motion='reduce', forced_colors='active', color_scheme='dark')
                pg = ctx.new_page(); pg.goto(url); pg.wait_for_timeout(800)
                pg.screenshot(path=f'{OUT}/{c}-forced-{label}.png')
                ctx.close()
            # 4. reduced motion screenshot of hero (to see final states are visible)
            ctx = b.new_context(viewport={'width': 1440, 'height': 900}, reduced_motion='reduce')
            pg = ctx.new_page(); pg.goto(url); pg.wait_for_timeout(300)
            pg.screenshot(path=f'{OUT}/{c}-rm-desktop.png')
            ctx.close()
        b.close()
    with open(f'{OUT}/audit.json', 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print('ok')


if __name__ == '__main__':
    main()
