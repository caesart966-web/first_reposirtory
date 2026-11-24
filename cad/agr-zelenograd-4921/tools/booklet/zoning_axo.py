"""Схема функционального зонирования (аксонометрия) — производственное здание, пр. 4921.

    python3 zoning_axo.py <куда.png>

Геометрия — по планам авторов (схемы планов 1 этажа и антресоли, оси 1–9 и А–Д через 6 м): помещения
прямоугольниками в осях здания, уровни разнесены по высоте («взрывная» аксонометрия), чтобы антресоль
не закрывала первый этаж. Номера помещений — по экспликации.
"""
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MPoly
import matplotlib.patheffects as pe

for f_ in ('Montserrat-Regular.ttf', 'Montserrat-SemiBold.ttf', 'Montserrat-Bold.ttf'):
    p = '/usr/share/fonts/truetype/montserrat/' + f_
    try:
        fm.fontManager.addfont(p)
    except Exception:
        pass
plt.rcParams['font.family'] = 'Montserrat'

ZONES = {
    'prod': ('#9FD3E0', 'производственная зона'),
    'adm': ('#F4C7A2', 'административная зона (антресоль)'),
    'san': ('#E7B7D2', 'санитарно-бытовые помещения'),
    'tech': ('#BDBDBD', 'технические помещения'),
    'stair': ('#EFE3A6', 'лестничные клетки'),
    'store': ('#C9B6DE', 'кладовая'),
}
L, B = 48.0, 24.0
LVL2 = 4.09
GAP = 21.0                                         # раздвижка уровней на схеме
# (зона, x0, y0, x1, y1, высота призмы) — x вдоль осей 1→9, y вдоль А→Д, м от осей 1 и А
FLOOR1 = [
    ('stair', 0.0, 0.0, 6.0, 3.45, 3.0),
    ('store', 6.0, 0.0, 7.3, 3.45, 3.0),
    ('tech', 7.4, 0.0, 8.8, 3.45, 3.0),            # водомерный узел
    ('san', 42.0, 21.4, 43.6, 24.0, 3.0),          # санузел 3
    ('san', 43.6, 21.4, 44.4, 24.0, 3.0),          # КУИ 4
    ('tech', 44.4, 21.4, 45.6, 24.0, 3.0),         # электрощитовая 5
    ('tech', 45.6, 21.4, 48.0, 24.0, 3.0),         # ИТП 6
]
FLOOR2 = [
    ('stair', 0.0, 0.0, 6.0, 3.3, 3.0),            # лестничная клетка 9
    ('adm', 0.0, 3.3, 12.0, 24.0, 3.0),            # антресоль 8
    ('adm', 6.0, 0.0, 12.0, 3.3, 3.0),
]
LABELS1 = [(3.0, 1.7, '1'), (6.65, 1.7, '7'), (24.0, 12.0, '2'), (42.8, 22.7, '3'), (44.0, 22.7, '4'),
           (45.0, 22.7, '5'), (46.8, 22.7, '6')]
LABELS2 = [(3.0, 1.6, '9'), (6.0, 13.5, '8')]
ENTR = [  # (x, y, направление внутрь, цвет, подпись)
    (0.0, 1.7, (1, 0), '#D7262C', ''), (0.0, 4.6, (1, 0), '#D7262C', ''),
    (0.0, 11.0, (1, 0), '#D7262C', ''), (0.0, 13.0, (1, 0), '#D7262C', ''),
    (20.6, 24.0, (0, -1), '#2F5597', 'ворота'), (39.7, 24.0, (0, -1), '#D7262C', ''),
    (46.8, 24.0, (0, -1), '#7A7A7A', ''),
]

AZ, EL = np.radians(36.0), np.radians(32.0)


def proj(p):
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    u = x * np.cos(AZ) - y * np.sin(AZ)
    w = x * np.sin(AZ) + y * np.cos(AZ)
    v = z * np.cos(EL) + w * np.sin(EL)
    d = -w * np.cos(EL) + z * np.sin(EL)            # глубина: больше — ближе к зрителю
    return np.stack([u, v], -1), d


def box_faces(x0, y0, x1, y1, z0, z1):
    P = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    idx = [(4, 5, 6, 7, 'top'), (0, 1, 5, 4, 's'), (1, 2, 6, 5, 'e'), (2, 3, 7, 6, 'n'), (3, 0, 4, 7, 'w')]
    return [(P[list(i[:4])], i[4]) for i in idx]


def shade(hexc, side):
    c = np.array(matplotlib.colors.to_rgb(hexc))
    k = {'top': 1.0, 's': 0.86, 'w': 0.78, 'e': 0.70, 'n': 0.66, 'slab': 0.9}[side]
    return tuple(np.clip(c * k, 0, 1))


