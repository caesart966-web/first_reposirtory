"""Пакет для согласования насосной с ГИП: листы 3 и 10 основного комплекта одним файлом.
Запускать после build_all.py."""
import os, sys
import pymupdf as fitz
from dxfkit import SHIFR
from meta import clean_pdf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out')
SHEETS = (3, 10)


def build():
    parts = [os.path.join(OUT, f'pdf_{no:02d}.pdf') for no in SHEETS]
    missing = [p for p in parts if not os.path.exists(p)]
    if missing:
        sys.exit('нет листов: ' + ', '.join(missing) + ' — сначала build_all.py')
    pkg = fitz.open()
    for p in parts:
        pkg.insert_pdf(fitz.open(p))
    path = os.path.join(OUT, f'{SHIFR.replace("/", "_")}_насосная_на_согласование.pdf')
    pkg.save(path)
    clean_pdf(path, f'{SHIFR}. Насосная станция пожаротушения')
    print('пакет', path)


if __name__ == '__main__':
    build()
