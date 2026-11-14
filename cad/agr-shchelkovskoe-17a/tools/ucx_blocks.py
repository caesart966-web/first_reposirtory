"""Разбивка рельефа на выпуклые блоки коллизий.

Блок — выпуклая оболочка вершин группы соседних треугольников рельефа и их
проекций на отметку низа. Группы объединяются, пока оболочка в плане совпадает
с группой, а её верх поднимается над рельефом не больше чем на допуск.
"""
import itertools
import numpy as np
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon, MultiPoint
from shapely.ops import unary_union


def bary_samples(n=8):
    pts = []
    for i in range(n + 1):
        for j in range(n + 1 - i):
            pts.append((i / n, j / n, 1 - (i + j) / n))
    return np.array(pts)


class Blocks:
    def __init__(self, W, top, zbot, tol):
        self.W, self.top, self.zbot, self.tol = W, top, zbot, tol
        S = bary_samples()
        self.samples = [S @ W[t] for t in top]          # точки на поверхности каждого треугольника
        self.tripoly = [Polygon(W[t][:, :2]) for t in top]
        self.cache = {}

    def hull(self, tris):
        vid = sorted({int(i) for t in tris for i in self.top[t]})
        P = self.W[vid]
        B = P.copy(); B[:, 2] = self.zbot
        return ConvexHull(np.vstack([P, B])), vid

    def check(self, tris):
        key = frozenset(tris)
        if key in self.cache:
            return self.cache[key]
        plan = unary_union([self.tripoly[t] for t in tris])
        ok = False
        dev = None
        if plan.geom_type == 'Polygon' and not plan.interiors:
            if plan.convex_hull.area - plan.area < 1e-6 * plan.area:
                h, _ = self.hull(tris)
                eq = h.equations[h.equations[:, 2] > 1e-9]       # верхние грани: n·x + d = 0
                pts = np.vstack([self.samples[t] for t in tris])
                ztop = np.min(-(pts[:, :2] @ eq[:, :2].T + eq[:, 3]) / eq[:, 2], axis=1)
                dev = float(np.max(ztop - pts[:, 2]))
                ok = dev <= self.tol
        self.cache[key] = (ok, dev)
        return ok, dev

    def adjacency(self):
        edges = {}
        for ti, t in enumerate(self.top):
            for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                edges.setdefault(frozenset((int(a), int(b))), []).append(ti)
        return [tuple(v) for v in edges.values() if len(v) == 2]

    def greedy(self, rng):
        groups = {i: [i] for i in range(len(self.top))}
        owner = {i: i for i in range(len(self.top))}
        adj = self.adjacency()
        changed = True
        while changed:
            changed = False
            pairs = sorted({tuple(sorted((owner[a], owner[b]))) for a, b in adj if owner[a] != owner[b]})
            rng.shuffle(pairs)
            best = None
            for a, b in pairs:
                ok, dev = self.check(groups[a] + groups[b])
                if ok and (best is None or dev < best[0]):
                    best = (dev, a, b)
                    if rng.random() < 0.35:
                        break
            if best:
                _, a, b = best
                groups[a] = groups[a] + groups.pop(b)
                for t in groups[a]:
                    owner[t] = a
                changed = True
        return list(groups.values())

    def solve(self, tries=300, seed=1):
        rng = np.random.default_rng(seed)
        best = None
        for _ in range(tries):
            g = self.greedy(rng)
            score = (len(g), max(self.check(x)[1] for x in g))
            if best is None or score < best[0]:
                best = (score, g)
        return best
