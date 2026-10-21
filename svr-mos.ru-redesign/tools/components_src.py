"""Источник фрагментов блочной разметки компонентов «Чертёж» (spec.md §5, §7).
Здесь — «черновая» разметка; tools/validate_blocks.py прогоняет её через парсер/валидатор/сериализатор
WordPress 7.1.3 (настоящий редактор на локальном стенде) и сохраняет каноническую форму в tmp/canon/*.html."""
import json, pathlib, html as H

R = pathlib.Path(__file__).resolve().parent.parent
U = 'https://svr-mos.ru/wp-content/uploads/2026/10/'
SITE = 'https://svr-mos.ru/'
MEDIA = {m['id']: m for m in json.loads((R.parent / 'media.json').read_text())}
SVG = {n: (R / 'assets/svg' / n).read_text().strip() for n in ('hero-drop.svg', 'cta-drop.svg')}
ICONS = [l for l in (R / 'assets/svg/stage-icons.html').read_text().splitlines() if l.startswith('<svg')]
PDF = U + 'svr-deklaraciya-eac.pdf'
TEL, MAIL = 'tel:+79652808090', 'mailto:info@svr-mos.ru'
NB = ' '


def url(i):
    return MEDIA[i]['url']


def attrs(d):
    d = {k: v for k, v in d.items() if v is not None}
    return (' ' + json.dumps(d, ensure_ascii=False, separators=(',', ':'))) if d else ''


def cls(*c):
    c = ' '.join(x for x in c if x)
    return f' class="{c}"' if c else ''


def blk(name, a, inner):
    return f'<!-- wp:{name}{attrs(a)} -->\n{inner}\n<!-- /wp:{name} -->'


def p(text, c=None, fs=None):
    return blk('paragraph', {'className': c, 'fontSize': fs}, f'<p{cls(c, fs and f"has-{fs}-font-size")}>{text}</p>')


def h(text, level=2, c=None, fs=None, anchor=None):
    a = {'level': level if level != 2 else None, 'className': c, 'fontSize': fs}
    idattr = f' id="{anchor}"' if anchor else ''
    if anchor:
        a = {'level': a['level'], 'anchor': anchor, 'className': c, 'fontSize': fs}
    return blk('heading', a, f'<h{level}{idattr}{cls("wp-block-heading", c, fs and f"has-{fs}-font-size")}>{text}</h{level}>')


def group(inner, c=None, tag='div', align=None, layout=None, anchor=None, gap=None, style=None):
    st = dict(style or {})
    if gap is not None:
        st.setdefault('spacing', {})['blockGap'] = gap
    a = {'tagName': tag if tag != 'div' else None, 'anchor': anchor, 'align': align, 'className': c,
         'style': st or None, 'layout': layout or {'type': 'default'}}
    idattr = f' id="{anchor}"' if anchor else ''
    return blk('group', a, f'<{tag}{idattr}{cls("wp-block-group", align and "align" + align, c)}>{"".join(inner) if isinstance(inner, list) else inner}</{tag}>')


def section(inner, c, anchor=None, gap='var:preset|spacing|60'):
    return group(inner, c=c, tag='section', align='full', layout={'type': 'constrained'}, anchor=anchor, gap=gap)


def columns(cols, c=None, align='wide', valign=None):
    a = {'verticalAlignment': valign, 'align': align, 'className': c}
    return blk('columns', a, f'<div{cls("wp-block-columns", valign and f"are-vertically-aligned-{valign}", align and "align" + align, c)}>{"".join(cols)}</div>')


def column(inner, width=None, c=None, valign=None):
    a = {'verticalAlignment': valign, 'width': width, 'className': c}
    st = f' style="flex-basis:{width}"' if width else ''
    return blk('column', a, f'<div{cls("wp-block-column", valign and f"is-vertically-aligned-{valign}", c)}{st}>{"".join(inner) if isinstance(inner, list) else inner}</div>')


def btn(text, href, c=None, outline=False, blank=False, width=None):
    cc = ' '.join(x for x in (('is-style-outline' if outline else None), c) if x) or None
    tgt = ' target="_blank" rel="noreferrer noopener"' if blank else ''
    a = {'width': width, 'className': cc}
    wcls = width and f'has-custom-width wp-block-button__width-{width}'
    return blk('button', a, f'<div{cls("wp-block-button", wcls, cc)}><a class="wp-block-button__link wp-element-button" href="{href}"{tgt}>{text}</a></div>')


def buttons(bs, c='svr-btns'):
    return blk('buttons', {'className': c}, f'<div{cls("wp-block-buttons", c)}>{"".join(bs)}</div>')


def lst(items, c=None):
    li = ''.join(blk('list-item', {}, f'<li>{t}</li>') for t in items)
    return blk('list', {'className': c}, f'<ul{cls("wp-block-list", c)}>{li}</ul>')


