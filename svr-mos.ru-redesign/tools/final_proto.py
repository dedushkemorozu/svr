"""Прототип ключевых узлов итоговой концепции: герой (H1 + чертёж 6 выносок), display-заголовок CTA.
Проверка переносов, размеров подписей и горизонтального скролла на 320–1440."""
import pathlib, sys
from playwright.sync_api import sync_playwright
R = pathlib.Path('/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign')
F = R / 'assets/fonts'
svg = (R / 'assets/svg/hero-drop.svg').read_text()
html = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
@font-face{{font-family:Manrope;src:url(file://{F}/manrope-cyrillic-wght-normal.woff2) format("woff2");font-weight:200 800;unicode-range:U+0400-045F,U+2116}}
@font-face{{font-family:Manrope;src:url(file://{F}/manrope-latin-wght-normal.woff2) format("woff2");font-weight:200 800;unicode-range:U+0000-00FF,U+2000-206F}}
@font-face{{font-family:"Fira Code";src:url(file://{F}/fira-code-cyrillic-wght-normal.woff2) format("woff2");font-weight:300 700;unicode-range:U+0400-045F}}
@font-face{{font-family:"Fira Code";src:url(file://{F}/fira-code-latin-wght-normal.woff2) format("woff2");font-weight:300 700;unicode-range:U+0000-00FF,U+2000-206F}}
:root{{--pad:clamp(16px,4vw,56px)}}
*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(180deg,#071B2F 0,#071B2F 40%,#04111F 100%);color:#E8F1F8;font:400 1.0625rem/1.6 Manrope,sans-serif;overflow-x:clip}}
.wrap{{max-width:calc(1280px + 2*var(--pad));margin:auto;padding-inline:var(--pad)}}
.grid{{display:flex;gap:clamp(24px,4vw,64px);align-items:center;padding-block:48px}}
.t{{flex:1 1 56%;min-width:0}}.d{{flex:1 1 44%;min-width:0;max-width:560px}}
h1{{font-size:clamp(2.125rem,1.25rem + 3.8889vw,4.75rem);font-weight:600;letter-spacing:-.04em;line-height:1.02;margin:24px 0 0;text-wrap:balance;hyphens:manual}}
h1 mark{{background:none;color:#0EB8DA;white-space:nowrap}}
.eb{{font:700 .8125rem/1.4 Manrope;letter-spacing:.14em;text-transform:uppercase;color:#7FDCF2;display:flex;gap:12px;align-items:center}}.eb::before{{content:"";width:32px;height:1px;background:currentColor}}
.lead{{font-size:clamp(1.0625rem,1rem + .2778vw,1.25rem);color:#A9BFD3;max-width:34em;margin-top:24px}}
.svr-dwg{{width:100%;height:auto;display:block;overflow:visible}}
.svr-dwg-t{{font-family:Manrope;font-weight:600;font-size:19px;fill:#A9BFD3}}
.svr-dwg-n{{font-family:"Fira Code";font-weight:600;fill:#0EB8DA}}
.svr-dwg-lead{{stroke:#7FDCF2;fill:none}}.svr-dwg-dot{{fill:#7FDCF2}}
.cta{{text-wrap:balance;font-size:clamp(3rem,1.5rem + 6.6667vw,7.5rem);font-weight:600;letter-spacing:-.045em;line-height:.96;margin:64px 0}}
.cta mark{{background:none;color:#0EB8DA}}
@media (max-width:1199px){{.grid{{flex-direction:column;align-items:stretch}}.d{{max-width:520px;margin:0 auto;width:100%}}}}
@media (max-width:599px){{.svr-dwg-name{{display:none}}.svr-dwg-t{{font-size:34px}}.d{{max-width:280px}}}}
</style></head><body><div class="wrap"><div class="grid"><div class="t"><p class="eb">Сервис водных ресурсов</p>
<h1>Очистка <mark>сточных вод</mark> на&nbsp;промышленных объектах</h1>
<p class="lead">Изыскания и обследование сооружений, отбор проб и лабораторные испытания, технологические решения, проектная и рабочая документация, пусконаладка и собственное оборудование.</p></div>
<div class="d">{svg}</div></div>
<p class="cta">Мы делаем мир <mark>чище</mark></p></div></body></html>'''
out = R / 'tmp/ad/proto.html'; out.write_text(html)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    for w in (1440, 1280, 1200, 1199, 1024, 768, 600, 390, 360, 320):
        pg = b.new_page(viewport={'width': w, 'height': 900})
        pg.goto('file://' + str(out)); pg.evaluate('document.fonts.ready'); pg.wait_for_timeout(300)
        info = pg.evaluate('''()=>{const h=document.querySelector('h1');const r=h.getClientRects();
          const lines=new Set();const rng=document.createRange();rng.selectNodeContents(h);[...rng.getClientRects()].forEach(x=>lines.add(Math.round(x.top)));
          const c=document.querySelector('.cta');const cl=new Set();const r2=document.createRange();r2.selectNodeContents(c);[...r2.getClientRects()].forEach(x=>cl.add(Math.round(x.top)));
          const svg=document.querySelector('.svr-dwg').getBoundingClientRect();
          const names=[...document.querySelectorAll('.svr-dwg-t')].map(t=>t.getBoundingClientRect()).filter(x=>x.width>0);
          const maxR=Math.max(...names.map(x=>x.right));
          const fs=parseFloat(getComputedStyle(document.querySelector('.svr-dwg-t')).fontSize)*svg.width/720;
          return {sw:document.documentElement.scrollWidth,h1:getComputedStyle(h).fontSize,h1lines:lines.size,h1text:h.textContent,cta:getComputedStyle(c).fontSize,ctaLines:cl.size,svgW:Math.round(svg.width),svgRight:Math.round(svg.right),labelsRight:Math.round(maxR),labelPx:fs.toFixed(1)}}''')
        print(w, info)
        pg.screenshot(path=str(R / f'tmp/ad/proto_{w}.png'), full_page=True)
        pg.close()
    b.close()
