"""Листы «Принципиальные решения ОВиК» (А3) поверх подложки АР.

python3 draw.py  ->  out/sheets.html, out/sheets_fg.pdf (графика), out/ОВ-листы.pdf (с подложкой АР)
"""
import json
import math
import os
import subprocess

import pymupdf as fitz

from gost import esc, fo, html_doc, line, sheet_svg, text

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)
C = json.load(open(os.path.join(HERE, 'calc.json')))
ROOM = {r['no']: r for r in C['rooms']}
COOL = {c['no']: c for c in C['cool']}
MM = 72 / 25.4


def kw(w, d=1):
    return f'{w / 1000:.{d}f}'.replace('.', ',')


def num(v, d=1):
    return f'{v:.{d}f}'.replace('.', ',')


# ----------------------------------------------------------------- стили и штриховки
DEFS = """
<defs>
 <pattern id="hUFH" patternUnits="userSpaceOnUse" width="1.6" height="1.6" patternTransform="rotate(45)">
  <line x1="0" y1="0" x2="0" y2="1.6" stroke="#d2412f" stroke-width="0.22" stroke-opacity="0.55"/></pattern>
 <pattern id="hUFHg" patternUnits="userSpaceOnUse" width="2.6" height="2.6" patternTransform="rotate(45)">
  <line x1="0" y1="0" x2="0" y2="2.6" stroke="#d2412f" stroke-width="0.2" stroke-opacity="0.45"/></pattern>
 <pattern id="hRad" patternUnits="userSpaceOnUse" width="0.9" height="0.9" patternTransform="rotate(45)">
  <line x1="0" y1="0" x2="0" y2="0.9" stroke="#c8102e" stroke-width="0.25"/></pattern>
 <pattern id="zA" patternUnits="userSpaceOnUse" width="2.2" height="2.2" patternTransform="rotate(45)">
  <rect width="2.2" height="2.2" fill="#e6f0ff" fill-opacity="0.55"/>
  <line x1="0" y1="0" x2="0" y2="2.2" stroke="#3b73c8" stroke-width="0.2" stroke-opacity="0.6"/></pattern>
 <pattern id="zB" patternUnits="userSpaceOnUse" width="2.2" height="2.2" patternTransform="rotate(-45)">
  <rect width="2.2" height="2.2" fill="#e9f7ea" fill-opacity="0.6"/>
  <line x1="0" y1="0" x2="0" y2="2.2" stroke="#2f8f3a" stroke-width="0.2" stroke-opacity="0.6"/></pattern>
 <pattern id="zC" patternUnits="userSpaceOnUse" width="2.2" height="2.2">
  <rect width="2.2" height="2.2" fill="#fff4dc" fill-opacity="0.6"/>
  <line x1="0" y1="1.1" x2="2.2" y2="1.1" stroke="#c98a12" stroke-width="0.2" stroke-opacity="0.7"/></pattern>
 <marker id="arr" viewBox="0 0 6 6" refX="5.5" refY="3" markerWidth="4" markerHeight="4" orient="auto">
  <path d="M0 0 L6 3 L0 6 z" fill="#000"/></marker>
 <marker id="arrS" viewBox="0 0 6 6" refX="5.5" refY="3" markerWidth="4" markerHeight="4" orient="auto">
  <path d="M0 0 L6 3 L0 6 z" fill="#1d5fc4"/></marker>
 <marker id="arrE" viewBox="0 0 6 6" refX="5.5" refY="3" markerWidth="4" markerHeight="4" orient="auto">
  <path d="M0 0 L6 3 L0 6 z" fill="#a35a1c"/></marker>
</defs>
<style>
 .ufh { fill: url(#hUFH); stroke: #d2412f; stroke-width: 0.25; stroke-dasharray: 1.4 0.7 }
 .ufhg { fill: url(#hUFHg); stroke: #d2412f; stroke-width: 0.25; stroke-dasharray: 0.5 0.9 }
 .t1 { stroke: #c8102e; stroke-width: 0.5; fill: none }
 .t2 { stroke: #1f5bb5; stroke-width: 0.5; fill: none; stroke-dasharray: 2.4 0.9 }
 .eco { stroke: #6b2fb3; stroke-width: 1.4; fill: none; stroke-opacity: 0.55 }
 .conv { fill: #c8102e; stroke: #6f0a18; stroke-width: 0.2 }
 .rad { fill: url(#hRad); stroke: #c8102e; stroke-width: 0.35 }
 .cab { fill: #ffe79a; stroke: #000; stroke-width: 0.3 }
 .eq { fill: #fff; stroke: #000; stroke-width: 0.3 }
 .eqs { fill: #eef3fb; stroke: #000; stroke-width: 0.3 }
 .tag { fill: #fff; fill-opacity: 0.93; stroke: #000; stroke-width: 0.18 }
 .lead { stroke: #000; stroke-width: 0.18; fill: none }
 .ductS { stroke: #1d5fc4; fill: none; stroke-linecap: square; stroke-linejoin: miter }
 .ductSi { stroke: #dbe8fb; fill: none; stroke-linecap: square; stroke-linejoin: miter }
 .ductE { stroke: #a35a1c; fill: none; stroke-linecap: square; stroke-linejoin: miter }
 .ductEi { stroke: #f6e3cf; fill: none; stroke-linecap: square; stroke-linejoin: miter }
 .freon { stroke: #a2179c; stroke-width: 0.45; fill: none; stroke-dasharray: 3 1 0.6 1 }
 .zA { fill: url(#zA); stroke: #3b73c8; stroke-width: 0.3; stroke-dasharray: 2 0.8 }
 .zB { fill: url(#zB); stroke: #2f8f3a; stroke-width: 0.3; stroke-dasharray: 2 0.8 }
 .zC { fill: url(#zC); stroke: #c98a12; stroke-width: 0.3; stroke-dasharray: 2 0.8 }
 .acu { fill: #fff; stroke: #a2179c; stroke-width: 0.35 }
 .ahu { fill: #fff; stroke: #1d5fc4; stroke-width: 0.4 }
 .shaft { fill: #fff; stroke: #000; stroke-width: 0.35 }
 .gS { fill: #1d5fc4 } .gE { fill: #a35a1c }
 .ax { stroke: #000; stroke-width: 0.18; stroke-dasharray: 6 1 1 1; fill: none }
 .bub { fill: #fff; stroke: #000; stroke-width: 0.25 }
 .red { fill: #c8102e } .blue { fill: #1d5fc4 } .brown { fill: #a35a1c } .mag { fill: #a2179c }
</style>
"""


