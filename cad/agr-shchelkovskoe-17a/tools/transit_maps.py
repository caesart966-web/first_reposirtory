"""Транспортный раздел АГР, части 5 и 6: схемы обслуживания территории наземным городским пассажирским
транспортом и скоростным внеуличным транспортом, М 1:25000, по данным OpenStreetMap.

    python3 transit_maps.py <папка выгрузок .osm> <папка полных отношений маршрутов> <areas.json> <выход>

Пишет ngpt.png, rail.png (рамка карты 632 × 600 пт, 300 dpi) и transit.json — остановки, маршруты,
пешеходные расстояния от главного входа до остановок и входов на станции (по сети пешеходных путей OSM).
Координаты — МСК (osm_base), север вверху.
"""
import glob
import json
import os
import pickle
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MPoly, Circle
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import linemerge, unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import frame  # noqa: E402
import osm_base  # noqa: E402

for f_ in ('Montserrat-Regular.ttf', 'Montserrat-Medium.ttf', 'Montserrat-SemiBold.ttf', 'Montserrat-Bold.ttf'):
    p_ = '/usr/share/fonts/truetype/montserrat/' + f_
    if os.path.exists(p_):
        fm.fontManager.addfont(p_)
plt.rcParams['font.family'] = 'Montserrat'

SCALE = 25000
MPP = SCALE * 0.3528 / 1000                 # метров на пункт листа: 8,82
SIZE_PT = (632.0, 600.0)
ENTRANCE = (4.3, -1.6)                      # главный вход в координатах модели (как в walk_rail.py)
WALK_KMH = 4.5                              # скорость пешехода для зоны 7,5 минуты
GREEN = {'park', 'garden', 'grass', 'forest', 'wood', 'recreation_ground', 'village_green', 'meadow', 'scrub',
         'cemetery', 'nature_reserve'}
ROADS = {'motorway': (2.6, 3.4, 6), 'trunk': (2.4, 3.2, 6), 'primary': (1.9, 2.6, 5), 'secondary': (1.5, 2.1, 4),
         'tertiary': (1.1, 1.6, 3), 'primary_link': (0.8, 1.2, 3), 'secondary_link': (0.8, 1.2, 3),
         'tertiary_link': (0.7, 1.1, 3), 'trunk_link': (0.9, 1.3, 3), 'unclassified': (0.6, 0.9, 2),
         'residential': (0.5, 0.8, 2)}
FOOT = {'footway', 'path', 'pedestrian', 'steps', 'living_street', 'residential', 'service', 'unclassified',
        'tertiary', 'secondary', 'primary', 'crossing', 'corridor', 'track', 'cycleway', 'platform',
        'tertiary_link', 'secondary_link', 'primary_link'}
BG = '#F6F4F0'
HALO = [pe.withStroke(linewidth=1.8, foreground='white')]
LINES = {'1': ('#E42313', 'Сокольническая линия'), '3': ('#0072BA', 'Арбатско-Покровская линия'),
         '14': ('#E42313', 'Московское центральное кольцо')}


# --- данные -----------------------------------------------------------------------------------------------------
def load(folder):
    cache = os.path.join(folder, '_cache.pkl')
    if os.path.exists(cache):
        return pickle.load(open(cache, 'rb'))
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
    D = dict(nodes=nodes, ways=ways, rels=rels, ntags=ntags)
    pickle.dump(D, open(cache, 'wb'))
    return D


def line_of(nodes, nds):
    pts = [nodes[i] for i in nds if i in nodes]
    return pts if len(pts) >= 2 else None


