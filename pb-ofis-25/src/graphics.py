"""Графическая часть ПБ-25.
Берёт исходный DXF раздела (из folder/ОПР-01_24_2026-ПБ-25.zip), оставляет листы 44–48, вносит изменения
по замечаниям и чертит новые листы 48.1 (конференц-зал) и 48.2 (серверная, АУГПТ).
Запуск: python3 graphics.py <pb25.dxf> <первый лист ГЧ в томе> <листов в томе>
Выход: out/ПБ-25-ГЧ.dxf (упаковывается в zip) и out/gch/<лист>.pdf."""
import math, os, sys
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA
import calc
from tables import EXT, ZKPS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out')

# лист: (x0, y0 листа в пространстве модели; ширина, высота бумаги, мм)
SHEETS = {'44': (13356, 0, 1189, 841), '45': (14587, 0, 594, 420), '46': (15223, 0, 420, 297),
          '47': (15685, 0, 420, 297), '48': (16147, 0, 420, 297),
          '48.1': (16609, 0, 420, 297), '48.2': (17071, 0, 420, 297)}
ORDER = ['44', '45', '46', '47', '48', '48.1', '48.2']
F1 = (16267.93, 81.02, 5.94375)      # план 1-го этажа на листе 48: ось 1, ось А, мм на 1 м
F2 = (15807.03, 83.8, 5.8695)        # план 2-го этажа на листе 47

RED, GREEN, BLUE, BLACK, GREY = 1, 3, 5, 7, 8
LAY = 'ПБ_ИЗМ'


def P(F, x, y):
    return F[0] + F[2] * x, F[1] + F[2] * y


# ───────────────────────── примитивы ─────────────────────────
class Draw:
    def __init__(self, msp, layer=LAY):
        self.m, self.layer = msp, layer

    def a(self, color, lw=None, **kw):
        d = {'layer': self.layer, 'color': color}
        if lw is not None:
            d['lineweight'] = lw
        d.update(kw)
        return d

    def line(self, p, q, color=BLACK, lw=None):
        return self.m.add_line(p, q, dxfattribs=self.a(color, lw))

    def pl(self, pts, color=BLACK, close=False, lw=None):
        return self.m.add_lwpolyline(pts, close=close, dxfattribs=self.a(color, lw))

    def rect(self, x0, y0, x1, y1, color=BLACK, lw=None):
        return self.pl([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], color, True, lw)

    def fill(self, pts, color=RED, rgb=None):
        h = self.m.add_hatch(color=color, dxfattribs={'layer': self.layer})
        if rgb is not None:
            h.rgb = rgb
        h.paths.add_polyline_path(pts, is_closed=True)
        return h

    def pattern(self, pts, name='ANSI31', scale=0.5, color=RED, angle=0):
        h = self.m.add_hatch(color=color, dxfattribs={'layer': self.layer})
        h.set_pattern_fill(name, scale=scale, angle=angle)
        h.paths.add_polyline_path(pts, is_closed=True)
        return h

    def mask(self, pts):
        """Маскировка (WIPEOUT): закрывает подоснову фоном — для проёмов в существующих стенах."""
        return self.m.add_wipeout(pts, dxfattribs={'layer': self.layer})

    def circle(self, c, r, color=BLACK, lw=None):
        return self.m.add_circle(c, r, dxfattribs=self.a(color, lw))

    def arc(self, c, r, a0, a1, color=BLACK):
        return self.m.add_arc(c, r, a0, a1, dxfattribs=self.a(color))

    def text(self, x, y, s, h=2.5, align='L', color=BLACK, rot=0):
        al = {'L': TA.LEFT, 'C': TA.CENTER, 'R': TA.RIGHT, 'ML': TA.MIDDLE_LEFT, 'MC': TA.MIDDLE_CENTER,
              'MR': TA.MIDDLE_RIGHT, 'TL': TA.TOP_LEFT, 'TC': TA.TOP_CENTER}[align]
        t = self.m.add_text(s, height=h, rotation=rot, dxfattribs={'layer': self.layer, 'color': color, 'style': 'GOST'})
        t.set_placement((x, y), align=al)
        return t

    def arrow(self, p, q, color=GREEN, size=1.6):
        self.line(p, q, color)
        ang = math.atan2(q[1] - p[1], q[0] - p[0])
        for s in (1, -1):
            a = ang + math.pi - s * 0.4
            self.line(q, (q[0] + size * math.cos(a), q[1] + size * math.sin(a)), color)

    def dim(self, p, q, off, label, h=2.5, color=BLACK):
        """Размер с засечками: p, q – концы, off – смещение размерной линии по нормали."""
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy); nx, ny = -dy / L, dx / L
        a = (p[0] + nx * off, p[1] + ny * off); b = (q[0] + nx * off, q[1] + ny * off)
        self.line(p, (a[0] + nx * 1.5 * math.copysign(1, off), a[1] + ny * 1.5 * math.copysign(1, off)), color)
        self.line(q, (b[0] + nx * 1.5 * math.copysign(1, off), b[1] + ny * 1.5 * math.copysign(1, off)), color)
        self.line((a[0] - dx / L * 1.5, a[1] - dy / L * 1.5), (b[0] + dx / L * 1.5, b[1] + dy / L * 1.5), color)
        for c in (a, b):
            self.line((c[0] - 0.9, c[1] - 0.9), (c[0] + 0.9, c[1] + 0.9), color)
        rot = math.degrees(math.atan2(dy, dx))
        if rot > 90 or rot < -90:
            rot += 180
        mx, my = (a[0] + b[0]) / 2 + nx * 0.8, (a[1] + b[1]) / 2 + ny * 0.8
        self.text(mx, my, label, h, 'C', color, rot)


