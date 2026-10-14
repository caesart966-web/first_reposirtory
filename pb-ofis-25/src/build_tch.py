"""Текстовая часть ПБ-25: разметка tch1..tch4 + значения из calc.py и tables.py → out/ПБ-25-ТЧ.pdf.
Первый лист текстовой части и общее число листов тома передаются из build_volume.py."""
import os, re, sys
import pbdoc
from calc import R
from tables import TABLES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out')
PARTS = ['tch1.txt', 'tch2.txt', 'tch3.txt', 'tch4.txt']


def source():
    src = '\n\n'.join(open(os.path.join(HERE, p), encoding='utf-8').read() for p in PARTS)
    vars_ = dict(R, **TABLES)
    # таблицы подставляются первыми: в них самих есть {{…}}
    src = re.sub(r'\{\{(tab_\w+)\}\}', lambda m: vars_[m.group(1)], src)
    missing = sorted(set(re.findall(r'\{\{(\w+)\}\}', src)) - set(vars_))
    if missing:
        raise SystemExit('нет значений: ' + ', '.join(missing))
    return src, vars_


def build(first_sheet=7, total=None, path=None):
    src, vars_ = source()
    path = path or os.path.join(OUT, 'ПБ-25-ТЧ.pdf')
    last = pbdoc.build(path, src, first_sheet, total, vars_)
    return path, last


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    p, last = build(7, int(sys.argv[1]) if len(sys.argv) > 1 else 99)
    print(p, 'последний лист', last)
