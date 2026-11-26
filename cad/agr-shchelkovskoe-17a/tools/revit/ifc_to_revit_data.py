"""Данные для пересборки ЦИМ АР в Revit из исправленного IFC (тот же объект, те же параметры).

    python3 ifc_to_revit_data.py <AR.ifc> <куда>

Пишет:
  * ar_model.json  — всё, что читает build_ar_pyrevit.py: координаты (точка и поворот МСК-77), уровни, оси,
    элементы (класс IFC, тип, уровень, сетка в локальных координатах проекта, мм; наборы RusSet_*),
    помещения и зоны (контуры, высота, наборы RusSet_*), сведения о проекте;
  * RusSets_mapping.txt — наборы свойств для экспорта IFC из Revit (пользовательские наборы свойств),
    запасной путь, если у плагина нет своего файла соответствия;
  * RUS_shared_params.txt — файл общих параметров (RUS_*, IfcExportAs, IfcExportType).

Локальные координаты = координаты относительно IfcSite (у этой модели здание и уровни без смещения): в Revit
это внутреннее начало, общие координаты задаются точкой и углом из блока site.
"""
import collections
import json
import math
import os
import sys

import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as ue
import ifcopenshell.util.placement as up
from shapely.geometry import Polygon
from shapely.ops import unary_union

SKIP = ('IfcOpeningElement', 'IfcSpace', 'IfcGrid', 'IfcSite', 'IfcBuildingStorey', 'IfcBuilding', 'IfcAnnotation')
VTYPE = {'IfcText': 'TEXT', 'IfcLabel': 'TEXT', 'IfcIdentifier': 'TEXT', 'IfcReal': 'NUMBER',
         'IfcBoolean': 'YESNO', 'IfcLogical': 'YESNO', 'IfcInteger': 'INTEGER'}


def rus_psets(e):
    out = {}
    for r in getattr(e, 'IsDefinedBy', ()) or ():
        if not r.is_a('IfcRelDefinesByProperties'):
            continue
        p = r.RelatingPropertyDefinition
        if not p.is_a('IfcPropertySet') or not p.Name.startswith('RusSet_'):
            continue
        d = out.setdefault(p.Name, {})
        for x in p.HasProperties:
            v = x.NominalValue
            d[x.Name] = None if v is None else [v.is_a(), v.wrappedValue]
    return out


def storey_of(e):
    for r in getattr(e, 'ContainedInStructure', ()) or ():
        return r.RelatingStructure.Name
    for r in getattr(e, 'Decomposes', ()) or ():
        if r.RelatingObject.is_a('IfcBuildingStorey'):
            return r.RelatingObject.Name
        return storey_of(r.RelatingObject)
    return None


