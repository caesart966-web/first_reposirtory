#!/usr/bin/env python3
"""Перерисовывает первый кадр серии сторис (assets/promo/x-pto-1-glavnaya.jpg).

Зачем. На кадре сайт показан снимками экрана, и на одном из них видны
карточки объектов. Когда объект убирают из data/site.json, со страниц он
исчезает сам, а со снимка — нет: картинка так и лежит в интернете с тем,
чего на сайте уже нет. Плюс подпись «8 объектов» — число, написанное
руками, которое молча расходится со списком.

Здесь всё собирается заново: снимки делает браузер прямо из dist/,
а числа считаются по данным.

Запуск (после обычной сборки):
    python3 build.py && python3 tools/make-story-cover.py

Нужен playwright: pip install playwright
"""
import base64
import html
import json
import functools
import http.server
import pathlib
import re
import socketserver
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
OUT = ROOT / "assets" / "promo" / "x-pto-1-glavnaya.jpg"
PORT = 8477

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Нужен playwright: pip install playwright")


def find_chrome():
    import os
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


def data_uri(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


COVER = """
<style>
  @font-face {{ font-family: "DisplayVar"; src: url("{f}/geologica-cyrillic.woff2") format("woff2");
               font-weight: 300 800; font-display: block; }}
  @font-face {{ font-family: "InterVar"; src: url("{f}/inter-cyrillic.woff2") format("woff2");
               font-weight: 300 800; font-display: block; }}
  @font-face {{ font-family: "MonoVar"; src: url("{f}/mono-cyrillic.woff2") format("woff2");
               font-weight: 400 700; font-display: block; }}
  @font-face {{ font-family: "MonoVar"; src: url("{f}/mono-latin.woff2") format("woff2");
               font-weight: 400 700; font-display: block; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ width: 1080px; height: 1920px; overflow: hidden;
         font-family: "InterVar", sans-serif; background: #0a1420; color: #fff; }}
  .frame {{ position: relative; width: 1080px; height: 1920px;
           padding: 96px 72px 84px; display: flex; flex-direction: column; }}
  .grid {{ position: absolute; inset: 0;
          background-image: linear-gradient(rgba(255,255,255,.045) 1px, transparent 1px),
                            linear-gradient(90deg, rgba(255,255,255,.045) 1px, transparent 1px);
          background-size: 64px 64px; }}
  .glow {{ position: absolute; inset: 0;
          background: radial-gradient(58% 34% at 80% 2%, rgba(31,111,235,.34), transparent 66%); }}
  .top {{ position: relative; display: flex; align-items: center; gap: 20px; margin-bottom: 58px; }}
  .mark {{ width: 62px; height: 62px; flex: none; }}
  .name {{ font-family: "DisplayVar", sans-serif; font-weight: 700; font-size: 52px; letter-spacing: .01em; }}
  .tag {{ font-family: "MonoVar", monospace; font-size: 15px; letter-spacing: .16em;
         text-transform: uppercase; color: #9fb4cd; margin-top: 6px; }}
  h1 {{ position: relative; font-family: "DisplayVar", sans-serif; font-weight: 700;
       font-size: 64px; line-height: 1.08; letter-spacing: -0.02em; margin-bottom: 30px; }}
  h1 span {{ color: #7fb0ff; }}
  .facts {{ position: relative; font-family: "MonoVar", monospace; font-size: 18px;
           letter-spacing: .13em; text-transform: uppercase; color: #9fb4cd; line-height: 1.85; }}
  .facts b {{ color: #fff; font-weight: 600; }}

  /* Снимки экрана лежат под небольшим наклоном — так видно, что это сайт,
     а не картинка, и кадр перестаёт быть плоским списком. */
  .stage {{ position: relative; flex: 1; margin-top: 44px; perspective: 1700px; }}
  .shot {{ position: absolute; border-radius: 14px; overflow: hidden;
          box-shadow: 0 40px 90px rgba(0,0,0,.55); border: 1px solid rgba(255,255,255,.12);
          background: #0d1c30; }}
  .shot img {{ display: block; width: 100%; }}
  .desk {{ left: -40px; top: 0; width: 900px;
          transform: rotateY(-13deg) rotateX(4deg) rotateZ(-2deg); }}
  .obj {{ right: -56px; top: 330px; width: 760px;
         transform: rotateY(-11deg) rotateX(3deg) rotateZ(-1.5deg); }}
  .phone {{ left: -18px; top: 430px; width: 296px; border-radius: 30px; border-width: 8px;
           border-color: rgba(255,255,255,.2);
           transform: rotateY(-12deg) rotateZ(-3deg); }}

  .foot {{ position: relative; padding-top: 34px; border-top: 1px solid rgba(255,255,255,.14);
          display: flex; align-items: flex-end; justify-content: space-between; }}
  .lbl {{ font-family: "MonoVar", monospace; font-size: 13px; letter-spacing: .14em;
         text-transform: uppercase; color: #9fb4cd; margin-bottom: 8px; }}
  .phone-num {{ font-family: "DisplayVar", sans-serif; font-weight: 700; font-size: 44px; }}
  .right {{ text-align: right; font-size: 21px; font-weight: 600; line-height: 1.4; }}
</style>
<div class="frame">
  <div class="grid"></div><div class="glow"></div>
  <div class="top">
    {logo}
    <div><div class="name">{company}</div><div class="tag">{tagline}</div></div>
  </div>
  <h1>Документация по объекту —<br><span>под ключ, по всей России</span></h1>
  <div class="facts">
    Проектирование · Исполнительная · Геодезия · Объёмы · Сдача<br>
    <b>{services} услуг</b> · <b>{objects} объектов</b> · работаем удалённо по всей России
  </div>
  <div class="stage">
    <div class="shot desk"><img src="{desk}" alt=""></div>
    <div class="shot obj"><img src="{obj}" alt=""></div>
    <div class="shot phone"><img src="{mob}" alt=""></div>
  </div>
  <div class="foot">
    <div><div class="lbl">Заявки и звонки</div><div class="phone-num">{tel}</div></div>
    <div class="right"><div class="lbl">Связь</div>Telegram {tg}<br>MAX: {max}</div>
  </div>
</div>
"""


def main() -> int:
    if not (DIST / "index.html").exists():
        print("Сначала соберите сайт: python3 build.py")
        return 1

    site = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
    services = json.loads((ROOT / "data" / "services.json").read_text(encoding="utf-8"))
    company, contacts = site["company"], site["contacts"]
    logo = re.sub(r"<!--.*?-->", "",
                  (ROOT / "assets" / "img" / "logo.svg").read_text(encoding="utf-8"),
                  flags=re.S).strip().replace("<svg", '<svg class="mark"', 1)

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass

    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", PORT),
                                 functools.partial(Quiet, directory=str(DIST)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{PORT}"
    chrome = find_chrome()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**({"executable_path": chrome} if chrome else {}))

            # Движение выключаем: иначе блоки на снимке останутся непроявленными.
            desk_ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                           reduced_motion="reduce")
            page = desk_ctx.new_page()
            page.goto(base + "/", wait_until="networkidle")
            page.wait_for_timeout(900)
            desk = page.screenshot()

            page.goto(base + "/obekty/", wait_until="networkidle")
            page.wait_for_timeout(700)
            page.evaluate("document.documentElement.style.scrollBehavior='auto'")
            # Прокручиваем честно, шагами: отложенные фотографии иначе
            # не успевают загрузиться и на снимке остаются пустые плитки.
            for y in range(0, 1400, 300):
                page.evaluate(f"window.scrollTo(0,{y})")
                page.wait_for_timeout(180)
            page.evaluate("window.scrollTo(0,150)")
            page.wait_for_timeout(700)
            obj = page.screenshot()
            desk_ctx.close()

            mob_ctx = browser.new_context(viewport={"width": 390, "height": 780},
                                          reduced_motion="reduce")
            page = mob_ctx.new_page()
            page.goto(base + "/", wait_until="networkidle")
            page.wait_for_timeout(900)
            mob = page.screenshot()
            mob_ctx.close()

            body = COVER.format(
                f=(ROOT / "assets" / "fonts").as_uri(),
                logo=logo,
                company=html.escape(company["name"]),
                tagline=html.escape(company["tagline"]),
                services=len(services),
                objects=len(site["portfolio"]["items"]),
                desk=data_uri(desk), obj=data_uri(obj), mob=data_uri(mob),
                tel=html.escape(contacts["phone_display"]),
                tg=html.escape(contacts["telegram_display"]),
                max=html.escape(contacts.get("max_display", "")),
            )
            shot_ctx = browser.new_context(viewport={"width": 1080, "height": 1920},
                                           device_scale_factor=1)
            page = shot_ctx.new_page()
            page.set_content(body)
            page.wait_for_timeout(700)
            page.screenshot(path=str(OUT), type="jpeg", quality=90)
            browser.close()
    finally:
        srv.shutdown()

    print(f"Готово: {OUT.relative_to(ROOT)}")
    print(f"  услуг на кадре: {len(services)}, объектов: {len(site['portfolio']['items'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
