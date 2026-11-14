"""Запись PNG RGB 8 бит без построчных фильтров.

Для изображений с малым числом цветов (бывшая палитра) фильтр «None» сжимается
заметно лучше, чем адаптивные фильтры, которые выбирает Pillow.
"""
import struct
import zlib

import numpy as np


def _chunk(tag, data):
    return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)


def save_rgb(path, arr, dpi=None, level=9):
    arr = np.ascontiguousarray(arr, dtype=np.uint8)
    h, w, c = arr.shape
    assert c == 3
    raw = np.zeros((h, w * 3 + 1), dtype=np.uint8)
    raw[:, 1:] = arr.reshape(h, w * 3)
    out = [b'\x89PNG\r\n\x1a\n', _chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))]
    if dpi:
        ppm = int(round(dpi[0] / 0.0254)), int(round(dpi[1] / 0.0254))
        out.append(_chunk(b'pHYs', struct.pack('>IIB', ppm[0], ppm[1], 1)))
    comp = zlib.compressobj(level, zlib.DEFLATED, 15, 9)
    data = comp.compress(raw.tobytes()) + comp.flush()
    step = 1 << 20
    for i in range(0, len(data), step):
        out.append(_chunk(b'IDAT', data[i:i + step]))
    out.append(_chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(b''.join(out))
