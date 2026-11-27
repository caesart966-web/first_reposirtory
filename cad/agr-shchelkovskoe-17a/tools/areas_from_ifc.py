"""Контуры частей зоны «Общая площадь» в areas.json — по исправленному AR.ifc (после fix_ifc_rules.py).

    python3 areas_from_ifc.py <areas.json> <AR.ifc> <новый areas.json>

areas.json пишет patch_ifc.py; по нему рисуются заливка s3 и строки ННП в DXF и XLSX (dwg_export.py). После обрезки
крылец и террасы по стенам (проверка ЦИМ 27.11.2026) контуры частей, их площади и итог берутся из модели:
каждая часть зоны сопоставляется с прежней по наибольшему перекрытию. Участок и внутренний контур не меняются.
"""
import json
import sys

import numpy as np
import ifcopenshell
import ifcopenshell.util.element as ue
import ifcopenshell.util.placement as up
from shapely.geometry import Polygon


def zone_parts(ar):
    m = ifcopenshell.open(ar)
    z = [s for s in m.by_type('IfcSpace') if ue.get_psets(s).get('RusSet_Common', {}).get('RUS_Name') == 'Общая площадь']
    assert len(z) == 1
    z = z[0]
    Ml = np.array(up.get_local_placement(z.ObjectPlacement))
    out = []
    for rep in z.Representation.Representations:
        for it in rep.Items:
            Mi = Ml @ np.array(up.get_axis2placement(it.Position))
            pts = [tuple((Mi @ np.array([p[0], p[1], 0.0, 1.0]))[:2]) for p in it.SweptArea.OuterCurve.Points.CoordList]
            if pts[0] == pts[-1]:
                pts = pts[:-1]
            out.append(pts)
    area = ue.get_psets(z)['RusSet_Quantities']['RUS_Area']
    return out, area


def main(src, ar, dst):
    a = json.load(open(src, encoding='utf-8'))
    parts, rus_area = zone_parts(ar)
    old = [Polygon(p) for p in a['parts_world']]
    new = [Polygon(p) for p in parts]
    assert len(old) == len(new)
    order = []
    for po in old:
        k = max(range(len(new)), key=lambda i: po.intersection(new[i]).area)
        assert k not in order
        order.append(k)
    names = list(a['parts'])
    a['parts_world'] = [[list(map(float, xy)) for xy in parts[k]] for k in order]
    a['parts'] = {nm: new[k].area / 1e6 for nm, k in zip(names, order)}
    a['total'] = sum(a['parts'].values())
    assert abs(a['total'] - rus_area) < 0.001, (a['total'], rus_area)
    for nm in names:
        print('%9.4f м²  %s' % (a['parts'][nm], nm))
    print('%9.4f м²  итого (RUS_Area в модели %.4f)' % (a['total'], rus_area))
    json.dump(a, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(*sys.argv[1:4])
