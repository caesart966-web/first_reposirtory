"""И05.09.26-ОВ, лист 11. Схемы систем вентиляции и кондиционирования.

python3 sheets/ov_vent_schemes.py  ->  out/ov_vent_schemes.dxf + out/ov_vent_schemes_Лист.pdf

Схемы П1 (приток, вытяжка) — фронтальная диметрия по трассам листов 9–10 (x — вправо, y — под 45° с
коэффициентом 0,5, z — вверх с коэффициентом 1,4), без масштаба; фреон и дренаж — структурные схемы.
Схемы лежат в модели отдельной областью (x от 40 м) и показаны своими видовыми экранами (лист А2).
"""
import math
import re
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ov_vent1 as v1                                                    # noqa: E402
import ov_vent2 as v2                                                    # noqa: E402
from ov_vent1 import (new_doc, DPlan, RDSheet, SHEET_LIST, SHEETS_TOTAL, VS, VE, AC, RD, BRV, Z1, Z2, ZROOF,  # noqa
                      RIS_P, RIS_V, RIS_P27, SH2_CH, SH2_X, SH2_CX, DUCT_LAYER, dlabel, save_sheet, fmt_num,
                      VZ_X150, VZ_X200, VZ_Y_WALL, VZ_RISER, VZ_Z_HOOD, VZ_Z_BOX, VZ_Z_WALL, VZ_Z_SHAFT_TOP,
                      VZ_Z_CAP, MANGAL_SHAFT, VZ_L, vz_calc, P1_NAME, P1_BOX, P1_Z, P1_ZAX, P1_DROP_X,
                      P1_DROP, P1_ESP_SUP, P1_ESP_EXH, P1_ESP_MIN, P1_KV, P1_KV_DP)

SHEET_NO = 11
KS = 100                    # масштаб экрана схемы притока
KE = 125                    # масштаб экрана схемы вытяжки
KF = 125                    # масштаб экрана схемы фреона
C45 = 0.60                  # смещение по оси y (вправо-вверх под 45°)
ZS = 1.4                    # растяжение по высоте
ORG_S = (40.0, 0.0)         # начало схемы притока в модели, м
ORG_E = (40.0, -30.0)       # схема вытяжки
ORG_F = (40.0, -60.0)       # схема фреона


def proj(org, x, y, z):
    return (org[0] + x + C45 * y, org[1] + ZS * z + C45 * y)


def n1(v, d=1):
    return fmt_num(v, d)


