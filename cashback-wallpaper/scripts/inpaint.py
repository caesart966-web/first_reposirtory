#!/usr/bin/env python3
"""Убирает со снимка экрана блокировки то, что нарисовал iOS: часы, дату,
строку состояния, кнопки. Восстанавливает фон нейросетью LaMa.

    python3 scripts/inpaint.py снимок.png маска.png чистый-фон.png [--model big-lama.pt] [--scale 0.5]

Маска — белым то, что убрать. Модель — big-lama.pt (TorchScript из IOPaint,
https://github.com/Sanster/models/releases/download/add_big_lama/big-lama.pt,
~200 МБ, в git не идёт); нужен PyTorch.

Почему не на полном размере: LaMa учили на кадрах около 512 px, и на снимке
1179×2556 большие дыры (цифры часов шириной 100 px) она заполняет мелким
повтором. На половинном размере она видит складки фона целиком и продолжает
их через дыру. Готовое увеличивается обратно и вклеивается ТОЛЬКО в маску
с мягким краем: всё вне маски остаётся пикселями оригинала. Сверху — зерно
той же силы, что у фона рядом: гладкая заливка на зернистом снимке видна
пятном.
"""
import argparse
import numpy as np
import torch
from PIL import Image, ImageFilter

ap = argparse.ArgumentParser()
ap.add_argument('image')
ap.add_argument('mask')
ap.add_argument('out')
ap.add_argument('--model', default='big-lama.pt')
ap.add_argument('--scale', type=float, default=0.5)
a = ap.parse_args()

img = Image.open(a.image).convert('RGB')
mask = Image.open(a.mask).convert('L')
W, H = img.size

def run(im, m):
    """LaMa на одном размере; стороны добиваются до кратных 8."""
    x = np.asarray(im, dtype=np.float32) / 255.0
    k = (np.asarray(m) > 127).astype(np.float32)
    h, w = k.shape
    ph, pw = (8 - h % 8) % 8, (8 - w % 8) % 8
    x = np.pad(x, ((0, ph), (0, pw), (0, 0)), mode='reflect')
    k = np.pad(k, ((0, ph), (0, pw)), mode='reflect')
    xt = torch.from_numpy(x).permute(2, 0, 1)[None]
    kt = torch.from_numpy(k)[None, None]
    with torch.inference_mode():
        y = model(xt, kt)[0].permute(1, 2, 0).numpy()
    return Image.fromarray(np.clip(y[:h, :w] * 255, 0, 255).astype(np.uint8))

torch.set_num_threads(max(1, torch.get_num_threads()))
model = torch.jit.load(a.model, map_location='cpu').eval()

if a.scale != 1:
    sw, sh = round(W * a.scale), round(H * a.scale)
    small = img.resize((sw, sh), Image.LANCZOS)
    msmall = mask.resize((sw, sh), Image.BILINEAR).point(lambda v: 255 if v > 20 else 0)
    fill = run(small, msmall).resize((W, H), Image.LANCZOS)
else:
    fill = run(img, mask)

# Зерно: остаток после размытия у оригинала вне маски — его сила
# переносится на заливку (уменьшение и увеличение зерно съели).
orig = np.asarray(img, dtype=np.float32)
blur = np.asarray(img.filter(ImageFilter.GaussianBlur(2)), dtype=np.float32)
outside = np.asarray(mask) < 10
# Медианное отклонение, а не std: края складок — тоже «остаток после
# размытия», и по std зерно выходило вдвое сильнее, чем у фона.
hp = (orig - blur).mean(axis=2)[outside]
sigma = float(1.4826 * np.median(np.abs(hp - np.median(hp))))
rng = np.random.default_rng(7)
noise = rng.normal(0, 1, (H, W, 1)).astype(np.float32)
noise = np.asarray(Image.fromarray(((noise[..., 0] * 40) + 128).clip(0, 255).astype(np.uint8))
                   .filter(ImageFilter.GaussianBlur(0.6)), dtype=np.float32)[..., None] - 128
noise *= sigma / max(noise.std(), 1e-6)
filled = np.clip(np.asarray(fill, dtype=np.float32) + noise, 0, 255)

soft = np.asarray(mask.filter(ImageFilter.GaussianBlur(3)), dtype=np.float32)[..., None] / 255.0
out = orig * (1 - soft) + filled * soft
Image.fromarray(out.round().astype(np.uint8)).save(a.out)
print(f'{a.out}: {W}×{H}, масштаб {a.scale}, зерно σ={sigma:.2f}')
