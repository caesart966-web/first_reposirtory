"""Подбор диаметров и гидравлический расчёт АУПТ (секции 1, 2) и ВПВ.
Методика — СП 485.1311500.2020 прил. Б: q = 10·K·√P (P, МПа); потери по длине
ΔH[м] = Q²·L / Kт, местные — 20 % от потерь по длине; геометрическая высота учитывается.
"""
import json, math, os, sys
from collections import defaultdict
from geom import GROUPS
HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, 'model.json')))

K_SPR = 0.42             # коэффициент производительности оросителя, л/(с·МПа^0,5)
LOCAL = 1.20             # +20 % местные потери
# Трубы: Ду -> (обозначение, внутр. диаметр мм, Kт л⁶/с²)
PIPES = {
    25: ('25×3,2 ГОСТ 3262-75', 27.1, 3.65),
    32: ('32×3,2 ГОСТ 3262-75', 35.9, 16.5),
    40: ('40×3,5 ГОСТ 3262-75', 41.0, 34.5),
    50: ('50×3,5 ГОСТ 3262-75', 53.0, 135.0),
    65: ('76×3,5 ГОСТ 10704-91', 69.0, 514.0),
    80: ('89×3,5 ГОСТ 10704-91', 82.0, 1305.0),
    100: ('108×4,0 ГОСТ 10704-91', 100.0, 3807.0),
    125: ('133×4,0 ГОСТ 10704-91', 125.0, 12650.0),
    150: ('159×4,5 ГОСТ 10704-91', 150.0, 34400.0),
}
DN_LIST = sorted(PIPES)

def key(p):
    return (round(p[0]), round(p[1]), round(p[2], 3))

def build_tree(sec):
    """Дерево секции от источника (выход УУ)."""
    adj = defaultdict(list)
    idx = [i for i, p in enumerate(M['pipes']) if p['sec'] == sec and p['sys'] != 'В2']
    for i in idx:
        p = M['pipes'][i]
        a, b = key(p['a']), key(p['b'])
        adj[a].append((b, i)); adj[b].append((a, i))
    src = key(M['src'][str(sec)])
    parent = {src: (None, None)}
    order = [src]
    stack = [src]
    while stack:
        u = stack.pop()
        for v, i in adj[u]:
            if v not in parent:
                parent[v] = (u, i)
                order.append(v); stack.append(v)
    spr_nodes = {}
    for j, s in enumerate(M['sprinklers']):
        if s['sec'] == sec:
            spr_nodes[(s['x'], s['y'], s['z'])] = j
    missing = [k for k in spr_nodes if k not in parent]
    unreached = [i for i in idx if key(M['pipes'][i]['a']) not in parent or key(M['pipes'][i]['b']) not in parent]
    children = defaultdict(list)
    for v, (u, i) in parent.items():
        if u is not None:
            children[u].append((v, i))
    return dict(src=src, parent=parent, order=order, children=children, spr=spr_nodes, missing=missing, unreached=unreached)

def length_m(p):
    a, b = p['a'], p['b']
    return math.sqrt(((a[0] - b[0]) / 1000) ** 2 + ((a[1] - b[1]) / 1000) ** 2 + (a[2] - b[2]) ** 2)

def size_section(T, sec, qdesign):
    """Ду: распределительные — по числу оросителей ниже по потоку, питающие — по расходу (v ≤ ~2,5 м/с)."""
    down = defaultdict(int); grp5 = defaultdict(bool)
    for v in reversed(T['order']):
        if v in T['spr']:
            down[v] += 1
            if M['sprinklers'][T['spr'][v]]['grp'] == 5:
                grp5[v] = True
        u, i = T['parent'][v]
        if u is not None:
            down[u] += down[v]; grp5[u] = grp5[u] or grp5[v]
    dn = {}
    for v, (u, i) in T['parent'].items():
        if u is None:
            continue
        p = M['pipes'][i]; n = down[v]
        if p['role'] == 'спуск':
            d = 25
        elif p['role'] in ('распределительный', 'подъём'):
            d = 25 if n <= 1 else 32 if n <= 2 else 40 if n <= 3 else 50 if n <= 5 else 65 if n <= 10 else 80 if n <= 16 else 100
        else:
            q = min(qdesign, n * 1.7)
            d = 50 if q <= 4.5 else 65 if q <= 8.5 else 80 if q <= 12 else 100 if q <= 19 else 125 if q <= 25 else 150
            if p['role'] == 'стояк':
                d = 150
        dn[i] = d
    return dn, down

