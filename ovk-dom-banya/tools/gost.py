"""Рамка, поле подшивки и основная надпись (ГОСТ Р 21.101-2020, форма 3 — 185×55) для листов А3 в SVG (мм)."""
import html

FONT = "file:///root/.fonts/isocpeur.ttf"

STAMP = dict(
    code='ЭП-ОВ',
    obj='Двухэтажный индивидуальный жилой дом с баней. Московская область, кадастровый номер участка '
        '50:08:0050209:1600',
    bld='Отопление, вентиляция и кондиционирование. Принципиальные решения',
    org='',
    stage='ЭП',
    people=[('Разраб.', '', ''), ('Пров.', '', ''), None, None, ('Н.контр.', '', ''), ('Утв.', '', '')],
)

TK, TN = 0.5, 0.18


def esc(s):
    s = str(s).replace('ё', 'е').replace('Ё', 'Е')    # в ISOCPEUR буква ё не отрисовывается
    return html.escape(s, quote=False)


def text(x, y, s, h=2.5, anchor='start', cls='', extra='', rot=0):
    """Текст ISOCPEUR наклонный; (x, y) — точка базовой линии/центра по dominant-baseline=central."""
    fs = h * 1.42
    tr = f'translate({x:.2f} {y:.2f})' + (f' rotate({rot})' if rot else '') + ' scale(0.88 1)'
    return (f'<text class="iso {cls}" transform="{tr}" font-size="{fs:.2f}" text-anchor="{anchor}" '
            f'dominant-baseline="central" {extra}>{esc(s)}</text>')


def fo(x, y, w, h, inner, fs=2.5, align='left', valign='flex-start', cls=''):
    """Абзац/таблица в SVG (foreignObject). Внутри — масштаб 1:10 (1 CSS px = 0,1 мм), чтобы линии таблиц
    были тонкими: Chromium не рисует рамку тоньше 1 px. fs — высота букв в мм."""
    inner = inner.replace('ё', 'е').replace('Ё', 'Е')
    return (f'<foreignObject x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}">'
            f'<div xmlns="http://www.w3.org/1999/xhtml" class="fo {cls}" style="font-size:{fs * 14.2:.1f}px;'
            f'text-align:{align};width:{w * 10:.0f}px;height:{h * 10:.0f}px;transform:scale(0.1);'
            f'transform-origin:0 0;display:flex;flex-direction:column;justify-content:{valign}">'
            f'{inner}</div></foreignObject>')


def line(x1, y1, x2, y2, w=TN, extra=''):
    return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="#000" stroke-width="{w}" {extra}/>'


def frame(W=420, H=297):
    s = [f'<rect x="20" y="5" width="{W - 25}" height="{H - 10}" fill="none" stroke="#000" stroke-width="{TK}"/>']
    # поле подшивки: Инв. № подл. (25), Подп. и дата (35), Взам. инв. № (25) — снизу вверх
    y = H - 5
    for label, h in (('Инв. № подл.', 25), ('Подп. и дата', 35), ('Взам. инв. №', 25)):
        s.append(f'<rect x="8" y="{y - h}" width="12" height="{h}" fill="none" stroke="#000" stroke-width="{TK}"/>')
        s.append(line(13, y - h, 13, y, TN))
        s.append(text(10.5, y - h / 2, label, 2.2, 'middle', rot=-90))
        y -= h
    s.append(text(W - 8, H - 2.2, 'Формат А3', 2.5, 'end'))
    s.append(text(W - 140, H - 2.2, 'Копировал', 2.5, 'start'))
    return ''.join(s)


def stamp(title, sheet, sheets, W=420, H=297, st=STAMP):
    x0, y0 = W - 5 - 185, H - 5 - 55          # левый верхний угол
    Y = lambda y: y0 + 55 - y                 # y — от низа штампа
    s = [f'<rect x="{x0}" y="{y0}" width="185" height="55" fill="#fff" stroke="#000" stroke-width="{TK}"/>']

    def L(a, b, c, d, w=TK):
        s.append(line(x0 + a, Y(b), x0 + c, Y(d), w))

    for y in (5, 10, 15, 20, 25, 40, 45, 50):
        L(0, y, 65, y, TN)
    L(0, 30, 185, 30)
    L(0, 35, 65, 35)
    for x in (10, 20, 30, 40, 55, 65):
        L(x, 30 if x in (10, 30) else 0, x, 55)
    L(65, 45, 185, 45)
    L(65, 15, 185, 15)
    L(135, 0, 135, 30)
    L(150, 15, 150, 30)
    L(165, 15, 165, 30)
    L(135, 25, 185, 25)

    def T(t, x, y, h, anchor='middle'):
        s.append(text(x0 + x, Y(y), t, h, anchor))

    def M(t, a, b, c, d, h):
        s.append(fo(x0 + a, Y(d), c - a, d - b, esc(t), h, 'center', 'center'))

    for t, xc in (('Изм.', 5), ('Кол.уч', 15), ('Лист', 25), ('№ док.', 35), ('Подп.', 47.5), ('Дата', 60)):
        T(t, xc, 32.5, 2.3)
    for i, row in enumerate(st['people']):
        if row:
            yy = 27.5 - i * 5
            T(row[0], 0.8, yy, 2.5, 'start')
            T(row[1], 20.8, yy, 2.5, 'start')
            T(row[2], 55.6, yy, 2.5, 'start')
    T(st['code'], 125, 50, 5.0)
    M(st['obj'], 66, 30, 184, 45, 2.4)
    M(st['bld'], 66, 15, 134, 30, 2.6)
    M(title, 66, 0, 134, 15, 2.6)
    M(st['org'], 136, 0, 184, 15, 2.6)
    for t, xc in (('Стадия', 142.5), ('Лист', 157.5), ('Листов', 175)):
        T(t, xc, 27.5, 2.5)
    for t, xc in ((st['stage'], 142.5), (sheet, 157.5), (sheets, 175)):
        T(t, xc, 20, 3.2)
    return ''.join(s)


CSS = f"""
@font-face {{ font-family: 'ISOCPEUR'; src: url('{FONT}') }}
@page {{ size: 420mm 297mm; margin: 0 }}
html, body {{ margin: 0; padding: 0 }}
svg.sheet {{ display: block; width: 420mm; height: 297mm; page-break-after: always }}
.iso {{ font-family: ISOCPEUR; font-style: italic; fill: #000 }}
.fo {{ font-family: ISOCPEUR; font-style: italic; line-height: 1.22; color: #000 }}
.fo p {{ margin: 0 0 9px; text-indent: 0 }}
.fo b {{ font-weight: normal; text-decoration: underline }}
.fo table {{ border-collapse: collapse; width: 100% }}
.fo td, .fo th {{ border: 1.8px solid #000; padding: 3px 6px; font-weight: normal; vertical-align: middle }}
.fo th {{ text-align: center }}
.fo td.c {{ text-align: center }} .fo td.r {{ text-align: right }}
"""


def sheet_svg(body, title, no, total):
    return (f'<svg class="sheet" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 297">'
            f'{body}{frame()}{stamp(title, no, total)}</svg>')


def html_doc(svgs, extra_css=''):
    return (f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><style>{CSS}{extra_css}</style>'
            f'</head><body>{"".join(svgs)}</body></html>')