def img(i, alt, c=None, caption=None, lightbox=False, href=None, blank=False, anchor=None, ratio=None):
    a = {'lightbox': {'enabled': True} if lightbox else None, 'id': i, 'aspectRatio': ratio, 'scale': 'cover' if ratio else None,
         'sizeSlug': 'full', 'linkDestination': 'custom' if href else 'none', 'className': c}
    if anchor:
        a = {'anchor': anchor, **a}
    st = f' style="aspect-ratio:{ratio};object-fit:cover"' if ratio else ''
    tag = f'<img src="{url(i)}" alt="{alt}" class="wp-image-{i}"{st}/>'
    if href:
        tgt = ' target="_blank" rel="noreferrer noopener"' if blank else ''
        tag = f'<a href="{href}"{tgt}>{tag}</a>'
    cap = f'<figcaption class="wp-element-caption">{caption}</figcaption>' if caption else ''
    idattr = f' id="{anchor}"' if anchor else ''
    return blk('image', a, f'<figure{idattr}{cls("wp-block-image size-full", c)}>{tag}{cap}</figure>')


def table(rows, c, fixed=True, head=None, caption=None):
    def cell(x):
        tag, txt, *rest = x
        extra = ''.join(f' {k}="{v}"' for k, v in (rest[0] if rest else {}).items())
        return f'<{tag}{extra}>{txt}</{tag}>'
    th = ('<thead><tr>' + ''.join(cell(x) for x in head) + '</tr></thead>') if head else ''
    tb = '<tbody>' + ''.join('<tr>' + ''.join(cell(x) for x in r) + '</tr>' for r in rows) + '</tbody>'
    cap = f'<figcaption class="wp-element-caption">{caption}</figcaption>' if caption else ''
    a = {'hasFixedLayout': None if fixed else False, 'className': c}
    return blk('table', a, f'<figure{cls("wp-block-table", c)}><table{cls("has-fixed-layout" if fixed else None)}>{th}{tb}</table>{cap}</figure>')


def rawhtml(x):
    return f'<!-- wp:html -->\n{x}\n<!-- /wp:html -->'


def gallery(items):
    inner = ''.join(img(i, alt, c=c, lightbox=True) for i, alt, c in items)
    a = {'columns': 2, 'imageCrop': False, 'linkTo': 'none', 'sizeSlug': 'full', 'className': 'svr-gallery'}
    return blk('gallery', a, f'<figure class="wp-block-gallery has-nested-images columns-2 svr-gallery">{inner}</figure>')


# ------------------------------------------------------------------ данные
STAGES = [  # код, название, краткое описание (только факты брифа)
    ('01', 'Обследование', f'Инженерные изыскания, обследование действующих и{NB}построенных сооружений.'),
    ('02', 'Лаборатория', f'Отбор проб сточных вод, лабораторные испытания, определение показателей сточных{NB}вод.'),
    ('03', 'Технологические решения', 'Определение оптимальных технологических решений.'),
    ('04', 'Проектирование', f'Проектная и{NB}рабочая документация.'),
    ('05', 'Оборудование', f'Проектируем и{NB}разрабатываем сами. <a href="#produkciya">Смотреть продукцию</a>'),
    ('06', 'Пусконаладка', f'Маркировка оборудования, выявление неисправностей, определение режимов{NB}работы.'),
]
STAGE_NAME = {s[0]: s[1] for s in STAGES}
PRODUCTS = [  # поз., название, id изображения, slug страницы /prod/<slug>/
    ('01', f'Станции дозирования и{NB}приготовления реагентов двухкамерные', 13, 'stanciya-dozirovaniya'),
    ('02', 'Реактор трёхкамерный', 14, 'reaktor-trehkamernyj'),
    ('03', 'Реактор однокамерный', 15, 'reaktor-odnokamernyj'),
    ('04', 'Установка комплексного обеззараживания сточных вод', 16, 'ustanovka-obezzarazhivaniya'),
    ('05', 'Канализационные насосные станции', 17, 'kns'),
]
# Названия — как в заголовках страниц (без неразрывных пробелов; для H1 шаблона и title страницы)
PRODUCT_TITLE = {
    'stanciya-dozirovaniya': 'Станции дозирования и приготовления реагентов двухкамерные',
    'reaktor-trehkamernyj': 'Реактор трёхкамерный', 'reaktor-odnokamernyj': 'Реактор однокамерный',
    'ustanovka-obezzarazhivaniya': 'Установка комплексного обеззараживания сточных вод',
    'kns': 'Канализационные насосные станции'}
