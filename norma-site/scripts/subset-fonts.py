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
# Шрифтов два, и роли у них разные.
#
# Literata — заголовки и текст статей. Это антиква, нарисованная для чтения
# с экрана, с полновесной кириллицей. Выбрана не за красоту вообще, а по делу:
# сайт говорит о законе, нормах и документах, и антиква говорит об этом же —
# рубленый шрифт в такой роли звучит как интерфейс банковского приложения.
# У неё же берётся курсив: у Golos Text его не существует, а в статьях
# курсив нужен.
#
# Golos Text — всё остальное: кнопки, подписи, таблицы, цифры, формы.
# Русский шрифт, нарисованный от кириллицы; спокойный рисунок, который
# не спорит с антиквой в заголовках и хорошо держится в мелком кегле.
JOBS = [
    ("@fontsource-variable/literata", "literata-cyrillic-wght-normal.woff2", "literata-cyrillic.woff2", CYRILLIC),
    ("@fontsource-variable/literata", "literata-latin-wght-normal.woff2", "literata-latin.woff2", LATIN),
    ("@fontsource-variable/literata", "literata-cyrillic-wght-italic.woff2", "literata-cyrillic-italic.woff2", CYRILLIC),
    ("@fontsource-variable/literata", "literata-latin-wght-italic.woff2", "literata-latin-italic.woff2", LATIN),
    ("@fontsource-variable/golos-text", "golos-text-cyrillic-wght-normal.woff2", "golos-cyrillic.woff2", CYRILLIC),
    ("@fontsource-variable/golos-text", "golos-text-latin-wght-normal.woff2", "golos-latin.woff2", LATIN),
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
