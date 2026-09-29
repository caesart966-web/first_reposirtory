#!/usr/bin/env python3
"""Кадры для шапок страниц услуг (с 29.09.2026).

До этого кадр был только у «Подготовки документов» (папки), остальные шесть
шапок стояли пустым графитом. Заказчик: «там чёрный фон — надо фотографии».
Кадры взяты из снимков, которые заказчик присылал раньше для других мест
сайта и которые лежали в assets-src/ без дела; источник и правовой статус
у них те же, что у остальных фотографий сайта (см. public/img/CREDITS.md,
раздел «Шапки услуг 29.09.2026»). Каждый кадр выбран под смысл страницы:

  vstuplenie — план этажа, каска и ключи на бетоне («под ключ»);
  podbor     — корешки кодексов и чертёж на столе, за окном стройка;
  nrs        — рабочее совещание за стеклянной перегородкой;
  nok        — архитектурный разрез здания, чертёж;
  uroven     — каркас строящегося корпуса и башенные краны;
  proverki   — совещание за столом с документами.

Кадр лежит справа, под плёнкой, которая слева почти сплошная (там текст),
поэтому предмет должен стоять в правой половине — crop выбирает эту часть.
Обработка общая для сайта: тёплый монохром (scripts/monotone.py).

    python3 scripts/prepare-service-photos.py      # из sro-site/
"""
from pathlib import Path

from PIL import Image

from monotone import monotone

SRC = Path("assets-src")
OUT = Path("public/img")
WIDTH = 1600  # шапка во всю ширину, но под плёнкой: шире не нужно
WEBP_QUALITY, AVIF_QUALITY = 72, 50
WEBP_LIMIT_KB, AVIF_LIMIT_KB = 190, 120

# (исходник, имя, обрезка долями кадра (left, top, right, bottom), уровни монохрома)
PHOTOS = [
    ("desk-src.jpg", "svc-vstuplenie", (0.0, 0.0, 1.0, 1.0), (0.04, 0.96, 0.85)),
    ("quiz-3-src.png", "svc-podbor", (0.0, 0.0, 1.0, 1.0), (0.03, 0.95, 0.85)),
    ("quiz-1-src.jpg", "svc-nrs", (0.0, 0.0, 1.0, 1.0), (0.03, 0.95, 0.8)),
    ("blueprint-crop-spare.jpg", "svc-nok", (0.0, 0.0, 1.0, 1.0), (0.30, 0.85, 0.9)),
    ("hero-day-src.png", "svc-uroven", (0.0, 0.0, 1.0, 1.0), (0.05, 0.95, 0.85)),
    ("quiz-2-src.jpg", "svc-proverki", (0.0, 0.0, 1.0, 1.0), (0.03, 0.95, 0.85)),
]


def main() -> None:
    for source, name, (l, t, r, b), levels in PHOTOS:
        img = Image.open(SRC / source).convert("RGB")
        w, h = img.size
        img = img.crop((round(l * w), round(t * h), round(r * w), round(b * h)))
        if img.width > WIDTH:
            img = img.resize((WIDTH, round(img.height * WIDTH / img.width)), Image.LANCZOS)
        img = monotone(img, *levels)
        webp, avif = OUT / f"{name}.webp", OUT / f"{name}.avif"
        img.save(webp, "WEBP", quality=WEBP_QUALITY, method=6)
        img.save(avif, "AVIF", quality=AVIF_QUALITY)
        for path, limit in ((webp, WEBP_LIMIT_KB), (avif, AVIF_LIMIT_KB)):
            kb = path.stat().st_size / 1024
            mark = "ok" if kb <= limit else f"ПРЕВЫШЕН бюджет {limit} КБ"
            print(f"{path}: {img.width}×{img.height}, {kb:.0f} КБ — {mark}")


if __name__ == "__main__":
    main()
