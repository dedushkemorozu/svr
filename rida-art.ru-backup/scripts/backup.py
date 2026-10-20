#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Полная резервная копия сайта rida-art.ru (конструктор сайтов Selectel).

Запуск:   python -I backup.py            (использует кеш: уже скачанное не качает повторно)
          python -I backup.py --refresh  (скачать всё заново)

Что делает:
  1. meta/    - заголовки, robots.txt, sitemap.xml, страница 404, редиректы, TLS-сертификат
  2. html/    - все страницы «как отдаёт сервер» (sitemap + обход внутренних ссылок)
  3. assets/  - все картинки (selstorage.ru), CSS/шрифты (selcdn.net, Google Fonts)
  4. api/     - ответы /api/v3/products/blocks (остатки, скрытые товары, варианты)
  5. data/    - структурированный экспорт: products.json/csv, pages.json, site.json ...
  6. MANIFEST.csv, verify.json - контрольные суммы и проверка полноты

Только стандартная библиотека Python.
"""
import csv
import hashlib
import html as htmllib
import http.client
import json
import re
import socket
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, OrderedDict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

SITE = "https://rida-art.ru"
HOST = "rida-art.ru"
OUT = Path(r"C:\l1bot\rida-art.ru-backup")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) rida-art-backup/1.0"
WORKERS = 6
REFRESH = "--refresh" in sys.argv
ASSET_HOST_SUFFIXES = (".selstorage.ru", ".selcdn.net")
ASSET_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com"}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_lock = threading.Lock()
MANIFEST = {}      # rel path -> record
FAILURES = []      # {"url", "status", "error"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(msg):
    print(f"{datetime.now():%H:%M:%S} {msg}", flush=True)


# ----------------------------------------------------------------------------
# HTTP + хранение
# ----------------------------------------------------------------------------
def hget(url, method="GET", body=None, headers=None, timeout=60, retries=3):
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "ru,en;q=0.8"}
    if headers:
        h.update(headers)
    err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, headers=h, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return {"status": r.status, "headers": dict(r.headers.items()),
                        "body": r.read(), "url": r.geturl(), "error": None}
        except urllib.error.HTTPError as e:
            data = e.read() if e.fp else b""
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            return {"status": e.code, "headers": dict(e.headers.items()),
                    "body": data, "url": url, "error": None}
        except Exception as e:  # сеть, таймаут, SSL
            err = repr(e)
            time.sleep(1.5 * (attempt + 1))
    return {"status": 0, "headers": {}, "body": b"", "url": url, "error": err}


def save(rel, data, url="", status=200, ctype=""):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    rec = {"file": rel.replace("\\", "/"), "url": url, "status": status, "bytes": len(data),
           "sha256": hashlib.sha256(data).hexdigest(), "content_type": ctype, "fetched": now()}
    with _lock:
        MANIFEST[rec["file"]] = rec


def fetch_to(rel, url, **kw):
    """Скачать url в rel (с кешем). Возвращает (status, bytes, final_url)."""
    p = OUT / rel
    key = rel.replace("\\", "/")
    if p.exists() and p.stat().st_size > 0 and not REFRESH:
        data = p.read_bytes()
        with _lock:
            if key not in MANIFEST:
                MANIFEST[key] = {"file": key, "url": url, "status": 200, "bytes": len(data),
                                 "sha256": hashlib.sha256(data).hexdigest(), "content_type": "",
                                 "fetched": "cached"}
        return 200, data, url
    r = hget(url, **kw)
    if r["status"] == 200:
        save(rel, r["body"], url, 200, r["headers"].get("Content-Type", ""))
    else:
        with _lock:
            FAILURES.append({"url": url, "status": r["status"], "error": r["error"]})
    return r["status"], r["body"], r["url"]


def write_json(rel, obj):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


# ----------------------------------------------------------------------------
# Пути и URL
# ----------------------------------------------------------------------------
def norm(url):
    u = urllib.parse.urlparse(url)
    host = u.netloc.lower()
    if host == "www." + HOST:
        host = HOST
    path = u.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return f"https://{host}{path}"


def slug_of(url):
    p = urllib.parse.urlparse(url).path.strip("/")
    return p.replace("/", "__") if p else "index"


def page_rel(url):
    return f"html/{slug_of(url)}.html"


def asset_rel(url):
    u = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(u.path) or "/index"
    if path.endswith("/"):
        path += "index"
    path = re.sub(r'[<>:"|?*\\]', "_", path)
    if u.query:
        q = hashlib.md5(u.query.encode()).hexdigest()[:8]
        last = path.rsplit("/", 1)[-1]
        if "." in last:
            base, ext = path.rsplit(".", 1)
            path = f"{base}__q{q}.{ext}"
        else:
            path = f"{path}__q{q}" + (".css" if u.netloc == "fonts.googleapis.com" else "")
    return f"assets/{u.netloc}{path}"


def is_asset_host(host):
    host = host.lower()
    return host in ASSET_HOSTS or host.endswith(ASSET_HOST_SUFFIXES)


def is_page_url(url):
    last = urllib.parse.urlparse(url).path.rsplit("/", 1)[-1]
    return "." not in last or last.lower().endswith((".html", ".htm"))


URL_RE = re.compile(r"""https?://[^\s"'()<>\\]+""")


