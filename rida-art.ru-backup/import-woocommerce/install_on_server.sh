#!/usr/bin/env bash
# =============================================================================
# Установка WordPress + WooCommerce для rida-art.ru и подготовка к импорту.
#
# ЗАПУСКАТЬ НА СЕРВЕРЕ (по SSH), под своим пользователем хостинга:
#     bash ~/import-woocommerce/install_on_server.sh
#
# Что делает:
#   1. проверяет PHP, расширения и подключение к базе данных;
#   2. скачивает WordPress (русская сборка) с wordpress.org в папку сайта;
#   3. создаёт wp-config.php (пароль базы нужен WordPress, больше он нигде не сохраняется);
#   4. устанавливает сайт, плагины WooCommerce, Cyr-To-Lat (транслитерация адресов), WordPress Importer;
#   5. настраивает рубли, часовой пояс, адреса вида /имя-страницы/, закрывает сайт от поисковиков;
#   6. создаёт категории товаров и загружает страницы (pages_import.xml);
#   7. копирует картинки в wp-content/uploads/rida-import/.
# Товары импортируются потом через админку (см. README.md рядом).
#
# Ничего не удаляет в уже существующих файлах: если в папке сайта что-то лежит,
# скрипт покажет список и спросит подтверждение.
#
# Настройки можно переопределить переменными окружения, например:
#     TARGET_DIR=/var/www/u0965861/data/www/rida-art.ru bash install_on_server.sh
# Чтобы не вводить данные вручную, можно заранее задать DB_PASS, WP_ADMIN, WP_EMAIL, WP_ADMIN_PASS.
# =============================================================================
set -euo pipefail

TARGET_DIR="${TARGET_DIR:-$HOME/rida-art}"
SITE_URL="${SITE_URL:-http://rida-art.ru}"
SITE_TITLE="${SITE_TITLE:-Рида Арт}"
DB_NAME="${DB_NAME:-u0965861_ridawp}"
DB_USER="${DB_USER:-u0965861_ridawp}"
DB_HOST="${DB_HOST:-localhost}"
DB_PREFIX="${DB_PREFIX:-rida_}"
PHP_BIN="${PHP_BIN:-php}"
PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/bin"

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
warn() { printf '\033[33m! %s\033[0m\n' "$*" >&2; }
die()  { printf '\033[31mОШИБКА: %s\033[0m\n' "$*" >&2; exit 1; }
ask_yes() { local a; read -r -p "$1 [yes/N] " a; [ "$a" = "yes" ]; }

# ---- 1. Проверки -------------------------------------------------------------
say "Проверка окружения"
command -v "$PHP_BIN" >/dev/null 2>&1 || die "не найден PHP ($PHP_BIN). Задайте PHP_BIN=/путь/к/php (в панели хостинга выберите PHP 8.1+)"
"$PHP_BIN" -r 'exit(version_compare(PHP_VERSION, "7.4", "<") ? 1 : 0);' || die "нужен PHP 7.4 или новее, сейчас: $("$PHP_BIN" -r 'echo PHP_VERSION;')"
echo "PHP $("$PHP_BIN" -r 'echo PHP_VERSION;')"
for ext in mysqli curl mbstring xml zip gd; do
  "$PHP_BIN" -m | grep -qix "$ext" || warn "у PHP нет расширения $ext — может понадобиться включить в панели хостинга"
done
if command -v curl >/dev/null 2>&1; then
  fetch() { curl -fsSL --retry 3 -o "$2" "$1"; }
elif command -v wget >/dev/null 2>&1; then
  fetch() { wget -q -O "$2" "$1"; }
else
  die "нужен curl или wget"
fi
command -v tar >/dev/null 2>&1 || die "нужен tar"
[ -f "$PKG_DIR/pages_import.xml" ] || die "рядом со скриптом нет pages_import.xml — скопируйте на сервер всю папку import-woocommerce"

# ---- 2. Папка сайта ----------------------------------------------------------
say "Папка сайта: $TARGET_DIR"
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"
if [ -e wp-config.php ] || [ -e wp-load.php ]; then
  die "в $TARGET_DIR уже есть WordPress. Скрипт ставит только на чистое место."
fi
if [ -n "$(ls -A "$TARGET_DIR")" ]; then
  echo "В папке уже есть файлы:"
  ls -la "$TARGET_DIR"
  ask_yes "Продолжить установку В ЭТУ папку (существующие файлы не удаляются, но одноимённые будут заменены)?" || die "остановлено по вашему решению"
fi

