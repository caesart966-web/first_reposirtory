"""Листы А4/А3 с рамкой и основной надписью (ГОСТ Р 21.101-2020, формы 5 и 6) в HTML для печати в PDF.
Копия work/gost_html.py для РД ОВ: данные штампа — из rdsh/rd_stamp.py (без организации и фамилий)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rd_stamp import CODE, STAGE  # noqa: E402

CSS = """
@font-face { font-family: 'ISOCPEUR'; src: url('file:///root/.fonts/isocpeur.ttf') }
@page { size: %(w)smm %(h)smm; margin: 0 }
* { box-sizing: border-box }
html, body { margin: 0; padding: 0 }
body { font-family: 'Times New Roman', 'Liberation Serif', serif; color: #000 }
.page { position: relative; width: %(w)smm; height: %(h)smm; overflow: hidden; page-break-after: always }
.frame { position: absolute; left: 20mm; top: 5mm; right: 5mm; bottom: 5mm; border: 0.6mm solid #000 }
.content { position: absolute; left: 25mm; right: 10mm; top: 10mm; font-size: 12pt; line-height: 1.35 }
.content p { margin: 0 0 2.2mm; text-align: justify; text-indent: 12.5mm }
.content p.ni { text-indent: 0 }
.content h1 { font-size: 13pt; font-weight: bold; text-align: center; margin: 0 0 4mm }
.content h2 { font-size: 12pt; font-weight: bold; margin: 3.5mm 0 2mm; text-indent: 12.5mm }
.content table.t { border-collapse: collapse; width: 100%%; margin: 1.5mm 0 3mm; font-size: 10.5pt; line-height: 1.2 }
.content table.t td, .content table.t th { border: 0.25mm solid #000; padding: 0.8mm 1.2mm; vertical-align: middle; text-align: center }
.content table.t th { font-weight: normal }
.content table.t td.l { text-align: left }
.content .f { text-align: center; margin: 1.5mm 0 2.5mm; text-indent: 0; font-style: italic }
.content ul { margin: 0 0 2mm 12.5mm; padding: 0 } .content li { margin-bottom: 1mm; text-align: justify }
.side { position: absolute; left: 8mm; width: 12mm; bottom: 5mm; height: 85mm; border: 0.6mm solid #000; border-right: none }
.side div { position: absolute; left: 0; width: 12mm; border-top: 0.6mm solid #000 }
.side span { position: absolute; left: 0; width: 5mm; height: 100%%; border-right: 0.25mm solid #000;
  writing-mode: vertical-rl; transform: rotate(180deg); font: italic 7pt 'ISOCPEUR', 'Liberation Sans', sans-serif; text-align: center }
.st { position: absolute; right: 5mm; bottom: 5mm; border-collapse: collapse; table-layout: fixed;
  font: italic 8pt 'ISOCPEUR', 'Liberation Sans', sans-serif }
.st td { border: 0.25mm solid #000; padding: 0 0.6mm; overflow: hidden; white-space: nowrap; text-align: left }
.st td.c { text-align: center } .st td.b { border-width: 0.6mm } .st .big { font-size: 13pt; text-align: center }
.st .mid { font-size: 9pt; text-align: center; white-space: normal; line-height: 1.15 }
.st .sm { font-size: 6.4pt; white-space: normal; line-height: 1.1; text-align: center }
.fmt { position: absolute; right: 8mm; bottom: 1.2mm; font: italic 7.5pt 'ISOCPEUR', 'Liberation Sans', sans-serif }
"""


def side_strip():
    # Взам. инв. № (25) / Подп. и дата (35) / Инв. № подл. (25) — снизу вверх
    parts = [('Инв.№ подл.', 25), ('Подпись и дата', 35), ('Взам.инв.№', 25)]
    y, html = 0, ''
    for label, h in parts:
        html += f'<div style="bottom:{y}mm;height:{h}mm"><span>{label}</span></div>'
        y += h
    return f'<div class="side">{html}</div>'


def form5(title, sheet, sheets, code=CODE, stage=STAGE):
    """Основная надпись первого листа текстового документа — по штампу Заказчика (форма 3, 185×55):
    та же сетка, что в чертежах (dxf_sheet.stamp3), наклонный ISOCPEUR. Рисуется SVG в мм."""
    from rd_stamp import OBJ, BLD, ORG, PEOPLE
    title = title.replace('ё', 'е').replace('Ё', 'Е')      # в шрифте штампа ё не используется
    TK, TN = 0.5, 0.18
    Y = lambda y: 55 - y
    ln = []

    def L(x1, y1, x2, y2, w=TK):
        ln.append(f'<line x1="{x1}" y1="{Y(y1)}" x2="{x2}" y2="{Y(y2)}" stroke-width="{w}"/>')

    for y in (5, 10, 15, 20, 25, 40, 45, 50):
        L(0, y, 65, y, TN)
    L(0, 30, 185, 30)
    L(0, 35, 65, 35)
    for x in (20, 40, 55, 65):
        L(x, 0, x, 55)
    for x in (10, 30):
        L(x, 30, x, 55)
    L(65, 45, 185, 45)
    L(65, 15, 185, 15)
    L(135, 0, 135, 30)
    L(150, 15, 150, 30)
    L(165, 15, 165, 30)
    L(135, 25, 185, 25)
    tx = []

    def T(t, x, y, h, anchor='middle'):
        fs = h * 1.42
        tx.append(f'<text transform="translate({x} {Y(y)}) scale(0.85 1)" font-size="{fs:.2f}" '
                  f'text-anchor="{anchor}" dominant-baseline="central">{t}</text>')

    def M(t, x1, y1, x2, y2, h):
        fs = h * 1.42
        tx.append(f'<foreignObject x="{x1}" y="{Y(y2)}" width="{x2 - x1}" height="{y2 - y1}">'
                  f'<div xmlns="http://www.w3.org/1999/xhtml" style="width:100%;height:100%;display:flex;'
                  f'align-items:center;justify-content:center;text-align:center;font-size:{fs:.2f}px;'
                  f'line-height:1.08;padding:0 1px;box-sizing:border-box">{t}</div></foreignObject>')

    for t, xc in (('Изм.', 5), ('Кол.уч', 15), ('Лист', 25), ('№ док', 35), ('Подп.', 47.5), ('Дата', 60)):
        T(t, xc, 32.5, 2.5)
    for i, row in enumerate(PEOPLE):
        if row:
            yy = 27.5 - i * 5
            T(row[0], 0.8, yy, 3.0, 'start')
            T(row[1], 20.8, yy, 3.0, 'start')
            T(row[2], 55.6, yy, 3.0, 'start')
    T(code, 125, 50, 5.5)
    M(OBJ, 66, 30, 184, 45, 2.2)
    M(BLD, 66, 15, 134, 30, 3.0)
    M(title, 66, 0, 134, 15, 3.0)
    M(ORG, 136, 0, 184, 15, 2.8)
    for t, xc in (('Стадия', 142.5), ('Лист', 157.5), ('Листов', 175)):
        T(t, xc, 27.5, 3.0)
    for t, xc in ((stage, 142.5), (sheet, 157.5), (sheets, 175)):
        T(t, xc, 20, 3.5)
    return (f'<svg class="st5" viewBox="0 0 185 55" style="position:absolute;right:5mm;bottom:5mm;width:185mm;'
            f'height:55mm;overflow:visible"><g fill="none" stroke="#000" stroke-linecap="square">'
            f'<rect x="0" y="0" width="185" height="55" stroke-width="{TK}"/>{"".join(ln)}</g>'
            f'<g style="font-family:ISOCPEUR;font-style:italic" fill="#000">{"".join(tx)}</g></svg>')


def form6(sheet, code=CODE):
    """Основная надпись последующих листов (185 x 15)."""
    w = [7, 10, 10, 10, 15, 10, 113, 10]
    cols = ''.join(f'<col style="width:{x}mm">' for x in w)
    rows = [
        f'<tr style="height:5mm">{"<td></td>" * 6}<td rowspan="3" class="big">{code}</td><td class="c">Лист</td></tr>',
        f'<tr style="height:5mm">{"<td></td>" * 6}<td rowspan="2" class="c" style="font-size:10pt">{sheet}</td></tr>',
        '<tr style="height:5mm"><td class="c">Изм.</td><td class="c">Кол.уч</td><td class="c">Лист</td>'
        '<td class="c">№ док.</td><td class="c">Подп.</td><td class="c">Дата</td></tr>',
    ]
    return f'<table class="st" style="width:185mm"><colgroup>{cols}</colgroup>{"".join(rows)}</table>'


def page(content, sheet, sheets, title, code, first, fmt='Формат А4', w=210, h=297):
    stamp = form5(title, sheet, sheets, code) if first else form6(sheet, code)
    return (f'<div class="page"><div class="frame"></div>{side_strip()}'
            f'<div class="content">{content}</div>{stamp}<div class="fmt">{fmt}</div></div>')


def document(pages, title, code, w=210, h=297, fmt='Формат А4'):
    n = len(pages)
    body = ''.join(page(c, i + 1, n, title, code, i == 0, fmt, w, h) for i, c in enumerate(pages))
    return (f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><style>{CSS % dict(w=w, h=h)}</style></head>'
            f'<body>{body}</body></html>')
