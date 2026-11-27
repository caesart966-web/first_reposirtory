# -*- coding: utf-8 -*-
"""Стены телом, облицовка навесного фасада — IfcCovering (CLADDING), высота зон площадей — по выгрузке.

Запуск: pyRevit, в собранной модели (после build_ar_pyrevit.py). Отчёт — walls_report.txt рядом со скриптом.
  * стены (IfcWall), которые в модели сеткой (Mesh), получают тело вытягиванием профиля фасада с проёмами на толщину
    (walls_prism.json из wall_prisms.py): выгрузка IFC 27.11.2026 пропустила 10 стен-сеток;
  * облицовки навесного фасада (8 шт.) — DirectShape в «Обобщённых моделях», IfcExportAs = IfcCovering,
    IfcExportType = CLADDING. В категории «Стены» выгрузка делает из них IfcWall, а для IfcWall проверка ЦИМ (IDS
    «Стена, перегородка») допускает только коды стен — у облицовки код «Фасад» ЭЛ 30 10 60; IfcCurtainWall из
    «Обобщённых моделей» выгрузка не делает (вышел IfcBuildingElementProxy — для ЦИМ АГР запрещён). IfcCovering
    с типом CLADDING — класс облицовки по требованиям к ЦИМ АР (ч. 2, приложение: «Облицовка — IfcCovering, тип
    CLADDING»). Облицовка из категории «Стены» пересоздаётся (имя, тип, GUID, параметры прежние), уже пересозданной
    меняются IfcExportAs и IfcExportType;
  * зоны площадей выгружаются на высоту от уровня до следующего (4,5 м), а RUS_Height стоял 3,8 м — RUS_Height и
    RUS_Volume ставятся по высоте выгрузки (то же расхождение было в замечании проверки 27.11.2026);
  * копия RusSets_mapping.txt (наборы RusSet_* и для IfcCovering) — в папку TRM на рабочем столе.
Повторный запуск безопасен.
"""
import io
import json
import os
import shutil

import clr
clr.AddReference('RevitAPI')
from System.Collections.Generic import List  # noqa: E402
from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory, BuiltInParameter, CurveLoop, DirectShape, DirectShapeType, ElementId, FailureProcessingResult,
    FailureSeverity, FilteredElementCollector, GeometryCreationUtilities, GeometryObject, IFailuresPreprocessor,
    Level, Line, Mesh, Options, Solid, StorageType, Transaction, ViewDetailLevel, XYZ)

HERE = os.path.dirname(os.path.abspath(__file__))
MM = 1.0 / 304.8
LOG = []
doc = __revit__.ActiveUIDocument.Document  # noqa: F821
with io.open(os.path.join(HERE, '..', 'BuildAR.pushbutton', 'ar_model.json'), encoding='utf-8') as f:
    data = json.load(f)
with io.open(os.path.join(HERE, 'walls_prism.json'), encoding='utf-8') as f:
    PRISMS = json.load(f)
BY_GUID = dict((e['guid'], e) for e in data['elements'])
GENERIC = ElementId(BuiltInCategory.OST_GenericModel)
CLAD = (u'IfcCovering', u'CLADDING')


def log(*a):
    s = u' '.join(u'%s' % x for x in a)
    LOG.append(s)
    print(s)


class QuietWarnings(IFailuresPreprocessor):
    def PreprocessFailures(self, fa):
        for f in fa.GetFailureMessages():
            if f.GetSeverity() == FailureSeverity.Warning:
                fa.DeleteWarning(f)
        return FailureProcessingResult.Continue


def clean_name(s):
    s = u'%s' % (s or u'')
    for ch in u'\\:{}[]|;<>?`~':
        s = s.replace(ch, u'-')
    return s.strip() or u'-'


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


def is_solid(ds, opt):
    ge = ds.get_Geometry(opt)
    if ge is None:
        return False
    s = m = 0
    for g in ge:
        if isinstance(g, Solid) and g.Volume > 1e-9:
            s += 1
        elif isinstance(g, Mesh):
            m += 1
    return s > 0 and m == 0


def prism_geometry(p):
    n, U, s0 = p['n'], p['U'], p['s_min']

    def pt(u, v):
        return XYZ((U[0] * u + n[0] * s0) * MM, (U[1] * u + n[1] * s0) * MM, (U[2] * u + v + n[2] * s0) * MM)
    out = List[GeometryObject]()
    for q in p['polys']:
        loops = List[CurveLoop]()
        for loop in [q['ext']] + q['holes']:
            pts = [pt(u, v) for u, v in loop]
            cl = CurveLoop()
            for i in range(len(pts)):
                cl.Append(Line.CreateBound(pts[i], pts[(i + 1) % len(pts)]))
            loops.Add(cl)
        out.Add(GeometryCreationUtilities.CreateExtrusionGeometry(loops, XYZ(n[0], n[1], n[2]), p['th'] * MM))
    return out


def volume_m3(geo):
    return sum(g.Volume for g in geo) / (MM ** 3) / 1e9