class Axo:
    def __init__(self, p, org):
        self.p, self.org = p, org

    def P(self, x, y, z):
        return proj(self.org, x, y, z)

    def line3(self, pts3, kind, lw=50):
        lay = DUCT_LAYER.get(kind, kind)
        self.p.pl([self.P(*q) for q in pts3], lay, lw=lw)

    def text(self, x, y, z, s, h=1.8, al='left', layer='ОВ_текст', dx=0.0, dy=0.0, rot=0):
        X, Y = self.P(x, y, z)
        self.p.t(X + dx, Y + dy, s, h, al, layer, rot=rot)

    def sec_label(self, pts3, s, kind, h=1.7, where=0.5, up=True, seg=None, minlen=1.0):
        P = [self.P(*q) for q in pts3]
        if max(math.hypot(P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1]) for i in range(len(P) - 1)) < minlen:
            return
        if seg is None:
            best, seg = -1, 0
            for i in range(len(P) - 1):
                L = math.hypot(P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1])
                if L > best:
                    best, seg = L, i
        (x0, y0), (x1, y1) = P[seg], P[seg + 1]
        mx, my = x0 + (x1 - x0) * where, y0 + (y1 - y0) * where
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        if ang > 90.01 or ang < -89.99:
            ang += 180
        off = self.p.H(h * 0.9) / self.p.unit
        sgn = 1 if up else -1
        if abs(ang) % 90 > 1:          # наклонный участок — подпись горизонтально, сбоку
            self.p.t(mx - off * 0.6 * sgn, my + off * 0.6 * sgn, s, h, 'right' if up else 'left',
                     DUCT_LAYER.get(kind, kind))
            return
        nx, ny = -math.sin(math.radians(ang)), math.cos(math.radians(ang))
        self.p.t(mx + nx * off * sgn, my + ny * off * sgn, s, h, 'center', DUCT_LAYER.get(kind, kind), rot=ang)

    def num(self, pts3, n, where=0.5, seg=0, side=1):
        """Номер участка основного направления — в кружке."""
        P = [self.P(*q) for q in pts3]
        (x0, y0), (x1, y1) = P[seg], P[seg + 1]
        mx, my = x0 + (x1 - x0) * where, y0 + (y1 - y0) * where
        L = math.hypot(x1 - x0, y1 - y0) or 1
        nx, ny = -(y1 - y0) / L, (x1 - x0) / L
        r = self.p.H(2.0) / self.p.unit
        cx, cy = mx + nx * r * 1.9 * side, my + ny * r * 1.9 * side
        self.p.circle(cx, cy, 0, 'ОВ_марки', r_paper=2.0)
        self.p.t(cx, cy, str(n), 2.0, 'center', 'ОВ_марки')

    def terminal(self, x, y, z, kind, txt, al='left', dz=-0.35, h=1.7, tdx=0.12, tdy=0.0):
        """Концевое устройство: короткий отвод вниз и треугольник (решётка), подпись."""
        lay = DUCT_LAYER.get(kind, kind)
        X0, Y0 = self.P(x, y, z)
        X1, Y1 = self.P(x, y, z + dz)
        self.p.pl([(X0, Y0), (X1, Y1)], lay, lw=35)
        s = self.p.H(1.4) / self.p.unit
        self.p.poly([(X1 - s, Y1), (X1 + s, Y1), (X1, Y1 - s * 1.2)], lay, fill=v1.LAYERS[lay][0])
        self.p.t(X1 + (tdx if al == 'left' else -tdx), Y1 - s * 0.6 + tdy, txt, h, al, lay)

    def damper(self, x, y, z, name, layer, h=1.6):
        """Клапан на воздуховоде (вдоль x): прямоугольник поперёк линии с диагональю, привод — кружок."""
        X, Y = self.P(x, y, z)
        a = self.p.H(1.0) / self.p.unit
        b = self.p.H(1.8) / self.p.unit
        self.p.wipe(X - a, Y - b, X + a, Y + b)
        self.p.pl([(X - a, Y - b), (X + a, Y - b), (X + a, Y + b), (X - a, Y + b)], layer, closed=True, lw=35)
        self.p.pl([(X - a, Y - b), (X + a, Y + b)], layer, lw=35)
        self.p.circle(X, Y + b + a * 0.7, a * 0.7, layer, lw=25)
        self.p.t(X, Y + b + a * 1.4 + self.p.H(1.2) / self.p.unit, name, h, 'bc', layer)

    def box(self, x0, y0, x1, y1, z0, z1, name, layer='ОВ_оборуд'):
        """Установка — параллелепипед в проекции."""
        P = self.P
        f = [P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), P(x0, y0, z1)]
        b = [P(x0, y1, z0), P(x1, y1, z0), P(x1, y1, z1), P(x0, y1, z1)]
        self.p.pl(f, layer, closed=True, lw=50)
        self.p.pl([f[3], b[3], b[2], f[2]], layer, lw=35)
        self.p.pl([f[1], b[1], b[2]], layer, lw=35)
        cx = (f[0][0] + f[2][0]) / 2
        cy = (f[0][1] + f[2][1]) / 2
        self.p.t(cx, cy, name, 2.2, 'center', layer)

    def elev(self, x, y, z, txt, h=1.7, dx=0.25, side='right', shelf=6.0):
        X, Y = self.P(x, y, z)
        s = self.p.H(1.4) / self.p.unit
        self.p.poly([(X, Y), (X - s * 0.6, Y + s), (X + s * 0.6, Y + s)], 'ОВ_марки', fill=7, outline=True)
        if side == 'right':
            self.p.pl([(X - s * 0.6, Y + s), (X + s * shelf, Y + s)], 'ОВ_марки')
            self.p.t(X + dx, Y + s * 1.6, txt, h, 'bl', 'ОВ_марки')
        else:
            self.p.pl([(X - s * shelf, Y + s), (X + s * 0.6, Y + s)], 'ОВ_марки')
            self.p.t(X - dx, Y + s * 1.6, txt, h, 'br', 'ОВ_марки')


def z_of(sid, floor):
    return Z1 if floor == 1 else Z2


def p1_ends(P3):
    """Опуски к патрубкам П1: конец участка на +3,400 у торца П1 заменяется опуском на ось патрубка
    (два отвода). Возвращает новую ломаную и число точек, вставленных в начало (сдвиг номера отрезка)."""
    def at_face(q):
        x, y, z = q
        return (abs(z - Z1) < 1e-6 and P1_BOX[1] <= y <= P1_BOX[3]
                and (abs(x - P1_BOX[0]) < 1e-6 or abs(x - P1_BOX[2]) < 1e-6))

    def drop(q):
        x, y, _ = q
        xo = x - P1_DROP_X if abs(x - P1_BOX[0]) < 1e-6 else x + P1_DROP_X
        return [(xo, y, Z1), (xo, y, P1_ZAX), (x, y, P1_ZAX)]
    out, pre = list(P3), 0
    if at_face(out[0]):
        out = drop(out[0])[::-1] + out[1:]
        pre = 2
    if at_face(out[-1]):
        out = out[:-1] + drop(out[-1])
    return out, pre


