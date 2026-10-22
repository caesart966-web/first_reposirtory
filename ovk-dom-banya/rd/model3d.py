"""И05.09.26-ОВ. 3D-модель вентиляции и кондиционирования дома — по трассам листов 9–11.

python3 model3d.py  ->  out/3d/model.json   — данные для просмотрщика (viewer3d/)
                        out/3d/I05-09-26-OV-3D.dxf — 3D-модель (сети — сетками POLYFACE), для DWG
                        out/3d/I05-09-26-OV-3D.ifc — IFC4 для Revit, Navisworks, Renga, BIM-просмотрщиков
                        out/3d/razvodka.txt — как разведены пересечения и что не помещается

Плановые трассы, сечения и расходы — те же данные, что рисуют листы 9–11 (ov_vent1, ov_vent2, ov_vent_schemes),
поэтому модель не расходится с чертежами. Высоты: оси воздуховодов +3,400 / +7,300 (как в РД), но не ниже
подшивки зоны (низ зоны + 30 мм на ГКЛ и зазор) и не выше низа плиты (−10 мм). Пересечения в плане разводятся
по высоте обходом («уткой») меньшего сечения; если по высоте не хватает — меньший круглый воздуховод на месте
пересечения становится плоским прямоугольным той же или большей площади; что не помещается и так — в отчёт.
Стены — штриховки стен из подложек АР03 и АР09 (выгрузка Revit), выдавлены на высоту этажа; проёмы окон и дверей
в разрезе плана — на всю высоту (упрощённо). Дренаж конденсата в модель не входит (листы 9, 10).
"""
import json
import math
import os
import sys

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'sheets'))
import ov_vent1 as v1                                                    # noqa: E402
import ov_vent2 as v2                                                    # noqa: E402
import ov_vent_schemes as vs                                             # noqa: E402
import ov_bath as vb                                                     # noqa: E402  лист 12: ВВ-б1, ВВ-б2
from ov_site import BX, BY                                               # noqa: E402  оси 1/А бани в осях дома (ГП01)

OUT = os.path.join(HERE, 'out', '3d')
Z1, Z2, ZROOF = v1.Z1, v1.Z2, v1.ZROOF
SLAB1, SLAB2 = 3.65, 7.55          # низ плиты над 1 этажом, низ плиты покрытия (АР, лист 9–10)
FL2 = 4.05                         # чистый пол 2 этажа
BOARD = 0.03                       # от низа подшивки до низа воздуховода: ГКЛ 12,5 мм + зазор
TOP = 0.01                         # от верха воздуховода до низа плиты
GAP = 0.01                         # между воздуховодами на пересечении
F_D = 0.05                         # фреонопроводы (жидкость + газ в изоляции) — одним «пучком» Ø50
ZF1, ZF2 = SLAB1 - TOP - F_D / 2, SLAB2 - TOP - F_D / 2
AC = v1.AC
BATH = 3                           # «этаж» бани: отдельное здание, сдвиг (BX; BY) от осей дома без поворота
WITH_BATH = '--bath' in sys.argv   # баню в модель не включаем (Заказчица 22.10.2026: «один небольшой воздуховод,
                                   # моделить не надо»); python3 model3d.py --bath — с баней
BATH_TOP = 2.80                    # стены бани в модели — до +2,800 (потолки +2,370…+2,750 по разрезам АР)

SYS = {   # система: (название, цвет RGB для просмотрщика, ACI для DXF)
    'П': ('П1 — приток', (37, 99, 235), 5),
    'В': ('П1 — вытяжка', (194, 65, 12), 30),
    'Н': ('П1 — наружный воздух', (22, 163, 74), 3),
    'X': ('П1 — выброс', (100, 116, 139), 8),
    'ВЗ': ('ВЗ — кухонный зонт', (146, 64, 14), 34),
    'В2': ('В2 — вытяжка топочной (естественная)', (180, 120, 60), 32),
    'Р': ('Кондиционирование: блоки К, КСД, воздуховоды', (192, 38, 211), 6),
    'F': ('Фреонопроводы мини-VRV', (219, 39, 119), 221),
    'ВВ': ('ВВ-б1, ВВ-б2 — вытяжка бани', (234, 88, 12), 30),
    'E': ('Оборудование', (148, 163, 184), 9),
}


# ---------------------------------------------------------------- зоны подшивки и пределы по высоте
def _low(low, depth, slab):
    if low.startswith('+'):
        return float(low[1:].replace(',', '.'))
    return slab - depth / 1000.0                     # «по АР» — по глубине зоны


ZONES = {1: [(Polygon(p), lab, _low(low, dep, SLAB1)) for p, lab, dep, low, what in v1.ZONES1],
         2: [(Polygon(p), lab, _low(low, dep, SLAB2)) for p, lab, dep, low, what in v2.ZONES2],
         BATH: []}


def zone_at(x, y, floor):
    pt = Point(x, y)
    for poly, lab, low in ZONES[floor]:
        if poly.buffer(1e-6).contains(pt):
            return lab, low
    return None, None


def zlim(x, y, floor):
    lab, low = zone_at(x, y, floor)
    zmax = {1: SLAB1 - TOP, 2: SLAB2 - TOP, BATH: BATH_TOP}[floor]
    zmin = (low + BOARD) if low is not None else {1: 0.0, 2: FL2, BATH: 0.0}[floor]
    return zmin, zmax


# ---------------------------------------------------------------- элементы
class Run:
    """Линейный элемент: воздуховод или труба. pts — 3D-ломаная (м); d — Ø, rect — (ширина, высота) в м."""

    def __init__(self, rid, sysk, pts, d=None, rect=None, name='', L=None, floor=1, kind='duct', flex=False,
                 clamp=True, label=None):
        self.id, self.sys, self.name, self.L, self.floor, self.kind = rid, sysk, name, L, floor, kind
        self.pts = [tuple(map(float, p)) for p in pts]
        self.d, self.rect, self.flex, self.clamp, self.label = d, rect, flex, clamp, label
        self.bumps = []            # (s0, s1 плато, s_a, s_b рампы, dz, flat (w,h) | None, причина)

    @property
    def rz(self):
        return self.d / 2 if self.d else self.rect[1] / 2

    @property
    def rxy(self):
        return self.d / 2 if self.d else self.rect[0] / 2

    def section(self):
        if self.d:
            return f'Ø{round(self.d * 1000)}'
        return f'{round(self.rect[0] * 1000)}×{round(self.rect[1] * 1000)}'

    # длина по ломаной
    def cum(self):
        c = [0.0]
        for a, b in zip(self.pts, self.pts[1:]):
            c.append(c[-1] + math.dist(a, b))
        return c


class Box:
    def __init__(self, bid, sysk, b, kind, name='', L=None, label=None, floor=1):
        x0, y0, z0, x1, y1, z1 = b
        self.id, self.sys, self.kind, self.name, self.L, self.label, self.floor = bid, sysk, kind, name, L, label, floor
        self.b = (min(x0, x1), min(y0, y1), min(z0, z1), max(x0, x1), max(y0, y1), max(z0, z1))


RUNS, BOXES, LABELS = [], [], []
CROSS = []                         # разводка пересечений — для листа 11 и отчёта
CLAMP = []                         # подъём осей по глубине зон


def run(*a, **k):
    r = Run(*a, **k)
    RUNS.append(r)
    return r


def box(*a, **k):
    b = Box(*a, **k)
    BOXES.append(b)
    return b


