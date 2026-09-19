#!/usr/bin/env python3
"""Картинки-обложки для соцсетей и мессенджеров (Open Graph), по одной на страницу.

Зачем. Когда ссылку на сайт кидают в Telegram, WhatsApp или ВКонтакте,
собеседник сначала видит карточку, и только потом — текст. Одна и та же
фотография на всех страницах означает, что ссылка на «Геодезию» и ссылка
на «Сметы» выглядят одинаково и не говорят ни слова о том, куда ведут.

Как. Каждая обложка рисуется браузером по тем же цветам и тем же шрифтам,
что и сайт, — поэтому она не может разойтись с ним по оформлению.
Заголовок берётся из готовой страницы (<h1>), а не пишется здесь руками.

Запуск (после обычной сборки):
    python3 build.py && python3 tools/make-og.py && python3 build.py

Вторая сборка нужна, чтобы страницы подхватили появившиеся файлы.
Нужен playwright: pip install playwright
"""
import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
OUT = ROOT / "assets" / "img" / "og"
FONTS = ROOT / "assets" / "fonts"

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


def page_name(rel: str) -> str:
    """dist/uslugi/geodeziya/index.html -> uslugi-geodeziya"""
    parts = pathlib.Path(rel).parent.parts
    return "-".join(parts) if parts else "home"


def collect():
    """Страницы сайта: адрес файла, заголовок, надстрочник над ним."""
    out = []
    for page in sorted(DIST.rglob("index.html")):
        rel = page.relative_to(DIST).as_posix()
        if rel.startswith("assets/"):
            continue
        s = page.read_text(encoding="utf-8")
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
        if not h1:
            continue
        title = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip()
        kicker = ""
        eyebrow = re.search(r'<(?:p|span|div)[^>]*class="[^"]*(?:eyebrow|kicker|section__tag)'
                            r'[^"]*"[^>]*>(.*?)</(?:p|span|div)>', s, re.S)
        if eyebrow:
            kicker = html.unescape(re.sub(r"<[^>]+>", "", eyebrow.group(1))).strip()
        out.append((page_name(rel), title, kicker))
    return out


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
  body {{ width: 1200px; height: 630px; overflow: hidden;
         font-family: "InterVar", sans-serif; background: #0d1c30; color: #fff; }}
  .card {{ position: relative; width: 1200px; height: 630px; padding: 64px 72px;
          display: flex; flex-direction: column; justify-content: space-between; }}
  /* Та же чертёжная сетка и то же световое пятно, что на тёмных блоках сайта */
  .grid {{ position: absolute; inset: 0;
          background-image: linear-gradient(rgba(255,255,255,.05) 1px, transparent 1px),
                            linear-gradient(90deg, rgba(255,255,255,.05) 1px, transparent 1px);
          background-size: 56px 56px; }}
  .glow {{ position: absolute; inset: 0;
          background: radial-gradient(70% 90% at 82% 8%, rgba(31,111,235,.42), transparent 62%); }}
  .bracket {{ position: absolute; right: 48px; bottom: 48px; width: 86px; height: 86px;
             border-right: 2px solid rgba(255,255,255,.18); border-bottom: 2px solid rgba(255,255,255,.18); }}
  .row {{ position: relative; display: flex; align-items: center; gap: 16px; }}
  .mark {{ width: 44px; height: 44px; flex: none; }}
  .name {{ font-family: "DisplayVar", sans-serif; font-weight: 700; font-size: 30px; letter-spacing: .01em; }}
  .tag {{ font-family: "MonoVar", monospace; font-size: 13px; letter-spacing: .14em;
         text-transform: uppercase; color: #9fb4cd; margin-top: 3px; }}
  .body {{ position: relative; }}
  .kicker {{ font-family: "MonoVar", monospace; font-size: 15px; letter-spacing: .14em;
            text-transform: uppercase; color: #7fb0ff; margin-bottom: 18px;
            display: flex; align-items: center; gap: 14px; }}
  .kicker::before {{ content: ""; width: 34px; height: 2px; background: #1f6feb; flex: none; }}
  h1 {{ font-family: "DisplayVar", sans-serif; font-weight: 700; font-size: {size}px;
       line-height: 1.08; letter-spacing: -0.015em; max-width: 1010px; }}
  .foot {{ position: relative; display: flex; align-items: center; justify-content: space-between;
          padding-top: 26px; border-top: 1px solid rgba(255,255,255,.14);
          font-family: "MonoVar", monospace; font-size: 17px; letter-spacing: .04em; color: #c9d7e8; }}
  .foot b {{ color: #fff; font-weight: 600; }}
</style>
<div class="card">
  <div class="grid"></div><div class="glow"></div><div class="bracket"></div>
  <div class="row">
    {logo}
    <div>
      <div class="name">{company}</div>
      <div class="tag">{tagline}</div>
    </div>
  </div>
  <div class="body">
    {kicker}
    <h1>{title}</h1>
  </div>
  <div class="foot"><span><b>{phone}</b></span><span>{domain}</span></div>
</div>
"""


def main() -> int:
    import json
    site = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
    company, contacts = site["company"], site["contacts"]
    domain = re.sub(r"^https?://", "", site["base_url"]).strip("/")
    logo = (ROOT / "assets" / "img" / "logo.svg").read_text(encoding="utf-8")
    logo = re.sub(r"<!--.*?-->", "", logo, flags=re.S).strip()
    logo = logo.replace("<svg", '<svg class="mark"', 1)

    pages = collect()
    if not pages:
        return print("Сначала соберите сайт: python3 build.py") or 1
    OUT.mkdir(parents=True, exist_ok=True)

    chrome = find_chrome()
    made = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(**({"executable_path": chrome} if chrome else {}))
        ctx = browser.new_context(viewport={"width": 1200, "height": 630},
                                  device_scale_factor=1)
        page = ctx.new_page()
        for name, title, kicker in pages:
            # Длинный заголовок набирается мельче — иначе он не помещается
            # в карточку и обрезается на самом важном слове.
            size = 68 if len(title) <= 34 else 58 if len(title) <= 52 else 48
            body = CARD.format(
                f=(ROOT / "assets" / "fonts").as_uri(),
                size=size,
                logo=logo,
                company=html.escape(company["name"]),
                tagline=html.escape(company["tagline"]),
                kicker=(f'<div class="kicker">{html.escape(kicker)}</div>' if kicker else ""),
                title=html.escape(title),
                phone=html.escape(contacts["phone_display"]),
                domain=html.escape(domain),
            )
            page.set_content(body)
            page.wait_for_timeout(120)
            page.screenshot(path=str(OUT / f"{name}.jpg"), type="jpeg", quality=88)
            made += 1
            print(f"  {name}.jpg — {title[:52]}")
        browser.close()
    print(f"\nГотово: {made} обложек в {OUT.relative_to(ROOT)}")
    print("Теперь пересоберите сайт, чтобы страницы их подхватили: python3 build.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
