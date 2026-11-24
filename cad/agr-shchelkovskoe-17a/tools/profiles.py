"""Транспортный раздел АГР, часть 9: поперечные профили УДС в створе объекта, М 1:200.

    python3 profiles.py <выход>

Профиль 1-1 — по оси u = 12 м (середина главного фасада), с севера (здание) на юг до красной линии за
Щёлковским шоссе; вид на восток. Ширины сняты с планировочной основы ППТ (рис. «Планировочное решение УДС»
из исходных данных ДГП) и с ортофотоплана тех же исходных данных, привязанных к участку по его контуру
(georef.py, около 0,5 м на пиксель, расхождение привязки до 0,8 м); округлены до 0,1 м. Проектный профиль
отличается от существующего только приобъектной парковкой у местного проезда: границы и элементы УДС
объект не меняет.

Пишет PNG ровно в масштабе 1:200 (1 м = 5 мм) и profiles.json с элементами для пояснительной записки.
"""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MPoly, Rectangle, Ellipse

for f_ in ('Montserrat-Regular.ttf', 'Montserrat-Medium.ttf', 'Montserrat-SemiBold.ttf'):
    p_ = '/usr/share/fonts/truetype/montserrat/' + f_
    if os.path.exists(p_):
        fm.fontManager.addfont(p_)
plt.rcParams['font.family'] = 'Montserrat'

SCALE = 200
RED_N, RED_S = -3.1, -111.8          # красные линии (redline.json, situation.py)
# (v0, v1, вид, подпись) — v от южной грани здания, м; север (+) слева
EXIST = [
    (3.0, 0.0, 'building', 'магазин'),
    (0.0, -2.4, 'walk', 'тротуар'),
    (-2.4, -5.9, 'local', 'местный проезд'),
    (-5.9, -28.5, 'green', 'газон, деревья'),
    (-28.5, -35.5, 'walk', 'тротуар'),
    (-35.5, -37.3, 'green', 'газон'),
    (-37.3, -44.3, 'road', 'дублёр Щёлковского ш., в центр'),
    (-44.3, -57.0, 'green', 'разделительная полоса, газон'),
    (-57.0, -70.5, 'road', 'основной ход, в центр'),
    (-70.5, -72.0, 'median', 'ограждение'),
    (-72.0, -88.0, 'road', 'основной ход, в область'),
    (-88.0, -93.3, 'green', 'газон'),
    (-93.3, -96.0, 'walk', 'тротуар'),
    (-96.0, -111.8, 'green', 'газон, деревья'),
    (-111.8, -115.0, 'green', 'парк'),
]
PROJ_CHANGE = [(-5.9, -8.4, 'parking', 'приобъектная парковка')]
ROWS = [(4.0, -57.0), (-57.0, -115.0)]          # две строки чертежа (север -> юг), стык по кромке
COL = {'building': ('#F58220', '#B45309'), 'walk': ('#D9D6D0', '#8A8A8A'), 'local': ('#9C9C9C', '#555555'),
       'road': ('#6E6E70', '#333333'), 'green': ('#CFE6BF', '#7FA77A'), 'median': ('#BDBDBD', '#555555'),
       'parking': ('#DCE9F7', '#0070C0')}
THICK = {'building': 0.0, 'walk': 0.15, 'local': 0.12, 'road': 0.12, 'green': 0.0, 'median': 0.0, 'parking': 0.12}


def elements(proj):
    if not proj:
        return list(EXIST)
    out = []
    for v0, v1, k, t in EXIST:
        if k == 'green' and v0 == -5.9:
            out += PROJ_CHANGE
            out.append((-8.4, v1, k, t))
        else:
            out.append((v0, v1, k, t))
    return out


