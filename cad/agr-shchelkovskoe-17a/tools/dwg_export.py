"""Чертежи для Комиссии по п. 2.3 Положения (DXF, затем DWG) и таблица расчёта площадей (XLSX).

    python3 dwg_export.py <AR.ifc> <BiO.ifc> <near.osm> <папка вывода>

* «План 1 этажа»: стены, колонны, витражи, окна и двери в разрезе на +1,0 м; крыльца, лестницы и пандусы;
  помещения с номерами и площадями; оси с марками и размерами; замкнутые контуры по наружному и внутреннему
  периметрам; заливки SOLID с прозрачностью 50 % в слоях spp2 (СПП в ГНС) и s3 (ННП отдельно стоящего
  нежилого здания). Местные координаты (u вдоль шоссе, v от шоссе), метры.
* «Разрезы и фасады»: разрезы 1-1, 2-2 и фасады 1-7, 7-1, А-И, И-А из модели АР с удалением невидимых линий,
  отметки относительные и абсолютные. Метры, ±0,000 = 154,850.
* «СПОЗУ»: участок, объект, опорная застройка, проезды, красная линия, полоса и места установки пожарной
  техники, приобъектная парковка, маршруты транспорта и пешеходов, покрытие. Координаты модели (МСК), метры.
* Таблица расчёта площадей: значения считаются по тем же контурам, что и заливки.
"""
import json
import os
import sys

import ezdxf
import numpy as np
import trimesh
from ezdxf.enums import TextEntityAlignment
from shapely.geometry import LineString, MultiLineString, Polygon, box
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import clean_meta  # noqa: E402
import frame          # noqa: E402
import ifc_geom       # noqa: E402
import sections_ifc as SI  # noqa: E402

FLOOR = 154.85
AXIS_NAMES = {'З': 'И'}
ROOM_FIX = {'Комната приема пищи': 'Комната приёма пищи',
            'Помещение приемки и предпродажной подготовки товара':
                'Помещение приёмки и предпродажной подготовки товара'}


# --- общее ------------------------------------------------------------------------------------------------------------
def new_doc():
    doc = ezdxf.new('R2018', setup=True)
    doc.header['$INSUNITS'] = 6            # метры
    doc.header['$MEASUREMENT'] = 1
    doc.header['$LUNITS'] = 2
    doc.header['$LUPREC'] = 2
    if 'TXT' not in doc.styles:
        doc.styles.add('TXT', font='arial.ttf')
    return doc


def lay(doc, name, color, lw=25, ltype='Continuous'):
    if name not in doc.layers:
        doc.layers.add(name, color=color, linetype=ltype, lineweight=lw)
    return name


def pl(msp, coords, layer, closed=False, **kw):
    pts = [(float(x), float(y)) for x, y in coords]
    if len(pts) < 2:
        return None
    return msp.add_lwpolyline(pts, close=closed, dxfattribs={'layer': layer, **kw})


def text(msp, s, xy, h, layer, align=TextEntityAlignment.MIDDLE_CENTER, rot=0.0):
    t = msp.add_text(s, height=h, rotation=rot, dxfattribs={'layer': layer, 'style': 'TXT'})
    t.set_placement((float(xy[0]), float(xy[1])), align=align)
    return t


def rings(geom):
    if geom is None or geom.is_empty:
        return []
    out = []
    for g in (geom.geoms if hasattr(geom, 'geoms') else [geom]):
        if g.geom_type == 'Polygon':
            out.append(list(g.exterior.coords)[:-1])
            out += [list(h.coords)[:-1] for h in g.interiors]
        elif g.geom_type in ('LineString', 'LinearRing'):
            out.append(list(g.coords))
    return out


def outline(msp, geom, layer, **kw):
    if geom is None or geom.is_empty:
        return
    for g in (geom.geoms if hasattr(geom, 'geoms') else [geom]):
        if g.geom_type == 'Polygon':
            pl(msp, list(g.exterior.coords)[:-1], layer, True, **kw)
            for h in g.interiors:
                pl(msp, list(h.coords)[:-1], layer, True, **kw)
        elif g.geom_type == 'LineString':
            pl(msp, list(g.coords), layer, **kw)
        elif g.geom_type == 'GeometryCollection':
            outline(msp, g, layer, **kw)


def hatch(msp, geom, layer, color, transparency=0.5):
    """Одна заливка SOLID на все полигоны (внешние контуры и отверстия)."""
    h = msp.add_hatch(color=color, dxfattribs={'layer': layer})
    for g in (geom.geoms if hasattr(geom, 'geoms') else [geom]):
        if g.geom_type != 'Polygon' or g.area < 1e-6:
            continue
        h.paths.add_polyline_path([(float(x), float(y)) for x, y in list(g.exterior.coords)[:-1]], is_closed=True,
                                  flags=ezdxf.const.BOUNDARY_PATH_EXTERNAL)
        for r in g.interiors:
            h.paths.add_polyline_path([(float(x), float(y)) for x, y in list(r.coords)[:-1]], is_closed=True,
                                      flags=ezdxf.const.BOUNDARY_PATH_OUTERMOST)
    if transparency is not None:
        h.transparency = transparency
    return h


