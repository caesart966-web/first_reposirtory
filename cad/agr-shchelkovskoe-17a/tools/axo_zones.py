"""Схема функционального зонирования объекта в аксонометрии (по модели АР).

    python3 axo_zones.py <AR.ifc> <areas.json> <near.osm> <куда.png>

Вид с юго-запада. Помещения — объёмы высотой до подвесного потолка, окрашенные
по назначению; крыльца и терраса — плиты; дом 17 и участок — в окружении.
"""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MPoly
from shapely.geometry import Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import frame      # noqa: E402
import ifc_geom   # noqa: E402
import ifcopenshell  # noqa: E402
import situation  # noqa: E402

for f_ in ('Montserrat-Regular.ttf', 'Montserrat-Medium.ttf', 'Montserrat-SemiBold.ttf', 'Montserrat-Bold.ttf'):
    p = '/usr/share/fonts/truetype/montserrat/' + f_
    if os.path.exists(p):
        fm.fontManager.addfont(p)
plt.rcParams['font.family'] = 'Montserrat'

ZONE_COL = {'trade': '#8FCFD3', 'mop': '#E6E1B4', 'staff': '#F2B99A', 'store': '#C9B6DE', 'tech': '#BDBDBD'}
ROOM_ZONE = {'1': 'mop', '2': 'trade', '3': 'staff', '4': 'staff', '5': 'staff', '6': 'staff', '7': 'staff',
             '8': 'store', '9': 'store', '10': 'tech', '11': 'tech'}
AZ = np.radians(225.0)      # взгляд с юго-запада (в местных осях)
EL = np.radians(30.0)


def proj(p):
    """(u, v, z) -> экран. Ось взгляда из точки (−,−) в сторону (+,+)."""
    p = np.atleast_2d(np.asarray(p, float))
    u, v, z = p[:, 0], p[:, 1], p[:, 2]
    x = (u - v) * np.cos(np.radians(45))
    depth = (u + v) * np.sin(np.radians(45))
    y = depth * np.sin(EL) + z * np.cos(EL)
    return np.c_[x, y], depth


def shade(hexcol, k):
    c = np.array(matplotlib.colors.to_rgb(hexcol))
    return tuple(np.clip(c * k, 0, 1))


def prism_faces(poly, z0, z1, col, edge='#3c3c3c', lw=0.5):
    faces = []
    pts = np.array(poly.exterior.coords)[:-1]
    if Polygon(pts).exterior.is_ccw is False:
        pts = pts[::-1]
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        e = b - a
        nrm = np.array([e[1], -e[0]])                     # наружная нормаль для обхода против часовой
        if nrm @ np.array([-1.0, -1.0]) <= 0:             # грань смотрит от зрителя
            continue
        quad = np.array([[a[0], a[1], z0], [b[0], b[1], z0], [b[0], b[1], z1], [a[0], a[1], z1]])
        k = 0.78 if abs(e[0]) > abs(e[1]) else 0.9
        faces.append((quad, shade(col, k), edge, lw))
    top = np.c_[pts, np.full(n, z1)]
    faces.append((top, col, edge, lw))
    return faces


def main(ifc_path, areas_path, osm_path, out_png, size=(11.69, 8.63), dpi=300):
    f = ifcopenshell.open(ifc_path)
    S = ifc_geom.spaces(f)
    A = json.load(open(areas_path))
    site = Polygon(frame.w2l(np.array(A['site_world']) / 1000))
    shell = Polygon(frame.w2l(np.array(A['inner_world']) / 1000)).buffer(0.28, join_style=2)
    G = situation.build(osm_path, areas_path)

    low, sides, tops = [], [], []
    ground = []
    # дом 17 (соседнее существующее здание) — контуром на земле
    for poly, num in G['buildings']:
        if num == '17':
            ground.append(Polygon(frame.w2l(np.array(poly.exterior.coords))))
    # открытые элементы: крыльца, терраса; цоколь
    for pw in A['parts_world'][1:]:
        pl = Polygon(frame.w2l(np.array(pw) / 1000))
        low += prism_faces(pl, -0.45, 0.0, '#D6D6D6', lw=0.35)
    low += prism_faces(shell, -0.45, 0.0, '#B9B9B9', lw=0.35)
    for nm, d in S.items():
        num = d['space'].Name
        if num not in ROOM_ZONE:
            continue
        pl = Polygon(frame.w2l(np.array(d['poly'].exterior.coords) / 1000))
        fs = prism_faces(pl, 0.0, 3.3, ZONE_COL[ROOM_ZONE[num]], lw=0.45)
        sides += fs[:-1]
        tops.append(fs[-1])
    faces = low + sides + tops

    fig = plt.figure(figsize=size, dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_aspect('equal'); ax.axis('off')
    # участок на земле
    sp, _ = proj(np.c_[np.array(site.exterior.coords), np.full(len(site.exterior.coords), -0.46)])
    ax.add_patch(MPoly(sp, closed=True, fc='#F4F4F2', ec='#1a1a1a', lw=1.0, zorder=1))

    def depth_key(face):
        q = face[0]
        _, d = proj(q)
        return -(d.mean()) + 0.001 * q[:, 2].mean()
    for g_ in ground:
        gp, _ = proj(np.c_[np.array(g_.exterior.coords), np.full(len(g_.exterior.coords), -0.45)])
        ax.add_patch(MPoly(gp, closed=True, fc='#E2E2E2', ec='#8a8a8a', lw=0.6, hatch='////', zorder=1.5))
        c = g_.representative_point()
        cp, _ = proj([(c.x, c.y, -0.45)])
        ax.text(cp[0, 0], cp[0, 1], '17', fontsize=9, ha='center', va='center', color='#555', zorder=1.6)
    for layer, z in ((low, 2), (sides, 3), (tops, 4)):
        for q, col, edge, lw in sorted(layer, key=depth_key):
            xy, _ = proj(q)
            ax.add_patch(MPoly(xy, closed=True, fc=col, ec=edge, lw=lw, joinstyle='round', zorder=z))

    # входы: посетители — красный треугольник, служебный и загрузка — синий
    def tri(uvz, color, size_=0.9):
        p, _ = proj([uvz])
        p = p[0]
        ax.add_patch(MPoly([p + [0, size_ * 1.15], p + [-size_, -size_ * 0.55], p + [size_, -size_ * 0.55]],
                           closed=True, fc=color, ec='white', lw=0.5, zorder=20))
    tri((4.3, -1.0, 0.6), '#D7262C')            # главный вход (юго-западный угол)
    tri((1.0, 25.1, 0.6), '#2F5597')            # служебный вход (запад)
    tri((20.6, 24.0, 0.6), '#2F5597')           # загрузка с террасы (восток)
    allp = np.vstack([proj(q)[0] for q, *_ in faces] + [sp] + [proj(np.c_[np.array(g_.exterior.coords), np.zeros(len(g_.exterior.coords))])[0] for g_ in ground])
    matplotlib.rcParams['hatch.color'] = '#9a9a9a'
    pad = 2.0
    ax.set_xlim(allp[:, 0].min() - pad, allp[:, 0].max() + pad)
    ax.set_ylim(allp[:, 1].min() - pad, allp[:, 1].max() + pad)
    fig.savefig(out_png, dpi=dpi, transparent=False, facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    main(*sys.argv[1:5])
