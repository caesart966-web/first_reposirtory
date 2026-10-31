"""И05.09.26-НВК: расчёты наружных сетей по модели nvk_model.

П1 — К1: расходы, наполнение и скорости выпусков и дворовой сети, перепады в ДК5-018;
П2 — К2: дождевой сток с кровель, пропускная способность колец и выпуска ЛК Ø63, регулирующий объём КЛ-1;
П3 — дренаж Др: приток, пропускная способность, уклоны;
П4 — ввод В1: потери напора, требуемый напор в точке подключения, подводка полива КХ-8.
-> out/nvk/nvk_calc.json
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nvk_model as M  # noqa: E402

OUT = M.OUT
VKC = json.load(open(os.path.join(HERE, 'out', 'vk', 'vk_calc.json')))
P = {p.id: p for p in M.PIPES}
W = {w.id: w for w in M.WELLS}
G = 9.81
N_PP = 0.009                                   # шероховатость ПП, ПЭ (Маннинг)
DI = {110: 0.0996, 160: 0.1452, 63: 0.0554, 32: 0.026, 25: 0.0204}   # внутр. диаметры: SN8 ПП, ПЭ SDR17/SDR11


def part(d, h_d):
    """Площадь и гидравлический радиус частично заполненной трубы."""
    th = 2 * math.acos(1 - 2 * h_d)
    A = d * d / 8 * (th - math.sin(th))
    Pw = d * th / 2
    return A, A / Pw


def manning(d, i, h_d):
    A, R = part(d, h_d)
    v = R ** (2 / 3) * math.sqrt(i) / N_PP
    return A * v, v


def fill(d, i, q):
    """Наполнение h/d и скорость при расходе q (м³/с) — подбором."""
    lo, hi = 1e-4, 0.999
    for _ in range(60):
        m = (lo + hi) / 2
        if manning(d, i, m)[0] < q:
            lo = m
        else:
            hi = m
    return m, manning(d, i, m)[1]


# ====================================================================================== П1: К1
def bath_sum():
    """К1 бани целиком (обе линии — К1-б и К1-бв — сходятся в КК-1): расход по формуле (7) СП 30 и тем же
    коэффициентам, что И05.09.26-ВК.П3 (vk_calc.sewer)."""
    import vk_calc as VC
    fx = [k for k, f_ in VC.FX.items() if f_.k1 and f_.bld == 'b' and k != 'СПА']
    n = len(fx)
    q0s = max(VC.FX[k].a1[7] for k in fx)
    phr = 3600 * VC.P['tot'] * VC.Q0['tot'] / VC.Q0HR['tot']
    k, _, _ = VC.ks(n, 1.0)
    qhr = 0.005 * VC.Q0HR['tot'] * VC.alpha(n * phr)
    qsl = qhr / 3.6 + k * q0s
    return dict(N=n, qsl=qsl, q=max(qsl, q0s))


def p1():
    sec = {s['id']: s for s in VKC['sewer']['sections']}
    sec['баня'] = bath_sum()
    out = []
    for pid, src, nm in (('К1-бн', 'К1-б', 'Выпуск бани К1-б (сборный от Д-б1) → КК-1'),
                         ('К1-бвн', 'К1-бв', 'Выпуск бани К1-бв (от стояка Ст.К1-б) → КК-1'),
                         ('К1-б1', 'баня', 'КК-1 → ввод в дом (К1-1, ВК)'),
                         ('К1-1н', 'К1-1', 'Выпуск К1-1 (дом и баня) → ДК5-018')):
        p = P[pid]
        s = sec[src]
        q = max(s['qsl'], s['q'])
        d = DI[p.dn]
        hd, v = fill(d, p.i, q / 1000)
        qf, vf = manning(d, p.i, 0.999)
        out.append(dict(id=pid, name=nm, N=s['N'], qsl=round(s['qsl'], 2), q=round(q, 2), dn=p.dn, i=p.i,
                        L=round(p.length(), 2), hd=round(hd, 2), v=round(v, 2), qfull=round(qf * 1000, 1),
                        vfull=round(vf, 2), z0=p.z[0], z1=p.z[-1]))
    dk = M.DK
    drops = [dict(id=pp.id, z=z, drop=round(z - dk.bottom, 2)) for pp, z in dk.ins]
    day = VKC['balance']['day']['sewer']
    return dict(rows=out, dk=dict(cover=dk.cover, tray=dk.bottom, drops=drops), day=day,
                i_min160=0.008, h_d_max=0.6, v_max=4.0)


# ====================================================================================== П2: К2
Q20, N_R, MR, GAMMA = 80.0, 0.71, 150, 1.54   # Москва и Московская обл. (СП 32.13330.2018)
F_ROOF = {'дом': 395.0, 'баня': 125.2}         # площади кровель, м²: дом — АР14 по контуру парапета; баня — АР14 бани
                                               # (кровля 124,75 + жёлоб северного карниза 0,40; 31.10.2026)
F_GAR = 0.0                                    # лоток гаража — талая вода с машин, не учитывается
KL_D = 1.50                                    # КЛ-1: колодец Ø1500 (ж/б кольца КС15)
H_MAX = round(M.H0 - 0.75, 2)                 # наибольший уровень в КЛ-1: ниже низа ПУ-1 гаража (−0,750) и дождеприёмников ДК у стен
Z_DOWN = M.LK_DOWN                             # излив выпуска Ø63 в ЛК355 (лоток ЛК355 184,90)
L_STUB = round(math.dist(M.LK_CON, M.LK355), 1)   # существующий выпуск Ø63 от врезки у КЛ-1 до ЛК355 (ИС-3ЛК), м


def q_rain(t, P_=1.0):
    """Интенсивность дождя, л/(с·га), продолжительностью t мин (через q20)."""
    k = (1 + math.log10(P_) / math.log10(MR)) ** GAMMA
    return Q20 * k * (20.0 / t) ** N_R


def q_out(h):
    """Расход через выпуск КЛ-1 → ЛК355 (ПЭ Ø63 SDR17: новый участок до врезки + существующий L_STUB) при уровне h
    в КЛ-1, л/с."""
    p = P['К2-ЛК']
    z0 = p.z[0]
    d = DI[63]
    if h <= z0:
        return 0.0
    if h <= z0 + d:                              # безнапорный режим у входа: по уклону выпуска
        i0 = (z0 - Z_DOWN) / (p.length() + L_STUB)
        return manning(d, max(i0, 0.002), max(1e-3, (h - z0) / d))[0] * 1000
    A = math.pi * d * d / 4
    lam, zeta = 0.025, 1.5
    dH = h - (Z_DOWN + d / 2)
    return A * math.sqrt(2 * G * dH / (zeta + lam * (p.length() + L_STUB) / d)) * 1000


def storage(h):
    """Объём воды в КЛ-1 и трубах К2 при уровне h, м³."""
    p = P['К2-ЛК']
    kl = M.KL1
    V = math.pi * KL_D ** 2 / 4 * max(0.0, h - kl.bottom)
    for pp in M.PIPES:
        if pp.sys != 'К2' or pp.id in ('К2-ЛК', 'К2-1н') or pp.id.startswith('К2-ДК'):   # подводки от ДК — выше уровня
            continue
        d = DI[pp.dn]
        L = pp.length()
        n = max(2, int(L / 0.25))
        for k in range(n):
            z = pp.at((k + 0.5) * L / n)[2]
            hd = min(0.999, max(0.0, (h - z) / d))
            if hd > 0:
                V += part(d, hd)[0] * L / n
    return V


def route(t_rain, F, dt=10.0):
    """Блочный дождь продолжительностью t_rain мин: шаг по времени, уровень в КЛ-1."""
    qin = q_rain(t_rain) * F / 10000              # л/с
    kl0 = P['К2-ЛК'].z[0]
    # таблица уровень → объём
    hs = [kl0 + k * 0.01 for k in range(0, int((H_MAX + 0.6 - kl0) / 0.01))]
    vs = [storage(h) for h in hs]
    V0 = storage(kl0)

    def h_of(V):
        for a, b, va, vb in zip(hs, hs[1:], vs, vs[1:]):
            if va <= V <= vb:
                return a + (b - a) * (V - va) / max(1e-9, vb - va)
        return hs[-1] if V > vs[-1] else hs[0]
    V, t, hmax, Vmax = V0, 0.0, kl0, V0
    while t < t_rain * 60 * 3:
        qi = qin if t < t_rain * 60 else 0.0
        h = h_of(V)
        V = max(V0, V + (qi - q_out(h)) / 1000 * dt)
        hmax = max(hmax, h_of(V))
        Vmax = max(Vmax, V)
        t += dt
    return dict(t=t_rain, q=round(q_rain(t_rain), 1), qin=round(qin, 2), hmax=round(hmax, 3),
                Vreg=round(Vmax - V0, 2))


def p2():
    F = sum(F_ROOF.values())
    roof = {k: dict(F=v, q=round(v * Q20 / 10000, 2)) for k, v in F_ROOF.items()}
    pipes = []
    for pid in ('К2-А', 'К2-Б', 'К2-БА', 'К2-Т', 'К2-К'):
        p = P[pid]
        d = DI[p.dn]
        qf, vf = manning(d, p.i, 0.999)
        qd = {'К2-А': roof['дом']['q'], 'К2-Б': roof['дом']['q'], 'К2-БА': roof['баня']['q'], 'К2-Т': roof['баня']['q'],
              'К2-К': roof['дом']['q'] + roof['баня']['q']}[pid]
        hd, v = fill(d, p.i, qd / 1000) if qd / 1000 < qf else (1.0, vf)
        pipes.append(dict(id=pid, L=round(p.length(), 1), dn=p.dn, i=p.i, q=qd, qfull=round(qf * 1000, 2),
                          hd=round(hd, 2), v=round(v, 2), note=p.note))
    kl0 = P['К2-ЛК'].z[0]
    outs = [dict(h=round(h, 2), q=round(q_out(h), 2)) for h in (kl0 + 0.03, kl0 + 0.055, 185.40, 185.70, 186.00,
                                                                  H_MAX)]
    runs = [route(t, F) for t in (5, 10, 15, 20, 30, 45, 60, 90, 120)]
    worst = max(runs, key=lambda r: r['hmax'])
    return dict(q20=Q20, n=N_R, mr=MR, gamma=GAMMA, F=F, roof=roof, pipes=pipes, outs=outs, runs=runs, worst=worst,
                kl_d=KL_D, h_max=H_MAX, z_down=Z_DOWN, L_stub=L_STUB, kl_out=kl0, kl_bottom=M.KL1.bottom,
                kl_cover=M.KL1.cover, ok=worst['hmax'] <= H_MAX)


# ====================================================================================== П3: дренаж
KF = 0.05                                      # коэффициент фильтрации суглинков, м/сут (ИГИ — уточнить)


def p3():
    rows = []
    for pid in ('Др-1/2', 'Др-2/3', 'Др-1/4', 'Др-4/3', 'ДрБ-1/2', 'ДрБ-2/3', 'ДрБ-1/4', 'ДрБ-4/3', 'Др-Т', 'Др-К'):
        p = P[pid]
        d = DI[110]
        qf, vf = manning(d, p.i, 0.999)
        rows.append(dict(id=pid, L=round(p.length(), 1), i=p.i, z0=p.z[0], z1=p.z[-1], qfull=round(qf * 1000, 2),
                         vfull=round(vf, 2)))
    L_tot = sum(P[r].length() for r in ('Др-1/2', 'Др-2/3', 'Др-1/4', 'Др-4/3', 'ДрБ-1/2', 'ДрБ-2/3', 'ДрБ-1/4',
                                         'ДрБ-4/3'))
    # приток: верховодка по контуру — удельный приток q = Kф·H, H — слой воды над дренажом 0,5 м (с запасом)
    q_unit = KF * 0.5 / 86400 * 1000            # л/(с·м)
    Q = q_unit * L_tot
    return dict(rows=rows, L=round(L_tot, 1), kf=KF, q_unit=q_unit, Q=round(Q, 3), i_min=0.002)


# ====================================================================================== П4: В1
def p4():
    net = VKC['network']['ВВ']
    q = net['q']                                 # л/с — расчётный расход дома и бани на вводе (ВК.П2)
    Htr = VKC['head']['Htr']
    p = P['В1-н']
    d = DI[32]
    A = math.pi * d * d / 4

    def loss(qq, L):
        v = qq / 1000 / A
        # ПЭ: Ф. А. Шевелев (i = 0,000685 v^1,774 / d^1,226 для пластмассовых труб, d — м)
        i = 0.000685 * v ** 1.774 / d ** 1.226
        return v, i, i * L * 1.3
    v, i, h = loss(q, p.length())
    z_in, z_stub = M.Z_VV, M.Z_STUB
    H_stub = Htr + h + (z_in - z_stub)
    q2 = q + 0.30                                 # с автополивом КХ-8 одновременно
    v2, i2, h2 = loss(q2, p.length())
    H_stub2 = Htr + h2 + (z_in - z_stub)
    kx = P['КХ-8н']
    dk = DI[25]
    vk = 0.30 / 1000 / (math.pi * dk * dk / 4)
    return dict(q=round(q, 3), Htr=round(Htr, 2), L=round(p.length(), 2), v=round(v, 2), i=round(i, 4),
                h=round(h, 2), dz=round(z_in - z_stub, 2), H_stub=round(H_stub, 1), q2=round(q2, 3),
                v2=round(v2, 2), h2=round(h2, 2), H_stub2=round(H_stub2, 1), z_in=z_in, z_stub=z_stub,
                depth_min=round(M.FROST + 0.5, 2), kx_v=round(vk, 2), kx_L=round(kx.length(), 2))


def main():
    for p in M.PIPES:
        M.frost_check(p)
    res = dict(p1=p1(), p2=p2(), p3=p3(), p4=p4())
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'nvk_calc.json'), 'w') as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    r = res
    for x in r['p1']['rows']:
        print('П1', x['id'], 'q', x['q'], 'Ø', x['dn'], 'i', x['i'], 'h/d', x['hd'], 'v', x['v'], 'Qп', x['qfull'])
    print('П1 ДК', r['p1']['dk'])
    print('П2 кровли', r['p2']['roof'], 'F', r['p2']['F'])
    for x in r['p2']['pipes']:
        print('П2', x)
    print('П2 выпуск', r['p2']['outs'])
    for x in r['p2']['runs']:
        print('П2 дождь', x)
    print('П2 худший', r['p2']['worst'], 'ok', r['p2']['ok'])
    print('П3', r['p3']['L'], r['p3']['Q'], r['p3']['rows'][0])
    print('П4', r['p4'])


if __name__ == '__main__':
    main()
