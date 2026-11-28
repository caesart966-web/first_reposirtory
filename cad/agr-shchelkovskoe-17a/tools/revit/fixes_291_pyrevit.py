# -*- coding: utf-8 -*-
"""Правки модели АР по проверке ЦИМ и справке заказчика 28.11.2026 — одной кнопкой («Правки 29.11»).

Запуск: pyRevit, в модели НН_К01_С01_АР_АГР.rvt. Отчёт — fixes291_report.txt рядом со скриптом. Повторный запуск
безопасен. После него — сохранить и выгрузить IFC + TRM плагином «Строим просто», как 27.11.
  1. Планы этажей: «Дисциплина» — Архитектура, «Подраздел» — «АР». Проверка ЦИМ (входной контроль, «Проверка на
     привязку планов к уровням») пишет «…или отсутствует дисциплина»; названия уровней при этом точно по требованиям
     Москвы к ЦИМ (ч. 1, примеры «С01_1_этаж_основной», «С01_крыша_дополнительный»), а у плана в TRM поле раздела
     пустое («  - План этажа - С01_1_этаж_основной»). Параметра «Подраздел» нет в проекте без шаблона — он
     добавляется общим параметром из Views_params.txt.
  2. Ось «З» -> «И»: буквы З, Й, О, Х, Ц, Ч, Щ, Ъ, Ы, Ь для осей не применяют (ГОСТ 21.101), в буклете и DWG — «И».
  3. RUS_Volume 13 частей кровли (исходный элемент 427184): у каждой стоял объём всей кровли 19,266 м³ (сумма 250 м³),
     ставится объём своей части по геометрии (сумма 19,145 м³).
  4. Стена 423961 удаляется: она целиком внутри стены 410006 того же типа (пересечение 0,783 м³ = весь её объём 0,781).
"""
import io
import os

import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory, BuiltInParameter, CategorySet, DirectShape, FilteredElementCollector, Grid, StorageType,
    Transaction, ViewPlan, ViewType)

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = []
doc = __revit__.ActiveUIDocument.Document  # noqa: F821
SUB = u'АР'
AXES = {u'З': u'И'}
DUP_WALL = u'1irTgMiGz4w89bdAsGkiBf'          # стена 423961, целиком внутри 410006
ROOF_VOL = {                                   # м³, по геометрии частей (IfcOpenShell, выгрузка 27.11.2026)
    u'3kaKj1Nn5ALf$F9CVIrfcU': 0.176, u'3kaKj1Nn5ALf$F9CRIrfcU': 1.671, u'3kaKj1Nn5ALf$F9C7IrfcU': 1.140,
    u'3kaKj1Nn5ALf$F9C3IrfcU': 5.072, u'3kaKj1Nn5ALf$F9CFIrfcU': 0.224, u'3kaKj1Nn5ALf$F9CBIrfcU': 1.668,
    u'3kaKj1Nn5ALf$F9CtIrfcU': 0.988, u'3kaKj1Nn5ALf$F9CpIrfcU': 2.095, u'3kaKj1Nn5ALf$F9C$IrfcU': 5.600,
    u'3kaKj1Nn5ALf$F9CxIrfcU': 0.066, u'3kaKj1Nn5ALf$F9CdIrfcU': 0.176, u'3kaKj1Nn5ALf$F9CZIrfcU': 0.024,
    u'3kaKj1Nn5ALf$F9ClIrfcU': 0.245}


def log(*a):
    s = u' '.join(u'%s' % x for x in a)
    LOG.append(s)
    print(s)


