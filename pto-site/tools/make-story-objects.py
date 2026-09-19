#!/usr/bin/env python3
"""Перерисовывает кадр «Объекты» для сторис (assets/promo/x-pto-3-obekty.jpg).

Зачем отдельный инструмент. Кадры для сторис — единственное место на сайте,
где объекты нарисованы КАРТИНКОЙ. Когда объект убирают из data/site.json,
со страниц он исчезает сам, а с картинки — нет: она так и лежит в интернете
с тем, чего на сайте уже нет. Так и случилось с распределительным центром,
договор по которому расторгли.

Кадр собирается по тем же данным и тем же цветам, что и сайт, — разойтись
с ним он не может.

Запуск:  python3 tools/make-story-objects.py
Нужен playwright: pip install playwright
"""
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "promo" / "x-pto-3-obekty.jpg"

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


def photo_for(slug: str):
    """Фотография объекта, если она есть. Нет — карточка идёт с заставкой.

    Файл вшивается в страницу целиком (data:), а не даётся ссылкой: страница
    собирается в памяти браузера и своего адреса не имеет, поэтому ссылку
    на файл на диске он не откроет — карточки выходили пустыми."""
    import base64, mimetypes
    for name in (f"{slug}-960.webp", f"{slug}.webp", f"{slug}.jpg", f"{slug}.png"):
        path = ROOT / "assets" / "img" / "objects" / name
        if path.exists():
            mime = mimetypes.guess_type(name)[0] or "image/webp"
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            return f"data:{mime};base64,{data}"
    return ""


CARD = """
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
  .frame {{ position: relative; width: 1080px; height: 1920px; padding: 96px 72px 84px;
           display: flex; flex-direction: column; }}
  .grid {{ position: absolute; inset: 0;
          background-image: linear-gradient(rgba(255,255,255,.045) 1px, transparent 1px),
                            linear-gradient(90deg, rgba(255,255,255,.045) 1px, transparent 1px);
          background-size: 64px 64px; }}
  .glow {{ position: absolute; inset: 0;
          background: radial-gradient(60% 40% at 78% 4%, rgba(31,111,235,.34), transparent 65%); }}
  .top {{ position: relative; display: flex; align-items: center; gap: 18px; margin-bottom: 78px; }}
  .mark {{ width: 46px; height: 46px; flex: none; }}
  .name {{ font-family: "DisplayVar", sans-serif; font-weight: 700; font-size: 34px; }}
  .tag {{ font-family: "MonoVar", monospace; font-size: 13px; letter-spacing: .14em;
         text-transform: uppercase; color: #9fb4cd; margin-top: 4px; }}
  .eyebrow {{ position: relative; font-family: "MonoVar", monospace; font-size: 17px;
             letter-spacing: .16em; text-transform: uppercase; color: #7fb0ff; margin-bottom: 20px; }}
  h1 {{ position: relative; font-family: "DisplayVar", sans-serif; font-weight: 700;
       font-size: 72px; line-height: 1.06; letter-spacing: -0.02em; margin-bottom: 26px; }}
  h1 span {{ color: #4d8dfa; }}
  .lead {{ position: relative; font-size: 27px; line-height: 1.45; color: #c2d2e6;
          max-width: 880px; margin-bottom: 54px; }}
  .cards {{ position: relative; display: grid; grid-template-columns: 1fr 1fr;
           gap: 26px; }}
  .card {{ position: relative; border-radius: 16px; overflow: hidden;
          border: 1px solid rgba(255,255,255,.1); background: #101f33; height: 320px; }}
  .card img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .card .shade {{ position: absolute; inset: 0;
                 background: linear-gradient(to top, rgba(7,17,30,.94) 22%, rgba(7,17,30,.1) 62%); }}
  .card .cap {{ position: absolute; left: 22px; right: 22px; bottom: 20px; }}
  .card .city {{ font-family: "MonoVar", monospace; font-size: 13px; letter-spacing: .12em;
                text-transform: uppercase; color: #9fb4cd; margin-bottom: 6px; }}
  .card .ttl {{ font-size: 22px; font-weight: 650; line-height: 1.22; }}
  .foot {{ position: relative; margin-top: auto; padding-top: 34px;
          border-top: 1px solid rgba(255,255,255,.14);
          display: flex; align-items: flex-end; justify-content: space-between; }}
  .foot .lbl {{ font-family: "MonoVar", monospace; font-size: 13px; letter-spacing: .14em;
               text-transform: uppercase; color: #9fb4cd; margin-bottom: 8px; }}
  .foot .phone {{ font-family: "DisplayVar", sans-serif; font-weight: 700; font-size: 44px; }}
  .foot .right {{ text-align: right; font-size: 21px; font-weight: 600; line-height: 1.4; }}
</style>
<div class="frame">
  <div class="grid"></div><div class="glow"></div>
  <div class="top">
    {logo}
    <div><div class="name">{company}</div><div class="tag">{tagline}</div></div>
  </div>
  <div class="eyebrow">Объекты</div>
  <h1>Где мы уже <span>работали</span></h1>
  <p class="lead">{lead}</p>
  <div class="cards">{cards}</div>
  <div class="foot">
    <div><div class="lbl">Заявки и звонки</div><div class="phone">{phone}</div></div>
    <div class="right"><div class="lbl">Связь</div>Telegram {tg}<br>MAX: {max}</div>
  </div>
</div>
"""


def main() -> int:
    site = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
    company, contacts = site["company"], site["contacts"]
    items = site["portfolio"]["items"][:6]

    logo = re.sub(r"<!--.*?-->", "",
                  (ROOT / "assets" / "img" / "logo.svg").read_text(encoding="utf-8"),
                  flags=re.S).strip().replace("<svg", '<svg class="mark"', 1)

    cards = ""
    for it in items:
        src = photo_for(it["slug"])
        img = f'<img src="{src}" alt="">' if src else ""
        cards += (f'<div class="card">{img}<div class="shade"></div>'
                  f'<div class="cap"><div class="city">{html.escape(it["city"])}</div>'
                  f'<div class="ttl">{html.escape(it["name"])}</div></div></div>')

    body = CARD.format(
        f=(ROOT / "assets" / "fonts").as_uri(),
        logo=logo,
        company=html.escape(company["name"]),
        tagline=html.escape(company["tagline"]),
        lead=html.escape(site["portfolio"]["lead"]),
        cards=cards,
        phone=html.escape(contacts["phone_display"]),
        tg=html.escape(contacts["telegram_display"]),
        max=html.escape(contacts.get("max_display", "")),
    )

    chrome = find_chrome()
    with sync_playwright() as p:
        browser = p.chromium.launch(**({"executable_path": chrome} if chrome else {}))
        page = browser.new_context(viewport={"width": 1080, "height": 1920},
                                   device_scale_factor=1).new_page()
        page.set_content(body)
        page.wait_for_timeout(600)
        page.screenshot(path=str(OUT), type="jpeg", quality=90)
        browser.close()

    print(f"Готово: {OUT.relative_to(ROOT)} — объектов на кадре: {len(items)}")
    for it in items:
        print(f"  • {it['name']}, {it['city']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
