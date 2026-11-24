"""Перспектива модели АГР (ВПМ здания + ВПМ благоустройства) с текстурами, солнцем и тенями — без внешних
рендереров: растеризация треугольников numpy, перспективно-корректные текстурные координаты, карта теней.

    python3 render_persp.py <папка ВПМ здания> <папка ВПМ благоустройства> <куда.png> <азимут°> <угол°> <дист.м>

Камера смотрит на центр здания; азимут — откуда смотрим (0 — с севера, 90 — с востока), угол — над горизонтом.
Вне модели благоустройства — нейтральная земля, небо — градиент.
"""
import glob
import json
import os
import re
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'agr-shchelkovskoe-17a',
                                'tools'))
import fbxio  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def load(folder, offset=(0.0, 0.0)):
    fbx = [p for p in glob.glob(os.path.join(folder, '*.fbx')) if not p.endswith('_Light.fbx')][0]
    f = fbxio.Fbx(fbx)
    objs, conn = f.one('Objects'), f.one('Connections')
    byid = {k.props[0].value: k for k in objs.kids}
    geom, mats = {}, {}
    for c in conn.kids:
        a, b = byid.get(c.props[1].value), byid.get(c.props[2].value)
        if a is None or b is None or b.name != 'Model':
            continue
        if a.name == 'Geometry':
            geom[c.props[2].value] = a
        elif a.name == 'Material':
            mats.setdefault(c.props[2].value, []).append(a.props[1].value.split('\x00')[0])
    tiles, alphas = {}, {}
    for p in glob.glob(os.path.join(folder, '*Diffuse*.png')):
        m = re.search(r'_(\d)\.(\d{4})\.png$', p)
        im = Image.open(p)
        key = (int(m.group(1)), int(m.group(2)))
        if im.mode == 'RGBA':
            a = im.getchannel('A')
            if a.width > 1024:
                a = a.resize((1024, 1024), Image.LANCZOS)
            alphas[key[1]] = np.asarray(a)
        im = im.convert('RGB')
        if im.width > 1024:
            im = im.resize((1024, 1024), Image.LANCZOS)
        tiles[key] = np.asarray(im)
    T = []
    for mid, g in geom.items():
        nm = byid[mid].props[1].value.split('\x00')[0]
        if nm.startswith('UCX_'):
            continue
        t = np.zeros(3)
        for c in byid[mid].one('Properties70').kids:
            if c.props[0].value == 'Lcl Translation':
                t = np.array([c.props[i].value for i in (4, 5, 6)])
        V = np.array(g.one('Vertices').props[0].value).reshape(-1, 3) + t + np.array([offset[0], offset[1], 0])
        pvi = g.one('PolygonVertexIndex').props[0].value
        UV = None
        if g.find('LayerElementUV'):
            lu = g.find('LayerElementUV')[0]
            uvv = np.array(lu.one('UV').props[0].value).reshape(-1, 2)
            UV = uvv[np.array(lu.one('UVIndex').props[0].value)] \
                if lu.one('ReferenceInformationType').props[0].value == 'IndexToDirect' else uvv
        glass = 'Glass' in nm
        cur, s0 = [], 0
        for i, x in enumerate(pvi):
            cur.append(~x if x < 0 else x)
            if x < 0:
                for k in range(1, len(cur) - 1):
                    ii = [0, k, k + 1]
                    uv = None if UV is None else UV[[s0 + j for j in ii]]
                    al = None
                    if uv is not None and alphas:
                        cu = uv.mean(0)
                        tid = 1001 + int(np.floor(cu[0])) + 10 * int(np.floor(cu[1]))
                        al = alphas.get(tid)
                    T.append((V[[cur[j] for j in ii]], uv, glass, al))
                cur, s0 = [], i + 1
    return T, tiles


def look(eye, target):
    f = target - eye
    f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1.0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return np.stack([r, u, -f]), eye


def sample(tiles, uv):
    u, v = uv[:, 0], uv[:, 1]
    tu, tv = np.floor(u).astype(int), np.floor(v).astype(int)
    tid = 1001 + tu + 10 * tv
    col = np.full((len(u), 3), 180.0)
    for t in np.unique(tid):
        tex = tiles.get((1, int(t)))
        if tex is None:
            continue
        s = tid == t
        h, w = tex.shape[:2]
        px = np.clip(((u[s] - tu[s]) * w).astype(int), 0, w - 1)
        py = np.clip(((1 - (v[s] - tv[s])) * h).astype(int), 0, h - 1)
        col[s] = tex[py, px]
    return col


