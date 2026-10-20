"""РД ОВиК (И05.09.26-ОВ): общая библиотека листов в DXF.

Модель — в мм, начало координат — пересечение осей 1/А (подложка АР из экспорта Revit сдвинута).
Геометрия задаётся в метрах (как в чертилке ЭП: x вдоль осей 1→5, y вдоль А→Ж).
Обозначения (подписи, ярлыки, решётки) рисуются в модели в масштабе листа: высота текста h мм листа
-> h*k мм модели (k — знаменатель масштаба вида, обычно 100).
Лист — пространство листа (layout) с рамкой, основной надписью формы 3 и видовыми экранами.
"""
import math
import os
import sys

import ezdxf
from ezdxf.enums import TextEntityAlignment as A

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rd_sheet import new_doc as _new_doc, Sheet, save, THICK, THIN          # noqa: E402
from rd_stamp import CODE, OBJ, BLD                                         # noqa: E402
from underlay import add_underlay, insert_underlay, OX, OY                  # noqa: E402

AR = os.path.join(HERE, '..', 'ar_dxf')
UNDER = {
    'plan1': os.path.join(AR, 'ar03_plan1.dxf'),
    'plan2': os.path.join(AR, 'ar09_plan2.dxf'),
    'roof': os.path.join(AR, 'ar14.dxf'),
    'cut11': os.path.join(AR, 'ar15_razrez11.dxf'),
    'cut22': os.path.join(AR, 'ar16_razrez22.dxf'),
    'bath': os.path.join(AR, 'b4_plan.dxf'),
    'bathcut': os.path.join(AR, 'b7_razrezy.dxf'),
}

# ---------------------------------------------------------------- слои ОВ (имя: цвет ACI, вес линии 1/100 мм)
LAYERS = {
    'ОВ_Т1': (1, 50), 'ОВ_Т2': (5, 50),                 # подающий / обратный отопления
    'ОВ_Т11': (6, 35), 'ОВ_Т21': (4, 35),               # подающий / обратный тёплого пола и подводки в стяжке
    'ОВ_ТП': (1, 13),                                    # контуры тёплого пола (зоны, петли)
    'ОВ_Т3': (3, 35), 'ОВ_Т4': (30, 35),                 # ГВС и циркуляция (к бойлерам — для увязки)
    'ОВ_приборы': (7, 35), 'ОВ_КШ': (7, 35), 'ОВ_оборуд': (7, 35),
    'ОВ_П': (5, 35), 'ОВ_В': (32, 35), 'ОВ_Н': (3, 35), 'ОВ_Выброс': (8, 35),   # приток, вытяжка, наружный, выброс
    'ОВ_Рец': (6, 35),                                   # рециркуляция К (возврат)
    'ОВ_Фреон': (6, 35), 'ОВ_Дренаж': (4, 25),
    'ОВ_шахты': (7, 35), 'ОВ_зоны': (5, 18),
    'ОВ_марки': (7, 18), 'ОВ_выноски': (7, 18), 'ОВ_текст': (7, 18), 'ОВ_размеры': (7, 13),
    'ОВ_видовые': (8, 13),
}
DUCT_LAYER = {'П': 'ОВ_П', 'В': 'ОВ_В', 'Н': 'ОВ_Н', 'X': 'ОВ_Выброс', 'Р': 'ОВ_Рец'}


def new_doc():
    doc = _new_doc()
    for n, (c, lw) in LAYERS.items():
        if n not in doc.layers:
            doc.layers.add(n, color=c, lineweight=lw)
    doc.layers.get('ОВ_видовые').dxf.plot = 0
    doc.layers.add('АР_подложка', color=8, lineweight=13)
    # штриховые линии — в мм модели при М 1:100 (для 1:50 у объекта ltscale 0.5)
    lt = doc.linetypes
    if 'ОВ_ШТРИХ' not in lt:
        lt.add('ОВ_ШТРИХ', pattern=[330.0, 240.0, -90.0], description='Штрих 2.4/0.9 при 1:100')
    if 'ОВ_ШП' not in lt:
        lt.add('ОВ_ШП', pattern=[460.0, 300.0, -80.0, 0.0, -80.0], description='Штрихпунктир 1:100')
    if 'ОВ_ПУНКТ' not in lt:
        lt.add('ОВ_ПУНКТ', pattern=[160.0, 80.0, -80.0], description='Пунктир 1:100')
    doc.header['$LTSCALE'] = 1.0
    doc.header['$PSLTSCALE'] = 0
    return doc


def fmt_num(v, d=1):
    return f'{v:.{d}f}'.replace('.', ',')


