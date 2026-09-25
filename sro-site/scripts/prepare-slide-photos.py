#!/usr/bin/env python3
"""Готовит три кадра слайдера первого экрана (они же шапки страниц видов СРО).

Исходники — вертикальные кадры, присланные заказчиком 25.09.2026, шириной
681–736 px. Первый экран на компьютере показывает из вертикального кадра
горизонтальную полосу во всю ширину окна, поэтому ширина здесь решает всё:
кадр увеличивается вдвое (Lanczos плюс лёгкая резкость) — растянутый
браузером, он мылится заметнее. Деталей это не прибавляет: придут оригиналы
крупнее MIN_WIDTH — положите их на место исходников, увеличение не сработает.

Цвет не трогается: закат, белая бумага и вечерний свет уже в палитре сайта,
а плёнка первого экрана приглушает их сама. Имена файлов прежние
(hero-day, slide-design, slide-survey) — на них ссылается src/content/images.ts.

    python3 scripts/prepare-slide-photos.py      # из sro-site/
"""
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

SRC = Path("assets-src")
OUT = Path("public/img")
# (исходник, имя, яркость). Чертежи — белая бумага: без приглушения мелкий текст
# первого экрана на 820–1024 px ложился на неё с контрастом 4,32:1 при норме 4,5
# (замер scripts/test-hero-contrast.mjs). Остальные кадры и так тёмные.
SLIDES = [
    ("slide-construction-src.jpg", "hero-day", 1.0),
    ("slide-design-src.jpg", "slide-design", 0.8),
    ("slide-survey-src.jpg", "slide-survey", 1.0),
]
MIN_WIDTH = 1000  # уже этого — увеличиваем вдвое
WEBP_QUALITY, AVIF_QUALITY = 74, 50
WEBP_LIMIT_KB, AVIF_LIMIT_KB = 180, 120


def prepare(src: Path, name: str, brightness: float) -> None:
    img = Image.open(src).convert("RGB")
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    if img.width < MIN_WIDTH:
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
        img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    webp, avif = OUT / f"{name}.webp", OUT / f"{name}.avif"
    img.save(webp, "WEBP", quality=WEBP_QUALITY, method=6)
    img.save(avif, "AVIF", quality=AVIF_QUALITY)
    for path, limit in ((webp, WEBP_LIMIT_KB), (avif, AVIF_LIMIT_KB)):
        kb = path.stat().st_size / 1024
        mark = "ok" if kb <= limit else f"ПРЕВЫШЕН бюджет {limit} КБ"
        print(f"{path}: {img.width}×{img.height}, {kb:.0f} КБ — {mark}")


def main() -> None:
    for source, name, brightness in SLIDES:
        prepare(SRC / source, name, brightness)


if __name__ == "__main__":
    main()
