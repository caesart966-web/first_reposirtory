"""Ситуационный план и мини-схемы (точки съемки, точки обзора) для буклета АГР — по OpenStreetMap.

    python3 sit_map.py <папка .osm> <site.json> <ВПМ здания .fbx> <ВПМ .geojson> <папка вывода>

Участок — по ГПЗУ (site.json), контур здания — по ВПМ (вершины низа стен, +0,1…+0,2 м, выпуклая оболочка),
поставленный в точку вставки из geojson. Окружение — из открытой основы, север вверху.
"""
import json
import os
import sys
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MPoly, FancyArrow
from shapely.geometry import LineString, Polygon, box, MultiPoint
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'agr-shchelkovskoe-17a', 'tools'))
import osm_base  # noqa: E402
import fbxio  # noqa: E402

for f_ in ('Montserrat-Regular.ttf', 'Montserrat-Medium.ttf', 'Montserrat-SemiBold.ttf', 'Montserrat-Bold.ttf'):
    p = '/usr/share/fonts/truetype/montserrat/' + f_
    if os.path.exists(p):
        fm.fontManager.addfont(p)
plt.rcParams['font.family'] = 'Montserrat'
HALO = [pe.withStroke(linewidth=1.6, foreground='white')]
ROADS = {'primary': 2.6, 'secondary': 2.2, 'tertiary': 1.8, 'unclassified': 1.3, 'residential': 1.3,
         'living_street': 1.0, 'service': 0.7, 'trunk': 3.0, 'primary_link': 1.2, 'secondary_link': 1.2,
         'tertiary_link': 1.1}


def footprint(fbx, geojson):
    f = fbxio.Fbx(fbx)
    objs, conn = f.one('Objects'), f.one('Connections')
    byid = {k.props[0].value: k for k in objs.kids}
    pts = []
    for c in conn.kids:
        a, b = byid.get(c.props[1].value), byid.get(c.props[2].value)
        if a is None or b is None or a.name != 'Geometry' or b.name != 'Model':
            continue
        if not b.props[1].value.split('\x00')[0].endswith('_Main'):
            continue
        V = np.array(a.one('Vertices').props[0].value).reshape(-1, 3)
        sel = V[(V[:, 2] > 0.1) & (V[:, 2] < 0.2)]          # низ стен (над нулем, ниже — заглубление)
        pts.extend(sel[:, :2].tolist())
    hull = MultiPoint(pts).convex_hull
    x, y = json.load(open(geojson, encoding='utf-8'))['features'][0]['geometry']['coordinates']
    return Polygon(np.array(hull.exterior.coords) + np.array([x, y]))


def load(folder):
    nodes, ways = {}, []
    for fn in sorted(os.listdir(folder)):
        if not fn.endswith('.osm'):
            continue
        r = ET.parse(os.path.join(folder, fn)).getroot()
        for n in r.iter('node'):
            nodes[n.get('id')] = osm_base.to_msk(float(n.get('lon')), float(n.get('lat')))
        for w in r.iter('way'):
            ways.append(([nd.get('ref') for nd in w.findall('nd')], {t.get('k'): t.get('v') for t in w.findall('tag')}))
    return nodes, ways


