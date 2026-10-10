"""Задания смежным разделам: ПТ.ЗД1 — КР, ПТ.ЗД2 — ВК. PDF по листу и общий DXF. Запускать после calc_final и spec_data."""
import os
from dxfkit import make_doc, SHIFR
from plans import setup_dimstyle
from export import sheet_pdf
from meta import clean_dxf, clean_pdf
import sh_tasks

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out')
BASE = SHIFR.replace('/', '_')
TASKS = [(sh_tasks.task_kr, 0, 'ЗД1_задание_КР_приямок_основания_отверстия', 'Задание разделу КР'),
         (sh_tasks.task_vk, 500, 'ЗД2_задание_ВК_отвод_дренажа', 'Задание разделу ВК')]


def build():
    doc = make_doc(); setup_dimstyle(doc); msp = doc.modelspace()
    for fn, ox, _, _ in TASKS:
        fn(msp, ox, 0)
    clean_dxf(doc)
    doc.saveas(os.path.join(OUT, f'{BASE}.ЗД_задания_КР_ВК.dxf'))
    for fn, ox, name, title in TASKS:
        p = os.path.join(OUT, f'{BASE}.{name}.pdf')
        sheet_pdf(doc, ox, 0, 'A3', 1, p)
        clean_pdf(p, f'{SHIFR}.{name[:3]}. {title}')
        print('задание', p)


if __name__ == '__main__':
    build()
