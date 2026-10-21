"""Сборка system/global-styles.json из токенов (spec.md §2–4, §10.1) и system/styles.css.
Запуск: python3 tools/build_system.py"""
import json, pathlib, re, sys

R = pathlib.Path(__file__).resolve().parent.parent
SYS = R / 'system'
css = (SYS / 'styles.css').read_text(encoding='utf-8')

# Защита: REST /wp/v2/global-styles отклоняет CSS с разметкой (</style и т. п.); не допускаем «<» вообще.
assert '<' not in css, 'В styles.css не должно быть символа "<" (только %3C в data-URI)'
assert css.count('{') == css.count('}'), 'Несбалансированные фигурные скобки в styles.css'

P = 'var:preset|color|'
palette = [
    ('base', '#071B2F', 'Основной фон'), ('contrast', '#E8F1F8', 'Основной текст'),
    ('accent-1', '#0EB8DA', 'Циан'), ('accent-2', '#0089BF', 'Синий (только графика)'),
    ('accent-3', '#7FDCF2', 'Светлый циан'), ('accent-4', '#A9BFD3', 'Вторичный текст'),
    ('accent-5', '#0B2540', 'Поверхность'), ('accent-6', '#04111F', 'Глубина'),
    ('surface-2', '#0F2D4D', 'Поверхность hover'), ('muted', '#8AA5BD', 'Подписи'),
    ('line', '#163A5C', 'Линия'), ('line-strong', '#24527A', 'Линия усиленная'),
    ('paper', '#DCE7EF', 'Бумага'), ('paper-ink', '#0B2540', 'Текст на бумаге'),
    ('paper-muted', '#3D5872', 'Подписи на бумаге'), ('paper-accent', '#005A82', 'Акцент на бумаге'),
]
gradients = [
    ('depth', 'Глубина', 'linear-gradient(180deg,#071B2F 0%,#071B2F 30%,#04111F 100%)'),
    ('flow', 'Поток', 'linear-gradient(90deg,#0089BF 0%,#0EB8DA 55%,#7FDCF2 100%)'),
    ('glow', 'Свечение', 'radial-gradient(closest-side,rgba(0,137,191,.22),rgba(0,137,191,0) 70%)'),
    ('cta', 'Финал', 'linear-gradient(180deg,rgba(4,17,31,0) 0%,#04111F 100%)'),
]
font_sizes = [
    ('x-small', 'Метка', '0.8125rem', False),
    ('small', 'Мелкий', '0.9375rem', ('0.875rem', '0.9375rem')),
    ('medium', 'Текст', '1.0625rem', ('1rem', '1.0625rem')),
    ('large', 'Лид', '1.25rem', ('1.0625rem', '1.25rem')),
    ('x-large', 'H3', '1.5rem', ('1.1875rem', '1.5rem')),
    ('xx-large', 'H2', '3.5rem', ('2rem', '3.5rem')),
    ('hero', 'H1 главной', '4.75rem', ('2.125rem', '4.75rem')),
    ('display', 'Дисплей', '7.5rem', ('3rem', '7.5rem')),
    ('phone', 'Телефон', '4rem', ('1.75rem', '4rem')),
]
spacing = [
    ('20', '1', '8px'), ('30', '2', '16px'), ('40', '3', '24px'),
    ('50', '4', 'clamp(26px, 20px + 1.667vw, 44px)'),
    ('60', '5', 'clamp(44px, 35.33px + 2.407vw, 70px)'),
    ('70', '6', 'clamp(72px, 54px + 5vw, 126px)'),
    ('80', '7', 'clamp(106px, 82px + 6.667vw, 178px)'),
]

settings = {
    'appearanceTools': True,
    'useRootPaddingAwareAlignments': True,
    'layout': {'contentSize': '760px', 'wideSize': '1280px'},
    'color': {
        'defaultPalette': False, 'defaultGradients': False, 'defaultDuotone': False,
        'custom': True, 'customGradient': True, 'duotone': [],
        'palette': {'theme': [{'slug': s, 'color': c, 'name': n} for s, c, n in palette]},
        'gradients': {'theme': [{'slug': s, 'name': n, 'gradient': g} for s, n, g in gradients]},
    },
    'typography': {
        'defaultFontSizes': False,
        'fluid': {'minViewportWidth': '360px', 'maxViewportWidth': '1440px'},
        'fontSizes': {'theme': [
            {'slug': s, 'name': n, 'size': size, 'fluid': (False if not f else {'min': f[0], 'max': f[1]})}
            for s, n, size, f in font_sizes]},
    },
    'spacing': {
        'defaultSpacingSizes': False,
        'units': ['px', 'em', 'rem', '%', 'vh', 'vw'],
        'spacingSizes': {'theme': [{'slug': s, 'name': n, 'size': v} for s, n, v in spacing]},
    },
}

