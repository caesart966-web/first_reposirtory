"""И05.09.26-ОВ. Лист 15 «Узлы и детали» (формат А2, узлы нарисованы прямо на листе, в мм листа).

python3 sheets/ov_nodes.py  ->  out/ov_nodes.dxf + out/ov_nodes_Лист.pdf
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from rdbase import new_doc, RDSheet, save_and_pdf, SHEET_LIST, SHEETS_TOTAL  # noqa: E402
from ov_heat1 import OUT  # noqa: E402

SHEET_NO = 15


class N:
    """Чертёжные примитивы в пространстве листа (мм листа)."""

    def __init__(self, sh):
        self.sh, self.s, self.m = sh, sh.s, sh.lay

    def L(self, x0, y0, x1, y1, layer='Узлы', lw=None, color=None):
        a = {'layer': layer}
        if lw:
            a['lineweight'] = lw
        if color is not None:
            a['color'] = color
        return self.m.add_line((x0, y0), (x1, y1), dxfattribs=a)

    def PL(self, pts, layer='Узлы', closed=False, lw=None, color=None):
        a = {'layer': layer}
        if lw:
            a['lineweight'] = lw
        if color is not None:
            a['color'] = color
        return self.m.add_lwpolyline(pts, close=closed, dxfattribs=a)

    def R(self, x0, y0, x1, y1, layer='Узлы', lw=None, color=None):
        return self.PL([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, True, lw, color)

    def H(self, pts, pattern='ANSI31', scale=0.5, angle=0.0, color=8, layer='Штриховка'):
        h = self.m.add_hatch(color=color, dxfattribs={'layer': layer})
        if pattern == 'SOLID':
            h.set_solid_fill(color=color)
        else:
            h.set_pattern_fill(pattern, scale=scale, angle=angle)
        h.paths.add_polyline_path(pts, is_closed=True)
        return h

    def HR(self, x0, y0, x1, y1, pattern='ANSI31', scale=0.5, angle=0.0, color=8):
        return self.H([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], pattern, scale, angle, color)

    def C(self, x, y, r, layer='Узлы', fill=None, lw=None, color=None):
        if fill is not None:
            h = self.m.add_hatch(color=fill, dxfattribs={'layer': layer})
            h.paths.add_edge_path().add_arc((x, y), r, 0, 360)
        a = {'layer': layer}
        if lw:
            a['lineweight'] = lw
        if color is not None:
            a['color'] = color
        return self.m.add_circle((x, y), r, dxfattribs=a)

    def T(self, s, x, y, h=2.5, align='left', rot=0, layer='Текст'):
        return self.s.text(s, x, y, h=h, align=align, rot=rot, layer=layer)

    def MT(self, s, x, y, w, h=2.2, spacing=1.0):
        return self.s.mtext(s, x, y, w, h=h, attach=1, spacing=spacing)

    def title(self, x, y, s, scale=None, h=3.2, right=None):
        self.T(s, x, y, h, 'left')
        w = len(s) * h * 0.66
        self.L(x, y - h * 0.8, x + w, y - h * 0.8, 'Узлы', lw=35)
        if scale:
            self.T(scale, x, y - 5.5, 2.5, 'left')

    def wipe(self, x0, y0, x1, y1):
        self.m.add_wipeout([(min(x0, x1), min(y0, y1)), (max(x0, x1), max(y0, y1))], dxfattribs={'layer': 'Текст'})

    def callout(self, n, px, py, cx, cy, r=2.3):
        """Позиционная выноска: точка на элементе -> кружок с номером."""
        d = math.hypot(cx - px, cy - py) or 1
        ex, ey = cx - (cx - px) / d * r, cy - (cy - py) / d * r
        self.L(px, py, ex, ey, 'Тонкие', lw=18, color=7)
        self.C(px, py, 0.45, 'Тонкие', fill=7)
        self.wipe(cx - r, cy - r, cx + r, cy + r)
        self.C(cx, cy, r, 'Тонкие', lw=18, color=7)
        self.T(str(n), cx, cy, 2.5, 'center')

    def legend(self, x, y, w, items, h=2.1, start=1):
        body = '\\P'.join(f'{i}. {t}' for i, t in enumerate(items, start))
        return self.MT(body, x, y, w, h=h, spacing=0.95)

    def tick(self, x, y):
        self.L(x - 1.0, y - 1.0, x + 1.0, y + 1.0, 'Размеры', lw=35)

    @staticmethod
    def tw(s, h):
        return len(s) * h * 0.62

    def dim_h(self, x0, x1, y, text, ext=None, h=2.2, wipe=True):
        """Горизонтальный размер на высоте y; ext — y начала выносных линий (или None)."""
        self.L(x0 - 1.5, y, x1 + 1.5, y, 'Размеры', lw=13)
        self.tick(x0, y)
        self.tick(x1, y)
        if ext is not None:
            for x in (x0, x1):
                self.L(x, ext, x, y + (1.5 if y > ext else -1.5), 'Размеры', lw=13)
        xm = (x0 + x1) / 2
        if wipe:
            w = self.tw(text, h) + 0.8
            self.wipe(xm - w / 2, y + 1.1, xm + w / 2, y + 1.1 + h)
        self.T(text, xm, y + 0.8, h, 'bc', layer='Размеры')

    def dim_v(self, y0, y1, x, text, ext=None, h=2.2, side='left', wipe=True):
        self.L(x, y0 - 1.5, x, y1 + 1.5, 'Размеры', lw=13)
        self.tick(x, y0)
        self.tick(x, y1)
        if ext is not None:
            for y in (y0, y1):
                self.L(ext, y, x + (1.5 if x > ext else -1.5), y, 'Размеры', lw=13)
        dx = -0.8 if side == 'left' else 0.8 + h
        ym = (y0 + y1) / 2
        if wipe:
            w = self.tw(text, h) + 0.8
            xa, xb = (x - 1.0 - h, x - 1.1) if side == 'left' else (x + 1.1, x + 1.0 + h)
            self.wipe(xa, ym - w / 2, xb, ym + w / 2)
        self.T(text, x + dx, ym, h, 'bc', rot=90, layer='Размеры')

    def chain_v(self, x, ys, texts, ext=None, side='left'):
        for (a, b), t in zip(zip(ys[:-1], ys[1:]), texts):
            self.dim_v(a, b, x, t, ext=ext, side=side)

    def chain_h(self, y, xs, texts, ext=None):
        for (a, b), t in zip(zip(xs[:-1], xs[1:]), texts):
            self.dim_h(a, b, y, t, ext=ext)

    def level(self, x, y, s, side='right', down=False, h=2.2):
        """Отметка уровня: треугольник вершиной на поверхность, полка, текст над полкой (down — под ней)."""
        sg = 1 if side == 'right' else -1
        yl = y - 2.2 if down else y + 2.2
        self.PL([(x, y), (x - 1.5, yl), (x + 1.5, yl)], 'Размеры', closed=True, lw=18)
        self.L(x, yl, x + sg * (self.tw(s, h) + 3.0), yl, 'Размеры', lw=13)
        xt = x + 1.6 if sg > 0 else x - 1.6 - self.tw(s, h)
        self.T(s, xt, yl - 0.8 - h if down else yl + 0.8, h, 'bl', layer='Размеры')

    def brk_h(self, x0, x1, y):
        """Линия обрыва (горизонтальная) с изломом."""
        xm = (x0 + x1) / 2
        self.PL([(x0 - 2, y), (xm - 2, y), (xm - 1, y + 2), (xm + 1, y - 2), (xm + 2, y), (x1 + 2, y)], 'Тонкие', lw=13)

    def brk_v(self, x, y0, y1):
        ym = (y0 + y1) / 2
        self.PL([(x, y0 - 2), (x, ym - 2), (x + 2, ym - 1), (x - 2, ym + 1), (x, ym + 2), (x, y1 + 2)], 'Тонкие', lw=13)

    def pipe(self, x, y, d, sys_='Т1'):
        lay, col = ('ОВ_Т1', 1) if sys_ in ('Т1', 'Т11') else ('ОВ_Т2', 5)
        self.C(x, y, d / 2, lay, lw=25, color=col)


# ------------------------------------------------------------------ узел 1: пироги пола с ТП
def node1(n):
    n.title(25, 404, 'Узел 1. Пол с водяным тёплым полом', 'М 1:10')

    def pie(top, x0, x1, layers, ufh_step, sub, brk=True):
        n.T(sub, x0 - 6, top + 11, 2.5, 'left')
        ys = [top]
        for name, t, pat, sc, ang in layers:
            y1 = ys[-1] - t
            if pat:
                n.HR(x0, y1, x1, ys[-1], pat, sc, ang)
            n.L(x0, y1, x1, y1, 'Узлы', lw=25)
            ys.append(y1)
        n.L(x0, top, x1, top, 'Узлы', lw=35)
        n.L(x1, ys[-1], x1, top, 'Тонкие', lw=13)
        if brk:
            n.brk_h(x0, x1, ys[-1])
        n.HR(x0 - 6, ys[-1], x0 - 1.0, top + 6, 'ANSI31', 0.35, 0, 8)            # стена
        n.R(x0 - 6, ys[-1], x0 - 1.0, top + 6, 'Узлы', lw=35)
        n.HR(x0 - 1.0, ys[2], x0, top, 'SOLID', 1, 0, 9)                          # демпферная лента
        n.R(x0 - 1.0, ys[2], x0, top, 'Тонкие', lw=13)
        yc = ys[2] + 1.0                                                          # трубы ТП в низу стяжки
        xs = []
        x = x0 + 4.5
        while x < x1 - 6:
            n.pipe(x, yc, 1.6, 'Т1' if len(xs) % 2 == 0 else 'Т2')
            xs.append(x)
            x += ufh_step
        return ys, yc, xs

    def callouts(ys, yc, xs, top):
        pos = [(1, 98, ys[0] - 1.0), (2, 98, ys[1] - 4.0), (3, xs[-1] + 0.8, yc), (4, 97, ys[2]),
               (5, 98, (ys[2] + ys[3]) / 2), (6, 98, (ys[3] + ys[4]) / 2), (7, 98, ys[4] - 7.0)]
        for k, px, py in pos:
            n.callout(k, px, py, 126, top + 4 - (k - 1) * 5.5)
        n.callout(8, 37.5, top - 3.0, 43.0, top + 4.5)

    # 1а — пол по грунту 1 этажа (толщины — допущение до экспликации полов)
    L1 = [('покрытие', 2.0, 'AR-PARQ1', 0.06, 0), ('стяжка', 10.0, 'AR-SAND', 0.04, 0),
          ('ЭППС', 10.0, 'INSUL', 0.6, 0), ('выравн.', 3.0, 'AR-SAND', 0.02, 0), ('плита', 15.0, 'AR-CONC', 0.05, 0)]
    top = 380.0
    ys, yc, xs = pie(top, 38, 106, L1, 15.0, '1а. 1 этаж — пол по грунту (покрытие — по экспликации АР)')
    n.level(75, top, '±0,000')
    n.chain_v(111, [ys[4], ys[3], ys[2], ys[1]], ['30', '100', '100'], side='right')
    n.dim_v(ys[4], ys[0], 117, '250', side='right')
    n.dim_h(xs[0], xs[1], yc - 5.5, 'шаг 100–300')
    callouts(ys, yc, xs, top)
    n.legend(131, 386, 70, [
        'Покрытие: доска 20 / плитка (с/у) — по экспликации АР',
        'Стяжка ц.-п. М200 с фиброй, 100 мм (над трубой ≈84 мм)',
        'Труба PE-Xa 16×2,0 с антидифф. слоем, шаг по листу 4',
        'Плёнка или мат с разметкой, крепление трубы скобами',
        'ЭППС 100 мм, λ ≤ 0,034 Вт/(м·°С)',
        'Гидроизоляция и выравнивающий слой ≈30 мм (АР/КР)',
        'Плита по грунту 300 мм (КР)',
        'Демпферная лента 8–10 мм на всю толщину стяжки',
    ], h=2.0)

    # 1б — пол по плите 2 этажа (санузлы 2.8, 2.9)
    L2 = [('покрытие', 1.5, 'ANSI37', 0.25, 0), ('стяжка', 10.0, 'AR-SAND', 0.04, 0),
          ('ЭППС', 5.0, 'INSUL', 0.3, 0), ('звукоиз.', 3.5, 'DOTS', 0.25, 0), ('плита', 20.0, 'AR-CONC', 0.05, 0)]
    top = 312.0
    ys2, yc2, xs2 = pie(top, 38, 106, L2, 10.0, '1б. 2 этаж — пол по плите перекрытия (с/у 2.8, 2.9)', brk=False)
    n.level(75, top, '+4,050')
    n.level(75, ys2[5], '+3,650', down=True)
    n.chain_v(111, [ys2[3], ys2[2], ys2[1]], ['50', '100'], side='right')
    n.dim_v(ys2[4], ys2[0], 117, '200', side='right')
    n.dim_v(ys2[5], ys2[4], 117, '200', side='right')
    callouts(ys2, yc2, xs2, top)
    n.legend(131, 318, 70, [
        'Плитка на клею 15 мм, обмазочная гидроизоляция (АР)',
        'Стяжка ц.-п. М200 с фиброй, 100 мм',
        'Труба PE-Xa 16×2,0, шаг 100 (ТП 2.8, 2.9; в комнатах — подводки к приборам в гофре)',
        'Плёнка с разметкой',
        'ЭППС 50 мм',
        'Звукоизоляционная подложка / выравнивание ≈35 мм (АР)',
        'Плита перекрытия 200 мм (КР)',
        'Демпферная лента 8–10 мм',
    ], h=2.0)
    n.T('Толщины слоёв — до экспликации полов, уточнить по АР', 30, 258, 2.2, 'left')


# ------------------------------------------------------------------ узел 2: внутрипольный конвектор у витража
def node2(n):
    x0, top = 222.0, 352.0           # x0 — плоскость витража (внутренняя грань), top — чистый пол; М 1:5
    n.title(210, 404, 'Узел 2. Внутрипольный конвектор у витража', 'М 1:5')
    s = 0.2
    # витраж (АР): профиль 70 мм, стекло
    n.R(x0 - 14, top - 50, x0, top + 40, 'Узлы', lw=35)
    n.L(x0 - 9, top + 1, x0 - 9, top + 40, 'Тонкие', lw=18)
    n.L(x0 - 5, top + 1, x0 - 5, top + 40, 'Тонкие', lw=18)
    n.brk_h(x0 - 14, x0, top + 40)
    # пирог пола (как узел 1а; плита показана частично)
    xe = 385.0
    lay = [(4.0, 'AR-PARQ1', 0.06), (20.0, 'AR-SAND', 0.04), (20.0, 'INSUL', 0.6), (6.0, 'AR-SAND', 0.02),
           (12.0, 'AR-CONC', 0.05)]
    xt0, xt1, depth = x0 + 100 * s, x0 + 400 * s, 150 * s       # отступ 100 от стекла, корпус 300×150
    ys = [top]
    for t, pat, sc in lay:
        ys.append(ys[-1] - t)
    g = 1.2                                                       # зазор вокруг корпуса
    for (t, pat, sc), ya, yb in zip(lay, ys[:-1], ys[1:]):
        for xa, xb in ((x0, xt0 - g), (xt1 + g, xe)):
            n.HR(xa, yb, xb, ya, pat, sc)
        if yb < top - depth - g:
            n.HR(xt0 - g, yb, xt1 + g, min(ya, top - depth - g), pat, sc)
        n.L(x0, yb, xt0 - g, yb, 'Узлы', lw=25)
        n.L(xt1 + g, yb, xe, yb, 'Узлы', lw=25)
    n.L(x0, top, xt0 - g, top, 'Узлы', lw=35)
    n.L(xt1 + g, top, xe, top, 'Узлы', lw=35)
    n.brk_h(x0, xe, ys[-1])
    n.brk_v(xe, ys[-1], top)
    # корпус конвектора, зазор (пена/раствор), опоры
    n.R(xt0 - g, top - depth - g, xt1 + g, top, 'Тонкие', lw=13)
    n.R(xt0, top - depth, xt1, top, 'Узлы', lw=50)
    for xx in (xt0 + 4, xt1 - 4):
        n.L(xx, top - depth, xx, top - depth - g, 'Узлы', lw=35)
    # решётка вровень с чистым полом
    for i in range(14):
        xx = xt0 + 1.5 + i * (xt1 - xt0 - 3) / 13
        n.R(xx - 0.6, top - 3, xx + 0.6, top, 'Тонкие', lw=13)
    # теплообменник (со стороны окна) и вентилятор (со стороны помещения)
    n.R(xt0 + 3, top - 26, xt0 + 22, top - 8, 'Узлы', lw=25, color=1)
    for i in range(7):
        xx = xt0 + 4.5 + i * 2.6
        n.L(xx, top - 25, xx, top - 9, 'Тонкие', lw=13, color=1)
    n.pipe(xt0 + 7, top - 17, 2.2, 'Т1')
    n.pipe(xt0 + 17, top - 17, 2.2, 'Т2')
    n.C(xt1 - 17, top - 17, 7.0, 'Узлы', lw=25)
    for a in range(0, 360, 45):
        r = math.radians(a)
        n.L(xt1 - 17 + 2.5 * math.cos(r), top - 17 + 2.5 * math.sin(r), xt1 - 17 + 6.5 * math.cos(r + 0.4),
            top - 17 + 6.5 * math.sin(r + 0.4), 'Тонкие', lw=13)
    # подводки в слое ЭППС (в гофре Ø32) и тёплый пол справа
    yg = ys[3] + 3.5
    for xx, sy in ((xt1 + 8, 'Т1'), (xt1 + 15, 'Т2')):
        n.C(xx, yg, 3.2, 'Тонкие', lw=13)
        n.pipe(xx, yg, 3.2, sy)
    for xx in (xt1 + 30, xt1 + 60):
        n.pipe(xx, ys[2] + 1.8, 3.2, 'Т1')
    # кабель 24 В
    n.PL([(xt1 - 5, top - depth + 2), (xt1 + 25, top - depth + 2), (xt1 + 25, ys[3] + 9)], 'Тонкие', lw=18, color=3)
    # размеры
    n.dim_h(x0, xt0, top + 9, '100', ext=top)
    n.dim_h(xt0, xt1, top + 9, '300', ext=top)
    n.dim_v(top - depth, top, xt0 - 6, '≤150', ext=xt0 - g)
    n.dim_v(ys[4], top, xe - 6, '250', side='left')
    n.level(370, top, '±0,000', side='left')
    # позиции: верхний ряд — над полом, нижний — под плитой
    top_row = [(8, xt0 + 7, top - 15.9, 238), (4, xt0 + 19, top - 12, 254), (3, xt0 + 30, top - 1.5, 270),
               (5, xt1 - 17, top - 10.5, 286), (9, xt1 + 25, top - 32, 322), (10, xt1 + 60, ys[2] + 1.8, 350)]
    for k, px, py, cx in top_row:
        n.callout(k, px, py, cx, 376)
    n.callout(1, x0 - 7, top + 25, 214, 383)
    low_row = [(6, xt0 + 4, top - depth - 0.6, 246), (2, xt1 - 10, top - depth, 276), (7, xt1 + 8, yg - 3.2, 306)]
    for k, px, py, cx in low_row:
        n.callout(k, px, py, cx, 283)
    n.legend(212, 276, 180, [
        'Витраж (АР)',
        'Конвектор внутрипольный КЗТО «Бриз В», вентилятор 24 В (тихий, решение Заказчика); в спальне 2.7 — КЗТО '
        '«Бриз» (естественная конвекция); корпус глубиной ≤150 мм, ширина — по каталогу КЗТО на мощность по листам '
        '3 и 5; отступ от витража '
        '100 мм (не менее указанного в паспорте)',
        'Решётка декоративная, вровень с чистым полом',
        'Теплообменник Cu-Al (со стороны окна)',
        'Вентилятор тангенциальный 24 В постоянного тока (со стороны помещения)',
        'Регулируемые опоры; зазор вокруг корпуса — монтажная пена/раствор',
        'Подводки PE-Xa 16×2,0 в теплоизоляции 6 мм и гофре — в слое ЭППС',
        'Термоклапан с сервоприводом и запорный вентиль — в корпусе, с торца',
        'Кабель 24 В постоянного тока от блока питания (раздел ЭОМ)',
        'Тёплый пол (узел 1а, лист 4)',
    ], h=2.0)


# ------------------------------------------------------------------ узел 3: коллекторные шкафы
def cabinet(n, x0, y0, W, Hh, n_dir, n_tp, label, s=0.05):
    w, h = W * s, Hh * s
    n.R(x0, y0, x0 + w, y0 + h, 'Узлы', lw=50)
    n.R(x0 + 1.2, y0 + 1.2, x0 + w - 1.2, y0 + h - 1.2, 'Тонкие', lw=13)
    ym = y0 + h * 0.52
    n.L(x0 + 1.2, ym, x0 + w - 1.2, ym, 'Узлы', lw=35)              # полка яруса
    # верхний ярус — прямой коллектор: подача (верх), обратка (ниже)
    ys, yr = y0 + h - 8, y0 + h - 15
    xa, xb = x0 + 9, x0 + w - 5
    for yy, col in ((ys, 1), (yr, 5)):
        n.R(xa, yy - 1.0, xb, yy + 1.0, 'Узлы', lw=25, color=col)
        for i in range(n_dir):
            xx = xa + 2.5 + i * (xb - xa - 5) / max(n_dir - 1, 1)
            n.L(xx, yy - 1.0, xx, yy - 3.2, 'Узлы', lw=25, color=col)
            if col == 1:
                n.C(xx, yy + 2.0, 0.8, 'Тонкие', lw=13)            # расходомер
    # вход снизу: стояки/магистраль по левой стороне до шаровых кранов
    for xx, yy, col in ((x0 + 4, ys, 1), (x0 + 6.5, yr, 5)):
        n.PL([(xx, y0), (xx, yy), (xa, yy)], 'Узлы', lw=25, color=col)
        n.PL([(xx - 1.1, yy - 3.5), (xx + 1.1, yy - 1.5), (xx + 1.1, yy - 3.5), (xx - 1.1, yy - 1.5)], 'Узлы',
             closed=True, lw=18)                                    # шаровой кран
    n.C(xb + 1.5, ys + 1.5, 0.7, 'Тонкие', lw=13)                    # воздухоотводчик
    # нижний ярус — смесительный узел и коллектор ТП
    yts, ytr = ym - 9, ym - 16
    xm = x0 + 13
    n.C(xm, ym - 22, 3.0, 'Узлы', lw=25)                              # насос
    n.PL([(xm - 1.6, ym - 23.6), (xm + 2.2, ym - 22), (xm - 1.6, ym - 20.4)], 'Узлы', closed=True, lw=13)
    n.PL([(xm - 2, yts + 1.5), (xm + 2, yts - 1.5), (xm + 2, yts + 1.5), (xm - 2, yts - 1.5)], 'Узлы',
         closed=True, lw=18)                                        # термостатический клапан
    n.C(xm, yts + 3.2, 1.2, 'Тонкие', lw=13)
    n.PL([(x0 + 4, ym - 1.2), (x0 + 4, yts), (xm - 2, yts)], 'Узлы', lw=25, color=1)
    n.PL([(xm, yts - 1.5), (xm, ym - 19)], 'Узлы', lw=25, color=1)
    n.PL([(xm + 3, ym - 22), (xm + 6, ym - 22), (xm + 6, yts), (xm + 8, yts)], 'Узлы', lw=25, color=6)
    n.PL([(x0 + 6.5, ym - 1.2), (x0 + 6.5, ytr), (xm + 8, ytr)], 'Узлы', lw=25, color=4)
    xa2, xb2 = xm + 8, x0 + w - 5
    for yy, col in ((yts, 6), (ytr, 4)):
        n.R(xa2, yy - 1.0, xb2, yy + 1.0, 'Узлы', lw=25, color=col)
        for i in range(n_tp):
            xx = xa2 + 2 + i * (xb2 - xa2 - 4) / max(n_tp - 1, 1)
            n.L(xx, yy - 1.0, xx, yy - 3.2, 'Узлы', lw=25, color=col)
            if col == 6:
                n.C(xx, yy + 2.0, 0.8, 'Тонкие', lw=13)
    n.C(xb2 + 1.5, yts + 1.5, 0.7, 'Тонкие', lw=13)
    # подписи и размеры
    n.T(label, x0 + w / 2, y0 + h + 9, 2.8, 'center')
    n.dim_h(x0, x0 + w, y0 - 6, f'≈{W}', ext=y0)
    n.dim_v(y0, y0 + h, x0 - 5, f'≈{Hh}', ext=x0)
    return dict(ys=ys, yr=yr, xa=xa, ym=ym, xm=xm, yts=yts, xa2=xa2, x0=x0, y0=y0, w=w, h=h)


def ft(t):
    return f'{t:.1f}'.rstrip('0').rstrip('.').replace('.', ',')


def node3(n, mix):
    n.title(405, 404, 'Узел 3. Коллекторные шкафы КШ-4 и КШ-2 (вид без дверцы)', 'М 1:20')
    a = cabinet(n, 420, 318, 750, 1250, 9, 2, 'КШ-4 (2 этаж, 2.6)')
    b = cabinet(n, 500, 316, 900, 1300, 8, 9, 'КШ-2 (1 этаж, 1.7)')
    for c, cx0 in ((a, 461), (b, 551)):
        pos = [(1, c['x0'] + c['w'] - 0.6, c['y0'] + c['h'] - 4), (2, c['xa'] + 12, c['ys'] + 1),
               (3, c['x0'] + 4, c['ys'] - 2.5), (4, c['xm'], c['ym'] - 22), (5, c['xa2'] + 6, c['yts'] + 1),
               (6, c['x0'] + c['w'] - 3.5, c['ys'] + 1.5), (7, c['xa'] + 14, c['yr'] - 2.0),
               (8, c['x0'] + c['w'] / 2, c['ym'])]
        pos.sort(key=lambda q: -q[2])                 # кружки сверху вниз в порядке точек — выноски не пересекаются
        for i, (k, px, py) in enumerate(pos):
            n.callout(k, px, py, cx0, c['y0'] + c['h'] + 2 - i * 7.6)
    t4, t2 = ft(mix['КШ-4']['t']), ft(mix['КШ-2']['t'])
    pumps = sorted({mix[k]['pump'] for k in ('КШ-4', 'КШ-2')})
    n.legend(407, 296, 178, [
        'Шкаф коллекторный встроенный двухъярусный (решение Заказчика): КШ-4 ≈750×1250×150, КШ-2 ≈900×1300×150 мм',
        'Верхний ярус — коллектор прямой 1" (70/55 °С) с расходомерами на подаче. КШ-4 — 9 выходов: Р-1–Р-3, Р-5, '
        'Кн-1, Кн-3, Пс-1, Пс-2 и резерв В6 (Кв-8 вместо Кн-2 по ЭП, решение Заказчика 19.10.2026); '
        'КШ-2 — 8 выходов: Кв-1–Кв-8',
        'Шаровые краны 1" на подаче и обратке; трубы входят снизу через основание шкафа',
        f'Смесительный узел с термостатическим клапаном и насосом класса {", ".join(pumps)}: подача ТП — '
        f'КШ-4 {t4} °С, КШ-2 {t2} °С',
        'Коллектор ТП с расходомерами: КШ-4 — 2 выхода (2.8, 2.9), КШ-2 — 9 выходов (1.10, 1.11, 1.8, 1.9-3)',
        'Автоматический воздухоотводчик и дренажный кран на каждой гребёнке',
        'Термоклапаны на обратке под сервоприводы; питание и управление — разделы ЭОМ, АК',
        'Полка между ярусами; подводки — снизу, в гофре',
    ], h=2.0)


# ------------------------------------------------------------------ узел 4: проход стояков через перекрытие
def node4(n):
    n.title(25, 200, 'Узел 4. Проход Т1, Т2 через перекрытие', 'М 1:10')
    n.T('(угол тамбура 1.7 — КШ-4 на 2 этаже)', 25, 189.5, 2.2, 'left')
    s = 0.1
    xw = 112.0                         # грань стены топочной (15,60)
    yb, yt = 120.0, 140.0              # низ и верх плиты
    yf = yt + 20.0                     # чистый пол 2 этажа
    n.HR(28, yb, xw, yt, 'AR-CONC', 0.05)
    n.R(28, yb, xw, yt, 'Узлы', lw=35)
    lay = [(3.5, 'DOTS', 0.25), (5.0, 'INSUL', 0.3), (10.0, 'AR-SAND', 0.04), (1.5, 'ANSI37', 0.25)]
    y = yt
    for t, pat, sc in lay:
        n.HR(28, y, xw, y + t, pat, sc)
        n.L(28, y + t, xw, y + t, 'Узлы', lw=25)
        y += t
    n.brk_v(28, yb, yf)
    n.HR(xw, 92, xw + 14, 185, 'ANSI31', 0.35)
    n.R(xw, 92, xw + 14, 185, 'Узлы', lw=35)
    n.brk_h(xw, xw + 14, 92)
    n.brk_h(xw, xw + 14, 185)
    # стояки: Т1 — 150 от стены, Т2 — 300 (лист 3: x 15,45 и 15,30)
    for x, sy in ((xw - 150 * s, 'Т1'), (xw - 300 * s, 'Т2')):
        col = 1 if sy == 'Т1' else 5
        lay_ = 'ОВ_Т1' if sy == 'Т1' else 'ОВ_Т2'
        # гильза Ø40: от низа плиты до +30 над чистым полом
        n.wipe(x - 2.0, yb, x + 2.0, yf + 3.0)
        n.R(x - 2.0, yb, x + 2.0, yf + 3.0, 'Узлы', lw=25)
        # труба 25
        for xx in (x - 1.25, x + 1.25):
            n.L(xx, 96, xx, 185, lay_, lw=35, color=col)
        # теплоизоляция 9 мм вне гильзы
        for ya, yb_ in ((96, yb), (yf + 3.0, 185)):
            n.R(x - 2.15, ya, x + 2.15, yb_, 'Тонкие', lw=13)
        n.T(sy, x, 189, 2.2, 'center')
    # короб ГКЛ на 1 этаже и низ КШ-4 на 2 этаже
    n.L(70, 92, 70, yb, 'Узлы', lw=35)
    n.L(70, yb - 0.1, 72, yb - 0.1, 'Узлы', lw=35)
    n.R(76, 178, xw, 185, 'Узлы', lw=35)
    n.HR(76, 178, xw, 185, 'SOLID', 1, 0, 2)
    n.T('КШ-4 (узел 3)', 94, 181.5, 2.0, 'center')
    # размеры и отметки
    n.dim_h(xw - 150 * s, xw, 172, '150', ext=None)
    n.dim_h(xw - 300 * s, xw - 150 * s, 172, '150', ext=None)
    n.dim_v(yf, yf + 3.0, 104, '30', ext=xw - 150 * s + 2.0, side='right', wipe=False)
    n.dim_v(yb, yt, 33, '200', side='right')
    n.dim_v(yt, yf, 33, '200', side='right')
    n.level(50, yf, '+4,050', side='left')
    n.level(62, yb, '+3,650', side='left', down=True)
    pos = [(1, xw - 300 * s + 2.15, 104, 89.5, 100), (2, xw - 300 * s - 2.0, yf + 2.5, 64, 170),
           (3, xw - 150 * s + 1.6, yb + 2.0, 105.5, 108), (4, 70, 100, 61, 100), (5, 45, yb + 5, 40, 112)]
    for k, px, py, cx, cy in pos:
        n.callout(k, px, py, cx, cy)
    n.legend(27, 86, 112, [
        'Т1, Т2 — PE-Xa 25×3,5 в теплоизоляции 9 мм (вне гильзы)',
        'Гильза ПВХ/ПП Ø40 (на 1–2 размера больше трубы), выступ над чистым полом 30 мм, низ — заподлицо с потолком',
        'Заделка зазора — негорючий уплотнитель (минвата, огнезащитный герметик)',
        'Короб ГКЛ с ревизионным лючком (АР)',
        'Плита перекрытия 200 (КР); пол 2 этажа — узел 1б',
    ], h=2.0)


# ------------------------------------------------------------------ узел 5: шахта Ш-2 (геометрия — как на листе 7)
def node5(n):
    n.title(145, 200, 'Узел 5. Шахта Ш-2 в плане', 'М 1:20')
    n.T('(у западной стены топочной, лист 7)', 145, 189.5, 2.2, 'left')
    s = 1 / 20
    W, Hh, t, te = 600 * s, 1500 * s, 100 * s, 200 * s     # в свету 600×1500 (АР); восточная стена — топочной, 200
    x0, y0 = 180.0, 98.0                                      # внутренний угол (ЮЗ) шахты
    xo0, yo0, xo1, yo1 = x0 - t, y0 - t, x0 + W + te, y0 + Hh + t
    n.HR(xo0, yo0, xo1, yo1, 'ANSI31', 0.3)
    n.wipe(x0, y0, x0 + W, y0 + Hh)
    n.R(xo0, yo0, xo1, yo1, 'Узлы', lw=50)
    n.R(x0, y0, x0 + W, y0 + Hh, 'Узлы', lw=50)
    P = lambda dx, dy: (x0 + dx * s, y0 + dy * s)            # noqa: E731  (мм натуры от ЮЗ угла)
    # 1 — канал 400×400 (АР) с воздуховодом выброса П1 Ø250
    n.R(*P(155, 45), *P(555, 445), 'Узлы', lw=35)
    c1 = P(355, 245)
    n.C(*c1, 125 * s, 'ОВ_В', lw=35, color=32)
    # 2 — вытяжка топочной Ø250
    c2 = P(300, 575)
    n.C(*c2, 125 * s, 'ОВ_В', lw=35, color=32)
    # 3 — каскадный дымоход котлов Viessmann Ø125
    c3 = P(300, 820)
    n.C(*c3, 62.5 * s, 'Узлы', lw=35)
    # 4 — дымоход пеллетного котла Ø180 в утеплённом канале Ø280
    c4 = P(400, 1080)
    n.C(*c4, 140 * s, 'Узлы', lw=35)
    n.C(*c4, 90 * s, 'Узлы', lw=25)
    n.H([(c4[0] + 90 * s * math.cos(a / 18 * math.pi), c4[1] + 90 * s * math.sin(a / 18 * math.pi))
         for a in range(36)], 'SOLID', 1, 0, 9)
    for cx, cy in (c1, c2, c3, c4):
        n.L(cx - 1.2, cy, cx + 1.2, cy, 'Тонкие', lw=13)
        n.L(cx, cy - 1.2, cx, cy + 1.2, 'Тонкие', lw=13)
    # размеры: от южной грани к центрам каналов и до северной; по x — оси каналов
    n.chain_v(xo0 - 6, [y0, c1[1], c2[1], c3[1], c4[1], y0 + Hh], ['245', '330', '245', '260', '420'], ext=x0)
    n.dim_h(x0, x0 + W, yo1 + 5, '600', ext=y0 + Hh)
    n.chain_h(yo0 - 6, [x0, c2[0], c4[0], x0 + W], ['300', '100', '200'], ext=y0)
    n.T('топочная 1.6', xo1 + 2, 99, 2.2, 'left')
    # север
    xn = xo1 + 20
    n.PL([(xn, yo1 - 9), (xn, yo1 + 1)], 'Тонкие', lw=25)
    n.PL([(xn - 1.5, yo1 - 2), (xn, yo1 + 1), (xn + 1.5, yo1 - 2)], 'Тонкие', lw=25)
    n.T('С', xn, yo1 + 4, 2.5, 'center')
    pos = [(1, c1[0] + 125 * s * 0.7, c1[1] + 125 * s * 0.7, 112), (2, c2[0] + 125 * s, c2[1], 128),
           (3, c3[0] + 62.5 * s, c3[1], 140), (4, c4[0] + 140 * s, c4[1], 153), (5, x0 + W + te * 0.5, 166, 166)]
    for k, px, py, cy in pos:
        n.callout(k, px, py, xo1 + 14, cy)
    n.legend(147, 82, 122, [
        'Выброс П1 — воздуховод Ø250 в канале 400×400 (АР)',
        'Вытяжка топочной — Ø250, оцинк. сталь (вместо Ø160 по ЭП)',
        'Дымоход котлов Viessmann (каскад, лист 7) — Ø125 вместо 2×Ø150 модели АР',
        'Дымоход пеллетного котла Ø180 в утеплённом канале Ø280 (АР), нерж. сталь',
        'Стенки шахты — негорючие (АР); зазоры — по паспортам дымоходов',
    ], h=2.0)


# ------------------------------------------------------------------ узел 6: щелевая решётка в стене спальни
def node6(n):
    n.title(275, 200, 'Узел 6. Щелевая решётка ЩП (ЩВ) в стене спальни', 'М 1:20')
    s = 0.05
    xw0, xw1 = 318.0, 318.0 + 200 * s          # перегородка 200 (АР)
    ys0, ys1 = 178.0, 178.0 + 200 * s          # плита покрытия 200
    n.HR(282, ys0, 398, ys1, 'AR-CONC', 0.05)
    n.R(282, ys0, 398, ys1, 'Узлы', lw=35)
    n.brk_v(282, ys0, ys1)
    n.brk_v(398, ys0, ys1)
    yb = ys0 - 900 * s                          # низ показанной части
    n.HR(xw0, yb, xw1, ys0, 'ANSI31', 0.35)
    # проём под камеру: решётка 150, верх — 75 ниже потолка спальни
    gt, gb = ys0 - 75 * s, ys0 - 225 * s
    n.wipe(xw0, gb - 1, xw1, gt + 1)
    n.L(xw0, yb, xw0, gb - 1, 'Узлы', lw=35)
    n.L(xw1, yb, xw1, gb - 1, 'Узлы', lw=35)
    n.L(xw0, gt + 1, xw0, ys0, 'Узлы', lw=35)
    n.L(xw1, gt + 1, xw1, ys0, 'Узлы', lw=35)
    n.brk_h(xw0, xw1, yb)
    # решётка (со стороны спальни) и камера статического давления
    n.R(xw0 - 1.2, gb - 0.8, xw0, gt + 0.8, 'Узлы', lw=35)
    for i in range(5):
        yy = gb + 0.8 + i * (gt - gb - 1.6) / 4
        n.L(xw0 - 1.2, yy, xw0, yy + 0.6, 'Тонкие', lw=13)
    xc1 = xw1 + 9.0
    n.R(xw0, gb, xc1, gt, 'Узлы', lw=35)
    n.L(xw0 + 0.5, gb + 0.6, xc1 - 0.5, gb + 0.6, 'Тонкие', lw=13, color=8)
    n.L(xw0 + 0.5, gt - 0.6, xc1 - 0.5, gt - 0.6, 'Тонкие', lw=13, color=8)
    n.HR(xw0 + 0.2, gb - 1.0, xw1 - 0.2, gb, 'INSUL', 0.15)
    n.HR(xw0 + 0.2, gt, xw1 - 0.2, gt + 1.0, 'INSUL', 0.15)
    # гибкая вставка
    xf1 = xc1 + 6.0
    n.L(xc1, gb + 0.5, xf1, gb + 0.5, 'Тонкие', lw=13)
    n.L(xc1, gt - 0.5, xf1, gt - 0.5, 'Тонкие', lw=13)
    for i in range(6):
        xx = xc1 + i
        n.L(xx, gb + 0.5, xx + 1, gt - 0.5, 'Тонкие', lw=13)
    # канальный блок К на подвесах, подшивка ГКЛ (зона 400)
    yp = ys0 - 400 * s
    n.L(xw1, yp, 398, yp, 'Узлы', lw=50)
    n.brk_v(398, yp - 2, yp + 2)
    ku0, ku1 = gb - 1.5, gb - 1.5 + 230 * s
    n.R(xf1, ku0, xf1 + 750 * s, ku1, 'Узлы', lw=50, color=6)
    n.T('К', xf1 + 375 * s, (ku0 + ku1) / 2, 2.5, 'center')
    for xx in (xf1 + 4, xf1 + 750 * s - 4):
        n.L(xx, ku1, xx, ys0, 'Тонкие', lw=18)
        n.R(xx - 0.8, ku1 + 2, xx + 0.8, ku1 + 3.4, 'Тонкие', lw=13)
    # подписи сторон
    n.T('спальня', 296, yb + 6, 2.2, 'center')
    n.T('(без подшивки)', 296, yb + 2.5, 2.0, 'center')
    n.T('гардеробная / холл', 375, yb + 6, 2.2, 'center')
    n.T('(подшивка, лист 10)', 375, yb + 2.5, 2.0, 'center')
    # размеры
    n.dim_v(gb, gt, xw0 - 8, '150', ext=xw0 - 1.2)
    n.dim_v(gt, ys0, xw0 - 8, '75', ext=xw0 - 1.2)
    n.dim_v(yp, ys0, 393, '400', side='right')
    n.dim_h(xw0, xw1, yb + 12, '200', ext=yb + 9)
    pos = [(1, xw0 - 0.6, gt - 2), (2, xw0 + 5, gt - 0.6), (3, xc1 + 3, gb + 1), (4, xf1 + 12, ku0 + 3),
           (5, 385, yp), (6, xw1 - 2.0, gt + 0.5), (7, xw0 + 7, yb + 20)]
    cxs = [(290, 168), (305, 190), (340, 190), (360, 190), (388, 166), (322, 190), (305, 160)]
    for (k, px, py), (cx, cy) in zip(pos, cxs):
        n.callout(k, px, py, cx, cy)
    n.legend(277, 128, 123, [
        'Решётка щелевая ≈800×150 (ЩП — подача, ЩВ — возврат), с регулятором расхода',
        'Камера статического давления, оцинк. сталь, внутри звукопоглощающая облицовка 10 мм',
        'Гибкая вставка (виброизолирующая)',
        'Канальный блок кондиционера на виброподвесах (лист 10)',
        'Подшивка ГКЛ, лючок обслуживания блока (АР)',
        'Заделка зазора в проёме — минвата и акустический герметик',
        'Перегородка (АР); проём ≈850×200 — задание АР',
    ], h=2.0)
    n.T('ЩВ — так же: решётка через камеру к всасывающему патрубку блока.', 277, 92, 2.0, 'left')
    n.T('Решётки ЩП и ЩВ разнесены по длине стены (лист 10).', 277, 88.5, 2.0, 'left')


def build():
    doc = new_doc()
    sh = RDSheet(doc, 'Лист', SHEET_LIST[SHEET_NO], SHEET_NO, SHEETS_TOTAL, fmt='А2')
    n = N(sh)
    import ov_boiler_scheme as BS                 # смесительные узлы: температура подачи ТП и класс насоса
    mix = BS.groups_calc()['mix']
    node1(n)
    node2(n)
    node3(n, mix)
    node4(n)
    node5(n)
    node6(n)
    # рамки ячеек (тонкие разделители)
    for x0, y0, x1, y1 in ((22, 210, 205, 412), (207, 210, 400, 412), (402, 210, 587, 412),
                           (22, 62, 141, 208), (143, 62, 271, 208), (273, 62, 400, 208)):
        n.R(x0, y0, x1, y1, 'Тонкие', lw=13, color=8)
    sh.notes(405, 203, 180, [
        'Узлы — схематично, размеры в мм. Толщины слоёв полов приняты до получения экспликации полов — уточнить по АР.',
        'Оборудование и материалы — по спецификации ОВ.СО, «или аналог». Конвекторы — КЗТО «Бриз В» (вентилятор '
        '24 В), в спальне 2.7 — «Бриз»; подбор по каталогу; '
        'коллекторные шкафы — по каталогу производителя коллекторов.',
        'Проходы трубопроводов и воздуховодов через перекрытия и стены — в гильзах и обрамлениях; заделка — '
        'негорючими материалами с пределом огнестойкости не ниже, чем у пересекаемой конструкции.',
        'Шахта Ш-2 — как на листе 7: дымоход котлов Viessmann (каскад, лист 7) Ø125 вместо 2×Ø150 по модели АР — '
        'чтобы поместилась вытяжка топочной Ø250 (задание АР). Дымоходы — по паспортам изготовителей, расстояния '
        'до сгораемых конструкций и между каналами — не менее паспортных; ревизии и сбор конденсата — в топочной.',
        'Электропитание вентиляторов конвекторов (24 В постоянного тока), насосов смесительных узлов и сервоприводов — по разделу ЭОМ, '
        'управление — по разделу АК.',
        'Перед заливкой стяжки — испытание систем отопления и ТП давлением (лист 4, прим. 6).',
    ], h=2.3)
    return doc


if __name__ == '__main__':
    doc = build()
    print(save_and_pdf(doc, os.path.join(OUT, 'ov_nodes.dxf')))
