"""И05.09.26-ТМ, лист 2. Котельная: план на отм. 0,000 (оборудование и трубы до +2,000) и план трубопроводов
выше +2,000. М 1:25. Всё — проекция 3D-модели tm_model.

python3 sheets/tm_plans.py -> out/tm_plans.dxf + PDF
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from rdbase import new_doc, RDSheet, save_and_pdf  # noqa: E402
import tm_model as TM  # noqa: E402
from tm_draw import (CODE_TM, BLD_TM, TM_LIST, TM_TOTAL, setup_layers, PP, View, Labels, draw_pipes, draw_eq,  # noqa
                     eq_outline, sym_fit, walls_plan, dim_h, dim_v, mm, axis_bubble, cut_mark, lev, f1)

OUT = os.path.join(ROOT, 'out')
RD = json.load(open(os.path.join(ROOT, '..', 'rd', 'rd_calc.json')))
SHEET_NO = 2
K = 25
Z_SPLIT = 2.00
CUTS = {  # разрез: (вид, плоскость)
    '1': ('N', 12.40), '2': ('W', 17.05), '3': ('E', 18.15), '4': ('S', 10.75)}

# подписи труб: id (или пара) -> текст; пары подписываются одной полкой
PAIRS = [
    (('Н3-П', 'Н3-О'), 'Т1, Т2 PE-Xa 32×4,4 → КШ-2 (Н3)'),
    (('Н4-П', 'Н4-О'), 'Т11, Т21 PE-Xa 25×3,5 → КШ-1, КШ-3 (Н4)'),
    (('КШ-3-П', 'КШ-3-О'), 'Т11, Т21 PE-Xa 25×3,5 → КШ-3'),
    (('Н2-П', 'Н2-О'), 'Т1, Т2 PE-Xa 25×3,5 → КШ-4 (Н2)'),
    (('Н5-П', 'Н5-О'), 'Т1, Т2 PE-Xa 20×2,8 → П1 (Н5)'),
    (('Н6-П', 'Н6-О'), 'Т1, Т2 Ecoflex → баня (Н6)'),
    (('Н7-П', 'Н7-О'), 'Т1, Т2 Ду25 → Б1 (Н7)'),
    (('ГС-РК-П', 'ГС-РК-О'), 'Т1, Т2 Ду32 ГС → РК'),
    (('XS',), 'Т1 Ду32 — подача котлов'),
    (('XR',), 'Т2 Ду32 — обратка котлов'),
    (('ГС-О',), 'Т2 Ду32'),
    (('К2-П', 'К2-О'), 'Т1, Т2 Ду25'),
    (('К1-П', 'К1-О'), 'Т1, Т2 Ду25'),
    (('ПК-КТ',), 'Т1 Ду32 подмес к КТ'),
    (('РБ',), 'Т2 Ду20 к РБ'),
    (('УП',), 'В1 Ду15 — подпитка (УП)'),
    (('Т3',), 'Т3 Ду25 → ВК'),
    (('Т4',), 'Т4 Ду20 ← ВК'),
    (('В1-Б1',), 'В1 Ду25 ← ВК'),
    (('РБ-ГВС',), 'В1 Ду20 к РБ-ГВС'),
    (('Г',), 'Г Ду25 (условно, ГСВ)'),
    (('Г-К1',), 'Г Ду20 (ГСВ)'),
    (('Д-каскад',), 'Дымоход каскадный Ø125, i=3° к котлам'),
    (('Д-ПК',), 'Дымоход ПК Ø180'),
    (('К-сб',), 'К ПП Ø32 — конденсат К1, К2'),
]


def pipe_by_id():
    return {p.id: p for p in TM.PIPES}


def plan_view(org, zr):
    return View('plan', K, org, (TM.X0, TM.Y0), zr=zr)


def visible_segments(V, pp):
    out = []
    for a, b in zip(pp.pts, pp.pts[1:]):
        c = V.clip(a, b)
        if c is None:
            continue
        A, B = V.P(c[0]), V.P(c[1])
        L = math.hypot(B[0] - A[0], B[1] - A[1])
        if L > 6.0:
            out.append((L, c, A, B))
    return out


def label_pipes(L, V, skip=()):
    P = pipe_by_id()
    for ids, txt in PAIRS:
        if ids[0] in skip or ids[0] not in P:
            continue
        segs = visible_segments(V, P[ids[0]])
        if not segs:
            continue
        segs.sort(key=lambda s: -s[0])
        Lm, c, A, B = segs[0]
        sub = None
        if abs(c[0][2] - c[1][2]) < 1e-6:
            sub = 'ось ' + lev(c[0][2])
            if ids[0] == 'Д-каскад':
                sub = None
        # точка подписи — 35 % длины отрезка (середины часто заняты чужими подписями)
        for t in (0.35, 0.6, 0.2, 0.8):
            at = (A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t)
            if L.shelf(at, txt, 1.8, sub=sub):
                break


def eq_marks(p, L, V, items, inside_min=(9.0, 5.0)):
    """Марки оборудования: в контуре, если помещается, иначе — на полке."""
    for e, txt in items:
        o = eq_outline(V, e)
        if o[0] == 'rect':
            _, x0, y0, x1, y1 = o
            cx, cy, w, h = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
        else:
            _, cx, cy, r = o
            w = h = 1.4 * r
        tw = p.tw(txt, 2.2) + 1.0
        if w >= max(inside_min[0], tw) and h >= inside_min[1]:
            p.t(cx, cy, txt, 2.2 if tw < w - 1 else 1.8, 'center', 'ТМ_марки')
            L.block((cx - tw / 2, cy - 1.6, cx + tw / 2, cy + 1.6))
        else:
            L.shelf((cx, cy), txt, 2.2)


def block_room(L, V, eqs=()):
    """Подписи не кладём на стены и корпуса оборудования."""
    for x0, y0, x1, y1 in ((TM.X0 - 0.20, TM.Y0 - 0.45, TM.X1 + 0.40, TM.Y0),
                           (TM.X0 - 0.20, TM.Y1, TM.X1 + 0.40, TM.Y1 + 0.45),
                           (TM.X0 - 0.20, TM.Y0, TM.X0, TM.Y1), (TM.X1, TM.Y0, TM.X1 + 0.40, TM.Y1)):
        a, b = V.P((x0, y0, 0)), V.P((x1, y1, 0))
        L.block((a[0], a[1], b[0], b[1]))
    for e in eqs:
        o = eq_outline(V, e)
        if o[0] == 'rect':
            L.block(o[1:])
        else:
            L.block((o[1] - o[3], o[2] - o[3], o[1] + o[3], o[2] + o[3]))


def draw_ctx(p, V, ctx_runs, ctx_boxes, zr):
    """Сети ОВ в топочной — тонко, для увязки (воздуховоды контуром)."""
    for c in ctx_runs:
        a, b = c['seg']
        if max(a[2], b[2]) < zr[0] or min(a[2], b[2]) > zr[1]:
            continue
        A, B = V.P(a), V.P(b)
        Lp = math.hypot(B[0] - A[0], B[1] - A[1])
        w = c['w'] * V.s / 2
        if Lp < 0.1:
            if c['rect']:
                p.rect(A[0] - w, A[1] - c['h'] * V.s / 2, A[0] + w, A[1] + c['h'] * V.s / 2, 'ТМ_ОВ')
            else:
                p.circle(A[0], A[1], 0, 'ТМ_ОВ', r_paper=w)
            continue
        dx, dy = (B[0] - A[0]) / Lp, (B[1] - A[1]) / Lp
        n = (-dy, dx)
        p.pl([(A[0] + n[0] * w, A[1] + n[1] * w), (B[0] + n[0] * w, B[1] + n[1] * w)], 'ТМ_ОВ')
        p.pl([(A[0] - n[0] * w, A[1] - n[1] * w), (B[0] - n[0] * w, B[1] - n[1] * w)], 'ТМ_ОВ')


def room_frame(p, V, walls):
    walls_plan(p, V, walls)


def axes_plan(p, V, right_x, top_y):
    """Оси 5, Г, Д и привязка внутренних граней стен."""
    x5 = V.P((20.0, 0, 0))[0]
    p.line(x5, V.P((0, TM.Y0 - 0.5, 0))[1], x5, top_y - 4.0, 'ТМ_оси', ltype='ОВ_ШП')
    axis_bubble(p, x5, top_y, '5')
    for nm, y in (('Г', 8.9), ('Д', 13.8)):
        yy = V.P((0, y, 0))[1]
        p.line(V.P((TM.X1 - 0.3, 0, 0))[0], yy, right_x - 4.0, yy, 'ТМ_оси', ltype='ОВ_ШП')
        axis_bubble(p, right_x, yy, nm)


def build():
    TM.build()
    ctx_runs, ctx_boxes = TM.ov_context()
    walls = TM.room_walls()
    doc = new_doc()
    setup_layers(doc)
    sh = RDSheet(doc, 'Лист', TM_LIST[SHEET_NO], SHEET_NO, TM_TOTAL, fmt='А2', code=CODE_TM, bld=BLD_TM)
    p = PP(doc, sh.lay)
    E = {e.id: e for e in TM.EQUIP}

    # ------------------------------------------------------------------ план на отм. 0,000 (до +2,000)
    org1 = (78.0, 160.0)
    V1 = plan_view(org1, (-0.30, Z_SPLIT))
    L1 = Labels(p, (24.0, 72.0, 300.0, 384.0))
    room_frame(p, V1, walls)
    # нижнее оборудование
    low = [e for e in TM.EQUIP if e.bbox()[2] < Z_SPLIT and not e.ctx and e.kind != 'cylx'
           and e.id not in ('ПК-горелка', 'БП-шнек', 'РБ-ГВС')]
    for e in sorted(low, key=lambda e: e.bbox()[5]):           # сначала низкие — высокие закрывают
        draw_eq(p, V1, e)
    for e in (E['П1'], E['П1-узел']):                          # П1 над головой — штрихом
        draw_eq(p, V1, e, layer='ТМ_ОВ', mask=False, ltype='ОВ_ШТРИХ')
    draw_pipes(p, V1, TM.PIPES)
    for f in TM.FITS:
        if Z_SPLIT >= f.pos[2] >= -0.3:
            sym_fit(p, V1, f)
    eq_marks(p, L1, V1, [(E['ПК'], 'ПК'), (E['БП'], 'БП'), (E['ШУ'], 'ШУ')])
    for m in ('К1', 'К2'):                                     # марка котла — у передней грани, вне подводок
        o = eq_outline(V1, E[m])
        p.t(o[3] - 2.6, (o[2] + o[4]) / 2 + 3.2, m, 2.2, 'center', 'ТМ_марки')
    o = eq_outline(V1, E['Б1'])
    p.t(o[1] - 3.0, o[2] + 3.0, 'Б1', 2.5, 'center', 'ТМ_марки')
    o = eq_outline(V1, E['КШ-3'])
    p.t(o[1] + 7.0, (o[2] + o[4]) / 2, 'КШ-3 (ОВ)', 1.8, 'center', 'ТМ_марки')
    for n, _ in TM.GROUPS:
        e = E[n]
        o = eq_outline(V1, e)
        p.t((o[1] + o[3]) / 2, (o[2] + o[4]) / 2 - 0.2, n, 1.8, 'center', 'ТМ_марки')
    block_room(L1, V1, [E[k] for k in ('К1', 'К2', 'ПК', 'БП', 'Б1', 'КШ-3', 'ШУ', 'Нейтр')])
    L1.block(V1.P((TM.gx(0) - 0.13, TM.GY - 0.12, 0)) + V1.P((TM.gx(5) + 0.13, TM.GY + 0.12, 0)))
    L1.shelf(V1.P((TM.HS[0], TM.HS[1], 0)), 'ГС', 2.2, force=(-10, -16))
    L1.shelf(V1.P((18.10, 13.18, 0)), 'УП', 2.2, force=(-8, -27))
    L1.shelf(V1.P((TM.RB[0] - 0.10, TM.RB[1] - 0.20, 0)), 'РБ', 2.2, force=(6, -20))
    L1.shelf(V1.P((TM.gx(3), TM.GY - 0.06, 0)), 'РК', 2.2, force=(6, -13))
    L1.shelf(V1.P((16.55, 11.42, 0)), 'нейтрализатор (ВК)', 1.8, force=(10, 10))
    L1.shelf(V1.P((17.00, 11.05, 0)), 'трап Ду50 (ВК)', 1.8, force=(10, -8))
    L1.shelf(V1.P((TM.ECO[0], TM.ECO[1] - 0.06, 0)), 'ввод Ecoflex (баня)', 1.8, force=(-4, -40))
    L1.shelf(V1.P((17.65, 9.75, 0)), 'П1 (ОВ, над головой, низ +2,450)', 1.8, force=(4, 9))
    label_pipes(L1, V1, skip=('Н3-П', 'Н4-П', 'Н2-П', 'Н5-П', 'КШ-3-П', 'Д-каскад', 'РБ', 'ГС-РК-П'))
    p.t(*V1.P((15.22, 12.75, 0)), 'Ш-2', 2.5, 'center', 'ТМ_марки')
    p.t(*V1.P((17.80, 10.75, 0)), '1.6 Топочная', 3.0, 'center', 'ТМ_марки')
    p.t(*V1.P((15.25, 10.00, 0)), '1.7', 2.5, 'center', 'ТМ_марки')
    # разрезы
    for nm, (kind, c) in CUTS.items():
        if kind in ('N', 'S'):
            a, b = V1.P((TM.X0 - 0.55, c, 0)), V1.P((TM.X1 + 0.55, c, 0))
            look = (0, 1) if kind == 'N' else (0, -1)
        else:
            a, b = V1.P((c, TM.Y0 - 0.62, 0)), V1.P((c, TM.Y1 + 0.50, 0))
            look = (-1, 0) if kind == 'W' else (1, 0)
        cut_mark(p, a, b, nm, look)
    # размеры: помещение и привязки оборудования
    xa, xb = V1.P((TM.X0, 0, 0))[0], V1.P((TM.X1, 0, 0))[0]
    ya, yb = V1.P((0, TM.Y0, 0))[1], V1.P((0, TM.Y1, 0))[1]
    dim_h(p, xa, xb, ya - 42.0, ya, ya, mm(TM.X1 - TM.X0))
    xb1 = V1.P((TM.B1[0], 0, 0))[0]
    dim_h(p, xa, xb1, ya - 34.0, None, None, mm(TM.B1[0] - TM.X0), h=1.8)
    dim_h(p, xb1, xb, ya - 34.0, None, None, mm(TM.X1 - TM.B1[0]), h=1.8)
    p.line(xb1, V1.P((0, TM.B1[1], 0))[1], xb1, ya - 35.5, 'ТМ_размеры', ltype='ОВ_ШП')
    yk = [TM.Y0, TM.KC['К2'] - 0.20, TM.KC['К2'] + 0.20, TM.KC['К1'] - 0.20, TM.KC['К1'] + 0.20, TM.PK[1],
          TM.Y1]
    xw = xa - 36.0
    for y0_, y1_ in zip(yk, yk[1:]):
        dim_v(p, V1.P((0, y0_, 0))[1], V1.P((0, y1_, 0))[1], xw, None, None, mm(y1_ - y0_), h=1.8)
    dim_v(p, ya, yb, xw - 8.0, None, None, mm(TM.Y1 - TM.Y0))
    for y_ in yk:
        p.line(xw - 9.0, V1.P((0, y_, 0))[1], xa - 0.8 if y_ in (TM.Y0, TM.Y1) else V1.P((TM.X0, 0, 0))[0],
               V1.P((0, y_, 0))[1], 'ТМ_размеры') if False else None
    # привязка РК, Б1 по x к восточной стене (сверху)
    yt = yb + 30.0
    xs_ = [TM.X0, TM.PK[0], TM.PK[3], TM.BP[3], TM.gx(0), TM.gx(5), TM.X1]
    for x0_, x1_ in zip(xs_, xs_[1:]):
        dim_h(p, V1.P((x0_, 0, 0))[0], V1.P((x1_, 0, 0))[0], yt, None, None, mm(x1_ - x0_), h=1.8)
    axes_plan(p, V1, xb + 34.0, yt + 16.0)
    sh.title(sum(V1.P((17.8, 0, 0))[:1]), 403.0, 'План котельной на отм. 0,000 (оборудование и трубопроводы '
             'до +2,000). М 1:25', h=3.2)

    # ------------------------------------------------------------------ план трубопроводов выше +2,000
    org2 = (360.0, 160.0)
    V2 = plan_view(org2, (Z_SPLIT, 3.70))
    L2 = Labels(p, (306.0, 72.0, 566.0, 384.0))
    room_frame(p, V2, walls)
    for e in low:                                                # нижнее — тонко, для ориентира
        if e.bbox()[5] <= Z_SPLIT:
            o = eq_outline(V2, e)
            if o[0] == 'rect':
                p.rect(o[1], o[2], o[3], o[4], 'ТМ_оборуд_тонк')
            else:
                p.circle(o[1], o[2], 0, 'ТМ_оборуд_тонк', r_paper=o[3])
    draw_ctx(p, V2, ctx_runs, ctx_boxes, (Z_SPLIT, 3.7))
    for e in (E['П1'], E['П1-узел']):
        draw_eq(p, V2, e, layer='ТМ_ОВ', mask=False)
    for e in (E['РБ-ГВС'], E['ШУ']):
        draw_eq(p, V2, e)
    draw_pipes(p, V2, TM.PIPES)
    for f in TM.FITS:
        if f.pos[2] > Z_SPLIT:
            sym_fit(p, V2, f)
    block_room(L2, V2, [E['РБ-ГВС']])
    L2.stack(V2.P((16.95, 10.45, 0)), ['Н3: Т1, Т2 PE-Xa 32×4,4 → КШ-2', 'Н4: Т11, Т21 PE-Xa 25×3,5 → КШ-1, КШ-3',
                                      'Н2: Т1, Т2 PE-Xa 25×3,5 → КШ-4', 'оси +3,200; в тамбур 1.7 над дверью (лист 3 ОВ)'],
             4.0, 30.0)
    L2.shelf(V2.P((17.65, 9.75, 0)), 'П1 (ОВ, лист 9)', 2.0, force=(4, 10))
    L2.shelf(V2.P((18.57, 10.18, 0)), 'смесительный узел П1', 1.8, force=(14, -10))
    L2.shelf(V2.P((TM.RBG[0], TM.RBG[1], 0)), 'РБ-ГВС', 2.2)
    label_pipes(L2, V2, skip=('К2-П', 'К1-П', 'ГС-РК-П', 'Н6-П', 'В1-Б1', 'Т4', 'УП', 'РБ', 'ГС-О', 'Н3-П', 'Н4-П',
                              'Н2-П'))
    xa2, xb2 = V2.P((TM.X0, 0, 0))[0], V2.P((TM.X1, 0, 0))[0]
    ya2, yb2 = V2.P((0, TM.Y0, 0))[1], V2.P((0, TM.Y1, 0))[1]
    # привязка поворотов магистралей групп к южной стене (по западной стене)
    ys = [TM.Y0, 10.30, 10.45, 10.60, TM.Y1]
    xw2 = xa2 - 36.0
    for y0_, y1_ in zip(ys, ys[1:]):
        dim_v(p, V2.P((0, y0_, 0))[1], V2.P((0, y1_, 0))[1], xw2, None, None, mm(y1_ - y0_), h=1.8)
    dim_h(p, xa2, xb2, ya2 - 42.0, ya2, ya2, mm(TM.X1 - TM.X0))
    yt2 = yb2 + 30.0
    xs2 = [TM.X0, TM.gx(0), TM.gx(1), TM.gx(2), TM.gx(3), TM.gx(4), TM.gx(5), TM.X1]
    for x0_, x1_ in zip(xs2, xs2[1:]):
        dim_h(p, V2.P((x0_, 0, 0))[0], V2.P((x1_, 0, 0))[0], yt2, None, None, mm(x1_ - x0_), h=1.6)
    axes_plan(p, V2, xb2 + 34.0, yt2 + 16.0)
    sh.title(V2.P((17.8, 0, 0))[0], 403.0, 'План трубопроводов котельной выше +2,000. М 1:25', h=3.2)
    explication(sh)
    sh.notes(212, 110, 170, NOTES, h=2.0, spacing=1.0)
    return doc, sh, p


def eq_rows():
    """Экспликация оборудования котельной (марки — как на листах ТМ и в ТМ.СО)."""
    from ov_boiler_scheme import groups_calc
    GC = groups_calc()
    ex, exd = RD['expansion_heat'], RD['expansion_dhw']['Б1 300 л']
    return [
        ('К1, К2', 'Котёл газовый конденсационный настенный ≈24–25 кВт (Viessmann Vitodens 200-W), каскад', '2'),
        ('ПК', 'Котёл пеллетный водогрейный ≈50 кВт с горелкой и автоподачей (резерв)', '1'),
        ('БП', 'Бункер пеллет со шнеком подачи (комплект ПК)', '1'),
        ('Н1, КТ', 'Насос котлового контура ПК; клапан термостатический 55 °С Ду32 (защита обратки)', '1+1'),
        ('ГС', f'Гидравлический разделитель Ду32, G до {f1(GC["hs_m3h"], 1)} м³/ч', '1'),
        ('ШО', 'Шламоотделитель магнитный Ду32 на обратке перед котлами', '1'),
        ('РК', 'Коллектор распределительный двухкамерный Ду32 на 6 групп', '1'),
        ('Н2, Н3, Н6, Н7', 'Группа насосная прямая (насос с электронным управлением)', '4'),
        ('Н4', 'Группа насосная смесительная (ТП, 48,5 °С)', '1'),
        ('Н5', 'Отвод к нагревателю П1 без насоса (насос — в узле Turkov)', '1'),
        ('Б1', 'Бойлер косвенного нагрева 300 л', '1'),
        ('РБ', f'Бак расширительный мембранный {ex["tank"]} л, p0 = {f1(ex["p0"], 1)} бар', '1'),
        ('РБ-ГВС', f'Бак расширительный для ГВС {exd["tank"]} л', '1'),
        ('ГБ, ГБ-ГВС', 'Группы безопасности котла (3 бар) и бойлера (6 бар)', '1+1'),
        ('УП', 'Узел подпитки Ду15 с редуктором 1,5 бар', '1'),
        ('ШУ', 'Шкаф управления котельной', '1'),
    ]


def explication(sh):
    rows = [['Марка', 'Наименование', 'Кол.']] + [list(r) for r in eq_rows()]
    widths = [24, 152, 10]
    sh.table(24, 108, widths, rows, h=1.9, heights=[6.0] + [5.0] * (len(rows) - 1),
             aligns=['center', 'left', 'center'])
    sh.s.text('Экспликация оборудования котельной', 24 + sum(widths) / 2, 111.5, h=2.8, align='center')


NOTES = [
    'Планы получены проекцией 3D-модели котельной (И05.09.26-ТМ, 3D): трубы, арматура и корпуса — те же, что в '
    'модели и спецификации ТМ.СО. Отметки — оси труб от чистого пола ±0,000; размеры — в мм.',
    'План на отм. 0,000 — оборудование и трубы до +2,000; выше — план трубопроводов. П1, воздуховоды и шумоглушители '
    '(ОВ, листы 9–11) показаны тонкой линией для увязки.',
    'Котловой контур: подача Т1 на +2,900 и обратка Т2 на +2,780 вдоль северной стены, под котлами — +0,700 и '
    '+0,550; ГС → РК — на +1,320.',
    'Магистрали групп Н3, Н4, Н2 (PE-Xa) поднимаются от РК на +3,200 и уходят в тамбур 1.7 над дверью (лист 3 ОВ); '
    'Н5 к П1 — на +3,050 под ними; отвод Н4 → КШ-3 — опуск на +2,600 под шумоглушителями П1.',
    'Газопровод показан условно — по проекту ГСВ. Конденсат котлов — шлангами в сборный ПП Ø32, через нейтрализатор '
    'в трап (ВК).',
    'Принципиальная схема — лист 8 ОВ; разрезы — листы 3, 4; аксонометрия — лист 5.',
]


if __name__ == '__main__':
    doc, sh, p = build()
    print(save_and_pdf(doc, os.path.join(OUT, 'tm_plans.dxf')))
