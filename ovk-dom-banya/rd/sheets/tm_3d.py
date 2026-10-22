"""И05.09.26-ТМ, лист 6. 3D-виды модели котельной (снимки просмотрщика модели, А2).

В DXF/DWG — рамки видов с картинками (IMAGE, файлы PNG лежат рядом), в PDF картинки вставляются поверх листа.
python3 sheets/tm_3d.py -> out/tm_3d.dxf + out/tm_3d_Лист.pdf (+ out/tm3d_*.png)
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from rdbase import new_doc, RDSheet, save_and_pdf  # noqa: E402
from tm_draw import CODE_TM, BLD_TM, TM_LIST, TM_TOTAL, setup_layers  # noqa: E402

OUT = os.path.join(ROOT, 'out')
from tm_3d_shots import SHOTS  # noqa: E402
SHEET_NO = 6
W, H = 250.0, 156.25                      # кадр 1600×1000 (16:10)
VIEWS = [  # файл, заголовок, левый нижний угол кадра на листе
    ('sw', 'Общий вид с юго-запада — с сетями ОВ (П1, воздуховоды) для увязки', (24.0, 232.0)),
    ('sw0', 'Тот же вид без сетей ОВ', (304.0, 232.0)),
    ('nw', 'Котлы К1, К2 и пеллетный котёл ПК: подключения, газ, дымоходы', (24.0, 64.0)),
    ('rk', 'Гидрострелка ГС, коллектор РК и насосные группы Н2…Н7', (304.0, 64.0)),
]


def build():
    doc = new_doc()
    setup_layers(doc)
    sh = RDSheet(doc, 'Лист', TM_LIST[SHEET_NO], SHEET_NO, TM_TOTAL, fmt='А2', code=CODE_TM, bld=BLD_TM)
    rects = []
    for name, title, (x, y) in VIEWS:
        png = f'tm3d_{name}.png'
        shutil.copy(os.path.join(SHOTS, name + '.png'), os.path.join(OUT, png))
        idef = doc.add_image_def(filename=png, size_in_pixel=(2400, 1500))
        sh.lay.add_image(idef, insert=(x, y), size_in_units=(W, H), dxfattribs={'layer': 'ТМ_оборуд_тонк'})
        sh.s.rect(x, y, W, H, lw=25)
        sh.s.text(title, x + W / 2, y + H + 4.0, h=2.8, align='center')
        rects.append((png, x, y))
    sh.s.mtext('Снимки 3D-модели котельной (И05.09.26-ТМ 3D). Модель открывается в браузере (файл «просмотр в '
               'браузере»: вращение, виды, включение систем), в AutoCAD (DWG 3D) и в BIM-программах (IFC4). '
               'Марки — как на листах 2–5 и в ТМ.СО.', 24.0, 56.0, 350.0, h=2.2, attach=1)
    return doc, rects


def overlay(pdf, rects):
    """Вставить картинки в PDF поверх рамок (ezdxf печатает IMAGE без растра)."""
    import pymupdf as fitz
    d = fitz.open(pdf)
    pg = d[0]
    Hp = pg.rect.height
    k = 72 / 25.4
    for png, x, y in rects:
        r = fitz.Rect(x * k, Hp - (y + H) * k, (x + W) * k, Hp - y * k)
        pg.insert_image(r, filename=os.path.join(OUT, png))
    d.saveIncr() if False else d.save(pdf + '.tmp', garbage=3, deflate=True)
    d.close()
    os.replace(pdf + '.tmp', pdf)


if __name__ == '__main__':
    doc, rects = build()
    pdfs = save_and_pdf(doc, os.path.join(OUT, 'tm_3d.dxf'))
    overlay(pdfs[0], rects)
    print(pdfs)
