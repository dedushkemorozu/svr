#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oracle_compare.py — проверка точности preview.py против НАСТОЯЩЕГО WordPress 7.1.3 (локальная копия).

Нужна приватная копия локального стенда WP (по умолчанию redesign/tmp/preview-oracle: core/ + db/ + router.php,
сделана копированием redesign/tmp/wp). Скрипт:
  1) записывает в ЭТУ копию (не в сайт!) global styles, части шаблона, шаблон и контент страницы;
  2) поднимает php -S на 127.0.0.1:<port> (если не запущен) и забирает HTML страницы;
  3) собирает ту же страницу через preview.py;
  4) снимает оба варианта (1440 и 390, full page), считает попиксельную разницу, склеивает «WP | preview»;
  5) сравнивает DOM (теги+классы), правила global-styles / core-block-supports и пишет <out>-compare.json.

  python3 tools/oracle_compare.py --content tmp/preview-tests/t1-layout.html --template page \
      --title "Тест" --page-id 50 --out tmp/preview-tests/cmp/t1
"""
import argparse
import difflib
import json
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REDESIGN = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import preview  # noqa: E402

APPLY_PHP = r'''<?php
$a = json_decode( file_get_contents( $argv[1] ), true );
define( 'WP_USE_THEMES', false );
$_SERVER['REQUEST_URI'] = '/';
require $a['core'] . '/wp-load.php';
wp_set_current_user( 1 );
kses_remove_filters();
$theme = get_stylesheet();

$gid = WP_Theme_JSON_Resolver::get_user_global_styles_post_id();
$cfg = array( 'version' => 3, 'isGlobalStylesUserThemeJSON' => true );
if ( ! empty( $a['settings'] ) ) { $cfg['settings'] = $a['settings']; }
if ( ! empty( $a['styles'] ) ) { $cfg['styles'] = $a['styles']; }
wp_update_post( array( 'ID' => $gid, 'post_content' => wp_slash( wp_json_encode( $cfg ) ) ) );

function svr_upsert( $type, $slug, $content, $theme, $area = null ) {
	$q = get_posts( array( 'post_type' => $type, 'name' => $slug, 'post_status' => 'any', 'numberposts' => 1,
		'tax_query' => array( array( 'taxonomy' => 'wp_theme', 'field' => 'name', 'terms' => $theme ) ) ) );
	$arr = array( 'post_type' => $type, 'post_name' => $slug, 'post_title' => $slug, 'post_status' => 'publish',
		'post_content' => wp_slash( $content ) );
	if ( $q ) { $arr['ID'] = $q[0]->ID; $id = wp_update_post( $arr ); } else { $id = wp_insert_post( $arr ); }
	wp_set_post_terms( $id, $theme, 'wp_theme' );
	if ( $area ) { wp_set_post_terms( $id, $area, 'wp_template_part_area' ); }
	return $id;
}
foreach ( $a['parts'] as $slug => $content ) {
	svr_upsert( 'wp_template_part', $slug, $content, $theme, in_array( $slug, array( 'header', 'footer' ), true ) ? $slug : 'uncategorized' );
}
svr_upsert( 'wp_template', $a['template'], $a['template_content'], $theme );

$pid = (int) $a['page_id'];
$post = $pid ? get_post( $pid ) : null;
$arr = array( 'post_type' => 'page', 'post_status' => 'publish', 'post_title' => wp_slash( $a['title'] ),
	'post_content' => wp_slash( $a['content'] ) );
if ( $post && 'page' === $post->post_type ) { $arr['ID'] = $pid; $pid = wp_update_post( $arr ); }
else { $arr['post_name'] = 'preview-oracle-test'; $pid = wp_insert_post( $arr ); }
update_post_meta( $pid, '_wp_page_template', 'page' === $a['template'] ? 'default' : $a['template'] );
if ( isset( $a['blogdescription'] ) ) { update_option( 'blogdescription', $a['blogdescription'] ); }
$url = get_permalink( $pid );
echo wp_json_encode( array( 'id' => $pid, 'path' => wp_parse_url( $url, PHP_URL_PATH ) ) );
'''


def port_open(port):
    with socket.socket() as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def ensure_server(wp_root, port):
    if port_open(port):
        return
    subprocess.Popen('cd %s && PHP_CLI_SERVER_WORKERS=4 nohup php -S 127.0.0.1:%d -t core router.php > server.log 2>&1 &'
                     % (wp_root, port), shell=True)
    for _ in range(50):
        if port_open(port):
            return
        time.sleep(0.1)
    raise SystemExit('php -S не поднялся на порту %d' % port)


def apply_to_wp(args, wp_root):
    warnings = []
    system = preview.SystemFiles(args.system, warnings, args.css, args.global_styles)
    user, css = system.global_styles()
    styles = dict(user.get('styles') or {}) if user else {}
    if css:
        styles['css'] = css
    tpl = system.template(args.template)
    parts = {}
    for slug in re.findall(r'wp:template-part\s+\{[^}]*"slug":"([^"]+)"', tpl):
        markup, _ = system.part(slug)
        if markup is not None:
            parts[slug] = markup
    payload = {'core': str(wp_root / 'core'), 'settings': (user or {}).get('settings') or {}, 'styles': styles,
               'parts': parts, 'template': Path(args.template).stem if args.template.endswith('.html') else args.template,
               'template_content': tpl, 'page_id': args.page_id, 'title': args.title,
               'content': Path(args.content).read_text(encoding='utf-8'), 'blogdescription': args.site_tagline}
    tmpdir = Path(args.out).parent
    jp = tmpdir / (Path(args.out).name + '-oracle-in.json')
    jp.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    php = tmpdir / '_oracle_apply.php'
    php.write_text(APPLY_PHP, encoding='utf-8')
    out = subprocess.run(['php', '-d', 'memory_limit=1G', str(php), str(jp)], capture_output=True, text=True)
    m = re.search(r'\{"id".*\}', out.stdout)
    if not m:
        raise SystemExit('Не удалось записать данные в WP:\n' + out.stdout[-2000:] + out.stderr[-2000:])
    return json.loads(m.group(0))


def css_rules(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    out, depth, cur = [], 0, ''
    for ch in css:
        cur += ch
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                out.append(re.sub(r'\s+', ' ', cur).strip())
                cur = ''
    return out


def style_block(html, sid):
    m = re.search(r'<style id="%s">(.*?)</style>' % re.escape(sid), html, re.S)
    return m.group(1) if m else ''


def dom_signature(html):
    body = html.split('<div class="wp-site-blocks">', 1)[-1]
    body = re.sub(r'<script.*?</script>', '', body, flags=re.S)
    sig = []
    for t in preview.iter_tags(body):
        if t.closer or t.name in ('path', 'rect', 'circle', 'g', 'line', 'polyline', 'polygon', 'defs', 'stop'):
            continue
        cls = ' '.join(sorted(preview.tag_classes(body, t)))
        sig.append('%s.%s' % (t.name, cls) if cls else t.name)
    return sig


def shoot(url_or_path, png, width, route_to=None):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=preview.CHROME, args=['--font-render-hinting=none', '--disable-gpu'],
                              proxy={'server': 'http://127.0.0.1:9', 'bypass': '127.0.0.1,localhost'})  # наружу — ничего
        ctx = b.new_context(viewport={'width': width, 'height': 900}, reduced_motion='reduce')
        page = ctx.new_page()

        def route(r):
            u = r.request.url
            if route_to and u.startswith('https://svr-mos.ru/'):
                try:
                    with urllib.request.urlopen(route_to + u[len('https://svr-mos.ru'):], timeout=20) as resp:
                        body = resp.read()
                        ctype = resp.headers.get('Content-Type', 'application/octet-stream')
                    return r.fulfill(status=200, body=body, headers={'Content-Type': ctype})
                except Exception:
                    return r.abort()
            if u.startswith(('file:', 'data:', 'about:', 'blob:')) or (route_to and u.startswith(route_to)):
                return r.continue_()
            return r.abort()
        page.route('**/*', route)
        page.goto(url_or_path, wait_until='load')
        page.evaluate(preview.PREP_JS)
        page.wait_for_timeout(200)
        preview.full_page_shot(page, png, {'width': width, 'height': 900})  # без пропавших картинок и предела 16384 px
        b.close()


def image_diff(a, b, out_side, out_diff):
    from PIL import Image, ImageChops
    A, B = Image.open(a).convert('RGB'), Image.open(b).convert('RGB')
    w, h = max(A.width, B.width), max(A.height, B.height)
    A2, B2 = Image.new('RGB', (w, h), 'white'), Image.new('RGB', (w, h), 'white')
    A2.paste(A, (0, 0))
    B2.paste(B, (0, 0))
    d = ImageChops.difference(A2, B2).convert('L')
    px = d.point(lambda v: 255 if v > 24 else 0).histogram()[255]
    side = Image.new('RGB', (w * 2 + 10, h), (255, 0, 255))
    side.paste(A2, (0, 0))
    side.paste(B2, (w + 10, 0))
    side.save(out_side)
    d.point(lambda v: 255 if v > 24 else 0).save(out_diff)
    return {'size_wp': [A.width, A.height], 'size_preview': [B.width, B.height],
            'diff_pixels': px, 'diff_ratio': round(px / float(w * h), 5)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--content', required=True)
    ap.add_argument('--template', default='page')
    ap.add_argument('--title', default='')
    ap.add_argument('--page-id', type=int, default=0)
    ap.add_argument('--front', action='store_true')
    ap.add_argument('--system', default=str(preview.DEFAULT_SYSTEM))
    ap.add_argument('--css', default=None)
    ap.add_argument('--global-styles', default=None)
    ap.add_argument('--site-tagline', default='Сервис водных ресурсов')
    ap.add_argument('--wp', default=str(REDESIGN / 'tmp' / 'preview-oracle'))
    ap.add_argument('--port', type=int, default=8091)
    ap.add_argument('--out', required=True)
    ap.add_argument('--widths', default='1440,390')
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    args.out = str(out)
    wp_root = Path(args.wp).resolve()
    res = apply_to_wp(args, wp_root)
    ensure_server(wp_root, args.port)
    base = 'http://127.0.0.1:%d' % args.port
    wp_html = urllib.request.urlopen(base + res['path']).read().decode('utf-8')
    Path(args.out + '-wp.html').write_text(wp_html, encoding='utf-8')
    pv_args = ['--content', args.content, '--template', args.template, '--title', args.title, '--out', args.out + '-pv',
               '--system', args.system, '--page-id', str(res['id']), '--no-shots', '--site-tagline', args.site_tagline]
    if args.front:
        pv_args.append('--front')
    if args.css:
        pv_args += ['--css', args.css]
    if args.global_styles:
        pv_args += ['--global-styles', args.global_styles]
    preview.main(pv_args)
    pv_html = Path(args.out + '-pv.html').read_text(encoding='utf-8')
    rep = {'wp_url': base + res['path'], 'page_id': res['id']}
    # DOM
    a, b = dom_signature(wp_html), dom_signature(pv_html)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    rep['dom'] = {'wp_elements': len(a), 'preview_elements': len(b), 'similarity': round(sm.ratio(), 4),
                  'diff': [l for l in difflib.unified_diff(a, b, 'wp', 'preview', n=1, lineterm='')][:300]}
    # CSS
    for sid in ('global-styles-inline-css', 'core-block-supports-inline-css', 'block-style-variation-styles-inline-css'):
        wa, pa = css_rules(style_block(wp_html, sid)), css_rules(style_block(pv_html, sid))
        rep[sid] = {'wp_rules': len(wa), 'preview_rules': len(pa),
                    'only_wp': [r for r in wa if r not in pa][:80], 'only_preview': [r for r in pa if r not in wa][:80],
                    'same_order': wa == pa}
    # картинки
    rep['screens'] = {}
    for w in [int(x) for x in args.widths.split(',')]:
        pw, pp = args.out + '-wp-%d.png' % w, args.out + '-pv-%d.png' % w
        shoot(base + res['path'], pw, w, route_to=base)
        shoot(Path(args.out + '-pv.html').as_uri(), pp, w)
        rep['screens'][str(w)] = image_diff(pw, pp, args.out + '-side-%d.png' % w, args.out + '-diff-%d.png' % w)
    Path(args.out + '-compare.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'dom_similarity': rep['dom']['similarity'],
                      'css': {k: (len(rep[k]['only_wp']), len(rep[k]['only_preview'])) for k in rep if k.endswith('-css')},
                      'screens': rep['screens']}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
