# -*- coding: utf-8 -*-
"""Сборка ЦИМ АР (Щёлковское ш., 17А, стр. 1) в Revit по ar_model.json.

Запуск: pyRevit (кнопка или «pyrevit run») либо RevitPythonShell, в НОВОМ проекте из архитектурного шаблона
(единицы — мм). Рядом со скриптом — ar_model.json и RUS_shared_params.txt.

Шаги (одна транзакция, отчёт — build_report.txt рядом со скриптом):
  1. общие параметры RUS_*, IfcExportAs, IfcExportType -> параметры проекта (экземпляр) нужных категорий;
  2. уровни «С01_1_этаж_основной» и «С01_крыша_дополнительный» — абсолютные отметки, как в IFC;
  3. оси 1–7, А–З;
  4. элементы — DirectShape нужной категории с типом (семейство и тип — по имени типа из IFC), IfcExportAs и
     IfcExportType, IfcGUID из IFC, все параметры RusSet_*;
  5. помещения по контурам (линии-разделители), номер, имя, высота, параметры RusSet_*, марки на плане;
  6. зоны «Общая площадь» и «СПП в ГНС» — площади в двух схемах площадей;
  7. сведения о проекте, широта и долгота, общие координаты МСК-77 (точка и угол) с проверкой по контрольной точке;
  8. лист АР-1 «План 1 этажа» — для видов TRM.
Предупреждения Revit (наложение линий и т. п.) в ходе сборки не показываются, их число — в отчёте.
"""
import io
import json
import math
import os

import clr
clr.AddReference('RevitAPI')
from System.Collections.Generic import List  # noqa: E402
from Autodesk.Revit.DB import (  # noqa: E402
    AreaScheme, BuiltInCategory, BuiltInParameter, CategorySet, CurveArray, DirectShape, DirectShapeType, ElementId,
    FailureProcessingResult, FailureSeverity, FamilySymbol, FilteredElementCollector, Grid, IFailuresPreprocessor,
    Level, Line, LinkElementId, Plane, ProjectPosition, SketchPlane, StorageType, TessellatedFace,
    TessellatedShapeBuilder, TessellatedShapeBuilderFallback, TessellatedShapeBuilderTarget, Transaction, UV,
    ViewFamily, ViewFamilyType, ViewPlan, ViewSheet, ViewType, Viewport, XYZ)

HERE = os.path.dirname(os.path.abspath(__file__))
MM = 1.0 / 304.8
USE_TYPES = True        # False — элементы без типов (если экспорт даст не тот класс типа)
LOG = []
OPENED = False

app = __revit__.Application  # noqa: F821
uidoc = None
try:
    uidoc = __revit__.ActiveUIDocument  # noqa: F821
except Exception:
    uidoc = None
if uidoc is not None:
    doc = uidoc.Document
else:                                   # pyrevit run <скрипт> <модель.rvt>
    doc = app.OpenDocumentFile(__models__[0])  # noqa: F821
    OPENED = True


def log(*a):
    s = u' '.join(u'%s' % x for x in a)
    LOG.append(s)
    print(s)


def P(x, y, z=0.0):
    return XYZ(x * MM, y * MM, z * MM)


def clean_name(s):
    """Символы, недопустимые в именах Revit, -> пробел/дефис."""
    s = u'%s' % (s or u'')
    for ch in u'\\:{}[]|;<>?`~':
        s = s.replace(ch, u'-')
    return s.strip() or u'-'


data = json.load(io.open(os.path.join(HERE, 'ar_model.json'), encoding='utf-8'))

