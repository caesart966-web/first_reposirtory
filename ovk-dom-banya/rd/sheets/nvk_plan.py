"""И05.09.26-НВК, лист 3. План наружных сетей В1, К1, К2, Др на топосъёмке. М 1:200 (А2).

python3 sheets/nvk_plan.py  ->  out/nvk_plan.dxf + PDF
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
import nvk_model as M  # noqa: E402
from nvk_draw import (legend_line, CODE_NVK, BLD_NVK, NVK_LIST, NVK_TOTAL, NVK_OUT, setup, finish, plan_view, draw_pipe,  # noqa
                      draw_well, flow_arrow, north_arrow, alev, data, msk, well_r, VLabels, PP, unit, in_box,
                      pipe_marked, fence_segs)

OUT = os.path.join(ROOT, 'out')
K = 200
MX, MY = 13.0, 7.0
BX = (30.0, 120.0, 250.0, 400.0)               # окно плана на листе, мм (44 × 56 м)
EXIST = {   # существующие поселковые сети (ИС ООО «Лика» в осях дома)
    'К1': {'pts': [(-9.0, -16.76), (1.39, -16.74), (10.40, -16.66), (34.0, -16.62)], 'mark': 'К1',
           'name': 'К1 сущ. Корсис Ø160 (ИС-3КК)'},
    'К1в': {'pts': [(M.DK.x, M.DK.y), (10.40, -16.66)], 'mark': 'К1', 'name': 'Ø110 (ИС-3КК)'},
    'К2': {'pts': [(-9.0, -15.45), (-0.56, -15.55), (21.34, -15.93), (34.0, -15.76)], 'mark': 'К2',
           'name': 'К2 сущ. Корсис Ø315 (ИС-3ЛК)'},
    'К2в': {'pts': [(21.34, -15.93), M.LK_STUB[:2]], 'mark': 'К2', 'name': 'выпуск ПЭ Ø63 (ИС-3ЛК)'},
    'В1': {'pts': [(-9.0, -18.86), (30.04, -18.88), (34.0, -18.87)], 'mark': 'В1',
           'name': 'В1 сущ. ПНД Ø110 (ИС-3ВК)'},
    'В1в': {'pts': [(30.04, -18.88), M.VK_STUB], 'mark': 'В1', 'name': 'выпуск ПЭ Ø32 в гильзе ПНД Ø63'},
}
EXIST_WELLS = [('КК355а', (10.40, -16.66), 'к 186,359, н.тр. 184,661'), ('КК355', (1.39, -16.74), 'к 186,615, н.тр. 184,969'),
               ('ЛК355', (21.34, -15.93), 'к 185,938, н.тр. 184,901'), ('ЛК354', (-0.56, -15.55), 'к 186,743, н.тр. 185,715'),
               ('ВК217', (30.04, -18.88), 'к 186,300, н.тр. 184,281')]


def draw_exist(p, V, box, L):
    for k, e in EXIST.items():
        pts = [V.P((x, y, 0)) for x, y in e['pts']]
        from nvk_draw import clip_poly
        for part in clip_poly(pts, box):
            pipe_marked(p, part, 'НВК_сущ', e['mark'], 34.0, 1.6, 'ОВ_ШТРИХ', None, L)
            for a, b in zip(part, part[1:]):
                L.segs.append((a, b))
    for nm, (x, y), sub in EXIST_WELLS:
        c = V.P((x, y, 0))
        if not in_box(c, box):
            continue
        p.circle(c[0], c[1], 0, 'НВК_сущ', r_paper=2.5)
        p.circle(c[0], c[1], 0, 'НВК_сущ', r_paper=1.1)


GRID = sorted(((dx, dy) for dx in range(-44, 45, 3) for dy in range(-18, 19, 2) if abs(dx) >= 4),
              key=lambda d: abs(d[0]) + 1.5 * abs(d[1]))       # запасные положения полок
GRID_W = sorted(((dx, dy) for dx in range(-60, 61, 3) for dy in range(-30, 31, 2) if abs(dx) >= 4),
                key=lambda d: abs(d[0]) + 1.5 * abs(d[1]))


def put(L, at, text, h, sub=None, cands=None, what=None, need=True):
    """Полка, у которой выноска не пересекает чужие выноски и полки, а полка — выноски, трубы и надписи
    (strict). Места: свои → обычные → сетка; сначала — рядом и вне зданий (L.bld_rects: полка и выноска
    не заходят на план дома и бани), затем где угодно, с широкой сеткой; не нашлось — сборка останавливается."""
    from tm_draw import default_cands
    soft = [r_ for r_ in getattr(L, 'bld_rects', []) if not (r_[0] <= at[0] <= r_[2] and r_[1] <= at[1] <= r_[3])]
    for extra in ([soft] if soft else []) + [[]]:
        L.busy += extra
        try:
            for cc in ([list(cands)] if cands else []) + [default_cands(), GRID] + ([] if extra else [GRID_W]):
                r = L.shelf(at, text, h, sub=sub, cands=cc, strict=True)
                if r is not None:
                    return r
        finally:
            for r_ in extra:
                L.busy.remove(r_)
    if need:
        raise SystemExit(f'НВК лист 3: нет места для подписи «{what or text}»')
    return None


CAND_OPT = None


def _cands_opt():
    """Смещения полок для подбора: ближние (как обычно) и сетка до 60 × 30 мм."""
    global CAND_OPT
    if CAND_OPT is None:
        from tm_draw import default_cands
        seen, out = set(), []
        for c in [tuple(c) for c in default_cands()] + \
                [(dx, dy) for dx in range(-60, 61, 3) for dy in range(-30, 31, 2) if abs(dx) >= 4]:
            if c not in seen:
                seen.add(c)
                out.append(c)
        CAND_OPT = out
    return CAND_OPT


def _geom(L, at, text, h, sub, dx, dy):
    p = L.p
    w = max(p.tw(text, h), p.tw(sub, h) if sub else 0) + 1.6
    top = h * 1.25 + 0.9
    bot = top if sub else 0.4
    x0 = at[0] + dx if dx >= 0 else at[0] + dx - w
    return (x0, at[1] + dy - bot, x0 + w, at[1] + dy + top), (x0 if dx >= 0 else x0 + w, at[1] + dy)


def _ovl(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def place_labels(L, reqs):
    """Подбор мест всех полок плана: выноска не пересекает чужие выноски и полки, полка — выноски, трубы,
    надписи и рамки (как VLabels strict). Из допустимых мест берётся самое дешёвое: длина выноски,
    полка на плане здания (L.bld_rects), выноска поперёк труб. Первыми ставятся подписи, у которых меньше
    всего допустимых мест (тесный двор, короткие трубы), — им не перекрывают последние места."""
    from vk_draw import _seg_x, _seg_rect

    def opts(rq, first=False):
        out = []
        prefs = [tuple(c) for c in (rq.get('prefs') or [])]
        for k, at in enumerate(rq['anchors']):
            for dx, dy in prefs + _cands_opt():
                r, e = _geom(L, at, rq['text'], rq['h'], rq['sub'], dx, dy)
                if not (L.free(r) and L._clean(at, e, r)):
                    continue
                if first:
                    out.append(None)
                    continue
                ln = math.dist(at, e)
                c = ln + 0.06 * max(0.0, ln - 20.0) ** 2 + 1.5 * k - (10.0 if (dx, dy) in prefs else 0.0)
                for s_ in getattr(L, 'bld_rects', []):
                    if s_[0] <= at[0] <= s_[2] and s_[1] <= at[1] <= s_[3]:
                        continue
                    c += 30.0 * _ovl(r, s_) / ((r[2] - r[0]) * (r[3] - r[1]))
                    c += 6.0 * _seg_rect(at, e, s_)
                c += 5.0 * sum(_seg_x(at, e, a_, b_) for a_, b_ in L.segs)
                c += 12.0 * sum(_seg_x(at, e, a_, b_) for a_, b_ in getattr(L, 'fence', []))
                out.append((c, at, (dx, dy)))
        return out

    order = sorted(reqs, key=lambda rq: (len(opts(rq, first=True)), rq.get('rank', 0)))
    for rq in order:
        o = opts(rq)
        if not o:
            raise SystemExit(f'НВК лист 3: нет места для подписи «{rq["text"]}»')
        c, at, f = min(o, key=lambda t: t[0])
        L.shelf(at, rq['text'], rq['h'], sub=rq['sub'], force=f)


def solid_rects(doc, V, box):
    """Сплошные заливки подложки (остекление, полотна дверей ГП01 и бани) — на листе тёмные, полки на них
    не ставятся."""
    from ezdxf import bbox
    out = []

    def walk(ins, depth=0):
        for ve in ins.virtual_entities():
            if ve.dxftype() == 'INSERT' and depth < 4:
                walk(ve, depth + 1)
            elif ve.dxftype() == 'HATCH' and ve.dxf.solid_fill:
                e = bbox.extents([ve], fast=True)
                if not e.has_data:
                    continue
                a, b = V.P((e.extmin.x / 1000, e.extmin.y / 1000, 0)), V.P((e.extmax.x / 1000, e.extmax.y / 1000, 0))
                r = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
                if r[2] >= box[0] and r[0] <= box[2] and r[3] >= box[1] and r[1] <= box[3]:
                    out.append(r)
    for ins in doc.modelspace().query('INSERT'):
        if ins.dxf.name in ('ГП01', 'БАНЯ_АР'):
            walk(ins)
    return out


def anchors(L, V, box, pts):
    """Точки выноски на трубе: середина самого длинного звена в окне, затем другие доли и звенья — только вне
    занятых мест (марки трубы, кружки колодцев), чтобы точка выноски не легла в текст."""
    segs = []
    for a, b in zip(pts, pts[1:]):
        A, B = V.P((a[0], a[1], 0)), V.P((b[0], b[1], 0))
        segs.append((math.dist(A, B), A, B))
    out = []
    for _, A, B in sorted(segs, key=lambda t: -t[0]):
        for t in (0.5, 0.38, 0.62, 0.27, 0.73, 0.16, 0.84, 0.92, 0.96):
            q = (A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t)
            if in_box(q, box) and not any(s_[0] - 0.4 <= q[0] <= s_[2] + 0.4 and s_[1] - 0.4 <= q[1] <= s_[3] + 0.4
                                          for s_ in L.busy):
                out.append(q)
    return out


def frag_rect(V0):
    """Рамка фрагмента 1 на плане 1:200 (нижний левый и верхний правый углы на листе)."""
    w2, h2 = (FB[2] - FB[0]) / 10.0, (FB[3] - FB[1]) / 10.0
    return V0.P((FM[0] - w2 / 2, FM[1] - h2 / 2, 0)), V0.P((FM[0] + w2 / 2, FM[1] + h2 / 2, 0))


def net(p, V, box, L, D, every=40.0):
    draw_exist(p, V, box, L)
    pipes = D['pipes']
    order = {'Др': 0, 'К2': 1, 'В1': 2, 'К1': 3}
    for pp in sorted(pipes, key=lambda q: order[q['sys']]):
        draw_pipe(p, V, pp, box, every=every if pp['sys'] != 'Др' else every * 1.15, L=L)
    # утепление — полоса вдоль трубы
    for pp in pipes:
        for s0, s1 in pp['ins']:
            mp = M.PIPES[[q.id for q in M.PIPES].index(pp['id'])]
            a, b = mp.at(s0), mp.at(s1)
            pts = []
            s = s0
            while s <= s1 + 1e-6:
                q = mp.at(min(s, s1))
                c_ = V.P((q[0], q[1], 0))
                if in_box(c_, box):
                    pts.append(c_)
                s += 0.2
            if len(pts) > 1:
                from tm_draw import DPlan  # noqa
                from rdbase import offset_poly
                for sg in (1, -1):
                    p.pl(offset_poly(pts, sg * 1.3), 'НВК_утепл')
    # теплотрасса ОВ (внешняя сеть) — двойной линией, как на листе 14 ОВ
    from nvk_draw import clip_poly
    from rdbase import offset_poly
    for e in D.get('ext', []):
        pts = [V.P((x, y, 0)) for x, y in e['pts']]
        for part in clip_poly(pts, box):
            if len(part) < 2:
                continue
            for sg in (1, -1):
                p.pl(offset_poly(part, sg * max(0.35, e['od'] * V.s / 2)), 'НВК_ТС')
            for a, b in zip(part, part[1:]):
                L.segs.append((a, b))
    # футляры на водопроводе — штриховыми линиями вдоль трубы
    for pp in pipes:
        mp = M.PIPES[[q.id for q in M.PIPES].index(pp['id'])]
        for s0, s1 in (mp.sleeve or []):
            pts, s = [], s0
            while s <= s1 + 1e-6:
                q = mp.at(min(s, s1))
                c_ = V.P((q[0], q[1], 0))
                if in_box(c_, box):
                    pts.append(c_)
                s += 0.2
            if len(pts) > 1:
                for sg in (1, -1):
                    p.pl(offset_poly(pts, sg * 0.9), 'НВК_футляр', ltype='ОВ_ШТРИХ')
    # направление стока
    for pp in pipes:
        if pp['kind'] != 'grav':
            continue
        lay = STY = {'К1': 'НВК_К1', 'К2': 'НВК_К2', 'Др': 'НВК_Др'}[pp['sys']]
        for a, b in zip(pp['pts'], pp['pts'][1:]):
            m_ = V.P((a[0] + (b[0] - a[0]) * 0.32, a[1] + (b[1] - a[1]) * 0.32, 0))
            if in_box(m_, box):
                flow_arrow(p, V, a, b, lay, at=0.32)
    # колодцы
    for w in D['wells']:
        if not in_box(V.P((w['x'], w['y'], 0)), box):
            continue
        c, r = draw_well(p, V, w)
        L.block((c[0] - r, c[1] - r, c[0] + r, c[1] + r))
    # граница ВК / НВК и выпуски
    for (x, y), d, txt in (((M.vk_end('К1-1')[0], M.vk_end('К1-1')[1]), (0, 1), 'выпуск К1-1 (ВК)'),
                           ((M.vk_end('К1-б')[0], M.vk_end('К1-б')[1]), (0, 1), 'выпуск К1-б (ВК)'),
                           ((M.vk_end('К1-бв')[0], M.vk_end('К1-бв')[1]), (0, 1), 'выпуск К1-бв (ВК)'),
                           ((20.60, M.Y_VV), (1, 0), 'ввод В1 (ВК)'), ((19.60, 0.10), (0, 1), 'К2-1 лотка гаража (ВК)')):
        c = V.P((x, y, 0))
        if not in_box(c, box):                         # во фрагменте 1:100 — только свои точки
            continue
        n = (d[1], -d[0])
        p.line(c[0] - n[0] * 1.8, c[1] - n[1] * 1.8, c[0] + n[0] * 1.8, c[1] + n[1] * 1.8, 'НВК_марки', lw=50)
    # кран на вводе
    vx, vy = M.v1.valve
    c = V.P((vx, vy, 0))
    if in_box(c, box):
        p.poly([(c[0] - 1.2, c[1] - 0.8), (c[0] + 1.2, c[1] + 0.8), (c[0] + 1.2, c[1] - 0.8), (c[0] - 1.2, c[1] + 0.8)],
               'НВК_В1', fill=7)
    return pipes


def main():
    D = data()
    doc = new_doc()
    setup(doc)
    sh = RDSheet(doc, 'Лист', NVK_LIST[3], 3, NVK_TOTAL, fmt='А2', code=CODE_NVK, bld=BLD_NVK)
    p = PP(doc, sh.lay)
    cx, cy = (BX[0] + BX[2]) / 2, (BX[1] + BX[3]) / 2
    V, box = plan_view(doc, sh, cx, cy, BX[2] - BX[0], BX[3] - BX[1], MX, MY, K)
    p.rect(*box, 'ТМ_оборуд_тонк')
    L = VLabels(p, box)
    # рамка фрагмента 1 (рисует fragment()) — полки и заголовки её не пересекают
    fa, fc = frag_rect(V)
    L.segs += [((fa[0], fa[1]), (fc[0], fa[1])), ((fc[0], fa[1]), (fc[0], fc[1])),
               ((fc[0], fc[1]), (fa[0], fc[1])), ((fa[0], fc[1]), (fa[0], fa[1]))]
    L.block((fc[0] - 1.0 - p.tw('Фрагмент 1', 2.2), fc[1] + 1.2, fc[0] - 1.0, fc[1] + 1.2 + 2.2))
    # подписи зданий и ±0,000
    for (x, y), t, sub in (((10.0, 8.3), 'Жилой дом', f'±0,000 = {alev(M.H0)}'),
                           ((11.0, 28.2), 'Баня', f'±0,000 = {alev(M.H0B)}')):
        c = V.P((x, y, 0))
        for dy in (0, -1, -2, -3, -4, -5, -6, 1, 2, 3):
            cc_ = (c[0], c[1] + dy)
            if L.free((cc_[0] - 14, cc_[1] - 4.5, cc_[0] + 14, cc_[1] + 4.5)):
                c = cc_
                break
        else:
            raise SystemExit(f'НВК лист 3: заголовок «{t}» ложится на рамку фрагмента')
        p.t(c[0], c[1] + 1.5, t, 3.0, 'center', 'НВК_марки')
        p.t(c[0], c[1] - 2.5, sub, 2.2, 'center', 'НВК_марки')
        L.block((c[0] - 14, c[1] - 4.5, c[0] + 14, c[1] + 4.5))
    # врезка выпуска КЛ-1 в сущ. ЛК: короткая труба почти вся в кружке КЛ-1 — марку сущ. выпуска у врезки
    # не ставить, здесь точка выноски К2-ЛК (место освобождается после сетей)
    q_ = V.P((M.LK_CON[0], M.LK_CON[1], 0))
    hold = (q_[0] - 2.5, q_[1] - 3.0, q_[0] + 2.5, q_[1] + 1.0)
    L.block(hold)
    pipes = net(p, V, box, L, D)
    L.busy.remove(hold)
    L.fence = fence_segs(V, box)                  # полки не пересекают границу участка, выноски — по возможности
    L.segs += L.fence
    # здания — полки по возможности вне их планов
    L.bld_rects = []
    for r_ in (M.HOUSE, M.BATHB):
        A_, B_ = V.P((r_[0], r_[1], 0)), V.P((r_[2], r_[3], 0))
        L.bld_rects.append((min(A_[0], B_[0]), min(A_[1], B_[1]), max(A_[0], B_[0]), max(A_[1], B_[1])))
    # беседка (ГП Заказчика) и садовая колонка у неё
    g = M.GAZEBO
    a0, a1 = V.P((g[0], g[1], 0)), V.P((g[2], g[3], 0))
    p.pl([(a0[0], a0[1]), (a1[0], a0[1]), (a1[0], a1[1]), (a0[0], a1[1]), (a0[0], a0[1])], 'НВК_ГП',
         ltype='ОВ_ШТРИХ')
    c = V.P(((g[0] + g[2]) / 2, (g[1] + g[3]) / 2, 0))
    p.t(c[0], c[1], 'Беседка', 2.0, 'center', 'НВК_марки')
    L.block((min(a0[0], a1[0]), min(a0[1], a1[1]), max(a0[0], a1[0]), max(a0[1], a1[1])))
    kb = V.P((M.KB[0], M.KB[1], 0))
    p.circle(kb[0], kb[1], 0, 'НВК_В1', r_paper=0.9, lw=50)
    # ---------------------------------------------------------------- подписи (подбор мест — place_labels)
    for r_ in solid_rects(doc, V, box):
        L.block(r_)
    REQ = []

    def req(anchors_, text, h, sub=None, prefs=None):
        REQ.append(dict(anchors=list(anchors_), text=text, h=h, sub=sub, prefs=prefs))

    def on_line(pts, q):                          # ближайшая точка ломаной к q
        best = None
        for a_, b_ in zip(pts, pts[1:]):
            dx_, dy_ = b_[0] - a_[0], b_[1] - a_[1]
            t = max(0.0, min(1.0, ((q[0] - a_[0]) * dx_ + (q[1] - a_[1]) * dy_) / (dx_ * dx_ + dy_ * dy_)))
            c_ = (a_[0] + t * dx_, a_[1] + t * dy_)
            if best is None or math.dist(c_, q) < math.dist(best, q):
                best = c_
        return best
    bq = on_line(M.FENCE_W, (-4.2, 26.0))         # точка на западной границе участка (она же забор)
    req([V.P((bq[0], bq[1], 0))], 'Граница з/у 50:08:0050209:1600', 1.9, sub='(з/у 19, ул. Лесная)',
        prefs=[(6, 6), (6, -6), (8, 14)])
    req([kb], 'КБ — колонка садовая с краном', 1.9, sub='сезонная, слив через КП-1')
    for w in D['wells']:
        c = V.P((w['x'], w['y'], 0))
        r = well_r(w, V)
        req([c], w['id'] + (' (сущ.)' if w['exist'] else ''), 2.0, sub=f'к {alev(w["cover"])}' if w['cover'] else None,
            prefs=[(r + 2, r + 2), (-r - 2, r + 2), (r + 2, -r - 2), (-r - 2, -r - 2), (r + 5, 0.5), (-r - 5, 0.5)])
    for nm, (x, y), sub in EXIST_WELLS:
        c = V.P((x, y, 0))
        if in_box(c, box):
            req([c], f'{nm} (сущ.)', 1.8, sub=sub)
    for e in D.get('ext', []):                    # теплотрасса ОВ
        a_, b_ = e['pts'][1], e['pts'][2]
        pts_ = [V.P((a_[0] + (b_[0] - a_[0]) * t, a_[1] + (b_[1] - a_[1]) * t, 0))
                for t in (0.62, 0.5, 0.75, 0.4, 0.85, 0.3, 0.2, 0.92)]
        req([q for q in pts_ if in_box(q, box)], 'Т1, Т2 — теплотрасса Ecoflex (ОВ, лист 14)', 1.9,
            sub=f'прямая, ниже Др: верх ≤ {alev(M.ECO_TOP)}')
    for sx in M.cross_s(M.kb_line, M.k12):        # футляр В1-Бс над К1-б1 — точка выноски задана пересечением
        q = M.kb_line.at(sx)
        req([V.P((q[0], q[1], 0))], 'В1-Бс над К1-б1 — в футляре', 1.9, sub='ПНД Ø63, по 2 м в стороны')
    drop = {pid: z - M.DK.bottom for pid, z in [(pp_.id, z_) for pp_, z_ in M.DK.ins]}
    kbt = [M.PLAN_Z - M.kb_line.top(s_) for s_ in (0.0, M.kb_line.length())]
    KB_D = (alev(min(kbt), 2), alev(max(kbt), 2))
    PM = {q.id: q for q in M.PIPES}

    def ii(pid):
        return alev(PM[pid].i, 3).rstrip('0')

    assert PM['К1-бн'].i == PM['К1-бвн'].i and PM['Др-1/2'].i == PM['Др-1/4'].i and PM['К2-А'].i == PM['К2-Б'].i
    assert PM['ДрБ-1/2'].i == PM['К2-БА'].i and PM['Др-Т'].i == PM['К2-Т'].i
    LBL = {
        'К1-1н': (f'К1-1 Ø110 ПП SN8, i={ii("К1-1н")}, L={alev(M.k1h.length(), 1)} м',
                  f'перепад в ДК5-018 {alev(drop["К1-1н"])} м'),
        'К1-бн': (f'К1-б и К1-бв Ø110 ПП SN8, i={ii("К1-бн")}',
                  f'от бани в КК-1, L={alev(M.k1b.length(), 1)} и {alev(M.k1be.length(), 1)} м'),
        'К1-б1': (f'К1 Ø110 ПП SN8, i={ii("К1-б1")}, L={alev(M.k12.length(), 1)} м', 'от КК-1 к вводу в дом (ВК)'),
        'В1-н': (f'В1 ПЭ 100 SDR11 32×3,0, L={alev(M.v1.length(), 1)} м', 'глубина 1,6 м, у ввода — утепл. и кабель'),
        'КХ-8н': (f'В1 (КХ-8) ПЭ 25, L={alev(PM["КХ-8н"].length(), 1)} м', 'сезонная, слив в КП-1'),
        'К2-ЛК': (f'К2 ПЭ Ø63, i={ii("К2-ЛК")}, L={alev(M.s_out.length(), 2)} м', 'врезка в сущ. выпуск ЛК Ø63'),
        'Др-1/2': (f'Др Ø110 перф. i={ii("Др-1/2")} + К2 Ø110 i={ii("К2-А")}', 'в общей траншее, К2 выше'),
        'Др-1/4': (f'Др Ø110 перф. i={ii("Др-1/4")} + К2 Ø110 i={ii("К2-Б")}', None),
        'ДрБ-1/2': (f'Др Ø110 перф. + К2 Ø110, i={ii("ДрБ-1/2")}', 'вокруг бани'),
        'Др-Т': ('Др и К2 Ø110 — транзит от бани', f'i={ii("Др-Т")}, L={alev(PM["Др-Т"].length(), 1)} м'),
        'К2-1н': ('К2 Ø110 от лотка гаража', 'утеплить, присоед. к кольцу К2'),
        'В1-Бс': (f'В1 ПЭ 25 от КП-1 к колонке КБ, L={alev(M.kb_line.length(), 0)} м',
                  f'сезонная, i={alev(M.I_KB, 3).rstrip("0")} к КП-1, гл. {KB_D[0]}–{KB_D[1]} м до верха'),
    }
    for pp in pipes:
        if pp['id'] in LBL:
            txt, sub = LBL[pp['id']]
            req(anchors(L, V, box, pp['pts'])[:8], txt, 1.9, sub=sub)
    place_labels(L, REQ)
    north_arrow(p, box[0] + 12, box[3] - 14)
    sh.title(cx, box[3] + 8.0, 'План наружных сетей В1, К1, К2, Др. М 1:200', h=3.5)
    # ведомость колодцев (справа)
    rows = [['Колодец', 'Тип, Ø', 'X (МСК-50)', 'Y (МСК-50)', 'x / y от осей 1/А, м', 'Крышка', 'Лоток вх.', 'Лоток вых.',
             'Глуб., м', 'Люк']]
    TYPE = {'КК': 'К1, полим. Ø630', 'ДрК': 'Др, полим. Ø315', 'КЛ': 'К2, ж/б Ø1500', 'КП': 'полив, Ø400',
            'ДК (сущ.)': 'К1, сущ.'}
    for w in D['wells']:
        N_, E_ = msk(w['x'], w['y'])
        zin = ', '.join(alev(z) for _, z in w['ins']) or '—'
        zout = ', '.join(sorted(set(alev(z) for _, z in w['outs']))) or ('—' if not w['exist'] else alev(w['bottom']))
        zmin = min([z for _, z in w['ins']] + [z for _, z in w['outs']] + ([w['bottom']] if w['bottom'] else []))
        dep = f'{w["cover"] - zmin:.2f}'.replace('.', ',') if w['cover'] else '—'
        rows.append([w['id'], TYPE[w['kind']], f'{N_:.2f}'.replace('.', ','), f'{E_:.2f}'.replace('.', ','),
                     f'{w["x"]:.2f} / {w["y"]:.2f}'.replace('.', ','), alev(w['cover']) if w['cover'] else '—',
                     zin, zout, dep, '—' if w['exist'] else ('Т' if w.get('drive') else 'Л')])
    widths = [16, 26, 24, 26, 30, 16, 30, 28, 14, 10]
    x_t = 262.0
    sh.s.text('Ведомость колодцев', x_t + sum(widths) / 2, 409, h=3.0, align='center')
    yb = sh.table(x_t, 404, widths, rows, row_h=6.2, head_h=8.0, h=1.9)
    # точки подключения
    pts_rows = [['Сеть', 'Точка подключения (сущ.)', 'Данные ИС / топосъёмки', 'Принято в проекте'],
                ['К1', 'ДК5-018 (дворовый колодец з/у)', f'к 186,750 / {alev(M.DK.cover)}; лоток 185,019 / {alev(M.DK.bottom)}',
                 'врезка выпуска К1-1 (дом и баня)'],
                ['В1', 'выпуск ПЭ Ø32 в гильзе Ø63 от ВК217', 'глубина 1,6–1,8 м (ИС-3ВК)',
                 f'ось {alev(M.Z_STUB)} — шурф'],
                ['К2, Др', 'выпуск ПЭ Ø63 от ЛК355', 'глубина 1,0–1,7 м (ИС-3ЛК)', f'лоток {alev(M.LK_STUB[2])} — шурф']]
    sh.s.text('Точки подключения к поселковым сетям (д. Исаково)', x_t + 108, yb - 8, h=3.0, align='center')
    yb2 = sh.table(x_t, yb - 12, [16, 66, 78, 56], pts_rows, row_h=6.5, head_h=7.0, h=1.9)
    notes = [
        f'Подложка — топосъёмка (ИГИ ООО «ЭККЕР», 08.2026) в осях дома, здания — по ГП01. Отметки абсолютные, '
        f'Балтийская система. Координаты колодцев — МСК-50 (по границам участка), привязки — от пересечения осей 1/А дома.',
        f'Отметки — по данным Заказчика: ±0,000 (чистый пол) дома и бани = {alev(M.H0)}, участок выравнивается до '
        f'{alev(M.PLAN_Z)}; отметки крышек колодцев — по планировке.',
        'Положение и отметки выпусков ВК и ЛК у юго-восточного угла участка и лотка ДК5-018 уточнить шурфованием '
        'до начала работ; при расхождении более 0,10 м — сообщить проектировщику.',
        'К1 — ПП SN8 Ø110, трасса — по схеме Заказчицы 26.10.2026: две прямые линии бани (К1-б — сборный от душа, '
        f'К1-бв — от стояка Ст.К1-б) через колодец КК-1 в сборный дома К1-1 (ВК) с уклоном {alev(M.k1b.i, 3).rstrip("0")}, '
        f'выпуск К1-1 (дом и баня) в ДК5-018 — {alev(M.k1h.i, 3).rstrip("0")} (П1). КК-1 — полимерный Ø630 с двумя входами '
        f'с лотком и телескопической шахтой. Заезды вдоль западного и восточного заборов (Заказчик): в полосе '
        f'{alev(M.DRIVE_W, 1)} м и перед гаражом — люки Т (C250), засыпка песком на всю глубину (Купл ≥ 0,95).',
        'Др — перфорированная труба Ø110 в геотекстиле в щебне 20–40 под утеплённой отмосткой зданий, колодцы '
        'Ø315; К2 — ПП SN8 Ø110 в той же траншее выше дренажа (лотки — листы 5, 6). Выпуски К2 из стен (стояки '
        'внутренних водостоков) присоединяются к кольцу К2 косыми тройниками — места по привязке воронок.',
        f'Дренаж и К2 — в КЛ-1 (ж/б Ø1500, отстойная часть {alev(M.KL_OUT - M.KL1.bottom, 1)} м, регулирующий объём — П2): '
        'К2-Б с запада, К2-К '
        'с севера, дренаж Др-К — с северо-запада, между ними, без пересечения с К2, через обратный клапан. КЛ-1 — '
        'восточнее пандуса гаража, у южной границы участка, на существующем выпуске ЛК Ø63 (Заказчица 27.10.2026): '
        'выпуск КЛ-1 — врезка в существующую трубу электросварной муфтой Ø63 за южной стенкой колодца, существующий '
        f'выпуск севернее врезки (≈{alev(M.LK_DEMO, 1)} м, в котловане КЛ-1) — демонтировать. Колодец — в зоне площадки '
        'перед гаражом: дорожная плита и чугунный люк тяжёлого типа Т (C250), крышка в уровне покрытия.',
        'Утепление — плиты ЭППС 50 мм шириной 1,2 м над трубой, где глубина меньше нормы (п. 6.2.4 '
        'СП 32.13330.2018): ' + ', '.join(pp_.id for pp_ in M.PIPES if pp_.sys != 'В1' and M.frost_check(pp_)) +
        '; В1 у ввода — в скорлупе ППУ с греющим кабелем (лист 8, узел 1).',
        'Пересечения в свету: В1 над К1, К2 — не менее 0,4 м, при меньшем — не менее 0,2 м в футляре ПНД Ø63 по 2 м '
        'в стороны (СП 31.13330.2021, п. 11.48): КХ-8н — целиком, В1-Бс — от КП-1 за теплотрассу и над К1-б1; К1 над '
        f'Др и К2, К2 над Др — не менее 0,1 м. Теплотрасса Ecoflex (ОВ, л. 14) — ниже Др и К2, верх не выше '
        f'{alev(M.ECO_TOP)}, не менее 0,2 м (СП 124.13330, прил. А). По горизонтали — табл. 12.6 СП 42.13330.2016. '
        'Трассы — прямые, без лишних поворотов (Заказчица 27.10.2026): теплотрасса Ecoflex — одной прямой от '
        'подъёма в доме до подъёма в бане, без изгибов в плане; В1-Бс — от КП-1 на север и прямо на запад. '
        'Ввод В1 — без приямка: под краем плиты и сквозь плиту в футляре (ВК, лист 14, узел 1; лист 8, узел 1).',
    ]
    sh.notes(262, yb2 - 8, 214, notes, h=2.0, spacing=1.0)
    # условные обозначения
    lx, ly = 486.0, yb2 - 8
    sh.s.text('Условные обозначения', lx + 48, ly, h=2.8, align='center')
    items = [('НВК_К1', None, 'К1', 'бытовая канализация (проект)'), ('НВК_К2', None, 'К2', 'ливневая канализация'),
             ('НВК_Др', 'ОВ_ШТРИХ', 'Др', 'дренаж'), ('НВК_В1', None, 'В1', 'водопровод'),
             ('НВК_сущ', 'ОВ_ШТРИХ', 'К1', 'существующие поселковые сети'),
             ('НВК_утепл', None, None, 'утепление ЭППС (контур)'),
             ('НВК_ТС', None, None, 'теплотрасса Т1, Т2 (раздел ОВ)'),
             ('НВК_футляр', 'ОВ_ШТРИХ', None, 'футляр ПНД на водопроводе')]
    for i, (lay, lt, mk, t) in enumerate(items):
        yy = ly - 7 - i * 6.0
        legend_line(p, lx, yy, lay, lt, mk)
        p.t(lx + 21, yy, t, 1.8, 'left', 'НВК_текст')
    yy = ly - 7 - len(items) * 6.0
    p.circle(lx + 9, yy, 0, 'НВК_К1', r_paper=1.6, lw=50)
    p.t(lx + 21, yy, 'колодец проектируемый', 1.8, 'left', 'НВК_текст')
    yy -= 6
    p.circle(lx + 9, yy, 0, 'НВК_сущ', r_paper=2.0)
    p.circle(lx + 9, yy, 0, 'НВК_сущ', r_paper=0.9)
    p.t(lx + 21, yy, 'колодец существующий', 1.8, 'left', 'НВК_текст')
    yy -= 6
    p.line(lx + 9, yy - 1.8, lx + 9, yy + 1.8, 'НВК_марки', lw=50)
    p.t(lx + 21, yy, 'граница ВК / НВК (выпуск, ввод)', 1.8, 'left', 'НВК_текст')
    yy -= 6
    flow_arrow(p, type('V', (), {'P': staticmethod(lambda q: (q[0], q[1]))})(), (lx + 2, yy - 1.6), (lx + 16, yy - 1.6),
               'НВК_марки', at=0.5)
    p.t(lx + 21, yy, 'направление стока', 1.8, 'left', 'НВК_текст')
    fragment(doc, sh, p, D, V, box)
    finish(doc)
    return save_and_pdf(doc, os.path.join(OUT, 'nvk_plan.dxf'))


FB = (266.0, 62.0, 466.0, 198.0)               # фрагмент 1: 20 × 13,6 м при М 1:100 (над ним — примечания)
FM = (17.0, 1.0)


def fragment(doc, sh, p, D, V0, box0):
    from tm_draw import dim_h, dim_v, default_cands
    cx, cy = (FB[0] + FB[2]) / 2, (FB[1] + FB[3]) / 2
    V, b = plan_view(doc, sh, cx, cy, FB[2] - FB[0], FB[3] - FB[1], FM[0], FM[1], 100)
    p.rect(*b, 'ТМ_оборуд_тонк')
    # рамка фрагмента на плане 1:200
    a, c = frag_rect(V0)
    p.rect(a[0], a[1], c[0], c[1], 'НВК_марки', ltype='ОВ_ШП')
    p.t(c[0] - 1.0, c[1] + 1.2, 'Фрагмент 1', 2.2, 'br', 'НВК_марки')
    L = VLabels(p, b)
    # оси 5 и А
    top_m = FM[1] + (FB[3] - FB[1]) / 2 / 10.0        # верх фрагмента в метрах (М 1:100)
    for nm, (p0, p1), at in (('5', ((20.0, -6.0), (20.0, top_m)), 'top'), ('А', ((7.0, 0.0), (27.0, 0.0)), 'left')):
        A, B = V.P((p0[0], p0[1], 0)), V.P((p1[0], p1[1], 0))
        p.pl([A, B], 'ТМ_оси', ltype='ОВ_ШП')
        q = B if at == 'top' else A
        off = (0, 5.0) if at == 'top' else (-5.0, 0)
        p.circle(q[0] + off[0], q[1] + off[1], 0, 'ТМ_оси', r_paper=3.5)
        p.t(q[0] + off[0], q[1] + off[1], nm, 2.8, 'center', 'ТМ_оси')
        L.block((q[0] + off[0] - 4, q[1] + off[1] - 4, q[0] + off[0] + 4, q[1] + off[1] + 4))
    net(p, V, b, L, D, every=60.0)
    L.segs += fence_segs(V, b)
    for w in D['wells']:
        cc = V.P((w['x'], w['y'], 0))
        if not in_box(cc, b):
            continue
        r = well_r(w, V)
        ins = ', '.join(sorted(set(alev(z) for _, z in w['ins'])))
        outs = ', '.join(sorted(set(alev(z) for _, z in w['outs'])))
        sub = (f'вх. {ins}' if ins else '') + (f'; вых. {outs}' if outs else '')
        if w['exist']:
            sub = f'к {alev(w["cover"])}; лоток {alev(w["bottom"])}'
        cands = [(r + 3, r + 4), (-r - 3, r + 4), (r + 3, -r - 4), (-r - 3, -r - 4), (r + 10, r + 12),
                 (-r - 10, r + 12), (r + 10, -r - 12), (-r - 10, -r - 12)]
        if w['id'] == 'КЛ-1':                     # справа внизу, правее линии сущ. выпуска ВК (выше — размер)
            cands = [(16.5, -3.0), (17.0, -3.4), (19.5, -8.2)] + cands
        put(L, cc, f'{w["id"]}' + (' (сущ.)' if w['exist'] else f', к {alev(w["cover"])}'), 1.9, sub=sub or None,
            cands=cands, what=f'фрагмент: марка колодца {w["id"]}')
    # ввод Др в КЛ-1 — точка на наружной стенке колодца по направлению Др-К
    _a = M.dK.pts[-2]
    _dl = math.dist(_a, M.KL1.xy)
    DR_IN = (M.KL1.x + (_a[0] - M.KL1.x) / _dl * 0.80, M.KL1.y + (_a[1] - M.KL1.y) / _dl * 0.80)
    det = [(M.VK_STUB, 'Выпуск ВК Ø32 в гильзе Ø63', f'(сущ.), ось ≈{alev(M.Z_STUB)} — шурф',
            [(16, -9), (16, -6), (17, -12)]),
           ((M.LK_STUB[0], M.LK_STUB[1]), 'Конец выпуска ЛК Ø63 (сущ.)',
            f'лоток ≈{alev(M.LK_STUB[2])} — шурф; демонтаж', [(-15, 9), (-15, 12), (-17, 15)]),
           (M.LK_CON, 'Врезка в выпуск ЛК Ø63', f'муфта, лоток ≈{alev(M.Z_LK_CON)}'),
           (M.v1.valve, 'ЗУ-1: кран шаровой ПЭ Ду32 подземный', 'со штоком и ковером'),
           ((19.60, 0.10), 'К2-1 от лотка гаража (ВК)', f'лоток {alev(M.H0 - 0.835)}'),
           (DR_IN, 'Ввод Др в КЛ-1 —', 'через обратный клапан',      # наклонной выноской: по горизонтали она
            [(34, 6), (34, 8), (36, 5), (34, -5), (36, -6), (38, 7)]),   # сливалась с полкой конца выпуска ЛК
           (next(c['xy'] for c in M.crossings() if c['up'] == 'К1-1н'), 'К1 над Др и К2:', 'зазоры ' + ' и '.join(
               alev(c['gap']) for c in M.crossings() if c['up'] == 'К1-1н') + ' м'),
           ((M.vk_end('К1-1')[0], M.vk_end('К1-1')[1]), 'Выпуск К1-1 (ВК)', f'лоток {alev(M.vk_end("К1-1")[2])}')]
    for (x, y), t, sub, *cn in det:
        cc = V.P((x, y, 0))
        put(L, cc, t, 1.8, sub=sub, cands=cn[0] if cn else None, what=f'фрагмент: {t}')
    # привязки к осям 5 и А
    kl = V.P((M.KL1.x, M.KL1.y, 0))
    ax5 = V.P((20.0, 0.0, 0))
    yb = b[3] - 9
    dim_h(p, ax5[0], kl[0], yb - 7, yref0=None, yref1=None, txt=f'{int(round((M.KL1.x - 20.0) * 1000))}')
    wx = V.P((M.X_W, -1.0, 0))
    dim_h(p, ax5[0], wx[0], yb, txt=f'{int(round((M.X_W - 20.0) * 1000))}')
    dk = V.P((M.DK.x, M.DK.y, 0))
    dim_v(p, ax5[1], kl[1], b[2] - 2.5, txt=f'{int(round(-M.KL1.y * 1000))}')
    dim_v(p, ax5[1], dk[1], b[0] + 10, txt=f'{int(round(-M.DK.y * 1000))}')
    p.t(FB[0], FB[3] + 4.0, 'Фрагмент 1. Южная часть участка. М 1:100', 2.8, 'left', 'НВК_текст')   # правее — кружок оси 5


if __name__ == '__main__':
    print(main())
