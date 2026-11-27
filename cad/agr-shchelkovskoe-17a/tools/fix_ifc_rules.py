"""Правка ЦИМ АР и ПС по замечаниям проверки 26.11.2026 (правила IFC4 и атрибуты).

    python3 fix_ifc_rules.py <папка с AR.ifc, PS.ifc, BiO.ifc> <куда>

АР:
  * 22 нарушения IfcUniqueDefinitionNames: у 20 плит и 2 лестниц наборы RusSet_* выгружены дважды
    с одинаковым содержимым — второй набор и его связь удаляются (свойства — если на них больше никто
    не ссылается);
  * 20 нарушений CorrectTypeAssigned: 16 окон и 4 ограждения привязаны к IfcCurtainWallType. Эти три
    типа («Витраж…») ни к чему другому не привязаны — они становятся IfcWindowType (.WINDOW.) и
    IfcRailingType с тем же GlobalId, именем и тегом;
  * у всех 23 стен RUS_Height = RUS_Length: высота ставится по геометрии стены (размах по Z, мм,
    до 0,1 мм). Так же — у остальных элементов, где RUS_Height расходится с геометрией больше чем
    на 50 мм (навесные фасады под кровлей, витражи ограждения кровли, два окна, проёмы). Значения
    свойств экспортёр делит между элементами, поэтому для высоты заводятся новые свойства (по одному
    на значение), а ссылка меняется только в наборе RusSet_Quantities своего элемента.
  * зона «Общая площадь»: части за наружными стенами (крыльца, терраса) обрезаны по следу стен и облицовки
    навесного фасада — проверка ЦИМ 27.11.2026, 4 пересечения с навесным фасадом больше 80 мм; RUS_Area,
    RUS_Volume — по новым контурам (520,63 -> 519,28 м²).
АР и ПС:
  * контуры профилей (IfcIndexedPolyCurve по списку точек) замыкаются явно — первая точка повторяется
    в конце списка: в ПС контур участка, в АР 4 контура зоны «Общая площадь»;
ПС:
  * RUS_AreaSquare = площадь этого контура (1057,10 м² — как в ГПЗУ) вместо 1057,277.

Правка построчная: остальные строки экспорта не меняются, новые сущности дописываются в конец DATA.
После правки файлы проверяются ifcopenshell.validate (схема и правила EXPRESS) — нарушений быть не должно.
"""
import collections
import os
import re
import shutil
import sys

import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.validate
import ifcopenshell.util.element as ue
from shapely.geometry import Polygon
from shapely.ops import unary_union

LINE = re.compile(r'^#(\d+)=', re.M)
HTOL = 50.0          # мм: расхождение высоты с геометрией, до которого атрибут не трогается (кроме стен)


def num(v):
    v = round(float(v), 6)
    return '%d.' % v if v == int(v) else repr(v)


class Text:
    """Файл IFC построчно: {id: строка}, порядок и переводы строк сохраняются."""

    def __init__(self, path):
        self.raw = open(path, 'rb').read().decode('ascii')
        self.nl = '\r\n' if '\r\n' in self.raw else '\n'
        self.lines = self.raw.split(self.nl)
        self.pos = {int(m.group(1)): i for i, ln in enumerate(self.lines) for m in [LINE.match(ln)] if m}
        self.new = []
        self.top = max(self.pos)

    def get(self, i):
        return self.lines[self.pos[i]]

    def set(self, i, s):
        self.lines[self.pos[i]] = s

    def drop(self, i):
        self.lines[self.pos[i]] = None

    def add(self, body):
        self.top += 1
        self.new.append('#%d=%s' % (self.top, body))
        return self.top

    def refs(self, i):
        pat = re.compile(r'#%d(?!\d)' % i)
        return sum(len(pat.findall(ln)) for ln in self.lines if ln is not None and not ln.startswith('#%d=' % i))

    def save(self, path):
        out = [ln for ln in self.lines if ln is not None]
        k = max(j for j, ln in enumerate(out) if LINE.match(ln))
        out[k + 1:k + 1] = self.new
        open(path, 'wb').write(self.nl.join(out).encode('ascii'))


def props_of(p):
    return sorted((x.Name, str(x.NominalValue)) for x in p.HasProperties)


