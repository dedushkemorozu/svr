# preview.py — превью страниц WordPress 7.1.3 + Twenty Twenty-Five без WordPress

Собирает HTML страницы из файлов дизайн-системы (`redesign/system/`: `global-styles.json`, `styles.css`,
`header.html`, `footer.html`, `page.html`, `page-no-title.html` …) и блочной разметки контента — так,
как его отрисует WordPress, — снимает скриншоты (Playwright/Chromium) и пишет отчёт о проблемах.

Точность проверена на настоящем WordPress 7.1.3 (локальная копия стенда, см. «Проверка точности»):
DOM (теги + классы) совпадает на 100 %, наборы CSS-правил `global-styles`, `core-block-supports` и
`block-style-variation-styles` совпадают целиком, высоты страниц совпадают, попиксельная разница 0–0,06 %.

## Источник правды и публикация (после ревью страниц)

* **Страницы сайта — `deploy/pages/<id>.html`** (49–58). Их правят вручную; скрипты их не перезаписывают.
  Генератор `components_src.py` синхронизирован с ними: его вывод после канонизации редактором (`tmp/canon-gen/`) совпадает
  с пакетом байт в байт, `rebuild.sh` печатает `DRIFT`, если это перестало быть так.
* Шаблоны и части — `system/*.html` (в т. ч. `wp-custom-template-obekt.html` для 51–54), CSS — `system/styles.css` →
  `build_system.py` → `global-styles.json`. `build_deploy.py` копирует их в `deploy/` и пишет `deploy/manifest.json`.
* `rebuild.sh` — полный цикл; деплой на **локальный** стенд — `php tools/apply_manifest.php` (те же REST-маршруты, что на сайте,
  затем GET и сверка с файлами). Старый `wp_deploy.php` (деплоил перегенерируемые `tmp/canon`) — обёртка над ним.

| скрипт | что делает |
|---|---|
| `make_drops.py`, `make_icons.py` | генерация `assets/svg/hero-drop.svg`, `cta-drop.svg` (+ синхронизация капли в `system/404.html`) и набора иконок этапов `stage-icons.html` |
| `regen.sh` | быстрый цикл: SVG → CSS → генератор страниц → каноника редактора WP → `deploy/pages` → пакет |
| `build_deploy.py` | пакет `deploy/`: global styles, части, шаблоны, `manifest.json`; запрет `file://`, `/tmp`, `localhost`, `127.0.0.1`, `:8090`, чужих ссылок |
| `apply_manifest.php` | применяет `deploy/manifest.json` к стенду и сверяет GET `context=edit` с файлами (id global styles на стенде подставляется сам) |
| `validate_blocks.py --strict --out DIR` | редактор WP 7.1.3: `isValid` + сериализация побайтно равна файлу (иначе BAD); каноника — в `DIR` |
| `wp_site_check.py [--shots DIR]` | регрессия настоящих страниц стенда: скролл 320–1440, h1, битые/без alt, апскейл фото, анимации (reduce → 0, ∞ ≤12), крошки, alt логотипа, меню (Esc, фокус), lightbox |
| `preview_pages.sh` | превью всех страниц; `SYS=`, `PAGES=` (по умолчанию `deploy/pages`), `O=`, `MENU=1`, `LOGO_ALT=` |
| `report_summary.py <папка>` | сводка отчётов превью (скролл на всех ширинах, h1, AA, alt, дубли id, анимации) |
| `word_fit.py <превью.html>` | ни одно слово в заголовках/названиях не шире своего блока (иначе оно рвётся посреди) на 320–1440 |

## Быстрый старт

