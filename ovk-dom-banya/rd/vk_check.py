"""Проверка коллизий модели ВК: трубы ВК между собой (кроме соединённых) и с трубами/оборудованием ТМ в 1.6."""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vk_model as VK  # noqa: E402


def seg_dist(p1, q1, p2, q2):
    """Минимальное расстояние между отрезками в 3D."""
    import numpy as np
    p1, q1, p2, q2 = map(np.array, (p1, q1, p2, q2))
    d1, d2, r = q1 - p1, q2 - p2, p1 - p2
    a, e, f = d1 @ d1, d2 @ d2, d2 @ r
    if a < 1e-12 and e < 1e-12:
        return float(np.linalg.norm(p1 - p2))
    if a < 1e-12:
        s, t = 0.0, min(max(f / e, 0), 1)
    else:
        c = d1 @ r
        if e < 1e-12:
            t, s = 0.0, min(max(-c / a, 0), 1)
        else:
            b = d1 @ d2
            den = a * e - b * b
            s = min(max((b * f - c * e) / den, 0), 1) if den > 1e-12 else 0.0
            t = (b * s + f) / e
            if t < 0:
                t, s = 0.0, min(max(-c / a, 0), 1)
            elif t > 1:
                t, s = 1.0, min(max((b - c) / a, 0), 1)
    return float(np.linalg.norm((p1 + d1 * s) - (p2 + d2 * t)))


def touching(a, b, tol=0.02):
    """Трубы соединены (конец одной лежит на другой)?"""
    for P_, Q_ in ((a, b), (b, a)):
        for end in (P_.pts[0], P_.pts[-1]):
            for s0, s1 in zip(Q_.pts, Q_.pts[1:]):
                if seg_dist(end, end, s0, s1) < max(tol, Q_.od / 2 + 0.01):
                    return True
    return False


def box_dist(p, q, bb):
    """Расстояние от отрезка до параллелепипеда (оценка по 40 точкам)."""
    best = 1e9
    for i in range(41):
        t = i / 40
        x, y, z = (p[k] + (q[k] - p[k]) * t for k in range(3))
        dx = max(bb[0] - x, 0, x - bb[3])
        dy = max(bb[1] - y, 0, y - bb[4])
        dz = max(bb[2] - z, 0, z - bb[5])
        best = min(best, math.sqrt(dx * dx + dy * dy + dz * dz))
    return best


def run(clear=0.010):
    out = []
    P = VK.PIPES
    for i, a in enumerate(P):
        for b in P[i + 1:]:
            if a.bld != b.bld or touching(a, b):
                continue
            need = a.r() + b.r() + clear
            for s0, s1 in zip(a.pts, a.pts[1:]):
                for t0, t1 in zip(b.pts, b.pts[1:]):
                    d = seg_dist(s0, s1, t0, t1)
                    if d < need:
                        out.append(f'{a.id} × {b.id}: {d:.3f} < {need:.3f}')
                        break
                else:
                    continue
                break
    # ТМ (топочная): трубы и корпуса
    tm = json.load(open(os.path.join(HERE, 'out', 'tm', 'tm.json')))
    BND = {'В1-Б1', 'УП', 'Т3', 'Т4', 'РБ-ГВС'}
    for a in P:
        if a.bld != 'h':
            continue
        for t in tm['pipes']:
            if t['id'] in BND:
                continue
            need = a.r() + t['od'] / 2 + 0.02 + clear
            hit = None
            for s0, s1 in zip(a.pts, a.pts[1:]):
                for t0, t1 in zip(t['pts'], t['pts'][1:]):
                    d = seg_dist(s0, s1, t0, t1)
                    if d < need:
                        hit = d
                        break
                if hit is not None:
                    break
            if hit is not None:
                out.append(f'{a.id} × ТМ {t["id"]}: {hit:.3f} < {need:.3f}')
        for e in tm['equip']:
            if e['id'] in ('Трап', 'Б1') or e.get('ctx') and e['id'] not in ('П1', 'П1-узел', 'КШ-3'):
                continue
            bb = e['bbox']
            for s0, s1 in zip(a.pts, a.pts[1:]):
                d = box_dist(s0, s1, bb)
                if d < a.r():
                    out.append(f'{a.id} × ТМ {e["id"]} (корпус): {d:.3f}')
                    break
    return out


if __name__ == '__main__':
    r = run()
    print('\n'.join(r) if r else '—')
    print(len(r), 'коллизий')
