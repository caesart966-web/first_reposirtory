"""И05.09.26-ОВ, лист 13. Баня. Схема КШ-Б. Узлы.

Схема и узлы рисуются прямо на листе (мм листа); расчётные величины — из ov_bath.bath_calc().
python3 sheets/ov_bath_scheme.py  ->  out/ov_bath_scheme.dxf + out/ov_bath_scheme_Лист.pdf
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from rdbase import new_doc, DPlan, RDSheet, save_and_pdf, fmt_num, SHEET_LIST, SHEETS_TOTAL  # noqa: E402
import ov_bath  # noqa: E402

OUT = os.path.join(ROOT, 'out')
SHEET_NO = 13


def n0(v):
    return fmt_num(v, 0)


class Sym:
    """Условные графические обозначения схем (ГОСТ 21.206) в мм листа."""

    def __init__(self, p):
        self.p = p

    def line(self, pts, lay, dashed=False, lw=None):
        self.p.m.add_lwpolyline(pts, dxfattribs=self._a(lay, dashed, lw))

    def _a(self, lay, dashed, lw):
        a = {'layer': lay}
        if dashed:
            a['linetype'] = 'ОВ_ШТРИХ'
            a['ltscale'] = 0.01            # тип линии задан в мм модели 1:100 -> на листе 1:1
        if lw:
            a['lineweight'] = lw
        return a

    def valve(self, x, y, vert=False, s=2.2, lay='ОВ_оборуд', fill=False):
        """Кран/клапан проходной: «бабочка»."""
        if vert:
            pts = [(x - s / 2, y - s), (x + s / 2, y - s), (x - s / 2, y + s), (x + s / 2, y + s)]
        else:
            pts = [(x - s, y + s / 2), (x - s, y - s / 2), (x + s, y + s / 2), (x + s, y - s / 2)]
        self.p.m.add_lwpolyline(pts, close=True, dxfattribs={'layer': lay})
        if fill:
            h = self.p.m.add_hatch(color=7, dxfattribs={'layer': lay})
            h.paths.add_polyline_path(pts, is_closed=True)

    def actuator(self, x, y, vert=False, s=2.2, lay='ОВ_оборуд', txt='М'):
        """Электропривод над клапаном."""
        if vert:
            self.p.m.add_line((x, y), (x - 3.2, y), dxfattribs={'layer': lay})
            self.p.m.add_lwpolyline([(x - 3.2 - 2.2, y - 1.4), (x - 3.2, y - 1.4), (x - 3.2, y + 1.4), (x - 5.4, y + 1.4)],
                                    close=True, dxfattribs={'layer': lay})
            self.p.t(x - 4.3, y, txt, 1.6, 'center', lay)
        else:
            self.p.m.add_line((x, y), (x, y + 3.2), dxfattribs={'layer': lay})
            self.p.m.add_lwpolyline([(x - 1.4, y + 3.2), (x + 1.4, y + 3.2), (x + 1.4, y + 5.4), (x - 1.4, y + 5.4)],
                                    close=True, dxfattribs={'layer': lay})
            self.p.t(x, y + 4.3, txt, 1.6, 'center', lay)

    def valve3(self, x, y, s=2.2, lay='ОВ_оборуд', third='down'):
        self.valve(x, y, s=s, lay=lay)
        d = -1 if third == 'down' else 1
        pts = [(x, y), (x - s / 2, y + d * 2 * s), (x + s / 2, y + d * 2 * s)]
        self.p.m.add_lwpolyline(pts, close=True, dxfattribs={'layer': lay})

    def pump(self, x, y, r=2.6, lay='ОВ_оборуд', dir_='right'):
        self.p.m.add_circle((x, y), r, dxfattribs={'layer': lay})
        if dir_ == 'right':
            pts = [(x - r * 0.6, y + r * 0.55), (x + r * 0.75, y), (x - r * 0.6, y - r * 0.55)]
        else:
            pts = [(x + r * 0.55, y - r * 0.6), (x, y + r * 0.75), (x - r * 0.55, y - r * 0.6)]
        self.p.m.add_lwpolyline(pts, close=True, dxfattribs={'layer': lay})

    def filt(self, x, y, s=2.2, lay='ОВ_оборуд'):
        self.p.m.add_lwpolyline([(x - s, y), (x, y + s), (x + s, y), (x, y - s)], close=True, dxfattribs={'layer': lay})
        self.p.m.add_line((x - s * 0.6, y - s * 0.6), (x + s * 0.6, y + s * 0.6), dxfattribs={'layer': lay})

    def meter(self, x, y, vert=True, lay='ОВ_оборуд'):
        """Расходомер (ротаметр) выхода коллектора."""
        if vert:
            self.p.m.add_lwpolyline([(x - 1.3, y - 2.0), (x + 1.3, y - 2.0), (x + 1.3, y + 2.0), (x - 1.3, y + 2.0)],
                                    close=True, dxfattribs={'layer': lay})
            self.p.m.add_line((x, y - 1.4), (x, y + 1.4), dxfattribs={'layer': lay})
            self.p.m.add_line((x - 0.6, y + 0.6), (x, y + 1.4), dxfattribs={'layer': lay})
            self.p.m.add_line((x + 0.6, y + 0.6), (x, y + 1.4), dxfattribs={'layer': lay})

    def sensor(self, x, y, txt='T', lay='ОВ_оборуд'):
        self.p.m.add_circle((x, y), 1.6, dxfattribs={'layer': lay})
        self.p.t(x, y, txt, 1.5, 'center', lay)

    def arrow(self, x0, y0, x1, y1, lay):
        self.p.arrow(x0, y0, x1, y1, lay, size=1.8)


def build():
    C = ov_bath.bath_calc()
    D, L = C['devices'], C['loops']
    doc = new_doc()
    sh = RDSheet(doc, 'Лист', SHEET_LIST[SHEET_NO], SHEET_NO, SHEETS_TOTAL)
    p = sh.p
    S = Sym(p)
    T1, T2, T11, T21 = 'ОВ_Т1', 'ОВ_Т2', 'ОВ_Т11', 'ОВ_Т21'

    # ====================================================================== схема (x 22…250, y 70…288)
    sh.title(136, 289.5, 'Принципиальная схема отопления бани (КШ-Б1, КШ-Б2)')
    YS, YR = 240.0, 232.0                    # магистрали Т1 (подача), Т2 (обратка) — вводная группа КШ-Б1
    X0, X1 = 30.0, 238.0
    # ввод Ecoflex
    S.line([(X0, YS), (X1, YS)], T1, lw=50)
    S.line([(X0, YR), (X1, YR)], T2, dashed=True, lw=50)
    p.rect(X0 - 2, YR - 4, X0 + 16, YS + 4, 'ОВ_оборуд')
    p.t(X0 + 7, YS + 6.0, 'Ecoflex', 1.8, 'center', 'ОВ_текст')
    p.label(24, 214, 'От РК топочной дома (листы 7, 8): Т1, Т2 PE-Xa 32×2,9', 1.9, at=(X0 + 7, YR - 4),
            lines=f'в общей оболочке Ecoflex Quattro, L≈17 м; G max {n0(C["b2"]["G"])} кг/ч')
    S.valve(X0 + 22, YS)
    S.valve(X0 + 22, YR)
    S.filt(X0 + 30, YS)
    p.t(X0 + 30, YS - 4, 'ФС', 1.6, 'center', 'ОВ_текст')
    S.sensor(X0 + 38, YS + 4.5, 'T')
    S.line([(X0 + 38, YS), (X0 + 38, YS + 2.9)], 'ОВ_оборуд')
    # --- Б2: трёхходовой переключающий клапан УК1 (приоритет ГВС)
    xb = 62.0
    S.valve3(xb, YS, third='up')
    p.t(xb + 3.5, YS - 3.5, 'УК1', 1.7, 'left', 'ОВ_марки')
    S.line([(xb, YS + 4.4), (xb, 250)], T1)
    p.rect(xb - 7, 250, xb + 9, 272, 'ОВ_оборуд')
    for i in range(5):
        yy = 253 + i * 3.6
        S.line([(xb - 4, yy), (xb + 6, yy + 1.8)], 'ОВ_оборуд')
    p.t(xb + 1, 274.0, 'Б2', 1.8, 'center', 'ОВ_марки')
    S.line([(xb + 6, 250), (xb + 6, 246), (xb + 14, 246), (xb + 14, YR)], T2, dashed=True)
    S.sensor(xb - 9.5, 262, 'T')
    for i, t_ in enumerate([f'Б2 — бойлер косвенного', 'нагрева 200 л, Ø520;', f'змеевик {C["b2"]["Q"] // 1000} кВт,',
                            f'G={C["b2"]["G"]} кг/ч, {C["b2"]["pipe"]}']):
        p.t(xb + 12, 270 - i * 3.0, t_, 1.7, 'left', 'ОВ_текст')
    # --- ТО-Д джакузи: зональный клапан УК2 + балансировочный
    xt = 112.0
    S.line([(xt, YS), (xt, 250)], T1)
    S.valve(xt, 244.5, vert=True)
    S.actuator(xt, 244.5, vert=True)
    p.t(xt + 2.5, 244.5, 'УК2', 1.7, 'left', 'ОВ_марки')
    S.valve(xt, 248.5, vert=True, fill=True)
    p.rect(xt - 2, 250, xt + 12, 268, 'ОВ_оборуд')
    S.line([(xt - 2, 250), (xt + 12, 268)], 'ОВ_оборуд')
    p.t(xt + 5, 270, 'ТО-Д', 1.8, 'center', 'ОВ_марки')
    S.line([(xt + 10, 250), (xt + 10, YR)], T2, dashed=True)
    S.line([(xt + 12, 264), (xt + 22, 264)], 'ОВ_Т3')
    S.line([(xt + 12, 254), (xt + 22, 254)], 'ОВ_Т4', dashed=True)
    for i, t_ in enumerate([f'ТО-Д — пластинчатый теплообменник {C["tod"]["Q"] // 1000} кВт (70/50 → 38/28 °С),',
                            f'G={C["tod"]["G"]} кг/ч, {C["tod"]["pipe"]}; вторичный контур — к фильтрации СПА',
                            '(по паспорту СПА, раздел ВК); УК2 — по таймеру СПА']):
        p.t(xt + 25, 266 - i * 3.0, t_, 1.7, 'left', 'ОВ_текст')
    p.t(X0 - 6, 279, 'УК1 — 3-ходовой переключающий клапан с приводом: приоритет загрузки Б2 по датчику бойлера.', 1.7,
        'left', 'ОВ_текст')

    # --- КШ-Б1: прямой коллектор
    xm0, xm1 = 140.0, 232.0
    ym_s, ym_r = 214.0, 206.0
    S.line([(xm0 - 8, YS), (xm0 - 8, ym_s), (xm0, ym_s)], T1, lw=50)
    S.line([(xm0 - 4, YR), (xm0 - 4, ym_r), (xm0, ym_r)], T2, dashed=True, lw=50)
    p.rect(xm0, ym_s - 1.3, xm1, ym_s + 1.3, T1, fill=1)
    p.rect(xm0, ym_r - 1.3, xm1, ym_r + 1.3, T2, fill=5)
    p.rect(xm0 - 12, 160, xm1 + 4, 226, 'ОВ_КШ')
    p.t(xm0 - 10, 223.5, 'КШ-Б1 — встроенный ШРВ-3 (≈750 мм), прямой коллектор 1"', 1.8, 'left', 'ОВ_марки')
    S.valve(xm0 - 8, 230, vert=True)
    S.valve(xm0 - 4, 230, vert=True)
    dev = ['Р-б1', 'Р-б2', 'Кв-б1', 'Кв-б2', 'Кв-б3', 'Пс-б1', 'Пс-б2']
    dx = (xm1 - xm0 - 8) / (len(dev) - 1)
    for i, n in enumerate(dev):
        x = xm0 + 4 + i * dx
        d = D[n]
        # подача: от гребёнки подачи вниз через расходомер; обратка — через термоклапан с сервоприводом
        S.line([(x - 1.6, ym_s - 1.3), (x - 1.6, 170)], T1)
        S.meter(x - 1.6, ym_s - 6)
        S.line([(x + 1.6, ym_r - 1.3), (x + 1.6, 170)], T2, dashed=True)
        S.valve(x + 1.6, ym_r - 6, vert=True, s=1.6)
        S.actuator(x + 1.6, ym_r - 6, vert=False, s=1.6)
        p.t(x, 166.5, n, 1.8, 'center', 'ОВ_марки')
        p.t(x, 162.8, f'{d["Q"]} Вт', 1.6, 'center', 'ОВ_текст')
        p.t(x, 192, f'{fmt_num(d["l_min"], 2)}', 1.5, 'center', 'ОВ_текст')
    p.t(xm0 - 10.5, 192, 'л/мин:', 1.5, 'left', 'ОВ_текст')
    S.line([(xm1 - 2, ym_s + 1.3), (xm1 - 2, ym_s + 4)], 'ОВ_оборуд')
    p.t(xm1 + 2.5, ym_s + 3.5, 'возд.', 1.5, 'left', 'ОВ_текст')

    # --- КШ-Б2: смесительный узел + коллектор ТП
    yu_s, yu_r = 128.0, 120.0
    xu0, xu1 = 150.0, 232.0
    xs = 136.0
    S.line([(xm0 - 8, ym_s), (xm0 - 8, 150), (xs, 150), (xs, 138)], T1)
    S.valve(xs, 140, vert=True)
    S.actuator(xs, 140, vert=True, txt='Т')
    S.line([(xs, 136), (xs, yu_s), (xs + 5, yu_s)], T11)
    S.pump(xs + 9, yu_s)
    S.line([(xs + 11.6, yu_s), (xu0, yu_s)], T11)
    S.sensor(xs + 17, yu_s + 4.2, 'T')
    S.line([(xs + 17, yu_s), (xs + 17, yu_s + 2.6)], 'ОВ_оборуд')
    S.line([(xu0, yu_r), (xs + 3, yu_r), (xs + 3, 112), (xm0 - 4, 112), (xm0 - 4, ym_r)], T21, dashed=True)
    S.line([(xs + 3, yu_r), (xs + 3, yu_s - 0.1)], 'ОВ_оборуд')
    S.valve(xs + 3, (yu_r + yu_s) / 2, vert=True, s=1.4, fill=True)
    p.rect(xu0, yu_s - 1.3, xu1, yu_s + 1.3, T11, fill=6)
    p.rect(xu0, yu_r - 1.3, xu1, yu_r + 1.3, T21, fill=4)
    p.rect(xs - 6, 76, xu1 + 4, 156, 'ОВ_КШ')
    mp = C['mixpump']
    p.t(xs - 4, 153.5, f'КШ-Б2 — встроенный ШРВ-3 (≈750 мм), смесительный узел ТП {fmt_num(C["tv"], 1)} °С и коллектор 7 вых.',
        1.8, 'left', 'ОВ_марки')
    p.label(122, 151, f'Н — насос смесительного узла: G={fmt_num(mp["m3h"], 2)} м³/ч, H={fmt_num(mp["H_m"], 1)} м;', 1.7,
            at=(xs + 9, yu_s + 2.6), lines='клапан с термоголовкой и выносным датчиком, байпас, защитный термостат 55 °С',
            anchor='right')
    loops = ['б7-1', 'б7-2', 'б6-1', 'б6-2', 'б2', 'б3', 'б4']
    dx = (xu1 - xu0 - 8) / (len(loops) - 1)
    for i, k in enumerate(loops):
        x = xu0 + 4 + i * dx
        l = L[k]
        S.line([(x - 1.6, yu_s - 1.3), (x - 1.6, 88)], T11)
        S.meter(x - 1.6, yu_s - 7)
        S.line([(x + 1.6, yu_r - 1.3), (x + 1.6, 88)], T21, dashed=True)
        S.valve(x + 1.6, yu_r - 6, vert=True, s=1.6)
        S.actuator(x + 1.6, yu_r - 6, vert=False, s=1.6)
        p.t(x, 84.5, k, 1.8, 'center', 'ОВ_марки')
        p.t(x, 81.0, f'{l["Q"]} Вт', 1.6, 'center', 'ОВ_текст')
        p.t(x, 78.0, f'L={n0(l["L"])}', 1.5, 'center', 'ОВ_текст')
        p.t(x, 101.5, fmt_num(l['l_min'], 2), 1.5, 'center', 'ОВ_текст')
    p.t(xs - 4.5, 98.0, 'л/мин:', 1.5, 'left', 'ОВ_текст')

    # ====================================================================== узлы (x 255…413)
    def ground(x0, x1, y):
        p.line(x0, y, x1, y, 'ОВ_оборуд', lw=35)
        for xx in range(int(x0) + 2, int(x1), 4):
            p.line(xx, y, xx - 2.0, y - 2.0, 'ОВ_оборуд', lw=13)

    def hatch_rect(x0, y0, x1, y1, pat='ANSI31', sc=0.5):
        p.rect(x0, y0, x1, y1, 'ОВ_оборуд', hatch=(pat, sc * 100.0, 45 if pat == 'ANSI31' else 0, 8))

    def node_entry(ox, top, title, inside, floor_build, slab, k=1000 / 30):
        """Ввод трубы Ecoflex через фундамент с подъёмом через плиту пола, М 1:30 (k мм на метр).
        ox — внутренняя грань стены, top — отметка чистого пола 0,000 (мм листа)."""
        p.t(ox - 1.15 * k, top + 23, title, 2.4, 'left', 'ОВ_текст')
        W_out, W_in = 1.15, 1.45
        # пол, стяжка, плита
        p.line(ox, top, ox + W_in * k, top, 'ОВ_оборуд', lw=35)
        hatch_rect(ox, top - floor_build * k, ox + W_in * k, top, 'AR-CONC', 0.03)
        hatch_rect(ox, top - (floor_build + slab) * k, ox + W_in * k, top - floor_build * k, 'ANSI31', 0.4)
        # стена и фундамент (по КР)
        hatch_rect(ox - 0.40 * k, top - 1.15 * k, ox, top + 0.55 * k, 'ANSI31', 0.9)
        ground(ox - W_out * k, ox - 0.40 * k, top - 0.25 * k)
        p.t(ox - 0.20 * k, top - 1.15 * k - 2.2, 'фундамент по КР', 1.6, 'center', 'ОВ_текст')
        # труба в оболочке: глубина до верха ≥0,8 м; гильза в фундаменте; отвод; подъём в гильзе через плиту
        D_ = 0.18 * k
        yax = top - 0.25 * k - 0.80 * k - D_ / 2
        xr = ox + 0.75 * k
        R = 0.50 * k
        for dy in (D_ / 2, -D_ / 2):
            p.line(ox - W_out * k, yax + dy, xr - R, yax + dy, 'ОВ_Т1', color=6)
        for r_ in (R - D_ / 2, R + D_ / 2):
            p.m.add_arc((xr - R, yax + R), r_, 270, 360, dxfattribs={'layer': 'ОВ_Т1', 'color': 6})
        for dx_ in (-D_ / 2, D_ / 2):
            p.line(xr + dx_, yax + R, xr + dx_, top + 0.12 * k, 'ОВ_Т1', color=6)
        p.rect(xr - D_ / 2 - 0.6, top + 0.12 * k, xr + D_ / 2 + 0.6, top + 0.12 * k + 1.6, 'ОВ_оборуд', fill=8)
        for dxp, lay in ((-1.2, 'ОВ_Т1'), (1.2, 'ОВ_Т2')):
            p.line(xr + dxp, top + 0.12 * k + 1.6, xr + dxp, top + 0.50 * k, lay, lw=35)
        p.rect(ox - 0.40 * k - 0.8, yax - D_ / 2 - 1.0, ox + 0.8, yax + D_ / 2 + 1.0, 'ОВ_оборуд')
        p.rect(xr - D_ / 2 - 1.0, top - (floor_build + slab) * k - 0.3, xr + D_ / 2 + 1.0, top, 'ОВ_оборуд')
        p.rect(ox - W_out * k, yax - D_ / 2 - 0.10 * k, ox - 0.42 * k, yax + D_ / 2 + 0.15 * k, 'ОВ_оборуд',
               hatch=('AR-SAND', 25.0, 0, 8))
        # глубина
        xd = ox - W_out * k + 3
        p.line(xd, top - 0.25 * k, xd, yax + D_ / 2, 'ОВ_размеры')
        p.t(xd - 1.3, (top - 0.25 * k + yax + D_ / 2) / 2, '≥800', 1.7, 'center', 'ОВ_размеры', rot=90)
        p.t(ox + 1.5, top + 1.0, '0,000', 1.7, 'bl', 'ОВ_размеры')
        # выноски (справа от узла)
        xl = ox + W_in * k + 2
        p.label(xl, top + 0.42 * k, inside, 1.6, at=(xr + 1.2, top + 0.38 * k))
        p.label(xl, top + 0.18 * k, 'Концевая манжета, 100–150 над полом', 1.6, at=(xr + D_ / 2 + 0.6, top + 0.15 * k))
        p.label(xl, top - 0.42 * k, 'Гильза в плите пола', 1.6, at=(xr + D_ / 2 + 1.0, top - 0.35 * k))
        p.label(xl, top - 0.80 * k, 'Отвод, R — по каталогу трубы', 1.6, at=(xr - R * 0.35, yax + R * 0.2))
        p.label(xl, top - 1.18 * k, 'Гильза с уплотнительным кольцом', 1.6, at=(ox + 0.8, yax + D_ / 2 + 1.0),
                lines='(комплект ввода производителя)')
        p.label(ox - W_out * k, top - 1.55 * k, 'Песок: подушка 100, засыпка 150 над трубой; лента — 300 над трубой', 1.6,
                at=(ox - 0.8 * k, yax - D_ / 2 - 0.05 * k))

    node_entry(296, 264, 'Узел 1. Ввод Ecoflex в баню (с/у б3, КШ-Б1). М 1:30',
               'Т1, Т2 — в КШ-Б1; санитарные — ВК', 0.10, 0.20)
    node_entry(296, 186, 'Узел 2. Ввод Ecoflex в дом: топочная 1.6 у сев. стены. М 1:30',
               'Т1, Т2 — к РК (листы 7, 8); санит. — ВК', 0.25, 0.30)
    p.t(296 - 1.15 * 1000 / 30, 186 + 18.5, 'Трасса — под полом хозблока 1.13 и под стеной 1.13/1.6; подъём — x≈19,25, y≈13,6 (оси дома)',
        1.6, 'left', 'ОВ_текст')

    # Узел 3 — КШ-Б, вид спереди, М 1:50
    ox, oy, k = 34, 92, 20.0
    p.t(ox - 2, oy + 41, 'Узел 3. КШ-Б1, КШ-Б2 в нише стены с/у. Вид. М 1:50', 2.4, 'left', 'ОВ_текст')
    p.line(ox - 4, oy, ox + 1.6 * k + 4, oy, 'ОВ_оборуд', lw=35)
    p.t(ox - 4, oy + 1.0, '0,000', 1.5, 'bl', 'ОВ_размеры')
    b1 = (ox + 0.80 * k, oy + 0.25 * k, ox + 1.55 * k, oy + 0.90 * k)        # КШ-Б1 (прямой) — у окна
    b2 = (ox + 0.05 * k, oy + 0.25 * k, ox + 0.80 * k, oy + 1.50 * k)        # КШ-Б2 (ТП) — два яруса
    for (x0, y0, x1, y1), nm in ((b1, 'КШ-Б1'), (b2, 'КШ-Б2')):
        p.rect(x0, y0, x1, y1, 'ОВ_КШ')
        p.rect(x0 + 0.6, y0 + 0.6, x1 - 0.6, y1 - 0.6, 'ОВ_КШ')
        p.t((x0 + x1) / 2, y1 - 2.0, nm, 1.6, 'center', 'ОВ_марки')
        for i in range(7):
            xx = x0 + 2.5 + i * (x1 - x0 - 5) / 6
            p.line(xx, y0 + 0.6, xx, oy, 'ОВ_Т1' if i % 2 == 0 else 'ОВ_Т2', lw=13)
    p.line(b2[0] + 0.6, b2[1] + 0.62 * k, b2[2] - 0.6, b2[1] + 0.62 * k, 'ОВ_КШ', ltype='ОВ_ШТРИХ')
    p.line(b1[2] + 2.5, oy, b1[2] + 2.5, b1[1], 'ОВ_размеры')
    p.t(b1[2] + 3.6, oy + 0.125 * k, '250', 1.5, 'center', 'ОВ_размеры', rot=90)
    p.line(b2[0], b2[3] + 2.5, b2[2], b2[3] + 2.5, 'ОВ_размеры')
    p.t((b2[0] + b2[2]) / 2, b2[3] + 3.0, '≈750', 1.5, 'bc', 'ОВ_размеры')
    p.line(b1[0], b1[3] + 2.5, b1[2], b1[3] + 2.5, 'ОВ_размеры')
    p.t((b1[0] + b1[2]) / 2, b1[3] + 3.0, '≈750', 1.5, 'bc', 'ОВ_размеры')
    p.t(ox + 1.65 * k + 6, oy + 1.25 * k, 'КШ-Б2 — смесит. узел и', 1.6, 'left', 'ОВ_текст')
    p.t(ox + 1.65 * k + 6, oy + 1.25 * k - 3.0, 'коллектор ТП, при необход.', 1.6, 'left', 'ОВ_текст')
    p.t(ox + 1.65 * k + 6, oy + 1.25 * k - 6.0, 'увеличенной высоты;', 1.6, 'left', 'ОВ_текст')
    p.t(ox + 1.65 * k + 6, oy + 1.25 * k - 9.0, 'трубы — снизу, из пола;', 1.6, 'left', 'ОВ_текст')
    p.t(ox + 1.65 * k + 6, oy + 1.25 * k - 12.0, 'ниша и утепление — по АР', 1.6, 'left', 'ОВ_текст')

    # ====================================================================== баланс помещений (x 22…228, y 8…66)
    XN, YN, WN = 252, 126.5, 161
    R_ = C['rooms']
    rows = [['Пом.', 'Наименование', 't, °С', 'Q, Вт', 'tпола max', 'ТП, Вт', 'ТП по ЭП', 'Приборы', 'Q приб., Вт']]
    devs = {'б2': ['Р-б2'], 'б3': ['Пс-б1'], 'б4': ['Пс-б2'], 'б5': ['Р-б1'], 'б6': ['Кв-б1', 'Кв-б2'],
            'б7': ['Кв-б3']}
    for no in ['б2', 'б3', 'б4', 'б5', 'б6', 'б7']:
        r = ov_bath.ROOM[no]
        rr = R_.get(no)
        qd = sum(D[n]['Q'] for n in devs[no])
        rows.append([no, r['name'], str(r['ti']), str(r['Q']), f'{rr["lim"]} °С' if rr else '—',
                     str(rr['Q_ufh']) if rr else '—', str(rr['Q_ufh_rd']) if rr else '—', ', '.join(devs[no]),
                     str(qd)])
    rows.append(['', 'Итого баня', '', str(sum(ov_bath.ROOM[n]['Q'] for n in devs)), '',
                 str(C['Q_ufh']), '', '', str(C['Q_direct'])])
    widths = [10, 34, 10, 14, 16, 14, 16, 30, 18]
    sh.s.text('Тепловой баланс помещений бани (при -25 °С)', 22 + sum(widths) / 2, 68.5, h=2.5, align='center')
    sh.table(22, 66, widths, rows, row_h=5.0, head_h=6.5, h=1.9,
             aligns=['center', 'left', 'center', 'center', 'center', 'center', 'center', 'left', 'center'])
    sh.notes(XN, YN, WN, [
        f'Подача ТП {fmt_num(C["tv"], 1)} °С — наименьшая, при которой все петли не длиннее 90 м и с потерями '
        f'не более 20 кПа (минимум по нагрузке — {fmt_num(C["tv_min"], 1)} °С); предел температуры пола — СП 60.',
        'Загрузка Б2 — с приоритетом (УК1 по датчику бойлера); на время загрузки отопление и ТО-Д не работают. '
        'ТО-Д — по таймеру СПА (≈3 ч на нагрев 1,8 м³), с низшим приоритетом.',
        'Выходы коллекторов — расходомеры на подаче, термоклапаны под сервоприводы на обратке; сервоприводы — '
        'по комнатным датчикам (раздел автоматизации). Настройки — по таблице на листе 12.',
        'Ввод Ecoflex: глубина до верха трубы не менее 0,8 м, под проездом — футляр; гильзы, уплотнения и концевые '
        'манжеты — комплект производителя трубы. Отметки фундамента и плиты — по КР.',
        'Испытания — гидравлические, давлением 1,5 рабочего, не менее 0,6 МПа, до заливки стяжки (СП 73.13330).',
    ], h=1.85)
    return doc


if __name__ == '__main__':
    doc = build()
    print(save_and_pdf(doc, os.path.join(OUT, 'ov_bath_scheme.dxf')))
