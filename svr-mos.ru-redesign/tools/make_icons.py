"""Набор иконок 6 этапов (assets/svg/stage-icons.html): сетка 48×48, штрих 2, round caps/joins, светлый штрих + один голубой акцент.
Запуск: python3 tools/make_icons.py"""
# рабочий файл для набора иконок: пишет redesign/assets/svg/stage-icons.html
A = '#0EB8DA'
HEAD = '<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
def acc(d, fill=False, extra=''):
    fl = f' fill="{A}" fill-opacity=".2"' if fill else ''
    return f'<path d="{d}" stroke="{A}"{fl}{extra}/>'
def light(d, extra=''):
    return f'<path d="{d}"{extra}/>'
icons = {}
# 01 Обследование: резервуар с уровнем воды + лупа (акцент)
icons['01'] = ('Обследование — резервуар под лупой',
  light('M8 7h14a2 2 0 0 1 2 2v30a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2z')
  + light('M6 24c2-1.8 3.6-1.8 6 0s4 1.8 6 0 3.4-1.6 6 0')
  + light('M6 15h4M6 32h4')
  + f'<circle cx="34" cy="28" r="7.5" stroke="{A}" fill="{A}" fill-opacity=".16"/>' + acc('M39.4 33.4 44 38'))
# 02 Лаборатория: колба + капля
icons['02'] = ('Лаборатория — колба с каплей',
  light('M18 6h12M20 6v11L9.6 36.6A4 4 0 0 0 13.2 42h21.6a4 4 0 0 0 3.6-5.4L28 17V6')
  + light('M13.5 30h21')
  + acc('M24 25.5c2.2 3 3.6 4.6 3.6 6.6a3.6 3.6 0 0 1-7.2 0c0-2 1.4-3.6 3.6-6.6z', fill=True))
# 03 Технологические решения: схема, ветвление потока
icons['03'] = ('Технологические решения — схема с ветвлением',
  light('M17 6h14a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H17a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z')
  + light('M24 16v6M10 28v-3a3 3 0 0 1 3-3h22a3 3 0 0 1 3 3v3')
  + light('M5 30h10a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H5z'.replace('M5 30h10a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H5z','M6 28h8a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2z'))
  + acc('M34 28h8a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2h-8a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2z', fill=True)
  + acc('M35.5 33l2 2 3-3.5'))
# 04 Проектирование: лист + карандаш
icons['04'] = ('Проектирование — чертёжный лист и карандаш',
  light('M30 6H12a2 2 0 0 0-2 2v32a2 2 0 0 0 2 2h14M30 6l8 8v7M30 6v6a2 2 0 0 0 2 2h6')
  + light('M16 22h12M16 29h7')
  + acc('M41.2 26.8a2.2 2.2 0 0 1 0 3.1L30 41.1l-5 1.4 1.4-5 11.2-11.2a2.2 2.2 0 0 1 3.1 0z', fill=True)
  + acc('M37 31l-3.1-3.1'))
# 05 Оборудование: реактор с мешалкой
icons['05'] = ('Оборудование — реактор с мешалкой',
  light('M12 15h24v17a9 9 0 0 1-9 9h-6a9 9 0 0 1-9-9z')
  + light('M12 15c0-3 5-4.5 12-4.5S36 12 36 15')
  + light('M12 24c3-2 4.5-2 6 0s4.5 2 6 0 4.5-2 6 0 3 1 6 0')
  + light('M20 5h8v5.5h-8z').replace('M20 5h8v5.5h-8z','M20.5 4h7a1.5 1.5 0 0 1 1.5 1.5V9H19V5.5A1.5 1.5 0 0 1 20.5 4z')
  + acc('M24 10.5V33')
  + acc('M18 33h12'))
# 06 Пусконаладка: задвижка
icons['06'] = ('Пусконаладка — задвижка со штурвалом',
  light('M4 32h8M36 32h8')
  + light('M12 24v16l12-8zM36 24v16l-12-8z')
  + acc('M24 32V17')
  + acc('M13 13.5c0-1.4 5-2.5 11-2.5s11 1.1 11 2.5-5 2.5-11 2.5-11-1.1-11-2.5z', fill=True))
import pathlib
out=['<!-- Иконки этапов, 48×48, единый набор: штрих 2, скруглённые концы и соединения, светлый штрих currentColor (--svr-ink) + один голубой акцент (#0EB8DA) на иконку. Вставляются в core/html: <span class="svr-stage__ico" aria-hidden="true">…</span> -->']
for k,(t,body) in icons.items():
    out.append(f'<!-- {k} {t} -->')
    out.append(HEAD+body+'</svg>')
(pathlib.Path(__file__).resolve().parent.parent/'assets/svg/stage-icons.html').write_text('\n'.join(out)+'\n')
