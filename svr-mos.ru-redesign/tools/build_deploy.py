"""Сборка пакета публикации redesign/deploy/ (источник правды для сайта).

* deploy/pages/<id>.html — финальные страницы 49–58: ИСТОЧНИК, редактируются вручную (после ревью),
  этот скрипт их не перезаписывает и генератор components_src.py их больше не трогает;
* global-styles.json, parts/, templates/ — копируются из system/ (system/styles.css → build_system.py → JSON);
* manifest.json — шаги в порядке применения (те же REST-маршруты, что применяет tools/apply_manifest.php на стенде);
* проверка: в файлах нет file://, /tmp, localhost, 127.0.0.1, :8090; ссылки только на https://svr-mos.ru/.
Запуск: python3 tools/build_deploy.py"""
import json, pathlib, re, shutil, sys, hashlib

R = pathlib.Path(__file__).resolve().parent.parent
SYS, D = R / 'system', R / 'deploy'
THEME = 'twentytwentyfive'
LOGO_ALT = 'ООО «СВР» — на главную'
PAGES = [  # id, slug, заголовок, шаблон ('' — шаблон по умолчанию «page»)
    (49, 'home', 'Главная', 'page-no-title'),
    (50, 'obj', 'Наши объекты', ''),
    (51, 'elteza', 'ОАО «Элтеза»', 'wp-custom-template-obekt'),
    (52, 'russkii', 'ОАО «Мясокомбинат «Рузский»', 'wp-custom-template-obekt'),
    (53, 'os3-marino', 'ОС3 Марьино-Саларьево (II этап)', 'wp-custom-template-obekt'),
    (54, 'os2-marino', 'ОС2 Марьино-Саларьево (II этап)', 'wp-custom-template-obekt'),
    (55, 'prod', 'Наша продукция', ''),
    (56, 'docs', 'Документы', ''),
    (57, 'rekvizit', 'Реквизиты компании', ''),
    (58, 'contact', 'Контакты', ''),
]
PROD_PARENT = 55  # «Наша продукция» (/prod/)
PROD_TEMPLATE = 'wp-custom-template-produkciya'
PROD_PAGES = [  # slug, заголовок (id на сайте появится после создания через REST; изображение — id медиатеки)
    ('stanciya-dozirovaniya', 'Станции дозирования и приготовления реагентов двухкамерные'),
    ('reaktor-trehkamernyj', 'Реактор трёхкамерный'),
    ('reaktor-odnokamernyj', 'Реактор однокамерный'),
    ('ustanovka-obezzarazhivaniya', 'Установка комплексного обеззараживания сточных вод'),
    ('kns', 'Канализационные насосные станции'),
]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main():
    for sub in ('parts', 'templates', 'pages'):
        (D / sub).mkdir(parents=True, exist_ok=True)
    missing = [i for i, *_ in PAGES if not (D / 'pages' / f'{i}.html').exists()]
    missing += [f'prod-{sl}' for sl, _ in PROD_PAGES if not (D / 'pages' / f'prod-{sl}.html').exists()]
    if missing:
        sys.exit(f'нет deploy/pages для {missing}: страницы — источник, их нужно положить вручную')
    shutil.copyfile(SYS / 'global-styles.json', D / 'global-styles.json')
    for n in ('header', 'footer'):
        shutil.copyfile(SYS / f'{n}.html', D / 'parts' / f'{n}.html')
    for n in ('page', 'page-no-title', '404', 'wp-custom-template-obekt', PROD_TEMPLATE):
        shutil.copyfile(SYS / f'{n}.html', D / 'templates' / f'{n}.html')

    steps = [{'kind': 'global-styles', 'method': 'POST', 'route': '/wp/v2/global-styles/6', 'file': 'global-styles.json',
              'body': 'содержимое файла целиком ({settings, styles}; styles.css — в styles.css)'}]
    for n in ('header', 'footer'):
        steps.append({'kind': 'template-part', 'method': 'POST', 'route': f'/wp/v2/template-parts/{THEME}//{n}',
                      'file': f'parts/{n}.html', 'body': '{"content": <файл>}'})
    for n in ('page', 'page-no-title', '404'):
        steps.append({'kind': 'template', 'method': 'POST', 'route': f'/wp/v2/templates/{THEME}//{n}',
                      'file': f'templates/{n}.html', 'body': '{"content": <файл>}'})
    steps.append({'kind': 'template', 'method': 'POST', 'route': '/wp/v2/templates', 'create': True,
                  'slug': 'wp-custom-template-obekt', 'title': 'Страница объекта',
                  'update_route': f'/wp/v2/templates/{THEME}//wp-custom-template-obekt',
                  'file': 'templates/wp-custom-template-obekt.html',
                  'body': '{"slug": "wp-custom-template-obekt", "title": "Страница объекта", "content": <файл>}; '
                          'если шаблон уже есть — POST {"content": <файл>} на update_route'})
    steps.append({'kind': 'template', 'method': 'POST', 'route': '/wp/v2/templates', 'create': True,
                  'slug': PROD_TEMPLATE, 'title': 'Страница продукции',
                  'update_route': f'/wp/v2/templates/{THEME}//{PROD_TEMPLATE}',
                  'file': f'templates/{PROD_TEMPLATE}.html',
                  'body': '{"slug": "%s", "title": "Страница продукции", "content": <файл>}; '
                          'если шаблон уже есть — POST {"content": <файл>} на update_route' % PROD_TEMPLATE})
    steps.append({'kind': 'media-alt', 'method': 'POST', 'route': '/wp/v2/media/7', 'id': 7, 'alt_text': LOGO_ALT,
                  'body': '{"alt_text": "%s"}' % LOGO_ALT})
    # Новые страницы продукции: создаются ДО страниц 55 и 49 (на них ссылки), после шаблона продукции.
    # id появится после создания; если страница с таким slug и parent уже есть — обновляется (POST /wp/v2/pages/<id>).
    for slug, title in PROD_PAGES:
        steps.append({'kind': 'page-create', 'method': 'POST', 'route': '/wp/v2/pages', 'slug': slug, 'title': title,
                      'parent': PROD_PARENT, 'status': 'publish', 'comment_status': 'closed', 'template': PROD_TEMPLATE,
                      'url': f'https://svr-mos.ru/prod/{slug}/', 'file': f'pages/prod-{slug}.html',
                      'body': '{"title": "%s", "slug": "%s", "parent": %d, "status": "publish", "comment_status": "closed", '
                              '"template": "%s", "content": <файл>}' % (title, slug, PROD_PARENT, PROD_TEMPLATE)})
    order = [55, 49] + [i for i, *_ in PAGES if i not in (55, 49)]
    byid = {x[0]: x for x in PAGES}
    for i, slug, title, tpl in (byid[k] for k in order):
        steps.append({'kind': 'page', 'method': 'POST', 'route': f'/wp/v2/pages/{i}', 'id': i, 'slug': slug, 'title': title,
                      'file': f'pages/{i}.html', 'template': tpl,
                      'body': '{"content": <файл>, "template": "%s"}' % tpl})
    for n, st in enumerate(steps, 1):
        st['step'] = n
        if 'file' in st:
            st['sha256_16'] = sha(D / st['file'])
    ordered = [{k: st[k] for k in ['step'] + [k for k in st if k != 'step']} for st in steps]
    (D / 'manifest.json').write_text(json.dumps(ordered, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    # Проверка на локальные адреса и чужие ссылки
    bad = re.compile(r'file://|/tmp/|localhost|127\.0\.0\.1|:8090|/scratchpad|/home/user')
    url = re.compile(r'https?://[^\s"\'<>)]+')
    problems = []
    for f in sorted(D.rglob('*')):
        if f.is_dir() or f.suffix not in ('.html', '.json', '.md'):
            continue
        txt = f.read_text(encoding='utf-8')
        for m in bad.finditer(txt):
            problems.append(f'{f.relative_to(D)}: локальный адрес «{m.group(0)}»')
        if f.suffix in ('.html', '.json'):
            for m in url.finditer(txt):
                u = m.group(0)
                if not (u.startswith('https://svr-mos.ru/') or u.startswith('http://www.w3.org/') or
                        u.startswith('https://yandex.ru/maps/')):
                    problems.append(f'{f.relative_to(D)}: внешняя ссылка {u}')
    print(f'manifest.json: {len(ordered)} шагов')
    if problems:
        print('\n'.join(problems)); sys.exit(1)
    print('проверка адресов: OK (только https://svr-mos.ru/…, w3.org в xmlns SVG, yandex.ru/maps на /contact/)')


if __name__ == '__main__':
    main()
