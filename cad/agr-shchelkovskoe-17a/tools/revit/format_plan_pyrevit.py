# -*- coding: utf-8 -*-
"""Оформление плана 1 этажа для видов TRM (как в прежнем TRM: оси, размерные цепочки, номера и площади помещений).

Запуск: pyRevit, после build_ar_pyrevit.py, в том же проекте. Отчёт — format_report.txt рядом со скриптом.
  1. имена планов этажей = имена их уровней (у нового уровня крыши план назывался по шаблону);
  2. план С01_1_этаж_основной: подрезка по зданию с осями, марки фасадов скрыты;
  3. размерные цепочки по осям снизу (1–7) и слева (А–З): шаги и общий размер;
  4. марки помещений — тип с площадью, если он есть в шаблоне; иначе площадь подписывается текстом под маркой.
Повторный запуск не дублирует размеры и подписи: поставленные прошлым запуском (format_state.json) удаляются.
"""
import io
import json
import os

import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory, BuiltInParameter, ElementId, ElementTypeGroup, FilteredElementCollector, Grid, Line,
    Reference, ReferenceArray, TextNote, Transaction, ViewPlan, ViewType, XYZ)

HERE = os.path.dirname(os.path.abspath(__file__))
MM = 1.0 / 304.8
LOG = []
doc = __revit__.ActiveUIDocument.Document  # noqa: F821
data = json.load(io.open(os.path.join(HERE, '..', 'BuildAR.pushbutton', 'ar_model.json'), encoding='utf-8'))


def log(*a):
    s = u' '.join(u'%s' % x for x in a)
    LOG.append(s)
    print(s)


def P(x, y, z=0.0):
    return XYZ(x * MM, y * MM, z * MM)


def tname(t):
    p = t.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
    return (u'%s: %s' % (getattr(t, 'FamilyName', u''), p.AsString() if p else u'')).strip()


def rename_plans():
    used = set(v.Name for v in FilteredElementCollector(doc).OfClass(ViewPlan).ToElements())
    n = 0
    for v in FilteredElementCollector(doc).OfClass(ViewPlan).ToElements():
        if v.IsTemplate or v.ViewType != ViewType.FloorPlan or v.GenLevel is None:
            continue
        want = v.GenLevel.Name
        if v.Name == want or want in used:
            continue
        old = v.Name
        v.Name = want
        used.add(want)
        n += 1
        log(u'1. план «%s» -> «%s»' % (old, want))
    log(u'1. переименовано планов:', n)


def plan_view():
    lv = data['levels'][0]['name']
    for v in FilteredElementCollector(doc).OfClass(ViewPlan).ToElements():
        if not v.IsTemplate and v.ViewType == ViewType.FloorPlan and v.Name == lv:
            return v
    raise Exception(u'нет плана «%s» — сначала «Собрать АР»' % lv)


def crop(v, x0, y0, x1, y1):
    v.CropBoxActive = True
    cb = v.CropBox
    inv = cb.Transform.Inverse
    a, b = inv.OfPoint(P(x0, y0)), inv.OfPoint(P(x1, y1))
    cb.Min = XYZ(min(a.X, b.X), min(a.Y, b.Y), cb.Min.Z)
    cb.Max = XYZ(max(a.X, b.X), max(a.Y, b.Y), cb.Max.Z)
    v.CropBox = cb
    v.CropBoxVisible = False
    eid = ElementId(BuiltInCategory.OST_Elev)
    if v.CanCategoryBeHidden(eid):
        v.SetCategoryHidden(eid, True)
    log(u'2. подрезка вида: x %.0f…%.0f, y %.0f…%.0f мм; марки фасадов скрыты' % (x0, x1, y0, y1))


STATE = os.path.join(HERE, 'format_state.json')
MADE = []


def clear_old():
    """Размеры и подписи прошлого запуска (их UniqueId — в format_state.json) удаляются."""
    if not os.path.exists(STATE):
        return
    n = 0
    for uid in json.load(io.open(STATE, encoding='utf-8')):
        e = doc.GetElement(uid)
        if e is not None:
            doc.Delete(e.Id)
            n += 1
    log(u'   удалено размеров и подписей прошлого запуска:', n)