# ---------------------------------------------------------------- рисование в модели
class DPlan:
    """Рисование в модели: вход — метры (оси 1/А = 0,0), выход — мм. k — знаменатель масштаба вида."""

    def __init__(self, doc, k=100, space=None, unit=1000.0, origin=(0.0, 0.0)):
        self.doc, self.k, self.unit = doc, k, unit
        self.m = space if space is not None else doc.modelspace()
        self.ox, self.oy = origin

    # --- координаты и размеры
    def P(self, x, y):
        return (self.ox + x * self.unit, self.oy + y * self.unit)

    def H(self, h):
        """мм листа -> единицы пространства (мм модели или мм листа): h * k."""
        return h * self.k

    def _attrs(self, layer, color=None, lw=None, ltype=None, ltscale=None):
        a = {'layer': layer}
        if color is not None:
            a['color'] = color
        if lw is not None:
            a['lineweight'] = lw
        if ltype:
            a['linetype'] = ltype
        if ltscale:
            a['ltscale'] = ltscale
        elif ltype and self.k != 100:
            a['ltscale'] = self.k / 100.0
        return a

    # --- примитивы
    def pl(self, pts, layer, closed=False, color=None, lw=None, ltype=None, width=None):
        e = self.m.add_lwpolyline([self.P(*p) for p in pts], close=closed,
                                  dxfattribs=self._attrs(layer, color, lw, ltype))
        if width:
            e.dxf.const_width = width
        return e

    def line(self, x0, y0, x1, y1, layer, **kw):
        return self.pl([(x0, y0), (x1, y1)], layer, **kw)

    def rect(self, x0, y0, x1, y1, layer, fill=None, hatch=None, **kw):
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return self.poly(pts, layer, fill=fill, hatch=hatch, **kw)

    def poly(self, pts, layer, fill=None, hatch=None, outline=True, **kw):
        if fill is not None or hatch is not None:
            h = self.m.add_hatch(color=fill if fill is not None else hatch[3] if len(hatch) > 3 else 7,
                                 dxfattribs={'layer': layer})
            if hatch is not None:
                h.set_pattern_fill(hatch[0], scale=hatch[1] * self.k / 100.0, angle=hatch[2])
            h.paths.add_polyline_path([self.P(*p) for p in pts], is_closed=True)
        if outline:
            return self.pl(pts, layer, closed=True, **kw)

    def circle(self, x, y, r, layer, fill=None, color=None, lw=None, r_paper=None):
        """r — радиус в метрах; r_paper — радиус в мм листа (для условных кружков)."""
        rr = self.H(r_paper) if r_paper else r * self.unit
        if fill is not None:
            h = self.m.add_hatch(color=fill, dxfattribs={'layer': layer})
            h.paths.add_edge_path().add_arc(self.P(x, y), rr, 0, 360)
        return self.m.add_circle(self.P(x, y), rr, dxfattribs=self._attrs(layer, color, lw))

    def t(self, x, y, s, h=2.5, align='left', layer='ОВ_текст', rot=0, color=None, style='GOST'):
        al = {'left': A.MIDDLE_LEFT, 'center': A.MIDDLE_CENTER, 'right': A.MIDDLE_RIGHT,
              'bl': A.BOTTOM_LEFT, 'bc': A.BOTTOM_CENTER, 'br': A.BOTTOM_RIGHT,
              'tl': A.TOP_LEFT, 'tc': A.TOP_CENTER}[align]
        a = {'layer': layer, 'style': style}
        if color is not None:
            a['color'] = color
        e = self.m.add_text(s, height=self.H(h), rotation=rot, dxfattribs=a)
        e.set_placement(self.P(x, y), align=al)
        return e

    def tw(self, s, h=2.5):
        """Ширина строки во входных единицах (ISOCPEUR, ширина 0,9)."""
        return len(s) * 0.62 * self.H(h) / self.unit

    def dot(self, x, y, layer='ОВ_выноски', r=0.35):
        self.circle(x, y, 0, layer, fill=7, r_paper=r)

    def arrow(self, x0, y0, x1, y1, layer, size=2.0, color=None):
        """Стрелка от (x0,y0) к (x1,y1); size — длина острия, мм листа."""
        self.pl([(x0, y0), (x1, y1)], layer, color=color)
        L = math.hypot(x1 - x0, y1 - y0) or 1
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        s = self.H(size) / self.unit
        bx, by = x1 - ux * s, y1 - uy * s
        px, py = -uy * s * 0.33, ux * s * 0.33
        pts = [(x1, y1), (bx + px, by + py), (bx - px, by - py)]
        self.poly(pts, layer, fill=color if color is not None else LAYERS.get(layer, (7, 0))[0], outline=False)

    # --- подписи
    def wipe(self, x0, y0, x1, y1, layer='ОВ_марки'):
        """Маскировка (WIPEOUT): закрывает то, что нарисовано раньше."""
        a, b = self.P(min(x0, x1), min(y0, y1)), self.P(max(x0, x1), max(y0, y1))
        self.m.add_wipeout([a, b], dxfattribs={'layer': layer})

    def label(self, x, y, s, h=2.5, anchor='left', at=None, layer='ОВ_марки', lines=None, mask=False):
        """Полка с надписью; выноска от точки at (м) к началу (или концу) полки.
        lines — вторая строка под полкой (необязательно); mask — белая подложка под текстом."""
        w = self.tw(s, h) + self.H(1.2) / self.unit
        if lines:
            w = max(w, self.tw(lines, h) + self.H(1.2) / self.unit)
        x0 = x if anchor == 'left' else x - w
        if mask:
            top = y + self.H(0.9 + h * 1.25) / self.unit
            bot = y - (self.H(0.9 + h * 1.25) / self.unit if lines else self.H(0.3) / self.unit)
            self.wipe(x0, bot, x0 + w, top)
        if at:
            self.pl([at, (x, y)], 'ОВ_выноски')
            self.dot(*at)
        self.pl([(x0, y), (x0 + w, y)], 'ОВ_выноски')
        self.t(x0 + self.H(0.6) / self.unit, y + self.H(0.9) / self.unit, s, h, 'bl', layer)
        if lines:
            self.t(x0 + self.H(0.6) / self.unit, y - self.H(0.9) / self.unit, lines, h, 'tl', layer)
        return w

    def tag(self, x, y, lines, anchor=None, h=2.5, w=None, mask=False):
        """Ярлык помещения: (x, y) — левый верх, м; первая строка отделена чертой; mask — белая подложка."""
        lh = self.H(h * 1.45) / self.unit
        pad = self.H(1.0) / self.unit
        if w is None:
            w = max(self.tw(s, h) for s in lines) + 2 * pad
        Hh = lh * len(lines) + pad * 0.6
        if mask:
            self.wipe(x, y - Hh, x + w, y)
        if anchor:
            cx = min(max(anchor[0], x), x + w)
            cy = min(max(anchor[1], y - Hh), y)
            self.pl([anchor, (cx, cy)], 'ОВ_выноски')
            self.dot(*anchor)
        self.rect(x, y - Hh, x + w, y, 'ОВ_марки', fill=None)
        for i, s in enumerate(lines):
            self.t(x + pad, y - pad * 0.3 - lh * (i + 0.5), s, h, 'left', 'ОВ_марки')
        self.pl([(x, y - lh - pad * 0.3), (x + w, y - lh - pad * 0.3)], 'ОВ_марки')
        return w, Hh

    # --- трубопроводы
    def pipe(self, pts, layer='ОВ_Т1', mark=None, every=4.0, h=2.0, ltype=None, lw=None):
        """Трубопровод; mark — обозначение в разрывах линии (Т1, Т2…) через every метров (ГОСТ 21.206)."""
        if not mark:
            return self.pl(pts, layer, ltype=ltype, lw=lw)
        gap = self.tw(mark, h) + self.H(1.6) / self.unit
        cum = [0.0]
        for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
            cum.append(cum[-1] + math.hypot(x1 - x0, y1 - y0))
        total = cum[-1]

        def at(sv):
            for i in range(len(pts) - 1):
                if cum[i] - 1e-9 <= sv <= cum[i + 1] + 1e-9:
                    L = cum[i + 1] - cum[i] or 1
                    t = (sv - cum[i]) / L
                    (x0, y0), (x1, y1) = pts[i], pts[i + 1]
                    return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, i
            return pts[-1][0], pts[-1][1], len(pts) - 2

        marks = []
        sv = min(every / 2, total / 2)
        while sv < total - gap * 0.6:
            x, y, i = at(sv)
            if cum[i] + gap * 0.6 <= sv <= cum[i + 1] - gap * 0.6:      # не на изломе
                marks.append((sv, x, y, i))
                sv += every
            else:
                sv += gap * 0.5
        # куски линии между разрывами
        cuts = [(m[0] - gap / 2, m[0] + gap / 2) for m in marks]
        bounds = [0.0] + [c for ab in cuts for c in ab] + [total]
        for k in range(0, len(bounds), 2):
            s0, s1 = bounds[k], bounds[k + 1]
            if s1 - s0 < 1e-6:
                continue
            seg = [at(s0)[:2]] + [pts[j] for j in range(len(pts)) if s0 < cum[j] < s1] + [at(s1)[:2]]
            self.pl(seg, layer, ltype=ltype, lw=lw)
        for sv, x, y, i in marks:
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
            if ang > 90.01 or ang < -89.99:
                ang += 180
            self.t(x, y, mark, h, 'center', layer, rot=ang)

    def pipes2(self, pts, gap=0.12, layers=('ОВ_Т1', 'ОВ_Т2'), marks=('Т1', 'Т2'), every=5.0, ltypes=(None, 'ОВ_ШТРИХ')):
        """Пара трубопроводов (подача/обратка) параллельно, на расстоянии gap (м): подача слева по ходу."""
        a = offset_poly(pts, +gap / 2)
        b = offset_poly(pts, -gap / 2)
        self.pipe(a, layers[0], marks[0], every, ltype=ltypes[0])
        self.pipe(b, layers[1], marks[1], every, ltype=ltypes[1])
        return a, b

    def riser(self, x, y, layer, r=1.0):
        """Стояк: кружок r мм листа."""
        self.circle(x, y, 0, layer, r_paper=r)

    # --- воздуховоды
    def duct(self, pts, size, kind='П', center=False):
        """Воздуховод двумя линиями. size — Ø (мм) или (ширина, высота) мм; ширина — в плане."""
        w = (size if isinstance(size, (int, float)) else size[0]) / 1000.0
        lay = DUCT_LAYER[kind]
        self.pl(offset_poly(pts, w / 2), lay)
        self.pl(offset_poly(pts, -w / 2), lay)
        # торцы
        for (xa, ya), (xb, yb) in ((pts[0], pts[1]), (pts[-1], pts[-2])):
            L = math.hypot(xb - xa, yb - ya) or 1
            nx, ny = -(yb - ya) / L * w / 2, (xb - xa) / L * w / 2
            self.pl([(xa + nx, ya + ny), (xa - nx, ya - ny)], lay)
        if center:
            self.pl(pts, lay, ltype='ОВ_ШП', lw=13)

    def duct_mark(self, x, y, txt, kind='П', h=2.2, rot=0):
        self.t(x, y, txt, h, 'center', DUCT_LAYER[kind], rot=rot)

    def grille(self, x, y, kind, L, direction='down', size=0.45, txt_side='right', name=None):
        """Решётка/диффузор в плане: квадрат size м, крест, стрелка движения воздуха и расход."""
        lay = DUCT_LAYER[kind if kind in DUCT_LAYER else 'П']
        a = size / 2
        self.rect(x - a, y - a, x + a, y + a, lay)
        self.line(x - a, y - a, x + a, y + a, lay)
        self.line(x - a, y + a, x + a, y - a, lay)
        dx, dy = dict(down=(0, -1), up=(0, 1), left=(-1, 0), right=(1, 0))[direction]
        s = self.H(3.2) / self.unit
        if kind == 'П':
            self.arrow(x + dx * a, y + dy * a, x + dx * (a + s), y + dy * (a + s), lay)
        else:
            self.arrow(x + dx * (a + s), y + dy * (a + s), x + dx * a, y + dy * a, lay)
        tx = x + (a + self.H(0.8) / self.unit) * (1 if txt_side == 'right' else -1)
        txt = f'L={L}' if name is None else f'{name}  L={L}'
        self.t(tx, y, txt, 2.0, 'left' if txt_side == 'right' else 'right', lay)

    def shaft(self, x0, y0, x1, y1, layer='ОВ_шахты'):
        self.rect(x0, y0, x1, y1, layer)
        self.line(x0, y0, x1, y1, layer, lw=18)
        self.line(x0, y1, x1, y0, layer, lw=18)

    def ufh_zone(self, pts, label=None):
        """Зона тёплого пола: контур штрихом и наклонная штриховка."""
        self.poly(pts, 'ОВ_ТП', hatch=('ANSI31', 22.0, 45, 1), ltype='ОВ_ШТРИХ')