def supply_scheme(p):
    p = DPlan(p.doc, k=KS)
    a = Axo(p, ORG_S)
    a.box(*P1_BOX, *P1_Z, 'П1')
    a.elev(P1_BOX[0], P1_BOX[1], P1_Z[0], f'низ П1 +{n1(P1_Z[0], 3)}', side='left', shelf=9.0, dx=0.25)
    crit = RD['vent']['supply_paths'][RD['vent']['crit_supply']]['path']
    numb = {sid: i + 1 for i, sid in enumerate(crit)}
    for sid, kind, pts, d, L in v1.NET1:
        if kind not in ('П', 'Н'):
            continue
        if sid in ('стояк П', 'стояк П2.7'):
            (x0, y0), (x1, y1) = pts
            P3 = [(x0, y0, Z1), (x1, y1, Z1), (x1, y1, Z2)]
            a.line3(P3, kind)
            a.sec_label(P3, f'{dlabel(d)}, {L}', kind, seg=1, where=0.55 if sid == 'стояк П' else 0.35,
                        up=(sid != 'стояк П'))
            if sid in numb:
                a.num(P3, numb[sid], seg=1, where=0.3, side=-1)
            continue
        P3, pre = p1_ends([(x, y, Z1) for x, y in pts])
        a.line3(P3, kind)
        if sid not in ('гр.1.10-в', 'гр.1.10-с', 'гр.1.10-з', '1.11-з'):
            a.sec_label(P3, f'{dlabel(d)}, {L}', kind, up=sid not in ('A-B', '1.2', 'Н', 'B-E', 'E-F', 'F-G', 'G-H', '1.11'))
        if sid in numb:
            a.num(P3, numb[sid], side=1, seg=pre)
    for sid, kind, pts, d, L in v2.NET2:
        if kind != 'П':
            continue
        P3 = [(x, y, Z2) for x, y in pts]
        a.line3(P3, kind)
        if sid not in ('2.5 (ЩП)', '2.4 (ЩП)', '2.7 (ЩП)'):
            a.sec_label(P3, f'{dlabel(d)}, {L}', kind, up=True)
        if sid in numb:
            a.num(P3, numb[sid], seg=0 if sid != '2эт-зап' else 1, side=1)
        if sid == '2эт-3.9':
            a.num(P3, numb['2.3 (ЩП)'], seg=1, where=0.4, side=-1)
    # концевые устройства
    for gx, gy, kind, L, dr, nm, wall in v1.GRILLES1:
        if kind == 'П':
            fresh = abs(gy - 7.75) < 0.01
            a.terminal(gx, 7.62 if fresh else gy, Z1, 'П', f'L={L}', dz=-0.10 if fresh else -0.35)
    for x, n, nm in ((0.45, '2.3', 'ЩП'), (8.15, '2.4', 'ЩП'), (11.85, '2.5', 'ЩП')):
        a.terminal(x, 6.58, Z2, 'П', f'{nm} {n}, 60')
    a.terminal(3.90, v2.YM, Z2, 'П', '2.2, 30')
    a.terminal(13.80, 9.88, Z2, 'П', 'в К-7 (2.7), 60', dz=-0.25)
    # наружный воздух
    a.text(19.80, 11.10, Z1, 'Н1, низ +2,600', 1.7, 'left', 'ОВ_Н', dx=0.20, dy=0.25)
    a.damper(P1_KV, 9.55, Z1, 'КВ-Н', DUCT_LAYER['Н'])
    a.elev(10.60, 6.75, Z1, f'+{n1(Z1, 3)}', dx=0.3)
    a.elev(7.00, v2.YM, Z2, f'+{n1(Z2, 3)}', dx=0.3)


def exhaust_scheme(p):
    p = DPlan(p.doc, k=KE)
    a = Axo(p, ORG_E)
    a.box(*P1_BOX, *P1_Z, 'П1')
    a.elev(P1_BOX[0], P1_BOX[1], P1_Z[0], f'низ П1 +{n1(P1_Z[0], 3)}', side='left', shelf=9.0, dx=0.25)
    crit = RD['vent']['exhaust_paths'][RD['vent']['crit_exhaust']]['path']
    numb = {sid: i + 1 for i, sid in enumerate(crit)}
    for sid, kind, pts, d, L in v1.NET1:
        if kind not in ('В', 'X'):
            continue
        if sid == 'стояк В':
            (x0, y0), (x1, y1) = pts
            P3 = [(x0, y0, Z2), (x0, y0, Z1), (x1, y1, Z1)]
            a.line3(P3, 'В')
            a.sec_label(P3, f'{dlabel(d)}, {L}', 'В', seg=0, where=0.5, up=False)
            a.num(P3, numb[sid], seg=0, where=0.3, side=1)
            continue
        if sid == 'Выброс':
            yc = SH2_CH[0][0]
            P3, _ = p1_ends([(x, y, Z1) for x, y in pts] + [(SH2_X, yc, Z1), (SH2_X, yc, ZROOF)])
            a.line3(P3, 'X')
            a.sec_label(P3, f'{dlabel(d)}, {L}', 'X', seg=len(P3) - 2, where=0.72, up=True)
            a.text(SH2_X, yc, ZROOF, 'оголовок ≈+9,000 (по АР)', 1.7, 'right', 'ОВ_Выброс', dx=-0.3)
            continue
        P3, pre = p1_ends([(x, y, Z1) for x, y in pts])
        a.line3(P3, kind)
        if sid not in ('1.4', '1.3', '1.8'):
            a.sec_label(P3, f'{dlabel(d)}, {L}', kind, up=sid not in ('С-B', 'D-С', 'E-D', 'кухня'),
                        seg=0 if sid == 'С-B' else None)
        if sid in numb:
            a.num(P3, numb[sid], side=-1)
    for sid, kind, pts, d, L in v2.NET2:
        if kind != 'В':
            continue
        P3 = [(x, y, Z2) for x, y in pts]
        a.line3(P3, kind)
        if sid not in ('2.6', '2.1', '2-зап-2', '2-сев'):
            a.sec_label(P3, f'{dlabel(d)}, {L}', kind, up=sid not in ('2-юг',))
        if sid in numb:
            a.num(P3, numb[sid], side=-1 if sid in ('2.1', '2-зап') else 1, where=0.5)
    # концевые устройства
    for gx, gy, kind, L, dr, nm, wall in v1.GRILLES1:
        if kind == 'В':
            a.terminal(gx, gy, Z1, 'В', f'L={L}', dz=-0.15 if gx == 14.80 else -0.35)
    for (x, y, L) in ((13.75, 8.25, 75), (18.00, 8.25, 75), (13.35, 10.80, 60), (11.00, 9.80, 90)):
        a.terminal(x, y, Z2, 'В', f'L={L}')
    a.terminal(9.75, 11.20, Z2, 'В', 'верх 2-го света, 120', dz=-0.45, al='right')
    # естественные и местные системы
    yc = SH2_CH[1][0]
    xc = SH2_CX['В2']
    a.line3([(15.66, yc, Z1 - 0.1), (xc, yc, Z1 - 0.1), (xc, yc, ZROOF - 0.35)], 'В', lw=35)
    a.text(xc, yc, Z1 + 1.6, f'В2 ест. Ø250, {BRV["L_exh"]}', 1.7, 'right', 'ОВ_В', dx=-0.25)
    vz_scheme(p, Axo(p, (ORG_E[0] + VZ_SHIFT, ORG_E[1])))
    a.elev(11.05, 2.00, Z1, f'+{n1(Z1, 3)}', dx=0.1)
    a.elev(16.75, 8.25, Z2, f'+{n1(Z2, 3)}', dx=0.2)


