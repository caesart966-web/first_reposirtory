#!/usr/bin/env python3
"""Готовит фоновую гравюру Фемиды из исходного скана (ТЗ, T23, путь B).

В ТЗ путь записан командой ImageMagick; здесь тот же смысл на Pillow, чтобы
обработку можно было повторить без установки magick:

    magick themis-source.jpg -colorspace Gray -normalize -level 30%,85% \
      -resize x1600 -quality 82 public/img/themis.webp

Что делает и зачем:
  1. grayscale     — снимает желтизну старой бумаги (она только в цвете);
  2. normalize     — растягивает гистограмму по перцентилям 0.15 / 99.85;
  3. level 30,85   — бумага уходит в чистый белый, штрих становится контрастнее;
                     белый важен: на сайте картинка идёт через mix-blend-multiply,
                     где белое становится прозрачным само;
  4. crop          — отрезаем поля, рамку оттиска и цоколь с подписью «THEMIS.»:
                     широкие горизонтали рамки на прозрачности 5% читаются как
                     случайные линейки поверх текста, а латинская подпись — как
                     мусор в русском макете;
  5. resize + webp — вертикальный формат под водяной знак во всю высоту экрана.

Запуск: python3 scripts/prepare-themis.py  (из sro-site/)
"""

from pathlib import Path

from PIL import Image

SRC = Path("public/img/themis-source.jpg")
DST = Path("public/img/themis.webp")

# Рамка оттиска начинается на y=780, фигура стоит на цоколе выше — режем по ней.
CROP = (232, 44, 660, 774)  # left, top, right, bottom
TARGET_HEIGHT = 1600
QUALITY = 80
BLACK_POINT, WHITE_POINT = 0.30, 0.85  # -level 30%,85%


def normalize(img: Image.Image) -> Image.Image:
    """Аналог -normalize: тянем гистограмму, отбрасывая по 0.15% с краёв."""
    hist = img.histogram()
    total = sum(hist)
    cut = total * 0.0015
    acc, low = 0, 0
    for value, count in enumerate(hist):
        acc += count
        if acc > cut:
            low = value
            break
    acc, high = 0, 255
    for value in range(255, -1, -1):
        acc += hist[value]
        if acc > cut:
            high = value
            break
    if high <= low:
        return img
    scale = 255.0 / (high - low)
    return img.point(lambda v: min(255, max(0, int((v - low) * scale))))


def level(img: Image.Image, black: float, white: float) -> Image.Image:
    lo, hi = black * 255.0, white * 255.0
    scale = 255.0 / (hi - lo)
    return img.point(lambda v: min(255, max(0, int((v - lo) * scale))))


def main() -> None:
    img = Image.open(SRC).convert("L")
    img = level(normalize(img), BLACK_POINT, WHITE_POINT)
    img = img.crop(CROP)
    width = round(img.width * TARGET_HEIGHT / img.height)
    img = img.resize((width, TARGET_HEIGHT), Image.LANCZOS)
    img.convert("RGB").save(DST, "WEBP", quality=QUALITY, method=6)
    size_kb = DST.stat().st_size / 1024
    print(f"{DST}: {img.width}x{img.height}, {size_kb:.0f} КБ")


if __name__ == "__main__":
    main()