def extinguisher(d, x, y, kind, label, side, s=3.0):
    """Знак F04: красный квадрат с белым силуэтом огнетушителя; подпись – обозначение по табл. 12.1."""
    h = s / 2
    d.fill([(x - h, y - h), (x + h, y - h), (x + h, y + h), (x - h, y + h)], RED)
    white = 0xFFFFFF
    d.fill([(x - 0.35 * h, y - 0.7 * h), (x + 0.25 * h, y - 0.7 * h), (x + 0.25 * h, y + 0.35 * h),
            (x - 0.35 * h, y + 0.35 * h)], 255)
    d.fill([(x - 0.2 * h, y + 0.35 * h), (x + 0.1 * h, y + 0.35 * h), (x + 0.1 * h, y + 0.6 * h),
            (x - 0.2 * h, y + 0.6 * h)], 255)
    d.fill([(x + 0.1 * h, y + 0.5 * h), (x + 0.65 * h, y + 0.62 * h), (x + 0.65 * h, y + 0.45 * h),
            (x + 0.1 * h, y + 0.4 * h)], 255)
    off = h + 0.8
    pos = {'n': (x, y + off, 'C'), 's': (x, y - off - 2.0, 'C'), 'e': (x + off, y - 1.0, 'L'), 'w': (x - off, y - 1.0, 'R')}[side]
    d.text(pos[0], pos[1], f'{label} {kind}', 2.0, pos[2], RED)


