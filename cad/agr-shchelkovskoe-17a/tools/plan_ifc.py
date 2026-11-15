"""Схема плана первого этажа по модели АР (разрез на высоте 1,0 м от пола).

    python3 plan_ifc.py <AR.ifc> <куда.png> <куда.json>

Стены, колонны, витражи, окна и двери режутся горизонтальной плоскостью; лестницы,
пандусы и крыльца ниже разреза показываются проекцией. Помещения окрашены по
функциональному назначению. Координаты — местные (u вдоль Щёлковского шоссе, v от него).
"""
import json
import os
import sys

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as ue
import ifcopenshell.util.placement as up
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MPoly, Circle
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import frame     # noqa: E402
import ifc_geom  # noqa: E402

for f_ in ('Montserrat-Regular.ttf', 'Montserrat-Medium.ttf', 'Montserrat-SemiBold.ttf', 'Montserrat-Bold.ttf'):
    p = '/usr/share/fonts/truetype/montserrat/' + f_
    if os.path.exists(p):
        fm.fontManager.addfont(p)
plt.rcParams['font.family'] = 'Montserrat'

FLOOR = 154.85
CUT = FLOOR + 1.0
AXIS_NAMES = {'З': 'И'}                       # по ГОСТ 21.101 буква З в маркировке осей не применяется
ZONES = {
    'trade': ('Торговый зал', '#DDEFF0'),
    'mop': ('Входная группа (тамбур)', '#F1F0E0'),
    'staff': ('Служебные и бытовые помещения', '#F8E4D6'),
    'store': ('Помещения приёмки и хранения товара', '#EFE8F5'),
    'tech': ('Технические помещения', '#DFDFDF'),
}
ROOM_ZONE = {'1': 'mop', '2': 'trade', '3': 'staff', '4': 'staff', '5': 'staff', '6': 'staff', '7': 'staff',
             '8': 'store', '9': 'store', '10': 'tech', '11': 'tech'}
ROOM_NAME = {'3': 'Помещение главной кассы'}


def local_poly(world_mm):
    return Polygon(frame.w2l(np.asarray(world_mm) / 1000.0))


def shapes(f, classes):
    s = ifcopenshell.geom.settings()
    s.set('use-world-coords', True)
    out = []
    for cls in classes:
        for e in f.by_type(cls):
            if not e.Representation:
                continue
            try:
                sh = ifcopenshell.geom.create_shape(s, e)
            except Exception:
                continue
            V = np.array(sh.geometry.verts).reshape(-1, 3)
            F = np.array(sh.geometry.faces).reshape(-1, 3)
            if V[:, 0].max() > 100000:          # мм -> м
                V = V / 1000.0
            out.append((cls, e, V, F))
    return out


def section(V, F, z):
    m = trimesh.Trimesh(vertices=V, faces=F, process=False)
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if sec is None:
        return None, []
    lines = []
    for ent in sec.entities:
        pts = sec.vertices[ent.points][:, :2]
        lines.append(frame.w2l(pts))
    try:
        planar, T = sec.to_2D()
        polys = []
        for p in planar.polygons_full:
            q = np.array(p.exterior.coords)
            q3 = np.c_[q, np.zeros(len(q)), np.ones(len(q))] @ T.T
            holes = []
            for h in p.interiors:
                hq = np.array(h.coords)
                hq3 = np.c_[hq, np.zeros(len(hq)), np.ones(len(hq))] @ T.T
                holes.append(frame.w2l(hq3[:, :2]))
            polys.append(Polygon(frame.w2l(q3[:, :2]), holes))
        return unary_union(polys) if polys else None, lines
    except Exception:
        return None, lines


def footprint(V, F):
    L = frame.w2l(V[:, :2])
    tris = [Polygon(L[t]) for t in F]
    tris = [t for t in tris if t.is_valid and t.area > 1e-6]
    return unary_union(tris) if tris else None