class Plan:
    def __init__(self, ox, oy, s):
        self.ox, self.oy, self.s = ox, oy, s       # мм листа для точки (0,0) осей; мм на 1 м
        self.out = []

    def P(self, x, y):
        return self.ox + x * self.s, self.oy - y * self.s

    def pts(self, pts):
        return ' '.join('%.2f,%.2f' % self.P(x, y) for x, y in pts)

    def add(self, s):
        self.out.append(s)

    def poly(self, pts, cls, extra=''):
        self.add(f'<polygon points="{self.pts(pts)}" class="{cls}" {extra}/>')

    def rect(self, x0, y0, x1, y1, cls, extra=''):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], cls, extra)

    def pl(self, pts, cls, extra=''):
        self.add(f'<polyline points="{self.pts(pts)}" class="{cls}" {extra}/>')

    def t(self, x, y, s, h=2.2, anchor='start', cls='', rot=0):
        X, Y = self.P(x, y)
        self.add(text(X, Y, s, h, anchor, cls, rot=rot))

    def circle(self, x, y, r, cls):
        X, Y = self.P(x, y)
        self.add(f'<circle cx="{X:.2f}" cy="{Y:.2f}" r="{r * self.s:.2f}" class="{cls}"/>')

    # ---- элементы
    def tag(self, x, y, lines, w=None, anchor=None, h=2.1, lw=None):
        """Ярлык помещения: (x, y) — левый верх ярлыка в метрах; anchor — точка выноски (м)."""
        X, Y = self.P(x, y)
        lh = h * 1.32
        if w is None:
            w = max(len(s) for s in lines) * h * 0.6 + 2.2
        H = lh * len(lines) + 1.0
        if anchor:
            ax, ay = self.P(*anchor)
            cx = min(max(ax, X), X + w)
            cy = min(max(ay, Y), Y + H)
            self.add(f'<polyline points="{ax:.2f},{ay:.2f} {cx:.2f},{cy:.2f}" class="lead"/>')
            self.add(f'<circle cx="{ax:.2f}" cy="{ay:.2f}" r="0.35" fill="#000"/>')
        self.add(f'<rect x="{X:.2f}" y="{Y:.2f}" width="{w:.2f}" height="{H:.2f}" class="tag"/>')
        for i, s in enumerate(lines):
            self.add(text(X + 1.0, Y + 0.5 + lh * (i + 0.5), s, h, 'start'))
        self.add(line(X, Y + lh + 0.5, X + w, Y + lh + 0.5, 0.15))
        return w, H

    def label(self, x, y, s, h=2.2, anchor='start', at=None, cls=''):
        """Подпись с выноской к точке at (м)."""
        X, Y = self.P(x, y)
        if at:
            ax, ay = self.P(*at)
            self.add(f'<polyline points="{ax:.2f},{ay:.2f} {X:.2f},{Y:.2f}" class="lead"/>')
            self.add(f'<circle cx="{ax:.2f}" cy="{ay:.2f}" r="0.3" fill="#000"/>')
        self.add(text(X + (0.6 if anchor == 'start' else -0.6 if anchor == 'end' else 0), Y - 1.0, s, h, anchor, cls))
        # подчёркивание полкой
        wtxt = len(s) * h * 0.62
        x0 = X if anchor == 'start' else X - wtxt if anchor == 'end' else X - wtxt / 2
        self.add(line(x0, Y, x0 + wtxt + 0.8, Y, 0.18))

    def duct(self, pts, d_mm, kind='S'):
        w = max(d_mm / 1000 * self.s, 0.9)
        self.pl(pts, f'duct{kind}', f'stroke-width="{w:.2f}"')
        self.pl(pts, f'duct{kind}i', f'stroke-width="{max(w - 0.5, 0.2):.2f}"')

    def grille(self, x, y, kind, L, direction='down', txt_side='right', d=None):
        """Решётка/диффузор: квадрат 0,5 м и стрелка движения воздуха."""
        X, Y = self.P(x, y)
        a = 0.45 * self.s / 2
        col = 'gS' if kind == 'S' else 'gE'
        self.add(f'<rect x="{X - a:.2f}" y="{Y - a:.2f}" width="{2 * a:.2f}" height="{2 * a:.2f}" '
                 f'class="{col}" stroke="#000" stroke-width="0.15"/>')
        self.add(line(X - a, Y - a, X + a, Y + a, 0.2, 'stroke="#fff"'))
        self.add(line(X - a, Y + a, X + a, Y - a, 0.2, 'stroke="#fff"'))
        dx, dy = dict(down=(0, 1), up=(0, -1), left=(-1, 0), right=(1, 0))[direction]
        mk = 'arrS' if kind == 'S' else 'arrE'
        stroke = '#1d5fc4' if kind == 'S' else '#a35a1c'
        if kind == 'S':
            x1, y1, x2, y2 = X + dx * a, Y + dy * a, X + dx * (a + 3.2), Y + dy * (a + 3.2)
        else:
            x1, y1, x2, y2 = X + dx * (a + 3.2), Y + dy * (a + 3.2), X + dx * a, Y + dy * a
        self.add(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{stroke}" '
                 f'stroke-width="0.3" marker-end="url(#{mk})"/>')
        tx = X + (a + 0.8 if txt_side == 'right' else -(a + 0.8))
        anchor = 'start' if txt_side == 'right' else 'end'
        ty = Y + (-1.5 if direction in ('down', 'up') and txt_side else 0)
        self.add(text(tx, Y - 0.2 if direction in ('left', 'right') else Y, f'L={L}', 1.9, anchor,
                      'blue' if kind == 'S' else 'brown'))

    def bubble_x(self, xs, y_m, names, r=4.0, ext=1.0):
        for x, n in zip(xs, names):
            X, Y = self.P(x, y_m)
            self.add(f'<circle cx="{X:.2f}" cy="{Y + ext + r:.2f}" r="{r}" class="bub"/>')
            self.add(text(X, Y + ext + r, n, 3.0, 'middle'))
            self.add(line(X, Y - 2, X, Y + ext, 0.18))

    def svg(self):
        return ''.join(self.out)


def legend(x, y, items, w=118, title='Условные обозначения'):
    """items: (svg-фрагмент символа в координатах 0..14 x -2..2, подпись)."""
    s = [text(x + w / 2, y, title, 3.0, 'middle')]
    yy = y + 5
    for sym, cap in items:
        s.append(f'<g transform="translate({x:.2f} {yy:.2f})">{sym}</g>')
        s.append(fo(x + 17, yy - 2.4, w - 17, 9, esc(cap), 2.1))
        n = max(1, math.ceil(len(cap) * 2.1 * 0.6 / (w - 17)))
        yy += 3.2 * n + 2.4
    return ''.join(s), yy


SYM = dict(
    ufh='<rect x="0" y="-2" width="14" height="4" class="ufh"/>',
    ufhg='<rect x="0" y="-2" width="14" height="4" class="ufhg"/>',
    conv='<rect x="1" y="-0.9" width="12" height="1.8" class="conv"/>',
    rad='<rect x="1" y="-1" width="12" height="2" class="rad"/>',
    cab='<rect x="3" y="-1.8" width="8" height="3.6" class="cab"/>',
    t1='<line x1="0" y1="0" x2="14" y2="0" class="t1"/>',
    t2='<line x1="0" y1="0" x2="14" y2="0" class="t2"/>',
    eco='<line x1="0" y1="0" x2="14" y2="0" class="eco"/>',
    ductS='<line x1="0" y1="0" x2="14" y2="0" class="ductS" stroke-width="2.2"/>'
          '<line x1="0" y1="0" x2="14" y2="0" class="ductSi" stroke-width="1.6"/>',
    ductE='<line x1="0" y1="0" x2="14" y2="0" class="ductE" stroke-width="2.2"/>'
          '<line x1="0" y1="0" x2="14" y2="0" class="ductEi" stroke-width="1.6"/>',
    gS='<rect x="5" y="-2" width="4" height="4" class="gS"/>'
       '<line x1="5" y1="-2" x2="9" y2="2" stroke="#fff" stroke-width="0.2"/>'
       '<line x1="5" y1="2" x2="9" y2="-2" stroke="#fff" stroke-width="0.2"/>',
    gE='<rect x="5" y="-2" width="4" height="4" class="gE"/>'
       '<line x1="5" y1="-2" x2="9" y2="2" stroke="#fff" stroke-width="0.2"/>'
       '<line x1="5" y1="2" x2="9" y2="-2" stroke="#fff" stroke-width="0.2"/>',
    acu='<rect x="2" y="-2" width="10" height="4" class="acu"/><text class="iso" x="7" y="0.1" font-size="2.6" '
        'text-anchor="middle" dominant-baseline="central">К</text>',
    ahu='<rect x="2" y="-2" width="10" height="4" class="ahu"/><text class="iso" x="7" y="0.1" font-size="2.6" '
        'text-anchor="middle" dominant-baseline="central">П1</text>',
    freon='<line x1="0" y1="0" x2="14" y2="0" class="freon"/>',
    shaft='<rect x="4" y="-2" width="6" height="4" class="shaft"/><line x1="4" y1="-2" x2="10" y2="2" '
          'stroke="#000" stroke-width="0.25"/><line x1="4" y1="2" x2="10" y2="-2" stroke="#000" stroke-width="0.25"/>',
    zA='<rect x="0" y="-2" width="14" height="4" class="zA"/>',
    zB='<rect x="0" y="-2" width="14" height="4" class="zB"/>',
    zC='<rect x="0" y="-2" width="14" height="4" class="zC"/>',
)


def notes(x, y, w, h, items, title='Примечания', fs=2.3):
    inner = ''.join(f'<p>{i}. {s}</p>' for i, s in enumerate(items, 1))
    return text(x + w / 2, y, title, 3.0, 'middle') + fo(x, y + 3, w, h, inner, fs)


# ----------------------------------------------------------------- подложки АР
HOUSE = 'src/Коттедж_Эскиз.pdf'
BATH = 'src/Баня_Эскиз.pdf'
K100 = 28.3465       # пт на метр при М 1:100
K75 = 37.7953
K200 = 14.1732
UNDER = {}           # номер листа -> (файл, стр, ось1_x_pt, осьА_y_pt, пт/м, clip(pt), ox_mm, oy_mm, s_mm_per_m)