def fix_ar(src, dst):
    m = ifcopenshell.open(src)
    t = Text(src)
    # 1. повторные наборы свойств
    n_dup = 0
    for e in m.by_type('IfcObject'):
        seen = {}
        for r in e.IsDefinedBy:
            if not r.is_a('IfcRelDefinesByProperties'):
                continue
            p = r.RelatingPropertyDefinition
            if p.Name not in seen:
                seen[p.Name] = p
                continue
            assert props_of(p) == props_of(seen[p.Name]), (e, p.Name)
            assert len(r.RelatedObjects) == 1, r
            t.drop(r.id())
            t.drop(p.id())
            n_dup += 1
            for x in p.HasProperties:
                if t.refs(x.id()) == 0:
                    t.drop(x.id())
    print('АР: удалено повторных наборов свойств', n_dup)
    # 2. типы «Витраж» у окон и ограждений
    for ty in m.by_type('IfcCurtainWallType'):
        objs = {o.is_a() for r in ty.Types for o in r.RelatedObjects}
        if not objs or objs == {'IfcCurtainWall'}:
            continue
        assert len(objs) == 1 and not ty.RepresentationMaps, (ty, objs)
        ln = t.get(ty.id())
        body = re.match(r'#\d+=IFCCURTAINWALLTYPE\((.*),\.(\w+)\.\);$', ln)
        assert body, ln
        if objs == {'IfcWindow'}:
            new = 'IFCWINDOWTYPE(%s,.WINDOW.,.NOTDEFINED.,$,$);' % body.group(1)
        elif objs == {'IfcRailing'}:
            new = 'IFCRAILINGTYPE(%s,.NOTDEFINED.);' % body.group(1)
        else:
            raise SystemExit('тип %s у %s' % (ty, objs))
        t.set(ty.id(), '#%d=%s' % (ty.id(), new))
        print('АР: #%d %s -> %s (%d эл.)' % (ty.id(), ty.Name, new.split('(')[0],
                                            sum(len(r.RelatedObjects) for r in ty.Types)))
    # 3. высота стен по геометрии
    st = ifcopenshell.geom.settings()
    st.set('use-world-coords', True)
    made, olds = {}, set()
    for w in m.by_type('IfcElement'):
        q = [r.RelatingPropertyDefinition for r in w.IsDefinedBy if r.is_a('IfcRelDefinesByProperties')
             and r.RelatingPropertyDefinition.Name == 'RusSet_Quantities']
        old = [x for p in q for x in p.HasProperties if x.Name == 'RUS_Height']
        if not old or not w.Representation:
            continue
        assert len(q) == 1 and len(old) == 1, w
        q, old = q[0], old[0]
        v = np.array(ifcopenshell.geom.create_shape(st, w).geometry.verts).reshape(-1, 3)
        h = round((v[:, 2].max() - v[:, 2].min()) * 1000, 1)
        if not w.is_a('IfcWall') and abs(h - old.NominalValue.wrappedValue) <= HTOL:
            continue
        olds.add(old.id())
        if h not in made:
            made[h] = t.add("IFCPROPERTYSINGLEVALUE('RUS_Height',$,IFCREAL(%s),$);" % num(h))
        ln = t.get(q.id())
        ln2, k = re.subn(r'#%d(?=[,)])' % old.id(), '#%d' % made[h], ln)
        assert k == 1, ln
        t.set(q.id(), ln2)
        print('АР: %s #%d RUS_Height %s -> %s мм' % (w.is_a(), w.id(), num(old.NominalValue.wrappedValue), num(h)))
    for x in olds:
        if t.refs(x) == 0:
            t.drop(x)
    close_profiles(m, t, 'АР')
    fix_mssk(m, t)
    fix_zone_depth(m, t)
    clip_open_parts(m, t)
    t.save(dst)


# Коды помещений по МССК «Помещения и зоны» (www.mos.ru/upload/documents/files/1115/05_MSSKPomesheniyaizoni.pdf):
# RUS_Name помещения -> (код, наименование ровно как в классификаторе). «Торгового зала» в классификаторе нет —
# ближайшее по смыслу «Зона обслуживания» (ПЗ 14); у автора стоял ПЗ 31 01 «Административно-деловые помещения».
# Пом. 11 «ВУ» — водомерный узел (ПД, ИОС2: «В пом. 11 установлен водомерный узел»), у автора «Вентиляционная
# шахта» (ПЗ 31 13 03 в классификаторе — «Вертикальная шахта»).
MSSK = {
    'Торговый зал': ('ПЗ 14', 'Зона обслуживания'),
    'Помещение ВУ': ('ПЗ 31 13 12', 'Помещение инженерных коммуникаций'),
    'Помещение приемки и предпродажной подготовки товара': ('ПЗ 31 13 07', 'Подсобное помещение'),
    'Комната приема пищи': ('ПЗ 31 12 07', 'Помещение приема пищи'),
    'ИТП': ('ПЗ 31 13 01', 'ИТП'),
}


