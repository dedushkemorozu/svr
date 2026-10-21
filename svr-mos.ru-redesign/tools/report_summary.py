"""Сводка отчётов preview.py по папке: python3 tools/report_summary.py <папка> — скролл на всех ширинах, h1, AA, alt, битые, дубли id, анимации, предупреждения."""
import json, sys, pathlib
d = pathlib.Path(sys.argv[1]); bad = 0
for f in sorted(d.glob('*-report.json')):
    r = json.loads(f.read_text())
    w = r.get('widths') or {}
    scroll = [k for k, v in (w.items() if isinstance(w, dict) else []) if (v or {}).get('has_scroll') or (v or {}).get('has_scroll_without_overflow_clip')]
    ms, ds = r.get('mobile_horizontal_scroll', {}), r.get('desktop_horizontal_scroll', {})
    for nm, x in (('390', ms), ('1440', ds)):
        if x.get('has_scroll') or x.get('has_scroll_without_overflow_clip'):
            scroll.append(nm)
    an = r.get('animations') or {}
    h = r.get('h1_count') or {}
    row = dict(h1=(h.get('desktop'), h.get('mobile')) if isinstance(h, dict) else h, aa=len(r.get('low_contrast_aa_fail') or []), noalt=len(r.get('images_without_alt') or []),
               broken=len(r.get('broken_images') or []), dup=len(r.get('duplicate_ids') or []), skips=len(r.get('heading_level_skips') or []),
               empty_links=len(r.get('empty_links') or []), anim='%s/%s inf %s/%s' % (an.get('desktop', {}).get('running'), an.get('mobile', {}).get('running'), an.get('desktop', {}).get('infinite'), an.get('mobile', {}).get('infinite')), warn=len(r.get('warnings') or []), scroll=scroll, widths=len(w))
    issue = row['h1'] not in (1, (1, 1)) or row['aa'] or row['noalt'] or row['broken'] or row['dup'] or row['skips'] or row['empty_links'] or scroll
    bad += bool(issue)
    print(('BAD ' if issue else 'ok  ') + f.name.replace('-report.json', ''), json.dumps(row, ensure_ascii=False))
sys.exit(1 if bad else 0)