# ================================================================= ЛИСТ 1: дом, 1 этаж, отопление
def sheet_heat1(no, total):
    pl = Plan(60.0, 212.0, 10.0)
    UNDER[no] = (HOUSE, 5, 209.8, 603.7, K100, (92, 38, 860, 622), pl.ox, pl.oy, pl.s)
    r = ROOM
    # зоны тёплого пола
    zones = {
        '1.10': [(0.3, 6.5), (9.3, 6.5), (9.3, 13.6), (0.3, 13.6)],
        '1.11': [(0.3, 0.3), (5.95, 0.3), (5.95, 6.1), (0.3, 6.1)],
        '1.2': [(6.3, 0.3), (9.35, 0.3), (9.35, 4.45), (6.3, 4.45)],
        '1.3': [(9.85, 0.45), (12.45, 0.45), (12.45, 4.25), (9.85, 4.25)],
        '1.4': [(9.85, 4.55), (12.45, 4.55), (12.45, 6.1), (9.85, 6.1)],
        '1.9': [(9.7, 6.5), (12.45, 6.5), (12.45, 10.5), (9.7, 10.5)],
        '1.7': [(12.8, 9.05), (15.45, 9.05), (15.45, 11.25), (12.8, 11.25)],
        '1.8': [(12.8, 11.55), (15.45, 11.55), (15.45, 13.6), (12.8, 13.6)],
        '1.6': [(15.75, 9.05), (19.8, 9.05), (19.8, 12.3), (15.75, 12.3)],
    }
    for k, z in zones.items():
        pl.poly(z, 'ufh')
    pl.poly([(12.8, 1.3), (19.8, 1.3), (19.8, 8.75), (12.8, 8.75)], 'ufhg')
    # конвекторы
    conv = [((1.7, 13.15, 3.65, 13.45), 'Кв-1'), ((3.75, 13.15, 5.7, 13.45), 'Кв-2'),
            ((5.8, 13.15, 7.45, 13.45), 'Кв-3'), ((0.32, 12.35, 0.62, 13.25), 'Кв-4'),
            ((0.32, 6.8, 0.62, 7.7), 'Кв-5'), ((1.25, 0.35, 3.2, 0.65), 'Кв-6'), ((3.3, 0.35, 5.25, 0.65), 'Кв-7')]
    for (x0, y0, x1, y1), n in conv:
        pl.rect(x0, y0, x1, y1, 'conv')
    pl.t(4.5, 12.75, 'Кв-1…Кв-3', 2.0, 'middle', 'red')
    pl.t(0.9, 12.75, 'Кв-4', 2.0, 'start', 'red')
    pl.t(0.9, 7.25, 'Кв-5', 2.0, 'start', 'red')
    pl.t(3.25, 1.05, 'Кв-6, Кв-7', 2.0, 'middle', 'red')
    # топочная: оборудование
    eq = [((18.55, 13.2, 19.0, 13.6), 'К1'), ((19.15, 13.2, 19.6, 13.6), 'К2'), ((17.75, 13.25, 18.25, 13.6), 'ЭК')]
    for (x0, y0, x1, y1), n in eq:
        pl.rect(x0, y0, x1, y1, 'eq')
        pl.t((x0 + x1) / 2, (y0 + y1) / 2, n, 1.7, 'middle')
    pl.rect(15.75, 10.6, 16.15, 13.1, 'eqs')                      # гидрострелка + распределительный коллектор
    pl.t(15.95, 11.85, 'ГС + РК', 1.7, 'middle', rot=-90)
    pl.circle(16.55, 12.85, 0.33, 'eq')
    pl.t(16.55, 12.85, 'Б1', 1.7, 'middle')
    pl.circle(16.45, 12.0, 0.22, 'eq')
    pl.t(16.45, 11.55, 'РБ', 1.6, 'middle')
    pl.rect(16.6, 9.05, 17.6, 9.25, 'eq')
    pl.t(17.1, 9.5, 'ШУ', 1.6, 'middle')
    # коллекторные шкафы
    cab = [((12.72, 9.3, 12.98, 10.35), 'КШ-1'), ((12.72, 10.45, 12.98, 11.2), 'КШ-2'), ((15.95, 9.05, 16.5, 9.3), 'КШ-3')]
    for (x0, y0, x1, y1), n in cab:
        pl.rect(x0, y0, x1, y1, 'cab')
    pl.label(13.4, 8.0, 'КШ-1 (ТП 11 вых.)', 2.0, at=(12.85, 9.8))
    pl.label(13.4, 7.4, 'КШ-2 (ТП 6 + Кв 7 вых.)', 2.0, at=(12.85, 10.8))
    pl.label(17.0, 7.9, 'КШ-3 (ТП 6 вых.)', 2.0, at=(16.2, 9.15))
    # магистрали котельная -> КШ, стояки на 2 этаж, выход в баню
    pl.pl([(15.75, 10.75), (14.0, 10.75), (13.0, 10.75)], 't1')
    pl.pl([(15.75, 10.6), (14.0, 10.6), (13.0, 10.6)], 't2')
    pl.pl([(15.75, 12.95), (15.3, 12.95), (15.3, 13.4)], 't1')
    pl.pl([(15.75, 12.8), (15.15, 12.8), (15.15, 13.4)], 't2')
    pl.circle(15.3, 13.4, 0.09, 'red')
    pl.circle(15.15, 13.4, 0.09, 'blue')
    pl.label(13.1, 14.9, 'Ст. Т1/Т2 на 2 этаж (КШ-4)', 2.0, at=(15.2, 13.45))
    pl.pl([(16.15, 13.0), (16.5, 13.0), (16.5, 14.6), (16.5, 15.6)], 'eco')
    pl.label(17.0, 16.3, 'Т1, Т2 → баня (лист 7)', 2.0, at=(16.5, 15.0))
    pl.add(f'<line x1="{pl.P(19.6, 13.42)[0]:.2f}" y1="{pl.P(19.6, 13.42)[1]:.2f}" x2="{pl.P(21.0, 13.42)[0]:.2f}" '
           f'y2="{pl.P(21.0, 13.42)[1]:.2f}" stroke="#555" stroke-width="0.7"/>')
    pl.label(20.4, 15.0, 'Дымоходы К1, К2', 2.0, at=(20.4, 13.42))
    # ярлыки помещений
    def tg(no, x, y, extra, anchor=None):
        rr = r[no]
        head = f'{no}  +{rr["ti"]} °С  {kw(rr["Q"])} кВт'
        pl.tag(x, y, [head] + extra, anchor=anchor)
    rr = r['1.10']
    tg('1.10', 0.9, 11.9, [f'ТП 6 конт. — {kw(rr["ufh"])} кВт', f'Кв-1…5 — {kw(rr["rest"])} кВт'])
    rr = r['1.11']
    tg('1.11', 0.6, 5.65, [f'ТП 3 конт. — {kw(rr["ufh"])} кВт', f'Кв-6, 7 — {kw(rr["rest"])} кВт'])
    tg('1.2', 6.45, 4.1, ['ТП 2 конт.'])
    tg('1.3', 9.95, 3.6, ['ТП 1 конт.'])
    tg('1.4', 9.95, 5.95, ['ТП 1 конт.'])
    tg('1.9', 9.75, 10.3, ['ТП 2 конт.'])
    tg('1.7', 13.15, 10.35, ['ТП 1 конт.'])
    tg('1.8', 12.85, 12.95, ['ТП 1 конт.'])
    rr = r['1.6']
    tg('1.6', 17.0, 12.45, ['ТП 2 конт. + радиатор'])
    rr = r['1.5']
    tg('1.5', 13.4, 6.4, ['ТП 4 конт., дежурный', 'режим +10 °С'])
    pl.bubble_x([0, 6.1, 9.5, 12.6, 20.0], -0.55, ['1', '2', '3', '4', '5'])
    body = pl.svg()
    lg, yy = legend(296, 14, [
        (SYM['ufh'], 'Водяной тёплый пол (ТП), петли PE-Xa 16×2,0 от коллектора'),
        (SYM['ufhg'], 'ТП гаража — дежурный режим +10 °С'),
        (SYM['conv'], 'Внутрипольный конвектор с вентилятором (Кв)'),
        (SYM['cab'], 'Коллекторный шкаф (КШ)'),
        (SYM['t1'], 'Т1 — подающий трубопровод отопления'),
        (SYM['t2'], 'Т2 — обратный трубопровод отопления'),
        (SYM['eco'], 'Теплотрасса в баню (предизолированная труба)'),
    ])
    body += lg
    tbl = ('<table><tr><th>Обозн.</th><th>Оборудование топочной 1.6</th></tr>'
           '<tr><td class="c">К1, К2</td><td>Котлы газовые настенные конденсационные одноконтурные, каскад 2×24 кВт</td></tr>'
           '<tr><td class="c">ЭК</td><td>Электрокотёл резервный 12 кВт, 380 В</td></tr>'
           '<tr><td class="c">ГС + РК</td><td>Гидрострелка и распределительный коллектор с насосными группами</td></tr>'
           f'<tr><td class="c">Б1</td><td>Бойлер косвенного нагрева 300 л (ГВС дома)</td></tr>'
           '<tr><td class="c">РБ</td><td>Расширительные баки отопления и ГВС</td></tr>'
           '<tr><td class="c">ШУ</td><td>Шкаф автоматики котельной</td></tr></table>')
    body += fo(296, yy + 1, 118, 40, tbl, 2.0)
    body += notes(296, yy + 42, 118, 120, [
        'Подложка — АР, Альбом 2, лист 4 (24.07.2026). Ярлык помещения: номер, расчётная температура, '
        'теплопотери при –25 °С.',
        'Весь 1 этаж — водяной тёплый пол. В гостиной и бильярдной ТП дополняется внутрипольными конвекторами '
        'с вентилятором у остекления (выбор Заказчика).',
        'Разводка от коллекторов — лучевая, в стяжке пола; температура пола в жилых не выше 29 °С, '
        'в санузлах — до 33 °С.',
        'Котельная: газ (основной) + электрокотёл (резерв). Помещение 1.6 — с наружной дверью и окном, '
        'дымоходы и вытяжка — выше кровли.',
        'Число контуров ТП, длины конвекторов уточняются на стадии Р.',
    ])
    return sheet_svg(DEFS + body + text(160, 10, 'План 1 этажа. Отопление. М 1:100', 3.5, 'middle'),
                     'План 1 этажа дома. Отопление', no, total)