# ---- 3. Данные для установки -------------------------------------------------
say "Данные для установки (нигде, кроме wp-config.php, не сохраняются)"
if [ -z "${DB_PASS:-}" ]; then read -r -s -p "Пароль базы данных $DB_NAME: " DB_PASS; echo; fi
[ -n "$DB_PASS" ] || die "пустой пароль базы"
if [ -z "${WP_ADMIN:-}" ]; then read -r -p "Логин администратора сайта (не 'admin'): " WP_ADMIN; fi
[ -n "$WP_ADMIN" ] || die "пустой логин"
[ "$WP_ADMIN" != "admin" ] || warn "логин 'admin' подбирают первым — лучше выбрать другой"
if [ -z "${WP_EMAIL:-}" ]; then read -r -p "E-mail администратора: " WP_EMAIL; fi
case "$WP_EMAIL" in *@*.*) ;; *) die "некорректный e-mail";; esac
if [ -z "${WP_ADMIN_PASS:-}" ]; then
  read -r -s -p "Пароль администратора сайта (придумайте длинный): " WP_ADMIN_PASS; echo
  read -r -s -p "Повторите пароль: " pass2; echo
  [ "$WP_ADMIN_PASS" = "$pass2" ] || die "пароли не совпали"
fi
[ "${#WP_ADMIN_PASS}" -ge 12 ] || warn "пароль короче 12 символов"

say "Проверка подключения к базе"
tables="$(DB_HOST="$DB_HOST" DB_USER="$DB_USER" DB_PASS="$DB_PASS" DB_NAME="$DB_NAME" "$PHP_BIN" <<'PHP'
<?php
mysqli_report(MYSQLI_REPORT_OFF);
$m = @new mysqli(getenv('DB_HOST'), getenv('DB_USER'), getenv('DB_PASS'), getenv('DB_NAME'));
if ($m->connect_errno) { fwrite(STDERR, "подключиться не удалось: " . $m->connect_error . "\n"); exit(1); }
$r = $m->query('SHOW TABLES');
echo $r ? $r->num_rows : 0;
PHP
)" || die "не удалось подключиться к базе $DB_NAME (проверьте имя, пользователя и пароль в панели хостинга)"
echo "подключение успешно, таблиц в базе: $tables"
if [ "$tables" != "0" ]; then
  warn "база не пуста"
  ask_yes "Всё равно использовать эту базу (префикс таблиц: $DB_PREFIX)?" || die "остановлено по вашему решению"
fi

# ---- 4. WordPress ------------------------------------------------------------
say "Скачиваю WordPress (ru_RU)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
fetch "https://ru.wordpress.org/latest-ru_RU.tar.gz" "$tmp/wp.tgz" || die "не удалось скачать WordPress"
tar -xzf "$tmp/wp.tgz" --strip-components=1 -C "$TARGET_DIR"
[ -f wp-config-sample.php ] || die "в архиве нет wp-config-sample.php"

say "Создаю wp-config.php"
DB_HOST="$DB_HOST" DB_USER="$DB_USER" DB_PASS="$DB_PASS" DB_NAME="$DB_NAME" DB_PREFIX="$DB_PREFIX" "$PHP_BIN" <<'PHP'
<?php
$c = file_get_contents('wp-config-sample.php');
if ($c === false) { fwrite(STDERR, "нет wp-config-sample.php\n"); exit(1); }
$set = function ($const, $value) use (&$c) {
    $val = var_export($value, true);
    $c = preg_replace_callback("/(define\(\s*'" . $const . "'\s*,\s*)'[^']*'/", function ($m) use ($val) { return $m[1] . $val; }, $c, 1, $n);
    if ($n !== 1) { fwrite(STDERR, "в wp-config-sample.php не найдено $const\n"); exit(1); }
};
$set('DB_NAME', getenv('DB_NAME'));
$set('DB_USER', getenv('DB_USER'));
$set('DB_PASSWORD', getenv('DB_PASS'));
$set('DB_HOST', getenv('DB_HOST'));
foreach (['AUTH_KEY', 'SECURE_AUTH_KEY', 'LOGGED_IN_KEY', 'NONCE_KEY', 'AUTH_SALT', 'SECURE_AUTH_SALT', 'LOGGED_IN_SALT', 'NONCE_SALT'] as $k) {
    $set($k, bin2hex(random_bytes(32)));
}
$prefix = var_export(getenv('DB_PREFIX'), true);
$c = preg_replace_callback('/\$table_prefix\s*=\s*\'[^\']*\';/', function () use ($prefix) { return '$table_prefix = ' . $prefix . ';'; }, $c, 1, $n);
if ($n !== 1) { fwrite(STDERR, "не найден \$table_prefix\n"); exit(1); }
$c = str_replace("/* That's all, stop editing!", "define('WP_MEMORY_LIMIT', '256M');\n\n/* That's all, stop editing!", $c);
file_put_contents('wp-config.php', $c);
chmod('wp-config.php', 0640);
PHP
grep -q "database_name_here\|username_here\|password_here" wp-config.php && die "wp-config.php собран некорректно"