# ---------------------------------------------------------------- трассы П1 (лист 9, 10, 11)
def build_runs():
    for sid, kind, pts, d, L in v1.NET1:
        nm = f'{SYS[kind][0]}, участок {sid}'
        if sid in ('стояк П', 'стояк П2.7'):
            (x0, y0), (x1, y1) = pts
            run(sid, kind, [(x0, y0, Z1), (x1, y1, Z1), (x1, y1, Z2)], d=d / 1000, name=nm, L=L)
            continue
        if sid == 'стояк В':
            (x0, y0), (x1, y1) = pts
            run(sid, kind, [(x0, y0, Z2), (x0, y0, Z1), (x1, y1, Z1)], d=d / 1000, name=nm, L=L)
            continue
        if sid == 'Выброс':
            yc = v1.SH2_CH[0][0]
            P3, _ = vs.p1_ends([(x, y, Z1) for x, y in pts] + [(v1.SH2_X, yc, Z1), (v1.SH2_X, yc, ZROOF)])
            run(sid, kind, P3, d=d / 1000, name='П1 — выброс в Ш-2, оголовок выше кровли', L=L)
            continue
        P3, _ = vs.p1_ends([(x, y, Z1) for x, y in pts])
        if sid == 'Н':                                  # от камеры за решёткой Н1
            P3 = [(19.70, 11.10, Z1)] + P3[1:]
            nm = 'П1 — наружный воздух от решётки Н1'
        run(sid, kind, P3, d=d / 1000, name=nm, L=L)
    for sid, kind, pts, d, L in v2.NET2:
        P3 = [(x, y, Z2) for x, y in pts]
        if sid == '2-зап-2':                            # от КСД решётки верха второго света (низ +6,400)
            P3 = [(9.75, 11.20, 6.70)] + P3
        run(sid, kind, P3, d=d / 1000, name=f'{SYS[kind][0]}, участок {sid}', L=L, floor=2)
    # В2 — естественная вытяжка топочной в Ш-2
    yc, xc = v1.SH2_CH[1][0], v1.SH2_CX['В2']
    run('В2', 'В2', [(15.66, yc, Z1 - 0.1), (xc, yc, Z1 - 0.1), (xc, yc, ZROOF - 0.35)], d=0.25,
        name='В2 — естественная вытяжка топочной Ø250 в Ш-2', L=v1.BRV['L_exh'], clamp=False)
    # ВЗ — зонт кухни → Ø150 над шкафами → Ø200 сквозь стену по оси Д → шахта над мангалом → выше кровли
    x = v1.VZ_X200
    run('ВЗ-1', 'ВЗ', [(x, 12.12, v1.VZ_Z_HOOD), (x, 12.12, v1.VZ_Z_BOX), (x, v1.VZ_Y_WALL, v1.VZ_Z_BOX),
                       (x, v1.VZ_Y_WALL, v1.VZ_Z_WALL)], d=0.15, name='ВЗ — от зонта Ø150', L=v1.VZ_L,
        clamp=False)
    run('ВЗ-2', 'ВЗ', [(x, v1.VZ_Y_WALL, v1.VZ_Z_WALL), (x, v1.VZ_RISER[1], v1.VZ_Z_WALL),
                       (x, v1.VZ_RISER[1], v1.VZ_Z_CAP)], d=0.20, name='ВЗ — Ø200 в шахте над мангалом',
        L=v1.VZ_L, clamp=False)
    # шумоглушители ШГ Ø250 L = 600 (наружный диаметр корпуса ≈ 340)
    sx1 = v1.P1_BOX[0] - v1.P1_DROP_X - 0.10
    for yy, k in ((9.95, 'П'), (9.55, 'В')):
        run(f'ШГ-{k}', k, [(sx1 - 0.60, yy, Z1), (sx1, yy, Z1)], d=0.34, kind='silencer',
            name=f'Шумоглушитель ШГ Ø250, L = 600 ({SYS[k][0]})', clamp=False)
    # воздуховоды блоков К 250×150 (2 этаж)
    for nm, kind, pts in v2.KDUCTS2:
        P3 = [(x, y, 7.33) for x, y in pts]
        if nm != 'К-7 подача' and nm != 'К-7 возврат':  # возврат К-4…К-6 — к задней стенке блока
            n = nm.split()[0]
            P3.append((P3[-1][0], v2.KU2[n][3], 7.33))
        run(nm, 'Р', P3, rect=(0.25, 0.15), name=f'Воздуховод блока {nm} 250×150', floor=2, clamp=False)
    # фреон (жидкость + газ одним пучком в изоляции)
    def fr(rid, pts, z, floor, end_z=None, nm=None):
        P3 = [(x, y, z) for x, y in pts]
        if end_z is not None:
            P3.append((P3[-1][0], P3[-1][1], end_z))
        run(rid, 'F', P3, d=F_D, name=nm or 'Фреонопроводы', floor=floor, kind='pipe', flex=True, clamp=False)
    fd = v1.freon_d
    fr('Ф-ввод', [(20.95, 13.35)], 0.60, 1)
    RUNS[-1].pts = [(20.95, 13.35, 0.60), (21.03, 13.35, 0.60), (21.03, 13.35, ZF1), (19.60, 13.35, ZF1),
                    (19.60, 10.95, ZF1)]
    RUNS[-1].name = f"Фреон НБ-1 → разветвитель Р1, {fd('НБ-1 → первый разветвитель (тамбур 1.7)')}"
    fr('Ф-1эт', v1.FREON1, ZF1, 1, nm='Фреон 1 этажа (Р1 → К-2, Р2, Р3, К-1)')
    fr('Ф-стояк', v1.FREON1_RISER, ZF1, 1, nm=f"Фреон Р1 → Ш-1 → 2 этаж, {fd('разв. 1 → Ш-1 → 2 этаж')}")
    RUNS[-1].pts.append((v1.RIS_F[0], v1.RIS_F[1], ZF2))
    zu1 = {n: unit_z(n, 1) for n in v1.KU1}
    for br, n in zip(v1.FREON1_BR, ('К-2', 'К-1', 'К-3')):
        fr(f'Ф-{n}', br, ZF1, 1, end_z=(zu1[n][0] + zu1[n][1]) / 2, nm=f'Фреон — отвод к {n}, 6,35/12,7')
    fr('Ф-2эт', v2.FREON2, ZF2, 2, nm='Фреон 2 этажа (Р4 → К-6, К-5, К-4)')
    zu2 = {n: unit_z(n, 2) for n in v2.KU2}
    fr('Ф-К-7', v2.FREON2_K7, ZF2, 2, end_z=sum(zu2['К-7']) / 2, nm='Фреон — к К-7, 6,35/12,7')
    for n in ('К-4', 'К-5', 'К-6'):
        x0, y0, x1, y1 = v2.KU2[n]
        cx = (x0 + x1) / 2 + 0.15
        fr(f'Ф-{n}', [(cx, 7.78), (cx, y1)], ZF2, 2, end_z=sum(zu2[n]) / 2, nm=f'Фреон — отвод к {n}, 6,35/12,7')


def build_bath():
    """Баня (лист 12): ВВ-б1, ВВ-б2 — решётка под потолком → канальный вентилятор Ø100 → проход Ø110 в наружной
    стене → наружная решётка с жалюзи; ось +2,200. Координаты листа 12 (оси бани) + сдвиг по ГП01."""
    z = vb.FAN_Z
    for nm, fd in vb.FANS.items():
        (gx, gy), (fx, fy), (ox_, oy_) = fd['grille'], fd['fan'], fd['out']
        gx, gy, fx, fy, ox_, oy_ = gx + BX, gy + BY, fx + BX, fy + BY, ox_ + BX, oy_ + BY
        L = math.hypot(ox_ - gx, oy_ - gy)
        ux, uy = (ox_ - gx) / L, (oy_ - gy) / L
        room = {'б3': 'с/у б3', 'б7': 'помывочная б7'}[fd['room']]
        run(nm, 'ВВ', [(gx, gy, z), (ox_, oy_, z)], d=0.10, name=f'{nm} — вытяжка {room}, Ø100',
            L=fd['L'], floor=BATH, clamp=False)
        run(f'{nm}-вент', 'ВВ', [(fx - ux * 0.16, fy - uy * 0.16, z), (fx + ux * 0.16, fy + uy * 0.16, z)], d=0.25,
            kind='fan', name=f'{nm} — канальный вентилятор Ø100, {fd["L"]}/{fd["Lmax"]} м³/ч, с датчиком влажности',
            L=fd['L'], floor=BATH, clamp=False)
        RUNS[-1].label = f'{nm} {fd["L"]}/{fd["Lmax"]}'

        def plate(cx, cy, t, a=0.10):
            hx = t / 2 if abs(ux) > 0.5 else a
            hy = t / 2 if abs(uy) > 0.5 else a
            return (cx - hx, cy - hy, z - a, cx + hx, cy + hy, z + a)
        box(f'{nm}-реш', 'ВВ', plate(gx - ux * 0.015, gy - uy * 0.015, 0.03), 'grille',
            name=f'{nm}: решётка под потолком, {room}', L=fd['L'], label=f'L={fd["L"]}…{fd["Lmax"]}', floor=BATH)
        box(f'{nm}-нар', 'ВВ', plate(ox_ + ux * 0.025, oy_ + uy * 0.025, 0.05, a=0.125), 'grille',
            name=f'{nm}: наружная решётка с гравитационными жалюзи', floor=BATH)


def unit_z(n, floor):
    b = v1.KU1[n] if floor == 1 else v2.KU2[n]
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    lab, low = zone_at(cx, cy, floor)
    z0 = low + BOARD
    return (z0, z0 + 0.20)                           # FXDQ — высота корпуса 200 мм