VZ_SHIFT = -4.85     # ВЗ — отдельная система: фрагмент сдвинут влево по X, чтобы не ложиться на сеть П1


def vz_scheme(p, a):
    """ВЗ по трассе (эскиз Заказчика 19.10.2026): зонт → Ø150 → переход Ø150/200 у стены → Ø200 сквозь стену
    по оси Д → стояк в шахте над мангалом → оголовок с зонтом выше кровли."""
    lay = DUCT_LAYER['В']
    xr, yr = VZ_RISER
    c1 = (VZ_X150, 12.12, VZ_Z_BOX)
    c2 = (VZ_X150, VZ_Y_WALL, VZ_Z_BOX)
    c3 = (VZ_X150, VZ_Y_WALL, VZ_Z_WALL)
    c4 = (xr, yr, VZ_Z_WALL)
    top = (xr, yr, VZ_Z_CAP)
    a.line3([(VZ_X150, 12.12, VZ_Z_HOOD), c1, c2, c3], 'В', lw=35)
    a.line3([c3, c4, top], 'В', lw=70)
    # зонт над плитой
    X, Y = a.P(VZ_X150, 12.12, VZ_Z_HOOD)
    p.pl([(X - 0.10, Y), (X + 0.10, Y), (X + 0.38, Y - 0.30), (X - 0.38, Y - 0.30)], lay, closed=True, lw=35)
    # обратный клапан на патрубке — штрих поперёк
    Xk, Yk = a.P(VZ_X150, 12.12, VZ_Z_HOOD + 0.17)
    p.pl([(Xk - 0.14, Yk - 0.07), (Xk + 0.14, Yk + 0.07)], lay, lw=35)
    # переход Ø150/200 у стены — короткая трапеция на оси
    X3, Y3 = a.P(*c3)
    p.pl([(X3, Y3 - 0.05), (X3 - 0.06, Y3 + 0.10), (X3 + 0.06, Y3 + 0.10), (X3, Y3 - 0.05)], lay, lw=25)
    # шахта над мангалом (плоскость стояка), верх — по АР
    x0, x1 = MANGAL_SHAFT[0], MANGAL_SHAFT[2]
    for xx in (x0, x1):
        p.pl([a.P(xx, yr, 3.65), a.P(xx, yr, VZ_Z_SHAFT_TOP)], 'ОВ_шахты', ltype='ОВ_ШТРИХ', lw=18)
    p.pl([a.P(x0, yr, VZ_Z_SHAFT_TOP), a.P(x1, yr, VZ_Z_SHAFT_TOP)], 'ОВ_шахты', ltype='ОВ_ШТРИХ', lw=18)
    # оголовок с зонтом
    Xt, Yt = a.P(*top)
    p.pl([(Xt - 0.32, Yt + 0.08), (Xt, Yt + 0.30), (Xt + 0.32, Yt + 0.08), (Xt - 0.32, Yt + 0.08)], lay, lw=35)
    # подписи и отметки
    s1, s2, tot, _ = vz_calc()
    a.text(VZ_X150, 12.12, VZ_Z_HOOD, f'ВЗ: зонт 500–600 м³/ч', 1.7, 'left', 'ОВ_В', dx=-0.38, dy=-0.55)
    a.text(VZ_X150, 12.12, VZ_Z_HOOD, 'обр. клапан Ø150', 1.7, 'left', 'ОВ_В', dx=-0.38, dy=-0.85)
    a.elev(VZ_X150, (12.12 + VZ_Y_WALL) / 2, VZ_Z_BOX, f'+{n1(VZ_Z_BOX, 3)}', side='left', shelf=5.0, dx=0.30)
    a.text(*c2, f'Ø150, {VZ_L}', 1.7, 'left', 'ОВ_В', dx=0.18, dy=0.62)
    a.text(*c3, 'переход Ø150/200', 1.7, 'left', 'ОВ_В', dx=0.25, dy=-0.05)
    a.elev(xr, (VZ_Y_WALL + yr) / 2, VZ_Z_WALL, f'+{n1(VZ_Z_WALL, 3)}', side='left', shelf=5.0, dx=0.30)
    a.text(x1, yr, (3.65 + VZ_Z_SHAFT_TOP) / 2, f'Ст. ВЗ Ø200, {VZ_L} м³/ч, изоляция НГ 50 мм', 1.7, 'center',
           'ОВ_В', dx=0.22, rot=90)
    a.text(x0, yr, (3.65 + VZ_Z_SHAFT_TOP) / 2, 'шахта над мангалом (АР)', 1.7, 'center', 'ОВ_шахты',
           dx=-0.22, rot=90)
    a.elev(x1, yr, VZ_Z_SHAFT_TOP, f'+{n1(VZ_Z_SHAFT_TOP, 3)} верх шахты (по АР, уточнить)', shelf=17.0,
           dx=0.15)
    a.elev(xr, yr, VZ_Z_CAP, f'+{n1(VZ_Z_CAP, 3)} низ зонта оголовка', shelf=13.0, dx=0.15)
    a.text(xr, yr, VZ_Z_CAP, 'Система ВЗ', 2.0, 'left', 'ОВ_В', dx=-0.30, dy=1.15)


