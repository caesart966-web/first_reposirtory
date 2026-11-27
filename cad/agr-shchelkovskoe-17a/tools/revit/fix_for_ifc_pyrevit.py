# -*- coding: utf-8 -*-
"""Доработка собранной модели перед выгрузкой IFC (после build_ar_pyrevit.py и первой выгрузки 27.11.2026).

Запуск: pyRevit, в том же проекте. Отчёт — fix_report.txt рядом со скриптом. Повторный запуск безопасен.
  1. проверка геометрии каждого элемента DirectShape: тело (Solid) или сетка (Mesh). Выгрузка IFC пропустила
     10 наружных стен — у всех исходная геометрия сложная (скошенный верх, проёмы). Элементы без тела
     перестраиваются телом: вершины сводятся с допуском 1 мм, вырожденные треугольники удаляются, построитель
     требует тело (Solid) без перехода в сетку. Если тело не строится — элемент остаётся как был, в отчёте ОШИБКА;
  2. параметр IfcName (общий параметр, группа IFC) — имя объекта в IFC как в исходной модели (у элементов
     и зон площадей); без него выгрузка пишет «Семейство:Тип:Id»;
  3. зоны площадей: у каждой площади свои RUS_Area и RUS_Volume (у четырёх частей «Общей площади» стояла
     площадь всей зоны — при сложении вышло бы вчетверо больше), самой большой части — GUID зоны из IFC;
  4. сводка IfcExportAs по элементам;
  5. копия RusSets_mapping.txt в папку TRM на рабочем столе — её выбирают в настройках IFC плагина
     («Характеристики» -> «Пользовательские наборы характеристик»).
"""
import io
import json
import os
import shutil
import uuid

import clr
clr.AddReference('RevitAPI')
from System.Collections.Generic import List  # noqa: E402
from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory, BuiltInParameter, CategorySet, DirectShape, ElementId, FilteredElementCollector, Mesh, Options,
    Solid, Transaction, TessellatedFace, TessellatedShapeBuilder, TessellatedShapeBuilderFallback,
    TessellatedShapeBuilderOutcome, TessellatedShapeBuilderTarget, ViewDetailLevel, XYZ)

HERE = os.path.dirname(os.path.abspath(__file__))
MM = 1.0 / 304.8
LOG = []
app = __revit__.Application  # noqa: F821
doc = __revit__.ActiveUIDocument.Document  # noqa: F821
data = json.load(io.open(os.path.join(HERE, '..', 'BuildAR.pushbutton', 'ar_model.json'), encoding='utf-8'))
BY_GUID = dict((e['guid'], e) for e in data['elements'])
PARAMS = os.path.join(HERE, 'IFC_extra_params.txt')
BIND_CATS = [BuiltInCategory.OST_Walls, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Roofs,
             BuiltInCategory.OST_Columns, BuiltInCategory.OST_Doors, BuiltInCategory.OST_Windows,
             BuiltInCategory.OST_StairsRailing, BuiltInCategory.OST_Stairs, BuiltInCategory.OST_Ramps,
             BuiltInCategory.OST_GenericModel, BuiltInCategory.OST_Rooms, BuiltInCategory.OST_Areas]


def log(*a):
    s = u' '.join(u'%s' % x for x in a)
    LOG.append(s)
    print(s)


def P(x, y, z):
    return XYZ(x * MM, y * MM, z * MM)


def write_params():
    g = uuid.uuid5(uuid.NAMESPACE_URL, 'agr17a/IfcName')
    txt = (u'# This is a Revit shared parameter file.\r\n# Do not edit manually.\r\n*META\tVERSION\tMINVERSION\r\n'
           u'META\t2\t1\r\n*GROUP\tID\tNAME\r\nGROUP\t2\tIFC\r\n*PARAM\tGUID\tNAME\tDATATYPE\tDATACATEGORY\tGROUP\t'
           u'VISIBLE\tDESCRIPTION\tUSERMODIFIABLE\tHIDEWHENNOEXIST\r\nPARAM\t%s\tIfcName\tTEXT\t\t2\t1\t\t1\t0\r\n' % g)
    io.open(PARAMS, 'w', encoding='utf-16', newline=u'').write(txt)        # без перевода \n -> \r\n: строки уже с \r\n