def main(src, out):
    os.makedirs(out, exist_ok=True)
    m = ifcopenshell.open(src)
    site = m.by_type('IfcSite')[0]
    Ms = up.get_local_placement(site.ObjectPlacement)          # мм
    inv = np.linalg.inv(Ms)
    ang = math.degrees(math.atan2(Ms[1, 0], Ms[0, 0]))
    data = {
        'source': os.path.basename(src),
        'units': 'mm',
        'site': {'east_mm': Ms[0, 3], 'north_mm': Ms[1, 3], 'elev_mm': Ms[2, 3],
                 'x_axis_angle_deg_ccw_from_east': ang,
                 'ref_latitude': list(site.RefLatitude), 'ref_longitude': list(site.RefLongitude),
                 'name': site.Name},
        'project': {'name': m.by_type('IfcProject')[0].Name, 'long_name': m.by_type('IfcProject')[0].LongName},
        'building': {'name': m.by_type('IfcBuilding')[0].Name,
                     'psets': rus_psets(m.by_type('IfcBuilding')[0])},
        'levels': [], 'grids': [], 'elements': [], 'spaces': []}
    for s in m.by_type('IfcBuildingStorey'):
        data['levels'].append({'name': s.Name, 'elevation_mm': float(s.Elevation), 'psets': rus_psets(s)})
    seen = set()
    for g in m.by_type('IfcGrid'):
        Mg = inv @ up.get_local_placement(g.ObjectPlacement)
        for ax in list(g.UAxes) + list(g.VAxes):
            if ax.AxisTag in seen:
                continue
            seen.add(ax.AxisTag)
            pts = [list((Mg @ np.array([p[0], p[1], 0, 1]))[:2]) for p in ax.AxisCurve.Points.CoordList]
            data['grids'].append({'tag': ax.AxisTag, 'p0': pts[0], 'p1': pts[-1]})
    st = ifcopenshell.geom.settings()
    st.set('use-world-coords', True)
    ok = collections.Counter()

    def mesh(e):
        sh = ifcopenshell.geom.create_shape(st, e)
        V = np.array(sh.geometry.verts).reshape(-1, 3) * 1000.0
        V = (inv @ np.c_[V, np.ones(len(V))].T).T[:, :3]
        F = np.array(sh.geometry.faces).reshape(-1, 3)
        return np.round(V, 2).tolist(), F.tolist()

    for e in m.by_type('IfcProduct'):
        if e.is_a() in SKIP or e.is_a('IfcSpatialElement') or not e.Representation:
            continue
        ty = ue.get_type(e)
        V, F = mesh(e)
        parent = None
        for r in e.Decomposes or ():
            parent = r.RelatingObject.is_a()
        data['elements'].append({
            'guid': e.GlobalId, 'ifc_class': e.is_a(), 'predefined': getattr(e, 'PredefinedType', None),
            'name': e.Name, 'type_name': ty.Name if ty else None, 'type_class': ty.is_a() if ty else None,
            'tag': getattr(e, 'Tag', None), 'level': storey_of(e), 'part_of': parent,
            'psets': rus_psets(e), 'verts': V, 'faces': F})
        ok[e.is_a()] += 1
    for s in m.by_type('IfcSpace'):
        loops = []
        h = None
        Ml = inv @ up.get_local_placement(s.ObjectPlacement)
        for rep in s.Representation.Representations:
            for it in rep.Items:
                if not it.is_a('IfcExtrudedAreaSolid'):
                    continue
                Mi = Ml @ up.get_axis2placement(it.Position)
                c = it.SweptArea.OuterCurve
                pts = c.Points.CoordList if c.is_a('IfcIndexedPolyCurve') else [p.Coordinates for p in c.Points]
                loop = [list((Mi @ np.array([p[0], p[1], 0, 1]))[:3]) for p in pts]
                if loop[0] == loop[-1]:
                    loop = loop[:-1]
                loops.append(loop)
                h = it.Depth
        ps = rus_psets(s)
        kind = 'area' if s.Name.startswith('Площадь') else 'room'
        polys = [Polygon([q[:2] for q in lp]).buffer(0) for lp in loops]
        inner = [list(pg.representative_point().coords[0]) for pg in polys]
        merged = unary_union([pg.buffer(1.0) for pg in polys])       # 1 мм — стыки контуров
        n_regions = len(getattr(merged, 'geoms', [merged]))
        data['spaces'].append({'guid': s.GlobalId, 'name': s.Name, 'long_name': s.LongName, 'kind': kind,
                               'level': storey_of(s), 'loops': loops, 'inner_pts': inner,
                               'regions': n_regions, 'area_m2': sum(pg.area for pg in polys) / 1e6,
                               'height_mm': h, 'psets': ps})
    json.dump(data, open(os.path.join(out, 'ar_model.json'), 'w'), ensure_ascii=False)
    print('элементы:', dict(ok), '| помещения/зоны:', len(data['spaces']), '| оси:', len(data['grids']),
          '| уровни:', [(l['name'], l['elevation_mm']) for l in data['levels']])
    print('МСК-77: E %.3f N %.3f м, поворот оси X %.4f° от востока' % (data['site']['east_mm'] / 1000,
                                                                     data['site']['north_mm'] / 1000, ang))
    # наборы свойств: сущности, где встречаются, и типы значений
    sets = collections.OrderedDict()
    scope = collections.defaultdict(set)

    def add(cls, psets):
        for pn, props in psets.items():
            d = sets.setdefault(pn, collections.OrderedDict())
            scope[pn].add(cls)
            for k, v in props.items():
                if v is not None:
                    d.setdefault(k, VTYPE.get(v[0], 'TEXT'))
    for e in data['elements']:
        add(e['ifc_class'], e['psets'])
    for s in data['spaces']:
        add('IfcSpace', s['psets'])
    add('IfcBuilding', data['building']['psets'])
    with open(os.path.join(out, 'RusSets_mapping.txt'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write('# Пользовательские наборы свойств для экспорта IFC из Revit (формат Revit IFC exporter)\n')
        for pn, props in sets.items():
            ents = ','.join(sorted(scope[pn]))
            f.write('PropertySet:\t%s\tI\t%s\n' % (pn, ents))
            for k, t in props.items():
                f.write('\t%s\t%s\n' % (k, {'TEXT': 'Text', 'NUMBER': 'Real', 'YESNO': 'Boolean',
                                             'INTEGER': 'Integer'}[t]))
            f.write('\n')
    with open(os.path.join(out, 'RUS_shared_params.txt'), 'w', encoding='utf-16', newline='\r\n') as f:
        f.write('# This is a Revit shared parameter file.\n# Do not edit manually.\n*META\tVERSION\tMINVERSION\n'
                'META\t2\t1\n*GROUP\tID\tNAME\nGROUP\t1\tRUS\nGROUP\t2\tIFC\n'
                '*PARAM\tGUID\tNAME\tDATATYPE\tDATACATEGORY\tGROUP\tVISIBLE\tDESCRIPTION\tUSERMODIFIABLE\t'
                'HIDEWHENNOEXIST\n')
        import uuid
        done = set()
        for pn, props in sets.items():
            for k, t in props.items():
                if k in done:
                    continue
                done.add(k)
                g = uuid.uuid5(uuid.NAMESPACE_URL, 'agr17a/' + k)
                f.write('PARAM\t%s\t%s\t%s\t\t1\t1\t%s\t1\t0\n' % (g, k, t, pn))
        for k in ('IfcExportAs', 'IfcExportType', 'IfcGUID'):
            g = uuid.uuid5(uuid.NAMESPACE_URL, 'agr17a/' + k)
            f.write('PARAM\t%s\t%s\tTEXT\t\t2\t1\t\t1\t0\n' % (g, k))
    print('наборы свойств:', {k: len(v) for k, v in sets.items()})


if __name__ == '__main__':
    main(*sys.argv[1:3])
