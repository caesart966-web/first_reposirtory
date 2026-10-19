"""И05.09.26-ОВ, лист 12. Баня. План отопления и вентиляции. М 1:50.

Расчётная часть (bath_calc) — общая для листов 12 и 13: тёплый пол бани пересчитан по пределу температуры
поверхности СП 60 (26 °С — постоянное пребывание, 31 °С — санузлы и временное), площади петель — по зонам,
нарисованным на плане; недостача пола переносится на приборы того же помещения.

python3 sheets/ov_bath.py  ->  out/ov_bath.dxf + out/ov_bath_Лист.pdf
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from rdbase import (new_doc, DPlan, RDSheet, add_underlay, insert_underlay, UNDER, save_and_pdf,  # noqa: E402
                    fmt_num, offset_poly, SHEET_LIST, SHEETS_TOTAL, axes, BATH_AX)

OUT = os.path.join(ROOT, 'out')
os.makedirs(OUT, exist_ok=True)
RD = json.load(open(os.path.join(ROOT, '..', 'rd', 'rd_calc.json')))
RDUFH = {u['no']: u for u in RD['ufh']}
RDDEV = {d['name']: d for d in RD['devices']}
CALC = json.load(open(os.path.join(ROOT, '..', 'ovk', 'calc.json')))
ROOM = {r['no']: r for r in CALC['rooms']}

SHEET_NO = 12
K = 50


def n0(v):
    return fmt_num(v, 0)


# =========================================================================== расчёт (как в rd/calc_rd.py)
CW = 4187.0
K_PEX = 0.007e-3
UFH_DO, UFH_DI = 0.016, 0.012
SCREED = 0.100
SU = SCREED - UFH_DO
LAM_E = 1.2
L_LOOP_MAX = 90.0
DP_LOOP_MAX = 20.0
COVER_R = {'плитка': 0.02, 'доска': 0.10}
COVER = {'б2': 'плитка', 'б3': 'плитка', 'б4': 'плитка', 'б6': 'доска', 'б7': 'плитка'}   # допущение (нет экспликации полов)
DOWN = (0.10 / 0.034 + 0.10 / 1.5 + 1 / 5.9, 5.0)          # пол по грунту: ЭППС 100, грунт +5 °С
TV_RAD, TR_RAD = 70.0, 55.0
DT_N = None

_RL = [0.0, 0.05, 0.10, 0.15]
_AT = [1.23, 1.188, 1.156, 1.134]
_T = [0.05, 0.075, 0.10, 0.15, 0.20, 0.225, 0.30, 0.375]
_AU = [[1.069, 1.056, 1.043, 1.037], [1.066, 1.053, 1.041, 1.035], [1.063, 1.050, 1.039, 1.033],
       [1.057, 1.046, 1.035, 1.030], [1.051, 1.041, 1.031, 1.027], [1.048, 1.038, 1.029, 1.025],
       [1.040, 1.031, 1.024, 1.021], [1.030, 1.025, 1.020, 1.018]]
_AD = [[1.013, 1.013, 1.012, 1.011], [1.021, 1.019, 1.016, 1.014], [1.029, 1.025, 1.022, 1.018],
       [1.040, 1.034, 1.029, 1.024], [1.046, 1.040, 1.035, 1.030], [1.049, 1.043, 1.038, 1.033],
       [1.053, 1.049, 1.044, 1.039], [1.056, 1.051, 1.046, 1.042]]


def _interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    for x0, x1, y0, y1 in zip(xs, xs[1:], ys, ys[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return ys[-1]


def _bilin(tab, T, R):
    return _interp(_T, [_interp(_RL, row, R) for row in tab], T)


def k_h(T, R):
    B = 6.7
    aB = (1 / 10.8 + 0.045 / 1.0) / (1 / 10.8 + 0.045 / LAM_E + R)
    return (B * aB * _interp(_RL, _AT, R) ** (1 - T / 0.075) * _bilin(_AU, T, R) ** (100 * (0.045 - SU))
            * _bilin(_AD, T, R) ** (250 * (UFH_DO - 0.020)))


def solve_return(tv, ti, dth):
    if dth >= tv - ti - 1e-6:
        return None
    lo, hi = ti + 1e-6, tv - 1e-6
    for _ in range(200):
        mid = (lo + hi) / 2
        d = (tv - mid) / math.log((tv - ti) / (mid - ti))
        if d > dth:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def water(t):
    tab = [(10, 999.7, 1.306e-6), (20, 998.2, 1.004e-6), (30, 995.7, 0.801e-6), (40, 992.2, 0.658e-6),
           (50, 988.0, 0.553e-6), (60, 983.2, 0.474e-6), (70, 977.8, 0.413e-6), (80, 971.8, 0.365e-6)]
    for (t0, r0, n0_), (t1, r1_, n1) in zip(tab, tab[1:]):
        if t0 <= t <= t1:
            k = (t - t0) / (t1 - t0)
            return r0 + k * (r1_ - r0), n0_ + k * (n1 - n0_)
    return tab[-1][1], tab[-1][2]


def pipe_dp(G_kgh, d_mm, L, t, zeta=0.0):
    rho, nu = water(t)
    d = d_mm / 1000
    v = G_kgh / 3600 / rho / (math.pi * d * d / 4)
    re = v * d / nu
    if re < 2300:
        lam = 64 / max(re, 1e-9)
    else:
        lam = 0.02
        for _ in range(40):
            lam = (-2 * math.log10(K_PEX / (3.7 * d) + 2.51 / (re * math.sqrt(lam)))) ** -2
    dyn = rho * v * v / 2
    return dict(v=v, dp=lam / d * dyn * L + zeta * dyn)


def lmtd(tv, tr, ti):
    return (tv - tr) / math.log((tv - ti) / (tr - ti))


DT_N = lmtd(75, 65, 20)


def area(poly):
    s = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        s += x0 * y1 - x1 * y0
    return abs(s) / 2


def plen(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


# ------------------------------------------------------------------ геометрия бани (оси бани 1/А = 0,0; м)
CAB_DIR = (15.57, 0.20, 15.70, 0.95)     # КШ-Б1 — прямой коллектор (у окна, южный), ШРВ-3 по АР
CAB_UFH = (15.57, 0.95, 15.70, 1.70)     # КШ-Б2 — коллектор ТП со смесительным узлом (северный), ШРВ-3 по АР
B2 = (15.04, 2.00, 0.27)                 # бойлер Б2 Ø520 в выгородке 600 мм (по АР)
NICHE = (14.70, 1.70, 15.70, 2.36)

# зоны укладки ТП (свободный от сантехники, встроенной мебели и пучка подводок пол)
LOOPS = {
    'б7-1': [(0.30, 2.70), (2.00, 2.70), (2.00, 6.30), (0.30, 6.30)],
    'б7-2': [(2.98, 2.02), (4.80, 2.02), (4.80, 3.35), (2.98, 3.35)],
    'б6-1': [(5.55, 3.40), (7.55, 3.40), (7.55, 6.35), (5.55, 6.35)],
    'б6-2': [(7.55, 3.40), (9.55, 3.40), (9.55, 6.35), (7.55, 6.35)],
    'б2': [(10.78, 0.65), (12.35, 0.65), (12.35, 1.80), (10.78, 1.80)],
    'б3': [(12.75, 0.95), (14.70, 0.95), (14.70, 1.55), (12.75, 1.55)],
    'б4': [(12.75, 2.65), (15.38, 2.65), (15.38, 3.28), (12.75, 3.28)],
}
LOOP_ROOM = {k: k.split('-')[0] for k in LOOPS}

# приборы: (x0, y0, x1, y1)
DEVPOS = {
    'Кв-б1': (5.65, 2.32, 7.80, 2.62), 'Кв-б2': (8.00, 2.32, 10.15, 2.62), 'Кв-б3': (2.65, 0.32, 4.85, 0.62),
    'Р-б1': (15.52, 4.40, 15.68, 5.50), 'Р-б2': (10.72, 1.80, 10.88, 2.30),
    'Пс-б1': (13.00, 1.58, 13.60, 1.68), 'Пс-б2': (15.58, 2.50, 15.68, 3.10),
}
TOD_POS = (2.65, 2.05, 2.95, 2.45)

# пучок подводок: юг -> север (порядок исключает пересечения при отводах)
BAND = ['б2', 'Р-б2', 'Кв-б2', 'Кв-б1', 'Кв-б3', 'б7-2', 'ТО-Д', 'б7-1', 'б6-1', 'б6-2', 'б4']
Y7 = {'Кв-б3': 3.42, 'б7-2': 3.48, 'ТО-Д': 3.54, 'б7-1': 3.60}      # ряды в помывочной б7 (у стеклянной стены парной)
STEP = 0.06
Y4 = {n: 1.97 + i * STEP for i, n in enumerate(BAND)}       # ряды пучка в раздевалке б4 и прихожей б2
Y6 = {n: 2.72 + i * STEP for i, n in enumerate(BAND)}       # ряды пучка в комнате отдыха б6 и проёмах
XV = {n: 14.80 + i * STEP for i, n in enumerate(BAND)}      # подъёмы из санузла в раздевалку (под выгородкой Б2)
X_JOG = 11.30                                               # переход пучка на ряды б6 (в прихожей б2)
DIRECT_OUT = ['Пс-б1', 'Р-б2', 'Кв-б2', 'Кв-б1', 'Кв-б3', 'ТО-Д', 'Пс-б2', 'Р-б1']   # КШ-Б1, с юга на север
UFH_OUT = ['б2', 'б7-1', 'б7-2', 'б6-1', 'б6-2', 'б4', 'б3']                        # КШ-Б2


def outlet_y(name):
    if name in DIRECT_OUT:
        i = DIRECT_OUT.index(name)
        return CAB_DIR[1] + 0.06 + i * (CAB_DIR[3] - CAB_DIR[1] - 0.12) / (len(DIRECT_OUT) - 1)
    i = UFH_OUT.index(name)
    return CAB_UFH[1] + 0.06 + i * (CAB_UFH[3] - CAB_UFH[1] - 0.12) / (len(UFH_OUT) - 1)


X_OUT = 15.50


def band_route(n, tail):
    """Подводка по пучку: выход шкафа -> подъём в б4 -> запад по рядам -> хвост (список точек)."""
    ys = outlet_y(n)
    pts = [(X_OUT, ys), (XV[n], ys), (XV[n], Y4[n]), (X_JOG + 0.0, Y4[n]), (X_JOG - 0.25, Y6[n])]
    return pts + tail


def routes():
    R = {}

    def b7(n, tail):
        return band_route(n, [(5.05, Y6[n]), (4.95, Y7[n])] + tail)

    R['б2'] = [(X_OUT, outlet_y('б2')), (XV['б2'], outlet_y('б2')), (XV['б2'], Y4['б2']), (11.80, Y4['б2']),
               (11.80, 1.80)]
    R['Р-б2'] = band_route('Р-б2', [(10.98, Y6['Р-б2']), (10.98, 2.05), (10.88, 2.05)])
    R['Кв-б2'] = band_route('Кв-б2', [(10.10, Y6['Кв-б2']), (10.10, 2.62)])
    R['Кв-б1'] = band_route('Кв-б1', [(7.75, Y6['Кв-б1']), (7.75, 2.62)])
    R['Кв-б3'] = b7('Кв-б3', [(4.88, Y7['Кв-б3']), (4.88, 0.62)])
    R['б7-2'] = b7('б7-2', [(4.60, Y7['б7-2']), (4.60, 3.35)])
    R['ТО-Д'] = b7('ТО-Д', [(2.80, Y7['ТО-Д']), (2.80, 2.45)])
    R['б7-1'] = b7('б7-1', [(2.00, Y7['б7-1'])])
    R['б6-1'] = band_route('б6-1', [(7.30, Y6['б6-1']), (7.30, 3.40)])
    R['б6-2'] = band_route('б6-2', [(9.30, Y6['б6-2']), (9.30, 3.40)])
    ys = outlet_y('б4')
    R['б4'] = [(X_OUT, ys), (XV['б4'], ys), (XV['б4'], Y4['б4']), (14.10, Y4['б4']), (14.10, 2.65)]
    ys = outlet_y('б3')
    R['б3'] = [(X_OUT, ys), (14.70, ys), (14.70, 1.50)]
    ys = outlet_y('Пс-б1')
    R['Пс-б1'] = [(X_OUT, ys), (14.74, ys), (14.74, 1.62), (13.60, 1.62)]
    ys = outlet_y('Пс-б2')
    R['Пс-б2'] = [(X_OUT, ys), (15.52, ys), (15.52, 2.80), (15.58, 2.80)]
    ys = outlet_y('Р-б1')
    R['Р-б1'] = [(X_OUT, ys), (15.46, ys), (15.46, 4.40)]
    return R


ROUTES = routes()


def bath_calc():
    """Детерминированный пересчёт ТП бани по СП 60 и догрузка приборов."""
    rooms = {}
    for loop, poly in LOOPS.items():
        rooms.setdefault(LOOP_ROOM[loop], []).append(loop)
    out = dict(loops={}, rooms={}, devices={}, notes=[])
    # 1) требуемая подача смесительного узла: по помещению с наибольшей потребностью при шаге 100 и σ = 5 К
    need = {}
    for no in rooms:
        r = ROOM[no]
        ti = r['ti']
        lim = RDUFH[no]['sp60_limit']
        A = sum(area(LOOPS[k]) for k in rooms[no])
        q_cap = 8.92 * (lim - ti) ** 1.1
        q = min(RDUFH[no]['q'], q_cap)
        need[no] = (A, q, lim)
    tv_need = {}
    for no, (A, q, lim) in need.items():
        ti = ROOM[no]['ti']
        Kmin = k_h(0.10, COVER_R[COVER[no]])
        dth = q / Kmin
        lo, hi = ti + 5.01, 90.0
        for _ in range(100):
            m = (lo + hi) / 2
            if 5 / math.log((m - ti) / (m - 5 - ti)) > dth:
                hi = m
            else:
                lo = m
        tv_need[no] = lo
    tv0 = math.ceil(max(tv_need.values()) * 2) / 2
    out['tv_need'] = {k: round(v, 1) for k, v in tv_need.items()}
    for step in range(0, 17):                    # поднимаем подачу, пока все петли не уложатся в 90 м и 20 кПа
        tv = tv0 + 0.5 * step
        res = _loops(tv, rooms, need)
        if all(l['ok'] for l in res[1].values()):
            break
    out['tv'] = tv
    out['tv_min'] = tv0
    out['rooms'], out['loops'] = res
    return _devices(out)


def _loops(tv, rooms, need):
    rooms_out, loops_out = {}, {}
    Ru, tu = DOWN
    for no, loops in rooms.items():
        r = ROOM[no]
        ti = r['ti']
        A_room = sum(area(LOOPS[k]) for k in loops)
        _, q, lim = need[no]
        R = COVER_R[COVER[no]]
        Ro = 1 / 10.8 + R + SU / LAM_E
        best = None
        for T in (0.30, 0.25, 0.20, 0.15, 0.10):
            Kh = k_h(T, R)
            tr = solve_return(tv, ti, q / Kh)
            if tr is None:
                continue
            sig = tv - tr
            best = (T, Kh, tr, sig)
            if sig >= 5.0 - 0.05:
                break
        T, Kh, tr, sig = best
        sig_d = min(sig, 15.0)
        Q_ufh = q * A_room
        tf = ti + (q / 8.92) ** (1 / 1.1)
        rooms_out[no] = dict(no=no, name=r['name'], ti=ti, Q=r['Q'], lim=lim, q_ep=RDUFH[no]['q'],
                                q=round(q, 1), A=round(A_room, 2), Q_ufh=round(Q_ufh), Q_ufh_rd=RDUFH[no]['Q_ufh'],
                                T_mm=int(round(T * 1000)), t_floor=round(tf, 1), sigma=round(sig_d, 1),
                                sigma_calc=round(sig, 1), t_ret=round(tv - sig_d, 1), cover=COVER[no])
        for k in loops:
            A = area(LOOPS[k])
            L_coil = A / T
            lead = plen(ROUTES[k]) + 1.0
            L_loop = L_coil + 2 * lead
            m = A * q / (sig_d * CW) * (1 + Ro / Ru + (ti - tu) / (q * Ru)) * 3600
            side = math.sqrt(A)
            nb = math.ceil(2 * L_coil / max(side, 0.5)) + 4
            h = pipe_dp(m, UFH_DI * 1000, L_loop, tv - sig_d / 2, zeta=0.3 * nb)
            loops_out[k] = dict(name=k, room=no, A=round(A, 2), T_mm=int(round(T * 1000)), Q=round(q * A),
                                   L_coil=round(L_coil, 1), lead=round(lead, 1), L=round(L_loop, 1),
                                   G=round(m, 1), l_min=round(m / 60 / water(40)[0] * 1000, 2),
                                   v=round(h['v'], 2), dp=round(h['dp'] / 1000, 2),
                                   ok=L_loop <= L_LOOP_MAX and h['dp'] / 1000 <= DP_LOOP_MAX)
    return rooms_out, loops_out


def _devices(out):
    # 3) недостача пола -> приборы
    deficit = {no: max(0, RDUFH[no]['Q_ufh'] - out['rooms'][no]['Q_ufh']) for no in out['rooms']}
    # помещения без ТП по ЭП: б5 — только радиатор
    share = {'Кв-б1': ('б6', 0.5), 'Кв-б2': ('б6', 0.5), 'Кв-б3': ('б7', 1.0), 'Пс-б1': ('б3', 1.0),
             'Пс-б2': ('б4', 1.0), 'Р-б2': ('б2', 1.0), 'Р-б1': (None, 0)}
    for name, (no, sh) in share.items():
        d = RDDEV[name]
        Q = d['Q'] + (deficit.get(no, 0) * sh if no else 0)
        ti = ROOM[d['room']]['ti']
        if name.startswith('Кв'):
            f = (lmtd(TV_RAD, TR_RAD, ti) / DT_N) ** 1.0
            L = d['sel']['L']
            sel = dict(L=L, q_need_n=round(Q / L / f), f=round(f, 3))
            txt = f'КЗТО, внутрипольный с вентилятором 12 В, L={int(round(L * 1000))}'
        elif name.startswith('Р'):
            typ = '33/500' if name == 'Р-б2' else d['sel']['type']
            qn = {'33/500': 2080, '22/500': 1480, '33/300': 1330, '22/300': 975}[typ]
            f = (lmtd(TV_RAD, TR_RAD, ti) / DT_N) ** 1.3
            L = next(x / 10 for x in range(4, 31) if qn * x / 10 * f >= Q)
            sel = dict(type=typ, L=L, Qn=round(qn * L), Q7055=round(qn * L * f))
            txt = f'радиатор {typ}, L={int(round(L * 1000))}'
        else:
            f = (lmtd(TV_RAD, TR_RAD, ti) / DT_N) ** 1.25
            sel = dict(Qn_need=round(Q / f))
            txt = f'полотенцесушитель водяной, ≥{round(Q / f, -1):.0f} Вт (75/65/20)'
        G = Q / (CW * (TV_RAD - TR_RAD)) * 3600
        lead = plen(ROUTES[name]) + 1.5
        h = pipe_dp(G, 12.0, 2 * lead, 62.5, zeta=4.0)
        out['devices'][name] = dict(name=name, room=d['room'], Q=round(Q), Q_rd=d['Q'], sel=sel, txt=txt,
                                    G=round(G, 1), lead=round(lead, 1), pipe='16×2,0', v=round(h['v'], 2),
                                    dp=round(h['dp'] / 1000, 2), l_min=round(G / 60 / water(62)[0] * 1000, 2))
    # ТО-Д джакузи, загрузка Б2, Ecoflex
    Q_tod = CALC['P_jac'] * 1000
    G_tod = Q_tod / (CW * 20) * 3600
    lead = plen(ROUTES['ТО-Д']) + 1.5
    h = pipe_dp(G_tod, 23.2, 2 * lead, 60, zeta=6.0)
    out['tod'] = dict(Q=round(Q_tod), G=round(G_tod), pipe='32×4,4', lead=round(lead, 1), v=round(h['v'], 2),
                      dp=round(h['dp'] / 1000, 1))
    Q_b2 = CALC['P_coil_bath'] * 1000
    G_b2 = Q_b2 / (CW * 15) * 3600
    out['b2'] = dict(Q=round(Q_b2), G=round(G_b2), pipe='32×4,4')
    # смесительный насос КШ-Б2
    G_ufh = sum(l['G'] for l in out['loops'].values())
    dp_max = max(l['dp'] + (l['G'] / 1000 / 1.5) ** 2 * 100 for l in out['loops'].values())
    H = dp_max + 5.0
    out['mixpump'] = dict(G=round(G_ufh, 1), m3h=round(G_ufh / 1000, 3), H_kPa=round(H, 1), H_m=round(H / 9.81, 2))
    for l in out['loops'].values():
        l['dp_bal'] = round(dp_max - (l['dp'] + (l['G'] / 1000 / 1.5) ** 2 * 100), 2)
    Q_dir = sum(d['Q'] for d in out['devices'].values())
    out['Q_direct'] = Q_dir
    out['Q_ufh'] = sum(r['Q_ufh'] for r in out['rooms'].values())
    out['Q_heat'] = Q_dir + out['Q_ufh']
    out['deficit'] = deficit
    return out


# =========================================================================== лист
def build():
    C = bath_calc()
    doc = new_doc()
    blk = add_underlay(doc, UNDER['bath'], 'АР_Баня_план')
    msp = doc.modelspace()
    insert_underlay(msp, blk)
    p = DPlan(doc, k=K)
    axes(p, BATH_AX, y_bub=-1.65, x_bub=-1.20, r=3.0)

    def pair(pts, ufh=False, gap=0.022):
        a = offset_poly(pts, gap)
        b = offset_poly(pts, -gap)
        p.pl(a, 'ОВ_Т11' if ufh else 'ОВ_Т1', lw=25)
        p.pl(b, 'ОВ_Т21' if ufh else 'ОВ_Т2', lw=25, ltype='ОВ_ПУНКТ')

    # --- шкафы, Б2, ТО-Д
    for (x0, y0, x1, y1), nm in ((CAB_DIR, 'КШ-Б1'), (CAB_UFH, 'КШ-Б2')):
        p.rect(x0, y0, x1, y1, 'ОВ_КШ', fill=2)
    x, y, r = B2
    p.circle(x, y, r, 'ОВ_оборуд')
    p.t(x, y, 'Б2', 2.0, 'center', 'ОВ_марки')
    p.rect(*TOD_POS, 'ОВ_оборуд')
    p.t((TOD_POS[0] + TOD_POS[2]) / 2, (TOD_POS[1] + TOD_POS[3]) / 2, 'ТО', 1.6, 'center', 'ОВ_марки')

    # --- приборы
    for name, (x0, y0, x1, y1) in DEVPOS.items():
        if name.startswith('Кв'):
            p.rect(x0, y0, x1, y1, 'ОВ_приборы', fill=1)
            p.rect(x0 + 0.03, y0 + 0.03, x1 - 0.03, y1 - 0.03, 'ОВ_приборы')
        elif name.startswith('Р'):
            p.rect(x0, y0, x1, y1, 'ОВ_приборы', hatch=('ANSI31', 3.0, 45, 1))
        else:
            p.rect(x0, y0, x1, y1, 'ОВ_приборы', hatch=('ANSI37', 2.0, 0, 1))

    # --- зоны ТП (петли)
    for k, poly in LOOPS.items():
        p.ufh_zone(poly)

    # --- подводки
    for n, pts in ROUTES.items():
        ufh = n in LOOPS
        pair(pts, ufh=ufh)
    # загрузка Б2 (от вводной группы КШ-Б1 по стене) и ввод Ecoflex
    pair([(15.62, 0.95), (15.62, 1.78), (15.25, 1.90)])
    # ввод Ecoflex: под фундаментом с юга, подъём в КШ-Б1 через плиту пола
    p.pl([(15.40, -1.05), (15.40, 0.40)], 'ОВ_Т1', lw=70, color=6)
    p.circle(15.40, 0.40, 0.09, 'ОВ_Т1', color=6)

    # --- естественная вентиляция: открывающиеся створки окон, парная по паспорту печи
    def vent_mark(x, y, txt, ang=0):
        p.circle(x, y, 0, 'ОВ_В', r_paper=1.6)
        p.t(x, y, txt, 2.0, 'center', 'ОВ_В')
    for x, y in ((0.12, 2.90), (15.85, 2.80), (15.85, 4.95), (2.80, 6.50)):
        vent_mark(x, y, 'В')
    # рекомендуемые вытяжные вентиляторы (по решению Заказчика) — помывочная и с/у
    for x, y in ((0.90, 6.05), (14.20, 1.40)):
        p.circle(x, y, 0.13, 'ОВ_В', lw=18)
        p.line(x - 0.09, y - 0.09, x + 0.09, y + 0.09, 'ОВ_В')
        p.line(x - 0.09, y + 0.09, x + 0.09, y - 0.09, 'ОВ_В')
    # парная: приток у печи, вытяжка под потолком с противоположной стороны (по паспорту печи)
    p.arrow(5.05, 4.55, 4.75, 4.30, 'ОВ_П', size=2.0)
    p.arrow(2.45, 6.05, 2.25, 6.30, 'ОВ_В', size=2.0)

    # --- марки и выноски (короткие; подробности — в таблице подключений)
    L = C['loops']
    D = C['devices']

    def lab(x, y, txt, at, extra=None, anchor='left', h=2.0):
        p.label(x, y, txt, h, anchor, at=at, lines=extra)

    lab(5.70, -0.45, f'Кв-б1, Кв-б2  L={int(D["Кв-б1"]["sel"]["L"] * 1000)}', (6.70, 2.47))
    lab(0.30, -0.45, f'Кв-б3  L={int(D["Кв-б3"]["sel"]["L"] * 1000)}', (3.75, 0.47))
    lab(16.25, 5.95, f'Р-б1  {D["Р-б1"]["sel"]["type"]}', (15.60, 4.95),
        extra=f'L={int(D["Р-б1"]["sel"]["L"] * 1000)}')
    lab(9.60, 1.35, f'Р-б2  {D["Р-б2"]["sel"]["type"]}  L={int(D["Р-б2"]["sel"]["L"] * 1000)}', (10.80, 2.05),
        anchor='right')
    lab(16.25, 3.55, 'Пс-б2', (15.63, 2.80))
    lab(16.25, 2.55, 'Б2 (200 л, Ø520)', (15.20, 2.10))
    lab(16.25, 1.65, 'КШ-Б2 (ТП)', (15.64, 1.32))
    lab(16.25, 0.85, 'КШ-Б1 (прямой)', (15.64, 0.58))
    lab(16.25, -0.45, 'Ввод Т1, Т2', (15.40, -0.70), extra='Ecoflex, уз. 1 л. 13')
    lab(0.30, 1.20, 'ТО-Д 20 кВт', (2.80, 2.25))
    # петли
    loop_lab = {'б7-1': (0.45, 4.45), 'б7-2': (3.05, 2.80), 'б6-1': (5.75, 5.25), 'б6-2': (7.75, 5.25),
                'б2': (10.85, 1.25), 'б3': (12.85, 1.25), 'б4': (12.85, 3.00)}
    for k, (x, y) in loop_lab.items():
        l = L[k]
        p.t(x, y + 0.10, f'{k}: шаг {l["T_mm"]}', 1.8, 'left', 'ОВ_ТП')
        p.t(x, y - 0.12, f'L={n0(l["L"])} м, {l["Q"]} Вт', 1.8, 'left', 'ОВ_ТП')

    # --- ярлыки помещений
    def tg(no, x, y, extra):
        r = ROOM[no]
        p.tag(x, y, [f'{no}  {r["name"]}  +{r["ti"]} °С  {fmt_num(r["Q"] / 1000, 2)} кВт'] + extra, h=2.0)

    R_ = C['rooms']
    tg('б7', 0.30, 5.70, [f'ТП {R_["б7"]["Q_ufh"]} Вт (≤31 °С), Кв-б3'])
    tg('б6', 5.70, 6.25, [f'ТП {R_["б6"]["Q_ufh"]} Вт (≤26 °С), Кв-б1, Кв-б2'])
    tg('б2', 10.65, 3.85, [f'ТП {R_["б2"]["Q_ufh"]} Вт, Р-б2'])
    tg('б5', 10.65, 6.25, ['Р-б1'])
    tg('б4', 12.75, 3.62, [f'ТП {R_["б4"]["Q_ufh"]} Вт, Пс-б2'])
    p.label(11.30, -0.45, f'б3  С/у  +25 °С  {fmt_num(ROOM["б3"]["Q"] / 1000, 2)} кВт: ТП {R_["б3"]["Q_ufh"]} Вт + Пс-б1',
            1.9, at=(13.30, 1.63))
    p.label(3.00, 7.10, 'б8 Парная — печь-каменка, водяное отопление не предусмотрено', 2.0, at=(3.6, 5.6))

    # --- лист
    sh = RDSheet(doc, 'Лист', SHEET_LIST[SHEET_NO], SHEET_NO, SHEETS_TOTAL)
    # окно модели: x -1.55…17.85 (19,4 м), y -1.95…7.35 (9,3 м) -> 388×186 мм при 1:50
    sh.viewport(216, 192, 388, 186, 8.15, 2.70, k=K)
    sh.title(216, 289.5, 'Баня. План отопления и вентиляции. М 1:50')

    rows = [['Шкаф', 'Вых.', 'Потребитель', 'Пом.', 'Q, Вт', 'G, кг/ч', 'Труба', 'L, м', 'Настр., л/мин']]
    i = 1
    for n in ['Р-б1', 'Р-б2', 'Кв-б1', 'Кв-б2', 'Кв-б3', 'Пс-б1', 'Пс-б2']:
        d = D[n]
        s_ = d['sel']
        if n.startswith('Кв'):
            t = f'{n} — КЗТО, внутрипольный с вент. 12 В, L={int(s_["L"] * 1000)}, ≥{s_["q_need_n"]} Вт/м*'
            if n == 'Кв-б3':
                t += ', влагозащ.'
        elif n.startswith('Р'):
            t = f'{n} — радиатор стальной панельный {s_["type"]}, L={int(s_["L"] * 1000)}, нижн. подкл.'
        else:
            t = f'{n} — полотенцесушитель водяной, ≥{s_["Qn_need"]} Вт*'
        rows.append(['КШ-Б1', f'В{i}', t, d['room'], str(d['Q']), n0(d['G']), d['pipe'], fmt_num(d['lead'], 1),
                     fmt_num(d['l_min'], 2)])
        i += 1
    t = C['tod']
    rows.append(['КШ-Б1', 'ввод', 'ТО-Д — теплообменник джакузи, линия с зональным клапаном', 'б7', str(t['Q']),
                 str(t['G']), t['pipe'], fmt_num(t['lead'], 1), '—'])
    rows.append(['КШ-Б1', 'ввод', 'Б2 — загрузка змеевика, 3-ходовой клапан (приоритет)', 'б3', str(C['b2']['Q']),
                 str(C['b2']['G']), C['b2']['pipe'], '1,5', '—'])
    j = 1
    for k in ['б7-1', 'б7-2', 'б6-1', 'б6-2', 'б2', 'б3', 'б4']:
        l = L[k]
        rows.append(['КШ-Б2', f'ТП{j}', f'петля {k}: PE-Xa 16×2,0, шаг {l["T_mm"]}, {fmt_num(l["A"], 1)} м²', l['room'],
                     str(l['Q']), n0(l['G']), '16×2,0', fmt_num(l['L'], 1), fmt_num(l['l_min'], 2)])
        j += 1
    widths = [12, 9, 82, 9, 12, 12, 14, 10, 15]
    sh.s.text('Подключения к коллекторным шкафам КШ-Б1, КШ-Б2', 22 + sum(widths) / 2, 96.5, h=2.5, align='center')
    sh.table(22, 94, widths, rows, row_h=4.6, head_h=6, h=1.8,
             aligns=['center', 'center', 'left', 'center', 'center', 'center', 'center', 'center', 'center'])
    sh.s.text('* при 75/65/20 °С; подбор — по каталогу производителя', 22, 9.0, h=1.8, align='left')
    mp = C['mixpump']
    sh.notes(236, 96.5, 177, [
        f'Подложка — АР «Баня. Планировочное решение» (Revit, 19.10.2026), отм. чистого пола 0,000. Т1/Т2 — 70/55 °С; '
        f'ТП — от смесительного узла КШ-Б2: {fmt_num(C["tv"], 1)} °С, насос G={fmt_num(mp["m3h"], 2)} м³/ч, '
        f'H={fmt_num(mp["H_m"], 1)} м.',
        'Температура поверхности пола — по СП 60: не выше 26 °С (комната отдыха б6) и 31 °С (санузел, помывочная, '
        'прихожая, раздевалка); недостающее тепло отдают конвекторы и полотенцесушители (табл. на л. 13). '
        'Покрытия пола приняты: доска — б6, плитка — остальные (экспликации полов нет — уточнить).',
        'КШ-Б1, КШ-Б2 — встроенные ШРВ-3 (≈750 мм) в восточной стене с/у, по АР и решению Заказчика; КШ-Б2 — '
        'увеличенной высоты, если узел с коллектором 7 вых. не помещается в один ярус. Подводки — PE-Xa 16×2,0 в '
        'гофре с теплоизоляцией 6 мм на участках вне своих петель; под выгородкой Б2 — без соединений.',
        'Вентиляция — естественная через открывающиеся створки окон («В»), по решению Заказчика. Рекомендуются '
        '(по решению Заказчика) вытяжные вентиляторы: помывочная — 150–200 м³/ч с гигростатом, с/у — 50–100 м³/ч. '
        'Парная — приток у печи, вытяжка под потолком с противоположной стороны, по паспорту печи.',
    ], h=1.9)
    return doc, C


if __name__ == '__main__':
    doc, C = build()
    out = os.path.join(OUT, 'ov_bath.dxf')
    print(save_and_pdf(doc, out))
    json.dump(C, open(os.path.join(OUT, 'ov_bath_calc.json'), 'w'), ensure_ascii=False, indent=1)
