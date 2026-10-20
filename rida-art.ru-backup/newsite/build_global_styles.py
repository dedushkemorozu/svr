# -*- coding: utf-8 -*-
"""Собирает тело запроса для POST /wp/v2/global-styles/<id> (палитра, шрифты, стили, CSS)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = 'https://rida-art.ru/wp-content/themes/twentytwentyfive/assets/fonts/'

palette = [
    {'slug': 'base', 'name': 'Фон', 'color': '#F6F4EF'},
    {'slug': 'contrast', 'name': 'Графит', 'color': '#1C1C1A'},
    {'slug': 'accent-1', 'name': 'Хвоя', 'color': '#2F4A3E'},
    {'slug': 'accent-2', 'name': 'Лён', 'color': '#EEEBE4'},
    {'slug': 'accent-3', 'name': 'Хвоя тёмная', 'color': '#2F4A3E'},
    {'slug': 'accent-4', 'name': 'Серый', 'color': '#706C65'},
    {'slug': 'accent-5', 'name': 'Линия', 'color': '#E0DBD2'},
    {'slug': 'accent-6', 'name': 'Песок', 'color': '#B5AC9E'},
]

body = {
    'settings': {
        'color': {'palette': {'theme': palette}},
        'typography': {'fontFamilies': {'custom': []}},
        'layout': {'contentSize': '720px', 'wideSize': '1360px'},
    },
    'styles': {
        'color': {'background': 'var:preset|color|base', 'text': 'var:preset|color|contrast'},
        'typography': {'fontFamily': 'var:preset|font-family|manrope', 'fontSize': '1.0625rem',
                       'lineHeight': '1.7', 'letterSpacing': '0', 'fontWeight': '400'},
        'elements': {
            'heading': {'typography': {'fontFamily': 'var:preset|font-family|manrope', 'fontWeight': '400',
                                       'lineHeight': '1.1', 'letterSpacing': '-0.025em'},
                        'color': {'text': 'var:preset|color|contrast'}},
            'link': {'color': {'text': 'var:preset|color|contrast'},
                     'typography': {'textDecoration': 'underline'},
                     ':hover': {'color': {'text': 'var:preset|color|accent-4'}}},
            'button': {'color': {'background': 'var:preset|color|contrast', 'text': 'var:preset|color|base'},
                       'border': {'radius': '0'},
                       'spacing': {'padding': {'top': '1.05em', 'bottom': '1.05em', 'left': '2.2em', 'right': '2.2em'}},
                       'typography': {'fontSize': '0.9rem', 'fontWeight': '500', 'letterSpacing': '0.01em'},
                       ':hover': {'color': {'background': 'var:preset|color|accent-1', 'text': 'var:preset|color|base'}}},
            'caption': {'typography': {'fontSize': '0.8rem'}, 'color': {'text': 'var:preset|color|accent-4'}},
        },
        'blocks': {
            'core/navigation': {'typography': {'fontSize': '0.88rem', 'fontWeight': '400'}},
            'core/quote': {'typography': {'fontStyle': 'normal'}},
        },
        'css': open(os.path.join(HERE, 'rida.css'), encoding='utf-8').read(),
    },
}
out = os.path.join(HERE, 'out', 'global_styles.json')
json.dump(body, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(out, os.path.getsize(out))