def draw_row(els, vmax, vmin, out_png, title=None):
    L = vmax - vmin
    W_in = L * 5 / 25.4
    H_m = 20.0                                         # высота строки, м чертежа (в масштабе)
    H_in = H_m * 5 / 25.4
    fig = plt.figure(figsize=(W_in, H_in), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    # ось x — расстояние вдоль профиля слева направо: x = vmax - v
    ax.set_xlim(0, L); ax.set_ylim(-8.0, 12.0); ax.axis('off')
    X = lambda v: vmax - v  # noqa: E731
    ground = 0.0
    for v0, v1, k, t in els:
        a, b = max(min(v0, vmax), vmin), max(min(v1, vmax), vmin)
        if a - b <= 0.01:
            continue
        x0, x1 = X(a), X(b)
        fc, ec = COL[k]
        if k == 'building':
            ax.add_patch(Rectangle((x0, ground), x1 - x0, 5.8, fc=fc, ec=ec, lw=0.6, zorder=3))
            ax.text((x0 + x1) / 2, 2.9, t, rotation=90, fontsize=6.5, ha='center', va='center', color='#3a1500')
            continue
        h = THICK[k]
        top = ground + h
        ax.add_patch(Rectangle((x0, ground - 0.35), x1 - x0, 0.35 + h, fc=fc, ec=ec, lw=0.5, zorder=3))
        if k == 'green':
            n = int((x1 - x0) // 7)
            for i in range(n):
                cx = x0 + (i + 0.5) * (x1 - x0) / n
                ax.plot([cx, cx], [0, 2.6], color='#6B4F2A', lw=0.9, zorder=2)
                ax.add_patch(Ellipse((cx, 4.4), 3.6, 4.0, fc='#9CC77F', ec='#5E8F4C', lw=0.4, zorder=2))
        if k in ('road', 'local'):
            lanes = max(1, int(round((x1 - x0) / 3.4)))
            for i in range(1, lanes):
                xm = x0 + i * (x1 - x0) / lanes
                ax.plot([xm, xm], [top + 0.02, top + 0.02], color='white')
                ax.add_patch(Rectangle((xm - 0.06, top - 0.04), 0.12, 0.06, fc='white', ec='none', zorder=4))
            for i in range(lanes):
                cx = x0 + (i + 0.5) * (x1 - x0) / lanes
                ax.add_patch(Rectangle((cx - 0.9, top + 0.15), 1.8, 1.3, fc='white', ec='#555', lw=0.4, zorder=4))
        if k == 'parking':
            cx = (x0 + x1) / 2
            ax.add_patch(Rectangle((cx - 0.9, top + 0.15), 1.8, 1.3, fc='#DCE9F7', ec='#0070C0', lw=0.6, zorder=4))
            ax.text(cx, top + 0.8, 'P', fontsize=5, ha='center', va='center', color='#0070C0', fontweight='bold',
                    zorder=5)
        # подпись над элементом и размер под ним
        if x1 - x0 > 1.2:
            ax.text((x0 + x1) / 2, 7.4 if k != 'green' else 7.9, t, fontsize=6.0, ha='center', va='bottom',
                    rotation=90 if (x1 - x0) < 6 else 0, color='#222', zorder=6,
                    wrap=True)
        ax.plot([x0, x0], [-0.5, -3.2], color='#333', lw=0.3)
        ax.plot([x1, x1], [-0.5, -3.2], color='#333', lw=0.3)
        ax.annotate('', xy=(x0, -2.8), xytext=(x1, -2.8),
                    arrowprops=dict(arrowstyle='<|-|>', lw=0.35, color='#333', mutation_scale=3, shrinkA=0,
                                    shrinkB=0))
        ax.text((x0 + x1) / 2, -2.45, ('%.1f' % (a - b)).replace('.', ','), fontsize=6.0, ha='center',
                va='bottom', zorder=6)
    for v, nm in ((RED_N, 'красная линия'), (RED_S, 'красная линия')):
        if vmin <= v <= vmax:
            x = X(v)
            ax.plot([x, x], [-4.2, 10.8], color='#D8262C', lw=0.8, dashes=(5, 2), zorder=7)
            ax.text(x + 0.3, 10.6, nm, fontsize=6.0, color='#D8262C', rotation=90, ha='left', va='top', zorder=7)
    ax.plot([0, L], [0, 0], color='#333', lw=0.4, zorder=2)
    ax.text(0.3, -6.2, 'М 1:%d' % SCALE + ('   ' + title if title else ''), fontsize=5, ha='left', va='center')
    fig.savefig(out_png, dpi=300, facecolor='white')
    plt.close(fig)
    return W_in * 72, H_in * 72


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    info = {}
    for proj in (False, True):
        els = elements(proj)
        rows = ROWS if not proj else ROWS[:1]
        for i, (a, b) in enumerate(rows):
            nm = 'prof_%s_%d.png' % ('proj' if proj else 'exist', i + 1)
            info[nm] = draw_row(els, a, b, os.path.join(outdir, nm))
        info['proj' if proj else 'exist'] = [dict(v0=v0, v1=v1, kind=k, label=t, width=round(v0 - v1, 1))
                                             for v0, v1, k, t in els]
    info['red_lines'] = [RED_N, RED_S]
    json.dump(info, open(os.path.join(outdir, 'profiles.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in info.items() if k.endswith('.png')}, ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1])
