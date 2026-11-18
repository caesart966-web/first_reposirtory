"""Проверка архива ВПМ: имена, сетка, коллизии, развёртка, текстуры, geojson."""
import json, os, re, subprocess, sys
from collections import Counter
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fbxio, ground_mesh

Image.MAX_IMAGE_PIXELS = None


def check(folder, base, kind):
    ok = True
    def say(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        print('  %s %s' % ('+' if cond else 'ОШИБКА', msg))
    addr = base[3:-7] if kind == 'Ground' else base[3:]
    path = os.path.join(folder, base + '.fbx')
    raw = open(path, 'rb').read()
    f = fbxio.Fbx(path)
    say(f.dumps() == raw, 'файл читается и собирается обратно без расхождений')
    say(f.version == 7400, 'версия FBX 7400 (двоичный)')
    say(len(raw) % 16 == 0, 'длина файла кратна 16')
    p70 = f.one('FBXHeaderExtension').one('SceneInfo').one('Properties70')
    paths = [k.props[4].value for k in p70.kids
             if len(k.props) > 4 and isinstance(k.props[4].value, str) and '\\' in k.props[4].value]
    say(paths and all(x.startswith('C:\\Projects\\') for x in paths) and b'Users' not in raw,
        'пути в метаданных нейтральные, рабочих папок автора нет')
    M = ground_mesh.meshes(f)
    sm = [k for k in M if k.startswith('SM_')]
    ucx = sorted(k for k in M if k.startswith('UCX_'))
    say(set(M) == set(sm) | set(ucx), 'в сцене только SM_ и UCX_')
    want = {'SM_%s_%s' % (addr, kind)} if kind == 'Ground' else {'SM_%s_Main' % addr, 'SM_%s_MainGlass' % addr}
    say(set(sm) == want, 'сетки: ' + ', '.join(sorted(sm)))
    pat = re.compile(r'^UCX_SM_%s_%s_(\d{3})$' % (re.escape(addr), kind))
    nums = [int(pat.match(k).group(1)) for k in ucx if pat.match(k)]
    say(len(nums) == len(ucx) and nums == list(range(1, len(ucx) + 1)),
        'коллизии: %d шт., имена UCX_SM_%s_%s_001…%03d подряд' % (len(ucx), addr, kind, len(ucx)))
    tri_total = 0
    for k in M:
        V, P, g, m = M[k]
        sides = Counter(len(q) for q in P)
        if set(sides) != {3}:
            say(False, '%s: есть многоугольники %s' % (k, dict(sides)))
        tri_total += len(P)
        area = np.linalg.norm(np.cross(V[[q[1] for q in P]] - V[[q[0] for q in P]],
                                       V[[q[2] for q in P]] - V[[q[0] for q in P]]), axis=1) / 2
        if (area < 1e-10).any():
            say(False, '%s: вырожденных треугольников %d' % (k, int((area < 1e-10).sum())))
        ln = g.one('LayerElementNormal')
        nrm = np.array(ln.one('Normals').props[0].value).reshape(-1, 3)
        nn = len(nrm)
        if ln.one('ReferenceInformationType').props[0].value == 'IndexToDirect':     # так пишет Blender
            idx = np.array(ln.one('NormalsIndex').props[0].value)
            nn = len(idx) if idx.size and idx.max() < len(nrm) and idx.min() >= 0 else -1
        if nn != 3 * len(P) or abs(np.linalg.norm(nrm, axis=1) - 1).max() > 1e-4:
            say(False, '%s: нормали' % k)
        if g.find('LayerElementColor'):
            say(False, '%s: есть слой цвета вершин' % k)
    say(True, 'все сетки из треугольников, всего %d' % tri_total)
    worst = 0
    for k in ucx:
        V, P, g, m = M[k]
        ed = Counter()
        for q in P:
            for i in range(3):
                ed[(q[i], q[(i + 1) % 3])] += 1
        closed = all(n == 1 and ed[(b, a)] == 1 for (a, b), n in ed.items())
        out = 0.0
        cen = V.mean(0)
        outward = True
        for q in P:
            p = V[q]; n = np.cross(p[1] - p[0], p[2] - p[0]); n /= np.linalg.norm(n)
            out = max(out, float(((V - p[0]) @ n).max()))
            outward &= ((cen - p[0]) @ n) < 0
        worst = max(worst, out)
        if not (closed and outward and out < 1e-4 and len(set(i for q in P for i in q)) == len(V)):
            say(False, '%s: замкнута=%s наружу=%s выпуклость=%.5f' % (k, closed, outward, out))
    say(worst < 1e-4, 'все коллизии замкнутые и выпуклые (наибольший выход вершины за грань %.1e м)' % worst)
    # развёртка и плитки UDIM
    tiles = set()
    for k in sm:
        V, P, g, m = M[k]
        uvn = g.one('LayerElementUV')
        uv = np.array(uvn.one('UV').props[0].value).reshape(-1, 2)
        ix = np.array(uvn.one('UVIndex').props[0].value).reshape(-1, 3)
        t = np.floor(uv[ix]).astype(int)
        if not ((t == t[:, :1]).all()):
            say(False, '%s: треугольники развёртки пересекают границы плиток' % k)
        if (t < 0).any() or (t[:, :, 0] > 9).any():
            say(False, '%s: развёртка вне сетки UDIM' % k)
        tiles |= {1001 + int(u) + 10 * int(v) for u, v in np.unique(t[:, 0, :], axis=0)}
    pngs = sorted(x for x in os.listdir(folder) if x.endswith('.png'))
    tp = 'T_%s%s_' % (addr, '_Ground' if kind == 'Ground' else '')
    have = {}
    for x in pngs:
        m = re.match(re.escape(tp) + r'(Diffuse|ERM|Normal)_1\.(\d{4})\.png$', x)
        if not m:
            say(False, 'лишний или неверно названный файл ' + x); continue
        im = Image.open(os.path.join(folder, x))
        w, h = im.size
        good = im.mode == 'RGB' and w == h and w & (w - 1) == 0
        if not good:
            say(False, '%s: %s %s' % (x, im.mode, im.size))
        have.setdefault(int(m.group(2)), {})[m.group(1)] = im.size
    full = all(set(v) == {'Diffuse', 'ERM', 'Normal'} for v in have.values())
    say(full, 'у каждой плитки три карты: Diffuse, ERM, Normal; всего плиток %d' % len(have))
    say(tiles <= set(have), 'плитки развёртки %s обеспечены текстурами' % sorted(tiles))
    say(all(Image.open(os.path.join(folder, x)).mode == 'RGB' for x in pngs), 'все текстуры RGB, 8 бит на канал')
    # материалы
    objs = f.one('Objects')
    mats = sorted(k.props[1].value.split('\x00')[0] for k in objs.kids if k.name == 'Material')
    say(all(re.match(r'^M_%s_(Main|MainGlass|Ground|GroundGlass)_\d+$' % re.escape(addr), x) for x in mats),
        'материалы: ' + ', '.join(sorted(set(mats))))
    defs = f.one('Definitions')
    cnt = Counter(k.name for k in objs.kids)
    good = all(ot.one('Count').props[0].value == cnt[ot.props[0].value]
               for ot in defs.find('ObjectType') if ot.props[0].value != 'GlobalSettings')
    say(good and defs.one('Count').props[0].value == sum(cnt.values()) + 1, 'счётчики объектов в Definitions сходятся')
    ids = [k.props[0].value for k in objs.kids]
    conn = f.one('Connections')
    say(len(ids) == len(set(ids)) and all(c.props[1].value in ids and (c.props[2].value in ids or c.props[2].value == 0)
                                         for c in conn.kids), 'идентификаторы уникальны, связи ведут на существующие объекты')
    # независимое чтение
    r = subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ufbx_probe.py'), path],
                       capture_output=True, text=True)
    say(r.returncode == 0, 'ufbx: файл открывается')
    if r.returncode == 0:
        u = json.loads(r.stdout)
        say(sorted(n[0] for n in u['nodes']) == sorted(M), 'ufbx: узлов %d, имена совпадают' % len(u['nodes']))
        nt = sum(n[3] for n in u['nodes'])
        say(nt == tri_total and all(n[2] == n[3] for n in u['nodes']), 'ufbx: треугольников %d' % nt)
        say(u['warnings'] == 0 and u['version'] == 7400 and u['unit_m'] == 1.0,
            'ufbx: предупреждений нет, версия %d, единица — метр' % u['version'])
    # geojson
    j = json.load(open(os.path.join(folder, base + '.geojson'), encoding='utf-8'))
    pr = j['features'][0]['properties']
    say(pr.get('Наименование GeoJSON-файла') == base, 'geojson: имя файла внутри совпадает')
    print('  geojson:', {k: v for k, v in pr.items() if k != 'imageBase64' and v != ''}, j['features'][0]['geometry']['coordinates'])
    return ok


if __name__ == '__main__':
    r = []
    for folder in sys.argv[1:]:
        base = os.path.basename(folder.rstrip('/'))
        print(base)
        r.append(check(folder, base, 'Ground' if base.endswith('_Ground') else 'Main'))
    print('ИТОГ:', 'всё в порядке' if all(r) else 'ЕСТЬ ОШИБКИ')