def routes(folder):
    """Маршруты НГПТ из полных отношений: номер, вид, пути, остановки (платформы и stop)."""
    out = []
    for p in sorted(glob.glob(os.path.join(folder, 'r_*.osm'))):
        r = ET.parse(p).getroot()
        nodes = {n.get('id'): osm_base.to_msk(float(n.get('lon')), float(n.get('lat'))) for n in r.iter('node')}
        ntags = {n.get('id'): {k.get('k'): k.get('v') for k in n.findall('tag')} for n in r.iter('node')}
        ways = {w.get('id'): [nd.get('ref') for nd in w.findall('nd')] for w in r.iter('way')}
        rid = os.path.basename(p)[2:-4]
        rel = [x for x in r.iter('relation') if x.get('id') == rid][0]
        t = {k.get('k'): k.get('v') for k in rel.findall('tag')}
        wl, st = [], []
        for m in rel.findall('member'):
            if m.get('type') == 'way' and m.get('ref') in ways and not (m.get('role') or '').startswith('platform'):
                pts = line_of(nodes, ways[m.get('ref')])
                if pts:
                    wl.append((m.get('ref'), pts))
            elif m.get('type') == 'node' and (m.get('role') or '').startswith('platform') and m.get('ref') in nodes:
                st.append((ntags[m.get('ref')].get('name'), nodes[m.get('ref')]))
        out.append(dict(id=rid, ref=t.get('ref'), kind=t.get('route'), name=t.get('name'), ways=wl, stops=st))
    return out


# --- пешеходная сеть ------------------------------------------------------------------------------------------
def foot_graph(D):
    nodes, G = D['nodes'], nx.Graph()
    for nds, t in D['ways'].values():
        hw = t.get('highway')
        if hw not in FOOT and t.get('foot') not in ('yes', 'designated'):
            continue
        if t.get('foot') == 'no' or (t.get('access') == 'private' and t.get('foot') != 'yes'):
            continue
        for a, b in zip(nds, nds[1:]):
            if a in nodes and b in nodes:
                G.add_edge(a, b, w=float(np.hypot(*(np.array(nodes[a]) - nodes[b]))))
    ids = list(G.nodes)
    return G, ids, np.array([D['nodes'][i] for i in ids])


def snap(ids, P, xy):
    d = np.hypot(*(P - np.asarray(xy)).T)
    j = int(np.argmin(d))
    return ids[j], float(d[j])


# --- основа ----------------------------------------------------------------------------------------------------
def base(ax, D, view):
    nodes = D['nodes']

    def fill(geom, **kw):
        geom = geom.intersection(view.buffer(50))
        for g in (geom.geoms if hasattr(geom, 'geoms') else [geom]):
            if g.geom_type == 'Polygon' and g.area > 50:
                ax.add_patch(MPoly(np.array(g.exterior.coords), closed=True, **kw))

    for nds, t in D['ways'].values():
        if len(nds) < 4 or nds[0] != nds[-1]:
            continue
        lu, le, na = t.get('landuse'), t.get('leisure'), t.get('natural')
        if not (lu in GREEN or le in GREEN or na in GREEN or na == 'water' or lu in ('industrial', 'railway')
                or t.get('building')):
            continue
        pts = line_of(nodes, nds)
        if not pts or len(pts) < 4:
            continue
        poly = Polygon(pts)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if not poly.intersects(view):
            continue
        if t.get('building'):
            if poly.area > 400:
                fill(poly, fc='#E3DFD8', ec='none', zorder=1.6)
        elif na == 'water':
            fill(poly, fc='#BBD8EC', ec='none', zorder=1.4)
        elif lu in ('industrial', 'railway'):
            fill(poly, fc='#ECE9EB', ec='none', zorder=1.0)
        else:
            fill(poly, fc='#DCEBCF', ec='none', zorder=1.2)
    roads = []
    for nds, t in D['ways'].values():
        hw = t.get('highway')
        if hw in ROADS and t.get('area') != 'yes':
            pts = line_of(nodes, nds)
            if pts and LineString(pts).intersects(view):
                roads.append((ROADS[hw], np.array(pts), t))
        elif t.get('railway') == 'rail' and t.get('service') is None and t.get('tunnel') != 'yes':
            pts = line_of(nodes, nds)
            if pts and LineString(pts).intersects(view):
                xy = np.array(pts)
                ax.plot(xy[:, 0], xy[:, 1], color='#A8A8A8', lw=0.9, zorder=3.2, solid_capstyle='butt')
                ax.plot(xy[:, 0], xy[:, 1], color='white', lw=0.4, zorder=3.3, dashes=(3, 3))
    for (fw, cw, z), xy, t in sorted(roads, key=lambda r: r[0][2]):
        if t.get('tunnel') == 'yes':
            continue
        ax.plot(xy[:, 0], xy[:, 1], color='#CFC9BF', lw=cw, zorder=3 + z * 0.01, solid_capstyle='round')
        ax.plot(xy[:, 0], xy[:, 1], color='white' if z < 5 else '#FFF4D6', lw=fw, zorder=3.5 + z * 0.01,
                solid_capstyle='round')
    return roads


