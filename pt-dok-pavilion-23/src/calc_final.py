"""Итоговый расчёт: диктующие площади, ВПВ (кольцо), подбор насосов, диафрагмы ПК."""
import json, math, os
from collections import defaultdict
import hydro
from hydro import M, PIPES, LOCAL, K_SPR, build_tree, size_section, cell_areas, dictating, length_m, key
from geom import GROUPS
HERE = os.path.dirname(os.path.abspath(__file__))
rep = json.load(open(os.path.join(HERE, 'hydro_report.json')))
MS = json.load(open(os.path.join(HERE, 'model_sized.json')))

LV = M['levels']
H_GUAR = 20.0          # ТУ от 08.10.2026: остаточное давление не менее 0,20 МПа при 40 л/с на вводе 23.1 (граница здания)
Q_TU = 41.0            # 40 л/с по ТУ, увеличение до 41 л/с согласовано заказчиком 10.10.2026
P_IN_MAX = 0.60        # максимальное давление в точке 23.1 (заказчик, 10.10.2026), МПа
P_PRV = 0.20           # уставка регуляторов давления «после себя» на вводах, МПа
KV_PRV = 350.0         # Kv регулятора Ду150 в полностью открытом положении, м³/ч
P_PK_MAX = 0.40        # предельное давление у клапана ПК при работе
P_HYDRO_MAX = 0.90     # предельное гидростатическое давление у нижнего ПК
Z_WELL = -1.900        # ось вводов на границе здания (наружная грань стены подвала по оси 1), точка ТУ
Z_PUMP = -1.750        # ось насосов и коллекторов (насосная в подвале, пол −2,200)
Q_VPV = 2 * 5.2        # 2 струи по 5,2 л/с
P_PK = 0.20            # требуемое давление у ПК Ду65 (ствол 19 мм, рукав 20 м, 5,2 л/с), МПа
XI_UU = 0.0011         # потери в УУ Ду150: ΔH = ξ·Q², м/(л/с)²
L_INPUT = 6.0          # ввод от стены до всасывающего коллектора, м
H_INPUT_LOC = 0.5      # затвор, сетчатый фильтр, переходы на вводе, м

def dh(Q, dn, L):
    return LOCAL * Q * Q * L / PIPES[dn][2]

def h_prv(Q):
    """потери в открытом регуляторе давления, м: ΔP = (Q/Kv)², бар"""
    return (Q * 3.6 / KV_PRV) ** 2 * 10.2

out = {}
for sec in (1, 2):
    T = build_tree(sec)
    dn = {int(i): p.get('dn') for i, p in enumerate(MS['pipes']) if p['sec'] == sec and p['sys'] != 'В2'}
    dn = {i: d for i, d in dn.items() if d}
    areas = cell_areas(sec)
    cases = rep[str(sec)]['cases']
    worst = max(cases, key=lambda c: c['p_uu'])
    open_spr = set()
    inv = {j: v for v, j in T['spr'].items()}
    for j in worst['sel']:
        open_spr.add(inv[j])
    p, q, P, Q = dictating(T, dn, open_spr, worst['qreq'])
    # путь от наиболее удалённого (наименьшее давление) оросителя к УУ
    vmin = min(open_spr, key=lambda v: P[v])
    path = []
    v = vmin
    flow = defaultdict(float)
    need = set()
    for w in open_spr:
        x = w
        while x is not None:
            need.add(x); x = T['parent'][x][0]
    for w in reversed(T['order']):
        if w not in need:
            continue
        if w in open_spr:
            flow[w] += q[w]
        u, i = T['parent'][w]
        if u is not None:
            flow[u] += flow[w]
    while T['parent'][v][0] is not None:
        u, i = T['parent'][v]
        pp = M['pipes'][i]
        L = length_m(pp); d = dn[i]; Qs = flow[v]
        vel = Qs / 1000 / (math.pi / 4 * (PIPES[d][1] / 1000) ** 2)
        path.append(dict(frm=list(u), to=list(v), dn=d, L=round(L, 2), Q=round(Qs, 3), v=round(vel, 2),
                         dh=round(dh(Qs, d, L), 3), P_to=round(P[v], 4), role=pp['role']))
        v = u
    path.reverse()
    # доп. потери в питающих при расходе 30 л/с (табл. 6.1, гр. 2) вместо расчётного
    Qd = max(Q, GROUPS[2]['Qmin'])
    extra = 0.0
    for sgm in path:
        if sgm['role'] in ('питающий', 'стояк'):
            extra += dh(Qd, sgm['dn'], sgm['L']) - sgm['dh']
    spr_rows = []
    for w in sorted(open_spr, key=lambda w: P[w]):
        j = T['spr'][w]; s = M['sprinklers'][j]
        spr_rows.append(dict(room=s['room'], x=s['x'], y=s['y'], z=s['z'], P=round(P[w], 4), q=round(q[w], 3), A=round(areas[j], 2)))
    out[sec] = dict(worst=worst['name'], grp=worst['grp'], n=worst['n'], area=worst['area'], Q=round(Q, 2), Qd=round(Qd, 2),
                    p_uu=round(p, 4), extra_m=round(extra, 2), path=path, sprinklers=spr_rows, cases=cases,
                    qreq=worst['qreq'], pmin=round(P[vmin], 4))