PROD_TEMPLATE = 'wp-custom-template-produkciya'
OBJ_TITLE = {
    'elteza': 'ОАО «Элтеза»', 'russkii': 'ОАО «Мясокомбинат «Рузский»',
    'os3-marino': f'ОС3 Марьино-Саларьево (II{NB}этап)', 'os2-marino': f'ОС2 Марьино-Саларьево (II{NB}этап)'}
OBJECTS = [  # slug, код, тип, задача, этапы, обложка
    ('elteza', 'ОБ-01', 'Гальваническое производство', 'Сточные воды гальванического производства.', ['01', '02', '03', '04'], 20),
    ('russkii', 'ОБ-02', 'Мясокомбинат', f'Проект очистных сооружений и{NB}сетей ливневой канализации.', ['01', '02', '03', '04'], 26),
    ('os3-marino', 'ОБ-03', 'Ливневые очистные сооружения', 'Пусконаладочные работы очистных сооружений ливневой канализации.', ['01', '02', '06'], 34),
    ('os2-marino', 'ОБ-04', 'Ливневые очистные сооружения', 'Пусконаладочные работы очистных сооружений ливневой канализации.', ['01', '02', '06'], 45),
]
ALT = {
    7: 'СВР', 12: 'Декларация о соответствии ЕАЭС — открыть PDF',
    13: 'Станции дозирования и приготовления реагентов двухкамерные — 3D-модель', 14: 'Реактор трёхкамерный — 3D-модель',
    15: 'Реактор однокамерный — 3D-модель', 16: 'Установка комплексного обеззараживания сточных вод — 3D-модель',
    17: 'Канализационные насосные станции — 3D-модель', 18: 'ОАО «Элтеза»: технологическая схема',
    19: 'Лабораторная посуда с растворами', 20: 'ОАО «Элтеза»: ёмкости и оборудование очистных сооружений (коллаж)',
    21: 'Лабораторная посуда с цветными растворами', 22: 'ОАО «Элтеза»: стаканы с пробами на лабораторных мешалках',
    23: 'ОАО «Элтеза»: чертёж оборудования', 24: 'ОАО «Элтеза»: чертёж компоновки оборудования',
    25: 'ОАО «Элтеза»: чертёж компоновки оборудования, разрез',
    26: 'ОАО «Мясокомбинат «Рузский»: помещения и площадка (коллаж)', 27: 'ОАО «Мясокомбинат «Рузский»: 3D-модель очистных сооружений',
    28: 'Рельефная карта местности', 29: 'Лабораторная посуда и документ',
    30: 'ОАО «Мясокомбинат «Рузский»: технологическая блок-схема', 31: 'ОАО «Мясокомбинат «Рузский»: чертежи',
    32: 'ОАО «Мясокомбинат «Рузский»: пробы сточных вод и лоток (коллаж)',
    33: 'ОАО «Мясокомбинат «Рузский»: пробы на лабораторных мешалках (коллаж)',
    34: 'ОС3 Марьино-Саларьево: напорный фильтр с манометрами', 35: 'ОС3 Марьино-Саларьево: манометры на напорных фильтрах',
    36: 'ОС3 Марьино-Саларьево: колодец и проба воды',
    37: 'ОС3 Марьино-Саларьево: таблица режима подачи очищенных сточных вод на промывку фильтров',
    38: 'ОС3 Марьино-Саларьево: напорные фильтры и шкаф управления', 39: 'ОС3 Марьино-Саларьево: таблицы расхода и графики',
    40: 'ОС3 Марьино-Саларьево: лаборатория и проба воды',
    41: 'ОС2 Марьино-Саларьево: напорный фильтр I ступени и шкафы управления',
    42: 'ОС2 Марьино-Саларьево: оборудование в помещении очистных сооружений',
    43: 'ОС2 Марьино-Саларьево: таблицы расхода и графики', 44: 'ОС2 Марьино-Саларьево: колодец и проба воды',
    45: 'ОС2 Марьино-Саларьево: напорные фильтры с маркировкой арматуры', 46: 'ОС2 Марьино-Саларьево: манометры на напорном фильтре',
    47: 'ОС2 Марьино-Саларьево: таблица режима подачи ливневых сточных вод на очистку', 48: 'Химическая лаборатория',
}
WORKS_OS = [('01', 'Обследование построенных сооружений'), ('02', 'Отбор проб сточных вод ливневой канализации'),
            ('02', 'Проведение лабораторных испытаний'), ('02', 'Определение показателей сточных вод'),
            ('06', 'Маркировка оборудования'), ('06', 'Выявление неисправностей'), ('06', 'Определение режимов работы')]
