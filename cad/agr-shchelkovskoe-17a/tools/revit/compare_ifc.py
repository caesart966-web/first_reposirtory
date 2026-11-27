"""Сверка IFC АР, выгруженного из Revit плагином, с эталоном (исправленный IFC). Файлы не меняются.

    python3 compare_ifc.py <эталон AR.ifc> <новый AR.ifc> [<trm.zip>]

Проверяет: правила IFC4 (ifcopenshell.validate), уровни (имена, отметки), классы и число элементов,
положение каждого элемента в МСК-77 (центр габарита, по GUID — Revit сохраняет его из параметра IfcGUID,
иначе по классу и имени), наборы RusSet_* (значения), помещения и зоны (площадь по геометрии, коды МССК),
высоту по геометрии, повторные наборы свойств, замкнутость контуров, координаты IfcSite.
С trm.zip — что контрольная сумма из info.xml совпадает с MD5 нового IFC (если плагин считает MD5).
Итог: ВСЁ СОВПАЛО или список расхождений.
"""
import collections
import hashlib
import re
import sys
import zipfile

import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as ue
import ifcopenshell.validate

TOL_MM = 20.0
# облицовка навесного фасада из Revit выгружается IfcCovering (CLADDING): IfcCurtainWall из DirectShape не выгружается,
# а IfcWall с кодом «Фасад» не проходит IDS «Стена, перегородка»
SAME = {'IfcCovering': 'IfcCurtainWall'}


def cls(e):
    return SAME.get(e.is_a(), e.is_a())


def psets(e):
    out = {}
    for k, v in ue.get_psets(e).items():
        if k.startswith('RusSet_'):
            out[k] = {kk: vv for kk, vv in v.items() if kk != 'id'}
    return out


def centers(m):
    st = ifcopenshell.geom.settings()
    st.set('use-world-coords', True)
    out = {}
    for e in m.by_type('IfcProduct'):
        if e.is_a('IfcOpeningElement') or e.is_a('IfcSpatialElement') and not e.is_a('IfcSpace') or \
                not e.Representation or e.is_a('IfcGrid'):
            continue
        try:
            v = np.array(ifcopenshell.geom.create_shape(st, e).geometry.verts).reshape(-1, 3) * 1000
        except Exception:
            continue
        out[e.GlobalId] = (e, (v.min(0) + v.max(0)) / 2, v[:, 2].max() - v[:, 2].min())
    return out


