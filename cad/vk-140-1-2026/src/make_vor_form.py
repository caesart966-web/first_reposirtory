"""ВОР ВК в форме Заказчика (Excel, лист «Вариант для импорта»): шаблон Заказчика, строки — из vor_data.

make_vor_form.py ШАБЛОН.xlsx СПЕЦИФИКАЦИЯ.pdf ВЫХОД.xlsx
Номера страниц — по единому тому 140-1-2026-ВК.pdf: листы 1–6, затем страницы спецификации."""
import copy
import math
import os
import re
import subprocess
import sys

import openpyxl
from openpyxl.styles import Alignment, Border, Side, Font

sys.path.insert(0, os.path.dirname(__file__))
from vor_data import R, NOTES  # noqa: E402

TPL, SPEC_PDF, OUT = sys.argv[1:4]
VOLUME = '140-1-2026-ВК'
CODE = '140-1/2026-ВК'
SHEETS_IN_VOLUME = 6

# позиция спецификации -> страница спецификации
pos_page = {}
xml = subprocess.check_output(['pdftotext', '-bbox', SPEC_PDF, '-']).decode()
for k, page in enumerate(re.findall(r'<page .*?</page>', xml, re.S), 1):
    for x1, y1, w in re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)"[^>]*>(\d{1,2})</word>', page):
        if 56 < float(x1) < 114 and float(y1) > 60:          # графа «Поз.» (20–40 мм от края), ниже шапки
            pos_page.setdefault(int(w), k)
n_pages = k
missing = [p for it in R if isinstance(it, dict) for p in it['pos'] if p not in pos_page]
assert not missing, missing

wb = openpyxl.load_workbook(TPL)
ws = wb['Вариант для импорта']
# образцы оформления — строка раздела (4) и строка работы (5)
sec_style = {c.column: copy.copy(c._style) for c in ws[4]}
row_style = {c.column: copy.copy(c._style) for c in ws[5]}
for mr in list(ws.merged_cells.ranges):
    if mr.min_row >= 4:
        ws.unmerge_cells(str(mr))
ws.delete_rows(4, ws.max_row - 3)

thin = Side(style='thin')
box = Border(left=thin, right=thin, top=thin, bottom=thin)
r, n, k = 4, 0, 0


def lines(text, width_chars):
    return max(1, sum(math.ceil(max(1, len(part)) / width_chars) for part in str(text).split('\n')))


for item in R:
    if isinstance(item, tuple):
        ws.cell(r, 1, item[1])
        for c in range(1, 10):
            ws.cell(r, c)._style = copy.copy(sec_style[c])
            ws.cell(r, c).border = box
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=9)
        ws.row_dimensions[r].height = 15.75
        r += 1
        continue
    if item.get('sub'):
        k += 1
        num = f'{n}.{k}'
    else:
        n, k = n + 1, 0
        num = str(n)
    sheets = sorted(set(item['sheets']))
    spec_pages = sorted({pos_page[p] for p in item['pos']})
    refs = []
    if sheets:
        refs.append(f'{CODE}, см. лист{"ы" if len(sheets) > 1 else ""} ' + ', '.join(map(str, sheets)))
    if item['pos']:
        refs.append(f'{CODE}.СО, {item["ref"]}')
    if item.get('xref'):
        refs.append(item['xref'])
    pages = sheets + [SHEETS_IN_VOLUME + p for p in spec_pages]
    vals = [num, item['name'], item['unit'], item['qty'], item['formula'] or None, '; '.join(refs), VOLUME,
            ' '.join(map(str, pages)), item['note'] or None]
    for c, v in enumerate(vals, 1):
        cell = ws.cell(r, c, v)
        cell._style = copy.copy(row_style[c])
        cell.border = box
        h = 'left' if c in (2, 6, 9) else 'center'
        cell.alignment = Alignment(horizontal=h, vertical='center', wrap_text=c in (2, 5, 6, 9))
    ws.row_dimensions[r].height = 15.0 * max(lines(vals[1], 36), lines(vals[5], 32), lines(vals[8] or '', 40),
                                             lines(vals[4] or '', 22))
    r += 1

ws.print_title_rows = '2:3'
ws.page_setup.orientation = 'landscape'
ws.page_setup.fitToWidth = 1
ws.page_setup.fitToHeight = 0
ws.sheet_properties.pageSetUpPr.fitToPage = True

# примечания — отдельным листом, чтобы не мешать импорту
wn = wb.create_sheet('Примечания')
wn.column_dimensions['A'].width = 120
wn.cell(1, 1, f'Примечания к ведомости объемов работ {CODE}.ВОР').font = Font(name='Times New Roman', size=11, bold=True)
for i, t in enumerate(NOTES, 1):
    c = wn.cell(1 + i, 1, f'{i}. {t}')
    c.font = Font(name='Times New Roman', size=11)
    c.alignment = Alignment(wrap_text=True, vertical='top')
    wn.row_dimensions[1 + i].height = 15.0 * lines(c.value, 115)
wb.properties.creator = ''
wb.properties.lastModifiedBy = ''
wb.properties.title = f'{CODE}.ВОР Ведомость объемов работ'
wb.save(OUT)
print('ok', n, 'rows; spec pages', n_pages)
