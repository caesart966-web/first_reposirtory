"""Поручни ограждения кровли в НПМ и ВПМ — графит RAL 7024 (29.11.2026).

    python3 fix_vpm_rail_colour.py <ВПМ здания.zip> <НПМ.zip> <папка вывода>

Справка заказчика 28.11.2026: у приоритетного варианта 1 поручни кровли (буклет, ведомость отделки, поз. 8 «в цвет
стоек») — графит RAL 7024, а в моделях они красно-розовые RGB (202, 86, 94):
  * ВПМ: плитка T_..._Diffuse_1.1008 (сплошной цвет; ей развёрнуты только 156 треугольников верха ограждения кровли
    на отметке +5,69…+5,77) — заливается RAL 7024 (71, 74, 80), размер и формат PNG прежние;
  * НПМ: в запечённой текстуре Main_d (встроена в FBX) поручни — квадрат 146×146 px того же цвета, он и перекрашивается;
  * миниатюра в GeoJSON ВПМ здания: тёплые пиксели верха ограждения приводятся к серому (рендер 256 px, в нём их ~90).
У здания пустая подземная площадь s_podz — «0» (подземной части нет, ТЭП: UndergroundArea 0). Координаты точки
вставки в GeoJSON остаются строками: файлы ВПМ сделаны по московскому шаблону (тип объекта «ObjectFeature», не
«Feature» по RFC 7946), и числовые координаты справки — по общему стандарту GeoJSON, а не по шаблону. Остальные
файлы архивов — байт в байт.
"""
import base64
import io
import json
import os
import re
import sys
import zipfile

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fbxio  # noqa: E402

RAL7024 = (71, 74, 80)
PINK = np.array((202, 86, 94))


def png_bytes(im):
    out = io.BytesIO()
    im.save(out, 'PNG', optimize=True)
    return out.getvalue()


def recolour_pink(data, expect_min=1, tol=2):
    im = Image.open(io.BytesIO(data))
    mode = im.mode
    a = np.asarray(im.convert('RGBA')).copy()
    m = (np.abs(a[..., :3].astype(int) - PINK) <= tol).all(-1)
    assert m.sum() >= expect_min, 'нет пикселей цвета (202, 86, 94)'
    a[m, :3] = RAL7024
    out = Image.fromarray(a, 'RGBA')
    return png_bytes(out if mode == 'RGBA' else out.convert(mode)), int(m.sum())


def thumb(b64):
    head, body = b64.split(',', 1)
    im = Image.open(io.BytesIO(base64.b64decode(body))).convert('RGB')
    a = np.asarray(im).astype(int)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    m = (R - B > 12) & (R - G > 4) & (R > 80)
    m[a.shape[0] // 2:] = False                       # только верх кадра — ограждение кровли
    L = (a[m] @ np.array([0.299, 0.587, 0.114])) * 0.6
    a[m] = np.stack([L * 71 / 74, L, L * 80 / 74], 1).clip(0, 255)
    out = io.BytesIO()
    Image.fromarray(a.astype('uint8')).save(out, 'JPEG', quality=92)
    return head + ',' + base64.b64encode(out.getvalue()).decode('ascii'), int(m.sum())


def geojson(data):
    text = data.decode('utf-8')
    d = json.loads(text)
    for ft in d['features']:
        pr = ft['properties']
        if pr.get('s_podz') == '':
            assert text.count('"s_podz": ""') == 1
            text = text.replace('"s_podz": ""', '"s_podz": "0"')
            print('   s_podz: "" -> "0"')
        new_b64, n = thumb(pr['imageBase64'])
        assert text.count(pr['imageBase64']) == 1
        text = text.replace(pr['imageBase64'], new_b64)
        print('   миниатюра: перекрашено %d px' % n)
    json.loads(text)
    return text.encode('utf-8')


def rezip(src, dst, edit):
    zin = zipfile.ZipFile(src)
    with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            data = edit(it.filename, zin.read(it.filename))
            zout.writestr(it, data)


def main(vpm, npm, out):
    os.makedirs(out, exist_ok=True)
    base = os.path.splitext(os.path.basename(vpm))[0]

    def ed_vpm(name, data):
        if name.endswith('_Diffuse_1.1008.png'):
            im = Image.open(io.BytesIO(data))
            cols = im.convert('RGB').getcolors()
            assert cols and len(cols) == 1 and cols[0][1] == tuple(PINK), cols
            print('%s: плитка %s %s -> RAL 7024' % (base, name, cols[0][1]))
            return png_bytes(Image.new(im.mode, im.size, RAL7024 if im.mode == 'RGB' else RAL7024 + (255,)))
        if name == base + '.geojson':
            print('%s: %s' % (base, name))
            return geojson(data)
        return data
    rezip(vpm, os.path.join(out, os.path.basename(vpm)), ed_vpm)

    def ed_npm(name, data):
        if not name.endswith('_01.fbx'):
            return data
        tmp = os.path.join(out, '_npm.fbx')
        open(tmp, 'wb').write(data)
        f = fbxio.Fbx(tmp)
        n_done = 0
        for v in f.one('Objects').find('Video'):
            fn = v.one('RelativeFilename').props[0].value
            if not fn.endswith('_Main_d_1.png'):
                continue
            c = v.one('Content').props[0]
            new, n = recolour_pink(c.value, expect_min=10000, tol=25)   # края квадрата сглажены при запекании
            c.set(new)
            n_done += 1
            print('%s: %s, перекрашено %d px' % (name, fn.rsplit('\\', 1)[-1], n))
        assert n_done == 1
        raw = f.dumps()
        os.remove(tmp)
        return raw
    rezip(npm, os.path.join(out, os.path.basename(npm)), ed_npm)


if __name__ == '__main__':
    main(*sys.argv[1:4])
