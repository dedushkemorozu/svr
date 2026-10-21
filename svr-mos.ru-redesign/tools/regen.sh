#!/bin/sh
# Быстрый цикл правок: CSS→JSON, генератор страниц → каноника редактора WP → deploy/pages, пакет deploy/.
# (полная проверка — tools/rebuild.sh)
set -e
cd "$(dirname "$0")/.."
python3 tools/make_drops.py >/dev/null
python3 tools/make_icons.py
python3 tools/build_system.py
python3 tools/components_src.py
python3 tools/validate_blocks.py --out tmp/canon-gen tmp/pages/*.html | grep -v "^OK" || true
for i in 49 50 51 52 53 54 55 56 57 58 prod-stanciya-dozirovaniya prod-reaktor-trehkamernyj prod-reaktor-odnokamernyj prod-ustanovka-obezzarazhivaniya prod-kns; do cp tmp/canon-gen/$i.html deploy/pages/$i.html; done
python3 tools/build_deploy.py