# ================================================================= ЛИСТ 2: дом, 2 этаж, отопление
def sheet_heat2(no, total):
    pl = Plan(60.0, 212.0, 10.0)
    UNDER[no] = (HOUSE, 7, 213.5, 606.7, K100, (92, 38, 860, 622), pl.ox, pl.oy, pl.s)
    r = ROOM
    for z in ([(12.8, 6.5), (15.45, 6.5), (15.45, 8.75), (12.8, 8.75)],
              [(15.75, 6.5), (19.8, 6.5), (19.8, 8.75), (15.75, 8.75)]):
        pl.poly(z, 'ufh')
    rads = [((1.4, 1.32, 3.0, 1.52), 'Р-1'), ((5.7, 1.32, 6.9, 1.52), 'Р-2'), ((9.6, 1.32, 11.2, 1.52), 'Р-3'),
            ((19.6, 10.3, 19.8, 11.5), 'Р-4'), ((14.7, 13.4, 15.3, 13.6), 'Р-5')]
    for (x0, y0, x1, y1), n in rads:
        pl.rect(x0, y0, x1, y1, 'rad')
    convs = [((17.2, 13.15, 18.2, 13.45), 'Кн-1'), ((10.2, 16.15, 12.2, 16.45), 'Кн-2'),
             ((0.32, 6.75, 0.62, 7.65), 'Кн-3')]
    for (x0, y0, x1, y1), n in convs:
        pl.rect(x0, y0, x1, y1, 'conv')
    tw = [((19.6, 7.3, 19.8, 8.0), 'Пс-1'), ((12.8, 7.1, 13.0, 7.8), 'Пс-2')]
    for (x0, y0, x1, y1), n in tw:
        pl.rect(x0, y0, x1, y1, 'rad')
    pl.rect(15.2, 12.0, 15.45, 13.0, 'cab')
    pl.label(16.0, 14.6, 'КШ-4 (Р 8 + ТП 2 вых., смесит. узел ТП)', 2.0, at=(15.35, 12.5))
    pl.circle(15.3, 13.4, 0.09, 'red')
    pl.circle(15.15, 13.4, 0.09, 'blue')
    pl.pl([(15.3, 13.4), (15.3, 12.95)], 't1')
    pl.pl([(15.15, 13.4), (15.15, 12.95)], 't2')

    def tg(no, x, y, extra, anchor=None):
        rr = r[no]
        pl.tag(x, y, [f'{no}  +{rr["ti"]} °С  {kw(rr["Q"])} кВт'] + extra, anchor=anchor)
    tg('2.3', 0.7, 4.6, ['Р-1 (под окном)'])
    tg('2.4', 4.6, 4.6, ['Р-2 (под окном)'])
    tg('2.5', 8.8, 4.6, ['Р-3 (под окном)'])
    tg('2.7', 16.0, 12.6, ['Р-4 + Кн-1 у О-8'])
    tg('2.6', 12.9, 12.6, ['Р-5'])
    tg('2.1', 9.8, 9.6, ['Кн-2 у витража О-13'])
    tg('2.2', 0.8, 9.0, ['Кн-3 у окна О-9'], anchor=(0.5, 7.2))
    rr = r['2.8']
    tg('2.8', 16.0, 6.1, [f'ТП {kw(rr["ufh"], 2)} + Пс-1'], anchor=(17.5, 7.5))
    rr = r['2.9']
    tg('2.9', 12.0, 6.1, [f'ТП {kw(rr["ufh"], 2)} + Пс-2'], anchor=(13.8, 7.5))
    pl.bubble_x([0, 6.1, 9.5, 12.6, 20.0], -0.55, ['1', '2', '3', '4', '5'])
    body = pl.svg()
    lg, yy = legend(296, 14, [
        (SYM['rad'], 'Радиатор стальной панельный (Р), нижнее подключение'),
        (SYM['conv'], 'Напольный конвектор у остекления в пол (Кн)'),
        (SYM['ufh'], 'Водяной тёплый пол санузлов (ЭППС 50 + стяжка 100)'),
        (SYM['cab'], 'Коллекторный шкаф (КШ)'),
        (SYM['t1'], 'Т1 — подающий стояк'),
        (SYM['t2'], 'Т2 — обратный стояк'),
    ])
    body += lg
    tbl = ('<table><tr><th>Прибор</th><th>Q, кВт</th><th>Тип (предварительно)</th></tr>'
           + ''.join(f'<tr><td class="c">{a}</td><td class="c">{b}</td><td>{c}</td></tr>' for a, b, c in (
               ('Р-1', kw(r['2.3']['Q']), 'тип 33, h=300, L≈1,6 м'),
               ('Р-2', kw(r['2.4']['Q']), 'тип 33, h=300, L≈1,2 м'),
               ('Р-3', kw(r['2.5']['Q']), 'тип 33, h=300, L≈1,6 м'),
               ('Р-4', '1,1', 'тип 22, h=500, L≈1,0 м'),
               ('Кн-1', '0,6', 'напольный, L≈1,0 м'),
               ('Кн-2', kw(r['2.1']['Q']), 'напольный, L≈2,0 м'),
               ('Кн-3', kw(r['2.2']['Q']), 'напольный, L≈1,0 м'),
               ('Р-5', kw(r['2.6']['Q']), 'тип 22, h=500, L≈0,6 м'),
               ('Пс-1, 2', '0,3/0,1', 'полотенцесушители'),
           )) + '</table>')
    body += fo(296, yy + 1, 118, 60, tbl, 2.0)
    body += notes(296, yy + 64, 118, 110, [
        'Приборы 2 этажа — стальные панельные радиаторы под окнами О-6 (подоконник ≈450 мм — низкие, h=300) '
        'и напольные конвекторы у остекления в пол (выбор Заказчика).',
        'Санузлы 2.8, 2.9 — тёплый пол от смесительного узла КШ-4 и полотенцесушители: водяные от '
        'отопления или от циркуляции ГВС (раздел ВК) — по выбору.',
        'Подводки от КШ-4 — лучевые, в стяжке; расчётные параметры приборов 70/55 °С.',
        'Ярлык: номер, температура, теплопотери при –25 °С.',
    ])
    return sheet_svg(DEFS + body + text(160, 10, 'План 2 этажа. Отопление. М 1:100', 3.5, 'middle'),
                     'План 2 этажа дома. Отопление', no, total)


# ================================================================= ЛИСТ 3: дом, 1 этаж, ВиК + подшивка
ZONES1 = [  # (полигон, класс, ярлык, глубина мм, отметка)
    ([(0.25, 6.45), (9.4, 6.45), (9.4, 7.9), (0.25, 7.9)], 'zA', 'П-1', 350, '+3,10'),
    ([(9.6, 6.45), (12.5, 6.45), (12.5, 9.0), (9.6, 9.0)], 'zB', 'П-2', 300, '+3,15'),
    ([(12.75, 9.05), (15.45, 9.05), (15.45, 11.25), (12.75, 11.25)], 'zA', 'П-3', 350, '+3,10'),
    ([(0.25, 5.0), (5.95, 5.0), (5.95, 6.15), (0.25, 6.15)], 'zA', 'П-4', 350, '+3,10'),
    ([(9.85, 0.45), (12.45, 0.45), (12.45, 6.15), (9.85, 6.15)], 'zB', 'П-5', 300, '+3,15'),
]
ZONES2 = [
    ([(12.75, 9.05), (15.45, 9.05), (15.45, 13.65), (12.75, 13.65)], 'zA', 'П-6', 400, '+6,75'),
    ([(9.6, 6.45), (12.5, 6.45), (12.5, 10.2), (9.6, 10.2)], 'zA', 'П-7', 350, '+6,80'),
    ([(0.25, 6.45), (9.4, 6.45), (9.4, 7.85), (0.25, 7.85)], 'zA', 'П-8', 400, '+6,75'),
    ([(0.25, 5.3), (12.45, 5.3), (12.45, 6.15), (0.25, 6.15)], 'zB', 'П-9', 350, '+6,80'),
    ([(15.75, 9.05), (16.75, 9.05), (16.75, 13.65), (15.75, 13.65)], 'zB', 'П-10', 350, '+6,80'),
    ([(12.75, 6.45), (19.8, 6.45), (19.8, 8.75), (12.75, 8.75)], 'zC', 'П-11', 0, '+6,42 (по АР)'),
]


def zone_table(zones, contents):
    rows = ''.join(f'<tr><td class="c">{z[2]}</td><td>{contents[z[2]]}</td><td class="c">'
                   f'{z[3] if z[3] else "—"}</td><td class="c">{z[4]}</td></tr>' for z in zones)
    return ('<table><tr><th>Зона</th><th>Что проходит</th><th>Глубина от низа плиты, мм</th>'
            f'<th>Низ подшивки</th></tr>{rows}</table>')


