"""Геопривязка ВПМ по НПМ и отдельный GeoJSON контура территории.

    python3 georef_vpm.py <ВПМ здания.zip> <ВПМ благоустройства.zip> <НПМ здания.fbx> <НПМ благоустройства.fbx>
                          <areas.json> <куда>

Точка в geojson ВПМ — положение нуля модели в МСК-77 (восток, север). У автора в обоих geojson стояла одна
точка (16803,660; 15592,460), тогда как сетки ВПМ в своих осях совпадают с сетками НПМ, а НПМ поставлена
в мир смещением узла: здание — (16809,178; 15610,056), благоустройство — (16816,711; 15617,135). По точке
автора здание уезжало от НПМ на 18 м, благоустройство — на 28 м (замечание проверки 26.11.2026).

Скрипт берёт смещение узла НПМ (Lcl Translation: X — восток, −Z — север; Y-вверх), проверяет, что габариты
сетки ВПМ в своих осях совпадают с НПМ до 1 см, и меняет в geojson только строки координат (остальные
байты файла и архива — как были). Высотная отметка h_relief не меняется: ноль модели — чистый пол
(±0,000 = 154,850), верх ограждения кровли на +5,800 = h_otn.

Контур территории — граница участка по ГПЗУ (areas.json → site_world, мм) отдельным GeoJSON: полигон
в МСК-77, метры, кольцо против часовой стрелки и замкнуто.
"""
import io
import json
import os
import re
import sys
import zipfile

import numpy as np
from shapely.geometry import Polygon, MultiPoint
from shapely.geometry.polygon import orient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fbxio  # noqa: E402

COORD = re.compile(rb'("coordinates": \[\s*")([-\d.]+)("\s*,\s*")([-\d.]+)("\s*\])')


def nodes(path):
    """{имя узла: (смещение узла, вершины сетки)} без блоков коллизий."""
    f = fbxio.Fbx(path)
    objs, conn = f.one('Objects'), f.one('Connections')
    byid = {k.props[0].value: k for k in objs.kids}
    out = {}
    for c in conn.kids:
        a, b = byid.get(c.props[1].value), byid.get(c.props[2].value)
        if a is None or b is None or b.name != 'Model' or a.name != 'Geometry':
            continue
        nm = b.props[1].value.split('\x00')[0]
        if nm.startswith('UCX'):
            continue
        t = np.zeros(3)
        for p in b.one('Properties70').kids:
            if p.props[0].value == 'Lcl Translation':
                t = np.array([p.props[i].value for i in (4, 5, 6)])
        out[nm] = (t, np.array(a.one('Vertices').props[0].value).reshape(-1, 3))
    return out


def box(nd):
    V = np.vstack([v for _, v in nd.values()])
    return V.min(0), V.max(0)


def point(vpm_fbx, npm_fbx):
    v, n = nodes(vpm_fbx), nodes(npm_fbx)
    (a0, a1), (b0, b1) = box(v), box(n)
    assert np.abs(a0 - b0).max() < 0.01 and np.abs(a1 - b1).max() < 0.01, ('сетки ВПМ и НПМ разные', a0, b0, a1, b1)
    ts = {tuple(np.round(t, 3)) for t, _ in n.values()}
    assert len(ts) == 1, ('у узлов НПМ разные смещения', ts)
    t = n[next(iter(n))][0]
    return float(t[0]), float(-t[2]), v


def patch_zip(src, dst, npm_fbx, tmp):
    zin = zipfile.ZipFile(src)
    base = os.path.splitext(os.path.basename(src))[0]
    fbx = os.path.join(tmp, base + '.fbx')
    open(fbx, 'wb').write(zin.read(base + '.fbx'))
    e, n, v = point(fbx, npm_fbx)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            data = zin.read(it.filename)
            if it.filename == base + '.geojson':
                assert len(COORD.findall(data)) == 1, it.filename
                old = COORD.search(data)
                data = COORD.sub(lambda m: m.group(1) + (b'%.3f' % e) + m.group(3) + (b'%.3f' % n) + m.group(5), data)
                print('%s: (%s; %s) -> (%.3f; %.3f), сдвиг %.1f м' % (
                    it.filename, old.group(2).decode(), old.group(4).decode(), e, n,
                    np.hypot(e - float(old.group(2)), n - float(old.group(4)))))
                json.loads(data.decode('utf-8'))
            zout.writestr(it, data)
    open(dst, 'wb').write(buf.getvalue())
    os.remove(fbx)
    return e, n, v


def territory(areas, out):
    a = json.load(open(areas))
    poly = orient(Polygon(np.array(a['site_world']) / 1000), 1.0)
    ring = [[round(x, 2), round(y, 2)] for x, y in poly.exterior.coords]
    gj = {
        'type': 'FeatureCollection',
        'name': 'Территория_ShchelkovskoeShosse_17A_1',
        'features': [{
            'type': 'Feature',
            'properties': {
                'name': 'Граница земельного участка (территория благоустройства)',
                'address': 'г. Москва, Щёлковское шоссе, земельный участок 17А/1',
                'cadNum': '77:03:0002010:3983',
                'GPZU': 'РФ-77-4-52-3-05-2026-11594-0 от 12.10.2026',
                'coord_system': 'МСК-77',
                'units': 'м',
                'area_m2': round(poly.area, 2),
                'ZU_area': '%.4f' % (poly.area / 10000),
            },
            'geometry': {'type': 'Polygon', 'coordinates': [ring]},
        }],
    }
    open(out, 'w', encoding='utf-8').write(json.dumps(gj, ensure_ascii=False, indent=4) + '\n')
    print(os.path.basename(out), len(ring) - 1, 'вершин, %.2f м²' % poly.area)
    return poly


def main(vpm_b, vpm_g, npm_b, npm_g, areas, out):
    os.makedirs(out, exist_ok=True)
    a = json.load(open(areas))
    inner = Polygon(np.array(a['inner_world']) / 1000)
    site = territory(areas, os.path.join(out, 'ShchelkovskoeShosse_17A_1_Territory.geojson'))
    for src, npm, kind in ((vpm_b, npm_b, 'здание'), (vpm_g, npm_g, 'благоустройство')):
        e, n, v = patch_zip(src, os.path.join(out, os.path.basename(src)), npm, out)
        hull = MultiPoint([(x + e, y + n) for _, V in v.values() for x, y, _ in V]).convex_hull
        ref = inner if kind == 'здание' else site
        share = hull.intersection(ref).area / ref.area
        print('  %s: контур %s покрыт моделью на %.1f %%' % (kind, 'здания' if kind == 'здание' else 'участка',
                                                            share * 100))
        assert share > 0.95, kind


if __name__ == '__main__':
    main(*sys.argv[1:7])
