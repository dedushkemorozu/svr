#!/usr/bin/env bash
# Создаёт категории WooCommerce с нужными адресами (slug). Запустить ОДИН раз из папки сайта ДО импорта товаров:
#   cd /путь/к/wordpress && bash create_categories.sh
set -e
wp term create product_cat "Новинки" --slug=new
wp term create product_cat "Ангелы" --slug=angels
wp term create product_cat "Домики" --slug=houses
wp term create product_cat "Маяки" --slug=mayak
wp term create product_cat "Птицы" --slug=birds
wp term create product_cat "Лошадки" --slug=horse
wp term create product_cat "Грибы" --slug=mush
wp term create product_cat "Наборы" --slug=nabory
wp term create product_cat "Весенняя и пасхальная коллекция" --slug=spring
wp term create product_cat "Новогодние подарки" --slug=new-year
SPRING=$(wp term list product_cat --slug=spring --field=term_id)
wp term create product_cat "Пасхальные стеклянные яйца с росписью" --slug=easter-glass-eggs --parent="$SPRING"
wp term create product_cat "Пасхальные деревянные яйца с росписью" --slug=easter-wooden-eggs --parent="$SPRING"
wp term create product_cat "Пасхальные ангелы" --slug=easter-angels --parent="$SPRING"
wp term create product_cat "Пасхальные подвески" --slug=easter-pendants --parent="$SPRING"
wp term create product_cat "Пасхальные наборы" --slug=easter-sets --parent="$SPRING"
