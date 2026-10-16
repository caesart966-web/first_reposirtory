#!/usr/bin/env python3
"""Кадры для шапок статей (16.10.2026).

Снимки прислал заказчик, источник не указан (см. public/img/CREDITS.md,
«Шапки статей 16.10.2026»). Обработка общая для сайта — тёплый монохром
(scripts/monotone.py), ширина как у шапок услуг.

  article-dogovor  — подпись договора за тёмным столом, «Нужна ли СРО,
                     если договор до 10 млн». Исходник — регистрация брака
                     (букет, невеста), поэтому кадр обрезан до рук, ручки,
                     листа и папки: ни лиц, ни букета, ни кольца в углу.
                     Отражён: лист стоял слева, под самой плотной плёнкой
                     шапки, а справа был пустой стол. Букв в кадре нет,
                     отражение не видно.
  article-proverka — человек читает договор с ручкой в руке, лица нет,
                     «Как проверить СРО перед вступлением».

    python3 scripts/prepare-article-photos.py      # из sro-site/
"""
from pathlib import Path

from PIL import Image

from monotone import monotone

SRC = Path("assets-src")
OUT = Path("public/img")
WIDTH = 1600
WEBP_QUALITY, AVIF_QUALITY = 72, 50
WEBP_LIMIT_KB, AVIF_LIMIT_KB = 190, 120

# (исходник, имя, обрезка в пикселях исходника (left, top, right, bottom) или None,
#  отразить по горизонтали, уровни)
PHOTOS = [
    ("article-dogovor-src.jpg", "article-dogovor", (860, 400, 1880, 1333), True, (0.04, 0.95, 0.85)),
    ("article-proverka-src.jpg", "article-proverka", None, False, (0.04, 0.96, 0.85)),
]


def main() -> None:
    for source, name, box, mirror, levels in PHOTOS:
        img = Image.open(SRC / source).convert("RGB")
        if box:
            img = img.crop(box)
        if mirror:
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
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
