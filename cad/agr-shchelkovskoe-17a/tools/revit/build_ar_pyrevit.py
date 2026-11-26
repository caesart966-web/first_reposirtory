# -*- coding: utf-8 -*-
"""Сборка ЦИМ АР (Щёлковское ш., 17А, стр. 1) в Revit по ar_model.json — запуск из pyRevit / RevitPythonShell
в НОВОМ проекте, созданном из архитектурного шаблона (единицы — мм).

Рядом со скриптом должны лежать ar_model.json и RUS_shared_params.txt (их пишет ifc_to_revit_data.py).

Что делает (одной транзакцией, по шагам с отчётом):
  1. общие параметры RUS_*, IfcExportAs, IfcExportType, IfcGUID -> параметры проекта (экземпляр) для нужных категорий;
  2. уровни «С01_1_этаж_основной» (+154 850) и «С01_крыша_дополнительный» (+159 350) — абсолютные отметки, как в IFC;
  3. оси 1–7, А–З;
  4. элементы — DirectShape нужной категории с типом (DirectShapeType) по имени типа из IFC, IfcExportAs/IfcExportType
     там, где категория Revit не даёт нужный класс IFC, IfcGUID = GUID из IFC, все параметры RusSet_*;
  5. помещения (11) по контурам через линии-разделители, номер/имя/высота и параметры RusSet_*;
  6. зоны «Общая площадь» и «СПП в ГНС» — площади (Area) в двух разных схемах площадей;
  7. сведения о проекте и параметры здания, широта/долгота, общие координаты МСК-77 (точка и угол) с проверкой;
  8. план 1 этажа с марками помещений и лист с этим планом — для видов TRM.
Ничего не удаляет, кроме лишних уровней шаблона (если их можно удалить).

ВНИМАНИЕ: скрипт не проверен в Revit на этой машине (готовился без доступа к Revit). Ошибки по элементам
пишутся в отчёт и не останавливают сборку; отчёт — в build_report.txt рядом со скриптом.
"""
import io
import json
import math
import os

import clr
clr.AddReference('RevitAPI')
from System.Collections.Generic import List  # noqa: E402
from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory, BuiltInParameter, CategorySet, CurveArray, DirectShape, DirectShapeType, ElementId,
    FilteredElementCollector, Grid, Level, Line, LinkElementId, Plane, ProjectPosition, SketchPlane,
    TessellatedFace, TessellatedShapeBuilder, TessellatedShapeBuilderFallback, TessellatedShapeBuilderTarget,
    Transaction, UV, ViewFamily, ViewFamilyType, ViewPlan, ViewSheet, Viewport, XYZ, AreaScheme, StorageType,
    FamilySymbol)

try:
    doc = __revit__.ActiveUIDocument.Document  # noqa: F821
    app = __revit__.Application  # noqa: F821
except Exception:
    doc = __revit__.ActiveUIDocument.Document  # noqa: F821
    app = doc.Application

HERE = os.path.dirname(os.path.abspath(__file__))
MM = 1.0 / 304.8
LOG = []


def log(*a):
    s = u' '.join(u'%s' % x for x in a)
    LOG.append(s)
    print(s)


def P(x, y, z=0.0):
    return XYZ(x * MM, y * MM, z * MM)


data = json.load(io.open(os.path.join(HERE, 'ar_model.json'), encoding='utf-8'))

CAT = {  # класс IFC -> (категория Revit, IfcExportAs, IfcExportType)
    'IfcWall': (BuiltInCategory.OST_Walls, 'IfcWall', None),
    'IfcCurtainWall': (BuiltInCategory.OST_Walls, 'IfcCurtainWall', None),
    'IfcSlab': (BuiltInCategory.OST_Floors, 'IfcSlab', None),
    'IfcColumn': (BuiltInCategory.OST_Columns, 'IfcColumn', None),
    'IfcDoor': (BuiltInCategory.OST_Doors, 'IfcDoor', None),
    'IfcWindow': (BuiltInCategory.OST_Windows, 'IfcWindow', None),
    'IfcRailing': (BuiltInCategory.OST_StairsRailing, 'IfcRailing', None),
    'IfcStair': (BuiltInCategory.OST_Stairs, 'IfcStair', None),
    'IfcRamp': (BuiltInCategory.OST_Ramps, 'IfcRamp', None),
}
PREDEF = {'BASESLAB': 'BASESLAB', 'FLOOR': 'FLOOR', 'ROOF': 'ROOF'}
BIND_CATS = [BuiltInCategory.OST_Walls, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Roofs,
             BuiltInCategory.OST_Columns, BuiltInCategory.OST_Doors, BuiltInCategory.OST_Windows,
             BuiltInCategory.OST_StairsRailing, BuiltInCategory.OST_Stairs, BuiltInCategory.OST_Ramps,
             BuiltInCategory.OST_GenericModel, BuiltInCategory.OST_Rooms, BuiltInCategory.OST_Areas,
             BuiltInCategory.OST_ProjectInformation]


