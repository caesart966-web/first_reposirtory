#!/usr/bin/env python3
"""Логотипы СРО-партнёров для ленты на главной.

Запуск (из norma-site):  python3 scripts/prepare-partner-logos.py
Нужны Pillow и numpy.

Исходники — как их прислал заказчик (30.09.2026), в assets-src/partners/
под именем партнёра: <slug>.png или <slug>.jpg. Результат:
  public/img/partners/<slug>.webp  — сам логотип;
  src/config/partner-logos.json    — размеры файлов, из них лента считает,
                                     какой высоты ставить каждый знак.
Какой партнёр с каким файлом — поле logo в src/config/partners.ts.

Что делается и почему.

1. Фон картинки убирается, цвета знака — нет. Заказчик выбрал «в цвете,
   как прислали», но фон — не часть знака: белый, кремовый и серо-бежевый
   прямоугольники разного оттенка в одной строке читались бы девятью
   наклейками. Прозрачным становится только фон, связанный с краем
   картинки: белое внутри знака (заливка соболей на гербе МСК, овал СССС)
   остаётся белым. Край знака «отмывается» от цвета фона — иначе вокруг
   него остался бы ореол, кремовый у одного и тёмно-синий у другого.

2. У «Строительство. Инженерные системы» фон оставлен: знак белый,
   без синего поля его не видно. Поля обрезаются, синий остаётся плашкой
   (в манифесте tile: true — лента скругляет ей углы).

3. У герба МСК первая строка пикселей — серая линия от снимка экрана,
   она срезается до всего остального.

4. Высота файла — не больше 128 px (вдвое больше самой высокой строки
   ленты, 64 px: чётко на экранах с двойной плотностью). Меньше исходника
   файл не растягивается: подробностей от этого не прибавится.
"""

import json
from pathlib import Path

import numpy as np
from PIL import Image

SRC = Path('assets-src/partners')
OUT = Path('public/img/partners')
MANIFEST = Path('src/config/partner-logos.json')
MAX_H = 128

# crop_top — сколько строк пикселей срезать сверху до обработки.
SPEC = {
    'sfera-a': {},
    'sfera-proektirovshchikov': {},
    'sfera-izyskateley': {},
    'ors': {},
    'ssss': {},
    'sis': {'keep_bg': True},
    'aso-msk': {'crop_top': 1},
    'rost': {},
    'itp': {},
}

# Порог «это ещё фон»: расстояние в RGB от цвета фона. Ниже T0 — фон
# целиком, выше T1 — знак целиком, между — край, частично прозрачный.
T0, T1 = 10.0, 60.0


def source(slug):
    for ext in ('png', 'jpg', 'jpeg', 'webp'):
        p = SRC / f'{slug}.{ext}'
        if p.exists():
            return p
    raise SystemExit(f'нет исходника для {slug} в {SRC}')


def border(a):
    return np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])


def connected_background(near):
    """Фон, связанный с краем картинки: заливка от рамки по пикселям,
    близким к цвету фона. Замкнутые области того же цвета внутри знака
    сюда не попадают — и остаются непрозрачными."""
    region = np.zeros_like(near)
    region[0, :] = near[0, :]
    region[-1, :] = near[-1, :]
    region[:, 0] = near[:, 0]
    region[:, -1] = near[:, -1]
    while True:
        grown = region.copy()
        grown[1:, :] |= region[:-1, :]
        grown[:-1, :] |= region[1:, :]
        grown[:, 1:] |= region[:, :-1]
        grown[:, :-1] |= region[:, 1:]
        grown &= near
        if (grown == region).all():
            return region
        region = grown


def trim(rgba, pad):
    ys, xs = np.nonzero(rgba[..., 3] > 0.1)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    out = rgba[y0:y1, x0:x1]
    return np.pad(out, ((pad, pad), (pad, pad), (0, 0)))


def keyed(rgb):
    bg = np.median(border(rgb), axis=0)
    d = np.sqrt(((rgb - bg) ** 2).sum(axis=2))
    region = connected_background(d < T1)
    t = np.clip((d - T0) / (T1 - T0), 0, 1)
    alpha = np.where(region, t * t * (3 - 2 * t), 1.0)
    # Отмыть край от цвета фона: пиксель = α·знак + (1−α)·фон.
    a = alpha[..., None]
    fg = np.where(a > 0.02, (rgb - (1 - a) * bg) / np.maximum(a, 0.02), rgb)
    rgba = np.dstack([np.clip(fg, 0, 255), alpha * 255])
    return trim(rgba, 2), bg


def tile(rgb):
    """Фон остаётся: обрезать поля до знака и оставить ровную плашку."""
    bg = np.median(border(rgb), axis=0)
    d = np.sqrt(((rgb - bg) ** 2).sum(axis=2))
    ys, xs = np.nonzero(d > T1)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    h = y1 - y0
    pad = int(round(h * 0.16))
    out = np.empty((h + 2 * pad, (x1 - x0) + 2 * pad, 3))
    out[:] = bg
    out[pad:pad + h, pad:pad + (x1 - x0)] = rgb[y0:y1, x0:x1]
    # Края исходника неровные по цвету (сжатие JPEG) — поля заливаются
    # ровным фоном, а в плашку переносится только сам знак с его окружением.
    return np.dstack([out, np.full(out.shape[:2], 255.0)]), bg


def save(rgba, slug):
    im = Image.fromarray(rgba.round().astype(np.uint8), 'RGBA')
    if im.height > MAX_H:
        w = round(im.width * MAX_H / im.height)
        # Premultiplied: иначе цвет прозрачных пикселей затекает в край.
        im = im.convert('RGBa').resize((w, MAX_H), Image.LANCZOS).convert('RGBA')
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f'{slug}.webp'
    im.save(path, 'WEBP', quality=90, method=6)
    return im.width, im.height, path.stat().st_size


def main():
    manifest = {}
    for slug, spec in SPEC.items():
        rgb = np.asarray(Image.open(source(slug)).convert('RGB')).astype(float)
        rgb = rgb[spec.get('crop_top', 0):]
        rgba, bg = (tile if spec.get('keep_bg') else keyed)(rgb)
        w, h, size = save(rgba, slug)
        manifest[slug] = {'file': f'img/partners/{slug}.webp', 'w': w, 'h': h}
        if spec.get('keep_bg'):
            manifest[slug]['tile'] = True
        print(f'  {slug:26s} {w:4d}×{h:<4d} {size / 1024:5.1f} КБ   фон {tuple(int(c) for c in bg)}')
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(f'✓ {len(manifest)} логотипов → {OUT}/, размеры → {MANIFEST}')


if __name__ == '__main__':
    main()
