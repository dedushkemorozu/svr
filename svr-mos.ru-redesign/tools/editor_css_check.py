"""Редактор WP 7.1.3 (локальный стенд): применяется ли styles.css в холсте и не перекрывают ли растянутые ссылки блоки.
Для страницы 49: ::after у ссылок H3 карточек объектов/листов и ::before у ссылок штампа — display:none в редакторе;
карточки не «застряли» в начальном кадре анимации появления. Запуск: python3 tools/editor_css_check.py"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pwlib import R, LAUNCH, route_site, login, sync_playwright
JS = r'''() => { const f = document.querySelector('iframe[name="editor-canvas"]'); const d = f ? f.contentDocument : document; const w = f ? f.contentWindow : window;
  const pe = (sel, ps) => { const e = d.querySelector(sel); return e ? w.getComputedStyle(e, ps).display : 'нет элемента'; };
  const card = d.querySelector('.svr-obj'); const sheet = d.querySelector('.svr-sheet');
  return { iframe: !!f, bodyClass: d.body.className.slice(0, 80),
    css_loaded: w.getComputedStyle(d.querySelector('.svr-kicker')).textTransform,
    obj_link_after: pe('.svr-obj .wp-block-heading a', '::after'), sheet_link_after: pe('.svr-sheet__name a', '::after'),
    tb_link_before: pe('.svr-tb__v a', '::before'),
    obj_opacity: card && w.getComputedStyle(card).opacity, sheet_anim: sheet && w.getComputedStyle(sheet).animationName,
    hit_on_image: (() => { const im = d.querySelector('.svr-obj__img img'); if (!im) return null; const r = im.getBoundingClientRect();
        const t = d.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return t ? t.tagName + '.' + (t.className || '').toString().slice(0, 40) : null; })() }; }'''
with sync_playwright() as p:
    b = p.chromium.launch(**LAUNCH)
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}); route_site(ctx)
    pg = ctx.new_page(); login(pg)
    pg.goto('https://svr-mos.ru/wp-admin/post.php?post=49&action=edit')
    pg.wait_for_function("window.wp && wp.data && wp.data.select('core/block-editor').getBlocks().length > 0", timeout=90000)
    pg.wait_for_timeout(4000)
    # прокрутить холст до объектов, чтобы elementFromPoint попал в видимую область
    pg.evaluate('''() => { const f = document.querySelector('iframe[name="editor-canvas"]'); const d = f ? f.contentDocument : document;
        const e = d.querySelector('.svr-obj__img'); if (e) e.scrollIntoView({block: 'center'}); }''')
    pg.wait_for_timeout(800)
    print(pg.evaluate(JS))
    b.close()
