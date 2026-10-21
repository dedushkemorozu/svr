#!/bin/sh
# Полный цикл: CSS→JSON, аудит, фрагменты components.md → валидация, пакет deploy/ → строгая валидация в редакторе WP
# → деплой пакета на ЛОКАЛЬНЫЙ стенд по deploy/manifest.json (те же REST-маршруты, что на сайте) + сверка.
#
# ВАЖНО (после ревью страниц): источник правды для страниц — deploy/pages/<id>.html. Их правят вручную, скрипты
# их НЕ перезаписывают. Генератор components_src.py пишет только черновики tmp/pages/ (каноника — tmp/canon-gen/)
# и фрагменты для components.md (tmp/frag → tmp/canon/NN-*.html). Шаблоны и части — system/ (копируются в deploy/).
set -e
cd "$(dirname "$0")/.."
python3 tools/build_system.py
python3 tools/audit_css.py | sed -n '1,4p'
python3 tools/components_src.py
python3 tools/build_components_md.py frags
python3 tools/validate_blocks.py tmp/frag/*.html | grep -v "^OK" || true
python3 tools/validate_blocks.py --out tmp/canon-gen tmp/pages/*.html | grep -v "^OK" || true
# Генератор и пакет не должны расходиться: каноника генератора == deploy/pages (иначе перенесите правку туда, где её нет)
for f in deploy/pages/*.html; do cmp -s "$f" "tmp/canon-gen/$(basename "$f")" || echo "DRIFT: $f ≠ tmp/canon-gen/$(basename "$f") (components_src.py)"; done
python3 tools/build_components_md.py md
python3 tools/build_demo.py
python3 tools/validate_blocks.py system/demo-content.html | grep -v "^OK" || true
python3 tools/build_deploy.py
# Пакет: каждый блок isValid и сериализация редактора побайтно равна файлу (--strict); при ошибке деплоя нет
python3 tools/validate_blocks.py --strict --out tmp/canon-deploy deploy/parts/*.html deploy/templates/*.html deploy/pages/*.html > tmp/validate-deploy.log
grep -v "^OK" tmp/validate-deploy.log || true
python3 tools/audit_markup.py deploy/parts/*.html deploy/templates/*.html deploy/pages/*.html system/components.md | tail -6
php tools/apply_manifest.php | grep -v "^20[01] \|^OK " || true