def enc(s):
    out, buf = [], []
    for ch in s:
        if ord(ch) < 128:
            if buf:
                out.append('\\X2\\' + ''.join(buf) + '\\X0\\')
                buf = []
            out.append(ch)
        else:
            buf.append('%04X' % ord(ch))
    if buf:
        out.append('\\X2\\' + ''.join(buf) + '\\X0\\')
    return ''.join(out)


def fix_zone_depth(m, t):
    """Расчётные зоны («Площадь:…», СПП в ГНС и Общая площадь) выдавлены на 4,5 м, а RUS_Height и RUS_Volume —
    на 3,8 м, как у помещений (замечание проверки 27.11.2026). Площади не меняются: глубина выдавливания
    приводится к RUS_Height, объём геометрии сходится с RUS_Volume."""
    for sp in m.by_type('IfcSpace'):
        if not (sp.Name or '').startswith('Площадь'):
            continue
        q = ue.get_psets(sp).get('RusSet_Quantities', {})
        h = q.get('RUS_Height')
        assert h, sp
        for rep in sp.Representation.Representations:
            for it in rep.Items:
                if it.is_a('IfcExtrudedAreaSolid') and abs(it.Depth - h) > 0.5:
                    ln = t.get(it.id())
                    ln2, k = re.subn(r',[-\d.E]+\);$', ',%s);' % num(h), ln)
                    assert k == 1, ln
                    t.set(it.id(), ln2)
                    print('АР: зона %s, выдавливание %s -> %s мм' % (sp.Name, num(it.Depth), num(h)))


def footprint(e, st):
    """След элемента в плане (мм, мировые координаты) — объединение проекций треугольников."""
    sh = ifcopenshell.geom.create_shape(st, e)
    v = np.array(sh.geometry.verts).reshape(-1, 3) * 1000.0
    fc = np.array(sh.geometry.faces).reshape(-1, 3)
    tri = [Polygon(v[f][:, :2]) for f in fc]
    return unary_union([p.buffer(0) for p in tri if p.area > 1e-3])


def tidy(pts, tol=0.5):
    """Убрать повторы точек и точки на прямой (отклонение до 0,5 мм)."""
    out = []
    for p in pts:
        if not out or np.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > tol:
            out.append(p)
    if np.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= tol:
        out.pop()
    res = []
    for i in range(len(out)):
        a, b, c = out[i - 1], out[i], out[(i + 1) % len(out)]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cross) / max(np.hypot(c[0] - a[0], c[1] - a[1]), 1.0) > tol:
            res.append(b)
    return res


