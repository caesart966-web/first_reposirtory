"""И05.09.26-ОВ, лист 6. Схема системы отопления (коллекторная, от РК топочной до приборов и петель ТП). А2.

python3 sheets/ov_scheme.py  ->  out/ov_scheme.dxf + out/ov_scheme_Лист.pdf
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from rdbase import RDSheet, save_and_pdf, fmt_num, SHEET_LIST, SHEETS_TOTAL      # noqa: E402
from ov_boiler_scheme import PDPlan, Sym, no_yo, prep_doc, groups_calc, kgh, SITE_L  # noqa: E402

OUT = os.path.join(ROOT, 'out')
import ov_heat2 as H2                                                          # noqa: E402

RD = json.load(open(os.path.join(ROOT, '..', 'rd', 'rd_calc.json')))
DEV = H2.DEV            # приборы 2 этажа по листу 5 (Пс-1, Пс-2 — от ГВС, к КШ-4 не подключаются)
UFH = H2.UFH            # ТП 2.8, 2.9 по листу 5: подача 42 °С, пол не выше 31 °С
BATH = json.load(open(os.path.join(ROOT, 'out', 'ov_bath_calc.json')))     # лист 12 (ov_bath.py)
CIRC = {c['name']: c for c in RD['circuits']}
UL = {c['name']: c for c in RD['ufh_lines']}
SHEET_NO = 6
ROW = 6.5           # шаг строк выходов, мм


def f(v, d=1):
    return fmt_num(v, d)


# ---------------------------------------------------------------- строки выходов
def dev_row(n, out):
    if n == 'Кн-2':
        return dict(out=out, mark='резерв', room='—', Q='—', type='(Кн-2 → Кв-8, прим. 6)', L=None, G=None,
                    kind='none', note='')
    d = DEV[n]
    s = d['sel']
    if n.startswith('Р'):
        t, kind = f'рад. {s["type"]}, L={int(s["L"] * 1000)}', 'rad'
    elif n.startswith('Кв'):
        t, kind = f'вентил., L={int(round(s["L"], 2) * 1000)}', 'conv'
    elif n.startswith('Кн'):
        t, kind = f'{"естеств." if n == "Кн-1" else "вентил."}, L={int(round(s["L"], 2) * 1000)}', 'conv'
    else:
        t, kind = f'п/суш. ≥{s["Qn_need"]} Вт*', 'towel'
    note = ''
    if n == 'Кн-2':
        t += ' (прим. 6)'
    return dict(out=out, mark=n, room=d['room'], Q=d['Q'], type=t, L=d['lead'], G=d['G'], kind=kind, note=note)


def ufh_rows(rooms, start=1):
    """Петли по данным rd_calc (КШ-4: санузлы 2 этажа)."""
    rows, k = [], start
    for no in rooms:
        u = UFH[no]
        for i in range(u['n_loops']):
            rows.append(dict(out=f'ТП{k}', mark=f'ТП {no}' + (f'.{i + 1}' if u['n_loops'] > 1 else ''), room=no,
                             Q=round(u['Q_ufh'] / u['n_loops']), type=f'шаг {u["T_mm"]}, {f(u["A_loops"] / u["n_loops"], 1)} м²',
                             L=u['L_loop'], G=u['G_loop'], kind='ufh', note=''))
            k += 1
    return rows


def loop_rows(C1, cab):
    """Петли 1 этажа по пересчёту листов 3–4 (calc1 из ov_heat1.py)."""
    ls = sorted([lp for lp in C1['loops'] if lp['cab'] == cab], key=lambda l: l['out'])
    return [dict(out=f'ТП{lp["out"]}', mark=f'ТП {lp["id"]}', room=lp['no'], Q=round(lp['Q']),
                 type=f'шаг {lp["T"]}, {f(lp["A"], 1)} м²', L=lp['L'], G=lp['G'], kind='ufh', note='')
            for lp in ls]


def kv_rows(C1):
    rows = []
    for i in range(1, 9):
        n = f'Кв-{i}'
        d = C1['dev'][n]
        t = f'вентил., L={int(round(d["L"], 2) * 1000)}'
        rows.append(dict(out=f'В{i}', mark=n, room=d['room'], Q=round(d['Q']), type=t, L=d['lead'], G=d['G'],
                         kind='conv', note=''))
    return rows


def bath_dev_rows():
    """КШ-Б1 (прямой): порядок выходов — как на листе 13."""
    rows = []
    for i, n in enumerate(['Р-б1', 'Р-б2', 'Кв-б1', 'Кв-б2', 'Кв-б3'], 1):
        d = BATH['devices'][n]
        txt = d['txt']
        if n.startswith('Р'):
            t, kind = 'рад. ' + txt.split('радиатор ')[1], 'rad'
        elif n.startswith('Кв'):
            t, kind = 'вентил., ' + txt.split(', ')[-1], 'conv'
        else:
            t, kind = 'п/суш. ' + txt.split(', ')[1].split(' (')[0] + '*', 'towel'
        rows.append(dict(out=f'В{i}', mark=n, room=d['room'], Q=d['Q'], type=t, L=d['lead'], G=d['G'], kind=kind,
                         note=''))
    return rows


def bath_loop_rows():
    """КШ-Б2 (ТП): порядок выходов — как на листе 13."""
    rows = []
    for i, k in enumerate(['б7-1', 'б7-2', 'б6-1', 'б6-2', 'б2', 'б3', 'б4'], 1):
        lp = BATH['loops'][k]
        rows.append(dict(out=f'ТП{i}', mark=f'ТП {k}', room=lp['room'], Q=lp['Q'],
                         type=f'шаг {lp["T_mm"]}, {f(lp["A"], 1)} м²', L=lp['L'], G=lp['G'], kind='ufh', note=''))
    return rows


# ---------------------------------------------------------------- шкаф: секция «коллектор + строки»
COLS = [('Вых.', 0, 7), ('Прибор/петля', 7, 17), ('Пом.', 24, 8), ('Q, Вт', 32, 9), ('Тип', 41, 31),
        ('L, м', 72, 8), ('G, л/ч', 80, 9), ('л/мин', 89, 9)]
TXT_W = 98


def section(S, x, ytop, rows, sysS='Т1', sysR='Т2', head=True):
    """Коллектор (двухкамерный блок) и строки выходов вправо. Возвращает (y низа, x блока, y верха блока)."""
    p = S.p
    xb, wb = x, 6.0
    xv, xd, xt = x + wb + 14, x + wb + 18, x + wb + 31
    yy = ytop
    if head:
        for name, dx, w in COLS:
            S.text(xt + dx + w / 2, yy, name, 1.55, 'center')
        p.line(xt, yy - 2.0, xt + TXT_W, yy - 2.0, 'ОВ_текст')
        yy -= 5.0
    y0 = yy + 2.5
    for r in rows:
        ys, yr = yy + 1.1, yy - 1.1
        S.pipe([(xb + wb, ys), (xd, ys)], sysS)
        S.pipe([(xd, yr), (xb + wb, yr)], sysR)
        # расходомер на подаче, термоклапан под сервопривод на обратке
        p.rect(xb + wb + 3.0, ys - 0.75, xb + wb + 6.0, ys + 0.75, 'ОВ_арматура')
        p.poly([(xv, yr), (xv - 1.0, yr + 0.7), (xv - 1.0, yr - 0.7)], 'ОВ_арматура')
        p.poly([(xv, yr), (xv + 1.0, yr + 0.7), (xv + 1.0, yr - 0.7)], 'ОВ_арматура')
        p.rect(xv - 0.5, yr - 1.9, xv + 0.5, yr - 0.9, 'ОВ_арматура', fill=7)
        # прибор
        k = r['kind']
        if k == 'none':
            pass
        elif k == 'rad':
            p.rect(xd, yy - 1.5, xd + 10, yy + 1.5, 'ОВ_приборы', hatch=('ANSI31', 40, 45, 1))
        elif k == 'conv':
            p.rect(xd, yy - 1.2, xd + 10, yy + 1.2, 'ОВ_приборы', fill=1)
        elif k == 'towel':
            p.rect(xd, yy - 1.5, xd + 10, yy + 1.5, 'ОВ_приборы')
            for i in range(1, 5):
                p.line(xd + i * 2, yy - 1.5, xd + i * 2, yy + 1.5, 'ОВ_приборы')
        else:
            pts = [(xd, yy + 1.1)]
            for i in range(5):
                xx = xd + 1 + i * 2
                pts += [(xx, yy + 1.4), (xx, yy - 1.4)] if i % 2 == 0 else [(xx, yy - 1.4), (xx, yy + 1.4)]
            pts += [(xd + 10, yy - 1.1)]
            p.pl(pts, 'ОВ_ТП', lw=25)
        if r['G'] is None:
            vals = [r['out'], r['mark'], r['room'], '—', r['type'], '—', '—', '—']
        else:
            vals = [r['out'], r['mark'], r['room'], f'{r["Q"]}', r['type'], f(r['L'], 1), f(r['G'], 0),
                    f(r['G'] / 60, 2)]
        for (name, dx, w), v in zip(COLS, vals):
            al = 'left' if name in ('Тип', 'Прибор/петля') else 'center'
            S.text(xt + dx + (0.6 if al == 'left' else w / 2), yy, v, 1.55, al)
        if r['note']:
            S.text(xt + TXT_W + 1.0, yy, r['note'], 1.35, 'left')
        yy -= ROW
    y1 = yy + ROW - 2.5
    # блок коллектора
    p.rect(xb, y1, xb + wb / 2, y0, 'ОВ_Т11' if sysS == 'Т11' else 'ОВ_Т1', lw=35)
    p.rect(xb + wb / 2, y1, xb + wb, y0, 'ОВ_Т21' if sysR == 'Т21' else 'ОВ_Т2', lw=35)
    S.airvent(xb + 1.5, y0)
    S.airvent(xb + 4.5, y0) if False else None
    S.drain(xb + 1.5, y1)
    return yy + ROW - 2.5, xb, y0


def inlet(S, xb, ytop_block, length, text_lines, sysS='Т1', sysR='Т2', filt=True):
    """Ввод в коллектор сверху: подача в левую камеру, обратка из правой; краны, фильтр, стрелки."""
    xs, xr = xb + 1.5, xb + 4.5
    ya = ytop_block + length
    S.pipe([(xs, ytop_block), (xs, ya)], sysS)
    S.pipe([(xr, ytop_block), (xr, ya)], sysR)
    S.ball(xs, ytop_block + 3.5, True)
    S.ball(xr, ytop_block + 3.5, True)
    if filt:
        S.filt(xs, ytop_block + 8.0, True)
    S.arrow(xs, ytop_block + 1.2, 'd', 'ОВ_арматура', 1.4)
    S.arrow(xr, ya + 0.8, 'u', 'ОВ_арматура', 1.4)
    for i, t in enumerate(text_lines):
        S.text(xr + 3.0, ya - 1.5 - i * 3.0, t, 1.5 if i else 1.7, 'left')


def cab_title(S, x, y, t1, t2=None):
    S.text(x, y, t1, 2.2, 'left')
    if t2:
        S.text(x, y - 3.4, t2, 1.6, 'left')


# ---------------------------------------------------------------- лист
def build():
    doc = prep_doc()
    sh = RDSheet(doc, 'Лист', SHEET_LIST[SHEET_NO], SHEET_NO, SHEETS_TOTAL, fmt='А2')
    p = PDPlan(doc, sh.lay)
    S = Sym(p)
    sh.title(300, 412, 'Схема системы отопления (от распределительного коллектора топочной до приборов)')

    GC = groups_calc()
    GR, C1, MIX = GC['groups'], GC['C1'], GC['mix']
    c4 = CIRC['Радиаторы и Кн 2 эт. → КШ-4 (70/55)']
    cp1 = CIRC['Калорифер П1 (70/50, смесительный узел)']
    g6 = GR['Н6']                                  # баня: нагрузка — из расчёта листа 12
    br = {b_['cab']: b_ for b_ in GR['Н4']['branches']}
    mix4 = MIX['КШ-4']
    cab1 = C1['cabs']

    # ============ КШ-4 (2 этаж): верх — прямой коллектор, низ — смесительный узел + ТП санузлов
    X4, Y4 = 30.0, 352.0
    cab_title(S, X4, 398, 'КШ-4 — шкаф коллекторный двухъярусный ≈750×1250×150',
              'в 2.6 у южной стены, низ шкафа +4,350; стояки Т1, Т2 — из угла тамбура 1.7')
    rows4 = [dev_row(n, f'В{i}') for i, n in enumerate(
        H2.K4_ORDER, 1)]
    yb, xb, yt = section(S, X4, Y4, rows4)
    g2 = GR['Н2']
    inlet(S, xb, yt, 30.0, [f'от РК, группа Н2 (лист 8)', f'PE-Xa {g2["pipe"]}, L≈{f(g2["L"], 1)} м',
                            f'{f(g2["Q"] / 1000, 1)} кВт, {f(g2["m3h"], 2)} м³/ч, 70/55 °С',
                            'стояк в 1.7: ±0,000 → +4,050'])
    ym = yb - 7
    xs = xb + 1.5
    S.pipe([(xs, yb), (xs, ym - 6)], 'Т1')
    S.three_way(xs, ym, True, 'r', act=False)
    S.text(xs + 4.6, ym + 1.6, f'термостатический смесительный клапан {f(mix4["t"], 1)} °С', 1.45)
    S.pump(xs, ym - 6.0, 'd', 1.6)
    S.text(xs + 4.6, ym - 6.0, f'насос {mix4["pump"]}: {f(mix4["m3h"], 2)} м³/ч, {f(mix4["H_m"], 2)} м; '
           'термостат-ограничитель 55 °С', 1.45)
    xr = xb + 4.5
    S.pipe([(xr, yb), (xr, ym)], 'Т2')
    S.pipe([(xs + 1.5, ym), (xr, ym)], 'Т21')
    S.dot(xr, ym)
    yb2, xb2, yt2 = section(S, X4, ym - 12, ufh_rows(['2.8', '2.9']), 'Т11', 'Т21', head=False)
    S.pipe([(xs, ym - 7.6), (xs, yt2)], 'Т11')
    S.pipe([(xr, yt2), (xr, ym)], 'Т21')

    # ============ КШ-2 (1 этаж, тамбур 1.7): верх — прямой (Кв-1…8), низ — смесит. узел 36 °С + петли ТП (10 с 20.10.2026)
    X2, Y2 = 168.0, 352.0
    g3 = GR['Н3']
    m2 = MIX['КШ-2']
    cab_title(S, X2, 398, f'КШ-2 — шкаф коллекторный двухъярусный ≈{cab1["КШ-2"]["W"]}×1300×150',
              'встроен в простенок тамбура 1.7 (стена 1.7/1.8, западнее двери), низ ниши ±0,000')
    yb, xb, yt = section(S, X2, Y2, kv_rows(C1))
    inlet(S, xb, yt, 30.0, ['от РК, группа Н3 (лист 8), 70/55 °С', f'PE-Xa {g3["pipe"]}, L≈{f(g3["L"], 0)} м',
                            f'{f(g3["Q_ksh2"] / 1000, 1)} кВт, {f(g3["G_ksh2"] / 1000, 2)} м³/ч'])
    ym = yb - 7
    xs = xb + 1.5
    xr = xb + 4.5
    S.pipe([(xs, yb), (xs, ym - 6)], 'Т1')
    S.three_way(xs, ym, True, 'r', act=False)
    S.text(xs + 4.6, ym + 1.6, f'термостатический смесительный клапан {f(C1["loops"][0]["tv"] if False else 36.0, 0)} °С',
           1.45)
    S.pump(xs, ym - 6.0, 'd', 1.6)
    S.text(xs + 4.6, ym - 6.0, f'насос {m2["pump"]}: {f(m2["m3h"], 2)} м³/ч, {f(m2["H_m"], 2)} м; '
           'термостат-ограничитель 45 °С; узел — на КШ-2 и КШ-5', 1.45)
    S.pipe([(xr, yb), (xr, ym)], 'Т2')
    S.pipe([(xs + 1.5, ym), (xr, ym)], 'Т21')
    S.dot(xr, ym)
    yb2, xb2, yt2 = section(S, X2, ym - 12, loop_rows(C1, 'КШ-2'), 'Т11', 'Т21', head=False)
    S.pipe([(xs, ym - 7.6), (xs, yt2)], 'Т11')
    S.pipe([(xr, yt2), (xr, ym)], 'Т21')
    # ---- КШ-5 (тамбур 1.7, восточнее двери в 1.8): коллектор ТП от того же смесительного узла — транзитом
    # из нижних торцов коллектора КШ-2 (решение Заказчицы 20.10.2026, 21:32)
    k5, tr5 = cab1['КШ-5'], cab1['КШ-5']['transit']
    yb5, xb5, yt5 = section(S, X2, yb2 - 24, loop_rows(C1, 'КШ-5'), 'Т11', 'Т21', head=False)
    inlet(S, xb5, yt5, yb2 - yt5, [f'транзит от смесит. узла КШ-2, 36 °С: PE-Xa {tr5["pipe"]}, '
                                   f'L≈{f(tr5["L"], 1)} м — в полу 1.7',
                                   f'{f(k5["Q_tp"] / 1000, 1)} кВт, {f(k5["G_tp"] / 1000, 2)} м³/ч'],
          'Т11', 'Т21', filt=False)
    cab_title(S, xb5 + 30, yb2 - 11.5, f'КШ-5 — шкаф коллекторный ТП ≈{k5["W"]}×1300×150 (как КШ-1, КШ-2)',
              'встроен в простенок тамбура 1.7 (стена 1.7/1.8, восточнее двери), низ ниши ±0,000')

    # ============ КШ-1 (1 этаж, тамбур 1.7): ТП 6 петель, 48,5 °С от Н4
    X1, Y1 = 306.0, 352.0
    b1 = br['КШ-1']
    cab_title(S, X1, 398, f'КШ-1 — шкаф коллекторный ТП ≈{cab1["КШ-1"]["W"]}×1300×150 (как КШ-2, КШ-5)',
              'встроен в простенок тамбура 1.7 (стена 1.7/гараж), низ ниши ±0,000')
    yb, xb, yt = section(S, X1, Y1, loop_rows(C1, 'КШ-1'), 'Т11', 'Т21')
    inlet(S, xb, yt, 30.0, ['от РК, группа Н4: ТП 48,5 °С', f'PE-Xa {b1["pipe"]}, L≈{f(b1["L"], 0)} м',
                            f'{f(b1["Q"] / 1000, 1)} кВт, {f(b1["G"] / 1000, 2)} м³/ч'], 'Т11', 'Т21')
    y1_bottom = yb

    # ============ КШ-3 (топочная): ТП 1.6 и гараж 1.5
    X3, Y3 = 446.0, 352.0
    b3 = br['КШ-3']
    cab_title(S, X3, 398, f'КШ-3 — шкаф коллекторный ТП ≈{cab1["КШ-3"]["W"]}×650×120',
              'в топочной 1.6 на южной стене, низ шкафа +0,300')
    yb, xb, yt = section(S, X3, Y3, loop_rows(C1, 'КШ-3'), 'Т11', 'Т21')
    inlet(S, xb, yt, 30.0, ['от РК, группа Н4: ТП 48,5 °С', f'PE-Xa {b3["pipe"]}, L≈{f(b3["L"], 0)} м',
                            f'{f(b3["Q"] / 1000, 1)} кВт, {f(b3["G"] / 1000, 2)} м³/ч',
                            'гараж 1.5 — дежурный +10 °С'], 'Т11', 'Т21')

    # ============ топочная 1.6 (без прибора), калорифер П1, баня — ответвления от РК
    yR = 292.0
    brh = RD['boiler_room_heat']
    S.text(306, yR, 'Топочная 1.6 — без отопительного прибора (решение Заказчицы 20.10.2026)', 2.0)
    S.text(306, yR - 5, f'ТП 3 петли (КШ-3) — {f(brh["Q_ufh"] / 1000, 1)} кВт; трубы в топочной без изоляции '
                        f'≈{f(brh["Q_pipes"] / 1000, 1)} кВт,', 1.5)
    S.text(306, yR - 8.5, f'котлы, баки, насосы ≈{f(brh["Q_equip"] / 1000, 1)} кВт; при -25 °С без пеллетного котла '
                          f'≈+{f(brh["t_min"], 0)} °С (лист 7)', 1.5)

    yP = 268.0
    g5 = GR['Н5']
    S.text(306, yP, 'Калорифер П1 — Turkov Zenit 750 Heco W (отвод Н5 от РК)', 2.0)
    S.pipe([(310, yP - 7), (334, yP - 7)], 'Т1')
    S.pipe([(334, yP - 13), (310, yP - 13)], 'Т2')
    S.ball(314, yP - 7, False)
    S.ball(314, yP - 13, False)
    # смесительный узел и автоматика — в комплекте установки (штрихом)
    p.rect(318, yP - 16.5, 341.5, yP - 3.5, 'ОВ_оборуд', ltype='ОВ_ШТРИХ')
    S.three_way(322, yP - 7, False, 'd', act=False)
    S.pipe([(322, yP - 8.5), (322, yP - 13)], 'Т2')
    S.dot(322, yP - 13)
    S.pump(328, yP - 7, 'r', 1.5)
    p.rect(334, yP - 15, 340, yP - 5, 'ОВ_оборуд')
    p.line(334, yP - 15, 340, yP - 5, 'ОВ_оборуд')
    S.text(329.75, yP - 2.2, 'в комплекте П1', 1.3, 'center')
    S.text(344, yP - 7, f'{f(g5["Q"] / 1000, 1)} кВт, 70/50 °С, {f(g5["m3h"], 2)} м³/ч', 1.5)
    S.text(344, yP - 10.5, f'PE-Xa {g5["pipe"]}, L≈{f(g5["L"], 1)} м; насос, 3-ход. клапан', 1.5)
    S.text(344, yP - 13.8, 'и защита от замерзания — Turkov', 1.5)

    # ============ баня: группа Н6 → Ecoflex → ввод (УК1 — Б2, УК2 — ТО-Д) → КШ-Б1 → КШ-Б2 (как на листе 13)
    S.text(306, 246.5, 'Баня: группа Н6 → Ecoflex Quattro → КШ-Б1, КШ-Б2', 2.0)
    S.text(306, 242.8, 'шкафы ШРВ-3 встроены в восточную стену с/у б3 (листы 12, 13)', 1.5)
    yS, yR = 222.0, 214.0
    XB = 446.0                                   # КШ-Б1, КШ-Б2 — под таблицей групп
    xs_b, xr_b = XB + 1.5, XB + 4.5
    yhead = 206.0
    gap = 1.2                                    # разрыв обратки на пересечении с подачей (ГОСТ 21.206)
    S.pipe([(307, yS), (xs_b, yS), (xs_b, yhead - 2.5)], 'Т1')
    S.pipe([(xr_b, yhead - 2.5), (xr_b, yR), (xs_b + gap, yR)], 'Т2')
    S.pipe([(xs_b - gap, yR), (307, yR)], 'Т2')
    p.rect(309, yR - 3.0, 321, yS + 3.0, 'ОВ_Т1', ltype='ОВ_ШТРИХ')
    S.text(315, yS + 4.6, 'Ecoflex', 1.4, 'center')
    S.ball(325, yS, False)
    S.ball(325, yR, False)
    S.filt(330, yS, False)
    S.arrow(308.5, yS, 'r', 'ОВ_арматура', 1.4)
    S.arrow(308.5, yR, 'l', 'ОВ_арматура', 1.4)
    # УК1 — трёхходовой переключающий: приоритет загрузки Б2
    xk1 = 340.0
    S.three_way(xk1, yS, False, 'u', act=True)
    S.text(xk1 + 2.0, yS - 2.2, 'УК1', 1.5)
    S.pipe([(xk1, yS + 1.5), (xk1, 227.0)], 'Т1')
    p.rect(335.0, 227.0, 349.0, 236.5, 'ОВ_оборуд')
    for i in range(4):
        yy_ = 228.6 + i * 1.9
        p.line(337.0, yy_, 345.0, yy_ + 1.0, 'ОВ_оборуд')
    S.text(342.0, 238.2, 'Б2', 1.5, 'center')
    S.pipe([(347.0, 227.0), (347.0, yS + gap)], 'Т2')
    S.pipe([(347.0, yS - gap), (347.0, yR)], 'Т2')
    S.dot(347.0, yR)
    b2 = BATH['b2']
    S.text(351.0, 233.6, f'Б2 — бойлер 200 л, змеевик {b2["Q"] // 1000} кВт', 1.45)
    S.text(351.0, 230.3, f'G={b2["G"]} кг/ч, {b2["pipe"]}', 1.45)
    # УК2 — зональный клапан ТО-Д джакузи
    xk2 = 394.0
    tod = BATH['tod']
    S.dot(xk2, yS)
    S.pipe([(xk2, yS), (xk2, 227.0)], 'Т1')
    S.motor(xk2, 224.6, True)
    S.text(xk2 - 1.6, 224.6, 'УК2', 1.5, 'right')
    p.rect(389.0, 227.0, 403.0, 236.5, 'ОВ_оборуд')
    p.line(389.0, 227.0, 403.0, 236.5, 'ОВ_оборуд')
    S.text(396.0, 238.2, 'ТО-Д', 1.5, 'center')
    S.pipe([(401.0, 227.0), (401.0, yS + gap)], 'Т2')
    S.pipe([(401.0, yS - gap), (401.0, yR)], 'Т2')
    S.dot(401.0, yR)
    S.text(405.0, 233.6, f'ТО-Д джакузи {tod["Q"] // 1000} кВт', 1.45)
    S.text(405.0, 230.3, f'G={tod["G"]} кг/ч, {tod["pipe"]}', 1.45)
    for i, t_ in enumerate([
            f'от РК, группа Н6 (лист 8): Т1, Т2 PE-Xa 32×2,9 в общей оболочке Ecoflex Quattro;',
            f'L≈{f(SITE_L, 1)} м по трассе (в гидравлике принято {f(g6["L"], 0)} м); {f(g6["Q"] / 1000, 1)} кВт, '
            f'{f(g6["m3h"], 2)} м³/ч, H={f(g6["H_m"], 2)} м:',
            f'отопление бани {f(BATH["Q_heat"] / 1000, 1)} кВт + ТО-Д {tod["Q"] // 1000} кВт; Б2 {b2["Q"] // 1000} кВт '
            '— с приоритетом (на время загрузки',
            'отопление и ТО-Д не работают). УК1 — по датчику бойлера, УК2 — по таймеру СПА.']):
        S.text(307, 208.0 - i * 3.3, t_, 1.45)

    # КШ-Б1 — прямой коллектор 7 выходов; КШ-Б2 — смесительный узел 44 °С и 7 петель ТП
    cab_title(S, XB + 9.0, 217.5, 'КШ-Б1 — ШРВ-3 (≈750 мм), прямой коллектор',
              'выходы — как на листе 13; Пс-б1.1, Пс-б1.2, Пс-б2 — от ГВС (ВК)')
    yb, xb, yt = section(S, XB, yhead, bath_dev_rows())
    mb = MIX['КШ-Б2']
    ym = yb - 7
    S.pipe([(xs_b, yb), (xs_b, ym - 6)], 'Т1')
    S.three_way(xs_b, ym, True, 'r', act=False)
    S.text(xs_b + 4.6, ym + 1.6, f'КШ-Б2 — ШРВ-3 (≈750 мм): термостатический смесительный клапан {f(mb["t"], 1)} °С',
           1.45)
    S.pump(xs_b, ym - 6.0, 'd', 1.6)
    S.text(xs_b + 4.6, ym - 6.0, f'насос {mb["pump"]}: {f(mb["m3h"], 2)} м³/ч, {f(mb["H_m"], 2)} м; '
           'термостат-ограничитель 55 °С', 1.45)
    S.pipe([(xr_b, yb), (xr_b, ym)], 'Т2')
    S.pipe([(xs_b + 1.5, ym), (xr_b, ym)], 'Т21')
    S.dot(xr_b, ym)
    yb2, xb2, yt2 = section(S, XB, ym - 12, bath_loop_rows(), 'Т11', 'Т21', head=False)
    S.pipe([(xs_b, ym - 7.6), (xs_b, yt2)], 'Т11')
    S.pipe([(xr_b, yt2), (xr_b, ym)], 'Т21')
    S.text(XB + 9.0, yb2 - 4.0, f'Итого баня: приборы {f(BATH["Q_direct"] / 1000, 1)} кВт + ТП {f(BATH["Q_ufh"] / 1000, 1)} кВт '
           f'= {f(BATH["Q_heat"] / 1000, 1)} кВт (расчёт — лист 12)', 1.5)

    # ============ таблица контуров (группы РК) и смесительных узлов шкафов
    rows = [['Группа РК', 'Q, кВт', 't, °С', 'G, м³/ч', 'Труба', 'L, м', 'H, м', 'Насос']]
    for n in ('Н2', 'Н3', 'Н4', 'Н5', 'Н6', 'Н7'):
        g = GR[n]
        rows.append([f'{n} → {g["dest"]}', f(g['Q'] / 1000, 1), g['t'], f(g['m3h'], 2), g['pipe'],
                     f(g['L'], 1), f(g['H_m'], 2), g['pump']])
    for c in ('КШ-2', 'КШ-4', 'КШ-Б2'):
        m = MIX[c]
        rows.append([f'смесит. узел {c} ({f(m["t"], 1)} °С)', f(m['Q'] / 1000, 1), f(m['t'], 1), f(m['m3h'], 2),
                     '—', '—', f(m['H_m'], 2), m['pump']])
    widths = [39, 10, 13, 11, 26, 9, 10, 11]
    TXX, yt_tab = 446.0, 300.0
    sh.table(TXX, yt_tab, widths, rows, row_h=5.2, head_h=6.0, h=1.55,
             aligns=['left', 'center', 'center', 'center', 'left', 'center', 'center', 'center'])
    S.text(TXX + sum(widths) / 2, yt_tab + 3.0, 'Группы РК и смесительные узлы', 2.2, 'center')

    # ============ условные обозначения и примечания
    from ov_boiler_scheme import legend3
    yl = legend3(S, 26, 120, cols=2, colw=88)
    # знаки приборов
    xx, yy = 206, 114.5
    S.text(xx + 40, 120, 'Приборы и арматура коллекторов', 2.2, 'center')
    sym = [('rad', 'Радиатор стальной панельный'), ('conv', 'Конвектор внутрипольный'),
           ('ufh', 'Петля тёплого пола'),
           ('fm', 'Расходомер с настройкой (подача)'), ('tv', 'Термоклапан под сервопривод (обратка)'),
           ('cab', 'Коллекторный шкаф')]
    for i, (k, cap) in enumerate(sym):
        y = yy - i * 4.6
        if k == 'rad':
            p.rect(xx, y - 1.4, xx + 9, y + 1.4, 'ОВ_приборы', hatch=('ANSI31', 40, 45, 1))
        elif k == 'conv':
            p.rect(xx, y - 1.1, xx + 9, y + 1.1, 'ОВ_приборы', fill=1)
        elif k == 'towel':
            p.rect(xx, y - 1.4, xx + 9, y + 1.4, 'ОВ_приборы')
            for j in range(1, 4):
                p.line(xx + j * 2.25, y - 1.4, xx + j * 2.25, y + 1.4, 'ОВ_приборы')
        elif k == 'ufh':
            pts = [(xx, y)]
            for j in range(4):
                x2 = xx + 1.5 + j * 2
                pts += [(x2, y + 1.3), (x2, y - 1.3)] if j % 2 == 0 else [(x2, y - 1.3), (x2, y + 1.3)]
            pts.append((xx + 9, y))
            p.pl(pts, 'ОВ_ТП', lw=25)
        elif k == 'fm':
            p.line(xx, y, xx + 9, y, 'ОВ_Т1')
            p.rect(xx + 3, y - 0.75, xx + 6, y + 0.75, 'ОВ_арматура')
        elif k == 'tv':
            p.line(xx, y, xx + 9, y, 'ОВ_Т2')
            p.poly([(xx + 4.5, y), (xx + 3.5, y + 0.7), (xx + 3.5, y - 0.7)], 'ОВ_арматура')
            p.poly([(xx + 4.5, y), (xx + 5.5, y + 0.7), (xx + 5.5, y - 0.7)], 'ОВ_арматура')
            p.rect(xx + 4.0, y - 1.9, xx + 5.0, y - 0.9, 'ОВ_арматура', fill=7)
        else:
            p.rect(xx + 1, y - 1.5, xx + 4, y + 1.5, 'ОВ_Т1')
            p.rect(xx + 4, y - 1.5, xx + 7, y + 1.5, 'ОВ_Т2')
        S.text(xx + 12, y, cap, 1.6)

    sh.notes(292, 120, 108, [
        'Схема принципиальная, без масштаба. Нумерация выходов и марки приборов — как на планах '
        '(листы 3–5); петли тёплого пола — лист 4.',
        'Подводки к приборам и петли — PE-Xa 16×2,0 с антидиффузионным слоем; соединения — только '
        'на коллекторах (евроконус 3/4"). Магистрали до шкафов — по таблице.',
        'Настройка расходомеров — по графе «л/мин»; точные значения — по паспортам приборов при '
        'заказе. Термоклапаны — под сервоприводы комнатного регулирования (автоматика «Люкс»).',
        'Шкафы КШ-2, КШ-4 — двухъярусные (решение Заказчика); КШ-1, КШ-2, КШ-5 — одного размера, встроены '
        'в простенки тамбура 1.7 (решение Заказчицы 20.10.2026); КШ-Б1, КШ-Б2 — встроенные ШРВ-3 в восточной '
        'стене с/у б3, ввод с УК1 (Б2) и УК2 (ТО-Д) — лист 13.',
        'Кн-1 (спальня 2.7) — КЗТО «Бриз», без вентилятора; Кн-3 и Кв-1…8 — КЗТО «Бриз В» с вентилятором 24 В '
        'постоянного тока (решение Заказчика); питание вентиляторов — раздел ЭОМ.',
        'Кв-8 (1.9, у витража лестницы на 1 этаже) — вместо Кн-2 по ЭП: под витражом на 2 этаже нет пола '
        '(решение Заказчика). Выход В6 КШ-4 — резерв.',
        'Температура поверхности пола — по СП 60. Петли 1 этажа (лист 4): КШ-1, КШ-3 — 48,5 °С от группы Н4, '
        f'КШ-2 — свой узел 36 °С, КШ-5 — от того же узла транзитом. Санузлы 2.8, 2.9 (лист 5): КШ-4 — '
        f'{f(MIX["КШ-4"]["t"], 1)} °С, недостающее '
        f'тепло — Пс-1, Пс-2 (2.8, 2.9) — от циркуляции ГВС, раздел ВК. Баня (лист 12): КШ-Б2 — '
        f'{f(MIX["КШ-Б2"]["t"], 1)} °С.',
        'Насосы групп — класс по расходу и напору с запасом 10 % (условная характеристика, уточнить '
        'по каталогу); напор — до самого нагруженного прибора/петли с учётом шкафа.',
    ], h=1.8, spacing=1.05)
    return doc


if __name__ == '__main__':
    doc = build()
    no_yo(doc)
    print(save_and_pdf(doc, os.path.join(OUT, 'ov_scheme.dxf')))
