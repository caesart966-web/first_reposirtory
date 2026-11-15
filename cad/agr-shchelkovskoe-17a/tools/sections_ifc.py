"""Схемы разрезов 1-1 и 2-2 по модели АР (те же оси и положение секущих, что на плане).

    python3 sections_ifc.py <AR.ifc> <BiO.ifc> <папка вывода>

Разрез 1-1 — плоскость u = 12,55 м, взгляд в сторону −u (оси А…И слева направо).
Разрез 2-2 — плоскость v = 11,67 м, взгляд в сторону +v (оси 1…7 слева направо).
Рассечённые элементы — заливкой, элементы за секущей плоскостью — силуэтами
(дальние перекрываются ближними), рельеф — по топоповерхности модели благоустройства.
Отметки относительные и абсолютные (±0,000 = 154,850).
"""
import os
import sys

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.placement as up
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MPoly, Circle
from shapely.geometry import Polygon, LineString
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
plt.rcParams['hatch.linewidth'] = 0.3

FLOOR = 154.85
AXIS_NAMES = {'З': 'И'}
SKIP = ('IfcOpeningElement', 'IfcSpace', 'IfcGrid', 'IfcSite', 'IfcBuilding', 'IfcBuildingStorey')

# ось, перпендикулярная секущей плоскости; координата плоскости; направление взгляда; ось, идущая по экрану вправо
SECTIONS = {
    '1-1': dict(cut_axis=0, at=12.55, look=-1, screen_axis=1),
    '2-2': dict(cut_axis=1, at=11.67, look=+1, screen_axis=0),
}


def load(path, classes=None):
    f = ifcopenshell.open(path)
    s = ifcopenshell.geom.settings()
    s.set('use-world-coords', True)
    out = []
    for e in f.by_type('IfcProduct'):
        if not e.Representation or e.is_a() in SKIP:
            continue
        if classes and e.is_a() not in classes:
            continue
        try:
            sh = ifcopenshell.geom.create_shape(s, e)
        except Exception:
            continue
        V = np.array(sh.geometry.verts).reshape(-1, 3)
        F = np.array(sh.geometry.faces).reshape(-1, 3)
        if V[:, 0].max() > 100000:
            V = V / 1000.0
        L = np.c_[frame.w2l(V[:, :2]), V[:, 2] - FLOOR]       # (u, v, z от ±0,000)
        out.append((e.is_a(), e, L, F))
    return f, out


def kind(cls, e):
    n = (e.Name or '')
    if cls == 'IfcSlab':
        if 'Фундамент' in n:
            return 'found'
        if 'крыша' in n.lower():
            return 'roof'
        if 'потолок' in n:
            return 'ceiling'
        return 'floor'
    return cls


CUT_STYLE = {
    'IfcWall': dict(fc='#3d3d3d', ec='#111111'),
    'IfcColumn': dict(fc='#1d1d1d', ec='#111111'),
    'roof': dict(fc='#5a5a5a', ec='#111111'),
    'found': dict(fc='#b4b4b4', ec='#333333', hatch='//////'),
    'floor': dict(fc='#d9d9d9', ec='#555555'),
    'ceiling': dict(fc='#d9d9d9', ec='#555555'),
    'IfcCurtainWall': dict(fc='#ffffff', ec='#222222'),
    'IfcWindow': dict(fc='#ffffff', ec='#222222'),
    'IfcDoor': dict(fc='#ffffff', ec='#222222'),
    'IfcRailing': dict(fc='#ffffff', ec='#222222'),
    'IfcStair': dict(fc='#cfcfcf', ec='#333333'),
    'IfcRamp': dict(fc='#cfcfcf', ec='#333333'),
}
FAR_FILL = {
    'IfcCurtainWall': '#E9F1F5', 'IfcWindow': '#E9F1F5', 'IfcDoor': '#F4F4F4', 'IfcRailing': '#EEF4F7',
    'IfcWall': '#FAFAFA', 'IfcColumn': '#F1F1F1', 'roof': '#F1F1F1', 'found': '#F1F1F1', 'floor': '#F7F7F7',
    'ceiling': '#F7F7F7', 'IfcStair': '#F1F1F1', 'IfcRamp': '#F1F1F1',
}


def to_screen(P, sa):
    return np.c_[P[:, sa], P[:, 2]]


