"""Подсчёт объёмов из модели: трубы, фасонные части, опоры, гильзы, оросители, ПК."""
import json, math, os
from collections import defaultdict, Counter
from geom import rooms, bb, pip
HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, 'model_sized.json')))

def key(p):
    return (round(p[0]), round(p[1]), round(p[2], 3))

def L(p):
    a, b = p['a'], p['b']
    return math.sqrt(((a[0] - b[0]) / 1000) ** 2 + ((a[1] - b[1]) / 1000) ** 2 + (a[2] - b[2]) ** 2)

def ring_dn(p):
    r = p['role']
    if p['sys'] != 'В2':
        return p.get('dn')
    if r in ('кольцо ВПВ', 'перемычка ВПВ'):
        return 100
    if r in ('стояк ВПВ', 'подводка ВПВ'):
        return 80 if r == 'стояк ВПВ' else 80
    return 100

def run():
    for p in M['pipes']:
        if p['sys'] == 'В2':
            p['dn'] = ring_dn(p)
        if p['role'] == 'подводка ВПВ' and L(p) < 1.0:
            p['dn'] = 65
    length = defaultdict(float)              # (sys, dn) -> м
    for p in M['pipes']:
        length[(p['sys'], p['dn'])] += L(p)
    # узлы: степень и Ду
    nodes = defaultdict(list)
    for i, p in enumerate(M['pipes']):
        nodes[key(p['a'])].append(i); nodes[key(p['b'])].append(i)
    spr_pts = {(s['x'], s['y'], s['z']) for s in M['sprinklers']}
    tees = Counter(); elbows = Counter(); reducers = Counter(); spr_outlets = Counter(); caps = Counter()
    for n, lst in nodes.items():
        dns = sorted((M['pipes'][i]['dn'] for i in lst), reverse=True)
        sysn = M['pipes'][lst[0]]['sys']
        if n in spr_pts:
            continue
        if len(lst) == 1:
            caps[(sysn, dns[0])] += 1
        elif len(lst) == 2:
            a, b = M['pipes'][lst[0]], M['pipes'][lst[1]]
            da = [a['b'][k] - a['a'][k] for k in range(3)]; db = [b['b'][k] - b['a'][k] for k in range(3)]
            da[2] *= 1000; db[2] *= 1000
            cross = abs(da[0] * db[1] - da[1] * db[0]) + abs(da[1] * db[2] - da[2] * db[1]) + abs(da[0] * db[2] - da[2] * db[0])
            if cross > 1:
                elbows[(sysn, dns[0])] += 1
                if dns[0] != dns[1]:
                    reducers[(sysn, dns[0], dns[1])] += 1
            elif dns[0] != dns[1]:
                reducers[(sysn, dns[0], dns[1])] += 1
        else:
            # тройник по большему Ду, ответвление — меньший
            tees[(sysn, dns[0], dns[-1])] += 1
            if dns[0] != dns[1]:
                reducers[(sysn, dns[0], dns[1])] += 1
    # оросители: подключение к распределительному (спуск/подъём Ду25 → R1/2)
    for s in M['sprinklers']:
        spr_outlets['DN' if s['floor'] == 1 else 'UP'] += 1
    # опоры: Ду≤50 — шаг 3 м, Ду65..100 — 4 м, Ду125..150 — 6 м (горизонтальные участки); стояки — 1 на этаж
    hangers = Counter()
    typed = Counter()        # (тип узла крепления, Ду) -> шт.
    def htype(p):
        z = max(p['a'][2], p['b'][2])
        if p['sys'] == 'В22' and z > 6.0:
            return 'прогон'          # к прогонам/балкам покрытия — струбцина
        if p['sys'] == 'В2' and z < 0:
            return 'подвал'          # к перекрытию над подвалом
        return 'перекрытие'          # к монолитному перекрытию по профлисту
    for p in M['pipes']:
        l = L(p); dn = p['dn']
        if abs(p['a'][2] - p['b'][2]) > 0.05 and abs(p['a'][0] - p['b'][0]) < 1 and abs(p['a'][1] - p['b'][1]) < 1:
            if l > 1.0:
                n = max(1, round(l / 3.0))
                hangers[dn] += n; typed[('стояк', dn)] += n
            continue
        step = 3.0 if dn <= 50 else 4.0 if dn <= 100 else 6.0
        hangers[dn] += l / step; typed[(htype(p), dn)] += l / step
    hangers = Counter({d: math.ceil(v) for d, v in hangers.items()})
    typed = Counter({k: math.ceil(v) for k, v in typed.items()})
    # проходы через стены (смена помещения вдоль горизонтального участка) и перекрытия
    R1, R2 = rooms('f1'), rooms('f2')
    def room_at(x, y, fl):
        RR = R1 if fl == 1 else R2
        for r in RR.values():
            if r['poly'] and pip(x, y, r['poly']):
                return r['num']
        return None
    walls = Counter(); slabs = Counter()
    for p in M['pipes']:
        a, b = p['a'], p['b']
        if abs(a[2] - b[2]) < 0.05 and (abs(a[0] - b[0]) > 1 or abs(a[1] - b[1]) > 1):
            z = a[2]
            fl = 1 if 0 < z < 3.6 else 2 if z >= 3.6 else 0
            if fl == 0:
                continue
            n = max(2, int(L(p) / 0.05))
            prev = None
            for t in range(n + 1):
                x = a[0] + (b[0] - a[0]) * t / n; y = a[1] + (b[1] - a[1]) * t / n
                r = room_at(x, y, fl)
                if r is not None and prev is not None and r != prev:
                    walls[p['dn']] += 1
                if r is not None:
                    prev = r
        else:
            z0, z1 = sorted((a[2], b[2]))
            for zs in (-0.10, 3.55):
                if z0 < zs < z1:
                    slabs[p['dn']] += 1
    out = dict(
        length={f'{s}|{d}': round(v, 1) for (s, d), v in sorted(length.items(), key=lambda t: (t[0][0], t[0][1]))},
        tees={f'{s}|{a}x{b}': v for (s, a, b), v in sorted(tees.items())},
        elbows={f'{s}|{d}': v for (s, d), v in sorted(elbows.items())},
        reducers={f'{s}|{a}x{b}': v for (s, a, b), v in sorted(reducers.items())},
        caps={f'{s}|{d}': v for (s, d), v in sorted(caps.items())},
        spr=dict(spr_outlets), hangers={str(d): v for d, v in sorted(hangers.items())},
        hangers_typed={f'{t}|{d}': v for (t, d), v in sorted(typed.items(), key=lambda kv: (kv[0][0], kv[0][1]))},
        walls={str(d): v for d, v in sorted(walls.items())}, slabs={str(d): v for d, v in sorted(slabs.items())},
        pk=len(M['pk']), spr_by_sec=dict(Counter(str(s['sec']) for s in M['sprinklers'])),
        spr_by_floor_room=dict(Counter(f"{s['floor']}|{s['room']}" for s in M['sprinklers'])),
    )
    json.dump(M, open(os.path.join(HERE, 'model_sized.json'), 'w'), ensure_ascii=False)
    json.dump(out, open(os.path.join(HERE, 'bom.json'), 'w'), ensure_ascii=False, indent=1)
    return out

if __name__ == '__main__':
    o = run()
    for k in ('length', 'tees', 'elbows', 'reducers', 'caps', 'spr', 'hangers', 'walls', 'slabs'):
        print(k, o[k])
