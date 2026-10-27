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
        TT = (0.5, 0.3, 0.7, 0.15, 0.85)
        pts = [(A[0] + (B[0] - A[0]) * tt, A[1] + (B[1] - A[1]) * tt) for tt in TT]
        strict = getattr(L, 'leads', None) is not None       # VLabels: сначала — без пересечения выносок
        if not (strict and any(L.shelf(at, t, h, strict=True) for at in pts)):
            for at in pts:
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


_UM = {}


def under_marks(key, V, box):
    """Настоящие габариты надписей подложки АР (TEXT, MTEXT) и марок помещений (блоки A-AREA-IDEN: номер
    в кружке), мм листа. under_texts ставит прямоугольник с центром в точке вставки, а у MTEXT она в левом
    верхнем углу — номер помещения с кружком оставался открытым для полок (ДП-1 на «1.4», лист 3)."""
    from ezdxf import recover, bbox
    from underlay import OX, OY
    src = UNDER[key]
    if src not in _UM:
        d, _ = recover.readfile(src)
        out = []
        for e in d.modelspace():
            t = e.dxftype()
            if t in ('TEXT', 'MTEXT') or (t == 'INSERT' and e.dxf.layer == 'A-AREA-IDEN'):
                try:
                    b = bbox.extents([e], fast=True)
                except Exception:
                    continue
                if b.has_data:
                    out.append(((b.extmin.x - OX) / 1000, (b.extmin.y - OY) / 1000,
                                (b.extmax.x - OX) / 1000, (b.extmax.y - OY) / 1000))
        _UM[src] = out
    res = []
    for x0, y0, x1, y1 in _UM[src]:
        a, c = V.P((x0, y0, 0)), V.P((x1, y1, 0))
        r = (min(a[0], c[0]), min(a[1], c[1]), max(a[0], c[0]), max(a[1], c[1]))
        if r[2] >= box[0] and r[0] <= box[2] and r[3] >= box[1] and r[1] <= box[3]:
            res.append(r)
    return res