CAT = {  # класс IFC -> (категория Revit, IfcExportAs)
    'IfcWall': (BuiltInCategory.OST_Walls, u'IfcWall'),
    'IfcCurtainWall': (BuiltInCategory.OST_Walls, u'IfcCurtainWall'),
    'IfcSlab': (BuiltInCategory.OST_Floors, u'IfcSlab'),
    'IfcColumn': (BuiltInCategory.OST_Columns, u'IfcColumn'),
    'IfcDoor': (BuiltInCategory.OST_Doors, u'IfcDoor'),
    'IfcWindow': (BuiltInCategory.OST_Windows, u'IfcWindow'),
    'IfcRailing': (BuiltInCategory.OST_StairsRailing, u'IfcRailing'),
    'IfcStair': (BuiltInCategory.OST_Stairs, u'IfcStair'),
    'IfcRamp': (BuiltInCategory.OST_Ramps, u'IfcRamp'),
}
BIND_CATS = [BuiltInCategory.OST_Walls, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Roofs,
             BuiltInCategory.OST_Columns, BuiltInCategory.OST_Doors, BuiltInCategory.OST_Windows,
             BuiltInCategory.OST_StairsRailing, BuiltInCategory.OST_Stairs, BuiltInCategory.OST_Ramps,
             BuiltInCategory.OST_GenericModel, BuiltInCategory.OST_Rooms, BuiltInCategory.OST_Areas,
             BuiltInCategory.OST_ProjectInformation]


class QuietWarnings(IFailuresPreprocessor):
    count = 0

    def PreprocessFailures(self, fa):
        for f in fa.GetFailureMessages():
            if f.GetSeverity() == FailureSeverity.Warning:
                fa.DeleteWarning(f)
                QuietWarnings.count += 1
        return FailureProcessingResult.Continue


def bind_params():
    old = app.SharedParametersFilename
    app.SharedParametersFilename = os.path.join(HERE, 'RUS_shared_params.txt')
    try:
        sp = app.OpenSharedParameterFile()
        cats = CategorySet()
        for bic in BIND_CATS:
            c = doc.Settings.Categories.get_Item(bic)
            if c is not None and c.AllowsBoundParameters:
                cats.Insert(c)
        binding = app.Create.NewInstanceBinding(cats)
        try:
            from Autodesk.Revit.DB import GroupTypeId
            grp = GroupTypeId.Data
        except Exception:
            from Autodesk.Revit.DB import BuiltInParameterGroup
            grp = BuiltInParameterGroup.PG_DATA
        n = 0
        for g in sp.Groups:
            for d in g.Definitions:
                if doc.ParameterBindings.Contains(d):
                    doc.ParameterBindings.ReInsert(d, binding, grp)
                else:
                    doc.ParameterBindings.Insert(d, binding, grp)
                n += 1
    finally:
        app.SharedParametersFilename = old or u''
    log(u'1. параметров проекта:', n, u'| категорий:', cats.Size)


def set_param(el, name, val):
    if val is None:
        return True
    v = val[1] if isinstance(val, list) else val
    if v is None:
        return True
    p = el.LookupParameter(name)
    if p is None or p.IsReadOnly:
        return False
    if p.StorageType == StorageType.String:
        return p.Set(u'%s' % v)
    if p.StorageType == StorageType.Integer:
        if isinstance(v, bool):
            return p.Set(1 if v else 0)
        if isinstance(v, (str, type(u''))):
            return p.Set(1 if v.strip(u'.').upper() in (u'T', u'TRUE') else 0)
        return p.Set(int(v))
    if p.StorageType == StorageType.Double:
        return p.Set(float(v))
    return False


def set_guid(el, guid):
    p = el.get_Parameter(BuiltInParameter.IFC_GUID)
    if p is not None and not p.IsReadOnly:
        return p.Set(guid)
    return False


def set_psets(el, psets, miss):
    for pn in psets:
        for k, v in psets[pn].items():
            if not set_param(el, k, v):
                miss.add(k)


def levels():
    want = sorted([(l['elevation_mm'], l['name']) for l in data['levels']])
    have = sorted(FilteredElementCollector(doc).OfClass(Level).ToElements(), key=lambda l: l.Elevation)
    out = []
    for i in range(len(want)):
        el, nm = want[i]
        lv = have[i] if i < len(have) else Level.Create(doc, el * MM)
        lv.Elevation = el * MM
        lv.Name = nm
        out.append(lv)
    for lv in have[len(want):]:
        try:
            doc.Delete(lv.Id)
        except Exception as ex:
            log(u'   уровень шаблона оставлен:', lv.Name, ex)
    log(u'2. уровни:', u', '.join(u'%s %+.3f' % (l.Name, l.Elevation / MM / 1000.0) for l in out))
    return out


