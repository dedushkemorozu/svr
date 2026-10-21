"""Шаблоны и части шаблона в Site Editor WP 7.1.3: нет невалидных блоков."""
import sys, pathlib, urllib.parse
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pwlib import R, CHROME, LAUNCH, route_site, login, sync_playwright
items = [('wp_template', 'page'), ('wp_template', 'page-no-title'), ('wp_template', '404'), ('wp_template_part', 'header'), ('wp_template_part', 'footer')]
with sync_playwright() as p:
    b = p.chromium.launch(**LAUNCH)
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}); route_site(ctx)
    pg = ctx.new_page(); login(pg)
    for kind, slug in items:
        path = urllib.parse.quote(f'/{kind}/twentytwentyfive//{slug}', safe='')
        pg.goto(f'https://svr-mos.ru/wp-admin/site-editor.php?p={path}&canvas=edit')
        try:
            pg.wait_for_function("window.wp && wp.data && wp.data.select('core/block-editor') && wp.data.select('core/block-editor').getBlocks().length > 0", timeout=90000)
        except Exception as e:
            print(kind, slug, 'timeout'); continue
        pg.wait_for_timeout(4000)
        r = pg.evaluate('''() => { const all = []; const walk = bs => bs.forEach(b => { all.push(b); walk(b.innerBlocks); });
          const sel = wp.data.select('core/block-editor'); walk(sel.getBlocks());
          const ids = all.map(b => b.clientId); const ctrl = all.filter(b => sel.getBlocks(b.clientId).length && !b.innerBlocks.length);
          const frame = document.querySelector('iframe[name="editor-canvas"]'); const doc = frame ? frame.contentDocument : document;
          return { blocks: all.length, invalid: all.filter(b => !b.isValid).map(b => b.name), warnings: doc ? doc.querySelectorAll('.block-editor-warning').length : -1 }; }''')
        print(kind, slug, r)
        if slug in ('page', 'header'):
            pg.screenshot(path=str(R / f'tmp/shots/site_editor_{slug}.png'))
    b.close()
