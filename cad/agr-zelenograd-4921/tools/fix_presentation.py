"""fix_presentation.py СТАРЫЙ_БУКЛЕТ.pdf НОВЫЙ_БУКЛЕТ.pdf ПРЕЗЕНТАЦИЯ.pptx ВЫХОД.pptx

ТЭП в презентации — те же, что в буклете после fix_booklet.py:
* текст слайдов 2 и 12;
* картинки из буклета (СПОЗУ — лист 4, фасады А-Д/Д-А — лист 9, таблица ТЭП — лист 17): положение
  и разрешение картинки на листе находятся по совпадению с рендером старого буклета (ORB + RANSAC),
  затем в картинку переносятся только пиксели, которые различаются в рендерах старого и нового буклета;
* остальные PNG пережимаются без потерь (попиксельная проверка): в исходнике они почти не сжаты,
  и презентация весила 167 МБ.
Нужны pymupdf, opencv-python, Pillow, numpy.
"""
import io
import re
import sys
import zipfile

import cv2
import numpy as np
import pymupdf
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
TXT = {'ppt/slides/slide2.xml': [('1 178,32 м²', '1 226,90 м²'), ('1 454,00 м²', '1 510,80 м²'), ('12,31 м', '11,94 м')],
       'ppt/slides/slide12.xml': [('1 454,00 м²', '1 510,80 м²'), ('4,6 тыс. м²/га', '4,5 тыс. м²/га'),
                                  ('1 484,46 м²', '1 470,50 м²'), ('206,11 м', '207,96 м')]}
IMG = {'ppt/media/image4.jpg': 4, 'ppt/media/image8.png': 9, 'ppt/media/image19.png': 17}   # картинка: лист буклета


def render(doc, pno, dpi):
    pm = doc[pno - 1].get_pixmap(dpi=dpi)
    return np.frombuffer(pm.samples, np.uint8).reshape(pm.height, pm.width, pm.n)[..., :3].astype(np.int16)


def locate(doc, pno, im, dpi=150):
    """Картинка -> (пт на пиксель, смещение в пт) по совпадению с рендером листа."""
    page = render(doc, pno, dpi).astype(np.uint8)
    k = 1600 / max(im.shape[:2])
    small = cv2.resize(im.astype(np.uint8), None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    g1, g2 = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY), cv2.cvtColor(page, cv2.COLOR_RGB2GRAY)
    orb = cv2.ORB_create(8000)
    k1, d1 = orb.detectAndCompute(g1, None)
    k2, d2 = orb.detectAndCompute(g2, None)
    m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d1, d2)
    p1 = np.float32([k1[x.queryIdx].pt for x in m]) / k
    p2 = np.float32([k2[x.trainIdx].pt for x in m]) / (dpi / 72)
    A, _ = cv2.estimateAffinePartial2D(p1, p2, ransacReprojThreshold=1.0)
    return np.hypot(A[0, 0], A[1, 0]), A[0, 2], A[1, 2]


def patch(old_doc, new_doc, pno, data, ext):
    im = np.asarray(Image.open(io.BytesIO(data)).convert('RGB')).astype(np.int16)
    s, ox, oy = locate(old_doc, pno, im)
    dpi = round(72 / s / 10) * 10
    h, w = im.shape[:2]
    old, new = render(old_doc, pno, dpi), render(new_doc, pno, dpi)
    best = None
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            x, y = int(round(ox * dpi / 72)) + dx, int(round(oy * dpi / 72)) + dy
            if 0 <= x and 0 <= y and y + h <= old.shape[0] and x + w <= old.shape[1]:
                e = np.abs(old[y:y + h, x:x + w] - im).mean()
                if best is None or e < best[0]:
                    best = (e, x, y)
    e, x, y = best
    assert e < 8, ('картинка не совпала с листом', pno, e)
    co, cn = old[y:y + h, x:x + w], new[y:y + h, x:x + w]
    mask = cv2.dilate((np.abs(co - cn).max(-1) > 0).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    assert mask.any()
    out = im.copy()
    out[mask] = cn[mask]
    b = io.BytesIO()
    res = Image.fromarray(out.astype(np.uint8))
    if ext == 'jpg':
        res.save(b, 'JPEG', quality=95, subsampling=0)
    else:
        res.save(b, 'PNG', optimize=True)
    print('лист %d: %d dpi, сдвиг %d,%d, расхождение %.2f, заменено пикселей %d' % (pno, dpi, x, y, e, mask.sum()))
    return b.getvalue()


def repack_png(data):
    a = Image.open(io.BytesIO(data))
    a.load()
    b = io.BytesIO()
    a.save(b, 'PNG', optimize=True)
    c = Image.open(io.BytesIO(b.getvalue()))
    if len(b.getvalue()) < len(data) and c.mode == a.mode and np.array_equal(np.asarray(a), np.asarray(c)):
        return b.getvalue()
    return data


def main(old_pdf, new_pdf, src, dst):
    od, nd = pymupdf.open(old_pdf), pymupdf.open(new_pdf)
    zi = zipfile.ZipFile(src)
    with zipfile.ZipFile(dst, 'w') as zo:
        for it in zi.infolist():
            data = zi.read(it.filename)
            if it.filename in TXT:
                x = data.decode('utf-8')
                for a, b in TXT[it.filename]:
                    pa = re.escape(a).replace(r'\ ', '[  ]')
                    x, n = re.subn('(<a:t>)' + pa + '(</a:t>)', lambda m: m.group(1) + b + m.group(2), x)
                    assert n == 1, (it.filename, a, n)
                data = x.encode('utf-8')
            elif it.filename in IMG:
                data = patch(od, nd, IMG[it.filename], data, it.filename.rsplit('.', 1)[1])
            elif it.filename.startswith('ppt/media/') and it.filename.endswith('.png'):
                data = repack_png(data)
            zo.writestr(it, data, compress_type=it.compress_type)


if __name__ == '__main__':
    main(*sys.argv[1:5])