# ---------------------------------------------------------------- высоты по зонам подшивки
def clamp_runs():
    notes = []
    for r in RUNS:
        if not r.clamp:
            continue
        lev = Z1 if r.floor == 1 else Z2
        lo, hi = -1e9, 1e9
        for a, b in zip(r.pts, r.pts[1:]):
            if abs(a[2] - lev) > 1e-6 or abs(b[2] - lev) > 1e-6:
                continue
            n = max(2, int(math.dist(a, b) / 0.1))
            for i in range(n + 1):
                t = i / n
                x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                zmin, zmax = zlim(x, y, r.floor)
                lo, hi = max(lo, zmin + r.rz), min(hi, zmax - r.rz)
        if lo > hi + 1e-6:
            notes.append(f'{r.id}: по высоте зоны не помещается ({r.section()})')
            continue
        z = min(max(lev, lo), hi)
        if abs(z - lev) > 1e-6:
            r.pts = [(x, y, z if abs(zz - lev) < 1e-6 else zz) for x, y, zz in r.pts]
            CLAMP.append(dict(id=r.id, sec=r.section(), sys=r.sys, floor=r.floor, z0=lev, z=z))
            notes.append(f'{r.id} ({r.section()}): ось {fmt(lev)} → {fmt(z)} — по глубине зоны подшивки')
    return notes


def fmt(z):
    return f'{z:+.3f}'.replace('.', ',')


# ---------------------------------------------------------------- разводка пересечений
def horiz_runs(r):
    """Горизонтальные участки ломаной: [(i0, i1, s0, s1, z)] — подряд идущие отрезки на одной отметке."""
    c = r.cum()
    out, i = [], 0
    P = r.pts
    while i < len(P) - 1:
        if abs(P[i][2] - P[i + 1][2]) < 1e-6 and math.dist(P[i][:2], P[i + 1][:2]) > 1e-9:
            j = i
            while j < len(P) - 1 and abs(P[j][2] - P[j + 1][2]) < 1e-6 and math.dist(P[j][:2], P[j + 1][:2]) > 1e-9:
                j += 1
            out.append((i, j, c[i], c[j], P[i][2]))
            i = j
        else:
            i += 1
    return out


def offset_at(r, s):
    """Смещение по высоте и сечение в точке s: побеждает обход с наибольшим |dz|."""
    best, flat = 0.0, None
    for s0, s1, sa, sb, dz, fl, why in r.bumps:
        if s < sa - 1e-6 or s > sb + 1e-6:
            continue
        if s0 - 1e-6 <= s <= s1 + 1e-6:
            k = 1.0
        elif s < s0:
            k = (s - sa) / max(s0 - sa, 1e-9)
        else:
            k = (sb - s) / max(sb - s1, 1e-9)
        v = dz * k
        if abs(v) > abs(best) + 1e-9:
            best = v
        if fl and s0 - 1e-9 <= s <= s1 + 1e-9:
            flat = fl
    return best, flat


def point_s(r, P):
    """s и z ломаной в плановой точке P (на горизонтальном участке)."""
    c = r.cum()
    for (i0, i1, s0, s1, z) in horiz_runs(r):
        for i in range(i0, i1):
            a, b = r.pts[i], r.pts[i + 1]
            seg = LineString([a[:2], b[:2]])
            if seg.distance(Point(P)) < 1e-6:
                return c[i] + math.dist(a[:2], P), (s0, s1), z
    return None, None, None


def connected_at(a, b, P, tol=0.02):
    """Точка P — стык (конец одного из элементов лежит в P)?"""
    for r in (a, b):
        for e in (r.pts[0], r.pts[-1]):
            if math.dist(e[:2], P) < tol:
                return True
    return False


def crossings():
    res = []
    for i, a in enumerate(RUNS):
        for b in RUNS[i + 1:]:
            if a.floor != b.floor or a.kind in ('silencer', 'fan') or b.kind in ('silencer', 'fan'):
                continue
            for (ia0, ia1, sa0, sa1, za) in horiz_runs(a):
                la = LineString([p[:2] for p in a.pts[ia0:ia1 + 1]])
                for (ib0, ib1, sb0, sb1, zb) in horiz_runs(b):
                    if abs(za - zb) > 0.8:
                        continue
                    lb = LineString([p[:2] for p in b.pts[ib0:ib1 + 1]])
                    x = la.intersection(lb)
                    if x.is_empty:
                        continue
                    pts = [x] if x.geom_type == 'Point' else [g for g in getattr(x, 'geoms', [x]) if g.geom_type == 'Point']
                    for p in pts:
                        if connected_at(a, b, (p.x, p.y)):
                            continue
                        res.append((a, b, (round(p.x, 4), round(p.y, 4))))
    return res


def z_at(r, P):
    s, rng, z = point_s(r, P)
    if s is None:
        return None, None, None
    dz, fl = offset_at(r, s)
    rz = (fl[1] / 2) if fl else r.rz
    return z + dz, rz, s


def add_bump(r, s, rng, dz, half, flat=None, why=''):
    ramp = max(abs(dz), 0.05)
    s0, s1 = max(rng[0], s - half), min(rng[1], s + half)
    # обход у конца участка, за которым элемент и так уходит вертикально в ту же сторону (стояк), —
    # плато до конца участка: без лишнего «вниз-вверх» перед стояком
    c = r.cum()
    for edge in (0, 1):
        se = rng[edge]
        if abs((s1 if edge else s0) - se) > ramp + 0.30:
            continue
        i = min(range(len(c)), key=lambda k: abs(c[k] - se))
        j = i + 1 if edge else i - 1
        if 0 <= j < len(r.pts) and math.dist(r.pts[i][:2], r.pts[j][:2]) < 1e-9 and \
                (r.pts[j][2] - r.pts[i][2]) * dz > 0:
            if edge:
                s1 = se
            else:
                s0 = se
    sa, sb = max(rng[0], s0 - ramp), min(rng[1], s1 + ramp)
    r.bumps.append((s0, s1, sa, sb, dz, flat, why))


def solve():
    log, fail = [], []
    for it in range(4):
        changed = False
        for a, b, P in crossings():
            za, rza, sa = z_at(a, P)
            zb, rzb, sb = z_at(b, P)
            if za is None or zb is None:
                continue
            gap = 0.005 if (a.flex or b.flex) else GAP
            need = rza + rzb + gap
            if abs(za - zb) >= need - 1e-6:
                continue
            # уступает гибкий (фреон), затем меньший по высоте сечения
            if a.flex != b.flex:
                Y, K = (a, b) if a.flex else (b, a)
            else:
                Y, K = (a, b) if (a.rz, a.d or 0) < (b.rz, b.d or 0) else (b, a)
            zY, rzY, sY = z_at(Y, P)
            zK, rzK, sK = z_at(K, P)
            _, rngY, zY0 = point_s(Y, P)
            _, rngK, zK0 = point_s(K, P)
            yminY, ymaxY = zlim(*P, Y.floor)
            yminK, ymaxK = zlim(*P, K.floor)
            if Y.flex:                                  # фреон может опуститься ниже подшивочной зоны? нет
                pass
            opts = []
            up = zK + need
            if up <= ymaxY - rzY + 1e-6:
                opts.append((abs(up - zY), 'Y', up, None))
            dn = zK - need
            if dn >= yminY + rzY - 1e-6:
                opts.append((abs(dn - zY), 'Y', dn, None))
            kt = ymaxK - rzK                            # больший — вверх, меньший — под ним
            if kt - need >= yminY + rzY - 1e-6:
                opts.append((abs(kt - zK) + abs(kt - need - zY), 'KY', kt, kt - need))
            kb = yminK + rzK                            # больший — вниз, меньший — над ним
            if kb + need <= ymaxY - rzY + 1e-6:
                opts.append((abs(kb - zK) + abs(kb + need - zY), 'KY', kb, kb + need))
            half_Y = K.rxy + Y.rz + 0.03                # плато шире чужого сечения на свой радиус: рампа 45°
            half_K = Y.rxy + K.rz + 0.03
            if opts:
                opts.sort(key=lambda o: o[0])
                _, who, z1, z2 = opts[0]
                if who == 'Y':
                    CROSS.append(dict(P=P, floor=Y.floor, Y=Y, K=K, zY=z1, zK=zK, flat=None))
                    add_bump(Y, sY, rngY, z1 - zY0, half_Y, why=f'обход {K.id}')
                    log.append(f'{Y.id} ({Y.section()}) {"над" if z1 > zK else "под"} {K.id} ({K.section()}) '
                               f'в точке ({P[0]:.2f}; {P[1]:.2f}): ось {fmt(zY)} → {fmt(z1)}')
                else:
                    CROSS.append(dict(P=P, floor=Y.floor, Y=Y, K=K, zY=z2, zK=z1, flat=None))
                    add_bump(K, sK, rngK, z1 - zK0, half_K, why=f'обход {Y.id}')
                    add_bump(Y, sY, rngY, z2 - zY0, half_Y, why=f'обход {K.id}')
                    log.append(f'{K.id} ({K.section()}) и {Y.id} ({Y.section()}) в точке ({P[0]:.2f}; {P[1]:.2f}): '
                               f'{K.id} — ось {fmt(z1)}, {Y.id} — ось {fmt(z2)}')
                changed = True
                continue
            # не помещается: меньший круглый воздуховод — плоским участком той же площади (больший — вверх)
            if Y.d and not Y.flex:
                kt = ymaxK - rzK
                h_av = (kt - rzK - GAP) - yminY
                h = math.floor(h_av * 100) / 100
                area = math.pi * Y.d ** 2 / 4
                if h >= 0.06:
                    w = math.ceil(area / h / 0.05) * 0.05
                    zc = yminY + h / 2
                    CROSS.append(dict(P=P, floor=Y.floor, Y=Y, K=K, zY=zc, zK=kt, flat=(w, h)))
                    add_bump(K, sK, rngK, kt - zK0, w / 2 + K.rz + 0.03, why=f'обход {Y.id}')
                    add_bump(Y, sY, rngY, zc - zY0, K.rxy + h / 2 + 0.05, flat=(w, h), why=f'плоский участок под {K.id}')
                    log.append(f'{Y.id} ({Y.section()}) × {K.id} ({K.section()}) в точке ({P[0]:.2f}; {P[1]:.2f}): '
                               f'по высоте зоны круглым не проходит — {K.id} вверх (ось {fmt(kt)}), {Y.id} на месте '
                               f'пересечения плоский {round(w * 1000)}×{round(h * 1000)} (площадь не меньше Ø), '
                               f'ось {fmt(zc)}')
                    changed = True
                    continue
            fail.append(f'{a.id} × {b.id} в точке ({P[0]:.2f}; {P[1]:.2f}): не помещается по высоте')
        if not changed:
            break
    return log, fail


