"""facades.py МОДЕЛЬ.fbx ПАПКА_ТЕКСТУР ВЫХОД_ПРЕФИКС — ортогональные фасады модели АГР для сверки с буклетом.

Рисует четыре фасада в осях здания (поворот в плане находится сам — по прямоугольнику наименьшей
площади вокруг выпуклой оболочки), цвет берется из карт диффузного цвета UDIM
(*Diffuse_<слот>.<плитка>.png), стекло — голубым. Масштаб — PX пикселей на метр.
Пишет ВЫХОД_from_<вид>.png, ВЫХОД_from_<вид>_edges.png (красным — разрывы глубины: двери, ворота,
швы), ВЫХОД_from_<вид>_zb.npy (глубина) и ВЫХОД_lohi.npy (габариты в осях здания).
Виды: from_-Y, from_+Y, from_-X, from_+X — с какой стороны смотрим; TOP=1 — вид сверху, NOROT=1 — без поворота.
Для НПМ: встроенную карту диффузного цвета сохранить в папку как X_Diffuse_1.1001.png.
"""
import glob, os, re, sys
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
src, texdir, out = sys.argv[1:4]
PX = 40                                  # пикселей на метр
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'agr-shchelkovskoe-17a', 'tools'))
import fbxio
f = fbxio.Fbx(src)
objs = f.one('Objects'); conn = f.one('Connections')
byid = {k.vals()[0]: k for k in objs.kids}
geom_of, mats_of = {}, {}
for c in conn.kids:
    v = c.vals(); a_, b_ = byid.get(v[1]), byid.get(v[2])
    if a_ is None or b_ is None or b_.name != 'Model':
        continue
    if a_.name == 'Geometry':
        geom_of[v[2]] = a_
    elif a_.name == 'Material':
        mats_of.setdefault(v[2], []).append(a_.vals()[1].split('\x00')[0])
tiles = {}
for p in glob.glob(os.path.join(texdir, '*Diffuse*.png')):
    m = re.search(r'_(\d)\.(\d{4})\.png$', p)
    tiles[(int(m.group(1)), int(m.group(2)))] = np.asarray(Image.open(p).convert('RGB'))
tris = []
for mid, g in geom_of.items():
    model = byid[mid]
    nm = model.vals()[1].split('\x00')[0]
    if nm.startswith('UCX_'):
        continue
    t = [0.0, 0.0, 0.0]
    for c in model.one('Properties70').kids:
        if c.props[0].value == 'Lcl Translation':
            t = [c.props[i].value for i in (4, 5, 6)]
    V = np.array(g.one('Vertices').props[0].value).reshape(-1, 3) + np.array(t)
    pvi = g.one('PolygonVertexIndex').props[0].value
    polys, cur, starts, k0 = [], [], [], 0
    for i, x in enumerate(pvi):
        if not cur:
            starts.append(i)
        if x < 0:
            cur.append(~x); polys.append(cur); cur = []
        else:
            cur.append(x)
    UV = None
    if g.find('LayerElementUV'):
        lu = g.find('LayerElementUV')[0]
        uvv = np.array(lu.one('UV').props[0].value).reshape(-1, 2)
        if lu.one('ReferenceInformationType').props[0].value == 'IndexToDirect':
            UV = uvv[np.array(lu.one('UVIndex').props[0].value)]
        else:
            UV = uvv
    fmat = [0] * len(polys)
    if g.find('LayerElementMaterial'):
        lm = g.find('LayerElementMaterial')[0]
        mv = lm.one('Materials').props[0].value
        fmat = mv if len(mv) == len(polys) else [mv[0]] * len(polys)
    names = mats_of.get(mid, [])
    glass = 'Glass' in nm
    for pi, poly in enumerate(polys):
        mn = names[fmat[pi]] if names and fmat[pi] < len(names) else ''
        mm = re.search(r'_(\d)$', mn)
        slot = int(mm.group(1)) if mm else 1
        s0 = starts[pi]
        for k in range(1, len(poly) - 1):
            ii = [0, k, k + 1]
            P = V[[poly[j] for j in ii]]
            tris.append((P, None if UV is None else UV[[s0 + j for j in ii]], slot, glass))
print('треугольников', len(tris))
allP = np.concatenate([t[0] for t in tris])
# поворот здания в плане: прямоугольник наименьшей площади по выпуклой оболочке
from scipy.spatial import ConvexHull
xy = allP[:, :2]
hull = xy[ConvexHull(xy).vertices]
best = None
for i in range(len(hull)):
    e = hull[(i + 1) % len(hull)] - hull[i]
    ang = np.arctan2(e[1], e[0])
    c_, s_ = np.cos(-ang), np.sin(-ang)
    r = hull @ np.array([[c_, -s_], [s_, c_]]).T
    area = np.ptp(r[:, 0]) * np.ptp(r[:, 1])
    if best is None or area < best[0]:
        best = (area, ang)
