"""И05.09.26-ТМ. Тепломеханические решения котельной (топочная 1.6): 3D-модель — единый источник листов ТМ,
спецификации ТМ.СО и выгрузок (DWG, IFC, просмотр в браузере).

Состав и схема — лист 8 ОВ (ov_boiler_scheme): котлы К1, К2 (каскад) и ПК → шламоотделитель → гидрострелка ГС →
двухкамерный коллектор РК на 6 групп: Н3 (КШ-2), Н4 (ТП: КШ-1, КШ-3), Н2 (КШ-4), Н5 (П1), Н6 (баня, снизу),
Н7 (Б1). Расстановка — лист 7 ОВ; диаметры групп — расчёт листа 8 (groups_calc). Координаты — м от осей 1/А
дома (как листы ОВ), отметки — от ±0,000.

python3 tm_model.py → out/tm/: tm.json (данные листов и СО), model.json (просмотр), I05-09-26-TM-3D.dxf,
I05-09-26-TM-3D.ifc, kollizii.txt
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'sheets'))
sys.path.insert(0, HERE)

OUT = os.path.join(HERE, 'out', 'tm')

# ---------------------------------------------------------------- помещение (лист 7: внутренние грани стен)
X0, X1, Y0, Y1 = 15.80, 19.80, 9.05, 13.60
H_SLAB = 3.65
Z_HI = 3.20            # магистрали под потолком (листы 3, 7)
Z_P1 = 3.05            # отвод к П1 — под магистралями
Z_XS, Z_XR = 2.90, 2.78   # котловые коллекторы подачи и обратки по северной стене
Z_K3 = 2.60            # отвод ТП к КШ-3 — под шумоглушителями П1

STEEL = {15: 0.0213, 20: 0.0268, 25: 0.0335, 32: 0.0423, 40: 0.0480}   # ГОСТ 3262-75, наружный Ø
PEX = {'20×2,8': 0.020, '25×3,5': 0.025, '32×4,4': 0.032, '32×2,9': 0.032}

SYS = {  # система: (название, RGB)
    'Т1': ('Т1 — подающий отопления (котловой контур, 70…80 °С)', (220, 38, 38)),
    'Т2': ('Т2 — обратный отопления', (37, 99, 235)),
    'Т11': ('Т11 — подающий тёплого пола 48,5 °С', (234, 88, 12)),
    'Т21': ('Т21 — обратный тёплого пола', (14, 165, 233)),
    'Т3': ('Т3 — горячая вода (граница — раздел ВК)', (22, 163, 74)),
    'Т4': ('Т4 — циркуляция ГВС (ВК)', (132, 204, 22)),
    'В1': ('В1 — холодная вода: подпитка, бойлер (ВК)', (6, 182, 212)),
    'Г': ('Г — газопровод (условно, проект ГСВ)', (202, 138, 4)),
    'Д': ('Дымоходы', (120, 113, 108)),
    'К': ('К — конденсат котлов (до нейтрализатора; далее — ВК)', (100, 116, 139)),
    'EQ': ('Оборудование', (226, 232, 240)),
    'AR': ('Арматура', (180, 140, 60)),
    'OV': ('Сети ОВ в топочной (П1, воздуховоды, фреон) — для увязки', (190, 196, 206)),
}

PIPES, FITS, EQUIP = [], [], []


class Pipe:
    def __init__(self, pid, sysk, mat, dn, pts, circ, name=''):
        self.id, self.sys, self.mat, self.dn, self.circ = pid, sysk, mat, dn, circ
        self.pts = [tuple(round(float(c), 4) for c in p) for p in pts]
        self.od = STEEL[dn] if mat == 'steel' else (PEX[dn] if mat in ('pex', 'eco') else dn)
        self.name = name or f'{sysk} {self.label()}'

    def label(self):
        if self.mat == 'steel':
            return f'Ду{self.dn}'
        if self.mat in ('pex', 'eco'):
            return f'PE-Xa {self.dn}'
        if self.mat == 'pp':
            return f'Ø{round(self.od * 1000)}'
        return str(self.dn)

    def length(self):
        return sum(math.dist(a, b) for a, b in zip(self.pts, self.pts[1:]))


def pipe(*a, **k):
    p = Pipe(*a, **k)
    PIPES.append(p)
    return p


class Fit:
    """Арматура и приборы на трубе: kind — ball, check, balance, filter, pump, three, mano, therm, vent, drain,
    safety, reducer, dirt, gas; pos — точка на оси трубы; axis — 'x', 'y', 'z' (по отрезку трубы)."""

    def __init__(self, kind, p, pos, name='', side=None, extra=None):
        self.kind, self.pipe, self.pos, self.name = kind, p, tuple(pos), name
        self.sys, self.od = p.sys, p.od
        self.axis = seg_axis(p, pos)
        self.side = side                       # куда смотрит ручка / привод: '+x', '-y', …
        self.extra = extra or {}


def seg_axis(p, pos):
    for a, b in zip(p.pts, p.pts[1:]):
        if point_on_seg(pos, a, b):
            d = [abs(b[k] - a[k]) for k in range(3)]
            return 'xyz'[d.index(max(d))]
    raise ValueError(f'{p.id}: точка {pos} не на трубе')


def point_on_seg(q, a, b, tol=1e-4):
    ab = [b[k] - a[k] for k in range(3)]
    L2 = sum(c * c for c in ab)
    if L2 < 1e-12:
        return math.dist(q, a) < tol
    t = sum((q[k] - a[k]) * ab[k] for k in range(3)) / L2
    if t < -1e-6 or t > 1 + 1e-6:
        return False
    proj = [a[k] + ab[k] * t for k in range(3)]
    return math.dist(q, proj) < tol


def fit(kind, p, pos, name='', side=None, **extra):
    f = Fit(kind, p, pos, name, side, extra)
    FITS.append(f)
    return f


class Eq:
    """Оборудование: kind 'box' (x0, y0, z0, x1, y1, z1) или 'cyl' (cx, cy, r, z0, z1) — вертикальный цилиндр;
    pos — номер позиции в СО ТМ, mark — обозначение на листах."""

    def __init__(self, eid, mark, kind, g, name, rgb=None, pos=None, ifc='IfcDistributionElement', ctx=False):
        self.id, self.mark, self.kind, self.g, self.name = eid, mark, kind, g, name
        self.rgb, self.pos, self.ifc, self.ctx = rgb or SYS['EQ'][1], pos, ifc, ctx

    def bbox(self):
        if self.kind == 'box':
            return self.g
        cx, cy, r, z0, z1 = self.g
        return (cx - r, cy - r, z0, cx + r, cy + r, z1)


def eq(*a, **k):
    e = Eq(*a, **k)
    EQUIP.append(e)
    return e


# ---------------------------------------------------------------- оборудование (расстановка — лист 7 ОВ)
KC = {'К2': 11.075, 'К1': 11.775}      # оси котлов по y; корпус 400×360×700 (Vitodens 200-W, ≤32 кВт)
K_X, K_Z = 15.98, 1.10                 # ось присоединений котла (от стены 180 мм) и низ котла
GROUPS = [('Н3', 'КШ-2'), ('Н4', 'ТП: КШ-1, КШ-3'), ('Н2', 'КШ-4'), ('Н5', 'П1'), ('Н6', 'баня'), ('Н7', 'Б1')]
GX0, GSTEP = 18.285, 0.25              # ось первой группы, шаг групп на РК
GY = 13.46                             # ось РК и групп (от стены 140 мм)
G_TOP, G_BOT = 1.80, 0.84              # выходы групп сверху (над РК) / снизу (Н6 — под РК)
HS = (18.06, 13.42, 0.044, 0.95, 1.85)  # гидрострелка: ось, радиус корпуса (Ø88 — rd_calc), низ, верх
B1 = (19.42, 11.10, 0.3335, 0.0, 1.734)  # бойлер 300 л Ø667×1734 (типовой; по каталогу)
RB = (18.42, 13.32, 0.24, 0.0, 0.62)   # бак расширительный 80 л (типовой Ø480×565 на ножках)
RBG = (19.64, 10.92, 0.14, 1.82, 2.18)  # бак ГВС 18 л на стене над Б1 (Ø280×360)
PK = (16.20, 12.50, 0.0, 17.00, 13.50, 1.45)
BP = (17.08, 12.70, 0.0, 17.78, 13.50, 1.40)
P1 = (16.90, 9.21, 2.45, 18.40, 10.29, 3.06)
ECO = (19.25, 13.46)                     # подъём Ecoflex через плиту пола (листы 3, 7, 14 ОВ: ECO_UP)
P1_MIX = (18.42, 10.09, 2.55, 18.72, 10.27, 2.95)


def gx(i):
    return GX0 + GSTEP * i


def build_equipment():
    for m, yc in KC.items():
        eq(m, m, 'box', (X0, yc - 0.20, K_Z, X0 + 0.36, yc + 0.20, K_Z + 0.70),
           f'{m} — котёл газовый конденсационный настенный Viessmann ≈24–25 кВт (Vitodens 200-W, 400×360×700)',
           rgb=(241, 245, 249), pos=1, ifc='IfcBoiler')
    eq('ПК', 'ПК', 'box', PK, 'ПК — котёл пеллетный ≈50 кВт (резерв)', rgb=(203, 213, 225), pos=2, ifc='IfcBoiler')
    eq('ПК-горелка', 'ПК', 'box', (16.40, 12.40, 0.45, 16.80, 12.50, 0.75), 'ПК — горелка', rgb=(148, 163, 184),
       ifc='IfcBurner')
    eq('БП', 'БП', 'box', BP, 'БП — бункер пеллет со шнеком', rgb=(214, 211, 209), pos=3)
    eq('БП-шнек', 'БП', 'box', (17.00, 12.80, 0.80, 17.08, 12.90, 0.90), 'шнек подачи', rgb=(120, 113, 108))
    x, y, r, z0, z1 = HS
    eq('ГС', 'ГС', 'cyl', (x, y, r, z0, z1), 'ГС — гидравлический разделитель Ду32', rgb=(71, 85, 105), pos=4,
       ifc='IfcPipeFitting')
    eq('РК', 'РК', 'box', (gx(0) - 0.125, GY - 0.06, 1.26, gx(5) + 0.125, GY + 0.06, 1.38),
       'РК — коллектор распределительный двухкамерный Ду32 на 6 групп', rgb=(51, 65, 85), pos=5, ifc='IfcPipeFitting')
    for i, (n, dest) in enumerate(GROUPS):
        x = gx(i)
        z0, z1 = (G_BOT, 1.26) if n == 'Н6' else (1.38, G_TOP)
        eq(n, n, 'box', (x - 0.12, GY - 0.11, z0, x + 0.12, GY + 0.11, z1), f'{n} — группа {"без насоса" if n == "Н5" else "насосная"} → {dest}',
           rgb=(30, 41, 59), pos=6, ifc='IfcPump' if n != 'Н5' else 'IfcValve')
        if n != 'Н5':                         # двигатель насоса — на подающей стороне, к помещению
            zc = (z0 + z1) / 2
            eq(f'{n}-мотор', n, 'cylx', (x - 0.0625, GY - 0.11, zc, GY - 0.20, 0.045), 'двигатель насоса',
               rgb=(0, 128, 120), ifc='IfcElectricMotor')
    x, y, r, z0, z1 = B1
    eq('Б1', 'Б1', 'cyl', B1, 'Б1 — бойлер косвенного нагрева 300 л', rgb=(248, 250, 252), pos=7, ifc='IfcTank')
    eq('РБ', 'РБ', 'cyl', RB, 'РБ — бак расширительный 80 л', rgb=(220, 38, 38), pos=8, ifc='IfcTank')
    eq('РБ-ГВС', 'РБ-ГВС', 'cyl', RBG, 'РБ-ГВС — бак расширительный ГВС 18 л', rgb=(37, 99, 235), pos=9, ifc='IfcTank')
    eq('ШУ', 'ШУ', 'box', (16.70, Y0, 1.70, 17.40, Y0 + 0.20, 2.30), 'ШУ — шкаф управления котельной',
       rgb=(226, 232, 240), pos=10, ifc='IfcElectricDistributionBoard')
    eq('КШ-3', 'КШ-3', 'box', (15.95, 9.07, 0.20, 16.50, 9.22, 0.85), 'КШ-3 — шкаф коллекторный ТП (ОВ)',
       rgb=(241, 245, 249), ifc='IfcDistributionElement')
    eq('Нейтр', 'Н', 'box', (16.40, 11.30, 0.0, 16.70, 11.55, 0.15), 'нейтрализатор конденсата (ВК)',
       rgb=(186, 230, 253), ifc='IfcDistributionElement')
    eq('Трап', 'Т', 'cyl', (17.00, 11.05, 0.08, -0.01, 0.01), 'трап Ду50 (ВК)', rgb=(100, 116, 139))
    eq('Ecoflex', 'Eco', 'cyl', (ECO[0], ECO[1], 0.0875, -0.10, 0.25), 'ввод Ecoflex Quattro (баня), лист 14 ОВ',
       rgb=(17, 24, 39), ifc='IfcPipeSegment')
    eq('П1', 'П1', 'box', P1, 'П1 — Turkov Zenit 750 Heco W (ОВ, лист 9)', rgb=SYS['OV'][1], ctx=True)
    eq('П1-узел', 'П1', 'box', P1_MIX, 'смесительный узел нагревателя П1 (комплект Turkov)', rgb=(148, 163, 184),
       ctx=True)


# ---------------------------------------------------------------- трубопроводы
def offset(pts, d):
    """Смещение плоской ломаной (оси пары) на d вправо по ходу (м)."""
    from rdbase import offset_poly
    return offset_poly(pts, d)


def build_pipes():
    # ------------------------------------ котлы К1, К2: присоединения (кран сверху вниз), нижние коллекторы
    xs_x, xr_x, zs, zr = 15.92, 16.04, 0.70, 0.55
    for m, yc in KC.items():
        s = pipe(f'{m}-П', 'Т1', 'steel', 25, [(K_X, yc - 0.09, K_Z), (K_X, yc - 0.09, zs), (xs_x, yc - 0.09, zs)],
                 'котлы', f'{m}: подача')
        r = pipe(f'{m}-О', 'Т2', 'steel', 25, [(K_X, yc + 0.09, K_Z), (K_X, yc + 0.09, zr), (xr_x, yc + 0.09, zr)],
                 'котлы', f'{m}: обратка')
        fit('ball', s, (K_X, yc - 0.09, 0.95), f'{m}: кран шаровой Ду25 (комплект подключения)', side='+x')
        fit('ball', r, (K_X, yc + 0.09, 0.95), f'{m}: кран шаровой Ду25 (комплект подключения)', side='+x')
    y2s, y1s = KC['К2'] - 0.09, KC['К1'] - 0.09
    y2r = KC['К2'] + 0.09
    xs = pipe('XS', 'Т1', 'steel', 32, [(xs_x, y2s, zs), (xs_x, 12.34, zs), (16.24, 12.34, zs), (16.24, 12.34, Z_XS),
                                        (16.24, 13.47, Z_XS), (17.86, 13.47, Z_XS), (17.86, 13.47, 1.70),
                                        (17.86, HS[1], 1.70), (HS[0] - HS[2], HS[1], 1.70)],
              'котловой контур', 'Коллектор подачи котлов К1, К2, ПК → ГС')
    xr = pipe('XR', 'Т2', 'steel', 32, [(xr_x, y2r, zr), (xr_x, 12.20, zr), (16.12, 12.20, zr), (16.12, 12.20, Z_XR),
                                        (16.12, 13.35, Z_XR), (17.96, 13.35, Z_XR), (17.96, 13.35, 0.80)],
              'котловой контур', 'Коллектор обратки ГС → К1, К2, ПК')
    pipe('ГС-О', 'Т2', 'steel', 32, [(HS[0] - HS[2], HS[1], 1.05), (17.96, HS[1], 1.05), (17.96, 13.35, 1.05)],
         'котловой контур', 'ГС: выход обратки котлового контура')
    fit('drain', xs, (xs_x, y2s, zs), 'Кран спускной Ду15 (нижняя точка подачи)', side='-z')
    fit('vent', xs, (16.24, 13.47, Z_XS), 'Воздухоотводчик автоматический Ду15 с краном', side='+z')
    fit('vent', xs, (17.86, 13.47, Z_XS), 'Воздухоотводчик автоматический Ду15 с краном', side='+z')
    fit('therm', xs, (17.86, 13.47, 2.30), 'Термометр', side='-y')
    fit('dirt', xr, (17.96, 13.35, 2.20), 'Шламоотделитель магнитный Ду32 (ШО)')
    fit('ball', xr, (17.96, 13.35, 2.50), 'Кран шаровой Ду32', side='-y')
    fit('ball', xr, (17.96, 13.35, 1.85), 'Кран шаровой Ду32', side='-y')
    fit('mano', xr, (17.96, 13.35, 1.60), 'Манометр 0–4 бар с краном', side='-y')
    fit('ball', xs, (17.86, 13.47, 2.05), 'Кран шаровой Ду32', side='-y')
    # ------------------------------------ ПК: подача и обратка сверху котла, подмес 55 °С (КТ + Н1), ГБ
    ps = pipe('ПК-П', 'Т1', 'steel', 32, [(16.45, 13.47, PK[5]), (16.45, 13.47, Z_XS)], 'котловой контур', 'ПК: подача')
    pr = pipe('ПК-О', 'Т2', 'steel', 32, [(16.85, 13.35, PK[5]), (16.85, 13.35, Z_XR)], 'котловой контур', 'ПК: обратка')
    pb = pipe('ПК-КТ', 'Т1', 'steel', 32, [(16.45, 13.47, 2.20), (16.85, 13.47, 2.20), (16.85, 13.385, 2.20)],
              'котловой контур', 'ПК: перемычка подмеса к КТ')
    fit('ball', ps, (16.45, 13.47, 1.58), 'Кран шаровой Ду32', side='-y')
    fit('safety', ps, (16.45, 13.47, 1.78), 'ГБ — группа безопасности котла 3 бар (клапан, манометр, воздухоотводчик)',
        side='-y')
    fit('check', ps, (16.45, 13.47, 2.55), 'Клапан обратный Ду32')
    fit('ball', pr, (16.85, 13.35, 1.58), 'Кран шаровой Ду32', side='-y')
    fit('pump', pr, (16.85, 13.35, 1.90), 'Н1 — насос котлового контура ПК (по паспорту ПК)', side='-y')
    fit('three', pr, (16.85, 13.35, 2.20), 'КТ — клапан термостатический трёхходовой 55 °С Ду32', side='-y')
    fit('ball', pr, (16.85, 13.35, 2.50), 'Кран шаровой Ду32', side='-y')
    # ------------------------------------ ГС → РК (вторичный контур), РБ, подпитка, спуск
    gs_s = pipe('ГС-РК-П', 'Т1', 'steel', 32, [(HS[0] + HS[2], GY + 0.03, 1.32), (gx(0) - 0.125, GY + 0.03, 1.32)],
                'ГС-РК', 'ГС → РК: подача')
    pipe('ГС-РК-О', 'Т2', 'steel', 32, [(gx(0) - 0.125, GY - 0.03, 1.32), (HS[0] + HS[2], GY - 0.03, 1.32)],
         'ГС-РК', 'РК → ГС: обратка')
    rbp = pipe('РБ', 'Т2', 'steel', 20, [(17.96, 13.35, 0.80), (17.96, 13.25, 0.80), (RB[0], 13.25, 0.80),
                                         (RB[0], 13.25, RB[4])], 'РБ', 'Подключение РБ к обратке котлового контура')
    fit('ball', rbp, (18.20, 13.25, 0.80), 'Кран шаровой с защитой от закрытия Ду20 (колпачковый)', side='-y')
    up = pipe('УП', 'В1', 'steel', 15, [(18.10, 13.18, 0.20), (18.10, 13.18, 0.80), (18.10, 13.25, 0.80)], 'УП',
              'УП — узел подпитки от В1 (ВК)')
    for z, k, nm in ((0.28, 'ball', 'Кран шаровой Ду15'), (0.38, 'filter', 'Фильтр сетчатый Ду15'),
                     (0.50, 'reducer', 'Редуктор давления 1,5 бар Ду15'), (0.62, 'check', 'Клапан обратный Ду15'),
                     (0.72, 'ball', 'Кран шаровой Ду15')):
        fit(k, up, (18.10, 13.18, z), nm, side='-y')
    sp = pipe('Спуск', 'Т2', 'steel', 15, [(17.96, 13.35, 0.80), (17.96, 13.35, 0.45)], 'котловой контур',
              'Спуск из нижней точки обратки')
    fit('ball', sp, (17.96, 13.35, 0.55), 'Кран шаровой спускной Ду15 со штуцером', side='-y')
    # ------------------------------------ насосные группы: подъём к +3,200 и магистрали в тамбур 1.7 (лист 3)
    pex = {'Н3': '32×4,4', 'Н4': '25×3,5', 'Н2': '25×3,5', 'Н5': '20×2,8', 'Н6': '32×2,9'}
    turn_y = {'Н3': 10.60, 'Н4': 10.45, 'Н2': 10.30}
    for i, (n, dest) in enumerate(GROUPS):
        x = gx(i)
        sx, rx = x - 0.0625, x + 0.0625
        if n in ('Н3', 'Н4', 'Н2'):
            ts, tr = ('Т11', 'Т21') if n == 'Н4' else ('Т1', 'Т2')
            gap = 0.07
            ctr = [(x, GY), (x, turn_y[n]), (X0 - 0.20, turn_y[n])]
            so, ro = offset(ctr, -gap / 2), offset(ctr, gap / 2)     # подача — слева по ходу (запад / север)
            ps_ = [(sx, GY, G_TOP), (sx, GY, Z_HI)] + [(a, b, Z_HI) for a, b in so]
            pr_ = [(a, b, Z_HI) for a, b in ro][::-1] + [(rx, GY, Z_HI), (rx, GY, G_TOP)]
            s = pipe(f'{n}-П', ts, 'pex', pex[n], ps_, n, f'{n} → {dest}: подача')
            r = pipe(f'{n}-О', tr, 'pex', pex[n], pr_, n, f'{n} ← {dest}: обратка')
            if n == 'Н4':                       # отвод к КШ-3: опуск под шумоглушители, вдоль южной стены, в шкаф
                ys_, yr_ = so[-1][1], ro[-1][1]
                pipe('КШ-3-П', 'Т11', 'pex', '25×3,5', [(16.30, ys_, Z_HI), (16.30, ys_, Z_K3), (16.30, 9.145, Z_K3),
                                                       (16.30, 9.145, 0.85)], n, 'Н4 → КШ-3: подача')
                pipe('КШ-3-О', 'Т21', 'pex', '25×3,5', [(16.38, 9.145, 0.85), (16.38, 9.145, Z_K3), (16.38, yr_, Z_K3),
                                                       (16.38, yr_, Z_HI)], n, 'КШ-3 → Н4: обратка')
        elif n == 'Н5':                         # к узлу П1: ниже магистралей, под ними — на запад
            ctr = [(x, GY), (x, 10.40), (18.57, 10.40)]
            so, ro = offset(ctr, -0.035), offset(ctr, 0.035)
            so[-1] = (18.50, so[-1][1])          # подача (северная) — дальше на запад, обратка опускается раньше
            ro[-1] = (18.64, ro[-1][1])
            ps_ = [(sx, GY, G_TOP), (sx, GY, Z_P1)] + [(a, b, Z_P1) for a, b in so] + [(18.50, 10.18, Z_P1),
                                                                                       (18.50, 10.18, P1_MIX[5])]
            pr_ = [(18.64, 10.18, P1_MIX[5]), (18.64, 10.18, Z_P1)] + [(a, b, Z_P1) for a, b in ro][::-1] + \
                  [(rx, GY, Z_P1), (rx, GY, G_TOP)]
            pipe(f'{n}-П', 'Т1', 'pex', pex[n], ps_, n, f'{n} → П1: подача')
            pipe(f'{n}-О', 'Т2', 'pex', pex[n], pr_, n, f'{n} ← П1: обратка')
        elif n == 'Н6':                         # вниз — к вводу Ecoflex (баня)
            for k, (xx, sk) in enumerate(((sx, 'Т1'), (rx, 'Т2'))):
                ex = ECO[0] + (-0.04 if k == 0 else 0.04)          # трубы Т1, Т2 в оболочке Ecoflex
                pts = [(xx, GY, G_BOT), (xx, GY, 0.40), (ex, GY, 0.40), (ex, GY, 0.25)]
                pipe(f'{n}-{"П" if k == 0 else "О"}', sk, 'eco', pex[n], pts if k == 0 else pts[::-1], n,
                     f'{n} {"→" if k == 0 else "←"} баня (Ecoflex Quattro)')
        elif n == 'Н7':                         # загрузка Б1: сталь Ду25, к змеевику с севера
            ys = B1[1] + B1[2]
            s = pipe(f'{n}-П', 'Т1', 'steel', 25, [(sx, GY, G_TOP), (sx, GY, Z_HI), (sx, 11.55, Z_HI), (sx, 11.55, 0.95),
                                                    (B1[0], 11.55, 0.95), (B1[0], ys, 0.95)], n, 'Н7 → Б1: подача')
            r = pipe(f'{n}-О', 'Т2', 'steel', 25, [(B1[0], ys, 0.32), (B1[0], 11.55, 0.32), (rx, 11.55, 0.32),
                                                    (rx, 11.55, Z_HI), (rx, GY, Z_HI), (rx, GY, G_TOP)], n,
                     'Б1 → Н7: обратка')
            fit('ball', s, (sx, 11.55, 1.20), 'Кран шаровой Ду25', side='-x')
            fit('ball', r, (rx, 11.55, 0.60), 'Кран шаровой Ду25', side='-x')
            fit('vent', s, (sx, 11.55, Z_HI), 'Воздухоотводчик автоматический Ду15', side='+z')
    # ------------------------------------ Б1: ГВС, циркуляция, ХВС (граница — раздел ВК)
    bx, by, br = B1[0], B1[1], B1[2]
    pipe('Т3', 'Т3', 'steel', 25, [(bx, by, B1[4]), (bx, by, 2.10), (18.80, by, 2.10)], 'ГВС', 'Т3 от Б1 → ВК')
    t4 = pipe('Т4', 'Т4', 'steel', 20, [(18.80, by, 1.05), (bx - br, by, 1.05)], 'ГВС', 'Т4 от ВК → Б1')
    fit('check', t4, (18.95, by, 1.05), 'Клапан обратный Ду20 (ВК)')
    b1 = pipe('В1-Б1', 'В1', 'steel', 25, [(18.55, 11.00, 0.15), (bx - br * math.cos(math.asin(0.10 / br)), 11.00, 0.15)],
              'ГВС', 'В1 от ВК → Б1')
    fit('ball', b1, (18.62, 11.00, 0.15), 'Кран шаровой Ду25 (ВК)', side='+z')
    fit('safety', b1, (18.80, 11.00, 0.15), 'ГБ-ГВС — группа безопасности бойлера 6 бар', side='+z')
    rg = pipe('РБ-ГВС', 'В1', 'steel', 20, [(18.95, 11.00, 0.15), (18.95, 10.72, 0.15), (18.95, 10.72, 2.30),
                                           (RBG[0], 10.72, 2.30), (RBG[0], RBG[1], 2.30), (RBG[0], RBG[1], RBG[4])],
               'ГВС', 'Подключение РБ-ГВС')
    fit('ball', rg, (18.95, 10.72, 1.80), 'Кран шаровой с защитой от закрытия Ду20', side='-x')
    # ------------------------------------ газ (условно — проект ГСВ): ввод в восточной стене, обход сверху
    g = pipe('Г', 'Г', 'steel', 25, [(20.20, 12.85, 2.20), (16.45, 12.85, 2.20), (16.45, KC['К2'], 2.20),
                                     (16.45, KC['К2'], 0.95), (K_X, KC['К2'], 0.95), (K_X, KC['К2'], K_Z)],
             'газ', 'Газопровод к К2 (условно, ГСВ)')
    g1 = pipe('Г-К1', 'Г', 'steel', 20, [(16.45, KC['К1'], 2.20), (16.45, KC['К1'], 0.95), (K_X, KC['К1'], 0.95),
                                         (K_X, KC['К1'], K_Z)], 'газ', 'Газопровод к К1 (условно, ГСВ)')
    fit('gas', g, (19.65, 12.85, 2.20), 'Кран газовый на вводе (ГСВ)', side='-y')
    fit('gas', g, (16.20, KC['К2'], 0.95), 'Кран газовый перед котлом (ГСВ)', side='+z')
    fit('gas', g1, (16.20, KC['К1'], 0.95), 'Кран газовый перед котлом (ГСВ)', side='+z')
    # ------------------------------------ дымоходы: каскад Ø125 (уклон 3° к котлам), ПК Ø180 — в Ш-2
    y0c, y1c = 10.95, 12.92
    z0c = 2.24
    z1c = z0c + (y1c - y0c) * math.tan(math.radians(3))
    pipe('Д-каскад', 'Д', 'pp', 0.125, [(K_X, y0c, z0c), (K_X, y1c, z1c), (15.30, y1c, z1c), (15.30, y1c, H_SLAB - 0.05)],
         'дымоход', 'Каскадный дымоход Ø125 → Ш-2')
    for m, yc in KC.items():
        zc = z0c + (yc - y0c) * math.tan(math.radians(3))
        pipe(f'Д-{m}', 'Д', 'pp', 0.080, [(K_X, yc, K_Z + 0.70), (K_X, yc, zc - 0.04)], 'дымоход', f'{m}: дымоход Ø80')
    # ------------------------------------ конденсат К1, К2: сифоны котлов → нейтрализатор → трап (ВК)
    for m, yc in KC.items():
        pipe(f'К-{m}', 'К', 'pp', 0.032, [(16.10, yc + 0.15, K_Z), (16.10, yc + 0.15, 0.25), (16.30, yc + 0.15, 0.25)],
             'конденсат', f'{m}: конденсат (шланг из комплекта котла)')
    pipe('К-сб', 'К', 'pp', 0.032, [(16.30, KC['К1'] + 0.15, 0.25), (16.30, KC['К2'] + 0.15, 0.25)], 'конденсат',
         'Сборный конденсатопровод')
    pipe('К-нейтр', 'К', 'pp', 0.032, [(16.30, 11.43, 0.25), (16.48, 11.43, 0.25), (16.48, 11.43, 0.15)], 'конденсат',
         'Конденсат → нейтрализатор')
    pipe('К-трап', 'К', 'pp', 0.032, [(16.70, 11.36, 0.08), (17.00, 11.36, 0.08), (17.00, 11.13, 0.08)], 'конденсат',
         'Нейтрализатор → трап (ВК, условно)')
    pipe('Д-ПК', 'Д', 'pp', 0.180, [(16.55, 13.18, PK[5]), (16.55, 13.18, 1.90), (15.40, 13.18, 1.90),
                                    (15.40, 13.18, H_SLAB - 0.05)], 'дымоход', 'Дымоход ПК Ø180 → канал Ø280 в Ш-2')


# ---------------------------------------------------------------- сети ОВ в топочной (для увязки): из 3D-модели ОВ
def ov_context():
    import model3d as m3
    m3.RUNS.clear(), m3.BOXES.clear()
    m3.build_runs()
    m3.clamp_runs()
    m3.solve()
    m3.build_boxes()
    out = []
    bb = (X0 - 0.40, Y0 - 0.25, X1 + 1.20, Y1 + 0.10)

    def inside(p):
        return bb[0] <= p[0] <= bb[2] and bb[1] <= p[1] <= bb[3]
    for r in m3.RUNS:
        if r.floor != 1:
            continue
        for p0, p1, sh in m3.segments(r):
            if inside(p0) and inside(p1) and max(p0[2], p1[2]) > 1.0:
                w, h = sh if sh else (r.d, r.d)
                out.append(dict(seg=(p0, p1), w=w, h=h, rect=bool(sh), name=r.name, sys=r.sys))
    boxes = [dict(b=b.b, name=b.name) for b in m3.BOXES
             if b.floor == 1 and inside(((b.b[0] + b.b[3]) / 2, (b.b[1] + b.b[4]) / 2)) and b.id not in ('П1',)]
    return out, boxes


# ---------------------------------------------------------------- проверка коллизий
def seg_samples(p0, p1, w, h=None, rect=False, step=0.03):
    from model3d import frame
    L = math.dist(p0, p1)
    if L < 1e-9:
        return []
    t, u, v, _ = frame(p0, p1)
    h = h or w
    st = min(step, L)
    if rect:
        e = [abs(u[k]) * w / 2 + abs(v[k]) * h / 2 + abs(t[k]) * st / 2 for k in range(3)]
    else:
        e = [w / 2 * math.sqrt(max(0.0, 1 - t[k] ** 2)) + abs(t[k]) * st / 2 for k in range(3)]
    n = max(1, int(L / step))
    out = []
    for i in range(n + 1):
        c = [p0[k] + (p1[k] - p0[k]) * i / n for k in range(3)]
        out.append((c[0] - e[0], c[1] - e[1], c[2] - e[2], c[0] + e[0], c[1] + e[1], c[2] + e[2]))
    return out


def ends_touch(a, b, tol=0.012):
    """Стык двух труб: конец одной лежит на другой (тройник, переход) или концы совпадают."""
    for p, q in ((a, b), (b, a)):
        for e in (p.pts[0], p.pts[-1]):
            for s0, s1 in zip(q.pts, q.pts[1:]):
                if point_on_seg(e, s0, s1, tol=max(tol, (p.od + q.od) / 2)):
                    return e
    return None


def clashes(ctx_runs, ctx_boxes):
    import numpy as np
    items = []                                    # (имя, массив образцов, объект)
    for p in PIPES:
        smp = []
        for a, b in zip(p.pts, p.pts[1:]):
            smp += seg_samples(a, b, p.od)
        items.append(('pipe', p, np.array(smp)))
    for c in ctx_runs:
        items.append(('ctx', c, np.array(seg_samples(*c['seg'], c['w'], c['h'], c['rect']))))
    res = []

    def overlap(A, B, gap=0.003):
        return ((A[:, None, 0] < B[None, :, 3] - gap) & (A[:, None, 3] > B[None, :, 0] + gap) &
                (A[:, None, 1] < B[None, :, 4] - gap) & (A[:, None, 4] > B[None, :, 1] + gap) &
                (A[:, None, 2] < B[None, :, 5] - gap) & (A[:, None, 5] > B[None, :, 2] + gap))
    for i, (ka, a, A) in enumerate(items):
        for kb, b, B in items[i + 1:]:
            if ka == 'ctx' and kb == 'ctx' or not len(A) or not len(B):
                continue
            ov = overlap(A, B)
            if not ov.any():
                continue
            j = ends_touch(a, b) if ka == kb == 'pipe' else None
            ia, ib = np.nonzero(ov)
            bad = [(A[ia[k], :3] + A[ia[k], 3:]) / 2 for k in range(len(ia))]
            if j:
                bad = [c for c in bad if math.dist(c, j) > 0.12]
            if bad:
                c = bad[len(bad) // 2]
                na = a.id if ka == 'pipe' else a['name']
                nb = b.id if kb == 'pipe' else b['name']
                res.append(f'{na} × {nb} около ({c[0]:.2f}; {c[1]:.2f}; {c[2]:+.2f})')
    # трубы × оборудование (кроме подключений: конец трубы у корпуса)
    for ka, a, A in items:
        if ka != 'pipe' or not len(A):
            continue
        for e in EQUIP + [Eq('ctx', '', 'box', b['b'], b['name']) for b in ctx_boxes]:
            if e.id.endswith('-мотор'):
                continue
            x0, y0, z0, x1, y1, z1 = e.bbox() if e.kind != 'cylx' else cylx_bbox(e.g)
            ov = ((A[:, 0] < x1 - 0.003) & (A[:, 3] > x0 + 0.003) & (A[:, 1] < y1 - 0.003) & (A[:, 4] > y0 + 0.003) &
                  (A[:, 2] < z1 - 0.003) & (A[:, 5] > z0 + 0.003))
            if not ov.any():
                continue
            pts = [(A[k, :3] + A[k, 3:]) / 2 for k in np.nonzero(ov)[0]]
            ends = [q for q in (a.pts[0], a.pts[-1]) if x0 - 0.05 <= q[0] <= x1 + 0.05 and y0 - 0.05 <= q[1] <= y1 + 0.05
                    and z0 - 0.05 <= q[2] <= z1 + 0.05]
            pts = [c for c in pts if not any(math.dist(c, q) < 0.10 for q in ends)]
            if e.kind == 'cyl':                        # цилиндр: точная проверка по радиусу
                cx, cy, r, _, _ = e.g
                pts = [c for c in pts if math.hypot(c[0] - cx, c[1] - cy) < r + a.od / 2 - 0.003]
            if pts:
                c = pts[len(pts) // 2]
                res.append(f'{a.id} × {e.id} около ({c[0]:.2f}; {c[1]:.2f}; {c[2]:+.2f})')
    return res


def cylx_bbox(g):
    """Горизонтальный цилиндр вдоль y: (x, y0, z, y1, r)."""
    x, ya, z, yb, r = g
    return (x - r, min(ya, yb), z - r, x + r, max(ya, yb), z + r)


# ---------------------------------------------------------------- 3D-представление арматуры
def fit_parts(f):
    """Арматура → примитивы: [('cyl', p0, p1, d, rgb) | ('box', bbox, rgb)]."""
    ax = {'x': (1, 0, 0), 'y': (0, 1, 0), 'z': (0, 0, 1)}[f.axis]
    c = f.pos
    d = f.od

    def along(L, dia, rgb, off=0.0):
        p0 = tuple(c[k] + ax[k] * (off - L / 2) for k in range(3))
        p1 = tuple(c[k] + ax[k] * (off + L / 2) for k in range(3))
        return ('cyl', p0, p1, dia, rgb)
    side = f.side or ('+z' if f.axis != 'z' else '-y')
    sd = {'+x': (1, 0, 0), '-x': (-1, 0, 0), '+y': (0, 1, 0), '-y': (0, -1, 0), '+z': (0, 0, 1), '-z': (0, 0, -1)}[side]

    def stub(L, dia, rgb, start=0.0):
        p0 = tuple(c[k] + sd[k] * start for k in range(3))
        p1 = tuple(c[k] + sd[k] * (start + L) for k in range(3))
        return ('cyl', p0, p1, dia, rgb)
    brass, steel_, red, dark = (191, 145, 66), (148, 163, 184), (220, 38, 38), (30, 41, 59)
    hcol = SYS[f.sys][1] if f.sys in SYS else red
    k = f.kind
    if k in ('ball', 'gas'):
        return [along(max(0.06, d * 2.0), d * 1.45, brass), stub(0.035, 0.012, brass, d * 0.7),
                stub(0.012, 0.09, (250, 204, 21) if k == 'gas' else hcol, d * 0.7 + 0.035)]
    if k == 'check':
        return [along(max(0.055, d * 1.8), d * 1.5, brass)]
    if k == 'balance':
        return [along(0.08, d * 1.5, brass), stub(0.05, 0.03, (59, 130, 246), d * 0.7)]
    if k == 'filter':
        return [along(0.07, d * 1.5, brass), stub(0.05, d * 1.1, brass, d * 0.5)]
    if k == 'reducer':
        return [along(0.07, d * 1.6, brass), stub(0.06, 0.05, brass, d * 0.6)]
    if k == 'dirt':
        return [along(0.28, 0.10, (100, 116, 139))]
    if k == 'pump':
        return [along(0.16, d * 2.0, dark), stub(0.13, 0.10, (0, 128, 120), d)]
    if k == 'three':
        return [along(0.10, d * 1.6, brass), stub(0.05, d * 1.2, brass, d * 0.6) if False else
                ('cyl', tuple(c), (c[0], c[1] + 0.06, c[2]), d * 1.1, brass),
                stub(0.08, 0.06, steel_, d * 0.7)]
    if k == 'mano':
        return [stub(0.05, 0.012, brass, d / 2), stub(0.025, 0.063, (241, 245, 249), d / 2 + 0.05)]
    if k == 'therm':
        return [stub(0.04, 0.012, brass, d / 2), stub(0.02, 0.063, (241, 245, 249), d / 2 + 0.04)]
    if k == 'vent':
        return [stub(0.03, 0.016, brass, d / 2), stub(0.06, 0.035, brass, d / 2 + 0.03)]
    if k == 'drain':
        return [stub(0.05, 0.016, brass, d / 2), stub(0.04, 0.025, brass, d / 2 + 0.05)]
    if k == 'safety':
        return [along(0.08, d * 1.4, brass), stub(0.06, 0.03, brass, d * 0.6), stub(0.025, 0.063, (241, 245, 249),
                                                                                     d * 0.6 + 0.06)]
    return [along(0.06, d * 1.4, brass)]


# ---------------------------------------------------------------- выгрузка для просмотрщика (тот же формат, что ОВ)
def export_view(ctx_runs, ctx_boxes, walls):
    data = {'title': 'И05.09.26-ТМ. Котельная (топочная 1.6) — 3D-модель',
            'systems': {k: {'name': v[0], 'rgb': list(v[1])} for k, v in SYS.items()},
            'walls': walls, 'slabs': [], 'runs': [], 'boxes': [], 'labels': [], 'views': 'tm'}
    for p in PIPES:
        segs = [[*a, *b, round(p.od, 4), round(p.od, 4), 0] for a, b in zip(p.pts, p.pts[1:]) if math.dist(a, b) > 1e-6]
        data['runs'].append({'id': p.id, 'sys': p.sys, 'name': p.name, 'sec': p.label(), 'kind': 'pipe', 'floor': 1,
                             'segs': segs, 'L': None})
    for f in FITS:
        for part in fit_parts(f):
            if part[0] == 'cyl':
                _, p0, p1, dia, rgb = part
                data['runs'].append({'id': f.name, 'sys': 'AR', 'name': f.name, 'sec': f.pipe.label(), 'kind': 'fit',
                                     'floor': 1, 'segs': [[*map(lambda v: round(v, 4), p0), *map(lambda v: round(v, 4), p1),
                                                           round(dia, 4), round(dia, 4), 0]], 'rgb': list(rgb), 'L': None})
    for e in EQUIP:
        sysk = 'OV' if e.ctx else 'EQ'
        if e.kind == 'box':
            data['boxes'].append({'id': e.id, 'sys': sysk, 'kind': 'unit', 'name': e.name, 'floor': 1,
                                  'b': [round(v, 4) for v in e.g], 'rgb': list(e.rgb), 'L': None})
        elif e.kind == 'cyl':
            cx, cy, r, z0, z1 = e.g
            data['runs'].append({'id': e.id, 'sys': sysk, 'name': e.name, 'sec': '', 'kind': 'equip', 'floor': 1,
                                 'segs': [[cx, cy, z0, cx, cy, z1, round(2 * r, 4), round(2 * r, 4), 0]],
                                 'rgb': list(e.rgb), 'L': None})
        elif e.kind == 'cylx':
            x, ya, z, yb, r = e.g
            data['runs'].append({'id': e.id, 'sys': sysk, 'name': e.name, 'sec': '', 'kind': 'equip', 'floor': 1,
                                 'segs': [[x, ya, z, x, yb, z, round(2 * r, 4), round(2 * r, 4), 0]],
                                 'rgb': list(e.rgb), 'L': None})
        if e.pos or e.mark in ('П1', 'КШ-3'):
            x0, y0, z0, x1, y1, z1 = e.bbox() if e.kind != 'cylx' else cylx_bbox(e.g)
            if e.id.endswith('-мотор') or e.id in ('ПК-горелка', 'БП-шнек', 'П1-узел'):
                continue
            data['labels'].append({'x': round((x0 + x1) / 2, 3), 'y': round((y0 + y1) / 2, 3), 'z': round(z1 + 0.10, 3),
                                   'text': e.mark, 'sys': 'OV' if e.ctx else 'EQ', 'floor': 1, 'rgb': [30, 41, 59]})
    for c in ctx_runs:
        p0, p1 = c['seg']
        data['runs'].append({'id': c['name'], 'sys': 'OV', 'name': c['name'] + ' (ОВ)', 'sec': '', 'kind': 'ctx', 'floor': 1,
                             'segs': [[*map(lambda v: round(v, 4), p0), *map(lambda v: round(v, 4), p1), round(c['w'], 4),
                                       round(c['h'], 4), 1 if c['rect'] else 0]], 'L': None})
    for b in ctx_boxes:
        data['boxes'].append({'id': b['name'], 'sys': 'OV', 'kind': 'unit', 'name': b['name'] + ' (ОВ)', 'floor': 1,
                              'b': [round(v, 4) for v in b['b']], 'L': None})
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'model.json'), 'w') as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(',', ':'))
    return data

# ---------------------------------------------------------------- DWG 3D (через DXF, мм, начало — оси 1/А)
LAY = {'Т1': ('ТМ_3D_Т1', 1), 'Т2': ('ТМ_3D_Т2', 5), 'Т11': ('ТМ_3D_Т11', 30), 'Т21': ('ТМ_3D_Т21', 4),
       'Т3': ('ТМ_3D_Т3', 3), 'Т4': ('ТМ_3D_Т4', 82), 'В1': ('ТМ_3D_В1', 4), 'Г': ('ТМ_3D_Газ_условно', 2),
       'Д': ('ТМ_3D_Дымоходы', 8), 'EQ': ('ТМ_3D_Оборудование', 9), 'AR': ('ТМ_3D_Арматура', 42),
       'OV': ('ОВ_3D_для_увязки', 253), 'К': ('ТМ_3D_Конденсат', 8)}


def export_dxf(data):
    import ezdxf
    from model3d import seg_mesh, box_mesh, prism_mesh
    doc = ezdxf.new('R2018', setup=True)
    doc.units = 4
    doc.header['$INSUNITS'] = 4
    doc.header['$LASTSAVEDBY'] = ''
    msp = doc.modelspace()
    for k, (nm, aci) in LAY.items():
        lay = doc.layers.add(nm, color=aci)
        lay.rgb = SYS[k][1]
    doc.layers.add('АР_3D_стены', color=8)
    doc.layers.add('ТМ_3D_Марки', color=7)

    def poly(V, F, layer, rgb=None):
        m = msp.add_polyface(dxfattribs={'layer': layer})
        m.append_faces([[tuple(c * 1000 for c in V[i]) for i in f] for f in F])
        m.optimize()
        if rgb:
            m.rgb = tuple(rgb)
    for wl in data['walls']:
        V, F = prism_mesh(wl['outer'], wl['holes'], wl['z0'], wl['z1'])
        poly(V, F, 'АР_3D_стены')
    for r in data['runs']:
        for s in r['segs']:
            p0, p1, w, h, rect = s[:3], s[3:6], s[6], s[7], s[8]
            if math.dist(p0, p1) < 1e-6:
                continue
            ext = w / 2 if r['kind'] == 'pipe' else 0.0
            n = 12 if r['kind'] in ('pipe', 'fit') else 24
            V, F = seg_mesh(p0, p1, w, h, rect, min(ext, 0.03), n=n)
            poly(V, F, LAY[r['sys']][0], r.get('rgb') if r['sys'] in ('AR', 'EQ') else None)
    for b in data['boxes']:
        V, F = box_mesh(b['b'])
        poly(V, F, LAY[b['sys']][0], b.get('rgb') if b['sys'] == 'EQ' else None)
    for lb in data['labels']:
        msp.add_text(lb['text'], dxfattribs={'layer': 'ТМ_3D_Марки', 'height': 60,
                                            'insert': (lb['x'] * 1000, lb['y'] * 1000, lb['z'] * 1000)})
    doc.set_modelspace_vport(height=6000, center=(17800, 11300))
    path = os.path.join(OUT, 'I05-09-26-TM-3D.dxf')
    doc.saveas(path)
    return path


# ---------------------------------------------------------------- IFC4 (в координатах выгрузки Revit, как ОВ)
FIT_IFC = {'ball': ('IfcValve', 'ISOLATING'), 'gas': ('IfcValve', 'GASCOCK'), 'check': ('IfcValve', 'CHECK'),
           'balance': ('IfcValve', 'REGULATING'), 'three': ('IfcValve', 'MIXING'), 'safety': ('IfcValve', 'SAFETYCUTOFF'),
           'reducer': ('IfcValve', 'PRESSUREREDUCING'), 'vent': ('IfcValve', 'AIRRELEASE'),
           'drain': ('IfcValve', 'DRAWOFFCOCK'), 'filter': ('IfcFilter', 'STRAINER'), 'dirt': ('IfcFilter', 'STRAINER'),
           'pump': ('IfcPump', 'CIRCULATOR'), 'mano': ('IfcFlowInstrument', 'PRESSUREGAUGE'),
           'therm': ('IfcFlowInstrument', 'THERMOMETER')}
SYS_IFC = {'Т1': 'HEATING', 'Т2': 'HEATING', 'Т11': 'HEATING', 'Т21': 'HEATING', 'Т3': 'DOMESTICHOTWATER',
           'Т4': 'DOMESTICHOTWATER', 'В1': 'DOMESTICCOLDWATER', 'Г': 'GAS', 'Д': 'EXHAUST', 'К': 'DRAINAGE'}


def export_ifc(data):
    import ifcopenshell
    import ifcopenshell.api
    from model3d import frame
    from underlay import OX, OY
    api = ifcopenshell.api.run
    f = ifcopenshell.file(schema='IFC4')
    proj = api('root.create_entity', f, ifc_class='IfcProject', name='И05.09.26-ТМ')
    api('unit.assign_unit', f, length={'is_metric': True, 'raw': 'METRE'})
    ctx = api('context.add_context', f, context_type='Model')
    body = api('context.add_context', f, context_type='Model', context_identifier='Body', target_view='MODEL_VIEW',
               parent=ctx)
    site = api('root.create_entity', f, ifc_class='IfcSite', name='Участок 50:08:0050209:1600')
    bld = api('root.create_entity', f, ifc_class='IfcBuilding', name='Жилой дом')
    st = api('root.create_entity', f, ifc_class='IfcBuildingStorey', name='Этаж 1')
    space = api('root.create_entity', f, ifc_class='IfcSpace', name='1.6', )
    space.LongName = 'Топочная (котельная)'
    api('aggregate.assign_object', f, relating_object=proj, products=[site])
    api('aggregate.assign_object', f, relating_object=site, products=[bld])
    api('aggregate.assign_object', f, relating_object=bld, products=[st])
    api('aggregate.assign_object', f, relating_object=st, products=[space])
    for obj in (site, bld, st, space):
        api('geometry.edit_object_placement', f, product=obj)
    bld.ObjectPlacement.RelativePlacement.Location.Coordinates = (OX / 1000, OY / 1000, 0.0)
    bld.ObjectPlacement.PlacementRelTo = site.ObjectPlacement
    st.ObjectPlacement.PlacementRelTo = bld.ObjectPlacement
    st.Elevation = 0.0
    space.ObjectPlacement.PlacementRelTo = st.ObjectPlacement

    def ax(p, z=(0.0, 0.0, 1.0), x=(1.0, 0.0, 0.0)):
        return f.createIfcAxis2Placement3D(f.createIfcCartesianPoint(tuple(map(float, p))),
                                           f.createIfcDirection(tuple(map(float, z))),
                                           f.createIfcDirection(tuple(map(float, x))))
    styles = {}

    def style(rgb, tr=0.0):
        k = (tuple(rgb), tr)
        if k not in styles:
            col = f.createIfcColourRgb(None, *(c / 255 for c in rgb))
            styles[k] = f.createIfcSurfaceStyle(None, 'BOTH', [f.createIfcSurfaceStyleShading(col, tr)])
        return styles[k]

    def shape(items, rgb, tr=0.0):
        for it in items:
            f.createIfcStyledItem(it, [style(rgb, tr)], None)
        rep = f.createIfcShapeRepresentation(body, 'Body', 'SweptSolid', items)
        return f.createIfcProductDefinitionShape(None, None, [rep])

    def cyl(p0, p1, dia):
        t, u, v, L = frame(p0, p1)
        prof = f.createIfcCircleProfileDef('AREA', None, f.createIfcAxis2Placement2D(
            f.createIfcCartesianPoint((0.0, 0.0)), None), float(dia / 2))
        return f.createIfcExtrudedAreaSolid(prof, ax(p0, t, u), f.createIfcDirection((0.0, 0.0, 1.0)), float(L))

    def boxs(b):
        x0, y0, z0, x1, y1, z1 = b
        prof = f.createIfcRectangleProfileDef('AREA', None, f.createIfcAxis2Placement2D(
            f.createIfcCartesianPoint(((x1 - x0) / 2, (y1 - y0) / 2)), None), float(x1 - x0), float(y1 - y0))
        return f.createIfcExtrudedAreaSolid(prof, ax((x0, y0, z0)), f.createIfcDirection((0.0, 0.0, 1.0)),
                                            float(max(z1 - z0, 0.001)))

    def poly_solid(outer, holes, z0, z1):
        def curve(pts):
            P = [f.createIfcCartesianPoint((float(x), float(y))) for x, y in pts]
            return f.createIfcPolyline(P + [P[0]])
        prof = (f.createIfcArbitraryProfileDefWithVoids('AREA', None, curve(outer), [curve(h) for h in holes]) if holes
                else f.createIfcArbitraryClosedProfileDef('AREA', None, curve(outer)))
        return f.createIfcExtrudedAreaSolid(prof, ax((0.0, 0.0, z0)), f.createIfcDirection((0.0, 0.0, 1.0)),
                                            float(z1 - z0))

    def place(prod):
        prod.ObjectPlacement = f.createIfcLocalPlacement(st.ObjectPlacement, ax((0.0, 0.0, 0.0)))

    def pset(prod, props):
        ps = api('pset.add_pset', f, product=prod, name='ТМ_Параметры')
        api('pset.edit_pset', f, pset=ps, properties={k: v for k, v in props.items() if v not in (None, '')})

    items_all, by_sys = [], {}
    for wl in data['walls']:
        w = api('root.create_entity', f, ifc_class='IfcWall', name='Стена по АР (для привязки)')
        w.Representation = shape([poly_solid(wl['outer'], wl['holes'], wl['z0'], wl['z1'])], (217, 217, 209), 0.55)
        place(w)
        items_all.append(w)
    for p in PIPES:
        e = api('root.create_entity', f, ifc_class='IfcPipeSegment', name=p.name)
        e.Tag = p.id
        e.ObjectType = 'Дымоход' if p.sys == 'Д' else None
        solids = [cyl(a, b, p.od) for a, b in zip(p.pts, p.pts[1:]) if math.dist(a, b) > 1e-6]
        e.Representation = shape(solids, SYS[p.sys][1])
        place(e)
        items_all.append(e)
        by_sys.setdefault(p.sys, []).append(e)
        pset(e, {'Система': SYS[p.sys][0], 'Материал': 'ПП (полипропилен)' if p.sys == 'К' else MAT_NAME[p.mat],
                 'Типоразмер': p.label(),
                 'Длина, м': round(p.length(), 2), 'Участок': p.circ})
    for fi in FITS:
        cls, pt = FIT_IFC.get(fi.kind, ('IfcValve', 'NOTDEFINED'))
        e = api('root.create_entity', f, ifc_class=cls, name=fi.name)
        e.PredefinedType = pt
        solids, rgb = [], None
        for part in fit_parts(fi):
            if part[0] == 'cyl':
                _, p0, p1, dia, c = part
                if math.dist(p0, p1) > 1e-6:
                    solids.append(cyl(p0, p1, dia))
                    rgb = rgb or c
        e.Representation = shape(solids, rgb or (180, 140, 60))
        place(e)
        items_all.append(e)
        by_sys.setdefault(fi.sys, []).append(e)
        pset(e, {'Система': SYS[fi.sys][0], 'Типоразмер': fi.pipe.label(), 'Трубопровод': fi.pipe.name})
    for q in EQUIP:
        cls = q.ifc
        e = api('root.create_entity', f, ifc_class=cls, name=q.name)
        e.Tag = q.mark
        if q.kind == 'box':
            sol = [boxs(q.g)]
        elif q.kind == 'cyl':
            cx, cy, r, z0, z1 = q.g
            sol = [cyl((cx, cy, z0), (cx, cy, z1), 2 * r)]
        else:
            x, ya, z, yb, r = q.g
            sol = [cyl((x, ya, z), (x, yb, z), 2 * r)]
        e.Representation = shape(sol, q.rgb if not q.ctx else SYS['OV'][1], 0.5 if q.ctx else 0.0)
        place(e)
        items_all.append(e)
        pset(e, {'Марка': q.mark, 'Позиция ТМ.СО': q.pos, 'Раздел': 'ОВ (для увязки)' if q.ctx else 'ТМ'})
    api('spatial.assign_container', f, relating_structure=st, products=items_all)
    for k, objs in by_sys.items():
        if k not in SYS_IFC:
            continue
        s = api('system.add_system', f, ifc_class='IfcDistributionSystem')
        s.Name = SYS[k][0]
        s.PredefinedType = SYS_IFC[k]
        api('system.assign_system', f, products=objs, system=s)
    path = os.path.join(OUT, 'I05-09-26-TM-3D.ifc')
    f.write(path)
    return path


MAT_NAME = {'steel': 'Сталь ВГП ГОСТ 3262-75', 'pex': 'PE-Xa с антидиффузионным слоем',
            'eco': 'Uponor Ecoflex Quattro (PE-Xa)', 'pp': 'Дымоход PP (комплект котла) / нерж. сталь'}


# ---------------------------------------------------------------- данные для листов и ТМ.СО
def export_data():
    out = {'pipes': [], 'fits': [], 'equip': [], 'room': [X0, Y0, X1, Y1], 'h_slab': H_SLAB}
    for p in PIPES:
        out['pipes'].append({'id': p.id, 'sys': p.sys, 'mat': p.mat, 'dn': p.dn, 'od': p.od, 'label': p.label(),
                             'circ': p.circ, 'name': p.name, 'pts': p.pts, 'L': round(p.length(), 3)})
    for fi in FITS:
        out['fits'].append({'kind': fi.kind, 'pipe': fi.pipe.id, 'pos': fi.pos, 'name': fi.name, 'axis': fi.axis,
                            'side': fi.side, 'sys': fi.sys, 'label': fi.pipe.label(), 'dn': fi.pipe.dn,
                            'mat': fi.pipe.mat})
    for q in EQUIP:
        out['equip'].append({'id': q.id, 'mark': q.mark, 'kind': q.kind, 'g': q.g, 'name': q.name, 'pos': q.pos,
                             'ctx': q.ctx, 'bbox': q.bbox() if q.kind != 'cylx' else cylx_bbox(q.g)})
    with open(os.path.join(OUT, 'tm.json'), 'w') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=0)
    return out


def room_walls():
    """Стены у топочной — из штриховок АР03 (через model3d.walls), обрезка рамкой вокруг помещения."""
    import model3d as m3
    from shapely.geometry import box as sbox
    W = m3.walls()
    clip = sbox(X0 - 0.95, Y0 - 0.45, X1 + 0.50, Y1 + 0.45)
    out = []
    for g in m3.geoms(W[1].intersection(clip)):
        if g.is_empty or g.area < 1e-4 or g.geom_type != 'Polygon':
            continue
        out.append({'floor': 1, 'z0': 0.0, 'z1': H_SLAB,
                    'outer': [[round(x, 4), round(y, 4)] for x, y in g.exterior.coords[:-1]],
                    'holes': [[[round(x, 4), round(y, 4)] for x, y in h.coords[:-1]] for h in g.interiors]})
    return out


def build():
    PIPES.clear(), FITS.clear(), EQUIP.clear()
    build_equipment()
    build_pipes()


def main():
    build()
    ctx_runs, ctx_boxes = ov_context()
    walls = room_walls()
    cl = clashes(ctx_runs, ctx_boxes)
    data = export_view(ctx_runs, ctx_boxes, walls)
    os.makedirs(OUT, exist_ok=True)
    export_data()
    if '--no-export' not in sys.argv:
        print(export_dxf(data))
        print(export_ifc(data))
    with open(os.path.join(OUT, 'kollizii.txt'), 'w') as fh:
        fh.write('\n'.join(cl) or '—')
    print('труб', len(PIPES), 'арматуры', len(FITS), 'оборудования', len(EQUIP), 'контекст ОВ', len(ctx_runs))
    print('коллизии:', *(cl or ['—']), sep='\n  ')


if __name__ == '__main__':
    main()
