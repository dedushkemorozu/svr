"""Валидация блочной разметки настоящим редактором WordPress 7.1.3 (локальный стенд).
Для каждого файла: wp.blocks.parse → проверка isValid у всех блоков (рекурсивно) → wp.blocks.serialize.
Каноническая сериализация сохраняется в tmp/canon/<имя> (или в --out DIR).
Запуск: python3 tools/validate_blocks.py [--out DIR] [--strict] [файлы…]
--strict: ошибка и при «normalized» (редактор пересохранил бы файл иначе) — так проверяется пакет deploy/."""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pwlib import R, CHROME, LAUNCH, route_site, login, sync_playwright

args = sys.argv[1:]
out_dir = R / 'tmp/canon'
strict = '--strict' in args
args = [a for a in args if a != '--strict']
if '--out' in args:
    i = args.index('--out'); out_dir = pathlib.Path(args[i + 1]); del args[i:i + 2]
files = [pathlib.Path(x) for x in args] or (
    [R / 'system' / n for n in ('header.html', 'footer.html', 'page.html', 'page-no-title.html', '404.html')] +
    sorted((R / 'tmp/pages').glob('*.html')))
out_dir.mkdir(parents=True, exist_ok=True)
JS = r'''(src) => {
  const blocks = wp.blocks.parse(src);
  const issues = [];
  const walk = (bs, path) => bs.forEach((b, i) => {
    const here = path + '/' + b.name + '[' + i + ']';
    if (!b.isValid || ['core/freeform', 'core/missing'].includes(b.name)) {
      issues.push({ path: here, issues: (b.validationIssues || []).map(x => (x.args || []).map(a => typeof a === 'string' ? a : JSON.stringify(a)).join(' | ').slice(0, 600)).slice(0, 4) });
    }
    walk(b.innerBlocks || [], here);
  });
  walk(blocks, '');
  let count = 0; const cnt = bs => bs.forEach(b => { count++; cnt(b.innerBlocks || []); }); cnt(blocks);
  return { issues, count, out: wp.blocks.serialize(blocks) };
}'''
with sync_playwright() as p:
    b = p.chromium.launch(**LAUNCH)
    ctx = b.new_context(viewport={'width': 1400, 'height': 900})
    route_site(ctx)
    pg = ctx.new_page()
    for attempt in range(3):  # встроенный php-сервер стенда изредка «зависает» на запросе — повторяем вход и загрузку редактора
        try:
            login(pg)
            pg.goto('https://svr-mos.ru/wp-admin/post-new.php?post_type=page')
            pg.wait_for_function('window.wp && wp.blocks && wp.blocks.getBlockTypes().length > 80', timeout=60000)
            break
        except Exception as e:  # noqa
            print('editor load retry:', type(e).__name__)
            if attempt == 2:
                raise
            pg.close(); pg = ctx.new_page()
    print('block types:', pg.evaluate('wp.blocks.getBlockTypes().length'), 'WP', pg.evaluate('document.body.className.match(/branch-[\\d-]+/)?.[0]'))
    bad = 0
    for f in files:
        src = f.read_text()
        r = pg.evaluate(JS, src)
        (out_dir / f.name).write_text(r['out'] + '\n')
        same = 'same' if r['out'].strip() == src.strip() else 'normalized'
        fail = bool(r['issues']) or (strict and same != 'same')
        status = 'OK ' if not fail else 'BAD'
        bad += fail
        print(f'{status} {f.name}: {r["count"]} blocks, {same}')
        for it in r['issues'][:12]:
            print('   ', it['path']); [print('       ', x) for x in it['issues']]
    b.close()
    sys.exit(1 if bad else 0)