WORKS = {
    'elteza': [('01', 'Обследование действующих сооружений'), ('02', 'Отбор проб сточных вод гальванического производства'),
               ('02', 'Проведение лабораторных испытаний'), ('02', 'Определение показателей сточных вод'),
               ('03', 'Определение оптимальных технологических решений'), ('04', 'Разработка проектной документации'),
               ('04', 'Разработка рабочей документации')],
    'russkii': [('01', 'Инженерные изыскания'), ('01', 'Обследование действующих сооружений'),
                ('02', 'Отбор проб сточных вод цеха обработки'), ('02', 'Определение показателей сточных вод'),
                ('02', 'Проведение лабораторных испытаний'), ('03', 'Определение оптимальных технологических решений'),
                ('04', 'Разработка рабочей документации')],
    'os3-marino': WORKS_OS, 'os2-marino': WORKS_OS,
}
GALLERY = {  # P — svr-on-paper, N — svr-native
    'elteza': '20 22 18P 23P 24P 25P 19 21N', 'russkii': '26 32 33 27P 30P 31P 29 28',
    'os3-marino': '34 35 38 36 40 37P 39P', 'os2-marino': '45 41 42 44 46 43P 47P 48'}
MATRIX = [
    ('01', 'Инженерные изыскания', '-+--'), ('01', 'Обследование действующих сооружений', '++--'),
    ('01', 'Обследование построенных сооружений', '--++'), ('02', 'Отбор проб сточных вод', '++++'),
    ('02', 'Лабораторные испытания', '++++'), ('02', 'Определение показателей сточных вод', '++++'),
    ('03', 'Определение оптимальных технологических решений', '++--'), ('04', 'Разработка проектной документации', '+---'),
    ('04', 'Разработка рабочей документации', '++--'), ('06', 'Маркировка оборудования', '--++'),
    ('06', 'Выявление неисправностей', '--++'), ('06', 'Определение режимов работы', '--++'),
]
HOURS = 'Пн—Пт 10:00—18:00'
ADDR = f'Москва, Ярославское шоссе, д.{NB}42, оф.{NB}603'
METRO = f'м.{NB}«ВДНХ», «Ботанический сад»'
YMAPS = 'https://yandex.ru/maps/?text=%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%2C%20%D0%AF%D1%80%D0%BE%D1%81%D0%BB%D0%B0%D0%B2%D1%81%D0%BA%D0%BE%D0%B5%20%D1%88%D0%BE%D1%81%D1%81%D0%B5%2C%2042'
# Кадрирование прозрачных полей у рендера УКО (id 16, чертёж — 43 % высоты холста): главная — 4/3, /prod/ — 1
CROP = {16: {False: '4/3', True: '1'}}


# ------------------------------------------------------------------ компоненты
def kicker(num, text):
    return p(f'<strong>{num}</strong> {text}' if num else text, 'svr-kicker')


def ghost(text, href, extra=None, blank=False):
    return btn(text, href, c=' '.join(x for x in ('svr-btn--ghost', extra) if x), blank=blank)


def head(num, kick, title, lead, ghost_btn=None):
    right = [p(lead, 'svr-lead', 'large')]
    if ghost_btn:
        right.append(buttons([ghost_btn], c='svr-btns'))
    top = [kicker(num, kick)] if kick else []
    return group(top + [columns([column(h(title), '56%'), column(right, '44%')], c='svr-head__row', align=None)],
                 c='svr-head', align='wide')


def call_buttons(short=False, mail_text='info@svr-mos.ru'):
    return buttons([btn('Позвонить' if short else f'Позвонить: 8{NB}965{NB}280-80-90', TEL, 'svr-ic-tel'),
                    btn('Написать' if short else mail_text, MAIL, 'svr-ic-mail', outline=True)])


def hero():
    text = column([
        p('Сервис водных ресурсов', 'svr-eyebrow'),
        h('Очистка <mark style="background-color:rgba(0,0,0,0)" class="has-inline-color has-accent-1-color">сточных вод</mark>'
          f' на{NB}промышленных объектах', 1, 'svr-hero__title', 'hero'),
        p(f'Изыскания и{NB}обследование сооружений, отбор проб и{NB}лабораторные испытания, технологические решения, проектная '
          f'и{NB}рабочая документация, пусконаладка и{NB}собственное оборудование.', 'svr-lead', 'large'),
        call_buttons(),
        p(f'{HOURS} · {METRO}', 'svr-meta svr-hero__note', 'small'),
    ], '56%', 'svr-hero__text', 'center')
    dwg = column(rawhtml(SVG['hero-drop.svg']), '44%', 'svr-hero__dwg', 'center')
    return section([columns([text, dwg], c='svr-hero__grid', valign='center'), facts()], 'svr-hero svr-mm svr-ruler',
                   gap='var:preset|spacing|50')