```bash
cd /tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign

# Внутренняя страница (шаблон page: шапка, хлебные крошки, H1 = --title, контент, CTA, подвал)
python3 tools/preview.py --content pages/obj.html --template page --title "Наши объекты" \
    --page-id 50 --out tmp/shots/obj

# Главная (шаблон page-no-title, класс body.home, aria-current у логотипа)
python3 tools/preview.py --content pages/home.html --template page-no-title --title "Главная" \
    --front --out tmp/shots/home

# + мобильное меню открытым и проверка горизонтального скролла на других ширинах
python3 tools/preview.py --content pages/home.html --template page-no-title --front --out tmp/shots/home \
    --menu --check-widths 320,360,375,414,430,600,768,1024,1280

# Готовый HTML из REST (content.rendered). С --raw (content.raw, context=edit) CSS контейнеров восстанавливается точно
python3 tools/preview.py --content tmp/rendered-50.html --rendered --raw tmp/raw-50.html \
    --title "Наши объекты" --page-id 50 --out tmp/shots/obj-rendered

# Другие файлы системы / только HTML без браузера
python3 tools/preview.py --content x.html --system tmp/my-system --global-styles tmp/gs.json --css tmp/s.css \
    --out tmp/shots/x --no-shots
```

Результат (`--out <prefix>`):

| файл | что внутри |
|---|---|
| `<prefix>.html` | полная страница: `<head>` в порядке WP (block-library → global-styles → block-style-variation-styles → core-block-supports → skip-link → TT5 style → @font-face), `body` с классами WP, skip-link, `div.wp-site-blocks`. Картинки и шрифты — локальные `file://` |
| `<prefix>-desktop.png` | 1440×900, full page (см. «Снимки» ниже) |
| `<prefix>-mobile.png` | 390×844, full page |
| `<prefix>-mobile-menu.png` | (с `--menu`) 390×844, меню открыто так же, как это делает Interactivity API |
| `<prefix>-report.json` | отчёт (ниже) |

### Параметры

| параметр | по умолчанию | назначение |
|---|---|---|
| `--content FILE` | — | блочная разметка контента (или `content.rendered` при `--rendered`) |
| `--template` | `page` | `page`, `page-no-title`, любой slug шаблона из `--system`, или путь к `.html` |
| `--title` | `''` | заголовок страницы: `core/post-title` и `<title>` |
| `--out PREFIX` | — | префикс выходных файлов (папки создаются) |
| `--system DIR` | `redesign/system` | файлы дизайн-системы; ищутся `<slug>.html`, `parts/<slug>.html`, `templates/<slug>.html` |
| `--global-styles FILE` / `--css FILE` | из `--system` | переопределить global styles / `styles.css` |
| `--page-id N` | 1000 (49 при `--front`) | `body.page-id-N`, текущий пункт меню (`current-menu-item`, `aria-current`) |
| `--front` | нет | главная: `body.home`, `aria-current` у логотипа и названия сайта |
| `--rendered` [+ `--raw FILE`] | нет | вход — готовый HTML из REST; `--raw` — исходная разметка для точного CSS |
| `--site-title` / `--site-tagline` | `СВР` / `''` | для `core/site-title`, `core/site-tagline`, `<title>` (на локальном стенде описание — «Сервис водных ресурсов») |
| `--logo-id` / `--logo-alt` | 7 / название сайта | `core/site-logo` (0 — логотипа нет) |
| `--motion` | `reduce` | `prefers-reduced-motion` при съёмке; `no-preference` — исходные состояния анимаций |
| `--menu` | нет | снять открытое мобильное меню |
| `--check-widths 320,…` | — | доп. ширины для проверки горизонтального скролла |
| `--scale` | 1 | device scale factor скриншотов |
| `--no-shots` | нет | только HTML (+ report.json с предупреждениями эмулятора) |
| `--block-css FILE` | `wp-data/block-library.css` | CSS блоков (по умолчанию — из WP 7.1.3; запасной — `preview-assets/wp-block-library.css`) |

### Отчёт `<prefix>-report.json`

* `summary` — сводка счётчиков (то же печатается в консоль строкой «Итог: …»).
* `mobile_horizontal_scroll` — `scrollingElement.scrollWidth > clientWidth` на 390 px как есть и с
  принудительно отключённым `overflow` у `html/body` (`has_scroll_without_overflow_clip`: `body{overflow-x:clip}`
  не должен маскировать ошибки); `offenders` — элементы, вылезающие за ширину (корневые: родитель не вылезает),
  с селектором, координатами и текстом. Аналогично `desktop_horizontal_scroll`, `widths` (для `--check-widths`).