def zones():
    levels = sorted([lv.Elevation for lv in FilteredElementCollector(doc).OfClass(Level).ToElements()])
    n = 0
    for a in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Areas).WhereElementIsNotElementType():
        if a.Area <= 0:
            continue
        z0 = doc.GetElement(a.LevelId).Elevation
        up = [z for z in levels if z > z0 + 1e-6]
        if not up:
            continue
        h = (up[0] - z0) / MM
        am2 = a.Area * 0.09290304
        if set_param(a, u'RUS_Height', h) and set_param(a, u'RUS_Volume', am2 * h / 1000.0):
            n += 1
    log(u'Зоны площадей: RUS_Height = высота выгрузки (до следующего уровня), RUS_Volume — по ней, площадей: %d' % n)


def mapping_copy():
    src = os.path.join(HERE, '..', 'BuildAR.pushbutton', 'RusSets_mapping.txt')
    dst_dir = os.path.join(os.path.expanduser('~'), 'Desktop', 'TRM')
    if not os.path.isdir(dst_dir):
        os.makedirs(dst_dir)
    shutil.copyfile(src, os.path.join(dst_dir, 'RusSets_mapping.txt'))
    log(u'Файл наборов свойств обновлён:', os.path.join(dst_dir, 'RusSets_mapping.txt'))


def main():
    opt = Options()
    opt.DetailLevel = ViewDetailLevel.Fine
    shapes = dict((d.ApplicationDataId, d) for d in FilteredElementCollector(doc).OfClass(DirectShape).ToElements()
                  if d.ApplicationId == u'agr17a')
    types = {}
    tr = Transaction(doc, u'Стены телом')
    o = tr.GetFailureHandlingOptions()
    o.SetFailuresPreprocessor(QuietWarnings())
    tr.SetFailureHandlingOptions(o)
    tr.Start()
    n_set = n_new = n_skip = 0
    bad = []
    try:
        for guid, p in PRISMS.items():
            e = BY_GUID.get(guid)
            old = shapes.get(guid)
            if e is None or old is None:
                bad.append(u'нет элемента %s' % guid)
                continue
            try:
                geo = prism_geometry(p)
            except Exception as ex:
                bad.append(u'%s: профиль не построился (%s)' % (e['name'], ex))
                continue
            vol = volume_m3(geo)
            if e['ifc_class'] == 'IfcCurtainWall':
                if old.Category is not None and old.Category.Id.Equals(GENERIC):
                    a = set_param(old, u'IfcExportAs', CLAD[0])
                    b = set_param(old, u'IfcExportType', CLAD[1])
                    n_skip += 1
                    log(u'   облицовка «%s»: IfcExportAs = %s, IfcExportType = %s%s' % (
                        e['name'].split(u':')[-1], CLAD[0], CLAD[1], u'' if a and b else u' — НЕ ЗАПИСАНО'))
                    continue
                ds = DirectShape.CreateElement(doc, GENERIC)
                ds.ApplicationId = u'agr17a'
                ds.ApplicationDataId = guid
                ds.SetShape(geo)
                full = e['type_name'] or e['name']
                fam, _, typ = full.partition(u':')
                if full not in types:
                    t = DirectShapeType.Create(doc, clean_name(typ or fam), GENERIC)
                    if typ:
                        t.SetFamilyName(clean_name(fam))
                    types[full] = t
                ds.SetTypeId(types[full].Id)
                try:
                    ds.SetName(clean_name(e['name']))
                except Exception:
                    pass
                miss = []
                for k, v in [(u'IfcExportAs', CLAD[0]), (u'IfcExportType', CLAD[1]), (u'IfcName', e['name'])]:
                    if not set_param(ds, k, v):
                        miss.append(k)
                for pn in e['psets']:
                    for k, v in e['psets'][pn].items():
                        if not set_param(ds, k, v):
                            miss.append(k)
                g = ds.get_Parameter(BuiltInParameter.IFC_GUID)
                doc.Delete(old.Id)
                if g is not None and not g.IsReadOnly:
                    g.Set(guid)
                n_new += 1
                log(u'   облицовка «%s» -> обобщённая модель, %s %s, объём %.3f м³%s'
                    % (e['name'].split(u':')[-1], CLAD[0], CLAD[1], vol,
                       (u', НЕ записаны: ' + u', '.join(miss)) if miss else u''))
            else:
                if is_solid(old, opt):
                    n_skip += 1
                    continue
                old.SetShape(geo)
                doc.Regenerate()
                n_set += 1
                log(u'   стена «%s» -> тело, объём %.3f м³, тело: %s'
                    % (e['name'].split(u':')[-1], vol, u'да' if is_solid(old, opt) else u'НЕТ'))
        zones()
        tr.Commit()
        try:
            mapping_copy()
        except Exception as ex:
            log(u'   ОШИБКА копирования файла наборов свойств:', ex)
        log(u'Стен телом: %d, облицовок пересоздано: %d, уже были в порядке: %d, ошибок: %d'
            % (n_set, n_new, n_skip, len(bad)))
        for b in bad:
            log(u'   ОШИБКА:', b)
        log(u'ГОТОВО. Сохранить проект (Ctrl+S)')
    except Exception as ex:
        if tr.HasStarted() and not tr.HasEnded():
            tr.RollBack()
        log(u'ОСТАНОВЛЕНО, изменения отменены:', ex)
    with io.open(os.path.join(HERE, 'walls_report.txt'), 'w', encoding='utf-8') as f:
        f.write(u'\n'.join(LOG))


main()