def grids(z):
    names = set(g.Name for g in FilteredElementCollector(doc).OfClass(Grid).ToElements())
    n = 0
    for g in data['grids']:
        if g['tag'] in names:
            continue
        gr = Grid.Create(doc, Line.CreateBound(P(g['p0'][0], g['p0'][1], z), P(g['p1'][0], g['p1'][1], z)))
        gr.Name = g['tag']
        n += 1
    log(u'3. оси:', n)


def shape(e):
    V = e['verts']
    b = TessellatedShapeBuilder()
    b.OpenConnectedFaceSet(False)
    k = 0
    for f in e['faces']:
        a, c, d = V[f[0]], V[f[1]], V[f[2]]
        ux, uy, uz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        vx, vy, vz = d[0] - a[0], d[1] - a[1], d[2] - a[2]
        cr = ((uy * vz - uz * vy) ** 2 + (uz * vx - ux * vz) ** 2 + (ux * vy - uy * vx) ** 2) ** 0.5
        if cr < 2.0:                    # треугольник меньше 1 мм²
            continue
        b.AddFace(TessellatedFace(List[XYZ]([P(*a), P(*c), P(*d)]), ElementId.InvalidElementId))
        k += 1
    b.CloseConnectedFaceSet()
    b.Target = TessellatedShapeBuilderTarget.AnyGeometry
    b.Fallback = TessellatedShapeBuilderFallback.Mesh
    b.Build()
    return b.GetBuildResult().GetGeometricalObjects(), k


def elements():
    types, miss, bad, noguid = {}, set(), [], 0
    n = 0
    for e in data['elements']:
        bic, ex_as = CAT[e['ifc_class']]
        cid = ElementId(bic)
        if not DirectShape.IsValidCategoryId(cid, doc):
            cid = ElementId(BuiltInCategory.OST_GenericModel)
        ex_type = None
        if e['ifc_class'] == 'IfcSlab':
            ex_type = u'ROOF' if e.get('part_of') == 'IfcRoof' else (e.get('predefined') or None)
        try:
            geo, k = shape(e)
            ds = DirectShape.CreateElement(doc, cid)
            ds.ApplicationId = u'agr17a'
            ds.ApplicationDataId = e['guid']
            ds.SetShape(geo)
            full = e['type_name'] or e['name'] or e['ifc_class']
            fam, _, typ = full.partition(u':')
            if USE_TYPES:
                key = (cid.ToString(), full)
                if key not in types:
                    t = DirectShapeType.Create(doc, clean_name(typ or fam), cid)
                    if typ:
                        t.SetFamilyName(clean_name(fam))
                    types[key] = t
                ds.SetTypeId(types[key].Id)
            try:
                ds.SetName(clean_name(e['name']))
            except Exception:
                pass
            set_param(ds, u'IfcExportAs', ex_as)
            if ex_type:
                set_param(ds, u'IfcExportType', ex_type)
            if not set_guid(ds, e['guid']):
                noguid += 1
            set_psets(ds, e['psets'], miss)
            n += 1
        except Exception as ex:
            bad.append((e['ifc_class'], e['name'], u'%s' % ex))
    log(u'4. элементов:', n, u'из', len(data['elements']), u'| типов:', len(types))
    if noguid:
        log(u'   IfcGUID не записан у', noguid, u'элементов (экспорт назначит свои GUID)')
    for b in bad:
        log(u'   ОШИБКА элемента:', b[0], b[1], b[2])
    if miss:
        log(u'   не нашлись параметры:', u', '.join(sorted(miss)))


def plan_view(lv):
    for v in FilteredElementCollector(doc).OfClass(ViewPlan).ToElements():
        if not v.IsTemplate and v.ViewType == ViewType.FloorPlan and v.GenLevel is not None \
                and v.GenLevel.Id == lv.Id:
            return v
    vft = [t for t in FilteredElementCollector(doc).OfClass(ViewFamilyType).ToElements()
           if t.ViewFamily == ViewFamily.FloorPlan][0]
    return ViewPlan.Create(doc, vft.Id, lv.Id)