def draw(folder, site, bld, out, centre, size_pt, scale, marks=(), labels=True, north=True, scalebar=True,
         dpi=300):
    nodes, ways = load(folder)
    mpp = scale * 0.3528 / 1000                     # метров на пункт
    W, H = size_pt[0] * mpp, size_pt[1] * mpp
    X0, Y0 = centre[0] - W / 2, centre[1] - H / 2
    view = box(X0, Y0, X0 + W, Y0 + H)
    fig = plt.figure(figsize=(size_pt[0] / 72, size_pt[1] / 72), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(X0, X0 + W); ax.set_ylim(Y0, Y0 + H); ax.set_aspect('equal'); ax.axis('off')
    ax.add_patch(plt.Rectangle((X0, Y0), W, H, fc='#F4F2EE', ec='none', zorder=0))
    roads = []
    for nds, t in ways:
        pts = [nodes[i] for i in nds if i in nodes]
        if len(pts) < 2:
            continue
        if nds[0] == nds[-1] and len(pts) >= 4:
            poly = Polygon(pts)
            if not poly.is_valid:
                poly = poly.buffer(0)
            if not poly.intersects(view):
                continue
            if t.get('building'):
                if poly.intersection(bld).area > 0.3 * poly.area:
                    continue                            # само здание в основе — рисуем по модели
                ax.add_patch(MPoly(np.array(poly.exterior.coords), fc='#D6D2CB', ec='#B9B3AA', lw=0.3, zorder=4))
            elif t.get('landuse') in ('grass', 'forest', 'meadow') or t.get('natural') in ('wood', 'scrub') \
                    or t.get('leisure') in ('park', 'garden'):
                ax.add_patch(MPoly(np.array(poly.exterior.coords), fc='#D9EACB', ec='none', zorder=1.2))
            elif t.get('amenity') == 'parking' or t.get('highway') in ('pedestrian',) or t.get('area') == 'yes':
                ax.add_patch(MPoly(np.array(poly.exterior.coords), fc='#ECEAE6', ec='#D8D3CC', lw=0.3, zorder=1.5))
        hw = t.get('highway')
        if hw in ROADS and t.get('area') != 'yes':
            ls = LineString(pts)
            if ls.intersects(view):
                roads.append((ls, ROADS[hw], t))
    for ls, w, t in sorted(roads, key=lambda r: r[1]):
        xy = np.array(ls.coords)
        lw = w * (2000 / scale) ** 0.85 * 2.2
        ax.plot(xy[:, 0], xy[:, 1], color='#CFC9C0', lw=lw + 0.9, zorder=5, solid_capstyle='round')
        ax.plot(xy[:, 0], xy[:, 1], color='white', lw=lw, zorder=5.1, solid_capstyle='round')
    ax.add_patch(MPoly(np.array(site.exterior.coords), fc='none', ec='#2F5597', lw=1.6, zorder=8))
    ax.add_patch(MPoly(np.array(bld.exterior.coords), fc='#F58220', ec='#B45309', lw=0.6, zorder=9))
    if labels:
        done = set()
        for ls, w, t in sorted(roads, key=lambda r: -r[0].length):
            nm = t.get('name')
            if not nm or nm in done:
                continue
            part = ls.intersection(view.buffer(-25 * mpp))
            if part.is_empty or part.length < 60 * mpp:
                continue
            g = max(part.geoms, key=lambda q: q.length) if hasattr(part, 'geoms') else part
            m = g.interpolate(0.5, normalized=True)
            a, b = g.interpolate(max(0, g.project(m) - 5)), g.interpolate(min(g.length, g.project(m) + 5))
            ang = np.degrees(np.arctan2(b.y - a.y, b.x - a.x))
            ang = ang - 180 if ang > 90 else ang + 180 if ang < -90 else ang
            txt = nm.replace('проезд', 'пр.').replace('улица', 'ул.')
            ax.text(m.x, m.y, txt, fontsize=5.2, rotation=ang, rotation_mode='anchor', ha='center', va='center',
                    color='#4F4A44', zorder=12, path_effects=HALO)
            done.add(nm)
    for mk in marks:                                   # точки съемки / обзора: ((x, y), угол°, текст)
        (x, y), angd, txt = mk
        r = 7 * mpp
        a = np.radians(angd)
        ax.add_patch(FancyArrow(x, y, np.cos(a) * 18 * mpp, np.sin(a) * 18 * mpp, width=2.2 * mpp,
                                head_width=8 * mpp, head_length=8 * mpp, color='#D7262C', zorder=15))
        ax.add_patch(plt.Circle((x, y), r, fc='#262626', ec='white', lw=0.8, zorder=16))
        ax.text(x, y, txt, fontsize=6.5, color='white', fontweight='bold', ha='center', va='center', zorder=17)
    if north:
        nx_, ny_ = X0 + W - 12 * mpp, Y0 + H - 34 * mpp
        ax.annotate('', xy=(nx_, ny_ + 20 * mpp), xytext=(nx_, ny_),
                    arrowprops=dict(arrowstyle='-|>', lw=1.0, color='#111', mutation_scale=9), zorder=20)
        ax.text(nx_, ny_ + 26 * mpp, 'С', fontsize=7, ha='center', va='center', fontweight='bold', zorder=20,
                path_effects=HALO)
    if scalebar:
        step = 20 if scale <= 2000 else 50
        bx, by = X0 + 12 * mpp, Y0 + 12 * mpp
        for i in range(2):
            ax.add_patch(plt.Rectangle((bx + i * step, by), step, 3 * mpp, fc='#111' if i == 0 else 'white',
                                       ec='#111', lw=0.5, zorder=20))
        for k in range(3):
            ax.text(bx + k * step, by + 5 * mpp, str(k * step), fontsize=5, ha='center', va='bottom', zorder=20,
                    path_effects=HALO)
        ax.text(bx + 2 * step + 4 * mpp, by + 1.5 * mpp, 'м', fontsize=5, va='center', zorder=20, path_effects=HALO)
    fig.savefig(out, dpi=dpi, facecolor='white')
    plt.close(fig)


def main(folder, site_json, fbx, geojson, outdir):
    s = json.load(open(site_json, encoding='utf-8'))
    site = Polygon(s['site'])
    bld = footprint(fbx, geojson)
    json.dump({'building': list(bld.exterior.coords), 'site': s['site']},
              open(os.path.join(outdir, 'footprint.json'), 'w'))
    c = np.array(site.centroid.coords[0])
    draw(folder, site, bld, os.path.join(outdir, 'situ.png'), c + np.array([0, -10]), (351.6, 412.8), 2000)
    print('площадь контура здания по ВПМ, м²:', round(bld.area, 1))
    return site, bld


if __name__ == '__main__':
    main(*sys.argv[1:6])
