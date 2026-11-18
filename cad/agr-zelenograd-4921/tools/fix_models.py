"""Правка моделей АГР «Производственное здание», Восточная коммунальная зона, пр. 4921 (77:10:0005004:1443).

fix_models.py ВПМ_ЗДАНИЯ ВПМ_БЛАГОУСТРОЙСТВА НПМ ВЫХОД — папки с распакованными архивами, ВЫХОД — новые ZIP.

* geojson ВПМ: адрес, район, опечатка в наименовании, номер действующего САГР, s_podz числом,
  параметры стекол числами — значения правятся в тексте, структура и порядок полей не меняются;
* НПМ: здание и благоустройство переносятся в координаты МСК-77 из geojson ВПМ (в НПМ они стояли
  на 7,5 км западнее и 17,7 км южнее — район Строгино), пути к текстурам на диске автора убираются;
* цвета фасада по ведомости отделки буклета (лист 11): в текстурах обеих моделей остались цвета
  САГР 2022 года — RAL 7016 вместо RAL 7012 (нижний пояс, цоколь, двери, ворота, фасонные элементы)
  и RAL 7038 вместо RAL 7035 (верхний пояс); RAL 7042 совпадает. Значения RGB — те же, что
  в колористике буклета (листы 8–9), чтобы модель и буклет совпадали до пикселя;
* ТЭП и высоты по итогам кадастрового инженера (письмо 17.09.2026, отметки 31.03.2026): нуль 196,02 вместо
  196,51 (geojson обеих ВПМ, высота вставки НПМ — здание и земля опускаются вместе, земля в модели плоская
  на нуле), верх 11,94 / 207,96, наземная = общая 1510,8, СПП в ГНС 1470,5 — меньше наземной, как требует
  ДГП (отказ от 11.09.2026);
* лестница на кровлю выше парапета сжата по высоте: в модели верх +12,085, в буклете и по факту +11,94;
* архивы называются по маскам требований: SM_<адрес>.zip, SM_<адрес>_Ground.zip, 1010_<адрес>.zip.
Геометрия ВПМ меняется только у верха лестницы на кровлю; перекрашиваются карты диффузного цвета.
"""
import io
import json
import os
import re
import shutil
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'agr-shchelkovskoe-17a', 'tools'))
import fbxio  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

ADDR = '77_10_0005004_1443'
ADDRESS = 'Восточная коммунальная зона, пр. 4921'      # как в заявлении arh-20261013-405
RAJON = 'Савёлки'
SAGR = '466-5-22/С'                                     # действующее свидетельство от 21.07.2022
ZERO_OLD, ZERO = 196.51, 196.02                         # нуль в модели и по факту (пол 1 этажа)
TOP = 11.94                                             # верх лестницы на кровлю над нулем
TEP = {'h_relief': ZERO, 'h_otn': TOP, 'h_abs': round(ZERO + TOP, 2),
       's_obsh': 1510.8, 's_naz': 1510.8, 'spp_gns': 1470.5}
PARAPET = 10.93                                         # выше — только лестница
LADDER = ((21.0, 23.05), (-13.7, -12.15))               # лестница в плане, локальные X, Y модели здания
# цвет в модели -> цвет по ведомости отделки (RGB как в колористике буклета)
RECOLOR = [((56, 62, 66), (89, 97, 99), 'RAL 7016 -> RAL 7012'),
           ((176, 176, 169), (203, 208, 204), 'RAL 7038 -> RAL 7035')]
TOL = 3                                                 # разброс оттенка в запеченном атласе НПМ


def recolor(im):
    """Перекрасить пиксели палитры RECOLOR, сохранив их отклонение от основного цвета. -> (картинка, счет)."""
    mode = im.mode
    a = np.asarray(im.convert('RGBA')).astype(int)
    rgb = a[..., :3]
    n = {}
    for src, dst, name in RECOLOR:
        m = np.abs(rgb - np.array(src)).max(-1) <= TOL
        rgb[m] = np.clip(rgb[m] - np.array(src) + np.array(dst), 0, 255)
        n[name] = int(m.sum())
    out = Image.fromarray(a.astype(np.uint8), 'RGBA')
    return (out if mode == 'RGBA' else out.convert(mode)), n