def sheet_vent1(no, total):
    pl = Plan(60.0, 212.0, 10.0)
    UNDER[no] = (HOUSE, 5, 209.8, 603.7, K100, (92, 38, 860, 622), pl.ox, pl.oy, pl.s)
    for poly, cls, lab, d, lvl in ZONES1:
        pl.poly(poly, cls)
    # приточная магистраль: шахта (в 1.7) -> холл -> под галерею -> гостиная/бильярдная/прихожая
    pl.rect(12.85, 9.15, 13.55, 9.85, 'shaft')
    pl.add(line(*pl.P(12.85, 9.15), *pl.P(13.55, 9.85), 0.25))
    pl.add(line(*pl.P(12.85, 9.85), *pl.P(13.55, 9.15), 0.25))
    pl.duct([(13.2, 9.5), (11.8, 9.5), (11.8, 7.2), (0.9, 7.2)], 250, 'S')
    pl.duct([(3.0, 7.2), (3.0, 5.6), (1.8, 5.6)], 160, 'S')
    pl.duct([(3.0, 5.6), (4.4, 5.6)], 160, 'S')
    pl.duct([(10.6, 7.2), (10.6, 2.6), (9.5, 2.6)], 125, 'S')
    for x in (1.6, 4.6, 7.6):
        pl.grille(x, 7.75, 'S', 70, 'up')
    pl.grille(1.8, 5.35, 'S', 60, 'down')
    pl.grille(4.4, 5.35, 'S', 60, 'down')
    pl.grille(9.15, 2.6, 'S', 30, 'left', 'left')
    # вытяжка 1 этажа
    pl.duct([(13.2, 9.3), (13.9, 9.3), (13.9, 8.95)], 160, 'E')
    pl.duct([(13.55, 9.75), (14.2, 9.75), (14.2, 11.9)], 125, 'E')
    pl.grille(14.2, 12.15, 'E', 30, 'down', 'right')
    pl.duct([(12.1, 9.0), (12.1, 3.0)], 160, 'E')
    pl.grille(11.4, 5.3, 'E', 50, 'left', 'left')
    pl.duct([(12.1, 5.3), (11.6, 5.3)], 125, 'E')
    pl.grille(11.4, 2.0, 'E', 40, 'left', 'left')
    pl.duct([(12.1, 2.0), (11.6, 2.0)], 125, 'E')
    pl.duct([(12.1, 9.0), (12.1, 9.3), (12.85, 9.3)], 160, 'E')
    pl.grille(9.15, 10.6, 'E', 90, 'right', 'right')
    pl.label(5.6, 9.6, 'В: кухня, решётка на стене +3,00', 2.0, at=(9.15, 10.6))
    pl.duct([(9.35, 10.6), (9.75, 10.6), (9.75, 8.7), (12.1, 8.7)], 125, 'E')
    # кондиционирование
    for (x0, y0, x1, y1), n, q in (((1.0, 6.55, 2.4, 7.55), 'К-1', '5,6'), ((5.5, 6.55, 6.9, 7.55), 'К-2', '5,6'),
                                   ((2.3, 5.05, 3.6, 5.9), 'К-3', '3,6')):
        pl.rect(x0, y0, x1, y1, 'acu')
        pl.t((x0 + x1) / 2, (y0 + y1) / 2, n, 1.9, 'middle', 'mag')
    pl.pl([(23.0, 3.6), (20.0, 3.6), (19.5, 3.6), (19.5, 8.4), (13.0, 8.4), (13.0, 9.05)], 'freon')
    pl.pl([(13.0, 8.4), (12.3, 8.4), (12.3, 7.0), (6.2, 7.0)], 'freon')
    pl.pl([(1.7, 7.0), (5.5, 7.0)], 'freon')
    pl.pl([(3.0, 7.0), (3.0, 5.9)], 'freon')
    pl.rect(21.2, 3.0, 23.6, 4.2, 'acu')
    pl.t(22.4, 3.6, 'НБ-1', 2.0, 'middle', 'mag')
    pl.label(20.6, 1.7, 'НБ-1, ≈22 кВт', 2.0, at=(22.4, 3.0))
    # топочная, гараж
    pl.label(20.4, 14.8, 'Топочная — прим. 5', 1.9, at=(19.7, 12.9))
    pl.label(20.4, 0.4, 'Гараж — прим. 6', 1.9, at=(19.7, 6.9))
    # ярлыки зон
    for poly, cls, lab, d, lvl in ZONES1:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        pl.t(min(xs) + 0.15, max(ys) - 0.25, f'{lab} {lvl}', 1.9, 'start')
    pl.label(13.7, 7.6, 'Шахта Ш-1 (с П1 на 2 этаже)', 2.0, at=(13.2, 9.5))
    pl.bubble_x([0, 6.1, 9.5, 12.6, 20.0], -0.55, ['1', '2', '3', '4', '5'])
    body = pl.svg()
    lg, yy = legend(296, 14, [
        (SYM['ductS'], 'Приточный воздуховод от П1 (Ø — на листе)'),
        (SYM['ductE'], 'Вытяжной воздуховод к П1'),
        (SYM['gS'], 'Приточная решётка/диффузор, L — м³/ч'),
        (SYM['gE'], 'Вытяжная решётка, L — м³/ч'),
        (SYM['acu'], 'Внутренний канальный блок кондиционирования'),
        (SYM['freon'], 'Фреонопроводы и дренаж'),
        (SYM['shaft'], 'Шахта воздуховодов и фреонопроводов'),
        (SYM['zA'], 'Подшивка: зона с блоками/магистралями'),
        (SYM['zB'], 'Подшивка: зона только воздуховодов'),
    ])
    body += lg
    cont = {'П-1': 'К-1, К-2 (гостиная), магистраль П Ø250, щелевые диффузоры на север',
            'П-2': 'магистраль П Ø250, В Ø160, фреон', 'П-3': 'шахта Ш-1, магистрали П и В',
            'П-4': 'К-3 (бильярдная), П Ø160', 'П-5': 'В от с/у и тамбура, П Ø125 в прихожую'}
    body += fo(296, yy + 1, 118, 50, zone_table(ZONES1, cont), 1.95)
    body += notes(296, yy + 54, 118, 80, [
        'Глубина подшивки — от низа плиты; отметки — при низе плиты +3,45 (уточнить по КР). Низ подшивки '
        'не ниже верха окон (+3,00).',
        'Гостиная (второй свет): подача — из подшивки под галереей 2.2 щелевыми диффузорами в сторону '
        'остекления; вытяжка — из верхней зоны второго света (лист 4).',
        'Над плитой — островная вытяжка с выбросом наружу или встроенная в столешницу; согласовать с дизайнером.',
        'Воздуховоды — оцинкованная сталь, с шумоглушителями; дренаж блоков — в канализацию через сифон (ВК).',
        'Топочная 1.6: вытяжка 3 обмена в час (≈190 м³/ч) — канал по фасаду выше кровли; приток — решётка '
        'в наружной стене; котлы с закрытой камерой сгорания.',
        'Гараж 1.5: естественная вентиляция — приточная решётка внизу, вытяжная вверху противоположной стены.',
    ])
    return sheet_svg(DEFS + body + text(160, 10, 'План 1 этажа. Вентиляция и кондиционирование. '
                                                 'Зоны подшивки потолков. М 1:100', 3.5, 'middle'),
                     'План 1 этажа дома. Вентиляция и кондиционирование. Зоны подшивки', no, total)


