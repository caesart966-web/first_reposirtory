"""Очистка генплана авторов проекта от прежних маршрутов (голубые стрелки).

    python3 clean_base.py <генплан.png> <куда.png>

Закрашенные точки получают цвет ближайшей ровной области подосновы, поэтому
на белом и на газоне следов не остаётся. Вторым файлом пишется копия,
увеличенная вдвое, — на ней рисуется новая схема.
"""
import sys
from collections import Counter

import cv2
import numpy as np
from PIL import Image


def main(src_path, out_path):
    src = np.asarray(Image.open(src_path).convert('RGB'))
    a = src.astype(int)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    m = (b > 135) & (g > 70) & (g < 225) & (r < 165) & (b - r > 35) & (g - r > 10) & (b - g > 5)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] >= 12:
            keep |= lab == i
    mask = cv2.dilate(keep.astype(np.uint8), np.ones((13, 13), np.uint8)).astype(bool)
    flat = [np.array(k) for k, _ in Counter(map(tuple, src.reshape(-1, 3))).most_common(6)]
    isflat = np.zeros(src.shape[:2], bool)
    for f in flat:
        isflat |= np.abs(a - f).sum(2) <= 6
    valid = isflat & ~mask
    _, labels = cv2.distanceTransformWithLabels((~valid).astype(np.uint8), cv2.DIST_L2, 5,
                                                labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(valid)
    lut = np.zeros((labels.max() + 1, 3), np.uint8)
    lut[labels[ys, xs]] = src[ys, xs]
    out = src.copy()
    my, mx = np.nonzero(mask)
    out[my, mx] = lut[labels[my, mx]]
    blur = cv2.GaussianBlur(out, (0, 0), 0.8)
    edge = cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8)) - cv2.erode(mask.astype(np.uint8),
                                                                                  np.ones((3, 3), np.uint8))
    out[edge > 0] = blur[edge > 0]
    Image.fromarray(out).save(out_path)
    Image.fromarray(out).resize((out.shape[1] * 2, out.shape[0] * 2), Image.LANCZOS).save(
        out_path.replace('.png', '_x2.png'))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