def bind_params():
    path = os.path.join(HERE, 'RUS_shared_params.txt')
    app.SharedParametersFilename = path
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
    log(u'1. параметров проекта:', n)


def set_param(el, name, val):
    if val is None:
        return True
    p = el.LookupParameter(name)
    if p is None or p.IsReadOnly:
        return False
    v = val[1] if isinstance(val, list) else val
    if p.StorageType == StorageType.String:
        return p.Set(u'%s' % v)
    if p.StorageType == StorageType.Integer:
        if isinstance(v, bool):
            return p.Set(1 if v else 0)
        if isinstance(v, (str, type(u''))):
            return p.Set(1 if v.strip('.').upper() in ('T', 'TRUE') else 0)
        return p.Set(int(v))
    if p.StorageType == StorageType.Double:
        return p.Set(float(v))
    return False


def set_psets(el, psets, miss):
    for pn, props in psets.items():
        for k, v in props.items():
            if not set_param(el, k, v):
                miss.add(k)


def levels():
    want = [(l['name'], l['elevation_mm']) for l in sorted(data['levels'], key=lambda x: x['elevation_mm'])]
    have = sorted(FilteredElementCollector(doc).OfClass(Level).ToElements(), key=lambda l: l.Elevation)
    out = {}
    for i, (nm, el) in enumerate(want):
        lv = have[i] if i < len(have) else Level.Create(doc, el * MM)
        lv.Elevation = el * MM
        lv.Name = nm
        out[nm] = lv
    for lv in have[len(want):]:
        try:
            doc.Delete(lv.Id)
        except Exception as ex:
            log(u'   уровень шаблона не удалён:', lv.Name, ex)
    log(u'2. уровни:', [(k, round(v.Elevation / MM, 1)) for k, v in out.items()])
    return out


def grids(lv0):
    names = set(g.Name for g in FilteredElementCollector(doc).OfClass(Grid).ToElements())
    for g in data['grids']:
        if g['tag'] in names:
            continue
        gr = Grid.Create(doc, Line.CreateBound(P(g['p0'][0], g['p0'][1], lv0), P(g['p1'][0], g['p1'][1], lv0)))
        gr.Name = g['tag']
    log(u'3. оси:', len(data['grids']))


def shape(e):
    V = e['verts']
    b = TessellatedShapeBuilder()
    b.OpenConnectedFaceSet(False)
    for f in e['faces']:
        a, c, d = [V[i] for i in f]
        ux, uy, uz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        vx, vy, vz = d[0] - a[0], d[1] - a[1], d[2] - a[2]
        cr = ((uy * vz - uz * vy) ** 2 + (uz * vx - ux * vz) ** 2 + (ux * vy - uy * vx) ** 2) ** 0.5
        if cr < 2.0:            # треугольник меньше ~1 мм² — пропускаем
            continue
        pts = List[XYZ]([P(*a), P(*c), P(*d)])
        b.AddFace(TessellatedFace(pts, ElementId.InvalidElementId))
    b.CloseConnectedFaceSet()
    b.Target = TessellatedShapeBuilderTarget.AnyGeometry
    b.Fallback = TessellatedShapeBuilderFallback.Mesh
    b.Build()
    return b.GetBuildResult().GetGeometricalObjects()


