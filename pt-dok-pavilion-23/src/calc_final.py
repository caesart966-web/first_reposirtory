"""Итоговый расчёт: диктующие площади, ВПВ (кольцо), подбор насосов, диафрагмы ПК."""
import json, math, os
from collections import defaultdict
import hydro
from hydro import M, PIPES, LOCAL, K_SPR, build_tree, size_section, cell_areas, dictating, length_m, key
from geom import GROUPS
HERE = os.path.dirname(os.path.abspath(__file__))
rep = json.load(open(os.path.join(HERE, 'hydro_report.json')))
MS = json.load(open(os.path.join(HERE, 'model_sized.json')))

H_GUAR = 10.0          # гарантированный напор в сети В2 у колодца В2-7, м (ПРИНЯТО до получения ТУ)
Z_WELL = -2.0          # ось трубы в колодце (≈1,4 м ниже планировки −0,57)
Z_PUMP = 0.50          # ось насосов
Q_VPV = 2 * 5.2        # 2 струи по 5,2 л/с
P_PK = 0.20            # требуемое давление у ПК Ду65 (ствол 19 мм, рукав 20 м, 5,2 л/с), МПа
XI_UU = 0.0011         # потери в УУ Ду150: ΔH = ξ·Q², м/(л/с)²
L_INPUT = 40.0         # длина ввода от колодца до насосов, м (до получения генплана НВК)

def dh(Q, dn, L):
    return LOCAL * Q * Q * L / PIPES[dn][2]

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
    LA_hdr = 1.0 + 1.7          # от коллектора (+1,0) вниз до кольца
    LB_hdr = 1.6 + 4.4 + 1.2 + 1.8 + 3.3 + 2.0  # перемычка через тамбур 92 до кольца 2
    L_e = 2.2 + 3.3 + 6.0 + 3.3 + 2.2          # восточная перемычка
    if ring_tap == 1:
        A = LA_hdr + (x_tap - 3500) / 1000
        B = LB_hdr + (97400 - 4700) / 1000 + L_e + (97400 - x_tap) / 1000
    else:
        A = LA_hdr + (97400 - 3500) / 1000 + L_e + (97400 - x_tap) / 1000
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
    L_riser = abs(z_v - (-0.7)) + abs((25200 if ring == 1 else 14800) - k['y']) / 1000 + 0.6
    h_riser = dh(Q_VPV, 80, L_riser)
    H_hdr = P_PK * 100 + h_ring + h_riser + (z_v - 1.0)     # напор на коллекторе (+1,0), м
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
    # выход УУ +1,20; коллектор насосов +1,00; потери в коллекторе и арматуре обвязки 1,5 м при Q_pump
    H_aup[sec] = o['p_uu'] * 100 + o['extra_m'] + h_uu + (1.20 - Z_PUMP) + 1.5
H_vpv = vpv_d['H_hdr'] + (1.0 - Z_PUMP) + 1.0
H_out = max(max(H_aup.values()), H_vpv)
h_input = dh(Q_pump, 150, L_INPUT)          # весь расход по одному вводу (второй — в ремонте)
H_in = H_GUAR - h_input - (Z_PUMP - Z_WELL)
H_pump = H_out - H_in
N_kw = 9.81 * Q_pump / 1000 * H_pump / 0.70
# давление у ПК при работе насосов на расчётном режиме и при нулевой подаче (запирание ~1,15·H)
P_shut = (H_in + 1.15 * H_pump)
dia = []
for r in vpv:
    p_dyn = (H_out - (r['z'] - Z_PUMP) - r['h_ring'] - r['h_riser']) / 100
    p_st = (P_shut - (r['z'] - Z_PUMP)) / 100
    need = p_dyn > 0.40
    # диаметр отверстия диафрагмы: гасит избыток (p_dyn − 0,20) при q=5,2 л/с на ПК Ду65
    d_or = None
    if need:
        dH = (p_dyn - P_PK) * 100
        # ΔH = ζ·v²/2g, ζ диафрагмы (Идельчик) ≈ (1/(μ·m) − 1)², m=(d/D)², μ≈0,62
        D = 0.065; best = None
        for dmm in range(10, 66):
            m = (dmm / 1000 / D) ** 2
            zeta = (1 / (0.62 * m) - 1) ** 2
            v = 5.2e-3 / (math.pi / 4 * D * D)
            h = zeta * v * v / 19.62
            if h <= dH:
                best = dmm; break
        d_or = best
    dia.append(dict(name=r['name'], floor=r['floor'], p_dyn=round(p_dyn, 3), p_static=round(p_st, 3), diaphragm=need, d_mm=d_or))
res = dict(sections=out, vpv=vpv, vpv_dict=vpv_d, Q_aup=round(Q_aup, 2), Q_vpv=Q_VPV, Q_pump=round(Q_pump, 2),
           H_aup={k: round(v, 2) for k, v in H_aup.items()}, H_vpv=round(H_vpv, 2), H_out=round(H_out, 2),
           h_input=round(h_input, 2), H_in=round(H_in, 2), H_pump=round(H_pump, 2), N_kw=round(N_kw, 1),
           H_guar=H_GUAR, P_shut=round(P_shut, 2), diaphragms=dia,
           volume_m3=round(Q_pump * 3600 / 1000, 1))
json.dump(res, open(os.path.join(HERE, 'calc_final.json'), 'w'), ensure_ascii=False, indent=1)
for sec in (1, 2):
    o = out[sec]
    print(f"Секция {sec}: диктующая «{o['worst']}» гр.{o['grp']} n={o['n']} S={o['area']} Q={o['Q']} (расч. {o['Qd']}) "
          f"P(УУ)={o['p_uu']} доп.потери={o['extra_m']} м, Pmin оросителя={o['pmin']}")
print('ВПВ диктующий', vpv_d)
print(f"Насосы: Q={Q_pump:.1f} л/с ({Q_pump*3.6:.0f} м³/ч), H вых={H_out:.1f} м, H вх={H_in:.1f} м, H насоса={H_pump:.1f} м, N≈{N_kw:.1f} кВт")
print('H по секциям', H_aup, 'H ВПВ', round(H_vpv, 2))
print('Диафрагмы:', [(d['name'], d['p_dyn'], d['d_mm']) for d in dia if d['diaphragm']][:40])
print('Без диафрагм:', [(d['name'], d['p_dyn']) for d in dia if not d['diaphragm']])
