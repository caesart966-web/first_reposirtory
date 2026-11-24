"""Картинки для буклета АГР-2 из материалов авторов: вырезки из листа СПОЗУ и ведомостей презентации,
разделенные листы фасадов, схемы точек съемки.

    python3 prep_images.py <media презентации> <фото 1> <фото 2> <папка OSM> <img>

<media презентации> — ppt/media исправленной презентации (fix_presentation.py), <img> — папка, где уже
лежат footprint.json (sit_map.py) и куда пишутся результаты.
"""
import json
import os
import shutil
import sys

import numpy as np
from PIL import Image
from shapely.geometry import Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sit_map  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

# лист СПОЗУ авторов (image4.jpg, 3461×2344): план, условные обозначения, экспликация, покрытия, МАФ
CROPS4 = {'spozu_plan.png': (170, 0, 1510, 1250), 'spozu_expl.png': (60, 1400, 1000, 1670),
          'pokr.png': (60, 1700, 1190, 2090), 'maf.png': (1735, 1470, 3190, 2015)}
# картинки МАФ из столбца «Примечание» (image4.jpg)
MAF = {'maf_1.png': (2989, 1639, 3182, 1710), 'maf_2.png': (2989, 1710, 3182, 1781),
       'maf_3.png': (2989, 1781, 3182, 1853), 'maf_4.png': (2989, 1853, 3182, 1928),
       'maf_5.png': (2989, 1928, 3182, 2005)}
# светильники и козырек из столбца «Изображение» ведомости отделки фасада (image10.png, правая таблица)
FIX = {'fix_14.png': (4142, 1373, 4421, 1646), 'fix_15.png': (4142, 1651, 4421, 1844),
       'fix_17.png': (4142, 1849, 4421, 2003), 'fix_18.png': (4142, 2011, 4421, 2249)}

# фотомонтаж и рендеры авторов: кадр без белых полей слайда (image*.jpg, 2303×1366)
SLIDE_PICS = {'image1.jpg': (22, 9, 2303, 1327), 'image5.jpg': (0, 131, 2303, 1283),
              'image6.jpg': (0, 147, 2303, 1223)}
# точки фотофиксации (МСК-77: восток, север) и направление съемки, угол от оси «восток» против часовой
PHOTO_PTS = [((-15172.0, 35088.0), 53.0, '1'), ((-15142.0, 35178.0), 22.0, '2')]
# точки обзора видов модели: азимут камеры (как в render_persp.py) и дальность по горизонтали
VIEW_PTS = [(148.0, 125.0 * np.cos(np.radians(30)), '3'), (232.0, 125.0 * np.cos(np.radians(30)), '4'),
            (38.0, 82.0 * np.cos(np.radians(13)), '5')]


def trim(im, thr=245, pad=6):
    a = np.asarray(im.convert('L'))
    ys, xs = np.nonzero(a < thr)
    if not len(xs):
        return im
    return im.crop((max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad + 1, im.size[0]),
                    min(ys.max() + pad + 1, im.size[1])))


def inset(b, k=12):
    """Рамка ячейки без линий таблицы."""
    return b[0] + k, b[1] + k, b[2] - k, b[3] - k


def split(im, axis, lo=0.35, hi=0.65):
    """Разрезать лист с двумя чертежами по самой светлой полосе в середине (axis=0 — по горизонтали)."""
    a = np.asarray(im.convert('L')).astype(float)
    prof = a.mean(axis=1 - axis) if axis == 0 else a.mean(axis=0)
    n = len(prof)
    i0, i1 = int(n * lo), int(n * hi)
    k = i0 + int(np.argmax(prof[i0:i1]))
    if axis == 0:
        return trim(im.crop((0, 0, im.size[0], k))), trim(im.crop((0, k, im.size[0], im.size[1])))
    return trim(im.crop((0, 0, k, im.size[1]))), trim(im.crop((k, 0, im.size[0], im.size[1])))


def main(media, photo1, photo2, osm, out):
    os.makedirs(out, exist_ok=True)
    m = lambda n: os.path.join(media, n)  # noqa: E731
    shutil.copy(photo1, os.path.join(out, 'photo1.jpg'))
    shutil.copy(photo2, os.path.join(out, 'photo2.jpg'))
    # тот же кадр, что у фотомонтажа: подобран сравнением пикселей (монтаж = фото 0..1276 × 42..779)
    Image.open(photo1).crop((0, 42, 1276, 779)).save(os.path.join(out, 'photo1_m.jpg'), quality=95)
    for n in ('image9.jpg', 'image11.png', 'image12.png', 'image17.png'):
        shutil.copy(m(n), os.path.join(out, n))
    for n, bx in SLIDE_PICS.items():                    # кадры со слайдов — без белых полей слайда
        Image.open(m(n)).convert('RGB').crop(bx).save(os.path.join(out, n), quality=94)
    i4 = Image.open(m('image4.jpg')).convert('RGB')
    for n, b in CROPS4.items():
        trim(i4.crop(b), pad=4).save(os.path.join(out, n))
    plan = Image.open(os.path.join(out, 'spozu_plan.png'))
    plan.crop((600, 0, plan.size[0], 800)).save(os.path.join(out, 'spozu_park.png'))   # стоянка, ТБО, въезд
    for n, b in MAF.items():
        trim(i4.crop(inset(b)), thr=235, pad=4).save(os.path.join(out, n))
    i10 = Image.open(m('image10.png')).convert('RGB')
    for n, b in FIX.items():
        trim(i10.crop(inset(b)), thr=235, pad=4).save(os.path.join(out, n))
    # фасады: 1–9 над 9–1 (image7), А–Д рядом с Д–А (image8, с исправленной отметкой 206,96)
    a, b = split(Image.open(m('image7.png')).convert('RGB'), 0)
    a.save(os.path.join(out, 'fac_1_9.png')); b.save(os.path.join(out, 'fac_9_1.png'))
    a, b = split(Image.open(m('image8.png')).convert('RGB'), 1)
    a.save(os.path.join(out, 'fac_a_d.png')); b.save(os.path.join(out, 'fac_d_a.png'))

    fp = json.load(open(os.path.join(out, 'footprint.json'), encoding='utf-8'))
    site, bld = Polygon(fp['site']), Polygon(fp['building'])
    c = np.array(bld.centroid.coords[0])
    sit_map.draw(osm, site, bld, os.path.join(out, 'mini_photo.png'), (-15130.0, 35168.0), (362.2, 268.9), 2000,
                 marks=PHOTO_PTS, labels=True)
    sit_map.draw(osm, site, bld, os.path.join(out, 'mini_photo1.png'), (-15130.0, 35160.0), (212.9, 206.6), 3000,
                 marks=PHOTO_PTS[:1], labels=False)
    marks = []
    for az, d, t in VIEW_PTS:
        cam = c + d * np.array([np.sin(np.radians(az)), np.cos(np.radians(az))])
        v = c - cam
        marks.append(((float(cam[0]), float(cam[1])), float(np.degrees(np.arctan2(v[1], v[0]))), t))
    sit_map.draw(osm, site, bld, os.path.join(out, 'mini_views.png'), c + np.array([0.0, 0.0]), (212.9, 206.6),
                 3500, marks=marks, labels=False)
    print('готово:', out)


if __name__ == '__main__':
    main(*sys.argv[1:6])
