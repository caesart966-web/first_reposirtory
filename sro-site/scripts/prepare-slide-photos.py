#!/usr/bin/env python3
"""Готовит три кадра видов СРО: шапки страниц видов, а кран (hero-day) — ещё
и первый экран главной (с 26.09.2026 он там один и растворяется в бумаге).

Исходники — кадры, присланные заказчиком 25.09.2026, шириной 820–960 px
(кран и план вертикальные, изыскатели — узкая горизонтальная панорама). Это
и есть оригиналы: крупнее их у заказчика нет. Шапки страниц видов растягивают
кадр во всю ширину окна, поэтому он увеличивается нейросетью Real-ESRGAN (x4plus),
если передан путь к её программе (`--esrgan`), иначе Lanczos с лёгкой
резкостью. Real-ESRGAN обучена на сжатых и уменьшенных снимках: снимает
артефакты JPEG и дорисовывает правдоподобную мелкую фактуру. Деталей,
которых в кадре не было, она не восстанавливает — придумывает похожие; для
фона под плёнкой это допустимо, для документального снимка — нет.

Модель увеличивает вчетверо, затем кадр уменьшается до SCALE исходника:
уменьшение после увеличения даёт чистые края без ореолов.

Затем тёплый монохром (scripts/monotone.py) — общий для всех фотографий
сайта: яркость в градиент «графит → бумага», у каждого кадра свои уровни.
До 26.09.2026 здесь было частичное тонирование в латунь, и кадры всё равно
читались тремя разными сайтами: лиловое небо, холодная бумага, бирюзовое небо.
Кран — «светлым ключом»: небо уходит в бумагу, и на первом экране кадр
растворяется в листе без серой полосы на стыке.

Имена файлов прежние (hero-day, slide-design, slide-survey) — на них ссылается
src/content/images.ts. Меняете кадры или тон — перемерьте контраст:
`node scripts/test-hero-contrast.mjs`.

    python3 scripts/prepare-slide-photos.py                                   # Lanczos
    python3 scripts/prepare-slide-photos.py --esrgan ./realesrgan-ncnn-vulkan # нейросеть

Программа: https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip
(47 МБ, в репозиторий не кладётся; модели лежат рядом с ней в models/). Без
видеокарты работает через программный Vulkan (пакет mesa-vulkan-drivers),
от 8 до 30 минут на кадр; результат кешируется во временной папке по содержимому
исходника.
"""
import argparse
import hashlib
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

from monotone import monotone

SRC = Path("assets-src")
OUT = Path("public/img")
# (исходник, имя, увеличение, яркость, уровни монохрома black/white/gamma).
# Чертежи — белая бумага: без приглушения мелкий текст шапки на 820–1024 px
# ложился на неё с контрастом 4,32:1 при норме 4,5. Кран — светлым ключом:
# белая точка на половине яркости уводит небо в бумагу.
# Панорама изыскателей увеличивается втрое: у неё всего 334 px высоты,
# а шапка страницы на компьютере выше 800 px.
SLIDES = [
    ("slide-construction-src.jpg", "hero-day", 2, 1.0, (0.03, 0.52, 0.80)),
    ("slide-design-src.jpg", "slide-design", 2, 0.8, (0.02, 0.95, 1.0)),
    ("slide-survey-src.jpg", "slide-survey", 3, 1.0, (0.02, 0.85, 0.95)),
]
WEBP_QUALITY, AVIF_QUALITY = 74, 50
WEBP_LIMIT_KB, AVIF_LIMIT_KB = 180, 120
CACHE = Path(tempfile.gettempdir()) / "sro-esrgan-cache"


def upscale(src: Path, img: Image.Image, scale: int, esrgan: Path | None) -> Image.Image:
    size = (img.width * scale, img.height * scale)
    if esrgan is None:
        img = img.resize(size, Image.LANCZOS)
        return img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    cached = CACHE / f"{hashlib.sha1(src.read_bytes()).hexdigest()}-x4.png"
    if not cached.exists():
        CACHE.mkdir(exist_ok=True)
        subprocess.run([str(esrgan), "-i", str(src.resolve()), "-o", str(cached), "-n", "realesrgan-x4plus"],
                       cwd=esrgan.parent, check=True, capture_output=True)
    return Image.open(cached).convert("RGB").resize(size, Image.LANCZOS)


def prepare(src: Path, name: str, scale: int, brightness: float,
            levels: tuple[float, float, float], esrgan: Path | None) -> None:
    img = upscale(src, Image.open(src).convert("RGB"), scale, esrgan)
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    img = monotone(img, *levels)
    webp, avif = OUT / f"{name}.webp", OUT / f"{name}.avif"
    img.save(webp, "WEBP", quality=WEBP_QUALITY, method=6)
    img.save(avif, "AVIF", quality=AVIF_QUALITY)
    for path, limit in ((webp, WEBP_LIMIT_KB), (avif, AVIF_LIMIT_KB)):
        kb = path.stat().st_size / 1024
        mark = "ok" if kb <= limit else f"ПРЕВЫШЕН бюджет {limit} КБ"
        print(f"{path}: {img.width}×{img.height}, {kb:.0f} КБ — {mark}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--esrgan", type=Path, help="программа realesrgan-ncnn-vulkan (иначе Lanczos)")
    args = ap.parse_args()
    for source, name, scale, brightness, levels in SLIDES:
        prepare(SRC / source, name, scale, brightness, levels, args.esrgan)


if __name__ == "__main__":
    main()
