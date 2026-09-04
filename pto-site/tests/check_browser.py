#!/usr/bin/env python3
"""Проверки сайта в настоящем браузере.

Ловит то, что не видно в исходном коде: съехавшую вёрстку, обрезанный текст,
недоступные для экранных дикторов места, неработающие кнопки.

Запуск:
    pip install playwright && playwright install chromium
    python3 build.py && python3 tests/check_browser.py

Что проверяет:
  1. страница нигде не уезжает вбок (ширины от 320 до 1600);
  2. текст нигде не обрезан — в том числе при увеличенном системном шрифте,
     который часто включают на телефонах;
  3. доступность по правилам WCAG 2.1 AA (библиотека axe-core, если она
     установлена рядом: npm pack axe-core);
  4. работают всплывающее окно с документом, галерея фотографий,
     мобильное меню и проверка полей формы;
  5. в консоли браузера нет ошибок.

Возвращает код 1, если что-то не так.
"""
import functools
import http.server
import os
import pathlib
import socketserver
import sys
import threading

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Нужен playwright: pip install playwright && playwright install chromium")

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
PORT = 8177
PAGES = ["/", "/uslugi/", "/uslugi/geodeziya/", "/obekty/", "/o-kompanii/",
         "/kontakty/", "/404.html"]
WIDTHS = (320, 360, 390, 768, 1024, 1280, 1440, 1600)
# Браузер можно указать вручную, если он лежит не там, где ждёт playwright
CHROME = os.environ.get("CHROME_PATH")

problems: list[str] = []

CLIPPED = """() => {
  const bad = [];
  document.querySelectorAll('*').forEach(el => {
    if (el.children.length && !el.matches(
        '.spec__val,.spec__row,.object__name,.rec__quote,.contact-card,.step,td,th')) return;
    const over = el.scrollWidth - el.clientWidth;
    if (over > 1 && el.clientWidth > 0 && el.getBoundingClientRect().width > 4) {
      bad.push((el.className || el.tagName) + ' +' + over + 'px «' +
               (el.textContent || '').trim().slice(0, 40) + '»');
    }
  });
  return [...new Set(bad)];
}"""


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
    socketserver.TCPServer.allow_reuse_address = True
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = socketserver.TCPServer(("127.0.0.1", PORT),
                                 functools.partial(Quiet, directory=str(DIST)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def axe_source():
    """Библиотека проверки доступности, если её положили рядом."""
    for path in (ROOT / "node_modules" / "axe-core" / "axe.min.js",
                 ROOT / "tests" / "axe.min.js"):
        if path.exists():
            return path.read_text(encoding="utf-8")
    return None


def main() -> int:
    if not DIST.exists():
        print("Сначала соберите сайт: python3 build.py")
        return 1
    srv = serve()
    base = f"http://127.0.0.1:{PORT}"
    axe = axe_source()

    with sync_playwright() as p:
        launch = {"executable_path": CHROME} if CHROME else {}
        browser = p.chromium.launch(**launch)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        errors: list[str] = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        # 1-2. вёрстка на всех ширинах, обычный и увеличенный шрифт.
        # Шрифт увеличиваем так же, как это делает настройка браузера
        # («Размер шрифта» в Chrome, системный масштаб на Android):
        # меняется размер по умолчанию, а не стиль страницы. Это важно —
        # от него зависят и rem, и точки переключения макета в em.
        cdp = ctx.new_cdp_session(page)
        for scale in (16, 20):
            cdp.send("Page.setFontSizes", {"fontSizes": {"standard": scale, "fixed": scale}})
            for width in WIDTHS:
                page.set_viewport_size({"width": width, "height": 900})
                for url in PAGES:
                    page.goto(base + url, wait_until="load")
                    page.wait_for_timeout(260)
                    over = page.evaluate("document.documentElement.scrollWidth") - width
                    if over > 1:
                        problems.append(f"{url} при ширине {width} ({scale}px): "
                                        f"страница шире экрана на {over}px")
                    for item in page.evaluate(CLIPPED):
                        problems.append(f"{url} при ширине {width} ({scale}px): "
                                        f"обрезан текст — {item}")

        # 3. доступность
        cdp.send("Page.setFontSizes", {"fontSizes": {"standard": 16, "fixed": 16}})
        page.set_viewport_size({"width": 1280, "height": 900})
        if axe:
            for url in PAGES:
                page.goto(base + url, wait_until="load")
                page.wait_for_timeout(4200)     # ждём появления блоков
                page.add_script_tag(content=axe)
                found = page.evaluate("""async () => {
                    const r = await axe.run(document, {runOnly: {type: 'tag', values:
                      ['wcag2a','wcag2aa','wcag21a','wcag21aa','best-practice']}});
                    return r.violations.map(v => v.impact + ' ' + v.id + ': ' + v.help);}""")
                for v in found:
                    problems.append(f"{url}: доступность — {v}")
        else:
            print("  (axe-core не найден, проверка доступности пропущена: "
                  "npm pack axe-core и положите axe.min.js в tests/)")

        # 4. живые элементы
        page.goto(base + "/obekty/", wait_until="load"); page.wait_for_timeout(2800)
        gallery = page.locator(".object__media--more").first
        gallery.scroll_into_view_if_needed(); gallery.click(); page.wait_for_timeout(600)
        if not page.is_visible(".lightbox img"):
            problems.append("/obekty/: галерея фотографий не открывается")
        page.keyboard.press("Escape"); page.wait_for_timeout(300)

        page.goto(base + "/o-kompanii/", wait_until="load"); page.wait_for_timeout(2800)
        page.locator(".rec__link").first.click(); page.wait_for_timeout(600)
        if not page.is_visible(".lightbox img"):
            problems.append("/o-kompanii/: документ не открывается")
        page.keyboard.press("Escape")

        page.goto(base + "/kontakty/", wait_until="load"); page.wait_for_timeout(2800)
        page.click("form button[type=submit]"); page.wait_for_timeout(300)
        if page.eval_on_selector_all(".field--error", "e => e.length") < 2:
            problems.append("/kontakty/: форма не ругается на пустые обязательные поля")

        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(base + "/", wait_until="load"); page.wait_for_timeout(2500)
        page.click(".burger"); page.wait_for_timeout(300)
        if not page.is_visible("#nav .nav__link"):
            problems.append("/: мобильное меню не открывается")

        if errors:
            for e in dict.fromkeys(errors):
                problems.append(f"ошибка в консоли браузера: {e[:120]}")
        browser.close()
    srv.shutdown()

    if problems:
        print(f"Найдено проблем: {len(problems)}")
        for item in problems:
            print("  •", item)
        return 1
    print("Проблем не найдено: вёрстка, доступность и живые элементы в порядке.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