def cell_areas(sec):
    """Площадь, защищаемая оросителем (по шагу в помещении), м²."""
    from geom import rooms, bb
    R1, R2 = rooms('f1'), rooms('f2')
    out = {}
    S = [(j, s) for j, s in enumerate(M['sprinklers']) if s['sec'] == sec]
    byroom = defaultdict(list)
    for j, s in S:
        byroom[(s['floor'], s['room'])].append((j, s))
    for (fl, rm), lst in byroom.items():
        R = (R1 if fl == 1 else R2).get(rm)
        x0, y0, x1, y1 = bb(R['poly']) if R else (min(s['x'] for _, s in lst) - 1500, min(s['y'] for _, s in lst) - 1500,
                                                  max(s['x'] for _, s in lst) + 1500, max(s['y'] for _, s in lst) + 1500)
        for j, s in lst:
            row = sorted(t['x'] for _, t in lst if abs(t['y'] - s['y']) < 300 and t is not s)
            col = sorted(t['y'] for _, t in lst if abs(t['x'] - s['x']) < 300 and t is not s)
            L = [x for x in row if x < s['x']]; Rr = [x for x in row if x > s['x']]
            D = [y for y in col if y < s['y']]; U = [y for y in col if y > s['y']]
            wl = (s['x'] - L[-1]) / 2 if L else min(s['x'] - x0, 2000)
            wr = (Rr[0] - s['x']) / 2 if Rr else min(x1 - s['x'], 2000)
            hd = (s['y'] - D[-1]) / 2 if D else min(s['y'] - y0, 2000)
            hu = (U[0] - s['y']) / 2 if U else min(y1 - s['y'], 2000)
            out[j] = max(1.0, (wl + wr) * (hd + hu) / 1e6)
    return out

def solve(T, dn, open_spr, p_src, z_src):
    """Расчёт дерева при заданном давлении на выходе УУ: итерации «расходы вверх — давления вниз»."""
    q = {v: 1.4 for v in open_spr}
    # подмножество дерева, содержащее открытые оросители
    need = set()
    for v in open_spr:
        w = v
        while w is not None and w not in need:
            need.add(w); w = T['parent'][w][0]
    P = {}
    for it in range(200):
        flow = defaultdict(float)
        for v in reversed(T['order']):
            if v not in need:
                continue
            if v in open_spr:
                flow[v] += q[v]
            u, i = T['parent'][v]
            if u is not None:
                flow[u] += flow[v]
        P = {T['src']: p_src}
        for v in T['order']:
            if v not in need or v == T['src']:
                continue
            u, i = T['parent'][v]
            p = M['pipes'][i]
            Q = flow[v]
            kt = PIPES[dn[i]][2]
            dh = LOCAL * Q * Q * length_m(p) / kt          # м
            P[v] = P[u] - dh / 100 - (v[2] - u[2]) / 100   # МПа
        err = 0
        for v in open_spr:
            qn = 10 * K_SPR * math.sqrt(max(P[v], 1e-6))
            err = max(err, abs(qn - q[v]))
            q[v] = 0.5 * q[v] + 0.5 * qn
        if err < 1e-5:
            break
    flow_total = sum(q.values())
    return q, P, flow_total

def dictating(T, dn, open_spr, qreq):
    """Давление на выходе УУ, при котором наименее обеспеченный ороситель даёт qreq."""
    lo, hi = 0.05, 2.0
    for _ in range(50):
        mid = (lo + hi) / 2
        q, P, Q = solve(T, dn, open_spr, mid, None)
        if min(q.values()) < qreq:
            lo = mid
        else:
            hi = mid
    q, P, Q = solve(T, dn, open_spr, hi, None)
    return hi, q, P, Q