# ================================================================= ЛИСТ 4: дом, 2 этаж, ВиК + подшивка
def sheet_vent2(no, total):
    pl = Plan(60.0, 212.0, 10.0)
    UNDER[no] = (HOUSE, 7, 213.5, 606.7, K100, (92, 38, 860, 622), pl.ox, pl.oy, pl.s)
    for poly, cls, lab, d, lvl in ZONES2:
        pl.poly(poly, cls)
    # П1 и шахта
    pl.rect(14.6, 9.1, 15.4, 9.9, 'ahu')
    pl.t(15.0, 9.5, 'П1', 2.0, 'middle', 'blue')
    pl.rect(12.85, 9.15, 13.55, 9.85, 'shaft')
    pl.add(line(*pl.P(12.85, 9.15), *pl.P(13.55, 9.85), 0.25))
    pl.add(line(*pl.P(12.85, 9.85), *pl.P(13.55, 9.15), 0.25))
    pl.label(16.9, 15.2, 'П1, ≈700 м³/ч (прим. 2)', 1.9, at=(15.0, 9.9))
    # приток 2 этажа
    pl.duct([(14.6, 9.6), (13.55, 9.6)], 250, 'S')
    pl.duct([(14.6, 9.6), (12.0, 9.6), (12.0, 7.4), (0.9, 7.4)], 200, 'S')
    for x, L in ((2.0, 60), (6.2, 60)):
        pl.duct([(x, 7.4), (x, 5.9)], 125, 'S')
        pl.grille(x, 5.65, 'S', L, 'down')
    pl.duct([(10.4, 7.4), (10.4, 5.9)], 125, 'S')
    pl.grille(10.4, 5.65, 'S', 60, 'down')
    pl.grille(0.75, 6.95, 'S', 30, 'down', 'right')
    pl.duct([(15.4, 9.6), (16.2, 9.6), (16.2, 10.8)], 125, 'S')
    pl.grille(16.2, 11.05, 'S', 60, 'right')
    # вытяжка 2 этажа
    pl.duct([(15.0, 9.1), (15.0, 8.0), (18.0, 8.0)], 160, 'E')
    pl.duct([(15.0, 8.0), (14.0, 8.0)], 125, 'E')
    pl.grille(18.25, 8.0, 'E', 75, 'up', 'right')
    pl.grille(13.75, 8.0, 'E', 75, 'up', 'left')
    pl.grille(14.0, 12.2, 'E', 60, 'up', 'right')
    pl.duct([(14.0, 11.95), (14.0, 9.9)], 125, 'E')
    pl.duct([(13.2, 9.85), (13.2, 10.6), (9.75, 10.6)], 160, 'E')
    pl.grille(11.0, 10.0, 'E', 90, 'down', 'right')
    pl.grille(9.55, 10.6, 'E', 120, 'right', 'left')
    pl.label(3.0, 12.0, 'В: верх второго света, решётка +6,40', 2.0, at=(9.55, 10.6))
    # кондиционирование
    for (x0, y0, x1, y1), n, q in (((1.3, 6.6, 2.6, 7.3), 'К-4', '2,8'), ((5.5, 6.6, 6.8, 7.3), 'К-5', '2,8'),
                                   ((9.75, 6.6, 11.05, 7.3), 'К-6', '2,8'), ((12.9, 11.3, 13.6, 12.6), 'К-7', '2,8')):
        pl.rect(x0, y0, x1, y1, 'acu')
        pl.t((x0 + x1) / 2, (y0 + y1) / 2, n, 1.8, 'middle', 'mag')
    for x in (1.95, 6.15, 10.4):
        pl.pl([(x, 6.6), (x, 6.0)], 'acu', 'stroke-width="1.6" stroke-opacity="0.5"')
    pl.pl([(13.6, 11.95), (15.9, 11.95)], 'acu', 'stroke-width="1.6" stroke-opacity="0.5"')
    pl.pl([(13.2, 9.85), (13.2, 11.3)], 'freon')
    pl.pl([(13.2, 9.15), (12.3, 9.15), (12.3, 7.0), (1.95, 7.0)], 'freon')
    pl.pl([(10.4, 7.0), (10.4, 7.3)], 'freon')
    pl.pl([(6.15, 7.0), (6.15, 7.3)], 'freon')
    for poly, cls, lab, d, lvl in ZONES2:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        pl.t(min(xs) + 0.15, max(ys) - 0.25, f'{lab} {lvl}', 1.9, 'start')
    pl.bubble_x([0, 6.1, 9.5, 12.6, 20.0], -0.55, ['1', '2', '3', '4', '5'])
    body = pl.svg()
    lg, yy = legend(296, 14, [
        (SYM['ahu'], 'Приточно-вытяжная установка П1 с рекуперацией'),
        (SYM['ductS'], 'Приточный воздуховод'),
        (SYM['ductE'], 'Вытяжной воздуховод'),
        (SYM['gS'], 'Приточная решётка, L — м³/ч'),
        (SYM['gE'], 'Вытяжная решётка, L — м³/ч'),
        (SYM['acu'], 'Канальный блок кондиционирования'),
        (SYM['freon'], 'Фреонопроводы и дренаж'),
        (SYM['zA'], 'Подшивка: зона с блоками/магистралями'),
        (SYM['zB'], 'Подшивка: зона диффузоров'),
        (SYM['zC'], 'Подшивка санузлов — по АР'),
    ])
    body += lg
    cont = {'П-6': 'П1, шахта Ш-1, К-7, магистрали', 'П-7': 'магистрали П Ø200, В Ø160, фреон',
            'П-8': 'К-4, К-5, магистраль П Ø200', 'П-9': 'диффузоры и возврат кондиционеров спален',
            'П-10': 'диффузоры К-7 и приток спальни 2.7', 'П-11': 'вытяжка с/у Ø125'}
    body += fo(296, yy + 1, 118, 52, zone_table(ZONES2, cont), 1.95)
    body += notes(296, yy + 56, 118, 70, [
        'Отметки — при низе плиты покрытия +7,15 (3,5 м от пола по опросному листу); уточнить по КР. '
        'Верх окон 2 этажа +6,65 — подшивка у окон не заходит.',
        'П1 — в гардеробной 2.6 (выгородка ≈1,5×1,5 м с дверью для обслуживания), воздухозабор и выброс — '
        'через кровлю с разносом.',
        'Канальные блоки спален — в подшивке галереи/холла; в спальни — подача и возврат через стену, '
        'обслуживание — из коридора.',
    ])
    return sheet_svg(DEFS + body + text(160, 10, 'План 2 этажа. Вентиляция и кондиционирование. '
                                                 'Зоны подшивки потолков. М 1:100', 3.5, 'middle'),
                     'План 2 этажа дома. Вентиляция и кондиционирование. Зоны подшивки', no, total)


# ================================================================= ЛИСТ 5: баня
def sheet_bath(no, total):
    s = 13.3333
    pl = Plan(52.0, 150.0, s)
    UNDER[no] = (BATH, 5, 186.0, 493.4, K75, (55, 140, 900, 520), pl.ox, pl.oy, pl.s)
    r = ROOM
    zones = {'б7': [(0.3, 0.3), (5.2, 0.3), (5.2, 3.75), (2.2, 3.75), (2.2, 6.35), (0.3, 6.35)],
             'б6': [(5.6, 2.2), (10.3, 2.2), (10.3, 6.35), (5.6, 6.35)],
             'б2': [(10.7, 0.3), (12.25, 0.3), (12.25, 3.85), (10.7, 3.85)],
             'б3': [(12.55, 0.3), (15.65, 0.3), (15.65, 1.85), (12.55, 1.85)],
             'б4': [(12.55, 2.15), (15.65, 2.15), (15.65, 3.85), (12.55, 3.85)]}
    for z in zones.values():
        pl.poly(z, 'ufh')
    for (x0, y0, x1, y1) in ((5.7, 2.25, 7.85, 2.5), (8.0, 2.25, 10.15, 2.5)):
        pl.rect(x0, y0, x1, y1, 'conv')
    for (x0, y0, x1, y1) in ((0.7, 0.35, 2.7, 0.6), (2.8, 0.35, 4.7, 0.6)):
        pl.rect(x0, y0, x1, y1, 'conv')
    pl.rect(11.2, 6.2, 12.6, 6.4, 'rad')                         # Р-б1 спальня
    pl.rect(11.0, 3.6, 11.6, 3.8, 'rad')                         # Р-б2 прихожая
    pl.rect(13.0, 1.6, 13.6, 1.8, 'rad')                          # Пс-б1 с/у
    pl.rect(15.5, 2.9, 15.7, 3.5, 'rad')                          # Пс-б2 раздевалка
    pl.rect(15.45, 0.45, 15.7, 1.25, 'cab')
    pl.circle(15.3, 2.55, 0.3, 'eq')
    pl.t(15.3, 2.55, 'Б2', 1.7, 'middle')
    pl.pl([(15.0, -1.9), (15.0, 0.1), (15.0, 0.85), (15.45, 0.85)], 'eco')
    pl.label(16.4, -1.0, 'Т1, Т2 от котельной дома', 2.0, at=(15.0, -1.5))
    pl.label(16.6, -0.8, 'КШ-Б (прим. 5)', 2.0, at=(15.6, 0.85))
    pl.label(16.6, 3.7, 'Б2 — бойлер 200 л', 2.0, at=(15.55, 2.55))
    # естественная вентиляция + рекомендации
    for x, y in ((14.2, 1.55), (1.0, 6.2)):
        pl.circle(x, y, 0.18, 'eq')
        pl.t(x, y, 'в', 1.6, 'middle', 'brown')
    pl.label(2.2, 7.7, 'Рекомендуемый вытяжной вентилятор (прим. 3)', 2.0, at=(1.0, 6.2))
    pl.label(4.6, 8.7, 'Парная — печь-каменка (прим. 4)', 2.0, at=(4.0, 5.2))

    def tg(no, x, y, extra, anchor=None):
        rr = r[no]
        pl.tag(x, y, [f'{rr["name"]}  +{rr["ti"]} °С  {kw(rr["Q"])} кВт'] + extra, anchor=anchor, h=2.0)
    rr = r['б7']
    tg('б7', 0.5, 3.4, [f'ТП 3 конт. — {kw(rr["ufh"])} кВт', f'Кв-б3, б4 (12 В) — {kw(rr["rest"])} кВт'])
    rr = r['б6']
    tg('б6', 5.8, 5.9, [f'ТП 2 конт. — {kw(rr["ufh"])} кВт', f'Кв-б1, б2 с вент. — {kw(rr["rest"])} кВт'])
    tg('б5', 10.7, 5.75, ['Р-б1'])
    tg('б2', 9.0, -0.4, ['ТП 1 конт. + Р-б2'], anchor=(11.4, 1.5))
    tg('б3', 12.5, -0.4, ['ТП 1 конт. + Пс-б1'], anchor=(13.3, 1.0))
    tg('б4', 12.6, 3.85, ['ТП 1 + Пс-б2'])
    pl.t(1.6, 1.0, 'Кв-б3, б4', 1.9, 'start', 'red')
    pl.t(6.0, 2.85, 'Кв-б1, Кв-б2', 1.9, 'start', 'red')
    pl.bubble_x([0, 5.4, 10.5, 15.9], -0.9, ['1', '2', '3', '4'])
    body = pl.svg()
    lg, yy = legend(30, 178, [
        (SYM['ufh'], 'Водяной тёплый пол бани'),
        (SYM['conv'], 'Внутрипольный конвектор (Кв-б)'),
        (SYM['rad'], 'Радиатор / полотенцесушитель'),
        (SYM['cab'], 'Коллекторный шкаф КШ-Б'),
        (SYM['eco'], 'Предизолированная теплотрасса'),
    ], w=110)
    body += lg
    t = ('<table><tr><th>Помещение</th><th>t, °С</th><th>Q, Вт</th><th>ТП, Вт</th><th>Доп. прибор, Вт</th></tr>'
         + ''.join(f'<tr><td>{r[n]["name"]}</td><td class="c">{r[n]["ti"]}</td><td class="c">{r[n]["Q"]}</td>'
                   f'<td class="c">{r[n].get("ufh", "—")}</td><td class="c">{r[n].get("rest", r[n]["Q"])}</td></tr>'
                   for n in ('б2', 'б3', 'б4', 'б5', 'б6', 'б7'))
         + f'<tr><td>Итого баня</td><td></td><td class="c">{C["Q_bath"]}</td><td></td><td></td></tr></table>')
    body += text(205, 178, 'Теплопотери бани при –25 °С', 3.0, 'middle')
    body += fo(150, 182, 112, 45, t, 2.1)
    body += notes(296, 30, 118, 120, [
        'Решение Заказчика: отопление бани — от котельной дома (Uponor Ecoflex Quattro), в с/у — шкаф с '
        'прямой и смесительной гребёнками; ГВС — собственный бойлер косвенного нагрева.',
        'Комната отдыха: внутрипольный конвектор с вентилятором вдоль панорамного окна + ТП по всей площади.',
        'Вентиляция бани — естественная, через окна (решение Заказчика); кондиционирования нет. Рекомендуем '
        'вытяжные вентиляторы с таймером в помывочной и с/у (50–100 м³/ч) — против сырости и плесени.',
        'Парная водяным отоплением не обслуживается: печь-каменка; приток — у печи, вытяжка — под потолком '
        'с противоположной стороны, по паспорту печи.',
        'Шкаф КШ-Б: прямой коллектор 5 вых. (Р-б, Кв-б, Пс-б), смесительный узел ТП 8 вых. (45/35 °С), '
        'загрузка бойлера Б2 через зональный клапан с приоритетом. Место Б2 — согласовать.',
    ])
    return sheet_svg(DEFS + body + text(200, 12, 'Баня. План. Отопление и вентиляция. М 1:75', 3.5, 'middle'),
                     'Баня. Отопление и вентиляция', no, total)