def segments(loop, z):
    out = []
    for i in range(len(loop)):
        a, b = loop[i], loop[(i + 1) % len(loop)]
        if math.hypot(b[0] - a[0], b[1] - a[1]) < 1.0:
            continue
        out.append(Line.CreateBound(P(a[0], a[1], z), P(b[0], b[1], z)))
    return out


def sketch(lv):
    return SketchPlane.Create(doc, Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ(0, 0, lv.Elevation)))


def rooms(lv, view):
    sk = sketch(lv)
    z = lv.Elevation / MM
    seen, n, miss = set(), 0, set()
    ca = CurveArray()
    for s in data['spaces']:
        if s['kind'] != 'room':
            continue
        for lp in s['loops']:
            for c in segments(lp, z):
                p0, p1 = c.GetEndPoint(0), c.GetEndPoint(1)
                key = tuple(sorted([(round(p0.X, 4), round(p0.Y, 4)), (round(p1.X, 4), round(p1.Y, 4))]))
                if key not in seen:
                    seen.add(key)
                    ca.Append(c)
    doc.Create.NewRoomBoundaryLines(sk, ca, view)
    doc.Regenerate()
    for s in data['spaces']:
        if s['kind'] != 'room':
            continue
        x, y = s['inner_pts'][0]
        r = doc.Create.NewRoom(lv, UV(x * MM, y * MM))
        r.Number = s['name']
        r.Name = s['long_name'] or u'Помещение'
        r.get_Parameter(BuiltInParameter.ROOM_UPPER_LEVEL).Set(lv.Id)
        r.get_Parameter(BuiltInParameter.ROOM_UPPER_OFFSET).Set(s['height_mm'] * MM)
        set_guid(r, s['guid'])
        set_psets(r, s['psets'], miss)
        try:
            doc.Create.NewRoomTag(LinkElementId(r.Id), UV(x * MM, y * MM), view.Id)
        except Exception:
            pass
        n += 1
    doc.Regenerate()
    areas = [u'%s: %.2f' % (r.Number, r.Area * 0.09290304)
             for r in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).ToElements()]
    log(u'5. помещений:', n, u'| площади в Revit, м²:', u'; '.join(areas))
    if miss:
        log(u'   не нашлись параметры помещений:', u', '.join(sorted(miss)))


def area_zones(lv):
    schemes = list(FilteredElementCollector(doc).OfClass(AreaScheme).ToElements())
    zs = [s for s in data['spaces'] if s['kind'] == 'area']
    if len(schemes) < len(zs):
        log(u'6. СТОП: нужно схем площадей', len(zs), u', в шаблоне', len(schemes),
            u'— добавить схему (Архитектура -> Площадь и объём -> Схемы площадей) и повторить')
        return
    z = lv.Elevation / MM
    miss = set()
    for sch, s in zip(schemes, zs):
        nm = s['psets'].get('RusSet_Common', {}).get('RUS_Name') or [None, s['name']]
        v = ViewPlan.CreateAreaPlan(doc, sch.Id, lv.Id)
        try:
            v.Name = clean_name(u'Площади %s' % nm[1])
        except Exception:
            pass
        sk = sketch(lv)
        for lp in s['loops']:
            for c in segments(lp, z):
                doc.Create.NewAreaBoundaryLine(sk, c, v)
        doc.Regenerate()
        total = 0.0
        for pt in s['inner_pts']:
            a = doc.Create.NewArea(v, UV(pt[0] * MM, pt[1] * MM))
            pn = a.get_Parameter(BuiltInParameter.ROOM_NAME)
            if pn is not None:
                pn.Set(s['long_name'] or u'Площадь')
            set_psets(a, s['psets'], miss)
            doc.Regenerate()
            total += a.Area * 0.09290304
        log(u'6. зона «%s»: схема «%s», площадей %d, всего %.2f м² (по данным %.2f)'
            % (nm[1], sch.Name, len(s['inner_pts']), total, s['area_m2']))
    if miss:
        log(u'   не нашлись параметры зон:', u', '.join(sorted(miss)))