def main(out):
    fig = plt.figure(figsize=(842 / 72, 621 / 72), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_aspect('equal'); ax.axis('off')
    halo = [pe.withStroke(linewidth=1.8, foreground='white')]

    def draw_faces(faces, z0):
        for i, (P, fc, lw, ec) in enumerate(sorted(faces, key=lambda f: proj(f[0])[1].mean())):
            uv, _ = proj(P)
            ax.add_patch(MPoly(uv, closed=True, fc=fc, ec=ec, lw=lw, joinstyle='round', zorder=z0 + i * 1e-4))

    def labels(base, labs, z):
        for x, y, t in labs:
            zz = base + (3.0 if base == 0 and t != '2' else 0.06 if t == '2' else 0.25)
            uv, _ = proj(np.array([x, y, zz]))
            ax.text(uv[0], uv[1], t, fontsize=7 if t not in ('2', '8') else 9, fontweight='bold', ha='center',
                    va='center', color='#1D1D1D', path_effects=halo, zorder=z)

    for lvl, (base, items, sx) in enumerate(((0.0, FLOOR1, L), (LVL2 + GAP, FLOOR2, 12.0))):
        slab = [(P, '#F1F1F1' if side == 'top' else shade('#D9D9D9', side), 0.4, '#8A8A8A')
                for P, side in box_faces(0, 0, sx, B, base - 0.35, base)]
        draw_faces(slab, 10 + lvl * 30)
        zf = []
        if base == 0.0:
            zf += [(P, ZONES['prod'][0], 0.3, '#7FAFBD') for P, side in box_faces(0.0, 0.0, L, B, base, base + 0.06)
                   if side == 'top']
        for z, x0, y0, x1, y1, h in items:
            if base > 0:
                h = 0.25                                   # антресоль — заливкой по плите, без стен
            zf += [(P, shade(ZONES[z][0], side), 0.35, '#5A5A5A') for P, side in box_faces(x0, y0, x1, y1, base,
                                                                                            base + h)]
        draw_faces(zf, 15 + lvl * 30)
        if lvl == 0:
            labels(0.0, LABELS1, 30)
            for x, y, d, col, cap in ENTR:
                p0 = np.array([x - d[0] * 3.2, y - d[1] * 3.2, 0.6])
                p1 = np.array([x - d[0] * 0.3, y - d[1] * 0.3, 0.6])
                a_, _ = proj(p0); b_, _ = proj(p1)
                ax.annotate('', xy=b_, xytext=a_, arrowprops=dict(arrowstyle='-|>', color=col, lw=1.6,
                                                                  mutation_scale=9), zorder=31)
            for i, nm in enumerate('123456789'):
                uv, _ = proj(np.array([i * 6.0, -1.8, -0.35]))
                ax.text(uv[0], uv[1], nm, fontsize=5.5, ha='center', va='center', color='#555')
            for j, nm in enumerate('АБВГД'):
                uv, _ = proj(np.array([-1.8, j * 6.0, -0.35]))
                ax.text(uv[0], uv[1], nm, fontsize=5.5, ha='center', va='center', color='#555')
        else:
            rect = np.array([[12, 0, base], [L, 0, base], [L, B, base], [12, B, base], [12, 0, base]], float)
            uv, _ = proj(rect)
            ax.plot(uv[:, 0], uv[:, 1], color='#7A7A7A', lw=0.6, ls=(0, (3, 2)), zorder=40)
            c, _ = proj(np.array([31.0, 12.0, base]))
            ax.text(c[0], c[1], 'второй свет над производственной зоной', fontsize=6.5, ha='center',
                    va='center', color='#555', style='italic', zorder=40)
            labels(base, LABELS2, 72)
    uv, _ = proj(np.array([L, 0.0, -0.35]))
    ax.text(uv[0] + 1.2, uv[1] - 2.2, '±0,000 (абс. 196,02) — 1 этаж', fontsize=6.5, ha='left', va='top',
            color='#333', zorder=45)
    uv, _ = proj(np.array([12.0, 0.0, LVL2 + GAP - 0.35]))
    ax.text(uv[0] + 1.2, uv[1] - 1.2, '+4,090 — антресоль', fontsize=6.5, ha='left', va='top', color='#333',
            zorder=75)
    ax.autoscale_view()
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    ax.set_xlim(x0 - 2, x1 + 9); ax.set_ylim(y0 - 2, y1 + 2)
    fig.savefig(out, dpi=300, facecolor='white')
    print(out)


if __name__ == '__main__':
    main(sys.argv[1])