# ───────────────────────── правка исходных сущностей ─────────────────────────
def pts_of(e):
    t = e.dxftype()
    if t == 'LINE':
        return [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
    if t == 'LWPOLYLINE':
        return [(p[0], p[1]) for p in e.get_points()]
    if t in ('TEXT', 'MTEXT'):
        return [(e.dxf.insert.x, e.dxf.insert.y)]
    if t in ('CIRCLE', 'ARC'):
        return [(e.dxf.center.x, e.dxf.center.y)]
    if t == 'WIPEOUT':
        return [(v.x, v.y) for v in e.boundary_path_wcs()]
    if t == 'HATCH':
        out = []
        for path in e.paths:
            if hasattr(path, 'vertices'):
                out += [(v[0], v[1]) for v in path.vertices]
        return out
    return []


class Index:
    """Грубый индекс по ячейкам 10 мм, чтобы не перебирать миллион сущностей на каждую правку."""
    def __init__(self, msp):
        self.cells = {}
        for e in msp:
            p = pts_of(e)
            if not p:
                continue
            for c in {(int(x // 10), int(y // 10)) for x, y in p}:
                self.cells.setdefault(c, []).append(e)

    def box(self, x0, y0, x1, y1):
        seen, out = set(), []
        for i in range(int(x0 // 10) - 1, int(x1 // 10) + 2):
            for j in range(int(y0 // 10) - 1, int(y1 // 10) + 2):
                for e in self.cells.get((i, j), []):
                    if id(e) not in seen and e.is_alive:
                        seen.add(id(e)); out.append(e)
        return out


def erase_inside(msp, idx, x0, y0, x1, y1, test=lambda e: True):
    n = 0
    for e in idx.box(x0, y0, x1, y1):
        p = pts_of(e)
        if p and all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in p) and test(e):
            msp.delete_entity(e); n += 1
    return n


def set_stamp(msp, idx, sheet, num, total):
    """Номер листа и общее число листов в основной надписи исходного листа."""
    ox, oy, W, H = SHEETS[sheet]
    xr = ox + W - 5
    for e in idx.box(xr - 50, oy + 14, xr, oy + 22):
        if e.dxftype() != 'TEXT' or not (oy + 15 <= e.dxf.insert.y <= oy + 18):
            continue
        x = e.dxf.insert.x
        if xr - 30 <= x <= xr - 15:
            e.dxf.text = f'{num:02d}'
        elif xr - 15 < x <= xr:
            e.dxf.text = str(total)


# ───────────────────────── лист 45: структурная схема СПС ─────────────────────────
def det(d, x, y, label, below=False):
    s = 5.4
    d.rect(x - s / 2, y - s / 2, x + s / 2, y + s / 2, RED)
    d.line((x - s / 2, y - s / 2), (x + s / 2, y + s / 2), 2)
    d.pl([(x - 0.4, y - 1.8), (x + 0.6, y - 0.4), (x - 0.6, y + 0.4), (x + 0.4, y + 1.8)], RED)
    d.text(x, y - s / 2 - 4.0 if below else y + s / 2 + 1.2, label, 2.5, 'C')


def sheet45(d):
    # 1-й этаж, обратная ветвь шлейфа ПС1.1 (y = 136.3): ИП 1.58–1.61, 1.64–1.67
    y = 136.3
    labels = ['1.58', '1.59', '1.60', '1.61', '1.64', '1.65', '1.66', '1.67']
    for k, lab in enumerate(labels):
        det(d, 14945 + k * 22.0, y, lab)
    # 2-й этаж, третий ряд после 2.69 (y ≈ 311.45)
    for k, lab in enumerate(['2.70', '2.71', '2.72', '2.73']):
        det(d, 15119.5 + k * 8.6, 311.45, lab, below=True)
    # серверная: ИП 1.62, 1.63 левее 1.36 на той же линии
    for k, lab in enumerate(['1.63', '1.62']):
        det(d, 14662.0 + k * 10.0, 284.6, lab)
    d.line((14664.7, 284.6), (14669.3, 284.6), RED); d.line((14674.7, 284.6), (14683.3, 284.6), RED)
    # ВРУ: ЗКПС, МПП-n, НР-n
    for k, (x0, x1) in enumerate(((14640.4, 14671.9), (14673.8, 14704.9), (14707.1, 14738.2), (14739.9, 14771.0))):
        n = k + 1
        d.text((x0 + x1) / 2 + 3.4, 381.6, f'-{n}', 3.5, 'L')
        d.text((x0 + x1) / 2, 371.0, f'ЗКПС {16 + n}', 2.5, 'C', RED)
    for k, x in enumerate((14642.1, 14673.8, 14704.9, 14743.4)):
        d.text(x + 14.5, 345.2, f'(НР-{k + 1})', 2.5, 'L')
    # примечания
    x, y = 14995, 118
    notes = ['Примечания',
             '1. ЗКПС и состав извещателей – по таблице 11.1 текстовой части; матрица управления – по таблице 11.2.',
             '2. ВРУ: в каждом шкафу ЩР-1...ЩР-4 – два ИП (3.1...3.8), модуль МПП-1...МПП-4 и независимый',
             '   расцепитель НР-1...НР-4 вводного автомата; помещение ВРУ – ЗКПС 16 (ИП 1.61).',
             '3. Серверная – ЗКПС 8: ИП 1.35, 1.36, 1.62, 1.63 (алгоритм С), С2000-АСПТ, см. лист 48.2.',
             '4. Управление ДУ1, ДУ2, КП1, ПД1, ПД2 и клапанами – блоки С2000-СП2 по матрице (табл. 11.2).']
    for k, s in enumerate(notes):
        d.text(x, y - k * 5.0, s, 2.5 if k else 3.5, 'L')


# ───────────────────────── листы 47, 48: планы ─────────────────────────
EXT_POS = {
    'О1-1': (6.5, 11.5, 'n'), 'О1-2': (8.3, 22.6, 'e'), 'О1-3': (22.2, 23.7, 's'), 'О1-4': (8.3, 7.6, 'e'),
    'О1-5': (22.2, 6.6, 'n'), 'О1-6': (27.0, 7.75, 's'), 'О1-7': (29.6, 20.15, 'n'), 'О1-8': (23.75, 12.8, 'e'),
    'О1-9': (31.0, 6.55, 'w'), 'О1-10': (38.2, 1.3, 'n'),
    'О2-1': (8.15, 20.5, 'e'), 'О2-2': (20.8, 23.75, 's'), 'О2-3': (8.15, 9.0, 'e'), 'О2-4': (20.8, 6.35, 'n'),
    'О2-5': (13.0, 21.5, 's'), 'О2-6': (25.3, 12.2, 'e'), 'О2-7': (31.5, 20.3, 's'), 'О2-8': (27.6, 8.75, 'n'),
    'О2-9': (35.0, 10.7, 'n'),
}


def fire_wall(d, F, y0, y1):
    x0, x1 = 40.15, 40.32
    pts = [P(F, x0, y0), P(F, x1, y0), P(F, x1, y1), P(F, x0, y1)]
    d.fill(pts, RED)
    xa, ya = P(F, 40.9, 15.0)
    d.text(xa + 4.0, ya, 'Противопожарная стена 1-го типа REI 150 (граница со складом №26)', 2.5, 'MC', RED, 90)


def legend(d, x, y, floor):
    d.text(x, y, 'Условные обозначения', 3.5, 'L')
    y -= 6
    extinguisher(d, x + 2, y + 1, '', '', 'e')
    d.text(x + 6, y, 'огнетушитель (знак F04 по ГОСТ 12.4.026-2015); О1-1 – номер по табл. 12.1 ТЧ', 2.5)
    y -= 5
    d.fill([(x, y - 0.5), (x + 4, y - 0.5), (x + 4, y + 2), (x, y + 2)], RED)
    d.text(x + 6, y, 'противопожарная стена 1-го типа REI 150 по оси 6', 2.5)
    y -= 5
    d.arrow((x, y + 0.8), (x + 4, y + 0.8))
    d.text(x + 6, y, 'направление эвакуации', 2.5)
    if floor == 2:
        y -= 5
        d.rect(x, y - 0.5, x + 4, y + 2, BLUE)
        d.pattern([(x, y - 0.5), (x + 4, y - 0.5), (x + 4, y + 2), (x, y + 2)], 'ANSI37', 0.25, BLUE)
        d.text(x + 6, y, 'пожаробезопасная зона для МГН (п. 6.3 ТЧ)', 2.5)
    y -= 6
    for s in (['Пожарные краны и шкафы не устанавливаются: ВПВ не требуется (п. 10.6 ТЧ).'] +
              (['Д1, Д2 – выходы конференц-зала, расстановка мест – лист 48.1; серверная – лист 48.2.'] if floor == 1 else [])):
        d.text(x, y, s, 2.5); y -= 4.5


def plan48(msp, idx, d, seats_draw):
    F = F1
    # конференц-зал: убрать расстановку мебели АР, показать 200 мест по листу 48.1
    hx0, hy0, hx1, hy1 = P(F, 23.5, 10.3) + P(F, 40.1, 19.7)
    erase_inside(msp, idx, hx0, hy0, hx1, hy1, lambda e: e.dxf.color == 2)
    # кресла АР вдоль стен зала: полосы от граней стен (север 19,76, юг 10,25, запад 23,47) до края кресел
    for bx0, by0, bx1, by1 in ((24.0, 19.18, 38.45, 19.76), (24.0, 10.265, 38.45, 10.8), (23.495, 11.7, 24.05, 18.2)):
        erase_inside(msp, idx, *P(F, bx0, by0), *P(F, bx1, by1), lambda e: e.dxftype() != 'TEXT')
    seats_draw(d, lambda x, y: P(F, 23.47 + x, 10.25 + y), 1.0)
    # прежний выход Д1 в западной стене – заделать
    x0, y0 = P(F, 22.25, 18.25); x1, y1 = P(F, 23.42, 19.80)
    erase_inside(msp, idx, x0, y0, x1, y1)
    for xx in (23.37, 23.47):
        d.line(P(F, xx, 18.28), P(F, xx, 19.75))
    d.pattern([P(F, 23.37, 18.28), P(F, 23.47, 18.28), P(F, 23.47, 19.75), P(F, 23.37, 19.75)], 'ANSI37', 0.08, BLACK)
    # новый выход Д1 в северной стене: проём 30,87–32,07, открывание в коридор
    xa, ya = P(F, 30.87, 19.70); xb, yb = P(F, 32.07, 19.90)
    erase_inside(msp, idx, xa, ya, xb, yb)
    d.mask([P(F, 30.87, 19.72), P(F, 32.07, 19.72), P(F, 32.07, 19.88), P(F, 30.87, 19.88)])
    k = F[2]
    hinge = P(F, 30.87, 19.85)
    d.line(hinge, P(F, 30.87, 21.05))
    d.arc(hinge, 1.2 * k, 0, 90)
    d.line(P(F, 30.87, 19.75), P(F, 30.87, 19.85)); d.line(P(F, 32.07, 19.75), P(F, 32.07, 19.85))
    d.text(*P(F, 31.47, 19.0), 'Д1', 2.5, 'C', RED)
    d.text(*P(F, 24.0, 11.0), 'Д2', 2.5, 'L', RED)
    # дверь ВРУ: из зала – заделать, в коридор №28 – новая
    xa, ya = P(F, 28.45, 9.15); xb, yb = P(F, 29.62, 10.20)
    k = F[2]
    def door_part(e):            # створка (контур у x 28,53–28,57) и дуга открывания, без цифр номера помещения
        p = pts_of(e)
        if e.dxftype() == 'LWPOLYLINE':
            xs = [q[0] for q in p]; ys = [q[1] for q in p]
            if len(p) >= 6:
                return max(xs) - min(xs) > 0.6 * k and max(ys) - min(ys) > 0.6 * k
            return max(xs) - min(xs) < 0.1 * k and max(ys) - min(ys) > 0.6 * k
        if e.dxftype() == 'LINE':
            (a, b), (c, dd) = p
            return abs(a - c) < 0.02 and P(F, 28.48, 0)[0] <= a <= P(F, 28.62, 0)[0]
        return False
    erase_inside(msp, idx, xa, ya, xb, yb, door_part)
    for yy in (10.15, 10.25):
        d.line(P(F, 28.5, yy), P(F, 29.5, yy))
    d.pattern([P(F, 28.5, 10.15), P(F, 29.5, 10.15), P(F, 29.5, 10.25), P(F, 28.5, 10.25)], 'ANSI37', 0.08, BLACK)
    # перегородка 7,968–8,067: грани – заливкой, штриховка – отрезками; проём закрывается маской
    xa, ya = P(F, 28.6, 7.95); xb, yb = P(F, 29.5, 8.2)
    erase_inside(msp, idx, xa, ya, xb, yb)
    d.mask([P(F, 28.6, 7.955), P(F, 29.5, 7.955), P(F, 29.5, 8.08), P(F, 28.6, 8.08)])
    for xx in (28.6, 29.5):
        d.line(P(F, xx, 7.968), P(F, xx, 8.067))
    hinge = P(F, 28.6, 8.067)
    d.line(hinge, P(F, 28.6, 8.967)); d.arc(hinge, 0.9 * k, 0, 90)
    # противопожарная стена по оси 6
    fire_wall(d, F, -0.15, 30.15)
    for code, (x, y, side) in EXT_POS.items():
        if code.startswith('О1'):
            kind = next(e[2] for e in EXT if e[0] == code)
            extinguisher(d, *P(F, x, y), kind, code, side)
    legend(d, 16172, 36, 1)


def plan47(msp, idx, d):
    F = F2
    zone = [P(F, 31.9, 8.38), P(F, 37.68, 8.38), P(F, 37.68, 10.38), P(F, 31.9, 10.38)]
    d.pattern(zone, 'ANSI37', 1.2, BLUE)
    d.fill([P(F, 35.2, 9.78), P(F, 37.5, 9.78), P(F, 37.5, 10.28), P(F, 35.2, 10.28)], 255)   # правее номера помещения
    d.text(*P(F, 36.35, 10.03), 'ПБЗ №33', 2.0, 'MC', BLUE)
    fire_wall(d, F, -0.15, 30.15)
    for code, (x, y, side) in EXT_POS.items():
        if code.startswith('О2'):
            kind = next(e[2] for e in EXT if e[0] == code)
            extinguisher(d, *P(F, x, y), kind, code, side)
    legend(d, 15710, 36, 2)


# ───────────────────────── новые листы ─────────────────────────
def copy_frame(msp, idx, src, dst):
    """Рамка и основная надпись нового листа – копия с листа src, сдвинутая на место dst."""
    sx, sy, W, H = SHEETS[src]; dx = SHEETS[dst][0] - sx
    for e in idx.box(sx, sy, sx + W, sy + H):
        p = pts_of(e)
        if not p:
            continue
        frame = e.dxf.layer == '01_РАМКА'
        in_stamp = all(sx + W - 191 <= x <= sx + W + 1 and sy - 1 <= y <= sy + 42 for x, y in p)
        if frame or in_stamp:
            c = e.copy(); c.translate(dx, 0, 0); msp.add_entity(c)


TITLES = {'44': ['План внутриплощадочных', 'дорог'], '45': ['Структурная схема СПС,', 'АУГПТ и УПА ВРУ'],
          '46': ['Структурная схема', 'СОУЭ'], '47': ['План 2-го этажа.', 'Пути эвакуации,', 'огнетушители, зона МГН'],
          '48': ['План 1-го этажа.', 'Пути эвакуации,', 'огнетушители'],
          '48.1': ['Конференц-зал №36.', 'Схема расстановки мест'], '48.2': ['Серверная №31.', 'План АУГПТ']}


def retitle(msp, idx, sheet, lines):
    """Наименование листа в основной надписи вместо «Графический / лист NN»: строки по центру графы,
    высота шрифта – как у исходной надписи, но не шире графы (62 мм)."""
    ox, oy, W, H = SHEETS[sheet]
    texts = [e for e in idx.box(ox + W - 120, oy + 5, ox + W - 60, oy + 25)
             if e.dxftype() == 'TEXT' and ox + W - 120 <= e.dxf.insert.x <= ox + W - 60 and oy + 5 <= e.dxf.insert.y <= oy + 25]
    assert len(texts) == 2, (sheet, [e.dxf.text for e in texts])
    texts.sort(key=lambda e: -e.dxf.insert.y)
    y0, y1 = texts[0].dxf.insert.y, texts[1].dxf.insert.y
    h0 = texts[0].dxf.height
    attrs = {'layer': texts[0].dxf.layer, 'color': texts[0].dxf.color, 'style': texts[0].dxf.style}
    for e in texts:
        msp.delete_entity(e)
    cyc = (y0 + y1) / 2 + h0 / 2                     # середина графы (5–25 мм) по исходной надписи
    h = min(h0, 58.0 / (0.72 * max(len(s) for s in lines)), 4.0 if len(lines) > 2 else h0)
    step = (y0 - y1) if len(lines) == 2 and h == h0 else 1.5 * h
    cx = ox + W - 5 - (204.9 - 123.5)
    for k, s in enumerate(lines):
        y = cyc - h / 2 + step * ((len(lines) - 1) / 2 - k)
        assert oy + 5.5 <= y and y + h <= oy + 24.5, (sheet, s, y - oy, h)
        t = msp.add_text(s, height=h, dxfattribs=attrs)
        t.set_placement((cx, y), align=TA.CENTER)


def seats(d, T, k, labels=False):
    """Расстановка мест конференц-зала. T(x, y) – из координат зала (от ЮЗ угла, м) в координаты листа."""
    rows = calc.ROWS
    x_front = 14.4
    for i, n in enumerate(rows):
        x1 = x_front - 0.9 * i; x0 = x1 - 0.45
        if i < 12:
            ys = [1.0 + 0.5 * j for j in range(15)]
            if i == 6:
                ys = [y for j, y in enumerate(ys) if j not in (1, 13)]
        else:
            ys = [2.0 + 0.5 * j for j in range(11)]
        assert len(ys) == n
        for y in ys:
            d.rect(*T(x0, y + 0.03), *T(x1 - 0.02, y + 0.47), BLACK)
        if labels:
            d.text(*T((x0 + x1) / 2, 9.0), str(i + 1), 2.2, 'C')


def sheet481(msp, d):
    ox, oy, W, H = SHEETS['48.1']
    S = 20.0                                  # М 1:50 – 20 мм на 1 м
    bx, by = ox + 45, oy + 64                 # юго-западный внутренний угол зала на листе
    T = lambda x, y: (bx + S * x, by + S * y)
    L, B = 16.68, 9.50
    t = 0.1
    # стены
    d.rect(*T(-t, -t), *T(L + 0.17, B + t))
    d.rect(*T(0, 0), *T(L, B))
    d.fill([T(L, -t), T(L + 0.17, -t), T(L + 0.17, B + t), T(L, B + t)], RED)
    # проёмы и двери: Д1 (север), Д2 (запад)
    d.mask([T(7.4, B - 0.02), T(8.6, B - 0.02), T(8.6, B + t + 0.02), T(7.4, B + t + 0.02)])
    d.line(T(7.4, B + t), T(7.4, B + t + 1.2)); d.arc(T(7.4, B + t), 1.2 * S, 0, 90)
    d.mask([T(-t - 0.02, 0.15), T(0.02, 0.15), T(0.02, 1.35), T(-t - 0.02, 1.35)])
    d.line(T(-t, 1.35), T(-t - 1.2, 1.35)); d.arc(T(-t, 1.35), 1.2 * S, 180, 270)
    d.text(*T(8.9, B + 0.45), 'Д1 (1200), в коридор', 3.0, 'L', RED)
    d.text(*T(-0.4, 1.7), 'Д2 (1200)', 3.5, 'R', RED)
    d.text(*T(-0.4, 0.4), 'в холл №3', 2.5, 'R')
    # колонны
    for cx, cy in ((8.53, 1.75), (8.53, 7.75), (0.53, 1.75), (0.53, 7.75)):
        d.fill([T(cx - 0.15, cy - 0.15), T(cx + 0.15, cy - 0.15), T(cx + 0.15, cy + 0.15), T(cx - 0.15, cy + 0.15)], BLACK)
    # президиум
    d.rect(*T(14.9, 2.5), *T(15.7, 7.0), GREY)
    d.text(*T(15.3, 4.75), 'президиум', 2.5, 'MC', BLACK, 90)
    seats(d, T, S, labels=True)
    d.text(*T(14.4 - 0.9 * 13 - 0.6, 9.0), 'ряд', 2.2, 'R')
    # пути эвакуации
    for pts in (((14.6, 0.5), (0.9, 0.5)), ((0.9, 0.5), (0.9, 1.0)), ((14.6, 9.0), (7.9, 9.0)), ((7.9, 9.0), (7.9, 9.4)),
                ((1.2, 8.9), (1.2, 2.0))):
        d.arrow(T(*pts[0]), T(*pts[1]), GREEN, 2.4)
    # размеры
    d.dim(T(0, 0), T(L, 0), -16, '16 680')
    d.dim(T(L + 0.17, 0), T(L + 0.17, B), -12, '9 500')
    d.dim(T(14.65, 0), T(14.65, 1.0), 0, '1000', 2.2)
    d.dim(T(14.65, 8.5), T(14.65, 9.5), 0, '1000', 2.2)
    d.dim(T(0, 0), T(1.8, 0), -7, '1800', 2.2)
    d.dim(T(1.8, 0), T(14.4, 0), -7, '14 рядов × 900 = 12 600', 2.2)
    d.dim(T(14.4, 0), T(L, 0), -7, '2280', 2.2)
    # расстояние между выходами
    d.line(T(7.4, B), T(0, 1.35), BLUE)
    d.text(*T(3.0, 6.4), f'{calc.R["d_doors"]} м ≥ D/2 = {calc.R["hall_d2"]} м', 3.0, 'C', BLUE, math.degrees(math.atan2(B - 1.35, 7.4)))
    # огнетушители
    extinguisher(d, *T(0.25, 2.6), 'ОП-4(з)', 'О1-8', 'e', 4.0)
    extinguisher(d, *T(6.2, B + 0.5), 'ОП-4(з)', 'О1-7', 'n', 4.0)
    d.text(ox + 25, oy + 279, 'Конференц-зал №36. Схема расстановки мест. М 1:50', 4.0, 'L')
    notes = ['1. Число мест – 200: ряды 1–12 по 15 мест (ряд 7 – 13 мест), ряды 13–14 по 11 мест.',
             '2. Место 500 мм, шаг рядов 900 мм, проход между рядами не менее 450 мм; кресла соединены в ряду',
             '   и крепятся к полу. Выход из каждого ряда – в обе стороны (проходы 1000 мм у стен).',
             f'3. Расчётное время эвакуации {calc.R["t_hall"]} мин при необходимом 2,0 мин (п. 6.2.1 ТЧ).',
             '4. Выход Д1 перенесён из западной стены в северную (задание ЗД-2); двери Д1, Д2 открываются наружу.',
             '5. Стена по оси 6 – противопожарная 1-го типа REI 150.']
    for k, s in enumerate(notes):
        d.text(ox + 25, oy + 36 - k * 4.6, s, 2.5)


def sheet482(msp, d):
    ox, oy, W, H = SHEETS['48.2']
    S = 20.0
    bx, by = ox + 100, oy + 62
    T = lambda x, y: (bx + S * x, by + S * y)
    Lx, Ly, t = 3.88, 10.05, 0.1
    d.rect(*T(-t, -0.25), *T(Lx + t, Ly + t))
    d.rect(*T(0, 0), *T(Lx, Ly))
    # окно в наружной стене по оси А
    d.mask([T(0.8, -0.27), T(3.65, -0.27), T(3.65, 0.02), T(0.8, 0.02)])
    for yy in (-0.25, -0.13, 0):
        d.line(T(0.8, yy), T(3.65, yy))
    d.text(*T(2.2, -0.75), 'окно неоткрывающееся', 2.5, 'C')
    # дверь в коридор №28
    d.mask([T(-t - 0.02, 6.4), T(0.02, 6.4), T(0.02, 7.4), T(-t - 0.02, 7.4)])
    d.line(T(-t, 6.4), T(-t - 1.0, 6.4)); d.arc(T(-t, 6.4), 1.0 * S, 90, 180)
    d.text(*T(-1.3, 6.75), 'коридор №28', 2.5, 'R')
    # модули, трубопроводы, насадки
    for k, ny in enumerate((7.6, 2.5)):
        mx = Lx - 0.32
        d.circle(T(mx, ny), 0.18 * S, RED)
        d.text(*T(mx, ny + 0.28), f'МГП-{k + 1}', 2.5, 'C', RED)
        d.line(T(mx - 0.18, ny), T(1.94, ny), RED, 50)
        d.circle(T(1.94, ny), 0.12 * S, RED)
        for a in range(0, 360, 45):
            r = math.radians(a)
            d.line(T(1.94 + 0.12 * math.cos(r), ny + 0.12 * math.sin(r)), T(1.94 + 0.3 * math.cos(r), ny + 0.3 * math.sin(r)), RED)
        d.text(*T(1.94, ny - 0.75), f'Н{k + 1}', 2.5, 'C', RED)
        d.rect(*T(mx - 0.6, ny - 0.08), *T(mx - 0.45, ny + 0.08), RED)
        d.text(*T(mx - 0.52, ny + 0.2), 'СДУ', 2.0, 'C', RED)
        d.text(*T(2.75, ny - 0.3), 'Ду25', 2.2, 'C', RED)
    # извещатели
    for lab, yy in (('1.35', 1.3), ('1.36', 3.8), ('1.62', 6.3), ('1.63', 8.8)):
        x, y = T(1.2, yy)
        d.circle((x, y), 1.6, RED); d.text(x - 2.5, y - 1.0, lab, 2.2, 'R', RED)
    # КСИД
    for kx, lab in ((0.25, 'КСИД-1'), (2.0, 'КСИД-2')):
        d.rect(*T(kx, -0.22), *T(kx + 0.3, -0.03), BLUE)
        d.text(*T(kx + 0.15, 0.25), lab, 2.2, 'C', BLUE)
    # табло, кнопки
    d.rect(*T(0.05, 7.55), *T(0.2, 7.95), RED); d.text(*T(0.3, 8.0), 'Газ – уходи! + сирена', 2.2, 'L', RED)
    d.rect(*T(-0.3, 7.55), *T(-0.15, 7.95), RED); d.text(*T(-0.4, 8.1), 'Газ – не входи!', 2.2, 'R', RED)
    d.text(*T(-0.4, 7.6), 'Автоматика отключена', 2.2, 'R', RED)
    d.rect(*T(-0.3, 5.9), *T(-0.15, 6.2), RED); d.text(*T(-0.4, 6.0), 'УДП «Пуск газа»,', 2.2, 'R', RED)
    d.text(*T(-0.4, 5.75), 'ключ блокировки', 2.2, 'R', RED)
    d.rect(*T(-1.6, 4.6), *T(-0.6, 5.0), RED); d.text(*T(-1.7, 4.65), 'С2000-АСПТ', 2.2, 'R', RED)
    d.text(*T(0.1, 6.15), 'ИО', 2.0, 'L', RED)
    extinguisher(d, *T(-0.35, 4.0), 'ОУ-5', 'О1-9', 'w', 3.0)
    # размеры
    d.dim(T(0, Ly + t), T(Lx, Ly + t), 6, '3 880')
    d.dim(T(Lx + t, 0), T(Lx + t, Ly), -18, '10 050')
    d.dim(T(Lx + t, 0), T(Lx + t, 2.5), -9, '2 500', 2.2)
    d.dim(T(Lx + t, 2.5), T(Lx + t, 7.6), -9, '5 100', 2.2)
    d.text(ox + 25, oy + 279, 'Серверная №31. План АУГПТ. М 1:50', 4.0, 'L')
    # таблицы справа
    R = calc.R
    x0, y0 = ox + 215, oy + 262
    rows = [('Поз.', 'Наименование', 'Кол.'),
            ('МГП-1, 2', 'Модуль газового пожаротушения 100 л, 4,2 МПа, хладон 227еа ' + R['m_fill'] + ' кг', '2'),
            ('Н1, Н2', 'Насадок радиальный 360°, 8 отв. d ' + R['d_hole'] + ' мм', '2'),
            ('СДУ', 'Сигнализатор давления (выход ГОТВ)', '2'),
            ('ИП', 'Извещатель ДИП-34А-03 (1.35, 1.36, 1.62, 1.63)', '4'),
            ('–', 'Прибор С2000-АСПТ', '1'),
            ('–', 'УДП 513-3АМ «Пуск газа», ключ блокировки', '1'),
            ('–', 'Табло «Газ – уходи!», «Газ – не входи!», «Автоматика отключена»', '3'),
            ('–', 'Оповещатель звуковой', '1'),
            ('ИО', 'Извещатель магнитоконтактный на двери', '1'),
            ('КСИД-1, 2', 'Клапан сброса избыточного давления 300×300', '2'),
            ('Ду25', 'Труба 33,7×3,5 ГОСТ 8732, по 5,0 м на модуль', '10 м')]
    cw = (20, 150, 15)
    table(d, x0, y0, cw, rows, 'Экспликация оборудования АУГПТ')
    hrows = [('Параметр', 'Значение'),
             ('Объём помещения Vр', R['v_srv'] + ' м³'), ('Масса Mр / Mг', R['mp'] + ' / ' + R['mg'] + ' кг'),
             ('Заправка (2 модуля)', R['m_tot'] + ' кг'), ('Концентрация, % об.', R['c_min'] + '...' + R['c_max'] + ' (NOAEL 9,0)'),
             ('Расход на линию G', R['g_line'] + ' кг/с'), ('Давление у насадка', R['p_noz'] + ' МПа'),
             ('Площадь отв. насадка', R['f_noz'] + ' мм²'), ('Время выпуска', R['t_dis'] + ' с ≤ 10 с'),
             ('КСИД, живое сечение', R['f_ksid'] + ' м² ≥ ' + R['fc2'] + ' м²'), ('Задержка выпуска', '30 с')]
    table(d, x0, y0 - 14 - 7 * len(rows), (80, 105), hrows, 'Расчётные параметры (п. 10.4 ТЧ)')
    notes = ['1. Окно – неоткрывающееся, стеклопакет на давление не менее 0,5 кПа; КСИД – низ на отм. +2,900.',
             '2. ОЗК на воздуховодах в местах пересечения ограждений – по разделу ОВ (задание ЗД-5).',
             '3. Ограждения – противопожарные перегородки EI 45, дверь EI 30 с доводчиком и уплотнением.']
    for k, s in enumerate(notes):
        d.text(ox + 25, oy + 36 - k * 4.6, s, 2.5)


def table(d, x0, y0, cw, rows, title, rh=7.0):
    d.text(x0, y0 + 2.5, title, 3.5)
    W = sum(cw)
    for i, r in enumerate(rows):
        y = y0 - rh * i
        d.line((x0, y), (x0 + W, y))
        x = x0
        for w, s in zip(cw, r):
            d.text(x + 1.5, y - rh / 2 - 1.1, s, 2.5 if i else 2.5)
            x += w
    yb = y0 - rh * len(rows)
    d.line((x0, yb), (x0 + W, yb))
    x = x0
    for w in (0,) + cw:
        x += w
        d.line((x, y0), (x, yb))


# ───────────────────────── сборка ─────────────────────────
def build(src, first, total, log=print):
    doc = ezdxf.readfile(src)
    msp = doc.modelspace()
    if LAY not in doc.layers:
        doc.layers.add(LAY)
    import re
    for e in msp.query('TEXT'):
        t = e.dxf.text
        if '\\U+' in t:
            e.dxf.text = re.sub(r'\\U\+([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), t)
    log('удаляю листы текстовой части')
    for e in list(msp):
        p = pts_of(e)
        if p and max(x for x, _ in p) < SHEETS['44'][0] - 5:
            msp.delete_entity(e)
    doc.entitydb.purge()
    idx = Index(msp)
    d = Draw(msp)
    log('правки листов 45, 47, 48')
    sheet45(d)
    plan47(msp, idx, d)
    plan48(msp, idx, d, lambda dd, T, k: seats(dd, T, k))
    log('новые листы 48.1, 48.2')
    for s in ('48.1', '48.2'):
        copy_frame(msp, idx, '48', s)
    idx = Index(msp)
    for s in ORDER:
        retitle(msp, idx, s, TITLES[s])
    sheet481(msp, d)
    sheet482(msp, d)
    nums = {}
    for k, s in enumerate(['44', '44.1', '45', '46', '47', '48', '48.1', '48.2']):
        nums[s] = first + k
    for s in ORDER:
        set_stamp(msp, idx, s, nums[s], total)
    return doc, nums


def export(doc, sheets=ORDER, log=print):
    import export as ex
    os.makedirs(os.path.join(OUT, 'gch'), exist_ok=True)
    idx = Index(doc.modelspace())
    paths = {}
    for s in sheets:
        ox, oy, W, H = SHEETS[s]
        p = os.path.join(OUT, 'gch', f'{s}.pdf')
        log('PDF лист', s)
        ex.sheet_pdf(doc, ox, oy, W, H, p, idx.box)
        paths[s] = p
    return paths


if __name__ == '__main__':
    doc, nums = build(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[4].split(',') if len(sys.argv) > 4 else ORDER
    export(doc, only)
    if len(sys.argv) <= 4:
        doc.saveas(os.path.join(OUT, 'ПБ-25-ГЧ.dxf'))
    print(nums)