def freon_scheme(p):
    p = DPlan(p.doc, k=KF)
    """Структурная схема фреонопроводов мини-VRV (без масштаба) и дренажа."""
    ox, oy = ORG_F
    F = {f['sec']: f for f in RD['ac']['freon']}

    def P(x, y):
        return (ox + x, oy + y)

    def pipe(a, b, sec, up=True, h=1.6):
        p.pl([P(*a), P(*b)], 'ОВ_Фреон', lw=50)
        f = F[sec]
        txt = f'Ж{n1(f["d_liq"], 2)}/Г{n1(f["d_gas"], 2)}, {n1(f["L"], 1)} м'
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        horiz = abs(b[1] - a[1]) < 1e-6
        if horiz:
            p.t(ox + mx, oy + my + (0.35 if up else -0.35), txt, h, 'center', 'ОВ_Фреон')
        elif abs(b[1] - a[1]) < 2.5:     # короткий отвод — подпись в две строки справа
            p.t(ox + mx + 0.22, oy + my + 0.08, f'Ж{n1(f["d_liq"], 2)}/Г{n1(f["d_gas"], 2)}', h, 'left',
                'ОВ_Фреон')
            p.t(ox + mx + 0.22, oy + my - 0.30, f'{n1(f["L"], 1)} м', h, 'left', 'ОВ_Фреон')
        else:
            p.t(ox + mx + (0.30 if up else -0.30), oy + my, txt, h, 'center', 'ОВ_Фреон', rot=90)

    def joint(xy, n):
        x, y = P(*xy)
        s = 0.22
        p.poly([(x - s, y), (x, y + s), (x + s, y), (x, y - s)], 'ОВ_Фреон', fill=6)
        p.t(x + 0.28, y + 0.30, n, 1.6, 'left', 'ОВ_Фреон')

    def unit(xy, name, cap, w=2.6, h=0.9):
        x, y = P(*xy)
        p.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, 'ОВ_Фреон', lw=35)
        p.t(x, y + 0.15, name, 2.0, 'center', 'ОВ_Фреон')
        p.t(x, y - 0.22, cap, 1.5, 'center', 'ОВ_Фреон')

    # НБ-1 слева, разветвитель Р1 в тамбуре 1.7
    unit((1.6, 6.0), 'НБ-1', 'Daikin мини-VRV 22,4 кВт', w=3.0, h=1.1)
    pipe((3.1, 6.0), (10.0, 6.0), 'НБ-1 → первый разветвитель (тамбур 1.7)')
    joint((10.0, 6.0), 'Р1')
    # 2 этаж — вверх, 1 этаж — вниз
    pipe((10.0, 6.0), (10.0, 9.0), 'разв. 1 → Ш-1 → 2 этаж', up=False)
    joint((10.0, 9.0), 'Р4')
    pipe((10.0, 9.0), (14.0, 9.0), '2 эт.: разв. → у К-6')
    joint((14.0, 9.0), 'Р5')
    pipe((14.0, 9.0), (18.5, 9.0), 'у К-6 → у К-5')
    joint((18.5, 9.0), 'Р6')
    pipe((18.5, 9.0), (23.0, 9.0), 'у К-5 → К-4')
    unit((24.4, 9.0), 'К-4', '2,8 кВт, 2.3', w=2.6)
    pipe((10.0, 9.0), (10.0, 11.0), '2 эт.: разв. → К-7', up=False)
    unit((10.0, 11.5), 'К-7', '2,8 кВт, 2.7')
    pipe((14.0, 9.0), (14.0, 11.0), 'отвод на К-6', up=False)
    unit((14.0, 11.5), 'К-6', '2,8 кВт, 2.5')
    pipe((18.5, 9.0), (18.5, 11.0), 'отвод на К-5', up=False)
    unit((18.5, 11.5), 'К-5', '2,8 кВт, 2.4')
    pipe((10.0, 6.0), (10.0, 3.0), 'разв. 1 → 1 этаж (до К-2)', up=False)
    joint((10.0, 3.0), 'Р2')
    pipe((10.0, 3.0), (14.0, 3.0), 'К-2 → разв. у К-3', up=False)
    joint((14.0, 3.0), 'Р3')
    pipe((10.0, 3.0), (10.0, 1.0), 'отвод на К-2', up=False)
    unit((10.0, 0.5), 'К-2', '5,6 кВт, 1.10')
    pipe((14.0, 3.0), (14.0, 1.0), 'разв. у К-3 → К-3', up=False)
    unit((14.0, 0.5), 'К-3', '3,6 кВт, 1.11')
    pipe((14.0, 3.0), (18.5, 3.0), 'разв. у К-3 → К-1', up=False)
    unit((19.9, 3.0), 'К-1', '5,6 кВт, 1.10')
    ac = RD['ac']
    p.t(ox + 0.1, oy + 12.4, f'Р1–Р6 — разветвители REFNET Daikin (по каталогу). Длина до дальнего блока '
        f'{n1(ac["L_far"])} м, общая {n1(ac["L_total"])} м, перепад высот {n1(ac["dH"])} м, '
        f'дозаправка ≈{n1(ac["charge_add"])} кг', 1.7, 'left', 'ОВ_текст')
    p.t(ox + 0.1, oy + 7.8, 'Ж — жидкость, Г — газ, Ø наружный, мм', 1.6, 'left', 'ОВ_текст')


