#!/usr/bin/env python3
"""Фотографии для тёмных шапок разделов — из снимков заказчика.

Запуск (из norma-site):
    python3 scripts/prepare-head-photos.py
    python3 scripts/prepare-head-photos.py --esrgan ./realesrgan-ncnn-vulkan

Исходники — assets-src/heads/, как их прислал заказчик 02.10.2026:
пять снимков Фемиды, книг, судейского молотка и зала суда. Результат —
public/img/<имя>.webp. Какой странице какой кадр — проп src у HeadPhoto
в самой странице (и photo у ServicePage).

Что делается и почему.

1. Обрезка — до всего остального. Кадр в шапке стоит фоном шириной
   во весь экран, а виден в правой половине (левую, под текстом, гасит
   маска из global.css). Поэтому у вытянутых по вертикали снимков
   берётся полоса с главным, а не весь кадр.

2. Зал суда — американский: флаг США над судейским местом и надпись
   «IN GOD WE TRUST» на портале. На сайте о российском законе они
   были бы чужими, и прятать их положением кадра нельзя — на какой-то
   ширине они бы выглянули. Поэтому из снимка берётся только нижняя
   полоса со скамьями и барьером, ниже флага и надписи.

3. Стол с книгой «THE LAW» — предметы слева, а слева в шапке текст,
   и маска их гасит. Полоса берётся ниже надписи (молоток, подставка,
   весы, без букв) и отражается: предметы уходят вправо, где их видно.
   Отражать можно только кадр без надписей — поэтому и обрезка ниже книги.

4. Снимки маленькие (600–740 px по ширине), а шапка на компьютере —
   во весь экран. С программой Real-ESRGAN (модель x4plus, вчетверо)
   края и фактура восстанавливаются; без неё — Lanczos вдвое с лёгкой
   резкостью. Результат всё равно приглушается фильтром шапки
   (global.css, .head-photo), так что мыло по краям не так заметно,
   но разница с увеличением нейросетью видна и сквозь фильтр.
   Без видеокарты программа идёт через программный Vulkan (lavapipe:
   пакет mesa-vulkan-drivers, VK_ICD_FILENAMES=.../lvp_icd.json) —
   минуты на кадр, поэтому результат кешируется по содержимому кадра.

Только Pillow.
"""
import argparse
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

SRC = Path('assets-src/heads')
OUT = Path('public/img')
CACHE = Path(tempfile.gettempdir()) / 'norma-esrgan-cache'
MAX_WIDTH = 1600
QUALITY = 78

# crop — (left, top, right, bottom) в пикселях исходника; None — весь кадр.
SPEC = {
    # Фемида справа на фоне книг в расфокусе — кадр уже горизонтальный.
    'themis-books': {'crop': None},
    # Тёмная библиотека: полоса от весов до стола с бумагами.
    'themis-library': {'crop': (0, 280, 736, 880)},
    # Стол с Фемидой и молотком: голова, плечи и весы. Шапка «Обо мне»
    # широкая и низкая (на 1440 px — 3,7 к 1), и от вертикального кадра
    # в ней видна полоса в четверть высоты: целиком, от весов до книг,
    # фигура выходила обрубком торса. Ноутбук справа отрезан — иначе он,
    # тёмный прямоугольник, встал бы на виду, а сама Фемида ушла бы
    # в середину шапки, под маску.
    'themis-desk': {'crop': (0, 150, 465, 360)},
    # Стол с книгой «THE LAW»: полоса ниже надписи, отражённая.
    'law-table': {'crop': (0, 140, 626, 375), 'flip': True},
    # Зал суда: скамьи и барьер — ниже флага США и надписи на портале.
    'courtroom': {'crop': (0, 250, 616, 411)},
}


def source(name: str) -> Path:
    for ext in ('jpg', 'jpeg', 'png', 'webp'):
        p = SRC / f'{name}.{ext}'
        if p.exists():
            return p
    raise SystemExit(f'нет исходника {name} в {SRC}')


def upscale(img: Image.Image, esrgan: Path | None) -> Image.Image:
    if esrgan is None:
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
        return img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    CACHE.mkdir(parents=True, exist_ok=True)
    raw = img.tobytes()
    key = hashlib.sha1(raw + str(img.size).encode()).hexdigest()
    cached = CACHE / f'{key}-x4.png'
    if not cached.exists():
        tmp_in = CACHE / f'{key}-in.png'
        img.save(tmp_in)
        env = dict(os.environ)
        env.setdefault('VK_ICD_FILENAMES', '/usr/share/vulkan/icd.d/lvp_icd.json')
        subprocess.run(
            [str(esrgan.resolve()), '-i', str(tmp_in), '-o', str(cached), '-n', 'realesrgan-x4plus', '-t', '128'],
            cwd=esrgan.resolve().parent, check=True, capture_output=True, env=env,
        )
    return Image.open(cached).convert('RGB')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--esrgan', type=Path, help='программа realesrgan-ncnn-vulkan (иначе Lanczos)')
    ap.add_argument('only', nargs='*', help='только эти кадры')
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    for name, spec in SPEC.items():
        if args.only and name not in args.only:
            continue
        img = Image.open(source(name)).convert('RGB')
        if spec.get('crop'):
            img = img.crop(spec['crop'])
        if spec.get('flip'):
            img = ImageOps.mirror(img)
        img = upscale(img, args.esrgan)
        if img.width > MAX_WIDTH:
            img = img.resize((MAX_WIDTH, round(img.height * MAX_WIDTH / img.width)), Image.LANCZOS)
        path = OUT / f'{name}.webp'
        img.save(path, 'WEBP', quality=QUALITY, method=6)
        print(f'  {name:16s} {img.width}×{img.height}  {path.stat().st_size / 1024:5.1f} КБ')
    print(f'✓ готово → {OUT}/')


if __name__ == '__main__':
    main()