def clip_open_parts(m, t):
    """Зона «Общая площадь»: части за наружными стенами (крыльцо главного входа с пандусом и лестницей, служебное
    крыльцо, терраса загрузки) заходили в стены и облицовку навесного фасада на всю толщину — проверка ЦИМ
    27.11.2026: «Матрица коллизий», 4 пересечения зоны с навесным фасадом больше 80 мм. Эти части обрезаются
    по следу стен (IfcWall) и навесных фасадов (IfcCurtainWall); часть внутри здания (самая большая, по внутренним
    поверхностям наружных стен, с перегородками) не меняется. RUS_Area и RUS_Volume — по новым контурам."""
    import ifcopenshell.util.placement as up
    st = ifcopenshell.geom.settings()
    st.set('use-world-coords', True)
    walls = unary_union([footprint(e, st) for e in m.by_type('IfcWall') + m.by_type('IfcCurtainWall')])
    zone = [s for s in m.by_type('IfcSpace')
            if ue.get_psets(s).get('RusSet_Common', {}).get('RUS_Name') == 'Общая площадь']
    assert len(zone) == 1, zone
    zone = zone[0]
    Ml = np.array(up.get_local_placement(zone.ObjectPlacement))
    items = [it for rep in zone.Representation.Representations for it in rep.Items]
    assert all(it.is_a('IfcExtrudedAreaSolid') and not it.SweptArea.OuterCurve.Segments for it in items)
    world, Mis = [], []
    for it in items:
        Mi = Ml @ np.array(up.get_axis2placement(it.Position))
        Mis.append(Mi)
        world.append(Polygon([tuple((Mi @ np.array([p[0], p[1], 0.0, 1.0]))[:2])
                              for p in it.SweptArea.OuterCurve.Points.CoordList]))
    big = max(range(len(items)), key=lambda i: world[i].area)
    total = world[big].area
    for i, it in enumerate(items):
        if i == big:
            continue
        d = world[i].difference(walls)
        pieces = [g for g in getattr(d, 'geoms', [d]) if g.area > 1e4]          # куски меньше 0,01 м² — щели
        assert len(pieces) == 1, [g.area for g in pieces]
        Pi = np.linalg.inv(Mis[i])
        loc = [tuple((Pi @ np.array([x, y, 0.0, 1.0]))[:2]) for x, y in tidy(list(pieces[0].exterior.coords)[:-1])]
        old = it.SweptArea.OuterCurve.Points.CoordList
        if Polygon(loc).exterior.is_ccw != Polygon(old).exterior.is_ccw:
            loc = loc[::-1]
        loc = [(round(x, 4), round(y, 4)) for x, y in loc]
        loc.append(loc[0])
        pid = it.SweptArea.OuterCurve.Points.id()
        assert t.refs(pid) == 1, pid
        t.set(pid, '#%d=IFCCARTESIANPOINTLIST2D((%s));' % (pid, ','.join('(%s,%s)' % (num(x), num(y)) for x, y in loc)))
        w = Polygon([tuple((Mis[i] @ np.array([x, y, 0.0, 1.0]))[:2]) for x, y in loc])
        assert w.intersection(walls).area < 100.0, w.intersection(walls).area      # только касание по грани
        total += w.area
        print('АР: зона «Общая площадь», часть #%d: %.4f -> %.4f м² (обрезано по стенам и облицовке %.4f м²)'
              % (it.id(), world[i].area / 1e6, w.area / 1e6, (world[i].area - w.area) / 1e6))
    total = round(total / 1e6, 6)
    q = [r.RelatingPropertyDefinition for r in zone.IsDefinedBy if r.is_a('IfcRelDefinesByProperties')
         and r.RelatingPropertyDefinition.Name == 'RusSet_Quantities']
    assert len(q) == 1
    vals = {x.Name: x for x in q[0].HasProperties}
    h = vals['RUS_Height'].NominalValue.wrappedValue
    ln = t.get(q[0].id())
    for key, v in (('RUS_Area', total), ('RUS_Volume', round(total * h / 1000.0, 6))):
        old = vals[key]
        new = t.add("IFCPROPERTYSINGLEVALUE('%s',$,IFCREAL(%s),$);" % (key, num(v)))
        ln, k = re.subn(r'#%d(?=[,)])' % old.id(), '#%d' % new, ln)
        assert k == 1, ln
        if t.refs(old.id()) == 1:            # ссылка была только из этого набора
            t.drop(old.id())
        print('АР: зона «Общая площадь» %s %s -> %s' % (key, num(old.NominalValue.wrappedValue), num(v)))
    t.set(q[0].id(), ln)
    return total


def new_storey_guids(m, t, tag):
    """У уровня ПС и БиО (абс. 154,350) был тот же GlobalId, что у уровня АР (154,850): разные уровни — разные GUID."""
    import uuid
    import ifcopenshell.guid
    for st in m.by_type('IfcBuildingStorey'):
        g = ifcopenshell.guid.compress(uuid.uuid5(uuid.NAMESPACE_URL, 'agr17a/%s/storey/%s' % (tag, st.Name)).hex)
        ln = t.get(st.id())
        assert ln.count("'%s'" % st.GlobalId) == 1, ln
        t.set(st.id(), ln.replace("'%s'" % st.GlobalId, "'%s'" % g))
        print('%s: GUID уровня %s -> %s' % (tag, st.GlobalId, g))


def fix_mssk(m, t):
    made, olds = {}, set()
    for sp in m.by_type('IfcSpace'):
        for r in sp.IsDefinedBy:
            if not r.is_a('IfcRelDefinesByProperties'):
                continue
            p = r.RelatingPropertyDefinition
            vals = {x.Name: x for x in p.HasProperties}
            if 'RUS_MSSK_SpaceAndZone_Code' not in vals or 'RUS_Name' not in vals:
                continue
            name = vals['RUS_Name'].NominalValue.wrappedValue
            if name not in MSSK:
                continue
            code, cname = MSSK[name]
            ln = t.get(p.id())
            for key, new in (('RUS_MSSK_SpaceAndZone_Code', code), ('RUS_MSSK_SpaceAndZone_Name', cname)):
                old = vals[key]
                if old.NominalValue.wrappedValue == new:
                    continue
                k = (key, new, old.NominalValue.is_a())
                if k not in made:
                    made[k] = t.add("IFCPROPERTYSINGLEVALUE('%s',$,%s('%s'),$);" % (key, old.NominalValue.is_a().upper(),
                                                                                  enc(new)))
                olds.add(old.id())
                ln, n = re.subn(r'#%d(?=[,)])' % old.id(), '#%d' % made[k], ln)
                assert n == 1, ln
                print('АР: помещение «%s» %s: %s -> %s' % (name, key[-4:], old.NominalValue.wrappedValue, new))
            t.set(p.id(), ln)
    for x in olds:
        if t.refs(x) == 0:
            t.drop(x)
    return made