def dimstyle(doc, name='АГР', h=0.25, factor=1000.0, arrow=0.12):
    if name in doc.dimstyles:
        return name
    ds = doc.dimstyles.new(name)
    ds.dxf.dimtxt = h
    ds.dxf.dimasz = arrow
    ds.dxf.dimexe = 0.1
    ds.dxf.dimexo = 0.1
    ds.dxf.dimlfac = factor            # чертёж в метрах, размерный текст в миллиметрах
    ds.dxf.dimdec = 0
    ds.dxf.dimgap = 0.06
    ds.dxf.dimtxsty = 'TXT'
    ds.dxf.dimtad = 1
    ds.dxf.dimtsz = 0.1                # засечки вместо стрелок
    return name


def dim(msp, p1, p2, base, layer, style='АГР', angle=0.0):
    d = msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle=style, dxfattribs={'layer': layer})
    d.render()


def level_mark(msp, x, y, rel, side, layer, h=0.22):
    """Знак отметки: треугольник, полка, относительная и абсолютная отметки."""
    s = 1 if side == 'right' else -1
    w = 0.25
    pl(msp, [(x - w, y + w), (x, y), (x + w, y + w)], layer, True)
    pl(msp, [(x, y), (x, y + 0.75), (x + s * 2.4, y + 0.75)], layer)
    rs = '±0,000' if abs(rel) < 5e-4 else ('%+.3f' % rel).replace('.', ',')
    ab = ('%.3f' % (FLOOR + rel)).replace('.', ',')
    al = TextEntityAlignment.BOTTOM_LEFT if s > 0 else TextEntityAlignment.BOTTOM_RIGHT
    text(msp, rs, (x + s * 0.1, y + 0.82), h, layer, al)
    al2 = TextEntityAlignment.TOP_LEFT if s > 0 else TextEntityAlignment.TOP_RIGHT
    text(msp, 'абс. ' + ab, (x + s * 0.1, y + 0.68), h * 0.8, layer, al2)


def axis_bubble(msp, xy, tag, layer, r=0.4):
    msp.add_circle((float(xy[0]), float(xy[1])), r, dxfattribs={'layer': layer})
    text(msp, tag, xy, r * 0.9, layer)


