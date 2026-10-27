"""И05.09.26-ТМ, листы 3 и 4. Котельная: разрезы 1-1, 2-2 (лист 3) и 3-3, 4-4 (лист 4), М 1:25.

Разрез — проекция 3D-модели tm_model на вертикальную плоскость: всё, что за плоскостью разреза, рисуется
от дальнего к ближнему (ближнее закрывает дальнее маскировкой), стены и перекрытия — в разрезе со штриховкой.

python3 sheets/tm_sections.py -> out/tm_sec12.dxf, out/tm_sec34.dxf + PDF
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from rdbase import new_doc, RDSheet, save_and_pdf  # noqa: E402
import tm_model as TM  # noqa: E402
from tm_draw import (CODE_TM, BLD_TM, TM_LIST, TM_TOTAL, setup_layers, PP, View, TMLabels as Labels, draw_eq,  # noqa: E402
                     eq_outline, sym_fit, PIPE_STYLE, unit, level_mark, lev, f1, mm, dim_v, pair_sub)
from tm_plans import PAIRS, CUTS  # noqa: E402

OUT = os.path.join(ROOT, 'out')
K = 25
SLAB_T = 0.40          # перекрытие с полом 2 этажа: +3,650…+4,050 (чистый пол 2 этажа — FL2 модели ОВ)
FLOOR_T = 0.30         # пол по грунту — условно


def cut_view(kind, cut, org):
    """Вид разреза: u0 — левый край помещения на виде, v0 — пол (±0,000)."""
    u0 = {'N': TM.X0, 'S': -TM.X1, 'W': TM.Y0, 'E': -TM.Y1}[kind]
    far = {'N': TM.Y1 + 0.45, 'S': TM.Y0 - 0.45, 'W': TM.X0 - 0.20, 'E': TM.X1 + 0.40}[kind]   # за дальней стеной
    return View(kind, K, org, (u0, 0.0), cut=cut, far=far)


def wall_spans(walls, kind, cut):
    """Пересечение стен (плановые многоугольники) с плоскостью разреза: интервалы по u."""
    from shapely.geometry import LineString, Polygon
    if kind in ('N', 'S'):
        ln = LineString([(10.0, cut), (25.0, cut)])
    else:
        ln = LineString([(cut, 5.0), (cut, 18.0)])
    out = []
    for wl in walls:
        g = Polygon(wl['outer']).intersection(ln)
        for seg in getattr(g, 'geoms', [g]):
            if seg.is_empty or seg.geom_type != 'LineString':
                continue
            (xa, ya), (xb, yb) = seg.coords[0], seg.coords[-1]
            ua, ub = {'N': (xa, xb), 'S': (-xa, -xb), 'W': (ya, yb), 'E': (-ya, -yb)}[kind]
            out.append((min(ua, ub), max(ua, ub)))
    return out


def draw_shell(p, V, walls, u_lo, u_hi):
    """Стены в разрезе, перекрытие над топочной и пол — штриховкой; линия чистого пола."""
    s, ox, oy = V.s, V.org[0], V.org[1]

    def X(u):
        return ox + (u - V.u0) * s

    def Y(z):
        return oy + z * s
    for a, b in wall_spans(walls, V.kind, V.cut):
        a, b = max(a, u_lo), min(b, u_hi)
        if b - a < 0.01:
            continue
        pts = [(X(a), Y(-FLOOR_T)), (X(b), Y(-FLOOR_T)), (X(b), Y(TM.H_SLAB + SLAB_T)), (X(a), Y(TM.H_SLAB + SLAB_T))]
        p.poly(pts, 'ТМ_штрих', hatch=('ANSI31', 70.0, 0, 8), outline=False)
        p.pl(pts, 'ТМ_стены', closed=True)
    # проём в стене по линии разреза (окно, дверь — по АР): граница помещения тонкой линией
    spans = wall_spans(walls, V.kind, V.cut)
    lo_in = {'N': TM.X0, 'S': -TM.X1, 'W': TM.Y0, 'E': -TM.Y1}[V.kind]
    hi_in = {'N': TM.X1, 'S': -TM.X0, 'W': TM.Y1, 'E': -TM.Y0}[V.kind]
    for u_in, side in ((lo_in, -1), (hi_in, 1)):
        if not any(a - 0.02 <= u_in <= b + 0.02 for a, b in spans):
            for du in (0.0, side * 0.40):
                p.line(X(u_in + du), Y(0), X(u_in + du), Y(TM.H_SLAB), 'ТМ_стены', lw=18)
            p.t(X(u_in + side * 0.20), Y(1.2), 'проём (АР)', 1.8, 'center', 'ТМ_размеры', rot=90)
    # перекрытие и пол — по всей ширине вида
    for z0, z1, hp in ((TM.H_SLAB, TM.H_SLAB + SLAB_T, ('ANSI31', 70.0, 0, 8)), (-FLOOR_T, 0.0, ('ANSI37', 70.0, 0, 8))):
        pts = [(X(u_lo), Y(z0)), (X(u_hi), Y(z0)), (X(u_hi), Y(z1)), (X(u_lo), Y(z1))]
        p.poly(pts, 'ТМ_штрих', hatch=hp, outline=False)
        p.line(X(u_lo), Y(z0), X(u_hi), Y(z0), 'ТМ_стены')
        p.line(X(u_lo), Y(z1), X(u_hi), Y(z1), 'ТМ_стены')


def clip_box(V, b):
    """Корпус, обрезанный плоскостью разреза (часть за плоскостью)."""
    x0, y0, z0, x1, y1, z1 = b
    c, k = V.cut, V.kind
    if k == 'N':
        y0 = max(y0, c)
    elif k == 'S':
        y1 = min(y1, c)
    elif k == 'W':
        x1 = min(x1, c)
    elif k == 'E':
        x0 = max(x0, c)
    return (x0, y0, z0, x1, y1, z1)


def draw_section(p, V, walls, ctx_runs, ctx_boxes, u_lo, u_hi, L, eq_labels=(), skip_labels=(), extra=None):
    draw_shell(p, V, walls, u_lo, u_hi)
    items = []                      # (глубина, вид, объект)
    for e in TM.EQUIP:
        if e.id in ('Трап',):
            continue
        bb = e.bbox() if e.kind != 'cylx' else TM.cylx_bbox(e.g)
        if not V.in_view_box(bb):
            continue
        if e.kind == 'box':
            cb = clip_box(V, e.g)
            if (cb[3] - cb[0]) < 0.005 or (cb[4] - cb[1]) < 0.005:
                continue
            e2 = TM.Eq(e.id, e.mark, 'box', cb, e.name, e.rgb, e.pos, e.ifc, e.ctx)
        else:
            e2 = e
        cx, cy, cz = (bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, (bb[2] + bb[5]) / 2
        items.append((V.depth((cx, cy, cz)), 'eq', e2))
    for pp in TM.PIPES:
        for a, b in zip(pp.pts, pp.pts[1:]):
            c = V.clip(a, b)
            if c is None:
                continue
            mid = tuple((c[0][k] + c[1][k]) / 2 for k in range(3))
            items.append((V.depth(mid) - 1e-4, 'seg', (pp, c)))
    for f in TM.FITS:
        c = V.clip(f.pos, f.pos)
        if c is None:
            continue
        items.append((V.depth(f.pos) - 2e-4, 'fit', f))
    # сети ОВ — фоном, тонко
    for c in ctx_runs:
        cc = V.clip(*c['seg'])
        if cc is None:
            continue
        A, B = V.P(cc[0]), V.P(cc[1])
        Lp = math.hypot(B[0] - A[0], B[1] - A[1])
        w, h = c['w'] * V.s / 2, c['h'] * V.s / 2
        if Lp < 0.1:
            if c['rect']:
                ww = w if V.kind in ('N', 'S') and abs(cc[0][0] - cc[1][0]) < 1e-6 else h
                p.rect(A[0] - w, A[1] - h, A[0] + w, A[1] + h, 'ТМ_ОВ')
            else:
                p.circle(A[0], A[1], 0, 'ТМ_ОВ', r_paper=w)
            continue
        d = unit(A, B)
        n = (-d[1], d[0])
        hh = h if (abs(d[0]) > 0.5 and c['rect']) else w
        p.pl([(A[0] + n[0] * hh, A[1] + n[1] * hh), (B[0] + n[0] * hh, B[1] + n[1] * hh)], 'ТМ_ОВ')
        p.pl([(A[0] - n[0] * hh, A[1] - n[1] * hh), (B[0] - n[0] * hh, B[1] - n[1] * hh)], 'ТМ_ОВ')
    for b in ctx_boxes:
        bb = b['b']
        if not V.in_view_box(bb) or bb[3] < TM.X0 - 0.2 or bb[0] > TM.X1 + 0.2 or bb[4] < TM.Y0 or bb[1] > TM.Y1:
            continue
        o = eq_outline(V, TM.Eq('ctx', '', 'box', clip_box(V, b['b']), ''))
        p.rect(o[1], o[2], o[3], o[4], 'ТМ_ОВ')
    items.sort(key=lambda t: -t[0])
    eq_rects = {}
    for _, kind, obj in items:
        if kind == 'eq':
            if obj.ctx:
                o = draw_eq(p, V, obj, layer='ТМ_ОВ', mask=False)
            elif obj.id.endswith('-мотор'):
                o = draw_eq(p, V, obj, layer='ТМ_оборуд')
            else:
                o = draw_eq(p, V, obj)
            eq_rects[obj.id] = o
        elif kind == 'seg':
            pp, c = obj
            lay, lt = PIPE_STYLE[pp.sys]
            A, B = V.P(c[0]), V.P(c[1])
            Lp = math.hypot(B[0] - A[0], B[1] - A[1])
            if Lp < 0.05:
                if math.dist(c[0], c[1]) > 0.02:
                    r = max(0.8, pp.od * V.s / 2)
                    p.m.add_wipeout([(A[0] - r * 0.7, A[1] - r * 0.7), (A[0] + r * 0.7, A[1] + r * 0.7)],
                                    dxfattribs={'layer': lay})
                    p.circle(A[0], A[1], 0, lay, r_paper=r)
                continue
            if pp.sys == 'Д' or pp.od * V.s > 1.6:
                w = pp.od * V.s / 2
                d = unit(A, B)
                n = (-d[1], d[0])
                q = [(A[0] + n[0] * w, A[1] + n[1] * w), (B[0] + n[0] * w, B[1] + n[1] * w),
                     (B[0] - n[0] * w, B[1] - n[1] * w), (A[0] - n[0] * w, A[1] - n[1] * w)]
                xs, ys = [t[0] for t in q], [t[1] for t in q]
                p.m.add_wipeout([(min(xs), min(ys)), (max(xs), max(ys))], dxfattribs={'layer': lay})
                p.pl(q, lay, closed=True)
                if pp.sys == 'Д':
                    p.pl([A, B], 'ТМ_оси', ltype='ОВ_ШП', lw=13)
            else:
                p.pl([A, B], lay, ltype=lt)
        else:
            sym_fit(p, V, obj)
    # подписи
    for e in TM.EQUIP:
        if e.id in eq_rects and not e.ctx:
            o = eq_rects[e.id]
            if o[0] == 'rect':
                L.block(o[1:])
    for eid, txt, force in eq_labels:
        if eid not in eq_rects:
            continue
        o = eq_rects[eid]
        if o[0] == 'rect':
            cx, cy, w, h = (o[1] + o[3]) / 2, (o[2] + o[4]) / 2, o[3] - o[1], o[4] - o[2]
        else:
            cx, cy, w, h = o[1], o[2], o[3] * 1.4, o[3] * 1.4
        if force == 'in':
            ty = cy + h * 0.28 if h > 12.0 else cy
            p.t(cx, ty, txt, 2.2, 'center', 'ТМ_марки')
            tw_ = p.tw(txt, 2.2)
            if hasattr(L, 'texts'):
                L.texts.append((cx - tw_ / 2, ty - 1.4, cx + tw_ / 2, ty + 1.4))
        else:
            L.shelf((cx, cy), txt, 2.0, force=force)
    label_pipes(p, V, L, skip_labels)
    if extra:
        extra(p, V, L)


def label_pipes(p, V, L, skip):
    P = {pp.id: pp for pp in TM.PIPES}
    for ids, txt in PAIRS:
        if ids[0] in skip or ids[0] not in P:
            continue
        best = None
        for a, b in zip(P[ids[0]].pts, P[ids[0]].pts[1:]):
            c = V.clip(a, b)
            if c is None:
                continue
            A, B = V.P(c[0]), V.P(c[1])
            Lp = math.hypot(B[0] - A[0], B[1] - A[1])
            if Lp > 7.0 and (best is None or Lp > best[0]):
                best = (Lp, c, A, B)
        if not best:
            continue
        Lp, c, A, B = best
        sub = pair_sub(P, ids, c[0], c[1]) if abs(c[0][2] - c[1][2]) < 1e-6 and ids[0] != 'Д-каскад' else None
        ats = [(A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t) for t in (0.4, 0.65, 0.2, 0.85)]
        if not any(L.shelf(at, txt, 1.8, sub=sub, fallback=False) for at in ats):
            if not any(L.shelf(at, txt, 1.8, sub=sub, fallback='soft') for at in ats):
                for at in ats:                                      # как раньше: первое свободное место
                    if L.shelf(at, txt, 1.8, sub=sub):
                        break


def levels(p, V, u_right):
    x = V.org[0] + (u_right - V.u0) * V.s
    for z, t in ((0.0, None), (TM.H_SLAB, None)):
        level_mark(p, x, V.org[1] + z * V.s, z)
    p.t(x + 1.0, V.org[1] + TM.H_SLAB * V.s - 3.0, 'низ плиты', 1.6, 'tl', 'ТМ_размеры')


def section_sheet(no, specs, fname):
    TM.build()
    ctx_runs, ctx_boxes = TM.ov_context()
    walls = TM.room_walls()
    doc = new_doc()
    setup_layers(doc)
    sh = RDSheet(doc, 'Лист', TM_LIST[no], no, TM_TOTAL, fmt='А2', code=CODE_TM, bld=BLD_TM)
    p = PP(doc, sh.lay)
    for spec in specs:
        name, org, frame, u_lo, u_hi, eq_labels, skip, extra = spec
        kind, cut = CUTS[name]
        V = cut_view(kind, cut, org)
        L = Labels(p, frame)
        draw_section(p, V, walls, ctx_runs, ctx_boxes, u_lo, u_hi, L, eq_labels, skip, extra)
        u_room_hi = {'N': TM.X1, 'S': -TM.X0, 'W': TM.Y1, 'E': -TM.Y0}[kind]
        levels(p, V, u_hi + 0.15)
        xm = V.org[0] + ((u_lo + u_hi) / 2 - V.u0) * V.s
        sh.title(xm, frame[3] + 6.0, f'Разрез {name}-{name}. М 1:25', h=3.5)
    return doc, sh, p


EQ_N = [('ПК', 'ПК', 'in'), ('БП', 'БП', 'in'), ('ГС', 'ГС', (-6, 22)), ('РБ', 'РБ', 'in'), ('Б1', 'Б1', (8, 10)),
        ('РК', 'РК', 'in')] + [(n, n, 'in') for n, _ in TM.GROUPS]
EQ_W = [('К1', 'К1', 'in'), ('К2', 'К2', 'in'), ('ПК', 'ПК', 'in'), ('КШ-3', 'КШ-3', (-6, 16)), ('ШУ', 'ШУ', 'in'),
        ('Нейтр', 'нейтрализатор (ВК)', (-8, 14))]
EQ_E = [('Б1', 'Б1', 'in'), ('РБ-ГВС', 'РБ-ГВС', (-8, 12)), ('РБ', 'РБ', 'in'),
        ('РК', 'РК с группами Н3…Н7 (вид с торца)', (6, 22))]
EQ_S = [('ШУ', 'ШУ', 'in'), ('КШ-3', 'КШ-3 (ОВ)', (8, 18)), ('П1', 'П1 (ОВ)', 'in'), ('П1-узел', 'смесит. узел П1', (6, 30))]


Z0 = 205.0                                   # чистый пол на листе
FR_L, FR_R = (24.0, 186.0, 300.0, 398.0), (306.0, 186.0, 566.0, 398.0)
GRP = ('Н3-П', 'Н4-П', 'Н2-П', 'Н5-П')       # магистрали групп — в таблице, марки — на группах


def group_table(sh, x, y):
    """Выходы РК: назначение, расчётные расходы и напоры (лист 8 ОВ), трубы и отметки магистралей (модель)."""
    from ov_boiler_scheme import groups_calc
    G = groups_calc()['groups']
    route = {'Н3': 'вверх на +3,200, в тамбур 1.7', 'Н4': 'вверх на +3,200, в 1.7; КШ-3 — опуск на +2,600',
             'Н2': 'вверх на +3,200, в тамбур 1.7', 'Н5': 'вверх на +3,050, к узлу П1',
             'Н6': 'вниз, к вводу Ecoflex в полу', 'Н7': 'на +3,200, опуск к Б1'}
    pipe = {'Н3': 'PE-Xa 32×4,4', 'Н4': 'PE-Xa 25×3,5', 'Н2': 'PE-Xa 25×3,5', 'Н5': 'PE-Xa 20×2,8',
            'Н6': 'Ecoflex 32×2,9', 'Н7': 'сталь Ду25'}
    rows = [['Группа', 'Потребитель', 'Q, кВт', 'G, м³/ч', 'H, м', 'Насос', 'Трубы от РК', 'Трасса в топочной']]
    for n, _ in TM.GROUPS:
        g = G[n]
        rows.append([n, g['dest'], f1(g['Q'] / 1000, 1), f1(g['m3h'], 2), f1(g['H_m'], 2),
                     g['pump'] if not g.get('no_pump') else 'в узле П1', pipe[n], route[n]])
    widths = [13, 38, 12, 13, 11, 17, 25, 75]
    sh.table(x, y, widths, rows, h=1.8, heights=[6.0] + [5.0] * (len(rows) - 1),
             aligns=['center', 'left', 'center', 'center', 'center', 'center', 'left', 'left'])
    sh.s.text('Насосные группы РК (слева направо, как на РК)', x + sum(widths) / 2, y + 3.5, h=2.8,
              align='center')


def mains_label(at3, txt, force):
    def f(p, V, L):
        c = V.clip(at3, at3)
        if c is not None:
            L.shelf(V.P(at3), txt, 1.8, force=force)
    return f


def main():
    f12 = [
        ('1', (88.0, Z0), FR_L, TM.X0 - 0.95, TM.X1 + 0.40, EQ_N,
         ('Д-каскад', 'К-сб', 'Т4', 'В1-Б1', 'РБ-ГВС') + GRP,
         mains_label((TM.gx(0) - 0.0625, 12.40, TM.Z_HI), 'магистрали групп на юг, +3,200 (таблица ниже)', (-8, 12))),
        ('2', (338.0, Z0), FR_R, TM.Y0 - 0.45, TM.Y1 + 0.45, EQ_W,
         ('ГС-О', 'ГС-РК-П') + GRP,
         mains_label((17.05, 10.45, TM.Z_HI), 'Н3, Н4, Н2 → тамбур 1.7, оси +3,200', (8, 12))),
    ]
    doc, sh, p = section_sheet(3, f12, 'tm_sec12')
    group_table(sh, 24, 168)
    sh.notes(236, 168, 140, NOTES_SEC, h=2.0, spacing=1.0)
    print(save_and_pdf(doc, os.path.join(OUT, 'tm_sec12.dxf')))
    f34 = [
        ('3', (70.0, Z0), FR_L, -TM.Y1 - 0.45, -TM.Y0 + 0.45, EQ_E,
         ('XS', 'XR', 'К2-П', 'К1-П') + GRP,
         mains_label((TM.gx(0) - 0.0625, 11.80, TM.Z_HI), 'магистрали групп: Н3, Н4, Н2 — +3,200, Н5 — +3,050',
                     (6, 14))),
        ('4', (338.0, Z0), FR_R, -TM.X1 - 0.40, -TM.X0 + 0.95, EQ_S,
         ('XS', 'XR') + GRP,
         mains_label((17.30, TM.turn_y_mid if hasattr(TM, 'turn_y_mid') else 10.45, TM.Z_HI),
                     'Н3, Н4, Н2 → тамбур 1.7, оси +3,200; Н5 → П1, +3,050', (-6, 16))),
    ]
    doc, sh, p = section_sheet(4, f34, 'tm_sec34')
    group_table(sh, 24, 168)
    sh.notes(236, 168, 140, NOTES_SEC, h=2.0, spacing=1.0)
    print(save_and_pdf(doc, os.path.join(OUT, 'tm_sec34.dxf')))


NOTES_SEC = [
    'Разрезы получены проекцией 3D-модели котельной; положение разрезов — на плане (лист 2). Показано всё, что '
    'за плоскостью разреза; ближнее закрывает дальнее.',
    'Отметки — оси труб от чистого пола топочной ±0,000. П1, воздуховоды и шумоглушители (ОВ) — тонкой линией, для '
    'увязки.',
    'Условные обозначения — лист 1; экспликация оборудования — лист 2.',
]

if __name__ == '__main__':
    main()