* `broken_images` (не загрузились / нет src), `failed_requests` (в т.ч. внешние запросы — сети нет).
* `empty_links` (нет доступного имени: текст/aria-label/alt/title), `links_without_href` (`href` пуст или `#`),
  `empty_buttons`.
* `h1_count` (+ тексты), `heading_outline`, `heading_level_skips` (h2 → h4 и т.п.).
* `low_contrast` — все тексты с контрастом < 4.5:1 (по вычисленным `color`/`background` предков, с учётом
  прозрачности, `opacity`, стопов градиентов — берётся худший случай, и полноразмерных фонов `::before/::after`);
  поле `aa_fail` учитывает крупный текст (≥ 24px или ≥ 18.66px bold → порог 3:1); `low_contrast_aa_fail` — только
  провалы AA; `contrast_uncertain` — текст поверх картинок (оценка по цвету под картинкой).
* `images_without_alt`, `images_empty_alt` (информативно; `decorative_cover` — фон обложки, `alt=""` там нормален).
* `duplicate_ids`, `animations` (сколько анимаций идёт и сколько бесконечных).
* `warnings` — предупреждения эмулятора: ключи global styles, которые **WordPress отбросит** при сохранении
  (не по схеме theme.json, незарегистрированные вариации стилей блоков, неизвестные блоки), HTML-теги в
  `styles.css` (REST API отклонит), незакрытые блоки и битый JSON атрибутов, неэмулируемые динамические блоки,
  пункты меню на несуществующие страницы, медиафайлы не из media.json, части шаблона/шаблоны, взятые из TT5.

## Что эмулируется (портировано из ядра WP 7.1.3)

* **Парсер блоков** `WP_Block_Parser` (в т.ч. самозакрывающиеся `/-->`, свободный HTML между блоками) и рендер
  дерева как `WP_Block::render()` (внутренние блоки рендерятся всегда, `core/navigation` рендерит детей
  повторно — поэтому номера `is-style-outline--N`, `modal-N`, `wp-elements-N` совпадают с WP).
* **Layout support** (`wp_render_layout_support_flag`): `is-layout-flow|constrained|flex|grid`,
  `wp-block-<name>-is-layout-*`, `has-global-padding`, `is-content-justification-*`, `is-vertical`, `is-nowrap`,
  классы `wp-container-<block>-is-layout-<hash>` **с тем же хэшем, что у WP** (`wp_unique_id_from_values`),
  CSS как `wp_get_layout_style()` (gap, justify, orientation, contentSize/wideSize, отрицательные отступы
  alignfull при своём padding, сетки columnCount/minimumColumnWidth), поиск внутренней обёртки (cover →
  `__inner-container`), дочерние размеры `wp-container-content-*` (fill/fixed/columnSpan + container query).
* **Global styles** = `default + blocks + TT5` (снято с WP: `wp-data/theme-base.json`) + ваш `global-styles.json`
  со слиянием как `WP_Theme_JSON::merge` (пресеты по источникам, замена списков), санитайз по схеме,
  `var:preset|…` → `var(--wp--preset--…)`, appearanceTools. CSS — как `wp_enqueue_global_styles()`:
  переменные (fluid typography → `clamp()` по формуле WP, с maxViewport = wideSize/maxViewportWidth), root layout
  rules (`--wp--style--root--padding-*`, `.has-global-padding`, `.wp-site-blocks`), `body`, элементы
  (`a`, `h1–h6`, `.wp-element-button`, caption; `:hover/:focus/…`; специфичность как в WP: `a:where(...)`
  и `h1` без обёртки, кнопки/подписи в `:root :where()`), классы пресетов `.has-*-color|background-color|
  border-color|gradient-background|font-size|font-family`, затем `styles.css`, **затем стили блоков**
  (`styles.blocks.*` — только для блоков, которые есть на странице: так делает `wp_add_global_styles_for_blocks`,
  и они идут ПОСЛЕ вашего CSS, при равной специфичности перебивая его), селекторы блоков/фич из block.json
  (`wp-data/blocks.json`), `css` блоков с `&`, вариации стилей блоков — отдельным стилем на каждый экземпляр
  (`is-style-outline--N`), брейкпоинты `@mobile/@tablet` у стилей блоков.
