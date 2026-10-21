"""Регрессия на ЛОКАЛЬНОМ стенде WP 7.1.3 после деплоя пакета (php tools/apply_manifest.php): настоящие страницы
https://svr-mos.ru/<slug>/ (маршрут → 127.0.0.1:8090), а не превью.
Проверяет на ширинах 320–1440: горизонтальный скролл (с отключённым overflow-x:clip у html/body), один h1, битые картинки,
alt, апскейл фото (>1 — ошибка), анимации (reduce → 0; no-preference → бесконечных ≤6), крошки страниц объектов,
alt логотипа, мобильное меню (клик → открыто, aria-modal, фокус внутри, Esc → закрыто), lightbox на /prod/.
Запуск: python3 tools/wp_site_check.py [--shots DIR]"""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pwlib import LAUNCH, route_site, sync_playwright

SITE = 'https://svr-mos.ru/'
PAGES = [('49', ''), ('50', 'obj/'), ('51', 'elteza/'), ('52', 'russkii/'), ('53', 'os3-marino/'), ('54', 'os2-marino/'),
         ('55', 'prod/'), ('56', 'docs/'), ('57', 'rekvizit/'), ('58', 'contact/'),
         ('p1', 'prod/stanciya-dozirovaniya/'), ('p2', 'prod/reaktor-trehkamernyj/'), ('p3', 'prod/reaktor-odnokamernyj/'),
         ('p4', 'prod/ustanovka-obezzarazhivaniya/'), ('p5', 'prod/kns/'), ('404', 'net-takoj-stranicy/')]
WIDTHS = [320, 360, 375, 390, 414, 430, 600, 768, 1024, 1280, 1440]
shots = None
if '--shots' in sys.argv:
    shots = pathlib.Path(sys.argv[sys.argv.index('--shots') + 1]); shots.mkdir(parents=True, exist_ok=True)

SCROLL_JS = '''() => { const h = document.documentElement, b = document.body; const s = [h.style.overflowX, b.style.overflowX];
  h.style.overflowX = 'visible'; b.style.overflowX = 'visible'; const r = h.scrollWidth - h.clientWidth;
  h.style.overflowX = s[0]; b.style.overflowX = s[1]; return r; }'''
PAGE_JS = '''() => { const imgs = [...document.images];
  const photo = imgs.filter(i => /\\.jpe?g/i.test(i.currentSrc) && i.naturalWidth && i.closest('.svr-gallery,.svr-obj__img'))
    .map(i => { const r = i.getBoundingClientRect(); const nat = parseInt((i.currentSrc.match(/-(\\d+)x\\d+\\.jpe?g/) || [])[1] || i.naturalWidth);
      return [i.currentSrc.split('/').pop(), Math.round(r.width), nat, +(r.width / nat).toFixed(2)]; });
  return { h1: document.querySelectorAll('h1').length, h1text: [...document.querySelectorAll('h1')].map(e => e.textContent.trim()),
    broken: imgs.filter(i => i.complete && !i.naturalWidth && i.getAttribute('src')).map(i => i.src),
    noalt: imgs.filter(i => !i.hasAttribute('alt')).map(i => i.src),
    upscaled: photo.filter(p => p[3] > 1.01),
    crumbs: [...document.querySelectorAll('.svr-crumbs p')].map(e => e.textContent.trim()).join(' '),
    logoAlt: (document.querySelector('.svr-logo img') || {}).alt,
    status: document.title }; }'''
ANIM_JS = '''() => { const a = document.getAnimations().filter(x => x.playState === 'running');
  return [a.length, a.filter(x => { try { return x.effect.getComputedTiming().iterations === Infinity } catch (e) { return false } }).length]; }'''

