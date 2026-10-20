#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Копия старого статического сайта ООО «СВР» на www.svr-mos.ru (хостинг Beget, 87.236.19.9).

Запуск:   python -I backup_www_old.py

Обходит все ссылки (href, src, url() в CSS/style) в пределах www.svr-mos.ru и сохраняет
файлы в www-old/ с исходной структурой путей. Итог — www-old/_crawl.json.
Только стандартная библиотека Python.
"""
import hashlib
import html as htmllib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

START = "http://www.svr-mos.ru/"
HOSTS = {"www.svr-mos.ru"}
OUT = Path(r"C:\l1bot\svr-mos.ru-backup\www-old")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) svr-mos-backup/1.0"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, dict(r.headers.items()), r.read(), r.geturl()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers.items()), e.read() if e.fp else b"", url
        except Exception as e:
            err = repr(e)
            time.sleep(1.5 * (attempt + 1))
    return 0, {"error": err}, b"", url


def rel_of(url):
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path) or "/"
    if path.endswith("/"):
        path += "index.html"
    return re.sub(r'[<>:"|?*\\]', "_", path.lstrip("/"))


def refs_in(text, base):
    found = re.findall(r'''(?:href|src|background)\s*=\s*["']([^"']+)["']''', text, re.I)
    found += re.findall(r"url\(\s*['\"]?([^'\")]+?)['\"]?\s*\)", text)
    found += re.findall(r"@import\s+['\"]([^'\"]+)['\"]", text)
    out = set()
    for f in found:
        f = htmllib.unescape(f).strip()
        if not f or f.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            continue
        u = urllib.parse.urljoin(base, f)
        u = urllib.parse.urldefrag(u)[0]
        p = urllib.parse.urlsplit(u)
        # пробелы и кириллица в именах файлов
        u = urllib.parse.urlunsplit((p.scheme, p.netloc, urllib.parse.quote(urllib.parse.unquote(p.path)), p.query, ""))
        out.add(u)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    queue, seen, log, external = deque([START]), {START}, [], set()
    while queue:
        url = queue.popleft()
        st, headers, body, final = get(url)
        rec = {"url": url, "status": st, "bytes": len(body), "content_type": headers.get("Content-Type", ""),
               "last_modified": headers.get("Last-Modified")}
        if st == 200:
            rel = rel_of(url)
            p = OUT / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)
            rec.update(file=rel, sha256=hashlib.sha256(body).hexdigest())
            ctype = rec["content_type"].lower()
            if "html" in ctype or "css" in ctype or rel.lower().endswith((".html", ".htm", ".css")):
                text = body.decode("utf-8", "replace")
                for u in refs_in(text, final):
                    host = urllib.parse.urlparse(u).netloc.lower()
                    if host in HOSTS:
                        u = u.replace("https://", "http://", 1)
                        if u not in seen:
                            seen.add(u)
                            queue.append(u)
                    else:
                        external.add(u)
        log.append(rec)
        print(f"{st} {len(body):>9} {url}", flush=True)
        time.sleep(0.1)
    summary = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "start": START,
               "files_ok": sum(1 for r in log if r["status"] == 200),
               "failed": [r for r in log if r["status"] != 200],
               "external_links": sorted(external), "files": log}
    (OUT / "_crawl.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Готово: {summary['files_ok']} файлов, ошибок {len(summary['failed'])}")


if __name__ == "__main__":
    main()