# ------------------------------------------------------------- ВПВ: кольцо (два пути)
def vpv_paths(x_tap, ring_tap):
    """Возвращает длины и Ду двух путей от коллектора насосной до точки врезки стояка в кольцо."""
    # путь A: коллектор → стояк x=3500 (−0,7) → кольцо 1 на восток до x_tap (или через восток в кольцо 2)
    zr, y1, y2 = LV['ZB_RING'], LV['Y_RING1'], LV['Y_RING2']
    xt, x0, x1 = LV['X_VPV_TAP'], LV['X_R0'], LV['X_R1']
    LA_hdr = (xt - LV['X_HDR']) / 1000 + (zr - LV['Z_HDR']) + (LV['Y_HDR'] - y1) / 1000   # коллектор → кольцо 1
    LB_hdr = LA_hdr + (xt - x0) / 1000 + 2 * (2.6 - zr) + (y1 - 18600) / 1000 + 0.8 + 1.8 + (16800 - y2) / 1000
    L_e = 2 * (2.6 - zr) + (y1 - y2) / 1000          # восточная перемычка
    if ring_tap == 1:
        A = LA_hdr + (x_tap - xt) / 1000
        B = LB_hdr + (x1 - 4700) / 1000 + L_e + (x1 - x_tap) / 1000
    else:
        A = LA_hdr + (x1 - xt) / 1000 + L_e + (x1 - x_tap) / 1000
        B = LB_hdr + (x_tap - 4700) / 1000
    return A, B

def split(Q, LA, LB, dn=100):
    # равные потери: Q_A²·L_A = Q_B²·L_B
    ra = 1 / math.sqrt(LA); rb = 1 / math.sqrt(LB)
    QA = Q * ra / (ra + rb); QB = Q - QA
    return QA, QB, dh(QA, dn, LA)

vpv = []
for k in MS['pk']:
    # врезка стояка в кольцо: x стояка, кольцо по y
    ring = 1 if k['y'] > 20000 else 2
    LA, LB = vpv_paths(k['x'], ring)
    QA, QB, h_ring = split(Q_VPV, LA, LB)
    # стояк Ду80: от кольца (−0,7) до клапана; отвод от кольца 2,5–5,4 м
    z_v = k['z']
    L_riser = abs(z_v - LV['ZB_RING']) + abs((LV['Y_RING1'] if ring == 1 else LV['Y_RING2']) - k['y']) / 1000 + 0.6
    h_riser = dh(Q_VPV, 80, L_riser)
    H_hdr = P_PK * 100 + h_ring + h_riser + (z_v - LV['Z_HDR'])     # напор на напорном коллекторе, м
    vpv.append(dict(name=k['name'], floor=k['floor'], x=k['x'], y=k['y'], z=z_v, LA=round(LA, 1), LB=round(LB, 1),
                    QA=round(QA, 2), QB=round(QB, 2), h_ring=round(h_ring, 2), h_riser=round(h_riser, 2), H_hdr=round(H_hdr, 2)))
vpv_d = max(vpv, key=lambda r: r['H_hdr'])

# ------------------------------------------------------------- насосная установка
Q_aup = max(out[1]['Qd'], out[2]['Qd'])
Q_pump = Q_aup + Q_VPV
H_aup = {}
for sec in (1, 2):
    o = out[sec]
    h_uu = XI_UU * o['Qd'] ** 2
    # выход УУ −0,600; ось насосов −1,750; потери в коллекторах и арматуре обвязки 1,5 м при Q_pump
    H_aup[sec] = o['p_uu'] * 100 + o['extra_m'] + h_uu + (LV['Z_UU_OUT'] - Z_PUMP) + 1.5
