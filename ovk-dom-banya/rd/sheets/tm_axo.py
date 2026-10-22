"""И05.09.26-ТМ, лист 5. Аксонометрическая схема трубопроводов котельной — фронтальная изометрия (ГОСТ 2.317:
x вправо, y под 45° вправо-вверх, z вверх, коэффициенты 1), М 1:25. Проекция той же 3D-модели tm_model.

python3 sheets/tm_axo.py -> out/tm_axo.dxf + PDF
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
from tm_draw import (CODE_TM, BLD_TM, TM_LIST, TM_TOTAL, setup_layers, PP, View, Labels, draw_eq, eq_outline,  # noqa
                     sym_fit, PIPE_STYLE, unit, lev, f1, C45)
from tm_plans import PAIRS  # noqa: E402

OUT = os.path.join(ROOT, 'out')
SHEET_NO = 5
K = 25

AXO_LABELS = PAIRS + [
    (('Н3-П', 'Н3-О'), 'Т1, Т2 PE-Xa 32×4,4 → КШ-2 (Н3)'),
]


def build():
    TM.build()
    doc = new_doc()
    setup_layers(doc)
    sh = RDSheet(doc, 'Лист', TM_LIST[SHEET_NO], SHEET_NO, TM_TOTAL, fmt='А2', code=CODE_TM, bld=BLD_TM)
    p = PP(doc, sh.lay)
    # начало: угол помещения X0, Y0 на полу; u0 = X0 + Y0·c
    V = View('axo', K, (150.0, 95.0), (TM.X0 + TM.Y0 * C45, TM.Y0 * C45))
    L = Labels(p, (24.0, 66.0, 440.0, 398.0))
    E = {e.id: e for e in TM.EQUIP}
    # контур пола топочной и линия западной стены (выход магистралей в тамбур 1.7)
    fl = [V.P((x, y, 0)) for x, y in ((TM.X0, TM.Y0), (TM.X1, TM.Y0), (TM.X1, TM.Y1), (TM.X0, TM.Y1))]
    p.pl(fl, 'ТМ_оборуд_тонк', closed=True, ltype='ОВ_ШТРИХ')
    for z in (0.0, TM.H_SLAB):
        p.pl([V.P((TM.X0 - 0.20, TM.Y0, z)), V.P((TM.X0 - 0.20, TM.Y1, z))], 'ТМ_оборуд_тонк', ltype='ОВ_ШТРИХ')
    p.pl([V.P((TM.X0 - 0.20, TM.Y0, 0)), V.P((TM.X0 - 0.20, TM.Y0, TM.H_SLAB))], 'ТМ_оборуд_тонк', ltype='ОВ_ШТРИХ')
    p.pl([V.P((TM.X0 - 0.20, TM.Y1, 0)), V.P((TM.X0 - 0.20, TM.Y1, TM.H_SLAB))], 'ТМ_оборуд_тонк', ltype='ОВ_ШТРИХ')
    at = V.P((TM.X0 - 0.20, TM.Y0 + 0.30, 0.25))
    p.t(at[0] - 1.0, at[1], 'западная стена (тамбур 1.7)', 1.8, 'right', 'ТМ_размеры')
    # оборудование — контуром
    skip = ('ПК-горелка', 'БП-шнек', 'Трап', 'П1', 'П1-узел', 'КШ-3', 'Нейтр', 'ШУ')
    for e in TM.EQUIP:
        if e.id in skip or e.id.endswith('-мотор'):
            continue
        draw_eq(p, V, e, layer='ТМ_оборуд_тонк', mask=False)
    for e in (E['П1-узел'], E['КШ-3'], E['Нейтр']):
        draw_eq(p, V, e, layer='ТМ_ОВ', mask=False)
    # трубы и арматура
    for pp in TM.PIPES:
        lay, lt = PIPE_STYLE[pp.sys]
        for a, b in zip(pp.pts, pp.pts[1:]):
            A, B = V.P(a), V.P(b)
            if math.hypot(B[0] - A[0], B[1] - A[1]) < 0.05:
                continue
            if pp.sys == 'Д':
                w = pp.od * V.s / 2
                d = unit(A, B)
                n = (-d[1], d[0])
                p.pl([(A[0] + n[0] * w, A[1] + n[1] * w), (B[0] + n[0] * w, B[1] + n[1] * w)], lay)
                p.pl([(A[0] - n[0] * w, A[1] - n[1] * w), (B[0] - n[0] * w, B[1] - n[1] * w)], lay)
            else:
                p.pl([A, B], lay, ltype=lt, lw=50 if pp.sys in ('Т1', 'Т2', 'Т11', 'Т21') else 35)
    for f in TM.FITS:
        sym_fit(p, V, f, scale=0.9)
    # марки оборудования
    for e in TM.EQUIP:
        if e.id in skip or e.id.endswith('-мотор') or not e.pos and e.id not in ('Ecoflex',):
            continue
        bb = e.bbox()
        top = V.P(((bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, bb[5]))
        if e.id in [n for n, _ in TM.GROUPS]:
            fr = V.P((bb[0], bb[1], bb[2]))
            p.t(fr[0] + (bb[3] - bb[0]) * V.s / 2, fr[1] + 3.0, e.mark, 1.8, 'center', 'ТМ_марки')
            continue
        L.shelf(top, e.mark if e.id != 'Ecoflex' else 'ввод Ecoflex (баня)', 2.2)
    for e, t in ((E['П1-узел'], 'смесит. узел П1 (ОВ)'), (E['КШ-3'], 'КШ-3 (ОВ)'), (E['Нейтр'], 'нейтрализатор (ВК)')):
        bb = e.bbox()
        L.shelf(V.P(((bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, bb[5])), t, 1.8)
    # подписи труб с диаметрами и отметками
    P = {pp.id: pp for pp in TM.PIPES}
    done = set()
    for ids, txt in PAIRS:
        if ids[0] in done or ids[0] not in P:
            continue
        done.add(ids[0])
        best = None
        for a, b in zip(P[ids[0]].pts, P[ids[0]].pts[1:]):
            A, B = V.P(a), V.P(b)
            Lp = math.hypot(B[0] - A[0], B[1] - A[1])
            if Lp > 6.0 and (best is None or Lp > best[0]):
                best = (Lp, (a, b), A, B)
        if not best:
            continue
        Lp, (a, b), A, B = best
        sub = 'ось ' + lev(a[2]) if abs(a[2] - b[2]) < 1e-6 and ids[0] != 'Д-каскад' else None
        for t in (0.4, 0.6, 0.25, 0.75):
            q = (A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t)
            if L.shelf(q, txt, 1.8, sub=sub):
                break
    # концы — куда уходят трубы
    for pid, t in (('Н3-П', 'к КШ-2 (листы 3, 6 ОВ)'), ('Н4-П', 'к КШ-1 (листы 3, 6 ОВ)'), ('Н2-П', 'к КШ-4 (лист 6 ОВ)'),
                   ('Т3', 'Т3 — к сети ГВС (ВК)'), ('В1-Б1', 'В1 — от сети ВК'), ('Г', 'ввод газа (ГСВ)')):
        pp = P[pid]
        end = pp.pts[-1] if pid not in ('В1-Б1',) else pp.pts[0]
        L.shelf(V.P(end), t, 1.8)
    sh.title(300.0, 403.0, 'Аксонометрическая схема трубопроводов котельной (фронтальная изометрия). М 1:25', h=3.5)
    sh.notes(446, 340, 118, NOTES, h=2.0, spacing=1.0)
    return doc


NOTES = [
    'Схема — проекция 3D-модели котельной (фронтальная изометрия, все оси без сокращения). Отметки — оси труб от '
    'чистого пола ±0,000.',
    'Трубы котлового контура, ГС → РК, Н7, обвязка Б1, подпитка — сталь ВГП ГОСТ 3262-75; магистрали групп Н2–Н5 — '
    'PE-Xa с антидиффузионным слоем; Н6 — Ecoflex Quattro; конденсат — ПП Ø32.',
    'Горизонтальные участки — с уклоном не менее 0,002 к спускным кранам; в верхних точках — автоматические '
    'воздухоотводчики (показаны), в нижних — спускные краны.',
    'Газопровод — условно, по проекту ГСВ.',
    'Арматура насосных групп (краны, обратный клапан, термометры, смесительный клапан Н4) — в составе групп заводской '
    'сборки, на схеме не показана.',
]

if __name__ == '__main__':
    print(save_and_pdf(build(), os.path.join(OUT, 'tm_axo.dxf')))
