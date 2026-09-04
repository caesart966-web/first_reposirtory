#!/usr/bin/env python3
"""Уменьшенные копии фотографий объектов.

Зачем: телефон показывает карточку шириной примерно 350 точек, а в папке
лежат снимки по 1200-1600 точек. То же с письмами: в карточке видна
превьюшка шириной 130 точек, а файл — на 1400. Без уменьшенных копий страница «Объекты»
весит полтора мегабайта, и на стройке по мобильному интернету это заметно.

Что делает: рядом с каждым файлом кладёт копии шириной 480 и 960 точек
(<имя>-480.webp и <имя>-960.webp). Генератор сайта подхватывает их сам:
браузер выбирает подходящую по размеру экрана, оригинал остаётся для
просмотра фотографии в полный экран.

Запуск (нужен Pillow: pip install pillow):
    python3 tools/make-thumbs.py

Файл, который уже сделан и новее оригинала, пропускается. Уменьшенные копии
лежат в репозитории, поэтому при обычной сборке сайта ничего запускать
не нужно — команда нужна только после добавления новых фотографий.
"""
import os
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Нужна библиотека Pillow. Установите: pip install pillow")

ROOT = Path(__file__).resolve().parent.parent
DIRS = [ROOT / "assets" / "img" / "objects", ROOT / "assets" / "docs"]
WIDTHS = (480, 960)
SRC_EXT = {".webp", ".jpg", ".jpeg", ".png"}
# Файлы, которые сами являются уменьшенной копией: <имя>-480.webp
DERIVED = re.compile(r"-(?:%s)\.webp$" % "|".join(str(w) for w in WIDTHS))


def main() -> None:
    made = skipped = 0
    saved = 0
    for d in DIRS:
        if not d.exists():
            continue
        for src in sorted(d.iterdir()):
            if src.suffix.lower() not in SRC_EXT or DERIVED.search(src.name):
                continue
            with Image.open(src) as im:
                im = im.convert("RGB")
                for w in WIDTHS:
                    if im.width <= w:
                        continue          # копия шире оригинала не нужна
                    dst = src.with_name(f"{src.stem}-{w}.webp")
                    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
                        skipped += 1
                        continue
                    h = round(im.height * w / im.width)
                    im.resize((w, h), Image.LANCZOS).save(dst, quality=82, method=6)
                    made += 1
                    saved += src.stat().st_size - dst.stat().st_size
                    print(f"  {dst.name}  {dst.stat().st_size // 1024} КБ")
    print(f"Сделано копий: {made}, пропущено готовых: {skipped}")


if __name__ == "__main__":
    main()
