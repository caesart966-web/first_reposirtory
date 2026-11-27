"""Площадь в geojson архива ВПМ здания (s_obsh, s_naz) — после изменения ТЭП (27.11.2026: 520,63 -> 519,28 м²).

    python3 vpm_area.py <ВПМ здания.zip> <куда.zip> <площадь>

Меняются только два значения по тексту geojson, остальные файлы архива и сам geojson — байт в байт.
"""
import io
import json
import os
import sys
import zipfile


def main(src, dst, area):
    area = '%.2f' % float(area)
    zin = zipfile.ZipFile(src)
    base = os.path.splitext(os.path.basename(src))[0]
    buf = io.BytesIO()
    done = False
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            data = zin.read(it.filename)
            if it.filename == base + '.geojson':
                pr = json.loads(data.decode('utf-8'))['features'][0]['properties']
                for key in ('s_obsh', 's_naz'):
                    old = ('"%s": "%s"' % (key, pr[key])).encode('utf-8')
                    assert data.count(old) == 1, key
                    data = data.replace(old, ('"%s": "%s"' % (key, area)).encode('utf-8'))
                    print('%s: %s %s -> %s' % (it.filename, key, pr[key], area))
                json.loads(data.decode('utf-8'))
                done = True
            zout.writestr(it, data)
    assert done, 'нет %s.geojson' % base
    open(dst, 'wb').write(buf.getvalue())


if __name__ == '__main__':
    main(*sys.argv[1:4])
