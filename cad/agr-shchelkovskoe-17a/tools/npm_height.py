"""Высота НПМ: ноль модели на отметку чистого пола ±0,000 = 154,850.

    python3 npm_height.py <архив НПМ.zip> <куда>

У прежнего исполнителя узлы НПМ (здание, благоустройство и их коллизии) стояли на Y = 154,35, то есть
ноль модели — чистый пол — оказывался на 0,5 м ниже проектного, а рельеф у здания (в осях модели −0,52)
выходил на 153,83 вместо 154,35. В ВПМ h_relief = 154,85, h_abs = h_relief + h_otn = 160,65.
Меняется только Y смещения узлов (с точностью float32, как пишет 3ds Max), остальные байты те же.
"""
import io
import os
import sys
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fbxio  # noqa: E402

OLD, NEW = float(np.float32(154.35)), float(np.float32(154.85))


def patch(raw, tmp):
    open(tmp, 'wb').write(raw)
    f = fbxio.Fbx(tmp)
    assert f.dumps() == raw
    n = 0
    for m in f.one('Objects').kids:
        if m.name != 'Model':
            continue
        for p in m.one('Properties70').kids:
            if p.props[0].value == 'Lcl Translation':
                assert abs(p.props[5].value - OLD) < 1e-6, (m.props[1].value, p.props[5].value)
                p.props[5].set(NEW)
                n += 1
    out = f.dumps()
    assert len(out) == len(raw)
    os.remove(tmp)
    return out, n


def main(src, out):
    os.makedirs(out, exist_ok=True)
    zin = zipfile.ZipFile(src)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            data = zin.read(it.filename)
            if it.filename.lower().endswith('.fbx'):
                data, n = patch(data, os.path.join(out, '_tmp.fbx'))
                print('%s: узлов %d, Y %.2f -> %.2f' % (it.filename, n, OLD, NEW))
            zout.writestr(it, data)
    open(os.path.join(out, os.path.basename(src)), 'wb').write(buf.getvalue())


if __name__ == '__main__':
    main(*sys.argv[1:3])
