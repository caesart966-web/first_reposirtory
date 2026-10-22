"""И05.09.26-ОВ. Лист 4 «План 1 этажа. Раскладка тёплого пола».

Расчёт — calc1() из ov_heat1.py (общий с листом 3).
python3 sheets/ov_ufh1.py  ->  out/ov_ufh1.dxf + out/ov_ufh1_Лист.pdf
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from rdbase import (new_doc, DPlan, RDSheet, add_underlay, insert_underlay, UNDER, save_and_pdf,  # noqa: E402
                    fmt_num, SHEET_LIST, SHEETS_TOTAL, axes, ufh_coil, ufh_coil_ortho, offset_poly)
import ov_heat1 as H1  # noqa: E402
from ov_heat1 import (calc1, LOOP_RECT, LOOP_POLY, KSH, KSH_SIZE, TRANSIT_K5, MAIN_ROUTES, pair, draw_base, draw_convectors, kw,  # noqa: E402
                      ROOM, OUT, mask, mlabel, mtag, noyo, ufh_routes)

SHEET_NO = 4
TP = ('ОВ_Т11', 'ОВ_Т21')


def routes():
    """Подводки петель — общие с расчётом длин (ov_heat1.ufh_routes)."""
    return ufh_routes()


# непрямоугольные зоны: угол начала «улитки» (к нему приходит подводка) и направление первого хода
POLY_START = {'1.10-5': ((8.72, 13.00), True), '1.9-3': ((12.30, 10.85), True)}


LABEL_AT = {  # где подписать петлю: (x, y) центра надписи; None — в центре зоны
    '1.4-1': ('in', 10.92, 5.32),
    '1.7-1': ('in', 14.60, 10.10),          # в верхнем правом углу зоны: видны вход и нижние витки
    '1.9-1': ('in', 10.65, 8.12),           # над транзитным пучком подводок (y 7,0–7,7) '1.9-2': (None,), '1.9-3': ('in', 11.72, 13.4),
    '1.6-3': ('in', 19.05, 10.25),
    '1.6-1': ('in', 16.88, 11.20),
    '1.6-2': ('in', 17.83, 11.85),
    '1.10-5': ('in', 7.79, 12.00),          # в северной части зоны (над островом)
    '1.9-3': ('in', 10.95, 13.10),          # под лестницей, в центре «улитки»
}


def build():
    C = calc1()
    loops = {lp['id']: lp for lp in C['loops']}
    doc = new_doc()
    blk = add_underlay(doc, UNDER['plan1'], 'АР_План_1_этажа')
    insert_underlay(doc.modelspace(), blk)
    p = DPlan(doc, k=100)
    axes(p, y_bub=-2.4, x_bub=-2.4)
    draw_base(p, doc)
    draw_convectors(p, light=True)

    # ---- петли: контур зоны штрихом и раскладка трубы «улиткой» (подача — красная, обратка — синяя)
    R = routes()
    COIL_L = {}
    for lid, (x0, y0, x1, y1) in LOOP_RECT.items():
        lp = loops[lid]
        zone = LOOP_POLY.get(lid) or [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        p.poly(zone, 'ОВ_ТП', ltype='ОВ_ШТРИХ')
        r = R.get(lid)
        lead = (offset_poly(r, 0.025)[-1], offset_poly(r, -0.025)[-1]) if r else None
        if lid in LOOP_POLY:
            st, ccw = POLY_START[lid]
            d = (r[-1][0] - r[-2][0], r[-1][1] - r[-2][1])
            COIL_L[lid] = ufh_coil_ortho(p, zone, lp['T'] / 1000.0, st, ccw=ccw, lays=TP, lead_pts=lead, lead_dir=d)
        else:
            COIL_L[lid] = ufh_coil(p, zone, lp['T'] / 1000.0, entry=r[-1] if r else None, lays=TP, lead_pts=lead)
    print('улитки, м (чертёж / расчёт A/T / L табл.):',
          {k: (round(v, 1), round(loops[k]['A'] / (loops[k]['T'] / 1000.0), 1), round(loops[k]['L'], 1))
           for k, v in COIL_L.items()})
    # ---- магистрали ТП от РК и подвод к КШ-2
    H1.boiler_mains(p, TP, 35)                                    # в топочной — по 3D-модели ТМ
    pair(p, TRANSIT_K5, lays=TP, gap=0.06, lw=35)                  # транзит 36 °С КШ-2 → КШ-5, в полу
    # ---- подводки петель
    for lid, r in routes().items():
        pair(p, r, lays=TP)
    # ---- надписи петель
    for lid, (x0, y0, x1, y1) in LOOP_RECT.items():
        lp = loops[lid]
        t1, t2 = lid, f'Ш{lp["T"]}, {fmt_num(lp["L"], 0)} м'
        spec = LABEL_AT.get(lid, (None,))
        if spec[0] == 'lead':
            mlabel(p, spec[1], spec[2], t1, 1.9, at=spec[3], lines=t2)
            continue
        if spec[0] == 'in':
            cx, cy = spec[1], spec[2]
        else:
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if lid in ('1.9-1', '1.9-2'):
                cx = 10.65
            if lid.startswith('1.11'):
                cx = 2.60
        w = max(p.tw(t1, 2.0), p.tw(t2, 2.0)) + 0.12
        mask(p, cx - w / 2, cy - 0.27, cx + w / 2, cy + 0.27)
        p.rect(cx - w / 2, cy - 0.27, cx + w / 2, cy + 0.27, 'ОВ_марки', fill=None)
        p.t(cx, cy + 0.12, t1, 2.0, 'center', 'ОВ_марки')
        p.t(cx, cy - 0.13, t2, 1.8, 'center', 'ОВ_марки')

    # ---- шкафы
    cabs = C['cabs']
    mlabel(p, 12.90, 8.25, f'КШ-1: {cabs["КШ-1"]["n_tp"]} петель, 48,5 °С', 1.9, at=(13.05, 8.97))
    mlabel(p, 13.00, 15.55, f'КШ-2, нижний ярус: {cabs["КШ-2"]["n_tp"]} петель', 1.9, at=(13.05, 11.07),
            lines='смесительный узел 36 °С — на КШ-2 и КШ-5')
    tr = cabs['КШ-5']['transit']
    mlabel(p, 15.40, 14.75, f'КШ-5: {cabs["КШ-5"]["n_tp"]} петель, 36 °С', 1.9, at=(15.40, 11.07),
            lines=f'транзит {tr["pipe"]} от КШ-2 в полу')
    mlabel(p, 16.55, 8.25, f'КШ-3: {cabs["КШ-3"]["n_tp"]} петель, 48,5 °С', 1.9, at=(16.22, 9.14))

    # ---- ярлыки помещений (кратко)
    def tg(no, x, y, extra, h=1.8, anchor=None):
        r = ROOM[no]
        mtag(p, x, y, [f'{no}  +{r["ti"]} °С  {kw(r["Q"])} кВт'] + extra, h=h, anchor=anchor)

    R = C['rooms']
    tg('1.10', 0.85, 13.05 + 0.0, [f'ТП {kw(R["1.10"]["Q_ufh"])} кВт, пол ≤26 °С'])
    tg('1.11', 0.85, 6.02, [f'ТП {kw(R["1.11"]["Q_ufh"])} кВт, пол ≤26 °С'])

    # ---- лист
    sh = RDSheet(doc, 'Лист', SHEET_LIST[SHEET_NO].replace('ё', 'е'), SHEET_NO, SHEETS_TOTAL)
    sh.viewport(152, 177, 258, 222, 9.4, 7.2, k=100)
    sh.title(152, 289.5, 'План 1 этажа. Раскладка тёплого пола. М 1:100')
    rows = [['Петля', 'КШ, вых.', 'Покр.', 'Шаг', 'A, м²', 'L, м', 'Q, Вт', 'G, л/ч', 'л/мин', 'Δp, кПа',
             'tпов, °С']]
    order = sorted(C['loops'], key=lambda lp: (lp['cab'], lp['out']))
    for lp in order:
        rows.append([lp['id'], f'{lp["cab"]}.{lp["out"]}', lp['cover'], f'{lp["T"]}', fmt_num(lp['A'], 1),
                     fmt_num(lp['L'], 0), f'{lp["Q"]:.0f}', fmt_num(lp['G'], 0), fmt_num(lp['lmin'], 2),
                     fmt_num(lp['dp'], 1), fmt_num(lp['tF'], 1)])
    widths = [13, 14, 12, 9, 10, 9, 10, 10, 11, 12, 13]
    sh.s.text('Петли тёплого пола 1 этажа (PE-Xa 16×2,0)', 290 + sum(widths) / 2, 289.5, h=2.5, align='center')
    yb = sh.table(290, 286, widths, rows, row_h=4.4, head_h=6.5, h=1.8,
                  aligns=['center'] * 11)
    rows = [['Шкаф', 'Подача, °С', 'Петель', 'G, кг/ч', 'Δp петли max, кПа', 'Ширина, мм']]
    for c, lab in (('КШ-1', f'{48.5:.1f}'.replace('.', ',')), ('КШ-2', '36,0'), ('КШ-5', '36,0 (от КШ-2)'),
                   ('КШ-3', '48,5')):
        d = cabs[c]
        rows.append([c + (' (низ)' if c == 'КШ-2' else ''), lab, f'{d["n_tp"]}', fmt_num(d['G_tp'], 0),
                     fmt_num(d['dp_max'], 1), f'≈{d["W"]}'])
    widths2 = [22, 18, 14, 18, 30, 21]
    yb = sh.table(290, yb - 3.5, widths2, rows, row_h=4.6, head_h=6, h=1.8, aligns=['center'] * 6)
    dp_hi = sorted((lp for lp in C['loops'] if lp['dp'] > 20.0), key=lambda lp: lp['id'])
    dp_txt = ('; ' + ', '.join(f'петля {lp["id"]} — {fmt_num(lp["dp"], 1)} кПа' for lp in dp_hi) +
              ' (допускается до 25 кПа)') if dp_hi else ''
    sh.notes(290, yb - 5, 123, [
        'Трубы — PE-Xa 16×2,0 с антидиффузионным слоем, в стяжке. Раскладка петель — спиралью («улиткой») '
        'по чертежу, шаг — по таблице; длины петель с подводками — по таблице (±10 % по месту), не более '
        f'90 м. Потери давления в петле — не более 20 кПа{dp_txt}.',
        'ТП не укладывается под кухонной мебелью и островом, сантехприборами, ванной и душевым поддоном, '
        'встроенными шкафами, а также под началом первого марша лестницы в 1.9 (первые две ступени: высота под '
        'ними 0,2–0,35 м, опора косоуров); под остальной лестницей и площадкой до Кв-8 — петля 1.9-3 (шаг 150).',
        'Температура поверхности пола — по СП 60.13330: в 1.10, 1.11 не выше 26 °С, в остальных — не выше '
        '31 °С. Петли 1.10, 1.11, 1.8, 1.9-3 — от смесительного узла КШ-2 (подача 36 °С, насос класса 25-40); '
        f'коллектор КШ-5 — от того же узла транзитом {cabs["КШ-5"]["transit"]["pipe"]} в полу тамбура 1.7 '
        '(перед дверью в 1.8, ниже подводки 1.8-1); '
        'КШ-1, КШ-3 — от РК, подача 48,5 °С.',
        'Пол по грунту (сверху вниз, АР06): покрытие, стяжка 90 мм армированная сеткой ВР-1 (гараж — 145), трубы '
        'на плёнке/мате с разметкой, ЭППС 150 (гараж — 100), демпферная лента по периметру. Деформационные швы — по границам петель и в '
        'дверных проёмах; карта стяжки не более 40 м² и не длиннее 8 м.',
        'Транзитные подводки (на плане — от КШ-1, КШ-2, КШ-5 через тамбур 1.7 под петлей 1.7-1 и холл 1.9) — '
        'в слое утеплителя под петлями, '
        'в гофре; пересечение с магистралями — с обходом по высоте.',
        'Перед заливкой стяжки — испытание давлением 0,6 МПа (не менее 1,5 рабочего) 24 ч; стяжка — под '
        'давлением. Первый пуск — после набора прочности стяжки, с плавным подъёмом температуры.',
        'Покрытия и стяжка — по экспликации полов АР06, АР12 (21.10.2026): ламинат 8 на подложке 2 для тёплого пола (1.9, 1.10; R покрытия с подложкой не более 0,10 м²·°С/Вт), паркетная доска 13 на клею по наливному полу (1.11), керамогранит 8 на клею (остальные), гараж — наливной пол; стяжка 90 мм (1.11 — 85 + 5, гараж — 145), ЭППС 150 (гараж — 100). Расчёт выполнен по стяжке 100 мм — в запас: при 90 мм подача нужна на ≈1 °С ниже.',
    ], h=2.0)
    return doc, C


if __name__ == '__main__':
    doc, C = build()
    print(save_and_pdf(doc, os.path.join(OUT, 'ov_ufh1.dxf')))
