"""И05.09.26-ОВ, лист 8. Топочная. Принципиальная тепловая схема (+ библиотека условных знаков арматуры
для схем листов 6 и 8 — рисование на листе в мм).

python3 sheets/ov_boiler_scheme.py  ->  out/ov_boiler_scheme.dxf + out/ov_boiler_scheme_Лист.pdf
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from rdbase import (new_doc, DPlan, RDSheet, save_and_pdf, fmt_num, SHEET_LIST, SHEETS_TOTAL)  # noqa: E402

OUT = os.path.join(ROOT, 'out')
os.makedirs(OUT, exist_ok=True)
RD = json.load(open(os.path.join(ROOT, '..', 'rd', 'rd_calc.json')))
CALC = json.load(open(os.path.join(ROOT, '..', 'ovk', 'calc.json')))
CIRC = {c['name']: c for c in RD['circuits']}
SHEET_NO = 8

EXTRA_LAYERS = (('ОВ_Г', 42, 35), ('ОВ_В1', 4, 35), ('ОВ_дымоход', 8, 35), ('ОВ_автоматика', 8, 18),
                ('ОВ_арматура', 7, 25))


def fnum(v, d=1):
    return fmt_num(v, d)


# =============================================================== рисование на листе (мм)
class PDPlan(DPlan):
    """Рисование на листе: координаты и размеры в мм (k=1: H(h)=h), штрих — в масштабе листа."""

    def __init__(self, doc, lay):
        super().__init__(doc, k=1, space=lay, unit=1.0)

    def _attrs(self, layer, color=None, lw=None, ltype=None, ltscale=None):
        a = super()._attrs(layer, color, lw, None)
        if ltype:
            a['linetype'] = ltype
            a['ltscale'] = ltscale or 0.01
        return a


PIPE = {  # система: (слой, вес, тип линии)
    'Т1': ('ОВ_Т1', 50, None), 'Т2': ('ОВ_Т2', 50, 'ОВ_ШТРИХ'),
    'Т11': ('ОВ_Т11', 50, None), 'Т21': ('ОВ_Т21', 50, 'ОВ_ШТРИХ'),
    'Т3': ('ОВ_Т3', 35, None), 'Т4': ('ОВ_Т4', 35, 'ОВ_ШТРИХ'),
    'В1': ('ОВ_В1', 35, None), 'Г': ('ОВ_Г', 35, 'ОВ_ШП'), 'Д': ('ОВ_дымоход', 35, 'ОВ_ШТРИХ'),
    'А': ('ОВ_автоматика', 18, 'ОВ_ПУНКТ'),
}


class Sym:
    """Условные знаки ГОСТ 21.205/21.206 (упрощённо, размеры в мм листа)."""

    def __init__(self, p):
        self.p = p

    # --- трубопроводы
    def pipe(self, pts, sys='Т1'):
        lay, lw, lt = PIPE[sys]
        self.p.pl(pts, lay, lw=lw, ltype=lt)

    def dot(self, x, y, r=0.55):
        self.p.circle(x, y, r, 'ОВ_арматура', fill=7)

    def arrow(self, x, y, d, lay='ОВ_арматура', s=2.2):
        """Стрелка направления потока с остриём в (x, y), d — 'u','d','l','r'."""
        dx, dy = dict(u=(0, 1), d=(0, -1), l=(-1, 0), r=(1, 0))[d]
        bx, by = x - dx * s, y - dy * s
        px, py = -dy * s * 0.35, dx * s * 0.35
        self.p.poly([(x, y), (bx + px, by + py), (bx - px, by - py)], lay, fill=7, outline=True)

    # --- арматура: (x, y) — центр, v=True — на вертикальной трубе
    def _bow(self, x, y, v, s=1.5, w=1.1, fill_one=None):
        if v:
            t1 = [(x, y), (x - w, y + s), (x + w, y + s)]
            t2 = [(x, y), (x - w, y - s), (x + w, y - s)]
        else:
            t1 = [(x, y), (x - s, y + w), (x - s, y - w)]
            t2 = [(x, y), (x + s, y + w), (x + s, y - w)]
        self.p.poly(t1, 'ОВ_арматура', fill=7 if fill_one == 1 else None)
        self.p.poly(t2, 'ОВ_арматура', fill=7 if fill_one == 2 else None)

    def ball(self, x, y, v=True):
        self._bow(x, y, v)
        self.p.circle(x, y, 0.5, 'ОВ_арматура', fill=7)

    def gate(self, x, y, v=True):
        self._bow(x, y, v)

    def check(self, x, y, v=True, flow='u'):
        """Обратный клапан: залит треугольник по ходу потока."""
        first = 1 if flow in ('u', 'l') else 2
        if not v:
            first = 2 if flow == 'r' else 1
        else:
            first = 1 if flow == 'u' else 2
        self._bow(x, y, v, fill_one=first)

    def balance(self, x, y, v=True):
        self._bow(x, y, v)
        if v:
            self.p.line(x - 2.0, y - 1.6, x + 2.0, y + 1.6, 'ОВ_арматура')
            self.arrow(x + 2.0, y + 1.6, 'u', s=0.9)
        else:
            self.p.line(x - 1.6, y - 2.0, x + 1.6, y + 2.0, 'ОВ_арматура')
            self.arrow(x + 1.6, y + 2.0, 'u', s=0.9)

    def motor(self, x, y, v=True, txt='М'):
        """Клапан с электроприводом."""
        self._bow(x, y, v)
        if v:
            self.p.line(x, y, x + 2.4, y, 'ОВ_арматура')
            self.p.rect(x + 2.4, y - 1.0, x + 4.4, y + 1.0, 'ОВ_арматура')
            self.p.t(x + 3.4, y, txt, 1.4, 'center', 'ОВ_арматура')
        else:
            self.p.line(x, y, x, y + 2.4, 'ОВ_арматура')
            self.p.rect(x - 1.0, y + 2.4, x + 1.0, y + 4.4, 'ОВ_арматура')
            self.p.t(x, y + 3.4, txt, 1.4, 'center', 'ОВ_арматура')

    def three_way(self, x, y, v=True, side='r', act=True, txt='М'):
        """Трёхходовой клапан: проход по трубе и третий патрубок в сторону side; привод — с другой стороны."""
        self._bow(x, y, v)
        s, w = 1.5, 1.1
        dx, dy = dict(r=(1, 0), l=(-1, 0), u=(0, 1), d=(0, -1))[side]
        if dx:
            tri = [(x, y), (x + dx * s, y + w), (x + dx * s, y - w)]
        else:
            tri = [(x, y), (x + w, y + dy * s), (x - w, y + dy * s)]
        self.p.poly(tri, 'ОВ_арматура')
        if act:
            ax, ay = -dx, -dy
            if ax == 0 and ay == 0:
                ax = 1
            ex, ey = x + ax * 2.4, y + ay * 2.4
            self.p.line(x, y, ex, ey, 'ОВ_арматура')
            cx, cy = x + ax * 3.4, y + ay * 3.4
            self.p.rect(cx - 1.0, cy - 1.0, cx + 1.0, cy + 1.0, 'ОВ_арматура')
            self.p.t(cx, cy, txt, 1.4, 'center', 'ОВ_арматура')

    def pump(self, x, y, flow='u', r=1.9):
        self.p.circle(x, y, r, 'ОВ_арматура')
        dx, dy = dict(u=(0, 1), d=(0, -1), l=(-1, 0), r=(1, 0))[flow]
        tip = (x + dx * r, y + dy * r)
        b1 = (x - dx * r * 0.5 + dy * r * 0.85, y - dy * r * 0.5 + dx * r * 0.85)
        b2 = (x - dx * r * 0.5 - dy * r * 0.85, y - dy * r * 0.5 - dx * r * 0.85)
        self.p.pl([b1, tip, b2], 'ОВ_арматура')

    def filt(self, x, y, v=True):
        """Фильтр сетчатый."""
        if v:
            self.p.rect(x - 1.1, y - 1.6, x + 1.1, y + 1.6, 'ОВ_арматура')
            self.p.line(x - 1.1, y - 1.6, x + 1.1, y + 1.6, 'ОВ_арматура')
        else:
            self.p.rect(x - 1.6, y - 1.1, x + 1.6, y + 1.1, 'ОВ_арматура')
            self.p.line(x - 1.6, y - 1.1, x + 1.6, y + 1.1, 'ОВ_арматура')

    def therm(self, x, y, side='r'):
        """Термометр на трубе."""
        dx = 1 if side == 'r' else -1
        self.p.line(x, y, x + dx * 1.6, y, 'ОВ_арматура')
        self.p.rect(min(x + dx * 1.6, x + dx * 2.4), y - 0.5, max(x + dx * 1.6, x + dx * 2.4) + 0.0, y + 0.5,
                    'ОВ_арматура')

    def mano(self, x, y, side='r'):
        dx = 1 if side == 'r' else -1
        self.p.line(x, y, x + dx * 1.8, y, 'ОВ_арматура')
        self.p.circle(x + dx * 2.8, y, 1.0, 'ОВ_арматура')
        self.p.line(x + dx * 2.8, y, x + dx * 3.4, y + 0.6, 'ОВ_арматура')

    def sensor(self, x, y, txt='T', side='r'):
        """Датчик температуры автоматики."""
        dx = 1 if side == 'r' else -1
        self.p.line(x, y, x + dx * 1.6, y, 'ОВ_автоматика')
        self.p.circle(x + dx * 2.8, y, 1.2, 'ОВ_автоматика')
        self.p.t(x + dx * 2.8, y, txt, 1.3, 'center', 'ОВ_автоматика')

    def airvent(self, x, y):
        """Воздухоотводчик автоматический (сверху трубы)."""
        self.p.line(x, y, x, y + 1.6, 'ОВ_арматура')
        self.p.rect(x - 0.9, y + 1.6, x + 0.9, y + 3.0, 'ОВ_арматура')
        self.p.line(x - 0.9, y + 3.0, x, y + 3.8, 'ОВ_арматура')
        self.p.line(x + 0.9, y + 3.0, x, y + 3.8, 'ОВ_арматура')

    def drain(self, x, y, v=True):
        """Спускной кран (снизу трубы)."""
        if v:
            self.p.line(x, y, x, y - 1.4, 'ОВ_арматура')
            self.ball(x, y - 2.6, True)
            self.p.line(x, y - 4.1, x, y - 5.0, 'ОВ_арматура')
        else:
            self.p.line(x, y, x + 1.4, y, 'ОВ_арматура')
            self.ball(x + 2.6, y, False)

    def safety(self, x, y, side='r', txt='3 бар'):
        """Предохранительный клапан (угловой) с выпуском."""
        dx = 1 if side == 'r' else -1
        self.p.line(x, y, x + dx * 1.6, y, 'ОВ_арматура')
        cx, cy = x + dx * 3.0, y
        self.p.poly([(cx, cy), (cx - dx * 1.4, cy + 1.0), (cx - dx * 1.4, cy - 1.0)], 'ОВ_арматура')
        self.p.poly([(cx, cy), (cx - 1.0, cy - 1.4), (cx + 1.0, cy - 1.4)], 'ОВ_арматура')
        self.p.pl([(cx, cy), (cx + dx * 0.5, cy + 0.6), (cx - dx * 0.0, cy + 1.2), (cx + dx * 0.5, cy + 1.8),
                   (cx, cy + 2.4)], 'ОВ_арматура')
        self.p.line(cx, cy - 1.4, cx, cy - 3.0, 'ОВ_арматура')
        if txt:
            self.p.t(cx + dx * 1.2, cy + 1.0, txt, 1.4, 'left' if dx > 0 else 'right', 'ОВ_арматура')

    def reducer(self, x, y, v=False):
        """Редуктор давления."""
        if v:
            self.p.poly([(x - 1.2, y - 1.6), (x + 1.2, y - 1.6), (x + 0.6, y + 1.6), (x - 0.6, y + 1.6)],
                        'ОВ_арматура')
        else:
            self.p.poly([(x - 1.6, y - 1.2), (x - 1.6, y + 1.2), (x + 1.6, y + 0.6), (x + 1.6, y - 0.6)],
                        'ОВ_арматура')

    def flowmeter(self, x, y, v=True):
        if v:
            self.p.rect(x - 1.0, y - 1.5, x + 1.0, y + 1.5, 'ОВ_арматура')
        else:
            self.p.rect(x - 1.5, y - 1.0, x + 1.5, y + 1.0, 'ОВ_арматура')
        self.p.t(x, y, 'Р', 1.2, 'center', 'ОВ_арматура')

    def tank(self, x, y, w, h, txt, sub=None):
        """Расширительный бак: прямоугольник со скруглёнными торцами (упрощённо — с диафрагмой)."""
        self.p.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, 'ОВ_оборуд')
        self.p.line(x - w / 2, y, x + w / 2, y, 'ОВ_арматура', ltype='ОВ_ПУНКТ')
        self.p.t(x, y + h / 4, txt, 1.8, 'center', 'ОВ_марки')
        if sub:
            self.p.t(x, y - h / 4, sub, 1.5, 'center', 'ОВ_марки')

    def box(self, x0, y0, x1, y1, lines, h=2.0, layer='ОВ_оборуд'):
        self.p.rect(x0, y0, x1, y1, layer)
        n = len(lines)
        for i, t in enumerate(lines):
            self.p.t((x0 + x1) / 2, (y0 + y1) / 2 + ((n - 1) / 2 - i) * h * 1.45, t, h if i == 0 else h * 0.85,
                     'center', 'ОВ_марки')

    def text(self, x, y, s, h=1.8, align='left', layer='ОВ_текст', rot=0):
        self.p.t(x, y, s, h, align, layer, rot=rot)

    def pos(self, x, y, n, r=2.0):
        """Номер позиции в кружке."""
        self.p.circle(x, y, r, 'ОВ_марки')
        self.p.t(x, y, str(n), 1.8, 'center', 'ОВ_марки')


# =============================================================== гидравлика групп РК (детерминированно)
CWJ = 4187.0
K_PEX = 0.007e-3
DI = {'16×2,0': 12.0, '20×2,8': 14.4, '25×3,5': 18.0, '32×4,4': 23.2, '40×5,5': 29.0}


def water(t):
    tab = [(10, 999.7, 1.306e-6), (20, 998.2, 1.004e-6), (30, 995.7, 0.801e-6), (40, 992.2, 0.658e-6),
           (50, 988.0, 0.553e-6), (60, 983.2, 0.474e-6), (70, 977.8, 0.413e-6), (80, 971.8, 0.365e-6)]
    for (t0, r0, n0), (t1, r1_, n1) in zip(tab, tab[1:]):
        if t0 <= t <= t1:
            k = (t - t0) / (t1 - t0)
            return r0 + k * (r1_ - r0), n0 + k * (n1 - n0)
    return tab[-1][1], tab[-1][2]


def pipe_dp(G_kgh, d_mm, L, t, zeta=0.0, k=K_PEX):
    """Потери в трубе, Па (Колбрук — Уайт; та же методика, что в rd/calc_rd.py)."""
    rho, nu = water(t)
    d = d_mm / 1000
    v = G_kgh / 3600 / rho / (math.pi * d * d / 4)
    re = v * d / nu
    if re < 2300:
        lam = 64 / max(re, 1e-9)
    else:
        lam = 0.02
        for _ in range(40):
            lam = (-2 * math.log10(k / (3.7 * d) + 2.51 / (re * math.sqrt(lam)))) ** -2
    dyn = rho * v * v / 2
    return dict(v=v, dp=lam / d * dyn * L + zeta * dyn)


def kgh(Q, dt):
    return Q / (CWJ * dt) * 3600


# условные характеристики классов насосов (H0 — напор при нулевой подаче, Gmax — подача при нулевом напоре):
# H(G) = H0·(1 − (G/Gmax)²); класс выбирается наименьший с запасом 10 % по напору (уточнить по каталогу)
PUMP_CLASSES = [('25-40', 4.0, 3.0), ('25-60', 6.0, 3.5), ('25-80', 8.0, 4.0)]


def pump_for(m3h, H_m):
    for nm, H0, Gm in PUMP_CLASSES:
        if H0 * (1 - (m3h / Gm) ** 2) >= 1.1 * H_m:
            return nm
    return '32-100'


def groups_calc():
    """Группы РК после пересчёта листов 3–4 (СП 60): данные — calc1() из ov_heat1.py (только чтение)."""
    import ov_heat1 as H1
    C1 = H1.calc1()
    cabs, dev, mains = C1['cabs'], C1['dev'], {m['name']: m for m in C1['mains']}
    loops = C1['loops']
    c4 = CIRC['Радиаторы и Кн 2 эт. → КШ-4 (70/55)']
    out = {}
    # Н2 → КШ-4 по листу 5 (ov_heat2: ТП 2.8, 2.9 по СП 60 — подача 42 °С, Пс-1, Пс-2 увеличены);
    # выход В6 (Кн-2) — резерв, его нагрузка перенесена в Кв-8 (1.9) — решение Заказчика
    import ov_heat2 as H2
    Qd4 = sum(H2.DEV[n]['Q'] for n in K4_DIRECT)
    Qu4 = sum(H2.UFH[no]['Q_ufh'] for no in ('2.8', '2.9'))
    Qdn4 = sum(H2.UFH0[no]['q_down'] * H2.UFH[no]['q'] / H2.UFH0[no]['q'] * H2.UFH[no]['A_loops']
               for no in ('2.8', '2.9'))                       # теплопоток вниз (в перекрытие) — нагрузка узла
    Q2 = Qd4 + Qu4 + Qdn4
    G2 = kgh(Q2, 15)
    h = pipe_dp(G2, DI['25×3,5'], 2 * c4['L'], 62.5, zeta=6.0)
    H2_ = h['dp'] / 1000 + c4['extra']
    out['Н2'] = dict(dest='КШ-4 (2 эт.)', Q=Q2, G=G2, pipe='25×3,5', L=c4['L'], H_kPa=H2_, t='70/55',
                     G_hs=G2, Q_direct=Qd4, Q_ufh=Qu4 + Qdn4)
    # Н3 → КШ-2 (Кв-1…8 + смесит. узел ТП 36 °С) + Р-т тройником на РК
    m2 = mains['КШ-2 (Кв + смес. узел ТП)']
    rt = C1['rt']
    G3 = m2['G'] + rt['G']
    Q3 = m2['Q'] + rt['Q']
    h = pipe_dp(m2['G'], DI['32×4,4'], 2 * m2['L'], 62.5, zeta=6.0)
    lead = max(pipe_dp(d['G'], DI['16×2,0'], 2 * d['lead'], 62.5, zeta=4.0)['dp'] / 1000 for d in dev.values())
    H3 = h['dp'] / 1000 + lead + 2.0 + 3.0
    out['Н3'] = dict(dest='КШ-2, Р-т', Q=Q3, G=G3, pipe='32×4,4', L=m2['L'], H_kPa=H3, t='70/55', G_hs=G3,
                     G_ksh2=m2['G'], Q_ksh2=m2['Q'], v=m2['v'])
    # Н4 → ТП 48,5 °С: КШ-1 и КШ-3 (смешение на РК)
    br = []
    for nm, cab in (('КШ-1 (ТП)', 'КШ-1'), ('КШ-3 (ТП)', 'КШ-3')):
        m = mains[nm]
        hh = pipe_dp(m['G'], DI[m['pipe']], 2 * m['L'], 44.0, zeta=6.0)
        br.append(dict(cab=cab, G=m['G'], Q=m['Q'], pipe=m['pipe'], L=m['L'], v=m['v'],
                       H_kPa=hh['dp'] / 1000 + cabs[cab]['dp_max'] + 2.0, t_ret=cabs[cab]['t_ret']))
    G4 = sum(b['G'] for b in br)
    Q4 = sum(b['Q'] for b in br)
    tr4 = sum(b['G'] * b['t_ret'] for b in br) / G4
    H4 = max(b['H_kPa'] for b in br) + 4.0
    out['Н4'] = dict(dest='ТП: КШ-1, КШ-3', Q=Q4, G=G4, pipe='20×2,8 / 32×4,4', L=max(b['L'] for b in br),
                     H_kPa=H4, t='48,5/' + fnum(tr4, 0), G_hs=kgh(Q4, 70 - tr4), branches=br, t_ret=tr4)
    # Н5, Н7 — без изменений (rd_calc.json)
    for n, key, dest, t in (('Н5', 'Калорифер П1 (70/50, смесительный узел)', 'калорифер П1', '70/50'),
                            ('Н7', 'Загрузка Б1 (80/60, приоритет)', 'Б1 (приоритет)', '80/60')):
        c = CIRC[key]
        out[n] = dict(dest=dest, Q=c['Q'], G=c['G'], pipe=c['pipe'].replace('PE-Xa ', '').replace(' (Ecoflex)', ''),
                      L=c['L'], H_kPa=c['H_kPa'], t=t, G_hs=c['G'] if n != 'Н5' else kgh(c['Q'], 20))
    # Н6 → баня: нагрузка — из расчёта бани (лист 12, ov_bath_calc.json): отопление + ТО-Д джакузи (Б2 — с
    # приоритетом, одновременно не работает); потери в Ecoflex — пересчёт расчёта rd по расходу (Δp ~ G^1,75),
    # шкафы и ввод — как в rd_calc (extra)
    c = CIRC['Баня → КШ-Б (Ecoflex Quattro 32×2,9)']
    Q6 = BATH['Q_heat'] + BATH['tod']['Q']
    G6 = kgh(Q6, 15)
    H6 = c['dp_pipe'] * (G6 / c['G']) ** 1.75 + c['extra']
    out['Н6'] = dict(dest='баня: КШ-Б1, КШ-Б2', Q=Q6, G=G6, pipe='32×2,9', L=c['L'], H_kPa=H6, t='70/55', G_hs=G6)
    out['Н6']['short'] = 'баня'                     # подпись над группой; шкафы — в экспликации
    for n, g in out.items():
        g['m3h'] = g['G'] / 1000
        g['H_m'] = g['H_kPa'] / 9.81
        g['pump'] = pump_for(g['m3h'], g['H_m'])
    # смесительные узлы шкафов: КШ-2 — calc1 (лист 4), КШ-4 — лист 5 (ov_heat2), КШ-Б2 — лист 12 (ov_bath_calc.json)
    k2 = cabs['КШ-2']
    Hm2 = k2['dp_max'] + 5.0
    u4 = [H2.UFH[no] for no in ('2.8', '2.9')]
    dp4 = max(u['dp_loop'] + H2.UFH0[u['no']]['dp_valve'] * (u['G_loop'] / H2.UFH0[u['no']]['G_loop']) ** 2 for u in u4)
    mix = {'КШ-2': dict(t=36.0, G=k2['G_tp'], H_kPa=Hm2, Q=k2['Q_tp']),
           'КШ-4': dict(t=H2.TV4, G=sum(u['G_loop'] for u in u4), H_kPa=dp4 + 3.0 + 2.0, Q=Qu4),
           'КШ-Б2': dict(t=BATH['tv'], G=BATH['mixpump']['G'], H_kPa=BATH['mixpump']['H_kPa'], Q=BATH['Q_ufh'])}
    for m in mix.values():
        m['m3h'] = m['G'] / 1000
        m['H_m'] = m['H_kPa'] / 9.81
        m['pump'] = pump_for(m['m3h'], m['H_m'])
    # гидрострелка: отбор групп одновременно (без Б1 — приоритет), с джакузи и без
    G_hs = sum(out[n]['G_hs'] for n in ('Н2', 'Н3', 'Н4', 'Н5', 'Н6'))
    G_bath_heat = kgh(BATH['Q_heat'], 15)
    G_hs_nojac = G_hs - out['Н6']['G'] + G_bath_heat
    return dict(groups=out, mix=mix, C1=C1, G_hs=G_hs, G_hs_nojac=G_hs_nojac,
                hs_m3h=math.ceil(G_hs / 100) / 10)


RD_DEV = {d['name']: d for d in RD['devices']}
K4_DIRECT = ['Р-1', 'Р-2', 'Р-3', 'Р-5', 'Кн-1', 'Кн-3', 'Пс-1', 'Пс-2']     # В6 (Кн-2) — резерв
BATH = json.load(open(os.path.join(ROOT, 'out', 'ov_bath_calc.json')))      # лист 12 (ov_bath.py)
def _site_L():
    import ov_site
    return ov_site.L_TOT                               # длина Ecoflex по трассе с подъёмами (лист 14)


SITE_L = _site_L()


def no_yo(doc):
    """В ISOCPEUR нет буквы «ё» — заменяем на «е» во всех текстах файла."""
    spaces = [doc.modelspace()] + [l for l in doc.layouts if l.name != 'Model'] + list(doc.blocks)
    for sp in spaces:
        for e in sp:
            if e.dxftype() == 'TEXT':
                e.dxf.text = e.dxf.text.replace('ё', 'е').replace('Ё', 'Е').replace('…', '...')
            elif e.dxftype() == 'MTEXT':
                e.text = e.text.replace('ё', 'е').replace('Ё', 'Е').replace('…', '...')


def prep_doc():
    doc = new_doc()
    for n, c, lw in EXTRA_LAYERS:
        if n not in doc.layers:
            doc.layers.add(n, color=c, lineweight=lw)
    return doc


def legend(S, x, y, w=100, h=1.8):
    """Условные обозначения арматуры; возвращает y низа."""
    p = S.p
    S.text(x + w / 2, y, 'Условные обозначения', 2.5, 'center')
    items = [
        (lambda a, b: S.pipe([(a - 4, b), (a + 4, b)], 'Т1'), 'Т1 — подающий трубопровод отопления'),
        (lambda a, b: S.pipe([(a - 4, b), (a + 4, b)], 'Т2'), 'Т2 — обратный трубопровод отопления'),
        (lambda a, b: S.pipe([(a - 4, b), (a + 4, b)], 'Т11'), 'Т11, Т21 — подающий/обратный тёплого пола'),
        (lambda a, b: S.pipe([(a - 4, b), (a + 4, b)], 'Т3'), 'Т3, Т4 — ГВС и циркуляция (раздел ВК)'),
        (lambda a, b: S.pipe([(a - 4, b), (a + 4, b)], 'В1'), 'В1 — холодная вода (подпитка)'),
        (lambda a, b: S.pipe([(a - 4, b), (a + 4, b)], 'Г'), 'Г — газопровод (проект ГСВ)'),
        (lambda a, b: S.ball(a, b, False), 'Кран шаровой'),
        (lambda a, b: S.check(a, b, False, 'r'), 'Клапан обратный'),
        (lambda a, b: S.balance(a, b, False), 'Клапан балансировочный'),
        (lambda a, b: S.three_way(a, b, False, 'd'), 'Клапан трёхходовой с электроприводом'),
        (lambda a, b: S.pump(a, b, 'r'), 'Насос циркуляционный'),
        (lambda a, b: S.filt(a, b, False), 'Фильтр сетчатый'),
        (lambda a, b: S.reducer(a, b, False), 'Редуктор давления'),
        (lambda a, b: S.safety(a - 2, b, 'r', ''), 'Клапан предохранительный'),
        (lambda a, b: S.airvent(a, b - 1.5), 'Воздухоотводчик автоматический'),
        (lambda a, b: S.therm(a - 1, b), 'Термометр'),
        (lambda a, b: S.mano(a - 1.5, b), 'Манометр'),
        (lambda a, b: S.sensor(a - 2, b), 'Датчик температуры автоматики'),
        (lambda a, b: S.flowmeter(a, b, False), 'Расходомер с настройкой (на коллекторе)'),
    ]
    yy = y - 5.5
    for fn, cap in items:
        fn(x + 6, yy)
        S.text(x + 14, yy, cap, h, 'left')
        yy -= 4.6
    return yy


# =============================================================== лист 8
def legend3(S, x, y, cols=3, colw=68, h=1.6, rowh=4.4):
    """Условные обозначения в несколько колонок; (x, y) — левый верх."""
    items = [
        (lambda a, b: S.pipe([(a - 4, b), (a + 4, b)], 'Т1'), 'Т1 — подающий отопления'),
        (lambda a, b: S.pipe([(a - 4, b), (a + 4, b)], 'Т2'), 'Т2 — обратный отопления'),
        (lambda a, b: S.pipe([(a - 4, b), (a + 4, b)], 'Т11'), 'Т11, Т21 — тёплый пол'),
        (lambda a, b: S.pipe([(a - 4, b), (a + 4, b)], 'Т3'), 'Т3, Т4 — ГВС, циркуляция (ВК)'),
        (lambda a, b: S.pipe([(a - 4, b), (a + 4, b)], 'В1'), 'В1 — холодная вода'),
        (lambda a, b: S.pipe([(a - 4, b), (a + 4, b)], 'Г'), 'Г — газопровод (ГСВ)'),
        (lambda a, b: S.ball(a, b, False), 'Кран шаровой'),
        (lambda a, b: S.check(a, b, False, 'r'), 'Клапан обратный'),
        (lambda a, b: S.balance(a, b, False), 'Клапан балансировочный'),
        (lambda a, b: S.three_way(a, b, False, 'd', act=False), 'Клапан 3-ходовой (с приводом — «М»)'),
        (lambda a, b: S.pump(a, b, 'r'), 'Насос циркуляционный'),
        (lambda a, b: S.filt(a, b, False), 'Фильтр, шламоотделитель'),
        (lambda a, b: S.reducer(a, b, False), 'Редуктор давления'),
        (lambda a, b: S.safety(a - 2, b, 'r', ''), 'Клапан предохранительный'),
        (lambda a, b: S.airvent(a, b - 1.5), 'Воздухоотводчик автоматический'),
        (lambda a, b: S.therm(a - 1, b), 'Термометр'),
        (lambda a, b: S.mano(a - 1.5, b), 'Манометр'),
        (lambda a, b: S.sensor(a - 2, b), 'Датчик температуры (автоматика)'),
        (lambda a, b: S.flowmeter(a, b, False), 'Расходомер с настройкой'),
        (lambda a, b: S.pos(a, b, 1), 'Номер позиции (экспликация)'),
    ]
    S.text(x + cols * colw / 2, y, 'Условные обозначения', 2.5, 'center')
    per = math.ceil(len(items) / cols)
    for i, (fn, cap) in enumerate(items):
        c, r = divmod(i, per)
        xx, yy = x + c * colw, y - 5.5 - r * rowh
        fn(xx + 6, yy)
        S.text(xx + 13, yy, cap, h, 'left')
    return y - 5.5 - per * rowh


def build():
    doc = prep_doc()
    sh = RDSheet(doc, 'Лист', SHEET_LIST[SHEET_NO], SHEET_NO, SHEETS_TOTAL)
    p = PDPlan(doc, sh.lay)
    S = Sym(p)
    sh.title(160, 288.5, 'Топочная. Принципиальная тепловая схема')

    GC = groups_calc()
    GR = GC['groups']
    c_b1 = CIRC['Загрузка Б1 (80/60, приоритет)']
    hs = RD['hydraulic_separator']
    ex = RD['expansion_heat']

    # ---------------------------------------------- котлы
    S.box(30, 236, 58, 266, ['К1', 'Viessmann', 'конденсац.', '≈24–25 кВт'], 2.0)
    S.box(30, 198, 58, 228, ['К2', 'Viessmann', 'конденсац.', '≈24–25 кВт'], 2.0)
    S.box(30, 118, 62, 168, ['ПК', 'пеллетный', '≈50 кВт', 'резерв', 'бункер БП'], 2.0)
    S.pos(27, 268.5, 1)
    S.pos(27, 171, 2)
    for yb in (251, 213):
        S.pump(52, yb, 'u', 1.6)
    S.text(60, 232.3, 'насос, обр. клапан — встроены', 1.4, 'left')
    for xb, yb in ((44, 266), (44, 228)):
        S.pipe([(xb, yb), (xb, yb + 3.0)], 'Д')
        S.arrow(xb, yb + 4.2, 'u', 'ОВ_дымоход', 1.4)
    S.text(47, 272.0, 'каскадный дымоход Ø125 → Ш-2', 1.5)
    S.pipe([(46, 168), (46, 171.5)], 'Д')
    S.arrow(46, 172.8, 'u', 'ОВ_дымоход', 1.4)
    S.text(49, 172.0, 'Ø180 → Ш-2', 1.5)
    for yb in (240, 202):
        S.pipe([(23, yb), (30, yb)], 'Г')
        S.ball(26.5, yb, False)
        S.text(23, yb + 2.8, 'Г', 1.6, 'left')

    # ---------------------------------------------- коллекторы котлов: обратка XR, подача XS
    XR, XS = 88.0, 96.0
    S.pipe([(58, 258), (XS, 258)], 'Т1')
    S.pipe([(58, 220), (XS, 220)], 'Т1')
    S.pipe([(XR, 244), (58, 244)], 'Т2')
    S.pipe([(XR, 206), (58, 206)], 'Т2')
    # ПК: подача — группа безопасности, перемычка подмеса, обратный клапан
    S.pipe([(62, 160), (XS, 160)], 'Т1')
    S.safety(65, 160, 'r', '')
    S.text(68.6, 165.8, 'ГБ', 1.5, 'left')
    S.pos(71, 152.5, 17)
    S.check(86, 160, False, 'r')
    S.dot(77, 160)
    # обратка ПК: КТ (подмес 55 °С) и насос Н1
    S.pipe([(XR, 128), (62, 128)], 'Т2')
    S.three_way(77, 128, False, 'u', act=False)
    S.pipe([(77, 129.5), (77, 160)], 'Т1')
    S.pump(68, 128, 'l', 1.8)
    S.text(77, 123.5, 'КТ 55 °С', 1.5, 'center')
    S.text(68, 123.5, 'Н1', 1.5, 'center')
    S.pos(83, 121.5, 13)
    S.pos(64, 121.5, 5)
    S.sensor(62, 142, 'Tпк', 'r')
    # коллекторы котлов
    S.pipe([(XS, 160), (XS, 262), (106, 262)], 'Т1')
    S.pipe([(XR, 128), (XR, 244)], 'Т2')
    for yy in (258, 220, 160):
        S.dot(XS, yy)
    for yy in (244, 206, 128):
        S.dot(XR, yy)
    S.mano(XR, 150, 'l')
    S.text(83.5, 145.8, '1,5 бар', 1.4, 'right')
    S.pipe([(XR, 128), (XR, 112), (110, 112), (110, 125)], 'Т2')

    # ---------------------------------------------- шламоотделитель, гидрострелка
    S.filt(100, 112, False)
    S.text(100, 108.3, 'ШО', 1.5, 'center')
    S.pos(100, 103.5, 21)
    GX0, GX1, GY0, GY1 = 106.0, 116.0, 125.0, 258.0
    p.rect(GX0, GY0, GX1, GY1, 'ОВ_оборуд')
    S.text(111, 196, 'ГС', 2.2, 'center', rot=90)
    S.text(111, 172, f'Ду32, до {fnum(GC["hs_m3h"], 1)} м³/ч', 1.5, 'center', rot=90)
    S.pos(117.5, 266, 3)
    S.pipe([(106, 262), (110, 262), (110, GY1)], 'Т1')
    S.airvent(113, GY1)
    S.drain(113, GY0)
    S.sensor(GX1, 225, 'Tгс', 'r')
    # расширительный бак и манометр — на общей обратке до ГС
    S.pipe([(94, 112), (94, 94)], 'Т2')
    S.dot(94, 112)
    S.ball(94, 101, True)
    S.tank(94, 86, 12, 14, 'РБ', f'{ex["tank"]} л')
    S.pos(104, 86, 15)
    # узел подпитки от В1
    S.pipe([(23, 100), (84, 100), (84, 112)], 'В1')
    S.dot(84, 112)
    S.ball(30, 100, False)
    S.filt(37, 100, False)
    S.reducer(44, 100, False)
    S.check(51, 100, False, 'r')
    S.ball(58, 100, False)
    S.text(23, 103.2, 'В1 (от ВК) — подпитка', 1.6)
    S.text(44, 95.8, 'УП: 1,5 бар', 1.5, 'center')
    S.pos(66, 100, 19)

    # ---------------------------------------------- РК: двухкамерный коллектор
    RX0, RX1, RY0, RY1 = 130.0, 256.0, 190.0, 210.0
    RM = (RY0 + RY1) / 2
    p.rect(RX0, RY0, RX1, RY1, 'ОВ_оборуд')
    p.line(RX0, RM, RX1, RM, 'ОВ_оборуд')
    S.text(RX0 + 2, RY1 - 3.2, 'Т1', 1.5)
    S.text(RX0 + 2, RY0 + 3.2, 'Т2', 1.5)
    S.text((RX0 + RX1) / 2, RY0 - 3.5, 'РК — коллектор распределительный двухкамерный Ду32', 1.8, 'center')
    S.pos(RX0 - 4, RY1 + 3.5, 4)
    S.pipe([(GX1, 250), (122, 250), (122, (RM + RY1) / 2), (RX0, (RM + RY1) / 2)], 'Т1')
    S.pipe([(RX0, (RY0 + RM) / 2), (125, (RY0 + RM) / 2), (125, 133), (GX1, 133)], 'Т2')
    S.airvent(RX0 + 4, RY1)
    S.drain(RX0 + 4, RY0)

    # ---------------------------------------------- насосные группы
    groups = [(143, 'Н2', 'd', 6), (164, 'Н3', 'd', 7), (185, 'Н4', 'm', 8), (206, 'Н5', 'm', 9), (227, 'Н6', 'd', 10)]
    for x, n, kind, pos in groups:
        g = GR[n]
        dest, pump = g['dest'], g['pump']
        xs, xr = x - 3.0, x + 3.0
        sup_sys, ret_sys = ('Т11', 'Т21') if n == 'Н4' else ('Т1', 'Т2')
        S.pipe([(xs, RY1), (xs, 260)], sup_sys)
        S.pipe([(xr, RY1), (xr, 260)], ret_sys)
        p.line(xr, RM, xr, RY1, 'ОВ_Т2', ltype='ОВ_ПУНКТ')
        S.dot(xr, RM, 0.5)
        S.ball(xs, 215, True)
        S.ball(xr, 215, True)
        if kind == 'm':
            S.three_way(xs, 224, True, 'r', act=True)
            S.pipe([(xs + 1.5, 224), (xr, 224)], ret_sys)
            S.dot(xr, 224)
            S.sensor(xs, 251, 'T', 'l')
        else:
            S.therm(xs, 251, 'l')
        S.pump(xs, 234, 'u')
        S.check(xs, 242, True, 'u')
        S.therm(xr, 251, 'r')
        S.balance(xr, 232, True)
        S.arrow(xs, 262.5, 'u', 'ОВ_арматура', 1.8)
        S.arrow(xr, 260.0, 'd', 'ОВ_арматура', 1.8)
        S.text(x, 275.5, f'{n} → {g.get("short", dest)}', 1.6, 'center')
        S.text(x, 272.0, f'{fnum(g["Q"] / 1000, 1)} кВт, {fnum(g["m3h"], 2)} м³/ч', 1.4, 'center')
        S.text(x, 268.8, f'H={fnum(g["H_m"], 2)} м, насос {pump}', 1.4, 'center')
        S.text(x, 265.6, g['pipe'] if n != 'Н4' else '20×2,8; 32×4,4', 1.4, 'center')
        if n == 'Н3':                                    # Р-т — тройником на группе КШ-2
            S.pipe([(xs, 257.0), (xs + 12.5, 257.0)], 'Т1')
            S.pipe([(xs + 12.5, 254.5), (xr, 254.5)], 'Т2')
            S.dot(xs, 257.0)
            S.dot(xr, 254.5)
            S.text(xs + 13.2, 255.8, 'Р-т', 1.4, 'left')
        S.pos(x, 280.5, pos)

    # ---------------------------------------------- Б1: загрузка от РК (Н7, приоритет)
    xs, xr = 243.0, 249.0
    BX0, BX1, BY0, BY1 = 262.0, 284.0, 128.0, 206.0
    BC = (BX0 + BX1) / 2
    S.pipe([(xs, RY1), (xs, 240), (BC, 240), (BC, 196)], 'Т1')
    S.pipe([(BC, 150), (BC, 140), (xr, 140), (xr, RY0)], 'Т2')
    S.ball(xs, 215, True)
    S.pump(xs, 225, 'u')
    S.check(xs, 233, True, 'u')
    S.ball(xr, 150, True)
    S.balance(xr, 162, True)
    S.text(255, 247.5, f'Н7 → Б1, {fnum(c_b1["Q"] / 1000, 0)} кВт', 1.4, 'center')
    S.text(255, 244.3, f'{fnum(c_b1["m3h"], 2)} м³/ч, насос 25-40', 1.4, 'center')
    S.pos(266, 246, 11)
    p.rect(BX0, BY0, BX1, BY1, 'ОВ_оборуд')
    S.text(BC, 201.5, 'Б1', 2.2, 'center')
    S.text(BX0 + 4.5, 132, '300 л', 1.6, 'center')
    S.pos(BX0 - 4, BY1 + 2.5, 14)
    zz = [(BC, 196)]
    for i in range(9):
        zz.append((BC + (3.5 if i % 2 == 0 else -3.5), 192 - i * 4.6))
    zz.append((BC, 150))
    p.pl(zz, 'ОВ_Т1', lw=25)
    S.sensor(BX1, 168, 'Tгвс', 'r')
    # ГВС / В1 / циркуляция (граница — раздел ВК)
    S.pipe([(280, BY1), (280, 214), (298, 214)], 'Т3')
    S.text(298.5, 214, 'Т3 → ВК', 1.5)
    S.pipe([(298, 184), (BX1, 184)], 'Т4')
    S.pump(292, 184, 'l', 1.6)
    S.text(292, 187.4, 'Н8', 1.4, 'center')
    S.pos(292, 192, 12)
    S.check(288, 184, False, 'l')
    S.text(298.5, 184, 'Т4 ← ВК', 1.5)
    S.pipe([(298, 134), (BX1, 134)], 'В1')
    S.check(292.5, 134, False, 'l')
    S.ball(296, 134, False)
    S.safety(288.5, 134, 'r', '')
    S.text(298.5, 134, 'В1 ← ВК', 1.5)
    S.pipe([(289.5, 134), (289.5, 120)], 'В1')
    S.dot(289.5, 134)
    S.tank(289.5, 113, 7, 10, 'РБ', '18 л')
    S.text(286.5, 127.5, 'ГБ 6 бар', 1.4, 'right')
    S.pos(297.5, 113, 16)
    S.pos(292, 140.5, 18)

    # ---------------------------------------------- ШУ
    S.box(130, 122, 214, 166, ['ШУ — шкаф управления котельной', 'каскадный погодозависимый контроллер:',
                               'К1, К2, ПК (резерв), насосы Н1–Н8,',
                               'клапаны групп Н4, Н5, приоритет Б1, Б2;',
                               'датчики Tн (наружный), Tгс, Tгвс, Tпк,', 'Tтп, Tп1, комнатные;',
                               'удалённый доступ, интеграция', 'в «умный дом»'], 1.8)
    S.pos(217, 164, 20)
    S.text(172, 116, 'связи с оборудованием — по паспорту контроллера / проекту автоматизации', 1.5, 'center')

    # ---------------------------------------------- экспликация и примечания
    rows = [['Поз.', 'Обозн.', 'Наименование', 'Кол.']]
    eq = [
        ('1', 'К1, К2', 'Котёл газовый конденсационный настенный одноконтурный Viessmann (серия с каскадным управлением, '
         'напр. Vitodens 200-W) ≈24–25 кВт; каскадный контроллер и каскадный дымоход — штатные Viessmann; '
         'типоразмеры — по каталогу Viessmann', '2'),
        ('2', 'ПК', 'Котёл пеллетный водогрейный ≈50 кВт: горелка, автоподача, бункер БП 300–500 л', '1'),
        ('3', 'ГС', f'Гидравлический разделитель Ду32, до {fnum(GC["hs_m3h"], 1)} м³/ч', '1'),
        ('4', 'РК', 'Коллектор распределительный двухкамерный Ду32 на 6 групп', '1'),
        ('5', 'Н1', f'Насос котлового контура ПК, G≈{fnum(hs["G_primary_pk"] / 1000, 1)} м³/ч '
         '(по паспорту ПК)', '1'),
        ('6', 'Н2', f'Группа насосная прямая Ду25, насос {GR["Н2"]["pump"]}: КШ-4', '1'),
        ('7', 'Н3', f'Группа насосная прямая Ду25, насос {GR["Н3"]["pump"]}: КШ-2 (Кв, смесит. узел ТП), '
         'Р-т — тройником', '1'),
        ('8', 'Н4', f'Группа насосная смесительная Ду25, 3-ходовой клапан с приводом, насос {GR["Н4"]["pump"]}: '
         'ТП 48,5 °С — КШ-1, КШ-3', '1'),
        ('9', 'Н5', f'Группа насосная смесительная Ду20, 3-ходовой клапан с приводом, насос {GR["Н5"]["pump"]}: П1',
         '1'),
        ('10', 'Н6', f'Группа насосная прямая Ду32, насос {GR["Н6"]["pump"]}: баня (Ecoflex → КШ-Б1, КШ-Б2)',
         '1'),
        ('11', 'Н7', f'Группа насосная прямая Ду25, насос {GR["Н7"]["pump"]}: загрузка Б1', '1'),
        ('12', 'Н8', 'Насос рециркуляции ГВС (для ГВС; подбор — раздел ВК)', '1'),
        ('13', 'КТ', 'Клапан термостатический трёхходовой подмеса 55 °С, Ду32', '1'),
        ('14', 'Б1', f'Бойлер косвенного нагрева 300 л, змеевик ≈{int(CALC["P_coil_house"])} кВт', '1'),
        ('15', 'РБ', f'Бак расширительный мембранный {ex["tank"]} л, p0 = {fnum(ex["p0"], 1)} бар', '1'),
        ('16', 'РБ-ГВС', f'Бак расширительный для ГВС {RD["expansion_dhw"]["Б1 300 л"]["tank"]} л', '1'),
        ('17', 'ГБ', 'Группа безопасности котла: клапан 3 бар, манометр, воздухоотводчик', '1'),
        ('18', 'ГБ-ГВС', 'Группа безопасности бойлера 6 бар', '1'),
        ('19', 'УП', 'Узел подпитки: краны, фильтр, редуктор 1,5 бар, обратный клапан', '1'),
        ('20', 'ШУ', 'Шкаф управления: каскадный погодозависимый контроллер (штатный Viessmann), '
         'управление насосами и клапанами групп', '1'),
        ('21', 'ШО', 'Шламоотделитель магнитный Ду32 на обратке перед ГС', '1'),
    ]
    rows += [list(r) for r in eq]
    widths = [7, 12, 74, 7]
    heights = [6.0] + [max(4.6, 1.8 + 2.8 * math.ceil(len(r[2]) / 68)) for r in rows[1:]]
    TX = 313
    yb = sh.table(TX, 285, widths, rows, h=1.65, heights=heights, aligns=['center', 'center', 'left', 'center'])
    sh.s.text('Экспликация оборудования', TX + sum(widths) / 2, 288.5, h=2.6, align='center')
    sh.notes(TX, yb - 4.5, 100, [
        'Котловой контур — до 80/60 °С; радиаторы, конвекторы, баня — 70/55 °С; калорифер П1 — 70/50 °С; '
        'ТП КШ-1, КШ-3 — 48,5 °С (смешение группой Н4); свои смесительные узлы: КШ-2 — 36 °С, '
        f'КШ-4 — {fnum(GC["mix"]["КШ-4"]["t"], 1)} °С, КШ-Б2 — {fnum(GC["mix"]["КШ-Б2"]["t"], 1)} °С (лист 6).',
        f'Баня (группа Н6): Ecoflex Quattro, Т1, Т2 PE-Xa 32×2,9, L≈{fnum(SITE_L, 1)} м по трассе (в гидравлике '
        f'{fnum(GR["Н6"]["L"], 0)} м) → '
        'УК1 (приоритет Б2) и УК2 (ТО-Д джакузи) → КШ-Б1, КШ-Б2 — листы 12, 13.',
        'К1, К2 — каскад со штатным контроллером Viessmann. ПК — резерв на полную нагрузку при '
        'отсутствии газа; обратка ПК не ниже 55 °С (КТ + Н1).',
        f'Давление рабочее 1,5 бар, предохранительные клапаны 3 бар; объём системы ≈{ex["V_sys"]} л.',
        'Приоритет ГВС: при загрузке Б1 группы отопления временно снижают отбор; ГВС 60 °С, '
        'термическая дезинфекция — по программе контроллера.',
        f'Подпитка, Т3, Т4 — от сетей ВК; Н8 и подключение ГВС — раздел ВК. Газ — проект ГСВ: расход '
        f'на К1, К2 ≈{fnum(RD["gas"]["gas_m3h"], 2)} м³/ч (уточняется по паспорту котлов).',
        'Насосы — с электронным управлением. Класс выбран по расходу и напору группы (лист 6), запас по напору '
        '10 % по условной характеристике; уточнить по каталогу.',
        f'Гидрострелка: одновременный отбор групп Н2–Н6 — {fnum(GC["G_hs"] / 1000, 2)} м³/ч '
        f'(без нагрева джакузи — {fnum(GC["G_hs_nojac"] / 1000, 2)} м³/ч).',
    ], h=1.75, spacing=1.05)
    legend3(S, 24, 64, cols=3, colw=68)
    return doc


if __name__ == '__main__':
    doc = build()
    no_yo(doc)
    print(save_and_pdf(doc, os.path.join(OUT, 'ov_boiler_scheme.dxf')))