ang = best[1]
if os.environ.get('NOROT'):
    ang = 0.0
print('поворот здания, град:', round(np.degrees(ang), 3))
c_, s_ = np.cos(-ang), np.sin(-ang)
R = np.array([[c_, -s_, 0], [s_, c_, 0], [0, 0, 1]])
tris = [(P @ R.T, UV, slot, glass) for P, UV, slot, glass in tris]
allP = np.concatenate([t[0] for t in tris])
print('габарит в осях здания:', np.round(np.ptp(allP, axis=0), 2))
lo, hi = allP.min(0), allP.max(0)
np.save(out+'_lohi.npy', np.array([lo,hi]))
VIEWS = {   # имя: (ось по горизонтали, знак, ось глубины, знак «к зрителю»)
    'from_-Y': (0, 1, 1, -1), 'from_+Y': (0, -1, 1, 1), 'from_-X': (1, -1, 0, -1), 'from_+X': (1, 1, 0, 1)}
if os.environ.get('TOP'):
    VIEWS = {'top': None}
for name, spec in VIEWS.items():
    if spec is None:            # вид сверху: x вправо, y вверх, глубина z
        ax, sgn, dax, toward, vax = 0, 1, 2, 1, 1
    else:
        (ax, sgn, dax, toward), vax = spec, 2
    w = int((hi[ax] - lo[ax]) * PX) + 20
    h = int((hi[vax] - lo[vax]) * PX) + 20
    img = np.full((h, w, 3), 255, np.uint8)
    zb = np.full((h, w), -np.inf)
    for P, UV, slot, glass in tris:
        sx = ((P[:, ax] - lo[ax]) * sgn if sgn > 0 else (hi[ax] - P[:, ax])) * PX + 10
        sy = (hi[vax] - P[:, vax]) * PX + 10
        dz = P[:, dax] * toward                 # больше — ближе к зрителю
        x0, x1 = int(np.floor(sx.min())), int(np.ceil(sx.max()))
        y0, y1 = int(np.floor(sy.min())), int(np.ceil(sy.max()))
        if x1 <= x0 or y1 <= y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
        if abs(d) < 1e-12:
            continue
        a = ((sy[1] - sy[2]) * (xs - sx[2]) + (sx[2] - sx[1]) * (ys - sy[2])) / d
        b = ((sy[2] - sy[0]) * (xs - sx[2]) + (sx[0] - sx[2]) * (ys - sy[2])) / d
        c = 1 - a - b
        inside = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6)
        if not inside.any():
            continue
        yy, xx = np.nonzero(inside)
        Y, X = yy + y0, xx + x0
        ok = (X >= 0) & (X < w) & (Y >= 0) & (Y < h)
        yy, xx, Y, X = yy[ok], xx[ok], Y[ok], X[ok]
        A, Bc, C = a[yy, xx], b[yy, xx], c[yy, xx]
        z = A * dz[0] + Bc * dz[1] + C * dz[2]
        front = z > zb[Y, X] + 1e-4
        if not front.any():
            continue
        Y, X, A, Bc, C, z = Y[front], X[front], A[front], Bc[front], C[front], z[front]
        zb[Y, X] = z
        if glass or UV is None:
            img[Y, X] = (150, 175, 205) if glass else (180, 180, 180)
            continue
        u = A * UV[0, 0] + Bc * UV[1, 0] + C * UV[2, 0]
        v = A * UV[0, 1] + Bc * UV[1, 1] + C * UV[2, 1]
        tu, tv = np.floor(u).astype(int), np.floor(v).astype(int)
        tile_id = 1001 + tu + 10 * tv
        col = np.full((len(u), 3), 200, np.uint8)
        for tid in np.unique(tile_id):
            tex = tiles.get((slot, int(tid)))
            if tex is None:
                continue
            sel = tile_id == tid
            th, tw = tex.shape[:2]
            px = np.clip(((u[sel] - tu[sel]) * tw).astype(int), 0, tw - 1)
            py = np.clip(((1 - (v[sel] - tv[sel])) * th).astype(int), 0, th - 1)
            col[sel] = tex[py, px]
        img[Y, X] = col
    Image.fromarray(img).save('%s_%s.png' % (out, name))
    np.save('%s_%s_zb.npy' % (out, name), zb)
    # линии по разрывам глубины — чтобы были видны двери, ворота, швы
    zf = np.where(np.isfinite(zb), zb, -1e3)
    e = np.zeros(zb.shape, bool)
    e[:, 1:] |= np.abs(np.diff(zf, axis=1)) > 0.02
    e[1:, :] |= np.abs(np.diff(zf, axis=0)) > 0.02
    ed = img.copy(); ed[e] = (255, 40, 40)
    Image.fromarray(ed).save('%s_%s_edges.png' % (out, name))
    print(name, img.shape)
sys.stdout.flush()
os._exit(0)
