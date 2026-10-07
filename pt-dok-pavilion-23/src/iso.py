"""Аксонометрические схемы (фронтальная диметрия: ось Y под 45°, коэффициент 0,5)."""
import json, math, os
from collections import defaultdict
from dxfkit import txt, mtxt, line, rect, ins, frame
HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, 'model_sized.json')))
C = 0.5 * math.cos(math.radians(45))

def P(x, y, z, ox, oy, zs=1.0):
    return (ox + x + y * C, oy + z * 1000 * zs + y * C)

def iso_sheet(doc, msp, ox, oy, fmt, k, sel, title, head, sheet_no, sheets_total, notes, place=(40, 200), zs=1.0,
              label_risers=True, elev_pts=(), pk_marks=False):
    frame(msp, ox, oy, fmt, k, title, sheet_no, sheets_total)
    bx, by = ox + place[0] * k, oy + place[1] * k
    pipes = [p for p in M['pipes'] if sel(p)]
    for p in pipes:
        a, b = p['a'], p['b']
        main = p['role'] in ('питающий', 'стояк', 'кольцо ВПВ', 'перемычка ВПВ', 'стояк ВПВ')
        lay = {'В21': 'ПТ_В21', 'В22': 'ПТ_В22', 'В2': 'ПТ_В2'}[p['sys']]
        if not main:
            lay += '_расп' if p['sys'] != 'В2' else ''
        col = {'В21': 1, 'В22': 6, 'В2': 3}[p['sys']]
        msp.add_line(P(*a, bx, by, zs), P(*b, bx, by, zs), dxfattribs={'layer': lay})
    # оросители
    secs = {p['sec'] for p in pipes}
    for s in M['sprinklers']:
        if s['sec'] in secs:
            ins(msp, 'SPR_DN' if s['floor'] == 1 else 'SPR_UP', *P(s['x'], s['y'], s['z'], bx, by, zs), k * 0.7, layer='ПТ_оросители')
    # Ду: сливаем коллинеарные отрезки одного Ду
    segs = defaultdict(list)
    for p in pipes:
        a, b = p['a'], p['b']
        if abs(a[0] - b[0]) > 1 and abs(a[1] - b[1]) < 1 and abs(a[2] - b[2]) < 0.01:
            segs[('x', a[1], a[2], p['dn'])].append(sorted([a[0], b[0]]))
        elif abs(a[1] - b[1]) > 1 and abs(a[0] - b[0]) < 1:
            segs[('y', a[0], None, p['dn'])].append((sorted([a[1], b[1]]), a, b))
        elif abs(a[2] - b[2]) > 0.3 and abs(a[0] - b[0]) < 1 and abs(a[1] - b[1]) < 1:
            segs[('z', a[0], a[1], p['dn'])].append(sorted([a[2], b[2]]))
    for (ori, c1, c2, dn), lst in segs.items():
        if ori == 'y':
            items = sorted(lst, key=lambda t: t[0][0])
            runs = []
            for (u, a, b) in items:
                if runs and u[0] <= runs[-1][0][1] + 1:
                    runs[-1][0][1] = max(runs[-1][0][1], u[1])
                else:
                    runs.append([list(u), a, b])
            for (u0, u1), a, b in runs:
                if u1 - u0 < 1500:
                    continue
                ym = (u0 + u1) / 2
                za = a[2] + (b[2] - a[2]) * ((ym - a[1]) / (b[1] - a[1])) if b[1] != a[1] else a[2]
                X, Y = P(c1, ym, za, bx, by, zs)
                txt(msp, X - 0.6 * k, Y + 0.6 * k, f'{dn}', 1.6, k, align='BR', rot=45)
            continue
        lst.sort()
        runs = []
        for u in lst:
            if runs and u[0] <= runs[-1][1] + (0.001 if ori == 'z' else 1):
                runs[-1][1] = max(runs[-1][1], u[1])
            else:
                runs.append(list(u))
        for u0, u1 in runs:
            if ori == 'x':
                if u1 - u0 < 1500:
                    continue
                X, Y = P((u0 + u1) / 2, c1, c2, bx, by, zs)
                txt(msp, X, Y + 0.5 * k, f'Ду{dn}', 1.8 if dn < 100 else 2.2, k, align='BC')
            else:
                if u1 - u0 < 0.8:
                    continue
                X, Y = P(c1, c2, (u0 + u1) / 2, bx, by, zs)
                txt(msp, X - 0.6 * k, Y, f'Ду{dn}', 1.8, k, align='BR', rot=90)
    # пожарные краны и стояки ВПВ
    if pk_marks:
        top = {}
        for p in pipes:
            if p['role'] == 'стояк ВПВ':
                for q in (p['a'], p['b']):
                    key = (round(q[0]), round(q[1]))
                    top[key] = max(top.get(key, -9), q[2])
        done = set()
        for pk in M['pk']:
            X, Y = P(pk['x'], pk['y'], pk['z'], bx, by, zs)
            ins(msp, 'PK2', X, Y + 0.3 * k, k * 0.9, layer='ПТ_ПК')
            txt(msp, X + 4.2 * k, Y + 0.6 * k, pk['name'], 1.6, k)
            key = (round(pk['rx']), round(pk['ry']))
            if pk['riser'] not in done and key in top:
                done.add(pk['riser'])
                X2, Y2 = P(pk['rx'], pk['ry'], top[key], bx, by, zs)
                txt(msp, X2 - 0.8 * k, Y2 - 1.0 * k, pk['riser'], 1.6, k, align='TR', rot=90)
    # отметки
    for (x, y, z, s) in elev_pts:
        X, Y = P(x, y, z, bx, by, zs)
        ins(msp, 'ELEV', X, Y, k, layer='ПТ_текст')
        txt(msp, X + 1.5 * k, Y + 2.2 * k, s, 2.0, k)
    txt(msp, ox + 420 * k if fmt == 'A0' else ox + 300 * k, oy + (800 if fmt == 'A0' else 560) * k, head, 5, k, align='BC', style='ПТ_загл')
    mtxt(msp, ox + 30 * k, oy + 140 * k if fmt == 'A0' else oy + 110 * k, '\\P'.join(f'{i + 1}. {n}' for i, n in enumerate(notes)), 2.5, 600, k, attach=1)
    return bx, by