def asset_urls_in(text):
    out = set()
    for u in URL_RE.findall(text):
        u = htmllib.unescape(u).rstrip(",;.")
        pu = urllib.parse.urlparse(u)
        if not is_asset_host(pu.netloc):
            continue
        # базовые пути (staticPath, preconnect) - не файлы
        if pu.netloc.endswith(".selcdn.net") and not re.search(r"\.[A-Za-z][A-Za-z0-9]{0,4}$", pu.path):
            continue
        out.add(u)
    return out


def extract_links(html, base):
    internal, external = set(), set()
    for href in re.findall(r'<a\b[^>]*?\bhref="([^"]*)"', html, re.I):
        href = htmllib.unescape(href).strip()
        if not href or href.startswith(("#", "javascript:")):
            continue
        if href.startswith(("mailto:", "tel:")):
            external.add(href)
            continue
        u = urllib.parse.urljoin(base, href)
        pu = urllib.parse.urlparse(u)
        if pu.netloc.lower() in (HOST, "www." + HOST):
            internal.add(norm(u))
        else:
            external.add(u)
    return internal, external


# ----------------------------------------------------------------------------
# Разбор HTML (stdlib)
# ----------------------------------------------------------------------------
BLOCK = {"p", "div", "section", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "br",
         "tr", "table", "header", "footer", "nav", "blockquote", "article"}
SKIP = {"script", "style", "template", "svg", "noscript"}