* **Block supports** у динамических блоков (`get_block_wrapper_attributes`: align, className, colors,
  typography, border, spacing, dimensions, shadow, anchor, aria-label) и render-фильтры: fluid font-size в
  inline-стиле, `wp-elements-*` (цвета ссылок/заголовков/кнопок в блоке), position sticky, background image,
  aspect-ratio, block visibility, custom CSS блока; белый список свойств `safecss_filter_attr`.
* **Динамические блоки:** `template-part` (тег по area/`tagName`), `post-title` (уровень, `isLink`),
  `post-content` (`entry-content`, `the_content`: do_blocks → wptexturize → wp_filter_content_tags),
  `site-logo` (ширина из атрибута, srcset), `site-title`, `site-tagline`, `navigation` (ul/li/a,
  `items-justified-*`, `is-responsive`, кнопки открытия/закрытия, оверлей с цветами `overlay*Color`,
  `hidden-by-default`/`always-shown` для overlayMenu `always`, aria-label с нумерацией как в WP, обёртка
  `li` для site-logo/site-title, разрыв `ul` перед не-li блоками вроде `core/buttons`), `navigation-link`,
  `navigation-submenu`, `page-list` (страницы из брифа — fallback меню с `ref`), `image` (+ lightbox: кнопка
  и оверлей), `gallery` (`wp-block-gallery-N`, `--wp--style--unstable-gallery-gap`), `heading`/`list`/
  `paragraph` (служебные классы `wp-block-heading`, `wp-block-list`, `wp-block-paragraph`), `button`
  (пустая кнопка не выводится; ширина `style.dimensions.width`), `post-featured-image` (пусто).
* **Медиа:** URL `https://svr-mos.ru/wp-content/uploads/…` → локальные файлы из `media.json`; производные
  размеры (`-300x144`, `-1024x490`, `-150x150`…) **генерируются** (Pillow, в `redesign/tmp/preview-cache/`) по
  правилам WP (`image_resize_dimensions`, обрезка по центру); `width/height`, `srcset`/`sizes`
  (`wp_calculate_image_srcset`), `loading="lazy"`/`fetchpriority="high"`, `sizes="auto, …"`, `decoding`.
* **Прочее:** skip-link «Перейти к содержимому» + `id` у `<main>`, классы `body`, `<title>`, wptexturize
  (ru_RU: «», –, —, …, ×), шрифты TT5 (те же woff2, что отдаёт сайт), строки интерфейса по-русски.

## Проверка точности: `oracle_compare.py`

Сравнение с настоящим WordPress 7.1.3. Нужна **приватная** копия стенда: `redesign/tmp/preview-oracle/`
(`core/ db/ router.php` — скопировано из `redesign/tmp/wp`; в неё пишутся тестовые данные, сайт и исходный стенд
`tmp/wp` не трогаются). Скрипт записывает в копию global styles, части шаблона, шаблон и контент страницы,
поднимает `php -S 127.0.0.1:8091`, рендерит обе версии и пишет `<out>-compare.json` (DOM-diff, разница
CSS-правил), `<out>-side-<w>.png` (WP | preview), `<out>-diff-<w>.png`.

```bash
python3 tools/oracle_compare.py --content tmp/preview-tests/t1-layout.html --template page \
    --title "Тестовая страница" --page-id 50 --out tmp/preview-tests/cmp/t1
```

Результаты на тестах из `redesign/tmp/preview-tests/` (система — актуальная `redesign/system`):

| тест | что внутри | DOM | CSS (WP-only/preview-only) | пиксели 1440 / 390 |
|---|---|---|---|---|
| t1-layout | group constrained/flex/grid, columns c blockGap, buttons + outline, list, цвета, fluid font-size, elements link color, contentSize | 100 % | 0/0* | 0,05 % / 0,05 % (кавычки: на стенде нет ru_RU) |
| t2-media | cover, image + lightbox, gallery + lightbox (с medium-размером), html+SVG, separator, table, spacer, кнопки | 100 % | 0/0* | 0 / 0 |
| p51 | реальная страница объекта (галерея 8 фото) | 100 % | 0/0* | 0 / 0 |
| t7-breadth | nav never/always/submenu, sticky, фон-картинка, flex fill/fixed, grid minColumnWidth+span, media-text, details, quote, file, image-ссылка c radius, vertical buttons, site-logo/tagline, post-title isLink | 100 % | 0/0* | 0,02 % / 0,06 % (ресемплинг превью-картинок) |
| t4/t5 rendered | `content.rendered` из REST (`--rendered`, t5 с `--raw`) | 100 % | 0/0* | 0 / 0 |
| меню | открытое мобильное меню (клик + Interactivity API в WP против `--menu`) | — | — | 0 |