def raster(tris, proj, W, H, want_attr=True):
    """tris: [(P(3x3 мир), UV|None, glass, tex_id)] -> zbuf, attr (номер треугольника, барицентрики)."""
    zb = np.full((H, W), np.inf)
    tri_id = np.full((H, W), -1, np.int64)
    bary = np.zeros((H, W, 3), np.float32)
    for n, (P, UV, glass, src, alpha) in enumerate(tris):
        s, wz = proj(P)                              # экранные координаты (3x2) и глубина вида (3)
        if np.any(wz <= 0.5):
            continue
        x0, x1 = int(max(np.floor(s[:, 0].min()), 0)), int(min(np.ceil(s[:, 0].max()), W))
        y0, y1 = int(max(np.floor(s[:, 1].min()), 0)), int(min(np.ceil(s[:, 1].max()), H))
        if x1 <= x0 or y1 <= y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        d = (s[1, 1] - s[2, 1]) * (s[0, 0] - s[2, 0]) + (s[2, 0] - s[1, 0]) * (s[0, 1] - s[2, 1])
        if abs(d) < 1e-9:
            continue
        a = ((s[1, 1] - s[2, 1]) * (xs - s[2, 0]) + (s[2, 0] - s[1, 0]) * (ys - s[2, 1])) / d
        b = ((s[2, 1] - s[0, 1]) * (xs - s[2, 0]) + (s[0, 0] - s[2, 0]) * (ys - s[2, 1])) / d
        c = 1 - a - b
        m = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6)
        if not m.any():
            continue
        yy, xx = np.nonzero(m)
        A, B, C = a[yy, xx], b[yy, xx], c[yy, xx]
        # перспективно-корректные веса
        iw = A / wz[0] + B / wz[1] + C / wz[2]
        z = 1.0 / iw
        if alpha is not None:                         # листва и т. п.: прозрачные пиксели пропускаются
            wb = np.stack([A / wz[0], B / wz[1], C / wz[2]], 1) * z[:, None]
            uv = wb @ UV
            fu, fv = uv[:, 0] - np.floor(uv[:, 0]), uv[:, 1] - np.floor(uv[:, 1])
            ah, aw = alpha.shape
            av = alpha[np.clip(((1 - fv) * ah).astype(int), 0, ah - 1), np.clip((fu * aw).astype(int), 0, aw - 1)]
            keep = av > 127
            yy, xx, A, B, C, z = yy[keep], xx[keep], A[keep], B[keep], C[keep], z[keep]
            if not len(z):
                continue
        Y, X = yy + y0, xx + x0
        front = z < zb[Y, X] - 1e-4
        if not front.any():
            continue
        Y, X, z = Y[front], X[front], z[front]
        zb[Y, X] = z
        if want_attr:
            tri_id[Y, X] = n
            bary[Y, X, 0] = (A[front] / wz[0]) * z
            bary[Y, X, 1] = (B[front] / wz[1]) * z
            bary[Y, X, 2] = (C[front] / wz[2]) * z
    return zb, tri_id, bary