def extents(doc):
    """Габариты трёх схем в модели (м) — по вершинам полилиний и центрам окружностей слоёв ОВ."""
    regs = [((ORG_S[1] - 2, ORG_S[1] + 28)), ((ORG_E[1] - 2, ORG_E[1] + 28)), ((ORG_F[1] - 3, ORG_F[1] + 16))]
    out = [[1e9, 1e9, -1e9, -1e9] for _ in regs]
    for e in doc.modelspace():
        if e.dxftype() == 'LWPOLYLINE':
            pts = [(q[0] / 1000, q[1] / 1000) for q in e.get_points('xy')]
        elif e.dxftype() == 'CIRCLE':
            pts = [(e.dxf.center[0] / 1000, e.dxf.center[1] / 1000)]
        else:
            continue
        for x, y in pts:
            if x < 30:
                continue
            for i, (lo, hi) in enumerate(regs):
                if lo <= y <= hi:
                    o = out[i]
                    o[0], o[1], o[2], o[3] = min(o[0], x), min(o[1], y), max(o[2], x), max(o[3], y)
    return out


def fit_k(bb, w, h, pad=(0.08, 0.10)):
    """Масштаб вида из ряда, при котором габарит + поля помещаются в экран w×h мм."""
    W = (bb[2] - bb[0]) * (1 + 2 * pad[0])
    H = (bb[3] - bb[1]) * (1 + 2 * pad[1])
    need = max(W * 1000 / w, H * 1000 / h)
    for k in (75, 80, 100, 110, 120, 125, 150, 175, 200):
        if k >= need:
            return k
    return 200


