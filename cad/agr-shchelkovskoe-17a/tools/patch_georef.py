"""Географические координаты участка в IfcSite (RefLatitude/RefLongitude) трёх ЦИМ АГР.

    python3 patch_georef.py <areas.json> <папка с AR.ifc, PS.ifc, BiO.ifc> <куда>

Revit при экспорте оставил координаты по умолчанию — район Бостона (42°24'53" с. ш., 71°15'29" з. д.).
Ставятся координаты центра участка по модели (МСК-77 -> WGS-84, osm_base.MSK) в формате
IfcCompoundPlaneAngleMeasure: градусы, минуты, секунды, миллионные доли секунды. Остальной файл
не меняется (меняется одна подстрока, проверяется, что она в файле ровно одна).
"""
import json
import os
import shutil
import sys

import numpy as np
from pyproj import Transformer
from shapely.geometry import Polygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import osm_base  # noqa: E402

OLD = b'(42,24,53,508911),(-71,-15,-29,-58837)'


def dms(v):
    s = 1 if v >= 0 else -1
    v = abs(v)
    d = int(v)
    m = int((v - d) * 60)
    sec = (v - d - m / 60) * 3600
    si = int(sec)
    mic = int(round((sec - si) * 1e6))
    if mic == 1000000:
        si, mic = si + 1, 0
    return tuple(s * x for x in (d, m, si, mic))


def main(areas, src, out):
    a = json.load(open(areas))
    c = Polygon(np.array(a['site_world']) / 1000).centroid
    lon, lat = Transformer.from_crs(osm_base.MSK, 'EPSG:4326', always_xy=True).transform(c.x, c.y)
    new = ('(%d,%d,%d,%d),(%d,%d,%d,%d)' % (dms(lat) + dms(lon))).encode()
    print('центр участка: %.6f с. ш., %.6f в. д. ->' % (lat, lon), new.decode())
    os.makedirs(out, exist_ok=True)
    for f in ('AR.ifc', 'PS.ifc', 'BiO.ifc'):
        b = open(os.path.join(src, f), 'rb').read()
        assert b.count(OLD) == 1, (f, b.count(OLD))
        open(os.path.join(out, f), 'wb').write(b.replace(OLD, new))
    for f in os.listdir(src):
        if not os.path.exists(os.path.join(out, f)):
            shutil.copyfile(os.path.join(src, f), os.path.join(out, f))


if __name__ == '__main__':
    main(*sys.argv[1:4])