def cut_polys(L, F, ca, at, sa):
    m = trimesh.Trimesh(vertices=L, faces=F, process=False)
    normal = np.zeros(3); normal[ca] = 1.0
    origin = np.zeros(3); origin[ca] = at
    try:
        sec = m.section(plane_origin=origin, plane_normal=normal)
    except Exception:
        return None
    if sec is None:
        return None
    polys = []
    for ent in sec.entities:
        pts = sec.vertices[ent.points]
        q = to_screen(pts, sa)
        if len(q) >= 3:
            p = Polygon(q)
            if not p.is_valid:
                p = p.buffer(0)
            if p.area > 1e-5:
                polys.append(p)
    if not polys:
        return None
    # чётно-нечётное правило для вложенных контуров
    polys.sort(key=lambda p: -p.area)
    res = None
    for p in polys:
        if res is None:
            res = p
        elif res.contains(p.representative_point()) and res.buffer(-1e-4).contains(p):
            res = res.difference(p)
        else:
            res = res.union(p)
    return res


def far_silhouette(L, F, ca, at, look, sa):
    """Силуэт части элемента за секущей плоскостью; глубина — среднее удаление."""
    T = L[F]
    d = (T[:, :, ca] - at) * look                    # >0 — за плоскостью по направлению взгляда
    keep = d.max(axis=1) > 1e-4
    if not keep.any():
        return None, None
    T = T[keep]
    d = np.clip(d[keep], 0, None)
    polys = []
    for t in T:
        q = to_screen(t, sa)
        p = Polygon(q)
        if p.is_valid and p.area > 1e-7:
            polys.append(p)
    if not polys:
        return None, None
    return unary_union(polys).buffer(0), float(d.mean())


def fill(ax, geom, z, **kw):
    if geom is None or geom.is_empty:
        return
    for g in (geom.geoms if hasattr(geom, 'geoms') else [geom]):
        if g.geom_type != 'Polygon' or g.area < 1e-6:
            continue
        hatch = kw.pop('hatch', None) if 'hatch' in kw else None
        ax.add_patch(MPoly(np.array(g.exterior.coords), closed=True, zorder=z, hatch=hatch, joinstyle='round', **kw))
        for h in g.interiors:
            ax.add_patch(MPoly(np.array(h.coords), closed=True, fc='white', ec=kw.get('ec', 'none'),
                               lw=kw.get('lw', 0), zorder=z + 0.001))
        if hatch:
            kw['hatch'] = hatch


def level_mark(ax, x, y, rel, side, ext=None):
    """Отметка уровня: треугольник на линии уровня, полка, относительная и абсолютная отметки."""
    s = 1 if side == 'right' else -1
    w, h = 0.28, 0.28
    ax.plot([x - w, x, x + w, x - w], [y + h, y, y + h, y + h], color='#111111', lw=0.45, zorder=20,
            solid_joinstyle='miter')
    shelf = 2.0
    ax.plot([x, x], [y, y + h + 0.42], color='#111111', lw=0.45, zorder=20)
    ax.plot([x, x + s * shelf], [y + h + 0.42, y + h + 0.42], color='#111111', lw=0.45, zorder=20)
    if ext is not None:
        ax.plot(sorted([x, ext]), [y, y], color='#111111', lw=0.3, zorder=19, dashes=(3, 2))
    txt = ('±0,000' if abs(rel) < 5e-4 else ('%+.3f' % rel).replace('.', ','))
    ab = ('%.3f' % (FLOOR + rel)).replace('.', ',')
    ha = 'left' if s > 0 else 'right'
    ax.text(x + s * 0.12, y + h + 0.5, txt, fontsize=6.6, ha=ha, va='bottom', zorder=21)
    ax.text(x + s * 0.12, y + h + 0.34, 'абс. ' + ab, fontsize=5.2, ha=ha, va='top', color='#333333', zorder=21)


def grid_axes(f):
    out = []
    for g in f.by_type('IfcGrid'):
        M = np.array(up.get_local_placement(g.ObjectPlacement))
        for a in list(g.UAxes) + list(g.VAxes):
            pts = np.array(a.AxisCurve.Points.CoordList)
            w = np.array([(M @ np.array([x, y, 0, 1]))[:2] for x, y in pts]) / 1000
            Lp = frame.w2l(w)
            vertical = abs(Lp[0, 0] - Lp[1, 0]) < 1e-3
            out.append((AXIS_NAMES.get(a.AxisTag, a.AxisTag), vertical, float(Lp[0, 0] if vertical else Lp[0, 1])))
    uniq = {}
    for t, v, c in out:
        uniq[(t, v)] = c
    return [(t, v, c) for (t, v), c in uniq.items()]


