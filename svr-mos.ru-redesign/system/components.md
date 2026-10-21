# Библиотека компонентов «Чертёж» — svr-mos.ru

WordPress 7.1.3 · Twenty Twenty-Five · стили — `global-styles.json` (поле `styles.css` = `styles.css` рядом).
Каждый фрагмент ниже **прогнан через парсер, валидатор и сериализатор блоков настоящего редактора WordPress 7.1.3**
(локальный стенд 7.1.3 из официального репозитория, `wp.blocks.parse` → `isValid` у всех блоков → `wp.blocks.serialize`)
и приведён ровно в той форме, в которой его сохранил бы редактор. Копируйте фрагменты целиком, от `<!-- wp:… -->` до
`<!-- /wp:… -->`. Тексты — только факты из брифа и spec.md.

## Как собирать страницы

**Источник правды для страниц сайта** — пакет `deploy/pages/<id>.html` (прошёл ревью и строгую проверку редактором). Фрагменты
ниже собраны тем же генератором (`tools/components_src.py`), что и страницы: после канонизации редактором генератор даёт
пакет байт в байт (проверка в `tools/rebuild.sh`). Типографика: неразрывные пробелы после коротких предлогов и союзов, перед тире,
в «ООО/ОАО/АО «…»» и в номере телефона — там, где без них остаются висячие слова (проверено на 320–1440 px).

**Шаблоны.** Главная (id 49) — шаблон `page-no-title` (контент целиком из компонентов, начиная с героя). Страницы объектов
51–54 — пользовательский шаблон `wp-custom-template-obekt` (как `page`, крошки «Главная / Наши объекты / Объект»). Страницы продукции
(`/prod/<slug>/`, дочерние /prod/) — `wp-custom-template-produkciya` (крошки «Главная / Продукция / Название»). Остальные —
шаблон `page`: он сам выводит шапку страницы (крошки «Главная / Заголовок» + H1 = заголовок страницы) и в конце блок
«Связаться» (`svr-cta-compact`). Поэтому в контенте внутренних страниц **нет H1** и нет финального CTA — контент начинается
с `svr-page-intro`, дальше секции с H2.

**Порядок блоков верхнего уровня в контенте:** только `svr-page-intro` (group `align:"wide"`) и секции (group
`tagName:"section"`, `align:"full"`, класс `svr-sec`/`svr-hero`). Внутри секции — только группы/колонки/таблицы `align:"wide"`.
Текст, положенный прямо в секцию, ядро сузит до 760 px и поставит по центру.

| Страница | Состав контента (номера фрагментов ниже) |
|---|---|
| 49 Главная (`page-no-title`) | 04 герой → 05 этапы → 06 продукция → 08 объекты → 09 документы → 10 финальный CTA |
| 50 /obj/ | 13 целиком (вступление → 4 строки объектов → ведомость) |
| 51–54 объекты | 14 (эталон 51; для 52–54 — данные из таблицы ниже) |
| 55 /prod/ | вступление с H2 «Мы сами проектируем и разрабатываем оборудование» + лид → секция `svr-sec svr-sec--band svr-mm svr-products` с фрагментом 07 (каждый лист — ссылка на страницу продукции) |
| /prod/<slug>/ (5 страниц, parent 55) | 18 (шаблон `wp-custom-template-produkciya`); таблица параметров — 19 |
| 56 /docs/ | 15 |
| 57 /rekvizit/ | 16 |
| 58 /contact/ | 17 |

**Данные для страниц объектов 52–54** (фрагмент 14 повторяется с этими значениями; альты — spec, приложение B):

| Стр. | Метка | Задача (ячейка «Задача» штампа) | Этапы (чипы) | Выполненные работы (`svr-works`) | Галерея (P = `svr-on-paper`, N = `svr-native`) |
|---|---|---|---|---|---|
| 52 /russkii/ | Мясокомбинат | Проект очистных сооружений и сетей ливневой канализации. | Обследование · Лаборатория · Технологические решения · Проектирование | 01 Инженерные изыскания · 01 Обследование действующих сооружений · 02 Отбор проб сточных вод цеха обработки · 02 Определение показателей сточных вод · 02 Проведение лабораторных испытаний · 03 Определение оптимальных технологических решений · 04 Разработка рабочей документации | 26, 32, 33, 27P, 30P, 31P, 29, 28 |
| 53 /os3-marino/ | Ливневые очистные сооружения | Пусконаладочные работы очистных сооружений ливневой канализации. | Обследование · Лаборатория · Пусконаладка | 01 Обследование построенных сооружений · 02 Отбор проб сточных вод ливневой канализации · 02 Проведение лабораторных испытаний · 02 Определение показателей сточных вод · 06 Маркировка оборудования · 06 Выявление неисправностей · 06 Определение режимов работы | 34, 35, 38, 36, 40, 37P, 39P |
| 54 /os2-marino/ | Ливневые очистные сооружения | то же, что 53 | Обследование · Лаборатория · Пусконаладка | тот же список, что у 53 | 45, 41, 42, 44, 46, 43P, 47P, 48 |

«Другие объекты» — три остальных объекта (код, название со ссылкой, тип).

## Правила разметки (обязательные)

1. **Валидность.** JSON в комментарии соответствует HTML: `className` ↔ `class`, `fontSize:"large"` ↔ `has-large-font-size`,
   `align:"wide"` ↔ `alignwide`, `anchor` ↔ `id`, `width` колонки ↔ `style="flex-basis:…"`. Не дописывайте в HTML атрибуты,
   которых нет в `save()` блока (`aria-label` на кнопке, `download` на `core/button`, `style` на параграфе без атрибута и т. п.).
2. **`\u002d\u002d` в JSON** — так редактор экранирует `--` внутри комментария блока (`svr-sec\u002d\u002dloose` = `svr-sec--loose`).
   Обе записи парсятся одинаково; HTML-атрибут `class` всегда с обычными `--`.
3. **Неразрывный пробел** редактор сохраняет как `&nbsp;` («на&nbsp;промышленных», «д.&nbsp;42», «оф.&nbsp;603», «II&nbsp;этап»).
4. **Ширина кнопки в WP 7.1** — `"style":{"dimensions":{"width":"100%"}}`. Старая форма `"width":100` + классы
   `has-custom-width wp-block-button__width-100` валидна, но редактор мигрирует её (deprecation) — не используйте.
5. **RichText:** только `<strong>`, `<em>`, `<code>`, `<a>`, `<mark style="background-color:rgba(0,0,0,0)" class="has-inline-color has-accent-1-color">`.
   Никаких `<span>`, `<br>`, `<b>`, `<i>`, `<small>` в параграфах/заголовках/ячейках/пунктах. `<span>` допустим только внутри `core/html`.