def routing():
    """Только трассы и разводка (без стен и выгрузок) — для листа 11 и спецификации."""
    RUNS.clear(), BOXES.clear(), LABELS.clear(), CROSS.clear(), CLAMP.clear()
    build_runs()
    if WITH_BATH:
        build_bath()
    clamp_runs()
    log, fail = solve()
    if fail:
        raise SystemExit('3D: пересечения не развелись: ' + '; '.join(fail))
    return dict(cross=list(CROSS), clamp=list(CLAMP), fittings=fittings())


def fittings():
    """Фасонные части обходов: отводы 45° (по два на каждый подъём или опуск), плоские участки и переходы."""
    el45, flat_len, trans = {}, {}, {}
    for r in RUNS:
        if not r.d or r.kind != 'duct':
            continue
        for s0, s1, sa, sb, dz, fl, why in r.bumps:
            ramps = (s0 > sa + 1e-6) + (sb > s1 + 1e-6)
            d = round(r.d * 1000)
            el45[d] = el45.get(d, 0) + 2 * ramps
            if fl:
                k = (d, round(fl[0] * 1000), round(fl[1] * 1000))
                flat_len[k] = flat_len.get(k, 0.0) + (s1 - s0)
                trans[k] = trans.get(k, 0) + 2
    return dict(el45=el45, flat=flat_len, trans=trans)


ZONE_OF = {}


def zone_label(P, floor):
    lab, low = zone_at(P[0], P[1], floor)
    return lab or '—'


# ---------------------------------------------------------------- геометрия после разводки
def segments(r):
    """Отрезки с учётом обходов: [(p0, p1, (w, h) | None)] — None — круглое сечение r.d."""
    c = r.cum()
    if not r.bumps:
        return [(a, b, r.rect) for a, b in zip(r.pts, r.pts[1:])]
    brk = set()
    for s0, s1, sa, sb, dz, fl, why in r.bumps:
        brk.update((s0, s1, sa, sb))
    out = []
    for i, (a, b) in enumerate(zip(r.pts, r.pts[1:])):
        L = c[i + 1] - c[i]
        if L < 1e-9:
            continue
        horiz = abs(a[2] - b[2]) < 1e-6
        ss = [c[i], c[i + 1]] + ([s for s in brk if c[i] < s < c[i + 1]] if horiz else [])
        ss = sorted(set(round(s, 6) for s in ss))
        pts = []
        for s in ss:
            t = (s - c[i]) / L
            p = [a[k] + (b[k] - a[k]) * t for k in range(3)]
            dz, fl = offset_at(r, s) if horiz else (offset_at(r, c[i])[0] if t < 0.5 else offset_at(r, c[i + 1])[0], None)
            if not horiz:                                # вертикаль: концы — по смещению своих вершин
                dz = offset_at(r, c[i])[0] if t == 0 else offset_at(r, c[i + 1])[0]
            p[2] += dz
            pts.append((tuple(p), s))
        for (p0, s0), (p1, s1) in zip(pts, pts[1:]):
            sm = (s0 + s1) / 2
            _, fl = offset_at(r, sm) if horiz else (0, None)
            out.append((p0, p1, fl if fl else r.rect))
    # слить соосные отрезки одного сечения
    merged = []
    for p0, p1, sh in out:
        if merged:
            q0, q1, qs = merged[-1]
            d0 = [q1[k] - q0[k] for k in range(3)]
            d1 = [p1[k] - p0[k] for k in range(3)]
            n0, n1 = math.sqrt(sum(v * v for v in d0)), math.sqrt(sum(v * v for v in d1))
            if qs == sh and n0 > 1e-9 and n1 > 1e-9 and \
                    sum(d0[k] * d1[k] for k in range(3)) / n0 / n1 > 1 - 1e-9 and math.dist(q1, p0) < 1e-9:
                merged[-1] = (q0, p1, sh)
                continue
        merged.append((p0, p1, sh))
    return merged


def end_z(r, end):
    segs = segments(r)
    return segs[0][0][2] if end == 0 else segs[-1][1][2]


def z_on(r, P):
    """Высота оси элемента в плановой точке P после разводки (или None)."""
    for p0, p1, sh in segments(r):
        if abs(p0[2] - p1[2]) > 1e-6 and math.dist(p0[:2], p1[:2]) < 1e-9:
            continue
        seg = LineString([p0[:2], p1[:2]])
        if seg.length > 1e-9 and seg.distance(Point(P)) < 1e-4:
            t = math.dist(p0[:2], P) / seg.length
            return p0[2] + (p1[2] - p0[2]) * t
    return None


def stubs():
    """Врезки: конец элемента на другом элементе, оси на разных высотах — вертикальная вставка."""
    for r in RUNS:
        if r.kind != 'duct':
            continue
        for end in (0, -1):
            P = r.pts[end]
            ze = end_z(r, end)
            for o in RUNS:
                if o is r or o.floor != r.floor or o.kind != 'duct' or o.sys != r.sys:
                    continue
                zo = z_on(o, P[:2])
                if zo is None or abs(zo - ze) < 0.005 or abs(zo - ze) > 0.6:
                    continue
                RUNS.append(Run(f'{r.id}-врезка', r.sys, [(P[0], P[1], ze), (P[0], P[1], zo)], d=r.d, rect=r.rect,
                                name=f'{r.name} — врезка', floor=r.floor, kind='stub', clamp=False))
                break