# --- план -------------------------------------------------------------------------------------------------------------
def plan(ar_path, areas_path, out_dxf):
    import plan_ifc as PI
    f = PI.ifcopenshell.open(ar_path)
    S = ifc_geom.spaces(f)
    A = json.load(open(areas_path))
    doc = new_doc()
    msp = doc.modelspace()
    L = {k: lay(doc, k, c, lw) for k, c, lw in (
        ('АР_Стены', 7, 50), ('АР_Колонны', 7, 50), ('АР_Окна_двери_витражи', 4, 18),
        ('АР_Крыльца_лестницы_пандусы', 8, 18), ('АР_Помещения', 8, 13), ('АР_Помещения_подписи', 7, 18),
        ('АР_Оси', 1, 13), ('АР_Оси_марки', 7, 18), ('АР_Размеры', 7, 13), ('АР_Разрезы', 7, 35),
        ('АР_Отметки', 7, 18), ('АР_Надписи', 7, 18), ('Контур_наружный', 30, 35),
        ('Контур_внутренний', 3, 35), ('spp2', 30, 13), ('s3', 3, 13))}
    doc.layers.get('АР_Оси').dxf.linetype = 'DASHDOT'

    # стены и колонны в разрезе
    for cls, e, V, F in PI.shapes(f, ['IfcWall', 'IfcColumn']):
        if V[:, 2].min() > PI.CUT or V[:, 2].max() < PI.CUT:
            continue
        poly, _ = PI.section(V, F, PI.CUT)
        if poly is not None and not poly.is_empty:
            ly = 'АР_Стены' if cls == 'IfcWall' else 'АР_Колонны'
            outline(msp, poly, ly)
            hatch(msp, poly, ly, 252 if cls == 'IfcWall' else 250, transparency=None)
    for cls, e, V, F in PI.shapes(f, ['IfcCurtainWall', 'IfcWindow', 'IfcPlate', 'IfcMember', 'IfcDoor']):
        if V[:, 2].min() > PI.CUT or V[:, 2].max() < PI.CUT:
            continue
        poly, lines = PI.section(V, F, PI.CUT)
        if poly is not None and not poly.is_empty:
            outline(msp, poly, 'АР_Окна_двери_витражи')
        else:
            for ln in lines:
                pl(msp, ln, 'АР_Окна_двери_витражи')
    for cls, e, V, F in PI.shapes(f, ['IfcStair', 'IfcRamp', 'IfcRailing', 'IfcSlab']):
        if V[:, 2].max() > PI.CUT + 0.6 and cls != 'IfcRailing':
            continue
        if cls == 'IfcSlab' and V[:, 2].max() > FLOOR + 0.05 and V[:, 2].min() > FLOOR - 0.05:
            continue
        fp = PI.footprint(V, F)
        if fp is not None:
            outline(msp, fp.simplify(0.005), 'АР_Крыльца_лестницы_пандусы')
        if cls in ('IfcStair', 'IfcRamp'):
            m = trimesh.Trimesh(vertices=V, faces=F, process=False)
            ev = V[m.edges_unique]
            flat = np.abs(ev[:, 0, 2] - ev[:, 1, 2]) < 1e-3
            for a, b in ev[flat]:
                la, lb = frame.w2l([a[:2], b[:2]])
                if np.linalg.norm(la - lb) > 0.25:
                    pl(msp, [la, lb], 'АР_Крыльца_лестницы_пандусы')

    # помещения
    rooms = []
    for nm, d in S.items():
        num = d['space'].Name
        if not (num or '').isdigit():
            continue
        poly = Polygon(frame.w2l(np.array(d['poly'].exterior.coords) / 1000.0))
        area = PI.ue.get_psets(d['space'])['RusSet_Quantities']['RUS_Area']
        rooms.append((int(num), ROOM_FIX.get(nm, nm), float(area), poly))
        pl(msp, list(poly.exterior.coords)[:-1], 'АР_Помещения', True)
    for num, nm, area, poly in sorted(rooms):
        c = poly.representative_point() if num != 2 else Polygon([(10, 13), (11, 13), (11, 14), (10, 14)]).centroid
        axis_bubble(msp, (c.x, c.y + 0.55), str(num), 'АР_Помещения_подписи', r=0.42)
        text(msp, ('%.2f' % area).replace('.', ','), (c.x, c.y - 0.15), 0.22, 'АР_Помещения_подписи')

    # контуры и заливки площадей
    spp = None
    for nm, d in S.items():
        if nm == 'СПП в ГНС':
            spp = Polygon(frame.w2l(np.array(d['poly'].exterior.coords) / 1000.0))
    inner = Polygon(frame.w2l(np.array(A['inner_world']) / 1000.0))
    parts = [Polygon(frame.w2l(np.array(p) / 1000.0)) for p in A['parts_world']]
    nnp = unary_union(parts)
    pl(msp, list(spp.exterior.coords)[:-1], 'Контур_наружный', True)
    pl(msp, list(inner.exterior.coords)[:-1], 'Контур_внутренний', True)
    hatch(msp, spp, 'spp2', 30)
    hatch(msp, nnp, 's3', 3)

    # оси и размеры
    axes = SI.grid_axes(f)
    xs = sorted((c, t) for t, v, c in axes if v)
    ys = sorted((c, t) for t, v, c in axes if not v)
    U0, U1, V0, V1 = -3.0, 25.4, -3.6, 31.4
    for c, t in xs:
        pl(msp, [(c, V0 + 0.9), (c, V1 - 0.5)], 'АР_Оси')
        axis_bubble(msp, (c, V0 + 0.45), t, 'АР_Оси_марки')
    for c, t in ys:
        pl(msp, [(U0 + 0.9, c), (U1 - 0.5, c)], 'АР_Оси')
        axis_bubble(msp, (U0 + 0.45, c), t, 'АР_Оси_марки')
    dimstyle(doc)
    for (a, _), (b, _) in zip(xs, xs[1:]):
        dim(msp, (a, -1.0), (b, -1.0), (0, -1.9), 'АР_Размеры')
    dim(msp, (xs[0][0], -1.0), (xs[-1][0], -1.0), (0, -2.6), 'АР_Размеры')
    for (a, _), (b, _) in zip(ys, ys[1:]):
        dim(msp, (0.6, a), (0.6, b), (-0.4, 0), 'АР_Размеры', angle=90)
    dim(msp, (0.6, ys[0][0]), (0.6, ys[-1][0]), (-1.1, 0), 'АР_Размеры', angle=90)

    # разрезы, отметка, надписи
    for p, dvec, lab in (((12.55, V1 + 0.6), (-1, 0), '1'), ((12.55, V0 - 0.9), (-1, 0), '1'),
                         ((U0 - 1.0, 11.67), (0, 1), '2'), ((U1 + 0.6, 11.67), (0, 1), '2')):
        p = np.array(p); dv = np.array(dvec, float); n = np.array([-dv[1], dv[0]])
        pl(msp, [p - n * 0.9, p + n * 0.9], 'АР_Разрезы')
        pl(msp, [p + n * 0.9, p + n * 0.9 + dv * 0.9], 'АР_Разрезы')
        text(msp, lab, p + n * 1.3 + dv * 0.5, 0.4, 'АР_Разрезы')
    text(msp, '±0,000 (абс. 154,850)', (10.6, 15.3), 0.25, 'АР_Отметки')
    text(msp, 'Схема плана 1 этажа. Реконструкция нежилого здания под магазин, '
              'г. Москва, Щёлковское шоссе, вл. 17А, стр. 1', (U0, V1 + 3.2), 0.45, 'АР_Надписи',
         TextEntityAlignment.BOTTOM_LEFT)
    text(msp, 'spp2 — СПП в ГНС %.2f м²; s3 — ННП отдельно стоящего нежилого здания %.2f м²'
         % (spp.area, nnp.area), (U0, V1 + 2.4), 0.3, 'АР_Надписи', TextEntityAlignment.BOTTOM_LEFT)
    clean_meta.save_dxf(doc, out_dxf)
    return dict(spp=spp.area, nnp=nnp.area, inner=inner.area, parts=[p.area for p in parts], rooms=rooms,
                names=list(A['parts'].keys()))


