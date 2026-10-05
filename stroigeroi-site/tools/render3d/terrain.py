"""Рельеф для фона первого экрана: Корякский, Авачинский, сопки, бухта."""
import numpy as np
from noise import fbm, ridged, perlin

EXAG = 1.6  # вертикальное преувеличение, как на открытках


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def volcano(x, y, cx, cy, H, R, p=1.75, G=28, depth=0.10, seed=0.0, cap=None):
    dx, dy = x - cx, y - cy
    r = np.hypot(dx, dy)
    th = np.arctan2(dy, dx)
    s = r / R
    h0 = H * np.clip(1 - s, 0, 1) ** p
    if cap is not None:  # срезанная вершина с куполом (Авачинский)
        c = cap * H
        over = np.clip(h0 - c, 0, None)
        h0 = np.where(h0 > c, c + over * 0.18, h0)
    t = (th / (2 * np.pi) + 0.5) * G
    u = s * 3.2 + seed
    rid = ridged(t, u, octaves=4, period_x=G)
    rid2 = ridged(t * 2.0 + 3.3, u * 1.7 + 9.1, octaves=3, period_x=G * 2)
    ridge = 0.65 * rid + 0.35 * rid2
    A = depth * H * np.clip(s, 0, 1) ** 0.65 * np.clip(1 - s, 0, 1) ** 1.3
    h = h0 - A * (1 - ridge) * 1.6
    h += fbm(x / 1800 + seed, y / 1800, octaves=5) * H * 0.025 * np.clip(s, 0, 1)
    return np.maximum(h, 0), ridge, s


def warp(n, lo, hi, a, b, share=0.72):
    """n точек от lo до hi; доля share приходится на отрезок [a, b]."""
    u = np.linspace(0, 1, n)
    ua = (1 - share) * (a - lo) / ((a - lo) + (hi - b))
    ub = ua + share
    return np.interp(u, [0, ua, ub, 1], [lo, a, b, hi])


def main_terrain(nx=1100, ny=1150):
    xs = warp(nx, -26000, 26000, -11000, 14000)
    ys = warp(ny, 6000, 52000, 17000, 40000)
    x, y = np.meshgrid(xs, ys)
    # Корякский: чуть левее центра кадра
    hk, rk, sk = volcano(x, y, -800, 30000, 3456 * EXAG, 9500, p=1.8, G=30, depth=0.22, seed=0.0)
    # Авачинский: правее и ближе, срезанный конус
    ha, ra, sa = volcano(x, y, 7600, 26500, 2741 * EXAG, 8200, p=1.55, G=24, depth=0.18, seed=4.0, cap=0.84)
    # Дальний конус слева (Вилючинский — вольность композиции)
    hv, rv, sv = volcano(x, y, -17500, 38000, 2175 * EXAG, 7000, p=1.6, G=22, depth=0.09, seed=8.0)
    # Сопки между бухтой и вулканами
    hills = (fbm(x / 6000, y / 6000, octaves=6) * 0.7 + 0.45) * 650
    hills += ridged(x / 3800 + 3, y / 3800 + 1, octaves=6) * 600
    hills += np.clip(fbm(x / 9000 + 5, y / 9000 + 2, octaves=3), 0, None) * 900
    hills *= smoothstep(9000, 15000, y) * (1 - 0.35 * smoothstep(30000, 46000, y))
    near = (fbm(x / 3000 + 9, y / 3000, octaves=5) * 0.5 + 0.5) * 260 * (1 - smoothstep(9000, 14000, y))
    h = np.maximum.reduce([hk, ha, hv, hills + near])
    # смягчить стык конусов с сопками
    h = np.maximum(h, 0.85 * hills + near)
    # берег бухты: всё ближе 8.5 км уходит под воду
    shore = 8200 + fbm(x / 4000, np.zeros_like(x) + 2, octaves=4) * 900
    h = h * smoothstep(shore - 400, shore + 1500, y) - 60 * (1 - smoothstep(shore - 600, shore + 300, y))
    # маска снега
    zrel_k = hk / (3456 * EXAG)
    zrel_a = ha / (2741 * EXAG)
    zrel_v = hv / (2175 * EXAG)
    snow = np.zeros_like(h)
    for zr, rr, line in ((zrel_k, rk, 0.22), (zrel_a, ra, 0.30), (zrel_v, rv, 0.30)):
        n = fbm(x / 700 + line * 10, y / 700, octaves=5) * 0.09
        z = zr + n
        top = smoothstep(line + 0.18, line + 0.32, z)            # верх: сплошной снег
        mid = smoothstep(line - 0.02, line + 0.06, z)            # средний пояс
        gully = smoothstep(0.35, 0.65, 1 - rr)                   # ложбины держат снег
        bare = smoothstep(0.80, 0.93, rr)                        # острые гребни — камень
        cover = top * (1 - 0.55 * bare) + (1 - top) * mid * (0.25 + 0.75 * gully) * (1 - 0.8 * bare)
        streak = smoothstep(line - 0.20, line - 0.06, z) * smoothstep(0.6, 0.85, 1 - rr)
        snow = np.maximum(snow, np.clip(np.maximum(cover, streak), 0, 1))
    # верхние части сопок тоже в снегу
    snow = np.maximum(snow, smoothstep(1500, 2200, h + fbm(x / 1200, y / 1200, octaves=4) * 400) * 0.9)
    return xs, ys, h, snow


if __name__ == '__main__':
    from PIL import Image
    xs, ys, h, snow = main_terrain(550, 575)
    gy, gx = np.gradient(h, ys[1] - ys[0], xs[1] - xs[0])
    shade = np.clip(0.5 + (-gx * 0.6 + gy * 0.4) * 0.8, 0, 1)
    img = np.stack([shade * 255 * (0.6 + 0.4 * snow)] * 3, -1)
    img[..., 2] = np.clip(img[..., 2] + (h < 0) * 120, 0, 255)
    Image.fromarray(img[::-1].astype(np.uint8)).save('out/hillshade.png')
    print(h.max(), h.min())