# ---------------------------------------------------------------- оборудование, КСД, решётки
def build_boxes():
    # П1, клапан, наружный блок, зонт
    box('П1', 'E', (*v1.P1_BOX[:2], v1.P1_Z[0], *v1.P1_BOX[2:], v1.P1_Z[1]), 'unit',
        name=f'П1 — {v1.P1_NAME}, 700 м³/ч', label='П1 700 м³/ч')
    box('КВ-Н', 'Н', (v1.P1_KV - 0.10, 9.38, Z1 - 0.17, v1.P1_KV + 0.10, 9.72, Z1 + 0.17), 'damper',
        name='КВ-Н — клапан наружного воздуха с электроприводом')
    box('НБ-1', 'E', (20.50, 13.10, 0.15, 20.95, 14.10, 1.77), 'unit', name='НБ-1 — наружный блок Daikin мини-VRV 22,4 кВт',
        label='НБ-1')
    hx0, hy0, hx1, hy1 = v1.VZ_HOOD
    box('Зонт', 'ВЗ', (hx0, hy0, 1.80, hx1, hy1, v1.VZ_Z_HOOD), 'unit', name='ВЗ — кухонный зонт 500–600 м³/ч',
        label='ВЗ 600')
    xr, yr = v1.VZ_RISER
    box('Оголовок ВЗ', 'ВЗ', (xr - 0.30, yr - 0.30, v1.VZ_Z_CAP, xr + 0.30, yr + 0.30, v1.VZ_Z_CAP + 0.04), 'cap',
        name='ВЗ — зонт оголовка')
    # Н1 — решётка 500×400, низ +2,600, камера за ней
    box('Н1', 'Н', (19.93, 10.85, 2.60, 19.97, 11.35, 3.00), 'grille', name='Н1 — решётка воздухозабора 500×400',
        L=700, label='Н1 L=700')
    box('Н1-камера', 'Н', (19.62, 10.85, 2.60, 19.93, 11.35, Z1 + 0.15), 'ksd', name='Камера за решёткой Н1')
    # блоки К
    for n, b in v1.KU1.items():
        z0, z1 = unit_z(n, 1)
        a = AC[n]['air']
        box(n, 'Р', (b[0], b[1], z0, b[2], b[3], z1), 'unit', name=f'{n} — Daikin FXDQ {AC[n]["cap"]:g} кВт, {a} м³/ч'
            .replace('.', ','), label=n)
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        _, low = zone_at(cx, cy, 1)
        box(f'{n}-люк', 'Р', (cx - 0.30, cy - 0.29, low - 0.015, cx + 0.30, cy + 0.29, low + 0.005), 'grille',
            name=f'{n}: возврат — решётка-люк 600×600', L=a, label=f'возвр. L={a}')
        kx0, ky0, kx1, ky1 = v1.KSD1[n]
        box(f'{n}-КСД', 'Р', (kx0, ky0, z0, kx1, ky1, z1), 'ksd', name=f'{n}: КСД щелевого диффузора')
        if n == 'К-3':
            box(f'{n}-диф', 'Р', (kx0, ky0 - 0.04, z0 + 0.03, kx1, ky0, z1 - 0.03), 'grille',
                name=f'{n}: щелевой диффузор {round((kx1 - kx0) * 1000)} мм', L=a, label=f'L={a}')
        else:
            box(f'{n}-диф', 'Р', (kx0, ky1, z0 + 0.03, kx1, ky1 + 0.04, z1 - 0.03), 'grille',
                name=f'{n}: щелевой диффузор {round((kx1 - kx0) * 1000)} мм', L=a, label=f'L={a}')
    for n, b in v2.KU2.items():
        z0, z1 = unit_z(n, 2)
        a = AC[n]['air']
        box(n, 'Р', (b[0], b[1], z0, b[2], b[3], z1), 'unit', name=f'{n} — Daikin FXDQ 2,8 кВт, {a} м³/ч',
            label=n, floor=2)
    # П1 — щелевые диффузоры через КСД в торце подшивки П-1 (1 этаж)
    for gx, gy, kind, L, dr, nm, wall in v1.GRILLES1:
        if wall and dr == 'up' and kind == 'П' and abs(gy - 7.75) < 0.01:
            box(f'КСД-П {gx:.2f}', 'П', (gx - 0.30, 7.62, 3.30, gx + 0.30, 7.86, 3.50), 'ksd',
                name='КСД щелевого диффузора П1')
            box(f'ЩД-П {gx:.2f}', 'П', (gx - 0.30, 7.86, 3.33, gx + 0.30, 7.90, 3.47), 'grille',
                name='Щелевой диффузор притока П1 (1.10)', L=L, label=f'L={L}')
    # стенные решётки 1 этажа на КСД с круглым патрубком
    WALL1 = {(9.40, 2.20): ('1.2', 'П', 'x-'), (9.55, 10.00): ('кухня', 'В', 'x-'), (14.80, 11.10): ('1.8', 'В', 'y+')}
    for gx, gy, kind, L, dr, nm, wall in v1.GRILLES1:
        key = (gx, gy)
        if key not in WALL1:
            continue
        k, sk, face = WALL1[key]
        x0, y0, x1, y1 = v1.KSD1_W[k]
        box(f'КСД {k}', sk, (x0, y0, 3.30, x1, y1, 3.50), 'ksd', name=f'КСД стенной решётки ({k})')
        if face == 'x-':
            g = (x0 - 0.04, y0, 3.30, x0, y1, 3.50)
        else:
            g = (x0, y1, 3.30, x1, y1 + 0.04, 3.50)
        room = {'1.2': '1.2', 'кухня': '1.10', '1.8': '1.8'}[k]
        box(f'Реш. {k}', sk, g, 'grille', name=f'Решётка в стене, {SYS[sk][0]}, {room}', L=L, label=f'L={L}')


def terminals_ceiling():
    """Потолочные решётки: патрубок от оси воздуховода до подшивки и решётка 400×400 в плоскости подшивки."""
    items = [(gx, gy, kind, L, 1) for gx, gy, kind, L, dr, nm, wall in v1.GRILLES1 if not wall]
    items += [(3.90, v2.YM, 'П', 30, 2), (13.75, 8.25, 'В', 75, 2), (18.00, 8.25, 'В', 75, 2),
              (13.35, 10.80, 'В', 60, 2), (11.00, 9.80, 'В', 90, 2)]
    for gx, gy, kind, L, fl in items:
        zs = [z for z in (z_on(r, (gx, gy)) for r in RUNS if r.floor == fl and r.sys == kind and r.kind == 'duct')
              if z is not None]
        _, low = zone_at(gx, gy, fl)
        if not zs or low is None:
            print('!! решётка без воздуховода или зоны', gx, gy, kind)
            continue
        zt = min(zs)
        d = min((r.d for r in RUNS if r.floor == fl and r.sys == kind and r.kind == 'duct' and r.d and
                 z_on(r, (gx, gy)) is not None), default=0.1)
        RUNS.append(Run(f'патр. {gx:.2f};{gy:.2f}', kind, [(gx, gy, zt), (gx, gy, low + 0.005)], d=d,
                        name='Патрубок решётки', floor=fl, kind='stub', clamp=False))
        box(f'Реш. {gx:.2f};{gy:.2f}', kind, (gx - 0.20, gy - 0.20, low - 0.015, gx + 0.20, gy + 0.20, low + 0.005),
            'grille', name=f'Потолочная решётка, {SYS[kind][0]}', L=L, label=f'L={L}', floor=fl)


def build_floor2_slots():
    for kind, xc, n in v2.SLOTS:
        L = v2.slot_L(kind, n)
        x0, y0, x1, y1 = v2.KSD2[(kind, n)]
        z0 = 7.20 if kind == 'ЩП' else 7.28
        box(f'{n}-{kind}-КСД', 'Р', (x0, y0, z0, x1, y1, 7.50), 'ksd', name=f'{n}: КСД решётки {kind}', floor=2)
        what = 'подача' if kind == 'ЩП' else 'возврат'
        box(f'{n}-{kind}', 'Р', (xc - 0.40, v2.Y_WALL - 0.07, 7.325, xc + 0.40, v2.Y_WALL + 0.07, 7.475), 'grille',
            name=f'{n}: {kind} 800×150 в стене ({what})', L=L, label=f'{kind} L={L}', floor=2)
    for kind, yc in (('ЩП', 11.75), ('ЩВ', 10.00)):
        x0, y0, x1, y1 = v2.KSD2[(kind, 'К-7')]
        L = v2.slot_L(kind, 'К-7')
        box(f'К-7-{kind}-КСД', 'Р', (x0, y0, 7.25, x1, y1, 7.50), 'ksd', name=f'К-7: КСД решётки {kind}', floor=2)
        box(f'К-7-{kind}', 'Р', (15.63, yc - 0.40, 7.325, 15.77, yc + 0.40, 7.475), 'grille',
            name=f'К-7: {kind} 800×150 в стене 2.6/2.7', L=L, label=f'{kind} L={L}', floor=2)
    x0, y0, x1, y1 = v2.KSD2_W
    box('КСД верх 2-го света', 'В', (x0, y0, 6.40, x1, y1, 6.70), 'ksd', name='КСД решётки верха второго света', floor=2)
    box('Реш. верх 2-го света', 'В', (x0 - 0.06, y0, 6.40, x0, y1, 6.60), 'grille',
        name='Решётка в стене, верх второго света 1.10, низ +6,400', L=120, label='L=120', floor=2)


# ---------------------------------------------------------------- стены и перекрытия из подложек АР
def walls():
    from ezdxf import recover
    from underlay import OX, OY
    out = {}
    for fl, key in ((1, 'plan1'), (2, 'plan2')) + (((BATH, 'bath'),) if WITH_BATH else ()):
        sx, sy = (BX, BY) if fl == BATH else (0.0, 0.0)
        doc, _ = recover.readfile(v1.UNDER[key])
        polys = []
        for e in doc.modelspace().query('HATCH'):
            if e.dxf.layer != 'A-WALL-PATT':
                continue
            for p in e.paths:
                pts = []
                for ed in getattr(p, 'edges', []):
                    s = ed.start
                    pts.append(((s[0] - OX) / 1000 + sx, (s[1] - OY) / 1000 + sy))
                if not pts and hasattr(p, 'vertices'):
                    pts = [((v[0] - OX) / 1000 + sx, (v[1] - OY) / 1000 + sy) for v in p.vertices]
                if len(pts) >= 3:
                    pg = Polygon(pts).buffer(0)
                    if pg.area > 1e-4:
                        polys.append(pg)
        out[fl] = unary_union(polys)
    return out


