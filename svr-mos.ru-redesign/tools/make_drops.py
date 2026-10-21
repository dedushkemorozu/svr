"""Генерация assets/svg/hero-drop.svg и cta-drop.svg: капля-резервуар в разрезе (стенка со штриховкой, вода с мягкой волной,
пузырьки только в герое) + ДВЕ трубы и ДВЕ подписи — вход слева сверху и выход справа снизу, как в первой версии.
Вход: турбулентный пучок линий сходится в ровную трубу (только в герое), задвижка и стрелка потока, бегущий пунктир.
Выход: труба от дна вправо, задвижка и стрелка. Никаких выносок 01–06, «R», размерных линий, отметки уровня, кропмарок.
Бесконечных анимаций: герой 6 (волна, пузырьки, 2 потока, 2 стрелки), CTA 2 (потоки; стрелки статичны) — всего на главной 8.
Запуск: python3 tools/make_drops.py"""
import math, pathlib

R_ = pathlib.Path(__file__).resolve().parent.parent
OUT = R_ / 'assets/svg'


def f(x):
    return ('%.2f' % x).rstrip('0').rstrip('.')


def drop_path(cx, cy, r, d):
    """Капля: вершина на расстоянии d над центром, окружность радиуса r (касательные из вершины, как в логотипе)."""
    k = r / d
    dx = r * math.sqrt(1 - k * k)
    ty = cy - r * k
    return f'M{f(cx)} {f(cy - d)} L{f(cx + dx)} {f(ty)} A{f(r)} {f(r)} 0 1 1 {f(cx - dx)} {f(ty)} Z', cy - d, ty, dx


def wave(x0, y, amp, seg, n, bottom):
    t = ' '.join(f't{seg} 0' for _ in range(n - 1))
    return f'M{x0} {y}q{seg // 2}-{amp} {seg} 0{" " + t if t else ""}V{bottom}H{x0}Z'


BUNDLE = ('<path d="M0 10C30 2 40 30 70 18S120 30 160 31"/><path d="M0 22C25 34 45 6 75 26S125 34 160 32"/>'
          '<path d="M0 34C20 20 50 50 80 34S125 30 160 32"/><path d="M0 46C30 58 40 26 72 44S120 36 160 33"/>'
          '<path d="M0 56C25 44 55 62 85 46S128 35 160 33"/><path d="M0 16C35 26 30 46 66 38S118 31 160 31.5"/>'
          '<path d="M0 40C28 30 48 56 78 30S124 33 160 32.5"/>')


def valve(x, y, w=24, h=16, stem=18):
    """Задвижка: «бабочка» на трубе + шток с планкой вверх."""
    return (f'<path d="M{f(x - w / 2)} {f(y - h / 2)}L{f(x + w / 2)} {f(y + h / 2)}V{f(y - h / 2)}L{f(x - w / 2)} {f(y + h / 2)}Z" '
            f'fill="#071B2F" stroke-linejoin="round"/>'
            f'<path d="M{f(x)} {f(y - h / 2)}V{f(y - h / 2 - stem)}M{f(x - 8)} {f(y - h / 2 - stem)}H{f(x + 8)}" fill="none"/>')


