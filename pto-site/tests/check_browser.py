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
  2б. главная на всех ширинах от 320 до 1920 px с шагом 4 px — ловит
     щели между правилами вёрстки, которые фиксированные ширины пропускают;
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
         "/kontakty/", "/politika/", "/404.html"]
WIDTHS = (320, 360, 390, 768, 1024, 1280, 1440, 1600)
# Браузер можно указать вручную, если он лежит не там, где ждёт playwright
def _find_chrome() -> str | None:
    """Путь к браузеру: сначала переменная CHROME_PATH, потом то,
    что уже установлено в системе (в облачной среде это /opt/pw-browsers)."""
    env = os.environ.get("CHROME_PATH")
    if env and pathlib.Path(env).exists():
        return env
    for pattern in ("chromium-*/chrome-linux/chrome",
                    "chromium_headless_shell-*/chrome-headless-shell-linux64/"
                    "chrome-headless-shell"):
        found = sorted(pathlib.Path("/opt/pw-browsers").glob(pattern))
        if found:
            return str(found[-1])
    return None


CHROME = _find_chrome()

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
        # config.js на хостинг кладут руками, в сборке его нет — и не должно
        # быть, иначе обновление сайта затрёт настоящие настройки заявок.
        # Поэтому 404 на него ошибкой не считается.
        page.on("console", lambda m: errors.append(m.text)
                if m.type == "error" and "config.js" not in (m.location or {}).get("url", "")
                else None)
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

        # 2б. Перебор ВСЕХ ширин главной с шагом 4 px. Восемь фиксированных
        # ширин выше пропускали щели между правилами: на 980 px не работало
        # ни одно из двух соседних (одно кончалось на 979, другое начиналось
        # с 981), а на 1320-1336 px подпись в шапке возвращалась раньше, чем
        # для неё появлялось место. Обе щели нашёл только перебор.
        cdp.send("Page.setFontSizes", {"fontSizes": {"standard": 16, "fixed": 16}})
        page.goto(base + "/", wait_until="load")
        page.wait_for_timeout(600)
        gaps = []
        for width in range(320, 1921, 4):
            page.set_viewport_size({"width": width, "height": 900})
            over = page.evaluate("document.documentElement.scrollWidth - innerWidth")
            if over > 0:
                gaps.append(f"{width}px (+{over})")
        if gaps:
            problems.append("/: страница шире экрана на ширинах " + ", ".join(gaps[:8])
                            + (f" и ещё {len(gaps) - 8}" if len(gaps) > 8 else ""))
        page.set_viewport_size({"width": 1280, "height": 900})

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

        # Мобильное меню. Проверяем не «поставился ли класс», а поведение:
        # видна ли шапка в середине длинной страницы, стоит ли фон под
        # открытым меню и возвращается ли страница на место при закрытии.
        # Однажды здесь молча пропала липкость шапки — до меню и до кнопки
        # звонка приходилось прокручивать страницу до самого верха.
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(base + "/", wait_until="load"); page.wait_for_timeout(2500)
        page.evaluate("document.documentElement.style.scrollBehavior='auto';"
                      "window.scrollTo(0, 1400)")
        page.wait_for_timeout(350)
        # Шапка на телефоне уезжает при прокрутке вниз — так и задумано.
        # Проверяем главное: движение вверх возвращает её сразу же, иначе
        # до меню и телефона пришлось бы мотать страницу до самого верха.
        page.evaluate("window.scrollTo(0, 1200)")
        page.wait_for_timeout(450)
        started = page.evaluate("Math.round(window.scrollY)")
        header = page.evaluate("Math.round(document.querySelector('.header')"
                               ".getBoundingClientRect().bottom)")
        if header <= 0:
            problems.append("/: на телефоне шапка не возвращается при прокрутке вверх — "
                            "до меню не добраться")
        # Нажимаем по координатам, как пальцем: обычный click() сам
        # прокручивает страницу и подменяет то, что мы меряем.
        spot = page.evaluate("(() => {const r = document.querySelector('.burger')"
                             ".getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]})()")
        page.mouse.click(spot[0], spot[1]); page.wait_for_timeout(400)
        if not page.is_visible("#nav .nav__link"):
            problems.append("/: мобильное меню не открывается")
        panel = page.evaluate("Math.round(document.querySelector('.nav').getBoundingClientRect().top)")
        page.mouse.wheel(0, 900); page.wait_for_timeout(350)
        moved = page.evaluate("Math.round(document.querySelector('.nav').getBoundingClientRect().top)")
        if abs(moved - panel) > 1:
            problems.append("/: под открытым меню прокручивается страница")
        page.keyboard.press("Escape"); page.wait_for_timeout(450)
        if page.get_attribute(".burger", "aria-expanded") != "false":
            problems.append("/: меню не закрывается клавишей Esc")
        back = page.evaluate("Math.round(window.scrollY)")
        if abs(back - started) > 2:
            problems.append(f"/: после закрытия меню страница уехала: {started} -> {back}")

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
