"""Лист 44.1 «Ситуационный план» (ПП РФ № 87, п. 26 «н»): фрагмент плана внутриплощадочных дорог (лист 44, PDF
генпроектировщика) в М 1:500 с нанесёнными решениями раздела. Запуск: python3 situation.py <лист44.pdf> <лист> <листов>"""
import os, sys
import pymupdf
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
import pbdoc
from pbdoc import draw_stamp, THICK, THIN, INK

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out')
W, H = 420.0, 297.0
CLIP = (509.4, 378.0, 1233.4, 778.0)            # область листа 44 (пт, от верхнего левого угла)
DST = (25.0, 17.0)                              # куда она ложится на листе, мм от верхнего левого угла
K = 380.0 / (CLIP[2] - CLIP[0])                 # мм листа на 1 пт исходника; даёт М 1:500
RED = (0.85, 0.0, 0.0)
ORANGE = (0.95, 0.55, 0.0)
BLUE = (0.0, 0.25, 0.75)


def P(x, y):
    """Точка исходного листа 44 (пт) → координаты reportlab (мм от нижнего левого угла)."""
    return DST[0] + (x - CLIP[0]) * K, H - (DST[1] + (y - CLIP[1]) * K)


def overlay(path, sheet, total):
    c = canvas.Canvas(path, pagesize=(W * mm, H * mm))
    c.setTitle(pbdoc.SHIFR); c.setCreator(''); c.setProducer('')
    v = pbdoc.Vol.__new__(pbdoc.Vol)
    v.c = c

    def T(x, y, s, size=11, color=INK, align='L'):
        pbdoc.Vol.text(v, x, y, s, size, color, align)

    def L(x1, y1, x2, y2, w=THIN, color=INK):
        c.setLineWidth(w); c.setStrokeColorRGB(*color); c.line(x1 * mm, y1 * mm, x2 * mm, y2 * mm)
    # рамка и основная надпись
    for a in ((20, 5, 415, 5), (20, 292, 415, 292), (20, 5, 20, 292), (415, 5, 415, 292)):
        L(*a, THICK)
    draw_stamp(T, lambda *a: L(*a), 415 - 204.9, 'Ситуационный\nплан', sheet, total)
    # здание №25 и противопожарная стена по оси 6
    x0, y0 = P(794.1, 636.0); x1, y1 = P(948.7, 520.3)
    c.setStrokeColorRGB(*RED); c.setLineWidth(1.6); c.rect(x0 * mm, y0 * mm, (x1 - x0) * mm, (y1 - y0) * mm)
    c.setLineWidth(4.0); c.line(x1 * mm, y0 * mm, x1 * mm, y1 * mm)
    T((x0 + x1) / 2, (y0 + y1) / 2 + 6, 'Здание №25', 16, RED, 'C')
    T((x0 + x1) / 2, (y0 + y1) / 2 + 0.5, '2 этажа, II, С0, Ф4.3', 11, RED, 'C')
    T(x1 + 3, y1 - 8, 'Склад №26 (Ф5.2)', 13, RED)
    T(x1 + 3, y1 - 13, 'стена по оси 6 – противопожарная 1-го типа REI 150', 10, RED)
    # зоны подъезда пожарной техники 5–8 м от стен (1 м = K·(пт/м))
    m = 154.6 / 40.53 * K                       # мм листа на 1 м местности
    c.setFillColorRGB(*ORANGE, alpha=0.30); c.setStrokeColorRGB(*ORANGE)
    for rx, ry, rw, rh in ((x0, y1 + 5 * m, x1 - x0, 3 * m), (x0, y0 - 8 * m, x1 - x0, 3 * m),
                           (x0 - 8 * m, y0, 3 * m, y1 - y0)):
        c.rect(rx * mm, ry * mm, rw * mm, rh * mm, stroke=1, fill=1)
    c.setFillColorRGB(*INK, alpha=1)
    T(x0 + 2, y1 + 8.5 * m + 1.5, 'зона подъезда пожарной техники: 5–8 м от стены, проезд шириной не менее 3,5 м', 10, ORANGE)
    # гидранты
    for name, (gx, gy), dist in (('ПГ-21', (704.4, 578.8), '23,5 м'), ('ПГ-20', (1036.4, 659.8), '23,9 м')):
        px, py = P(gx, gy)
        c.setStrokeColorRGB(*BLUE); c.setLineWidth(1.0); c.circle(px * mm, py * mm, 2.2 * mm)
        T(px + 3, py + 2.5, f'{name}: до стены здания {dist}', 10, BLUE)
    # расстояния
    kx, ky = P(547.8, 494.0)
    L(x0, (y0 + y1) / 2 + 20, kx, (y0 + y1) / 2 + 20, THIN, BLUE)
    T((x0 + kx) / 2, (y0 + y1) / 2 + 21.5, 'до КПП №1 – 64 м', 10, BLUE, 'C')
    L((x0 + x1) / 2, y1, (x0 + x1) / 2, H - DST[1] - 1, THIN, BLUE)
    T((x0 + x1) / 2 + 2, H - DST[1] - 6, 'до зданий севернее внутриплощадочной дороги 5 – не менее 50 м', 10, BLUE)
    T(25, H - DST[1] + 3.0, 'Ситуационный план. Фрагмент плана внутриплощадочных дорог (лист 44). М 1:500', 14)
    # примечания
    notes = ['1. Подложка – план внутриплощадочных дорог (лист 44); решения раздела нанесены цветом.',
             '2. Здание №25 пристроено к складу №26 по оси 6; противопожарное расстояние не нормируется (п. 3 ТЧ).',
             '3. Наружное пожаротушение – 15 л/с, 3 ч, от ПГ-20 и ПГ-21 на кольцевой сети (п. 4.1 ТЧ);',
             '   рукавные линии 55–70 м по дорогам с твёрдым покрытием (дуги – по листу 44).',
             '4. Проезды для пожарной техники – с осей Е, А и 1; требования – задание ЗД-9 разделу ГП (п. 4.2 ТЧ).']
    for k, s in enumerate(notes):
        T(23, 62 - k * 4.6, s, 10)
    c.showPage(); c.save()


def build(src_pdf, sheet, total, path=None):
    path = path or os.path.join(OUT, 'gch', '44.1.pdf')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ov = path + '.ov.pdf'
    overlay(ov, sheet, total)
    doc = pymupdf.open()
    page = doc.new_page(width=W * 72 / 25.4, height=H * 72 / 25.4)
    src = pymupdf.open(src_pdf)
    r = pymupdf.Rect(DST[0] * 72 / 25.4, DST[1] * 72 / 25.4, (DST[0] + 380) * 72 / 25.4,
                     (DST[1] + (CLIP[3] - CLIP[1]) * K) * 72 / 25.4)
    sp = src[0]
    clip = pymupdf.Rect(*CLIP) * sp.derotation_matrix          # лист 44 повёрнут на 270°: обрезка задаётся в исходных координатах
    page.show_pdf_page(r, src, 0, clip=clip, rotate=-sp.rotation)
    page.show_pdf_page(page.rect, pymupdf.open(ov), 0)
    doc.save(path, garbage=3, deflate=True)
    os.remove(ov)
    return path


if __name__ == '__main__':
    print(build(sys.argv[1], int(sys.argv[2]), int(sys.argv[3])))