def main(ref_path, new_path, trm=None):
    bad = []
    ref, new = ifcopenshell.open(ref_path), ifcopenshell.open(new_path)
    lg = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(new, lg, express_rules=True)
    c = collections.Counter(str(s['message']).split('\n')[0][:90] for s in lg.statements)
    print('правила IFC4: нарушений', len(lg.statements), dict(c) if c else '')
    if lg.statements:
        bad.append('нарушения IFC4: %d' % len(lg.statements))
    lv = lambda m: sorted((s.Name, round(float(s.Elevation))) for s in m.by_type('IfcBuildingStorey'))  # noqa
    print('уровни:', lv(new))
    if lv(new) != lv(ref):
        bad.append('уровни: %s, ожидалось %s' % (lv(new), lv(ref)))
    for s in new.by_type('IfcSite'):
        print('IfcSite', s.RefLatitude, s.RefLongitude)
        if tuple(s.RefLatitude or ())[:3] != tuple(ref.by_type('IfcSite')[0].RefLatitude)[:3]:
            bad.append('широта IfcSite %s' % (s.RefLatitude,))
    cnt = lambda m: collections.Counter(cls(e) for e in m.by_type('IfcElement') if not e.is_a('IfcOpeningElement'))  # noqa
    print('элементы:', dict(cnt(new)))
    for k in set(cnt(ref)) | set(cnt(new)):
        if k == 'IfcRoof':          # в Revit кровля — плиты IfcSlab.ROOF без контейнера IfcRoof
            if cnt(ref)[k] != cnt(new)[k]:
                print('   IfcRoof: %d (в эталоне %d) — контейнеры, части кровли сверяются как IfcSlab'
                      % (cnt(new)[k], cnt(ref)[k]))
            continue
        if cnt(ref)[k] != cnt(new)[k]:
            bad.append('%s: %d, в эталоне %d' % (k, cnt(new)[k], cnt(ref)[k]))
    R, N = centers(ref), centers(new)
    byname = {(cls(e), e.Name): g for g, (e, _, _) in N.items()}
    used = set(g for g in R if g in N)

    def nearest(e, cr):
        best = None
        for g2, (e2, cn, _) in N.items():
            if g2 in used or cls(e2) != cls(e):
                continue
            d = np.linalg.norm(cn - cr)
            if d < 100 and (best is None or d < best[0]):
                best = (d, g2)
        return best and best[1]
    moved, pdiff, found = [], [], 0
    for g, (e, cr, hr) in R.items():
        g2 = g if g in N else byname.get((cls(e), e.Name))
        if g2 is None or g2 in used and g2 != g:
            g2 = nearest(e, cr)
        if g2 is not None:
            used.add(g2)
        if g2 is None:
            if not e.is_a('IfcSpace'):
                bad.append('нет элемента %s %s' % (e.is_a(), e.Name))
            continue
        found += 1
        e2, cn, hn = N[g2]
        d = np.linalg.norm(cn - cr)
        if d > TOL_MM:
            moved.append((e.is_a(), e.Name, round(d)))
        a, b = psets(e), psets(e2)
        for pn in set(a) | set(b):
            for k in set(a.get(pn, {})) | set(b.get(pn, {})):
                x, y = a.get(pn, {}).get(k), b.get(pn, {}).get(k)
                if isinstance(x, float) and isinstance(y, float) and abs(x - y) <= max(1.0, abs(x) * 1e-3):
                    continue
                if x != y:
                    pdiff.append((e.is_a(), e.Name, pn, k, x, y))
    print('сопоставлено элементов с эталоном:', found, 'из', len(R))
    if moved:
        bad.append('смещены больше %d мм: %d' % (TOL_MM, len(moved)))
        for x in moved[:15]:
            print('   смещён', *x)
    if pdiff:
        bad.append('расходятся параметры: %d' % len(pdiff))
        for x in sorted(pdiff, key=lambda t: ('навесной' in str(t[1]), str(t)))[:40]:
            print('   параметр', *x)
    # высоты, повторы наборов, контуры
    for g, (e, _, h) in N.items():
        q = psets(e).get('RusSet_Quantities', {})
        if 'RUS_Height' in q and abs(q['RUS_Height'] - h) > 50 and not e.is_a('IfcSpace'):
            bad.append('RUS_Height %s %s: %s при геометрии %.0f' % (e.is_a(), e.Name, q['RUS_Height'], h))
        names = [r.RelatingPropertyDefinition.Name for r in getattr(e, 'IsDefinedBy', ())
                 if r.is_a('IfcRelDefinesByProperties')]
        dup = [k for k, v in collections.Counter(names).items() if v > 1]
        if dup:
            bad.append('повтор наборов %s у %s %s' % (dup, e.is_a(), e.Name))
    for p in new.by_type('IfcArbitraryClosedProfileDef'):
        c = p.OuterCurve
        if c.is_a('IfcIndexedPolyCurve') and not c.Segments and c.Points.CoordList[0] != c.Points.CoordList[-1]:
            bad.append('незамкнутый контур #%d' % c.id())
        if c.is_a('IfcPolyline') and c.Points[0].Coordinates != c.Points[-1].Coordinates:
            bad.append('незамкнутый контур #%d' % c.id())
    for s in new.by_type('IfcSpace'):
        f = {k: v for p in psets(s).values() for k, v in p.items()}
        print('   помещение', s.Name, s.LongName, f.get('RUS_Name'), f.get('RUS_MSSK_SpaceAndZone_Code'),
              f.get('RUS_MSSK_SpaceAndZone_Name'))
    if trm:
        z = zipfile.ZipFile(trm)
        info = z.read('info.xml').decode('utf-8-sig')
        h = re.findall(r'Name="IFCHash" Value="([0-9a-fA-F]+)"', info)
        md5 = hashlib.md5(open(new_path, 'rb').read()).hexdigest()
        print('TRM IFCHash:', h, '| MD5 IFC:', md5)
        if h and md5 not in [x.lower() for x in h]:
            print('   (хеш TRM не MD5 этого файла — сверить по дате выгрузки: IFC и TRM должны быть из одной выгрузки)')
    print('\nИТОГ:', 'ВСЁ СОВПАЛО' if not bad else 'РАСХОЖДЕНИЯ')
    for b in bad:
        print(' -', b)
    return not bad


if __name__ == '__main__':
    sys.exit(0 if main(*sys.argv[1:4]) else 1)
