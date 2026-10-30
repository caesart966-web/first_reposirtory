"""И05.09.26-ВК: 3D-модель систем В1, Т3, Т4, К1 дома и бани — выгрузка для просмотра в браузере, DWG (через DXF)
и IFC4. Источник — vk_model (тот же, что у листов и ВК.СО). Баня — на своём месте по ГП01 (сдвиг осей BX, BY),
трубы котельной ТМ — серым для увязки (out/tm/tm.json).

python3 vk_3d.py -> out/vk3d/model.json, I05-09-26-VK-3D.dxf, I05-09-26-VK-3D.ifc
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'sheets'))
import vk_model as VK  # noqa: E402

OUT = os.path.join(HERE, 'out', 'vk3d')
BX, BY = 7.132, 25.000             # оси 1/А бани в осях дома (ГП01, как ov_site.py)
SYS = {
    'В1': ('В1 — водопровод хозяйственно-питьевой', (6, 182, 212)),
    'Т3': ('Т3 — горячая вода', (22, 163, 74)),
    'Т4': ('Т4 — циркуляция ГВС', (132, 204, 22)),
    'К1': ('К1 — канализация бытовая', (194, 65, 12)),
    'К1в': ('К1в — вытяжные части стояков', (161, 98, 7)),
    'К2': ('К2 — от лотка гаража в ливневую сеть', (37, 99, 235)),
    'EQ': ('Оборудование и шкафы', (226, 232, 240)),
    'AR': ('Арматура', (180, 140, 60)),
    'TM': ('Трубы котельной ТМ — для увязки', (190, 196, 206)),
}
COLL_IDS = ('КХ',) + tuple(c + s for c in ('ШВК-1', 'ШВК-2', 'ШВК-Б1', 'ШВК-Б2') for s in ('В', 'Т'))


def sh(p, bld):
    """Точка в осях дома (баня — со сдвигом по ГП01)."""
    return (p[0] + BX, p[1] + BY, p[2]) if bld == 'b' else tuple(p)


def floor_of(pts, bld):
    if bld == 'b':
        return 3
    zs = [q[2] for q in pts]
    return 2 if sum(zs) / len(zs) > VK.SLAB2_TOP - 0.05 else 1


def fit_parts(f):
    """Арматура → примитивы ('cyl', p0, p1, d, rgb)."""
    ax = {'x': (1, 0, 0), 'y': (0, 1, 0), 'z': (0, 0, 1)}[f.axis]
    c = f.pos
    d = f.od

    def along(L, dia, rgb, off=0.0):
        return ('cyl', tuple(c[k] + ax[k] * (off - L / 2) for k in range(3)),
                tuple(c[k] + ax[k] * (off + L / 2) for k in range(3)), dia, rgb)
    side = f.side or ('+z' if f.axis != 'z' else '-y')
    sd = {'+x': (1, 0, 0), '-x': (-1, 0, 0), '+y': (0, 1, 0), '-y': (0, -1, 0), '+z': (0, 0, 1), '-z': (0, 0, -1)}[side]

    def stub(L, dia, rgb, start=0.0):
        return ('cyl', tuple(c[k] + sd[k] * start for k in range(3)), tuple(c[k] + sd[k] * (start + L) for k in range(3)),
                dia, rgb)
    brass, dark, white, grey = (191, 145, 66), (30, 41, 59), (241, 245, 249), (120, 113, 108)
    hcol = SYS[f.sys][1]
    k = f.kind
    if k == 'ball':
        return [along(max(0.05, d * 2.0), d * 1.45, brass), stub(0.03, 0.010, brass, d * 0.7),
                stub(0.010, 0.07, hcol, d * 0.7 + 0.03)]
    if k == 'check':
        return [along(max(0.05, d * 1.8), d * 1.5, brass)]
    if k == 'mvalve':                                   # кран с электроприводом: корпус крана + блок привода
        return [along(max(0.05, d * 2.0), d * 1.45, brass), stub(0.03, 0.012, brass, d * 0.7),
                stub(0.06, 0.07, (71, 85, 105), d * 0.7 + 0.03)]
    if k == 'balance':
        return [along(0.07, d * 1.5, brass), stub(0.05, 0.03, (59, 130, 246), d * 0.7)]
    if k in ('filter', 'filter_fine'):
        return [along(0.07, d * 1.5, brass), stub(0.06 if k == 'filter' else 0.16, d * 1.2 if k == 'filter' else 0.06,
                                                   brass if k == 'filter' else (203, 213, 225), d * 0.5)]
    if k == 'reducer':
        return [along(0.07, d * 1.6, brass), stub(0.06, 0.05, brass, d * 0.6)]
    if k == 'meter':
        return [along(0.11, d * 1.6, brass), stub(0.03, 0.07, (37, 99, 235), d * 0.7)]
    if k == 'pump':
        return [along(0.14, d * 2.4, dark), stub(0.09, 0.08, (0, 128, 120), d)]
    if k == 'mano':
        return [stub(0.05, 0.012, brass, d / 2), stub(0.025, 0.063, white, d / 2 + 0.05)]
    if k == 'air':
        return [stub(0.03, 0.014, brass, d / 2)]
    if k == 'safety':
        return [along(0.08, d * 1.4, brass), stub(0.06, 0.03, brass, d * 0.6)]
    if k == 'tap':
        return [stub(0.08, 0.02, brass, d / 2), stub(0.02, 0.04, brass, d / 2 + 0.08)]
    if k == 'revision':
        return [along(0.16, d * 1.18, grey)]
    if k == 'cleanout':
        return [along(0.10, d * 1.15, grey)]
    return [along(0.05, d * 1.4, brass)]


def tm_context():
    path = os.path.join(HERE, 'out', 'tm', 'tm.json')
    if not os.path.exists(path):
        return []
    tm = json.load(open(path))
    out = []
    for p in tm['pipes']:
        if p['sys'] in ('Г', 'Д'):
            continue
        for a, b in zip(p['pts'], p['pts'][1:]):
            if math.dist(a, b) > 1e-6:
                out.append({'name': f'ТМ: {p["name"]}', 'seg': (a, b), 'w': p['od']})
    return out


def export_view(walls):
    data = {'title': 'И05.09.26-ВК. Водопровод и канализация дома и бани — 3D-модель',
            'systems': {k: {'name': v[0], 'rgb': list(v[1])} for k, v in SYS.items()},
            'walls': walls, 'slabs': [], 'runs': [], 'boxes': [], 'labels': [], 'views': 'vk'}
    for p in VK.PIPES:
        pts = [sh(q, p.bld) for q in p.pts]
        segs = [[*map(lambda v: round(v, 4), a), *map(lambda v: round(v, 4), b), round(p.od, 4), round(p.od, 4), 0]
                for a, b in zip(pts, pts[1:]) if math.dist(a, b) > 1e-6]
        data['runs'].append({'id': p.id, 'sys': p.sys, 'name': p.name, 'sec': p.label(), 'kind': 'pipe',
                             'floor': floor_of(p.pts, p.bld), 'segs': segs, 'L': None})
    for f in VK.FITS:
        for part in fit_parts(f):
            _, p0, p1, dia, rgb = part
            p0, p1 = sh(p0, f.pipe.bld), sh(p1, f.pipe.bld)
            data['runs'].append({'id': f.name, 'sys': 'AR', 'name': f.name, 'sec': f.pipe.label(), 'kind': 'fit',
                                 'floor': floor_of([f.pos], f.pipe.bld),
                                 'segs': [[*map(lambda v: round(v, 4), p0), *map(lambda v: round(v, 4), p1),
                                           round(dia, 4), round(dia, 4), 0]], 'rgb': list(rgb), 'L': None})
    for e in VK.EQUIP:
        b = e.bbox()
        b0, b1 = sh(b[:3], e.bld), sh(b[3:], e.bld)
        fl = floor_of([b[:3]], e.bld)
        rgb = (203, 213, 225) if e.ctx else (226, 232, 240)
        if e.kind == 'cyl':
            cx, cy, r, z0, z1 = e.g
            c0 = sh((cx, cy, z0), e.bld)
            data['runs'].append({'id': e.id, 'sys': 'EQ', 'name': e.name, 'sec': '', 'kind': 'equip', 'floor': fl,
                                 'segs': [[c0[0], c0[1], z0, c0[0], c0[1], z1, round(2 * r, 4), round(2 * r, 4), 0]],
                                 'rgb': list(rgb), 'L': None})
        elif e.id != 'КХ':
            data['boxes'].append({'id': e.id, 'sys': 'EQ', 'kind': 'unit', 'name': e.name, 'floor': fl,
                                  'b': [round(v, 4) for v in (*b0, *b1)], 'rgb': list(rgb), 'L': None})
        data['labels'].append({'x': round((b0[0] + b1[0]) / 2, 3), 'y': round((b0[1] + b1[1]) / 2, 3),
                               'z': round(b1[2] + 0.12, 3), 'text': e.mark, 'sys': 'EQ', 'floor': fl,
                               'rgb': [30, 41, 59]})
    for k, fx in VK.FIXT.items():
        z = (VK.FL2 if fx.floor == 2 else 0.0) + 0.9
        q = sh((fx.pos[0], fx.pos[1], z), fx.bld)
        data['labels'].append({'x': round(q[0], 3), 'y': round(q[1], 3), 'z': round(q[2], 3), 'text': k, 'sys': 'EQ',
                               'floor': 3 if fx.bld == 'b' else fx.floor, 'rgb': [71, 85, 105]})
    for c in tm_context():
        a, b = c['seg']
        data['runs'].append({'id': c['name'], 'sys': 'TM', 'name': c['name'], 'sec': '', 'kind': 'ctx', 'floor': 1,
                             'segs': [[*map(lambda v: round(v, 4), a), *map(lambda v: round(v, 4), b),
                                       round(c['w'], 4), round(c['w'], 4), 0]], 'L': None})
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'model.json'), 'w') as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(',', ':'))
    return data


def walls():
    """Стены по АР: 1 и 2 этажи дома, баня (штриховки A-WALL-PATT, через model3d.walls)."""
    import model3d as m3
    m3.WITH_BATH = True
    W = m3.walls()
    out = []
    for fl, (z0, z1) in ((1, (0.0, VK.CEIL1)), (2, (VK.FL2, VK.ROOF_SLAB)), (3, (0.0, VK.B_ROOF_TOP - 0.25))):
        for g in m3.geoms(W[{1: 1, 2: 2, 3: m3.BATH}[fl]]):
            if g.is_empty or g.area < 1e-4 or g.geom_type != 'Polygon':
                continue
            out.append({'floor': fl, 'z0': z0, 'z1': z1,
                        'outer': [[round(x, 4), round(y, 4)] for x, y in g.exterior.coords[:-1]],
                        'holes': [[[round(x, 4), round(y, 4)] for x, y in h.coords[:-1]] for h in g.interiors]})
    return out


LAY = {'В1': ('ВК_3D_В1', 4), 'Т3': ('ВК_3D_Т3', 3), 'Т4': ('ВК_3D_Т4', 82), 'К1': ('ВК_3D_К1', 30),
       'К1в': ('ВК_3D_К1в', 32), 'К2': ('ВК_3D_К2', 5), 'EQ': ('ВК_3D_Оборудование', 9), 'AR': ('ВК_3D_Арматура', 42),
       'TM': ('ТМ_3D_для_увязки', 253)}


def export_dxf(data):
    import ezdxf
    from model3d import seg_mesh, box_mesh, prism_mesh
    doc = ezdxf.new('R2018', setup=True)
    doc.units = 4
    doc.header['$INSUNITS'] = 4
    doc.header['$LASTSAVEDBY'] = ''
    msp = doc.modelspace()
    for k, (nm, aci) in LAY.items():
        lay = doc.layers.add(nm, color=aci)
        lay.rgb = SYS[k][1]
    doc.layers.add('АР_3D_стены', color=8)
    doc.layers.add('ВК_3D_Марки', color=7)

    def poly(V, F, layer, rgb=None):
        m = msp.add_polyface(dxfattribs={'layer': layer})
        m.append_faces([[tuple(c * 1000 for c in V[i]) for i in f] for f in F])
        m.optimize()
        if rgb:
            m.rgb = tuple(rgb)
    for wl in data['walls']:
        V, F = prism_mesh(wl['outer'], wl['holes'], wl['z0'], wl['z1'])
        poly(V, F, 'АР_3D_стены')
    for r in data['runs']:
        for s in r['segs']:
            p0, p1, w, h, rect = s[:3], s[3:6], s[6], s[7], s[8]
            if math.dist(p0, p1) < 1e-6:
                continue
            ext = w / 2 if r['kind'] == 'pipe' else 0.0
            n = 10 if r['kind'] in ('pipe', 'fit', 'ctx') else 24
            V, F = seg_mesh(p0, p1, w, h, rect, min(ext, 0.03), n=n)
            poly(V, F, LAY[r['sys']][0], r.get('rgb') if r['sys'] in ('AR', 'EQ') else None)
    for b in data['boxes']:
        V, F = box_mesh(b['b'])
        poly(V, F, LAY[b['sys']][0], b.get('rgb'))
    for lb in data['labels']:
        msp.add_text(lb['text'], dxfattribs={'layer': 'ВК_3D_Марки', 'height': 70,
                                            'insert': (lb['x'] * 1000, lb['y'] * 1000, lb['z'] * 1000)})
    doc.set_modelspace_vport(height=40000, center=(14000, 18000))
    path = os.path.join(OUT, 'I05-09-26-VK-3D.dxf')
    doc.saveas(path)
    return path


FIT_IFC = {'ball': ('IfcValve', 'ISOLATING'), 'check': ('IfcValve', 'CHECK'), 'balance': ('IfcValve', 'REGULATING'),
           'safety': ('IfcValve', 'SAFETYCUTOFF'), 'reducer': ('IfcValve', 'PRESSUREREDUCING'),
           'air': ('IfcValve', 'AIRRELEASE'), 'tap': ('IfcValve', 'FAUCET'), 'filter': ('IfcFilter', 'STRAINER'),
           'filter_fine': ('IfcFilter', 'WATERFILTER'), 'pump': ('IfcPump', 'CIRCULATOR'),
           'mano': ('IfcFlowInstrument', 'PRESSUREGAUGE'), 'meter': ('IfcFlowMeter', 'WATERMETER'),
           'revision': ('IfcPipeFitting', 'NOTDEFINED'), 'cleanout': ('IfcPipeFitting', 'NOTDEFINED')}
SYS_IFC = {'К2': 'STORMWATER', 'Т3': 'DOMESTICHOTWATER', 'Т4': 'DOMESTICHOTWATER', 'В1': 'DOMESTICCOLDWATER', 'К1': 'DRAINAGE',
           'К1в': 'VENT'}
MAT_NAME = {'pex': 'PE-Xa (ГОСТ 32415)', 'pe': 'ПЭ 100 SDR11 (ГОСТ 18599)', 'pp': 'ПП канализационная (ГОСТ 32414)',
            'ppn': 'ПП наружная SN8 (ГОСТ 32413)', 'sml': 'Чугун безраструбный SML (Smart SML)'}


def export_ifc(data):
    import ifcopenshell
    import ifcopenshell.api
    from model3d import frame
    from underlay import OX, OY
    api = ifcopenshell.api.run
    f = ifcopenshell.file(schema='IFC4')
    proj = api('root.create_entity', f, ifc_class='IfcProject', name='И05.09.26-ВК')
    api('unit.assign_unit', f, length={'is_metric': True, 'raw': 'METRE'})
    ctx = api('context.add_context', f, context_type='Model')
    body = api('context.add_context', f, context_type='Model', context_identifier='Body', target_view='MODEL_VIEW',
               parent=ctx)
    site = api('root.create_entity', f, ifc_class='IfcSite', name='Участок 50:08:0050209:1600')
    house = api('root.create_entity', f, ifc_class='IfcBuilding', name='Жилой дом')
    bath = api('root.create_entity', f, ifc_class='IfcBuilding', name='Баня')
    st = {1: api('root.create_entity', f, ifc_class='IfcBuildingStorey', name='Этаж 1'),
          2: api('root.create_entity', f, ifc_class='IfcBuildingStorey', name='Этаж 2'),
          3: api('root.create_entity', f, ifc_class='IfcBuildingStorey', name='Баня, этаж 1')}
    api('aggregate.assign_object', f, relating_object=proj, products=[site])
    api('aggregate.assign_object', f, relating_object=site, products=[house, bath])
    api('aggregate.assign_object', f, relating_object=house, products=[st[1], st[2]])
    api('aggregate.assign_object', f, relating_object=bath, products=[st[3]])
    for obj in (site, house, bath, *st.values()):
        api('geometry.edit_object_placement', f, product=obj)
    house.ObjectPlacement.RelativePlacement.Location.Coordinates = (OX / 1000, OY / 1000, 0.0)
    house.ObjectPlacement.PlacementRelTo = site.ObjectPlacement
    bath.ObjectPlacement.RelativePlacement.Location.Coordinates = (OX / 1000, OY / 1000, 0.0)
    bath.ObjectPlacement.PlacementRelTo = site.ObjectPlacement
    for k, s in st.items():
        s.ObjectPlacement.PlacementRelTo = (bath if k == 3 else house).ObjectPlacement
    st[1].Elevation, st[2].Elevation, st[3].Elevation = 0.0, VK.FL2, 0.0

    def ax(p, z=(0.0, 0.0, 1.0), x=(1.0, 0.0, 0.0)):
        return f.createIfcAxis2Placement3D(f.createIfcCartesianPoint(tuple(map(float, p))),
                                           f.createIfcDirection(tuple(map(float, z))),
                                           f.createIfcDirection(tuple(map(float, x))))
    styles = {}

    def style(rgb, tr=0.0):
        k = (tuple(rgb), tr)
        if k not in styles:
            col = f.createIfcColourRgb(None, *(c / 255 for c in rgb))
            styles[k] = f.createIfcSurfaceStyle(None, 'BOTH', [f.createIfcSurfaceStyleShading(col, tr)])
        return styles[k]

    def shape(items, rgb, tr=0.0):
        for it in items:
            f.createIfcStyledItem(it, [style(rgb, tr)], None)
        rep = f.createIfcShapeRepresentation(body, 'Body', 'SweptSolid', items)
        return f.createIfcProductDefinitionShape(None, None, [rep])

    def cyl(p0, p1, dia):
        t, u, v, L = frame(p0, p1)
        prof = f.createIfcCircleProfileDef('AREA', None, f.createIfcAxis2Placement2D(
            f.createIfcCartesianPoint((0.0, 0.0)), None), float(dia / 2))
        return f.createIfcExtrudedAreaSolid(prof, ax(p0, t, u), f.createIfcDirection((0.0, 0.0, 1.0)), float(L))

    def boxs(b):
        x0, y0, z0, x1, y1, z1 = b
        prof = f.createIfcRectangleProfileDef('AREA', None, f.createIfcAxis2Placement2D(
            f.createIfcCartesianPoint(((x1 - x0) / 2, (y1 - y0) / 2)), None), float(x1 - x0), float(y1 - y0))
        return f.createIfcExtrudedAreaSolid(prof, ax((x0, y0, z0)), f.createIfcDirection((0.0, 0.0, 1.0)),
                                            float(max(z1 - z0, 0.001)))

    def poly_solid(outer, holes, z0, z1):
        def curve(pts):
            P = [f.createIfcCartesianPoint((float(x), float(y))) for x, y in pts]
            return f.createIfcPolyline(P + [P[0]])
        prof = (f.createIfcArbitraryProfileDefWithVoids('AREA', None, curve(outer), [curve(h) for h in holes]) if holes
                else f.createIfcArbitraryClosedProfileDef('AREA', None, curve(outer)))
        return f.createIfcExtrudedAreaSolid(prof, ax((0.0, 0.0, z0)), f.createIfcDirection((0.0, 0.0, 1.0)),
                                            float(z1 - z0))

    def place(prod, fl):
        # координаты модели — в осях дома (баня уже сдвинута), поэтому размещение — от здания «дом» для всех
        prod.ObjectPlacement = f.createIfcLocalPlacement(house.ObjectPlacement, ax((0.0, 0.0, 0.0)))

    def pset(prod, props):
        ps = api('pset.add_pset', f, product=prod, name='ВК_Параметры')
        api('pset.edit_pset', f, pset=ps, properties={k: v for k, v in props.items() if v not in (None, '')})

    cont = {1: [], 2: [], 3: []}
    by_sys = {}
    for wl in data['walls']:
        w = api('root.create_entity', f, ifc_class='IfcWall', name='Стена по АР (для привязки)')
        w.Representation = shape([poly_solid(wl['outer'], wl['holes'], wl['z0'], wl['z1'])], (217, 217, 209), 0.55)
        place(w, wl['floor'])
        cont[wl['floor']].append(w)
    for p in VK.PIPES:
        fl = floor_of(p.pts, p.bld)
        e = api('root.create_entity', f, ifc_class='IfcPipeSegment', name=p.name)
        e.Tag = p.id
        pts = [sh(q, p.bld) for q in p.pts]
        e.Representation = shape([cyl(a, b, p.od) for a, b in zip(pts, pts[1:]) if math.dist(a, b) > 1e-6],
                                 SYS[p.sys][1])
        place(e, fl)
        cont[fl].append(e)
        by_sys.setdefault(p.sys, []).append(e)
        pset(e, {'Система': SYS[p.sys][0], 'Материал': MAT_NAME.get(p.mat, p.mat), 'Типоразмер': p.label(),
                 'Длина, м': round(p.length(), 2), 'Прокладка': p.where, 'Здание': 'баня' if p.bld == 'b' else 'дом'})
    for fi in VK.FITS:
        fl = floor_of([fi.pos], fi.pipe.bld)
        cls, pt = FIT_IFC.get(fi.kind, ('IfcValve', 'NOTDEFINED'))
        e = api('root.create_entity', f, ifc_class=cls, name=fi.name)
        e.PredefinedType = pt
        solids, rgb = [], None
        for part in fit_parts(fi):
            _, p0, p1, dia, c = part
            p0, p1 = sh(p0, fi.pipe.bld), sh(p1, fi.pipe.bld)
            if math.dist(p0, p1) > 1e-6:
                solids.append(cyl(p0, p1, dia))
                rgb = rgb or c
        e.Representation = shape(solids, rgb or (180, 140, 60))
        place(e, fl)
        cont[fl].append(e)
        by_sys.setdefault(fi.sys, []).append(e)
        pset(e, {'Система': SYS[fi.sys][0], 'Типоразмер': fi.pipe.label(), 'Трубопровод': fi.pipe.name})
    for q in VK.EQUIP:
        fl = floor_of([q.bbox()[:3]], q.bld)
        e = api('root.create_entity', f, ifc_class='IfcTank' if q.kind == 'cyl' else 'IfcDistributionElement',
                name=q.name)
        e.Tag = q.mark
        b = q.bbox()
        b0, b1 = sh(b[:3], q.bld), sh(b[3:], q.bld)
        if q.kind == 'cyl':
            cx, cy, r, z0, z1 = q.g
            c0 = sh((cx, cy, z0), q.bld)
            sol = [cyl(c0, (c0[0], c0[1], z1), 2 * r)]
        else:
            sol = [boxs((*b0, *b1))]
        e.Representation = shape(sol, (203, 213, 225) if q.ctx else (226, 232, 240), 0.4 if q.ctx else 0.0)
        place(e, fl)
        cont[fl].append(e)
        pset(e, {'Марка': q.mark, 'Раздел': 'смежный раздел (контекст)' if q.ctx else 'ВК'})
    for k, objs in cont.items():
        if objs:
            api('spatial.assign_container', f, relating_structure=st[k], products=objs)
    for k, objs in by_sys.items():
        if k not in SYS_IFC:
            continue
        s = api('system.add_system', f, ifc_class='IfcDistributionSystem')
        s.Name = SYS[k][0]
        s.PredefinedType = SYS_IFC[k]
        api('system.assign_system', f, products=objs, system=s)
    path = os.path.join(OUT, 'I05-09-26-VK-3D.ifc')
    f.write(path)
    return path


def main():
    data = export_view(walls())
    print('runs', len(data['runs']), 'boxes', len(data['boxes']), 'walls', len(data['walls']))
    if '--no-export' not in sys.argv:
        print(export_dxf(data))
        print(export_ifc(data))


if __name__ == '__main__':
    main()
