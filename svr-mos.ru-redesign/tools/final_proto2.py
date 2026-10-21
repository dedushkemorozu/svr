"""Проверка эталонных SVG: CTA-капля, пучок «турбулентный→ламинарный», иконки этапов."""
import pathlib
from playwright.sync_api import sync_playwright
R = pathlib.Path('/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign')
F = R / 'assets/fonts'; S = R / 'assets/svg'
html = f'''<!doctype html><meta charset="utf-8"><style>
@font-face{{font-family:Manrope;src:url(file://{F}/manrope-cyrillic-wght-normal.woff2);font-weight:200 800;unicode-range:U+0400-045F}}
@font-face{{font-family:Manrope;src:url(file://{F}/manrope-latin-wght-normal.woff2);font-weight:200 800;unicode-range:U+0000-00FF,U+2000-206F}}
body{{margin:0;padding:24px;background:#071B2F;color:#E8F1F8;font-family:Manrope;display:flex;gap:40px;align-items:flex-start}}
.svr-dwg{{width:360px;height:auto}}.svr-dwg-t{{font:600 17px Manrope;fill:#A9BFD3}}
.flow{{display:flex;align-items:center;gap:0}}.flow svg.svr-flow__bundle{{width:160px;height:64px}}
.pipe{{width:200px;height:10px;border-block:1px solid rgba(14,184,218,.7);background:rgba(14,184,218,.07);position:relative}}
.pipe::after{{content:"";position:absolute;left:0;right:0;top:3px;height:2px;background:repeating-linear-gradient(90deg,#0EB8DA 0 10px,transparent 10px 24px)}}
.ico{{display:grid;grid-template-columns:repeat(4,72px);gap:16px;color:#0EB8DA}}.ico svg{{width:48px;height:48px;border:1px solid #24527A;padding:12px}}
</style><div>{(S/"cta-drop.svg").read_text()}</div>
<div><div class="flow"><span style="font:600 14px Manrope;color:#8AA5BD;margin-right:12px">Вход · сточные воды</span>{(S/"flow-in.svg").read_text()}<div class="pipe"></div></div>
<div class="ico" style="margin-top:40px">{(S/"stage-icons.html").read_text()}</div></div>'''
out = R / 'tmp/ad/proto2.html'; out.write_text(html)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    pg = b.new_page(viewport={'width': 1100, 'height': 520}); pg.goto('file://' + str(out)); pg.evaluate('document.fonts.ready'); pg.wait_for_timeout(300)
    pg.screenshot(path=str(R / 'tmp/ad/proto2.png')); b.close()
