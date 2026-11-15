"""Фрагмент схемы расположения в районе (лист 2 буклета) по данным OpenStreetMap.

    python3 district_map.py <папка с выгрузками .osm> <куда.png>

В папке — выгрузки участков карты (t*.osm) и полные отношения границ районов (rel_*.osm).
Координаты — МСК (osm_base), север вверху. Район проектирования — красной границей,
участок — жёлтым с красным контуром, станции метро и МЦК — значками с названиями.
"""
import glob
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
from matplotlib.patches import Polygon as MPoly, Circle
from shapely.geometry import LineString, Polygon, box, Point
from shapely.ops import linemerge, polygonize, unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import osm_base  # noqa: E402

for f_ in ('Montserrat-Regular.ttf', 'Montserrat-Medium.ttf', 'Montserrat-SemiBold.ttf', 'Montserrat-Bold.ttf'):
    p = '/usr/share/fonts/truetype/montserrat/' + f_
    if os.path.exists(p):
        fm.fontManager.addfont(p)
plt.rcParams['font.family'] = 'Montserrat'

SIZE_PT = (351.6, 412.8)
MPP = 6.6                                   # метров на пункт листа
GREEN = {'park', 'garden', 'grass', 'forest', 'wood', 'recreation_ground', 'village_green', 'meadow', 'scrub',
         'cemetery', 'nature_reserve', 'playground', 'pitch'}
ROADS = {  # ширина заливки, ширина обводки (пт), слой
    'motorway': (3.6, 4.6, 6), 'trunk': (3.4, 4.4, 6), 'primary': (2.8, 3.7, 5), 'secondary': (2.2, 3.0, 4),
    'tertiary': (1.6, 2.3, 3), 'motorway_link': (1.4, 2.0, 3), 'trunk_link': (1.4, 2.0, 3),
    'primary_link': (1.3, 1.9, 3), 'secondary_link': (1.2, 1.8, 3), 'tertiary_link': (1.1, 1.6, 3),
    'unclassified': (1.0, 1.5, 2), 'residential': (1.0, 1.5, 2), 'living_street': (0.8, 1.2, 2),
    'service': (0.45, 0.0, 1),
}


def load(folder):
    nodes, ways, rels, ntags = {}, {}, {}, {}
    for p in sorted(glob.glob(os.path.join(folder, '*.osm'))):
        r = ET.parse(p).getroot()
        for n in r.iter('node'):
            nodes[n.get('id')] = osm_base.to_msk(float(n.get('lon')), float(n.get('lat')))
            t = {k.get('k'): k.get('v') for k in n.findall('tag')}
            if t:
                ntags[n.get('id')] = t
        for w in r.iter('way'):
            ways[w.get('id')] = ([nd.get('ref') for nd in w.findall('nd')],
                                 {k.get('k'): k.get('v') for k in w.findall('tag')})
        for rel in r.iter('relation'):
            rels[rel.get('id')] = ([(m.get('type'), m.get('ref'), m.get('role')) for m in rel.findall('member')],
                                   {k.get('k'): k.get('v') for k in rel.findall('tag')})
    return nodes, ways, rels, ntags


def line_of(nodes, nds):
    pts = [nodes[i] for i in nds if i in nodes]
    return pts if len(pts) >= 2 else None


def rel_polygon(nodes, ways, members, role='outer'):
    lines = []
    for typ, ref, rl in members:
        if typ == 'way' and ref in ways and (rl or 'outer') == role:
            pts = line_of(nodes, ways[ref][0])
            if pts:
                lines.append(LineString(pts))
    if not lines:
        return None
    u = unary_union(lines)
    try:
        u = linemerge(u) if u.geom_type == 'MultiLineString' else u
    except ValueError:
        pass
    polys = list(polygonize(u))
    return unary_union(polys) if polys else None


