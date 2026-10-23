"""И05.09.26-ВК. Расчёты П1–П4 по СП 30.13330.2020 (таблицы — по тексту свода: ovk-dom-banya/norms/sp30-2020-bolid.txt).

П1 — баланс водопотребления и водоотведения (п. 5.2–5.13, табл. А.2);
П2 — расходы на участках, диаметры и скорости, требуемый напор, водомерный узел (п. 5.3, 8.26–8.28, разд. 12);
П3 — канализация К1: расходы, стояк, сборные трубопроводы и выпуски, уклоны и наполнения (п. 5.5, 5.7, 19.1, прил. К);
П4 — циркуляция ГВС дома и бани, насосы Н8, Н9 (п. 4.7, 9.6, 10.3, формула 16).
Исходные — 3D-модель vk_model (приборы на участках, длины труб).
python3 vk_calc.py  ->  out/vk/vk_calc.json
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vk_model as VK  # noqa: E402

# ---------------------------------------------------------------- СП 30.13330.2020, табл. Б.2: α(NP) при P ≤ 0,1
B2 = [
    (0.015, .202), (.016, .205), (.017, .207), (.018, .210), (.019, .212), (.020, .215), (.021, .217),
    (.022, .219), (.023, .222), (.024, .224), (.025, .226), (.026, .228), (.027, .230), (.028, .233),
    (.029, .235), (.030, .237), (.031, .239), (.032, .241), (.033, .243), (.034, .245), (.035, .247),
    (.036, .249), (.037, .250), (.038, .252), (.039, .254), (.040, .256), (.041, .258), (.042, .259),
    (.043, .261), (.044, .263), (.045, .265), (.046, .266), (.047, .268), (.048, .270), (.049, .271),
    (.050, .273), (.052, .276), (.054, .280), (.056, .283), (.058, .286), (.060, .289), (.062, .292),
    (.064, .295), (.065, .298), (.068, .301), (.070, .304), (.072, .307), (.074, .309), (.076, .312),
    (.078, .315), (.080, .318), (.082, .320), (.084, .323), (.086, .326), (.088, .328), (.090, .331),
    (.092, .333), (.094, .336), (.096, .338), (.098, .341), (.100, .343), (.105, .349), (.110, .355),
    (.115, .361), (.120, .367), (.125, .373), (.130, .378), (.135, .384), (.140, .389), (.145, .394),
    (.150, .399), (.155, .405), (.160, .410), (.165, .415), (.170, .420), (.175, .425), (.180, .430),
    (.185, .435), (.190, .439), (.195, .444), (.20, .449), (.21, .458), (.22, .467), (.23, .476),
    (.24, .485), (.25, .493), (.26, .502), (.27, .510), (.28, .518), (.29, .526), (.30, .534),
    (.31, .542), (.32, .550), (.33, .558), (.34, .565), (.35, .573), (.36, .580), (.37, .588),
    (.38, .595), (.39, .602), (.40, .610), (.41, .617), (.42, .624), (.43, .631), (.44, .638),
    (.45, .645), (.46, .652), (.47, .658), (.48, .665), (.49, .672), (.50, .678), (.52, .692),
    (.54, .704), (.56, .717), (.58, .730), (.60, .742), (.62, .755), (.64, .767), (.66, .779),
    (.68, .791), (.70, .803), (.72, .815), (.74, .826), (.76, .838), (.78, .849), (.80, .860),
]


def alpha(np_):
    if np_ < 0.015:
        return 0.200
    for (x0, a0), (x1, a1) in zip(B2, B2[1:]):
        if x0 <= np_ <= x1:
            return a0 + (a1 - a0) * (np_ - x0) / (x1 - x0)
    raise ValueError(np_)


# ---------------------------------------------------------------- табл. 5.1: Ks(N, L)
KS_L = [1, 3, 5, 7, 10, 15, 20, 30, 40, 50, 100, 500, 1000]
KS = {
    4: [.61, .51, .46, .43, .40, .36, .34, .31, .27, .25, .23, .15, .13],
    8: [.63, .53, .48, .45, .41, .37, .35, .32, .28, .26, .24, .16, .13],
    12: [.64, .54, .49, .46, .42, .39, .36, .33, .29, .26, .24, .16, .14],
    16: [.65, .55, .50, .47, .43, .39, .37, .33, .30, .27, .25, .17, .14],
    20: [.66, .56, .51, .48, .44, .40, .38, .34, .30, .28, .25, .17, .14],
    24: [.67, .57, .52, .48, .45, .41, .38, .35, .31, .28, .26, .17, .15],
}


def ks(n, length):
    rows = sorted(KS)
    n_row = next((r for r in rows if r >= n), rows[-1])     # в запас — ближайшее большее N
    i = max(j for j, l_ in enumerate(KS_L) if l_ <= max(length, 1))  # в запас — ближайшая меньшая L
    return KS[n_row][i], n_row, KS_L[i]


# ---------------------------------------------------------------- табл. 12.1: счётчики (Ду, Qmin, Qэкспл, Qmax м³/ч, S)
METERS = [(15, .03, 1.2, 3, 14.5), (20, .05, 2.0, 5, 5.18), (25, .07, 2.8, 7, 2.64), (32, .10, 4.0, 10, 1.3)]
STACK_CAP = {(110, 110, 87.5): 3.60, (110, 50, 87.5): 5.20, (110, 110, 45): 5.90}   # табл. К.2 (ПП, вентилируемые)

# ======================================================================== ИСХОДНЫЕ ДАННЫЕ
U = 6                 # жителей: K + 1 (табл. А.2, прим. 9), K = 5 жилых комнат: спальни 2.3, 2.4, 2.5, 2.7, кухня-гостиная 1.10
K_ROOMS = ['2.3', '2.4', '2.5', '2.7', '1.10']
NORM = dict(name='Жилые дома с ваннами длиной от 1500 мм, оборудованными душами (табл. А.2, п. 1)',
            qu_tot=180, qu_h=70, qhr_tot=11.6, qhr_h=6.5, q0_tot=0.3, q0_c=0.2, q0_h=0.2,
            q0hr_tot=300, q0hr_c=200, q0hr_h=200, T=24)
NORM['qu_c'] = NORM['qu_tot'] - NORM['qu_h']
NORM['qhr_c'] = round(NORM['qhr_tot'] - NORM['qhr_h'], 2)
POLIV = dict(area=300.0, norm=3.0, n=1)   # травяной покров 3 л/м² (табл. А.2, п. 26); площадь — допущение
T_H, T_C = 65.0, 5.0                      # температура ГВС на выходе Б1, Б2 (п. 4.7: у приборов не ниже 60 °С); ХВС
H_FREE = 20.0                             # п. 8.21 — свободный напор у диктующего прибора
KL = 0.3                                  # п. 8.28 — хоз.-питьевой водопровод жилых зданий
H_HEAT = 3.0                              # п. 8.27 — потери в водонагревателе (ориентировочно)
V_MAX = 1.5                               # прил. И: 35 дБА, арматура — краны, ζ подключения ≤ 10
EPS = 7e-6                                # шероховатость PE-X, м
NU = {'c': 1.306e-6, 'h': 0.475e-6}       # 10 °С и 60 °С
PE_DI = {'32×3,0': 0.026, '40×3,7': 0.0326}
ECO = dict(dn='32×4,4', L=17.0, di=0.0232)   # санитарная труба Ecoflex Quattro (ОВ: L = 17 м)
Z_VVOD = -0.85
SHOWER_HEAD = 2.10                        # высота излива душевой сетки над полом (диктующая точка)
# арматура водомерного узла: Kvs, м³/ч (типовые для Ду32; уточнить по паспортам)
NODE_FIT = [('Фильтр сетчатый косой Ду32', 16.0), ('Обратный клапан Ду32', 15.0),
            ('Фильтр тонкой очистки самопромывной Ду32', 7.0), ('Регулятор давления Ду32 (полностью открыт)', 7.0)]
REG_SET = 40.0                            # уставка регулятора давления, м (4 бар)
REG_DROOP = 5.0                           # падение давления за регулятором при расчётном расходе, м (≈0,5 бар)

FX = VK.FIXT


def water(f):
    return f.cold or f.hot


ALL = sorted(k for k, f in FX.items() if water(f))
COLD = sorted(k for k, f in FX.items() if f.cold)
HOT = sorted(k for k, f in FX.items() if f.hot)
HOUSE = {k for k, f in FX.items() if f.bld == 'h'}
BATH = {k for k, f in FX.items() if f.bld == 'b'}
ON_KX = {'СМ-1', 'ПК-1', 'ПК-2'}
SHVK1 = {'УМ-1', 'УН-1', 'Д-1', 'М-1', 'ПМ-1'}

P = dict(tot=NORM['qhr_tot'] * U / (NORM['q0_tot'] * 3600 * len(ALL)),
         c=NORM['qhr_c'] * U / (NORM['q0_c'] * 3600 * len(COLD)),
         h=NORM['qhr_h'] * U / (NORM['q0_h'] * 3600 * len(HOT)))
Q0 = dict(tot=NORM['q0_tot'], c=NORM['q0_c'], h=NORM['q0_h'])
Q0HR = dict(tot=NORM['q0hr_tot'], c=NORM['q0hr_c'], h=NORM['q0hr_h'])
A1I = dict(tot=1, c=2, h=3)


def members(p):
    s = set()
    for t in p.serves:
        if t == '*':
            s |= set(ALL) | {'Б1', 'Б2'}
        elif t == '*дом':
            s |= {k for k in HOUSE if water(FX[k]) and k not in ON_KX}
        elif t == '*1эт':
            s |= SHVK1
        elif t in ('*баня', 'баня'):
            s |= {k for k in BATH if water(FX[k])} | {'Б2'}
        elif t == 'М-1':
            s |= {'М-1', 'ПМ-1'}
        else:
            s.add(t)
    return s


def flow(mode, fxs):
    """Расчётный секундный расход (п. 5.3): один прибор — q0 по табл. А.1; группа — 5·q0·α (q0 по табл. А.2),
    но не меньше q0 наибольшего прибора (п. 5.3, прим. 1)."""
    fxs = sorted(fxs)
    n = len(fxs)
    if n == 0:
        return None
    qmax = max(FX[k].a1[A1I[mode]] for k in fxs)
    if n == 1:
        return dict(mode=mode, N=1, P=None, NP=None, a=None, q=qmax, fx=fxs, by='А.1')
    np_ = n * P[mode]
    a = alpha(np_)
    q = 5 * Q0[mode] * a
    return dict(mode=mode, N=n, P=P[mode], NP=np_, a=a, q=max(q, qmax), fx=fxs, by='5·q0·α' if q >= qmax else 'q0 max')


def water_flow(p):
    m = members(p)
    if p.sys == 'В1':
        if m == {'УП'}:
            return dict(mode='УП', N=0, q=0.10, fx=[], by='подпитка ОВ (Ду15), в расход ввода не входит')
        if m == {'*АП'}:
            return dict(mode='АП', N=0, q=0.30, fx=[], by='автополив — по ландшафтному проекту (полив по таймеру, '
                                                          'не одновременно с пиковым водоразбором)')
        if not m:
            return None
        fx = {k for k in m if k in FX}
        heaters = m & {'Б1', 'Б2'}
        if heaters and not fx:                      # подвод только к водонагревателю — его расход ГВС
            grp = HOUSE if 'Б1' in heaters else BATH
            return flow('h', {k for k in grp if FX[k].hot})
        if heaters:
            tot = set(fx)
            if 'Б1' in heaters:
                tot |= {k for k in HOUSE if FX[k].hot}
            if 'Б2' in heaters:
                tot |= {k for k in BATH if FX[k].hot}
            return flow('tot', {k for k in tot if water(FX[k])})
        return flow('c', {k for k in fx if FX[k].cold})
    if p.sys == 'Т3':
        return flow('h', {k for k in m if k in FX and FX[k].hot})
    return None


def di_of(p):
    if p.mat == 'pex':
        return VK.PEX_DI[p.dn]
    if p.mat == 'pe':
        return PE_DI[p.dn]
    return None


def hyd(q_ls, di, nu):
    a = math.pi * di ** 2 / 4
    v = q_ls / 1000 / a
    re = v * di / nu
    lam = 64 / re if re < 2300 else 0.25 / (math.log10(EPS / (3.7 * di) + 5.74 / re ** 0.9)) ** 2
    return v, lam / di * v ** 2 / 19.62, re


# ======================================================================== П1. Баланс
def balance():
    day_tot = NORM['qu_tot'] * U / 1000
    day_h = NORM['qu_h'] * U / 1000
    day_c = day_tot - day_h
    poliv = POLIV['area'] * POLIV['norm'] * POLIV['n'] / 1000
    qT = dict(tot=day_tot / NORM['T'], h=day_h / NORM['T'], c=day_c / NORM['T'])
    sec, hr = {}, {}
    for mode, n in (('tot', len(ALL)), ('c', len(COLD)), ('h', len(HOT))):
        np_ = n * P[mode]
        sec[mode] = dict(N=n, P=P[mode], NP=np_, a=alpha(np_), q=5 * Q0[mode] * alpha(np_))
        phr = 3600 * P[mode] * Q0[mode] / Q0HR[mode]
        ahr = alpha(n * phr)
        hr[mode] = dict(Phr=phr, NPhr=n * phr, a=ahr, q=0.005 * Q0HR[mode] * ahr)
    q_heat_h = 1.16 * hr['h']['q'] * (T_H - T_C)        # кВт без Qht (п. 5.12, формула 13)
    q_heat_T = 1.16 * qT['h'] * (T_H - T_C)
    return dict(U=U, K_rooms=K_ROOMS, norm=NORM, N=dict(tot=len(ALL), c=len(COLD), h=len(HOT)),
                fixtures=dict(all=ALL, cold=COLD, hot=HOT), P=P,
                day=dict(tot=day_tot, h=day_h, c=day_c, poliv=poliv, total=day_tot + poliv, sewer=day_tot),
                qT=qT, sec=sec, hr=hr, sewer=dict(day=day_tot, hr=hr['tot']['q'], sec=sec['tot']['q']),
                heat=dict(Qhr=q_heat_h, QT=q_heat_T), poliv=POLIV)


# ======================================================================== П2. Расходы, диаметры, напор
def network():
    rows = {}
    for p in VK.PIPES:
        if p.sys not in ('В1', 'Т3'):
            continue
        fl = water_flow(p)
        if not fl:
            continue
        di = di_of(p)
        v, i, re = hyd(fl['q'], di, NU['h' if p.sys == 'Т3' else 'c'])
        rows[p.id] = dict(id=p.id, sys=p.sys, bld=p.bld, name=p.name, dn=p.label(), di=di, L=p.length(), **fl,
                          v=v, i=i, H=i * p.length() * (1 + KL), ok_v=v <= V_MAX)
    # санитарная труба Ecoflex Quattro (дом — баня), В1
    fl = water_flow(VK.Pipe('ЭФ', 'В1', 'pex', '32×4,4', [(0, 0, 0), (1, 0, 0)], serves=['*баня']))
    v, i, re = hyd(fl['q'], ECO['di'], NU['c'])
    rows['ЭФ'] = dict(id='ЭФ', sys='В1', bld='h', name='В1 в санитарной трубе Ecoflex Quattro (дом — баня)',
                      dn='PE-Xa 32×4,4', di=ECO['di'], L=ECO['L'], **fl, v=v, i=i, H=i * ECO['L'] * (1 + KL),
                      ok_v=v <= V_MAX)
    return rows


def node_losses(q):
    q_m3h = q * 3.6
    return [dict(name=n, kvs=k, h=10.2 * (q_m3h / k) ** 2) for n, k in NODE_FIT]


def meter_pick(q, qT_m3h):
    rows = []
    for dn, qmin, qe, qmax, s in METERS:
        h = s * q ** 2
        rows.append(dict(dn=dn, qmin=qmin, qe=qe, qmax=qmax, S=s, h=h, ok_qT=qT_m3h <= qe, ok_h=h <= 5.0,
                         ok_qmax=q * 3.6 <= qmax))
    first = next(r for r in rows if r['ok_qT'] and r['ok_h'] and r['ok_qmax'])
    chosen = next(r for r in rows if r['dn'] == 20)       # принят Ду20: потери ≈1 м вместо ≈2,9 м у Ду15
    return dict(q=q, q_m3h=q * 3.6, qT=qT_m3h, rows=rows, first=first['dn'], chosen=chosen)


PATHS = [
    dict(key='h_c', name='Дом, ХВС: ввод → КХ → ШВК-2 → душ Д-3 (2 этаж)', bld='h',
         ids=['ВВ', 'В1-узел', 'КХ', 'КХ-4', 'В1-гараж', 'ШВК-2В', 'В1-Д-3'], z=VK.FL2 + SHOWER_HEAD, heater=False),
    dict(key='h_h', name='Дом, ГВС: ввод → КХ → Б1 → Т3 → ШВК-2 → душ Д-3 (2 этаж)', bld='h',
         ids=['ВВ', 'В1-узел', 'КХ', 'КХ-1', 'Т3-1.6', 'Т3-гараж', 'ШВК-2Т', 'Т3-Д-3'], z=VK.FL2 + SHOWER_HEAD,
         heater=True),
    dict(key='b_c', name='Баня, ХВС: ввод → КХ → Ecoflex → ШВК-Б → душ Д-б1', bld='b',
         ids=['ВВ', 'В1-узел', 'КХ', 'КХ-3', 'ЭФ', 'В1-баня', 'ШВК-БВ', 'В1-Д-б1'], z=VK.B_FL + SHOWER_HEAD,
         heater=False),
    dict(key='b_h', name='Баня, ГВС: ввод → КХ → Ecoflex → Б2 → Т3 → ШВК-Б → душ Д-б1', bld='b',
         ids=['ВВ', 'В1-узел', 'КХ', 'КХ-3', 'ЭФ', 'В1-баня', 'В1-Б2', 'Т3-Б2', 'ШВК-БТ', 'Т3-Д-б1'],
         z=VK.B_FL + SHOWER_HEAD, heater=True),
]


def head(rows, meter):
    q_in = rows['ВВ']['q']
    fits = node_losses(q_in)
    h_fit = sum(f['h'] for f in fits)
    h_m = meter['chosen']['S'] * q_in ** 2
    out = []
    for pth in PATHS:
        secs = [rows[i] for i in pth['ids']]
        hl = sum(s['H'] for s in secs)
        h_geom = pth['z'] - Z_VVOD
        h_heat = H_HEAT if pth['heater'] else 0.0
        htr = h_geom + hl + H_FREE + h_m + h_fit + h_heat
        # за регулятором давления (отметка узла): что нужно на выходе регулятора
        after = [s for s in secs if s['id'] not in ('ВВ', 'В1-узел')]
        h_after = sum(s['H'] for s in after) + rows['В1-узел']['H'] * 0.1
        h_reg = (pth['z'] - VK.Z_NODE) + h_after + H_FREE + h_heat
        out.append(dict(key=pth['key'], name=pth['name'], ids=pth['ids'], z=pth['z'], h_geom=h_geom, hl=hl,
                        h_free=H_FREE, h_meter=h_m, h_fit=h_fit, h_heat=h_heat, Htr=htr, H_reg_need=h_reg,
                        reg_ok=h_reg <= REG_SET - REG_DROOP))
    return dict(paths=out, fits=fits, Htr=max(p['Htr'] for p in out),
                dict_path=max(out, key=lambda p: p['Htr'])['key'], reg_set=REG_SET, reg_droop=REG_DROOP)


# ======================================================================== П3. Канализация
PP_DI = {50: 0.0464, 110: 0.1036, 32: 0.0284}


def part_flow(d_in, i, q_ls, n_rough=0.009):
    q = q_ls / 1000

    def fl(hd):
        th = 2 * math.acos(1 - 2 * hd)
        a = d_in ** 2 / 8 * (th - math.sin(th))
        pw = d_in * th / 2
        v = (a / pw) ** (2 / 3) * math.sqrt(i) / n_rough
        return a * v, v
    lo, hi = 1e-4, 0.94
    for _ in range(80):
        mid = (lo + hi) / 2
        if fl(mid)[0] < q:
            lo = mid
        else:
            hi = mid
    hd = (lo + hi) / 2
    return hd, fl(hd)[1]


K1_SETS = {
    'К1-гараж': (['УН-2', 'В-2', 'УМ-2', 'УН-3', 'УМ-3', 'Д-3', 'В-3'], 'гориз', 110, 0.02,
                 'Сборный Ø110 под потолком гаража (2 этаж)'),
    'Ст.К1-1': (['УН-2', 'В-2', 'УМ-2', 'УН-3', 'УМ-3', 'Д-3', 'В-3'], 'стояк', 110, None,
                'Стояк Ст.К1-1 (вентилируемый, Ст.К1-1в)'),
    'К1-1': (['УН-1', 'УМ-1', 'Д-1', 'М-1', 'ПМ-1', 'СМ-1', 'Т-1', 'УН-2', 'В-2', 'УМ-2', 'УН-3', 'УМ-3', 'Д-3',
              'В-3'], 'гориз', 110, 0.02, 'Выпуск К1-1 (дом), сборный под плитой'),
    'К1-1.6': (['Т-1', 'СМ-1'], 'гориз', 50, 0.03, 'Отвод Ø50 от трапа и СМ топочной 1.6'),
    'К1-б': (['УН-б1', 'УМ-б1', 'М-б1', 'Д-б1', 'В-б1', 'Т-б1'], 'гориз', 110, 0.02, 'Выпуск К1-б (баня)'),
}


def sewer():
    phr = 3600 * P['tot'] * Q0['tot'] / Q0HR['tot']
    res = dict(Phr=phr, P=P['tot'], sections=[], branches=[])
    for sid, (fx, kind, d, i, nm) in K1_SETS.items():
        n = len(fx)
        q0s = max(FX[k].a1[7] for k in fx)
        a = alpha(n * P['tot'])
        qtot = 5 * Q0['tot'] * a
        row = dict(id=sid, name=nm, fx=fx, N=n, q0s=q0s, NP=n * P['tot'], a=a, qtot=qtot, d=d, kind=kind)
        if kind == 'стояк':
            cap = STACK_CAP[(110, 110, 87.5)]
            row.update(qs=qtot + q0s, cap=cap, ok=qtot + q0s <= cap)
        else:
            L = 1.0 if sid in ('К1-1', 'К1-б') else max(1.0, [p for p in VK.PIPES if p.id == sid][0].length())
            k, n_row, l_row = ks(n, L)
            ahr = alpha(n * phr)
            qhr = 0.005 * Q0HR['tot'] * ahr
            qsl = qhr / 3.6 + k * q0s
            qd = max(qsl, q0s)
            hd, v = part_flow(PP_DI[d], i, qd)
            row.update(NPhr=n * phr, ahr=ahr, qhr=qhr, Ks=k, Ks_N=n_row, Ks_L=l_row, L=L, qsl=qsl, q=qd, i=i,
                       hd=hd, v=v, kk=v * math.sqrt(hd), self_clean=v >= 0.7 and hd >= 0.3 and v * math.sqrt(hd) >= 0.5,
                       i_min=1 / d)
        res['sections'].append(row)
    # отводы от приборов: Ø50 (i 0,03), Ø110 от унитазов и трапа Ду100 (i 0,02)
    seen = set()
    for p in VK.PIPES:
        if p.sys != 'К1' or p.id in K1_SETS or not p.serves or p.where == 'riser':
            continue
        fx = [s for s in p.serves if s in FX]
        if not fx:
            continue
        key = (p.dn, tuple(sorted({FX[k].typ for k in fx})))
        q0s = max(FX[k].a1[7] for k in fx)
        i = 0.03 if p.dn == 50 else 0.02
        hd, v = part_flow(PP_DI[p.dn], i, q0s)
        res['branches'].append(dict(id=p.id, name=p.name, fx=fx, d=p.dn, q=q0s, i=i, hd=hd, v=v,
                                    kk=v * math.sqrt(hd), L=p.length(), bld=p.bld, i_min=1 / p.dn, rep=key not in seen))
        seen.add(key)
    return res


# ======================================================================== П4. Циркуляция ГВС
LAM_INS, LAM_PEX, DELTA, ALPHA_AIR, R_FLOOR = 0.038, 0.35, 0.013, 8.0, 0.40
T_AIR = dict(garage=16.0, boiler=18.0, room=20.0, wet=24.0)
TOWEL = {'Пс-1': 359, 'Пс-2': 128, 'Пс-б1.1': 436, 'Пс-б1.2': 436, 'Пс-б2': 419}   # Вт при 60/50 °С (ОВ, ТЗ-3)


def q_lin(dn, t_w, where, t_a):
    do, di = VK.PEX[dn], VK.PEX_DI[dn]
    r = math.log(do / di) / (2 * math.pi * LAM_PEX) + math.log((do + 2 * DELTA) / do) / (2 * math.pi * LAM_INS)
    r += R_FLOOR if where == 'floor' else 1 / (math.pi * (do + 2 * DELTA) * ALPHA_AIR)
    return (t_w - t_a) / r


def loop(name, parts, towels, t_set=T_H, dt=10.0):
    """parts: [(pipe id или (имя, dn, L, where, t_a)), система Т3/Т4]; towels: имена полотенцесушителей."""
    rows = []
    for item, sysk in parts:
        if isinstance(item, str):
            p = [x for x in VK.PIPES if x.id == item][0]
            dn, L, where = p.dn, p.length(), p.where
            ta = T_AIR['wet'] if p.bld == 'b' else (T_AIR['garage'] if where in ('ceil', 'wall') else T_AIR['room'])
            if item in ('Т3-1.6', 'Т4-1.6'):
                ta = T_AIR['boiler']
            nm = p.name
        else:
            nm, dn, L, where, ta = item
            item = nm
        tw = t_set - 1.0 if sysk == 'Т3' else t_set - dt * 0.6
        q = q_lin(dn, tw, where, ta)
        rows.append(dict(id=item, name=nm, sys=sysk, dn=dn, L=L, where=where, ta=ta, tw=tw, q=q, Q=q * L))
    q_t3 = sum(r['Q'] for r in rows if r['sys'] == 'Т3')
    q_t4 = sum(r['Q'] for r in rows if r['sys'] == 'Т4')
    q_tw = sum(TOWEL[t] for t in towels)
    q_all = q_t3 + q_t4 + q_tw
    g = q_all / 1000 / (4.2 * dt)                          # кг/с ≈ л/с, формула (16)
    t_end_t3 = t_set - q_t3 / 1000 / (4.2 * g)
    # гидравлика кольца
    hl = 0.0
    for r in rows:
        di = VK.PEX_DI[r['dn']]
        v, i, re = hyd(g, di, NU['h'])
        r.update(v=v, i=i, H=i * r['L'] * (1 + KL))
        hl += r['H']
    zeta = 3.0 * len(towels) + 4.0 + 2.0              # полотенцесушители, обратный клапан, коллекторы
    v20 = g / 1000 / (math.pi * VK.PEX_DI['20×2,8'] ** 2 / 4)
    h_loc = zeta * v20 ** 2 / 19.62
    h_bv = 0.3                                          # минимальный перепад на балансировочном клапане, м
    h_pump = hl + h_loc + h_bv
    return dict(name=name, rows=rows, towels={t: TOWEL[t] for t in towels}, Q_t3=q_t3, Q_t4=q_t4, Q_towel=q_tw,
                Q=q_all, dt=dt, t_set=t_set, G=g, G_m3h=g * 3.6, t_end_t3=t_end_t3, t_ret=t_set - dt,
                h_pipes=hl, h_loc=h_loc, h_bv=h_bv, H=h_pump,
                pump_Q=math.ceil(g * 3.6 * 1.1 * 100) / 100, pump_H=math.ceil(h_pump * 1.2 * 10) / 10)


def dead_ends():
    """Объём тупиковых подводок Т3 (от коллектора до прибора) и время ожидания горячей воды при q0 прибора."""
    out = []
    for p in VK.PIPES:
        if p.sys != 'Т3' or len(p.serves) != 1 or p.serves[0] not in FX:
            continue
        f = FX[p.serves[0]]
        vol = math.pi / 4 * VK.PEX_DI[p.dn] ** 2 * p.length() * 1000
        out.append(dict(id=p.id, fx=f.id, dn=p.dn, L=p.length(), V=vol, q0=f.a1[3], t=vol / f.a1[3]))
    return out


def main():
    bal = balance()
    rows = network()
    qT_m3h = bal['day']['total'] / 24
    meter = meter_pick(rows['ВВ']['q'], qT_m3h)
    hd = head(rows, meter)
    sw = sewer()
    house = loop('Дом: Б1 → ШВК-2 → ШВК-1 → Пс-2, Пс-1 → Н8 → Б1',
                 [(('Т3 в топочной от Б1 (ТМ)', '25×3,5', 1.0, 'wall', T_AIR['boiler']), 'Т3'), ('Т3-1.6', 'Т3'),
                  ('Т3-гараж', 'Т3'), ('ШВК-2Т', 'Т3'), ('Т3-ШВК1', 'Т3'), ('ШВК-1Т', 'Т3'), ('Т4-дом', 'Т4'),
                  ('Т4-1.6', 'Т4'), (('Т4 в топочной к Б1 (ТМ)', '20×2,8', 0.3, 'wall', T_AIR['boiler']), 'Т4')],
                 ['Пс-2', 'Пс-1'])
    bath = loop('Баня: Б2 → ШВК-Б → Пс-б1.1, Пс-б1.2, Пс-б2 → Н9 → Б2',
                [('Т3-Б2', 'Т3'), ('ШВК-БТ', 'Т3'), ('Т4-баня', 'Т4')], ['Пс-б1.1', 'Пс-б1.2', 'Пс-б2'])
    res = dict(balance=bal, network=rows, meter=meter, head=hd, sewer=sw, circ=dict(house=house, bath=bath),
               dead_ends=dead_ends(), assume=dict(
                   U=f'{U} жителей: K + 1 по прим. 9 к табл. А.2, K = 5 (спальни 2.3, 2.4, 2.5, 2.7, кухня-гостиная 1.10)',
                   poliv=f'полив газона {int(POLIV["area"])} м² × {POLIV["norm"]:.0f} л/м², один раз в сутки (в т. ч. '
                         f'автополив от КХ-8) — площадь уточнить по ландшафтному проекту',
                   source='централизованный поселковый водопровод и канализация д. Исаково (ответ Заказчика)',
                   bath='баня — те же жители: приборы бани учтены в N, суточная норма на жителя включает пользование баней',
                   z_bath='±0,000 бани = ±0,000 дома (уточнить по ГП)',
                   t_air='температура воздуха: гараж 16 °С, топочная 18 °С, комнаты 20 °С, помещения бани 24 °С',
                   node='Kvs арматуры водомерного узла — типовые для Ду32, уточнить по паспортам принятого оборудования'))
    os.makedirs(VK.OUT, exist_ok=True)
    json.dump(res, open(os.path.join(VK.OUT, 'vk_calc.json'), 'w'), ensure_ascii=False, indent=1, default=float)
    return res


if __name__ == '__main__':
    r = main()
    b = r['balance']
    print('U', b['U'], 'N', b['N'], 'P', {k: round(v, 5) for k, v in b['P'].items()})
    print('сут', {k: round(v, 3) for k, v in b['day'].items()}, 'qT', {k: round(v, 4) for k, v in b['qT'].items()})
    print('q', {k: round(v['q'], 3) for k, v in b['sec'].items()}, 'qhr', {k: round(v['q'], 3) for k, v in b['hr'].items()})
    print('Q ГВС', {k: round(v, 2) for k, v in b['heat'].items()})
    for k, x in r['network'].items():
        print(f"{k:12s} {x['sys']} {x['dn']:16s} N={x['N']:2d} q={x['q']:.3f} v={x['v']:.2f} i={x['i']*1000:6.1f}мм/м "
              f"L={x['L']:5.1f} H={x['H']:.2f}{'' if x['ok_v'] else '  !!! v'}")
    m = r['meter']
    print('счётчик', m['first'], m['chosen'], 'qT', round(m['qT'], 4))
    for p in r['head']['paths']:
        print(p['key'], round(p['h_geom'], 2), round(p['hl'], 2), round(p['h_meter'], 2), round(p['h_fit'], 2),
              p['h_heat'], 'Hтр', round(p['Htr'], 1), 'за регулятором', round(p['H_reg_need'], 1), p['reg_ok'])
    for s in r['sewer']['sections']:
        print(s['id'], s['N'], round(s['qtot'], 3), {k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items()
                                                     if k in ('qs', 'cap', 'qsl', 'q', 'hd', 'v', 'kk', 'Ks', 'self_clean')})
    for bb in r['sewer']['branches']:
        print(' ', bb['id'], bb['d'], bb['q'], round(bb['hd'], 2), round(bb['v'], 2))
    for k, c in r['circ'].items():
        print(k, 'Q', round(c['Q_t3']), round(c['Q_t4']), c['Q_towel'], round(c['Q']), 'G', round(c['G_m3h'], 3), 'м³/ч',
              't_end', round(c['t_end_t3'], 1), 'H', round(c['H'], 2), 'насос', c['pump_Q'], c['pump_H'])
    for d in r['dead_ends']:
        print('  тупик', d['id'], round(d['L'], 1), 'м', round(d['V'], 2), 'л', round(d['t']), 'с')