6. **Цвета и размеры** — только через классы компонентов и пресеты (`fontSize`), без инлайн-цветов и пиксельных размеров в `style`.
   Не используйте `accent-2` (#0089BF) и `accent-1` на бумаге для текста — контраст ниже AA.
7. **Изображения:** `core/image` с `id`, классом `wp-image-<id>`, `sizeSlug:"full"` и URL из media.json; alt — из spec
   (приложение B). WP сам добавит `width/height`, `srcset`, `sizes`, `loading`. Фото id 8, 9, 10 не используются.
8. **SVG** — только в `core/html`, файлы `assets/svg/*` без правки координат. `hero-drop.svg` — один раз (герой главной),
   `cta-drop.svg` — не больше одного раза на странице (финальный CTA главной; на /contact/ — в «Как добраться»).
   Бюджет бесконечных анимаций (≤8 на главной: герой — волна, пузырьки, 2 потока, 2 стрелки = 6; CTA — 2 потока) уже занят этими двумя чертежами — новых бесконечных анимаций не добавлять.
9. **Ссылки** между страницами — абсолютные `https://svr-mos.ru/<slug>/`; якоря главной — `#etapy`, `#produkciya`, `#obekty`,
   `#dokumenty`, `#kontakty`; листы /prod/ — `#poz-01…#poz-05` (якоря сохранены для старых ссылок), страницы продукции — `https://svr-mos.ru/prod/<slug>/`. Телефон — `tel:+79652808090`, почта — `mailto:info@svr-mos.ru`.
10. **Заголовки:** один H1 на страницу; секции — H2, карточки/узлы/листы — H3. Ключи штампов и контактов — параграфы, не заголовки.
11. **Появление по прокрутке** (≥782 px, при поддержке `animation-timeline`) получают классы `svr-sheet`, `svr-obj`, `svr-stage`,
    `svr-card` — не вешайте эти классы на что-то другое.
12. **Ничего не выдумывать:** никаких лет, количеств, клиентов, сертификатов (кроме декларации ЕАЭС), гарантий, цен,
    характеристик оборудования, сроков, отзывов, соцсетей.

## Радиусы, плотность и фон (редакция «Чертёж: плотнее»)

Радиусы заданы переменными в `:root` (`styles.css`): `--svr-r-btn: 12px` (все кнопки: `wp-block-button__link`, кнопка PDF `wp-block-file`, кнопки меню; тот же 12 px в `theme.json`
`styles.elements.button.border.radius`), `--svr-r-card: 14px` (листы, карточки объектов и документов, штамп, ведомость, контакты, фото галереи),
`--svr-r-tile: 20px` (плитка иконки этапа), `--svr-r-sm: 10px` (картинка в lightbox), `--svr-r-chip: 8px` (чипы этапов), `--svr-r-xs: 6px` (превью документа, ghost-кнопка).
Отступы: пресеты `spacing|50…80` = 26…44 / 44…70 / 70…122 / 104…174 px (первая версия: 24…40 / 40…64 / 64…112 / 96…160, то есть чуть воздушнее на ≈ 9 %), межстрочный основного текста 1,6.
Фон: миллиметровка снова заметная — `--svr-grid-fine/major` = .055/.115 (в первой версии .045/.095), маска `.svr-mm` широкая, на всей странице под секциями мягкая сетка 80 px (`body`),
линейка-тики `svr-ruler` над каждой секцией главной и над полосами внутренних страниц, ромб-кикер с линией, миллиметровка и уголки-метки на листах продукции (`svr-sheet`), уголки на фото
объектов и в галерее (один слой, двойных рамок нет), штамп под героем `svr-facts` из 3 ячеек. Номера и микроподписи (`Поз.`, `ОБ-0N`, `Рис. NN`) не возвращены.
Бесконечных анимаций ≤ 8 на главной (герой 6 + CTA 2), при `prefers-reduced-motion: reduce` — 0.

## Компоненты шаблонов (не вставлять в контент)

| Компонент | Где | Файл |
|---|---|---|
| Шапка `svr-header` (topbar ≥1024 px, логотип `core/site-logo`, навигация `svr-nav` с оверлеем ≤1023 px, кнопка-телефон) | часть шаблона `header` | `header.html` |
| Подвал `svr-footer` (бренд + контакты, разделы, объекты, строка реквизитов `svr-footer__req`, строка ©) | часть шаблона `footer` | `footer.html` |
| Шапка страницы `svr-page-hero` (крошки `svr-crumbs` + H1 `svr-page-title`) | шаблон `page` | `page.html` |
| То же с уровнем «Наши объекты» в крошках | шаблон `wp-custom-template-obekt` (51–54) | `wp-custom-template-obekt.html` |
| «Связаться» `svr-cta-compact` | шаблон `page` (скрыт на /contact/) | `page.html` |
| Страница 404 `svr-404` | шаблон `404` | `404.html` |

## Справочник классов

| Класс | Блок | Назначение |
|---|---|---|
| `svr-sec` `svr-sec--loose` `svr-sec--tight` `svr-sec--band` | group section | секция и её ритм |
| `svr-mm` | group | миллиметровка на фоне (нужен `position`/`isolation` — уже в CSS) |
| `svr-ruler` | group | линейка-шкала у верхнего края |
| `svr-head` `svr-head__row` | group / columns | шапка секции |
| `svr-kicker` `svr-eyebrow` `svr-lead` `svr-meta` `svr-label` | paragraph | текстовые роли |
| `svr-btns` · `svr-btn--ghost` `svr-btn--back` `svr-btn--lg` · `svr-ic-tel` `svr-ic-mail` `svr-ic-doc` `svr-ic-arrow` `svr-ic-ext` | buttons / button | кнопки |
| `svr-hero` `svr-hero__grid` `svr-hero__text` `svr-hero__title` `svr-hero__dwg` `svr-hero__note` | group / columns / column / heading / paragraph | герой |
| `svr-tb` `svr-tb__cell` `svr-tb__k` `svr-tb__v` | group grid / group / paragraph | штамп «задача / этапы» на страницах объектов |
| `svr-facts` `svr-facts__cell` `svr-facts__k` `svr-facts__v` | group grid / group / paragraph | штамп под героем главной (3 ячейки-ссылки) |
| `svr-stages` `svr-stage` `svr-stage__ico` `svr-stage__no` `svr-stage__text` | group grid / html / paragraph | этапы работ |
| `svr-products` `svr-sheets` `svr-sheets--page` `svr-sheets--rel` `svr-sheet` `svr-sheet--cta` `svr-sheet--lead` `svr-sheet__img` `svr-sheet__tb` `svr-sheet__name` `svr-sheet__more` | group / image / heading / paragraph | листы продукции |
| `svr-prod` `svr-prod__text` `svr-spec-note` `svr-spec` | columns / column / group / table | страница продукции: колонки фото + параметры, заглушка и таблица характеристик |
| `svr-objs` `svr-obj` `svr-obj--row` `svr-obj__img` `svr-obj__body` `svr-obj__desc` `svr-objs-list` | group / image / paragraph | объекты |
| `svr-chips` `svr-works` | list | чипы этапов, список работ |
| `svr-matrix` `svr-req` `svr-req--mini` | table | ведомость, реквизиты |
| `svr-footer__req` | group flex | строка реквизитов в подвале (3 абзаца) |
| `svr-docs-grid` `svr-card` `svr-card--doc` `svr-card--lg` `svr-doc-sheet` `svr-doc-actions` `svr-file` | group / columns / image / file | документы |
| `svr-cta` `svr-cta__grid` `svr-cta__title` `svr-cta__dwg` `svr-contacts` `svr-contacts__cell(--wide)` `svr-phone` `svr-mail` | group / columns / heading / paragraph | контакты |
| `svr-page-intro` `svr-mini-objs` `svr-mini-obj` `svr-gallery` `svr-on-paper` `svr-native` | group / gallery / image | внутренние страницы |

Каждый класс из таблицы имеет стили в `styles.css`, и каждый класс `styles.css` используется во фрагментах или шаблонах
(проверка — `tools/audit_markup.py`). Классы-маркеры секций без стилей (`svr-process`, `svr-objects`, `svr-docs`,
`svr-header__main`, `svr-footer__brand`, `svr-footer__col`, `svr-page-hero__head`, `svr-dwg--cta`) убраны при аудите:
секцию главной однозначно задаёт её якорь (`#etapy`, `#obekty`, `#dokumenty`). Не добавляйте свои `svr-*` без стилей.

**Демо-страница** `demo-content.html` (рядом) собрана из всех фрагментов ниже (`tools/build_demo.py`) и прошла валидатор
редактора: удобна для проверки CSS целиком (`tools/preview.py --content system/demo-content.html …`). Это не страница сайта.

## Фрагменты

### 01. Утилиты текста: надзаголовок, лид, мета, метка, код

*spec §5.1.* Параграфы с классами `svr-kicker` (короткая метка с линией; номер секции в формате «Жирный» `<strong>01</strong>` допустим, на сайте не используется), `svr-eyebrow` (только герой), `svr-lead` (+ `fontSize:"large"`), `svr-meta` (+ `fontSize:"small"`), `svr-label`. Коды и числа — формат «Код» (`<code>`): Fira Code 13 px, циан. Никаких `<span>`/`<br>`.

```html
<!-- wp:paragraph {"className":"svr-kicker"} -->
<p class="svr-kicker"><strong>01</strong> Как мы работаем</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"svr-eyebrow"} -->
<p class="svr-eyebrow">Сервис водных ресурсов</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Собственное оборудование для очистки сточных вод. Подбор и подробности — по запросу.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"svr-meta","fontSize":"small"} -->
<p class="svr-meta has-small-font-size">Пн—Пт 10:00—18:00 · м.&nbsp;«ВДНХ», «Ботанический сад»</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Гальваническое производство</p>
<!-- /wp:paragraph -->
```

### 02. Кнопки (`core/buttons` › `core/button`)

*spec §5.2.* primary — стиль по умолчанию; secondary — `is-style-outline`; ghost — `svr-btn--ghost` (стрелка справа, линия снизу); назад — `svr-btn--ghost svr-btn--back`; внешняя ссылка — `svr-btn--ghost svr-ic-ext`. Иконка слева: `svr-ic-tel`, `svr-ic-mail`, `svr-ic-doc`, `svr-ic-arrow` (не на ghost). Крупная — `svr-btn--lg`. Обёртка `core/buttons` с классом `svr-btns`. Новая вкладка — `target="_blank" rel="noreferrer noopener"` (так сохраняет редактор; у ghost-кнопки CSS добавляет скринридеру «(откроется в новой вкладке)»). Надпись главной кнопки — «Позвонить: 8&nbsp;965&nbsp;280-80-90» (номер через неразрывные пробелы: на ≤374 px у кнопок перенос разрешён). На ≤599 px в героe, полосе-CTA, CTA-листе, CTA страниц и 404 кнопки автоматически во всю ширину.

```html
<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"svr-ic-tel"} -->
<div class="wp-block-button svr-ic-tel"><a class="wp-block-button__link wp-element-button" href="tel:+79652808090">Позвонить: 8&nbsp;965&nbsp;280-80-90</a></div>
<!-- /wp:button -->

<!-- wp:button {"className":"is-style-outline svr-ic-mail"} -->
<div class="wp-block-button is-style-outline svr-ic-mail"><a class="wp-block-button__link wp-element-button" href="mailto:info@svr-mos.ru">info@svr-mos.ru</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"svr-btn\u002d\u002dghost"} -->
<div class="wp-block-button svr-btn--ghost"><a class="wp-block-button__link wp-element-button" href="https://svr-mos.ru/obj/">Все объекты</a></div>
<!-- /wp:button -->

<!-- wp:button {"className":"svr-btn\u002d\u002dghost svr-btn\u002d\u002dback"} -->
<div class="wp-block-button svr-btn--ghost svr-btn--back"><a class="wp-block-button__link wp-element-button" href="https://svr-mos.ru/obj/">Все объекты</a></div>
<!-- /wp:button -->

<!-- wp:button {"className":"svr-btn\u002d\u002dghost svr-ic-ext"} -->
<div class="wp-block-button svr-btn--ghost svr-ic-ext"><a class="wp-block-button__link wp-element-button" href="https://yandex.ru/maps/?text=%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%2C%20%D0%AF%D1%80%D0%BE%D1%81%D0%BB%D0%B0%D0%B2%D1%81%D0%BA%D0%BE%D0%B5%20%D1%88%D0%BE%D1%81%D1%81%D0%B5%2C%2042">Открыть в Яндекс Картах</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"is-style-outline svr-ic-doc"} -->
<div class="wp-block-button is-style-outline svr-ic-doc"><a class="wp-block-button__link wp-element-button" href="https://svr-mos.ru/wp-content/uploads/2026/10/svr-deklaraciya-eac.pdf" target="_blank" rel="noreferrer noopener">Открыть PDF</a></div>
<!-- /wp:button -->

<!-- wp:button {"className":"svr-ic-tel svr-btn\u002d\u002dlg"} -->
<div class="wp-block-button svr-ic-tel svr-btn--lg"><a class="wp-block-button__link wp-element-button" href="tel:+79652808090">Позвонить: 8&nbsp;965&nbsp;280-80-90</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons -->
```

### 03. Секция и шапка секции (`svr-sec`, `svr-head`)

*spec §5.1, §10.4.* `core/group` `tagName:"section"`, `align:"full"`, layout constrained, `blockGap` = `var:preset|spacing|60` (шапка → контент). Модификаторы: `svr-sec--loose` (паддинг 80), `svr-sec--tight` (без верхнего), `svr-sec--band` (полоса с фоном и линиями), `svr-mm` (миллиметровка). **Все прямые дети секции — группы `align:"wide"`** (иначе ядро сузит их до 760 px по центру). Шапка `svr-head`: кикер на всю ширину + `core/columns` 56/44 (H2 | лид + ghost-кнопка); ≤1023 px — в стек. Если нужен только заголовок — `svr-head` с кикером и/или H2 без колонок.

```html
<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec svr-sec\u002d\u002dband svr-mm","style":{"spacing":{"blockGap":"var:preset|spacing|60"}},"layout":{"type":"constrained"}} -->
<section class="wp-block-group alignfull svr-sec svr-sec--band svr-mm"><!-- wp:group {"align":"wide","className":"svr-head","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-head"><!-- wp:paragraph {"className":"svr-kicker"} -->
<p class="svr-kicker"><strong>01</strong> Как мы работаем</p>
<!-- /wp:paragraph -->

<!-- wp:columns {"className":"svr-head__row"} -->
<div class="wp-block-columns svr-head__row"><!-- wp:column {"width":"56%"} -->
<div class="wp-block-column" style="flex-basis:56%"><!-- wp:heading -->
<h2 class="wp-block-heading">Контроль качества на&nbsp;каждом этапе</h2>
<!-- /wp:heading --></div>
<!-- /wp:column -->

<!-- wp:column {"width":"44%"} -->
<div class="wp-block-column" style="flex-basis:44%"><!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Технологическая цепочка от обследования сооружений и лабораторных испытаний до технологических решений, проекта, собственного оборудования и пусконаладки.</p>
<!-- /wp:paragraph -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"svr-btn\u002d\u002dghost"} -->
<div class="wp-block-button svr-btn--ghost"><a class="wp-block-button__link wp-element-button" href="https://svr-mos.ru/obj/">Все объекты</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group -->

<!-- wp:group {"align":"wide","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide"><!-- wp:paragraph -->
<p>Контент секции — группы align:wide.</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></section>
<!-- /wp:group -->
```

### 04. Герой главной (`svr-hero`)

*spec §5.4.* Только на главной, первым блоком. Единственный H1 сайта на главной (`fontSize:"hero"`, «сточных вод» — формат «Подсветка» с `has-accent-1-color`; переносы — только CSS, «на&nbsp;промышленных» через неразрывный пробел). Справа — капля-резервуар в разрезе с трубами: `core/html` с `assets/svg/hero-drop.svg` без правок (id `svrHero*`, один раз на странице; viewBox 600×568, колонка до 520 px). Слева сверху труба входа: турбулентный пучок линий сходится в ровную трубу, задвижка, стрелка потока, бегущий пунктир; справа снизу труба выхода: задвижка, стрелка, пунктир. Подписей ровно две — «Вход · сточные воды» и «Выход · чистая вода» (моноширинный, 17 px в масштабе схемы, на ≤599 px 22 px — читаемо ≥12 px). Выносок 01–06, «R», размерных линий, отметки уровня и кропмарок нет. Генератор — `tools/make_drops.py`. Под героем — штамп `svr-facts` из 3 ячеек («Цикл: От изысканий до пусконаладки» → `#etapy`, «Оборудование: Проектируем и разрабатываем сами» → /prod/, «Соответствие: Декларация ЕАЭС» → /docs/): group grid `columnCount:3`, ячейка `svr-facts__cell` = ключ `svr-facts__k` + значение-ссылка `svr-facts__v` (ссылка растягивается на ячейку, ≥44 px); на ≤781 px — одна колонка строками. `svr-hero__note` виден только ≤1023 px.

```html
<!-- wp:group {"tagName":"section","align":"full","className":"svr-hero svr-mm svr-ruler","style":{"spacing":{"blockGap":"var:preset|spacing|50"}},"layout":{"type":"constrained"}} -->
<section class="wp-block-group alignfull svr-hero svr-mm svr-ruler"><!-- wp:columns {"verticalAlignment":"center","align":"wide","className":"svr-hero__grid"} -->
<div class="wp-block-columns alignwide are-vertically-aligned-center svr-hero__grid"><!-- wp:column {"verticalAlignment":"center","width":"56%","className":"svr-hero__text"} -->
<div class="wp-block-column is-vertically-aligned-center svr-hero__text" style="flex-basis:56%"><!-- wp:paragraph {"className":"svr-eyebrow"} -->
<p class="svr-eyebrow">Сервис водных ресурсов</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":1,"className":"svr-hero__title","fontSize":"hero"} -->
<h1 class="wp-block-heading svr-hero__title has-hero-font-size">Очистка <mark style="background-color:rgba(0,0,0,0)" class="has-inline-color has-accent-1-color">сточных вод</mark> на&nbsp;промышленных объектах</h1>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Изыскания и&nbsp;обследование сооружений, отбор проб и&nbsp;лабораторные испытания, технологические решения, проектная и&nbsp;рабочая документация, пусконаладка и&nbsp;собственное оборудование.</p>
<!-- /wp:paragraph -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"svr-ic-tel"} -->
<div class="wp-block-button svr-ic-tel"><a class="wp-block-button__link wp-element-button" href="tel:+79652808090">Позвонить: 8&nbsp;965&nbsp;280-80-90</a></div>
<!-- /wp:button -->

<!-- wp:button {"className":"is-style-outline svr-ic-mail"} -->
<div class="wp-block-button is-style-outline svr-ic-mail"><a class="wp-block-button__link wp-element-button" href="mailto:info@svr-mos.ru">info@svr-mos.ru</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons -->

<!-- wp:paragraph {"className":"svr-meta svr-hero__note","fontSize":"small"} -->
<p class="svr-meta svr-hero__note has-small-font-size">Пн—Пт 10:00—18:00 · м.&nbsp;«ВДНХ», «Ботанический сад»</p>
<!-- /wp:paragraph --></div>
<!-- /wp:column -->

<!-- wp:column {"verticalAlignment":"center","width":"44%","className":"svr-hero__dwg"} -->
<div class="wp-block-column is-vertically-aligned-center svr-hero__dwg" style="flex-basis:44%"><!-- wp:html -->
<svg class="svr-dwg" viewBox="0 0 600 568" role="img" aria-labelledby="svrHeroT svrHeroD" focusable="false" xmlns="http://www.w3.org/2000/svg">
<title id="svrHeroT">Капля-резервуар: вход сточных вод слева, выход чистой воды справа</title>
<desc id="svrHeroD">Чертёж капли-резервуара. Слева сверху труба входа: турбулентный поток сточных вод сходится в ровную трубу и поступает в резервуар. Справа снизу труба выхода: чистая вода. Внутри резервуара вода с мягкой волной и пузырьки.</desc>
<defs>
<clipPath id="svrHeroIn"><path d="M300 123.8 L407.26 284.33 A129 129 0 1 1 192.74 284.33 Z"/></clipPath>
<pattern id="svrHeroHatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" stroke="#0EB8DA" stroke-opacity=".5"/></pattern>
<mask id="svrHeroWall"><path d="M300 104 L416.41 278.22 A140 140 0 1 1 183.59 278.22 Z" fill="#fff"/><path d="M300 123.8 L407.26 284.33 A129 129 0 1 1 192.74 284.33 Z" fill="#000"/></mask>
<linearGradient id="svrHeroWater" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0EB8DA" stop-opacity=".42"/><stop offset="1" stop-color="#0089BF" stop-opacity=".08"/></linearGradient>
<linearGradient id="svrHeroBundle" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#3B5F8C" stop-opacity=".35"/><stop offset=".6" stop-color="#0EB8DA" stop-opacity=".7"/><stop offset="1" stop-color="#7FDCF2"/></linearGradient>
<radialGradient id="svrHeroGlow"><stop offset="0" stop-color="#0EB8DA" stop-opacity="0.14"/><stop offset="1" stop-color="#0EB8DA" stop-opacity="0"/></radialGradient>
</defs>
<circle cx="300" cy="356" r="238" fill="url(#svrHeroGlow)"/>
<circle cx="300" cy="360" r="159.6" fill="none" stroke="#0EB8DA" stroke-opacity=".3" stroke-dasharray="3 6"/>
<g clip-path="url(#svrHeroIn)">
<rect x="160" y="104" width="280" height="392" fill="#0B2540" fill-opacity=".55"/>
<path fill="url(#svrHeroWater)" opacity=".55" d="M-200 314q30-7 60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0V516H-200Z"/>
<g class="svr-dwg-wave"><path fill="url(#svrHeroWater)" d="M-200 322q30-8 60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0V516H-200Z"/></g>
<g class="svr-dwg-bubble" fill="none" stroke="#7FDCF2" stroke-opacity=".5">
<circle cx="268" cy="440" r="3.4"/>
<circle cx="338" cy="428" r="2.6"/>
</g>
</g>
<rect x="148" y="92" width="304" height="416" fill="url(#svrHeroHatch)" mask="url(#svrHeroWall)"/>
<path d="M300 104 L416.41 278.22 A140 140 0 1 1 183.59 278.22 Z" fill="none" stroke="#0EB8DA" stroke-width="2.2" stroke-linejoin="round"/>
<path d="M300 123.8 L407.26 284.33 A129 129 0 1 1 192.74 284.33 Z" fill="none" stroke="#0EB8DA" stroke-opacity=".7" stroke-linejoin="round"/>
<path d="M198.12 381.4A105 105 0 0 0 244.36 445.05" fill="none" stroke="#E8F1F8" stroke-opacity=".28" stroke-width="3" stroke-linecap="round"/>
<g transform="translate(18 30)" fill="none" stroke="url(#svrHeroBundle)" stroke-linecap="round"><path d="M0 10C30 2 40 30 70 18S120 30 160 31"/><path d="M0 22C25 34 45 6 75 26S125 34 160 32"/><path d="M0 34C20 20 50 50 80 34S125 30 160 32"/><path d="M0 46C30 58 40 26 72 44S120 36 160 33"/><path d="M0 56C25 44 55 62 85 46S128 35 160 33"/><path d="M0 16C35 26 30 46 66 38S118 31 160 31.5"/><path d="M0 40C28 30 48 56 78 30S124 33 160 32.5"/></g>
<path d="M178 62H300V104" fill="none" stroke="#0EB8DA" stroke-width="2"/>
<path class="svr-dwg-flow" d="M178 62H300V104" fill="none" stroke="#E8F1F8" stroke-width="2" stroke-dasharray="6 10"/>
<g stroke="#0EB8DA" stroke-width="1.5"><path d="M200.16 54L224.16 70V54L200.16 70Z" fill="#071B2F" stroke-linejoin="round"/><path d="M212.16 54V36M204.16 36H220.16" fill="none"/></g>
<path class="svr-dwg-arrow" d="M258.52 55l14 7-14 7z" fill="#0EB8DA"/>
<text class="svr-dwg-t" x="18" y="20">Вход · сточные воды</text>
<path d="M300 496V524H572" fill="none" stroke="#0EB8DA" stroke-width="2"/>
<path class="svr-dwg-flow" d="M300 496V524H572" fill="none" stroke="#E8F1F8" stroke-width="2" stroke-dasharray="6 10"/>
<path d="M572 514V534" stroke="#0EB8DA" stroke-width="2"/>
<g stroke="#0EB8DA" stroke-width="1.5"><path d="M410.4 516L434.4 532V516L410.4 532Z" fill="#071B2F" stroke-linejoin="round"/><path d="M422.4 516V498M414.4 498H430.4" fill="none"/></g>
<path class="svr-dwg-arrow" d="M517.6 517l14 7-14 7z" fill="#0EB8DA"/>
<text class="svr-dwg-t" x="572" y="556" text-anchor="end">Выход · чистая вода</text>
</svg>
<!-- /wp:html --></div>
<!-- /wp:column --></div>
<!-- /wp:columns -->

<!-- wp:group {"align":"wide","className":"svr-facts","layout":{"type":"grid","columnCount":3}} -->
<div class="wp-block-group alignwide svr-facts"><!-- wp:group {"className":"svr-facts__cell","layout":{"type":"default"}} -->
<div class="wp-block-group svr-facts__cell"><!-- wp:paragraph {"className":"svr-facts__k"} -->
<p class="svr-facts__k">Цикл</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"svr-facts__v"} -->
<p class="svr-facts__v"><a href="#etapy">От&nbsp;изысканий до&nbsp;пусконаладки</a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-facts__cell","layout":{"type":"default"}} -->
<div class="wp-block-group svr-facts__cell"><!-- wp:paragraph {"className":"svr-facts__k"} -->
<p class="svr-facts__k">Оборудование</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"svr-facts__v"} -->
<p class="svr-facts__v"><a href="https://svr-mos.ru/prod/">Проектируем и&nbsp;разрабатываем сами</a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-facts__cell","layout":{"type":"default"}} -->
<div class="wp-block-group svr-facts__cell"><!-- wp:paragraph {"className":"svr-facts__k"} -->
<p class="svr-facts__k">Соответствие</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"svr-facts__v"} -->
<p class="svr-facts__v"><a href="https://svr-mos.ru/docs/">Декларация&nbsp;ЕАЭС</a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group --></section>
<!-- /wp:group -->
```

### 05. Этапы работ (`svr-stages`, `svr-stage`)

*spec §5.5.* Якорь `etapy`. Канонический набор из 6 этапов. Сетка `svr-stages` — group grid `columnCount:3` (≤1023 px — 2 колонки, ≤699 px — 1). Карточка `svr-stage`: иконка в плитке 92 px (`core/html`, `<span class="svr-stage__ico">` + inline SVG 48×48 из `assets/svg/stage-icons.html`: штрих 2, скруглённые концы, светлый штрих + один голубой акцент; генератор — `tools/make_icons.py`), номер `<code>01</code>` в `svr-stage__no`, H3 и одна короткая фраза `svr-stage__text` (только факты брифа).

```html
<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec svr-sec\u002d\u002dloose svr-ruler","style":{"spacing":{"blockGap":"var:preset|spacing|60"}},"layout":{"type":"constrained"},"anchor":"etapy"} -->
<section class="wp-block-group alignfull svr-sec svr-sec--loose svr-ruler" id="etapy"><!-- wp:group {"align":"wide","className":"svr-head","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-head"><!-- wp:paragraph {"className":"svr-kicker"} -->
<p class="svr-kicker">Как мы работаем</p>
<!-- /wp:paragraph -->

<!-- wp:columns {"className":"svr-head__row"} -->
<div class="wp-block-columns svr-head__row"><!-- wp:column {"width":"56%"} -->
<div class="wp-block-column" style="flex-basis:56%"><!-- wp:heading -->
<h2 class="wp-block-heading">Контроль качества на&nbsp;каждом этапе</h2>
<!-- /wp:heading --></div>
<!-- /wp:column -->

<!-- wp:column {"width":"44%"} -->
<div class="wp-block-column" style="flex-basis:44%"><!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Технологическая цепочка от&nbsp;обследования сооружений и&nbsp;лабораторных испытаний до&nbsp;технологических решений, проекта, собственного оборудования и&nbsp;пусконаладки.</p>
<!-- /wp:paragraph --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group -->

<!-- wp:group {"align":"wide","className":"svr-stages","layout":{"type":"grid","columnCount":3}} -->
<div class="wp-block-group alignwide svr-stages"><!-- wp:group {"className":"svr-stage","layout":{"type":"default"}} -->
<div class="wp-block-group svr-stage"><!-- wp:html -->
<span class="svr-stage__ico" aria-hidden="true"><svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M8 7h14a2 2 0 0 1 2 2v30a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2z"/><path d="M6 24c2-1.8 3.6-1.8 6 0s4 1.8 6 0 3.4-1.6 6 0"/><path d="M6 15h4M6 32h4"/><circle cx="34" cy="28" r="7.5" stroke="#0EB8DA" fill="#0EB8DA" fill-opacity=".16"/><path d="M39.4 33.4 44 38" stroke="#0EB8DA"/></svg></span>
<!-- /wp:html -->

<!-- wp:paragraph {"className":"svr-stage__no"} -->
<p class="svr-stage__no"><code>01</code></p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Обследование</h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-stage__text"} -->
<p class="svr-stage__text">Инженерные изыскания, обследование действующих и&nbsp;построенных сооружений.</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-stage","layout":{"type":"default"}} -->
<div class="wp-block-group svr-stage"><!-- wp:html -->
<span class="svr-stage__ico" aria-hidden="true"><svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M18 6h12M20 6v11L9.6 36.6A4 4 0 0 0 13.2 42h21.6a4 4 0 0 0 3.6-5.4L28 17V6"/><path d="M13.5 30h21"/><path d="M24 25.5c2.2 3 3.6 4.6 3.6 6.6a3.6 3.6 0 0 1-7.2 0c0-2 1.4-3.6 3.6-6.6z" stroke="#0EB8DA" fill="#0EB8DA" fill-opacity=".2"/></svg></span>
<!-- /wp:html -->

<!-- wp:paragraph {"className":"svr-stage__no"} -->
<p class="svr-stage__no"><code>02</code></p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Лаборатория</h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-stage__text"} -->
<p class="svr-stage__text">Отбор проб сточных вод, лабораторные испытания, определение показателей сточных&nbsp;вод.</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-stage","layout":{"type":"default"}} -->
<div class="wp-block-group svr-stage"><!-- wp:html -->
<span class="svr-stage__ico" aria-hidden="true"><svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M17 6h14a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H17a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z"/><path d="M24 16v6M10 28v-3a3 3 0 0 1 3-3h22a3 3 0 0 1 3 3v3"/><path d="M6 28h8a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2z"/><path d="M34 28h8a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2h-8a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2z" stroke="#0EB8DA" fill="#0EB8DA" fill-opacity=".2"/><path d="M35.5 33l2 2 3-3.5" stroke="#0EB8DA"/></svg></span>
<!-- /wp:html -->

<!-- wp:paragraph {"className":"svr-stage__no"} -->
<p class="svr-stage__no"><code>03</code></p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Технологические решения</h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-stage__text"} -->
<p class="svr-stage__text">Определение оптимальных технологических решений.</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-stage","layout":{"type":"default"}} -->
<div class="wp-block-group svr-stage"><!-- wp:html -->
<span class="svr-stage__ico" aria-hidden="true"><svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M30 6H12a2 2 0 0 0-2 2v32a2 2 0 0 0 2 2h14M30 6l8 8v7M30 6v6a2 2 0 0 0 2 2h6"/><path d="M16 22h12M16 29h7"/><path d="M41.2 26.8a2.2 2.2 0 0 1 0 3.1L30 41.1l-5 1.4 1.4-5 11.2-11.2a2.2 2.2 0 0 1 3.1 0z" stroke="#0EB8DA" fill="#0EB8DA" fill-opacity=".2"/><path d="M37 31l-3.1-3.1" stroke="#0EB8DA"/></svg></span>
<!-- /wp:html -->

<!-- wp:paragraph {"className":"svr-stage__no"} -->
<p class="svr-stage__no"><code>04</code></p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Проектирование</h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-stage__text"} -->
<p class="svr-stage__text">Проектная и&nbsp;рабочая документация.</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-stage","layout":{"type":"default"}} -->
<div class="wp-block-group svr-stage"><!-- wp:html -->
<span class="svr-stage__ico" aria-hidden="true"><svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M12 15h24v17a9 9 0 0 1-9 9h-6a9 9 0 0 1-9-9z"/><path d="M12 15c0-3 5-4.5 12-4.5S36 12 36 15"/><path d="M12 24c3-2 4.5-2 6 0s4.5 2 6 0 4.5-2 6 0 3 1 6 0"/><path d="M20.5 4h7a1.5 1.5 0 0 1 1.5 1.5V9H19V5.5A1.5 1.5 0 0 1 20.5 4z"/><path d="M24 10.5V33" stroke="#0EB8DA"/><path d="M18 33h12" stroke="#0EB8DA"/></svg></span>
<!-- /wp:html -->

<!-- wp:paragraph {"className":"svr-stage__no"} -->
<p class="svr-stage__no"><code>05</code></p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Оборудование</h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-stage__text"} -->
<p class="svr-stage__text">Проектируем и&nbsp;разрабатываем сами. <a href="#produkciya">Смотреть продукцию</a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-stage","layout":{"type":"default"}} -->
<div class="wp-block-group svr-stage"><!-- wp:html -->
<span class="svr-stage__ico" aria-hidden="true"><svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M4 32h8M36 32h8"/><path d="M12 24v16l12-8zM36 24v16l-12-8z"/><path d="M24 32V17" stroke="#0EB8DA"/><path d="M13 13.5c0-1.4 5-2.5 11-2.5s11 1.1 11 2.5-5 2.5-11 2.5-11-1.1-11-2.5z" stroke="#0EB8DA" fill="#0EB8DA" fill-opacity=".2"/></svg></span>
<!-- /wp:html -->

<!-- wp:paragraph {"className":"svr-stage__no"} -->
<p class="svr-stage__no"><code>06</code></p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Пусконаладка</h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-stage__text"} -->
<p class="svr-stage__text">Маркировка оборудования, выявление неисправностей, определение режимов&nbsp;работы.</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group --></section>
<!-- /wp:group -->
```

### 06. Продукция на главной (`svr-products`, `svr-sheets`, `svr-sheet`, `svr-sheet--cta`)

*spec §5.6.* Якорь `produkciya`. Сетка 3×2 (`columnCount:3`): 5 листов + CTA-лист. Лист — рендер, название (H3 `svr-sheet__name` со ссылкой на СВОЮ страницу `https://svr-mos.ru/prod/<slug>/`: `stanciya-dozirovaniya`, `reaktor-trehkamernyj`, `reaktor-odnokamernyj`, `ustanovka-obezzarazhivaniya`, `kns`) и подпись «Подробнее» (`svr-sheet__more`). Ссылка растягивается на весь лист (фокус виден, лист ≥44 px), стрелка ↗ — у листов со ссылкой. Служебных строк («Поз.», «Назначение», «Исполнение») нет. На бумаге — миллиметровка и уголки-метки (один слой). CAD-рендеры только на бумаге (`svr-sheet`). У рендера id 16 (чертёж занимает 43 % высоты прозрачного холста) — штатное кадрирование `core/image`: `"aspectRatio":"4/3","scale":"cover"` (срезаются только пустые поля).

```html
<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec svr-sec\u002d\u002dband svr-mm svr-ruler svr-products","style":{"spacing":{"blockGap":"var:preset|spacing|60"}},"layout":{"type":"constrained"},"anchor":"produkciya"} -->
<section class="wp-block-group alignfull svr-sec svr-sec--band svr-mm svr-ruler svr-products" id="produkciya"><!-- wp:group {"align":"wide","className":"svr-head","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-head"><!-- wp:paragraph {"className":"svr-kicker"} -->
<p class="svr-kicker">Продукция</p>
<!-- /wp:paragraph -->

<!-- wp:columns {"className":"svr-head__row"} -->
<div class="wp-block-columns svr-head__row"><!-- wp:column {"width":"56%"} -->
<div class="wp-block-column" style="flex-basis:56%"><!-- wp:heading -->
<h2 class="wp-block-heading">Мы сами проектируем и&nbsp;разрабатываем оборудование</h2>
<!-- /wp:heading --></div>
<!-- /wp:column -->

<!-- wp:column {"width":"44%"} -->
<div class="wp-block-column" style="flex-basis:44%"><!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Собственное оборудование для&nbsp;очистки сточных вод. Подбор и&nbsp;подробности&nbsp;— по&nbsp;запросу.</p>
<!-- /wp:paragraph -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"svr-btn\u002d\u002dghost"} -->
<div class="wp-block-button svr-btn--ghost"><a class="wp-block-button__link wp-element-button" href="https://svr-mos.ru/prod/">Вся продукция</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group -->

<!-- wp:group {"align":"wide","className":"svr-sheets","layout":{"type":"grid","columnCount":3}} -->
<div class="wp-block-group alignwide svr-sheets"><!-- wp:group {"className":"svr-sheet","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet"><!-- wp:image {"id":13,"sizeSlug":"full","linkDestination":"none","className":"svr-sheet__img"} -->
<figure class="wp-block-image size-full svr-sheet__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-stanciya-dozirovaniya-sdphr.png" alt="Станции дозирования и приготовления реагентов двухкамерные — 3D-модель" class="wp-image-13"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-sheet__tb","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet__tb"><!-- wp:heading {"level":3,"className":"svr-sheet__name"} -->
<h3 class="wp-block-heading svr-sheet__name"><a href="https://svr-mos.ru/prod/stanciya-dozirovaniya/">Станции дозирования и&nbsp;приготовления реагентов двухкамерные</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-sheet__more"} -->
<p class="svr-sheet__more">Подробнее</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-sheet","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet"><!-- wp:image {"id":14,"sizeSlug":"full","linkDestination":"none","className":"svr-sheet__img"} -->
<figure class="wp-block-image size-full svr-sheet__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-reaktor-trehkamernyj.png" alt="Реактор трёхкамерный — 3D-модель" class="wp-image-14"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-sheet__tb","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet__tb"><!-- wp:heading {"level":3,"className":"svr-sheet__name"} -->
<h3 class="wp-block-heading svr-sheet__name"><a href="https://svr-mos.ru/prod/reaktor-trehkamernyj/">Реактор трёхкамерный</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-sheet__more"} -->
<p class="svr-sheet__more">Подробнее</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-sheet","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet"><!-- wp:image {"id":15,"sizeSlug":"full","linkDestination":"none","className":"svr-sheet__img"} -->
<figure class="wp-block-image size-full svr-sheet__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-reaktor-odnokamernyj.png" alt="Реактор однокамерный — 3D-модель" class="wp-image-15"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-sheet__tb","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet__tb"><!-- wp:heading {"level":3,"className":"svr-sheet__name"} -->
<h3 class="wp-block-heading svr-sheet__name"><a href="https://svr-mos.ru/prod/reaktor-odnokamernyj/">Реактор однокамерный</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-sheet__more"} -->
<p class="svr-sheet__more">Подробнее</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-sheet","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet"><!-- wp:image {"id":16,"aspectRatio":"4/3","scale":"cover","sizeSlug":"full","linkDestination":"none","className":"svr-sheet__img"} -->
<figure class="wp-block-image size-full svr-sheet__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-ustanovka-obezzarazhivaniya-uko.png" alt="Установка комплексного обеззараживания сточных вод — 3D-модель" class="wp-image-16" style="aspect-ratio:4/3;object-fit:cover"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-sheet__tb","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet__tb"><!-- wp:heading {"level":3,"className":"svr-sheet__name"} -->
<h3 class="wp-block-heading svr-sheet__name"><a href="https://svr-mos.ru/prod/ustanovka-obezzarazhivaniya/">Установка комплексного обеззараживания сточных вод</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-sheet__more"} -->
<p class="svr-sheet__more">Подробнее</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-sheet","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet"><!-- wp:image {"id":17,"sizeSlug":"full","linkDestination":"none","className":"svr-sheet__img"} -->
<figure class="wp-block-image size-full svr-sheet__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-kns.png" alt="Канализационные насосные станции — 3D-модель" class="wp-image-17"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-sheet__tb","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet__tb"><!-- wp:heading {"level":3,"className":"svr-sheet__name"} -->
<h3 class="wp-block-heading svr-sheet__name"><a href="https://svr-mos.ru/prod/kns/">Канализационные насосные станции</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-sheet__more"} -->
<p class="svr-sheet__more">Подробнее</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-sheet svr-sheet\u002d\u002dcta","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet svr-sheet--cta"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">По запросу</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3,"className":"svr-sheet__name"} -->
<h3 class="wp-block-heading svr-sheet__name">Подбор оборудования под&nbsp;ваш объект</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Подробности по&nbsp;каждой позиции&nbsp;— по&nbsp;запросу.</p>
<!-- /wp:paragraph -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"svr-ic-tel"} -->
<div class="wp-block-button svr-ic-tel"><a class="wp-block-button__link wp-element-button" href="tel:+79652808090">Позвонить</a></div>
<!-- /wp:button -->

<!-- wp:button {"className":"is-style-outline svr-ic-mail"} -->
<div class="wp-block-button is-style-outline svr-ic-mail"><a class="wp-block-button__link wp-element-button" href="mailto:info@svr-mos.ru">Написать</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:group --></div>
<!-- /wp:group --></section>
<!-- /wp:group -->
```

### 07. Листы продукции для /prod/ (`svr-sheets--page`)

*spec §7.4.* Как на главной, но: якоря `poz-01…poz-05` на листах (сохранены для старых ссылок), у изображений нет lightbox (весь лист — ссылка на страницу продукции; увеличение — на странице продукции), рендер до 300 px; id 16 — `"aspectRatio":"1","scale":"cover"` (высота рамки как у соседних листов). На ≤781 px листы /prod/ вертикальные (крупный рендер), на 600–781 px — 2 колонки. Вставляется в секцию `svr-sec svr-sec--band svr-mm svr-products` (см. рецепт /prod/).

```html
<!-- wp:group {"align":"wide","className":"svr-sheets svr-sheets\u002d\u002dpage","layout":{"type":"grid","columnCount":3}} -->
<div class="wp-block-group alignwide svr-sheets svr-sheets--page"><!-- wp:group {"className":"svr-sheet","layout":{"type":"default"},"anchor":"poz-01"} -->
<div id="poz-01" class="wp-block-group svr-sheet"><!-- wp:image {"id":13,"sizeSlug":"full","linkDestination":"none","className":"svr-sheet__img"} -->
<figure class="wp-block-image size-full svr-sheet__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-stanciya-dozirovaniya-sdphr.png" alt="Станции дозирования и приготовления реагентов двухкамерные — 3D-модель" class="wp-image-13"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-sheet__tb","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet__tb"><!-- wp:heading {"level":3,"className":"svr-sheet__name"} -->
<h3 class="wp-block-heading svr-sheet__name"><a href="https://svr-mos.ru/prod/stanciya-dozirovaniya/">Станции дозирования и&nbsp;приготовления реагентов двухкамерные</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-sheet__more"} -->
<p class="svr-sheet__more">Подробнее</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-sheet","layout":{"type":"default"},"anchor":"poz-02"} -->
<div id="poz-02" class="wp-block-group svr-sheet"><!-- wp:image {"id":14,"sizeSlug":"full","linkDestination":"none","className":"svr-sheet__img"} -->
<figure class="wp-block-image size-full svr-sheet__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-reaktor-trehkamernyj.png" alt="Реактор трёхкамерный — 3D-модель" class="wp-image-14"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-sheet__tb","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet__tb"><!-- wp:heading {"level":3,"className":"svr-sheet__name"} -->
<h3 class="wp-block-heading svr-sheet__name"><a href="https://svr-mos.ru/prod/reaktor-trehkamernyj/">Реактор трёхкамерный</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-sheet__more"} -->
<p class="svr-sheet__more">Подробнее</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-sheet","layout":{"type":"default"},"anchor":"poz-03"} -->
<div id="poz-03" class="wp-block-group svr-sheet"><!-- wp:image {"id":15,"sizeSlug":"full","linkDestination":"none","className":"svr-sheet__img"} -->
<figure class="wp-block-image size-full svr-sheet__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-reaktor-odnokamernyj.png" alt="Реактор однокамерный — 3D-модель" class="wp-image-15"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-sheet__tb","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet__tb"><!-- wp:heading {"level":3,"className":"svr-sheet__name"} -->
<h3 class="wp-block-heading svr-sheet__name"><a href="https://svr-mos.ru/prod/reaktor-odnokamernyj/">Реактор однокамерный</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-sheet__more"} -->
<p class="svr-sheet__more">Подробнее</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-sheet","layout":{"type":"default"},"anchor":"poz-04"} -->
<div id="poz-04" class="wp-block-group svr-sheet"><!-- wp:image {"id":16,"aspectRatio":"1","scale":"cover","sizeSlug":"full","linkDestination":"none","className":"svr-sheet__img"} -->
<figure class="wp-block-image size-full svr-sheet__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-ustanovka-obezzarazhivaniya-uko.png" alt="Установка комплексного обеззараживания сточных вод — 3D-модель" class="wp-image-16" style="aspect-ratio:1;object-fit:cover"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-sheet__tb","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet__tb"><!-- wp:heading {"level":3,"className":"svr-sheet__name"} -->
<h3 class="wp-block-heading svr-sheet__name"><a href="https://svr-mos.ru/prod/ustanovka-obezzarazhivaniya/">Установка комплексного обеззараживания сточных вод</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-sheet__more"} -->
<p class="svr-sheet__more">Подробнее</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-sheet","layout":{"type":"default"},"anchor":"poz-05"} -->
<div id="poz-05" class="wp-block-group svr-sheet"><!-- wp:image {"id":17,"sizeSlug":"full","linkDestination":"none","className":"svr-sheet__img"} -->
<figure class="wp-block-image size-full svr-sheet__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-kns.png" alt="Канализационные насосные станции — 3D-модель" class="wp-image-17"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-sheet__tb","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet__tb"><!-- wp:heading {"level":3,"className":"svr-sheet__name"} -->
<h3 class="wp-block-heading svr-sheet__name"><a href="https://svr-mos.ru/prod/kns/">Канализационные насосные станции</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-sheet__more"} -->
<p class="svr-sheet__more">Подробнее</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-sheet svr-sheet\u002d\u002dcta","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet svr-sheet--cta"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">По запросу</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3,"className":"svr-sheet__name"} -->
<h3 class="wp-block-heading svr-sheet__name">Подбор оборудования под&nbsp;ваш объект</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Подробности по&nbsp;каждой позиции&nbsp;— по&nbsp;запросу.</p>
<!-- /wp:paragraph -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"svr-ic-tel"} -->
<div class="wp-block-button svr-ic-tel"><a class="wp-block-button__link wp-element-button" href="tel:+79652808090">Позвонить</a></div>
<!-- /wp:button -->

<!-- wp:button {"className":"is-style-outline svr-ic-mail"} -->
<div class="wp-block-button is-style-outline svr-ic-mail"><a class="wp-block-button__link wp-element-button" href="mailto:info@svr-mos.ru">Написать</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->
```

### 08. Объекты на главной (`svr-objs`, `svr-obj`, `svr-chips`)

*spec §5.7.* Якорь `obekty`. Сетка 2×2, без кикера. Фото без подписи-плашки. Фото в родной пропорции 740/354, без апскейла. H3 со ссылкой на страницу объекта (растягивается на карточку). Чипы — только выполненные этапы, без номеров (51, 52: Обследование, Лаборатория, Технологические решения, Проектирование; 53, 54: Обследование, Лаборатория, Пусконаладка).

```html
<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec svr-ruler","style":{"spacing":{"blockGap":"var:preset|spacing|60"}},"layout":{"type":"constrained"},"anchor":"obekty"} -->
<section class="wp-block-group alignfull svr-sec svr-ruler" id="obekty"><!-- wp:group {"align":"wide","className":"svr-head","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-head"><!-- wp:columns {"className":"svr-head__row"} -->
<div class="wp-block-columns svr-head__row"><!-- wp:column {"width":"56%"} -->
<div class="wp-block-column" style="flex-basis:56%"><!-- wp:heading -->
<h2 class="wp-block-heading">Наши объекты</h2>
<!-- /wp:heading --></div>
<!-- /wp:column -->

<!-- wp:column {"width":"44%"} -->
<div class="wp-block-column" style="flex-basis:44%"><!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Гальваническое производство, мясокомбинат, очистные сооружения ливневой канализации&nbsp;— и&nbsp;состав работ на&nbsp;каждом объекте.</p>
<!-- /wp:paragraph -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"svr-btn\u002d\u002dghost"} -->
<div class="wp-block-button svr-btn--ghost"><a class="wp-block-button__link wp-element-button" href="https://svr-mos.ru/obj/">Все объекты</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group -->

<!-- wp:group {"align":"wide","className":"svr-objs","layout":{"type":"grid","columnCount":2}} -->
<div class="wp-block-group alignwide svr-objs"><!-- wp:group {"className":"svr-obj","layout":{"type":"default"}} -->
<div class="wp-block-group svr-obj"><!-- wp:image {"id":20,"sizeSlug":"full","linkDestination":"none","className":"svr-obj__img"} -->
<figure class="wp-block-image size-full svr-obj__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-elteza-3.png" alt="ОАО «Элтеза»: ёмкости и оборудование очистных сооружений (коллаж)" class="wp-image-20"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-obj__body","layout":{"type":"default"}} -->
<div class="wp-block-group svr-obj__body"><!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading"><a href="https://svr-mos.ru/elteza/">ОАО&nbsp;«Элтеза»</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-obj__desc"} -->
<p class="svr-obj__desc">Сточные воды гальванического производства.</p>
<!-- /wp:paragraph -->

<!-- wp:list {"className":"svr-chips"} -->
<ul class="wp-block-list svr-chips"><!-- wp:list-item -->
<li>Обследование</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Лаборатория</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Технологические решения</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Проектирование</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-obj","layout":{"type":"default"}} -->
<div class="wp-block-group svr-obj"><!-- wp:image {"id":26,"sizeSlug":"full","linkDestination":"none","className":"svr-obj__img"} -->
<figure class="wp-block-image size-full svr-obj__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-ruzskii-1.png" alt="ОАО «Мясокомбинат «Рузский»: помещения и площадка (коллаж)" class="wp-image-26"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-obj__body","layout":{"type":"default"}} -->
<div class="wp-block-group svr-obj__body"><!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading"><a href="https://svr-mos.ru/russkii/">ОАО&nbsp;«Мясокомбинат «Рузский»</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-obj__desc"} -->
<p class="svr-obj__desc">Проект очистных сооружений и&nbsp;сетей ливневой канализации.</p>
<!-- /wp:paragraph -->

<!-- wp:list {"className":"svr-chips"} -->
<ul class="wp-block-list svr-chips"><!-- wp:list-item -->
<li>Обследование</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Лаборатория</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Технологические решения</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Проектирование</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-obj","layout":{"type":"default"}} -->
<div class="wp-block-group svr-obj"><!-- wp:image {"id":34,"sizeSlug":"full","linkDestination":"none","className":"svr-obj__img"} -->
<figure class="wp-block-image size-full svr-obj__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-os3-marino-1.jpg" alt="ОС3 Марьино-Саларьево: напорный фильтр с манометрами" class="wp-image-34"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-obj__body","layout":{"type":"default"}} -->
<div class="wp-block-group svr-obj__body"><!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading"><a href="https://svr-mos.ru/os3-marino/">ОС3 Марьино-Саларьево (II&nbsp;этап)</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-obj__desc"} -->
<p class="svr-obj__desc">Пусконаладочные работы очистных сооружений ливневой канализации.</p>
<!-- /wp:paragraph -->

<!-- wp:list {"className":"svr-chips"} -->
<ul class="wp-block-list svr-chips"><!-- wp:list-item -->
<li>Обследование</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Лаборатория</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Пусконаладка</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-obj","layout":{"type":"default"}} -->
<div class="wp-block-group svr-obj"><!-- wp:image {"id":45,"sizeSlug":"full","linkDestination":"none","className":"svr-obj__img"} -->
<figure class="wp-block-image size-full svr-obj__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-os2-marino-5.jpg" alt="ОС2 Марьино-Саларьево: напорные фильтры с маркировкой арматуры" class="wp-image-45"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-obj__body","layout":{"type":"default"}} -->
<div class="wp-block-group svr-obj__body"><!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading"><a href="https://svr-mos.ru/os2-marino/">ОС2 Марьино-Саларьево (II&nbsp;этап)</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-obj__desc"} -->
<p class="svr-obj__desc">Пусконаладочные работы очистных сооружений ливневой канализации.</p>
<!-- /wp:paragraph -->

<!-- wp:list {"className":"svr-chips"} -->
<ul class="wp-block-list svr-chips"><!-- wp:list-item -->
<li>Обследование</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Лаборатория</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Пусконаладка</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list --></div>
<!-- /wp:group --></div>
<!-- /wp:group --></div>
<!-- /wp:group --></section>
<!-- /wp:group -->
```

### 09. Документы и реквизиты на главной (`svr-docs-grid`, `svr-card`, `svr-card--doc`, `svr-req--mini`)

*spec §5.10.* Якорь `dokumenty`. Превью id 12 → PDF id 11 (новая вкладка). Числа реквизитов — формат «Код».

```html
<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec svr-sec\u002d\u002dtight","style":{"spacing":{"blockGap":"var:preset|spacing|50"}},"layout":{"type":"constrained"},"anchor":"dokumenty"} -->
<section class="wp-block-group alignfull svr-sec svr-sec--tight" id="dokumenty"><!-- wp:group {"align":"wide","className":"svr-head","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-head"><!-- wp:heading -->
<h2 class="wp-block-heading">Документы и&nbsp;реквизиты</h2>
<!-- /wp:heading --></div>
<!-- /wp:group -->

<!-- wp:columns {"align":"wide","className":"svr-docs-grid"} -->
<div class="wp-block-columns alignwide svr-docs-grid"><!-- wp:column {"width":"50%"} -->
<div class="wp-block-column" style="flex-basis:50%"><!-- wp:group {"className":"svr-card svr-card\u002d\u002ddoc","layout":{"type":"default"}} -->
<div class="wp-block-group svr-card svr-card--doc"><!-- wp:columns {"verticalAlignment":"top"} -->
<div class="wp-block-columns are-vertically-aligned-top"><!-- wp:column {"width":"180px"} -->
<div class="wp-block-column" style="flex-basis:180px"><!-- wp:image {"id":12,"sizeSlug":"full","linkDestination":"custom","className":"svr-doc-sheet"} -->
<figure class="wp-block-image size-full svr-doc-sheet"><a href="https://svr-mos.ru/wp-content/uploads/2026/10/svr-deklaraciya-eac.pdf" target="_blank" rel="noreferrer noopener"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-deklaraciya-eac-preview.jpg" alt="Декларация о соответствии ЕАЭС — открыть PDF" class="wp-image-12"/></a></figure>
<!-- /wp:image --></div>
<!-- /wp:column -->

<!-- wp:column -->
<div class="wp-block-column"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Документ · PDF</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Декларация о&nbsp;соответствии&nbsp;ЕАЭС</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Документ доступен для&nbsp;просмотра и&nbsp;скачивания.</p>
<!-- /wp:paragraph -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"is-style-outline svr-ic-doc"} -->
<div class="wp-block-button is-style-outline svr-ic-doc"><a class="wp-block-button__link wp-element-button" href="https://svr-mos.ru/wp-content/uploads/2026/10/svr-deklaraciya-eac.pdf" target="_blank" rel="noreferrer noopener">Открыть PDF</a></div>
<!-- /wp:button -->

<!-- wp:button {"className":"svr-btn\u002d\u002dghost"} -->
<div class="wp-block-button svr-btn--ghost"><a class="wp-block-button__link wp-element-button" href="https://svr-mos.ru/docs/">Все документы</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group --></div>
<!-- /wp:column -->

<!-- wp:column {"width":"50%"} -->
<div class="wp-block-column" style="flex-basis:50%"><!-- wp:group {"className":"svr-card","layout":{"type":"default"}} -->
<div class="wp-block-group svr-card"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Реквизиты</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">ООО&nbsp;«Сервис водных ресурсов»</h3>
<!-- /wp:heading -->

<!-- wp:table {"hasFixedLayout":false,"className":"svr-req svr-req\u002d\u002dmini"} -->
<figure class="wp-block-table svr-req svr-req--mini"><table><tbody><tr><th scope="row">ИНН</th><td><code>7716962072</code></td></tr><tr><th scope="row">КПП</th><td><code>771601001</code></td></tr><tr><th scope="row">Банк</th><td>АО&nbsp;«Райффайзенбанк»</td></tr><tr><th scope="row">БИК</th><td><code>044525700</code></td></tr></tbody></table></figure>
<!-- /wp:table -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"svr-btn\u002d\u002dghost"} -->
<div class="wp-block-button svr-btn--ghost"><a class="wp-block-button__link wp-element-button" href="https://svr-mos.ru/rekvizit/">Все реквизиты</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:group --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></section>
<!-- /wp:group -->
```

### 10. Финальный CTA и штамп контактов (`svr-cta`, `svr-contacts`, `svr-phone`, `svr-mail`)

*spec §5.11.* Якорь `kontakty`. Display-заголовок `fontSize:"display"`, «чище» — подсветка. Капля — `core/html` с `cta-drop.svg` (меньшая капля-резервуар: вход слева сверху с подписью «Сточные воды», выход справа снизу с подписью «Чистая вода», задвижки, стрелки, бегущий пунктир; id `svrCta*`, на странице не более одного раза; ≤1023 px скрыта). Телефон — `fontSize:"phone"`.

```html
<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec svr-sec\u002d\u002dloose svr-mm svr-ruler svr-cta","style":{"spacing":{"blockGap":"var:preset|spacing|60"}},"layout":{"type":"constrained"},"anchor":"kontakty"} -->
<section class="wp-block-group alignfull svr-sec svr-sec--loose svr-mm svr-ruler svr-cta" id="kontakty"><!-- wp:group {"align":"wide","className":"svr-head","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-head"><!-- wp:paragraph {"className":"svr-kicker"} -->
<p class="svr-kicker">Контакты</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:columns {"align":"wide","className":"svr-cta__grid"} -->
<div class="wp-block-columns alignwide svr-cta__grid"><!-- wp:column {"width":"60%"} -->
<div class="wp-block-column" style="flex-basis:60%"><!-- wp:heading {"className":"svr-cta__title","fontSize":"display"} -->
<h2 class="wp-block-heading svr-cta__title has-display-font-size">Мы делаем мир <mark style="background-color:rgba(0,0,0,0)" class="has-inline-color has-accent-1-color">чище</mark></h2>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Расскажите о&nbsp;задаче на&nbsp;вашем объекте&nbsp;— позвоните или напишите. Подбор оборудования и&nbsp;подробности&nbsp;— по&nbsp;запросу.</p>
<!-- /wp:paragraph --></div>
<!-- /wp:column -->

<!-- wp:column {"width":"40%","className":"svr-cta__dwg"} -->
<div class="wp-block-column svr-cta__dwg" style="flex-basis:40%"><!-- wp:html -->
<svg class="svr-dwg" viewBox="0 0 440 456" fill="none" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg">
<defs>
<clipPath id="svrCtaIn"><path d="M220 120.22 L292.38 228.72 A87 87 0 1 1 147.62 228.72 Z"/></clipPath>
<pattern id="svrCtaHatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" stroke="#0EB8DA" stroke-opacity=".5"/></pattern>
<mask id="svrCtaWall"><path d="M220 104 L299.86 223.73 A96 96 0 1 1 140.14 223.73 Z" fill="#fff"/><path d="M220 120.22 L292.38 228.72 A87 87 0 1 1 147.62 228.72 Z" fill="#000"/></mask>
<linearGradient id="svrCtaWater" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0EB8DA" stop-opacity=".42"/><stop offset="1" stop-color="#0089BF" stop-opacity=".08"/></linearGradient>
<radialGradient id="svrCtaGlow"><stop offset="0" stop-color="#0EB8DA" stop-opacity="0.18"/><stop offset="1" stop-color="#0EB8DA" stop-opacity="0"/></radialGradient>
</defs>
<circle cx="220" cy="277" r="163.2" fill="url(#svrCtaGlow)"/>
<circle cx="220" cy="281" r="109.44" fill="none" stroke="#0EB8DA" stroke-opacity=".3" stroke-dasharray="3 6"/>
<g clip-path="url(#svrCtaIn)">
<rect x="124" y="104" width="192" height="269" fill="#0B2540" fill-opacity=".55"/>
<path fill="url(#svrCtaWater)" opacity=".55" d="M-200 246q30-7 60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0V393H-200Z"/>
<g><path fill="url(#svrCtaWater)" d="M-200 254q30-8 60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0V393H-200Z"/></g>
</g>
<rect x="112" y="92" width="216" height="293" fill="url(#svrCtaHatch)" mask="url(#svrCtaWall)"/>
<path d="M220 104 L299.86 223.73 A96 96 0 1 1 140.14 223.73 Z" fill="none" stroke="#0EB8DA" stroke-width="2" stroke-linejoin="round"/>
<path d="M220 120.22 L292.38 228.72 A87 87 0 1 1 147.62 228.72 Z" fill="none" stroke="#0EB8DA" stroke-opacity=".7" stroke-linejoin="round"/>
<path d="M158.87 292.24A63 63 0 0 0 186.62 330.43" fill="none" stroke="#E8F1F8" stroke-opacity=".28" stroke-width="3" stroke-linecap="round"/>
<path d="M16 74H220V104" fill="none" stroke="#0EB8DA" stroke-width="2"/>
<path class="svr-dwg-flow" d="M16 74H220V104" fill="none" stroke="#E8F1F8" stroke-width="2" stroke-dasharray="6 10"/>
<g stroke="#0EB8DA" stroke-width="1.5"><path d="M61.12 66L85.12 82V66L61.12 82Z" fill="#071B2F" stroke-linejoin="round"/><path d="M73.12 66V48M65.12 48H81.12" fill="none"/></g>
<path d="M150.64 67l14 7-14 7z" fill="#0EB8DA"/>
<text class="svr-dwg-t" x="16" y="28">Сточные воды</text>
<path d="M220 373V410H424" fill="none" stroke="#0EB8DA" stroke-width="2"/>
<path class="svr-dwg-flow" d="M220 373V410H424" fill="none" stroke="#E8F1F8" stroke-width="2" stroke-dasharray="6 10"/>
<path d="M424 400V420" stroke="#0EB8DA" stroke-width="2"/>
<g stroke="#0EB8DA" stroke-width="1.5"><path d="M299.8 402L323.8 418V402L299.8 418Z" fill="#071B2F" stroke-linejoin="round"/><path d="M311.8 402V384M303.8 384H319.8" fill="none"/></g>
<path d="M383.2 403l14 7-14 7z" fill="#0EB8DA"/>
<text class="svr-dwg-t" x="424" y="442" text-anchor="end">Чистая вода</text>
</svg>
<!-- /wp:html --></div>
<!-- /wp:column --></div>
<!-- /wp:columns -->

<!-- wp:group {"align":"wide","className":"svr-contacts","layout":{"type":"grid","columnCount":3}} -->
<div class="wp-block-group alignwide svr-contacts"><!-- wp:group {"className":"svr-contacts__cell svr-contacts__cell\u002d\u002dwide","layout":{"type":"default"}} -->
<div class="wp-block-group svr-contacts__cell svr-contacts__cell--wide"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Телефон</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"svr-phone","fontSize":"phone"} -->
<p class="svr-phone has-phone-font-size"><a href="tel:+79652808090">8 965 280-80-90</a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-contacts__cell","layout":{"type":"default"}} -->
<div class="wp-block-group svr-contacts__cell"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Почта</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"svr-mail"} -->
<p class="svr-mail"><a href="mailto:info@svr-mos.ru">info@svr-mos.ru</a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-contacts__cell","layout":{"type":"default"}} -->
<div class="wp-block-group svr-contacts__cell"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Офис</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Москва, Ярославское шоссе, д.&nbsp;42, оф.&nbsp;603</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-contacts__cell","layout":{"type":"default"}} -->
<div class="wp-block-group svr-contacts__cell"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Метро</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>«ВДНХ», «Ботанический сад»</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-contacts__cell","layout":{"type":"default"}} -->
<div class="wp-block-group svr-contacts__cell"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Режим работы</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Пн—Пт 10:00—18:00</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"svr-meta","fontSize":"small"} -->
<p class="svr-meta has-small-font-size">Сб—Вс выходные</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group --></section>
<!-- /wp:group -->
```

### 11. Штамп контактов отдельно (`svr-contacts`, 5 ячеек — как в финальном CTA главной)

*spec §5.11.* Сетка 3 колонки (телефон на 2), 600–1023 px — 2, ≤599 px — 1. На /contact/ используется вариант «каналы связи» (телефон, почта, режим работы — фрагмент 18): адрес и метро там даёт «Как добраться», чтобы данные не повторялись.

```html
<!-- wp:group {"align":"wide","className":"svr-contacts","layout":{"type":"grid","columnCount":3}} -->
<div class="wp-block-group alignwide svr-contacts"><!-- wp:group {"className":"svr-contacts__cell svr-contacts__cell\u002d\u002dwide","layout":{"type":"default"}} -->
<div class="wp-block-group svr-contacts__cell svr-contacts__cell--wide"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Телефон</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"svr-phone","fontSize":"phone"} -->
<p class="svr-phone has-phone-font-size"><a href="tel:+79652808090">8 965 280-80-90</a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-contacts__cell","layout":{"type":"default"}} -->
<div class="wp-block-group svr-contacts__cell"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Почта</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"svr-mail"} -->
<p class="svr-mail"><a href="mailto:info@svr-mos.ru">info@svr-mos.ru</a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-contacts__cell","layout":{"type":"default"}} -->
<div class="wp-block-group svr-contacts__cell"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Офис</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Москва, Ярославское шоссе, д.&nbsp;42, оф.&nbsp;603</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-contacts__cell","layout":{"type":"default"}} -->
<div class="wp-block-group svr-contacts__cell"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Метро</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>«ВДНХ», «Ботанический сад»</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-contacts__cell","layout":{"type":"default"}} -->
<div class="wp-block-group svr-contacts__cell"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Режим работы</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Пн—Пт 10:00—18:00</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"svr-meta","fontSize":"small"} -->
<p class="svr-meta has-small-font-size">Сб—Вс выходные</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->
```

### 12. Вступление внутренней страницы (`svr-page-intro`)

*spec §7.* Первый блок контента внутренних страниц (H1 даёт шаблон `page`). Группа `align:"wide"`. Лид — `svr-lead`. Для /prod/ внутри может быть H2.

```html
<!-- wp:group {"align":"wide","className":"svr-page-intro","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-page-intro"><!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Документы ООО&nbsp;«СВР» для&nbsp;просмотра и&nbsp;скачивания.</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->
```

### 13. Объекты строками для /obj/ (`svr-obj--row`) и ведомость (`svr-matrix`)

*spec §7.2, §5.9.* Строки: `core/columns` 50/50 (фото | текст), каждая вторая зеркально на ≥1024 px; фото «липнет» при прокрутке. Фото без подписи-плашки: тип объекта — в метке `svr-label` над H2. H2 со ссылкой, задача, чипы, `svr-works`, ghost «Подробнее об объекте». Ведомость: `core/table` с `<th scope="col">` в шапке и `<th scope="row">` в строках, значения `<strong>Да</strong>` / `<em>Нет</em>` (визуально точка/тире, текст остаётся для скринридеров), легенда — подпись таблицы. На ≤599 px таблица прокручивается внутри, первая колонка липкая.

```html
<!-- wp:group {"align":"wide","className":"svr-page-intro","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-page-intro"><!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Гальваническое производство, мясокомбинат, очистные сооружения ливневой канализации&nbsp;— состав работ на&nbsp;каждом объекте.</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec","style":{"spacing":{"blockGap":"var:preset|spacing|60"}},"layout":{"type":"constrained"}} -->
<section class="wp-block-group alignfull svr-sec"><!-- wp:group {"align":"wide","className":"svr-objs-list","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-objs-list"><!-- wp:group {"className":"svr-obj svr-obj\u002d\u002drow","layout":{"type":"default"}} -->
<div class="wp-block-group svr-obj svr-obj--row"><!-- wp:columns -->
<div class="wp-block-columns"><!-- wp:column {"width":"50%"} -->
<div class="wp-block-column" style="flex-basis:50%"><!-- wp:image {"id":20,"sizeSlug":"full","linkDestination":"none","className":"svr-obj__img"} -->
<figure class="wp-block-image size-full svr-obj__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-elteza-3.png" alt="ОАО «Элтеза»: ёмкости и оборудование очистных сооружений (коллаж)" class="wp-image-20"/></figure>
<!-- /wp:image --></div>
<!-- /wp:column -->

<!-- wp:column {"width":"50%"} -->
<div class="wp-block-column" style="flex-basis:50%"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Гальваническое производство</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading"><a href="https://svr-mos.ru/elteza/">ОАО «Элтеза»</a></h2>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Сточные воды гальванического производства.</p>
<!-- /wp:paragraph -->

<!-- wp:list {"className":"svr-chips"} -->
<ul class="wp-block-list svr-chips"><!-- wp:list-item -->
<li>Обследование</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Лаборатория</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Технологические решения</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Проектирование</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:list {"className":"svr-works"} -->
<ul class="wp-block-list svr-works"><!-- wp:list-item -->
<li>Обследование действующих сооружений</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Отбор проб сточных вод гальванического производства</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Проведение лабораторных испытаний</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Определение показателей сточных вод</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Определение оптимальных технологических решений</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Разработка проектной документации</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Разработка рабочей документации</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"svr-btn\u002d\u002dghost"} -->
<div class="wp-block-button svr-btn--ghost"><a class="wp-block-button__link wp-element-button" href="https://svr-mos.ru/elteza/">Подробнее об объекте</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-obj svr-obj\u002d\u002drow","layout":{"type":"default"}} -->
<div class="wp-block-group svr-obj svr-obj--row"><!-- wp:columns -->
<div class="wp-block-columns"><!-- wp:column {"width":"50%"} -->
<div class="wp-block-column" style="flex-basis:50%"><!-- wp:image {"id":26,"sizeSlug":"full","linkDestination":"none","className":"svr-obj__img"} -->
<figure class="wp-block-image size-full svr-obj__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-ruzskii-1.png" alt="ОАО «Мясокомбинат «Рузский»: помещения и площадка (коллаж)" class="wp-image-26"/></figure>
<!-- /wp:image --></div>
<!-- /wp:column -->

<!-- wp:column {"width":"50%"} -->
<div class="wp-block-column" style="flex-basis:50%"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Мясокомбинат</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading"><a href="https://svr-mos.ru/russkii/">ОАО «Мясокомбинат «Рузский»</a></h2>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Проект очистных сооружений и&nbsp;сетей ливневой канализации.</p>
<!-- /wp:paragraph -->

<!-- wp:list {"className":"svr-chips"} -->
<ul class="wp-block-list svr-chips"><!-- wp:list-item -->
<li>Обследование</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Лаборатория</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Технологические решения</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Проектирование</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:list {"className":"svr-works"} -->
<ul class="wp-block-list svr-works"><!-- wp:list-item -->
<li>Инженерные изыскания</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Обследование действующих сооружений</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Отбор проб сточных вод цеха обработки</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Определение показателей сточных вод</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Проведение лабораторных испытаний</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Определение оптимальных технологических решений</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Разработка рабочей документации</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"svr-btn\u002d\u002dghost"} -->
<div class="wp-block-button svr-btn--ghost"><a class="wp-block-button__link wp-element-button" href="https://svr-mos.ru/russkii/">Подробнее об объекте</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-obj svr-obj\u002d\u002drow","layout":{"type":"default"}} -->
<div class="wp-block-group svr-obj svr-obj--row"><!-- wp:columns -->
<div class="wp-block-columns"><!-- wp:column {"width":"50%"} -->
<div class="wp-block-column" style="flex-basis:50%"><!-- wp:image {"id":34,"sizeSlug":"full","linkDestination":"none","className":"svr-obj__img"} -->
<figure class="wp-block-image size-full svr-obj__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-os3-marino-1.jpg" alt="ОС3 Марьино-Саларьево: напорный фильтр с манометрами" class="wp-image-34"/></figure>
<!-- /wp:image --></div>
<!-- /wp:column -->

<!-- wp:column {"width":"50%"} -->
<div class="wp-block-column" style="flex-basis:50%"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Ливневые очистные сооружения</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading"><a href="https://svr-mos.ru/os3-marino/">ОС3 Марьино-Саларьево (II&nbsp;этап)</a></h2>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Пусконаладочные работы очистных сооружений ливневой канализации.</p>
<!-- /wp:paragraph -->

<!-- wp:list {"className":"svr-chips"} -->
<ul class="wp-block-list svr-chips"><!-- wp:list-item -->
<li>Обследование</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Лаборатория</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Пусконаладка</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:list {"className":"svr-works"} -->
<ul class="wp-block-list svr-works"><!-- wp:list-item -->
<li>Обследование построенных сооружений</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Отбор проб сточных вод ливневой канализации</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Проведение лабораторных испытаний</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Определение показателей сточных вод</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Маркировка оборудования</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Выявление неисправностей</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Определение режимов работы</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"svr-btn\u002d\u002dghost"} -->
<div class="wp-block-button svr-btn--ghost"><a class="wp-block-button__link wp-element-button" href="https://svr-mos.ru/os3-marino/">Подробнее об объекте</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-obj svr-obj\u002d\u002drow","layout":{"type":"default"}} -->
<div class="wp-block-group svr-obj svr-obj--row"><!-- wp:columns -->
<div class="wp-block-columns"><!-- wp:column {"width":"50%"} -->
<div class="wp-block-column" style="flex-basis:50%"><!-- wp:image {"id":45,"sizeSlug":"full","linkDestination":"none","className":"svr-obj__img"} -->
<figure class="wp-block-image size-full svr-obj__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-os2-marino-5.jpg" alt="ОС2 Марьино-Саларьево: напорные фильтры с маркировкой арматуры" class="wp-image-45"/></figure>
<!-- /wp:image --></div>
<!-- /wp:column -->

<!-- wp:column {"width":"50%"} -->
<div class="wp-block-column" style="flex-basis:50%"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Ливневые очистные сооружения</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading"><a href="https://svr-mos.ru/os2-marino/">ОС2 Марьино-Саларьево (II&nbsp;этап)</a></h2>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Пусконаладочные работы очистных сооружений ливневой канализации.</p>
<!-- /wp:paragraph -->

<!-- wp:list {"className":"svr-chips"} -->
<ul class="wp-block-list svr-chips"><!-- wp:list-item -->
<li>Обследование</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Лаборатория</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Пусконаладка</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:list {"className":"svr-works"} -->
<ul class="wp-block-list svr-works"><!-- wp:list-item -->
<li>Обследование построенных сооружений</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Отбор проб сточных вод ливневой канализации</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Проведение лабораторных испытаний</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Определение показателей сточных вод</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Маркировка оборудования</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Выявление неисправностей</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Определение режимов работы</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"svr-btn\u002d\u002dghost"} -->
<div class="wp-block-button svr-btn--ghost"><a class="wp-block-button__link wp-element-button" href="https://svr-mos.ru/os2-marino/">Подробнее об объекте</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group --></div>
<!-- /wp:group --></section>
<!-- /wp:group -->

<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec svr-sec\u002d\u002dband svr-ruler","style":{"spacing":{"blockGap":"var:preset|spacing|40"}},"layout":{"type":"constrained"}} -->
<section class="wp-block-group alignfull svr-sec svr-sec--band svr-ruler"><!-- wp:group {"align":"wide","className":"svr-head","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-head"><!-- wp:heading -->
<h2 class="wp-block-heading">Ведомость работ по&nbsp;объектам</h2>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-meta","fontSize":"small"} -->
<p class="svr-meta has-small-font-size">12&nbsp;видов работ&nbsp;× 4&nbsp;объекта</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"align":"wide","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide"><!-- wp:table {"className":"svr-matrix"} -->
<figure class="wp-block-table svr-matrix"><table class="has-fixed-layout"><thead><tr><th scope="col">Вид работ</th><th scope="col">Элтеза</th><th scope="col">Рузский</th><th scope="col">ОС3</th><th scope="col">ОС2</th></tr></thead><tbody><tr><th scope="row">Инженерные изыскания</th><td><em>Нет</em></td><td><strong>Да</strong></td><td><em>Нет</em></td><td><em>Нет</em></td></tr><tr><th scope="row">Обследование действующих сооружений</th><td><strong>Да</strong></td><td><strong>Да</strong></td><td><em>Нет</em></td><td><em>Нет</em></td></tr><tr><th scope="row">Обследование построенных сооружений</th><td><em>Нет</em></td><td><em>Нет</em></td><td><strong>Да</strong></td><td><strong>Да</strong></td></tr><tr><th scope="row">Отбор проб сточных вод</th><td><strong>Да</strong></td><td><strong>Да</strong></td><td><strong>Да</strong></td><td><strong>Да</strong></td></tr><tr><th scope="row">Лабораторные испытания</th><td><strong>Да</strong></td><td><strong>Да</strong></td><td><strong>Да</strong></td><td><strong>Да</strong></td></tr><tr><th scope="row">Определение показателей сточных вод</th><td><strong>Да</strong></td><td><strong>Да</strong></td><td><strong>Да</strong></td><td><strong>Да</strong></td></tr><tr><th scope="row">Определение оптимальных технологических решений</th><td><strong>Да</strong></td><td><strong>Да</strong></td><td><em>Нет</em></td><td><em>Нет</em></td></tr><tr><th scope="row">Разработка проектной документации</th><td><strong>Да</strong></td><td><em>Нет</em></td><td><em>Нет</em></td><td><em>Нет</em></td></tr><tr><th scope="row">Разработка рабочей документации</th><td><strong>Да</strong></td><td><strong>Да</strong></td><td><em>Нет</em></td><td><em>Нет</em></td></tr><tr><th scope="row">Маркировка оборудования</th><td><em>Нет</em></td><td><em>Нет</em></td><td><strong>Да</strong></td><td><strong>Да</strong></td></tr><tr><th scope="row">Выявление неисправностей</th><td><em>Нет</em></td><td><em>Нет</em></td><td><strong>Да</strong></td><td><strong>Да</strong></td></tr><tr><th scope="row">Определение режимов работы</th><td><em>Нет</em></td><td><em>Нет</em></td><td><strong>Да</strong></td><td><strong>Да</strong></td></tr></tbody></table><figcaption class="wp-element-caption">●&nbsp;выполнено · —&nbsp;не входило в&nbsp;состав работ</figcaption></figure>
<!-- /wp:table --></div>
<!-- /wp:group --></section>
<!-- /wp:group -->
```

### 14. Страница объекта (51–54): вступление, работы, галерея, другие объекты

*spec §7.3, §5.8, §5.14.* Эталон — ОАО «Элтеза» (51). Шаблон страницы — `wp-custom-template-obekt` (крошки «Главная / Наши объекты / …»). Вступление: метка с типом объекта, ghost «Все объекты» (`svr-btn--back`), штамп `svr-tb` из 2 ячеек без ссылок «Задача | Этапы» (`columnCount:2`; отдельного лида и ячейки «Объект» нет — они повторяли штамп и H1). Работы — `svr-works` (формулировка брифа, без номеров). Галерея — `core/gallery` `svr-gallery` (2 колонки, `imageCrop:false`, lightbox у каждого изображения); схемы на белом — класс `svr-on-paper` у изображения, мелкий исходник id 21 — `svr-native`. «Другие объекты» — 3 карточки `svr-mini-obj`.

```html
<!-- wp:group {"align":"wide","className":"svr-page-intro","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-page-intro"><!-- wp:group {"layout":{"type":"flex","flexWrap":"wrap","justifyContent":"space-between"}} -->
<div class="wp-block-group"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Гальваническое производство</p>
<!-- /wp:paragraph -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"svr-btn\u002d\u002dghost svr-btn\u002d\u002dback"} -->
<div class="wp-block-button svr-btn--ghost svr-btn--back"><a class="wp-block-button__link wp-element-button" href="https://svr-mos.ru/obj/">Все объекты</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:group -->

<!-- wp:group {"align":"wide","className":"svr-tb","layout":{"type":"grid","columnCount":2}} -->
<div class="wp-block-group alignwide svr-tb"><!-- wp:group {"className":"svr-tb__cell","layout":{"type":"default"}} -->
<div class="wp-block-group svr-tb__cell"><!-- wp:paragraph {"className":"svr-tb__k"} -->
<p class="svr-tb__k">Задача</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"svr-tb__v"} -->
<p class="svr-tb__v">Сточные воды гальванического производства.</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-tb__cell","layout":{"type":"default"}} -->
<div class="wp-block-group svr-tb__cell"><!-- wp:paragraph {"className":"svr-tb__k"} -->
<p class="svr-tb__k">Этапы</p>
<!-- /wp:paragraph -->

<!-- wp:list {"className":"svr-chips"} -->
<ul class="wp-block-list svr-chips"><!-- wp:list-item -->
<li>Обследование</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Лаборатория</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Технологические решения</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Проектирование</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list --></div>
<!-- /wp:group --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec","style":{"spacing":{"blockGap":"var:preset|spacing|50"}},"layout":{"type":"constrained"}} -->
<section class="wp-block-group alignfull svr-sec"><!-- wp:group {"align":"wide","className":"svr-head","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-head"><!-- wp:heading -->
<h2 class="wp-block-heading">Выполненные работы</h2>
<!-- /wp:heading --></div>
<!-- /wp:group -->

<!-- wp:group {"align":"wide","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide"><!-- wp:list {"className":"svr-works"} -->
<ul class="wp-block-list svr-works"><!-- wp:list-item -->
<li>Обследование действующих сооружений</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Отбор проб сточных вод гальванического производства</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Проведение лабораторных испытаний</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Определение показателей сточных вод</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Определение оптимальных технологических решений</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Разработка проектной документации</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Разработка рабочей документации</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list --></div>
<!-- /wp:group --></section>
<!-- /wp:group -->

<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec svr-sec\u002d\u002dband svr-ruler","style":{"spacing":{"blockGap":"var:preset|spacing|50"}},"layout":{"type":"constrained"}} -->
<section class="wp-block-group alignfull svr-sec svr-sec--band svr-ruler"><!-- wp:group {"align":"wide","className":"svr-head","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-head"><!-- wp:heading -->
<h2 class="wp-block-heading">Фотографии и&nbsp;материалы</h2>
<!-- /wp:heading --></div>
<!-- /wp:group -->

<!-- wp:group {"align":"wide","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide"><!-- wp:gallery {"columns":2,"imageCrop":false,"linkTo":"none","sizeSlug":"full","className":"svr-gallery"} -->
<figure class="wp-block-gallery has-nested-images columns-2 svr-gallery"><!-- wp:image {"lightbox":{"enabled":true},"id":20,"sizeSlug":"full","linkDestination":"none"} -->
<figure class="wp-block-image size-full"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-elteza-3.png" alt="ОАО «Элтеза»: ёмкости и оборудование очистных сооружений (коллаж)" class="wp-image-20"/></figure>
<!-- /wp:image -->

<!-- wp:image {"lightbox":{"enabled":true},"id":22,"sizeSlug":"full","linkDestination":"none"} -->
<figure class="wp-block-image size-full"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-elteza-5.png" alt="ОАО «Элтеза»: стаканы с пробами на лабораторных мешалках" class="wp-image-22"/></figure>
<!-- /wp:image -->

<!-- wp:image {"lightbox":{"enabled":true},"id":18,"sizeSlug":"full","linkDestination":"none","className":"svr-on-paper"} -->
<figure class="wp-block-image size-full svr-on-paper"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-elteza-1.png" alt="ОАО «Элтеза»: технологическая схема" class="wp-image-18"/></figure>
<!-- /wp:image -->

<!-- wp:image {"lightbox":{"enabled":true},"id":23,"sizeSlug":"full","linkDestination":"none","className":"svr-on-paper"} -->
<figure class="wp-block-image size-full svr-on-paper"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-elteza-6.png" alt="ОАО «Элтеза»: чертёж оборудования" class="wp-image-23"/></figure>
<!-- /wp:image -->

<!-- wp:image {"lightbox":{"enabled":true},"id":24,"sizeSlug":"full","linkDestination":"none","className":"svr-on-paper"} -->
<figure class="wp-block-image size-full svr-on-paper"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-elteza-7.png" alt="ОАО «Элтеза»: чертёж компоновки оборудования" class="wp-image-24"/></figure>
<!-- /wp:image -->

<!-- wp:image {"lightbox":{"enabled":true},"id":25,"sizeSlug":"full","linkDestination":"none","className":"svr-on-paper"} -->
<figure class="wp-block-image size-full svr-on-paper"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-elteza-8.png" alt="ОАО «Элтеза»: чертёж компоновки оборудования, разрез" class="wp-image-25"/></figure>
<!-- /wp:image -->

<!-- wp:image {"lightbox":{"enabled":true},"id":19,"sizeSlug":"full","linkDestination":"none"} -->
<figure class="wp-block-image size-full"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-elteza-2.png" alt="Лабораторная посуда с растворами" class="wp-image-19"/></figure>
<!-- /wp:image -->

<!-- wp:image {"lightbox":{"enabled":true},"id":21,"sizeSlug":"full","linkDestination":"none","className":"svr-native"} -->
<figure class="wp-block-image size-full svr-native"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-elteza-4.jpg" alt="Лабораторная посуда с цветными растворами" class="wp-image-21"/></figure>
<!-- /wp:image --></figure>
<!-- /wp:gallery --></div>
<!-- /wp:group --></section>
<!-- /wp:group -->

<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec","style":{"spacing":{"blockGap":"var:preset|spacing|50"}},"layout":{"type":"constrained"}} -->
<section class="wp-block-group alignfull svr-sec"><!-- wp:group {"align":"wide","className":"svr-head","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-head"><!-- wp:heading -->
<h2 class="wp-block-heading">Другие объекты</h2>
<!-- /wp:heading --></div>
<!-- /wp:group -->

<!-- wp:group {"align":"wide","className":"svr-mini-objs","layout":{"type":"grid","columnCount":3}} -->
<div class="wp-block-group alignwide svr-mini-objs"><!-- wp:group {"className":"svr-mini-obj","layout":{"type":"default"}} -->
<div class="wp-block-group svr-mini-obj"><!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading"><a href="https://svr-mos.ru/russkii/">ОАО «Мясокомбинат «Рузский»</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-meta","fontSize":"small"} -->
<p class="svr-meta has-small-font-size">Мясокомбинат</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-mini-obj","layout":{"type":"default"}} -->
<div class="wp-block-group svr-mini-obj"><!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading"><a href="https://svr-mos.ru/os3-marino/">ОС3 Марьино-Саларьево (II&nbsp;этап)</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-meta","fontSize":"small"} -->
<p class="svr-meta has-small-font-size">Ливневые очистные сооружения</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-mini-obj","layout":{"type":"default"}} -->
<div class="wp-block-group svr-mini-obj"><!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading"><a href="https://svr-mos.ru/os2-marino/">ОС2 Марьино-Саларьево (II&nbsp;этап)</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-meta","fontSize":"small"} -->
<p class="svr-meta has-small-font-size">Ливневые очистные сооружения</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group --></section>
<!-- /wp:group -->
```

### 15. Документ на /docs/ (`svr-card--lg`, `core/file` `svr-file`)

*spec §7.5.* Кнопка «Открыть PDF» (новая вкладка) + `core/file` только с кнопкой «Скачать PDF» (атрибут `download` даёт сам блок; высота и кегль — как у `core/button`). Текст карточки не повторяет лид страницы. Название-ссылку у `core/file` не заполнять (иначе блок выведет вторую ссылку).

```html
<!-- wp:group {"align":"wide","className":"svr-page-intro","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-page-intro"><!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Документы ООО&nbsp;«СВР» для&nbsp;просмотра и&nbsp;скачивания.</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec","style":{"spacing":{"blockGap":"var:preset|spacing|60"}},"layout":{"type":"constrained"}} -->
<section class="wp-block-group alignfull svr-sec"><!-- wp:group {"align":"wide","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide"><!-- wp:group {"className":"svr-card svr-card\u002d\u002ddoc svr-card\u002d\u002dlg","layout":{"type":"default"}} -->
<div class="wp-block-group svr-card svr-card--doc svr-card--lg"><!-- wp:columns {"verticalAlignment":"top"} -->
<div class="wp-block-columns are-vertically-aligned-top"><!-- wp:column {"width":"280px"} -->
<div class="wp-block-column" style="flex-basis:280px"><!-- wp:image {"id":12,"sizeSlug":"full","linkDestination":"custom","className":"svr-doc-sheet"} -->
<figure class="wp-block-image size-full svr-doc-sheet"><a href="https://svr-mos.ru/wp-content/uploads/2026/10/svr-deklaraciya-eac.pdf" target="_blank" rel="noreferrer noopener"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-deklaraciya-eac-preview.jpg" alt="Декларация о соответствии ЕАЭС — открыть PDF" class="wp-image-12"/></a></figure>
<!-- /wp:image --></div>
<!-- /wp:column -->

<!-- wp:column -->
<div class="wp-block-column"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Документ · PDF</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Декларация о&nbsp;соответствии ЕАЭС</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Откройте документ в&nbsp;новой вкладке или&nbsp;скачайте файл&nbsp;PDF.</p>
<!-- /wp:paragraph -->

<!-- wp:group {"className":"svr-doc-actions","layout":{"type":"flex","flexWrap":"wrap"}} -->
<div class="wp-block-group svr-doc-actions"><!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"is-style-outline svr-ic-doc"} -->
<div class="wp-block-button is-style-outline svr-ic-doc"><a class="wp-block-button__link wp-element-button" href="https://svr-mos.ru/wp-content/uploads/2026/10/svr-deklaraciya-eac.pdf" target="_blank" rel="noreferrer noopener">Открыть PDF</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons -->

<!-- wp:file {"id":11,"href":"https://svr-mos.ru/wp-content/uploads/2026/10/svr-deklaraciya-eac.pdf","className":"svr-file"} -->
<div class="wp-block-file svr-file"><a href="https://svr-mos.ru/wp-content/uploads/2026/10/svr-deklaraciya-eac.pdf" class="wp-block-file__button wp-element-button" download>Скачать PDF</a></div>
<!-- /wp:file --></div>
<!-- /wp:group --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group --></div>
<!-- /wp:group --></section>
<!-- /wp:group -->
```

### 16. Реквизиты на /rekvizit/ (`svr-req`)

*spec §7.6.* `core/table` с `hasFixedLayout:false`, ключ — `<th scope="row">` полными словами («Расчётный счёт», не «Р/с»), числа — `<code>`. Значения выделяются целиком (`-webkit-user-select:all; user-select:all`), в буфер попадают обычные пробелы.

```html
<!-- wp:group {"align":"wide","className":"svr-page-intro","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-page-intro"><!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Реквизиты ООО&nbsp;«СВР» для&nbsp;договоров и&nbsp;счетов. Значения выделяются целиком для&nbsp;копирования.</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec","style":{"spacing":{"blockGap":"var:preset|spacing|60"}},"layout":{"type":"constrained"}} -->
<section class="wp-block-group alignfull svr-sec"><!-- wp:group {"align":"wide","className":"svr-card","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-card"><!-- wp:table {"hasFixedLayout":false,"className":"svr-req"} -->
<figure class="wp-block-table svr-req"><table><tbody><tr><th scope="row">Полное наименование</th><td>Общество с&nbsp;ограниченной ответственностью «СЕРВИС ВОДНЫХ РЕСУРСОВ»</td></tr><tr><th scope="row">Сокращённое наименование</th><td>ООО&nbsp;«СВР»</td></tr><tr><th scope="row">Юридический адрес</th><td>129347, г.&nbsp;Москва, вн.тер.г. муниципальный округ Ярославский, Ярославское шоссе, д.&nbsp;124, помещ.&nbsp;1</td></tr><tr><th scope="row">ИНН</th><td><code>7716962072</code></td></tr><tr><th scope="row">КПП</th><td><code>771601001</code></td></tr><tr><th scope="row">Банк</th><td>АО&nbsp;«Райффайзенбанк»</td></tr><tr><th scope="row">Расчётный счёт</th><td><code>40702810800000204238</code></td></tr><tr><th scope="row">Корреспондентский счёт</th><td><code>30101810200000000700</code></td></tr><tr><th scope="row">БИК</th><td><code>044525700</code></td></tr><tr><th scope="row">Генеральный директор</th><td>Новицкий Андрей Аркадьевич</td></tr></tbody></table></figure>
<!-- /wp:table --></div>
<!-- /wp:group --></section>
<!-- /wp:group -->
```

### 17. Контакты /contact/: каналы связи и «Как добраться»

*spec §7.7.* Штамп `svr-contacts` (`columnCount:2`) — каналы связи: телефон во всю ширину, почта, режим работы. «Как добраться» — место: адрес, метро, ghost «Открыть в Яндекс Картах» (`svr-ic-ext`, новая вкладка); колонка текста по центру чертежа капли. Каждое значение на странице встречается один раз. Карту и схему проезда не встраивать. `svr-cta-compact` на этой странице скрыт CSS-ом автоматически.

```html
<!-- wp:group {"align":"wide","className":"svr-page-intro","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-page-intro"><!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Позвоните или напишите&nbsp;— обсудим задачу на&nbsp;вашем объекте. Подбор оборудования и&nbsp;подробности&nbsp;— по&nbsp;запросу.</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec svr-mm","style":{"spacing":{"blockGap":"var:preset|spacing|60"}},"layout":{"type":"constrained"}} -->
<section class="wp-block-group alignfull svr-sec svr-mm"><!-- wp:group {"align":"wide","className":"svr-contacts","layout":{"type":"grid","columnCount":2}} -->
<div class="wp-block-group alignwide svr-contacts"><!-- wp:group {"className":"svr-contacts__cell svr-contacts__cell\u002d\u002dwide","layout":{"type":"default"}} -->
<div class="wp-block-group svr-contacts__cell svr-contacts__cell--wide"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Телефон</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"svr-phone","fontSize":"phone"} -->
<p class="svr-phone has-phone-font-size"><a href="tel:+79652808090">8&nbsp;965&nbsp;280-80-90</a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-contacts__cell","layout":{"type":"default"}} -->
<div class="wp-block-group svr-contacts__cell"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Почта</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"svr-mail"} -->
<p class="svr-mail"><a href="mailto:info@svr-mos.ru">info@svr-mos.ru</a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-contacts__cell","layout":{"type":"default"}} -->
<div class="wp-block-group svr-contacts__cell"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Режим работы</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Пн—Пт 10:00—18:00</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"svr-meta","fontSize":"small"} -->
<p class="svr-meta has-small-font-size">Сб—Вс выходные</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group --></section>
<!-- /wp:group -->

<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec svr-sec\u002d\u002dband","style":{"spacing":{"blockGap":"var:preset|spacing|60"}},"layout":{"type":"constrained"}} -->
<section class="wp-block-group alignfull svr-sec svr-sec--band"><!-- wp:columns {"align":"wide","className":"svr-cta__grid"} -->
<div class="wp-block-columns alignwide svr-cta__grid"><!-- wp:column {"verticalAlignment":"center","width":"60%"} -->
<div class="wp-block-column is-vertically-aligned-center" style="flex-basis:60%"><!-- wp:heading -->
<h2 class="wp-block-heading">Как добраться</h2>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Москва, Ярославское шоссе, д.&nbsp;42, оф.&nbsp;603</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>м.&nbsp;«ВДНХ», «Ботанический сад»</p>
<!-- /wp:paragraph -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"svr-btn\u002d\u002dghost svr-ic-ext"} -->
<div class="wp-block-button svr-btn--ghost svr-ic-ext"><a class="wp-block-button__link wp-element-button" href="https://yandex.ru/maps/?text=%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%2C%20%D0%AF%D1%80%D0%BE%D1%81%D0%BB%D0%B0%D0%B2%D1%81%D0%BA%D0%BE%D0%B5%20%D1%88%D0%BE%D1%81%D1%81%D0%B5%2C%2042" target="_blank" rel="noreferrer noopener">Открыть в Яндекс Картах</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:column -->

<!-- wp:column {"width":"40%","className":"svr-cta__dwg"} -->
<div class="wp-block-column svr-cta__dwg" style="flex-basis:40%"><!-- wp:html -->
<svg class="svr-dwg" viewBox="0 0 440 456" fill="none" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg">
<defs>
<clipPath id="svrCtaIn"><path d="M220 120.22 L292.38 228.72 A87 87 0 1 1 147.62 228.72 Z"/></clipPath>
<pattern id="svrCtaHatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" stroke="#0EB8DA" stroke-opacity=".5"/></pattern>
<mask id="svrCtaWall"><path d="M220 104 L299.86 223.73 A96 96 0 1 1 140.14 223.73 Z" fill="#fff"/><path d="M220 120.22 L292.38 228.72 A87 87 0 1 1 147.62 228.72 Z" fill="#000"/></mask>
<linearGradient id="svrCtaWater" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0EB8DA" stop-opacity=".42"/><stop offset="1" stop-color="#0089BF" stop-opacity=".08"/></linearGradient>
<radialGradient id="svrCtaGlow"><stop offset="0" stop-color="#0EB8DA" stop-opacity="0.18"/><stop offset="1" stop-color="#0EB8DA" stop-opacity="0"/></radialGradient>
</defs>
<circle cx="220" cy="277" r="163.2" fill="url(#svrCtaGlow)"/>
<circle cx="220" cy="281" r="109.44" fill="none" stroke="#0EB8DA" stroke-opacity=".3" stroke-dasharray="3 6"/>
<g clip-path="url(#svrCtaIn)">
<rect x="124" y="104" width="192" height="269" fill="#0B2540" fill-opacity=".55"/>
<path fill="url(#svrCtaWater)" opacity=".55" d="M-200 246q30-7 60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0V393H-200Z"/>
<g><path fill="url(#svrCtaWater)" d="M-200 254q30-8 60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0V393H-200Z"/></g>
</g>
<rect x="112" y="92" width="216" height="293" fill="url(#svrCtaHatch)" mask="url(#svrCtaWall)"/>
<path d="M220 104 L299.86 223.73 A96 96 0 1 1 140.14 223.73 Z" fill="none" stroke="#0EB8DA" stroke-width="2" stroke-linejoin="round"/>
<path d="M220 120.22 L292.38 228.72 A87 87 0 1 1 147.62 228.72 Z" fill="none" stroke="#0EB8DA" stroke-opacity=".7" stroke-linejoin="round"/>
<path d="M158.87 292.24A63 63 0 0 0 186.62 330.43" fill="none" stroke="#E8F1F8" stroke-opacity=".28" stroke-width="3" stroke-linecap="round"/>
<path d="M16 74H220V104" fill="none" stroke="#0EB8DA" stroke-width="2"/>
<path class="svr-dwg-flow" d="M16 74H220V104" fill="none" stroke="#E8F1F8" stroke-width="2" stroke-dasharray="6 10"/>
<g stroke="#0EB8DA" stroke-width="1.5"><path d="M61.12 66L85.12 82V66L61.12 82Z" fill="#071B2F" stroke-linejoin="round"/><path d="M73.12 66V48M65.12 48H81.12" fill="none"/></g>
<path d="M150.64 67l14 7-14 7z" fill="#0EB8DA"/>
<text class="svr-dwg-t" x="16" y="28">Сточные воды</text>
<path d="M220 373V410H424" fill="none" stroke="#0EB8DA" stroke-width="2"/>
<path class="svr-dwg-flow" d="M220 373V410H424" fill="none" stroke="#E8F1F8" stroke-width="2" stroke-dasharray="6 10"/>
<path d="M424 400V420" stroke="#0EB8DA" stroke-width="2"/>
<g stroke="#0EB8DA" stroke-width="1.5"><path d="M299.8 402L323.8 418V402L299.8 418Z" fill="#071B2F" stroke-linejoin="round"/><path d="M311.8 402V384M303.8 384H319.8" fill="none"/></g>
<path d="M383.2 403l14 7-14 7z" fill="#0EB8DA"/>
<text class="svr-dwg-t" x="424" y="442" text-anchor="end">Чистая вода</text>
</svg>
<!-- /wp:html --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></section>
<!-- /wp:group -->
```

### 18. Страница продукции (`/prod/<slug>/`, шаблон `wp-custom-template-produkciya`)

*spec §7.4.* Пять дочерних страниц «Нашей продукции» (parent = /prod/): `stanciya-dozirovaniya`, `reaktor-trehkamernyj`, `reaktor-odnokamernyj`, `ustanovka-obezzarazhivaniya`, `kns`. H1 и крошки «Главная / Продукция / Название» выводит шаблон. Состав: `svr-page-intro` (метка + ghost «Вся продукция») → секция: колонки 56/44 `svr-prod` — крупное фото на бумаге `svr-sheet svr-sheet--lead` (lightbox) | лид «Мы сами проектируем и разрабатываем оборудование.» и блок `svr-spec-note` («Технические параметры — по запросу», телефон, почта, кнопки) → секция «Другая продукция»: остальные 4 позиции листами `svr-sheets--rel` (4 колонки ≥1200 px), каждый лист — ссылка на свою страницу. Когда параметры будут присланы, `svr-spec-note` заменяют таблицей `svr-spec` (следующий фрагмент). Пример — «Канализационные насосные станции».

```html
<!-- wp:group {"align":"wide","className":"svr-page-intro","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-page-intro"><!-- wp:group {"layout":{"type":"flex","flexWrap":"wrap","justifyContent":"space-between"}} -->
<div class="wp-block-group"><!-- wp:paragraph {"className":"svr-label"} -->
<p class="svr-label">Продукция СВР</p>
<!-- /wp:paragraph -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"svr-btn\u002d\u002dghost svr-btn\u002d\u002dback"} -->
<div class="wp-block-button svr-btn--ghost svr-btn--back"><a class="wp-block-button__link wp-element-button" href="https://svr-mos.ru/prod/">Вся продукция</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec svr-sec\u002d\u002dtight","style":{"spacing":{"blockGap":"var:preset|spacing|50"}},"layout":{"type":"constrained"}} -->
<section class="wp-block-group alignfull svr-sec svr-sec--tight"><!-- wp:group {"align":"wide","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide"><!-- wp:columns {"align":"wide","className":"svr-prod"} -->
<div class="wp-block-columns alignwide svr-prod"><!-- wp:column {"width":"56%"} -->
<div class="wp-block-column" style="flex-basis:56%"><!-- wp:group {"className":"svr-sheet svr-sheet\u002d\u002dlead","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet svr-sheet--lead"><!-- wp:image {"lightbox":{"enabled":true},"id":17,"sizeSlug":"full","linkDestination":"none","className":"svr-sheet__img"} -->
<figure class="wp-block-image size-full svr-sheet__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-kns.png" alt="Канализационные насосные станции — 3D-модель" class="wp-image-17"/></figure>
<!-- /wp:image --></div>
<!-- /wp:group --></div>
<!-- /wp:column -->

<!-- wp:column {"width":"44%","className":"svr-prod__text"} -->
<div class="wp-block-column svr-prod__text" style="flex-basis:44%"><!-- wp:paragraph {"className":"svr-lead","fontSize":"large"} -->
<p class="svr-lead has-large-font-size">Мы сами проектируем и&nbsp;разрабатываем оборудование.</p>
<!-- /wp:paragraph -->

<!-- wp:group {"className":"svr-card svr-spec-note","layout":{"type":"default"}} -->
<div class="wp-block-group svr-card svr-spec-note"><!-- wp:heading -->
<h2 class="wp-block-heading">Технические параметры</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>По&nbsp;запросу. Позвоните <a href="tel:+79652808090">8&nbsp;965&nbsp;280-80-90</a> или&nbsp;напишите <a href="mailto:info@svr-mos.ru">info@svr-mos.ru</a>.</p>
<!-- /wp:paragraph -->

<!-- wp:buttons {"className":"svr-btns"} -->
<div class="wp-block-buttons svr-btns"><!-- wp:button {"className":"svr-ic-tel"} -->
<div class="wp-block-button svr-ic-tel"><a class="wp-block-button__link wp-element-button" href="tel:+79652808090">Позвонить</a></div>
<!-- /wp:button -->

<!-- wp:button {"className":"is-style-outline svr-ic-mail"} -->
<div class="wp-block-button is-style-outline svr-ic-mail"><a class="wp-block-button__link wp-element-button" href="mailto:info@svr-mos.ru">Написать</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:group --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group --></section>
<!-- /wp:group -->

<!-- wp:group {"tagName":"section","align":"full","className":"svr-sec svr-sec\u002d\u002dband svr-mm svr-ruler svr-products","style":{"spacing":{"blockGap":"var:preset|spacing|50"}},"layout":{"type":"constrained"}} -->
<section class="wp-block-group alignfull svr-sec svr-sec--band svr-mm svr-ruler svr-products"><!-- wp:group {"align":"wide","className":"svr-head","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide svr-head"><!-- wp:heading -->
<h2 class="wp-block-heading">Другая продукция</h2>
<!-- /wp:heading --></div>
<!-- /wp:group -->

<!-- wp:group {"align":"wide","className":"svr-sheets svr-sheets\u002d\u002drel","layout":{"type":"grid","columnCount":4}} -->
<div class="wp-block-group alignwide svr-sheets svr-sheets--rel"><!-- wp:group {"className":"svr-sheet","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet"><!-- wp:image {"id":13,"sizeSlug":"full","linkDestination":"none","className":"svr-sheet__img"} -->
<figure class="wp-block-image size-full svr-sheet__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-stanciya-dozirovaniya-sdphr.png" alt="Станции дозирования и приготовления реагентов двухкамерные — 3D-модель" class="wp-image-13"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-sheet__tb","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet__tb"><!-- wp:heading {"level":3,"className":"svr-sheet__name"} -->
<h3 class="wp-block-heading svr-sheet__name"><a href="https://svr-mos.ru/prod/stanciya-dozirovaniya/">Станции дозирования и&nbsp;приготовления реагентов двухкамерные</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-sheet__more"} -->
<p class="svr-sheet__more">Подробнее</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-sheet","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet"><!-- wp:image {"id":14,"sizeSlug":"full","linkDestination":"none","className":"svr-sheet__img"} -->
<figure class="wp-block-image size-full svr-sheet__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-reaktor-trehkamernyj.png" alt="Реактор трёхкамерный — 3D-модель" class="wp-image-14"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-sheet__tb","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet__tb"><!-- wp:heading {"level":3,"className":"svr-sheet__name"} -->
<h3 class="wp-block-heading svr-sheet__name"><a href="https://svr-mos.ru/prod/reaktor-trehkamernyj/">Реактор трёхкамерный</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-sheet__more"} -->
<p class="svr-sheet__more">Подробнее</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-sheet","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet"><!-- wp:image {"id":15,"sizeSlug":"full","linkDestination":"none","className":"svr-sheet__img"} -->
<figure class="wp-block-image size-full svr-sheet__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-reaktor-odnokamernyj.png" alt="Реактор однокамерный — 3D-модель" class="wp-image-15"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-sheet__tb","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet__tb"><!-- wp:heading {"level":3,"className":"svr-sheet__name"} -->
<h3 class="wp-block-heading svr-sheet__name"><a href="https://svr-mos.ru/prod/reaktor-odnokamernyj/">Реактор однокамерный</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-sheet__more"} -->
<p class="svr-sheet__more">Подробнее</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:group {"className":"svr-sheet","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet"><!-- wp:image {"id":16,"aspectRatio":"4/3","scale":"cover","sizeSlug":"full","linkDestination":"none","className":"svr-sheet__img"} -->
<figure class="wp-block-image size-full svr-sheet__img"><img src="https://svr-mos.ru/wp-content/uploads/2026/10/svr-ustanovka-obezzarazhivaniya-uko.png" alt="Установка комплексного обеззараживания сточных вод — 3D-модель" class="wp-image-16" style="aspect-ratio:4/3;object-fit:cover"/></figure>
<!-- /wp:image -->

<!-- wp:group {"className":"svr-sheet__tb","layout":{"type":"default"}} -->
<div class="wp-block-group svr-sheet__tb"><!-- wp:heading {"level":3,"className":"svr-sheet__name"} -->
<h3 class="wp-block-heading svr-sheet__name"><a href="https://svr-mos.ru/prod/ustanovka-obezzarazhivaniya/">Установка комплексного обеззараживания сточных вод</a></h3>
<!-- /wp:heading -->

<!-- wp:paragraph {"className":"svr-sheet__more"} -->
<p class="svr-sheet__more">Подробнее</p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group --></div>
<!-- /wp:group --></section>
<!-- /wp:group -->
```

### 19. Таблица характеристик (`svr-spec`) и заглушка (`svr-spec-note`)

*spec §7.4.* `core/table` с классом `svr-spec`, `hasFixedLayout:false`, шапка «Параметр / Значение» (`<th scope="col">`), параметры — `<th scope="row">`, значения — `<td>`; единицы измерения пишут в значении («…&nbsp;мм»), составные значения — через запятую. Необязательная заметка — подпись таблицы (`figcaption`), например условия или примечание. Ниже — ШАБЛОН с условными подписями (замените на данные заказчика; своих цифр не придумывать). Как добавить параметры на страницу продукции: открыть страницу → заменить группу `svr-spec-note` (заголовок «Технические параметры», текст «По запросу…» и кнопки) на этот блок под H2 «Технические параметры» → обновить. Кнопки «Позвонить/Написать» можно оставить под таблицей.

```html
<!-- wp:group {"align":"wide","layout":{"type":"default"}} -->
<div class="wp-block-group alignwide"><!-- wp:heading -->
<h2 class="wp-block-heading">Технические параметры</h2>
<!-- /wp:heading -->

<!-- wp:table {"hasFixedLayout":false,"className":"svr-spec"} -->
<figure class="wp-block-table svr-spec"><table><thead><tr><th scope="col">Параметр</th><th scope="col">Значение</th></tr></thead><tbody><tr><th scope="row">Название параметра 1</th><td>Значение 1</td></tr><tr><th scope="row">Название параметра 2</th><td>Значение 2</td></tr><tr><th scope="row">Название параметра 3</th><td>Значение 3</td></tr></tbody></table><figcaption class="wp-element-caption">Заметка: условия или примечание к параметрам (необязательно).</figcaption></figure>
<!-- /wp:table --></div>
<!-- /wp:group -->
```