def close_profiles(m, t, tag):
    """Контуры замкнутых профилей (IfcArbitraryClosedProfileDef) по списку точек без сегментов —
    первая точка повторяется в конце. Возвращает {id кривой: площадь, м²}."""
    out = {}
    for p in m.by_type('IfcArbitraryClosedProfileDef'):
        for c in [p.OuterCurve] + list(getattr(p, 'InnerCurves', None) or []):
            if not c.is_a('IfcIndexedPolyCurve'):
                assert not c.is_a('IfcPolyline') or c.Points[0].Coordinates == c.Points[-1].Coordinates, c
                continue
            pts = c.Points.CoordList
            if c.Segments:
                idx = [i for sg in c.Segments for i in sg.wrappedValue]
                assert idx[0] == idx[-1], c          # замкнут сегментами (дуги)
                continue
            if pts[0] == pts[-1]:
                continue
            assert t.refs(c.Points.id()) == 1, c
            ln = t.get(c.Points.id())
            first = re.search(r'\(\((\([^()]*\))', ln).group(1)
            assert ln.endswith('));'), ln
            t.set(c.Points.id(), ln[:-3] + ',' + first + '));')
            out[c.id()] = Polygon(pts).area / 1e6
            print('%s: контур #%d замкнут, %d -> %d точек, площадь %.4f м²' % (tag, c.id(), len(pts), len(pts) + 1,
                                                                            out[c.id()]))
    return out


def fix_ps(src, dst):
    t = Text(src)
    m = ifcopenshell.open(src)
    # имя уровня по требованиям ДГП (ч. 1, п. 6.7, табл. 6): <секция>_<номер>_<наименование>_<назначение>;
    # у ПС было «Этаж 01» — замечание проверки ЦИМ 26.11.2026 «нет типа в названии этажа»
    for st in m.by_type('IfcBuildingStorey'):
        if not re.match(r'^[СП]\d\d_[^_]+_[^_]+_(основной|дополнительный|вспомогательный)', st.Name or ''):
            new = 'С01_1_этаж_основной'
            ln = t.get(st.id())
            old = re.match(r"#\d+=IFCBUILDINGSTOREY\('[^']*',#\d+,'([^']*)'", ln).group(1)
            assert ln.count("'%s'" % old) == 2, ln
            t.set(st.id(), ln.replace("'%s'" % old, "'%s'" % enc(new)))
            print('ПС: уровень «%s» -> «%s»' % (st.Name, new))
    new_storey_guids(m, t, 'ПС')
    closed = close_profiles(m, t, 'ПС')
    assert len(closed) == 1
    area = next(iter(closed.values()))
    for p in m.by_type('IfcPropertySingleValue'):
        if p.Name == 'RUS_AreaSquare':
            ln = t.get(p.id())
            ln2 = re.sub(r'IFCREAL\([-\d.E]+\)', 'IFCREAL(%s)' % num(round(area, 2)), ln)
            t.set(p.id(), ln2)
            print('ПС: RUS_AreaSquare %s -> %s' % (p.NominalValue.wrappedValue, num(round(area, 2))))
    t.save(dst)


def check(path):
    m = ifcopenshell.open(path)
    lg = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(m, lg, express_rules=True)
    c = collections.Counter(str(s['message']).split('\n')[0][:100] for s in lg.statements)
    print('  %s: нарушений %d %s' % (os.path.basename(path), len(lg.statements), dict(c) if c else ''))
    return len(lg.statements)


def main(src, out):
    os.makedirs(out, exist_ok=True)
    fix_ar(os.path.join(src, 'AR.ifc'), os.path.join(out, 'AR.ifc'))
    fix_ps(os.path.join(src, 'PS.ifc'), os.path.join(out, 'PS.ifc'))
    m = ifcopenshell.open(os.path.join(src, 'BiO.ifc'))
    t = Text(os.path.join(src, 'BiO.ifc'))
    assert not close_profiles(m, t, 'БиО')
    new_storey_guids(m, t, 'БиО')
    t.save(os.path.join(out, 'BiO.ifc'))
    bad = sum(check(os.path.join(out, f)) for f in ('AR.ifc', 'PS.ifc', 'BiO.ifc'))
    assert bad == 0


if __name__ == '__main__':
    main(*sys.argv[1:3])