HOUSE_AX = ([('1', 0.0), ('2', 6.1), ('3', 9.5), ('4', 12.6), ('5', 20.0)],
            [('А', 0.0), ('Б', 1.1), ('В', 6.3), ('Г', 8.9), ('Д', 13.8), ('Е', 15.5), ('Ж', 16.7)])
BATH_AX = ([('1', 0.0), ('2', 5.4), ('3', 10.5), ('4', 15.9)], [('А', 0.0), ('Б', 2.0), ('В', 6.6)])


def axes(p, ax=HOUSE_AX, y_bub=-2.6, x_bub=-2.6, top=None, right=None, r=4.0, dims=True):
    """Марки осей (кружок r мм листа) и размерные цепочки между осями.
    y_bub — где ставить марки вертикальных осей (м), x_bub — горизонтальных; top/right — вторые ряды марок."""
    xs, ys = ax
    R = p.H(r) / p.unit
    y0, y1 = ys[0][1], ys[-1][1]
    x0, x1 = xs[0][1], xs[-1][1]
    for n, x in xs:
        for yb, sgn in ((y_bub, -1), (top, 1)):
            if yb is None:
                continue
            p.line(x, (y0 - 0.4) if sgn < 0 else (y1 + 0.4), x, yb - sgn * 0, 'ОВ_размеры', ltype='ОВ_ШП')
            p.circle(x, yb + sgn * R, 0, 'ОВ_размеры', r_paper=r)
            p.t(x, yb + sgn * R, n, 3.5, 'center', 'ОВ_размеры')
    for n, y in ys:
        for xb, sgn in ((x_bub, -1), (right, 1)):
            if xb is None:
                continue
            p.line((x0 - 0.4) if sgn < 0 else (x1 + 0.4), y, xb, y, 'ОВ_размеры', ltype='ОВ_ШП')
            p.circle(xb + sgn * R, y, 0, 'ОВ_размеры', r_paper=r)
            p.t(xb + sgn * R, y, n, 3.5, 'center', 'ОВ_размеры')
    if dims:
        tick = p.H(1.2) / p.unit
        yd = y_bub + 0.75
        for (na, xa), (nb, xb) in zip(xs[:-1], xs[1:]):
            p.line(xa, yd, xb, yd, 'ОВ_размеры')
            p.t((xa + xb) / 2, yd + p.H(1.2) / p.unit, f'{int(round((xb - xa) * 1000))}', 2.5, 'bc', 'ОВ_размеры')
        for _, x in xs:
            p.line(x - tick, yd - tick, x + tick, yd + tick, 'ОВ_размеры', lw=35)
        xd = x_bub + 0.75
        for (na, ya), (nb, yb) in zip(ys[:-1], ys[1:]):
            p.line(xd, ya, xd, yb, 'ОВ_размеры')
            p.t(xd - p.H(1.2) / p.unit, (ya + yb) / 2, f'{int(round((yb - ya) * 1000))}', 2.5, 'bc', 'ОВ_размеры', rot=90)
        for _, y in ys:
            p.line(xd - tick, y - tick, xd + tick, y + tick, 'ОВ_размеры', lw=35)