\* единственное расхождение — URL логотипа в `styles.css` (у превью намеренно `file://`).

## Снимки (исправлено при аудите)

* Штатный `page.screenshot(full_page=True)` в Chromium нестабилен: при пересчёте размеров под съёмку уже загруженные
  картинки с `srcset` иногда не отрисовываются (на мобильной главной пропадали рендеры продукции и превью декларации
  примерно в половине запусков). Теперь `full_page_shot()`: окно растягивается на высоту документа, картинки ждутся
  и декодируются (`img.decode()`), снимается окно целиком, затем размер окна восстанавливается для аудита.
* Страницы выше 16 000 px (предел текстуры Chromium 16 384 px — ниже всё белое) снимаются кусками по 8 000 px с
  прокруткой и склейкой (`tiled_shot()`); липкие элементы на время съёмки переводятся в `relative` со сброшенными
  `top/bottom`, чтобы каждый кусок совпадал с рендером «на всю высоту».
* Браузер запускается через прокси-«тупик» `127.0.0.1:9`: даже не перехваченный маршрутом запрос наружу не уйдёт.
* `oracle_compare.py` снимает теми же функциями — сравнение с WP больше не «плавает» из-за пропавших картинок.
* Аудит: контраст не считает фоном узкие неповторяющиеся градиенты (подчёркивание `100% 2px` у телефона) и текст,
  обрезанный самим элементом (приём image replacement «Да/Нет» в ведомости, телефон-иконка в шапке); `ERR_ABORTED`
  у существующих файлов (браузер отменил кандидат `srcset`) не считается ошибкой загрузки.

## Инструменты аудита дизайн-системы

| скрипт | что делает |
|---|---|
| `audit_css.py` | `global-styles.json` + `styles.css`: структура, `var:preset` → существующие slug'и, синтаксис (tinycss2), каждый селектор и декларация через CSSOM Chromium, анимации вне `prefers-reduced-motion`, `:focus-visible`, опасные для оверлея меню свойства на `.svr-header` |
| `audit_markup.py` | шаблоны, части шаблона, сниппеты `components.md`, любая страница: баланс блоков, JSON атрибутов, className/align/fontSize/anchor/level ↔ HTML, ссылки и телефон, картинки ↔ media.json, RichText без `<span>/<br>`, h1, классы `svr-*` ↔ `styles.css` (мёртвые и без стилей) |
| `validate_blocks.py` | настоящий редактор WP 7.1.3 на локальном стенде: `isValid` у каждого блока + каноническая сериализация |
| `editor_check.py`, `site_editor_check.py`, `editor_css_check.py` | страницы и шаблоны в редакторе / Site Editor; применение `styles.css` в холсте и отсутствие перекрытий растянутыми ссылками |
| `gs_roundtrip.php` | POST global styles в локальный стенд → GET: что WP отбросил/изменил |
| `build_demo.py` | `system/demo-content.html` — демо-страница из всех 18 фрагментов `components.md` |
| `preview_pages.sh` | превью всех страниц 49–58 и шаблона 404 со всеми ширинами |
| `focus_check.py` | проход Tab по странице превью: у каждого фокуса виден контур (свой или `:focus-within` у карточки) |
| `slice_png.py` | нарезка длинного снимка на куски для просмотра |

## Данные ядра `tools/wp-data/`

