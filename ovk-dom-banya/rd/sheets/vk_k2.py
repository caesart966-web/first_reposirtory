"""И05.09.26-ВК, лист 15 (А1). Внутренние водостоки К2 (Заказчица 30.10.2026: «водосточные трубы внутри стен —
чугунные безраструбные Smart SML; подключение — через дождеприёмники; в стенах до дождеприёмника чугун, после — в
грунте пластик»; расположение воронок — АР03, АР13.1, АР14 от 30.10.2026).

План кровли над 2 этажом, план кровли над 1 этажом, план 1 этажа (М 1:100) — проекции модели vk_model (K2_STACKS),
схема стояков, таблица по П5, примечания.

python3 sheets/vk_k2.py  ->  out/vk_k2_15.dxf + PDF
"""
import contextlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import rdbase  # noqa: E402
from rdbase import new_doc, RDSheet, save_and_pdf, HOUSE_AX, UNDER  # noqa: E402
import vk_model as VK  # noqa: E402
import vk_draw  # noqa: E402
from vk_draw import (CODE_VK, BLD_VK, VK_LIST, VK_TOTAL, setup, finish_layers, PP, VLabels as Labels, plan_doc,  # noqa
                     under_lines, under_texts, in_box, lev)

OUT = os.path.join(ROOT, 'out')
NO = 15
# новые выгрузки АР от 30.10.2026 — только для этого листа (остальные листы ВК и ОВ — на прежних подложках)
UNDER.update({'k2roof2': os.path.join(rdbase.AR, 'ar14_3010.dxf'),
              'k2roof1': os.path.join(rdbase.AR, 'ar131_3010.dxf'),
              'k2plan1': os.path.join(rdbase.AR, 'ar03_3010.dxf')})
vk_draw.UNDER_DY.update({'k2roof2': 240.0, 'k2roof1': 300.0, 'k2plan1': 360.0})
CALC = json.load(open(os.path.join(OUT, 'vk', 'vk_calc.json')))['k2']
R = {r['id']: r for r in CALC['rows']}
PIPES = {p.id: p for p in VK.PIPES}
REV = {f.extra.get('riser'): f for f in VK.FITS if f.kind == 'revision' and str(f.extra.get('riser', '')).startswith('Ст.К2')}
K = 100
MX0, MX1, MY0, MY1 = -3.0, 23.0, -2.6, 18.4          # окно планов в модели, м (26 × 21 м → 260 × 210 мм)
W, H = (MX1 - MX0) * 1000 / K, (MY1 - MY0) * 1000 / K


def f2(v, n=2):
    return f'{v:.{n}f}'.replace('.', ',')


def axes(p, V, box, left=True):
    xs, ys = HOUSE_AX
    for n, x in xs:
        a = V.P((x, 0, 0))
        p.line(a[0], box[3], a[0], box[3] + 2.5, 'ТМ_оси', ltype='ОВ_ШП')
        p.circle(a[0], box[3] + 5.5, 0, 'ТМ_оси', r_paper=3.0)
        p.t(a[0], box[3] + 5.5, n, 2.5, 'center', 'ТМ_оси')
    if left:
        for n, y in ys:
            if n in ('Б', 'Е'):                       # близкие оси — без кружков, чтобы кружки не налезали
                continue
            a = V.P((0, y, 0))
            p.line(box[0] - 2.5, a[1], box[0], a[1], 'ТМ_оси', ltype='ОВ_ШП')
            p.circle(box[0] - 5.5, a[1], 0, 'ТМ_оси', r_paper=3.0)
            p.t(box[0] - 5.5, a[1], n, 2.5, 'center', 'ТМ_оси')


_RL = {}