class TextEx(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.o, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip += 1
        elif tag in BLOCK:
            self.o.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in BLOCK:
            self.o.append("\n")

    def handle_data(self, d):
        if not self.skip:
            self.o.append(d)


def html_to_text(frag):
    p = TextEx()
    p.feed(frag)
    p.close()
    s = "".join(p.o).replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


class Cleaner(HTMLParser):
    KEEP = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "br", "ul", "ol", "li", "strong", "b", "em",
            "i", "u", "a", "img", "blockquote", "table", "tr", "td", "th"}
    VOID = {"br", "img"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.o, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip += 1
            return
        if self.skip:
            return
        a = dict(attrs)
        q = lambda s: htmllib.escape(s or "", quote=True)
        if tag == "a":
            self.o.append(f'<a href="{q(a.get("href"))}">')
        elif tag == "img":
            self.o.append(f'<img src="{q(a.get("src"))}" alt="{q(a.get("alt"))}">')
        elif tag in self.KEEP:
            self.o.append(f"<{tag}>")
        elif tag in BLOCK:
            self.o.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in self.KEEP and tag not in self.VOID:
            self.o.append(f"</{tag}>")
        elif tag in BLOCK:
            self.o.append("\n")

    def handle_data(self, d):
        if not self.skip:
            self.o.append(htmllib.escape(d, quote=False))


def clean_html(frag):
    c = Cleaner()
    c.feed(frag)
    c.close()
    s = "".join(c.o).replace("\xa0", " ")
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def attrs_of(tag_html):
    d = {}
    for k, v in re.findall(r'([\w:.-]+)\s*=\s*"([^"]*)"', tag_html):
        d[k.lower()] = htmllib.unescape(v)
    for k, v in re.findall(r"([\w:.-]+)\s*=\s*'([^']*)'", tag_html):
        d.setdefault(k.lower(), htmllib.unescape(v))
    return d


def element_inner(html, start, tag):
    """Содержимое элемента tag, открывающий тег которого закончился в позиции start."""
    depth = 1
    pat = re.compile(rf"<(/?){tag}\b[^>]*>", re.I)
    for m in pat.finditer(html, start):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return html[start:m.start()]
    return html[start:]


def sections_of(html):
    res, end = [], 0
    for m in re.finditer(r"<section\b[^>]*>", html):
        if m.start() < end:
            continue
        inner = element_inner(html, m.end(), "section")
        end = m.end() + len(inner)
        res.append((attrs_of(m.group(0)), inner))
    return res


def field_inner(html, field):
    m = re.search(rf'<(\w+)\b[^>]*data-goods-field="{field}"[^>]*>', html)
    return element_inner(html, m.end(), m.group(1)) if m else None


def meta_of(html):
    meta = OrderedDict()
    for tag in re.findall(r"<meta\b[^>]*>", html, re.I):
        a = attrs_of(tag)
        key = a.get("name") or a.get("property")
        if key and "content" in a:
            meta[key] = a["content"]
    return meta


def tb_config(html):
    m = re.search(r"window\.tbConfig\s*=\s*(\{.*?\});", html, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return {}


# ----------------------------------------------------------------------------
# Этап 1. Метаданные сервера
# ----------------------------------------------------------------------------
def stage_meta():
    log("[1] Метаданные: robots, sitemap, 404, редиректы, TLS")
    status, body, _ = fetch_to("meta/robots.txt", SITE + "/robots.txt")
    status, sm, _ = fetch_to("meta/sitemap.xml", SITE + "/sitemap.xml")
    r = hget(SITE + "/no-such-page-for-backup-check")
    save("meta/404_page.html", r["body"], r["url"], r["status"], r["headers"].get("Content-Type", ""))
    fav = hget(SITE + "/favicon.ico")   # у сайта PNG-иконки; /favicon.ico ожидаемо 404

    r = hget(SITE + "/")
    write_json("meta/home_response_headers.json", {"status": r["status"], "headers": r["headers"]})

    checks = []
    for u in ["http://rida-art.ru/", "http://www.rida-art.ru/", "https://www.rida-art.ru/",
              "https://rida-art.ru/index.html", "https://rida-art.ru/angels/"]:
        p = urllib.parse.urlparse(u)
        cls = http.client.HTTPSConnection if p.scheme == "https" else http.client.HTTPConnection
        try:
            c = cls(p.netloc, timeout=20)
            c.request("GET", p.path or "/", headers={"User-Agent": UA})
            resp = c.getresponse()
            checks.append({"url": u, "status": resp.status, "location": resp.getheader("Location")})
            resp.read()
            c.close()
        except Exception as e:
            checks.append({"url": u, "error": repr(e)})

    tls = {}
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((HOST, 443), timeout=20) as s:
            with ctx.wrap_socket(s, server_hostname=HOST) as ss:
                cert = ss.getpeercert()
                tls = {"protocol": ss.version(), "subject": cert.get("subject"),
                       "issuer": cert.get("issuer"), "notBefore": cert.get("notBefore"),
                       "notAfter": cert.get("notAfter"), "subjectAltName": cert.get("subjectAltName")}
    except Exception as e:
        tls = {"error": repr(e)}
    try:
        ips = sorted({x[4][0] for x in socket.getaddrinfo(HOST, 443)})
    except Exception as e:
        ips = [repr(e)]
    write_json("meta/redirects_and_tls.json", {"redirect_checks": checks, "tls": tls, "resolved_ips": ips,
                                               "favicon_ico_status": fav["status"]})

    entries = []
    for m in re.finditer(r"<url>(.*?)</url>", sm.decode("utf-8", "replace"), re.S):
        loc = re.search(r"<loc>(.*?)</loc>", m.group(1))
        lm = re.search(r"<lastmod>(.*?)</lastmod>", m.group(1))
        if loc:
            entries.append((norm(htmllib.unescape(loc.group(1)).strip()), lm.group(1) if lm else None))
    log(f"    sitemap: {len(entries)} URL")
    return entries


# ----------------------------------------------------------------------------
# Этап 2. Страницы
# ----------------------------------------------------------------------------
def stage_pages(sitemap_entries):
    log("[2] Страницы: sitemap + обход внутренних ссылок")
    lastmod = dict(sitemap_entries)
    pages = OrderedDict()   # url -> {status, rel, final_url, html}
    queue = deque(u for u, _ in sitemap_entries)
    seen = set(queue)
    ext_links = {}

    def get(url):
        st, body, final = fetch_to(page_rel(url), url)
        return url, st, body, final

    with ThreadPoolExecutor(WORKERS) as pool:
        while queue:
            batch = []
            while queue:
                batch.append(queue.popleft())
            for url, st, body, final in pool.map(get, batch):
                nul = st == 200 and bool(body) and not body.strip(b"\x00")   # файл из одних нулей (битая публикация)
                html = body.decode("utf-8", "replace") if st == 200 and not nul else ""
                pages[url] = {"status": st, "rel": page_rel(url), "final_url": final, "html": html,
                              "lastmod": lastmod.get(url), "nul": nul, "internal": []}
                if st != 200 or nul:
                    if nul:
                        log(f"    ВНИМАНИЕ: {url} отдаёт файл из одних нулевых байтов ({len(body)} байт)")
                    continue
                internal, external = extract_links(html, url)
                pages[url]["internal"] = sorted(internal)
                ext_links[url] = sorted(external)
                for l in internal:
                    if l not in seen and is_page_url(l):
                        seen.add(l)
                        queue.append(l)
                        log(f"    найдена страница вне sitemap: {l}")
    return pages, ext_links


def goods_ids_in(html):
    ids = []
    for pat in (r'data-cart-goods-id="([^"]+)"', r'data-goods-id="([^"]+)"'):
        for i in re.findall(pat, html):
            if i not in ids:
                ids.append(i)
    # полный список товаров каталожного блока (в HTML отрисованы только первые 12 карточек)
    for val in re.findall(r'<input[^>]*name="goodsIds"[^>]*value="([^"]*)"', html):
        for i in val.split(","):
            if i and i not in ids:
                ids.append(i)
    return ids


def catalog_def(attrs, inner):
    """Описание каталожного блока: полный список товаров, сортировка, скрытые поля."""
    def hidden(name):
        m = re.search(rf'<input[^>]*name="{name}"[^>]*value="([^"]*)"', inner)
        return htmllib.unescape(m.group(1)) if m else None

    raw = hidden("goodsIds")
    if raw is not None:
        ids, source = [i for i in raw.split(",") if i], "goodsIds input"
    else:
        ids, source = [], "cards"
        for i in re.findall(r'data-cart-goods-id="([^"]+)"', inner) + re.findall(r"selstorage\.ru/([a-z]{7})/", inner):
            if i not in ids:
                ids.append(i)
        if not ids:
            return None
    h2 = re.search(r"<h2\b[^>]*>(.*?)</h2>", inner, re.S)
    return {"section_id": attrs.get("id"), "type": attrs.get("data-type"), "subtype": attrs.get("data-subtype"),
            "heading": html_to_text(h2.group(1)) if h2 else None, "source": source, "goods_ids": ids,
            "cards_in_html": len(re.findall(r"js-catalog__item", inner)),
            "sorting": hidden("sorting"), "hidden_fields": hidden("hiddenFields")}


def stage_missing_products(pages, sitemap_entries):
    """Товары, упомянутые в каталогах, но без страницы в sitemap - пробуем /product-<id>."""
    ids = set()
    for p in pages.values():
        ids.update(goods_ids_in(p["html"]))
    added = []
    for i in sorted(ids):
        url = f"{SITE}/product-{i}"
        if url in pages:
            continue
        st, body, final = fetch_to(page_rel(url), url)
        pages[url] = {"status": st, "rel": page_rel(url), "final_url": final,
                      "html": body.decode("utf-8", "replace") if st == 200 else "", "lastmod": None}
        added.append((i, st))
    if added:
        log(f"    товары вне sitemap: {added}")
    return ids


# ----------------------------------------------------------------------------
# Этап 3. Ресурсы
# ----------------------------------------------------------------------------
def stage_assets(pages):
    log("[3] Ресурсы: картинки, CSS, шрифты")
    refs = {}     # url -> set(источники)
    for url, p in pages.items():
        for a in asset_urls_in(p["html"]):
            refs.setdefault(a, set()).add(url)
    done, results = set(), {}
    pending = set(refs)

    def dl(u):
        st, body, _ = fetch_to(asset_rel(u), u)
        return u, st, body

    with ThreadPoolExecutor(WORKERS) as pool:
        while pending:
            batch = sorted(pending - done)
            pending = set()
            if not batch:
                break
            log(f"    скачиваю {len(batch)} ресурсов...")
            for u, st, body in pool.map(dl, batch):
                done.add(u)
                results[u] = st
                is_css = u.lower().split("?")[0].endswith(".css") or "fonts.googleapis.com" in u
                if st == 200 and is_css:
                    css = body.decode("utf-8", "replace")
                    found = re.findall(r"url\(\s*['\"]?([^'\")]+?)['\"]?\s*\)", css)
                    found += re.findall(r"@import\s+(?:url\()?['\"]?([^'\")\s;]+)", css)
                    for ref in found:
                        if ref.startswith("data:"):
                            continue
                        full = urllib.parse.urljoin(u, htmllib.unescape(ref))
                        if is_asset_host(urllib.parse.urlparse(full).netloc) and full not in done:
                            refs.setdefault(full, set()).add(u)
                            pending.add(full)
    bad = {u: s for u, s in results.items() if s != 200}
    log(f"    ресурсов: {len(results)}, ошибок: {len(bad)}")
    return refs, results


# ----------------------------------------------------------------------------
# Этап 4. API с данными товаров
# ----------------------------------------------------------------------------
def stage_api(goods_ids, home_html):
    log("[4] API: /api/v3/products/blocks")
    cart_hash = tb_config(home_html).get("cartHash", "")
    ids = sorted(goods_ids)
    goods, children, params, missing = {}, [], [], []
    n = 0
    for i in range(0, len(ids), 20):
        batch = ids[i:i + 20]
        n += 1
        rel = f"api/products_blocks_{n:02d}.json"
        p = OUT / rel
        if p.exists() and not REFRESH:
            data = json.loads(p.read_text(encoding="utf-8"))
        else:
            r = hget(SITE + "/api/v3/products/blocks", "POST",
                     json.dumps({"hash": cart_hash, "ids": batch}).encode(),
                     {"Content-Type": "application/json", "Origin": SITE, "Referer": SITE + "/"})
            if r["status"] != 200:
                FAILURES.append({"url": "POST /api/v3/products/blocks", "status": r["status"], "error": r["error"]})
                continue
            save(rel, r["body"], "POST " + SITE + "/api/v3/products/blocks", 200, "application/json")
            data = json.loads(r["body"].decode("utf-8"))
            write_json(f"api/products_blocks_{n:02d}.request_ids.json", batch)
        for g in data.get("goods", []):
            goods[g["id"]] = g
        children += data.get("children", [])
        params += data.get("params", [])
        time.sleep(0.2)
    for i in ids:
        if i not in goods:
            missing.append(i)
    log(f"    товаров из API: {len(goods)} из {len(ids)}; вариантов: {len(children)}; отсутствуют: {missing}")
    return goods, children, params, missing


# ----------------------------------------------------------------------------
# Этап 5. Структурированный экспорт
# ----------------------------------------------------------------------------
def section_info(attrs, inner):
    imgs = sorted(asset_urls_in(inner))
    imgs = [u for u in imgs if ".selstorage.ru/" in u]
    links = []
    for href, label in re.findall(r'<a\b[^>]*?\bhref="([^"]*)"[^>]*>(.*?)</a>', inner, re.S | re.I):
        links.append({"href": htmllib.unescape(href), "text": html_to_text(label)})
    heads = []
    for lvl, txt in re.findall(r"<h([1-6])\b[^>]*>(.*?)</h\1>", inner, re.S | re.I):
        t = html_to_text(txt)
        if t:
            heads.append({"level": int(lvl), "text": t})
    return {"id": attrs.get("id"), "type": attrs.get("data-type"), "subtype": attrs.get("data-subtype"),
            "headings": heads, "text": html_to_text(inner), "html": clean_html(inner),
            "images": [{"url": u, "file": asset_rel(u)} for u in imgs], "links": links}


CHROME = {"header", "footer-customer", "script"}


def stage_extract(pages, sitemap_entries, ext_links, goods, children, params, missing):
    log("[5] Структурированный экспорт")
    page_records, product_pages, listed, catalogs = [], {}, {}, []
    section_types = Counter()
    site = {"menu": [], "footer": {}, "contacts": {}, "custom_scripts": [], "maps": [], "icons": [],
            "logos": [], "forms_found_on": []}

    for url, p in pages.items():
        if p["status"] != 200:
            continue
        if p.get("nul"):
            page_records.append({"url": url, "slug": slug_of(url), "file": p["rel"], "lastmod": p["lastmod"],
                                 "corrupt_nul": True, "title": "", "text": "", "sections": []})
            continue
        html = p["html"]
        secs = sections_of(html)
        title = (re.search(r"<title>(.*?)</title>", html, re.S) or [None, ""])[1]
        meta = meta_of(html)
        canon = re.search(r'<link[^>]*rel="canonical"[^>]*href="([^"]*)"', html)
        internal, external = extract_links(html, url)
        sec_recs = []
        for a, inner in secs:
            t = a.get("data-type")
            section_types[(t, a.get("data-subtype"))] += 1
            if t not in CHROME:
                sec_recs.append(section_info(a, inner))
            if t == "header" and url == SITE + "/":
                site["menu"] = [{"text": html_to_text(l), "href": h} for h, l in
                                re.findall(r'<a\b[^>]*?\bhref="([^"]*)"[^>]*>(.*?)</a>', inner, re.S) if html_to_text(l)]
                site["logos"].append([u for u in asset_urls_in(inner) if ".selstorage.ru/" in u])
            if t == "footer-customer" and url == SITE + "/":
                site["footer"] = {"text": html_to_text(inner),
                                  "links": [{"text": html_to_text(l), "href": h} for h, l in
                                            re.findall(r'<a\b[^>]*?\bhref="([^"]*)"[^>]*>(.*?)</a>', inner, re.S)
                                            if html_to_text(l)]}
                site["logos"].append([u for u in asset_urls_in(inner) if ".selstorage.ru/" in u])
            if t == "script" and url == SITE + "/":
                site["custom_scripts"].append({"id": a.get("id"), "html": inner.strip()})
            if t == "contacts" and url == SITE + "/":
                site["contacts"] = {"text": html_to_text(inner)}
                for dm in re.findall(r'data-map="([^"]*)"', inner):
                    try:
                        site["maps"].append(json.loads(htmllib.unescape(dm)))
                    except Exception:
                        pass
            if "form" in (t or "") or "<form" in inner:
                site["forms_found_on"].append({"url": url, "section": t})
            if t != "product-page" and t not in CHROME and not slug_of(url).startswith("product-"):
                cat = catalog_def(a, inner)
                if cat:
                    catalogs.append(dict(cat, page=slug_of(url), url=url, page_title=title.strip()))
                    for pos, gid in enumerate(cat["goods_ids"], 1):
                        listed.setdefault(gid, []).append(
                            {"slug": slug_of(url), "url": url, "page_title": title.strip(),
                             "section": cat["heading"], "position": pos})
            if t == "product-page":
                product_pages[a.get("data-goods-id")] = (url, inner)
        if url == SITE + "/":
            site["icons"] = [attrs_of(t) for t in re.findall(r"<link\b[^>]*rel=\"[^\"]*icon[^\"]*\"[^>]*>", html)]
            site["tbConfig"] = {k: v for k, v in tb_config(html).items() if k != "cartHash"}
            site["meta"] = meta
            site["phones"] = sorted(set(re.findall(r"8 \(\d{3}\) \d{3}-\d{2}-\d{2}", html)))
        page_records.append({
            "url": url, "slug": slug_of(url), "file": p["rel"], "lastmod": p["lastmod"],
            "final_url": p["final_url"], "lang": (re.search(r'<html[^>]*lang="([^"]*)"', html) or [None, None])[1],
            "title": title.strip(), "meta": meta, "canonical": canon.group(1) if canon else None,
            "text": html_to_text("".join(i for a_, i in secs if a_.get("data-type") not in CHROME)),
            "sections": sec_recs,
            "internal_links": sorted(internal), "external_links": sorted(external)})

    # --- товары ---
    lm = dict(sitemap_entries)
    # у каждого фото есть основной файл (страница товара) и уменьшенное превью для каталога
    rend = {}
    for p_ in pages.values():
        for m in re.finditer(r"https://[a-z0-9-]+\.selstorage\.ru/([a-z]{7})/([0-9a-f-]{36})/[^\s\"'()<>\\]+", p_["html"]):
            rend.setdefault((m.group(1), m.group(2)), set()).add(htmllib.unescape(m.group(0)).rstrip(",;."))
    kids = {}
    for c in children:
        kids.setdefault(c.get("parentId"), []).append(c)
    products = []
    for gid in sorted(set(goods) | set(product_pages) | set(listed)):
        api = goods.get(gid, {})
        purl, inner = product_pages.get(gid, (None, ""))
        imgs, seen_img = [], set()
        for tag in re.findall(r"<img\b[^>]*data-image-id=[^>]*>", inner):
            a = attrs_of(tag)
            if a.get("data-image-id") in seen_img or not a.get("src"):
                continue
            seen_img.add(a["data-image-id"])
            others = sorted(u for u in rend.get((gid, a["data-image-id"]), ()) if u != a["src"])
            imgs.append({"id": a["data-image-id"], "url": a["src"], "file": asset_rel(a["src"]), "alt": a.get("alt"),
                         "thumbnails": [{"url": u, "file": asset_rel(u)} for u in others]})
        t_html = field_inner(inner, "title")
        d_html = field_inner(inner, "description")
        pr = field_inner(inner, "priceFull")
        po = field_inner(inner, "priceOldFull")
        products.append(OrderedDict([
            ("id", gid), ("url", purl or f"{SITE}/product-{gid}"), ("has_page", bool(purl)),
            ("sitemap_lastmod", lm.get(purl)) if purl else ("sitemap_lastmod", None),
            ("title", html_to_text(t_html) if t_html else api.get("title")),
            ("price", api.get("price")), ("price_text", html_to_text(pr) if pr else api.get("priceFull")),
            ("price_old", api.get("priceOld")), ("price_old_text", (html_to_text(po) if po else api.get("priceOldFull")) or ""),
            ("description", html_to_text(d_html) if d_html else (api.get("description") or "")),
            ("description_html", clean_html(d_html) if d_html else ""),
            ("api_description", api.get("description")), ("api_description_full", api.get("descriptionFull")),
            ("quantity", api.get("quantity")), ("is_hidden", api.get("isHidden")),
            ("child_count", api.get("childCount")), ("pos_available", api.get("isPosAvailable")),
            ("listed_on", listed.get(gid, [])), ("images", imgs), ("variants", kids.get(gid, [])),
            ("in_api", gid in goods)]))
    write_json("data/products.json", {"generated": now(), "count": len(products), "api_params": params,
                                      "api_variants": children, "api_missing_ids": missing, "products": products})
    with open(OUT / "data/products.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["id", "url", "title", "price", "price_old", "description", "api_description_full", "quantity",
                    "is_hidden", "child_count", "pos_available", "listed_on", "images_count", "images_local",
                    "images_url", "sitemap_lastmod"])
        for pr_ in products:
            w.writerow([pr_["id"], pr_["url"], pr_["title"], pr_["price"], pr_["price_old"] or "",
                        pr_["description"].replace("\n", " / "), pr_["api_description_full"] or "",
                        pr_["quantity"] if pr_["quantity"] is not None else "", pr_["is_hidden"],
                        pr_["child_count"], pr_["pos_available"],
                        ";".join(x["slug"] for x in pr_["listed_on"]), len(pr_["images"]),
                        ";".join(i["file"] for i in pr_["images"]), ";".join(i["url"] for i in pr_["images"]),
                        pr_["sitemap_lastmod"] or ""])
    write_json("data/catalogs.json", {"generated": now(), "count": len(catalogs), "catalogs": catalogs})
    write_json("data/pages.json", {"generated": now(), "count": len(page_records), "pages": page_records})
    site["section_types"] = [{"type": k[0], "subtype": k[1], "count": v} for k, v in sorted(section_types.items(), key=str)]
    write_json("data/site.json", site)
    write_json("data/external_links.json", ext_links)
    return products, page_records, site


# ----------------------------------------------------------------------------
# Этап 6. Проверка и манифест
# ----------------------------------------------------------------------------
def stage_verify(sitemap_entries, pages, refs, results, products, goods):
    log("[6] Проверка полноты")
    v = OrderedDict()
    v["sitemap_urls"] = len(sitemap_entries)
    v["pages_fetched_ok"] = sum(1 for p in pages.values() if p["status"] == 200)
    v["pages_failed"] = {u: p["status"] for u, p in pages.items() if p["status"] != 200}
    v["pages_outside_sitemap"] = [u for u in pages if u not in dict(sitemap_entries)]
    v["pages_corrupt_all_nul"] = [u for u, p in pages.items() if p.get("nul")]
    broken = {}
    for u, p in pages.items():
        for target in p.get("internal", []):
            t = pages.get(target)
            if t is not None and (t["status"] != 200 or t.get("nul")):
                broken.setdefault(target, []).append(slug_of(u))
    v["broken_internal_links"] = {t: {"status": pages[t]["status"], "linked_from_pages": len(s), "examples": s[:3]}
                                  for t, s in broken.items()}
    try:
        cats = json.loads((OUT / "data/catalogs.json").read_text(encoding="utf-8"))["catalogs"]
        v["catalogs"] = [{"page": c["page"], "heading": c["heading"], "goods": len(c["goods_ids"]),
                          "cards_in_html": c["cards_in_html"], "source": c["source"]} for c in cats]
    except Exception as e:
        v["catalogs"] = repr(e)
    v["assets_referenced"] = len(refs)
    v["assets_ok"] = sum(1 for s in results.values() if s == 200)
    v["assets_failed"] = {u: s for u, s in results.items() if s != 200}
    missing_files = [u for u in refs if not (OUT / asset_rel(u)).exists()]
    v["assets_missing_on_disk"] = missing_files
    v["products_total"] = len(products)
    v["products_without_page"] = [p["id"] for p in products if not p["has_page"]]
    v["products_without_images"] = [p["id"] for p in products if not p["images"]]
    v["products_missing_in_api"] = [p["id"] for p in products if not p["in_api"]]
    v["products_hidden"] = [p["id"] for p in products if p["is_hidden"]]
    v["products_with_variants"] = [p["id"] for p in products if p["child_count"]]
    v["products_not_listed_in_any_catalog"] = [p["id"] for p in products if not p["listed_on"]]
    v["product_images_missing_on_disk"] = [i["file"] for p in products for i in p["images"] if not (OUT / i["file"]).exists()]
    known = {(p["id"], i["id"]) for p in products for i in p["images"]}
    covered = {i["file"] for p in products for i in p["images"]} | \
              {t["file"] for p in products for i in p["images"] for t in i["thumbnails"]}
    stray = []
    for f in (OUT / "assets").rglob("*"):
        parts = f.relative_to(OUT).as_posix().split("/")
        if f.is_file() and len(parts) == 5 and parts[1].startswith("cc3c1d0e") and parts[4].endswith((".jpeg", ".jpg", ".png")):
            if f.relative_to(OUT).as_posix() not in covered:
                stray.append(f.relative_to(OUT).as_posix())
    v["goods_images_not_linked_to_any_product"] = stray
    mism = []
    for p in products:
        g = goods.get(p["id"])
        if g and (g.get("price") != p["price"] and p["price_text"] != g.get("priceFull")):
            mism.append({"id": p["id"], "html": p["price_text"], "api": g.get("priceFull")})
        if g and p["title"] and p["title"] != g.get("title"):
            mism.append({"id": p["id"], "title_html": p["title"], "title_api": g.get("title")})
    v["html_vs_api_mismatches"] = mism
    v["placeholder_descriptions"] = [p["id"] for p in products if (p["api_description"] or "").startswith("Краткое описание")]
    v["empty_descriptions"] = [p["id"] for p in products if not p["description"]]
    v["failures"] = FAILURES
    write_json("verify.json", v)
    return v


def write_manifest():
    rows = []
    for p in sorted(OUT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(OUT).as_posix()
        if rel in ("MANIFEST.csv", "MANIFEST.json"):
            continue
        rec = MANIFEST.get(rel)
        data = p.read_bytes()
        rows.append({"file": rel, "kind": "fetched" if rec else "derived", "url": rec["url"] if rec else "",
                     "status": rec["status"] if rec else "", "bytes": len(data),
                     "sha256": hashlib.sha256(data).hexdigest()})
    with open(OUT / "MANIFEST.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "kind", "url", "status", "bytes", "sha256"], delimiter=";")
        w.writeheader()
        w.writerows(rows)
    return rows


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    log(f"Старт. Каталог: {OUT}  refresh={REFRESH}")
    sitemap_entries = stage_meta()
    pages, ext_links = stage_pages(sitemap_entries)
    goods_ids = stage_missing_products(pages, sitemap_entries)
    refs, results = stage_assets(pages)
    home_html = pages.get(SITE + "/", {}).get("html", "")
    goods, children, params, missing = stage_api(goods_ids, home_html)
    products, page_records, site = stage_extract(pages, sitemap_entries, ext_links, goods, children, params, missing)
    v = stage_verify(sitemap_entries, pages, refs, results, products, goods)
    rows = write_manifest()
    total = sum(r["bytes"] for r in rows)
    log(f"Готово за {time.time() - t0:.0f} c. Файлов: {len(rows)}, {total / 1048576:.1f} МБ")
    log("ИТОГ ПРОВЕРКИ: " + json.dumps({k: (len(x) if isinstance(x, (list, dict)) else x) for k, x in v.items()},
                                         ensure_ascii=False))


if __name__ == "__main__":
    main()