H_vpv = vpv_d['H_hdr'] + (LV['Z_HDR'] - Z_PUMP) + 1.0
H_out = max(max(H_aup.values()), H_vpv)
h_input = dh(Q_pump, 150, L_INPUT) + H_INPUT_LOC     # весь расход по одному вводу (второй — в ремонте)
h_reg = h_prv(Q_pump)                              # регулятор открыт полностью при давлении на вводе 0,20 МПа
H_in = H_GUAR - h_input - h_reg - (Z_PUMP - Z_WELL)
H_pump = H_out - H_in
N_kw = 9.81 * Q_pump / 1000 * H_pump / 0.70
H_sel = math.ceil(H_pump + 2)
H0 = 1.15 * H_sel                                  # напор насоса при нулевой подаче
def H_curve(Q):
    return H0 - (H0 - H_sel) * (Q / Q_pump) ** 2
def H_in_at(Q):
    return H_GUAR - dh(Q, 150, L_INPUT) - H_INPUT_LOC * (Q / Q_pump) ** 2 - h_prv(Q) - (Z_PUMP - Z_WELL)
# гидростатика: регулятор держит за собой не более 0,20 МПа, насос работает на закрытую задвижку
P_shut = P_PRV * 100 - (Z_PUMP - Z_WELL) + H0
# без регуляторов при 0,60 МПа на вводе — для обоснования
P_shut_noprv = P_IN_MAX * 100 - (Z_PUMP - Z_WELL) + H0
H_act = H_in + H_sel                               # напор за насосной на расчётном режиме (АУПТ + ВПВ)
H_vpv_only = H_in_at(Q_VPV) + H_curve(Q_VPV) - 1.0 * (Q_VPV / Q_pump) ** 2   # работают только 2 струи ВПВ
D = 0.065; V_PK = 5.2e-3 / (math.pi / 4 * D * D)
def h_dia(dmm):
    # ΔH = ζ·v²/2g, ζ диафрагмы (Идельчик) ≈ (1/(μ·m) − 1)², m=(d/D)², μ≈0,62
    m = (dmm / 1000 / D) ** 2
    return (1 / (0.62 * m) - 1) ** 2 * V_PK * V_PK / 19.62
dia = []
for r in vpv:
    lift = r['z'] - Z_PUMP
    p_dyn = (H_act - lift - r['h_ring'] - r['h_riser']) / 100
    p_vpv = (H_vpv_only - lift - r['h_ring'] - r['h_riser']) / 100
    p_st = (P_shut - lift) / 100
    p_hi, p_lo = max(p_dyn, p_vpv), min(p_dyn, p_vpv)
    need = p_hi > P_PK_MAX
    d_or = h_d = None
    if need:
        # диафрагма гасит избыток над 0,40 МПа с запасом 0,01 МПа; на расчётном режиме у клапана остаётся не менее 0,20 МПа
        dH_min = (p_hi - P_PK_MAX) * 100 + 1.0
        d_or = next(dmm for dmm in range(64, 9, -1) if h_dia(dmm) >= dH_min)
        h_d = h_dia(d_or)
        assert p_lo - h_d / 100 >= P_PK, (r['name'], p_lo, h_d)
    dia.append(dict(name=r['name'], floor=r['floor'], z=r['z'], p_dyn=round(p_dyn, 3), p_vpv=round(p_vpv, 3),
                    p_static=round(p_st, 3), p_static_noprv=round((P_shut_noprv - lift) / 100, 3),
                    diaphragm=need, d_mm=d_or, h_dia=round(h_d, 2) if h_d else None,
                    p_after=round((p_hi * 100 - h_d) / 100, 3) if h_d else round(p_hi, 3)))
# на этаже — один диаметр отверстия (наименьший из требуемых), с проверкой каждого ПК на обоих режимах
for fl in sorted({d['floor'] for d in dia if d['diaphragm']}):
    grp = [d for d in dia if d['floor'] == fl and d['diaphragm']]
    d_fl = min(d['d_mm'] for d in grp)
    for d in grp:
        h_d = h_dia(d_fl)
        p_hi, p_lo = max(d['p_dyn'], d['p_vpv']), min(d['p_dyn'], d['p_vpv'])
        assert p_lo - h_d / 100 >= P_PK and p_hi - h_d / 100 <= P_PK_MAX, (d['name'], d_fl)
        d.update(d_mm=d_fl, h_dia=round(h_d, 2), p_after=round(p_hi - h_d / 100, 3), p_after_lo=round(p_lo - h_d / 100, 3))
