"""Таблица параметров ЦИМ АР для сборки в Revit (из ar_model.json).

    python3 params_table.py <ar_model.json> <Параметры.xlsx>
"""
import collections
import json
import os
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import clean_meta  # noqa: E402

HEAD = PatternFill('solid', fgColor='DDEBF7')


def sheet(wb, title, header, rows, widths=None):
    ws = wb.create_sheet(title)
    ws.append(header)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = HEAD
        c.alignment = Alignment(wrap_text=True, vertical='top')
    for r in rows:
        ws.append(r)
    for i, h in enumerate(header, 1):
        w = (widths or {}).get(h) or min(60, max(10, max(len(str(x[i - 1])) if i - 1 < len(x) and x[i - 1]
                                                             is not None else 0 for x in rows + [header]) + 2))
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = 'A2'
    return ws


def val(v):
    return None if v is None else v[1]


def main(src, out):
    d = json.load(open(src, encoding='utf-8'))
    wb = Workbook()
    wb.remove(wb.active)
    st = d['site']
    rows = [
        ['Общие координаты (МСК-77), восток, м', round(st['east_mm'] / 1000, 4),
         'Точка (0,0,0) проекта Revit = внутреннее начало'],
        ['Общие координаты (МСК-77), север, м', round(st['north_mm'] / 1000, 4), ''],
        ['Отметка внутреннего начала, м', st['elev_mm'] / 1000, 'Уровни — абсолютные отметки'],
        ['Поворот оси X проекта от востока, °', round(st['x_axis_angle_deg_ccw_from_east'], 4),
         'против часовой стрелки'],
        ['Широта IfcSite', '%d°%d\'%d.%06d"' % tuple(st['ref_latitude']), ''],
        ['Долгота IfcSite', '%d°%d\'%d.%06d"' % tuple(st['ref_longitude']), ''],
        ['Сведения о проекте: Наименование / Здание', d['building']['name'], ''],
    ]
    for pn, props in d['building']['psets'].items():
        for k, v in props.items():
            rows.append(['%s.%s (Сведения о проекте)' % (pn, k), val(v), ''])
    for l in d['levels']:
        rows.append(['Уровень', l['name'], 'отметка %+.3f м (абс.)' % (l['elevation_mm'] / 1000)])
    rows += [['Экспорт IFC', 'IFC4 Reference View 1.2', 'база координат — общие координаты'],
             ['Файл IFC', 'НН_К01_С01_АР_АГР.ifc', 'выгрузка плагином «Якорь IFC» вместе с TRM']]
    sheet(wb, 'Проект', ['Что', 'Значение', 'Примечание'], rows, {'Что': 48, 'Значение': 62, 'Примечание': 50})
    sheet(wb, 'Оси', ['Ось', 'X1, мм', 'Y1, мм', 'X2, мм', 'Y2, мм'],
          [[g['tag']] + [round(x, 1) for x in g['p0'] + g['p1']] for g in d['grids']])
    # типы
    keys = []
    for e in d['elements']:
        for pn, props in e['psets'].items():
            if pn == 'RusSet_Quantities':
                continue
            for k in props:
                if (pn, k) not in keys:
                    keys.append((pn, k))
    grp = collections.OrderedDict()
    for e in d['elements']:
        k = (e['ifc_class'], e['predefined'] if e['ifc_class'] != 'IfcSlab' or e['part_of'] != 'IfcRoof'
             else 'ROOF', e['type_name'] or e['name'])
        g = grp.setdefault(k, {'n': 0, 'vals': e['psets']})
        g['n'] += 1
    rows = []
    for (cls, pre, ty), g in grp.items():
        rows.append([cls, pre, ty, g['n']] + [val(g['vals'].get(pn, {}).get(k)) for pn, k in keys])
    sheet(wb, 'Типы элементов', ['Класс IFC', 'PredefinedType', 'Тип (имя в Revit)', 'Кол-во'] +
          ['%s\n%s' % k for k in keys], rows, {'Тип (имя в Revit)': 60})
    qk = []
    for e in d['elements']:
        for k in e['psets'].get('RusSet_Quantities', {}):
            if k not in qk:
                qk.append(k)
    rows = [[e['guid'], e['ifc_class'], e['type_name'], e['name'], e['level']] +
            [val(e['psets'].get(pn, {}).get(k)) for pn, k in keys] +
            [val(e['psets'].get('RusSet_Quantities', {}).get(k)) for k in qk] for e in d['elements']]
    sheet(wb, 'Элементы', ['GUID (IfcGUID)', 'Класс IFC', 'Тип', 'Имя', 'Уровень'] + ['%s\n%s' % k for k in keys] +
          ['RusSet_Quantities\n%s' % k for k in qk], rows, {'Тип': 45, 'Имя': 50})
    sk = []
    for s in d['spaces']:
        for pn, props in s['psets'].items():
            for k in props:
                if (pn, k) not in sk:
                    sk.append((pn, k))
    rows = [[s['name'], s['long_name'], 'помещение' if s['kind'] == 'room' else 'площадь (зона)',
             round(s['area_m2'], 2), len(s['loops']), round(s['height_mm'])] +
            [val(s['psets'].get(pn, {}).get(k)) for pn, k in sk] for s in d['spaces']]
    sheet(wb, 'Помещения и зоны', ['Номер / имя IFC', 'Имя (LongName)', 'Вид', 'Площадь по контуру, м²',
                                    'Контуров', 'Высота, мм'] + ['%s\n%s' % k for k in sk], rows)
    wb.save(out)
    clean_meta.clean(out)
    print(out, {ws.title: ws.max_row - 1 for ws in wb.worksheets})


if __name__ == '__main__':
    main(*sys.argv[1:3])
