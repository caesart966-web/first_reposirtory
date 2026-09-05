#!/usr/bin/env python3
"""Все ли символы сайта есть в шрифтах.

Шрифты урезаны до нужных символов — так они весят 8-30 КБ вместо сотен.
Обратная сторона: если в тексте появится символ, которого в наборе нет,
браузер молча подставит системный шрифт. Буква будет другой формы, и на
глаз это замечают не сразу. Проверка ловит такое сразу.

Запуск (нужен fonttools: pip install fonttools):
    python3 build.py && python3 tests/check_fonts.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
FONTS = ROOT / "assets" / "fonts"

# Какими шрифтами что набрано — совпадает с assets/style.css
FAMILIES = {
    "заголовки (Geologica)": ["geologica-cyrillic.woff2", "geologica-latin.woff2"],
    "текст (Inter)": ["inter-cyrillic.woff2", "inter-latin.woff2"],
    "цифры и подписи (JetBrains Mono)": ["mono-cyrillic.woff2", "mono-latin.woff2"],
}
# Служебная страница с картинками для сторис к сайту не относится
SKIP = ("assets/promo/",)
IGNORE = set(" \t\n\r ﻿&;#")

try:
    from fontTools.ttLib import TTFont
except ImportError:
    print("Проверка пропущена: нет fonttools (pip install fonttools)")
    sys.exit(0)


def site_text() -> set:
    chars = set()
    for page in DIST.rglob("*.html"):
        if any(s in str(page).replace("\\", "/") for s in SKIP):
            continue
        html = page.read_text(encoding="utf-8")
        html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
        html = re.sub(r"<[^>]+>", " ", html)
        for entity, ch in (("&nbsp;", " "), ("&mdash;", "—"), ("&ndash;", "–"),
                           ("&laquo;", "«"), ("&raquo;", "»"), ("&amp;", "&"),
                           ("&quot;", '"'), ("&#39;", "'"), ("&lt;", "<"), ("&gt;", ">")):
            html = html.replace(entity, ch)
        chars |= set(html)
    return chars


def main() -> int:
    if not DIST.exists():
        print("Сначала соберите сайт: python3 build.py")
        return 1
    text = site_text()
    bad = False
    for label, files in FAMILIES.items():
        have = set()
        for name in files:
            path = FONTS / name
            if not path.exists():
                print(f"  нет файла шрифта: {name}")
                bad = True
                continue
            have |= set(TTFont(path).getBestCmap())
        missing = sorted(c for c in text
                         if c not in IGNORE and not c.isspace() and ord(c) not in have)
        if missing:
            bad = True
            show = ", ".join(f"«{c}» U+{ord(c):04X}" for c in missing[:12])
            print(f"  {label}: не хватает символов — {show}")
        else:
            print(f"  {label}: все символы на месте")
    if bad:
        print("\nДобавьте символы в набор: tools/ — пересборка шрифта, "
              "и не забудьте unicode-range в assets/style.css")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
