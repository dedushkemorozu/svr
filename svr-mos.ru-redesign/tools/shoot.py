"""Скриншоты и проверки локального стенда.
python3 tools/shoot.py <путь> <ширины через запятую> [--full] [--reduce] [--tag x] [--h 900] [--scroll Y]"""
import sys, json, argparse, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pwlib import R, CHROME, LAUNCH, route_site, sync_playwright
ap = argparse.ArgumentParser()
ap.add_argument('path'); ap.add_argument('widths'); ap.add_argument('--full', action='store_true')
ap.add_argument('--reduce', action='store_true'); ap.add_argument('--tag', default=''); ap.add_argument('--h', type=int, default=900)
ap.add_argument('--scroll', type=int, default=0); ap.add_argument('--clip', default='')
a = ap.parse_args()
out = R / 'tmp/shots'; out.mkdir(parents=True, exist_ok=True)
CHECK = r'''() => {
  const de = document.documentElement;
  const wide = [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width && (r.right > innerWidth + 1); })
     .slice(0, 6).map(e => (e.className && e.className.baseVal === undefined ? e.className : e.tagName) + ' ' + Math.round(e.getBoundingClientRect().right));
  const inf = document.getAnimations().filter(x => x.effect && x.effect.getTiming().iterations === Infinity).length;
  return { sw: de.scrollWidth, iw: innerWidth, h: de.scrollHeight, h1: document.querySelectorAll('h1').length,
           noalt: [...document.images].filter(i => !i.hasAttribute('alt')).length, anim: document.getAnimations().length, inf, wide };
}'''
with sync_playwright() as p:
    b = p.chromium.launch(**LAUNCH)
    for w in [int(x) for x in a.widths.split(',')]:
        ctx = b.new_context(viewport={'width': w, 'height': a.h}, reduced_motion='reduce' if a.reduce else 'no-preference')
        route_site(ctx)
        pg = ctx.new_page()
        pg.goto('https://svr-mos.ru' + a.path, wait_until='networkidle')
        pg.evaluate('document.fonts.ready')
        pg.wait_for_timeout(1800)
        if a.scroll:
            pg.evaluate(f'window.scrollTo(0,{a.scroll})'); pg.wait_for_timeout(600)
        info = pg.evaluate(CHECK)
        print(w, json.dumps(info, ensure_ascii=False))
        name = f"{a.path.strip('/').replace('/', '_') or 'home'}_{w}{a.tag}.png"
        if a.full:
            pg.evaluate('''async () => { for (let y = 0; y < document.documentElement.scrollHeight; y += 450) { scrollTo(0, y); await new Promise(r => setTimeout(r, 160)); } scrollTo(0, 0); }''')
            pg.wait_for_timeout(1200)
            # отключить появление по прокрутке для полного скриншота
            pg.add_style_tag(content='.svr-sheet,.svr-obj,.svr-stage,.svr-card{animation:none!important}')
        pg.screenshot(path=str(out / name), full_page=a.full)
        ctx.close()
    b.close()
