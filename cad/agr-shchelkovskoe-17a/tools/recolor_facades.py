"""Схемы фасадов вариантов 2 и 3 из чертежей варианта 1.

    python3 recolor_facades.py <папка с im-023…026> <папка вывода>

В исходном буклете на листах вариантов 2 и 3 стояли те же файлы, что у варианта 1 (белый клинкер).
Чертежи одинаковы по геометрии, различаются только цветом отделки, поэтому зоны берутся по цвету:
клинкер и карниз нарисованы тёплым светлым тоном (R − B ≈ +5), стекло — холодным, сэндвич-панели,
цоколь и обрамления — нейтральным серым. Карниз — тёплая полоса высотой до 14 px между линиями под
кровлей; обрамления и стойки — небольшие серые блоки; колонна входа — высокий узкий серый блок;
цоколь — широкая серая полоса внизу. Новый цвет = цвет RAL × (яркость пикселя / медиана яркости зоны),
поэтому швы кладки и тени сохраняются.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

RAL = {'9010': (241, 236, 225), '7024': (71, 74, 80), '7039': (108, 105, 96), '6003': (76, 80, 57),
       '8028': (78, 59, 49), '7006': (117, 105, 94), '8004': (142, 64, 42)}
VARIANTS = {
    2: dict(clinker='6003', cornice='6003', frame='8028', column='6003', plinth='7006'),
    3: dict(clinker='8004', cornice='7024', frame=None, column=None, plinth=None),
}
NAMES = {'im-023': '1-7', 'im-024': '7-1', 'im-025': 'А-И', 'im-026': 'И-А'}
# колонна входной группы (поз. 14) нарисована вертикальным градиентом — её место задано рамкой (x0, y0, x1, y1)
COLUMN = {'im-023': (199, 140, 206, 312), 'im-026': (1145, 130, 1153, 288)}
# карниз фасада 7-1 не отделён от кладки линией — его полоса задана рамкой
CORNICE = {'im-024': (40, 126, 1000, 138)}


def zones(a, name):
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    L = a.mean(2)
    warm = (R - B >= 3) & (R - B <= 14) & (G - B >= 2) & (L > 100)
    lab, n = ndi.label(warm)
    sl = ndi.find_objects(lab)
    cornice = np.zeros_like(warm)
    clinker = np.zeros_like(warm)
    for i, s in enumerate(sl, 1):
        h, w = s[0].stop - s[0].start, s[1].stop - s[1].start
        area = (lab[s] == i).sum()
        if h <= 14 and w >= 120 and area > 300:
            cornice[s] |= lab[s] == i
        elif area > 400:
            clinker[s] |= lab[s] == i
    cornice = ndi.binary_closing(cornice, np.ones((3, 3))) & (L > 60)
    clinker = ndi.binary_closing(clinker, np.ones((3, 3))) & ~cornice & (L > 60)
    rows = np.nonzero(clinker)[0]
    cl_bottom = np.percentile(rows, 99) if len(rows) else a.shape[0]
    grey = (np.abs(R - B) <= 5) & (np.abs(R - G) <= 4) & (L > 80) & (L < 135)
    lab, n = ndi.label(grey)
    frame = np.zeros_like(grey); column = np.zeros_like(grey); plinth = np.zeros_like(grey)
    for i, s in enumerate(ndi.find_objects(lab), 1):
        h, w = s[0].stop - s[0].start, s[1].stop - s[1].start
        m = lab[s] == i
        area = m.sum()
        if area < 40:
            continue
        if w <= 30 and 10 <= h <= 90 and area / (h * w) > 0.6:
            if s[0].start >= cl_bottom - 3:
                plinth[s] |= m                  # плитки цоколя ниже клинкера
            else:
                frame[s] |= m
        elif w <= 25 and h > 90:
            column[s] |= m
        elif w > 200 and h <= 45 and s[0].start > a.shape[0] * 0.45:
            plinth[s] |= m
    if name in CORNICE:
        x0, y0, x1, y1 = CORNICE[name]
        box = np.zeros_like(cornice)
        box[y0:y1, x0:x1] = True
        extra = box & (clinker | ((R - B >= 2) & (L > 100)))
        cornice |= extra
        clinker &= ~extra
    column[:] = False
    if name in COLUMN:
        x0, y0, x1, y1 = COLUMN[name]
        box = np.zeros_like(column)
        box[y0:y1, x0:x1] = True
        column = box & (np.abs(R - B) <= 8) & (L > 50) & (L < 252)
        frame &= ~column
    return dict(clinker=clinker, cornice=cornice, frame=frame, column=column, plinth=plinth), L


def paint(out, L, mask, ral):
    if ral is None or not mask.any():
        return
    ref = np.median(L[mask])
    k = np.clip(L[mask] / ref, 0, 1.25)[:, None]
    out[mask] = np.clip(np.array(RAL[ral])[None, :] * k, 0, 255)


def main(src, dst):
    os.makedirs(dst, exist_ok=True)
    for f in NAMES:
        a = np.asarray(Image.open(os.path.join(src, f + '.png')).convert('RGB')).astype(float)
        Z, L = zones(a, f)
        for v, cfg in VARIANTS.items():
            out = a.copy()
            for key in ('clinker', 'cornice', 'frame', 'column', 'plinth'):
                paint(out, L, Z[key], cfg[key])
            p = os.path.join(dst, 'facade_v%d_%s.png' % (v, f))
            Image.fromarray(out.astype(np.uint8)).save(p)
        print(f, {k: int(m.sum()) for k, m in Z.items()})


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
