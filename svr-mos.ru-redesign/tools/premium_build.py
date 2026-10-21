"""Build concepts/premium/home.html from home.src.html: inline WP block CSS, fonts, file:// images, flow SVG."""
import json, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import premium_flow
S = '/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad'
D = S + '/redesign/concepts/premium'
src = open(D + '/home.src.html', encoding='utf-8').read()
media = {m['id']: m for m in json.load(open(S + '/media.json'))}
wpcss = open(S + '/preview-assets/wp-block-library.css', encoding='utf-8').read()
src = src.replace('{{WPCSS}}', wpcss)
src = src.replace('{{FONTS}}', S + '/preview-assets/fonts')
src = src.replace('{{FIRA}}', S + '/redesign/assets/fonts')
src = src.replace('{{FLOW_HERO}}', premium_flow.svg(idp='flh'))
src = src.replace('{{FLOW_CTA}}', premium_flow.svg(n=18, idp='flc'))
src = re.sub(r'\{\{IMG(\d+)\}\}', lambda m: 'file://' + media[int(m.group(1))]['local'], src)
left = re.findall(r'\{\{[^}]+\}\}', src)
assert not left, left
open(D + '/home.html', 'w', encoding='utf-8').write(src)
print('ok', len(src))