def main(folder, out_png, areas_json=None):
    nodes, ways, rels, ntags = load(folder)
    A = json.load(open(areas_json or os.path.join(HERE, 'out_ifc2', 'areas.json')))
    site = Polygon(np.array(A['site_world']) / 1000)
    c = np.array(site.centroid.coords[0])
    centre = c + np.array([-560.0, 250.0])
    W, H = SIZE_PT[0] * MPP, SIZE_PT[1] * MPP
    X0, X1, Y0, Y1 = centre[0] - W / 2, centre[0] + W / 2, centre[1] - H / 2, centre[1] + H / 2
    view = box(X0, Y0, X1, Y1)

    fig = plt.figure(figsize=(SIZE_PT[0] / 72, SIZE_PT[1] / 72), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect('equal'); ax.axis('off')
    ax.add_patch(plt.Rectangle((X0, Y0), W, H, fc='#F4F2EE', ec='none', zorder=0))

    def fill(geom, **kw):
        if geom is None or geom.is_empty:
            return
        geom = geom.intersection(view.buffer(50))
        for g in (geom.geoms if hasattr(geom, 'geoms') else [geom]):
            if g.geom_type != 'Polygon' or g.area < 1:
                continue
            ax.add_patch(MPoly(np.array(g.exterior.coords), closed=True, **kw))
            for h in g.interiors:
                ax.add_patch(MPoly(np.array(h.coords), closed=True, fc='#F4F2EE', ec='none',
                                   zorder=kw.get('zorder', 1) + 0.001))

    # площадные объекты
    for wid, (nds, t) in ways.items():
        if len(nds) < 4 or nds[0] != nds[-1]:
            continue
        pts = line_of(nodes, nds)
        if not pts or len(pts) < 4:
            continue
        poly = Polygon(pts)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if not poly.intersects(view):
            continue
        lu, le, na = t.get('landuse'), t.get('leisure'), t.get('natural')
        if t.get('building'):
            fill(poly, fc='#DCD8D1', ec='#CEC8C0', lw=0.15, zorder=4)
        elif na == 'water' or t.get('waterway') == 'riverbank':
            fill(poly, fc='#BBD8EC', ec='none', zorder=2)
        elif lu in GREEN or le in GREEN or na in GREEN:
            fill(poly, fc='#D3E8C4', ec='none', zorder=1.5 if lu in ('grass',) else 1.2)
        elif lu in ('industrial', 'railway', 'garages', 'construction'):
            fill(poly, fc='#ECE8EA', ec='none', zorder=1.0)
        elif lu in ('residential', 'commercial', 'retail') or t.get('amenity') in ('school', 'kindergarten',
                                                                                     'hospital'):
            fill(poly, fc='#F0EDE8', ec='none', zorder=1.0)
    for rid, (mem, t) in rels.items():
        if t.get('type') != 'multipolygon':
            continue
        lu, le, na = t.get('landuse'), t.get('leisure'), t.get('natural')
        if not (lu in GREEN or le in GREEN or na in GREEN or na == 'water' or t.get('building')):
            continue
        poly = rel_polygon(nodes, ways, mem)
        if poly is None or not poly.intersects(view):
            continue
        holes = rel_polygon(nodes, ways, mem, 'inner')
        if holes is not None:
            poly = poly.difference(holes)
        if t.get('building'):
            fill(poly, fc='#DCD8D1', ec='#CEC8C0', lw=0.15, zorder=4)
        elif na == 'water':
            fill(poly, fc='#BBD8EC', ec='none', zorder=2)
        else:
            fill(poly, fc='#D3E8C4', ec='none', zorder=1.2)

    # район Гольяново и соседи
    districts = {}
    for rid, (mem, t) in rels.items():
        if t.get('boundary') == 'administrative' and t.get('admin_level') == '8':
            poly = rel_polygon(nodes, ways, mem)
            if poly is not None:
                districts[t.get('name', '').replace('район ', '')] = poly
    gol = districts.get('Гольяново')
    fill(gol, fc=(0.85, 0.1, 0.1, 0.07), ec='none', zorder=4.5)

    # дороги и железные дороги
    lines = []
    for wid, (nds, t) in ways.items():
        hw = t.get('highway')
        if hw in ROADS and t.get('area') != 'yes':
            pts = line_of(nodes, nds)
            if pts and LineString(pts).intersects(view):
                lines.append((ROADS[hw], LineString(pts), t))
        elif t.get('railway') in ('rail', 'light_rail') and t.get('service') is None and t.get('tunnel') != 'yes':
            pts = line_of(nodes, nds)
            if pts and LineString(pts).intersects(view):
                xy = np.array(pts)
                ax.plot(xy[:, 0], xy[:, 1], color='#9A9A9A', lw=1.1, zorder=5.2, solid_capstyle='butt')
                ax.plot(xy[:, 0], xy[:, 1], color='white', lw=0.5, zorder=5.3, dashes=(3, 3))
    for (fw, cw, z), ls, t in sorted(lines, key=lambda r: r[0][2]):
        xy = np.array(ls.coords)
        if t.get('tunnel') == 'yes':
            ax.plot(xy[:, 0], xy[:, 1], color='#C9C3BA', lw=fw * 0.6, zorder=5 + z * 0.01, dashes=(2, 1.5))
            continue
        if cw:
            ax.plot(xy[:, 0], xy[:, 1], color='#C2BCB2', lw=cw, zorder=5 + z * 0.01, solid_capstyle='round')
        ax.plot(xy[:, 0], xy[:, 1], color='#FFFFFF' if z < 5 else '#FFF6D9', lw=fw, zorder=5.5 + z * 0.01,
                solid_capstyle='round')

    # граница района
    if gol is not None:
        for g in (gol.geoms if hasattr(gol, 'geoms') else [gol]):
            xy = np.array(g.exterior.coords)
            ax.plot(xy[:, 0], xy[:, 1], color='#C00000', lw=2.0, zorder=8, solid_joinstyle='round')

    halo = [pe.withStroke(linewidth=1.6, foreground='white')]
    placed = []
    # станции рельсового каркаса
    st = {}
    for nid, t in ntags.items():
        if t.get('railway') == 'station' and t.get('station') == 'subway' or t.get('railway') == 'halt':
            st[t.get('name')] = (np.array(nodes[nid]), 'МЦК' if t.get('railway') == 'halt' else 'М')
    for nm, (xy, kind) in st.items():
        if not view.buffer(-80).contains(Point(xy)):
            continue
        placed.append(Point(xy).buffer(12 * MPP))
        if kind == 'М':
            placed.append(box(xy[0] - 75 * MPP, xy[1] - 17 * MPP, xy[0] - 6 * MPP, xy[1] - 7 * MPP))
            ax.add_patch(Circle(xy, 6.2 * MPP, fc='#D52B1E', ec='white', lw=0.8, zorder=14))
            ax.text(xy[0], xy[1] - 0.3 * MPP, 'М', fontsize=6.4, color='white', ha='center', va='center',
                    fontweight='bold', zorder=15)
            ax.text(xy[0] - 9 * MPP, xy[1] - 9 * MPP, 'Черкизовская' if 'Черкизовская' in nm else nm,
                    fontsize=6.0, ha='right', va='top', fontweight='semibold', color='#222', zorder=15,
                    path_effects=halo)
        else:
            q = xy + np.array([14, 10]) * MPP
            placed.append(box(q[0] - 7 * MPP, q[1] - 7 * MPP, q[0] + 60 * MPP, q[1] + 7 * MPP))
            ax.add_patch(Circle(q, 6.2 * MPP, fc='white', ec='#D52B1E', lw=1.4, zorder=14))
            ax.text(q[0], q[1] - 0.2 * MPP, 'МЦК', fontsize=3.4, color='#D52B1E', ha='center', va='center',
                    fontweight='bold', zorder=15)
            ax.text(q[0] + 9 * MPP, q[1] + 2 * MPP, nm, fontsize=6.0, ha='left', va='center',
                    fontweight='semibold', color='#222', zorder=15, path_effects=halo)

    # участок
    placed.append(Point(c).buffer(27 * MPP))
    ax.add_patch(Circle(c, 26 * MPP, fc='none', ec='#C00000', lw=1.0, zorder=16, ls=(0, (3, 2))))
    ax.add_patch(MPoly(np.array(site.exterior.coords), closed=True, fc='#FFFF00', ec='#FF0000', lw=1.0,
                       zorder=17))

    # подписи районов
    for nm, poly in districts.items():
        part = poly.intersection(view.buffer(-250))
        if part.is_empty or part.area < 2.5e5:
            continue
        if nm == 'Гольяново':
            gx, gy = c[0] - 330, c[1] + 640
            placed.append(box(gx - 50 * MPP, gy - 9 * MPP, gx + 50 * MPP, gy + 9 * MPP))
            ax.text(gx, gy, 'ГОЛЬЯНОВО', fontsize=11, color='#C00000', fontweight='bold',
                    ha='center', va='center', zorder=13, path_effects=[pe.withStroke(linewidth=2.2,
                                                                                    foreground='white')])
        else:
            p = part.representative_point()
            placed.append(box(p.x - len(nm) * 2.2 * MPP, p.y - 5 * MPP, p.x + len(nm) * 2.2 * MPP, p.y + 5 * MPP))
            ax.text(p.x, p.y, nm.upper(), fontsize=6.2, color='#8A847C', fontweight='semibold', ha='center',
                    va='center', zorder=13, path_effects=halo)

    # названия улиц: самый длинный отрезок с одним направлением
    named = {}
    for (fw, cw, z), ls, t in lines:
        nm = t.get('name')
        if not nm or z < 2 or t.get('tunnel') == 'yes':
            continue
        part = ls.intersection(view.buffer(-120))
        for g in (part.geoms if hasattr(part, 'geoms') else [part]):
            if g.geom_type != 'LineString':
                continue
            named.setdefault(nm, []).append(g)
    SHORT = {'улица': 'ул.', 'проезд': 'пр.', 'бульвар': 'бульв.', 'переулок': 'пер.'}
    for nm, segs in sorted(named.items(), key=lambda kv: -max(s.length for s in kv[1])):
        u = unary_union(segs)
        merged = linemerge(u) if u.geom_type == 'MultiLineString' else u
        cand = merged.geoms if hasattr(merged, 'geoms') else [merged]
        best = max(cand, key=lambda g: g.length)
        txt = nm
        for a, b in SHORT.items():
            txt = txt.replace(a, b)
        size = 5.6 if 'шоссе' in nm else 5.0
        need = len(txt) * size * 0.56 * MPP
        if best.length < need * 1.05:
            continue
        for frac in (0.5, 0.35, 0.65, 0.25, 0.75):
            m = best.interpolate(frac, normalized=True)
            a = best.interpolate(max(0, best.project(m) - need / 2))
            b = best.interpolate(min(best.length, best.project(m) + need / 2))
            d = np.array(b.coords[0]) - np.array(a.coords[0])
            if np.linalg.norm(d) < need * 0.93:
                continue                                # изгиб — подпись не ляжет
            ang = np.degrees(np.arctan2(d[1], d[0]))
            if ang > 90:
                ang -= 180
            if ang < -90:
                ang += 180
            foot = LineString([a.coords[0], b.coords[0]]).buffer(size * 0.75 * MPP)
            if any(foot.intersects(p) for p in placed):
                continue
            placed.append(foot)
            ax.text(m.x, m.y, txt, fontsize=size, rotation=ang, rotation_mode='anchor', ha='center', va='center',
                    color='#4F4A44', zorder=12, path_effects=halo)
            break

    # север и масштаб
    nx_, ny_ = X1 - 16 * MPP, Y1 - 42 * MPP
    ax.annotate('', xy=(nx_, ny_ + 24 * MPP), xytext=(nx_, ny_),
                arrowprops=dict(arrowstyle='-|>', lw=1.1, color='#111', mutation_scale=10), zorder=20)
    ax.text(nx_, ny_ + 31 * MPP, 'С', fontsize=8, ha='center', va='center', fontweight='bold', zorder=20,
            path_effects=halo)
    bx, by = X0 + 14 * MPP, Y0 + 14 * MPP
    for i, (a, b) in enumerate(((0, 250), (250, 500))):
        ax.add_patch(plt.Rectangle((bx + a, by), b - a, 3.2 * MPP, fc='#111' if i == 0 else 'white', ec='#111',
                                   lw=0.6, zorder=20))
    for m in (0, 250, 500):
        ax.text(bx + m, by + 6 * MPP, str(m), fontsize=5.2, ha='center', va='bottom', zorder=20,
                path_effects=halo)
    ax.text(bx + 500 + 5 * MPP, by + 1.6 * MPP, 'м', fontsize=5.2, ha='left', va='center', zorder=20,
            path_effects=halo)
    fig.savefig(out_png, dpi=300, facecolor='white')
    plt.close(fig)
    print(out_png, 'станции:', [n for n in st], 'районы:', list(districts))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
