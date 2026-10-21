"""Build concepts/deep/home.html from home.src.html:
{{IMG:<id>}}      -> file:// local path from media.json
{{SVGURI:<file>}} -> url-encoded data URI of an SVG file in concepts/deep/
{{FONTDIR}}       -> file:// path of concepts/deep/fonts
{{WPCSS}}         -> contents of preview-assets/wp-block-library.css"""
import json, re, sys, urllib.parse, os
ROOT = '/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad'
D = ROOT + '/redesign/concepts/deep'
media = {m['id']: m for m in json.load(open(ROOT + '/media.json'))}
src = open(D + '/home.src.html').read()
def svguri(name):
    s = open(D + '/' + name).read().strip()
    s = re.sub(r'\s+', ' ', s)
    return 'data:image/svg+xml,' + urllib.parse.quote(s, safe=" =:/'(),;-.")
src = re.sub(r'\{\{IMG:(\d+)\}\}', lambda m: 'file://' + media[int(m.group(1))]['local'], src)
src = re.sub(r'\{\{SVGURI:([\w.\-]+)\}\}', lambda m: svguri(m.group(1)), src)
src = src.replace('{{FONTDIR}}', 'file://' + D + '/fonts')
src = src.replace('{{WPCSS}}', open(ROOT + '/preview-assets/wp-block-library.css').read())
open(D + '/home.html', 'w').write(src)
print('built', len(src), 'bytes')