def bind_subdiscipline():
    """Общий параметр «Подраздел» (текст) для категории «Виды», если в проекте его нет."""
    probe = [v for v in FilteredElementCollector(doc).OfClass(ViewPlan) if not v.IsTemplate]
    if probe and (probe[0].LookupParameter(u'Подраздел') or probe[0].LookupParameter(u'Sub-Discipline')):
        return u'уже есть в проекте'
    app = __revit__.Application  # noqa: F821
    old = app.SharedParametersFilename
    app.SharedParametersFilename = os.path.join(HERE, 'Views_params.txt')
    try:
        sp = app.OpenSharedParameterFile()
        cats = CategorySet()
        cats.Insert(doc.Settings.Categories.get_Item(BuiltInCategory.OST_Views))
        binding = app.Create.NewInstanceBinding(cats)
        try:
            from Autodesk.Revit.DB import GroupTypeId
            grp = GroupTypeId.IdentityData
        except Exception:
            from Autodesk.Revit.DB import BuiltInParameterGroup
            grp = BuiltInParameterGroup.PG_IDENTITY_DATA
        for g in sp.Groups:
            for d in g.Definitions:
                if not doc.ParameterBindings.Contains(d):
                    doc.ParameterBindings.Insert(d, binding, grp)
    finally:
        app.SharedParametersFilename = old or u''
    doc.Regenerate()
    return u'добавлен общим параметром'


def views():
    log(u'1. Планы: «Подраздел» —', bind_subdiscipline())
    for v in FilteredElementCollector(doc).OfClass(ViewPlan):
        if v.IsTemplate or v.ViewType not in (ViewType.FloorPlan, ViewType.CeilingPlan):
            continue
        d = v.get_Parameter(BuiltInParameter.VIEW_DISCIPLINE)
        before = d.AsValueString() if d else u'—'
        if d and not d.IsReadOnly and d.AsInteger() != 1:
            d.Set(1)                                    # 1 — Архитектура
        names = []
        for n in (u'Подраздел', u'Sub-Discipline'):
            p = v.LookupParameter(n)
            if p is not None and not p.IsReadOnly and p.StorageType == StorageType.String:
                p.Set(SUB)
                names.append(n)
        log(u'   план «%s»: дисциплина %s -> %s; %s = «%s»' % (
            v.Name, before, d.AsValueString() if d else u'—', u', '.join(names) or u'ПОДРАЗДЕЛ НЕ ЗАПИСАН', SUB))


def grids():
    have = dict((g.Name, g) for g in FilteredElementCollector(doc).OfClass(Grid))
    for a, b in AXES.items():
        if a in have and b not in have:
            have[a].Name = b
            log(u'2. Ось «%s» -> «%s»' % (a, b))
        elif b in have and a not in have:
            log(u'2. Ось «%s» уже есть, «%s» нет — без изменений' % (b, a))
        else:
            log(u'2. ОСИ: «%s» %s, «%s» %s — проверить вручную' % (a, a in have, b, b in have))


def shapes():
    ds = dict((d.ApplicationDataId, d) for d in FilteredElementCollector(doc).OfClass(DirectShape).ToElements()
              if d.ApplicationId == u'agr17a')
    n = 0
    for guid, vol in sorted(ROOF_VOL.items()):
        d = ds.get(guid)
        p = d.LookupParameter(u'RUS_Volume') if d else None
        if p is None or p.IsReadOnly:
            log(u'   ОШИБКА: часть кровли %s — нет элемента или RUS_Volume' % guid)
            continue
        p.Set(float(vol))
        n += 1
    log(u'3. RUS_Volume частей кровли 427184: записано %d из %d, сумма %.3f м³' % (n, len(ROOF_VOL),
                                                                              sum(ROOF_VOL.values())))
    w = ds.get(DUP_WALL)
    if w is None:
        log(u'4. Стена 423961: уже удалена')
    else:
        doc.Delete(w.Id)
        log(u'4. Стена 423961 удалена (дубль внутри стены 410006)')


def main():
    tr = Transaction(doc, u'Правки 29.11')
    tr.Start()
    try:
        views()
        grids()
        shapes()
        tr.Commit()
        log(u'ГОТОВО. Сохранить (Ctrl+S) и выгрузить IFC + TRM плагином «Строим просто»')
    except Exception as ex:
        if tr.HasStarted() and not tr.HasEnded():
            tr.RollBack()
        log(u'ОСТАНОВЛЕНО, изменения отменены:', ex)
    with io.open(os.path.join(HERE, 'fixes291_report.txt'), 'w', encoding='utf-8') as f:
        f.write(u'\n'.join(LOG))


main()