def facts():
    cell = lambda k, v, href: group([p(k, 'svr-facts__k'), p(f'<a href="{href}">{v}</a>', 'svr-facts__v')], c='svr-facts__cell')
    return group([cell('Цикл', f'От{NB}изысканий до{NB}пусконаладки', '#etapy'),
                  cell('Оборудование', f'Проектируем и{NB}разрабатываем сами', SITE + 'prod/'),
                  cell('Соответствие', f'Декларация{NB}ЕАЭС', SITE + 'docs/')],
                 c='svr-facts', align='wide', layout={'type': 'grid', 'columnCount': 3})


def stage(code, name, text, icon):
    return group([rawhtml(f'<span class="svr-stage__ico" aria-hidden="true">{icon}</span>'),
                  p(f'<code>{code}</code>', 'svr-stage__no'), h(name, 3), p(text, 'svr-stage__text')], c='svr-stage')


def process():
    stages = group([stage(c, n, t, ICONS[k]) for k, (c, n, t) in enumerate(STAGES)], c='svr-stages', align='wide',
                   layout={'type': 'grid', 'columnCount': 3})
    return section([head(None, 'Как мы работаем', f'Контроль качества на{NB}каждом этапе',
                         f'Технологическая цепочка от{NB}обследования сооружений и{NB}лабораторных испытаний до{NB}технологических '
                         f'решений, проекта, собственного оборудования и{NB}пусконаладки.'),
                    stages],
                   'svr-sec svr-sec--loose svr-ruler', anchor='etapy')


def prod_url(slug):
    return f'{SITE}prod/{slug}/'


def sheet(pos, name, i, slug, page=False):
    """Лист продукции: фото + название-ссылка на страницу /prod/<slug>/ (растянутая на весь лист) + «Подробнее»."""
    return group([img(i, ALT[i], 'svr-sheet__img', ratio=CROP.get(i, {}).get(page)),
                  group([h(f'<a href="{prod_url(slug)}">{name}</a>', 3, 'svr-sheet__name'), p('Подробнее', 'svr-sheet__more')], c='svr-sheet__tb')],
                 c='svr-sheet', anchor=f'poz-{pos}' if page else None)


def sheet_cta():
    return group([p('По запросу', 'svr-label'),
                  h(f'Подбор оборудования под{NB}ваш объект', 3, 'svr-sheet__name'),
                  p(f'Подробности по{NB}каждой позиции{NB}— по{NB}запросу.'), call_buttons(short=True)], c='svr-sheet svr-sheet--cta')


def sheets(page=False):
    return group([sheet(*x, page=page) for x in PRODUCTS] + [sheet_cta()], c='svr-sheets svr-sheets--page' if page else 'svr-sheets',
                 align='wide', layout={'type': 'grid', 'columnCount': 3})


def sheets_rel(slug):
    """«Другая продукция» на странице продукции: остальные 4 позиции, 4 колонки."""
    return group([sheet(*x) for x in PRODUCTS if x[3] != slug], c='svr-sheets svr-sheets--rel', align='wide',
                 layout={'type': 'grid', 'columnCount': 4})


PROD_TITLE = f'Мы сами проектируем и{NB}разрабатываем оборудование'
PROD_LEAD = f'Собственное оборудование для{NB}очистки сточных вод. Подбор и{NB}подробности{NB}— по{NB}запросу.'


def products():
    return section([head(None, 'Продукция', PROD_TITLE, PROD_LEAD,
                         ghost('Вся продукция', SITE + 'prod/')), sheets()],
                   'svr-sec svr-sec--band svr-mm svr-ruler svr-products', anchor='produkciya')


def chips(codes):
    return lst([STAGE_NAME[c] for c in codes], 'svr-chips')


def obj_card(slug, code, kind, task, codes, cover):
    title = OBJ_TITLE[slug].replace('ОАО ', f'ОАО{NB}')
    return group([img(cover, ALT[cover], 'svr-obj__img'),
                  group([h(f'<a href="{SITE}{slug}/">{title}</a>', 3), p(task, 'svr-obj__desc'), chips(codes)], c='svr-obj__body')],
                 c='svr-obj')


def objects():
    return section([head(None, None, 'Наши объекты',
                         f'Гальваническое производство, мясокомбинат, очистные сооружения ливневой канализации{NB}— и{NB}состав работ на{NB}каждом объекте.',
                         ghost('Все объекты', SITE + 'obj/')),
                    group([obj_card(*o) for o in OBJECTS], c='svr-objs', align='wide', layout={'type': 'grid', 'columnCount': 2})],
                   'svr-sec svr-ruler', anchor='obekty')


