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
from ov_boiler_scheme import PDPlan, Sym, no_yo, prep_doc, groups_calc           # noqa: E402

OUT = os.path.join(ROOT, 'out')
RD = json.load(open(os.path.join(ROOT, '..', 'rd', 'rd_calc.json')))
DEV = {d['name']: d for d in RD['devices']}
UFH = {u['no']: u for u in RD['ufh']}
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
        t = f'вентил., L={int(round(d["L"], 2) * 1000)}' + (' (предл.)' if n == 'Кв-8' else '')
        rows.append(dict(out=f'В{i}', mark=n, room=d['room'], Q=round(d['Q']), type=t, L=d['lead'], G=d['G'],
                         kind='conv', note=''))
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
    cb = CIRC['Баня → КШ-Б (Ecoflex Quattro 32×2,9)']
    br = {b_['cab']: b_ for b_ in GR['Н4']['branches']}
    mix4 = MIX['КШ-4']
    cab1 = C1['cabs']

    # ============ КШ-4 (2 этаж): верх — прямой коллектор, низ — смесительный узел + ТП санузлов
    X4, Y4 = 30.0, 352.0
    cab_title(S, X4, 398, 'КШ-4 — шкаф коллекторный двухъярусный ≈750×1250×150',
              'в 2.6 у южной стены, низ шкафа +4,350; стояки Т1, Т2 — из угла тамбура 1.7')
    rows4 = [dev_row(n, f'В{i}') for i, n in enumerate(
        ['Р-1', 'Р-2', 'Р-3', 'Р-5', 'Кн-1', 'Кн-2', 'Кн-3', 'Пс-1', 'Пс-2'], 1)]
    yb, xb, yt = section(S, X4, Y4, rows4)
    g2 = GR['Н2']
    inlet(S, xb, yt, 30.0, [f'от РК, группа Н2 (лист 8)', f'PE-Xa {g2["pipe"]}, L≈{f(g2["L"], 1)} м',
                            f'{f(g2["Q"] / 1000, 1)} кВт, {f(g2["m3h"], 2)} м³/ч, 70/55 °С',
                            'стояк в 1.7: ±0,000 → +4,050'])
    ym = yb - 7
    xs = xb + 1.5
    S.pipe([(xs, yb), (xs, ym - 6)], 'Т1')
    S.three_way(xs, ym, True, 'r', act=False)
    S.text(xs + 3.6, ym + 1.6, f'термостатический смесительный клапан {RD["tv_group"]["КШ-4"]} °С', 1.45)
    S.pump(xs, ym - 6.0, 'd', 1.6)
    S.text(xs + 3.6, ym - 6.0, f'насос {mix4["pump"]}: {f(mix4["m3h"], 2)} м³/ч, {f(mix4["H_m"], 2)} м; '
           'термостат-ограничитель 55 °С', 1.45)
    xr = xb + 4.5
    S.pipe([(xr, yb), (xr, ym)], 'Т2')
    S.pipe([(xs + 1.5, ym), (xr, ym)], 'Т21')
    S.dot(xr, ym)
    yb2, xb2, yt2 = section(S, X4, ym - 12, ufh_rows(['2.8', '2.9']), 'Т11', 'Т21', head=False)
    S.pipe([(xs, ym - 7.6), (xs, yt2)], 'Т11')
    S.pipe([(xr, yt2), (xr, ym)], 'Т21')

    # ============ КШ-2 (1 этаж, тамбур 1.7): верх — прямой (Кв-1…8), низ — смесит. узел 36 °С + 9 петель ТП
    X2, Y2 = 168.0, 352.0
    g3 = GR['Н3']
    m2 = MIX['КШ-2']
    cab_title(S, X2, 398, f'КШ-2 — шкаф коллекторный двухъярусный ≈{cab1["КШ-2"]["W"]}×1300×150',
              'в тамбуре 1.7 у простенка, низ шкафа +0,300')
    yb, xb, yt = section(S, X2, Y2, kv_rows(C1))
    inlet(S, xb, yt, 30.0, ['от РК, группа Н3 (лист 8), 70/55 °С', f'PE-Xa {g3["pipe"]}, L≈{f(g3["L"], 0)} м',
                            f'{f(g3["Q_ksh2"] / 1000, 1)} кВт, {f(g3["G_ksh2"] / 1000, 2)} м³/ч '
                            f'(без Р-т)', 'Р-т — тройником на РК, см. ниже'])
    ym = yb - 7
    xs = xb + 1.5
    xr = xb + 4.5
    S.pipe([(xs, yb), (xs, ym - 6)], 'Т1')
    S.three_way(xs, ym, True, 'r', act=False)
    S.text(xs + 3.6, ym + 1.6, f'термостатический смесительный клапан {f(C1["loops"][0]["tv"] if False else 36.0, 0)} °С',
           1.45)
    S.pump(xs, ym - 6.0, 'd', 1.6)
    S.text(xs + 3.6, ym - 6.0, f'насос {m2["pump"]}: {f(m2["m3h"], 2)} м³/ч, {f(m2["H_m"], 2)} м; '
           'термостат-ограничитель 45 °С', 1.45)
    S.pipe([(xr, yb), (xr, ym)], 'Т2')
    S.pipe([(xs + 1.5, ym), (xr, ym)], 'Т21')
    S.dot(xr, ym)
    yb2, xb2, yt2 = section(S, X2, ym - 12, loop_rows(C1, 'КШ-2'), 'Т11', 'Т21', head=False)
    S.pipe([(xs, ym - 7.6), (xs, yt2)], 'Т11')
    S.pipe([(xr, yt2), (xr, ym)], 'Т21')

    # ============ КШ-1 (1 этаж, тамбур 1.7): ТП 6 петель, 48,5 °С от Н4
    X1, Y1 = 306.0, 352.0
    b1 = br['КШ-1']
    cab_title(S, X1, 398, f'КШ-1 — шкаф коллекторный ТП ≈{cab1["КШ-1"]["W"]}×650×120',
              'в тамбуре 1.7 у простенка, низ шкафа +0,300')
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

    # ============ Р-т, калорифер П1, баня — ответвления от РК
    yR = 292.0
    S.text(306, yR, 'Р-т — радиатор топочной 1.6 (тройником на группе Н3, РК)', 2.0)
    d = DEV['Р-т']
    S.pipe([(310, yR - 7), (330, yR - 7)], 'Т1')
    S.pipe([(330, yR - 11), (310, yR - 11)], 'Т2')
    S.ball(315, yR - 7, False)
    p.rect(330, yR - 12.5, 342, yR - 5.5, 'ОВ_приборы', hatch=('ANSI31', 40, 45, 1))
    S.balance(322, yR - 11, False)
    S.text(345, yR - 7, f'{d["sel"]["type"]}, L={int(d["sel"]["L"] * 1000)}, {d["Q"]} Вт', 1.5)
    S.text(345, yR - 10.5, f'G={f(d["G"], 0)} л/ч; термоклапан + запорно-балансировочный', 1.5)

    yP = 268.0
    S.text(306, yP, 'Калорифер П1 (группа Н5, смешение на РК)', 2.0)
    S.pipe([(310, yP - 7), (332, yP - 7)], 'Т1')
    S.pipe([(332, yP - 13), (310, yP - 13)], 'Т2')
    S.ball(315, yP - 7, False)
    S.ball(315, yP - 13, False)
    S.filt(322, yP - 7, False)
    p.rect(332, yP - 15, 340, yP - 5, 'ОВ_оборуд')
    p.line(332, yP - 15, 340, yP - 5, 'ОВ_оборуд')
    S.sensor(328, yP - 13, 'T', 'r')
    S.text(343, yP - 7, f'{f(cp1["Q"] / 1000, 1)} кВт, 70/50 °С, {f(cp1["m3h"], 2)} м³/ч', 1.5)
    S.text(343, yP - 10.5, f'PE-Xa {cp1["pipe"]}, L≈{f(cp1["L"], 1)} м; датчик обратки —', 1.5)
    S.text(343, yP - 13.8, 'защита от замерзания (автоматика П1)', 1.5)

    yB = 242.0
    S.text(306, yB, 'Баня: группа Н6 → Ecoflex Quattro → КШ-Б (листы 12, 13)', 2.0)
    S.pipe([(310, yB - 7), (336, yB - 7)], 'Т1')
    S.pipe([(336, yB - 12), (310, yB - 12)], 'Т2')
    p.rect(316, yB - 14, 330, yB - 5, 'ОВ_Т1', ltype='ОВ_ШТРИХ')
    S.text(323, yB - 3.3, 'Ecoflex', 1.4, 'center')
    p.rect(336, yB - 15, 346, yB - 4, 'ОВ_КШ', fill=2)
    S.text(341, yB - 9.5, 'КШ-Б', 1.5, 'center')
    S.text(349, yB - 6.5, f'2×PE-Xa 32×2,9 в изоляции, L≈{f(cb["L"], 0)} м', 1.5)
    S.text(349, yB - 9.8, f'{f(cb["Q"] / 1000, 1)} кВт, {f(cb["m3h"], 2)} м³/ч, H={f(cb["H_m"], 2)} м', 1.5)
    S.text(349, yB - 13.1, 'отопление, ТО-Д джакузи, Б2 (приоритет)', 1.5)

    # ============ таблица контуров (группы РК) и смесительных узлов шкафов
    rows = [['Группа РК', 'Q, кВт', 't, °С', 'G, м³/ч', 'Труба', 'L, м', 'H, м', 'Насос']]
    for n in ('Н2', 'Н3', 'Н4', 'Н5', 'Н6', 'Н7'):
        g = GR[n]
        rows.append([f'{n} → {g["dest"]}', f(g['Q'] / 1000, 1), g['t'], f(g['m3h'], 2), g['pipe'],
                     f(g['L'], 1), f(g['H_m'], 2), g['pump']])
    for c, m in (('КШ-2', MIX['КШ-2']), ('КШ-4', MIX['КШ-4'])):
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
           ('towel', 'Полотенцесушитель водяной'), ('ufh', 'Петля тёплого пола'),
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
        'Шкафы КШ-2, КШ-4 — двухъярусные (решение Заказчика); КШ-Б — лист 13.',
        'Кн-1 (спальня 2.7) — без вентилятора, Кн-3 и Кв-1…8 — с вентилятором 12 В (решение '
        'Заказчика); питание вентиляторов — раздел ЭОМ.',
        'Кв-8 (1.9, у витража лестницы) — предложение вместо Кн-2 (под витражом на 2 этаже нет пола), '
        'по согласованию с Заказчиком; выход В6 КШ-4 — резерв. Если Кн-2 вернут на В6, расход Н2 '
        f'— {f(c4["m3h"], 2)} м³/ч, Н3 уменьшается на расход Кв-8.',
        '* Мощность полотенцесушителя указана в паспортных условиях 75/65/20 °С.',
        'Петли 1 этажа — по листу 4 (температура поверхности пола 1.10, 1.11 не выше 26 °С, СП 60): '
        'КШ-1, КШ-3 — 48,5 °С от группы Н4, КШ-2 — свой смесительный узел 36 °С.',
        'Насосы групп — класс по расходу и напору с запасом 10 % (условная характеристика, уточнить '
        'по каталогу); напор — до самого нагруженного прибора/петли с учётом шкафа.',
    ], h=1.8, spacing=1.05)
    return doc


if __name__ == '__main__':
    doc = build()
    no_yo(doc)
    print(save_and_pdf(doc, os.path.join(OUT, 'ov_scheme.dxf')))