def offset_poly(pts, d):
    """Смещение полилинии влево по ходу на d (м), стыки — по биссектрисе."""
    clean = [pts[0]]
    for q in pts[1:]:
        if math.hypot(q[0] - clean[-1][0], q[1] - clean[-1][1]) > 1e-6:
            clean.append(q)
    pts = clean
    if len(pts) < 2:
        return pts
    out = []
    n = len(pts)
    for i in range(n):
        if i == 0:
            (xa, ya), (xb, yb) = pts[0], pts[1]
            L = math.hypot(xb - xa, yb - ya) or 1
            nx, ny = -(yb - ya) / L, (xb - xa) / L
            out.append((pts[0][0] + nx * d, pts[0][1] + ny * d))
        elif i == n - 1:
            (xa, ya), (xb, yb) = pts[-2], pts[-1]
            L = math.hypot(xb - xa, yb - ya) or 1
            nx, ny = -(yb - ya) / L, (xb - xa) / L
            out.append((pts[-1][0] + nx * d, pts[-1][1] + ny * d))
        else:
            (xa, ya), (xb, yb), (xc, yc) = pts[i - 1], pts[i], pts[i + 1]
            L1 = math.hypot(xb - xa, yb - ya) or 1
            L2 = math.hypot(xc - xb, yc - yb) or 1
            n1 = (-(yb - ya) / L1, (xb - xa) / L1)
            n2 = (-(yc - yb) / L2, (xc - xb) / L2)
            bx, by = n1[0] + n2[0], n1[1] + n2[1]
            bl = math.hypot(bx, by)
            if bl < 1e-9:
                out.append((xb + n1[0] * d, yb + n1[1] * d))
                continue
            bx, by = bx / bl, by / bl
            cos = bx * n1[0] + by * n1[1]
            if abs(cos) < 1e-3:
                out.append((xb + n1[0] * d, yb + n1[1] * d))
                continue
            out.append((xb + bx * d / cos, yb + by * d / cos))
    return out