def fragment(doc, sh, p, under, cx, cy, x0, y0, x1, y1, zr, systems, bld='h', title='', marks_floor=None,
             eqs=(), fits=True, label=True, skip=(), text=None, extra=None, leak=None, k=None, pipes=None,
             title_h=3.0, eq_nolabel=()):
    k = k or K
    w, h = (x1 - x0) * 1000 / k, (y1 - y0) * 1000 / k
    V, box = plan_doc(doc, sh, under, cx, cy, w, h, (x0 + x1) / 2, (y0 + y1) / 2, k, frame=zr)
    p.rect(*box, 'ТМ_оборуд_тонк')
    ax_top = axes_marks(p, V, box, bld)
    L = VLabels(p, box)
    for r in under_texts(UNDER[under], V, box) + under_marks(under, V, box):
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
        if eid in eq_nolabel:                      # подписано отдельной выноской листа
            continue
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
    if pp.id == 'Т4-ШВК2':
        return 'Т4 20: ШВК-2 → Пс-2 → Пс-1 → Н8'
    if pp.id == 'Т4-ШВК1':
        return 'Т4 20: ШВК-1 → Н8'
    if pp.id == 'В1-ШВК1':
        return f'В1 {dn}: КХ-10 → ШВК-1'
    if pp.id == 'Т3-ШВК1':
        return f'Т3 {dn}: Б1 → ШВК-1'
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
                                  ((15.60, 7.15, 3.95), 'Т4 20 — из ШВК-2 в полу к Пс-2,', 'далее под потолок гаража (лист 5)')):
            cc = [(-8, 10), (-8, 16), (-14, 22), (8, 30), (14, 30)] if t.startswith('В1 32') else None
            if not (cc and L.shelf(V.P((x, y, z)), t, 1.8, sub=sub, cands=cc, strict=True)):
                L.shelf(V.P((x, y, z)), t, 1.8, sub=sub)
        # Т3 к УМ-3 — полкой вправо вниз, мимо «2.8»: общим порядком выноска пересекала выноску «В1 32, Т3 25»
        at = V.P((15.95, 7.97, 3.925))
        if not L.shelf(at, 'Т3 16 → УМ-3', 1.6, cands=[(27, -21), (27, -18), (30, -21), (24, -21)], strict=True):
            L.shelf(at, 'Т3 16 → УМ-3', 1.6)
    fragment(doc, sh, p, 'plan2', 212, 211, X0, Y0, X1, Y1, zr, sysw,
             title='План 2 этажа: с/у 2.8, 2.9. Водопровод В1, Т3, Т4 и канализация К1. М 1:25', marks_floor=2,
             eqs=('ШВК-2',), extra=ex, text=txt2, leak=2, skip=('ШВК-2В', 'ШВК-2Т', 'Т3-УМ-3'),
             eq_nolabel=('ШВК-2',))
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
    'Заказчицы 26.10.2026; ТЗ-1). В1 и Т3 — снизу, из-под потолка гаража (лист 5). Коллекторы подключены '
    'независимо (Заказчица 27.10.2026): ШВК-1 питается своими линиями от топочной 1.6. Т3 ШВК-2 проходной: от его '
    'конца Т4 идёт в полу к Пс-2, затем под потолок гаража, к Пс-1 и к насосу Н8.',
    'Подводки от ШВК-2 — в пироге пола 2 этажа, в пазах утеплителя под стяжкой: В1 — нижний ряд, ось +3,870, Т3 — '
    'верхний ряд, ось +3,925; трубы одного ряда не пересекаются. Сквозь перегородку 2.9/2.8 — у пола, в гильзах; '
    'подъёмы к приборам — в инсталляциях и штробах (отметки присоединения — у приборов).',
    'Канализация 2 этажа: отводы от приборов — выпусками сквозь плиту в гильзах в сборный К1 Ø110 под потолком '
    'гаража (лист 5) к стояку Ст.К1-1 в стене гаража/1.9 (лист 6); вытяжная часть Ст.К1-1в — в стене по оси Г за '
    'инсталляцией УН-3, над кровлей 0,35 м. Унитазы — Ø110, ванны, душ, умывальники — Ø50 (П3).',
    'Дренаж конденсата К-4…К-6 и К-7 (ОВ) — в штробах стен к сифонам с сухим затвором в стене 2.9 и у ванны 2.9.',
    'Т4 ШВК-2 — в полу к Пс-2 (2.9), опуск под потолок гаража и подъём к Пс-1 (2.8). ДП-9…ДП-13 — датчики '
    'протечки на полу у приборов и под ШВК-2 (КЗП-1).',
]


def sheet5(doc, sh):
    """Сети под потолком гаража: магистрали В1, Т3 к ШВК-2 и от ШВК-2 к штробе ШВК-1, Т4, сборный К1."""
    p = PP(doc, sh.lay)
    zr = (2.7, 3.75)
    sysw = ('В1', 'Т3', 'Т4', 'К1', 'К1в')

    def ex(p, L, V, box):
        for pt, t, sub, cc in (((VK.ST1[0], VK.ST1[1], 3.3), 'Ст.К1-1 Ø110 вниз (в стене гаража/1.9)', 'ревизия +1,000',
                                [(10, -12), (10, -16), (14, -12), (8, 8)]),
                               ((19.30, 8.90, 3.4), 'Ст.К1-1в Ø110 вверх', 'ревизия в начале сборного',
                                [(-14, 3), (-14, 6), (-20, 3)]),        # верхняя точка — верхняя полка
                               ((19.18, 8.80, 3.0), 'В1, Т3, Т4 — в топочную 1.6', 'сквозь стену в гильзах',
                                [(-14, -4), (-14, -2), (-20, -4)]),
                               ((15.66, 7.97, 3.3), 'В1, Т3 — вверх в ШВК-2 (2 этаж)', 'сквозь плиту в гильзах', None),
                               ((15.53, 6.67, 3.3), 'Т4 от ШВК-2 и Пс-2 — сверху', None, None),
                               ((X_SH, 6.68, 3.0), 'В1 (КХ-10), Т3 (Б1) — вниз к ШВК-1,',
                                'Т4 ШВК-1 — снизу; штроба в стене гаража (лист 3)', None)):
            if (cc and L.shelf(V.P(pt), t, 1.8, sub=sub, cands=cc, strict=True)) or L.shelf(V.P(pt), t, 1.8, sub=sub):
                continue
            print('  !! нет места для полки:', t)
    fragment(doc, sh, p, 'plan1', 212, 211, X0, Y0, X1, Y1, zr, sysw,
             title='Сети под потолком гаража: В1, Т3, Т4, К1. М 1:25', extra=ex, text=txt2)
    sh.notes(24, 143, 205, NOTES5, h=1.8, spacing=1.0)
    legend2(p, 248, 132)
    return doc


