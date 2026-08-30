#!/usr/bin/env python3
"""
Урезает шрифты до символов, которые реально встречаются на сайте.

Зачем: готовые шрифты содержат тысячи знаков — латиницу с диакритикой всех
европейских языков, валюты, стрелки, служебные символы. Нам нужны кириллица,
цифры, латиница и десяток знаков препинания. После урезки файлы весят в
2-4 раза меньше, поэтому все шрифты успевают загрузиться до первой отрисовки:
посетитель сразу видит сайт в фирменных шрифтах, а не в системных.

Шрифт остаётся разделён на кириллическую и латинскую части — так браузер
качает только то, что нужно для показанного текста (в CSS это unicode-range).

Требуется: pip install fonttools brotli
Запуск:    python3 scripts/subset-fonts.py
Результат: public/fonts/*.woff2

Повторять нужно, только если в текстах появятся необычные символы.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES = ROOT / "node_modules"
OUT = ROOT / "public" / "fonts"

# Латиница, цифры, знаки препинания — то, что попадает в латинскую часть.
LATIN = "".join(chr(c) for c in range(0x20, 0x7F)) + " " + "«»„“”‘’—–…•·°×÷±≤≥≈→←↑↓✓✔✕✖€$"

# Кириллица — русский алфавит целиком плюс знак номера и рубля.
CYRILLIC = "".join(chr(c) for c in range(0x410, 0x450)) + "ЁёЄєІіЇїҐґ№₽"

# Какие файлы урезаем: (пакет npm, исходный файл, итоговое имя, набор знаков).
#
# Playfair Display — переменный шрифт: один файл на все начертания.
# PT Serif — обычный, поэтому светлое, жирное и курсив лежат отдельно.
# Курсив нужен только в статьях, поэтому его файлы не грузятся заранее
# (см. styles/fonts.css): браузер возьмёт их, только если курсив на странице есть.
JOBS = [
    ("@fontsource-variable/playfair-display", "playfair-display-cyrillic-wght-normal.woff2", "playfair-cyrillic.woff2", CYRILLIC),
    ("@fontsource-variable/playfair-display", "playfair-display-latin-wght-normal.woff2", "playfair-latin.woff2", LATIN),
    ("@fontsource/pt-serif", "pt-serif-cyrillic-400-normal.woff2", "pt-serif-cyrillic.woff2", CYRILLIC),
    ("@fontsource/pt-serif", "pt-serif-latin-400-normal.woff2", "pt-serif-latin.woff2", LATIN),
    ("@fontsource/pt-serif", "pt-serif-cyrillic-700-normal.woff2", "pt-serif-cyrillic-700.woff2", CYRILLIC),
    ("@fontsource/pt-serif", "pt-serif-latin-700-normal.woff2", "pt-serif-latin-700.woff2", LATIN),
    ("@fontsource/pt-serif", "pt-serif-cyrillic-400-italic.woff2", "pt-serif-cyrillic-italic.woff2", CYRILLIC),
    ("@fontsource/pt-serif", "pt-serif-latin-400-italic.woff2", "pt-serif-latin-italic.woff2", LATIN),
    ("@fontsource-variable/jetbrains-mono", "jetbrains-mono-cyrillic-wght-normal.woff2", "jetbrains-mono-cyrillic.woff2", CYRILLIC),
    ("@fontsource-variable/jetbrains-mono", "jetbrains-mono-latin-wght-normal.woff2", "jetbrains-mono-latin.woff2", LATIN),
]


def subset_one(pkg: str, src_name: str, out_name: str, chars: str) -> tuple[int, int, int]:
    from fontTools.ttLib import TTFont
    from fontTools.subset import Subsetter, Options

    src = MODULES / pkg / "files" / src_name
    font = TTFont(src)

    # Оставляем только те знаки, которые в этом файле вообще есть:
    # кириллическая часть не содержит латиницы и наоборот.
    have = set(font.getBestCmap())
    keep = {ord(ch) for ch in chars if ord(ch) in have}

    options = Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]  # кернинг и лигатуры сохраняем
    options.drop_tables += ["DSIG"]
    options.hinting = True
    options.notdef_outline = True
    # Оси переменного шрифта не трогаем: одним файлом обслуживаются все
    # начертания от светлого до жирного.

    subsetter = Subsetter(options=options)
    subsetter.populate(unicodes=keep)
    subsetter.subset(font)

    dest = OUT / out_name
    font.flavor = "woff2"
    font.save(dest)
    font.close()

    return src.stat().st_size, dest.stat().st_size, len(keep)


def main() -> int:
    try:
        import fontTools  # noqa: F401
    except ImportError:
        print("Нужен fonttools: pip install fonttools brotli", file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    total_before = total_after = 0

    for pkg, src_name, out_name, chars in JOBS:
        before, after, count = subset_one(pkg, src_name, out_name, chars)
        total_before += before
        total_after += after
        print(f"{out_name:30} {before // 1024:3} КБ → {after // 1024:3} КБ   ({count} знаков)")

    print(f"\nВсего: {total_before // 1024} КБ → {total_after // 1024} КБ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