def bind():
    write_params()
    old = app.SharedParametersFilename
    app.SharedParametersFilename = PARAMS
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
            grp = GroupTypeId.Ifc
        except Exception:
            from Autodesk.Revit.DB import BuiltInParameterGroup
            grp = BuiltInParameterGroup.PG_IFC
        for g in sp.Groups:
            for d in g.Definitions:
                if doc.ParameterBindings.Contains(d):
                    doc.ParameterBindings.ReInsert(d, binding, grp)
                else:
                    doc.ParameterBindings.Insert(d, binding, grp)
    finally:
        app.SharedParametersFilename = old or u''
    log(u'2. параметр IfcName добавлен, категорий:', cats.Size)


def setp(el, name, v):
    p = el.LookupParameter(name)
    if p is None or p.IsReadOnly:
        return False
    try:
        return p.Set(v)
    except Exception:
        return False


def kinds(ds, opt):
    s, m, vol = 0, 0, 0.0
    ge = ds.get_Geometry(opt)
    if ge is None:
        return 0, 0, 0.0
    for g in ge:
        if isinstance(g, Solid) and g.Volume > 1e-9:
            s += 1
            vol += g.Volume
        elif isinstance(g, Mesh):
            m += 1
    return s, m, vol / (MM ** 3) / 1e9


def solid_shape(e, tol=1.0):
    idx, pts, remap = {}, [], []
    for v in e['verts']:
        k = (int(round(v[0] / tol)), int(round(v[1] / tol)), int(round(v[2] / tol)))
        if k not in idx:
            idx[k] = len(pts)
            pts.append(v)
        remap.append(idx[k])
    b = TessellatedShapeBuilder()
    b.OpenConnectedFaceSet(True)
    n = 0
    for f in e['faces']:
        a, c, d = remap[f[0]], remap[f[1]], remap[f[2]]
        if a == c or c == d or a == d:
            continue
        A, C, D = pts[a], pts[c], pts[d]
        ux, uy, uz = C[0] - A[0], C[1] - A[1], C[2] - A[2]
        vx, vy, vz = D[0] - A[0], D[1] - A[1], D[2] - A[2]
        cr = ((uy * vz - uz * vy) ** 2 + (uz * vx - ux * vz) ** 2 + (ux * vy - uy * vx) ** 2) ** 0.5
        if cr < 2.0:
            continue
        b.AddFace(TessellatedFace(List[XYZ]([P(*A), P(*C), P(*D)]), ElementId.InvalidElementId))
        n += 1
    b.CloseConnectedFaceSet()
    b.Target = TessellatedShapeBuilderTarget.Solid
    b.Fallback = TessellatedShapeBuilderFallback.Abort
    b.Build()
    r = b.GetBuildResult()
    return r, n


def geometry():
    opt = Options()
    opt.DetailLevel = ViewDetailLevel.Fine
    shapes = [d for d in FilteredElementCollector(doc).OfClass(DirectShape).ToElements()
              if d.ApplicationId == u'agr17a']
    fixed, bad, solid_ok = 0, [], 0
    for ds in shapes:
        e = BY_GUID.get(ds.ApplicationDataId)
        s, m, vol = kinds(ds, opt)
        if s and not m:
            solid_ok += 1
            continue
        nm = e['name'] if e else ds.ApplicationDataId
        log(u'   сетка, не тело: %s %s (тел %d, сеток %d)' % (e and e['ifc_class'], nm, s, m))
        if e is None:
            bad.append(nm)
            continue
        done = False
        for tol in (1.0, 2.0, 5.0):
            try:
                r, n = solid_shape(e, tol)
            except Exception as ex:
                log(u'      допуск %.0f мм: %s' % (tol, ex))
                continue
            if r.Outcome == TessellatedShapeBuilderOutcome.Solid:
                ds.SetShape(r.GetGeometricalObjects())
                s2, m2, vol2 = kinds(ds, opt)
                log(u'      перестроено телом, допуск %.0f мм, граней %d, объём %.3f м³' % (tol, n, vol2))
                fixed += 1
                done = True
                break
            log(u'      допуск %.0f мм: тело не строится (%s)' % (tol, r.Outcome))
        if not done:
            bad.append(nm)
    log(u'1. элементов DirectShape: %d, телом сразу: %d, перестроено: %d, не удалось: %d'
        % (len(shapes), solid_ok, fixed, len(bad)))
    for b in bad:
        log(u'   ОШИБКА: тело не строится —', b)
    return shapes


