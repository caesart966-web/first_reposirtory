#!/usr/bin/env python3
"""Иконки сайта из assets/img/favicon.svg.

Зачем: iOS не умеет ставить SVG на домашний экран, а старые браузеры и
некоторые агрегаторы ищут favicon.ico. Без них вместо знака компании
показывается пустой квадрат или буква из адреса.

Что делает: рисует знак в браузере и сохраняет
    assets/img/apple-touch-icon.png   180x180 — для iPhone и iPad
    assets/img/favicon.ico            32 и 16 — для старых браузеров

Файлы уже лежат в репозитории. Запускать нужно, только если поменялся знак:
    pip install playwright pillow && playwright install chromium
    python3 tools/make-icons.py
"""
import io
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SVG = ROOT / "assets" / "img" / "favicon.svg"
OUT = ROOT / "assets" / "img"

try:
    from PIL import Image
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Нужны playwright и pillow: pip install playwright pillow")


def render(size: int) -> Image.Image:
    """Рисует SVG в браузере и возвращает картинку нужного размера."""
    html = (f'<style>html,body{{margin:0}}svg{{display:block;width:{size}px;'
            f'height:{size}px}}</style>' + SVG.read_text(encoding="utf-8"))
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        page = browser.new_context(viewport={"width": size, "height": size},
                                   device_scale_factor=1).new_page()
        page.set_content(html)
        page.wait_for_timeout(200)
        shot = page.screenshot(omit_background=False)
        browser.close()
    return Image.open(io.BytesIO(shot)).convert("RGBA")


def main() -> None:
    big = render(180)
    big.save(OUT / "apple-touch-icon.png")
    print(f"  apple-touch-icon.png  180x180  {(OUT / 'apple-touch-icon.png').stat().st_size // 1024} КБ")
    ico = render(64)
    ico.save(OUT / "favicon.ico", sizes=[(32, 32), (16, 16)])
    print(f"  favicon.ico           32 и 16  {(OUT / 'favicon.ico').stat().st_size // 1024} КБ")


if __name__ == "__main__":
    main()