def elements():
    types, miss, bad = {}, set(), []
    n = 0
    for e in data['elements']:
        bic, ex_as, ex_type = CAT[e['ifc_class']]
        cid = ElementId(bic)
        if not DirectShape.IsValidCategoryId(cid, doc):
            bic = BuiltInCategory.OST_GenericModel
            cid = ElementId(bic)
        if e['ifc_class'] == 'IfcSlab':
            ex_type = 'ROOF' if e.get('part_of') == 'IfcRoof' else PREDEF.get(e.get('predefined'))
        try:
            key = (int(bic), e['type_name'] or e['name'])
            if key not in types:
                t = DirectShapeType.Create(doc, key[1], cid)
                types[key] = t
            ds = DirectShape.CreateElement(doc, cid)
            ds.ApplicationId = 'agr17a'
            ds.ApplicationDataId = e['guid']
            ds.SetShape(shape(e))
            ds.SetTypeId(types[key].Id)
            try:
                ds.SetName(e['name'] or '')
            except Exception:
                ds.Name = e['name'] or ''
            set_param(ds, 'IfcExportAs', ex_as)
            if ex_type:
                set_param(ds, 'IfcExportType', ex_type)
            set_param(ds, 'IfcGUID', e['guid'])
            set_psets(ds, e['psets'], miss)
            n += 1
        except Exception as ex:
            bad.append((e['ifc_class'], e['name'], u'%s' % ex))
    log(u'4. элементов создано:', n, u'из', len(data['elements']), u'| типов:', len(types))
    for b in bad:
        log(u'   ОШИБКА элемента:', *b)
    if miss:
        log(u'   не нашлись параметры:', sorted(miss))


def plan_view(lv):
    for v in FilteredElementCollector(doc).OfClass(ViewPlan).ToElements():
        if not v.IsTemplate and v.GenLevel is not None and v.GenLevel.Id == lv.Id and \
                v.ViewType.ToString() == 'FloorPlan':
            return v
    vft = [t for t in FilteredElementCollector(doc).OfClass(ViewFamilyType).ToElements()
           if t.ViewFamily == ViewFamily.FloorPlan][0]
    return ViewPlan.Create(doc, vft.Id, lv.Id)


def loop_curves(loop, z):
    ca = CurveArray()
    for i in range(len(loop)):
        a, b = loop[i], loop[(i + 1) % len(loop)]
        if math.hypot(b[0] - a[0], b[1] - a[1]) < 1.0:
            continue
        ca.Append(Line.CreateBound(P(a[0], a[1], z), P(b[0], b[1], z)))
    return ca


def rooms(lv, view):
    sk = SketchPlane.Create(doc, Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ(0, 0, lv.Elevation)))
    z = lv.Elevation / MM
    seen, n, miss = set(), 0, set()
    for s in data['spaces']:
        if s['kind'] != 'room':
            continue
        for lp in s['loops']:
            ca = CurveArray()
            for c in loop_curves(lp, z):
                k = tuple(sorted([(round(c.GetEndPoint(i).X, 3), round(c.GetEndPoint(i).Y, 3)) for i in (0, 1)]))
                if k not in seen:
                    seen.add(k)
                    ca.Append(c)
            if ca.Size:
                doc.Create.NewRoomBoundaryLines(sk, ca, view)
    doc.Regenerate()
    for s in data['spaces']:
        if s['kind'] != 'room':
            continue
        x, y = s['inner_pts'][0]
        r = doc.Create.NewRoom(lv, UV(x * MM, y * MM))
        r.Number = s['name']
        r.Name = s['long_name'] or ''
        r.get_Parameter(BuiltInParameter.ROOM_UPPER_LEVEL).Set(lv.Id)
        r.get_Parameter(BuiltInParameter.ROOM_UPPER_OFFSET).Set(s['height_mm'] * MM)
        set_param(r, 'IfcGUID', s['guid'])
        set_psets(r, s['psets'], miss)
        try:
            doc.Create.NewRoomTag(LinkElementId(r.Id), UV(x * MM, y * MM), view.Id)
        except Exception:
            pass
        n += 1
    doc.Regenerate()
    log(u'5. помещений:', n, [(s['name'], round(s['area_m2'], 2)) for s in data['spaces'] if s['kind'] == 'room'])
    if miss:
        log(u'   не нашлись параметры помещений:', sorted(miss))


def areas(lv):
    schemes = list(FilteredElementCollector(doc).OfClass(AreaScheme).ToElements())
    zs = [s for s in data['spaces'] if s['kind'] == 'area']
    if len(schemes) < len(zs):
        log(u'6. СТОП по площадям: нужно схем площадей', len(zs), u', в шаблоне', len(schemes),
            u'— добавьте схему (Управление -> Площадь и объём) и запустите шаг заново')
        return
    z = lv.Elevation / MM
    miss = set()
    for sch, s in zip(schemes, zs):
        v = ViewPlan.CreateAreaPlan(doc, sch.Id, lv.Id)
        v.Name = u'Площади — %s' % s['psets'].get('RusSet_Common', {}).get('RUS_Name', [None, s['name']])[1]
        sk = SketchPlane.Create(doc, Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ(0, 0, lv.Elevation)))
        for lp in s['loops']:
            for c in loop_curves(lp, z):
                doc.Create.NewAreaBoundaryLine(sk, c, v)
        doc.Regenerate()
        for (x, y) in s['inner_pts']:
            a = doc.Create.NewArea(v, UV(x * MM, y * MM))
            a.get_Parameter(BuiltInParameter.ROOM_NAME).Set(s['long_name'] or u'Площадь')
            set_psets(a, s['psets'], miss)
        log(u'6. площадь', s['name'], u'-> схема', sch.Name, u', контуров', len(s['loops']),
            u', всего %.2f м²' % s['area_m2'])
    if miss:
        log(u'   не нашлись параметры площадей:', sorted(miss))


