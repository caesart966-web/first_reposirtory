"""Схема организации движения транспорта и пешеходов, М 1:2000 (PNG для буклета и DXF).

    python3 situation.py <near.osm> <areas.json> <куда.png> <куда.dxf>

Участок и здание — из модели, окружение — из открытой векторной основы, совмещённой
с генпланом авторов проекта. Чертёж ориентирован на север, координаты — как в модели.
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
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import frame      # noqa: E402
import osm_base   # noqa: E402

SHIFT = np.array([-9.3, -2.5])          # совмещение основы с генпланом авторов проекта
for f in ('Montserrat-Regular.ttf', 'Montserrat-Medium.ttf', 'Montserrat-SemiBold.ttf', 'Montserrat-Bold.ttf'):
    p = '/usr/share/fonts/truetype/montserrat/' + f
    if os.path.exists(p):
        fm.fontManager.addfont(p)
plt.rcParams['font.family'] = 'Montserrat'

FIRE, TRUCK, CAR, WALK, NAVY, ORANGE = '#E3000F', '#7B2D8E', '#0070C0', '#00963F', '#0000C8', '#F58220'
WIDTH = {'primary': 11.0, 'tertiary': 9.0, 'tertiary_link': 5.0, 'service': 5.5}
RED_N, RED_S = -3.08, -111.8            # красные линии Щёлковского шоссе в местных координатах (v)


def build(osm_path, areas_path):
    nodes, ways, rels = osm_base.load(osm_path)
    a = json.load(open(areas_path))
    site = Polygon(np.array(a['site_world']) / 1000)
    inner = Polygon(np.array(a['inner_world']) / 1000)
    g = {'site': site, 'object': inner.buffer(0.3, join_style=2), 'buildings': [], 'green': [], 'roads': [],
         'foot': [], 'stops': [], 'cross': [], 'signals': []}
    for wid, w in ways.items():
        t = w['tags']
        xy = osm_base.coords(nodes, w) + SHIFT
        if len(xy) < 2:
            continue
        if 'building' in t:
            if wid == '590152489':                      # существующий магазин — показан объектом
                continue
            poly = Polygon(xy)
            if not poly.is_valid:
                poly = poly.buffer(0)
            if wid == '53340209':                       # дом 17 примыкает к участку
                poly = poly.difference(site.buffer(1.2))
                if poly.geom_type == 'MultiPolygon':
                    poly = max(poly.geoms, key=lambda q: q.area)
            g['buildings'].append((poly, t.get('addr:housenumber', '')))
        elif t.get('highway') in WIDTH:
            g['roads'].append((LineString(xy), t.get('highway'), t.get('name', ''), t.get('oneway') == 'yes', wid))
        elif t.get('highway') in ('footway', 'path', 'steps', 'pedestrian', 'cycleway'):
            g['foot'].append(LineString(xy))
        elif (t.get('landuse') in ('grass', 'forest', 'recreation_ground', 'village_green') or
              t.get('leisure') in ('park', 'garden') or t.get('natural') in ('wood', 'scrub', 'grassland')):
            if len(xy) > 3:
                p = Polygon(xy)
                g['green'].append(p if p.is_valid else p.buffer(0))
    for nid, n in nodes.items():
        t = n['tags']
        xy = np.array(n['xy']) + SHIFT
        if t.get('highway') == 'bus_stop':
            g['stops'].append((xy, t.get('name', '')))
        elif t.get('highway') == 'crossing':
            (g['signals'] if t.get('crossing') == 'traffic_signals' else g['cross']).append(xy)
    return g


def routes():
    """Маршруты в местных координатах (u, v)."""
    lane = 3.86 - 5.0 - 1.75
    return {
        'entry': [(-30.6, -42.0), (-30.9, -6.0)],
        'car': [(60.0, -40.9), (-28.0, -41.6), (-30.8, -38.5), (-30.9, -8.0), (-28.5, -5.0), (47.0, -5.0)],
        'truck': [(-30.9, -9.5), (-28.0, -4.0), (53.1, -4.0), (55.6, -1.5), (55.6, 19.1), (53.1, 21.6), (31.0, 22.2)],
        'car_out': [(-31.4, -38.0), (-34.5, -42.0), (-75.0, -42.4)],
        'fire': [(-30.9, -11.0), (-27.5, -6.3), (-9.0, -6.3), (-6.2, -3.4), (lane, 1.6), (lane, 29.8),
                 (lane - 2.6, 32.3), (-62.0, 32.5)],
        'walk1': [(138.7, -47.0), (70.0, -31.9), (61.0, -9.6), (58.5, -1.5), (9.0, -1.5), (6.4, 0.6)],
        'walk2': [(-17.9, -39.0), (-17.9, -30.0), (-12.0, -8.0), (2.0, -1.5), (4.6, 0.9)],
    }


def draw(g, out_png, half_w=250.0, half_h=165.0, centre=(22.0, -18.0), scale=2000, dpi=300):
    c = frame.l2w([centre])[0]
    x0, x1, y0, y1 = c[0] - half_w, c[0] + half_w, c[1] - half_h, c[1] + half_h
    win = box(x0, y0, x1, y1)
    fig_w, fig_h = 2 * half_w / scale / 0.0254, 2 * half_h / scale / 0.0254
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.axis('off')
    ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fc='#FBFBF9', ec='none', zorder=0))
    pt = 72 * fig_w / (x1 - x0)                                   # пунктов на метр

    def fill(poly, **kw):
        if poly.is_empty:
            return
        for q in (poly.geoms if hasattr(poly, 'geoms') else [poly]):
            if q.geom_type == 'Polygon':
                ax.add_patch(MPoly(np.array(q.exterior.coords), closed=True, **kw))

    for p in g['green']:
        fill(p.intersection(win), fc='#DCEDCD', ec='none', zorder=1)
    for cas in (True, False):
        for ls, kind, name, oneway, wid in sorted(g['roads'], key=lambda r: WIDTH[r[1]]):
            q = ls.intersection(win.buffer(30))
            for part in (q.geoms if hasattr(q, 'geoms') else [q]):
                if part.is_empty or part.geom_type != 'LineString':
                    continue
                xy = np.array(part.coords)
                w = WIDTH[kind] * pt
                ax.plot(xy[:, 0], xy[:, 1], color='#9A9A9A' if cas else 'white', lw=w + (1.0 if cas else 0),
                        solid_capstyle='round', solid_joinstyle='round', zorder=2 if cas else 3)
    for ls in g['foot']:
        q = ls.intersection(win)
        for part in (q.geoms if hasattr(q, 'geoms') else [q]):
            if not part.is_empty and part.geom_type == 'LineString':
                xy = np.array(part.coords)
                ax.plot(xy[:, 0], xy[:, 1], color='#A8A8A8', lw=0.5, dashes=(2.2, 1.4), zorder=4)
    for poly, num in g['buildings']:
        q = poly.intersection(win)
        fill(q, fc='#C8C8C8', ec='#8C8C8C', lw=0.4, zorder=5)
        if num and q.area > 250 and q.area > 0.6 * poly.area:
            r = poly.representative_point()
            ax.text(r.x, r.y, num, fontsize=5.2, ha='center', va='center', color='#333', zorder=6)
    fill(g['object'], fc=ORANGE, ec='#B45309', lw=0.5, zorder=7)
    fill(g['site'], fc='none', ec=NAVY, lw=1.1, zorder=8)

    # красные линии
    for v in (RED_N, RED_S):
        uu = np.linspace(-320, 360, 3)
        xy = frame.l2w(np.c_[uu, np.full(3, v)])
        ax.plot(xy[:, 0], xy[:, 1], color='#D8262C', lw=0.8, zorder=6)

    R = routes()

    def route(key, color, lw, heads=(), dash=None, z=9):
        xy = frame.l2w(R[key])
        line, = ax.plot(xy[:, 0], xy[:, 1], color=color, lw=lw, solid_capstyle='round', solid_joinstyle='round',
                        zorder=z)
        if dash:
            line.set_dashes(dash)
        seg = np.linalg.norm(np.diff(xy, axis=0), axis=1)
        cum = np.r_[0, np.cumsum(seg)]
        for h in heads:
            t, d_ = (h, 1) if not isinstance(h, tuple) else h
            s = t * cum[-1]
            i = min(np.searchsorted(cum, s, side='right') - 1, len(seg) - 1)
            d = (xy[i + 1] - xy[i]) / seg[i] * d_
            cc = xy[i] + (xy[i + 1] - xy[i]) * (s - cum[i]) / seg[i]
            n = np.array([-d[1], d[0]])
            L, Wd = 5.2, 2.0
            ax.add_patch(MPoly([cc + d * L * 0.55, cc - d * L * 0.45 + n * Wd, cc - d * L * 0.45 - n * Wd],
                               closed=True, fc=color, ec='white', lw=0.3, zorder=z + 1))

    route('car', CAR, 1.3, heads=(0.2, 0.5, (0.58, -1), 0.85))
    route('car_out', CAR, 1.3, heads=(0.8,))
    route('truck', TRUCK, 1.5, heads=(0.3, (0.36, -1), 0.72, 0.95))
    route('fire', FIRE, 1.5, heads=(0.25, 0.52, 0.9))
    route('walk1', WALK, 1.1, dash=(0.5, 1.8), heads=(0.5, 0.97))
    route('walk2', WALK, 1.1, dash=(0.5, 1.8), heads=(0.96,))

    # направления движения на шоссе и дублёре — по направлению осей в основе
    flow = []
    for ls, kind, name, oneway, wid in g['roads']:
        if kind in ('primary', 'tertiary') and oneway:
            q = ls.intersection(win.buffer(-25))
            for part in (q.geoms if hasattr(q, 'geoms') else [q]):
                if part.is_empty or part.geom_type != 'LineString' or part.length < 120:
                    continue
                for frac in (0.22, 0.78):
                    a0 = np.array(part.interpolate(frac, normalized=True).coords[0])
                    a1 = np.array(part.interpolate(min(frac + 14.0 / part.length, 1.0), normalized=True).coords[0])
                    ax.annotate('', xy=a1, xytext=a0, arrowprops=dict(arrowstyle='-|>', lw=0.8, color='#444',
                                                                    mutation_scale=7), zorder=8)
                d = np.array(part.coords[-1]) - np.array(part.coords[0])
                flow.append((kind, name, part, d @ frame.U))

    def lab(uv, text, size=5.0, color='#222', rot=0.0, weight='medium', bx=True, ha='center'):
        x, y = frame.l2w([uv])[0]
        ax.text(x, y, text, fontsize=size, color=color, ha=ha, va='center', rotation=rot, rotation_mode='anchor',
                fontweight=weight, zorder=14, linespacing=1.1,
                bbox=dict(boxstyle='round,pad=0.18', fc='white', ec='none', alpha=0.85) if bx else None)

    for kind, name, part, along in flow:
        m = np.array(part.interpolate(0.62 if kind == 'primary' else 0.2, normalized=True).coords[0])
        uv = frame.w2l([m])[0]
        if kind == 'primary':
            lab((uv[0], uv[1] + 0.2), 'Щёлковское шоссе, ' + ('в центр' if along < 0 else 'в область'), 5.2, rot=25.2,
                bx=False, weight='semibold')
        else:
            lab((uv[0], uv[1] + 0.2), 'Щёлковское шоссе, дублёр', 4.6, rot=25.2, bx=False)
    e = frame.l2w([(-30.8, -22.0)])[0]
    t = frame.l2w([(-66.0, -17.0)])[0]
    ax.annotate('въезд и выезд\nсуществующие', xy=e, xytext=t, fontsize=4.8, ha='center', va='center',
                fontweight='semibold', zorder=14, linespacing=1.1,
                bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='#555', lw=0.4, alpha=0.95),
                arrowprops=dict(arrowstyle='-|>', lw=0.6, color='#333', shrinkA=1, shrinkB=0, mutation_scale=6))
    lab((14.0, 14.0), 'магазин', 4.6, color='#3a1500', bx=False, weight='semibold', rot=25.2)
    lab((86.0, 2.2), 'красная линия', 4.0, color='#D8262C', rot=25.2, bx=False)
    lab((86.0, -116.5), 'красная линия', 4.0, color='#D8262C', rot=25.2, bx=False)
    for xy, name in g['stops']:
        if win.buffer(-45).contains(Point(xy)):
            ax.add_patch(plt.Circle(xy, 3.2, fc='#D8262C', ec='white', lw=0.5, zorder=12))
            ax.text(xy[0], xy[1], 'А', fontsize=3.6, color='white', ha='center', va='center', fontweight='bold',
                    zorder=13)
            ax.text(xy[0] + 5, xy[1] + 6, 'ост. «%s»' % name, fontsize=4.4, color='#222', ha='left', va='center',
                    zorder=14, bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.85))
    for xy in g['cross']:
        if win.contains(Point(xy)):
            ax.add_patch(plt.Rectangle(xy - 2.2, 4.4, 4.4, fc='#0B5CAD', ec='white', lw=0.4, zorder=12))
            ax.text(xy[0], xy[1], 'П', fontsize=3.2, color='white', ha='center', va='center', fontweight='bold',
                    zorder=13)
    for xy in g['signals']:
        if win.contains(Point(xy)):
            ax.add_patch(plt.Circle(xy, 2.6, fc='#111', ec='white', lw=0.4, zorder=12))
            ax.text(xy[0], xy[1], 'С', fontsize=3.2, color='#FFD400', ha='center', va='center', fontweight='bold',
                    zorder=13)

    # север и масштаб
    ax.annotate('', xy=(x1 - 16, y1 - 10), xytext=(x1 - 16, y1 - 36),
                arrowprops=dict(arrowstyle='-|>', lw=1.0, color='#111', mutation_scale=10), zorder=15)
    ax.text(x1 - 16, y1 - 8.5, 'С', fontsize=6.5, ha='center', va='bottom', fontweight='bold', zorder=15)
    bx, by = x0 + 14, y1 - 16
    for i, (a_, b_) in enumerate(((0, 25), (25, 50), (50, 100))):
        ax.add_patch(plt.Rectangle((bx + a_, by), b_ - a_, 2.4, fc='#111' if i % 2 == 0 else 'white', ec='#111',
                                   lw=0.4, zorder=15))
    for m in (0, 25, 50, 100):
        ax.text(bx + m, by + 4.2, str(m), fontsize=4.2, ha='center', va='bottom', zorder=15)
    ax.text(bx + 104, by + 1.2, 'м', fontsize=4.2, ha='left', va='center', zorder=15)
    ax.text(bx + 118, by + 1.2, 'М 1:%d' % scale, fontsize=4.6, ha='left', va='center', fontweight='semibold', zorder=15)
    fig.savefig(out_png, dpi=dpi)
    plt.close(fig)


def dxf(g, out_dxf):
    import ezdxf
    doc = ezdxf.new('R2010', setup=True)
    doc.header['$INSUNITS'] = 6
    doc.styles.add('TXT', font='arial.ttf')
    msp = doc.modelspace()
    layers = {'Граница участка': 5, 'Объект реконструкции': 30, 'Опорная застройка': 8, 'Проезжая часть, оси': 9,
              'Пешеходные дорожки': 8, 'Красные линии': 1, 'Движение легкового транспорта': 5,
              'Движение грузового транспорта': 6, 'Движение пожарной техники': 1, 'Движение пешеходов': 3,
              'Остановки и переходы': 2, 'Подписи': 7}
    for name, col in layers.items():
        doc.layers.add(name, color=col)

    def pl(coords, layer, closed=False):
        msp.add_lwpolyline([(float(x), float(y)) for x, y in coords], close=closed, dxfattribs={'layer': layer})

    pl(list(g['site'].exterior.coords)[:-1], 'Граница участка', True)
    pl(list(g['object'].exterior.coords)[:-1], 'Объект реконструкции', True)
    for poly, num in g['buildings']:
        for q in (poly.geoms if hasattr(poly, 'geoms') else [poly]):
            if q.geom_type == 'Polygon' and not q.is_empty:
                pl(list(q.exterior.coords)[:-1], 'Опорная застройка', True)
                if num:
                    r = q.representative_point()
                    msp.add_text(num, height=2.5, dxfattribs={'layer': 'Подписи', 'style': 'TXT'}).set_placement(
                        (r.x, r.y))
    for ls, kind, name, oneway, wid in g['roads']:
        pl(list(ls.coords), 'Проезжая часть, оси')
    for ls in g['foot']:
        pl(list(ls.coords), 'Пешеходные дорожки')
    for v in (RED_N, RED_S):
        pl(frame.l2w([(-320, v), (360, v)]), 'Красные линии')
    R = routes()
    for key, layer in (('car', 'Движение легкового транспорта'), ('car_out', 'Движение легкового транспорта'), ('truck', 'Движение грузового транспорта'),
                       ('fire', 'Движение пожарной техники'), ('walk1', 'Движение пешеходов'),
                       ('walk2', 'Движение пешеходов')):
        pl(frame.l2w(R[key]), layer)
    for xy, name in g['stops']:
        msp.add_circle((float(xy[0]), float(xy[1])), 3.0, dxfattribs={'layer': 'Остановки и переходы'})
        msp.add_text('ост. «%s»' % name, height=2.5, dxfattribs={'layer': 'Подписи', 'style': 'TXT'}).set_placement(
            (float(xy[0]) + 5, float(xy[1]) + 4))
    for xy in g['cross'] + g['signals']:
        msp.add_point((float(xy[0]), float(xy[1])), dxfattribs={'layer': 'Остановки и переходы'})
    doc.saveas(out_dxf)


if __name__ == '__main__':
    G = build(sys.argv[1], sys.argv[2])
    draw(G, sys.argv[3])
    if len(sys.argv) > 4:
        dxf(G, sys.argv[4])
    print('готово')


def plain_map(g, out_png, size_pt, scale, centre, views=(), dpi=300, labels=True, streets=True, north=True,
              scalebar=True):
    """Карта без маршрутов: ситуационный план или мини-карта с точками съёмки.

    views — [(номер, (u, v) точки, (du, dv) направления взгляда), ...] в местных координатах."""
    c = frame.l2w([centre])[0]
    half_w = size_pt[0] / 72 * 0.0254 * scale / 2
    half_h = size_pt[1] / 72 * 0.0254 * scale / 2
    x0, x1, y0, y1 = c[0] - half_w, c[0] + half_w, c[1] - half_h, c[1] + half_h
    win = box(x0, y0, x1, y1)
    fig = plt.figure(figsize=(size_pt[0] / 72, size_pt[1] / 72), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.axis('off')
    ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fc='#FBFBF9', ec='none', zorder=0))
    pt = 72 * (size_pt[0] / 72) / (x1 - x0)

    def fill(poly, **kw):
        if poly.is_empty:
            return
        for q in (poly.geoms if hasattr(poly, 'geoms') else [poly]):
            if q.geom_type == 'Polygon':
                ax.add_patch(MPoly(np.array(q.exterior.coords), closed=True, **kw))

    for p in g['green']:
        fill(p.intersection(win), fc='#DCEDCD', ec='none', zorder=1)
    for cas in (True, False):
        for ls, kind, name, oneway, wid in sorted(g['roads'], key=lambda r: WIDTH[r[1]]):
            q = ls.intersection(win.buffer(30))
            for part in (q.geoms if hasattr(q, 'geoms') else [q]):
                if part.is_empty or part.geom_type != 'LineString':
                    continue
                xy = np.array(part.coords)
                w = WIDTH[kind] * pt
                ax.plot(xy[:, 0], xy[:, 1], color='#9A9A9A' if cas else 'white', lw=w + (0.8 if cas else 0),
                        solid_capstyle='round', solid_joinstyle='round', zorder=2 if cas else 3)
    for ls in g['foot']:
        q = ls.intersection(win)
        for part in (q.geoms if hasattr(q, 'geoms') else [q]):
            if not part.is_empty and part.geom_type == 'LineString':
                xy = np.array(part.coords)
                ax.plot(xy[:, 0], xy[:, 1], color='#B4B4B4', lw=0.4, dashes=(2.0, 1.4), zorder=4)
    for poly, num in g['buildings']:
        q = poly.intersection(win)
        fill(q, fc='#D9D9D9', ec='#8C8C8C', lw=0.35, zorder=5)
        if labels and num and q.area > 150 and q.area > 0.6 * poly.area:
            r = poly.representative_point()
            ax.text(r.x, r.y, num, fontsize=5.0, ha='center', va='center', color='#333', zorder=6)
    fill(g['object'], fc='#F58220', ec='#B45309', lw=0.5, zorder=7)
    fill(g['site'], fc='none', ec='#2F5597', lw=1.2, zorder=8)
    for v in (RED_N, RED_S):
        xy = frame.l2w(np.c_[[-400, 400], [v, v]])
        ax.plot(xy[:, 0], xy[:, 1], color='#D8262C', lw=0.7, zorder=6)
    if streets:
        named = {}
        for ls, kind, name, oneway, wid in g['roads']:
            if kind in ('primary', 'tertiary') and name:
                q = ls.intersection(win.buffer(-15))
                if q.is_empty:
                    continue
                part = max(q.geoms, key=lambda z: z.length) if hasattr(q, 'geoms') else q
                if part.length > named.get(name, (0,))[0]:
                    named[name] = (part.length, part)
        for name, (L, part) in named.items():
            m = np.array(part.interpolate(0.5, normalized=True).coords[0])
            ax.text(m[0], m[1], name, fontsize=5.6 if 'дублёр' not in name else 4.8, rotation=25.2,
                    rotation_mode='anchor', ha='center', va='center', zorder=14, fontweight='medium', color='#222')
    for num, p, d in views:
        p = frame.l2w([p])[0]
        d = np.array(d, float); d /= np.linalg.norm(d)
        dw = frame.U * d[0] + frame.V * d[1]
        r = (x1 - x0) * 0.042
        for s in (-1, 1):
            a = np.arctan2(dw[1], dw[0]) + s * np.radians(22)
            ax.plot([p[0], p[0] + np.cos(a) * r * 1.9], [p[1], p[1] + np.sin(a) * r * 1.9], color='#C00000',
                    lw=0.8, zorder=15)
        ax.add_patch(plt.Rectangle((p[0] - r * 0.5, p[1] - r * 0.5), r, r, fc='#262626', ec='white', lw=0.4,
                                   zorder=16))
        ax.text(p[0], p[1], str(num), fontsize=6.0, color='white', ha='center', va='center', zorder=17,
                fontweight='bold')
    if north:
        ax.annotate('', xy=(x1 - (x1 - x0) * 0.06, y1 - (y1 - y0) * 0.05),
                    xytext=(x1 - (x1 - x0) * 0.06, y1 - (y1 - y0) * 0.16),
                    arrowprops=dict(arrowstyle='-|>', lw=0.8, color='#111', mutation_scale=8), zorder=18)
        ax.text(x1 - (x1 - x0) * 0.06, y1 - (y1 - y0) * 0.035, 'С', fontsize=6, ha='center', va='bottom',
                fontweight='bold', zorder=18)
    if scalebar:
        step = 50 if scale >= 2000 else 20
        bx, by = x0 + (x1 - x0) * 0.04, y0 + (y1 - y0) * 0.035
        hh = (y1 - y0) * 0.011
        for i in range(2):
            ax.add_patch(plt.Rectangle((bx + i * step, by), step, hh, fc='#111' if i == 0 else 'white', ec='#111',
                                       lw=0.4, zorder=18))
        for i in range(3):
            ax.text(bx + i * step, by + hh * 2.2, str(i * step), fontsize=4.2, ha='center', va='bottom', zorder=18)
        ax.text(bx + 2 * step + (x1 - x0) * 0.012, by + hh * 0.5, 'м', fontsize=4.2, va='center', zorder=18)
        ax.text(bx, by - hh * 1.2, 'М 1:%d' % scale, fontsize=4.6, va='top', fontweight='semibold', zorder=18)
    fig.savefig(out_png, dpi=dpi)
    plt.close(fig)