REQ_MINI = [('ИНН', '<code>7716962072</code>'), ('КПП', '<code>771601001</code>'), ('Банк', f'АО{NB}«Райффайзенбанк»'), ('БИК', '<code>044525700</code>')]
REQ_FULL = [('Полное наименование', f'Общество с{NB}ограниченной ответственностью «СЕРВИС ВОДНЫХ РЕСУРСОВ»'),
            ('Сокращённое наименование', f'ООО{NB}«СВР»'),
            ('Юридический адрес', f'129347, г.{NB}Москва, вн.тер.г. муниципальный округ Ярославский, Ярославское шоссе, д.{NB}124, помещ.{NB}1'),
            ('ИНН', '<code>7716962072</code>'), ('КПП', '<code>771601001</code>'), ('Банк', f'АО{NB}«Райффайзенбанк»'),
            ('Расчётный счёт', '<code>40702810800000204238</code>'), ('Корреспондентский счёт', '<code>30101810200000000700</code>'), ('БИК', '<code>044525700</code>'),
            ('Генеральный директор', 'Новицкий Андрей Аркадьевич')]


def req_table(rows, extra=None):
    return table([[('th', k, {'scope': 'row'}), ('td', v)] for k, v in rows], ' '.join(x for x in ('svr-req', extra) if x), fixed=False)


def doc_card(lg=False):
    left = column(img(12, ALT[12], 'svr-doc-sheet', href=PDF, blank=True), '280px' if lg else '180px')
    btns = [btn('Открыть PDF', PDF, 'svr-ic-doc', outline=True, blank=True)]
    # /docs/: текст карточки не повторяет лид страницы и говорит, что делают кнопки (новая вкладка — WCAG G201)
    right_items = [p('Документ · PDF', 'svr-label'),
                   h(f'Декларация о{NB}соответствии ЕАЭС' if lg else f'Декларация о{NB}соответствии{NB}ЕАЭС', 2 if lg else 3),
                   p(f'Откройте документ в{NB}новой вкладке или{NB}скачайте файл{NB}PDF.' if lg
                     else f'Документ доступен для{NB}просмотра и{NB}скачивания.')]
    if lg:
        right_items.append(group([buttons(btns), blk('file', {'id': 11, 'href': PDF, 'className': 'svr-file'},
                               f'<div class="wp-block-file svr-file"><a href="{PDF}" class="wp-block-file__button wp-element-button" download>Скачать PDF</a></div>')],
                                 c='svr-doc-actions', layout={'type': 'flex', 'flexWrap': 'wrap'}))
    else:
        btns.append(ghost('Все документы', SITE + 'docs/'))
        right_items.append(buttons(btns))
    return group(columns([left, column(right_items)], align=None, valign='top'),
                 c='svr-card svr-card--doc svr-card--lg' if lg else 'svr-card svr-card--doc')


def docs():
    req = group([p('Реквизиты', 'svr-label'), h(f'ООО{NB}«Сервис водных ресурсов»', 3), req_table(REQ_MINI, 'svr-req--mini'),
                 buttons([ghost('Все реквизиты', SITE + 'rekvizit/')])], c='svr-card')
    return section([group([h(f'Документы и{NB}реквизиты')], c='svr-head', align='wide'),
                    columns([column(doc_card(), '50%'), column(req, '50%')], c='svr-docs-grid')],
                   'svr-sec svr-sec--tight', anchor='dokumenty', gap='var:preset|spacing|50')


def contacts():
    cell = lambda inner, extra=None: group(inner, c=' '.join(x for x in ('svr-contacts__cell', extra) if x))
    return group([
        cell([p('Телефон', 'svr-label'), p(f'<a href="{TEL}">8 965 280-80-90</a>', 'svr-phone', 'phone')], 'svr-contacts__cell--wide'),
        cell([p('Почта', 'svr-label'), p(f'<a href="{MAIL}">info@svr-mos.ru</a>', 'svr-mail')]),
        cell([p('Офис', 'svr-label'), p(ADDR)]),
        cell([p('Метро', 'svr-label'), p('«ВДНХ», «Ботанический сад»')]),
        cell([p('Режим работы', 'svr-label'), p(HOURS), p('Сб—Вс выходные', 'svr-meta', 'small')]),
    ], c='svr-contacts', align='wide', layout={'type': 'grid', 'columnCount': 3})


def contacts_channels():
    cell = lambda inner, extra=None: group(inner, c=' '.join(x for x in ('svr-contacts__cell', extra) if x))
    return group([
        cell([p('Телефон', 'svr-label'), p(f'<a href="{TEL}">8{NB}965{NB}280-80-90</a>', 'svr-phone', 'phone')], 'svr-contacts__cell--wide'),
        cell([p('Почта', 'svr-label'), p(f'<a href="{MAIL}">info@svr-mos.ru</a>', 'svr-mail')]),
        cell([p('Режим работы', 'svr-label'), p(HOURS), p('Сб—Вс выходные', 'svr-meta', 'small')]),
    ], c='svr-contacts', align='wide', layout={'type': 'grid', 'columnCount': 2})


