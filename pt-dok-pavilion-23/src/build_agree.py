"""Пакет для согласования насосной с ГИП: лист решений + листы 3 и 10 основного комплекта.
Запускать после build_all.py (берёт out/pdf_03.pdf и out/pdf_10.pdf)."""
import os, sys
import pymupdf as fitz
from dxfkit import make_doc, SHIFR
from plans import setup_dimstyle
from export import sheet_pdf
from meta import clean_dxf, clean_pdf
import sh_agree

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out')
BASE = SHIFR.replace('/', '_')


def build():
    doc = make_doc(); setup_dimstyle(doc); msp = doc.modelspace()
    sh_agree.agree_sheet(msp, 0, 0)
    clean_dxf(doc)
    doc.saveas(os.path.join(OUT, f'{BASE}_насосная_на_согласование.dxf'))
    p1 = os.path.join(OUT, 'pdf_agree.pdf')
    sheet_pdf(doc, 0, 0, 'A1', 1, p1)
    parts = [p1] + [os.path.join(OUT, f'pdf_{no:02d}.pdf') for no in (3, 10)]
    missing = [p for p in parts if not os.path.exists(p)]
    if missing:
        sys.exit('нет листов основного комплекта: ' + ', '.join(missing) + ' — сначала build_all.py')
    pkg = fitz.open()
    for p in parts:
        pkg.insert_pdf(fitz.open(p))
    path = os.path.join(OUT, f'{BASE}_насосная_на_согласование.pdf')
    pkg.save(path)
    clean_pdf(path, f'{SHIFR}. Насосная станция пожаротушения. Материалы для согласования')
    print('пакет', path)


if __name__ == '__main__':
    build()
