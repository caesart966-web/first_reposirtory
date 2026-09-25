#!/usr/bin/env python3
"""Готовит три кадра слайдера первого экрана (они же шапки страниц видов СРО).

Исходники — вертикальные кадры, присланные заказчиком 25.09.2026, шириной
681–960 px. Первый экран на компьютере показывает из вертикального кадра
горизонтальную полосу во всю ширину окна, поэтому кадр увеличивается вдвое:
нейросетью EDSR, если передан её файл (`--edsr`), иначе Lanczos с лёгкой
резкостью. EDSR даёт чуть более чистые тонкие линии (тросы кранов, линии
чертежа), но деталей, которых нет в исходнике, не прибавляет ни то, ни другое.
Придут оригиналы крупнее MIN_WIDTH — увеличение не сработает.

Затем тон серии: тени сводятся к графиту сайта, полутона — к латуни, света —
к крему, частичным смешиванием (`tone`). Без него три кадра читались тремя
разными сайтами: оранжевый закат, холодная белая бумага, бирюзовое небо.

Имена файлов прежние (hero-day, slide-design, slide-survey) — на них ссылается
src/content/images.ts. Меняете кадры или тон — перемерьте контраст:
`node scripts/test-hero-contrast.mjs`.

    python3 scripts/prepare-slide-photos.py                         # Lanczos
    python3 scripts/prepare-slide-photos.py --edsr EDSR_x2.pb       # нейросеть

Файл модели: https://raw.githubusercontent.com/Saafke/EDSR_Tensorflow/master/models/EDSR_x2.pb
(38 МБ, в репозиторий не кладётся), нужен пакет opencv-contrib-python-headless.
На процессоре EDSR считает 3–6 минут на кадр, поэтому результат кешируется
во временной папке по содержимому исходника.
"""
import argparse
import hashlib
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

SRC = Path("assets-src")
OUT = Path("public/img")
# (исходник, имя, яркость, тон). Чертежи — белая бумага: без приглушения мелкий
# текст первого экрана на 820–1024 px ложился на неё с контрастом 4,32:1 при
# норме 4,5. Тон сильнее там, где кадр дальше от палитры: у крана над вечерним
# городом верх неба лиловый, у чертежей — холодная белая бумага.
SLIDES = [
    ("slide-construction-src.jpg", "hero-day", 1.0, 0.25),
    ("slide-design-src.jpg", "slide-design", 0.8, 0.35),
    ("slide-survey-src.jpg", "slide-survey", 1.0, 0.30),
]
SHADOW, MID, HIGH = (28, 24, 21), (157, 116, 67), (245, 241, 234)  # accent-950, accent-500, neutral-100
MIN_WIDTH = 1000  # уже этого — увеличиваем вдвое
WEBP_QUALITY, AVIF_QUALITY = 74, 50
WEBP_LIMIT_KB, AVIF_LIMIT_KB = 180, 120
CACHE = Path(tempfile.gettempdir()) / "sro-edsr-cache"


def upscale(src: Path, img: Image.Image, edsr: Path | None) -> Image.Image:
    if edsr is None:
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
        return img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    cached = CACHE / f"{hashlib.sha1(src.read_bytes()).hexdigest()}.png"
    if not cached.exists():
        import cv2
        sr = cv2.dnn_superres.DnnSuperResImpl_create()
        sr.readModel(str(edsr))
        sr.setModel("edsr", 2)
        CACHE.mkdir(exist_ok=True)
        cv2.imwrite(str(cached), sr.upsample(cv2.imread(str(src))))
    return Image.open(cached).convert("RGB")


def tone(img: Image.Image, strength: float) -> Image.Image:
    """Три точки палитры по яркости: тень → латунь → крем, смешивание strength."""
    a = np.asarray(img, float)
    lum = ((0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]) / 255.0)[..., None]
    shadow, mid, high = (np.array(c, float) for c in (SHADOW, MID, HIGH))
    toned = np.where(lum < 0.5,
                     shadow + (mid - shadow) * np.clip(lum / 0.5, 0, 1),
                     mid + (high - mid) * np.clip((lum - 0.5) / 0.5, 0, 1))
    return Image.fromarray(np.clip(a * (1 - strength) + toned * strength, 0, 255).astype("uint8"))


def prepare(src: Path, name: str, brightness: float, strength: float, edsr: Path | None) -> None:
    img = Image.open(src).convert("RGB")
    if img.width < MIN_WIDTH:
        img = upscale(src, img, edsr)
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    if strength:
        img = tone(img, strength)
    webp, avif = OUT / f"{name}.webp", OUT / f"{name}.avif"
    img.save(webp, "WEBP", quality=WEBP_QUALITY, method=6)
    img.save(avif, "AVIF", quality=AVIF_QUALITY)
    for path, limit in ((webp, WEBP_LIMIT_KB), (avif, AVIF_LIMIT_KB)):
        kb = path.stat().st_size / 1024
        mark = "ok" if kb <= limit else f"ПРЕВЫШЕН бюджет {limit} КБ"
        print(f"{path}: {img.width}×{img.height}, {kb:.0f} КБ — {mark}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--edsr", type=Path, help="файл модели EDSR_x2.pb (иначе Lanczos)")
    args = ap.parse_args()
    for source, name, brightness, strength in SLIDES:
        prepare(SRC / source, name, brightness, strength, args.edsr)


if __name__ == "__main__":
    main()
