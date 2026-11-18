"""Правка моделей АГР «Производственное здание», Восточная коммунальная зона, пр. 4921 (77:10:0005004:1443).

fix_models.py ВПМ_ЗДАНИЯ ВПМ_БЛАГОУСТРОЙСТВА НПМ ВЫХОД — папки с распакованными архивами, ВЫХОД — новые ZIP.

* geojson ВПМ: адрес, район, опечатка в наименовании, номер действующего САГР, s_podz числом,
  параметры стекол числами — значения правятся в тексте, структура и порядок полей не меняются;
* НПМ: здание и благоустройство переносятся в координаты МСК-77 из geojson ВПМ (в НПМ они стояли
  на 7,5 км западнее и 17,7 км южнее — район Строгино), пути к текстурам на диске автора убираются;
* архивы называются по маскам требований: SM_<адрес>.zip, SM_<адрес>_Ground.zip, 1010_<адрес>.zip.
FBX ВПМ не меняются (файлы копируются как есть).
"""
import json
import os
import re
import shutil
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'agr-shchelkovskoe-17a', 'tools'))
import fbxio  # noqa: E402

ADDR = '77_10_0005004_1443'
ADDRESS = 'Восточная коммунальная зона, пр. 4921'      # как в заявлении arh-20261013-405
RAJON = 'Савёлки'
SAGR = '466-5-22/С'                                     # действующее свидетельство от 21.07.2022


def fix_geojson(src, dst, building):
    s = open(src, encoding='utf-8').read()
    reps = [
        (r'("address": )"77:10:0005004:1443"', r'\1"%s"' % ADDRESS),
        (r'("rajon": )"Савелки"', r'\1"%s"' % RAJON),
        (r'роизводсвтенн', 'роизводственн'),
        (r'("act_AGR": )""', r'\1"%s"' % SAGR),
    ]
    if building:
        reps += [(r'("s_podz": )"0"', r'\g<1>0')]
        reps += [(r'("(transparency|refraction|roughness|metallicity)": )"([0-9.]+)"', r'\1\3')]
    for a, b in reps:
        s, n = re.subn(a, b, s)
        assert n >= 1, (a, src)
    j = json.loads(s)                       # проверка, что JSON цел
    pr = j['features'][0]['properties']
    assert pr['address'] == ADDRESS and pr['act_AGR'] == SAGR and 'свтен' not in pr['name']
    open(dst, 'w', encoding='utf-8', newline='\n').write(s)
    return j['features'][0]['geometry']['coordinates']


def neutral_paths(f, fname):
    """Абсолютные пути (C:\\Users\\...) заменить на относительные/имя файла."""
    n = 0

    def walk(node):
        nonlocal n
        rel = None
        for k in node.kids:
            if k.name == 'RelativeFilename' and k.props:
                rel = k.props[0].value
        for k in node.kids:
            if k.name in ('FileName', 'Filename') and k.props and k.props[0].t == 'S' and ':\\' in k.props[0].value:
                k.props[0].set(rel if rel else k.props[0].value.split('\\')[-1])
                n += 1
            walk(k)
        if node.name == 'Properties70':
            for k in node.kids:
                for p in k.props:
                    if p.t == 'S' and ':\\' in p.value and 'Users' in p.value:
                        p.set('C:\\Projects\\' + fname)
                        n += 1
    for t in f.top:
        walk(t)
    return n


def move_npm(path, out, place):
    """place: {имя модели: (x, y)} — новые Lcl Translation по X, Y (Z без изменений)."""
    f = fbxio.Fbx(path)
    done = set()
    for k in f.one('Objects').kids:
        if k.name != 'Model':
            continue
        nm = k.props[1].value.split('\x00')[0]
        for c in k.one('Properties70').kids:
            if c.props[0].value == 'Lcl Translation':
                x, y = place[nm]
                c.props[4].set(float(x))
                c.props[5].set(float(y))
                done.add(nm)
    assert done == set(place), (done, place)
    n = neutral_paths(f, os.path.basename(out))
    open(out, 'wb').write(f.dumps())
    return n


def zipdir(folder, out):
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(folder)):
            z.write(os.path.join(folder, name), name)


def main(vb, vg, npm, out):
    os.makedirs(out, exist_ok=True)
    tmp = os.path.join(out, '_build')
    shutil.rmtree(tmp, ignore_errors=True)
    # ВПМ здания и благоустройства
    pts = {}
    for src, base, building in ((vb, 'SM_%s' % ADDR, True), (vg, 'SM_%s_Ground' % ADDR, False)):
        d = os.path.join(tmp, base)
        os.makedirs(d)
        for name in os.listdir(src):
            if name.endswith('.geojson'):
                pts[base] = fix_geojson(os.path.join(src, name), os.path.join(d, name), building)
            else:
                shutil.copy2(os.path.join(src, name), os.path.join(d, name))
        zipdir(d, os.path.join(out, base + '.zip'))
    # НПМ
    d = os.path.join(tmp, '1010_' + ADDR)
    os.makedirs(d)
    bx, by = pts['SM_%s' % ADDR]
    gx, gy = pts['SM_%s_Ground' % ADDR]
    n1 = move_npm(os.path.join(npm, '1010_%s_01.fbx' % ADDR), os.path.join(d, '1010_%s_01.fbx' % ADDR),
                  {'SM_%s_001_Main' % ADDR: (bx, by)})
    n2 = move_npm(os.path.join(npm, '1010_%s_Ground.fbx' % ADDR), os.path.join(d, '1010_%s_Ground.fbx' % ADDR),
                  {'SM_%s_%s' % (ADDR, s): (gx, gy) for s in ('Ground', 'GroundEl', 'Flora')})
    zipdir(d, os.path.join(out, '1010_%s.zip' % ADDR))
    print('ВПМ: точки вставки', pts, '; НПМ перенесена, путей к файлам автора убрано:', n1 + n2)


if __name__ == '__main__':
    main(*sys.argv[1:5])