def roof_lines(src, V, box, layers=('A-DETL', 'A-FLOR', 'S-GRID')):
    """Коньки и ендовы (A-DETL, красные), края кровли (A-FLOR) и оси (S-GRID) подложки — отрезки листа, как under_lines
    (у той кеш по файлу, другой набор слоёв через неё не взять)."""
    import ezdxf
    from underlay import OX, OY
    if (src, layers) not in _RL:
        d = ezdxf.readfile(src)
        out = []
        for e in d.modelspace().query('LINE LWPOLYLINE'):
            if e.dxf.layer not in layers:
                continue
            pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)] if e.dxftype() == 'LINE' else \
                [(q[0], q[1]) for q in e.get_points('xy')]
            out.extend((a, b) for a, b in zip(pts, pts[1:]) if math.dist(a, b) > 1.0)
        _RL[(src, layers)] = [(((a[0] - OX) / 1000, (a[1] - OY) / 1000), ((b[0] - OX) / 1000, (b[1] - OY) / 1000)) for a, b in out]
    res = []
    for a, b in _RL[(src, layers)]:
        A, B = V.P((a[0], a[1], 0)), V.P((b[0], b[1], 0))
        if max(A[0], B[0]) >= box[0] and min(A[0], B[0]) <= box[2] and max(A[1], B[1]) >= box[1] and \
                min(A[1], B[1]) <= box[3]:
            res.append((A, B))
    return res


def view(doc, sh, key, cx, cy):
    V, box = plan_doc(doc, sh, key, cx, cy, W, H, (MX0 + MX1) / 2, (MY0 + MY1) / 2, K)
    sh.p.rect(*box, 'ТМ_оборуд_тонк')
    L = Labels(sh.p, box)
    for r in under_texts(UNDER[key], V, box):
        L.block(r)
    L.add_segs(under_lines(UNDER[key], V, box))
    # подписи мимо осей, на кровлях — и мимо коньков, ендов и краёв кровли (просьба Заказчицы: выноски на пустые поля)
    L.add_segs(roof_lines(UNDER[key], V, box) if key.startswith('k2roof') else
               roof_lines(UNDER[key], V, box, layers=('S-GRID',)))
    L.far_r = (30, 40, 50, 60)
    return V, box, L


@contextlib.contextmanager
def own_free(L, r):
    """На время подписи знака снять его собственную рамку: выноска начинается внутри неё и иначе считалась бы
    пересечением — тогда полка уходила в запасной поиск, мимо заданных мест."""
    L.busy.remove(r)
    try:
        yield
    finally:
        L.busy.append(r)


def funnel(p, c, r=2.0):
    """Воронка кровельная: окружность с крестом (условно)."""
    p.circle(c[0], c[1], 0, 'ВК_К2', r_paper=r)
    p.circle(c[0], c[1], 0, 'ВК_К2', r_paper=r * 0.45)
    p.line(c[0] - r, c[1], c[0] + r, c[1], 'ВК_К2')
    p.line(c[0], c[1] - r, c[0], c[1] + r, 'ВК_К2')


def stack_dot(p, c, r=1.1):
    p.circle(c[0], c[1], 0, 'ВК_К2', r_paper=r, fill=5)


def roof_plan(doc, sh, key, cx, cy, roof, title):
    V, box, L = view(doc, sh, key, cx, cy)
    axes(sh.p, V, box)
    p = sh.p
    own = {}                                        # знак у точки: свою выноску не запирает (own_free)
    for n, xy, rf, path, d, room in VK.K2_STACKS:
        c = V.P((xy[0], xy[1], 0))
        if rf == roof:
            funnel(p, c)
            own[n] = (c[0] - 2.2, c[1] - 2.2, c[0] + 2.2, c[1] + 2.2)
        elif roof == 'low':                         # стояк с верхней кровли проходит 2 этаж в стене
            stack_dot(p, c)
            own[n] = (c[0] - 1.3, c[1] - 1.3, c[0] + 1.3, c[1] + 1.3)
        if n in own:
            L.block(own[n])
    for n, xy, rf, path, d, room in VK.K2_STACKS:
        c = V.P((xy[0], xy[1], 0))
        r = R[n]
        # одна строка: площадь, расход и отметка — в таблице и на схеме этого листа (подписи — на чистом поле)
        if rf == roof:
            t = f'Вр-{n} → Ст.К2-{n}'
        elif roof == 'low':
            t = f'Ст.К2-{n} — в стене 2 этажа'
        else:
            continue
        with own_free(L, own[n]):
            if L.shelf(c, t, 1.8, strict=True) is None and L.soft([(c, None)], t, 1.8) is None:
                print('  !! нет места:', t)
    sh.title(cx, box[3] + 13.0, title, h=3.2)
    return V, box