def cta():
    grid = columns([column([h('Мы делаем мир <mark style="background-color:rgba(0,0,0,0)" class="has-inline-color has-accent-1-color">чище</mark>',
                               2, 'svr-cta__title', 'display'),
                             p(f'Расскажите о{NB}задаче на{NB}вашем объекте{NB}— позвоните или напишите. Подбор оборудования и{NB}подробности{NB}— по{NB}запросу.',
                               'svr-lead', 'large')], '60%'),
                    column(rawhtml(SVG['cta-drop.svg']), '40%', 'svr-cta__dwg')], c='svr-cta__grid')
    return section([group(kicker(None, 'Контакты'), c='svr-head', align='wide'), grid, contacts()], 'svr-sec svr-sec--loose svr-mm svr-ruler svr-cta', anchor='kontakty')


def page_intro(inner):
    return group(inner, c='svr-page-intro', align='wide')


def works(slug):
    return lst([t for _c, t in WORKS[slug]], 'svr-works')


def obj_row(slug, code, kind, task, codes, cover):
    text = column([p(kind, 'svr-label'),
                   h(f'<a href="{SITE}{slug}/">{OBJ_TITLE[slug]}</a>'), p(task, 'svr-lead', 'large'), chips(codes), works(slug),
                   buttons([ghost('Подробнее об объекте', f'{SITE}{slug}/')])], '50%')
    pic = column(img(cover, ALT[cover], 'svr-obj__img'), '50%')
    return group(columns([pic, text], align=None), c='svr-obj svr-obj--row')


def matrix():
    head_ = [('th', 'Вид работ', {'scope': 'col'})] + [('th', n, {'scope': 'col'}) for n in ('Элтеза', 'Рузский', 'ОС3', 'ОС2')]
    rows = [[('th', t, {'scope': 'row'})] + [('td', '<strong>Да</strong>' if f == '+' else '<em>Нет</em>') for f in flags]
            for c, t, flags in MATRIX]
    return table(rows, 'svr-matrix', head=head_, caption=f'●{NB}выполнено · —{NB}не входило в{NB}состав работ')


def obj_page(slug):
    o = next(x for x in OBJECTS if x[0] == slug)
    _, code, kind, task, codes, _ = o
    tb = group([group([p('Задача', 'svr-tb__k'), p(task, 'svr-tb__v')], c='svr-tb__cell'),
                group([p('Этапы', 'svr-tb__k'), chips(codes)], c='svr-tb__cell')],
               c='svr-tb', align='wide', layout={'type': 'grid', 'columnCount': 2})
    intro = page_intro([group([p(kind, 'svr-label'), buttons([ghost('Все объекты', SITE + 'obj/', 'svr-btn--back')])],
                              layout={'type': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'space-between'}),
                        tb])
    items = []
    for t in GALLERY[slug].split():
        i = int(t.rstrip('PN'))
        c = 'svr-on-paper' if t.endswith('P') else 'svr-native' if t.endswith('N') else None
        items.append((i, ALT[i], c))
    others = [x for x in OBJECTS if x[0] != slug]
    mini = group([group([h(f'<a href="{SITE}{x[0]}/">{OBJ_TITLE[x[0]]}</a>', 3),
                         p(x[2], 'svr-meta', 'small')], c='svr-mini-obj') for x in others],
                 c='svr-mini-objs', align='wide', layout={'type': 'grid', 'columnCount': 3})
    return '\n\n'.join([
        intro,
        section([group(h('Выполненные работы'), c='svr-head', align='wide'), group(works(slug), align='wide')], 'svr-sec', gap='var:preset|spacing|50'),
        section([group(h(f'Фотографии и{NB}материалы'), c='svr-head', align='wide'), group(gallery(items), align='wide')], 'svr-sec svr-sec--band svr-ruler', gap='var:preset|spacing|50'),
        section([group(h('Другие объекты'), c='svr-head', align='wide'), mini], 'svr-sec', gap='var:preset|spacing|50'),
    ])


def page_obj():
    return '\n\n'.join([
        page_intro([p(f'Гальваническое производство, мясокомбинат, очистные сооружения ливневой канализации{NB}— состав работ на{NB}каждом объекте.', 'svr-lead', 'large')]),
        section(group([obj_row(*o) for o in OBJECTS], c='svr-objs-list', align='wide'), 'svr-sec'),
        section([group([h(f'Ведомость работ по{NB}объектам'), p(f'12{NB}видов работ{NB}× 4{NB}объекта', 'svr-meta', 'small')], c='svr-head', align='wide'), group(matrix(), align='wide')],
                'svr-sec svr-sec--band svr-ruler', gap='var:preset|spacing|40'),
    ])


