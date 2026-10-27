"""И05.09.26-ВК, листы 4 и 5. Планы М 1:25 — проекции 3D-модели vk_model.

Лист 4 (А3): план 2 этажа — с/у 2.8, 2.9: ШВК-2, подводки в пироге пола, канализация К1 (выпуски сквозь плиту).
Лист 5 (А3): сети под потолком гаража — магистрали В1, Т3, Т4, сборный К1.

python3 sheets/vk_frag.py [4|5]
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from rdbase import new_doc, RDSheet, save_and_pdf, UNDER, HOUSE_AX, BATH_AX  # noqa: E402
import vk_model as VK  # noqa: E402
from vk_draw import (CODE_VK, BLD_VK, VK_LIST, VK_TOTAL, setup, finish_layers, PP, VLabels, plan_doc, under_texts,  # noqa
                     draw_net, vk_fit, longest_seg, fixture_marks, in_box, lev, f1, DN_SHORT, draw_eq, leak_marks, leak_block)

OUT = os.path.join(ROOT, 'out')
K = 25
SHORT = {'16×2,2': '16', '20×2,8': '20', '25×3,5': '25', '32×4,4': '32'}


def target(pp):
    """Куда идёт труба — для подписи."""
    fx = [s for s in pp.serves if s in VK.FIXT]
    if fx:
        return ', '.join(fx)
    return {'*дом': 'дом', '*1эт': 'ШВК-1', '*баня': 'баня', 'Т4': 'циркуляция', '*': 'все', '*АП': 'автополив'}.get(
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


def axes_marks(p, V, box, bld='h'):
    """Марки координационных осей, попавших в окно: вертикальных — над окном, горизонтальных — слева
    (справа, если слева до рамки листа нет места). Возвращает True, если марки стоят над окном."""
    xs, ys = BATH_AX if bld == 'b' else HOUSE_AX
    top = False
    for n, x in xs:
        a = V.P((x, 0, 0))
        if box[0] + 2 <= a[0] <= box[2] - 2:
            yt = box[3] + 6.0
            p.line(a[0], box[3], a[0], yt - 4.0, 'ТМ_оси', ltype='ОВ_ШП')
            p.circle(a[0], yt, 0, 'ТМ_оси', r_paper=4.0)
            p.t(a[0], yt, n, 3.0, 'center', 'ТМ_оси')
            top = True
    left = box[0] - 10.0 >= 22.0
    for n, y in ys:
        a = V.P((0, y, 0))
        if box[1] + 2 <= a[1] <= box[3] - 2:
            xc = box[0] - 6.0 if left else box[2] + 6.0
            p.line(box[0] if left else box[2], a[1], xc + (4.0 if left else -4.0), a[1], 'ТМ_оси', ltype='ОВ_ШП')
            p.circle(xc, a[1], 0, 'ТМ_оси', r_paper=4.0)
            p.t(xc, a[1], n, 3.0, 'center', 'ТМ_оси')
    return top


def fragment(doc, sh, p, under, cx, cy, x0, y0, x1, y1, zr, systems, bld='h', title='', marks_floor=None,
             eqs=(), fits=True, label=True, skip=(), text=None, extra=None, leak=None, k=None, pipes=None,
             title_h=3.0):
    k = k or K
    w, h = (x1 - x0) * 1000 / k, (y1 - y0) * 1000 / k
    V, box = plan_doc(doc, sh, under, cx, cy, w, h, (x0 + x1) / 2, (y0 + y1) / 2, k, frame=zr)
    p.rect(*box, 'ТМ_оборуд_тонк')
    ax_top = axes_marks(p, V, box, bld)
    L = VLabels(p, box)
    for r in under_texts(UNDER[under], V, box):
        L.block(r)
    if pipes is None:
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
    if leak is not None:
        leak_block(L, V, box, bld, leak)
    if marks_floor is not None:
        fixture_marks(p, L, V, box, bld, floor=marks_floor, h=1.8)
    if leak is not None:
        leak_marks(p, L, V, box, bld, leak)
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
        sh.s.text(title, cx, box[3] + (13.0 if ax_top else 4.0), h=title_h, align='center')
    return V, box, L


def txt2(pp):
    dn = f'Ø{pp.dn}' if pp.mat in ('pp', 'ppn') else SHORT.get(pp.dn, pp.dn)
    if pp.sys == 'К1':
        src = target(pp).replace('Сифон', 'сифона', 1)
        return f'К1 {dn} от {src}' if pp.id != 'К1-гараж' else 'К1 Ø110 сборный, i=0,02 → Ст.К1-1'
    if pp.id == 'Т4-дом':
        return 'Т4 20: от ШВК-1 → Пс-2 → Пс-1 → Н8'
    if pp.id in ('В1-ШВК1', 'Т3-ШВК1'):
        return f'{pp.sys} {dn}: ШВК-2 → ШВК-1'
    tg = target(pp)
    return f'{pp.sys} {dn} → {"ШВК-2" if tg == "дом" else tg}'


X0, Y0, X1, Y1 = 12.40, 6.20, 20.10, 9.15            # окно планов листов 4 и 5, м (7,7 × 2,95 м)


def sheet4(doc, sh):
    """План 2 этажа: с/у 2.8, 2.9 — водопровод в пироге пола от ШВК-2 и канализация К1 (выпуски сквозь плиту)."""
    p = PP(doc, sh.lay)
    zr = (3.80, 6.5)
    sysw = ('В1', 'Т3', 'Т4', 'К1', 'К1в')

    def ex(p, L, V, box):
        for (x, y, z), t, sub in (((15.53, 6.88, 4.3), 'Пс-2 (Т4)', None), ((19.73, 7.65, 4.3), 'Пс-1 (Т4)', None),
                                  ((15.66, 7.55, 4.6), 'ШВК-2: ниша в перегородке 2.9/2.8,', 'люк со стороны 2.9 (лист 13)'),
                                  ((19.30, 8.90, 4.5), 'Ст.К1-1в Ø110 — вытяжная часть', 'в стене по оси Г, на кровлю'),
                                  ((15.66, 7.99, 4.0), 'В1 32, Т3 25 — снизу, из-под потолка гаража', 'лист 5'),
                                  ((15.66, 7.20, 4.0), 'В1 25, Т3 25 — вниз, к ШВК-1', 'лист 5')):
            L.shelf(V.P((x, y, z)), t, 1.8, sub=sub)
    fragment(doc, sh, p, 'plan2', 212, 211, X0, Y0, X1, Y1, zr, sysw,
             title='План 2 этажа: с/у 2.8, 2.9. Водопровод В1, Т3, Т4 и канализация К1. М 1:25', marks_floor=2,
             eqs=('ШВК-2',), extra=ex, text=txt2, leak=2, skip=('ШВК-2В', 'ШВК-2Т'))
    sh.notes(24, 143, 205, NOTES4, h=1.8, spacing=1.0)
    legend2(p, 248, 132)
    return doc


def legend2(p, x, y):
    from vk_draw import leak_sym
    rows = [('В1', 'ВК_В1', None, 'водопровод холодной воды'), ('Т3', 'ВК_Т3', None, 'горячая вода, подающий'),
            ('Т4', 'ВК_Т4', 'ОВ_ШТРИХ', 'горячая вода, циркуляционный'), ('К1', 'ВК_К1', None, 'бытовая канализация'),
            ('К1в', 'ВК_К1в', 'ОВ_ШП', 'вытяжная часть стояка')]
    p.t(x, y + 6, 'Условные обозначения', 2.2, 'bl', 'ТМ_текст')
    for i, (c, lay, lt, t) in enumerate(rows):
        yy = y - i * 4.6
        p.pl([(x, yy), (x + 12, yy)], lay, ltype=lt, lw=50)
        p.t(x + 15, yy, f'{c} — {t}', 1.8, 'left', 'ТМ_текст')
    yy = y - len(rows) * 4.6
    p.circle(x + 6, yy, 0, 'ВК_В1', r_paper=0.9)
    p.t(x + 15, yy, 'стояк, подъём, выпуск сквозь плиту', 1.8, 'left', 'ТМ_текст')
    yy -= 4.6
    leak_sym(p, (x + 6, yy))
    p.t(x + 15, yy, 'ДП — датчик протечки', 1.8, 'left', 'ТМ_текст')


NOTES4 = [
    'План — проекция 3D-модели ВК. Отметки — от ±0,000 (пол 2 этажа +4,050, верх плиты +3,850).',
    'Коллектор ШВК-2 — в нише перегородки 2.9/2.8 со стороны с/у 2.9, нажимной люк под плитку (замечание '
    'Заказчицы 26.10.2026; ТЗ-1). В1 и Т3 проходные: снизу — из-под потолка гаража, вниз — к ШВК-1 (лист 5).',
    'Подводки от ШВК-2 — в пироге пола 2 этажа, в пазах утеплителя под стяжкой: В1 — нижний ряд, ось +3,870, Т3 — '
    'верхний ряд, ось +3,925; трубы одного ряда не пересекаются. Сквозь перегородку 2.9/2.8 — у пола, в гильзах; '
    'подъёмы к приборам — в инсталляциях и штробах (отметки присоединения — у приборов).',
    'Канализация 2 этажа: отводы от приборов — выпусками сквозь плиту в гильзах в сборный К1 Ø110 под потолком '
    'гаража (лист 5) к стояку Ст.К1-1 в стене гаража/1.9 (лист 6); вытяжная часть Ст.К1-1в — в стене по оси Г за '
    'инсталляцией УН-3, над кровлей 0,35 м. Унитазы — Ø110, ванны, душ, умывальники — Ø50 (П3).',
    'Дренаж конденсата К-4…К-6 и К-7 (ОВ) — в штробах стен к сифонам с сухим затвором в стене 2.9 и у ванны 2.9.',
    'Т4 — подъёмы из-под потолка гаража к полотенцесушителям Пс-2 (2.9) и Пс-1 (2.8). ДП-9…ДП-13 — датчики '
    'протечки на полу у приборов и под ШВК-2 (КЗП-1).',
]


def sheet5(doc, sh):
    """Сети под потолком гаража: магистрали В1, Т3 к ШВК-2 и от ШВК-2 к штробе ШВК-1, Т4, сборный К1."""
    p = PP(doc, sh.lay)
    zr = (2.7, 3.75)
    sysw = ('В1', 'Т3', 'Т4', 'К1', 'К1в')

    def ex(p, L, V, box):
        for pt, t, sub in (((VK.ST1[0], VK.ST1[1], 3.3), 'Ст.К1-1 Ø110 вниз (в стене гаража/1.9)', 'ревизия +1,000'),
                           ((19.30, 8.90, 3.4), 'Ст.К1-1в Ø110 вверх', 'ревизия в начале сборного'),
                           ((19.18, 8.80, 3.0), 'В1, Т3, Т4 — в топочную 1.6', 'сквозь стену в гильзах'),
                           ((15.66, 7.60, 3.3), 'В1, Т3 — в ШВК-2 (2 этаж) и обратно', 'сквозь плиту в гильзах'),
                           ((X_SH, 6.68, 3.0), 'В1, Т3 — вниз к ШВК-1, Т4 — снизу', 'штроба в стене гаража (лист 3)')):
            L.shelf(V.P(pt), t, 1.8, sub=sub)
    fragment(doc, sh, p, 'plan1', 212, 211, X0, Y0, X1, Y1, zr, sysw,
             title='Сети под потолком гаража: В1, Т3, Т4, К1. М 1:25', extra=ex, text=txt2)
    sh.notes(24, 143, 205, NOTES5, h=1.8, spacing=1.0)
    legend2(p, 248, 132)
    return doc


X_SH = VK.X_SH
NOTES5 = [
    'План — проекция 3D-модели ВК (сети между потолком гаража +3,650 и низом подшивки). Отметки — от ±0,000.',
    'Сети под потолком гаража — в подшивном потолке (коробе), ТЗ-1: низ подшивки не выше +2,900, люк 600×600 у '
    'ревизии в начале сборного К1 (у стены по оси Г). Соединений труб PE-Xa под подшивкой нет — от гребёнки КХ и '
    'Б1 до ШВК-2 и от ШВК-2 до ШВК-1 — цельные трубы.',
    'Отметки осей: Т4 — +2,970; магистрали В1, Т3 — +3,050; сборный К1 Ø110 — ось от +3,420 у Ст.К1-1в до '
    '≈+3,280 у Ст.К1-1 (i = 0,02), отводы К1 от приборов 2 этажа — выше магистралей водопровода.',
    'Кольцо ГВС санузлов: Б1 → Т3 → ШВК-2 (2 этаж) → ШВК-1 (с/у 1.4) → Т4 → Пс-2 → Пс-1 → Н8 → Б1 (П4); кухня — '
    'своим кольцом от топочной 1.6 (лист 3). В1 и Т3 спускаются к ШВК-1 и Т4 поднимается от ШВК-1 — в штробе '
    'стены гаража у оси В.',
    'Крепление труб PE-Xa под потолком — в лотках или на подвесах с хомутами, шаг — не более 0,5 м (16, 20), '
    '0,6 м (25, 32); К1 — хомуты под каждым раструбом, не реже 10 диаметров; уклон К1: Ø110 — 0,02, Ø50 — 0,03.',
    'К1 внутри дома (сборный под потолком гаража, стояк Ст.К1-1, отводы 2 этажа) — бесшумные трубы и фасонные части '
    '(ВК.СО), хомуты с резиновыми вкладышами. Проверка пересечений по 3D-модели — 0 (между собой, с ТМ).',
]


if __name__ == '__main__':
    no = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    doc = new_doc()
    setup(doc)
    sh = RDSheet(doc, 'Лист', VK_LIST[no], no, VK_TOTAL, fmt='А3', code=CODE_VK, bld=BLD_VK)
    (sheet4 if no == 4 else sheet5)(doc, sh)
    finish_layers(doc)
    print(save_and_pdf(doc, os.path.join(OUT, f'vk_frag_{no}.dxf')))
