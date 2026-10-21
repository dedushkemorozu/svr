#!/bin/sh
# Локальная настройка: заменяет абсолютные пути облачной среды на пути вашего клона и проверяет зависимости.
# Запуск из папки svr-mos.ru-redesign:  sh setup_local.sh
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
OLD_RED="/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign"
OLD_SCR="/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad"
OLD_REPO="/home/user/svr"
OLD_CHROME="/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
for f in $(grep -rlE "/tmp/claude-0|/home/user/svr" "$ROOT" --include="*.py" --include="*.php" --include="*.sh" --include="*.md" --include="*.json" --include="*.html" | grep -v "backup-before"); do
  [ "$f" = "$ROOT/setup_local.sh" ] && continue
  sed -i -e "s#$OLD_RED#$ROOT#g" -e "s#$OLD_SCR#$ROOT#g" -e "s#$OLD_REPO#$REPO#g" "$f"
done
echo "Пути заменены на: $ROOT"
CHROME="${CHROME_PATH:-}"
echo "--- зависимости ---"
for c in python3 php node; do command -v $c >/dev/null && echo "ok: $c" || echo "НЕТ: $c"; done
python3 -c "import PIL, playwright; print('ok: Pillow, playwright')" 2>/dev/null || echo "НЕТ: pip install pillow playwright && playwright install chromium"
echo "Если Chromium лежит не в $OLD_CHROME, замените путь в tools/pwlib.py (поиск executable_path)."
