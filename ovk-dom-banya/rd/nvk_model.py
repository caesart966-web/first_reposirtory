"""И05.09.26-НВК. Наружные сети водопровода и канализации участка (з/у 19, ул. Лесная, д. Исаково):
ввод В1, выпуски К1 дома и бани, дренаж Др и ливневая К2 вокруг зданий, подводка полива КХ-8.
Единый источник плана, профилей, таблицы колодцев, расчётов, НВК.СО и ВОР.

Координаты — м в осях дома (пересечение осей 1/А = 0,0; x вдоль 1→5, y вдоль А→Ж; север — +y, улица — −y),
как в ВК, ОВ и ТМ. Привязка к МСК-50 — nvk/house2msk.json (по границам участка), топосъёмка — nvk/topo_house_axes.dxf.
Отметки — абсолютные, Балтийская система (как топосъёмка и исполнительные схемы поселковых сетей).

Точки подключения (исполнительные схемы ООО «Лика»: ИС-3ВК, ИС-3КК, ИС-3ЛК; топосъёмка — «вых. закл. тр.»):
- К1 — дворовый колодец ДК5-018 у южной границы участка (крышка 186,78, лоток 184,98 по съёмке; 186,750 / 185,019
  по ИС-3КК), выпуск Ø110 от него — в КК355а;
- В1 — выпуск ПЭ Ø32 в гильзе ПНД Ø63 от ВК217 у юго-восточного угла участка;
- К2 и Др — выпуск ПЭ Ø63 от ЛК355 там же (ИС-3ЛК, глубина 1,0–1,7 м).

Допущения (вопросы Заказчику — ASSUME): ±0,000 дома 186,90 и бани 186,85 (наивысшая отметка земли у контура
+0,15; по разрезам АР земля у зданий −0,150…−0,300), планировка у зданий −0,300; принадлежность выпусков ЛК и ВК у
юго-восточного угла и лоток выпуска ЛК (≈185,10) — уточнить шурфованием до начала работ.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, 'out', 'nvk')

H0, H0B = 186.90, 186.85                     # ±0,000 дома и бани, абс. (допущение)
BATH_AX = (7.132, 25.000)                    # оси 1/А бани в осях дома (ГП01)
HOUSE = (-0.24, -0.24, 20.24, 16.94)         # наружный контур стен дома (ГП01)
BATHB = (6.89, 23.96, 23.27, 31.84)          # наружный контур бани с террасой (ГП01)
PORCH_S = (5.55, -1.25, 10.00, -0.24)        # крыльцо дома, юг (ГП01, A-FLOR)
PORCH_E = (20.24, 8.40, 22.00, 11.60)        # крыльцо 1.6, восток
FROST = 1.10                                 # нормативная глубина промерзания (ИГИ ЭККЕР), м
PLAN_DH = 0.30                               # планировка у зданий: −0,300 от ±0,000

ASSUME = {
    'h0': f'±0,000 дома = {H0:.2f}, бани = {H0B:.2f} (абс.) — по съёмке: наивысшая отметка земли у контура дома '
          '186,75 + 0,15 (разрезы АР: земля у здания −0,150…−0,300); уточнить по вертикальной планировке',
    'plan': 'планировка у зданий −0,300 (186,60 у дома, 186,55 у бани), далее — сопряжение с существующей '
            'поверхностью на 3 м; вертикальная планировка участка не выполнялась',
    'stubs': 'выпуски ВК (Ø32 в гильзе Ø63, от ВК217) и ЛК (Ø63, от ЛК355) у юго-восточного угла участка — по ИС и '
             'топосъёмке («вых. закл. тр.»); какой из двух — водопровод, а какой — ливнёвка, и лоток ЛК (принят '
             '185,10) — уточнить шурфованием до начала работ',
    'dk': 'ДК5-018 — дворовый колодец участка (ИС-3КК): крышка 186,78, лоток 184,98 по съёмке 2026 г. '
          '(186,750 / 185,019 по ИС); врезка двух выпусков в существующий колодец',
    'roof': 'стояки внутренних водостоков — в стенах (Заказчик); места выпусков К2 — по привязке воронок',
}

# ====================================================================================== рельеф
# отметки земли по топосъёмке (точки вне навала грунта), оси дома
SPOTS = [
    (-7.8, 6.7, 186.92), (-7.2, 15.5, 186.90), (-6.3, 24.5, 186.88), (-5.4, 34.0, 186.88), (-3.8, 39.3, 186.86),
    (5.2, 39.0, 186.76), (14.8, 38.9, 186.42), (22.7, 39.0, 186.43), (6.0, 31.1, 186.68), (13.7, 31.0, 186.52),
    (22.4, 31.9, 186.19), (5.8, 21.0, 186.42), (15.3, 20.6, 186.10), (24.2, 20.6, 185.99), (32.7, 20.4, 185.92),
    (24.6, 10.9, 185.95), (33.7, 10.7, 185.92), (30.7, 1.3, 185.88), (19.6, 1.0, 186.08), (12.1, 11.2, 186.13),
    (5.7, 12.2, 186.43), (1.45, 1.45, 186.73), (4.45, 0.35, 186.79), (6.5, -0.9, 186.82), (2.8, -3.4, 186.80),
    (5.3, -3.6, 186.79), (9.42, -3.85, 186.78), (16.0, -5.5, 186.40), (-8.4, -2.4, 187.15), (-12.8, -5.7, 187.09),
]


def g_exist(x, y):
    """Существующая поверхность: обратные квадраты расстояний по 6 ближайшим точкам съёмки."""
    d = sorted(((math.hypot(x - a, y - b), z) for a, b, z in SPOTS))[:6]
    if d[0][0] < 0.05:
        return d[0][1]
    w = [1 / r ** 2 for r, _ in d]
    return sum(wi * z for wi, (_, z) in zip(w, d)) / sum(w)


def _dist_rect(x, y, r):
    dx = max(r[0] - x, 0, x - r[2])
    dy = max(r[1] - y, 0, y - r[3])
    return math.hypot(dx, dy)


def g_design(x, y):
    """Проектная поверхность (допущение): у зданий −0,300, на 3…6 м — сопряжение с существующей."""
    best = None
    for r, h0 in ((HOUSE, H0), (BATHB, H0B)):
        d = _dist_rect(x, y, r)
        if best is None or d < best[0]:
            best = (d, h0 - PLAN_DH)
    d, zp = best
    ze = g_exist(x, y)
    if d <= 3.0:
        return zp
    if d >= 6.0:
        return ze
    t = (d - 3.0) / 3.0
    return zp + (ze - zp) * t


# ====================================================================================== объекты
WELLS, PIPES = [], []


class Well:
    def __init__(self, wid, sys_, kind, x, y, dn, bottom=None, exist=False, note='', hatch='Л'):
        self.id, self.sys, self.kind, self.x, self.y, self.dn = wid, sys_, kind, x, y, dn
        self.exist, self.note, self.hatch = exist, note, hatch
        self.cover = round(g_design(x, y), 2) if not exist else None
        self.bottom = bottom
        self.ins, self.outs = [], []        # (pipe, отметка лотка)
        WELLS.append(self)

    @property
    def xy(self):
        return (self.x, self.y)

    def tray(self):
        """Лоток выходящей трубы (у существующего — по съёмке)."""
        if self.outs:
            return min(z for _, z in self.outs)
        return self.bottom


class Pipe:
    def __init__(self, pid, sys_, pts, dn, od, mat, z, i=None, kind='grav', frm=None, to=None, note='',
                 sleeve=None, trench=None):
        self.id, self.sys, self.pts, self.dn, self.od, self.mat = pid, sys_, [tuple(p) for p in pts], dn, od, mat
        self.z = list(z)                  # самотёк — лоток в вершинах; напорные — ось
        self.i, self.kind, self.frm, self.to, self.note = i, kind, frm, to, note
        self.sleeve, self.trench = sleeve, trench
        self.ins = []                     # участки утепления: (s0, s1)
        PIPES.append(self)

    def length(self):
        return sum(math.dist(a, b) for a, b in zip(self.pts, self.pts[1:]))

    def segs(self):
        out, s = [], 0.0
        for k, (a, b) in enumerate(zip(self.pts, self.pts[1:])):
            L = math.dist(a, b)
            out.append((s, s + L, a, b, self.z[k], self.z[k + 1]))
            s += L
        return out

    def at(self, s):
        """(x, y, z) на расстоянии s от начала."""
        for s0, s1, a, b, z0, z1 in self.segs():
            if s <= s1 + 1e-9:
                t = 0 if s1 == s0 else (s - s0) / (s1 - s0)
                return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, z0 + (z1 - z0) * t)
        a, z = self.pts[-1], self.z[-1]
        return (a[0], a[1], z)

    def bottom(self, s):
        """Низ трубы (наружный) на расстоянии s."""
        z = self.at(s)[2]
        return z if self.kind == 'grav' else z - self.od / 2

    def top(self, s):
        z = self.at(s)[2]
        return z + self.od if self.kind == 'grav' else z + self.od / 2


def grav(pid, sys_, pts, z0, i, dn, od, mat, frm=None, to=None, note='', drop_end=None, trench=None):
    """Самотёчная линия: z0 — лоток в начале, i — уклон по длине."""
    z, zs = z0, [z0]
    for a, b in zip(pts, pts[1:]):
        z -= i * math.dist(a, b)
        zs.append(round(z, 3))
    zs[0] = round(z0, 3)
    p = Pipe(pid, sys_, pts, dn, od, mat, zs, i=i, frm=frm, to=to, note=note, trench=trench)
    if frm:
        frm.outs.append((p, zs[0]))
    if to:
        to.ins.append((p, zs[-1]))
    return p


def vk_end(pid):
    """Конец выпуска К1 из модели ВК: (x, y в осях дома, лоток абс.)."""
    import vk_model as VK
    p = {q.id: q for q in VK.PIPES}[pid]
    x, y, z = p.pts[-1]
    if p.bld == 'b':
        return (x + BATH_AX[0], y + BATH_AX[1], round(H0B + z - p.od / 2, 3))
    return (x, y, round(H0 + z - p.od / 2, 3))


# ====================================================================================== К1
PP110 = 'ПП SN8 Ø110 (ГОСТ 32413)'
PP160 = 'ПП SN8 Ø160 (ГОСТ 32413)'
DK = Well('ДК5-018', 'К1', 'ДК (сущ.)', 9.42, -3.85, 1000, bottom=184.98, exist=True,
          note='существующий дворовый колодец (ИС-3КК): врезка выпусков дома и бани')
DK.cover = 186.78
I_OUT_H = 0.10                                # выпуск дома: 3 м до ДК, перепад в ДК ≤ 0,5 м
I_Y = 0.010                                   # дворовая сеть Ø160 (не менее 0,008, п. 5.4.? СП 32 — табл. уклонов)

xh, yh, zh = vk_end('К1-1')
k1h = grav('К1-1н', 'К1', [(xh, yh), DK.xy], zh, I_OUT_H, 110, 0.110, PP110, to=DK,
           note='выпуск К1-1 дома (продолжение ВК) в ДК5-018')
xb, yb, zb = vk_end('К1-б')
KK1 = Well('КК-1', 'К1', 'КК', xb, 21.00, 630, note='первый колодец на выпуске бани')
KK2 = Well('КК-2', 'К1', 'КК', -2.00, 21.00, 630, note='поворот')
KK3 = Well('КК-3', 'К1', 'КК', -2.00, -2.00, 630, note='поворот')
k1b = grav('К1-бн', 'К1', [(xb, yb), KK1.xy], zb, 0.02, 110, 0.110, PP110, to=KK1,
           note='выпуск К1-б бани (продолжение ВК) в КК-1')
z = k1b.z[-1] + 0.110 - 0.160                 # Ø110 → Ø160: по шелыгам
k12 = grav('К1-б1', 'К1', [KK1.xy, KK2.xy], z, I_Y, 160, 0.160, PP160, frm=KK1, to=KK2)
k23 = grav('К1-б2', 'К1', [KK2.xy, KK3.xy], k12.z[-1] - 0.02, I_Y, 160, 0.160, PP160, frm=KK2, to=KK3)
k3d = grav('К1-б3', 'К1', [KK3.xy, DK.xy], k23.z[-1] - 0.02, I_Y, 160, 0.160, PP160, frm=KK3, to=DK)

# ====================================================================================== дренаж и К2
OFF_D, OFF_S = 0.75, 1.00                     # оси дренажа и К2 от наружной грани стен (общая траншея)
I_D = 0.005


def ring(r, off):
    return (r[0] - off, r[1] - off, r[2] + off, r[3] + off)


RD, RS = ring(HOUSE, OFF_D), ring(HOUSE, OFF_S)          # дом: дренаж, К2
BD, BS = ring(BATHB, OFF_D), ring(BATHB, OFF_S)          # баня
DR = {}
for wid, (x, y), note in (('Др-1', (RD[0], RD[3]), 'северо-западный угол дома — начало'),
                          ('Др-2', (RD[2], RD[3]), 'северо-восточный угол дома, приём транзита от бани'),
                          ('Др-3', (RD[2], RD[1]), 'юго-восточный угол дома'),
                          ('Др-4', (RD[0], RD[1]), 'юго-западный угол дома'),
                          ('ДрБ-1', (BD[0], BD[3]), 'северо-западный угол бани — начало'),
                          ('ДрБ-2', (BD[2], BD[3]), 'северо-восточный угол бани'),
                          ('ДрБ-3', (BD[2], BD[1]), 'юго-восточный угол бани — выход транзита'),
                          ('ДрБ-4', (BD[0], BD[1]), 'юго-западный угол бани')):
    DR[wid] = Well(wid, 'Др', 'ДрК', x, y, 315, note=note)
KL1 = Well('КЛ-1', 'К2', 'КЛ', 20.30, -2.80, 1500,
           note='сборный колодец К2 и Др с отстойной частью и регулирующим объёмом → выпуск ЛК Ø63')
LK_STUB = (21.05, -3.80, 185.10)              # выпуск ЛК Ø63 (лоток — допущение, шурф)
VK_STUB = (21.40, -3.10)                      # выпуск ВК Ø32 в гильзе Ø63
DRAIN = 'ПВХ/ПНД гофр. перфорир. Ø110 в геотекстиле'
DRAIN_T = 'ПП SN8 Ø110 (транзит, без перфорации)'
STORM = 'ПП SN8 Ø110 (ГОСТ 32413)'

DS = 0.235                                    # К2 выше дренажа в общей траншее: выходы К2 и Др расходятся по высоте
Z_S1 = round(H0 - 1.276, 3)                   # лоток К2 в начале кольца дома (Н1): под выпуском К1-1 с зазором
Z_DR1 = round(Z_S1 - DS, 3)                   # лоток дренажа в Др-1
Z_SB1 = round(H0B - 1.14, 3)                  # лоток К2 в начале кольца бани (Б1): под выпуском К1-б
Z_DRB1 = round(Z_SB1 - DS - 0.015, 3)
d = DR


def leg(pid, a, b, z0, mat=DRAIN, sys_='Др', trench='Т-дом', note=''):
    return grav(pid, sys_, [d[a].xy, d[b].xy], z0, I_D, 110, 0.110, mat, frm=d[a], to=d[b], trench=trench, note=note)


dA1 = leg('Др-1/2', 'Др-1', 'Др-2', Z_DR1)
dA2 = leg('Др-2/3', 'Др-2', 'Др-3', dA1.z[-1])
dB1 = leg('Др-1/4', 'Др-1', 'Др-4', Z_DR1)
dB2 = leg('Др-4/3', 'Др-4', 'Др-3', dB1.z[-1])
dC1 = leg('ДрБ-1/2', 'ДрБ-1', 'ДрБ-2', Z_DRB1, trench='Т-баня')
dC2 = leg('ДрБ-2/3', 'ДрБ-2', 'ДрБ-3', dC1.z[-1], trench='Т-баня')
dC3 = leg('ДрБ-1/4', 'ДрБ-1', 'ДрБ-4', Z_DRB1, trench='Т-баня')
dC4 = leg('ДрБ-4/3', 'ДрБ-4', 'ДрБ-3', dC3.z[-1], trench='Т-баня')
dT = leg('Др-Т', 'ДрБ-3', 'Др-2', min(dC2.z[-1], dC4.z[-1]), mat=DRAIN_T, trench='Т-транзит',
         note='транзит дренажа бани к дому')
dK = grav('Др-К', 'Др', [d['Др-3'].xy, KL1.xy], min(dA2.z[-1], dB2.z[-1]), I_D, 110, 0.110, DRAIN_T,
          frm=d['Др-3'], to=KL1, note='в КЛ-1 через обратный клапан', trench='Т-КЛ')

# К2 — кольцевые коллекторы вдоль дренажа (в той же траншее, снаружи и выше на DS)
S = {'Н1': (RS[0], RS[3]), 'Н2': (RS[2], RS[3]), 'Н3': (RS[2], RS[1]), 'Н4': (RS[0], RS[1]),
     'Б1': (BS[0], BS[3]), 'Б2': (BS[2], BS[3]), 'Б3': (BS[2], BS[1]), 'Б4': (BS[0], BS[1])}
sA = grav('К2-А', 'К2', [S['Н1'], S['Н2'], S['Н3']], Z_S1, I_D, 110, 0.110, STORM, trench='Т-дом',
          note='кольцо К2 дома, север и восток')
sB = grav('К2-Б', 'К2', [S['Н1'], S['Н4'], S['Н3']], Z_S1, I_D, 110, 0.110, STORM, trench='Т-дом',
          note='кольцо К2 дома, запад и юг')
sCA = grav('К2-БА', 'К2', [S['Б1'], S['Б2'], S['Б3']], Z_SB1, I_D, 110, 0.110, STORM, trench='Т-баня',
           note='кольцо К2 бани, север и восток')
sCB = grav('К2-ББ', 'К2', [S['Б1'], S['Б4'], S['Б3']], Z_SB1, I_D, 110, 0.110, STORM, trench='Т-баня',
           note='кольцо К2 бани, запад и юг')
sT = grav('К2-Т', 'К2', [S['Б3'], S['Н2']], min(sCA.z[-1], sCB.z[-1]), I_D, 110, 0.110, STORM, trench='Т-транзит',
          note='транзит К2 бани к кольцу дома')
sK = grav('К2-К', 'К2', [S['Н3'], KL1.xy], min(sA.z[-1], sB.z[-1]), I_D, 110, 0.110, STORM, to=KL1, trench='Т-КЛ',
          note='в КЛ-1')
# лоток гаража (ВК: К2-1 до 1 м за плитой) → кольцо К2 (южная ветвь) с перепадом
K2G = (19.60, 0.10)
s_g = Pipe('К2-1н', 'К2', [K2G, (19.60, RS[1] + 0.25)], 110, 0.110, STORM,
           [round(H0 - 0.835, 3), round(H0 - 0.835 - 0.02 * (K2G[1] - RS[1] - 0.25), 3)], i=0.02,
           note='выпуск лотка гаража ЛГ-1 (ВК, К2-1) → кольцо К2: отвод 45° вниз и косой тройник')
# выпуск КЛ-1 → ЛК
KL_OUT = round(LK_STUB[2] + 0.02 * math.dist(KL1.xy, LK_STUB[:2]), 3)
s_out = grav('К2-ЛК', 'К2', [KL1.xy, LK_STUB[:2]], KL_OUT, 0.02, 63, 0.063, 'ПЭ 100 SDR17 63×3,8', frm=KL1,
             note='выпуск КЛ-1 → существующий выпуск ЛК Ø63 (муфта электросварная Ø63)')
KL1.bottom = round(KL_OUT - 0.50, 2)          # отстойная часть 0,5 м

# ====================================================================================== В1
Z_VV = round(H0 - 0.85, 3)                    # ось ввода у наружной грани фундамента (ВК)
X_W = 22.80                                    # трасса вдоль восточной стороны: 1,5 м от К2
Y_VV = 9.45
XR = 21.45                                     # подъём к вводу — снаружи траншеи дренажа
Z_STUB = 184.60                                # ось выпуска ВК Ø32 у участка (ИС: глубина 1,6–1,8 м)
Z_RUN = 184.95
v1 = Pipe('В1-н', 'В1', [VK_STUB, (X_W, -1.70), (X_W, Y_VV), (XR, Y_VV), (XR, Y_VV), (20.60, Y_VV)],
          32, 0.032, 'ПЭ 100 SDR11 32×3,0 (ГОСТ 18599)',
          [Z_STUB, Z_STUB + 0.01, Z_RUN, Z_RUN, Z_VV, Z_VV], kind='press',
          note='ввод В1 от выпуска ВК217 до наружной грани фундамента 1.6')
v1.valve = (X_W, -1.20)                        # кран шаровой подземный с штоком и ковером
v1.heat = (XR - 1.0, 20.60)                    # греющий кабель: подъём, горизонтальный участок и 1 м до подъёма
# КХ-8 — подводка полива и беседки (ВК: PE-Xa 25 до наружной грани), сезонная
Z_KX8 = round(H0 - 0.95, 3)
KP1 = Well('КП-1', 'В1', 'КП', 23.10, 9.62, 400,
           note='колодец полива: кран Ду20, спускной кран; далее — автополив и беседка по ландшафтному проекту')
kx8 = Pipe('КХ-8н', 'В1', [(20.60, 9.62), (KP1.x, KP1.y)], 25, 0.025, 'ПЭ 100 SDR11 25×2,3 (ГОСТ 18599)',
           [Z_KX8, round(Z_KX8 - 0.01 * (KP1.x - 20.60), 3)], kind='press',
           note='подводка полива КХ-8 (сезонная, с уклоном 0,01 к спускному крану в КП-1)')
KP1.bottom = round(kx8.z[-1] - 0.25, 2)


# ====================================================================================== проверки
def frost_check(p):
    """Утепление самотёчных и напорных труб, где заглубление меньше нормы (по проектной поверхности)."""
    out, step = [], 0.25
    L = p.length()
    s = 0.0
    bad = []
    while s <= L + 1e-6:
        x, y, z = p.at(min(s, L))
        g = g_design(x, y)
        if p.sys == 'В1':
            need = (g - p.bottom(min(s, L))) >= FROST + 0.5 if p.id == 'В1-н' else True
        elif p.sys == 'Др':
            need = True                         # дренаж — под утеплённой отмосткой зданий (КР/АР)
        else:
            need = (g - p.bottom(min(s, L))) >= FROST - 0.3 and (g - p.top(min(s, L))) >= 0.7
        bad.append(not need)
        s += step
    run = None
    for k, b in enumerate(bad):
        s = k * step
        if b and run is None:
            run = s
        if not b and run is not None:
            out.append((round(run, 2), round(s, 2)))
            run = None
    if run is not None:
        out.append((round(run, 2), round(L, 2)))
    p.ins = out
    return out


def seg_x(a, b, c, d):
    """Точка пересечения отрезков в плане: (t на ab, u на cd) или None."""
    r = (b[0] - a[0], b[1] - a[1])
    q = (d[0] - c[0], d[1] - c[1])
    den = r[0] * q[1] - r[1] * q[0]
    if abs(den) < 1e-9:
        return None
    t = ((c[0] - a[0]) * q[1] - (c[1] - a[1]) * q[0]) / den
    u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den
    if 0 < t < 1 and 0 < u < 1:
        return t, u
    return None


def crossings():
    """Пересечения труб разных систем в плане: зазор по вертикали (м)."""
    res = []
    for i, p in enumerate(PIPES):
        for q in PIPES[i + 1:]:
            if p.trench and p.trench == q.trench:
                continue
            for s0, s1, a, b, *_ in p.segs():
                for u0, u1, c, d, *_ in q.segs():
                    x = seg_x(a, b, c, d)
                    if not x:
                        continue
                    sp = s0 + (s1 - s0) * x[0]
                    sq = u0 + (u1 - u0) * x[1]
                    hi, lo = (p, q) if p.bottom(sp) > q.bottom(sq) else (q, p)
                    s_hi, s_lo = (sp, sq) if hi is p else (sq, sp)
                    gap = hi.bottom(s_hi) - lo.top(s_lo)
                    xy = (a[0] + (b[0] - a[0]) * x[0], a[1] + (b[1] - a[1]) * x[0])
                    res.append(dict(up=hi.id, down=lo.id, xy=(round(xy[0], 2), round(xy[1], 2)),
                                    gap=round(gap, 3), z_up=round(hi.bottom(s_hi), 3), z_dn=round(lo.top(s_lo), 3)))
    return res


def report():
    for p in PIPES:
        frost_check(p)
    print(f'±0,000 дома {H0}, бани {H0B}')
    print('Колодцы:')
    for w in WELLS:
        ins = ', '.join(f'{pp.id} {z:.3f}' for pp, z in w.ins)
        outs = ', '.join(f'{pp.id} {z:.3f}' for pp, z in w.outs)
        print(f'  {w.id:8s} ({w.x:6.2f};{w.y:6.2f}) крышка {w.cover} | вх: {ins} | вых: {outs} | дно {w.bottom}')
    print('Трубы:')
    for p in PIPES:
        g0, g1 = g_design(*p.pts[0]), g_design(*p.pts[-1])
        print(f'  {p.id:7s} {p.sys:3s} L={p.length():5.2f} i={p.i} z {p.z[0]:.3f}→{p.z[-1]:.3f} '
              f'глуб.(лоток/ось) {g0 - p.z[0]:.2f}→{g1 - p.z[-1]:.2f} утепл. {p.ins}')
    print('Пересечения:')
    for c in crossings():
        flag = '' if c['gap'] >= 0.1 else '  <-- МАЛО'
        print(f"  {c['up']} над {c['down']} в {c['xy']}: зазор {c['gap']}{flag}")
    dk_in = [(pp.id, z) for pp, z in DK.ins]
    print('ДК5-018: входы', dk_in, 'лоток', DK.bottom, 'перепады', [round(z - DK.bottom, 2) for _, z in dk_in])
    print('Др-2: дом', dA1.z[-1], 'транзит бани', dT.z[-1], '| Н2: дом', round(sA.at(math.dist(S['Н1'], S['Н2']))[2], 3),
          'транзит', sT.z[-1])


def export():
    os.makedirs(OUT, exist_ok=True)
    for p in PIPES:
        frost_check(p)
    data = dict(
        h0=H0, h0b=H0B, assume=ASSUME,
        wells=[dict(id=w.id, sys=w.sys, kind=w.kind, x=w.x, y=w.y, dn=w.dn, cover=w.cover, bottom=w.bottom,
                    exist=w.exist, note=w.note, ins=[(p.id, z) for p, z in w.ins], outs=[(p.id, z) for p, z in w.outs])
               for w in WELLS],
        pipes=[dict(id=p.id, sys=p.sys, pts=p.pts, dn=p.dn, od=p.od, mat=p.mat, z=p.z, i=p.i, kind=p.kind,
                    L=round(p.length(), 2), ins=p.ins, note=p.note, trench=p.trench) for p in PIPES],
        crossings=crossings(),
    )
    with open(os.path.join(OUT, 'nvk.json'), 'w') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    return data


if __name__ == '__main__':
    report()
    export()