def street_labels(ax, roads, view, names, size=5.4):
    """Подписи выбранных улиц по самому длинному прямому участку в пределах рамки."""
    done = set()
    segs = defaultdict(list)
    for _, xy, t in roads:
        nm = t.get('name')
        if nm in names:
            part = LineString(xy).intersection(view.buffer(-300))
            for g in (part.geoms if hasattr(part, 'geoms') else [part]):
                if g.geom_type == 'LineString' and g.length > 0:
                    segs[nm].append(g)
    for nm, gs in segs.items():
        merged = linemerge(unary_union(gs))
        g = max(merged.geoms, key=lambda q: q.length) if hasattr(merged, 'geoms') else merged
        if g.length < 350 or nm in done:
            continue
        m = g.interpolate(0.5, normalized=True)
        a, b = g.interpolate(max(0, g.project(m) - 60)), g.interpolate(min(g.length, g.project(m) + 60))
        ang = np.degrees(np.arctan2(b.y - a.y, b.x - a.x))
        ang = ang - 180 if ang > 90 else ang + 180 if ang < -90 else ang
        ax.text(m.x, m.y, names[nm], fontsize=size, rotation=ang, rotation_mode='anchor', ha='center',
                va='center', color='#5A544C', zorder=12, path_effects=HALO)
        done.add(nm)


