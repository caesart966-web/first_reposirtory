"""Профили стен для построения телом в Revit (вытягивание профиля фасада с проёмами на толщину стены).

    python3 wall_prisms.py <ar_model.json> <walls_prism.json>

Выгрузка IFC из Revit пропускает стены-DirectShape, построенные сеткой (Mesh): 10 наружных стен первой
выгрузки 27.11.2026. Все стены и облицовки модели — призмы: две большие грани с одинаковым контуром
(с проёмами), расстояние между ними — толщина. Для каждой стены пишется: нормаль n (горизонтальная), ось U
вдоль стены (U x Z = n), смещение грани s_min вдоль n, толщина и контуры (u, v = z) — наружный против часовой
стрелки, проёмы по часовой. Проверяется: контуры обеих граней совпадают, объём сетки = площадь x толщина.
"""
import json
import sys

import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union


def tidy(pts, tol=0.5):
    out = []
    for p in pts:
        if not out or np.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > tol:
            out.append(p)
    if len(out) > 1 and np.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= tol:
        out.pop()
    res = []
    for i in range(len(out)):
        a, b, c = out[i - 1], out[i], out[(i + 1) % len(out)]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cross) / max(np.hypot(c[0] - a[0], c[1] - a[1]), 1.0) > 0.05:
            res.append([round(float(b[0]), 3), round(float(b[1]), 3)])
    return res


def prism(e):
    V = np.array(e['verts'])
    F = np.array(e['faces'])
    T = V[F]
    N = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    A = np.linalg.norm(N, axis=1) / 2
    Nn = N / np.maximum(2 * A[:, None], 1e-12)
    i = [k for k in np.argsort(-A) if abs(Nn[k, 2]) < 0.01][0]
    n = np.array([Nn[i, 0], Nn[i, 1], 0.0])
    n /= np.linalg.norm(n)
    Z = np.array([0.0, 0.0, 1.0])
    U = np.cross(Z, n)
    if np.dot(np.cross(U, Z), n) < 0:
        U = -U
    s = V @ n
    smin, smax = s.min(), s.max()

    def side(sv, sign):
        sel = [k for k in range(len(F)) if abs(np.dot(Nn[k], n) * sign - 1) < 1e-4
               and np.all(np.abs(T[k] @ n - sv) < 0.05) and A[k] > 1e-6]
        return unary_union([Polygon([(p @ U, p @ Z) for p in T[k]]).buffer(0) for k in sel])
    a, b = side(smin, -1), side(smax, 1)
    assert a.symmetric_difference(b).area < 1.0, e['name']
    vol = abs(trimesh.Trimesh(V, F).volume)
    assert abs(vol - a.area * (smax - smin)) / vol < 1e-3, e['name']
    polys = []
    for g in getattr(a, 'geoms', [a]):
        g = orient(g, 1.0)
        polys.append({'ext': tidy(list(g.exterior.coords)[:-1]),
                      'holes': [tidy(list(h.coords)[:-1]) for h in g.interiors]})
    chk = sum(Polygon(p['ext'], p['holes']).area for p in polys)
    assert abs(chk - a.area) < 50.0, (e['name'], chk, a.area)
    return {'n': n.round(9).tolist(), 'U': U.round(9).tolist(), 's_min': round(float(smin), 3),
            'th': round(float(smax - smin), 3), 'polys': polys, 'area_mm2': a.area}


def main(src, dst):
    d = json.load(open(src, encoding='utf-8'))
    out = {}
    for e in d['elements']:
        if e['ifc_class'] in ('IfcWall', 'IfcCurtainWall'):
            out[e['guid']] = prism(e)
            p = out[e['guid']]
            print('%-60s %s толщина %.0f, контуров %d, проёмов %d' % (
                e['name'][-60:], e['ifc_class'], p['th'], len(p['polys']), sum(len(q['holes']) for q in p['polys'])))
    json.dump(out, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
    print('стен:', len(out))


if __name__ == '__main__':
    main(*sys.argv[1:3])