def dms_rad(v):
    d, m, s, u = v
    sg = -1 if (d < 0 or m < 0 or s < 0 or u < 0) else 1
    return sg * math.radians(abs(d) + abs(m) / 60.0 + (abs(s) + abs(u) / 1e6) / 3600.0)


def location():
    st = data['site']
    pi = doc.ProjectInformation
    pi.Name = data['building']['name'] or u'Магазин'
    pi.BuildingName = data['building']['name'] or u'Магазин'
    miss = set()
    set_psets(pi, data['building']['psets'], miss)
    addr = data['building']['psets'].get('RusSet_Project', {}).get('RUS_BuildingAddress')
    if addr:
        pi.Address = addr[1]
    sl = doc.SiteLocation
    sl.Latitude = dms_rad(st['ref_latitude'])
    sl.Longitude = dms_rad(st['ref_longitude'])
    E, N, th = st['east_mm'], st['north_mm'], math.radians(st['x_axis_angle_deg_ccw_from_east'])
    want = (E + 10000 * math.cos(th), N + 10000 * math.sin(th))
    if miss:
        log(u'   не нашлись параметры проекта:', sorted(miss))
    pl = doc.ActiveProjectLocation
    for sign in (1, -1):
        pl.SetProjectPosition(XYZ.Zero, ProjectPosition(E * MM, N * MM, st['elev_mm'] * MM, sign * th))
        doc.Regenerate()
        t = pl.GetTotalTransform()
        for tt in (t, t.Inverse):
            q = tt.OfPoint(P(10000, 0, 0))
            if abs(q.X / MM - want[0]) < 1 and abs(q.Y / MM - want[1]) < 1:
                log(u'7. общие координаты МСК-77: E %.3f N %.3f м, угол %+.4f° — проверено по точке'
                    % (E / 1000, N / 1000, sign * math.degrees(th)))
                return
    log(u'7. ПРОВЕРИТЬ ВРУЧНУЮ общие координаты: точка в (0,0) = E %.3f N %.3f м, ось X повернута на %.4f° '
        u'против часовой от востока' % (E / 1000, N / 1000, math.degrees(th)))


def sheet(view):
    tbs = list(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_TitleBlocks)
               .OfClass(FamilySymbol).ToElements())
    if not tbs:
        log(u'8. основной надписи в шаблоне нет — лист не создан, план есть:', view.Name)
        return
    sh = ViewSheet.Create(doc, tbs[0].Id)
    sh.SheetNumber = u'АР-1'
    sh.Name = u'План 1 этажа'
    Viewport.Create(doc, sh.Id, view.Id, XYZ(1.0, 0.7, 0))
    log(u'8. лист АР-1 «План 1 этажа» с видом', view.Name)


def main():
    tr = Transaction(doc, u'АГР-1: сборка АР из IFC')
    tr.Start()
    try:
        bind_params()
        lv = levels()
        lv0 = sorted(lv.values(), key=lambda l: l.Elevation)[0]
        grids(lv0.Elevation / MM)
        elements()
        view = plan_view(lv0)
        try:
            view.Name = lv0.Name
        except Exception:
            pass
        for step in (lambda: rooms(lv0, view), lambda: areas(lv0), location, lambda: sheet(view)):
            try:
                step()
            except Exception as ex:
                log(u'   ОШИБКА шага (остальное продолжено):', ex)
        tr.Commit()
        log(u'ГОТОВО. Сохраните проект как НН_К01_С01_АР_АГР.rvt')
    except Exception as ex:
        tr.RollBack()
        log(u'ОСТАНОВЛЕНО, изменения отменены:', ex)
    io.open(os.path.join(HERE, 'build_report.txt'), 'w', encoding='utf-8').write(u'\n'.join(LOG))


main()