def path_len(T, v):
    L = 0
    while T['parent'][v][0] is not None:
        u, i = T['parent'][v]; L += length_m(M['pipes'][i]); v = u
    return L

def pick_area(T, sec, areas, cand_rooms, S_target, remote_by='path'):
    """Наиболее удалённая площадь: самый удалённый ороситель в помещениях cand_rooms
    и ближайшие к нему (в плане, в тех же помещениях), пока сумма площадей < S_target."""
    nodes = [(v, j) for v, j in T['spr'].items() if M['sprinklers'][j]['room'] in cand_rooms]
    if not nodes:
        return None
    far = max(nodes, key=lambda t: path_len(T, t[0]) + 100 * t[0][2])
    fx, fy = far[0][0], far[0][1]
    nodes.sort(key=lambda t: (t[0][0] - fx) ** 2 + (t[0][1] - fy) ** 2)
    sel = []; acc = 0
    for v, j in nodes:
        if acc >= S_target:
            break
        sel.append((v, j)); acc += areas[j]
    return sel, acc

def run():
    report = {}
    sized = {}
    for sec in (1, 2):
        T = build_tree(sec)
        assert not T['missing'], ('оросители вне дерева', sec, len(T['missing']))
        assert not T['unreached'], ('трубы вне дерева', sec, len(T['unreached']))
        dn, down = size_section(T, sec, 30.0)
        areas = cell_areas(sec)
        cases = []
        if sec == 1:
            groups = [('21', 2, ['21', '03']), ('35', 2, ['35', '04']), ('20', 2, ['20']), ('34', 2, ['34']),
                      ('93', 2, ['93']), ('98', 2, ['98'])]
        else:
            stores = sorted({s['room'] for s in M['sprinklers'] if s['sec'] == 2 and s['grp'] == 5})
            groups = [(r, 5, [r]) for r in stores]
            groups += [('37 холл', 2, ['37', '98']), ('94 второй свет', 2, ['94', '38']), ('95 второй свет', 2, ['95', '39']),
                       ('33/34 тех.', 2, ['33', '34']), ('28', 2, ['28', '29', '30'])]
        for name, g, rms in groups:
            G = GROUPS[g]
            res = pick_area(T, sec, areas, rms, G['S'])
            if not res:
                continue
            sel, acc = res
            open_spr = {v for v, j in sel}
            qreq = G['q'] * min(G['Amax'], max(areas[j] for v, j in sel))
            qreq = max(qreq, G['q'] * G['Amax'])          # консервативно: нормативная площадь на ороситель
            p, q, P, Q = dictating(T, dn, open_spr, qreq)
            cases.append(dict(name=name, grp=g, n=len(sel), area=round(acc, 1), qreq=round(qreq, 3), p_uu=round(p, 4),
                              Q=round(Q, 2), intensity=round(Q / acc, 3), pmin_spr=round(min(P[v] for v in open_spr), 4),
                              sel=[j for v, j in sel]))
        worst = max(cases, key=lambda c: c['p_uu'])
        report[sec] = dict(cases=cases, worst=worst['name'])
        sized[sec] = dict(dn=dn, down=down)
        # итерация: если давление высоко — увеличить питающие на пути к диктующей площади
        print(f'Секция {sec}: оросителей {len(T["spr"])}')
        for c in sorted(cases, key=lambda c: -c['p_uu'])[:8]:
            print(f"  {c['name']:>16} гр.{c['grp']} n={c['n']:2d} S={c['area']:6.1f} м² Q={c['Q']:6.2f} л/с "
                  f"i={c['intensity']:.3f} P(УУ)={c['p_uu']:.3f} МПа")
    return report, sized

if __name__ == '__main__':
    rep, sized = run()
    for sec in (1, 2):
        for i, d in sized[sec]['dn'].items():
            M['pipes'][i]['dn'] = d
    json.dump(rep, open(os.path.join(HERE, 'hydro_report.json'), 'w'), ensure_ascii=False, indent=1, default=str)
    json.dump(M, open(os.path.join(HERE, 'model_sized.json'), 'w'), ensure_ascii=False)
