"""Демо-страница из ВСЕХ фрагментов system/components.md → system/demo-content.html.
Собирается из тех же сниппетов, что лежат в components.md (они уже прошли валидатор редактора WP 7.1.3).
Правки ради одной страницы (иначе дубли id и нарушение правил spec):
  * 01 (утилиты текста) и 02 (кнопки) показаны внутри секции-шаблона 03 вместо её текста-заглушки;
  * 11 (штамп контактов) входит в 10 и 17;
  * в 17 («Как добраться») убрана колонка с cta-drop.svg: капля разрешена один раз на странице и стоит в 10.
H1 в демо один — в герое (04). В шаблоне page шаблон добавит свой H1 (заголовок страницы) — это особенность демо:
герой предназначен только для главной (page-no-title).
Запуск: python3 tools/build_demo.py"""
import pathlib, re

R = pathlib.Path(__file__).resolve().parent.parent
md = (R / 'system/components.md').read_text(encoding='utf-8')
snip = {}
for m in re.finditer(r'^### (\d\d)\. .*?\n```html\n(.*?)```', md, re.S | re.M):
    snip[m.group(1)] = m.group(2).strip()
assert len(snip) == 19, sorted(snip)


def one(s, old, new):
    assert s.count(old) == 1, (old[:80], s.count(old))
    return s.replace(old, new)


# 03 + 01 + 02: секция «Утилиты текста и кнопки»
sec = snip['03']
sec = one(sec, '<p class="svr-kicker"><strong>01</strong> Как мы работаем</p>', '<p class="svr-kicker"><strong>00</strong> Библиотека</p>')
sec = one(sec, '<h2 class="wp-block-heading">Контроль качества на&nbsp;каждом этапе</h2>', '<h2 class="wp-block-heading">Утилиты текста и&nbsp;кнопки</h2>')
sec = one(sec, '<p class="svr-lead has-large-font-size">Технологическая цепочка от обследования сооружений и лабораторных испытаний до технологических решений, проекта, собственного оборудования и пусконаладки.</p>',
          '<p class="svr-lead has-large-font-size">Надзаголовок, лид, мета, метка и код; кнопки primary, secondary, ghost, «назад», внешняя ссылка и крупная.</p>')
sec = one(sec, '<!-- wp:paragraph -->\n<p>Контент секции — группы align:wide.</p>\n<!-- /wp:paragraph -->', snip['01'] + '\n\n' + snip['02'])

# 18 без капли
c18 = snip['17']
c18 = re.sub(r'\n\n<!-- wp:column \{"width":"40%","className":"svr-cta__dwg"\} -->.*?<!-- /wp:column -->', '', c18, count=1, flags=re.S)
assert 'svrCta' not in c18

# 07 — внутри секции продукции страницы /prod/ (как в рецепте), со вступлением-H2
prod_intro = ('<!-- wp:group {"align":"wide","className":"svr-page-intro","layout":{"type":"default"}} -->\n'
              '<div class="wp-block-group alignwide svr-page-intro"><!-- wp:heading -->\n'
              '<h2 class="wp-block-heading">Мы сами проектируем и разрабатываем оборудование</h2>\n<!-- /wp:heading -->\n\n'
              '<!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->\n'
              '<p class="svr-lead has-large-font-size">Собственное оборудование для очистки сточных вод. Подбор и подробности — по запросу.</p>\n'
              '<!-- /wp:paragraph --></div>\n<!-- /wp:group -->')
prod_sec = ('<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec svr-sec\\u002d\\u002dband svr-mm svr-products",'
            '"style":{"spacing":{"blockGap":"var:preset|spacing|60"}},"layout":{"type":"constrained"}} -->\n'
            '<section class="wp-block-group alignfull svr-sec svr-sec--band svr-mm svr-products">' + snip['07'] + '</section>\n<!-- /wp:group -->')

parts = [
    snip['04'],            # герой (H1)
    snip['05'],            # этапы
    snip['06'],            # продукция на главной
    snip['08'],            # объекты
    snip['09'],            # документы и реквизиты
    sec,                   # 03 + 01 + 02
    snip['12'],            # вступление внутренней страницы
    snip['13'],            # объекты строками + ведомость
    snip['14'],            # страница объекта: вступление, работы, галерея, другие объекты
    prod_intro, prod_sec,  # 07 листы /prod/ с lightbox
    snip['15'],            # документ /docs/
    snip['16'],            # реквизиты
    snip['18'],            # страница продукции (заглушка параметров + другая продукция)
    snip['19'],            # таблица характеристик svr-spec
    c18,                   # контакты /contact/ (каналы связи + «Как добраться»)
    snip['10'],            # финальный CTA с каплей + штамп контактов
]
out = R / 'system/demo-content.html'
out.write_text('\n\n'.join(parts) + '\n', encoding='utf-8')
print(out, out.stat().st_size, 'B')