def build():
    doc = new_doc()
    p = DPlan(doc, k=KS)
    supply_scheme(p)
    exhaust_scheme(p)
    freon_scheme(p)

    sh = RDSheet(doc, 'Лист', SHEET_LIST[SHEET_NO], SHEET_NO, SHEETS_TOTAL, fmt='А2')
    bs, be, bf = extents(doc)

    def vp(bb, x0, y0, w, h, k, title):
        cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        sh.viewport(x0 + w / 2, y0 + h / 2, w, h, cx, cy, k=k)
        sh.s.text(title, x0 + w / 2, y0 + h + 3.5, h=3.0, align='center')
    vp(bs, 22, 282, 262, 122, KS, 'Система П1 (приток). Схема')
    vp(be, 287, 222, 126, 182, KE, 'Система П1 (вытяжка, выброс), В2, ВЗ. Схема')
    vp(bf, 22, 152, 262, 118, KF, 'Схема фреонопроводов мини-VRV (без масштаба)')

    # таблица оборудования (справа)
    x0, w = 416, 172
    rows = [['Поз.', 'Наименование и техническая характеристика', 'Кол.', 'Примечание']]
    v = RD['vent']
    rows += [
        ['П1', f'Приточно-вытяжная установка {P1_NAME} (рекуперация тепла и влаги) или аналог: трехступенчатый '
               f'пластинчатый рекуператор, 750 м³/ч ном., рабочая точка {v["L_unit"]} м³/ч; сеть {n1(P1_ESP_SUP, 0)}/'
               f'{n1(P1_ESP_EXH, 0)} Па (приток/вытяжка), напор установки при {v["L_unit"]} м³/ч — по графику Turkov, '
               f'не менее {P1_ESP_MIN} Па; водяной нагреватель (2 ряда) со смесительным узлом в комплекте, '
               f'≈{n1(v["Q_heater_sel"] / 1000)} кВт (70/50 °С); патрубки Ø250; ≈1500×1080×610 мм, ≈145 кг; '
               '220 В, ≈0,8 кВт; дренаж конденсата — через сифон', '1',
         'выбор Заказчицы 20.10.2026; данные — по паспорту Turkov'],
        ['КВ-Н', 'Клапан воздушный Ø250 с электроприводом 230 В с возвратной пружиной, нормально закрыт — '
                 'на воздуховоде Н у П1', '1', 'если встроен в Turkov — не ставить'],
        ['НБ-1', 'Наружный блок мини-VRV Daikin серии VRV-S, тепловой насос, Qх = 22,4 кВт, ночной '
                 'малошумный режим', '1', 'модель — по каталогу Daikin или аналог'],
        ['К-1, К-2', f'Внутренний блок канальный тонкий Daikin серии FXDQ, Qх = 5,6 кВт, ≈{AC["К-1"]["air"]} м³/ч',
         '2', 'типоразмер — по каталогу Daikin'],
        ['К-3', f'То же, Qх = 3,6 кВт, ≈{AC["К-3"]["air"]} м³/ч', '1', 'то же'],
        ['К-4…К-7', f'То же, Qх = 2,8 кВт, ≈{AC["К-4"]["air"]} м³/ч', '4', 'то же'],
        ['Р1…Р6', 'Разветвитель фреоновый REFNET Daikin', '6', 'по каталогу Daikin'],
        ['ШГ', 'Шумоглушитель круглый Ø250, L = 600 мм', '2', 'на П и В у П1, между опуском и стеной'],
        ['РР', 'Регулятор расхода (ирисовый клапан) Ø100–Ø200', '20', 'на ответвлениях'],
        ['ВЗ', 'Кухонный зонт 500–600 м³/ч (поставка Заказчика), обратный клапан Ø150, Ø150 → Ø200 в шахте '
               'над мангалом, оголовок с зонтом выше кровли', '1', 'зонт — не менее 200 Па при 600 м³/ч'],
        ['КК', 'Клапан компенсации Ø200 с электроприводом, сблокирован с ВЗ', '1', ''],
        ['ЩП, ЩВ', 'Решетка щелевая настенная 800×150 с регулированием; у ЩП — напорная камера', '4 + 4',
         'спальни 2.3–2.5, 2.7 (К-4…К-7)'],
    ]
    yb = sh.table(x0, 409, [16, 99, 12, 45], rows, h=1.8, heights=[5.5, 16.0] + [8.6] * (len(rows) - 2),
                  aligns=['center', 'left', 'center', 'left'])
    sh.s.text('Основное оборудование', x0 + w / 2, 412.0, h=2.5, align='center')

    def aero(title, paths, net, crit, term_dp, extra, x, y, ww):
        path = paths[crit]['path']
        r = [['№', 'Участок', 'L, м³/ч', 'Ø, мм', 'l, м', 'v, м/с', 'Δp, Па']]
        for i, sid in enumerate(path, 1):
            q = net[sid]
            r.append([str(i), sid, str(q['L']), str(q['d']), n1(q['len'], 1), n1(q['v'], 1), n1(q['dp'], 1)])
        r.append(['', 'решетка, регулятор', '', '', '', '', str(term_dp)])
        r.append(['', 'итого сеть', '', '', '', '', n1(paths[crit]['dp'], 1)])
        for t, vv in extra:
            r.append(['', t, '', '', '', '', vv])
        sh.s.text(title, x + ww / 2, y + 2.6, h=2.2, align='center')
        return sh.table(x, y, [6, 27, 11, 9, 8, 9, 11], r, row_h=4.8, head_h=4.8, h=1.6,
                        aligns=['center', 'left', 'center', 'center', 'center', 'center', 'center'])

    ya = yb - 7
    y1 = aero('Приток П1 — до ЩП 2.3 (основное направление)', v['supply_paths'], VS, v['crit_supply'], 45,
              [('наружный воздух + ШГ', n1(v['dp_intake'] + 10, 1)),
               ('опуски к П1 (Н, П), 4 отвода', n1(2 * P1_DROP, 1)),
               ('клапан КВ-Н', n1(P1_KV_DP, 1)),
               ('своб. напор, 700 м³/ч', n1(P1_ESP_SUP, 0))], x0, ya, 81)
    y2 = aero('Вытяжка П1 — от 2.1 (основное направление)', v['exhaust_paths'], VE, v['crit_exhaust'], 40,
              [('выброс через Ш-2 + ШГ', n1(v['dp_discharge'] + 10, 1)),
               ('опуски к П1 (В, выброс), 4 отвода', n1(2 * P1_DROP, 1)),
               ('своб. напор, 700 м³/ч', n1(P1_ESP_EXH, 0))], x0, y1 - 8, 81)
    # сеть ВЗ (кухонный зонт) — отдельная система
    s1, s2, vz_tot, _ = vz_calc()
    rz = [['№', 'Участок', 'L, м³/ч', 'Ø, мм', 'l, м', 'v, м/с', 'Δp, Па'],
          ['1', 'зонт → стена, Ø150', str(VZ_L), '150', n1(s1['len'], 1), n1(s1['v'], 1), n1(s1['dp'], 1)],
          ['2', 'стена → оголовок, Ø200', str(VZ_L), '200', n1(s2['len'], 1), n1(s2['v'], 1), n1(s2['dp'], 1)],
          ['', 'итого сеть ВЗ', '', '', '', '', n1(vz_tot, 1)],
          ['', 'зонт, не менее', '', '', '', '', '200']]
    sh.s.text('Вытяжка ВЗ — кухонный зонт (с местными)', x0 + 81 / 2, y2 - 8 + 2.6, h=2.2, align='center')
    sh.table(x0, y2 - 8, [6, 27, 11, 9, 8, 9, 11], rz, row_h=4.8, head_h=4.8, h=1.6,
             aligns=['center', 'left', 'center', 'center', 'center', 'center', 'center'])
    # дренаж
    cond = RD['ac']['condensate']
    out = {'К-1': '1.4', 'К-2': '1.4', 'К-3': '1.4', 'К-4': '2.9', 'К-5': '2.9', 'К-6': '2.9', 'К-7': '2.9'}
    rr = [['Блок', 'Конденсат, л/ч', 'Выпуск в сифон']]
    for c in cond:
        rr.append([c['name'], n1(c['l_h'], 2), f'пом. {out[c["name"]]} (ВК)'])
    yd = 205
    sh.s.text('Дренаж конденсата', 287 + 38, yd + 2.6, h=2.2, align='center')
    yd2 = sh.table(287, yd, [16, 24, 36], rr, row_h=4.6, head_h=4.8, h=1.6, aligns=['center', 'center', 'left'])
    sh.notes(x0 + 84, ya + 2.6, 85, [
        'Схемы П1 — в косоугольной проекции по трассам листов 9, 10, высоты условно увеличены; отметки — оси '
        'воздуховодов от ±0,000. Номера в кружках — участки основного направления (таблицы).',
        f'П1 — {P1_NAME} или аналог, низ ≈ +{n1(P1_Z[0], 3)}; воздуховоды с +3,400 опускаются к патрубкам '
        f'(≈ +{n1(P1_ZAX, 3)}) — по два отвода. Сеть при {v["L_unit"]} м³/ч с опусками: приток {n1(P1_ESP_SUP, 0)} Па, '
        f'вытяжка {n1(P1_ESP_EXH, 0)} Па; напор установки при {v["L_unit"]} м³/ч — по графику Turkov, '
        f'не менее {P1_ESP_MIN} Па. '
        'Регуляторы расхода настроить по расходам на схемах.',
        'Фреонопроводы — медные трубы для холодильной техники в изоляции из вспененного каучука; хладагент и '
        'дозаправка — по паспорту НБ-1; перед пуском — опрессовка азотом и вакуумирование.',
        'Дренаж — трубы ПП Ø32 с уклоном не менее 0,01 к выпуску, сифон с сухим затвором (ВК); '
        'при недостатке уклона — дренажная помпа.',
        'ВЗ — отдельная система кухонного зонта (эскиз Заказчика 19.10.2026), на схеме вытяжки сдвинута влево. '
        f'Сеть при {VZ_L} м³/ч ≈ {n1(vz_tot, 0)} Па (ζ: обратный клапан 1,0, отвод 0,3, переход Ø150/200 0,19, '
        'оголовок с зонтом 1,8) — зонт с располагаемым давлением не менее 200 Па. Ø200 от стены до оголовка — '
        'в изоляции НГ 50 мм; с дымоходом мангала не соединять, в свету не менее 130 мм.',
    ], h=1.7)
    # воздушный баланс по помещениям (рядом со схемой вытяжки)
    bal = [['Пом.', 'Наименование', 'П, м³/ч', 'В, м³/ч', 'Примечание']]
    sup = {}
    for no, nm, L in v1.CALC['SUP']:
        sup[no] = (nm, sup.get(no, ('', 0))[1] + L)
    exh = {}
    for no, nm, L in v1.CALC['EXH']:
        exh[no] = (exh.get(no, (nm, 0))[0], exh.get(no, (nm, 0))[1] + L)
    order = ['1.10', '1.11', '1.2', '1.3', '1.4', '1.8', '2.1', '2.2', '2.3', '2.4', '2.5', '2.6', '2.7', '2.8', '2.9']
    names = {r['no']: r['name'] for r in v1.CALC['rooms']}
    notes_b = {'1.10': 'В — кухня 90, верх 2-го света 120; ВЗ — отдельно', '2.3': 'через ЩП', '2.4': 'через ЩП',
               '2.5': 'через ЩП', '2.7': 'в К-7 → ЩП', '2.1': 'с перетоком из спален'}
    ts, te = 0, 0
    for no in order:
        Ls = sup.get(no, ('', 0))[1]
        Le = exh.get(no, ('', 0))[1]
        ts += Ls
        te += Le
        bal.append([no, re.sub(r'\s*\(.*', '', names.get(no, ''))[:26], str(Ls) if Ls else '—', str(Le) if Le else '—', notes_b.get(no, '')])
    bal.append(['', 'Итого П1', str(ts), str(te), 'баланс'])
    bal.append(['1.6', 'Топочная (ест.)', str(BRV['L_in']), str(BRV['L_exh']), 'ПН в двери, В2 в Ш-2'])
    sh.s.text('Воздушный баланс', 22 + 73, 141, h=2.5, align='center')
    sh.table(22, 138, [10, 38, 14, 14, 70], bal, row_h=4.6, head_h=4.8, h=1.6,
             aligns=['center', 'left', 'center', 'center', 'left'])
    return doc


if __name__ == '__main__':
    doc = build()
    print(save_sheet(doc, 'ov_vent_schemes'))
