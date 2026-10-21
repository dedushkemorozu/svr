"""Build self-contained home.html from home.src.html: replaces {{M:<id>}} with file:// path of media id,
{{FONTS}} with fonts dir URL, {{BLOCKCSS}} with wp-block-library.css URL."""
import json, re, sys, pathlib
S = pathlib.Path('/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad')
R = S / 'redesign'
media = {m['id']: m for m in json.load(open(S / 'media.json'))}
src = (R / 'concepts/blueprint/home.src.html').read_text(encoding='utf-8')
def media_url(m):
    return 'file://' + media[int(m.group(1))]['local']
out = re.sub(r'\{\{M:(\d+)\}\}', media_url, src)
out = out.replace('{{FONTS}}', 'file://' + str(R / 'assets/fonts'))
out = out.replace('{{BLOCKCSS}}', 'file://' + str(S / 'preview-assets/wp-block-library.css'))
left = re.findall(r'\{\{[^}]+\}\}', out)
if left: print('UNRESOLVED', left); sys.exit(1)
(R / 'concepts/blueprint/home.html').write_text(out, encoding='utf-8')
print('built', len(out), 'bytes')
