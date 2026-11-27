# -*- coding: utf-8 -*-
"""Классы IFC элементов — встроенными параметрами Revit «Экспорт в IFC как» и «Предопределённый тип IFC».

Запуск: pyRevit, в собранной модели. Отчёт — classes_report.txt рядом со скриптом. Повторный запуск безопасен.
Выгрузки 27.11.2026 показали: экспорт IFC Revit 2025 не читает общий параметр IfcExportAs/IfcExportType
(облицовки в «Обобщённых моделях» вышли IfcBuildingElementProxy, 14 плит кровли — IfcSlab.FLOOR вместо ROOF,
двери — NOTDEFINED вместо DOOR). Класс и тип берутся из исходного IFC (ar_model.json): облицовка навесного
фасада — IfcCurtainWall (как в исходной модели и в IDS «Фасад, витраж» с кодом ЭЛ 30 10 60), плиты кровли —
IfcSlab ROOF, двери — DOOR, колонны — COLUMN. Общие параметры IfcExportAs/IfcExportType ставятся теми же.
Уровень кровли (С01_крыша_дополнительный) — не «Этаж здания»: иначе Revit пишет в Pset_BuildingCommon
NumberOfStoreys = 2 при этажности 1 в ТЭП (FloorsCount), а проверка ЦИМ требует СПП на каждом надземном уровне,
в том числе на кровле. Элементы кровли выгружаются в составе этажа С01_1_этаж_основной.
"""
import io
import json
import os

import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInParameter, DirectShape, FilteredElementCollector, Level, Transaction)

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = []
doc = __revit__.ActiveUIDocument.Document  # noqa: F821
with io.open(os.path.join(HERE, '..', 'BuildAR.pushbutton', 'ar_model.json'), encoding='utf-8') as f:
    data = json.load(f)
BY_GUID = dict((e['guid'], e) for e in data['elements'])
AS_NAMES = [u'Экспорт в IFC как', u'Export to IFC As']
PT_NAMES = [u'Предопределённый тип IFC', u'Предопределенный тип IFC', u'IFC Predefined Type']


def log(*a):
    s = u' '.join(u'%s' % x for x in a)
    LOG.append(s)
    print(s)


def bip(name):
    return getattr(BuiltInParameter, name, None)


B_AS, B_PT = bip('IFC_EXPORT_ELEMENT_AS'), bip('IFC_EXPORT_PREDEFINEDTYPE')


def param(el, b, names):
    p = el.get_Parameter(b) if b is not None else None
    if p is None:
        for n in names:
            p = el.LookupParameter(n)
            if p is not None:
                break
    return p


def put(el, b, names, v):
    p = param(el, b, names)
    if p is None or p.IsReadOnly:
        return False
    p.Set(v)
    return p.AsString() == v


def shared(el, name, v):
    p = el.LookupParameter(name)
    if p is not None and not p.IsReadOnly:
        p.Set(v)


def main():
    shapes = [d for d in FilteredElementCollector(doc).OfClass(DirectShape).ToElements() if d.ApplicationId == u'agr17a']
    tr = Transaction(doc, u'Классы IFC')
    tr.Start()
    try:
        cnt, bad = {}, []
        for ds in shapes:
            e = BY_GUID.get(ds.ApplicationDataId)
            if e is None:
                continue
            cls = e['ifc_class']
            pt = e.get('predefined') or u''
            if pt in (u'NOTDEFINED', u'USERDEFINED'):
                pt = u''
            if cls == 'IfcSlab' and e.get('part_of') == 'IfcRoof':
                pt = u'ROOF'
            ok_as = put(ds, B_AS, AS_NAMES, cls)
            ok_pt = put(ds, B_PT, PT_NAMES, pt) if pt else True
            shared(ds, u'IfcExportAs', cls)
            shared(ds, u'IfcExportType', pt)
            if not (ok_as and ok_pt):
                bad.append(u'%s (%s%s)' % (e['name'], u'' if ok_as else u'«Экспорт в IFC как» ',
                                         u'' if ok_pt else u'«Предопределённый тип»'))
            k = u'%s %s' % (cls, pt or u'')
            cnt[k] = cnt.get(k, 0) + 1
        for lv in FilteredElementCollector(doc).OfClass(Level).ToElements():
            p = lv.get_Parameter(BuiltInParameter.LEVEL_IS_BUILDING_STORY)
            if p is None or p.IsReadOnly:
                continue
            want = 0 if u'крыша' in lv.Name else 1
            if p.AsInteger() != want:
                p.Set(want)
            log(u'Уровень «%s»: «Этаж здания» — %s' % (lv.Name, u'да' if want else u'нет'))
        tr.Commit()
        log(u'Встроенный параметр «Экспорт в IFC как»:', u'есть' if B_AS is not None else u'нет — по имени')
        log(u'Проставлено:', u'; '.join(u'%s — %d' % (k.strip(), v) for k, v in sorted(cnt.items())))
        log(u'Не записано: %d' % len(bad))
        for b in bad:
            log(u'   ОШИБКА:', b)
        log(u'ГОТОВО. Сохранить проект (Ctrl+S)')
    except Exception as ex:
        if tr.HasStarted() and not tr.HasEnded():
            tr.RollBack()
        log(u'ОСТАНОВЛЕНО, изменения отменены:', ex)
    with io.open(os.path.join(HERE, 'classes_report.txt'), 'w', encoding='utf-8') as f:
        f.write(u'\n'.join(LOG))


main()
