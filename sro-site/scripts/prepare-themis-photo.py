#!/usr/bin/env python3
"""Готовит фотографию Фемиды для тёмного раздела «О нас».

Исходник — assets-src/themis-photo-src.jpg (1024×1024, прислан заказчиком
25.09.2026). До 26.09.2026 кадр стоял в «Как проходит работа», теперь —
фоном раздела «О нас». Раздел залит тёплым графитом accent-950 (#1C1815),
а фон снимка — холодный серый: на стыке маски он читался бы серым
прямоугольником. Тёплый монохром сайта (scripts/monotone.py) это и решает:
его тёмный конец — тот же графит, и чёрная точка LEVELS уводит фон в него
целиком, а статуя переходит в ту же гамму, что остальные фотографии.

Только Pillow, без numpy.

    python3 scripts/prepare-themis-photo.py      # из sro-site/
"""
from pathlib import Path

from PIL import Image

from monotone import monotone

SRC = Path("assets-src/themis-photo-src.jpg")
OUT = Path("public/img")
NAME = "themis-photo"
LEVELS = (0.03, 0.92, 0.95)  # монохром: black, white, gamma
WEBP_QUALITY, AVIF_QUALITY = 80, 55
WEBP_LIMIT_KB, AVIF_LIMIT_KB = 180, 120


def main() -> None:
    graded = monotone(Image.open(SRC).convert("RGB"), *LEVELS)

    webp, avif = OUT / f"{NAME}.webp", OUT / f"{NAME}.avif"
    graded.save(webp, "WEBP", quality=WEBP_QUALITY, method=6)
    graded.save(avif, "AVIF", quality=AVIF_QUALITY)
    for path, limit in ((webp, WEBP_LIMIT_KB), (avif, AVIF_LIMIT_KB)):
        kb = path.stat().st_size / 1024
        mark = "ok" if kb <= limit else f"ПРЕВЫШЕН бюджет {limit} КБ"
        print(f"{path}: {graded.width}×{graded.height}, {kb:.0f} КБ — {mark}")


if __name__ == "__main__":
    main()
