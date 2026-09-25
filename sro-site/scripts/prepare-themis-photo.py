#!/usr/bin/env python3
"""Готовит фотографию Фемиды для тёмного раздела «Как проходит работа».

Исходник — assets-src/themis-photo-src.jpg (1024×1024, прислан заказчиком
25.09.2026). Раздел залит тёплым графитом accent-950 (#1C1815), а фон снимка —
холодный серый: на стыке маски он читался бы серым прямоугольником. Поэтому
самые тёмные тона сводятся к графиту сайта: чем темнее пиксель, тем сильнее
(до яркости THRESHOLD правка сходит на нет), — сама статуя не трогается.

Только Pillow, без numpy: маска строится из яркости через Image.point.

    python3 scripts/prepare-themis-photo.py      # из sro-site/
"""
from pathlib import Path

from PIL import Image

SRC = Path("assets-src/themis-photo-src.jpg")
OUT = Path("public/img")
NAME = "themis-photo"
GRAPHITE = (28, 24, 21)  # accent-950
THRESHOLD = 48  # ярче этого пиксель остаётся как есть
WEBP_QUALITY, AVIF_QUALITY = 80, 55
WEBP_LIMIT_KB, AVIF_LIMIT_KB = 180, 120


def main() -> None:
    img = Image.open(SRC).convert("RGB")
    luma = img.convert("L")
    # 255 — полностью графит (чёрный фон), 0 — без правки (статуя).
    weight = luma.point(lambda v: round(max(0.0, (THRESHOLD - v) / THRESHOLD) * 255))
    graded = Image.composite(Image.new("RGB", img.size, GRAPHITE), img, weight)

    webp, avif = OUT / f"{NAME}.webp", OUT / f"{NAME}.avif"
    graded.save(webp, "WEBP", quality=WEBP_QUALITY, method=6)
    graded.save(avif, "AVIF", quality=AVIF_QUALITY)
    for path, limit in ((webp, WEBP_LIMIT_KB), (avif, AVIF_LIMIT_KB)):
        kb = path.stat().st_size / 1024
        mark = "ok" if kb <= limit else f"ПРЕВЫШЕН бюджет {limit} КБ"
        print(f"{path}: {graded.width}×{graded.height}, {kb:.0f} КБ — {mark}")


if __name__ == "__main__":
    main()