def geoms(g):
    return [g] if g.geom_type == 'Polygon' else list(g.geoms)


def slab_outline(w1):
    """Контур перекрытия над 1 этажом: стены 1 этажа, замкнутые через проёмы (до 4,4 м), минус второй свет
    над 1.10 и лестничный проём (по АР09)."""
    closed = w1.buffer(2.3, join_style=2).buffer(-2.3, join_style=2)
    outer = unary_union([Polygon(g.exterior) for g in geoms(closed)])
    void = Polygon([(0.15, 7.96), (9.46, 7.96), (9.46, 13.64), (0.15, 13.64)])
    stair = Polygon([(9.69, 11.03), (12.38, 11.03), (12.38, 15.33), (9.69, 15.33)])
    return outer.difference(void).difference(stair)


# ---------------------------------------------------------------- проверка коллизий по готовой модели
def samples(r, step=0.05):
    out = []
    for p0, p1, sh in segments(r):
        L = math.dist(p0, p1)
        n = max(1, int(L / step))
        if L < 1e-9:
            continue
        w, h = (sh if sh else (r.d, r.d))
        t, u, v, _ = frame(p0, p1)
        st = min(step, L)
        if sh:                                          # брус: габарит по осям u (ширина), v (высота)
            e = [abs(u[k]) * w / 2 + abs(v[k]) * h / 2 + abs(t[k]) * st / 2 for k in range(3)]
        else:                                           # круг: габарит диска радиуса r поперёк оси
            e = [w / 2 * math.sqrt(max(0.0, 1 - t[k] ** 2)) + abs(t[k]) * st / 2 for k in range(3)]
        for i in range(n + 1):
            tt = i / n
            c = [p0[k] + (p1[k] - p0[k]) * tt for k in range(3)]
            out.append((c[0] - e[0], c[1] - e[1], c[2] - e[2], c[0] + e[0], c[1] + e[1], c[2] + e[2]))
    return out


def joints(a, b, tol=0.03):
    """Точки соединения двух элементов (конец одного на другом)."""
    pts = []
    for r, o in ((a, b), (b, a)):
        for e in (r.pts[0], r.pts[-1]):
            for p0, p1, sh in segments(o):
                seg = LineString([p0, p1]) if math.dist(p0, p1) > 1e-9 else Point(p0)
                if Point(e).distance(seg) < max(tol, (o.rxy + r.rxy)):
                    pts.append(e)
                    break
    return pts


def clash_check():
    import numpy as np
    S = {id(r): np.array(samples(r)) for r in RUNS}
    issues = []
    for i, a in enumerate(RUNS):
        for b in RUNS[i + 1:]:
            if a.floor != b.floor and not (a.kind == 'duct' and b.kind == 'duct'):
                pass
            A, B = S[id(a)], S[id(b)]
            if not len(A) or not len(B):
                continue
            ov = ((A[:, None, 0] < B[None, :, 3] - 0.003) & (A[:, None, 3] > B[None, :, 0] + 0.003) &
                  (A[:, None, 1] < B[None, :, 4] - 0.003) & (A[:, None, 4] > B[None, :, 1] + 0.003) &
                  (A[:, None, 2] < B[None, :, 5] - 0.003) & (A[:, None, 5] > B[None, :, 2] + 0.003))
            if not ov.any():
                continue
            J = joints(a, b)
            ia, ib = np.nonzero(ov)
            bad = []
            for k in range(len(ia)):
                c = (A[ia[k], :3] + A[ia[k], 3:]) / 2
                if any(math.dist(c, j) < 0.6 for j in J):
                    continue
                bad.append(c)
            if bad:
                c = bad[len(bad) // 2]
                issues.append(f'{a.id} ({a.section()}) × {b.id} ({b.section()}) около ({c[0]:.2f}; {c[1]:.2f}; '
                              f'{fmt(c[2])})')
    # сети × оборудование, КСД, решётки (кроме мест подключения: конец элемента у коробки)
    for r in RUNS:
        A = S[id(r)]
        if not len(A):
            continue
        for bx in BOXES:
            if bx.kind == 'damper':                     # клапан стоит на самом воздуховоде
                continue
            x0, y0, z0, x1, y1, z1 = bx.b
            ov = ((A[:, 0] < x1 - 0.003) & (A[:, 3] > x0 + 0.003) & (A[:, 1] < y1 - 0.003) & (A[:, 4] > y0 + 0.003) &
                  (A[:, 2] < z1 - 0.003) & (A[:, 5] > z0 + 0.003))
            if not ov.any():
                continue
            ends = [e for e in (r.pts[0], r.pts[-1])
                    if x0 - 0.35 <= e[0] <= x1 + 0.35 and y0 - 0.35 <= e[1] <= y1 + 0.35 and z0 - 0.8 <= e[2] <= z1 + 0.8]
            bad = [(A[k, :3] + A[k, 3:]) / 2 for k in np.nonzero(ov)[0]]
            bad = [c for c in bad if not any(math.dist(c, e) < 0.6 for e in ends)]
            if bad:
                c = bad[len(bad) // 2]
                issues.append(f'{r.id} ({r.section()}) × {bx.id} около ({c[0]:.2f}; {c[1]:.2f}; {fmt(c[2])})')
    return issues


# ---------------------------------------------------------------- выгрузка: данные для просмотрщика
def export_json(W, slab):
    data = {'title': 'И05.09.26-ОВ. Вентиляция и кондиционирование дома — 3D-модель',
            'systems': {k: {'name': v[0], 'rgb': v[1]} for k, v in SYS.items()},
            'walls': [], 'slabs': [], 'runs': [], 'boxes': [], 'labels': []}
    for fl, (z0, z1) in ((1, (0.0, SLAB1)), (2, (SLAB1, SLAB2)), (BATH, (0.0, BATH_TOP))):
        if fl not in W:
            continue
        for g in geoms(W[fl]):
            data['walls'].append({'floor': fl, 'z0': z0, 'z1': z1, 'outer': [list(map(lambda v: round(v, 4), p))
                                                                              for p in g.exterior.coords[:-1]],
                                  'holes': [[list(map(lambda v: round(v, 4), p)) for p in h.coords[:-1]]
                                            for h in g.interiors]})
    for g in geoms(slab):
        data['slabs'].append({'z0': SLAB1, 'z1': FL2, 'outer': [[round(x, 4), round(y, 4)] for x, y in g.exterior.coords[:-1]],
                              'holes': [[[round(x, 4), round(y, 4)] for x, y in h.coords[:-1]] for h in g.interiors]})
    for r in RUNS:
        segs = []
        for p0, p1, sh in segments(r):
            w, h = sh if sh else (r.d, r.d)
            segs.append([*map(lambda v: round(v, 4), p0), *map(lambda v: round(v, 4), p1), round(w, 4), round(h, 4),
                         1 if sh else 0])
        data['runs'].append({'id': r.id, 'sys': r.sys, 'name': r.name, 'L': r.L, 'kind': r.kind,
                             'sec': r.section(), 'floor': r.floor, 'segs': segs})
    for r in RUNS:
        if r.label:
            (x0, y0, z0), (x1, y1, z1) = r.pts[0], r.pts[-1]
            data['labels'].append({'x': round((x0 + x1) / 2, 3), 'y': round((y0 + y1) / 2, 3), 'z': round(z0 + 0.30, 3),
                                   'text': r.label, 'sys': r.sys, 'floor': r.floor})
    for b in BOXES:
        data['boxes'].append({'id': b.id, 'sys': b.sys, 'kind': b.kind, 'name': b.name, 'L': b.L, 'floor': b.floor,
                              'b': [round(v, 4) for v in b.b]})
        if b.label:
            x0, y0, z0, x1, y1, z1 = b.b
            zz = z0 - 0.12 if b.kind == 'grille' else z1 + (0.32 if b.kind == 'unit' else 0.10)
            data['labels'].append({'x': round((x0 + x1) / 2, 3), 'y': round((y0 + y1) / 2, 3), 'z': round(zz, 3),
                                   'text': b.label, 'sys': b.sys, 'floor': b.floor})
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'model.json'), 'w') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    return data


