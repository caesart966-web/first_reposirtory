"""Правка архивов ВПМ (здание и благоустройство).

    python3 fix_vpm.py <папка здания> <папка благоустройства> <куда> <площадь>

Что делается:
  * в обоих FBX пути к рабочим файлам автора заменяются нейтральными;
  * в FBX благоустройства коллизии пересобираются: выпуклые блоки по рельефу
    с именами UCX_SM_<адрес>_Ground_NNN;
  * слой цвета вершин, целиком белый, из сетки благоустройства убирается;
  * текстуры в палитровом режиме переводятся в RGB;
  * в geojson здания обновляются s_obsh и s_naz.
"""
import copy
import json
import os
import shutil
import struct
import sys

import numpy as np
from PIL import Image
from scipy.spatial import ConvexHull

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fbxio          # noqa: E402
import ground_mesh    # noqa: E402
import ucx_blocks     # noqa: E402
import pngrgb         # noqa: E402

ADDR = 'ShchelkovskoeShosse_17A_1'
ROOT = 'C:\\Projects\\' + ADDR
TOL = 0.01          # допуск по высоте для блоков коллизий, м


def f32(a):
    """Числа с точностью float32, как их пишет 3ds Max."""
    return [float(x) for x in np.asarray(a, dtype=np.float32).ravel()]


def set_paths(f, base):
    p70 = f.one('FBXHeaderExtension').one('SceneInfo').one('Properties70')
    new = {
        'DocumentUrl': ROOT + '\\' + base + '.fbx',
        'SrcDocumentUrl': ROOT + '\\' + base + '.fbx',
        'Original|FileName': ROOT + '\\' + base + '.fbx',
        'Original|ApplicationActiveProject': ROOT,
        'Original|ApplicationNativeFile': ROOT + '\\' + base + '.max',
    }
    done = set()
    for p in p70.kids:
        k = p.props[0].value
        if k in new:
            p.props[4].set(new[k])
            done.add(k)
    assert done == set(new), set(new) - done


def edges(pvi):
    seen, out, i = set(), [], 0
    while i < len(pvi):
        j = i
        while pvi[j] >= 0:
            j += 1
        n = j - i + 1
        for k in range(n):
            a = pvi[i + k]; a = a if a >= 0 else ~a
            b = pvi[i + (k + 1) % n]; b = b if b >= 0 else ~b
            key = (min(a, b), max(a, b))
            if key not in seen:
                seen.add(key); out.append(i + k)
        i = j + 1
    return out


def hull_mesh(points):
    """Выпуклая оболочка -> (вершины, треугольники наружу, нормали граней)."""
    h = ConvexHull(points)
    vid = list(h.vertices)
    remap = {v: i for i, v in enumerate(vid)}
    V = points[vid]
    tris, nrm = [], []
    for s, eq in zip(h.simplices, h.equations):
        a, b, c = points[s]
        if np.dot(np.cross(b - a, c - a), eq[:3]) < 0:
            s = s[[0, 2, 1]]
        tris.append([remap[int(i)] for i in s])
        nrm.append(eq[:3])
    # порядок граней: сначала верх, затем бока, затем низ — как удобнее читать в редакторе
    order = sorted(range(len(tris)), key=lambda i: (-round(nrm[i][2], 3), tris[i]))
    return V, [tris[i] for i in order], [nrm[i] for i in order]


def rebuild_ground_ucx(f):
    M = ground_mesh.meshes(f)
    main = 'SM_%s_Ground' % ADDR
    V, T, geom, model = M[main]
    W, top, side, _ = ground_mesh.terrain(V, T)
    zbot = float(W[side].reshape(-1, 3)[:, 2].min())
    B = ucx_blocks.Blocks(W, top, zbot, TOL)
    (n, dev), groups = B.solve(tries=1500, seed=7)

    def centroid(g):
        return np.mean([W[top[t]][:, :2].mean(0) for t in g], axis=0)
    groups.sort(key=lambda g: (round(float(centroid(g)[0]), 1), float(centroid(g)[1])))

    old = sorted(k for k in M if k.startswith('UCX'))
    tmpl_geom, tmpl_model = M[old[1]][2], M[old[1]][3]
    objs, conn = f.one('Objects'), f.one('Connections')
    drop = set()
    for k in old:
        drop.add(M[k][2].props[0].value); drop.add(M[k][3].props[0].value)
    used = {k.props[0].value for k in objs.kids}
    gid = max(k.props[0].value for k in objs.kids if k.name == 'Geometry')
    mid = max(k.props[0].value for k in objs.kids if k.name == 'Model')
    handle = max(p.props[4].value for k in objs.kids if k.name == 'Model'
                 for p in k.one('Properties70').kids if p.props[0].value == 'MaxHandle')

    new_geoms, new_models, stats = [], [], []
    for i, g in enumerate(groups, 1):
        vid = sorted({int(v) for t in g for v in top[t]})
        P = W[vid]
        Bm = P.copy(); Bm[:, 2] = zbot
        HV, tris, nrm = hull_mesh(np.vstack([P, Bm]))
        pvi = []
        for t in tris:
            pvi += [t[0], t[1], ~t[2]]
        normals = []
        for nv in nrm:
            normals += list(nv) * 3

        gnode = copy.deepcopy(tmpl_geom)
        gid += 480
        while gid in used:
            gid += 480
        used.add(gid)
        gnode.props[0].set(gid)
        gnode.one('Vertices').props[0].set(f32(HV))
        gnode.one('PolygonVertexIndex').props[0].set(pvi)
        gnode.one('Edges').props[0].set(edges(pvi))
        ln = gnode.one('LayerElementNormal')
        ln.one('Normals').props[0].set(f32(normals))
        ln.one('NormalsW').props[0].set([0.0] * len(pvi))
        new_geoms.append(gnode)

        mnode = copy.deepcopy(tmpl_model)
        mid += 2192
        while mid in used:
            mid += 2192
        used.add(mid)
        handle += 1
        mnode.props[0].set(mid)
        mnode.props[1].set('UCX_SM_%s_Ground_%03d\x00\x01Model' % (ADDR, i))
        for p in mnode.one('Properties70').kids:
            if p.props[0].value == 'MaxHandle':
                p.props[4].set(handle)
        new_models.append(mnode)
        stats.append((len(HV), len(tris), B.check(g)[1]))

    keep = [k for k in objs.kids if k.props[0].value not in drop]
    geoms = [k for k in keep if k.name == 'Geometry']
    models = [k for k in keep if k.name == 'Model']
    rest = [k for k in keep if k.name not in ('Geometry', 'Model')]
    objs.kids = new_geoms + geoms + new_models + models + rest

    c_tmpl = conn.kids[0]
    links = [c for c in conn.kids if c.props[1].value not in drop and c.props[2].value not in drop]

    def link(a, b):
        c = copy.deepcopy(c_tmpl)
        c.props[1].set(a); c.props[2].set(b)
        return c
    root = [c for c in links if c.props[2].value == 0]
    other = [c for c in links if c.props[2].value != 0]
    conn.kids = ([link(m.props[0].value, 0) for m in new_models] + root
                 + [link(g.props[0].value, m.props[0].value) for g, m in zip(new_geoms, new_models)] + other)

    defs = f.one('Definitions')
    total = 0
    for ot in defs.find('ObjectType'):
        kind = ot.props[0].value
        if kind in ('Model', 'Geometry'):
            ot.one('Count').props[0].set(sum(1 for k in objs.kids if k.name == kind))
        total += ot.one('Count').props[0].value
    defs.one('Count').props[0].set(total)
    return stats, dev


