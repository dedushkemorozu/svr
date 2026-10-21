# Редизайн svr-mos.ru («Чертёж»)

Рабочие материалы редизайна (WordPress 7.1.3, тема Twenty Twenty-Five).

- `deploy/` — пакет публикации: `manifest.json`, `global-styles.json`, `parts/`, `templates/`, `pages/`, `shots/`, `README.md` (порядок применения, откат).
- `system/` — исходники дизайн-системы: `styles.css`, шапка/подвал/шаблоны, `components.md`.
- `tools/` — сборка и проверка (`rebuild.sh`, `build_system.py`, `preview.py`, `validate_blocks.py` и др.). Пути в скриптах абсолютные от облачной среды — при локальной работе поправьте.
- `assets/svg/` — SVG капли и иконок; `spec.md` — спецификация; `brief.md` — бриф и факты; `media.json` — карта медиатеки.
- `new-product-images/` — 5 новых изображений продукции (1 КНС, 2 УКО, 3 станция дозирования, 4 реактор трёхкамерный, 5 реактор однокамерный). **Уже загружены на сайт и опубликованы**: медиатека id 125 (станция дозирования), 126 (УКО), 127 (КНС), 128 (реактор трёхкамерный), 129 (реактор однокамерный) — используются на главной (49), /prod/ (55) и всех пяти страницах продукции (140–144) вместо старых CAD-рендеров (id 13–17, остались в медиатеке неиспользуемыми). См. media.json.
- `backup-before-*.json` — резервные копии состояния сайта перед публикациями.

На сайте сейчас опубликован пакет из `deploy/` (страницы 49–58, 140–144 — продукция).

## Работа локально
1. `git fetch origin main-kshiz8 && git checkout main-kshiz8`, затем в папке проекта: `sh setup_local.sh` (заменит пути облака на ваши и проверит python3, php, node, Pillow, playwright).
2. Нужно: Python 3 + `pip install pillow playwright` + `playwright install chromium` (или `CHROME_PATH=/путь/к/chrome`), PHP 8.x с sqlite.
3. Превью страниц без WordPress: `python3 tools/preview.py --content deploy/pages/49.html --template page-no-title --front --out out/49` (см. `tools/README.md`). Картинки в превью берутся из `svr-mos.ru-backup/` (нужен репозиторий целиком) по `media.json`.
4. Локальный стенд WordPress 7.1.3 (для строгой валидации блоков, `tools/rebuild.sh`) в репозиторий не вошёл: поднимается из исходников WordPress (`git clone --branch 7.1.3 https://github.com/WordPress/WordPress`) + SQLite-плагин по `tools/wp_setup.php`/`tools/README.md`.
5. Публикация на сайт — через WordPress-коннектор svr (Claude Code), порядок шагов в `deploy/README.md` и `deploy/manifest.json`.