def draw(ifc_path, out_png, out_json, dpi=300, size=(10.08, 8.62)):
    f = ifcopenshell.open(ifc_path)
    S = ifc_geom.spaces(f)
    fig = plt.figure(figsize=size, dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_aspect('equal'); ax.axis('off')
    U0, U1, V0, V1 = -6.6, 28.4, -5.9, 34.0
    ax.set_xlim(U0, U1); ax.set_ylim(V0, V1)

    def fill(geom, **kw):
        if geom is None or geom.is_empty:
            return
        for g in (geom.geoms if hasattr(geom, 'geoms') else [geom]):
            if g.geom_type != 'Polygon':
                continue
            ax.add_patch(MPoly(np.array(g.exterior.coords), closed=True, **kw))
            for h in g.interiors:
                ax.add_patch(MPoly(np.array(h.coords), closed=True, fc='white', ec=kw.get('ec', 'none'),
                                   lw=kw.get('lw', 0), zorder=kw.get('zorder', 1) + 0.01))

    # помещения
    rooms = []
    for nm, d in S.items():
        num = d['space'].Name
        if num not in ROOM_ZONE:
            continue
        poly = local_poly(np.array(d['poly'].exterior.coords))
        zone = ROOM_ZONE[num]
        fill(poly, fc=ZONES[zone][1], ec='none', zorder=1)
        area = ue.get_psets(d['space'])['RusSet_Quantities']['RUS_Area']
        rooms.append({'num': num, 'name': ROOM_NAME.get(num, nm), 'area': round(float(area), 2), 'zone': zone,
                      'poly': poly})

    # крыльца и терраса (открытые планировочные элементы) — по зоне «Общая площадь»
    parts = json.load(open(os.path.join(HERE, 'out_ifc', 'areas.json')))['parts_world'][1:]
    for pw in parts:
        fill(Polygon(frame.w2l(np.array(pw) / 1000.0)), fc='#EDEDED', ec='none', zorder=1)

    # элементы ниже разреза — проекция (лестницы, пандусы, плиты крылец, ограждения)
    low = shapes(f, ['IfcStair', 'IfcRamp', 'IfcRailing', 'IfcSlab'])
    for cls, e, V, F in low:
        if V[:, 2].max() > CUT + 0.6 and cls != 'IfcRailing':
            continue                                        # перекрытия и кровля
        if cls == 'IfcSlab' and V[:, 2].max() > FLOOR + 0.05 and V[:, 2].min() > FLOOR - 0.05:
            continue
        fp = footprint(V, F)
        if fp is None:
            continue
        if cls == 'IfcSlab':
            outer = Polygon(fp.exterior.coords) if fp.geom_type == 'Polygon' else None
            fill(fp, fc='none', ec='#7d7d7d', lw=0.35, zorder=2)
        else:
            fill(fp, fc='none', ec='#555555', lw=0.45, zorder=3)
            if cls in ('IfcStair', 'IfcRamp'):
                # ступени: рёбра горизонтальных граней на разных отметках
                m = trimesh.Trimesh(vertices=V, faces=F, process=False)
                edges = m.edges_unique
                ev = V[edges]
                flat = np.abs(ev[:, 0, 2] - ev[:, 1, 2]) < 1e-3
                for a, b in ev[flat]:
                    la, lb = frame.w2l([a[:2], b[:2]])
                    if np.linalg.norm(la - lb) > 0.25:
                        ax.plot([la[0], lb[0]], [la[1], lb[1]], color='#666666', lw=0.25, zorder=3)

    # разрез стен и колонн
    cut = shapes(f, ['IfcWall', 'IfcColumn'])
    for cls, e, V, F in cut:
        if V[:, 2].min() > CUT or V[:, 2].max() < CUT:
            continue
        poly, lines = section(V, F, CUT)
        if poly is not None:
            fill(poly, fc='#3a3a3a' if cls == 'IfcWall' else '#1d1d1d', ec='#111111', lw=0.4, zorder=5)
    # витражи, окна, двери — разрез тонкими линиями
    glz = shapes(f, ['IfcCurtainWall', 'IfcWindow', 'IfcPlate', 'IfcMember', 'IfcDoor'])
    for cls, e, V, F in glz:
        if V[:, 2].min() > CUT or V[:, 2].max() < CUT:
            continue
        poly, lines = section(V, F, CUT)
        if poly is not None and not poly.is_empty:
            fill(poly, fc='white' if cls != 'IfcMember' else '#555555', ec='#222222', lw=0.35, zorder=6)
        for ln in lines:
            ax.plot(ln[:, 0], ln[:, 1], color='#222222', lw=0.35, zorder=6)

    # оси
    g = f.by_type('IfcGrid')[0]
    M = np.array(up.get_local_placement(g.ObjectPlacement))
    axes = []
    for a in list(g.UAxes) + list(g.VAxes):
        pts = np.array(a.AxisCurve.Points.CoordList)
        w = np.array([(M @ np.array([x, y, 0, 1]))[:2] for x, y in pts]) / 1000
        L = frame.w2l(w)
        tag = AXIS_NAMES.get(a.AxisTag, a.AxisTag)
        vertical = abs(L[0, 0] - L[1, 0]) < 1e-3
        axes.append((tag, vertical, float(L[0, 0] if vertical else L[0, 1])))
    R = 0.62
    xs = sorted(c for t, v, c in axes if v)
    ys = sorted(c for t, v, c in axes if not v)
    yb, xl = -3.15, -3.25                          # положение кружков
    for tag, vertical, c in axes:
        if vertical:
            ax.plot([c, c], [yb + R, V1 - 2.6], color='#444444', lw=0.3, dashes=(9, 2, 1.2, 2), zorder=4)
            ax.add_patch(Circle((c, yb), R, fc='white', ec='#222222', lw=0.5, zorder=8))
            ax.text(c, yb - 0.02, tag, fontsize=7.2, ha='center', va='center', zorder=9)
        else:
            ax.plot([xl + R, U1 - 2.4], [c, c], color='#444444', lw=0.3, dashes=(9, 2, 1.2, 2), zorder=4)
            ax.add_patch(Circle((xl, c), R, fc='white', ec='#222222', lw=0.5, zorder=8))
            ax.text(xl, c - 0.02, tag, fontsize=7.2, ha='center', va='center', zorder=9)

    def dim_chain(vals, fixed, horizontal, label_off):
        for a, b in zip(vals, vals[1:]):
            if horizontal:
                ax.plot([a, b], [fixed, fixed], color='#222222', lw=0.35, zorder=8)
                ax.text((a + b) / 2, fixed + label_off, '%d' % round((b - a) * 1000), fontsize=5.4, ha='center',
                        va='center', zorder=9)
            else:
                ax.plot([fixed, fixed], [a, b], color='#222222', lw=0.35, zorder=8)
                ax.text(fixed + label_off, (a + b) / 2, '%d' % round((b - a) * 1000), fontsize=5.4, ha='center',
                        va='center', rotation=90, zorder=9)
        for v in vals:
            if horizontal:
                ax.plot([v - 0.12, v + 0.12], [fixed - 0.12, fixed + 0.12], color='#222222', lw=0.6, zorder=8)
            else:
                ax.plot([fixed - 0.12, fixed + 0.12], [v - 0.12, v + 0.12], color='#222222', lw=0.6, zorder=8)

    dim_chain(xs, -1.55, True, 0.38)
    dim_chain([xs[0], xs[-1]], -2.25, True, 0.36)
    dim_chain(ys, -1.65, False, -0.38)
    dim_chain([ys[0], ys[-1]], -2.35, False, -0.36)

    # разрезы 1-1 и 2-2 — по чертежу авторов
    def sec_mark(p, d, label, lab_off):
        p = np.array(p, float); d = np.array(d, float)
        n = np.array([-d[1], d[0]])
        ax.plot([p[0] - n[0] * 0.9, p[0] + n[0] * 0.9], [p[1] - n[1] * 0.9, p[1] + n[1] * 0.9], color='#111111',
                lw=1.6, solid_capstyle='butt', zorder=9)
        ax.annotate('', xy=p + d * 1.15 + n * 0.0, xytext=p + d * 0.0, zorder=9,
                    arrowprops=dict(arrowstyle='-|>', lw=0.6, color='#111111', mutation_scale=7))
        ax.text(*(p + d * 0.75 + np.array(lab_off)), label, fontsize=7, ha='center', va='center', zorder=9)
    sec_mark((12.55, V1 - 4.2), (-1, 0), '1', (0, 0.55))
    sec_mark((12.55, -4.55), (-1, 0), '1', (0, -0.55))
    sec_mark((-5.45, 11.67), (0, 1), '2', (-0.55, 0))
    sec_mark((24.9, 11.67), (0, 1), '2', (0.55, 0))

    # номера помещений
    for r in rooms:
        c = r['poly'].representative_point()
        if r['num'] == '2':
            c = type(c)(10.6, 14.0)
        rr = 0.55
        ax.add_patch(Circle((c.x, c.y), rr, fc='white', ec='#222222', lw=0.45, zorder=10))
        ax.text(c.x, c.y - 0.02, r['num'], fontsize=6.4, ha='center', va='center', zorder=11)

    # отметка пола и стрелка севера
    ax.text(10.6, 15.2, '±0,000', fontsize=5.6, ha='center', va='center', zorder=11,
            bbox=dict(boxstyle='square,pad=0.15', fc='white', ec='#222222', lw=0.35))
    north = frame.w2l([frame.C + np.array([0.0, 1.0])])[0] - frame.w2l([frame.C])[0]
    n0 = np.array([U1 - 2.2, V1 - 3.0])
    ax.annotate('', xy=n0 + north * 2.0, xytext=n0 - north * 1.2,
                arrowprops=dict(arrowstyle='-|>', lw=0.8, color='#111111', mutation_scale=10), zorder=12)
    ax.text(*(n0 + north * 2.7), 'С', fontsize=8, ha='center', va='center', fontweight='bold', zorder=12)
    fig.savefig(out_png, dpi=dpi)
    plt.close(fig)
    json.dump([{k: v for k, v in r.items() if k != 'poly'} for r in sorted(rooms, key=lambda r: int(r['num']))],
              open(out_json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('помещений', len(rooms), 'сумма', round(sum(r['area'] for r in rooms), 2))


if __name__ == '__main__':
    draw(sys.argv[1], sys.argv[2], sys.argv[3])