def floor_plan(doc, sh, cx, cy):
    V, box, L = view(doc, sh, 'k2plan1', cx, cy)
    axes(sh.p, V, box)
    p = sh.p
    own = {}
    for n, xy, rf, path, d, room in VK.K2_STACKS:
        c = V.P((xy[0], xy[1], 0))
        stack_dot(p, c)
        out = PIPES[f'К2-ДК{n}']
        pts = [V.P(q) for q in out.pts]
        p.pl(pts, 'ВК_К2', lw=50)
        dk = VK.K2_DK[n]
        a, b = V.P((dk[0] - VK.DK_HALF, dk[1] - VK.DK_HALF, 0)), V.P((dk[0] + VK.DK_HALF, dk[1] + VK.DK_HALF, 0))
        p.rect(a[0], a[1], b[0], b[1], 'ВК_К2')
        p.line(a[0], a[1], b[0], b[1], 'ВК_К2')
        L.block((a[0] - 0.3, a[1] - 0.3, b[0] + 0.3, b[1] + 0.3))
        own[n] = (c[0] - 1.3, c[1] - 1.3, c[0] + 1.3, c[1] + 1.3)
        L.block(own[n])
        L.add_segs(list(zip(pts, pts[1:])))
    for n, xy, rf, path, d, room in VK.K2_STACKS:
        c = V.P((xy[0], xy[1], 0))
        t = f'Ст.К2-{n} SML DN100 → ДК-{n}'           # выпуск −0,130, i = 0,02 у всех — в прим. 5 и на схеме
        sub = f'ревизия +1,000, люк из {room}'
        cc = {'3': [(18, 14), (24, 16), (30, 14), (18, 20)], '5': [(16, -14), (22, -18), (28, -14)],
              '7': [(-14, -14), (-20, -16), (-26, -14)], '1': [(-12, -16), (-16, -20), (-20, -14)],
              '8': [(-30, 8), (-32, 8), (-30, 9), (-34, 8)]}.get(n)   # над террасой 1.12, рядом со стояком
        with own_free(L, own[n]):
            if L.shelf(c, t, 1.8, sub=sub, cands=cc, strict=True) is None and L.soft([(c, sub)], t, 1.8) is None:
                print('  !! нет места:', t)
    sh.title(cx, box[3] + 13.0, 'План 1 этажа. Стояки К2, выпуски в дождеприёмники ДК. М 1:100', h=3.2)
    return V, box


def scheme(p, sh, x0, y0):
    """Схема стояков К2 (вертикальный масштаб 1:50, по горизонтали — условно)."""
    KZ = 50
    z0 = -0.60

    def Y(z):
        return y0 + (z - z0) * 1000 / KZ
    step = 24.0
    xs = [x0 + 52 + i * step for i in range(len(VK.K2_STACKS))]
    for z, nm in ((0.0, '±0,000 — пол 1 этажа'), (VK.FL2, f'{lev(VK.FL2)} — пол 2 этажа'),
                  (VK.Z_K2_TOP['main'], f'{lev(VK.Z_K2_TOP["main"])} — кровля над 2 этажом')):
        p.line(x0 + 2, Y(z), xs[-1] + 18, Y(z), 'ТМ_оборуд_тонк', ltype='ОВ_ШТРИХ')
        p.t(x0 + 2, Y(z) + 1.2, nm, 1.8, 'bl', 'ТМ_текст')
    for x, (n, xy, rf, path, d, room) in zip(xs, VK.K2_STACKS):
        st = PIPES[f'Ст.К2-{n}']
        zt, zb = st.pts[0][2], st.pts[-1][2]
        p.line(x, Y(zt), x, Y(zb + 0.12), 'ВК_К2', lw=50)
        # переход двумя отводами 45° и выпуск в ДК
        p.pl([(x, Y(zb + 0.12)), (x + 2.4, Y(zb)), (x + 10.0, Y(zb - 0.02))], 'ВК_К2', lw=50)
        q = [(x + 10.0, Y(-0.32)), (x + 16.0, Y(-0.32)), (x + 16.0, Y(-0.02)), (x + 10.0, Y(-0.02))]
        p.poly(q, 'ВК_К2')
        p.t(x + 13.0, Y(-0.32) - 2.5, f'ДК-{n}', 1.7, 'center', 'ТМ_текст')
        p.pl([(x + 16.0, Y(-0.17)), (x + 19.0, Y(-0.17))], 'ВК_К2', ltype='ОВ_ШТРИХ')
        # воронка
        fq = [(x - 3.0, Y(zt) + 3.0), (x + 3.0, Y(zt) + 3.0), (x + 0.8, Y(zt)), (x - 0.8, Y(zt))]
        p.poly(fq, 'ВК_К2')
        p.t(x, Y(zt) + 5.0, f'Вр-{n}', 1.8, 'center', 'ТМ_текст')
        # ревизия
        rq = [(x - 1.4, Y(1.0) - 1.4), (x + 1.4, Y(1.0) - 1.4), (x + 1.4, Y(1.0) + 1.4), (x - 1.4, Y(1.0) + 1.4)]
        p.m.add_wipeout(rq, dxfattribs={'layer': 'ТМ_арматура'})
        p.poly(rq, 'ТМ_арматура')
        p.t(x, Y(1.0), 'Р', 1.4, 'center', 'ТМ_арматура')
        # марка стояка — вертикально вдоль трубы
        zm = (zt + 1.0) / 2 + 0.6
        p.t(x - 1.6, Y(zm), f'Ст.К2-{n}', 1.8, 'center', 'ТМ_текст', rot=90)
    p.t(x0 + 2, Y(1.0) + 2.0, 'Р — ревизия +1,000', 1.7, 'bl', 'ТМ_текст')
    p.t(x0 + 2, Y(-0.32) - 9.0, f'Выпуски SML DN100: ось {lev(VK.Z_K2_OUT)} у стояка, i = 0,02, сквозь стену в боковой '
        f'вход ДК 300×300 (НВК: верх −0,020,', 1.7, 'bl', 'ТМ_текст')
    p.t(x0 + 2, Y(-0.32) - 12.5, 'выход −0,170 → ПП SN8 Ø110 в кольцо К2). Длины выпусков — в таблице; по горизонтали '
        'схема условная.', 1.7, 'bl', 'ТМ_текст')
    sh.title(x0 + 120, Y(VK.Z_K2_TOP['main']) + 12.0, 'Схема водостоков К2 (стояки SML DN100). М 1:50 по высоте', h=3.2)