# ---------------------------------------------------------------- состав комплекта И05.09.26-ОВ (номер листа: наименование)
SHEET_LIST = {
    1: 'Общие данные (начало)',
    2: 'Общие данные (окончание). Условные обозначения',
    3: 'План 1 этажа. Отопление',
    4: 'План 1 этажа. Раскладка тёплого пола',
    5: 'План 2 этажа. Отопление',
    6: 'Схема системы отопления',
    7: 'Топочная. План расположения оборудования',
    8: 'Топочная. Принципиальная тепловая схема',
    9: 'План 1 этажа. Вентиляция и кондиционирование',
    10: 'План 2 этажа. Вентиляция и кондиционирование',
    11: 'Схемы систем вентиляции и кондиционирования',
    12: 'Баня. План отопления и вентиляции',
    13: 'Баня. Схема КШ-Б. Узлы',
    14: 'Ситуационный план. Теплотрасса дом – баня. Наружный блок НБ-1',
    15: 'Узлы и детали',
}
SHEETS_TOTAL = len(SHEET_LIST)

# ---------------------------------------------------------------- лист
FORMATS = {'А3': (420, 297), 'А2': (594, 420), 'А1': (841, 594), 'А4': (210, 297), 'А3x3': (630, 297)}


class RDSheet:
    """Лист РД: пространство листа с рамкой и штампом; модель — общая для файла."""

    def __init__(self, doc, name, title, no, total, fmt='А3', code=CODE):
        self.doc = doc
        W, H = FORMATS[fmt]
        self.W, self.H = W, H
        self.lay = doc.layouts.new(name)
        if 'Layout1' in doc.layouts and len(doc.layouts.get('Layout1')) == 0:
            doc.layouts.delete('Layout1')
        self.lay.page_setup(size=(W, H), margins=(0, 0, 0, 0), units='mm')
        self.s = Sheet(doc, W, H)
        self.s.m = self.lay
        self.s.frame(f'Формат {fmt}')
        self.s.stamp3(code, OBJ, BLD, title, no, total)
        self.p = DPlan(doc, k=1, space=self.lay, unit=1.0)        # рисование на листе в мм

    def viewport(self, cx, cy, w, h, model_cx, model_cy, k=100):
        """Видовой экран: центр и размер на листе (мм), центр вида в модели (м), масштаб 1:k."""
        vp = self.lay.add_viewport(center=(cx, cy), size=(w, h),
                                   view_center_point=(model_cx * 1000, model_cy * 1000),
                                   view_height=h * k, dxfattribs={'layer': 'ОВ_видовые'})
        vp.dxf.status = 2
        return vp

    def title(self, x, y, s, h=3.5):
        self.s.text(s, x, y, h=h, align='center')
        w = len(s) * h * 0.55
        self.s.line(x - w / 2, y - h * 0.75, x + w / 2, y - h * 0.75, lw=THIN)

    def notes(self, x, y, w, items, h=2.5, title='Примечания', spacing=1.15):
        """Нумерованные примечания одним MTEXT; возвращает оценку высоты (мм)."""
        self.s.text(title, x + w / 2, y, h=3.0, align='center')
        body = '\\P'.join(f'{i}. {t}' for i, t in enumerate(items, 1))
        self.s.mtext(body, x, y - 4, w, h=h, attach=1, spacing=spacing)
        chars = sum(len(t) + 3 for t in items)
        per_line = w / (h * 0.55)
        n_lines = sum(math.ceil((len(t) + 3) / per_line) for t in items)
        return 4 + n_lines * h * 1.7 * spacing

    def table(self, x, y, widths, rows, **kw):
        return self.s.table(x, y, widths, rows, **kw)