def drop_white_vertex_colour(f):
    geom = ground_mesh.meshes(f)['SM_%s_Ground' % ADDR][2]
    lc = geom.find('LayerElementColor')
    if not lc:
        return False
    col = np.array(lc[0].one('Colors').props[0].value)
    assert np.all(col == 1.0), 'цвет вершин не белый — слой оставляем'
    geom.kids = [k for k in geom.kids if k.name != 'LayerElementColor']
    layer = geom.one('Layer')
    layer.kids = [k for k in layer.kids
                  if not (k.name == 'LayerElement' and k.one('Type').props[0].value == 'LayerElementColor')]
    return True


def copy_textures(src, dst):
    changed = []
    for name in sorted(os.listdir(src)):
        if not name.lower().endswith('.png'):
            continue
        a, b = os.path.join(src, name), os.path.join(dst, name)
        im = Image.open(a)
        if im.mode == 'RGB':
            shutil.copy2(a, b)
            continue
        pngrgb.save_rgb(b, np.asarray(im.convert('RGB')), dpi=im.info.get('dpi'))
        changed.append((name, im.mode))
    return changed


def main(bdir, gdir, out, area):
    Image.MAX_IMAGE_PIXELS = None
    ob, og = os.path.join(out, 'SM_' + ADDR), os.path.join(out, 'SM_' + ADDR + '_Ground')
    for d in (ob, og):
        os.makedirs(d, exist_ok=True)
    report = {}

    f = fbxio.Fbx(os.path.join(bdir, 'SM_%s.fbx' % ADDR))
    set_paths(f, 'SM_' + ADDR)
    open(os.path.join(ob, 'SM_%s.fbx' % ADDR), 'wb').write(f.dumps())

    f = fbxio.Fbx(os.path.join(gdir, 'SM_%s_Ground.fbx' % ADDR))
    set_paths(f, 'SM_' + ADDR + '_Ground')
    stats, dev = rebuild_ground_ucx(f)
    report['ucx'] = {'blocks': len(stats), 'max_dev_m': dev, 'verts_tris_dev': stats}
    report['vertex_colour_removed'] = drop_white_vertex_colour(f)
    open(os.path.join(og, 'SM_%s_Ground.fbx' % ADDR), 'wb').write(f.dumps())

    report['textures_building'] = copy_textures(bdir, ob)
    report['textures_ground'] = copy_textures(gdir, og)

    # geojson: правка двух значений по тексту, чтобы остальной файл остался байт в байт
    src = open(os.path.join(bdir, 'SM_%s.geojson' % ADDR), 'rb').read()
    j = json.loads(src.decode('utf-8'))
    pr = j['features'][0]['properties']
    for key in ('s_obsh', 's_naz'):
        old = ('"%s": "%s"' % (key, pr[key])).encode('utf-8')
        assert src.count(old) == 1, key
        src = src.replace(old, ('"%s": "%s"' % (key, area)).encode('utf-8'))
    json.loads(src.decode('utf-8'))
    open(os.path.join(ob, 'SM_%s.geojson' % ADDR), 'wb').write(src)
    shutil.copy2(os.path.join(gdir, 'SM_%s_Ground.geojson' % ADDR), og)
    json.dump(report, open(os.path.join(out, 'vpm_report.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in report.items() if k != 'ucx'}, ensure_ascii=False))
    print('коллизий', len(stats), 'отклонение, м', round(dev, 4))


if __name__ == '__main__':
    main(*sys.argv[1:5])