def build(p, cx, apex, r, d, w, vb_w, vb_h, level, *, pin, pout, in_label, out_label, in_x, bundle, font, bubbles=None,
          title=None, desc=None, glow=.14, sw=2.2, wave_anim=True, flow_anim=True, arrow_anim=True):
    """p — префикс id; pin = (y трубы входа); pout = (y трубы выхода, x конца); подписи: (x, y) якорь."""
    cy = apex + d
    outer, ay, ty, dx = drop_path(cx, cy, r, d)
    ri = r - w
    inner, *_ = drop_path(cx, cy, ri, d * ri / r)
    bottom = cy + r
    hx0, hy0, hw, hh = cx - r - 12, ay - 12, 2 * r + 24, (cy + r + 12) - (ay - 12)
    wv_n = int((vb_w + 240) / 60) + 2
    attrs = ('role="img" aria-labelledby="%sT %sD"' % (p, p)) if title else 'fill="none" aria-hidden="true"'
    s = [f'<svg class="svr-dwg" viewBox="0 0 {vb_w} {vb_h}" {attrs} focusable="false" xmlns="http://www.w3.org/2000/svg">']
    if title:
        s += [f'<title id="{p}T">{title}</title>', f'<desc id="{p}D">{desc}</desc>']
    s.append('<defs>')
    s.append(f'<clipPath id="{p}In"><path d="{inner}"/></clipPath>')
    s.append(f'<pattern id="{p}Hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" stroke="#0EB8DA" stroke-opacity=".5"/></pattern>')
    s.append(f'<mask id="{p}Wall"><path d="{outer}" fill="#fff"/><path d="{inner}" fill="#000"/></mask>')
    s.append(f'<linearGradient id="{p}Water" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0EB8DA" stop-opacity=".42"/><stop offset="1" stop-color="#0089BF" stop-opacity=".08"/></linearGradient>')
    if bundle:
        s.append(f'<linearGradient id="{p}Bundle" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#3B5F8C" stop-opacity=".35"/><stop offset=".6" stop-color="#0EB8DA" stop-opacity=".7"/><stop offset="1" stop-color="#7FDCF2"/></linearGradient>')
    s.append(f'<radialGradient id="{p}Glow"><stop offset="0" stop-color="#0EB8DA" stop-opacity="{glow}"/><stop offset="1" stop-color="#0EB8DA" stop-opacity="0"/></radialGradient>')
    s.append('</defs>')
    s.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r * 1.7)}" fill="url(#{p}Glow)"/>')
    s.append(f'<circle cx="{f(cx)}" cy="{f(cy + 4)}" r="{f(r * 1.14)}" fill="none" stroke="#0EB8DA" stroke-opacity=".3" stroke-dasharray="3 6"/>')
    # вода
    s.append(f'<g clip-path="url(#{p}In)">')
    s.append(f'<rect x="{f(cx - r)}" y="{f(ay)}" width="{f(2 * r)}" height="{f(cy + r - ay)}" fill="#0B2540" fill-opacity=".55"/>')
    s.append(f'<path fill="url(#{p}Water)" opacity=".55" d="{wave(-200, level - 8, 7, 60, wv_n + 4, bottom + 20)}"/>')
    cls = ' class="svr-dwg-wave"' if wave_anim else ''
    s.append(f'<g{cls}><path fill="url(#{p}Water)" d="{wave(-200, level, 8, 60, wv_n + 4, bottom + 20)}"/></g>')
    if bubbles:
        s.append('<g class="svr-dwg-bubble" fill="none" stroke="#7FDCF2" stroke-opacity=".5">')
        s += [f'<circle cx="{bx}" cy="{by}" r="{br}"/>' for bx, by, br in bubbles]
        s.append('</g>')
    s.append('</g>')
    s.append(f'<rect x="{f(hx0)}" y="{f(hy0)}" width="{f(hw)}" height="{f(hh)}" fill="url(#{p}Hatch)" mask="url(#{p}Wall)"/>')
    s.append(f'<path d="{outer}" fill="none" stroke="#0EB8DA" stroke-width="{sw}" stroke-linejoin="round"/>')
    s.append(f'<path d="{inner}" fill="none" stroke="#0EB8DA" stroke-opacity=".7" stroke-linejoin="round"/>')
    a1, a2 = math.radians(166), math.radians(122)
    rr = ri - 24
    s.append(f'<path d="M{f(cx + rr * math.cos(a1))} {f(cy + rr * math.sin(a1))}A{f(rr)} {f(rr)} 0 0 0 {f(cx + rr * math.cos(a2))} {f(cy + rr * math.sin(a2))}" fill="none" stroke="#E8F1F8" stroke-opacity=".28" stroke-width="3" stroke-linecap="round"/>')

    fl = ' class="svr-dwg-flow"' if flow_anim else ''
    ar = ' class="svr-dwg-arrow"' if arrow_anim else ''
    # ---- вход: слева сверху (пучок → труба → задвижка → стрелка → верх капли)
    iy = pin
    if bundle:
        s.append(f'<g transform="translate({in_x} {iy - 32})" fill="none" stroke="url(#{p}Bundle)" stroke-linecap="round">{BUNDLE}</g>')
        px0 = in_x + 160
    else:
        px0 = in_x
    ipath = f'M{px0} {iy}H{cx}V{f(ay)}'
    s.append(f'<path d="{ipath}" fill="none" stroke="#0EB8DA" stroke-width="2"/>')
    s.append(f'<path{fl} d="{ipath}" fill="none" stroke="#E8F1F8" stroke-width="2" stroke-dasharray="6 10"/>')
    vx = px0 + (cx - px0) * .28
    s.append(f'<g stroke="#0EB8DA" stroke-width="1.5">{valve(vx, iy)}</g>')
    ax = px0 + (cx - px0) * .66
    s.append(f'<path{ar} d="M{f(ax)} {iy - 7}l14 7-14 7z" fill="#0EB8DA"/>')
    lx, ly = in_label
    s.append(f'<text class="svr-dwg-t" x="{lx}" y="{ly}">{in_label_text(p)}</text>')
    # ---- выход: справа снизу (дно → труба вправо → задвижка → стрелка → торец)
    oy, ox = pout
    opath = f'M{f(cx)} {f(bottom)}V{oy}H{ox}'
    s.append(f'<path d="{opath}" fill="none" stroke="#0EB8DA" stroke-width="2"/>')
    s.append(f'<path{fl} d="{opath}" fill="none" stroke="#E8F1F8" stroke-width="2" stroke-dasharray="6 10"/>')
    s.append(f'<path d="M{ox} {oy - 10}V{oy + 10}" stroke="#0EB8DA" stroke-width="2"/>')
    vx = cx + (ox - cx) * .45
    s.append(f'<g stroke="#0EB8DA" stroke-width="1.5">{valve(vx, oy)}</g>')
    ax = cx + (ox - cx) * .8
    s.append(f'<path{ar} d="M{f(ax)} {oy - 7}l14 7-14 7z" fill="#0EB8DA"/>')
    lx, ly = out_label
    s.append(f'<text class="svr-dwg-t" x="{lx}" y="{ly}" text-anchor="end">{out_label_text(p)}</text>')
    s.append('</svg>')
    return '\n'.join(s) + '\n'


LABELS = {'svrHero': ('Вход · сточные воды', 'Выход · чистая вода'), 'svrCta': ('Сточные воды', 'Чистая вода')}


def in_label_text(p):
    return LABELS[p][0]


def out_label_text(p):
    return LABELS[p][1]


hero = build('svrHero', 300, 104, 140, 252, 11, 600, 568, 322, pin=62, pout=(524, 572), in_label=(18, 20), out_label=(572, 556),
             in_x=18, bundle=True, font=17, bubbles=[(268, 440, 3.4), (338, 428, 2.6)],
             title='Капля-резервуар: вход сточных вод слева, выход чистой воды справа',
             desc='Чертёж капли-резервуара. Слева сверху труба входа: турбулентный поток сточных вод сходится в ровную трубу и поступает в резервуар. '
                  'Справа снизу труба выхода: чистая вода. Внутри резервуара вода с мягкой волной и пузырьки.')
cta = build('svrCta', 220, 104, 96, 173, 9, 440, 456, 254, pin=74, pout=(410, 424), in_label=(16, 28), out_label=(424, 442),
            in_x=16, bundle=False, font=17, glow=.18, sw=2, bubbles=None, wave_anim=False, arrow_anim=False)
(OUT / 'hero-drop.svg').write_text(hero)
(OUT / 'cta-drop.svg').write_text(cta)
print('hero-drop.svg', len(hero.encode()), 'B; cta-drop.svg', len(cta.encode()), 'B')

# 404 (system/404.html) содержит ту же каплю inline — синхронизируем
t404 = R_ / 'system/404.html'
if t404.exists():
    s = t404.read_text()
    a = s.index('<svg class="svr-dwg"')
    b = s.index('</svg>', a) + 6
    t404.write_text(s[:a] + cta.strip() + s[b:])
    print('system/404.html: капля синхронизирована')
