"""И05.09.26-ВК, листы 4 и 5. Фрагменты планов М 1:25 — проекции 3D-модели vk_model.

Лист 4 (А3): с/у 1.4 и ШВК-1 (сети в полу), топочная 1.6 (сети в полу, гребёнка КХ, выходы).
Лист 5 (А2): сети под потолком гаража (магистрали, ШВК-2, подводки 2 этажа, Т4, К1) и план 2 этажа — с/у 2.8, 2.9
(подъёмы сквозь плиту, подводки в пироге пола, отводы К1).

python3 sheets/vk_frag.py [4|5]
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from rdbase import new_doc, RDSheet, save_and_pdf, UNDER  # noqa: E402
import vk_model as VK  # noqa: E402
from vk_draw import (CODE_VK, BLD_VK, VK_LIST, VK_TOTAL, setup, finish_layers, PP, VLabels, plan_doc, under_texts,  # noqa
                     draw_net, vk_fit, longest_seg, fixture_marks, in_box, lev, f1, DN_SHORT, draw_eq)

OUT = os.path.join(ROOT, 'out')
K = 25
SHORT = {'16×2,2': '16', '20×2,8': '20', '25×3,5': '25', '32×4,4': '32'}


def target(pp):
    """Куда идёт труба — для подписи."""
    fx = [s for s in pp.serves if s in VK.FIXT]
    if fx:
        return ', '.join(fx)
    return {'*дом': 'дом', '*1эт': 'ШВК-1', '*баня': 'баня', 'Т4': 'циркуляция', '*': 'все'}.get(
        pp.serves[0] if pp.serves else '', pp.name)


def label_pipes(L, V, pipes, box, zr, h=1.6, skip=(), text=None):
    for pp in pipes:
        if pp.id in skip:
            continue
        seg = longest_seg(V, pp, box, zr=zr, horiz=not pp.sys.startswith('К1'))
        if not seg or seg[0] < 5.0:
            continue
        Lm, c, A, B = seg
        dn = f'Ø{pp.dn}' if pp.mat in ('pp', 'ppn') else SHORT.get(pp.dn, pp.dn)
        t = text(pp) if text else f'{pp.sys} {dn} → {target(pp)}'
        for tt in (0.5, 0.3, 0.7, 0.15, 0.85):
            at = (A[0] + (B[0] - A[0]) * tt, A[1] + (B[1] - A[1]) * tt)
            if L.shelf(at, t, h):
                break


def fragment(doc, sh, p, under, cx, cy, x0, y0, x1, y1, zr, systems, bld='h', title='', marks_floor=None,
             eqs=(), fits=True, label=True, skip=(), text=None, extra=None):
    w, h = (x1 - x0) * 1000 / K, (y1 - y0) * 1000 / K
    V, box = plan_doc(doc, sh, under, cx, cy, w, h, (x0 + x1) / 2, (y0 + y1) / 2, K, frame=zr)
    p.rect(*box, 'ТМ_оборуд_тонк')
    L = VLabels(p, box)
    for r in under_texts(UNDER[under], V, box):
        L.block(r)
    pipes = [pp for pp in VK.PIPES if pp.bld == bld and pp.sys in systems]
    draw_net(p, V, pipes, box, zr=zr, L=L)
    E = {e.id: e for e in VK.EQUIP}
    for eid in eqs:
        e = E[eid]
        x_0, y_0, z_0, x_1, y_1, z_1 = e.bbox()
        a, b = V.P((x_0, y_0, 0)), V.P((x_1, y_1, 0))
        r = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
        p.rect(*r, 'ТМ_оборуд', ltype='ОВ_ШТРИХ' if e.ctx else None)
    if fits:
        for f in VK.FITS:
            if f.pipe in pipes and zr[0] <= f.pos[2] <= zr[1] and in_box(V.P(f.pos), box):
                vk_fit(p, V, f, scale=0.8)
    if marks_floor is not None:
        fixture_marks(p, L, V, box, bld, floor=marks_floor, h=1.8)
    if extra:
        extra(p, L, V, box)
    if label:
        label_pipes(L, V, pipes, box, zr, skip=skip, text=text)
    for eid in eqs:
        e = E[eid]
        bb = e.bbox()
        c = V.P(((bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, 0))
        L.shelf(c, e.mark if not e.ctx else e.name.split(' (')[0], 1.8)
    if title:
        sh.s.text(title, cx, box[3] + 4.0, h=3.0, align='center')
    return V, box, L


def sheet4(doc, sh):
    p = PP(doc, sh.lay)
    zr = (-1.3, 2.6)
    sysw = ('В1', 'Т3', 'Т4')

    def ex_a(p, L, V, box):
        for pt, t, sub in (((12.87, 7.05, 0), 'ШВК-1: В1 — выходы к 1.4 вперёд и вниз,', 'Т3 — вниз у стены (лист 13)'),):
            L.shelf(V.P(pt), t, 1.8, sub=sub)
    fragment(doc, sh, p, 'plan1', 100, 205, 9.70, 4.40, 13.45, 7.70, zr, sysw, title='С/у 1.4 и ШВК-1. М 1:25',
             marks_floor=1, eqs=('ШВК-1',), extra=ex_a, skip=('ШВК-1В', 'ШВК-1Т'))

    def ex_b(p, L, V, box):
        for pt, t, sub in (((19.40, 9.45, 0), 'Приямок ввода 600×600, дно -1,100', 'ввод ПЭ 32 — лист 7'),
                           ((19.25, 13.46, 0), 'Ecoflex Quattro: санитарная 32×4,4 — В1 в баню', 'вторая (20×2,8) — резерв'),
                           ((18.80, 11.10, 0), 'Б1 (ТМ): Т3 от Б1, Т4 к Б1', 'граница с ТМ'),):
            L.shelf(V.P(pt), t, 1.8, sub=sub)
    fragment(doc, sh, p, 'plan1', 300, 172, 17.60, 9.05, 20.45, 13.90, zr, sysw, title='Топочная 1.6. М 1:25',
             marks_floor=1, eqs=('КХ', 'ПРВ'), extra=ex_b, skip=('КХ', 'В1-узел'),
             text=lambda pp: (f'{pp.id}: В1 {SHORT.get(pp.dn, pp.dn)} → {target(pp)}' if pp.id.startswith('КХ-')
                              else f'{pp.sys} {SHORT.get(pp.dn, pp.dn)} → {target(pp)}'))
    sh.notes(24, 124, 200, NOTES4, h=1.8, spacing=1.0)
    return doc


NOTES4 = [
    'Фрагменты — проекции 3D-модели (лист 3 — общий план). Отметки — оси труб от ±0,000.',
    'Ряды в утеплителе пола: В1 — ось −0,230, Т3, Т4 — ось −0,175. Выходы из шкафа ШВК-1 и гребёнки КХ — '
    'вертикально вниз в пол в гофре с фиксатором поворота; трубы между выходом и полосой — в том же ряду.',
    'Подъёмы к приборам — в инсталляциях и штробах: отметки присоединения указаны на листе 3; подводки — с '
    'фиксаторами поворота 90° у выхода из пола и настенными водорозетками (угольниками) у приборов.',
    'Гребёнка КХ — Ду32 на 7 выходов с шаровыми кранами на каждом выходе и маркировкой назначения (лист 7).',
    'В топочной трубы над полом — по стенам на хомутах с резиновыми вкладышами; под Б1 и котлами — без '
    'соединений.',
]


def sheet5(doc, sh):
    p = PP(doc, sh.lay)
    zr = (2.7, 3.75)
    sysw = ('В1', 'Т3', 'Т4', 'К1', 'К1в')

    def txt(pp):
        dn = f'Ø{pp.dn}' if pp.mat in ('pp', 'ppn') else SHORT.get(pp.dn, pp.dn)
        if pp.sys == 'К1':
            return f'К1 {dn} от {target(pp)}' if pp.id != 'К1-гараж' else 'К1 Ø110 сборный, i=0,02 → Ст.К1-1'
        return f'{pp.sys} {dn} → {target(pp)}'

    def ex1(p, L, V, box):
        for pt, t, sub in (((12.97, 8.55, 0), 'Ст.К1-1 Ø110 вниз', 'ревизия +1,000'),
                           ((19.68, 8.58, 0), 'Ст.К1-1в Ø110 вверх', 'прочистка в начале сборного'),
                           ((19.10, 8.70, 0), 'В1, Т3, Т4 — в топочную 1.6', 'сквозь стену в гильзах')):
            L.shelf(V.P(pt), t, 1.8, sub=sub)
    fragment(doc, sh, p, 'plan1', 180, 318, 12.55, 6.35, 20.05, 9.00, zr, sysw,
             title='Сети под потолком гаража (В1, Т3, Т4, К1). М 1:25', eqs=('ШВК-2',), extra=ex1,
             skip=('ШВК-2В', 'ШВК-2Т'), text=txt)
    zr2 = (3.80, 6.5)

    def ex2(p, L, V, box):
        for (x, y), t in (((15.53, 6.88), 'Пс-2 (Т4)'), ((19.73, 7.65), 'Пс-1 (Т4)')):
            L.shelf(V.P((x, y, 0)), t, 1.8)
    fragment(doc, sh, p, 'plan2', 180, 160, 12.55, 6.35, 20.05, 9.00, zr2, sysw, title='План 2 этажа: с/у 2.9, 2.8. М 1:25',
             marks_floor=2, extra=ex2, text=txt)
    sh.notes(344, 400, 236, NOTES5, h=1.9, spacing=1.0)
    return doc


NOTES5 = [
    'Сети 2 этажа (кроме коротких подводок в пироге пола у стен 2.8, 2.9) проложены под потолком гаража в подшивном '
    'потолке (коробе) — ТЗ-1: низ короба не выше +2,900, люки 600×600 у ШВК-2 и у прочистки в начале сборного К1.',
    'Отметки осей: Т4 — +2,970; магистрали и коллекторы ШВК-2 — +3,050; ряд отводов В1 — +3,170, Т3 — +3,250 (выше '
    'коллекторов, ниже К1); сборный К1 Ø110 — ось от +3,400 у Ст.К1-1в до +3,265 у Ст.К1-1 (i = 0,02), отводы К1 '
    'от приборов — выше рядов водопровода.',
    'Подъёмы к приборам 2 этажа — сквозь плиту в гильзах (лист 14) у стен и в инсталляциях; подводки к УН-2, В-2, '
    'УН-3 — в утеплителе пола 2 этажа (+3,910) к стене; Т4 — подъёмы к полотенцесушителям Пс-2, Пс-1.',
    'Порядок выходов на коллекторах ШВК-2 согласован с рядами: трубы одной системы не пересекаются, выходы Т3 '
    'отстоят от труб В1 не менее чем на 60 мм; проверка пересечений по 3D-модели — 0 (с ОВ, ТМ и между собой).',
    'Крепление труб PE-Xa под потолком — в лотках или на подвесах с хомутами, шаг — не более 0,5 м (16, 20), '
    '0,6 м (25, 32); К1 — хомуты под каждым раструбом, не реже 10 диаметров; уклон К1 — не менее 0,02.',
    'Конденсат кондиционеров К-4…К-6 и К-7 (ОВ) — в сифоны с сухим затвором за инсталляцией 2.9 и у ванны 2.9, '
    'далее в отводы К1.',
]

if __name__ == '__main__':
    no = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    doc = new_doc()
    setup(doc)
    sh = RDSheet(doc, 'Лист', VK_LIST[no], no, VK_TOTAL, fmt='А3' if no == 4 else 'А2', code=CODE_VK, bld=BLD_VK)
    (sheet4 if no == 4 else sheet5)(doc, sh)
    finish_layers(doc)
    print(save_and_pdf(doc, os.path.join(OUT, f'vk_frag_{no}.dxf')))
