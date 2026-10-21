"""Общие функции Playwright для локального стенда: https://svr-mos.ru/** → http://127.0.0.1:8090/**."""
import pathlib
from playwright.sync_api import sync_playwright
R = pathlib.Path(__file__).resolve().parent.parent
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
LOCAL = 'http://127.0.0.1:8090'


def route_site(context):
    def handler(route):
        u = route.request.url.replace('https://svr-mos.ru', LOCAL, 1)
        try:
            resp = route.fetch(url=u, max_redirects=0)
            headers = dict(resp.headers)
            if 'location' in headers:
                headers['location'] = headers['location'].replace(LOCAL, 'https://svr-mos.ru')
                if route.request.is_navigation_request() and 300 <= resp.status < 400:
                    # Браузер не отдаёт маршрутам запрос, по которому сам идёт за редиректом из fulfill,
                    # поэтому редирект навигации превращаем в meta refresh (cookies из ответа сохраняются).
                    loc = headers.pop('location'); headers['content-type'] = 'text/html; charset=utf-8'
                    route.fulfill(status=200, headers=headers, body=f'<meta http-equiv="refresh" content="0;url={loc}">')
                    return
            route.fulfill(status=resp.status, headers=headers, body=resp.body())
        except Exception as e:  # noqa
            route.abort()
    # Сначала «всё остальное» — abort (наружу ничего не уходит), затем svr-mos.ru → локальный стенд
    # (маршрут, добавленный последним, проверяется первым).
    context.route(lambda u: not u.startswith('https://svr-mos.ru'), lambda r: r.abort())
    context.route(lambda u: u.startswith('https://svr-mos.ru'), handler)


# Браузер всегда запускать через этот прокси-«тупик»: любой запрос, не перехваченный маршрутом, падает локально
# и не уходит в сеть; к локальному стенду route.fetch ходит напрямую (bypass).
import os as _os
CHROME = _os.environ.get('CHROME_PATH') or (CHROME if _os.path.exists(CHROME) else None)
LAUNCH = {**({'executable_path': CHROME} if CHROME else {}), 'proxy': {'server': 'http://127.0.0.1:9', 'bypass': '127.0.0.1,localhost'}}


def login(page):
    page.goto('https://svr-mos.ru/wp-login.php')
    page.fill('#user_login', 'admin')
    page.fill('#user_pass', 'admin')
    page.click('#wp-submit')
    page.wait_for_timeout(2500)
    page.goto('https://svr-mos.ru/wp-admin/')
    page.wait_for_load_state('networkidle')
