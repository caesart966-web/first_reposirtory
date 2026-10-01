#!/usr/bin/env python3
"""Готовит фотографию папок для раздела «Документы».

Исходник — assets-src/documents-photo-src.jpg (прислан заказчиком 25.09.2026
под именем «доки.jpg»: кириллица в имени файла ломается на части хостингов
и в архивах). Кадр стоит фоном во всю высоту раздела, а исходник всего
417×626 — превью из поиска по картинкам, не оригинал.

С 01.10.2026 (заказчик: «улучшить качество картинки») превью увеличивается
нейросетью Real-ESRGAN (x4plus) вчетверо, до 1668×2504, — тем же способом,
что кран на первом экране (scripts/prepare-slide-photos.py). Она обучена
на сжатых и уменьшенных снимках: снимает «кашу» от сжатия и восстанавливает
края — кольца папок, обрезы листов. Фон в расфокусе так и остаётся
в расфокусе: глубина резкости у снимка своя. Без программы (`--esrgan`
не передан) — прежнее увеличение вдвое Lanczos с лёгкой резкостью.
Придёт оригинал — положите его на место исходника и запустите скрипт снова:
увеличение сработает, только если исходник уже MIN_WIDTH.

Полный размер 1668×2504 весит 95 КБ WebP / 59 КБ AVIF — монохром и
расфокус сжимаются хорошо, — поэтому кадр не уменьшается до 1200: на
компьютере он стоит в полную высоту раздела (около 1500 px), и экранам
с плотностью 2× нужен запас.

С 26.09.2026 кадр в тёплом монохроме, как все фотографии сайта
(scripts/monotone.py): коричневые корешки уходят в графит и песок.

    python3 scripts/prepare-documents-photo.py                                # из sro-site/
    python3 scripts/prepare-documents-photo.py --esrgan ./realesrgan-ncnn-vulkan
"""
import argparse
import hashlib
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter

from monotone import monotone

SRC = Path("assets-src/documents-photo-src.jpg")
OUT = Path("public/img")
NAME = "documents-photo"
MIN_WIDTH = 800  # уже этого — увеличиваем
MAX_WIDTH = 1700  # шире не нужно: полная высота раздела с запасом под 2×
LEVELS = (0.02, 0.90, 0.95)  # монохром: black, white, gamma
WEBP_QUALITY, AVIF_QUALITY = 80, 55
WEBP_LIMIT_KB, AVIF_LIMIT_KB = 180, 120
# Тот же кеш, что у prepare-slide-photos.py: нейросеть на процессоре
# считает кадр несколько минут, повторный запуск берёт готовое.
CACHE = Path(tempfile.gettempdir()) / "sro-esrgan-cache"


def upscale(img: Image.Image, esrgan: Path | None) -> Image.Image:
    if esrgan is None:
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
        return img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    cached = CACHE / f"{hashlib.sha1(SRC.read_bytes()).hexdigest()}-x4.png"
    if not cached.exists():
        CACHE.mkdir(exist_ok=True)
        subprocess.run([str(esrgan), "-i", str(SRC.resolve()), "-o", str(cached), "-n", "realesrgan-x4plus"],
                       cwd=esrgan.parent, check=True, capture_output=True)
    return Image.open(cached).convert("RGB")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--esrgan", type=Path, help="программа realesrgan-ncnn-vulkan (иначе Lanczos)")
    args = ap.parse_args()

    img = Image.open(SRC).convert("RGB")
    if img.width < MIN_WIDTH:
        img = upscale(img, args.esrgan)
    if img.width > MAX_WIDTH:
        img = img.resize((MAX_WIDTH, round(img.height * MAX_WIDTH / img.width)), Image.LANCZOS)
    img = monotone(img, *LEVELS)

    webp, avif = OUT / f"{NAME}.webp", OUT / f"{NAME}.avif"
    img.save(webp, "WEBP", quality=WEBP_QUALITY, method=6)
    img.save(avif, "AVIF", quality=AVIF_QUALITY)
    for path, limit in ((webp, WEBP_LIMIT_KB), (avif, AVIF_LIMIT_KB)):
        kb = path.stat().st_size / 1024
        mark = "ok" if kb <= limit else f"ПРЕВЫШЕН бюджет {limit} КБ"
        print(f"{path}: {img.width}×{img.height}, {kb:.0f} КБ — {mark}")


if __name__ == "__main__":
    main()