NOTES = [
    'Подложки — АР03, АР13.1, АР14 (выгрузка 30.10.2026). Отметки — от чистого пола 1 этажа ±0,000 (абс. 186,80). '
    'Планы и схема — проекции 3D-модели ВК.',
    'Воронки Вр-1…Вр-5 — на кровле над 2 этажом (АР14, +8,020), Вр-6…Вр-8 — на кровлях над 1 этажом (АР13.1); '
    'марка воронок, обогрев и примыкание к кровле — по АР (в модели АР — HL64.1H / HL62.1). Присоединение воронки к '
    'стояку — переходником на SML DN100.',
    'Водосточные стояки Ст.К2-1…8 — внутри стен, в штрабах 150×200 с внутренней стороны наружных стен (по АР), из '
    'чугунных безраструбных труб и фасонных частей SML DN100 (Smart SML или аналог) на соединительных хомутах '
    'с когтевой фиксацией (при засоре стояк работает под напором); у основания — опора стояка, крепление к стене '
    '— хомутами не реже чем через 2 м и у каждого отвода; в стенах дома — в изоляции 9 мм от конденсата (кроме '
    'Ст.К2-8 в стене террасы 1.12); проходы сквозь плиты и стены — в гильзах Ø160 (ТЗ-1).',
    'Внизу стояка — переход двумя отводами 45° в выпуск SML DN100 сквозь стену в гильзе (ТЗ-1) в боковой вход '
    'дождеприёмника ДК 300×300 у наружной грани стены (раздел НВК); ось выпуска у стояка −0,130, к ДК — с уклоном '
    '0,02; верх ДК −0,020, выход из ДК — ось −0,170 (разрез Заказчицы 30.10.2026). В стенах до ДК — чугун, после ДК '
    '— пластиковая труба в грунте (НВК).',
    'Ст.К2-3 и Ст.К2-5 в 1 этаже стоят во внутренних стенах (у хозблока 1.13; между тамбуром 1.3 и гаражом): их '
    'выпуски идут в нижней части той же стены (штроба в кладке у пола, ТЗ-1) до наружной грани — на север к ДК-3 и '
    'на юг, затем на восток к ДК-5. Выпуск Ст.К2-7 обходит ступень крыльца: в стене на запад, затем на юг к ДК-7.',
    'Ревизии — на каждом стояке на +1,000 за нажимными люками 300×300 в стенах (помещения — в подписях на плане '
    '1 этажа; ТЗ-1). Испытание — наполнением водой до уровня наивысшей воронки не менее 10 мин, до закрытия штраб '
    '(СП 73.13330.2016); выпуски на время испытания заглушаются.',
    'Расчёт — приложение П5: наибольший расход — '
    f'Ст.К2-{max(CALC["rows"], key=lambda r: r["q"])["id"]}, {f2(max(r["q"] for r in CALC["rows"]))} л/с при '
    f'предельном для стояка DN100 {f2(CALC["rows"][0]["q_stack"], 0)} л/с (СП 30.13330.2020, разд. 24). Суммарная площадь '
    f'кровли {f2(CALC["F"], 1)} м² — как в П2 НВК.',
    'Баня — водостоки по АР бани (в комплекте ВК не показаны: расположение воронок бани не передано).',
]