bad = []
with sync_playwright() as p:
    b = p.chromium.launch(**LAUNCH)
    res = {}
    for motion in ('reduce', 'no-preference'):
        ctx = b.new_context(viewport={'width': 1440, 'height': 900}, reduced_motion=motion)
        route_site(ctx)
        pg = ctx.new_page()
        for pid, slug in PAGES:
            r = res.setdefault(pid, {'scroll': {}})
            resp = pg.goto(SITE + slug, wait_until='networkidle')
            r['http'] = resp.status
            if motion == 'reduce':
                for w in WIDTHS:
                    pg.set_viewport_size({'width': w, 'height': 900}); pg.wait_for_timeout(150)
                    d = pg.evaluate(SCROLL_JS)
                    if d > 0: r['scroll'][w] = d
                pg.set_viewport_size({'width': 1440, 'height': 900})
                pg.evaluate('window.scrollTo(0, document.body.scrollHeight)'); pg.wait_for_timeout(600)
                pg.evaluate('window.scrollTo(0, 0)'); pg.wait_for_timeout(200)
                r.update(pg.evaluate(PAGE_JS))
                r['anim_reduce'] = pg.evaluate(ANIM_JS)
                if shots and pid in ('49', '50', '51', '55', '58', 'p5'):
                    for w, h in ((1440, 900), (390, 844)):
                        pg.set_viewport_size({'width': w, 'height': h}); pg.wait_for_timeout(300)
                        pg.screenshot(path=str(shots / f'wp-{pid}-{w}.png'))
                    pg.set_viewport_size({'width': 1440, 'height': 900})
            else:
                pg.wait_for_timeout(1500)
                r['anim_motion'] = pg.evaluate(ANIM_JS)
        if motion == 'reduce':
            # мобильное меню (Interactivity API ядра): открыть, проверить, закрыть Esc
            pg.set_viewport_size({'width': 390, 'height': 844}); pg.goto(SITE, wait_until='networkidle')
            btn = pg.locator('.svr-nav .wp-block-navigation__responsive-container-open')
            btn.click(); pg.wait_for_timeout(500)
            opened = pg.evaluate("() => [!!document.querySelector('.svr-nav .is-menu-open'), document.querySelector('.svr-nav .wp-block-navigation__responsive-dialog').getAttribute('aria-modal'), !!(document.activeElement && document.activeElement.closest('.svr-nav .is-menu-open'))]")
            pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
            closed = pg.evaluate("() => !document.querySelector('.svr-nav .is-menu-open')")
            res['menu'] = {'opened': opened, 'closed_by_esc': closed}
            # lightbox на странице продукции (/prod/kns/)
            pg.set_viewport_size({'width': 1440, 'height': 900}); pg.goto(SITE + 'prod/kns/', wait_until='networkidle')
            lb = pg.locator('.svr-sheet__img .lightbox-trigger').first
            n_trig = pg.locator('.svr-sheet__img .lightbox-trigger').count()
            lb.click(force=True); pg.wait_for_timeout(700)
            res['lightbox'] = {'triggers': n_trig, 'overlay_active': pg.evaluate("() => !!document.querySelector('.wp-lightbox-overlay.active')")}
        ctx.close()
    b.close()

for pid, slug in PAGES:
    r = res[pid]
    exp_http = 404 if pid == '404' else 200
    issues = []
    if r['http'] != exp_http: issues.append(f"http {r['http']}")
    if r['scroll']: issues.append(f"scroll {r['scroll']}")
    if r['h1'] != 1: issues.append(f"h1={r['h1']}")
    if r['broken']: issues.append(f"broken {r['broken'][:3]}")
    if r['noalt']: issues.append(f"noalt {r['noalt'][:3]}")
    if r['upscaled']: issues.append(f"upscaled {r['upscaled']}")
    if r['anim_reduce'][0] != 0: issues.append(f"anim(reduce)={r['anim_reduce']}")
    if r['anim_motion'][1] > 8: issues.append(f"infinite={r['anim_motion'][1]}")
    if pid in ('51', '52', '53', '54') and 'Наши объекты' not in r['crumbs']: issues.append('crumbs без «Наши объекты»')
    if pid.startswith('p') and not r['crumbs'].startswith('Главная / Продукция /'): issues.append('crumbs без «Продукция»')
    if r['logoAlt'] != 'ООО «СВР» — на главную': issues.append(f"logo alt={r['logoAlt']!r}")
    if issues: bad.append(pid)
    print(('BAD ' if issues else 'ok  ') + f"{pid:>3} /{slug:<20} http={r['http']} h1={r['h1']} anim reduce={r['anim_reduce'][0]} "
          f"motion={r['anim_motion'][0]} (∞{r['anim_motion'][1]}) crumbs=«{r['crumbs']}» " + '; '.join(issues))
m = res['menu']; l = res['lightbox']
print('menu:', m, '| lightbox:', l)
if not (m['opened'][0] and m['opened'][1] == 'true' and m['opened'][2] and m['closed_by_esc']): bad.append('menu')
if not (l['triggers'] == 1 and l['overlay_active']): bad.append('lightbox')
print('ИТОГ:', 'OK' if not bad else f'проблемы: {bad}')
sys.exit(1 if bad else 0)