assert max(d['p_static'] for d in dia) <= P_HYDRO_MAX
# подбор оборудования насосной
MOTORS = [5.5, 7.5, 11, 15, 18.5, 22, 30, 37, 45]
N_motor = min(m for m in MOTORS if m >= N_kw * 1.15)
I_nom = round(N_motor * 1000 / (math.sqrt(3) * 380 * 0.88 * 0.91))
QF = min(a for a in (10, 16, 20, 25, 32, 40, 50, 63, 80, 100) if a >= 1.25 * I_nom)
SEC_MM = min(sq for sq, i in ((2.5, 25), (4, 32), (6, 42), (10, 55), (16, 75), (25, 95)) if i >= 1.25 * I_nom)
H_jockey = 5 * math.ceil((H_out + 5 - H_in) / 5) + 5
pump = dict(Q_m3h=round(Q_pump * 3.6), H=H_sel, N=N_motor, I_nom=I_nom, I_start=7 * I_nom, QF=QF, sec=SEC_MM,
            jockey=dict(Q_m3h=1.5, H=H_jockey, N=0.55, I_nom=1.4),
            drain=dict(Q_m3h=10, H=10, N=0.75, I_nom=1.9, n=2),
            p_jockey_on=round((H_out + 3) / 100, 2), p_jockey_off=round((H_out + 8) / 100, 2), p_main_start=round((H_out - 2) / 100, 2))
res = dict(sections=out, pump=pump, vpv=vpv, vpv_dict=vpv_d, Q_aup=round(Q_aup, 2), Q_vpv=Q_VPV, Q_pump=round(Q_pump, 2),
           H_aup={k: round(v, 2) for k, v in H_aup.items()}, H_vpv=round(H_vpv, 2), H_out=round(H_out, 2),
           h_input=round(h_input, 2), h_prv=round(h_reg, 2), H_in=round(H_in, 2), H_pump=round(H_pump, 2), N_kw=round(N_kw, 1),
           H_guar=H_GUAR, Q_tu=Q_TU, over_tu=round(Q_pump - Q_TU, 2), P_shut=round(P_shut, 2), diaphragms=dia,
           P_in_max=P_IN_MAX, P_prv=P_PRV, Kv_prv=KV_PRV, H0=round(H0, 2), H_act=round(H_act, 2), H_vpv_only=round(H_vpv_only, 2),
           P_shut_noprv=round(P_shut_noprv, 2),
           z_pump=Z_PUMP, z_in=Z_WELL, L_input=L_INPUT,
           volume_m3=round(Q_pump * 3600 / 1000, 1))
json.dump(res, open(os.path.join(HERE, 'calc_final.json'), 'w'), ensure_ascii=False, indent=1)
for sec in (1, 2):
    o = out[sec]
    print(f"Секция {sec}: диктующая «{o['worst']}» гр.{o['grp']} n={o['n']} S={o['area']} Q={o['Q']} (расч. {o['Qd']}) "
          f"P(УУ)={o['p_uu']} доп.потери={o['extra_m']} м, Pmin оросителя={o['pmin']}")
print('ВПВ диктующий', vpv_d)
print(f"Насосы: Q={Q_pump:.1f} л/с ({Q_pump*3.6:.0f} м³/ч), H вых={H_out:.1f} м, H вх={H_in:.1f} м, H насоса={H_pump:.1f} м, N≈{N_kw:.1f} кВт")
print('H по секциям', H_aup, 'H ВПВ', round(H_vpv, 2))
print('Подбор:', pump, 'превышение ТУ, л/с:', round(Q_pump - Q_TU, 2))
print(f"Регулятор: h={h_reg:.2f} м; H0={H0:.1f} м; напор за насосной: расч. {H_act:.1f} м, только ВПВ {H_vpv_only:.1f} м; "
      f"гидростатика {P_shut:.1f} м (без регуляторов {P_shut_noprv:.1f} м)")
print('Диафрагмы:', [(d['name'], d['p_dyn'], d['p_vpv'], d['d_mm'], d['p_after']) for d in dia if d['diaphragm']])
print('Без диафрагм:', [(d['name'], d['p_dyn'], d['p_vpv']) for d in dia if not d['diaphragm']])
