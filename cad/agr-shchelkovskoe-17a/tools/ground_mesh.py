"""Рельеф из FBX благоустройства: верхняя поверхность основного блока."""
import numpy as np
import fbxio


def polys(pvi):
    out, cur = [], []
    for i in pvi:
        if i < 0:
            cur.append(~i); out.append(cur); cur = []
        else:
            cur.append(i)
    return out


def meshes(f):
    objs = f.one('Objects'); conn = f.one('Connections')
    byid = {k.vals()[0]: k for k in objs.kids}
    out = {}
    for c in conn.kids:
        v = c.vals(); a, b = byid.get(v[1]), byid.get(v[2])
        if a is None or b is None or a.name != 'Geometry' or b.name != 'Model':
            continue
        nm = b.vals()[1].split('\x00')[0]
        V = np.array(a.one('Vertices').props[0].value).reshape(-1, 3)
        out[nm] = (V, polys(a.one('PolygonVertexIndex').props[0].value), a, b)
    return out


def terrain(V, T):
    """Основной связный блок рельефа -> (вершины, верхние треугольники, боковые, нижние)."""
    T = np.array(T)
    key = {}
    idx = np.array([key.setdefault(tuple(p), len(key)) for p in np.round(V, 4)])
    W = np.zeros((len(key), 3))
    W[idx] = V
    Tw = idx[T]
    parent = list(range(len(key)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for t in Tw:
        a = find(t[0])
        for j in t[1:]:
            b = find(j)
            if a != b:
                parent[b] = a
    comp = {}
    for ti, t in enumerate(Tw):
        comp.setdefault(find(t[0]), []).append(ti)
    main = max(comp.values(), key=len)
    main = max(comp.values(), key=lambda tis: np.linalg.norm(
        np.cross(W[Tw[tis]][:, 1] - W[Tw[tis]][:, 0], W[Tw[tis]][:, 2] - W[Tw[tis]][:, 0]), axis=1).sum())
    tri = Tw[main]
    n = np.cross(W[tri][:, 1] - W[tri][:, 0], W[tri][:, 2] - W[tri][:, 0])
    nz = n[:, 2] / np.linalg.norm(n, axis=1)
    return W, tri[nz > 0.3], tri[np.abs(nz) <= 0.3], tri[nz < -0.3]