def names(shapes):
    n = 0
    for ds in shapes:
        e = BY_GUID.get(ds.ApplicationDataId)
        if e and e['name'] and setp(ds, u'IfcName', e['name']):
            n += 1
    log(u'2. IfcName у элементов:', n, u'из', len(shapes))


def areas():
    zs = dict(((s['psets'].get('RusSet_Common', {}).get('RUS_Name') or [None, None])[1], s)
              for s in data['spaces'] if s['kind'] == 'area')
    got = {}
    for a in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Areas).WhereElementIsNotElementType():
        p = a.LookupParameter(u'RUS_Name')
        nm = p.AsString() if p is not None else None
        if nm in zs and a.Area > 0:
            got.setdefault(nm, []).append(a)
    for nm, lst in got.items():
        z = zs[nm]
        h = None
        for k, v in z['psets'].get('RusSet_Quantities', {}).items():
            if k == 'RUS_Height' and v:
                h = float(v[1])
        lst.sort(key=lambda a: -a.Area)
        tot = 0.0
        for i, a in enumerate(lst):
            am2 = a.Area * 0.09290304
            tot += am2
            setp(a, u'RUS_Area', am2)
            if h:
                setp(a, u'RUS_Volume', am2 * h / 1000.0)
            setp(a, u'IfcName', z['name'] if i == 0 else u'%s.%d' % (z['name'], i + 1))
            if i == 0:
                g = a.get_Parameter(BuiltInParameter.IFC_GUID)
                if g is not None and not g.IsReadOnly:
                    g.Set(z['guid'])
        log(u'3. зона «%s»: площадей %d, RUS_Area по каждой, сумма %.2f м² (по данным %.2f)'
            % (nm, len(lst), tot, z['area_m2']))


def export_as(shapes):
    c = {}
    for ds in shapes:
        p = ds.LookupParameter(u'IfcExportAs')
        v = p.AsString() if p is not None else None
        c[v] = c.get(v, 0) + 1
    log(u'4. IfcExportAs:', u'; '.join(u'%s — %d' % (k, v) for k, v in sorted(c.items(), key=lambda x: u'%s' % x[0])))


def mapping_copy():
    src = os.path.join(HERE, '..', 'BuildAR.pushbutton', 'RusSets_mapping.txt')
    dst_dir = os.path.join(os.path.expanduser('~'), 'Desktop', 'TRM')
    if not os.path.isdir(dst_dir):
        os.makedirs(dst_dir)
    dst = os.path.join(dst_dir, 'RusSets_mapping.txt')
    shutil.copyfile(src, dst)
    log(u'5. файл наборов свойств для настроек IFC:', dst)


def main():
    tr = Transaction(doc, u'Доработка модели для IFC')
    tr.Start()
    try:
        bind()
        shapes = geometry()
        for step in (lambda: names(shapes), areas, lambda: export_as(shapes)):
            try:
                step()
            except Exception as ex:
                log(u'   ОШИБКА шага, остальные шаги продолжены:', ex)
        tr.Commit()
        try:
            mapping_copy()
        except Exception as ex:
            log(u'   ОШИБКА копирования файла наборов свойств:', ex)
        log(u'ГОТОВО. Сохранить проект (Ctrl+S)')
    except Exception as ex:
        if tr.HasStarted() and not tr.HasEnded():
            tr.RollBack()
        log(u'ОСТАНОВЛЕНО, изменения отменены:', ex)
    io.open(os.path.join(HERE, 'fix_report.txt'), 'w', encoding='utf-8').write(u'\n'.join(LOG))


main()
