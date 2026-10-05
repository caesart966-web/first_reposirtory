#!/usr/bin/env python3
"""
Собирает картинки главной из трёхмерных съёмок (tools/render3d/*.py).

    python3 tools/render3d/make-home-images.py <папка с рендерами>

В папке ждёт:
    plateA.png, plateA-mask.png   вулканы, сопки, город и бухта (hero_plate.py)
    plateB.png                    стройка с краном, фон прозрачный (hero_site.py)
    prod-<имя>.png                предметы на прозрачном (products.py)

Пишет в assets/home/ (рядом со страницами макета):
    scene-{800,1200,1600,2400}.{avif,webp}, scene-1200.jpg   сцена первого экрана
    hero-{470,940}.{avif,webp}                                герой с баннера
    cat-<имя>.{avif,webp}                                     плитки разделов
    promo-calc.*, promo-paint.*                               карточки

Герой вырезан из баннера заказчика (assets/banner.jpg) заранее — исходник
вырезки лежит в variants/img/mascot.webp.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets' / 'home'
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')

CATS = ['bricks', 'drill', 'hammer', 'socket', 'faucet', 'bolts', 'radiator', 'wheelbarrow', 'hardhat']
PROMO = {'calculator': 'promo-calc', 'paint': 'promo-paint'}


def save(im, name, sizes=None, jpg=None, q_webp=82, q_avif=58):
    """Пишет AVIF и WebP; sizes — ширины, иначе один размер как есть."""
    OUT.mkdir(parents=True, exist_ok=True)
    targets = [(None, im)] if not sizes else [
        (w, im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)) for w in sizes]
    for w, frame in targets:
        stem = f'{name}-{w}' if w else name
        frame.save(OUT / f'{stem}.webp', 'WEBP', quality=q_webp, method=6)
        frame.save(OUT / f'{stem}.avif', 'AVIF', quality=q_avif, speed=4)
        if jpg and w == jpg:
            frame.convert('RGB').save(OUT / f'{stem}.jpg', 'JPEG', quality=84, optimize=True, progressive=True)


def fade_edges(im, margin=0.07):
    """Тень от студийного света доходит до края кадра; на плитке это была бы
    прямая граница. Альфа плавно гаснет к краям."""
    a = np.asarray(im.split()[-1]).astype(np.float32)
    h, w = a.shape
    m = int(min(h, w) * margin)
    ramp = np.clip(np.minimum.reduce([
        np.arange(w)[None, :].repeat(h, 0), (w - 1 - np.arange(w))[None, :].repeat(h, 0),
        np.arange(h)[:, None].repeat(w, 1), (h - 1 - np.arange(h))[:, None].repeat(w, 1)]) / m, 0, 1)
    out = im.copy()
    out.putalpha(Image.fromarray((a * ramp).astype(np.uint8)))
    return out


def fbm(shape, scale, octaves=5, seed=3):
    rng = np.random.default_rng(seed)
    h, w = shape
    total = np.zeros(shape, np.float32)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        s = max(2, int(scale * 2 ** o))
        small = rng.random((s, int(s * w / h) + 1)).astype(np.float32)
        layer = np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255
        total += layer * amp
        norm += amp
        amp *= 0.5
    return total / norm


def clouds(size, mask_sky):
    """Несколько мягких кучевых облаков в небе. Только там, где за ними
    небо (маска из рендера), и не над вершиной вулкана."""
    w, h = size
    n = fbm((h, w), 3, 6, seed=11)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    blobs = np.zeros((h, w), np.float32)
    for cx, cy, rx, ry in [(0.20, 0.17, 0.12, 0.05), (0.33, 0.30, 0.08, 0.035),
                           (0.70, 0.12, 0.10, 0.04), (0.88, 0.30, 0.09, 0.035), (0.58, 0.40, 0.07, 0.025)]:
        d = ((xx / w - cx) / rx) ** 2 + ((yy / h - cy) / ry) ** 2
        blobs = np.maximum(blobs, np.clip(1.2 - d, 0, 1))
    dens = np.clip((n - 0.42) * 3.2, 0, 1) * blobs
    dens = np.asarray(Image.fromarray((dens * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
    # подсветка слева сверху, тень снизу справа
    shade = np.clip(0.88 + (np.roll(dens, (6, 6), (0, 1)) - dens) * -1.2, 0.62, 1.0)
    rgb = np.stack([shade * 255, shade * 255, np.clip(shade * 255 + 6, 0, 255)], -1)
    alpha = dens * 0.92 * mask_sky
    return rgb, alpha


def scene():
    a = Image.open(SRC / 'plateA.png').convert('RGB')
    w, h = a.size
    mask = np.asarray(Image.open(SRC / 'plateA-mask.png').split()[-1], np.float32) / 255
    sky = 1 - mask
    rgb, alpha = clouds((w, h), sky)
    base = np.asarray(a, np.float32)
    base = base * (1 - alpha[..., None]) + rgb * alpha[..., None]
    img = Image.fromarray(base.clip(0, 255).astype(np.uint8)).convert('RGBA')
    # стройка справа: по высоте сцены, прижата к правому краю
    b = Image.open(SRC / 'plateB.png').convert('RGBA')
    bh = h
    bw = round(b.width * bh / b.height)
    b = b.resize((bw, bh), Image.LANCZOS)
    ba = np.asarray(b.split()[-1], np.float32)
    # земля стройки (ниже забора) растворяется влево — дальше вода и город
    yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
    ground = np.clip((yy / bh - 0.70) / 0.05, 0, 1)
    fade = np.clip(xx / (bw * 0.42), 0, 1)
    ba = ba * (1 - ground * (1 - fade))
    b.putalpha(Image.fromarray(ba.astype(np.uint8)))
    img.alpha_composite(b, (w - bw, 0))
    img = img.convert('RGB')
    img.save(SRC / 'scene.png')
    save(img, 'scene', sizes=[800, 1200, 1600, 2400], jpg=1200, q_webp=80, q_avif=55)


def hero():
    m = Image.open(ROOT / 'variants' / 'img' / 'mascot.webp').convert('RGBA')
    save(m, 'hero', sizes=[470, 940], q_webp=84, q_avif=62)


def products():
    for name in CATS:
        im = fade_edges(Image.open(SRC / f'prod-{name}.png').convert('RGBA'))
        im = im.resize((320, 320), Image.LANCZOS)
        save(im, f'cat-{name}', q_webp=84, q_avif=60)
    for src, dst in PROMO.items():
        im = fade_edges(Image.open(SRC / f'prod-{src}.png').convert('RGBA'), 0.05)
        im = im.resize((560, 560), Image.LANCZOS)
        save(im, dst, q_webp=84, q_avif=60)


if __name__ == '__main__':
    scene()
    hero()
    products()
    total = sum(f.stat().st_size for f in OUT.iterdir())
    print(f'assets/home: {len(list(OUT.iterdir()))} файлов, {total / 1024:.0f} КБ')
