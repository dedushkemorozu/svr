"""Открыть страницы в настоящем редакторе WP 7.1.3 и проверить: нет предупреждений «недопустимое содержимое», все блоки isValid."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pwlib import R, CHROME, LAUNCH, route_site, login, sync_playwright
ids = [int(x) for x in sys.argv[1:]] or [49, 50, 51, 55, 56, 57, 58]
with sync_playwright() as p:
    b = p.chromium.launch(**LAUNCH)
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}); route_site(ctx)
    pg = ctx.new_page(); login(pg)
    for i in ids:
        pg.goto(f'https://svr-mos.ru/wp-admin/post.php?post={i}&action=edit')
        pg.wait_for_function("window.wp && wp.data && wp.data.select('core/block-editor').getBlocks().length > 0", timeout=90000)
        pg.wait_for_timeout(2500)
        r = pg.evaluate('''() => { const all = []; const walk = bs => bs.forEach(b => { all.push(b); walk(b.innerBlocks); });
          walk(wp.data.select('core/block-editor').getBlocks());
          const frame = document.querySelector('iframe[name="editor-canvas"]'); const doc = frame ? frame.contentDocument : document;
          return { blocks: all.length, invalid: all.filter(b => !b.isValid).map(b => b.name),
                   warnings: doc.querySelectorAll('.block-editor-warning').length,
                   dirty: wp.data.select('core/editor').isEditedPostDirty() }; }''')
        print(i, r)
    b.close()