def frame_fig(centre):
    W, H = SIZE_PT[0] * MPP, SIZE_PT[1] * MPP
    X0, Y0 = centre[0] - W / 2, centre[1] - H / 2
    fig = plt.figure(figsize=(SIZE_PT[0] / 72, SIZE_PT[1] / 72), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(X0, X0 + W); ax.set_ylim(Y0, Y0 + H); ax.set_aspect('equal'); ax.axis('off')
    ax.add_patch(plt.Rectangle((X0, Y0), W, H, fc=BG, ec='none', zorder=0))
    return fig, ax, box(X0, Y0, X0 + W, Y0 + H), (X0, Y0, W, H)


def furniture(ax, ext, site_poly):
    X0, Y0, W, H = ext
    ax.add_patch(MPoly(np.array(site_poly.exterior.coords), closed=True, fc='#FFFF00', ec='#FF0000', lw=1.0,
                       zorder=30))
    c = site_poly.centroid
    ax.add_patch(Circle((c.x, c.y), 9 * MPP, fc='none', ec='#C00000', lw=1.1, zorder=30, ls=(0, (3, 2))))
    nx_, ny_ = X0 + W - 14 * MPP, Y0 + H - 40 * MPP
    ax.annotate('', xy=(nx_, ny_ + 22 * MPP), xytext=(nx_, ny_),
                arrowprops=dict(arrowstyle='-|>', lw=1.0, color='#111', mutation_scale=9), zorder=40)
    ax.text(nx_, ny_ + 29 * MPP, 'С', fontsize=7, ha='center', va='center', fontweight='bold', zorder=40,
            path_effects=HALO)
    bx, by, step = X0 + 14 * MPP, Y0 + 14 * MPP, 500.0
    for i in range(2):
        ax.add_patch(plt.Rectangle((bx + i * step, by), step, 3 * MPP, fc='#111' if i == 0 else 'white', ec='#111',
                                   lw=0.5, zorder=40))
    for k in range(3):
        ax.text(bx + k * step, by + 5 * MPP, str(int(k * step)), fontsize=5, ha='center', va='bottom', zorder=40,
                path_effects=HALO)
    ax.text(bx + 2 * step + 5 * MPP, by + 1.5 * MPP, 'м', fontsize=5, va='center', zorder=40, path_effects=HALO)
    ax.text(X0 + W - 8 * MPP, Y0 + 8 * MPP, 'М 1:25000', fontsize=5.5, ha='right', va='bottom', zorder=40,
            path_effects=HALO)


STREETS = {'Щёлковское шоссе': 'Щёлковское ш.', 'Амурская улица': 'Амурская ул.',
           'Сиреневый бульвар': 'Сиреневый б-р', 'Монтажная улица': 'Монтажная ул.',
           'Байкальская улица': 'Байкальская ул.', 'Уральская улица': 'Уральская ул.',
           'Открытое шоссе': 'Открытое ш.', 'Большая Черкизовская улица': 'Б. Черкизовская ул.',
           'Первомайская улица': 'Первомайская ул.', 'Хабаровская улица': 'Хабаровская ул.',
           'Курганская улица': 'Курганская ул.', 'Иркутская улица': 'Иркутская ул.',
           'Измайловский проспект': 'Измайловский пр-т', 'Северо-Восточная хорда': 'СВХ',
           'Тагильская улица': 'Тагильская ул.', 'Байкальская': 'Байкальская ул.'}


# --- часть 5: НГПТ -------------------------------------------------------------------------------------------
def map_ngpt(D, R, site, entr, G, ids, P, out_png):
    c = np.array(site.centroid.coords[0])
    fig, ax, view, ext = frame_fig(c)
    roads = base(ax, D, view)
    # сеть маршрутов: путь -> набор номеров
    wref, wgeom = defaultdict(set), {}
    for r in R:
        for wid, pts in r['ways']:
            wref[wid].add(r['ref'])
            wgeom[wid] = pts
    for wid, refs in wref.items():
        xy = np.array(wgeom[wid])
        lw = 1.0 + 0.22 * min(len(refs), 12)
        ax.plot(xy[:, 0], xy[:, 1], color='#1F6FD1', lw=lw, alpha=0.85, zorder=8, solid_capstyle='round',
                solid_joinstyle='round')
    # остановки у объекта и зона 7,5 минуты пешком от них
    near = {}
    for r in R:
        for nm, xy in r['stops']:
            d = float(np.hypot(*(np.array(xy) - entr)))
            if d < 650:
                near.setdefault(nm, []).append((xy, r['ref']))
    reach = 7.5 / 60 * WALK_KMH * 1000
    zone_pts = []
    stops_out = []
    for nm, lst in near.items():
        xys = {tuple(np.round(xy, 1)) for xy, _ in lst}
        refs = sorted({rf for _, rf in lst}, key=lambda s: (len(s), s))
        for xy in xys:
            src, d0 = snap(ids, P, xy)
            L = nx.single_source_dijkstra_path_length(G, src, cutoff=reach, weight='w')
            zone_pts += [Point(D['nodes'][k]).buffer(max(reach - v, 0) * 0.25 + 25) for k, v in L.items()]
        stops_out.append(dict(name=nm, points=[list(x) for x in xys], routes=refs))
    zone = unary_union(zone_pts).buffer(30).buffer(-30)
    for g in (zone.geoms if hasattr(zone, 'geoms') else [zone]):
        if g.area > 1000:
            ax.add_patch(MPoly(np.array(g.exterior.coords), closed=True, fc=(0.25, 0.42, 0.85, 0.12),
                               ec='#3D63C9', lw=0.6, zorder=6))
    # пешеходные пути от входа до ближайшей остановки каждого направления
    src, d_in = snap(ids, P, entr)
    L, paths = nx.single_source_dijkstra(G, src, weight='w')
    for s in stops_out:
        best = None
        for xy in s['points']:
            k, dd = snap(ids, P, xy)
            if k in L and (best is None or L[k] + dd < best[0]):
                best = (L[k] + dd + d_in, k, xy)
        s['walk_m'] = round(best[0]) if best else None
        s['line_m'] = round(min(float(np.hypot(*(np.array(xy) - entr))) for xy in s['points']))
        if best and best[0] < 400:
            pth = np.array([D['nodes'][k] for k in paths[best[1]]])
            ax.plot(pth[:, 0], pth[:, 1], color='#00963F', lw=1.1, zorder=9, dashes=(2, 1.2))
    for s in stops_out:
        for xy in s['points']:
            ax.add_patch(Circle(xy, 2.6 * MPP, fc='#111', ec='white', lw=0.5, zorder=20))
    # подписи остановок
    lab = {'Калошино': (70, -50, 'left'), 'Сиреневый сад': (-70, -55, 'right'),
           'Тагильская улица': (-40, 60, 'right')}
    stop_boxes = []
    for s in stops_out:
        if s['name'] not in lab:
            continue
        dx, dy, ha = lab[s['name']]
        xy = np.mean(np.array(s['points']), axis=0)
        tx, ty = xy[0] + dx * MPP / 3, xy[1] + dy * MPP / 3
        t_ = '«%s»' % s['name']
        w = len(t_) * 5.6 * 0.6 * MPP
        stop_boxes.append(box(tx - (w if ha == 'right' else 0), ty - 5 * MPP, tx + (w if ha == 'left' else 0),
                              ty + 5 * MPP).buffer(4 * MPP))
        ax.annotate(t_, xy=xy, xytext=(tx, ty), fontsize=5.6, ha=ha, va='center', fontweight='semibold',
                    color='#111', zorder=25, path_effects=HALO, arrowprops=dict(arrowstyle='-', lw=0.4, color='#333'))
    # номера маршрутов на участках сети с одинаковым набором маршрутов: без наложений, рядом с объектом
    def tbox(x, y, lines, size, ha='center'):
        w = max(len(q) for q in lines) * size * 0.56 * MPP + 4 * MPP
        h = len(lines) * size * 1.25 * MPP + 3 * MPP
        x0 = x - w / 2 if ha == 'center' else x if ha == 'left' else x - w
        return box(x0, y - h / 2, x0 + w, y + h / 2)
    taken = [Point(c).buffer(14 * MPP)] + [b_ for b_ in stop_boxes]
    groups = defaultdict(list)
    for wid, refs in wref.items():
        groups[tuple(sorted(refs, key=lambda q: (len(q), q)))].append(LineString(wgeom[wid]))
    for refs, ls in sorted(groups.items(), key=lambda g: -len(g[0])):
        u = unary_union(ls)
        if u.geom_type == 'MultiLineString':
            u = linemerge(u)
        parts = [g for g in (u.geoms if hasattr(u, 'geoms') else [u]) if g.geom_type == 'LineString']
        parts = [g.intersection(view.buffer(-350)) for g in parts]
        parts = [g for g in parts if g.geom_type == 'LineString' and g.length > 250 and g.distance(Point(c)) < 1700]
        if not parts:
            continue
        lines = [', '.join(refs[i:i + 7]) for i in range(0, len(refs), 7)]
        done = False
        for g in sorted(parts, key=lambda q: -q.length):
            for frac in (0.5, 0.35, 0.65, 0.2, 0.8):
                m = g.interpolate(frac, normalized=True)
                bx_ = tbox(m.x, m.y, lines, 4.8)
                if not any(bx_.intersects(q) for q in taken):
                    taken.append(bx_.buffer(6 * MPP))
                    ax.text(m.x, m.y, '\n'.join(lines), fontsize=4.8, ha='center', va='center', color='#1F4FA0',
                            fontweight='semibold', zorder=27, linespacing=1.1,
                            bbox=dict(boxstyle='round,pad=0.25', fc='white', ec='#1F6FD1', lw=0.5))
                    done = True
                    break
            if done:
                break
    street_labels(ax, roads, view, STREETS)
    furniture(ax, ext, site)
    fig.savefig(out_png, dpi=300, facecolor='white')
    plt.close(fig)
    return stops_out


# --- часть 6: внеуличный транспорт ----------------------------------------------------------------------------
def map_rail(D, site, entr, G, ids, P, out_png):
    nodes, c = D['nodes'], np.array(site.centroid.coords[0])
    fig, ax, view, ext = frame_fig(c)
    roads = base(ax, D, view)
    # линии метро и МЦК по отношениям маршрутов
    drawn = set()
    for mem, t in D['rels'].values():
        if t.get('route') not in ('subway', 'train') or t.get('ref') not in LINES:
            continue
        if t.get('route') == 'train' and 'Кольцо' not in (t.get('name') or ''):
            continue
        col = LINES[t['ref']][0]
        for typ, ref, role in mem:
            if typ != 'way' or ref not in D['ways'] or (ref, t['ref']) in drawn:
                continue
            nds, wt = D['ways'][ref]
            if wt.get('railway') not in ('subway', 'rail', 'light_rail'):
                continue
            pts = line_of(nodes, nds)
            if not pts:
                continue
            drawn.add((ref, t['ref']))
            xy = np.array(pts)
            if t['ref'] == '14':
                ax.plot(xy[:, 0], xy[:, 1], color=col, lw=3.0, zorder=10, solid_capstyle='butt')
                ax.plot(xy[:, 0], xy[:, 1], color='white', lw=1.4, zorder=10.1, solid_capstyle='butt')
            else:
                ax.plot(xy[:, 0], xy[:, 1], color=col, lw=2.2, zorder=10, alpha=0.9,
                        dashes=(4, 1.5) if wt.get('tunnel') == 'yes' or wt.get('layer', '0').startswith('-')
                        else (None, None))
    # станции и входы
    stations, entrances = [], []
    for nid, t in D['ntags'].items():
        xy = nodes[nid]
        if not view.contains(Point(xy)):
            continue
        if t.get('railway') in ('station', 'halt') and (t.get('station') == 'subway' or t.get('network') == 'МЦК'):
            kind = 'М' if t.get('station') == 'subway' else 'МЦК'
            line = '1' if t.get('colour') == 'red' else '3' if t.get('colour') == 'blue' else '14'
            stations.append(dict(name=t.get('name'), kind=kind, line=line, xy=list(xy)))
        elif t.get('railway') in ('subway_entrance', 'train_station_entrance'):
            entrances.append((nid, xy, t))
    # пешеходные расстояния от главного входа
    src, d_in = snap(ids, P, entr)
    L, paths = nx.single_source_dijkstra(G, src, weight='w')
    for s in stations:
        best = None
        want = 'subway_entrance' if s['kind'] == 'М' else 'train_station_entrance'
        for nid, xy, t in entrances:
            if t.get('railway') != want or np.hypot(*(np.array(xy) - s['xy'])) > 400:
                continue
            k, dd = snap(ids, P, xy)
            if dd < 40 and k in L and (best is None or L[k] + dd < best[0]):
                best = (L[k] + dd + d_in, k, t.get('ref'))
        if best is None:
            k, dd = snap(ids, P, s['xy'])
            best = (L.get(k, np.inf) + dd + d_in, k, None)
        s['walk_m'] = round(best[0]) if np.isfinite(best[0]) else None
        s['entrance'] = best[2]
        s['line_m'] = round(float(np.hypot(*(np.array(s['xy']) - entr))))
        s['_node'] = best[1]
    near = min((s for s in stations if s['walk_m']), key=lambda s: s['walk_m'])
    pth = np.array([nodes[k] for k in paths[near['_node']]])
    ax.plot(pth[:, 0], pth[:, 1], color='#00963F', lw=1.4, zorder=12, dashes=(2.5, 1.2))
    m = pth[int(len(pth) * 0.62)]
    ax.text(m[0], m[1] + 25, '%d м' % (round(near['walk_m'] / 10) * 10), fontsize=5.8, color='#00963F',
            fontweight='bold', ha='center', va='bottom', zorder=26, path_effects=HALO)
    # зоны пешеходной доступности по 945-ПП (прил. 6): 1200 и 2200 м
    for r_, lab in ((1200, '1200 м'), (2200, '2200 м')):
        ax.add_patch(Circle(entr, r_, fc='none', ec='#7A4FB5', lw=0.8, zorder=7, ls=(0, (5, 3))))
        ax.text(entr[0] + r_ * 0.71, entr[1] + r_ * 0.71, lab, fontsize=5.4, color='#7A4FB5', zorder=26,
                path_effects=HALO, ha='left', va='bottom')
    seen = {}
    for s in stations:
        key = (s['name'], s['kind'])
        if key in seen:
            continue
        seen[key] = s
        xy = np.array(s['xy'])
        if s['kind'] == 'М':
            ax.add_patch(Circle(xy, 6.0 * MPP, fc=LINES[s['line']][0], ec='white', lw=0.8, zorder=22))
            ax.text(xy[0], xy[1] - 0.3 * MPP, 'М', fontsize=6.0, color='white', ha='center', va='center',
                    fontweight='bold', zorder=23)
        else:
            ax.add_patch(Circle(xy, 6.0 * MPP, fc='white', ec='#E42313', lw=1.4, zorder=22))
            ax.text(xy[0], xy[1] - 0.2 * MPP, 'МЦК', fontsize=3.2, color='#E42313', ha='center', va='center',
                    fontweight='bold', zorder=23)
    for (nm, kind), s in seen.items():
        xy = np.array(s['xy'])
        off = LABEL_OFF.get((nm, kind), (9, 6, 'left'))
        ax.text(xy[0] + off[0] * MPP, xy[1] + off[1] * MPP, nm, fontsize=5.8, ha=off[2], va='center',
                fontweight='semibold', color='#222', zorder=24, path_effects=HALO)
    street_labels(ax, roads, view, STREETS)
    furniture(ax, ext, site)
    fig.savefig(out_png, dpi=300, facecolor='white')
    plt.close(fig)
    for s in stations:
        s.pop('_node', None)
    return stations


LABEL_OFF = {('Бульвар Рокоссовского', 'М'): (9, -8, 'left'), ('Бульвар Рокоссовского', 'МЦК'): (-9, 8, 'right'),
             ('Черкизовская', 'М'): (-9, -9, 'right'), ('Локомотив', 'МЦК'): (9, 9, 'left'),
             ('Измайлово', 'МЦК'): (-9, 0, 'right'), ('Партизанская', 'М'): (9, 0, 'left'),
             ('Измайловская', 'М'): (9, 0, 'left'), ('Первомайская', 'М'): (9, 0, 'left'),
             ('Щёлковская', 'М'): (9, 6, 'left')}


def main(folder, rfolder, areas_json, outdir):
    os.makedirs(outdir, exist_ok=True)
    D = load(folder)
    R = routes(rfolder)
    areas = json.load(open(areas_json))
    site = Polygon(np.array(areas['site_world']) / 1000)
    entr = frame.l2w(np.array([ENTRANCE]))[0]
    G, ids, P = foot_graph(D)
    stops = map_ngpt(D, R, site, entr, G, ids, P, os.path.join(outdir, 'ngpt.png'))
    stations = map_rail(D, site, entr, G, ids, P, os.path.join(outdir, 'rail.png'))
    rr = sorted({(r['ref'], r['kind']) for r in R}, key=lambda x: (len(x[0]), x[0]))
    names = {}
    for r in R:
        names.setdefault(r['ref'], r['name'])
    json.dump(dict(stops=stops, stations=stations, routes=[dict(ref=a, kind=b, name=names[a]) for a, b in rr]),
              open(os.path.join(outdir, 'transit.json'), 'w'), ensure_ascii=False, indent=1)
    for s in stops:
        print('остановка', s['name'], s['walk_m'], 'м пешком', s['routes'])
    for s in sorted(stations, key=lambda s: s['walk_m'] or 1e9):
        print(s['kind'], s['name'], s['walk_m'], 'м пешком, вход', s['entrance'], s['line_m'], 'м по прямой')


if __name__ == '__main__':
    main(*sys.argv[1:5])