def main(bfold, gfold, out, az_deg, el_deg, dist, W=2400, H=1400, ss=2, fov=34.0):
    bj = json.load(open(glob.glob(os.path.join(bfold, '*.geojson'))[0], encoding='utf-8'))
    gj = json.load(open(glob.glob(os.path.join(gfold, '*.geojson'))[0], encoding='utf-8'))
    bp, gp = np.array(bj['features'][0]['geometry']['coordinates']), np.array(gj['features'][0]['geometry']['coordinates'])
    TB, texb = load(bfold)
    TG, texg = load(gfold, offset=gp - bp)
    TG = [t for t in TG if t[0][:, 2].min() > -0.3]     # без заглубления контура (требование к ВПМ, не видно)
    tris = [(P, UV, g, 'b', al) for P, UV, g, al in TB] + [(P, UV, g, 'g', al) for P, UV, g, al in TG]
    tex = {'b': texb, 'g': texg}
    allP = np.concatenate([t[0] for t in TB])
    tgt = np.array([(allP[:, 0].min() + allP[:, 0].max()) / 2, (allP[:, 1].min() + allP[:, 1].max()) / 2, 4.0])
    az, el = np.radians(az_deg), np.radians(el_deg)
    eye = tgt + dist * np.array([np.sin(az) * np.cos(el), np.cos(az) * np.cos(el), np.sin(el)])
    R, E = look(eye, tgt)
    Wp, Hp = W * ss, H * ss
    fpx = (Wp / 2) / np.tan(np.radians(fov) / 2)

    def proj(P):
        q = (P - E) @ R.T
        wz = -q[:, 2]
        return np.stack([Wp / 2 + fpx * q[:, 0] / wz, Hp / 2 - fpx * q[:, 1] / wz], 1), wz

    print('треугольников', len(tris))
    zb, tid, bary = raster(tris, proj, Wp, Hp)
    # солнце и карта теней
    sun = np.array([np.sin(np.radians(205)) * np.cos(np.radians(38)), np.cos(np.radians(205)) * np.cos(np.radians(38)),
                    np.sin(np.radians(38))])
    sun /= np.linalg.norm(sun)
    Rs, _ = look(tgt + sun * 300, tgt)
    SM = 3072
    allW = np.concatenate([t[0] for t in tris])
    q = (allW - tgt) @ Rs.T
    ext = max(np.abs(q[:, 0]).max(), np.abs(q[:, 1]).max()) * 1.02

    def sproj(P):
        q = (P - (tgt + sun * 300)) @ Rs.T
        return np.stack([SM / 2 + q[:, 0] / ext * SM / 2, SM / 2 - q[:, 1] / ext * SM / 2], 1), -q[:, 2]
    szb, _, _ = raster(tris, sproj, SM, SM, want_attr=False)
    # закраска
    img = np.zeros((Hp, Wp, 3))
    yy, xx = np.mgrid[0:Hp, 0:Wp]
    sky_t = np.clip(yy / Hp, 0, 1)[..., None]
    img[:] = (np.array([196, 214, 232]) * (1 - sky_t) + np.array([233, 238, 242]) * sky_t)
    # земля вне модели — плоскость z = -0.02
    dirs = np.stack([(xx + 0.5 - Wp / 2) / fpx, -(yy + 0.5 - Hp / 2) / fpx, -np.ones_like(xx, float)], -1) @ R
    tg = (-0.05 - E[2]) / np.where(dirs[..., 2] < -1e-6, dirs[..., 2], -1e-6)
    ground = (dirs[..., 2] < -1e-6) & (tid < 0)
    gp_w = E + dirs * tg[..., None]
    fog = np.clip((tg - dist) / (dist * 6), 0, 1)[..., None]
    base_g = np.array([214, 214, 208]) * (1 - fog) + np.array([232, 235, 238]) * fog
    img[ground] = base_g[ground]
    # тени на земле вне модели
    hit = tid >= 0
    idx = tid[hit]
    b = bary[hit]
    Pw = np.zeros((len(idx), 3))
    cols = np.zeros((len(idx), 3))
    nrm = np.zeros((len(idx), 3))
    glass = np.zeros(len(idx), bool)
    order = np.argsort(idx)
    idx_s = idx[order]
    starts = np.r_[0, np.nonzero(np.diff(idx_s))[0] + 1]
    ends = np.r_[starts[1:], len(idx_s)]
    for s0, s1 in zip(starts, ends):
        n = idx_s[s0]
        sel = order[s0:s1]
        P, UV, gl, src, _ = tris[n]
        bb = b[sel]
        Pw[sel] = bb @ P
        nv = np.cross(P[1] - P[0], P[2] - P[0])
        nv /= (np.linalg.norm(nv) + 1e-12)
        if nv @ (E - P[0]) < 0:
            nv = -nv
        if tris[n][4] is not None:                    # листва: свет без направленности
            nv = np.array([0.0, 0.0, 1.0]) * 0.6 + sun * 0.4
        nrm[sel] = nv
        glass[sel] = gl
        if UV is not None and not gl:
            cols[sel] = sample(tex[src], bb @ UV)
        else:
            cols[sel] = (150, 176, 205)
    # тени
    allpts = np.zeros((Hp, Wp, 3)); allpts[hit] = Pw
    allpts[ground] = gp_w[ground]
    lit_mask = hit | ground
    pts = allpts[lit_mask]
    sq, sd = sproj(pts)
    ix = np.clip(sq[:, 0].astype(int), 0, SM - 1)
    iy = np.clip(sq[:, 1].astype(int), 0, SM - 1)
    shadow = sd > szb[iy, ix] + 0.08
    shadow_img = np.zeros((Hp, Wp), bool)
    shadow_img[lit_mask] = shadow
    # освещение модели
    lam = np.clip(nrm @ sun, 0, 1)
    sh = shadow_img[hit]
    light = 0.55 + 0.55 * lam * (~sh)
    skyl = 0.08 * np.clip(nrm[:, 2], 0, 1)
    c = cols * (light + skyl)[:, None]
    # стекло: отражение неба
    gsel = glass
    if gsel.any():
        vdir = Pw[gsel] - E
        vdir /= np.linalg.norm(vdir, axis=1)[:, None]
        refl = vdir - 2 * (vdir * nrm[gsel]).sum(1)[:, None] * nrm[gsel]
        tsky = np.clip(refl[:, 2] * 1.5 + 0.3, 0, 1)[:, None]
        c[gsel] = (np.array([110, 135, 160]) * (1 - tsky) + np.array([200, 218, 235]) * tsky) * (0.85 + 0.15 * (~sh[gsel]))[:, None]
    img[hit] = c
    gs = shadow_img & ground
    img[gs] = img[gs] * 0.72
    # воздушная перспектива по глубине
    out_img = np.clip(img, 0, 255).astype(np.uint8)
    im = Image.fromarray(out_img).resize((W, H), Image.LANCZOS)
    im.save(out, quality=94)
    print(out, im.size)


if __name__ == '__main__':
    a = sys.argv
    main(a[1], a[2], a[3], float(a[4]), float(a[5]), float(a[6]))