def no_yo(doc):
    """В ISOCPEUR нет «ё» и «…»: заменить во всех надписях модели, листов и блоков ОВ."""
    rep = (('ё', 'е'), ('Ё', 'Е'), ('…', '...'))
    spaces = [doc.modelspace()] + [l for l in doc.layouts if l.name != 'Model']
    for sp in spaces:
        for e in sp.query('TEXT MTEXT'):
            t = e.dxf.text if e.dxftype() == 'TEXT' else e.text
            n = t
            for a, b in rep:
                n = n.replace(a, b)
            if n != t:
                if e.dxftype() == 'TEXT':
                    e.dxf.text = n
                else:
                    e.text = n


def save_and_pdf(doc, dxf_path, pdf=True, layouts=None):
    no_yo(doc)
    save(doc, dxf_path)
    if not pdf:
        return
    import subprocess
    pdfs = []
    for lay in doc.layouts:
        if lay.name == 'Model' or (layouts and lay.name not in layouts):
            continue
        out = dxf_path[:-4] + '_' + lay.name.replace(' ', '_') + '.pdf'
        subprocess.run([sys.executable, os.path.join(HERE, 'render_layout.py'), dxf_path, out, lay.name],
                       check=True, capture_output=True)
        pdfs.append(out)
    return pdfs


# ---------------------------------------------------------------- тёплый пол: раскладка петли «улиткой»
def _rect_spiral(W, H, a, step, sh):
    """Прямоугольная спираль внутрь в осях [0,W]×[0,H]: старт (a+sh, a+sh), шаг между витками step."""
    l, b, r, t = a + sh, a + sh, W - a - sh, H - a - sh
    if r - l < 1e-6 or t - b < 1e-6:
        return []
    pts = [(l, b)]
    while True:
        if r - pts[-1][0] < 1e-6:
            break
        pts.append((r, b))
        if t - b < 1e-6:
            break
        pts.append((r, t))
        if r - l < 1e-6:
            break
        pts.append((l, t))
        nb = b + step
        if t - nb < 1e-6:
            break
        pts.append((l, nb))
        l, b, r, t = l + step, nb, r - step, t - step
        if r - l < -1e-6 or t - b < -1e-6:
            # ширина или высота кончилась — «язык» по оси оставшейся полосы, чтобы не было пустот
            x, y = pts[-1]
            if t - b > 1e-6:                                  # высокая полоса: вверх по середине
                xc = (l - step + r + step) / 2.0
                pts += [(xc, y), (xc, t + step)]
            elif r - l > 1e-6:                                # широкая полоса: вправо по середине
                pts += [(r + step, y)]
            break
        if r < l:
            r = l
    return pts


