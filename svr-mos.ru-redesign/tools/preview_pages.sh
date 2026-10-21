#!/bin/sh
# Превью всех страниц сайта (49…58) и шаблона 404 через tools/preview.py. Результат: $O/<id>-*.png, -report.json
# Запуск: sh tools/preview_pages.sh [ширины для проверки скролла]
# Переменные окружения (необязательно): SYS — папка дизайн-системы (по умолчанию system),
#   PAGES — папка с разметкой страниц <id>.html (по умолчанию deploy/pages, если есть, иначе tmp/canon),
#   O — папка результатов (по умолчанию tmp/audit/pages), MENU=1 — снимать открытое мобильное меню,
#   LOGO_ALT — alt логотипа шапки (как в медиатеке после деплоя).
cd "$(dirname "$0")/.."
W=${1:-320,360,375,390,414,430,600,768,1024,1280,1440}
SYS=${SYS:-system}
if [ -z "$PAGES" ]; then if [ -d deploy/pages ]; then PAGES=deploy/pages; else PAGES=tmp/canon; fi; fi
O=${O:-tmp/audit/pages}; mkdir -p $O
LOGO_ALT=${LOGO_ALT:-ООО «СВР» — на главную}
M=""; [ -n "$MENU" ] && M="--menu"
printf '49: '; python3 tools/preview.py --system $SYS --content $PAGES/49.html --template page-no-title --title "Главная" --front --logo-alt "$LOGO_ALT" --out $O/49 --check-widths $W $M | tail -1
# Шаблон страниц объектов: wp-custom-template-obekt (крошки «Главная / Наши объекты / …»), если он есть в $SYS
OBJ_T=page; [ -f $SYS/wp-custom-template-obekt.html ] && OBJ_T=wp-custom-template-obekt
for x in "50|page|Наши объекты" "51|$OBJ_T|ОАО «Элтеза»" "52|$OBJ_T|ОАО «Мясокомбинат «Рузский»" "53|$OBJ_T|ОС3 Марьино-Саларьево (II этап)" \
         "54|$OBJ_T|ОС2 Марьино-Саларьево (II этап)" "55|page|Наша продукция" "56|page|Документы" "57|page|Реквизиты компании" "58|page|Контакты"; do
  id=${x%%|*}; r=${x#*|}; tp=${r%%|*}; t=${r#*|}
  printf '%s: ' $id; python3 tools/preview.py --system $SYS --content $PAGES/$id.html --template $tp --title "$t" --page-id $id --logo-alt "$LOGO_ALT" --out $O/$id --check-widths $W $M | tail -1
done
# Страницы продукции (дочерние /prod/, шаблон wp-custom-template-produkciya, родитель 55)
PROD_T=page; [ -f $SYS/wp-custom-template-produkciya.html ] && PROD_T=wp-custom-template-produkciya
for x in "stanciya-dozirovaniya|Станции дозирования и приготовления реагентов двухкамерные" "reaktor-trehkamernyj|Реактор трёхкамерный" \
         "reaktor-odnokamernyj|Реактор однокамерный" "ustanovka-obezzarazhivaniya|Установка комплексного обеззараживания сточных вод" \
         "kns|Канализационные насосные станции"; do
  sl=${x%%|*}; t=${x#*|}
  [ -f $PAGES/prod-$sl.html ] || continue
  printf 'prod-%s: ' $sl; python3 tools/preview.py --system $SYS --content $PAGES/prod-$sl.html --template $PROD_T --title "$t" --page-id 1055 --parent-id 55 --logo-alt "$LOGO_ALT" --out $O/prod-$sl --check-widths $W $M | tail -1
done
printf '404: '; printf '' > $O/empty.html
python3 tools/preview.py --system $SYS --content $O/empty.html --template 404 --title "Страница не найдена" --logo-alt "$LOGO_ALT" --out $O/404 --check-widths $W $M | tail -1