# ---------------------------------------------------------------- сетки (DXF) и тела (IFC)
def frame(p0, p1):
    """Базис отрезка: ось t, поперечная горизонталь u, вертикаль сечения v."""
    t = [p1[k] - p0[k] for k in range(3)]
    L = math.sqrt(sum(c * c for c in t))
    t = [c / L for c in t]
    if abs(t[2]) > 0.999:
        u, v = [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]
    else:
        u = [-t[1], t[0], 0.0]
        n = math.hypot(u[0], u[1])
        u = [u[0] / n, u[1] / n, 0.0]
        v = [t[1] * u[2] - t[2] * u[1], t[2] * u[0] - t[0] * u[2], t[0] * u[1] - t[1] * u[0]]
    return t, u, v, L


def seg_mesh(p0, p1, w, h, rect, ext, n=16):
    """Вершины и грани отрезка воздуховода: цилиндр (n граней) или брус; концы продлены на ext."""
    t, u, v, L = frame(p0, p1)
    a = [p0[k] - t[k] * ext for k in range(3)]
    b = [p1[k] + t[k] * ext for k in range(3)]
    if rect:
        ring = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    else:
        ring = [(w / 2 * math.cos(2 * math.pi * i / n), w / 2 * math.sin(2 * math.pi * i / n)) for i in range(n)]
    V = []
    for base in (a, b):
        for cu, cv in ring:
            V.append(tuple(base[k] + u[k] * cu + v[k] * cv for k in range(3)))
    m = len(ring)
    F = [[i, (i + 1) % m, m + (i + 1) % m, m + i] for i in range(m)]
    F.append(list(range(m))[::-1])
    F.append([m + i for i in range(m)])
    return V, F


def box_mesh(b):
    x0, y0, z0, x1, y1, z1 = b
    V = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    F = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    return V, F


def prism_mesh(outer, holes, z0, z1):
    from ezdxf.math.triangulation import mapbox_earcut_2d
    from ezdxf.math import Vec2
    tris = mapbox_earcut_2d([Vec2(p) for p in outer], [[Vec2(p) for p in h] for h in holes])
    V, F, idx = [], [], {}

    def vid(x, y, z):
        k = (round(x, 6), round(y, 6), round(z, 6))
        if k not in idx:
            idx[k] = len(V)
            V.append(k)
        return idx[k]
    for tri in tris:
        F.append([vid(p.x, p.y, z0) for p in tri][::-1])
        F.append([vid(p.x, p.y, z1) for p in tri])
    for ring in [outer] + holes:
        for i in range(len(ring)):
            (xa, ya), (xb, yb) = ring[i], ring[(i + 1) % len(ring)]
            F.append([vid(xa, ya, z0), vid(xb, yb, z0), vid(xb, yb, z1), vid(xa, ya, z1)])
    return V, F


def export_dxf(data):
    import ezdxf
    doc = ezdxf.new('R2018', setup=True)
    doc.units = 4                                       # мм, начало — оси 1/А, как у листов 9–11
    doc.header['$INSUNITS'] = 4
    msp = doc.modelspace()
    LAY = {'П': 'ОВ_3D_П1_приток', 'В': 'ОВ_3D_П1_вытяжка', 'Н': 'ОВ_3D_П1_наружный', 'X': 'ОВ_3D_П1_выброс',
           'ВЗ': 'ОВ_3D_ВЗ', 'В2': 'ОВ_3D_В2', 'Р': 'ОВ_3D_Кондиционирование', 'F': 'ОВ_3D_Фреон',
           'E': 'ОВ_3D_Оборудование', 'ВВ': 'ОВ_3D_Баня_вытяжка'}
    for k, nm in LAY.items():
        lay = doc.layers.add(nm, color=SYS[k][2])
        lay.rgb = SYS[k][1]
    doc.layers.add('АР_3D_стены', color=8)
    doc.layers.add('АР_3D_перекрытие', color=9)

    def poly(V, F, layer):
        m = msp.add_polyface(dxfattribs={'layer': layer})
        m.append_faces([[tuple(c * 1000 for c in V[i]) for i in f] for f in F])
        m.optimize()
    for wl in data['walls']:
        V, F = prism_mesh(wl['outer'], wl['holes'], wl['z0'], wl['z1'])
        poly(V, F, 'АР_3D_стены')
    for sl in data['slabs']:
        V, F = prism_mesh(sl['outer'], sl['holes'], sl['z0'], sl['z1'])
        poly(V, F, 'АР_3D_перекрытие')
    for r in data['runs']:
        for s in r['segs']:
            p0, p1, w, h, rect = s[:3], s[3:6], s[6], s[7], s[8]
            ext = (w / 2 if rect else w / 2) if r['kind'] in ('duct', 'pipe') else 0.0
            V, F = seg_mesh(p0, p1, w, h, rect, min(ext, 0.13), n=12 if r['kind'] == 'pipe' else 16)
            poly(V, F, LAY[r['sys']])
    for b in data['boxes']:
        V, F = box_mesh(b['b'])
        poly(V, F, LAY[b['sys']])
    for lb in data['labels']:
        msp.add_text(lb['text'], dxfattribs={'layer': LAY[lb['sys']], 'height': 100,
                                            'insert': (lb['x'] * 1000, lb['y'] * 1000, lb['z'] * 1000)})
    doc.set_modelspace_vport(height=25000, center=(10000, 8000))
    path = os.path.join(OUT, 'I05-09-26-OV-3D.dxf')
    doc.header['$LASTSAVEDBY'] = ''
    doc.saveas(path)
    return path