# ================================================================= ЛИСТ 6: принципиальная схема
def sheet_scheme(no, total):
    s = []
    A = s.append

    def box(x, y, w, h, lines, cls='eq', fs=2.2):
        A(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="{cls}"/>')
        n = len(lines)
        for i, t in enumerate(lines):
            A(text(x + w / 2, y + h / 2 + (i - (n - 1) / 2) * fs * 1.35, t, fs, 'middle'))

    def pipe(pts, cls):
        A(f'<polyline points="{" ".join(f"{x},{y}" for x, y in pts)}" class="{cls}"/>')

    def pump(x, y, d='right'):
        A(f'<circle cx="{x}" cy="{y}" r="2.2" fill="#fff" stroke="#000" stroke-width="0.3"/>')
        if d == 'right':
            A(f'<path d="M{x - 1.2},{y - 1.6} L{x + 2.0},{y} L{x - 1.2},{y + 1.6}" fill="none" stroke="#000" stroke-width="0.3"/>')
        else:
            A(f'<path d="M{x - 1.6},{y + 1.2} L{x},{y - 2.0} L{x + 1.6},{y + 1.2}" fill="none" stroke="#000" stroke-width="0.3"/>')

    def valve3(x, y):
        A(f'<path d="M{x - 2},{y - 1.3} L{x + 2},{y + 1.3} L{x + 2},{y - 1.3} L{x - 2},{y + 1.3} z" fill="#fff" stroke="#000" stroke-width="0.3"/>')
        A(f'<path d="M{x - 1.3},{y + 2.6} L{x},{y} L{x + 1.3},{y + 2.6} z" fill="#fff" stroke="#000" stroke-width="0.3"/>')
        A(f'<rect x="{x - 1}" y="{y - 4.5}" width="2" height="2" fill="#fff" stroke="#000" stroke-width="0.3"/>')
        A(line(x, y - 2.5, x, y - 1.3, 0.3))

    A(text(160, 12, 'Принципиальная схема теплоснабжения дома и бани', 3.5, 'middle'))
    # котлы
    box(30, 30, 22, 26, ['К1', 'газовый', 'конденс.', '24 кВт'])
    box(58, 30, 22, 26, ['К2', 'газовый', 'конденс.', '24 кВт'])
    box(86, 30, 22, 26, ['ЭК', 'электро-', 'котёл', '12 кВт'])
    # подача/обратка котлов в гидрострелку
    for x in (41, 69, 97):
        pipe([(x - 4, 56), (x - 4, 70), (122, 70)], 't1')
        pipe([(x + 4, 56), (x + 4, 82), (122, 82)], 't2')
        A(f'<circle cx="{x - 4}" cy="64" r="1.4" fill="#fff" stroke="#000" stroke-width="0.25"/>')
    box(122, 62, 10, 28, ['ГС'], 'eqs')
    A(text(127, 95, 'гидрострелка', 2.0, 'middle'))
    # распределительный коллектор
    A('<rect x="140" y="66" width="190" height="6" fill="#f6c9c9" stroke="#000" stroke-width="0.3"/>')
    A('<rect x="140" y="80" width="190" height="6" fill="#c9d9f6" stroke="#000" stroke-width="0.3"/>')
    pipe([(132, 69), (140, 69)], 't1')
    pipe([(132, 83), (140, 83)], 't2')
    A(text(235, 62.5, 'Распределительный коллектор (Т1 / Т2)', 2.3, 'middle'))
    circuits = [
        (150, 'Б1 ГВС дома', '300 л', 'priority'),
        (172, 'Радиаторы и Кн', '2 эт. → КШ-4', 'direct'),
        (194, 'Конвекторы Кв', '1 эт. → КШ-2', 'direct'),
        (216, 'ТП 1 эт., гараж', '→ КШ-1…3', 'mix'),
        (238, 'Калорифер П1', '≈2 кВт', 'mix'),
        (260, 'Баня', 'Ecoflex Quattro', 'direct'),
    ]
    for x, n1, n2, typ in circuits:
        pipe([(x, 72), (x, 120)], 't1')
        pipe([(x + 8, 86), (x + 8, 120)], 't2')
        pump(x, 100, 'up')
        if typ == 'mix':
            valve3(x, 110)
            pipe([(x + 2, 110), (x + 8, 110)], 't2')
        if typ == 'priority':
            A(text(x + 4, 92, 'приоритет', 1.7, 'middle'))
        A(text(x + 4, 126, n1, 2.0, 'middle'))
        A(text(x + 4, 129.5, n2, 2.0, 'middle'))
    # бойлер дома
    A('<rect x="146" y="140" width="16" height="30" rx="7" fill="#fff" stroke="#000" stroke-width="0.35"/>')
    A(text(154, 155, 'Б1', 2.3, 'middle'))
    A(text(154, 159, '300 л', 2.0, 'middle'))
    pipe([(150, 132), (150, 145)], 't1')
    pipe([(158, 132), (158, 165)], 't2')
    A(text(154, 176, 'ХВС → ГВС, циркуляция', 2.0, 'middle'))
    A(text(154, 179.5, '(подключение — раздел ВК)', 2.0, 'middle'))
    # баня
    pipe([(260, 132), (260, 150), (300, 150)], 't1')
    pipe([(268, 132), (268, 158), (300, 158)], 't2')
    A('<rect x="272" y="145.5" width="22" height="16" fill="none" stroke="#6b2fb3" stroke-width="0.3" stroke-dasharray="1.5 0.8"/>')
    A(text(283, 142.8, 'трасса ≈15 м', 2.0, 'middle'))
    A('<rect x="298" y="134" width="114" height="72" fill="none" stroke="#000" stroke-width="0.3" stroke-dasharray="3 1"/>')
    A(text(355, 138.5, 'Баня — шкаф КШ-Б в с/у', 2.4, 'middle'))
    pipe([(300, 150), (308, 150)], 't1')
    valve3(310, 150)
    pipe([(312, 150), (330, 150)], 't1')
    A(text(310, 143.2, 'зональный клапан', 1.7, 'middle'))
    pipe([(300, 158), (330, 158)], 't2')
    # бойлер бани
    pipe([(310, 152.6), (310, 178)], 't1')
    A('<rect x="302" y="176" width="18" height="24" rx="7" fill="#fff" stroke="#000" stroke-width="0.35"/>')
    A(text(311, 186, 'Б2', 2.3, 'middle'))
    A(text(311, 190, '200 л', 2.0, 'middle'))
    pipe([(318, 196), (324, 196), (324, 158)], 't2')
    # прямая гребёнка
    A('<rect x="330" y="146" width="30" height="5" fill="#f6c9c9" stroke="#000" stroke-width="0.3"/>')
    A('<rect x="330" y="155.5" width="30" height="5" fill="#c9d9f6" stroke="#000" stroke-width="0.3"/>')
    A(text(345, 165.5, 'прямая гребёнка, 5 вых.', 1.9, 'middle'))
    A(text(345, 168.7, 'Р-б, Кв-б, Пс-б, 70/55 °С', 1.9, 'middle'))
    # смесительный узел ТП
    pipe([(360, 148.5), (366, 148.5)], 't1')
    pump(368.5, 148.5)
    pipe([(371, 148.5), (376, 148.5)], 't1')
    valve3(378, 148.5)
    pipe([(380, 148.5), (386, 148.5)], 't1')
    A('<rect x="386" y="146" width="20" height="5" fill="#f6c9c9" stroke="#000" stroke-width="0.3"/>')
    A('<rect x="386" y="155.5" width="20" height="5" fill="#c9d9f6" stroke="#000" stroke-width="0.3"/>')
    pipe([(386, 158), (360, 158)], 't2')
    pipe([(378, 151.1), (378, 158)], 't2')
    A(text(396, 165.5, 'гребёнка ТП, 8 вых.', 1.9, 'middle'))
    A(text(396, 168.7, '45/35 °С', 1.9, 'middle'))
    A(fo(330, 176, 78, 26, '<p>Загрузка Б2 — с приоритетом (зональный клапан переключает подачу на бойлер); '
         'отопление бани в это время работает на тепловой инерции полов.</p>', 1.9))
    # подпитка, баки, газ, автоматика
    A('<ellipse cx="128" cy="112" rx="5" ry="7" fill="#fff" stroke="#000" stroke-width="0.35"/>')
    A(text(128, 112, 'РБ', 2.0, 'middle'))
    A(text(128, 123, 'бак 80 л', 1.9, 'middle'))
    pipe([(128, 90), (128, 105)], 't2')
    box(30, 100, 70, 20, ['ШУ: каскадный контроллер, погодозависимое', 'регулирование, комнатные датчики,',
                          'Wi-Fi/Modbus — интеграция в «умный дом»'], 'eqs', 2.0)
    A(text(65, 26, 'Газ — ввод по проекту газоснабжения; дымоходы — раздельные, выше кровли', 2.0, 'middle'))
    pipe([(20, 140), (60, 140)], 't1')
    A(text(62, 140, 'Т1 — подающий', 2.0, 'start'))
    pipe([(20, 146), (60, 146)], 't2')
    A(text(62, 146, 'Т2 — обратный', 2.0, 'start'))
    pump(25, 156)
    A(text(30, 156, 'циркуляционный насос', 2.0, 'start'))
    valve3(25, 166)
    A(text(30, 166, 'трёхходовой клапан с приводом', 2.0, 'start'))
    body = ''.join(s)
    tbl = ('<table><tr><th>Контур</th><th>Параметры</th><th>Нагрузка</th></tr>'
           '<tr><td>Котлы К1+К2 (каскад)</td><td class="c">до 80/60 °С</td><td class="c">48 кВт</td></tr>'
           f'<tr><td>Отопление дома (без гаража)</td><td class="c">—</td><td class="c">{kw(C["Q_house"])} кВт</td></tr>'
           f'<tr><td>Гараж (+10 °С)</td><td class="c">45/35 °С</td><td class="c">{kw(C["Q_gar"])} кВт</td></tr>'
           f'<tr><td>Баня (отопление)</td><td class="c">70/55 °С</td><td class="c">{kw(C["Q_bath"])} кВт</td></tr>'
           f'<tr><td>Калорифер П1</td><td class="c">70/50 °С</td><td class="c">{kw(C["Q_vent_heater"])} кВт</td></tr>'
           '<tr><td>Радиаторы, Кн, Кв</td><td class="c">70/55 °С</td><td class="c">—</td></tr>'
           '<tr><td>Тёплые полы</td><td class="c">45/35 °С</td><td class="c">—</td></tr>'
           f'<tr><td>ГВС дома (Б1 300 л)</td><td class="c">приоритет</td><td class="c">≈{int(C["P_coil_house"])} кВт</td></tr>'
           f'<tr><td>ГВС бани (Б2 200 л)</td><td class="c">приоритет</td><td class="c">≈{int(C["P_coil_bath"])} кВт</td></tr>'
           '</table>')
    body += text(84, 177, 'Тепловые нагрузки', 3.0, 'middle')
    body += fo(25, 180, 118, 56, tbl, 2.0)
    body += notes(150, 214, 76, 76, [
        'Схема принципиальная: арматура, фильтры, байпасы, предохранительные группы показываются на стадии Р.',
        'Котлы — каскад двух настенных конденсационных (24 кВт): при отказе одного второй покрывает ≈55 % '
        'нагрузки; электрокотёл 12 кВт — резерв на случай отключения газа (дежурный режим).',
        'ГВС дома и бани — с приоритетом загрузки бойлеров; температура ГВС 60 °С (данные Заказчика), '
        'дезинфекционный нагрев — по программе контроллера.',
        'Автоматика уровня «Люкс»: погодозависимое управление контурами, комнатные датчики и приводы на '
        'коллекторах, управление со смартфона, интеграция в «умный дом».',
    ], fs=2.3)
    return sheet_svg(DEFS + body, 'Принципиальная схема теплоснабжения', no, total)


# ================================================================= ЛИСТ 7: ситуационная схема
def sheet_site(no, total):
    # page 3 АР: М 1:200; ось 1 дома x≈? (по растру 100 dpi: ось1 520 px, ось5 915 px -> 1 м = 14,22 пт)
    pl = Plan(95.0, 205.0, 5.0)
    UNDER[no] = (HOUSE, 3, 374.4, 584.6, 14.22, (150, 40, 800, 700), pl.ox, pl.oy, pl.s)
    # трасса: от топочной (16.5, 13.8) к с/у бани
    pl.pl([(16.5, 13.0), (16.5, 18.0), (18.9, 20.3), (18.9, 25.0)], 'eco')
    pl.label(22.0, 18.6, 'Ecoflex Quattro, L≈15 м (прим. 3)', 2.2, at=(17.7, 19.2))
    pl.rect(21.2, 3.0, 23.6, 4.2, 'acu')
    pl.label(24.6, 1.5, 'НБ-1 (прим. 6)', 2.2, at=(22.4, 3.6))
    pl.label(22.0, 11.0, 'Дымоходы, вытяжка топочной (прим. 5)', 2.2, at=(20.0, 13.3))
    body = pl.svg()
    body += notes(296, 20, 118, 120, [
        'Подложка — АР, лист «Привязка дома и бани на участке», М 1:200.',
        'Граница проекта ОВиК — по наружным стенам дома и бани. Трасса в грунте показана для привязки '
        'вводов; земляные работы и основание — по месту.',
        'Ввод трубы в здания — через гильзы с уплотнением Uponor (ниже отметки 0,000), в доме — в топочную '
        '1.6, в бане — в с/у (шкаф КШ-Б).',
        'Санитарные трубы Quattro при отдельном бойлере бани не используются для ГВС; возможна подача по ним '
        'ХВС — согласовать с разделом ВК.',
        'Дымоходы котлов К1, К2 и вытяжка топочной — через стену топочной и вертикально по северо-восточному '
        'фасаду выше кровли; приток и выброс П1 — через кровлю над гардеробной 2.6.',
        'Наружный блок НБ-1 — на опорной раме у северо-восточного фасада гаража (вариант — на кровле).',
        'Труба Ecoflex Quattro: две трубы отопления PE-Xa 32×2,9 и две санитарные в общей изоляции; '
        'глубина заложения — не менее 0,8 м, под проездом — в футляре.',
    ])
    return sheet_svg(DEFS + body + text(160, 12, 'Ситуационная схема. Теплотрасса дом — баня, наружные блоки. М 1:200',
                                        3.5, 'middle'), 'Ситуационная схема', no, total)


SHEETS = [sheet_heat1, sheet_heat2, sheet_vent1, sheet_vent2, sheet_bath, sheet_scheme, sheet_site]


def build():
    total = len(SHEETS)
    svgs = [f(i + 1, total) for i, f in enumerate(SHEETS)]
    hp = os.path.join(OUT, 'sheets.html')
    open(hp, 'w').write(html_doc(svgs))
    env = dict(os.environ, NODE_PATH=subprocess.check_output(['npm', 'root', '-g'], text=True).strip())
    fg = os.path.join(OUT, 'sheets_fg.pdf')
    subprocess.check_call(['node', os.path.join(HERE, '..', 'work', 'html2pdf.js'), hp, fg, '420', '297'], env=env)
    doc = fitz.open(fg)
    for no, (src, pno, ax, ay, k, clip, ox, oy, s_mm) in UNDER.items():
        page = doc[no - 1]
        f = (s_mm * MM) / k                      # масштаб подложки относительно листа АР
        X0 = ox * MM + (clip[0] - ax) * f
        Y0 = oy * MM + (clip[1] - ay) * f
        rect = fitz.Rect(X0, Y0, X0 + (clip[2] - clip[0]) * f, Y0 + (clip[3] - clip[1]) * f)
        page.draw_rect(rect, color=None, fill=(1, 1, 1), fill_opacity=0.5, overlay=False)
        page.show_pdf_page(rect, fitz.open(os.path.join(HERE, src)), pno - 1, clip=fitz.Rect(*clip), overlay=False)
    out = os.path.join(OUT, 'ОВ-листы.pdf')
    doc.save(out, garbage=3, deflate=True)
    print('ok', out, len(doc), 'листов')


if __name__ == '__main__':
    build()