# --- разрезы и фасады -------------------------------------------------------------------------------------------------
CLS_LAYER = {'IfcWall': ('Стены', 7), 'IfcCurtainWall': ('Навесной_фасад', 30), 'IfcWindow': ('Окна_витражи', 4),
             'IfcDoor': ('Двери', 4), 'IfcRailing': ('Ограждения', 8), 'IfcColumn': ('Колонны', 7),
             'roof': ('Кровля', 7), 'found': ('Фундамент', 8), 'floor': ('Пол', 8), 'ceiling': ('Потолок', 8),
             'IfcStair': ('Лестницы_пандусы', 8), 'IfcRamp': ('Лестницы_пандусы', 8), 'topo': ('Рельеф', 34)}


def feature_edges(L, F, angle=0.35):
    m = trimesh.Trimesh(vertices=L, faces=F, process=True)
    if len(m.faces) == 0:
        return np.zeros((0, 2, 3))
    adj = m.face_adjacency
    ang = m.face_adjacency_angles
    sharp = m.face_adjacency_edges[ang > angle]
    # открытые кромки
    e = np.sort(m.edges, axis=1)
    u, cnt = np.unique(e, axis=0, return_counts=True)
    border = u[cnt == 1]
    E = np.vstack([sharp, border]) if len(border) else sharp
    return m.vertices[E]


def elevation(items, topo, d, right, cut=None):
    """Невидимые линии удаляются по силуэтам элементов: ближние закрывают дальние."""
    d = np.asarray(d, float); right = np.asarray(right, float)
    elems = []
    for cls, e, L, F in items + topo:
        k = 'topo' if e is None or cls == 'IfcCivilElement' else SI.kind(cls, e)
        T = L[F]
        dep = T[..., :2] @ d[:2]
        if cut is not None:
            keep = dep.max(axis=1) > cut + 1e-4
            if not keep.any():
                continue
            T, F_ = T[keep], F[keep]
            dep = dep[keep]
        else:
            F_ = F
        X = T[..., :2] @ right[:2]
        Z = T[..., 2]
        polys = [Polygon(np.c_[x, z]) for x, z in zip(X, Z)]
        polys = [p for p in polys if p.is_valid and p.area > 1e-7]
        if not polys:
            continue
        sil = unary_union(polys).buffer(0)
        dmin = float(np.min(dep)) if cut is None else float(np.min(np.clip(dep, cut, None)))
        elems.append((dmin, k, sil, L, F_))
    elems.sort(key=lambda t: t[0])
    covered = None
    out = []
    for dmin, k, sil, L, F_ in elems:
        vis = sil if covered is None else sil.difference(covered)
        covered = sil if covered is None else unary_union([covered, sil]).buffer(0)
        if vis.is_empty or vis.area < 1e-5:
            continue
        lines = []
        if k not in ('topo', 'found', 'floor', 'ceiling'):
            E = feature_edges(L, F_)
            if len(E):
                segs = [LineString([(a[:2] @ right[:2], a[2]), (b[:2] @ right[:2], b[2])]) for a, b in E]
                ml = unary_union([s for s in segs if s.length > 0.02])
                clip = ml.intersection(vis.buffer(0.005))
                lines = clip
        out.append((k, vis, lines))
    return out


def draw_elevation(msp, doc, parts, off, layer_prefix):
    ox, oy = off
    for k, vis, lines in parts:
        name, col = CLS_LAYER.get(k, ('Прочее', 7))
        ly = lay(doc, layer_prefix + name, col, 18)
        g = shift(vis, ox, oy)
        outline(msp, g, ly)
        if lines is not None and not getattr(lines, 'is_empty', True):
            outline(msp, shift(lines, ox, oy), ly)


def shift(geom, dx, dy):
    from shapely import affinity
    return affinity.translate(geom, dx, dy)


