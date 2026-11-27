"""Лист буклета: схема планировочной организации участка со схемой транспортного
и пожарного обслуживания. Основа — генплан авторов проекта, очищенный от прежних
маршрутов; новые маршруты наносятся в координатах модели.

    python3 scheme_booklet.py <очищенная основа x2> <куда.png>
"""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MPoly, FancyArrowPatch
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import frame  # noqa: E402

K = 2.0                                    # основа увеличена вдвое
PXM = K / frame.S_                         # пикселей листа на метр
for f in ('Montserrat-Regular.ttf', 'Montserrat-Medium.ttf', 'Montserrat-SemiBold.ttf', 'Montserrat-Bold.ttf'):
    p = '/usr/share/fonts/truetype/montserrat/' + f
    if os.path.exists(p):
        fm.fontManager.addfont(p)
plt.rcParams['font.family'] = 'Montserrat'

FIRE, TRUCK, CAR, WALK, NAVY = '#E3000F', '#7B2D8E', '#0070C0', '#00963F', '#0000C8'

# --- геометрия в местных координатах (u — вдоль шоссе на восток, v — от шоссе), м ---
B_W, B_E, B_S, B_N = 3.86, 22.32, 0.0, 28.59          # наружные грани здания
LANE_IN, LANE_W = 5.0, 3.5                              # полоса для пожарной техники у западного фасада
LANE_U1 = B_W - LANE_IN                                 # ближняя к зданию кромка
LANE_U0 = LANE_U1 - LANE_W
FRONT_V = -4.15                                         # ось проезда вдоль главного фасада
V_TRUCK, V_FIRE = -3.45, -5.6
PARK_V0, PARK_V1 = -8.3, -5.8                           # приобъектные места вдоль южного края проезда
PARKING = [('mgn', 8.4, 14.4, -4.7), ('std', 14.8, 20.8, PARK_V1), ('ev', 21.2, 27.2, PARK_V1)]
BOTTOM = 803                                            # ниже этой строки основы карта кончается
EAST_U = 55.6                                           # ось проезда восточнее дома 17
GATE = (47.2, 21.6)                                     # ворота во двор
RED = json.load(open(os.path.join(HERE, 'redline.json')))


def P(uv):
    return frame.l2p(uv, K)


def poly(ax, uv, **kw):
    ax.add_patch(MPoly(P(uv), closed=True, **kw))


def route(ax, uv, color, lw=2.6, heads=(), both=False, ls='-', z=6, dash=None):
    p = P(uv)
    line, = ax.plot(p[:, 0], p[:, 1], color=color, lw=lw, ls=ls, solid_capstyle='round',
                    solid_joinstyle='round', zorder=z)
    if dash:
        line.set_dashes(dash)
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    cum = np.r_[0, np.cumsum(seg)]
    for h in heads:
        t, direction = (h, 1) if not isinstance(h, tuple) else h
        s = t * cum[-1]
        i = min(np.searchsorted(cum, s, side='right') - 1, len(seg) - 1)
        d = (p[i + 1] - p[i]) / seg[i] * direction
        c = p[i] + (p[i + 1] - p[i]) * (s - cum[i]) / seg[i]
        L, Wd = 0.95 * PXM * 1.9, 0.95 * PXM * 0.75
        n = np.array([-d[1], d[0]])
        tri = np.array([c + d * L * 0.55, c - d * L * 0.45 + n * Wd, c - d * L * 0.45 - n * Wd])
        ax.add_patch(MPoly(tri, closed=True, fc=color, ec='white', lw=0.5, zorder=z + 1))


def label(ax, uv, text, size=6.4, color='#1a1a1a', ha='center', va='center', rot=0, weight='medium',
          box=True, z=12):
    x, y = P([uv])[0]
    ax.text(x, y, text, fontsize=size, color=color, ha=ha, va=va, rotation=rot, fontweight=weight, zorder=z,
            linespacing=1.15, rotation_mode='anchor',
            bbox=dict(boxstyle='round,pad=0.22', fc='white', ec='none', alpha=0.88) if box else None)


def dim(ax, a, b, text, off=(0, 0), size=5.6):
    pa, pb = P([a])[0], P([b])[0]
    ax.annotate('', xy=pb, xytext=pa, arrowprops=dict(arrowstyle='<->', lw=0.7, color='#111', shrinkA=0, shrinkB=0),
                zorder=11)
    m = (pa + pb) / 2 + np.array(off) * PXM
    ax.text(m[0], m[1], text, fontsize=size, ha='center', va='center', color='#111', zorder=12, fontweight='semibold',
            bbox=dict(boxstyle='round,pad=0.12', fc='white', ec='none', alpha=0.9))