def ufh_coil(p, poly_pts, T, entry=None, lays=('ОВ_Т11', 'ОВ_Т21'), lw=18, d0=None, lead_pts=None):
    """Петля тёплого пола двойной спиралью («улитка»): подача и обратка чередуются с шагом T (м).

    Прямоугольная зона — две ортогональные спирали с шагом 2T, вложенные со сдвигом T: без пересечений,
    оба конца у угла, ближайшего к подводке. Непрямоугольная — витки по внутренним отступам контура.
    poly_pts — контур зоны (м); entry — куда приходит подводка; lead_pts — (конец подачи, конец обратки).
    Возвращает длину трубы в зоне, м."""
    from shapely.geometry import Polygon, LineString, Point
    from shapely.geometry.polygon import orient
    from shapely.ops import substring

    d0 = T / 2 if d0 is None else d0
    xs = [q[0] for q in poly_pts]
    ys = [q[1] for q in poly_pts]
    X0, X1, Y0, Y1 = min(xs), max(xs), min(ys), max(ys)
    P = Polygon(poly_pts)
    is_rect = abs(P.area - (X1 - X0) * (Y1 - Y0)) < 1e-6
    E = entry if entry is not None else (X0, Y0)
    sup, ret = [], []
    if is_rect:
        W, H = X1 - X0, Y1 - Y0
        fx = (E[0] - X0) > (X1 - E[0])          # угол входа: ближайший к подводке
        fy = (E[1] - Y0) > (Y1 - E[1])

        def g(q):
            x, y = q
            return (X1 - x if fx else X0 + x, Y1 - y if fy else Y0 + y)
        # первая сторона спирали — вдоль той стороны, по которой не приходит подводка
        dx = min(abs(E[0] - X0), abs(E[0] - X1))
        dy = min(abs(E[1] - Y0), abs(E[1] - Y1))
        swap = dy > dx        # подводка ближе к вертикальной стороне — первый ход вверх
        if swap:
            S = _rect_spiral(H, W, d0, 2 * T, 0.0)
            Rr = _rect_spiral(H, W, d0, 2 * T, T)
            S = [(y, x) for x, y in S]
            Rr = [(y, x) for x, y in Rr]
        else:
            S = _rect_spiral(W, H, d0, 2 * T, 0.0)
            Rr = _rect_spiral(W, H, d0, 2 * T, T)
        sup = [g(q) for q in S]
        ret = [g(q) for q in Rr]
    else:
        rings, d = [], d0
        while True:
            gg = P.buffer(-d, join_style=2, mitre_limit=10)
            if gg.is_empty:
                break
            if gg.geom_type == 'MultiPolygon':
                gg = max(gg.geoms, key=lambda q: q.area)
            bx0, by0, bx1, by1 = gg.bounds
            if min(bx1 - bx0, by1 - by0) < 0.6 * T or gg.exterior.length < 5 * T:
                break
            rings.append(LineString(orient(gg, sign=-1.0).exterior.coords))
            d += T
        if not rings:
            return 0.0
        c = P.centroid
        Ep = Point(E)
        vx, vy = c.x - Ep.x, c.y - Ep.y
        n = math.hypot(vx, vy) or 1.0
        ray = LineString([(Ep.x - vx / n * 0.5, Ep.y - vy / n * 0.5), (c.x + vx / n * 50, c.y + vy / n * 50)])

        def start_param(ring):
            it = ring.intersection(ray)
            pts = [q for q in getattr(it, 'geoms', [it]) if q.geom_type == 'Point' and not q.is_empty]
            return ring.project(min(pts, key=lambda q: q.distance(Ep))) if pts else ring.project(Ep)

        def walk(ring, s0, length):
            L = ring.length
            s0 %= L
            if s0 + length <= L:
                return list(substring(ring, s0, s0 + length).coords)
            return list(substring(ring, s0, L).coords) + list(substring(ring, 0, s0 + length - L).coords)[1:]

        gap = 3 * T
        for k, ring in enumerate(rings):
            L = ring.length
            st = start_param(ring) - (0 if k % 2 == 0 else T)
            (sup if k % 2 == 0 else ret).extend(walk(ring, st, max(L - gap, L * 0.3)))
    if not sup:
        return 0.0
    if ret:
        sup = sup + [ret[-1]]                 # разворот в центре: конец подачи → конец обратки
    if lead_pts is not None:
        a, b = lead_pts
        if ret and math.dist(a, sup[0]) + math.dist(b, ret[0]) > math.dist(b, sup[0]) + math.dist(a, ret[0]):
            a, b = b, a
        sup = [a] + sup
        if ret:
            ret = [b] + ret
    p.pl(sup, lays[0], lw=lw)
    if len(ret) > 1:
        p.pl(ret, lays[1], lw=lw)
    return LineString(sup).length + (LineString(ret).length if len(ret) > 1 else 0.0)