def sections_facades(ar_path, bio_path, out_dxf):
    f, items = SI.load(ar_path)
    _, topo = SI.load(bio_path, ('IfcCivilElement',))
    doc = new_doc()
    msp = doc.modelspace()
    dimstyle(doc)
    lay(doc, 'Отметки', 7, 18); lay(doc, 'Оси', 1, 13); lay(doc, 'Оси_марки', 7, 18); lay(doc, 'Размеры', 7, 13)
    lay(doc, 'Надписи', 7, 18); lay(doc, 'Разрез_сечение', 7, 50); lay(doc, 'Помещения_номера', 7, 18)
    doc.layers.get('Оси').dxf.linetype = 'DASHDOT'
    axes = SI.grid_axes(f)
    allL = np.vstack([L for _, _, L, _ in items])
    zmax = float(allL[:, 2].max())
    views = [
        ('Фасад 1–7', (0, 1), (1, 0), None, 'u'),
        ('Фасад 7–1', (0, -1), (-1, 0), None, 'u'),
        ('Фасад А–И', (-1, 0), (0, 1), None, 'v'),
        ('Фасад И–А', (1, 0), (0, -1), None, 'v'),
        ('Разрез 1–1', (-1, 0), (0, 1), 12.55, 'v'),
        ('Разрез 2–2', (0, 1), (1, 0), 11.67, 'u'),
    ]
    info = {}
    for i, (title, d, right, cut, axk) in enumerate(views):
        d = np.array(d, float); r = np.array(right, float)
        cutdep = None if cut is None else cut * (d[0] if abs(d[0]) > 0 else d[1])
        parts = elevation(items, topo, d, r, cut=cutdep)
        # ограничение рельефа по ширине чертежа
        xs_all = [p[1].bounds for p in parts if p[0] != 'topo']
        x0 = min(b[0] for b in xs_all); x1 = max(b[2] for b in xs_all)
        ox, oy = (i % 2) * 48.0 - x0, -(i // 2) * 16.0          # левый край вида — у левого края ячейки
        parts = [(k, v.intersection(box(x0 - 4, -3, x1 + 4, 9)) if k == 'topo' else v, ln) for k, v, ln in parts]
        draw_elevation(msp, doc, parts, (ox, oy), '')
        if cut is not None:
            ca = 0 if abs(d[0]) > 0 else 1
            sa = 0 if abs(r[0]) > 0 else 1
            sign = r[sa]
            for cls, e, L, F in items:
                lo, hi = L[:, ca].min(), L[:, ca].max()
                if not (lo <= cut <= hi):
                    continue
                p = SI.cut_polys(L, F, ca, cut, sa)
                if p is None:
                    continue
                if sign < 0:
                    from shapely import affinity
                    p = affinity.scale(p, -1, 1, origin=(0, 0))
                g = shift(p, ox, oy)
                outline(msp, g, 'Разрез_сечение')
                hatch(msp, g, 'Разрез_сечение', 251, transparency=None)
            # номера помещений
            S = ifc_geom.spaces(f)
            line = LineString([(cut, -50), (cut, 80)] if ca == 0 else [(-50, cut), (80, cut)])
            for nm, dd in S.items():
                num = dd['space'].Name
                if not (num or '').isdigit():
                    continue
                poly = Polygon(frame.w2l(np.array(dd['poly'].exterior.coords) / 1000.0))
                seg = poly.intersection(line)
                segs = [s_ for s_ in (seg.geoms if hasattr(seg, 'geoms') else [seg]) if s_.length > 1.2]
                if segs:
                    cx = np.array(max(segs, key=lambda s_: s_.length).coords)[:, sa].mean() * sign
                    axis_bubble(msp, (cx + ox, 1.6 + oy), num, 'Помещения_номера', r=0.35)
        # оси: на фасадах — крайние и промежуточные, на разрезах — все
        tags = [(t, c) for t, v, c in axes if (v if axk == 'u' else not v)]
        tags.sort(key=lambda t: t[1] * (r[0] if axk == 'u' else r[1]))
        if cut is None:
            keep = {'Фасад 1–7': ('1', '2', '7'), 'Фасад 7–1': ('7', '1'), 'Фасад А–И': ('А', 'Д', 'И'),
                    'Фасад И–А': ('И', 'Б', 'А')}[title]
            tags = [t for t in tags if t[0] in keep]
        sx = [(t, c * (r[0] if axk == 'u' else r[1])) for t, c in tags]
        for t, x in sx:
            pl(msp, [(x + ox, -1.2 + oy), (x + ox, zmax + 0.3 + oy)], 'Оси')
            axis_bubble(msp, (x + ox, -3.3 + oy), t, 'Оси_марки')
        xsv = [x for _, x in sx]
        for a, b in zip(xsv, xsv[1:]):
            dim(msp, (a + ox, -1.5 + oy), (b + ox, -1.5 + oy), (ox, -2.0 + oy), 'Размеры')
        if len(xsv) > 2:
            dim(msp, (xsv[0] + ox, -1.5 + oy), (xsv[-1] + ox, -1.5 + oy), (ox, -2.6 + oy), 'Размеры')
        # отметки
        roof = max(L[:, 2].max() for cls, e, L, F in items if SI.kind(cls, e) == 'roof')
        xl, xr = x0 - 2.0 + ox, x1 + 2.0 + ox
        for z in (0.0, -0.5, zmax):
            level_mark(msp, xl, z + oy, round(z, 3), 'left', 'Отметки')
        level_mark(msp, xr, roof + oy, round(roof, 3), 'right', 'Отметки')
        text(msp, title, (ox + (x0 + x1) / 2, oy + zmax + 1.6), 0.5, 'Надписи')
        info[title] = (round(x1 - x0, 2), round(zmax, 3))
    clean_meta.save_dxf(doc, out_dxf)
    return info


# --- СПОЗУ ------------------------------------------------------------------------------------------------------------
def spozu(osm_path, areas_path, ar_path, out_dxf):
    import situation
    import scheme_booklet as SB
    g = situation.build(osm_path, areas_path)
    A = json.load(open(areas_path))
    doc = new_doc()
    msp = doc.modelspace()
    dimstyle(doc, 'СПОЗУ', h=1.0, factor=1.0, arrow=0.6)
    doc.dimstyles.get('СПОЗУ').dxf.dimdec = 1
    doc.dimstyles.get('СПОЗУ').dxf.dimdsep = ord(',')
    L = {k: lay(doc, k, c, lw) for k, c, lw in (
        ('Граница участка', 5, 50), ('Объект реконструкции', 30, 50), ('Опорная застройка', 8, 25),
        ('Проезжая часть', 9, 18), ('Пешеходные дорожки', 8, 13), ('Красные линии', 1, 35),
        ('Покрытие асфальтобетон', 252, 13), ('Полоса для пожарной техники', 1, 25),
        ('Места установки пожарной техники', 1, 25), ('Приобъектная парковка', 5, 25),
        ('Движение легкового транспорта', 5, 35), ('Движение грузового транспорта', 6, 35),
        ('Движение пожарной техники', 1, 35), ('Движение пешеходов', 3, 25), ('Размеры', 7, 13),
        ('Подписи', 7, 18))}
    W = lambda uv: frame.l2w(np.asarray(uv, float))  # noqa: E731
    _u = W([(1.0, 0.0)])[0] - W([(0.0, 0.0)])[0]
    ROT = float(np.degrees(np.arctan2(_u[1], _u[0])))      # направление оси u (вдоль шоссе) в МСК
    site = g['site']
    win = Polygon(W([(-62.0, -48.0), (112.0, -48.0), (112.0, 62.0), (-62.0, 62.0)]))   # окно схемы М 1:500
    lay(doc, 'Рамка', 7, 35)
    pl(msp, list(win.exterior.coords)[:-1], 'Рамка', True)
    clip = lambda geom: geom.intersection(win)  # noqa: E731
    outline(msp, site, 'Граница участка')
    # объект — контур застройки по модели (наружный контур с крыльцами)
    f, items = SI.load(ar_path)
    fps = []
    for cls, e, Lc, F in items:
        k = SI.kind(cls, e)
        if k in ('roof', 'ceiling') or (Lc[:, 2].min() > 0.5 and cls not in ('IfcWall', 'IfcColumn')):
            continue
        ps = [Polygon(t[:, :2]) for t in Lc[F]]
        fps.append(unary_union([p for p in ps if p.is_valid and p.area > 1e-7]).buffer(0))
    fp_local = unary_union(fps).buffer(0.01).buffer(-0.01).simplify(0.01)
    fp_world = Polygon(W(np.array(fp_local.exterior.coords)))
    pl(msp, list(fp_world.exterior.coords)[:-1], 'Объект реконструкции', True)
    hatch(msp, fp_world, 'Объект реконструкции', 30, transparency=0.5)
    pave = site.difference(fp_world)
    hatch(msp, pave, 'Покрытие асфальтобетон', 252, transparency=0.6)
    outline(msp, pave, 'Покрытие асфальтобетон')
    for poly, num in g['buildings']:
        q = clip(poly)
        if q.is_empty:
            continue
        outline(msp, q, 'Опорная застройка')
        if num and q.area > 30:
            c = q.representative_point()
            text(msp, num, (c.x, c.y), 2.0, 'Подписи')
    roads = unary_union([ls.buffer(situation.WIDTH.get(kind, 5.5) / 2, cap_style=2, join_style=2)
                         for ls, kind, name, oneway, wid in g['roads']])
    outline(msp, clip(roads.boundary), 'Проезжая часть')
    for ls in g['foot']:
        outline(msp, clip(ls), 'Пешеходные дорожки')
    ru = np.array([-62.0, 112.0])
    pl(msp, W(np.c_[ru, SB.RED['b'] + SB.RED['k'] * ru]), 'Красные линии')
    # север
    nb = W([(100.0, 45.0)])[0]
    pl(msp, [(nb[0], nb[1] - 4), (nb[0], nb[1] + 4)], 'Подписи')
    pl(msp, [(nb[0] - 1.2, nb[1] + 1.8), (nb[0], nb[1] + 4), (nb[0] + 1.2, nb[1] + 1.8)], 'Подписи')
    text(msp, 'С', (nb[0], nb[1] + 5.5), 2.0, 'Подписи')
    # пожарная полоса и места установки
    lane = [(SB.LANE_U0, 0.6), (SB.LANE_U1, 0.6), (SB.LANE_U1, SB.B_N + 3.0), (SB.LANE_U0, SB.B_N + 3.0)]
    pl(msp, W(lane), 'Полоса для пожарной техники', True)
    lane_c = (SB.LANE_U0 + SB.LANE_U1) / 2
    for vc in (7.5, 21.0):
        q = [(lane_c - 1.25, vc - 4), (lane_c + 1.25, vc - 4), (lane_c + 1.25, vc + 4), (lane_c - 1.25, vc + 4)]
        pl(msp, W(q), 'Места установки пожарной техники', True)
        h = msp.add_hatch(color=1, dxfattribs={'layer': 'Места установки пожарной техники'})
        h.set_pattern_fill('ANSI31', scale=0.2)
        h.paths.add_polyline_path([tuple(map(float, p)) for p in W(q)], is_closed=True)
    # парковка
    for kind, u0, u1, vtop in SB.PARKING:
        q = [(u0, SB.PARK_V0), (u1, SB.PARK_V0), (u1, vtop), (u0, vtop)]
        pl(msp, W(q), 'Приобъектная парковка', True)
        c = W([((u0 + u1) / 2, (SB.PARK_V0 + vtop) / 2)])[0]
        text(msp, {'mgn': 'МГН', 'std': 'P', 'ev': 'ЭЗС'}[kind], c, 0.9, 'Приобъектная парковка', rot=ROT)
    # маршруты (как на листе буклета)
    left = -34.0
    R = {
        'Движение пожарной техники': [(left, SB.V_FIRE), (-9.0, SB.V_FIRE), (-6.2, -3.4), (lane_c, 1.6),
                                      (lane_c, SB.B_N + 1.2), (lane_c - 2.6, SB.B_N + 3.7), (-40.0, SB.B_N + 3.9)],
        'Движение грузового транспорта': [(left, SB.V_TRUCK), (SB.EAST_U - 2.5, SB.V_TRUCK),
                                          (SB.EAST_U, SB.V_TRUCK + 2.5), (SB.EAST_U, SB.GATE[1] - 2.5),
                                          (SB.EAST_U - 2.5, SB.GATE[1]), SB.GATE, (31.0, SB.GATE[1] + 0.6)],
        'Движение легкового транспорта': [(left, SB.FRONT_V), (47.0, SB.FRONT_V)],
    }
    for ly, uv in R.items():
        pl(msp, W(uv), ly)
    for uv in ([(-9.5, -1.5), (2.0, -1.5), (4.6, 0.9)],
               [(70.0, -21.0), (61.0, -9.6), (58.5, -1.5), (9.0, -1.5), (6.4, 0.6)]):
        pl(msp, W(uv), 'Движение пешеходов')
    # размеры
    def wdim(a, b, off):
        pa, pb = W([a])[0], W([b])[0]
        dv = pb - pa
        ang = np.degrees(np.arctan2(dv[1], dv[0]))
        n = np.array([-dv[1], dv[0]]) / np.linalg.norm(dv)
        base = (pa + pb) / 2 + n * off
        d = msp.add_linear_dim(base=tuple(base), p1=tuple(pa), p2=tuple(pb), angle=ang, dimstyle='СПОЗУ',
                               dxfattribs={'layer': 'Размеры'})
        d.render()
    wdim((SB.LANE_U0, 26.5), (SB.LANE_U1, 26.5), 1.5)
    wdim((SB.LANE_U1, 14.0), (SB.B_W, 14.0), 1.5)
    wdim((8.4, -9.6), (14.4, -9.6), -1.5)
    wdim((14.4, SB.PARK_V0), (14.4, -4.7), 1.5)
    # подписи
    c = W([(12.5, 13.5)])[0]
    text(msp, 'Магазин (реконструкция), 1 этаж', c, 1.2, 'Подписи', rot=ROT)
    text(msp, 'проезд пожарной техники', W([(lane_c - 3.5, 12.0)])[0], 0.9, 'Подписи', rot=ROT + 90)
    text(msp, 'ворота', W([(SB.GATE[0], SB.GATE[1] - 3.0)])[0], 0.9, 'Подписи', rot=ROT)
    text(msp, 'Щёлковское шоссе (дублёр)', W([(30.0, -20.0)])[0], 2.0, 'Подписи', rot=ROT)
    clean_meta.save_dxf(doc, out_dxf)
    return dict(site=site.area, building=fp_world.area, pave=pave.area)


# --- таблица площадей -------------------------------------------------------------------------------------------------
def xlsx(info, out_xlsx):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
    wb = Workbook()
    ws = wb.active
    ws.title = 'Расчёт площадей'
    thin = Side(style='thin', color='999999')
    br = Border(left=thin, right=thin, top=thin, bottom=thin)
    ws.append(['Реконструкция нежилого здания под магазин, г. Москва, Щёлковское шоссе, вл. 17А, стр. 1'])
    ws.append(['Таблица расчёта суммарной поэтажной площади и нежилой наземной площади (по заливкам схемы плана 1 этажа)'])
    ws.append([])
    ws.append(['Этаж', 'Показатель', 'Слой DWG', 'Площадь, м²', 'Примечание'])
    hdr = ws.max_row
    rows = [
        ('1 этаж', 'Суммарная поэтажная площадь в габаритах наружных стен (СПП в ГНС), нежилое здание', 'spp2',
         info['spp'], 'по наружному контуру наружных стен'),
        ('1 этаж', 'Нежилая наземная площадь отдельно стоящего нежилого здания (ННП)', 's3', None,
         'сумма строк ниже'),
    ]
    for r in rows:
        ws.append(list(r))
    nnp_row = ws.max_row
    first = ws.max_row + 1
    for nm, a in zip(info['names'], info['parts']):
        ws.append(['', '   в т. ч. ' + nm, 's3', a, ''])
    last = ws.max_row
    ws.cell(nnp_row, 4).value = '=SUM(D%d:D%d)' % (first, last)
    ws.append(['1 этаж', 'Наземная площадь (НП)', 's3', '=D%d' % nnp_row, 'равна ННП: жилых помещений нет'])
    ws.append(['1 этаж', 'Общая площадь объекта', 's3', '=D%d' % nnp_row, 'подземных этажей нет'])
    ws.append(['1 этаж', 'Площадь помещений (справочно)', '—', "='Экспликация'!C13",
               'по экспликации, 11 помещений'])
    ws.append(['', 'Общая площадь квартир, площадь квартир, количество квартир', '—', '—', 'жилых помещений нет'])
    for row in ws.iter_rows(min_row=hdr, max_row=ws.max_row, max_col=5):
        for c in row:
            c.border = br
            c.alignment = Alignment(wrap_text=True, vertical='center')
            if c.column == 4 and c.row > hdr:
                c.number_format = '0.00'
    for c in ws[hdr]:
        c.font = Font(bold=True)
        c.fill = PatternFill('solid', fgColor='FACACD')
    ws['A1'].font = Font(bold=True)
    for col, w in zip('ABCDE', (10, 70, 10, 14, 34)):
        ws.column_dimensions[col].width = w
    ws2 = wb.create_sheet('Экспликация')
    ws2.append(['№', 'Наименование помещения', 'Площадь, м²'])
    for num, nm, a, _ in sorted(info['rooms']):
        ws2.append([num, nm, round(a, 2)])               # площади помещений округляются до 0,01 м², как в экспликации
    ws2.append(['', 'Итого', '=SUM(C2:C%d)' % ws2.max_row])
    for row in ws2.iter_rows(min_row=1, max_row=ws2.max_row, max_col=3):
        for c in row:
            c.border = br
            if c.column == 3 and c.row > 1:
                c.number_format = '0.00'
    for c in ws2[1]:
        c.font = Font(bold=True)
    ws2.column_dimensions['B'].width = 60
    ws2.column_dimensions['C'].width = 14
    wb.save(out_xlsx)
    clean_meta.clean(out_xlsx)


def main(ar, bio, osm, outdir):
    os.makedirs(outdir, exist_ok=True)
    areas = os.path.join(HERE, 'out_ifc2', 'areas.json')
    info = plan(ar, areas, os.path.join(outdir, 'План_1_этажа.dxf'))
    print('план: spp2 %.3f, s3 %.3f, внутр. контур %.3f' % (info['spp'], info['nnp'], info['inner']))
    xlsx(info, os.path.join(outdir, 'Расчет_площадей.xlsx'))
    print('разрезы и фасады:', sections_facades(ar, bio, os.path.join(outdir, 'Разрезы_и_фасады.dxf')))
    print('СПОЗУ:', spozu(osm, areas, ar, os.path.join(outdir, 'СПОЗУ.dxf')))


if __name__ == '__main__':
    main(*sys.argv[1:5])