def fix_geojson(src, dst, building):
    s = open(src, encoding='utf-8').read()
    reps = [
        (r'("address": )"77:10:0005004:1443"', r'\1"%s"' % ADDRESS),
        (r'("rajon": )"Савелки"', r'\1"%s"' % RAJON),
        (r'роизводсвтенн', 'роизводственн'),
        (r'("act_AGR": )""', r'\1"%s"' % SAGR),
    ]
    reps += [(r'("h_relief": )%s' % ZERO_OLD, r'\g<1>%s' % ZERO)]
    if building:
        reps += [(r'("%s": )[0-9.]+' % k, r'\g<1>%s' % v) for k, v in TEP.items() if k != 'h_relief']
        reps += [(r'("s_podz": )"0"', r'\g<1>0')]
        reps += [(r'("(transparency|refraction|roughness|metallicity)": )"([0-9.]+)"', r'\1\3')]
    for a, b in reps:
        s, n = re.subn(a, b, s)
        assert n >= 1, (a, src)
    j = json.loads(s)                       # проверка, что JSON цел
    pr = j['features'][0]['properties']
    assert pr['address'] == ADDRESS and pr['act_AGR'] == SAGR and 'свтен' not in pr['name'] and pr['h_relief'] == ZERO
    if building:
        assert all(pr[k] == v for k, v in TEP.items()) and pr['spp_gns'] < pr['s_naz'] == pr['s_obsh']
    open(dst, 'w', encoding='utf-8', newline='\n').write(s)
    return j['features'][0]['geometry']['coordinates']


def squash_ladder(f):
    """Верх лестницы на кровлю: вершины выше парапета в плане лестницы сжать по Z так, чтобы верх стал TOP."""
    objs = f.one('Objects')
    byid = {k.props[0].value: k for k in objs.kids}
    n = 0
    for c in f.one('Connections').kids:
        a, b = byid.get(c.props[1].value), byid.get(c.props[2].value)
        if a is None or b is None or a.name != 'Geometry' or b.name != 'Model':
            continue
        if not b.props[1].value.split('\x00')[0].endswith('Main'):
            continue
        vp = a.one('Vertices').props[0]
        V = np.array(vp.value).reshape(-1, 3)
        (x0, x1), (y0, y1) = LADDER
        sel = (V[:, 0] > x0) & (V[:, 0] < x1) & (V[:, 1] > y0) & (V[:, 1] < y1) & (V[:, 2] > PARAPET)
        if not sel.any():
            continue
        top = V[sel, 2].max()
        assert 12.0 < top < 12.2, top                      # верх лестницы в исходной модели — +12,085
        assert V[~sel, 2].max() <= PARAPET + 1e-6           # выше парапета нет ничего, кроме лестницы
        V[sel, 2] = PARAPET + (V[sel, 2] - PARAPET) * (TOP - PARAPET) / (top - PARAPET)
        vp.set([float(x) for x in V.ravel()])
        n += int(sel.sum())
    assert n > 0
    return n


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


def move_npm(path, out, place, paint=False):
    """place: {имя модели: (x, y)} — новые Lcl Translation по X, Y, по Z — нуль ZERO; paint — здание: цвета и лестница."""
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
                assert abs(c.props[6].value - ZERO_OLD) < 1e-3, (nm, c.props[6].value)
                c.props[6].set(float(ZERO))
                done.add(nm)
    assert done == set(place), (done, place)
    if paint:
        print('НПМ: верх лестницы, вершин', squash_ladder(f))
    for k in f.one('Objects').kids:            # встроенная карта диффузного цвета
        if paint and k.name == 'Video' and '_d_' in k.props[1].value and k.find('Content'):
            c = k.one('Content').props[0]
            im, cnt = recolor(Image.open(io.BytesIO(bytes(c.value))))
            b = io.BytesIO()
            im.save(b, 'PNG', optimize=True)
            c.set(b.getvalue())
            print('НПМ', os.path.basename(out), k.props[1].value.split('\x00')[0], cnt)
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
            elif building and name == base + '.fbx':
                f = fbxio.Fbx(os.path.join(src, name))
                print('ВПМ: верх лестницы, вершин', squash_ladder(f))
                open(os.path.join(d, name), 'wb').write(f.dumps())
            elif building and '_Diffuse_' in name and name.endswith('.png'):
                im, cnt = recolor(Image.open(os.path.join(src, name)))
                im.save(os.path.join(d, name), 'PNG', optimize=True)
                print('ВПМ', name, cnt)
            else:
                shutil.copy2(os.path.join(src, name), os.path.join(d, name))
        zipdir(d, os.path.join(out, base + '.zip'))
    # НПМ
    d = os.path.join(tmp, '1010_' + ADDR)
    os.makedirs(d)
    bx, by = pts['SM_%s' % ADDR]
    gx, gy = pts['SM_%s_Ground' % ADDR]
    n1 = move_npm(os.path.join(npm, '1010_%s_01.fbx' % ADDR), os.path.join(d, '1010_%s_01.fbx' % ADDR),
                  {'SM_%s_001_Main' % ADDR: (bx, by)}, paint=True)
    n2 = move_npm(os.path.join(npm, '1010_%s_Ground.fbx' % ADDR), os.path.join(d, '1010_%s_Ground.fbx' % ADDR),
                  {'SM_%s_%s' % (ADDR, s): (gx, gy) for s in ('Ground', 'GroundEl', 'Flora')})
    zipdir(d, os.path.join(out, '1010_%s.zip' % ADDR))
    print('ВПМ: точки вставки', pts, '; НПМ перенесена, путей к файлам автора убрано:', n1 + n2)


if __name__ == '__main__':
    main(*sys.argv[1:5])