def spec_note():
    """Заглушка вместо таблицы параметров, пока владелец не прислал данные (см. components.md, `svr-spec`)."""
    return group([h('Технические параметры'),
                  p(f'По{NB}запросу. Позвоните {TELNUM} или{NB}напишите {MAILTXT}.'),
                  call_buttons(short=True)], c='svr-card svr-spec-note')


TELNUM = f'<a href="{TEL}">8{NB}965{NB}280-80-90</a>'
MAILTXT = f'<a href="{MAIL}">info@svr-mos.ru</a>'


def spec_table(rows, note=None):
    """Таблица характеристик «Параметр — Значение» (когда владелец пришлёт параметры). rows: [(параметр, значение), …]."""
    return table([[('th', k, {'scope': 'row'}), ('td', v)] for k, v in rows], 'svr-spec', fixed=False,
                 head=[('th', 'Параметр', {'scope': 'col'}), ('th', 'Значение', {'scope': 'col'})], caption=note)


def product_page(slug):
    pos, name, i, _ = next(x for x in PRODUCTS if x[3] == slug)
    intro = page_intro([group([p('Продукция СВР', 'svr-label'), buttons([ghost('Вся продукция', SITE + 'prod/', 'svr-btn--back')])],
                              layout={'type': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'space-between'})])
    photo = group(img(i, ALT[i], 'svr-sheet__img', lightbox=True, ratio=CROP.get(i, {}).get(False)), c='svr-sheet svr-sheet--lead')
    main = columns([column(photo, '56%'),
                    column([p(f'Мы сами проектируем и{NB}разрабатываем оборудование.', 'svr-lead', 'large'), spec_note()], '44%', 'svr-prod__text')],
                   c='svr-prod')
    return '\n\n'.join([
        intro,
        section([group(main, align='wide')], 'svr-sec svr-sec--tight', gap='var:preset|spacing|50'),
        section([group(h('Другая продукция'), c='svr-head', align='wide'), sheets_rel(slug)],
                'svr-sec svr-sec--band svr-mm svr-ruler svr-products', gap='var:preset|spacing|50'),
    ])


def page_prod():
    return '\n\n'.join([
        page_intro([h(PROD_TITLE), p(PROD_LEAD, 'svr-lead', 'large')]),
        section(sheets(page=True), 'svr-sec svr-sec--band svr-mm svr-ruler svr-products'),
    ])


def page_docs():
    return '\n\n'.join([page_intro([p(f'Документы ООО{NB}«СВР» для{NB}просмотра и{NB}скачивания.', 'svr-lead', 'large')]),
                        section(group(doc_card(lg=True), align='wide'), 'svr-sec')])


def page_rekvizit():
    return '\n\n'.join([page_intro([p(f'Реквизиты ООО{NB}«СВР» для{NB}договоров и{NB}счетов. Значения выделяются целиком для{NB}копирования.', 'svr-lead', 'large')]),
                        section(group(req_table(REQ_FULL), c='svr-card', align='wide'), 'svr-sec')])


def page_contact():
    route = columns([column([h('Как добраться'), p(ADDR, 'svr-lead', 'large'), p(METRO),
                             buttons([ghost('Открыть в Яндекс Картах', YMAPS, 'svr-ic-ext', blank=True)])], '60%', valign='center'),
                     column(rawhtml(SVG['cta-drop.svg']), '40%', 'svr-cta__dwg')], c='svr-cta__grid')
    return '\n\n'.join([page_intro([p(f'Позвоните или напишите{NB}— обсудим задачу на{NB}вашем объекте. Подбор оборудования и{NB}подробности{NB}— по{NB}запросу.', 'svr-lead', 'large')]),
                        section(contacts_channels(), 'svr-sec svr-mm'),
                        section(route, 'svr-sec svr-sec--band')])


def page_home():
    return '\n\n'.join([hero(), process(), products(), objects(), docs(), cta()])


PROD_PAGES = {f'prod-{x[3]}': (lambda s=x[3]: product_page(s)) for x in PRODUCTS}
PAGES = {49: page_home, 50: page_obj, 51: lambda: obj_page('elteza'), 52: lambda: obj_page('russkii'),
         53: lambda: obj_page('os3-marino'), 54: lambda: obj_page('os2-marino'), 55: page_prod, 56: page_docs,
         57: page_rekvizit, 58: page_contact, **PROD_PAGES}

if __name__ == '__main__':
    out = R / 'tmp/pages'
    out.mkdir(parents=True, exist_ok=True)
    for pid, fn in PAGES.items():
        (out / f'{pid}.html').write_text(fn() + '\n')
    print('pages:', sorted(PAGES, key=str))