def mark(e):
    MADE.append(e.UniqueId)


def dims(v):
    grids = dict((g.Name, g) for g in FilteredElementCollector(doc).OfClass(Grid).ToElements())
    vert = sorted([g for g in data['grids'] if abs(g['p0'][0] - g['p1'][0]) < 1], key=lambda g: g['p0'][0])
    hor = sorted([g for g in data['grids'] if abs(g['p0'][1] - g['p1'][1]) < 1], key=lambda g: g['p0'][1])
    n = 0
    for seq, along_x, chain, total in ((vert, True, -1500.0, -2200.0), (hor, False, -3800.0, -4600.0)):
        refs = [grids[g['tag']] for g in seq if g['tag'] in grids]
        if len(refs) < 2:
            log(u'3. мало осей для размеров:', len(refs))
            continue
        c0 = seq[0]['p0'][0 if along_x else 1]
        c1 = seq[-1]['p0'][0 if along_x else 1]
        for off, items in ((chain, refs), (total, [refs[0], refs[-1]])):
            ra = ReferenceArray()
            for g in items:
                ra.Append(Reference(g))
            if along_x:
                ln = Line.CreateBound(P(c0 - 500, off), P(c1 + 500, off))
            else:
                ln = Line.CreateBound(P(off, c0 - 500), P(off, c1 + 500))
            d = doc.Create.NewDimension(v, ln, ra)
            mark(d)
            n += 1
    log(u'3. размерных цепочек:', n)


def room_tags(v):
    types = list(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_RoomTags)
                 .WhereElementIsElementType().ToElements())
    names = [(t, tname(t)) for t in types]
    log(u'4. типы марок помещений в шаблоне:', u'; '.join(n for _, n in names) or u'нет')
    pick = [t for t, n in names if u'площад' in n.lower() or u'area' in n.lower()]
    tags = list(FilteredElementCollector(doc, v.Id).OfCategory(BuiltInCategory.OST_RoomTags)
                .WhereElementIsNotElementType().ToElements())
    if pick:
        for tg in tags:
            try:
                tg.ChangeTypeId(pick[0].Id)
            except Exception:
                tg.RoomTagType = pick[0]
        log(u'4. марки помещений (%d) -> тип «%s»' % (len(tags), tname(pick[0])))
        return
    tt = doc.GetDefaultElementTypeId(ElementTypeGroup.TextNoteType)
    n = 0
    for s in data['spaces']:
        if s['kind'] != 'room':
            continue
        x, y = s['inner_pts'][0]
        area = (u'%.2f' % s['area_m2']).replace(u'.', u',')
        t = TextNote.Create(doc, v.Id, P(x, y - 900.0), area, tt)
        mark(t)
        n += 1
    log(u'4. типа марки с площадью в шаблоне нет — площадь подписана текстом под маркой у %d помещений' % n)


def main():
    tr = Transaction(doc, u'Оформление плана для TRM')
    tr.Start()
    try:
        rename_plans()
        v = plan_view()
        clear_old()
        crop(v, -6600.0, -3900.0, 19200.0, 29000.0)
        for step in (lambda: dims(v), lambda: room_tags(v)):
            try:
                step()
            except Exception as ex:
                log(u'   ОШИБКА шага, остальные шаги продолжены:', ex)
        tr.Commit()
        io.open(STATE, 'w', encoding='utf-8').write(u'%s' % json.dumps(MADE))
        log(u'ГОТОВО. Открыть план «%s», проверить и сохранить проект (Ctrl+S)' % v.Name)
    except Exception as ex:
        if tr.HasStarted() and not tr.HasEnded():
            tr.RollBack()
        log(u'ОСТАНОВЛЕНО, изменения отменены:', ex)
    io.open(os.path.join(HERE, 'format_report.txt'), 'w', encoding='utf-8').write(u'\n'.join(LOG))


main()