focus = {'outline': {'color': P + 'accent-1', 'offset': '3px', 'style': 'solid', 'width': '2px'}}
styles = {
    'color': {'background': P + 'base', 'text': P + 'contrast'},
    'typography': {'fontFamily': 'var:preset|font-family|manrope', 'fontSize': 'var:preset|font-size|medium',
                   'fontWeight': '400', 'lineHeight': '1.6', 'letterSpacing': '0'},
    'spacing': {'blockGap': '1.25rem',
                'padding': {'top': '0', 'bottom': '0', 'left': 'clamp(16px, 4vw, 56px)', 'right': 'clamp(16px, 4vw, 56px)'}},
    'elements': {
        'link': {'color': {'text': P + 'accent-1'}, 'typography': {'textDecoration': 'underline'},
                 ':hover': {'color': {'text': P + 'accent-3'}, 'typography': {'textDecoration': 'underline'}}},
        'heading': {'color': {'text': P + 'contrast'},
                    'typography': {'fontFamily': 'var:preset|font-family|manrope', 'fontWeight': '600',
                                   'lineHeight': '1.08', 'letterSpacing': '-0.022em', 'textTransform': 'none'}},
        'h1': {'typography': {'fontSize': 'var:preset|font-size|xx-large', 'lineHeight': '1.04', 'letterSpacing': '-0.034em'}},
        'h2': {'typography': {'fontSize': 'var:preset|font-size|xx-large', 'lineHeight': '1.05', 'letterSpacing': '-0.03em'}},
        'h3': {'typography': {'fontSize': 'var:preset|font-size|x-large', 'lineHeight': '1.2', 'letterSpacing': '-0.015em'}},
        'h4': {'typography': {'fontSize': 'var:preset|font-size|large', 'lineHeight': '1.3', 'letterSpacing': '-0.01em'}},
        'h5': {'typography': {'fontSize': 'var:preset|font-size|medium', 'lineHeight': '1.4', 'letterSpacing': '0'}},
        'h6': {'typography': {'fontSize': 'var:preset|font-size|small', 'lineHeight': '1.4', 'fontWeight': '700',
                              'letterSpacing': '0.12em', 'textTransform': 'uppercase'}},
        'button': {
            'color': {'background': P + 'accent-1', 'text': P + 'accent-6'},
            'border': {'radius': '12px', 'width': '1px', 'style': 'solid', 'color': P + 'accent-1'},
            'typography': {'fontFamily': 'var:preset|font-family|manrope', 'fontSize': '1rem', 'fontWeight': '600', 'lineHeight': '1.2'},
            'spacing': {'padding': {'top': '0', 'bottom': '0', 'left': '26px', 'right': '26px'}},
            ':hover': {'color': {'background': P + 'accent-3', 'text': P + 'accent-6'}, 'border': {'color': P + 'accent-3'}},
            ':focus': focus,
        },
        'caption': {'color': {'text': P + 'muted'}, 'typography': {'fontSize': 'var:preset|font-size|small', 'lineHeight': '1.45'}},
    },
    'blocks': {
        'core/button': {'variations': {'outline': {
            'color': {'background': 'rgba(4,17,31,0.35)', 'text': P + 'contrast'},
            'border': {'color': P + 'accent-1', 'width': '1px', 'style': 'solid', 'radius': '12px'},
            'spacing': {'padding': {'top': '0', 'bottom': '0', 'left': '26px', 'right': '26px'}},
            'css': '.wp-block-button__link:not(.has-background):hover{background-color:rgba(14,184,218,.1)}',
        }}},
        'core/navigation': {
            'color': {'text': P + 'accent-4'},
            'typography': {'fontSize': '0.9375rem', 'fontWeight': '500'},
            'elements': {'link': {'typography': {'textDecoration': 'none'},
                                  ':hover': {'typography': {'textDecoration': 'none'}}}},
        },
        'core/table': {'typography': {'fontSize': 'var:preset|font-size|small'}},
        'core/code': {'typography': {'fontFamily': 'var:preset|font-family|fira-code', 'fontSize': 'var:preset|font-size|small', 'fontWeight': '400'},
                      'color': {'background': P + 'accent-5', 'text': P + 'contrast'},
                      'border': {'color': P + 'line', 'width': '1px', 'style': 'solid', 'radius': '8px'}},
        'core/separator': {'color': {'text': P + 'line-strong'}},
        'core/quote': {'border': {'color': P + 'accent-1'}},
        'core/post-title': {'elements': {'link': {'color': {'text': P + 'contrast'}}}},
    },
    'css': css,
}

data = {'settings': settings, 'styles': styles}
out = SYS / 'global-styles.json'
out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(f'global-styles.json: {out.stat().st_size} B; styles.css: {len(css.encode())} B')