def export_ifc(data):
    import ifcopenshell
    import ifcopenshell.api
    import ifcopenshell.guid
    api = ifcopenshell.api.run
    f = ifcopenshell.file(schema='IFC4')
    proj = api('root.create_entity', f, ifc_class='IfcProject', name='И05.09.26-ОВ')
    api('unit.assign_unit', f, length={'is_metric': True, 'raw': 'METRE'})
    ctx = api('context.add_context', f, context_type='Model')
    body = api('context.add_context', f, context_type='Model', context_identifier='Body', target_view='MODEL_VIEW',
               parent=ctx)
    site = api('root.create_entity', f, ifc_class='IfcSite', name='Участок 50:08:0050209:1600')
    bld = api('root.create_entity', f, ifc_class='IfcBuilding', name='Жилой дом')
    st = {1: api('root.create_entity', f, ifc_class='IfcBuildingStorey', name='Этаж 1'),
          2: api('root.create_entity', f, ifc_class='IfcBuildingStorey', name='Этаж 2')}
    api('aggregate.assign_object', f, relating_object=proj, products=[site])
    api('aggregate.assign_object', f, relating_object=site, products=[bld])
    api('aggregate.assign_object', f, relating_object=bld, products=[st[1], st[2]])
    bath = None
    if WITH_BATH:
        bath = api('root.create_entity', f, ifc_class='IfcBuilding', name='Баня')
        st[BATH] = api('root.create_entity', f, ifc_class='IfcBuildingStorey', name='Баня, этаж 1')
        api('aggregate.assign_object', f, relating_object=site, products=[bath])
        api('aggregate.assign_object', f, relating_object=bath, products=[st[BATH]])
        api('geometry.edit_object_placement', f, product=bath)
        api('geometry.edit_object_placement', f, product=st[BATH])
    for obj in (site, bld):
        api('geometry.edit_object_placement', f, product=obj)
    from underlay import OX, OY                         # оси 1/А в координатах выгрузки Revit, мм
    bld.ObjectPlacement.RelativePlacement.Location.Coordinates = (OX / 1000, OY / 1000, 0.0)
    for k, s in st.items():
        api('geometry.edit_object_placement', f, product=s)
        s.Elevation = 0.0 if k == 1 else FL2
        s.ObjectPlacement.RelativePlacement.Location.Coordinates = (0.0, 0.0, 0.0 if k == 1 else FL2)
    bld.ObjectPlacement.PlacementRelTo = site.ObjectPlacement      # цепочка участок → здание → этаж
    for k in (1, 2):
        st[k].ObjectPlacement.PlacementRelTo = bld.ObjectPlacement
    # баня — здание с началом в осях 1/А бани: сдвиг по ГП01 от осей дома (элементы — в общей системе дома)
    if bath is not None:
        bath.ObjectPlacement.RelativePlacement.Location.Coordinates = (OX / 1000 + BX, OY / 1000 + BY, 0.0)
        bath.ObjectPlacement.PlacementRelTo = site.ObjectPlacement
        st[BATH].ObjectPlacement.RelativePlacement.Location.Coordinates = (0.0, 0.0, 0.0)
        st[BATH].ObjectPlacement.PlacementRelTo = bath.ObjectPlacement

    O = f.createIfcCartesianPoint((0.0, 0.0, 0.0))

    def ax(p, z=(0.0, 0.0, 1.0), x=(1.0, 0.0, 0.0)):
        return f.createIfcAxis2Placement3D(f.createIfcCartesianPoint(tuple(map(float, p))),
                                           f.createIfcDirection(tuple(map(float, z))),
                                           f.createIfcDirection(tuple(map(float, x))))
    styles = {}

    def style(k):
        if k not in styles:
            rgb = SYS[k][1] if k in SYS else (200, 200, 200)
            col = f.createIfcColourRgb(None, *(c / 255 for c in rgb))
            tr = 0.0
            if k == 'wall':
                col, tr = f.createIfcColourRgb(None, 0.85, 0.85, 0.82), 0.55
            if k == 'slab':
                col, tr = f.createIfcColourRgb(None, 0.80, 0.80, 0.78), 0.65
            ss = f.createIfcSurfaceStyleShading(col, tr)
            styles[k] = f.createIfcSurfaceStyle(SYS[k][0] if k in SYS else k, 'BOTH', [ss])
        return styles[k]

    def shape(items, k):
        for it in items:
            f.createIfcStyledItem(it, [style(k)], None)
        rep = f.createIfcShapeRepresentation(body, 'Body', 'SweptSolid', items)
        return f.createIfcProductDefinitionShape(None, None, [rep])

    def place(prod, storey):
        z = FL2 if storey == 2 else 0.0
        dx, dy = (-BX, -BY) if storey == BATH else (0.0, 0.0)  # координаты элементов бани — в осях дома
        rel = st[storey].ObjectPlacement
        prod.ObjectPlacement = f.createIfcLocalPlacement(rel, ax((dx, dy, -z)))

    def extr_seg(p0, p1, w, h, rect):
        t, u, v, L = frame(p0, p1)
        prof = (f.createIfcRectangleProfileDef('AREA', None, f.createIfcAxis2Placement2D(
            f.createIfcCartesianPoint((0.0, 0.0)), None), float(w), float(h)) if rect else
            f.createIfcCircleProfileDef('AREA', None, f.createIfcAxis2Placement2D(
                f.createIfcCartesianPoint((0.0, 0.0)), None), float(w / 2)))
        return f.createIfcExtrudedAreaSolid(prof, ax(p0, t, u), f.createIfcDirection((0.0, 0.0, 1.0)), float(L))

    def extr_box(b):
        x0, y0, z0, x1, y1, z1 = b
        prof = f.createIfcRectangleProfileDef('AREA', None, f.createIfcAxis2Placement2D(
            f.createIfcCartesianPoint(((x1 - x0) / 2, (y1 - y0) / 2)), None), float(x1 - x0), float(y1 - y0))
        return f.createIfcExtrudedAreaSolid(prof, ax((x0, y0, z0)), f.createIfcDirection((0.0, 0.0, 1.0)),
                                            float(max(z1 - z0, 0.001)))

    def extr_poly(outer, holes, z0, z1):
        def curve(pts):
            P = [f.createIfcCartesianPoint((float(x), float(y))) for x, y in pts]
            return f.createIfcPolyline(P + [P[0]])
        if holes:
            prof = f.createIfcArbitraryProfileDefWithVoids('AREA', None, curve(outer), [curve(h) for h in holes])
        else:
            prof = f.createIfcArbitraryClosedProfileDef('AREA', None, curve(outer))
        return f.createIfcExtrudedAreaSolid(prof, ax((0.0, 0.0, z0)), f.createIfcDirection((0.0, 0.0, 1.0)),
                                            float(z1 - z0))

    systems = {}

    def system(k):
        if k not in systems and k in SYS and k != 'E':
            ptype = {'П': 'VENTILATION', 'В': 'VENTILATION', 'Н': 'VENTILATION', 'X': 'EXHAUST', 'ВЗ': 'EXHAUST',
                     'В2': 'EXHAUST', 'Р': 'AIRCONDITIONING', 'F': 'REFRIGERATION', 'ВВ': 'EXHAUST'}[k]
            s = api('system.add_system', f, ifc_class='IfcDistributionSystem')
            s.Name = SYS[k][0]
            s.PredefinedType = ptype
            systems[k] = s
        return systems.get(k)

    by_store = {1: [], 2: [], BATH: []}
    by_sys = {}

    def pset(prod, props):
        ps = api('pset.add_pset', f, product=prod, name='ОВ_Параметры')
        api('pset.edit_pset', f, pset=ps, properties={k: v for k, v in props.items() if v is not None})

    for wl in data['walls']:
        w = api('root.create_entity', f, ifc_class='IfcWall',
                name='Стена бани по АР4' if wl['floor'] == BATH else f'Стена по АР (этаж {wl["floor"]})')
        w.Representation = shape([extr_poly(wl['outer'], wl['holes'], wl['z0'], wl['z1'])], 'wall')
        place(w, wl['floor'])
        by_store[wl['floor']].append(w)
    for sl in data['slabs']:
        s = api('root.create_entity', f, ifc_class='IfcSlab', name='Перекрытие над 1 этажом (условно)')
        s.Representation = shape([extr_poly(sl['outer'], sl['holes'], sl['z0'], sl['z1'])], 'slab')
        place(s, 2)
        by_store[2].append(s)
    for r in data['runs']:
        cls = 'IfcPipeSegment' if r['sys'] == 'F' else 'IfcDuctSegment'
        if r['kind'] == 'silencer':
            cls = 'IfcDuctSilencer'
        if r['kind'] == 'fan':
            cls = 'IfcFan'
        e = api('root.create_entity', f, ifc_class=cls, name=r['name'])
        e.Tag = r['id']
        items = [extr_seg(s[:3], s[3:6], s[6], s[7], s[8]) for s in r['segs'] if math.dist(s[:3], s[3:6]) > 1e-6]
        if not items:
            continue
        e.Representation = shape(items, r['sys'])
        place(e, r['floor'])
        by_store[r['floor']].append(e)
        by_sys.setdefault(r['sys'], []).append(e)
        pset(e, {'Сечение': r['sec'], 'Расход, м³/ч': float(r['L']) if r['L'] else None, 'Система': SYS[r['sys']][0]})
    for b in data['boxes']:
        cls = {'unit': 'IfcUnitaryEquipment', 'grille': 'IfcAirTerminal', 'ksd': 'IfcAirTerminalBox',
               'damper': 'IfcDamper', 'cap': 'IfcAirTerminal'}[b['kind']]
        if b['id'] == 'П1':
            cls = 'IfcAirToAirHeatRecovery'
        e = api('root.create_entity', f, ifc_class=cls, name=b['name'])
        e.Tag = b['id']
        e.Representation = shape([extr_box(b['b'])], b['sys'])
        place(e, b['floor'])
        by_store[b['floor']].append(e)
        by_sys.setdefault(b['sys'], []).append(e)
        pset(e, {'Расход, м³/ч': float(b['L']) if b['L'] else None, 'Система': SYS[b['sys']][0]})
    for k, objs in by_store.items():
        if objs:
            api('spatial.assign_container', f, relating_structure=st[k], products=objs)
    for k, objs in by_sys.items():
        s = system(k)
        if s is not None:
            api('system.assign_system', f, products=objs, system=s)
    path = os.path.join(OUT, 'I05-09-26-OV-3D.ifc')
    f.write(path)
    return path


# ---------------------------------------------------------------- сборка
def main():
    build_runs()
    if WITH_BATH:
        build_bath()
    notes = clamp_runs()
    log, fail = solve()
    stubs()
    build_boxes()
    terminals_ceiling()
    build_floor2_slots()
    W = walls()
    slab = slab_outline(W[1])
    clashes = clash_check()
    data = export_json(W, slab)
    dxf = export_dxf(data)
    ifc = export_ifc(data)
    with open(os.path.join(OUT, 'razvodka.txt'), 'w') as fh:
        fh.write('Высоты по зонам подшивки:\n' + '\n'.join('  ' + n for n in notes) + '\n\n')
        fh.write('Разводка пересечений:\n' + '\n'.join('  ' + n for n in log) + '\n\n')
        fh.write('Не развелось:\n' + ('\n'.join('  ' + n for n in fail) or '  —') + '\n\n')
        fh.write('Проверка коллизий готовой модели (сети между собой, без стен):\n' +
                 ('\n'.join('  ' + n for n in clashes) or '  —') + '\n')
    print(open(os.path.join(OUT, 'razvodka.txt')).read())
    print(len(RUNS), 'линейных элементов,', len(BOXES), 'оборудование/решётки/КСД')
    print(dxf, ifc, sep='\n')


if __name__ == '__main__':
    main()