def stand(ax, centre, along, length=8.0, width=2.5):
    """Место установки пожарного автомобиля: прямоугольник с косой штриховкой."""
    c = np.array(centre, float)
    a = np.array(along, float) / np.linalg.norm(along)
    n = np.array([-a[1], a[0]])
    q = [c - a * length / 2 - n * width / 2, c + a * length / 2 - n * width / 2,
         c + a * length / 2 + n * width / 2, c - a * length / 2 + n * width / 2]
    poly(ax, q, fc='white', ec=FIRE, lw=1.1, hatch='////', zorder=7, alpha=0.92)


def main(base_path, out_path, mode='routes', win=None):
    """win — окно по ширине (px0, px1) для листа другой пропорции; None — вся ширина."""
    base = np.asarray(Image.open(base_path).convert('RGB'))
    H, W = base.shape[:2]
    fig = plt.figure(figsize=(W / 200, H / 200), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(base, interpolation='lanczos')
    ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis('off')
    matplotlib.rcParams['hatch.linewidth'] = 0.9
    matplotlib.rcParams['hatch.color'] = FIRE

    # высотная отметка во дворе была закрыта прежней стрелкой — набираем заново
    ax.add_patch(plt.Rectangle((553 * K, 360 * K), 50 * K, 18.4 * K, fc=(122 / 255,) * 3, ec='none', zorder=2))
    ax.plot([543.5 * K, 560 * K, 598.5 * K], [400 * K, 377.6 * K, 377.6 * K], color='#111', lw=0.75, zorder=3)
    ax.text(579.5 * K, 375.4 * K, '154,35', fontsize=6.9, color='#E0242B', ha='center', va='baseline', zorder=3,
            family='DejaVu Sans', style='italic', stretch='condensed')

    # красная линия и граница участка — поверх основы, по координатам
    ru = np.array([-8.0, 110.0])
    rl = P(np.c_[ru, RED['b'] + RED['k'] * ru])
    ax.plot(rl[:, 0], rl[:, 1], color='#D8262C', lw=1.0, zorder=4)
    site = np.array(json.load(open(os.path.join(HERE, 'out_ifc', 'areas.json')))['site_world']) / 1000
    sp = frame.w2p(site, K)
    ax.add_patch(MPoly(sp, closed=True, fc='none', ec=NAVY, lw=1.9, zorder=5, joinstyle='miter'))

    if mode == 'routes':
        # полоса для проезда и установки пожарной техники вдоль западного (продольного) фасада
        poly(ax, [(LANE_U0, 0.6), (LANE_U1, 0.6), (LANE_U1, B_N + 3.0), (LANE_U0, B_N + 3.0)],
             fc=FIRE, ec=FIRE, lw=0.8, alpha=0.13, zorder=3)
        poly(ax, [(LANE_U0, 0.6), (LANE_U1, 0.6), (LANE_U1, B_N + 3.0), (LANE_U0, B_N + 3.0)],
             fc='none', ec=FIRE, lw=0.9, ls=(0, (5, 3)), zorder=6)
        lane_c = (LANE_U0 + LANE_U1) / 2
        stand(ax, (lane_c, 7.5), (0, 1))
        stand(ax, (lane_c, 21.0), (0, 1))

        # маршруты
        left = -34.0
        # пожарная техника: с проезда вдоль главного фасада — вдоль западного фасада — сквозной выезд на север
        route(ax, [(left, V_FIRE), (-9.0, V_FIRE), (-6.2, -3.4), (lane_c, 1.6), (lane_c, B_N + 1.2),
                   (lane_c - 2.6, B_N + 3.7), (-40.0, B_N + 3.9)], FIRE, heads=(0.33, 0.52, 0.9))
        # грузовой транспорт: проезд вдоль главного фасада — проезд восточнее дома 17 — ворота — двор
        truck = [(left, V_TRUCK), (EAST_U - 2.5, V_TRUCK), (EAST_U, V_TRUCK + 2.5), (EAST_U, GATE[1] - 2.5),
                 (EAST_U - 2.5, GATE[1]), (GATE[0], GATE[1]), (31.0, GATE[1] + 0.6)]
        route(ax, truck, TRUCK, heads=(0.42, (0.47, -1), 0.66, (0.71, -1), 0.93))
        # легковой транспорт: проезд вдоль главного фасада в обе стороны
        route(ax, [(left, FRONT_V), (47.0, FRONT_V)], CAR, lw=1.8, heads=(0.50, (0.56, -1), 0.86, (0.92, -1)))
        # пешеходы: к главному входу в юго-западном углу здания
        route(ax, [(-9.5, -1.5), (2.0, -1.5), (4.6, 0.9)], WALK, lw=1.7, dash=(0.6, 2.0), heads=(0.96,))
        route(ax, [(70.0, -21.0), (61.0, -9.6), (58.5, -1.5), (9.0, -1.5), (6.4, 0.6)], WALK, lw=1.7, dash=(0.6, 2.0),
              heads=(0.27, 0.985))

        # приобъектная парковка: 3 м/м, в т.ч. 1 для МГН (М4, 6,0 × 3,6 м) и 1 для электромобиля
        for kind, u0, u1, vtop in PARKING:
            poly(ax, [(u0, PARK_V0), (u1, PARK_V0), (u1, vtop), (u0, vtop)], fc='white', ec=CAR, lw=1.0, zorder=7)
            c = P([((u0 + u1) / 2, (PARK_V0 + vtop) / 2)])[0]
            if kind == 'mgn':
                ax.text(c[0], c[1], '\u267F', fontsize=15, family='DejaVu Sans', color=CAR, ha='center', va='center',
                        rotation=25.2, zorder=8)
            elif kind == 'ev':
                ax.text(c[0], c[1], '\u26A1', fontsize=13, family='DejaVu Sans', color=CAR, ha='center', va='center',
                        rotation=25.2, zorder=8)
            else:
                ax.text(c[0], c[1], 'P', fontsize=8.0, color=CAR, ha='center', va='center', rotation=25.2,
                        fontweight='bold', zorder=8)
        dim(ax, (8.4, -9.6), (14.4, -9.6), '6,0', off=(0, -1.1))
        dim(ax, (13.4, PARK_V0), (13.4, -4.7), '3,6', off=(-1.2, 0))

        # размеры
        dim(ax, (LANE_U1, 14.0), (B_W, 14.0), '5,0', off=(0, -1.25))
        dim(ax, (LANE_U0, 26.5), (LANE_U1, 26.5), '3,5', off=(0, -1.25))

        # подписи
        label(ax, (12.5, 13.5), 'Магазин\nреконструкция\n1 этаж, выс. 6,30 м', size=6.6, weight='semibold', box=False,
              color='#3a1500')
        label(ax, (-17.0, B_N + 6.3), 'сквозной выезд', size=5.6, color=FIRE)
        label(ax, (36.5, 23.3), 'двор\nзона загрузки', size=5.8, color='white', box=False, weight='semibold')
        label(ax, (GATE[0] + 0.4, GATE[1] - 4.4), 'ворота', size=5.4)
        label(ax, (51.0, 9.2), 'контейнерная\nплощадка', size=5.4)
        label(ax, (lane_c - 5.4, 10.0), 'полоса для проезда\nи установки\nпожарной техники', size=5.4, color=FIRE,
              rot=64.8)
        label(ax, (78.0, RED['b'] + RED['k'] * 78.0 - 1.5), 'красная линия', size=5.2, color='#D8262C', rot=25.2,
              box=False)
        label(ax, (-21.0, 16.5), '15', size=6.6, box=False, color='#333')
        label(ax, (14.0, 52.5), '17 к1', size=6.6, box=False, color='#333')
        # главный вход: подпись с выноской
        e0, e1 = P([(5.6, -0.2)])[0], P([(-6.0, -11.0)])[0]
        ax.annotate('главный вход', xy=e0, xytext=e1, fontsize=5.6, color=WALK, ha='center', va='center', zorder=12,
                    fontweight='medium', bbox=dict(boxstyle='round,pad=0.22', fc='white', ec='none', alpha=0.9),
                    arrowprops=dict(arrowstyle='-', lw=0.6, color=WALK, shrinkA=0, shrinkB=1))
        # въезд с дублёра — за нижним краем листа
        q = P([(-9.3, FRONT_V)])[0]
        ax.annotate('к въезду с дублёра\nЩёлковского шоссе, 30 м', xy=(q[0] - 3.0 * PXM, BOTTOM * K - 5), xytext=(176 * K, 762 * K),
                    fontsize=6.0, ha='center', va='center', fontweight='semibold', zorder=12, linespacing=1.15,
                    bbox=dict(boxstyle='round,pad=0.25', fc='white', ec='#555', lw=0.5, alpha=0.95),
                    arrowprops=dict(arrowstyle='-|>', lw=0.9, color='#333', shrinkA=2, shrinkB=0, mutation_scale=9))

    elif mode == 'blago':
        label(ax, (12.5, 13.5), 'Магазин\nреконструкция', size=7.0, weight='semibold', box=False, color='#3a1500')
        label(ax, (37.5, 23.0), 'двор, зона загрузки\nасфальтобетон', size=6.0, color='white', box=False,
              weight='semibold')
        label(ax, (51.0, 9.2), 'контейнерная\nплощадка', size=5.6)
        label(ax, (-5.5, 13.0), 'проезд, асфальтобетон', size=5.6, rot=64.8)
        label(ax, (42.0, -5.6), 'проезд, асфальтобетон', size=5.6, rot=25.2)
        label(ax, (42.0, -13.0), 'газон', size=5.8, rot=25.2, box=False, color='#2f6b2f')
        label(ax, (-21.0, 16.5), '15', size=6.6, box=False, color='#333')
        label(ax, (14.0, 52.5), '17 к1', size=6.6, box=False, color='#333')

    # название шоссе вместо повреждённой подписи основы
    x0, x1, y0, y1 = [int(v * K) for v in (1186, 1491, 652, 824)]
    patch = base[y0:y1, x0:x1].copy()
    dark = patch.astype(int).sum(2) < 330
    import cv2
    grow = cv2.dilate(dark.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    flat = np.array([[255, 255, 255], [220, 237, 205]])
    valid = ~grow
    dist, labels = cv2.distanceTransformWithLabels((~valid).astype(np.uint8), cv2.DIST_L2, 5,
                                                   labelType=cv2.DIST_LABEL_PIXEL)
    vy, vx = np.nonzero(valid)
    lut = np.zeros((labels.max() + 1, 3), np.uint8)
    lut[labels[vy, vx]] = patch[vy, vx]
    gy, gx = np.nonzero(grow)
    patch[gy, gx] = lut[labels[gy, gx]]
    ax.imshow(patch, extent=(x0, x1, y1, y0), interpolation='lanczos', zorder=2)
    ax.set_xlim(0, W); ax.set_ylim(H, 0)
    WX0, WX1 = (0, W) if win is None else win
    if win is None:
        label(ax, frame.w2l([[frame.X0 + 1335 * frame.S_, frame.Y0 - 738 * frame.S_]])[0], 'Щёлковское шоссе',
              size=9.5, rot=25.2, box=False, weight='medium', color='#222')

    # стрелка севера и линейный масштаб
    nx, ny = WX1 - 0.045 * W, 0.105 * H
    ax.annotate('', xy=(nx, ny - 0.06 * H), xytext=(nx, ny + 0.03 * H),
                arrowprops=dict(arrowstyle='-|>', lw=1.2, color='#111', mutation_scale=13), zorder=13)
    ax.text(nx, ny - 0.075 * H, 'С', fontsize=8.5, ha='center', va='bottom', fontweight='bold', zorder=13)
    bx, by = WX0 + 0.035 * W, 0.075 * H
    for i, (a, b) in enumerate(((0, 5), (5, 10), (10, 20))):
        ax.add_patch(plt.Rectangle((bx + a * PXM, by), (b - a) * PXM, 0.012 * H, fc='#111' if i % 2 == 0 else 'white',
                                   ec='#111', lw=0.6, zorder=13))
    for m in (0, 5, 10, 20):
        ax.text(bx + m * PXM, by - 0.008 * H, str(m), fontsize=5.4, ha='center', va='bottom', zorder=13,
                bbox=dict(boxstyle='round,pad=0.1', fc='white', ec='none', alpha=0.85))
    ax.text(bx + 20 * PXM + 0.012 * W, by + 0.006 * H, 'м', fontsize=5.4, ha='left', va='center', zorder=13)

    tmp = out_path + '.full.png'
    fig.savefig(tmp, dpi=200)
    Image.open(tmp).convert('RGB').crop((int(WX0), 0, int(WX1), int(BOTTOM * K))).save(out_path)
    os.remove(tmp)
    print(out_path, W, H)


if __name__ == '__main__':
    w_ = tuple(int(v) for v in sys.argv[4].split(',')) if len(sys.argv) > 4 else None
    main(sys.argv[1], sys.argv[2], *(sys.argv[3:4]), win=w_)
