#!/usr/bin/env python3
"""
Фон первого экрана из фотографии: kamchatka-photo.jpg (1920x705,
прислана 06.10.2026) -> assets/home/scene-{800,1200,1600,1920}.{avif,webp}
и scene-1200.jpg для браузеров без AVIF и WebP.

    python3 tools/render3d/photo-scene.py      (из stroigeroi-site)

Больше 1920 не делаем: исходник такой ширины, растянутый снимок
на большом экране был бы мыльным.
"""
import pathlib
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent.parent / 'assets' / 'home'

src = Image.open(HERE / 'kamchatka-photo.jpg').convert('RGB')
W, H = src.size
for w in (800, 1200, 1600, 1920):
    h = round(H * w / W)
    im = src if w == W else src.resize((w, h), Image.LANCZOS)
    im.save(OUT / f'scene-{w}.webp', 'WEBP', quality=82, method=6)
    im.save(OUT / f'scene-{w}.avif', 'AVIF', quality=62, speed=4)
    if w == 1200:
        im.save(OUT / 'scene-1200.jpg', 'JPEG', quality=82, optimize=True, progressive=True)
    print(f'scene-{w}: {w}x{h}')
