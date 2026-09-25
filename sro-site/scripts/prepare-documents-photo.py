#!/usr/bin/env python3
"""Готовит фотографию папок для раздела «Документы».

Исходник — assets-src/documents-photo-src.jpg (прислан заказчиком 25.09.2026
под именем «доки.jpg»: кириллица в имени файла ломается на части хостингов
и в архивах). Кадр стоит фоном во всю высоту раздела, а исходник всего
417×626 — превью из поиска по картинкам, не оригинал. Поэтому он увеличивается
вдвое (Lanczos плюс лёгкая резкость): растянутый браузером, он мылится
заметнее. Деталей это не прибавляет — придёт оригинал, положите его на место
исходника и запустите скрипт снова; увеличение сработает, только если
исходник уже MIN_WIDTH.

Цвет не трогается: коричневые, бежевые и серые корешки и так в палитре сайта.

    python3 scripts/prepare-documents-photo.py      # из sro-site/
"""
from pathlib import Path

from PIL import Image, ImageFilter

SRC = Path("assets-src/documents-photo-src.jpg")
OUT = Path("public/img")
NAME = "documents-photo"
MIN_WIDTH = 800  # уже этого — увеличиваем вдвое
MAX_WIDTH = 1200  # шире не нужно: на компьютере кадр занимает 42% экрана
WEBP_QUALITY, AVIF_QUALITY = 80, 55
WEBP_LIMIT_KB, AVIF_LIMIT_KB = 180, 120


def main() -> None:
    img = Image.open(SRC).convert("RGB")
    if img.width < MIN_WIDTH:
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
        img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    elif img.width > MAX_WIDTH:
        img = img.resize((MAX_WIDTH, round(img.height * MAX_WIDTH / img.width)), Image.LANCZOS)

    webp, avif = OUT / f"{NAME}.webp", OUT / f"{NAME}.avif"
    img.save(webp, "WEBP", quality=WEBP_QUALITY, method=6)
    img.save(avif, "AVIF", quality=AVIF_QUALITY)
    for path, limit in ((webp, WEBP_LIMIT_KB), (avif, AVIF_LIMIT_KB)):
        kb = path.stat().st_size / 1024
        mark = "ok" if kb <= limit else f"ПРЕВЫШЕН бюджет {limit} КБ"
        print(f"{path}: {img.width}×{img.height}, {kb:.0f} КБ — {mark}")


if __name__ == "__main__":
    main()