def dms_rad(v):
    neg = any(x < 0 for x in v)
    d, m, s, u = [abs(x) for x in v]
    r = math.radians(d + m / 60.0 + (s + u / 1e6) / 3600.0)
    return -r if neg else r


def location():
    st = data['site']
    pi = doc.ProjectInformation
    pi.Name = data['building']['name'] or u'Магазин'
    pi.BuildingName = data['building']['name'] or u'Магазин'
    addr = data['building']['psets'].get('RusSet_Project', {}).get('RUS_BuildingAddress')
    if addr:
        pi.Address = addr[1]
    miss = set()
    set_psets(pi, data['building']['psets'], miss)
    if miss:
        log(u'   не нашлись параметры проекта:', u', '.join(sorted(miss)))
    sl = doc.SiteLocation
    sl.Latitude = dms_rad(st['ref_latitude'])
    sl.Longitude = dms_rad(st['ref_longitude'])
    E, N, th = st['east_mm'], st['north_mm'], math.radians(st['x_axis_angle_deg_ccw_from_east'])
    want = (E + 10000 * math.cos(th), N + 10000 * math.sin(th))
    pl = doc.ActiveProjectLocation
    for sign in (1, -1):
        pl.SetProjectPosition(XYZ.Zero, ProjectPosition(E * MM, N * MM, st['elev_mm'] * MM, sign * th))
        doc.Regenerate()
        t = pl.GetTotalTransform()
        for tt in (t, t.Inverse):
            q = tt.OfPoint(P(10000, 0, 0))
            if abs(q.X / MM - want[0]) < 1 and abs(q.Y / MM - want[1]) < 1:
                log(u'7. общие координаты МСК-77: E %.3f м, N %.3f м, угол %+.4f° — контрольная точка сошлась'
                    % (E / 1000, N / 1000, sign * math.degrees(th)))
                return
    log(u'7. ПРОВЕРИТЬ ВРУЧНУЮ общие координаты: начало проекта = E %.3f м, N %.3f м; ось X повёрнута на %.4f° '
        u'против часовой стрелки от востока' % (E / 1000, N / 1000, math.degrees(th)))


def sheet(view):
    tbs = list(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_TitleBlocks)
               .OfClass(FamilySymbol).ToElements())
    if not tbs:
        log(u'8. в шаблоне нет основной надписи — лист не создан; план:', view.Name)
        return
    sh = ViewSheet.Create(doc, tbs[0].Id)
    sh.SheetNumber = u'АР-1'
    sh.Name = u'План 1 этажа'
    Viewport.Create(doc, sh.Id, view.Id, XYZ(1.0, 0.7, 0))
    log(u'8. лист АР-1 «План 1 этажа», вид', view.Name)


def main():
    tr = Transaction(doc, u'Сборка АР из IFC')
    opts = tr.GetFailureHandlingOptions()
    opts.SetFailuresPreprocessor(QuietWarnings())
    tr.SetFailureHandlingOptions(opts)
    tr.Start()
    try:
        bind_params()
        lv = levels()
        grids(lv[0].Elevation / MM)
        elements()
        view = plan_view(lv[0])
        try:
            view.Name = lv[0].Name
        except Exception:
            pass
        for step in (lambda: rooms(lv[0], view), lambda: area_zones(lv[0]), location, lambda: sheet(view)):
            try:
                step()
            except Exception as ex:
                log(u'   ОШИБКА шага, остальные шаги продолжены:', ex)
        tr.Commit()
        log(u'Предупреждений Revit скрыто:', QuietWarnings.count)
        if OPENED:
            doc.Save()
        log(u'ГОТОВО. Сохранить проект как НН_К01_С01_АР_АГР.rvt')
    except Exception as ex:
        if tr.HasStarted() and not tr.HasEnded():
            tr.RollBack()
        log(u'ОСТАНОВЛЕНО, изменения отменены:', ex)
    with io.open(os.path.join(HERE, 'build_report.txt'), 'w', encoding='utf-8') as f:
        f.write(u'\n'.join(LOG))


main()