| файл | откуда |
|---|---|
| `theme-base.json` | `WP_Theme_JSON_Resolver::get_merged_data('theme')` — core theme.json + block.json-стили + TT5 1.5 |
| `blocks.json` | метаданные 116 блоков: селекторы для global styles, supports, атрибуты по умолчанию, динамичность, style handles |
| `block-library.css` | `wp-includes/css/dist/block-library/style.css` + `common.css` из WP 7.1.3 |
| `safe-css.json` | белый список свойств `safecss_filter_attr` |
| `tt5/style.min.css`, `tt5/page*.html`, `tt5/*-fallback.html` | стили и шаблоны TT5 (запасные, если в `--system` чего-то нет) |
| `fonts/*.woff2` | Manrope и Fira Code из TT5 |
| `skip-link.min.css`, `wp-version.txt` | CSS skip-link, версия источника |

Пересобрать: `php tools/wp_dump_data.php <путь к wp core> tools/wp-data` (против локальной копии WP, не сайта).

## Ограничения эмуляции

1. **Локаль.** Типографика wptexturize — для ru_RU («кавычки»); локальный стенд без ru_RU выводит “кавычки”.
   wptexturize упрощён (тире, многоточие, кавычки, апостроф, ×); `convert_smilies`, шорткоды не выполняются.
2. **Неэмулируемые динамические блоки** (предупреждение в отчёте, вместо них пусто/HTML-комментарий):
   query/post-template, комментарии, post-date/author/excerpt, `core/pattern`, синхронизированные паттерны
   `core/block` (ref), архивы/категории/RSS, embed (oEmbed не разрешается), поиск. `core/navigation` с `ref`
   (запись wp_navigation) показывает список страниц из брифа.
3. **JS не выполняется** (Interactivity API): меню открывается только в снимке `--menu` (классы ставятся как у
   view-скрипта), lightbox не открывается; `aria-label` у кнопки lightbox ставит JS — она исключена из
   `empty_buttons`. Анимации: по умолчанию съёмка с `prefers-reduced-motion: reduce` и
   `animations: disabled`; появление по скроллу (view-timeline) в режиме `no-preference` в full-page снимке
   может остаться в начальном состоянии.
4. **Режим `--rendered` без `--raw`:** у `wp-container-*` нет исходных атрибутов — CSS восстанавливается по
   умолчаниям (flex: justify/orientation/nowrap по классам; constrained: только отступы alignfull по inline
   padding; grid: `auto-fill, minmax(12rem)`); свои gap, columnCount, contentSize и цвета `wp-elements-*`
   потеряются — каждый такой класс перечислен в предупреждениях. С `--raw` — точно.
5. **Картинки:** производные размеры генерирует Pillow — ресемплинг чуть отличается от GD/Imagick WP (разница
   видна только попиксельно). Отредактированные (`-e123…`) и `-scaled` вложения сводятся к оригиналу.
   `alt` логотипа `core/site-logo` — `--logo-alt` (в WP — alt из медиатеки или название сайта).
6. **Счётчики** `wp_unique_id` (`is-style-*--N`, `modal-N`, `wp-block-gallery-N`) совпадают с WP для
   поддержанных блоков; если на странице есть неэмулируемые блоки, номера могут сдвинуться (на вид не влияет).
7. **Валидность блоков в редакторе не проверяется:** сохранённый HTML выводится как есть; соответствие JSON
   атрибутов и HTML (то, из-за чего редактор пишет «блок содержит недопустимое содержимое») не сверяется —
   ловятся только незакрытые блоки и битый JSON.
8. **Санитайз global styles** — по схеме theme.json 7.1 (пишет, что WP отбросит); kses для не-админа и
   миграция схемы v2 → v3 не эмулируются. Пер-экземплярные состояния блоков (`style[":hover"]`, states.php)
   и responsive-классы навигации (`@mobile` у атрибутов блока) не эмулируются.
9. **CSS блоков** подключается целиком (WP грузит только стили блоков страницы) — визуально не влияет.
   Admin bar, Customizer CSS, плагины (Yoast) не эмулируются; вид — для неавторизованного посетителя.
10. **Аудит приближённый:** контраст — по вычисленным цветам предков (градиенты — худший стоп, фон-картинка →
    `contrast_uncertain`, `::before/::after` учитываются, если перекрывают элемент целиком), SVG-текст и
    `text-shadow` не учитываются; скролл и «вылезающие» элементы — по `getBoundingClientRect`,
    элементы внутри контейнеров с `overflow`≠visible и `position:fixed` не считаются.
