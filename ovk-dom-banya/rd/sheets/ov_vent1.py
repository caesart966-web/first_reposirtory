"""И05.09.26-ОВ, лист 9. План 1 этажа. Вентиляция и кондиционирование.

python3 sheets/ov_vent1.py  ->  out/ov_vent1.dxf + out/ov_vent1_Лист.pdf

Здесь же — общие для листов 9–11 данные сети (участки с трассой, отметкой, Ø и расходом из rd_calc.json)
и помощники рисования; ov_vent2.py и ov_vent_schemes.py импортируют их отсюда.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from rdbase import (new_doc, DPlan, RDSheet, add_underlay, insert_underlay, UNDER, save_and_pdf,  # noqa: E402
                    fmt_num, offset_poly, SHEET_LIST, SHEETS_TOTAL, axes, DUCT_LAYER, LAYERS)

OUT = os.path.join(ROOT, 'out')
os.makedirs(OUT, exist_ok=True)
RD = json.load(open(os.path.join(ROOT, '..', 'rd', 'rd_calc.json')))
CALC = json.load(open(os.path.join(ROOT, '..', 'ovk', 'calc.json')))
VS = RD['vent']['supply']
VE = RD['vent']['exhaust']
AC = {u['name']: u for u in RD['ac']['units']}
BRV = RD['boiler_room_vent']

SHEET_NO = 9

# ---------------------------------------------------------------- отметки (м от ±0,000)
Z1 = 3.40          # оси воздуховодов 1 этажа в подшивке (низ плиты +3,650)
Z2 = 7.30          # оси воздуховодов 2 этажа в подшивке (низ плиты покрытия +7,550)
ZROOF = 9.00       # оголовки выброса над кровлей (кровля ≈+8,40 по АР16) — по АР

# Ш-1 (АР09: x 12.70–13.90, y 9.05–9.45): стояки — П Ø200, В Ø200, фреон, П (2.7) Ø100
SH1 = (12.70, 9.05, 13.90, 9.45)
RIS_P, RIS_V, RIS_F, RIS_P27 = (12.95, 9.25), (13.35, 9.25), (13.60, 9.22), (13.80, 9.25)
# Ш-2 (АР03/АР09: x 15.10–15.60, y 12.10–13.60): каналы снизу вверх по плану (задание АР)
SH2 = (15.10, 12.10, 15.60, 13.60)
SH2_CH = [  # (y центра, Ø мм, обозначение) — с юга на север, согласовано с листами 7–8
    (12.30, 250, 'Выб.П1'),   # выброс П1 — в квадратном канале 400×400 из АР (y 12,10–12,50)
    (12.68, 250, 'В2'),       # вытяжка топочной (естественная)
    (12.92, 125, 'Дг'),       # дымоход газовых котлов К1, К2 — общий каскадный Ø125
    (13.18, 280, 'Дп'),       # дымоход пеллетного котла (сэндвич Ø200/280, как в АР)
]
SH2_SQ = (12.10, 12.50)       # квадратный канал АР
SH2_X = 15.36


def sec_d(net, sid):
    return net[sid]['d']


def sec_L(net, sid):
    return net[sid]['L']


# ---------------------------------------------------------------- сеть 1 этажа: (id, вид, трасса, Ø, L)
# вид: П — приток П1, В — вытяжка П1, Н — наружный воздух, X — выброс
NET1 = [
    ('П1-A', 'П', [(16.90, 9.95), (12.95, 9.95)], sec_d(VS, 'П1-A'), sec_L(VS, 'П1-A')),
    ('A-B', 'П', [(12.95, 9.95), (11.65, 9.95), (11.65, 6.75), (10.60, 6.75)], sec_d(VS, 'A-B'), sec_L(VS, 'A-B')),
    ('1.2', 'П', [(10.60, 6.75), (10.60, 2.20), (9.55, 2.20)], sec_d(VS, '1.2'), sec_L(VS, '1.2')),
    ('B-E', 'П', [(10.60, 6.75), (7.60, 6.75)], sec_d(VS, 'B-E'), sec_L(VS, 'B-E')),
    ('гр.1.10-в', 'П', [(7.60, 6.75), (7.60, 7.62)], sec_d(VS, 'гр.1.10-в'), sec_L(VS, 'гр.1.10-в')),
    ('E-F', 'П', [(7.60, 6.75), (4.60, 6.75)], sec_d(VS, 'E-F'), sec_L(VS, 'E-F')),
    ('гр.1.10-с', 'П', [(4.60, 6.75), (4.60, 7.62)], sec_d(VS, 'гр.1.10-с'), sec_L(VS, 'гр.1.10-с')),
    ('F-G', 'П', [(4.60, 6.75), (3.00, 6.75)], sec_d(VS, 'F-G'), sec_L(VS, 'F-G')),
    ('1.11', 'П', [(3.00, 6.75), (3.00, 5.55), (2.20, 5.55)], sec_d(VS, '1.11'), sec_L(VS, '1.11')),
    ('1.11-з', 'П', [(2.20, 5.55), (1.00, 5.55)], sec_d(VS, '1.11-з'), sec_L(VS, '1.11-з')),
    ('G-H', 'П', [(3.00, 6.75), (0.90, 6.75)], sec_d(VS, 'G-H'), sec_L(VS, 'G-H')),
    ('гр.1.10-з', 'П', [(0.90, 6.75), (0.90, 7.62)], sec_d(VS, 'гр.1.10-з'), sec_L(VS, 'гр.1.10-з')),
    ('стояк П', 'П', [(12.95, 9.95), RIS_P], sec_d(VS, 'стояк П'), sec_L(VS, 'стояк П')),
    ('стояк П2.7', 'П', [(13.80, 9.95), RIS_P27], sec_d(VS, '2.7 (ЩП)'), sec_L(VS, '2.7 (ЩП)')),
    # вытяжка П1 (трасса — по ходу воздуха к П1)
    ('A-П1', 'В', [(14.80, 9.55), (16.90, 9.55)], sec_d(VE, 'A-П1'), sec_L(VE, 'A-П1')),
    ('1.8', 'В', [(14.80, 11.00), (14.80, 9.55)], sec_d(VE, '1.8'), sec_L(VE, '1.8')),
    ('B-A', 'В', [(13.35, 9.55), (14.80, 9.55)], sec_d(VE, 'B-A'), sec_L(VE, 'B-A')),
    ('стояк В', 'В', [RIS_V, (13.35, 9.55)], sec_d(VE, 'стояк В'), sec_L(VE, 'стояк В')),
    ('С-B', 'В', [(12.05, 8.70), (12.05, 9.55), (13.35, 9.55)], sec_d(VE, 'С-B'), sec_L(VE, 'С-B')),
    ('кухня', 'В', [(9.62, 10.00), (9.90, 10.00), (9.90, 8.70), (12.05, 8.70)], sec_d(VE, 'кухня'), sec_L(VE, 'кухня')),
    ('D-С', 'В', [(12.05, 5.30), (12.05, 8.70)], sec_d(VE, 'D-С'), sec_L(VE, 'D-С')),
    ('1.4', 'В', [(11.30, 5.30), (12.05, 5.30)], sec_d(VE, '1.4'), sec_L(VE, '1.4')),
    ('E-D', 'В', [(12.05, 2.00), (12.05, 5.30)], sec_d(VE, 'E-D'), sec_L(VE, 'E-D')),
    ('1.3', 'В', [(11.00, 2.00), (12.05, 2.00)], sec_d(VE, '1.3'), sec_L(VE, '1.3')),
    # наружный воздух и выброс
    ('Н', 'Н', [(19.80, 11.10), (19.40, 11.10), (19.40, 9.55), (18.50, 9.55)], 250, 700),
    ('Выброс', 'X', [(18.50, 9.95), (18.90, 9.95), (18.90, SH2_CH[0][0]), (15.60, SH2_CH[0][0])], 250, 700),
]

# решётки 1 этажа: (x, y, вид, L, направление, подпись, на стене?)
GRILLES1 = [
    (7.60, 7.75, 'П', 70, 'up', None, True),
    (4.60, 7.75, 'П', 70, 'up', None, True),
    (0.90, 7.75, 'П', 70, 'up', None, True),
    (2.20, 5.55, 'П', 60, 'down', None, False),
    (1.00, 5.55, 'П', 60, 'down', None, False),
    (9.40, 2.20, 'П', 30, 'left', None, True),
    (14.80, 11.10, 'В', 30, 'up', None, True),
    (9.55, 10.00, 'В', 90, 'left', None, True),
    (11.30, 5.30, 'В', 50, 'down', None, False),
    (11.00, 2.00, 'В', 40, 'down', None, False),
]

# блоки кондиционирования: имя -> (x0, y0, x1, y1) в плане; подшивка
KU1 = {'К-1': (1.75, 7.25, 2.65, 7.87), 'К-2': (5.45, 7.25, 6.35, 7.87), 'К-3': (3.60, 5.45, 4.30, 6.07)}
KU2 = {'К-4': (0.65, 6.62, 1.35, 7.24), 'К-5': (7.25, 6.62, 7.95, 7.24), 'К-6': (11.05, 6.62, 11.75, 7.24),
       'К-7': (13.90, 11.40, 14.52, 12.10)}

# зоны подшивки 1 этажа: (полигон, ярлык, глубина мм, низ подшивки, что проходит)
ZONES1 = [
    ([(0.25, 6.46), (9.45, 6.46), (9.45, 7.90), (0.25, 7.90)], 'П-1', 350, '+3,300',
     'К-1, К-2, магистраль П Ø250…Ø125, фреон, дренаж; диффузоры в торце подшивки'),
    ([(9.70, 6.46), (12.40, 6.46), (12.40, 10.15), (9.70, 10.15)], 'П-2', 400, '+3,250',
     'П Ø250, В Ø160/Ø125 с пересечением, фреон, дренаж'),
    ([(12.70, 9.05), (15.60, 9.05), (15.60, 11.00), (12.70, 11.00)], 'П-3', 450, '+3,200',
     'магистрали П и В Ø250 от П1 с пересечениями, стояки в Ш-1, фреон'),
    ([(0.20, 5.00), (5.85, 5.00), (5.85, 6.15), (0.20, 6.15)], 'П-4', 350, '+3,300',
     'К-3, П Ø125/Ø100, фреон, дренаж; диффузор К-3 в торце'),
    ([(9.70, 0.25), (12.25, 0.25), (12.25, 6.15), (9.70, 6.15)], 'П-5', 300, '+3,350',
     'П Ø100 в прихожую 1.2, В Ø125/Ø100 от 1.3, 1.4'),
]

# фреон и дренаж 1 этажа (жидкость+газ — одной линией)
FREON_IN = [(20.95, 13.35), (19.60, 13.35), (19.60, 10.35)]
FREON1 = [(19.60, 10.35), (12.30, 10.35), (12.30, 7.05), (2.20, 7.05)]
FREON1_RISER = [(13.60, 10.35), RIS_F]
FREON1_BR = [[(6.00, 7.05), (6.00, 7.25)], [(2.20, 7.05), (2.20, 7.25)], [(3.95, 7.05), (3.95, 6.07)]]
DRAIN1 = [(1.75, 7.40), (1.55, 7.40), (1.55, 7.15), (12.20, 7.15), (12.20, 5.80)]
DRAIN1_BR = [[(5.45, 7.40), (5.30, 7.40), (5.30, 7.15)], [(4.30, 5.90), (4.45, 5.90), (4.45, 7.15)]]


# ---------------------------------------------------------------- помощники рисования (общие для 9–11)
def dlabel(d):
    return f'Ø{d}' if isinstance(d, (int, float)) else f'{d[0]}×{d[1]}'


def seg_longest(pts):
    best, bi = -1, 0
    for i in range(len(pts) - 1):
        L = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        if L > best:
            best, bi = L, i
    return bi, best


def duct_text(p, pts, txt, kind, side=1, h=1.9, where=0.5, seg=None):
    """Подпись вдоль воздуховода (Ø и расход) на самом длинном участке трассы, со смещением в сторону side."""
    i, L = seg_longest(pts) if seg is None else (seg, None)
    (x0, y0), (x1, y1) = pts[i], pts[i + 1]
    L = math.hypot(x1 - x0, y1 - y0) or 1
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    nx, ny = -uy, ux
    mx, my = x0 + (x1 - x0) * where, y0 + (y1 - y0) * where
    off = p.H(h * 0.95) / p.unit + 0.13
    ang = math.degrees(math.atan2(uy, ux))
    if ang > 90.01 or ang < -89.99:
        ang += 180
        nx, ny = -nx, -ny
    p.t(mx + nx * off * side, my + ny * off * side, txt, h, 'center', DUCT_LAYER[kind], rot=ang)


def wall_grille(p, x, y, kind, L, direction, h=1.9, txt_side=1, size=0.40, name=None, txt_off=None):
    """Решётка в стене (в плане — полоска на грани стены) со стрелкой движения воздуха и расходом."""
    lay = DUCT_LAYER[kind]
    dx, dy = dict(down=(0, -1), up=(0, 1), left=(-1, 0), right=(1, 0))[direction]
    a, b = size / 2, 0.06
    if dx == 0:
        p.rect(x - a, y - b, x + a, y + b, lay, fill=LAYERS[lay][0])
    else:
        p.rect(x - b, y - a, x + b, y + a, lay, fill=LAYERS[lay][0])
    s = p.H(3.0) / p.unit
    if kind in ('П', 'Н') and kind != 'Н':
        p.arrow(x + dx * b, y + dy * b, x + dx * (b + s), y + dy * (b + s), lay)
    else:
        p.arrow(x + dx * (b + s), y + dy * (b + s), x + dx * b, y + dy * b, lay)
    txt = (f'{name} ' if name else '') + (f'L={L}' if L is not None else '')
    if txt_off is None:
        if dx == 0:
            tx, ty, al = x + a + p.H(0.8) / p.unit, y + dy * (b + s * 0.55), 'left'
        else:
            tx, ty, al = x + dx * (b + s * 0.5), y + (a + p.H(1.6) / p.unit) * txt_side, 'center'
    else:
        tx, ty, al = x + txt_off[0], y + txt_off[1], 'left'
    p.t(tx, ty, txt, h, al, lay)


def ceil_grille(p, x, y, kind, L, txt=(0.30, 0.0), h=1.9, size=0.40, name=None, al='left'):
    """Потолочная решётка/диффузор: квадрат с диагоналями, расход."""
    lay = DUCT_LAYER[kind]
    a = size / 2
    p.rect(x - a, y - a, x + a, y + a, lay)
    p.line(x - a, y - a, x + a, y + a, lay)
    p.line(x - a, y + a, x + a, y - a, lay)
    t = (f'{name} ' if name else '') + f'L={L}'
    p.t(x + txt[0], y + txt[1], t, h, al, lay)


def slot_diff(p, x0, x1, y, kind, direction, L=None, h=1.9, label=None, lab_dy=0.25):
    """Щелевой (линейный) диффузор в торце подшивки: полоса и стрелки выпуска."""
    lay = DUCT_LAYER[kind]
    p.rect(x0, y - 0.05, x1, y + 0.05, lay, fill=LAYERS[lay][0])
    dy = 1 if direction == 'up' else -1
    s = p.H(2.6) / p.unit
    n = max(2, int((x1 - x0) / 0.45) + 1)
    for i in range(n):
        xx = x0 + (x1 - x0) * (i + 0.5) / n
        p.arrow(xx, y + dy * 0.05, xx, y + dy * (0.05 + s), lay, size=1.5)
    if label:
        p.t((x0 + x1) / 2, y + dy * (0.05 + s + lab_dy) if dy > 0 else y - (0.05 + s + lab_dy), label, h,
            'center', lay)


def ku(p, name, box, h=2.0, cap=None):
    x0, y0, x1, y1 = box
    p.rect(x0, y0, x1, y1, 'ОВ_Фреон')
    p.rect(x0 + 0.04, y0 + 0.04, x1 - 0.04, y1 - 0.04, 'ОВ_Фреон')
    p.t((x0 + x1) / 2, (y0 + y1) / 2, name, h, 'center', 'ОВ_Фреон')


def riser(p, xy, kind, d):
    lay = DUCT_LAYER[kind] if kind in DUCT_LAYER else kind
    r = d / 2000.0
    p.circle(xy[0], xy[1], r, lay)
    p.line(xy[0] - r * 0.7, xy[1] - r * 0.7, xy[0] + r * 0.7, xy[1] + r * 0.7, lay)


def freon(p, pts, lw=35):
    p.pl(pts, 'ОВ_Фреон', ltype='ОВ_ШП', lw=lw)


def drain(p, pts):
    p.pl(pts, 'ОВ_Дренаж', ltype='ОВ_ПУНКТ')


def zone(p, pts, lab, depth, low, tx=None, ty=None, h=1.9, label=True):
    p.poly(pts, 'ОВ_зоны', hatch=('ANSI31', 170.0, 45, 5), ltype='ОВ_ШТРИХ')
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    if not label:
        return
    x = min(xs) + 0.12 if tx is None else tx
    y = max(ys) - 0.22 if ty is None else ty
    p.t(x, y, f'{lab}  низ {low}', h, 'left', 'ОВ_зоны')


def draw_net(p, net, labels=None, skip_labels=()):
    """Воздуховоды двумя линиями + подписи Ø/расход. labels: {id: (side, where, seg)}."""
    labels = labels or {}
    for sid, kind, pts, d, L in net:
        p.duct(pts, d, kind)
    for sid, kind, pts, d, L in net:
        if sid in skip_labels:
            continue
        side, where, seg = labels.get(sid, (1, 0.5, None))
        duct_text(p, pts, f'{dlabel(d)}  L={L}', kind, side=side, where=where, seg=seg)


def shaft2_inset(sh, x0, y0, title='Ш-2 в плане, верх — стенка к топочной (задание АР). М 1:20'):
    """Врезка на листе: шахта Ш-2 в плане, М 1:20 (1 м = 50 мм листа); длинная сторона — по горизонтали."""
    q = DPlan(sh.doc, k=1, space=sh.lay, unit=50.0, origin=(x0, y0))
    L = SH2[3] - SH2[1]
    W = SH2[2] - SH2[0]
    q.rect(0, 0, L, W, 'ОВ_шахты', lw=35)
    q.rect(-0.10, -0.10, L + 0.10, W + 0.10, 'ОВ_шахты', lw=50)
    names = {'Дг': 'Дг Ø125 — газовые котлы (каскад)', 'Выб.П1': 'выброс П1 Ø250', 'В2': 'В2 Ø250 — вытяжка топочной',
             'Дп': 'Дп Ø200/280 — пеллетный котел'}
    ups = {'Выб.П1': True, 'В2': False, 'Дг': False, 'Дп': True}
    depth = {'Выб.П1': 0.15, 'В2': 0.12, 'Дг': 0.30, 'Дп': 0.15}
    q.rect(SH2_SQ[0] - SH2[1], SH2_X - SH2[0] - 0.20, SH2_SQ[1] - SH2[1], SH2_X - SH2[0] + 0.20, 'ОВ_шахты', lw=25)
    for yc, d, n in SH2_CH:
        up = ups[n]
        cx, cy = yc - SH2[1], SH2_X - SH2[0]
        q.circle(cx, cy, d / 2000.0, 'ОВ_шахты', lw=35)
        if n == 'Дп':
            q.circle(cx, cy, 0.10, 'ОВ_шахты', lw=18)
        ty = (W + depth[n]) if up else -depth[n]
        q.pl([(cx, cy + (d / 2000.0 if up else -d / 2000.0)), (cx, ty)], 'ОВ_выноски')
        q.t(cx - 0.04, ty + (0.02 if up else -0.02), names[n], 2.0, 'bl' if up else 'tl', 'ОВ_марки')
    q.t(-0.18, W / 2, 'юг', 1.8, 'right', 'ОВ_текст')
    q.t(L + 0.18, W / 2, 'север', 1.8, 'left', 'ОВ_текст')
    sh.s.text(title, x0 + L * 50 / 2, y0 + W * 50 + 17, h=2.5, align='center')


def shaft1_inset(sh, x0, y0, title='Ш-1 в плане (2 этаж). М 1:20'):
    q = DPlan(sh.doc, k=1, space=sh.lay, unit=50.0, origin=(x0, y0))
    L = SH1[2] - SH1[0]
    W = SH1[3] - SH1[1]
    q.rect(0, 0, L, W, 'ОВ_шахты', lw=35)
    q.rect(-0.10, -0.10, L + 0.10, W + 0.10, 'ОВ_шахты', lw=50)
    items = [(RIS_P, 200, 'П Ø200', 'П'), (RIS_V, 200, 'В Ø200', 'В'), (RIS_P27, 100, 'П Ø100 (2.7)', 'П')]
    ups = [True, False, True]
    for ((x, y), d, n, kind), up in zip(items, ups):
        cx, cy = x - SH1[0], y - SH1[1]
        q.circle(cx, cy, d / 2000.0, DUCT_LAYER[kind], lw=35)
        ty = (W + 0.12) if up else -0.20
        q.pl([(cx, cy + (d / 2000.0 if up else -d / 2000.0)), (cx, ty)], 'ОВ_выноски')
        q.t(cx - 0.04, ty + (0.02 if up else -0.02), n, 2.0, 'bl' if up else 'tl', 'ОВ_марки')
    fx, fy = RIS_F[0] - SH1[0], RIS_F[1] - SH1[1]
    q.circle(fx - 0.03, fy, 0.012, 'ОВ_Фреон')
    q.circle(fx + 0.03, fy, 0.020, 'ОВ_Фреон')
    q.pl([(fx, fy - 0.03), (fx + 0.12, -0.20)], 'ОВ_выноски')
    q.t(fx + 0.12, -0.22, 'фреон', 2.0, 'tc', 'ОВ_марки')
    sh.s.text(title, x0 + L * 50 / 2, y0 + W * 50 + 13, h=2.5, align='center')


def legend(sh, x, y, items, w=120, h=2.0, title='Условные обозначения'):
    """items: (функция(p, x, y) рисования символа в мм листа, подпись). Возвращает y низа."""
    sh.s.text(title, x + w / 2, y, h=3.0, align='center')
    p = sh.p
    yy = y - 6
    for fn, cap in items:
        fn(p, x + 1, yy)
        lines = max(1, math.ceil(len(cap) * h * 0.56 / (w - 20)))
        sh.s.mtext(cap, x + 19, yy + 1.2, w - 20, h=h, attach=1)
        yy -= max(5.0, lines * h * 1.55 + 1.6)
    return yy


def L_duct(kind):
    def f(p, x, y):
        p.duct([(x, y), (x + 14, y)], 2000, kind)
    return f


def L_grille(kind):
    def f(p, x, y):
        a = 2.0
        lay = DUCT_LAYER[kind]
        p.rect(x + 5, y - a, x + 9, y + a, lay)
        p.line(x + 5, y - a, x + 9, y + a, lay)
        p.line(x + 5, y + a, x + 9, y - a, lay)
    return f


def L_wgrille(kind):
    def f(p, x, y):
        lay = DUCT_LAYER[kind]
        p.rect(x + 3, y - 0.6, x + 11, y + 0.6, lay, fill=LAYERS[lay][0])
    return f


def L_slot(kind):
    def f(p, x, y):
        lay = DUCT_LAYER[kind]
        p.rect(x + 1, y - 0.5, x + 13, y + 0.5, lay, fill=LAYERS[lay][0])
        for xx in (3.5, 7, 10.5):
            p.arrow(x + xx, y + 0.5, x + xx, y + 3.0, lay, size=1.2)
    return f


def L_ku(p, x, y):
    p.rect(x + 2, y - 2, x + 12, y + 2, 'ОВ_Фреон')
    p.rect(x + 2.5, y - 1.5, x + 11.5, y + 1.5, 'ОВ_Фреон')
    p.t(x + 7, y, 'К', 2.0, 'center', 'ОВ_Фреон')


def L_freon(p, x, y):
    p.pl([(x, y), (x + 14, y)], 'ОВ_Фреон', ltype='ОВ_ШП', lw=35)


def L_drain(p, x, y):
    p.pl([(x, y), (x + 14, y)], 'ОВ_Дренаж', ltype='ОВ_ПУНКТ')


def L_shaft(p, x, y):
    p.shaft(x + 4, y - 2, x + 10, y + 2)


def L_riser(kind, d=4.0):
    def f(p, x, y):
        lay = DUCT_LAYER[kind] if kind in DUCT_LAYER else kind
        p.circle(x + 7, y, d / 2, lay)
        p.line(x + 7 - 1.4, y - 1.4, x + 7 + 1.4, y + 1.4, lay)
    return f


def L_zone(p, x, y):
    p.poly([(x, y - 2), (x + 14, y - 2), (x + 14, y + 2), (x, y + 2)], 'ОВ_зоны',
           hatch=('ANSI31', 60.0, 45, 5), ltype='ОВ_ШТРИХ')


def L_ahu(p, x, y):
    p.rect(x + 1, y - 2, x + 13, y + 2, 'ОВ_оборуд', lw=35)
    p.t(x + 7, y, 'П1', 2.0, 'center', 'ОВ_оборуд')


def ahu(p, box, name='П1'):
    x0, y0, x1, y1 = box
    p.rect(x0, y0, x1, y1, 'ОВ_оборуд', lw=50)
    p.line(x0 + 0.35, y0, x0 + 0.35, y1, 'ОВ_оборуд', lw=18)
    p.line(x1 - 0.35, y0, x1 - 0.35, y1, 'ОВ_оборуд', lw=18)
    p.line(x0 + 0.35, y0, x1 - 0.35, y1, 'ОВ_оборуд', lw=18)
    p.line(x0 + 0.35, y1, x1 - 0.35, y0, 'ОВ_оборуд', lw=18)
    p.t((x0 + x1) / 2, (y0 + y1) / 2 + 0.17, name, 2.2, 'center', 'ОВ_оборуд')


def mask(p, x0, y0, x1, y1):
    """Белая заливка (закрывает подложку АР под нашим чертежом)."""
    h = p.m.add_hatch(dxfattribs={'layer': 'ОВ_шахты'})
    h.set_solid_fill(color=7, rgb=(255, 255, 255))
    h.paths.add_polyline_path([p.P(x0, y0), p.P(x1, y0), p.P(x1, y1), p.P(x0, y1)], is_closed=True)


def save_sheet(doc, name):
    """DXF — как есть (Ø для AutoCAD); PDF — с копии, где Ø заменён на ⌀ (у ISOCPEUR в matplotlib Ø заливается)."""
    import subprocess
    from rdbase import save
    path = os.path.join(OUT, name + '.dxf')
    save(doc, path)
    raw = open(path, 'rb').read().replace('ё'.encode(), 'е'.encode()).replace('Ё'.encode(), 'Е'.encode())
    raw = raw.replace('…'.encode(), '...'.encode())
    open(path, 'wb').write(raw)
    tmp = os.path.join(OUT, '_' + name + '_print.dxf')
    open(tmp, 'wb').write(raw.replace('Ø'.encode(), '⌀'.encode()))
    pdf = os.path.join(OUT, name + '_Лист.pdf')
    subprocess.run([sys.executable, os.path.join(ROOT, 'render_layout.py'), tmp, pdf, 'Лист'], check=True,
                   capture_output=True)
    os.remove(tmp)
    return [path, pdf]


def kw1(w):
    return fmt_num(w / 1000, 1)


# ---------------------------------------------------------------- лист 9
def build():
    doc = new_doc()
    blk = add_underlay(doc, UNDER['plan1'], 'АР_План_1_этажа')
    insert_underlay(doc.modelspace(), blk)
    p = DPlan(doc, k=100)
    axes(p, y_bub=-2.4, x_bub=-2.4)

    # зоны подшивки
    ZPOS = {'П-1': (7.95, 7.40), 'П-2': (10.05, 9.45), 'П-3': (12.80, 10.72), 'П-4': (0.30, 5.97),
            'П-5': (9.80, 0.50)}
    for pts, lab, dep, low, what in ZONES1:
        zone(p, pts, lab, dep, low, *ZPOS[lab])

    # проекция Ш-1 (шахта — со 2 этажа) и стояки в ней
    x0, y0, x1, y1 = SH1
    p.rect(x0, y0, x1, y1, 'ОВ_шахты', ltype='ОВ_ШТРИХ')
    riser(p, RIS_P, 'П', 200)
    riser(p, RIS_V, 'В', 200)
    riser(p, RIS_P27, 'П', 100)
    p.circle(RIS_F[0], RIS_F[1], 0.05, 'ОВ_Фреон')
    # Ш-2 с каналами (подложка внутри шахты закрыта — каналы по заданию ОВ)
    mask(p, *SH2)
    p.shaft(*SH2)
    p.rect(SH2_X - 0.20, SH2_SQ[0], SH2_X + 0.20, SH2_SQ[1], 'ОВ_шахты', lw=25)
    for yc, d, n in SH2_CH:
        p.circle(SH2_X, yc, d / 2000.0, 'ОВ_шахты', lw=25)

    # П1 под потолком топочной
    ahu(p, (16.90, 9.35, 18.50, 10.15))
    draw_net(p, NET1, labels={
        'П1-A': (1, 0.45, None), 'A-B': (-1, 0.5, 1), '1.2': (-1, 0.55, 0), 'B-E': (-1, 0.5, None),
        'E-F': (-1, 0.5, None), 'F-G': (-1, 0.55, None), 'G-H': (-1, 0.55, None),
        '1.11': (1, 0.55, 0), 'A-П1': (-1, 0.7, None), '1.8': (-1, 0.62, None), 'B-A': (-1, 0.5, None),
        'С-B': (1, 0.5, 0), 'кухня': (1, 0.5, 2), 'D-С': (1, 0.5, None), 'E-D': (1, 0.4, None),
        'Н': (1, 0.55, 1), 'Выброс': (1, 0.5, 2),
    }, skip_labels=('гр.1.10-в', 'гр.1.10-с', 'гр.1.10-з', 'стояк П', 'стояк П2.7', 'стояк В', '1.4', '1.3',
                    '1.11-з'))
    p.t(1.6, 5.70, 'Ø100', 1.8, 'center', 'ОВ_П')

    # решётки
    for gx, gy, kind, L, dr, nm, wall in GRILLES1:
        if wall and dr == 'up' and kind == 'П' and abs(gy - 7.75) < 0.01:
            slot_diff(p, gx - 0.30, gx + 0.30, 7.86, 'П', 'up')
            p.t(gx, 8.40, f'L={L}', 1.9, 'center', 'ОВ_П')
        elif wall:
            wall_grille(p, gx, gy, kind, L, dr)
        else:
            ceil_grille(p, gx, gy, kind, L, txt=(0.0, -0.36), al='center')
    # воздухозабор П1 и вытяжка топочной
    wall_grille(p, 19.93, 11.10, 'Н', 700, 'left', name='Н1', txt_off=(-1.25, 0.30))
    p.label(19.70, 7.15, 'Н1 — воздухозабор П1: решётка 500×400, низ +2,600', 1.9, anchor='right',
            at=(19.93, 11.10))
    wall_grille(p, 15.66, SH2_CH[1][0], 'В', BRV['L_exh'], 'right', name='В2', txt_off=(0.25, 0.25))
    p.label(12.6, 16.25, 'Ш-2: дымоходы Дг, Дп, выброс П1, вытяжка В2 — врезка, задание АР', 1.9,
            at=(15.36, 13.40))
    p.label(12.6, 15.55, f'В2 — вытяжка топочной {BRV["L_exh"]} м³/ч, естественная, Ø250', 1.9,
            at=(15.70, SH2_CH[1][0]))
    p.label(12.6, 14.85, 'Выброс П1 Ø250 — в Ш-2, оголовок выше кровли', 1.9, at=(15.62, SH2_CH[0][0]))
    # приток в топочную (естественный) — решётка внизу наружной двери
    wall_grille(p, 20.08, 10.02, 'Н', BRV['L_in'], 'left', name='ПН', txt_off=(0.30, -0.55))

    # кухня: зонт ВЗ, выброс через стену по оси Д, клапан компенсации КК
    p.rect(8.88, 11.85, 9.40, 12.40, 'ОВ_оборуд')
    p.t(9.14, 12.12, 'ВЗ', 1.8, 'center', 'ОВ_оборуд')
    p.duct([(9.14, 12.40), (9.14, 13.80)], 150, 'В')
    wall_grille(p, 9.14, 13.92, 'В', '500–600', 'up', name='ВЗ', txt_off=(-2.35, 0.32))
    p.label(2.0, 15.3, 'ВЗ — зонт над плитой, выброс через стену (прим. 4)', 1.9, at=(9.14, 13.2))
    p.rect(7.90, 13.70, 8.50, 13.95, 'ОВ_Н')
    p.t(8.2, 13.825, 'КК', 1.5, 'center', 'ОВ_Н')
    p.label(2.0, 14.6, 'КК Ø200 — клапан компенсации (прим. 4)', 1.9, at=(8.2, 13.95))

    # гараж — естественная вентиляция
    wall_grille(p, 20.05, 1.85, 'Н', None, 'left', name='Пр. ест.', txt_off=(-1.75, 0.32))
    wall_grille(p, 20.05, 8.20, 'В', None, 'right', name='Выт. ест.', txt_off=(-2.0, 0.30))

    # кондиционирование
    for n, box in KU1.items():
        ku(p, n, box)
    slot_diff(p, 1.70, 2.70, 7.86, 'Р', 'up')
    slot_diff(p, 5.40, 6.40, 7.86, 'Р', 'up')
    slot_diff(p, 3.40, 4.50, 5.05, 'Р', 'down')
    for (gx, gy) in ((2.20, 6.98), (5.90, 6.98), (4.85, 5.75)):
        q = 0.15
        p.rect(gx - q, gy - q, gx + q, gy + q, 'ОВ_Рец')
        p.line(gx - q, gy - q, gx + q, gy + q, 'ОВ_Рец')
        p.line(gx - q, gy + q, gx + q, gy - q, 'ОВ_Рец')
    freon(p, FREON_IN)
    freon(p, FREON1)
    freon(p, FREON1_RISER)
    for br in FREON1_BR:
        freon(p, br)
    drain(p, DRAIN1)
    for br in DRAIN1_BR:
        drain(p, br)
    # НБ-1 снаружи у восточной стены топочной
    p.rect(20.50, 13.10, 20.95, 14.10, 'ОВ_Фреон', lw=50)
    p.t(20.725, 13.6, 'НБ-1', 1.8, 'center', 'ОВ_Фреон', rot=90)
    p.label(21.5, 14.75, 'НБ-1 — Daikin мини-VRV 22,4 кВт', 1.9, anchor='right', at=(20.95, 13.90),
            lines='на площадке, выдув от стены')

    # марки блоков и П1
    p.label(2.9, 9.05, 'К-1, К-2 — Daikin FXDQ, 5,6 кВт', 1.9, at=(2.20, 7.80))
    p.pl([(2.9, 9.05), (5.90, 7.80)], 'ОВ_выноски')
    p.dot(5.90, 7.80)
    p.label(0.4, 4.30, 'К-3 — Daikin FXDQ, 3,6 кВт', 1.9, at=(3.95, 5.60))
    p.label(13.2, 8.40, 'П1 — ПВУ с рекуперацией 700 м³/ч, низ +2,900', 1.9, at=(17.70, 9.40))
    p.label(12.40, 11.25, 'Ш-1 (2 этаж): стояки П, В Ø200, П Ø100, фреон', 1.8, anchor='right', at=(13.30, 9.30))
    p.label(12.9, 5.25, 'Дренаж блоков К — в сифон 1.4 (ВК)', 1.8, at=(12.20, 5.80))

    # ярлыки помещений: номер, приток/вытяжка
    def tg(x, y, lines, anchor=None):
        p.tag(x, y, lines, anchor=anchor, h=2.0)

    tg(0.5, 12.6, ['1.10  П 210 / В 210', 'вытяжка: кухня 90,', 'верх 2-го света 120 (л.10)', 'К-1, К-2'])
    tg(0.5, 3.40, ['1.11  П 120', 'К-3'])
    tg(6.4, 4.4, ['1.2  П 30'])
    tg(9.85, 1.20, ['1.3  В 40'], anchor=None)
    tg(9.85, 4.30, ['1.4  В 50'])
    tg(13.0, 13.4, ['1.8  В 30'])
    tg(16.05, 11.75, ['1.6  топочная', f'ест.: П {BRV["L_in"]} / В {BRV["L_exh"]}'])
    tg(14.2, 4.6, ['1.5  ест. вентиляция'])

    # ---------------------------------------------------------------- лист
    sh = RDSheet(doc, 'Лист', SHEET_LIST[SHEET_NO], SHEET_NO, SHEETS_TOTAL)
    sh.viewport(152, 177, 258, 222, 9.4, 7.2, k=100)
    sh.title(152, 289.5, 'План 1 этажа. Вентиляция и кондиционирование. М 1:100')
    yb = legend(sh, 292, 290, [
        (L_ahu, 'П1 — приточно-вытяжная установка с рекуперацией'),
        (L_duct('П'), 'Приточный воздуховод П1 (Ø, L — м³/ч)'),
        (L_duct('В'), 'Вытяжной воздуховод к П1'),
        (L_duct('Н'), 'Наружный воздух к П1'),
        (L_duct('X'), 'Выброс от П1 в шахту Ш-2'),
        (L_wgrille('П'), 'Решётка в стене, щелевой диффузор в торце подшивки'),
        (L_grille('В'), 'Потолочная решётка (вытяжка)'),
        (L_grille('Р'), 'Решётка рециркуляции блока К'),
        (L_slot('Р'), 'Щелевой диффузор блока К'),
        (L_ku, 'Внутренний канальный блок мини-VRV'),
        (L_freon, 'Фреонопроводы (жидкость + газ)'),
        (L_drain, 'Дренаж конденсата'),
        (L_riser('П'), 'Стояк воздуховода в Ш-1'),
        (L_shaft, 'Шахта'),
        (L_zone, 'Зона подшивки потолка'),
    ], w=122)
    rows = [['Зона', 'Глуб., мм', 'Низ', 'Что проходит']]
    for pts, lab, dep, low, what in ZONES1:
        rows.append([lab, str(dep), low, what])
    yt = sh.table(292, yb - 1, [11, 12, 15, 84], rows, row_h=7.4, head_h=5.5, h=1.8,
                  aligns=['center', 'center', 'center', 'left'])
    sh.s.text('Зоны подшивки потолков 1 этажа', 292 + 61, yb + 1.6, h=2.2, align='center')
    sh.notes(292, yt - 4, 122, [
        'Подложка — АР03 (выгрузка из Revit 19.10.2026). Отметки — от ±0,000; низ плиты перекрытия +3,650 '
        '(подтверждено Заказчиком). Подшивка — не ниже верха окон; к блокам К и клапанам — люки 600×600.',
        'П1 — 700 м³/ч (630 в сеть), под потолком топочной; воздухозабор — решётка в восточной стене между '
        'дверью и окном, выброс — канал Ø250 в Ш-2 выше кровли. Воздуховоды — круглые оцинкованные; '
        'Н и выброс — в теплоизоляции 25 мм с паробарьером; на ответвлениях — регуляторы расхода, у П1 — '
        'шумоглушители. Расчёт сети — лист 11.',
        'Подшивка П-3 углублена до 450 мм, П-2 — до 400 мм: магистрали П и В у Ш-1 пересекаются '
        '(обход по высоте).',
        'Кухня (ответ Заказчика): зонт ВЗ только над плитой, 500–600 м³/ч, Ø150 в коробе над шкафами к '
        'стене по оси Д; выброс — через стену выше кровли террасы 1.12, с обратным клапаном и решёткой '
        '(место — с АР). Компенсация — КК Ø200 с электроприводом, сблокирован с зонтом.',
        f'Топочная: вытяжка В2 — {BRV["L_exh"]} м³/ч (3 обмена) естественной тягой каналом Ø250 в Ш-2 '
        f'(Ø160 по ЭП не проходит: потери {fmt_num(BRV["natural"]["160"]["dp"], 1)} Па при располагаемых '
        f'{fmt_num(BRV["dP_nat"], 1)} Па); приток ПН — решётка, живое сечение '
        f'не менее {fmt_num(BRV["A_in_free"], 2)} м² в низу наружной двери ({BRV["L_in"]} м³/ч вместе с '
        f'воздухом на горение).',
        'Ш-2 (врезка, согласовано с листами 7, 8): с юга на север — выброс П1 Ø250 в канале 400×400 АР, '
        'вытяжка топочной В2 Ø250 (решётка под потолком в западной стене топочной), общий каскадный '
        'дымоход газовых котлов Ø125 вместо двух (по паспорту котлов), дымоход пеллетного котла Ø200/280 — '
        'задание АР; стенки шахты — негорючие.',
        'Кондиционирование — мини-VRV Daikin (серия VRV-S): НБ-1 22,4 кВт на площадке у восточной стены '
        'топочной (решение Заказчика), внутренние блоки — тонкие канальные серии FXDQ (типоразмер — по '
        'каталогу Daikin или аналог). Фреон — медь в изоляции; дренаж — в канализацию через сифон с сухим '
        'затвором (ВК), уклон не менее 0,01, иначе — помпа.',
        'Гараж 1.5 — естественная вентиляция: решётки 400×200 в восточной стене, приток внизу у ворот, '
        'вытяжка вверху у северного угла.',
    ], h=1.9)
    shaft2_inset(sh, 34, 25)
    shaft1_inset(sh, 140, 28)
    return doc


if __name__ == '__main__':
    doc = build()
    print(save_sheet(doc, 'ov_vent1'))