# ---- 5. WP-CLI ---------------------------------------------------------------
say "Скачиваю WP-CLI (инструмент установки)"
mkdir -p "$BIN_DIR"
fetch "https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar" "$BIN_DIR/wp-cli.phar" || die "не удалось скачать WP-CLI"
cat > "$BIN_DIR/wp" <<EOF
#!/usr/bin/env bash
exec "$PHP_BIN" -d memory_limit=512M "$BIN_DIR/wp-cli.phar" "\$@"
EOF
chmod +x "$BIN_DIR/wp"
export PATH="$BIN_DIR:$PATH"
wp --info >/dev/null || die "WP-CLI не запускается"

# ---- 6. Установка сайта и плагинов ------------------------------------------
say "Устанавливаю сайт ($SITE_URL)"
wp core install --url="$SITE_URL" --title="$SITE_TITLE" --admin_user="$WP_ADMIN" \
   --admin_password="$WP_ADMIN_PASS" --admin_email="$WP_EMAIL" --skip-email

say "Плагины"
wp plugin install cyr2lat --activate || warn "Cyr-To-Lat не установился — адреса товаров будут на кириллице; поставьте плагин из админки до импорта товаров"
wp plugin install woocommerce --activate
wp plugin install wordpress-importer --activate
wp plugin delete hello akismet 2>/dev/null || true

say "Настройки"
wp option update blogdescription "Мастерская сказочных игрушек"
wp option update timezone_string "Europe/Moscow"
wp option update date_format "j F Y"
wp option update time_format "H:i"
wp option update blog_public 0          # закрыто от поисковиков до запуска; включить: Настройки → Чтение
wp rewrite structure '/%postname%/'
wp rewrite flush --hard || warn "не удалось записать .htaccess — проверьте права на папку"
wp option update woocommerce_currency RUB
wp option update woocommerce_default_country "RU:MOW"
wp option update woocommerce_currency_pos right_space
wp option update woocommerce_price_num_decimals 0
wp option update woocommerce_price_thousand_sep " "
wp option update woocommerce_weight_unit kg
wp option update woocommerce_dimension_unit cm

say "Убираю демо-контент WordPress"
for id in $(wp post list --post_type=post --name=hello-world --format=ids); do wp post delete "$id" --force; done
for id in $(wp post list --post_type=page --name=sample-page --format=ids); do wp post delete "$id" --force; done
# черновик «Политика конфиденциальности» из коробки занимает адрес /privacy-policy/
for id in $(wp post list --post_type=page --name=privacy-policy --post_status=draft --format=ids); do wp post delete "$id" --force; done
wp option update wp_page_for_privacy_policy 0

# ---- 7. Категории, страницы, картинки ---------------------------------------
say "Категории товаров"
if [ -f "$PKG_DIR/create_categories.sh" ]; then
  bash "$PKG_DIR/create_categories.sh"
else
  warn "нет create_categories.sh — создайте категории вручную"
fi

say "Страницы (О нас, Контакты, Доставка и оплата, Оферта ...)"
wp import "$PKG_DIR/pages_import.xml" --authors=skip

say "Картинки"
mkdir -p "$TARGET_DIR/wp-content/uploads"
cp -r "$PKG_DIR/uploads/rida-import" "$TARGET_DIR/wp-content/uploads/"
echo "скопировано: $(find "$TARGET_DIR/wp-content/uploads/rida-import" -type f | wc -l) файлов"

say "ГОТОВО"
cat <<EOM
WordPress и WooCommerce установлены в $TARGET_DIR.
Админка: $SITE_URL/wp-admin/   (логин: $WP_ADMIN)

Если сайт по адресу $SITE_URL ещё не открывается (DNS не переключён), на своём компьютере добавьте
в файл hosts строку «37.140.192.134 rida-art.ru» (см. README.md) — тогда новый сайт увидите только вы.

Дальше: Товары → Импорт → $PKG_DIR/products_import.csv (подробности — README.md).
Сайт закрыт от поисковиков (Настройки → Чтение). Не забудьте открыть его при запуске.
EOM