X_SH = VK.X_SH


def _ins(p):
    return (13 if p.sys in ('Т3', 'Т4') else 9 if p.sys == 'В1' else 0) / 1000


# отметки под потолком гаража — из модели (те же правила, что в ТЗ-1: гараж южнее стены гараж/1.6, y < 8,75)
_CEIL = [p for p in VK.PIPES if p.bld == 'h' and (p.where == 'ceil' or p.id in ('В1-ШВК1', 'Т3-ШВК1'))]
_LOW = min(min(a[2], b[2]) - p.od / 2 - _ins(p) for p in _CEIL for a, b in zip(p.pts, p.pts[1:])
           if min(a[2], b[2]) > 2.5 and min(a[1], b[1]) < 8.75)
BOX_Z5 = math.floor((_LOW - 0.02) * 20) / 20


def _lv(z):
    return ('+' if z >= 0 else '') + f'{z:.3f}'.replace('.', ',')


_P5 = {p.id: p for p in VK.PIPES}
_KG = _P5['К1-гараж']
NOTES5 = [
    'План — проекция 3D-модели ВК (сети между потолком гаража +3,650 и низом подшивки). Отметки — от ±0,000.',
    f'Сети под потолком гаража — в подшивном потолке (коробе), ТЗ-1: низ подшивки не выше {_lv(BOX_Z5)} (низ труб в '
    f'изоляции — {_lv(_LOW)}: В1 к ШВК-1 у стены 1.6), люк 600×600 у ревизии в начале сборного К1 (у стены по оси Г). '
    'Соединений труб PE-Xa под подшивкой нет — от гребёнки КХ и Б1 до ШВК-2 и до ШВК-1 — цельные трубы.',
    f'Отметки осей: Т4 — {_lv(VK.Z_T4G)}; магистрали В1, Т3 к ШВК-2 — {_lv(VK.Z_GW)}, к ШВК-1 — {_lv(VK.Z_N1V)} и '
    f'{_lv(VK.Z_N1T)} (у стены 1.6 В1 к ШВК-1 обходит Т3 снизу на +2,850); сборный К1 Ø110 — ось от '
    f'{_lv(_KG.pts[0][2])} у Ст.К1-1в до {_lv(_KG.pts[-1][2])} у Ст.К1-1 (i = 0,02), отводы К1 от приборов 2 этажа — '
    'выше магистралей водопровода.',
    'Коллекторы подключены независимо (Заказчица 27.10.2026): ШВК-2 — В1 от КХ-4 и Т3 от Б1, Т4 → Пс-2 → Пс-1 → Н8; '
    'ШВК-1 — В1 от КХ-10 и Т3 тройником у Б1, Т4 — отдельно к Н8 (П4); кухня — своим кольцом от топочной 1.6 '
    '(лист 3). В1 и Т3 спускаются к ШВК-1 и Т4 поднимается от ШВК-1 — в штробе стены гаража у оси В. Выпуски '
    '2 этажа примыкают к сборному К1 косыми тройниками 45° по ходу стока, унитазы — в вертикальной плоскости.',
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