def _ortho_rings(poly_pts, T, d0, step, start, ccw=True):
    """Кольца отступа ортогонального контура: d0, d0+step, … (части уже ≈T отбрасываются «раскрытием»).
    Каждое кольцо — список вершин, начиная с угла, ближайшего к start (для следующих — к углу предыдущего)."""
    from shapely.geometry import Polygon, Point
    from shapely.geometry.polygon import orient
    P = Polygon(poly_pts)
    r = 0.45 * T
    rings, d, corner = [], d0, start
    while True:
        g = P.buffer(-(d + r), join_style=2, mitre_limit=10)
        if g.is_empty:
            break
        g = g.buffer(r, join_style=2, mitre_limit=10)
        if g.geom_type == 'MultiPolygon':
            g = min(g.geoms, key=lambda q: q.distance(Point(corner)))
        g = orient(g.simplify(1e-6), sign=1.0 if ccw else -1.0)
        V = list(g.exterior.coords)[:-1]
        i0 = min(range(len(V)), key=lambda i: math.dist(V[i], corner))
        V = V[i0:] + V[:i0]
        rings.append(V)
        corner = V[0]
        d += step
    return rings


def _ortho_spiral(rings, step):
    """Спираль по кольцам: последняя сторона витка обрывается на линии первой стороны следующего витка
    (как у прямоугольной «улитки»), переходы — без диагоналей."""
    pts = []
    for k, V in enumerate(rings):
        if k == 0:
            pts.append(V[0])
        pts.extend(V[1:])
        a, b = V[-1], V[0]                          # последняя сторона витка a → b
        if k + 1 < len(rings):
            W = rings[k + 1]
            c, e = W[0], W[1]                       # первая сторона следующего витка c → e
            if abs(a[0] - b[0]) < 1e-6 and abs(c[1] - e[1]) < 1e-6:
                end = (b[0], c[1])
            elif abs(a[1] - b[1]) < 1e-6 and abs(c[0] - e[0]) < 1e-6:
                end = (c[0], b[1])
            else:
                end = c
        else:                                        # последний виток: не доходить до своего начала
            L = math.dist(a, b)
            t = max(0.0, (L - step) / L) if L > 1e-9 else 0.0
            end = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        pts.append(end)
    return pts


def ufh_coil_ortho(p, poly_pts, T, start, ccw=True, lays=('ОВ_Т11', 'ОВ_Т21'), lw=18, lead_pts=None,
                   lead_dir=None):
    """«Улитка» для ортогональной зоны любой формы (Г-образной, с вырезами): две вложенные спирали с шагом 2T —
    по отступам T/2, 5T/2… и 3T/2, 7T/2…; начало — в углу start (ближний к подводке), ccw — направление
    первого хода. В центре спирали соединяются. lead_pts — концы подводки (подача, обратка), lead_dir —
    направление последнего участка подводки: подключение к виткам — с поворотом 90°, без диагоналей; какая
    спираль внешняя, выбирается так, чтобы подключения не пересекались (цвет витков — по своей трубе подводки).
    Возвращает длину трубы в зоне, м."""
    from shapely.geometry import LineString
    rs = _ortho_rings(poly_pts, T, T / 2, 2 * T, start, ccw)
    if not rs:
        return 0.0
    rr = _ortho_rings(poly_pts, T, 1.5 * T, 2 * T, rs[0][0], ccw)
    A = _ortho_spiral(rs, 2 * T)
    B = _ortho_spiral(rr, 2 * T) if rr else []
    joint = []
    if B:
        a, b = A[-1], B[-1]
        if abs(a[0] - b[0]) > 1e-6 and abs(a[1] - b[1]) > 1e-6:
            joint = [(a[0], b[1])]

    def link(q, c):
        if lead_dir is None:
            return [q]
        if abs(lead_dir[0]) < abs(lead_dir[1]):          # подводка вертикальная: сначала по ней, затем поперёк
            return [q, (q[0], c[1])]
        return [q, (c[0], q[1])]

    cands = []
    if lead_pts is None:
        cands.append((A, B, 0))
    else:
        qs, qr = lead_pts
        for swap in (False, True):
            ls, lr = (qs, qr) if not swap else (qr, qs)   # ls — к внешней спирали A, lr — к B
            Af = link(ls, A[0]) + A
            Bf = (link(lr, B[0]) + B) if B else []
            bad = 0
            if Bf:
                g1, g2 = LineString(Af), LineString(Bf)
                bad = 1 if g1.intersects(g2) else 0
            Lc = LineString(Af[:3]).length + (LineString(Bf[:3]).length if Bf else 0)
            cands.append((Af, Bf, (bad, Lc), swap))
    if lead_pts is None:
        Af, Bf, swap = A, B, False
    else:
        Af, Bf, _, swap = min(cands, key=lambda c: c[2])
    # подача — по слою своей трубы подводки: при swap внешняя спираль A идёт от обратки
    full_A = Af + joint + ([Bf[-1]] if Bf else [])
    la, lb = (lays[1], lays[0]) if swap else (lays[0], lays[1])
    p.pl(full_A, la, lw=lw)
    if len(Bf) > 1:
        p.pl(Bf, lb, lw=lw)
    return LineString(full_A).length + (LineString(Bf).length if len(Bf) > 1 else 0.0)