def draw(name, items, topo, f, out_png, width_pt=725.0, dpi=400):
    cfg = SECTIONS[name]
    ca, at, look, sa = cfg['cut_axis'], cfg['at'], cfg['look'], cfg['screen_axis']
    allL = np.vstack([L for _, _, L, _ in items])
    x0, x1 = allL[:, sa].min(), allL[:, sa].max()
    X0, X1 = x0 - 8.0, x1 + 8.0
    Y0, Y1 = -3.9, 7.5
    h_pt = width_pt * (Y1 - Y0) / (X1 - X0)
    fig = plt.figure(figsize=(width_pt / 72, h_pt / 72), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_aspect('equal'); ax.axis('off')
    ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1)

    # грунт по топоповерхности: верх топотел по линии разреза
    line = LineString([(at, -50), (at, 80)] if ca == 0 else [(-50, at), (80, at)])
    gz = []
    for _, _, L, F in topo:
        for t in L[F]:
            tri = Polygon(t[:, :2])
            if not tri.is_valid or tri.area < 1e-6 or not tri.intersects(line):
                continue
            seg = tri.intersection(line)
            for c in np.array(seg.coords) if seg.geom_type == 'LineString' else []:
                # отметка по плоскости треугольника
                A = np.c_[t[:, :2], np.ones(3)]
                try:
                    k = np.linalg.solve(A, t[:, 2])
                except np.linalg.LinAlgError:
                    continue
                gz.append((c[sa], c @ k[:2] + k[2]))
    gz = np.array(gz) if gz else np.array([[X0, -0.5], [X1, -0.5]])
    # верхняя огибающая по бинам
    bins = np.linspace(X0, X1, 400)
    top = np.full(len(bins), np.nan)
    for i, b in enumerate(bins):
        sel = np.abs(gz[:, 0] - b) < 0.35
        if sel.any():
            top[i] = gz[sel, 1].max()
    ok = ~np.isnan(top)
    top = np.interp(bins, bins[ok], top[ok]) if ok.any() else np.full(len(bins), -0.5)
    ax.fill_between(bins, top, -1.25, color='#EFE9DF', zorder=0.5, lw=0)
    ax.plot(bins, top, color='#4d4d4d', lw=0.7, zorder=1)

    # дальние элементы: силуэты от дальних к ближним
    far = []
    for cls, e, L, F in items:
        k = kind(cls, e)
        sil, depth = far_silhouette(L, F, ca, at, look, sa)
        if sil is not None:
            far.append((depth, k, sil))
    far.sort(key=lambda t: -t[0])
    for i, (depth, k, sil) in enumerate(far):
        fill(ax, sil, 2 + i * 1e-3, fc=FAR_FILL.get(k, '#F4F4F4'), ec='#6e6e6e', lw=0.28)

    # рассечённые элементы
    order = ['found', 'floor', 'ceiling', 'IfcStair', 'IfcRamp', 'roof', 'IfcWall', 'IfcColumn', 'IfcCurtainWall',
             'IfcWindow', 'IfcDoor', 'IfcRailing']
    cuts = []
    for cls, e, L, F in items:
        k = kind(cls, e)
        lo, hi = L[:, ca].min(), L[:, ca].max()
        if not (lo - 1e-6 <= at <= hi + 1e-6):
            continue
        p = cut_polys(L, F, ca, at, sa)
        if p is not None:
            cuts.append((order.index(k) if k in order else 5, k, p))
    for i, k, p in sorted(cuts, key=lambda t: t[0]):
        st = dict(CUT_STYLE.get(k, dict(fc='#9a9a9a', ec='#222222')))
        fill(ax, p, 10 + i * 0.01, lw=0.4, **st)

    # помещения в разрезе — номер в кружке
    S = ifc_geom.spaces(f)
    for nm, d in S.items():
        num = d['space'].Name
        if not (num or '').isdigit():
            continue
        poly = Polygon(frame.w2l(np.array(d['poly'].exterior.coords) / 1000.0))
        seg = poly.intersection(line)
        if seg.is_empty:
            continue
        segs = seg.geoms if hasattr(seg, 'geoms') else [seg]
        segs = [s_ for s_ in segs if s_.length > 1.2]
        if not segs:
            continue
        s_ = max(segs, key=lambda s_: s_.length)
        cx = np.array(s_.coords)[:, sa].mean()
        ax.add_patch(Circle((cx, 1.6), 0.42, fc='white', ec='#222222', lw=0.45, zorder=30))
        ax.text(cx, 1.6 - 0.02, num, fontsize=6.4, ha='center', va='center', zorder=31)

    # оси
    axes_ = [(t, c) for t, v, c in grid_axes(f) if (v if sa == 0 else not v)]
    axes_.sort(key=lambda t: t[1])
    yb, R = -3.25, 0.45
    for t, c in axes_:
        ax.plot([c, c], [yb + R, 5.4], color='#444444', lw=0.3, dashes=(9, 2, 1.2, 2), zorder=25)
        ax.add_patch(Circle((c, yb), R, fc='white', ec='#222222', lw=0.5, zorder=26))
        ax.text(c, yb - 0.02, t, fontsize=6.6, ha='center', va='center', zorder=27)
    cs = [c for _, c in axes_]

    def chain(vals, y, off):
        for a, b in zip(vals, vals[1:]):
            ax.plot([a, b], [y, y], color='#222222', lw=0.35, zorder=26)
            ax.text((a + b) / 2, y + off, '%d' % round((b - a) * 1000), fontsize=5.6, ha='center', va='bottom',
                    zorder=27)
        for v_ in vals:
            ax.plot([v_ - 0.1, v_ + 0.1], [y - 0.1, y + 0.1], color='#222222', lw=0.6, zorder=26)
    chain(cs, -1.95, 0.06)
    chain([cs[0], cs[-1]], -2.55, 0.06)

    # отметки
    zmax = allL[:, 2].max()
    roof = [L for cls, e, L, F in items if kind(cls, e) == 'roof']
    roof_top = max(L[:, 2].max() for L in roof)
    ceil = [L for cls, e, L, F in items if kind(cls, e) == 'ceiling']
    ceil_bot = min(L[:, 2].min() for L in ceil)
    xl, xr = x0 - 2.4, x1 + 2.4
    g_left = float(np.interp(x0 - 0.6, bins, top))
    g_right = float(np.interp(x1 + 0.6, bins, top))
    level_mark(ax, xl, 0.0, 0.0, 'left', ext=x0)
    level_mark(ax, xl, round(ceil_bot, 3), round(ceil_bot, 3), 'left', ext=x0)
    level_mark(ax, xl, round(zmax, 3), round(zmax, 3), 'left', ext=x0)
    level_mark(ax, xl - 3.0, round(g_left, 3), round(g_left, 3), 'left', ext=x0 - 0.4)
    R_ = np.vstack(roof)
    rx = float(R_[np.argmax(R_[:, 2]), sa])
    if rx - x0 < x1 - rx:
        level_mark(ax, xl - 3.0, round(roof_top, 3), round(roof_top, 3), 'left', ext=rx)
    else:
        level_mark(ax, xr, round(roof_top, 3), round(roof_top, 3), 'right', ext=rx)
    level_mark(ax, xr + 3.0, round(g_right, 3), round(g_right, 3), 'right', ext=x1 + 0.4)
    fig.savefig(out_png, dpi=dpi, facecolor='white')
    plt.close(fig)
    return dict(zmax=round(float(zmax), 3), roof=round(float(roof_top), 3), ceil=round(float(ceil_bot), 3),
                ground=(round(g_left, 3), round(g_right, 3)), axes=[t for t, _ in axes_], h_pt=h_pt)


def main(ar_path, bio_path, outdir):
    os.makedirs(outdir, exist_ok=True)
    f, items = load(ar_path)
    _, topo = load(bio_path, ('IfcCivilElement',))
    for nm in SECTIONS:
        info = draw(nm, items, topo, f, os.path.join(outdir, 'section_%s.png' % nm.replace('-', '_')))
        print(nm, info)


if __name__ == '__main__':
    main(*sys.argv[1:4])