def table(sh, x, y):
    rows = [['Стояк', 'Воронка', 'F, м²', 'Q, л/с', 'Стояк SML, м', 'Ревизия', 'Выпуск, м', 'ДК (НВК)']]
    for n, xy, rf, path, d, room in VK.K2_STACKS:
        r = R[n]
        rows.append([f'Ст.К2-{n}', f'Вр-{n}, ' + ('над 2 эт.' if rf == 'main' else 'над 1 эт.'), f2(r['F'], 1),
                     f2(r['q']), f2(r['L_st'], 1), f'+1,000 ({room})', f2(r['L_out'], 2), f'ДК-{n}'])
    rows.append(['Итого', '', f2(CALC['F'], 1), f2(CALC['Q']), f2(sum(r['L_st'] for r in CALC['rows']), 1), '8 шт.',
                 f2(sum(r['L_out'] for r in CALC['rows']), 1), '8 шт.'])
    sh.s.text('Водостоки К2 (по модели и П5)', x + 160, y + 4, h=3.0, align='center')
    return sh.table(x, y, [20, 36, 18, 18, 26, 34, 22, 22], rows, row_h=6.0, head_h=8.0, h=1.9)


def legend(p, x, y):
    p.t(x, y + 6, 'Условные обозначения', 2.2, 'bl', 'ТМ_текст')
    funnel(p, (x + 7, y))
    p.t(x + 17, y, 'Вр — воронка кровельная (по АР)', 1.9, 'left', 'ТМ_текст')
    yy = y - 6
    stack_dot(p, (x + 7, yy))
    p.t(x + 17, yy, 'Ст.К2 — стояк водостока SML DN100 в стене', 1.9, 'left', 'ТМ_текст')
    yy -= 6
    p.pl([(x, yy), (x + 14, yy)], 'ВК_К2', lw=50)
    p.t(x + 17, yy, 'выпуск SML DN100 сквозь стену в ДК', 1.9, 'left', 'ТМ_текст')
    yy -= 6
    p.rect(x + 5.5, yy - 1.5, x + 8.5, yy + 1.5, 'ВК_К2')
    p.line(x + 5.5, yy - 1.5, x + 8.5, yy + 1.5, 'ВК_К2')
    p.t(x + 17, yy, 'ДК — дождеприёмник 300×300 (НВК)', 1.9, 'left', 'ТМ_текст')


def main():
    doc = new_doc()
    setup(doc)
    sh = RDSheet(doc, 'Лист', VK_LIST[NO], NO, VK_TOTAL, fmt='А1', code=CODE_VK, bld=BLD_VK)
    roof_plan(doc, sh, 'k2roof2', 160, 452, 'main', 'План кровли над 2 этажом. Воронки Вр-1…Вр-5. М 1:100')
    roof_plan(doc, sh, 'k2roof1', 440, 452, 'low', 'План кровли над 1 этажом. Воронки Вр-6…Вр-8. М 1:100')
    floor_plan(doc, sh, 160, 190)
    scheme(sh.p, sh, 585, 345)
    yb = table(sh, 312, 318)
    legend(sh.p, 312, (yb if isinstance(yb, (int, float)) else 230) - 14)
    sh.notes(655, 330, 176, NOTES, h=1.9, spacing=1.0)
    finish_layers(doc)
    return save_and_pdf(doc, os.path.join(OUT, 'vk_k2_15.dxf'))


if __name__ == '__main__':
    print(main())
