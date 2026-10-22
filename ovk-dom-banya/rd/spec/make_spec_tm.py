"""Спецификация И05.09.26-ТМ.СО: оборудование котельной (из прежнего раздела 1 ОВ.СО), трубы, арматура, изоляция и
крепления — по 3D-модели котельной tm_model (длины с запасом 10 %, вверх до целого метра).

python3 spec/make_spec_tm.py -> out/И05.09.26-ТМ.СО Спецификация.pdf / .xlsx
"""
import math
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'sheets'))
sys.path.insert(0, HERE)
import tm_model as TM  # noqa: E402
from tm_draw import CODE_TM, BLD_TM  # noqa: E402
from spec_data import sec_boiler, data, m, f, A  # noqa: E402
from spec_render import render  # noqa: E402

OUT = os.path.join(ROOT, 'out')
STEEL_S = {15: '2,8', 20: '2,8', 25: '3,2', 32: '3,2'}
SUPPORT = {'steel': {15: 1.5, 20: 2.0, 25: 2.0, 32: 2.5}, 'pex': 1.0}     # шаг креплений, м (СП 73, паспорта PE-Xa)
GALV = ('В1', 'Т3', 'Т4')


def bends(p):
    """Повороты трубы на 90° (изломы ломаной)."""
    n = 0
    pts = p.pts
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        u = [b[k] - a[k] for k in range(3)]
        v = [c[k] - b[k] for k in range(3)]
        lu, lv = math.sqrt(sum(x * x for x in u)), math.sqrt(sum(x * x for x in v))
        if lu < 1e-6 or lv < 1e-6:
            continue
        cos = sum(u[k] * v[k] for k in range(3)) / lu / lv
        if cos < 0.9:
            n += 1
    return n


def tees():
    """Тройники: конец трубы лежит внутри отрезка другой трубы того же назначения (по типоразмеру большей)."""
    out = Counter()
    for a in TM.PIPES:
        for e in (a.pts[0], a.pts[-1]):
            for b in TM.PIPES:
                if b is a or b.sys != a.sys and not (a.sys in ('Т1', 'Т2') and b.sys in ('Т1', 'Т2')):
                    continue
                for s0, s1 in zip(b.pts, b.pts[1:]):
                    if TM.point_on_seg(e, s0, s1, tol=1e-3) and math.dist(e, s0) > 1e-3 and math.dist(e, s1) > 1e-3:
                        out[(b.mat, b.dn, b.sys in GALV)] += 1
    return out


def rows_tm():
    C1, H2, GC, GR, MIX, SITE = data()
    TM.build()
    NOTE = {'листы 7, 8': 'ТМ, листы 2–5', 'лист 7': 'ТМ, листы 2–5'}
    equip = [r[:6] + (NOTE.get(r[6], r[6]),) for r in sec_boiler(GC, GR, MIX)
             if not r[0].startswith(('Труба стальная', 'Фасонные части', 'Опоры и подвески'))]
    equip.append(('Комплект подключения котла к отопительному контуру (краны шаровые Ду25 на подаче и обратке, '
                  'присоединения), штатный', 'Viessmann, по каталогу', '', 'Viessmann', 'компл.', 2, 'К1, К2'))
    equip.append(('Нейтрализатор конденсата для газовых конденсационных котлов', 'по каталогу Viessmann', '', '',
                  'шт.', 1, 'перед трапом; по разделу ВК — уточнить'))
    # ---------------------------------------------------------------- трубы по модели
    L = defaultdict(float)
    for p in TM.PIPES:
        if p.sys in ('Г', 'Д') or p.mat == 'eco':
            continue
        key = ('galv' if p.sys in GALV else p.mat, p.dn)
        L[key] += p.length()
    pipes = []
    for dn in (32, 25, 20, 15):
        if L[('steel', dn)]:
            pipes.append((f'Труба стальная водогазопроводная Ду {dn}×{STEEL_S[dn]}', 'ГОСТ 3262-75', '', '', 'м',
                          m(L[('steel', dn)]), f'по модели {f(L[("steel", dn)], 1)} м + 10 %'))
    for dn in (25, 20, 15):
        if L[('galv', dn)]:
            pipes.append((f'Труба стальная водогазопроводная оцинкованная Ду {dn}×{STEEL_S[dn]} (В1, Т3, Т4)',
                          'ГОСТ 3262-75', '', '', 'м', m(L[('galv', dn)]),
                          f'по модели {f(L[("galv", dn)], 1)} м + 10 %; или нерж. сталь по ВК'))
    for sz in ('32×4,4', '25×3,5', '20×2,8'):
        if L[('pex', sz)]:
            pipes.append((f'Труба PE-Xa {sz} с антидиффузионным слоем (EVOH) — магистрали групп в топочной', A, '',
                          '', 'м', m(L[('pex', sz)]), f'по модели {f(L[("pex", sz)], 1)} м; далее — ОВ.СО'))
    Lk = L[('pp', 0.032)]
    pipes.append(('Труба полипропиленовая канализационная Ø32 — конденсат котлов', 'ГОСТ 32414-2013', '', '', 'м',
                  m(Lk), 'с уклоном к нейтрализатору'))
    # фасонные части: повороты и тройники
    bend = Counter()
    for p in TM.PIPES:
        if p.sys in ('Г', 'Д') or p.mat == 'eco':
            continue
        bend[('galv' if p.sys in GALV else p.mat, p.dn)] += bends(p)
    te = tees()
    fits = []
    for dn in (32, 25, 20, 15):
        for kind, nm in (('steel', ''), ('galv', ' оцинкованный')):
            if bend[(kind, dn)]:
                fits.append((f'Угольник 90°{nm} Ду {dn} (или отвод)', 'ГОСТ 8946-75', '', '', 'шт.', bend[(kind, dn)],
                             'повороты по модели'))
        for galv, nm in ((False, ''), (True, ' оцинкованный')):
            if te[('steel', dn, galv)]:
                fits.append((f'Тройник{nm} Ду {dn}', 'ГОСТ 8948-75', '', '', 'шт.', te[('steel', dn, galv)],
                             'ответвления по модели'))
    for sz in ('32×4,4', '25×3,5', '20×2,8'):
        if bend[('pex', sz)]:
            fits.append((f'Уголок 90° пресс для трубы PE-Xa {sz} (или гиб R ≥ 8D)', A, '', '', 'шт.', bend[('pex', sz)],
                         'повороты магистралей'))
    n_pex_end = Counter()
    for p in TM.PIPES:
        if p.mat == 'pex' and p.id.split('-')[0] in ('Н3', 'Н4', 'Н2', 'Н5'):
            n_pex_end[p.dn] += 2 if p.id.startswith('Н5') else 1     # Н5 — оба конца в топочной (РК и узел П1)
    THREAD = {'20×2,8': 'G¾"', '25×3,5': 'G1"', '32×4,4': 'G1"'}
    for sz, n in sorted(n_pex_end.items()):
        fits.append((f'Фитинг (пресс или компрессионный) для трубы PE-Xa {sz} на резьбу {THREAD[sz]}', A, '', '',
                     'шт.', n, 'выходы групп РК' + (', узел П1' if sz == '20×2,8' else '')))
    k3 = sum(1 for p in TM.PIPES if p.id.startswith('КШ-3'))
    if k3:
        fits.append(('Тройник пресс для трубы PE-Xa 25×3,5', A, '', '', 'шт.', k3, 'отвод Н4 → КШ-3'))
        fits.append(('Фитинг (пресс или компрессионный) для трубы PE-Xa 25×3,5 на резьбу G1"', A, '', '', 'шт.', k3,
                     'вход КШ-3'))
    fits.append(('Фасонные части стальные: сгоны, муфты, контргайки, переходы, американки Ду 15–32', 'ГОСТ 8954-75, '
                 '8957-75, 8969-75', '', '', 'компл.', 1, 'по месту'))
    # ---------------------------------------------------------------- арматура по модели (без вошедшей в оборудование)
    SKIP_PIPES = ('УП',)
    SKIP_KIND = ('safety', 'three', 'pump', 'dirt', 'gas')
    arm = Counter()
    names = {}
    for fi in TM.FITS:
        if fi.kind in SKIP_KIND or fi.pipe.id in SKIP_PIPES or 'комплект подключения' in fi.name:
            continue
        generic = fi.kind in ('vent', 'drain', 'mano', 'therm')
        key = (fi.kind, '' if generic else fi.name.split(' (')[0], 15 if generic else fi.pipe.dn)
        arm[key] += 1
    KIND_NAME = {'ball': None, 'check': 'Клапан обратный', 'filter': 'Фильтр сетчатый', 'reducer': 'Редуктор давления',
                 'vent': 'Воздухоотводчик автоматический Ду 15 с отсечным краном', 'drain': 'Кран спускной Ду 15',
                 'mano': 'Манометр 0–4 бар с трёхходовым краном', 'therm': 'Термометр биметаллический 0–120 °С'}
    arms = []
    for (kind, nm, dn), n in sorted(arm.items(), key=lambda t: (t[0][0], -t[0][2] if isinstance(t[0][2], int) else 0)):
        if kind == 'ball':
            nm2 = nm.replace('Ду32', 'Ду 32').replace('Ду25', 'Ду 25').replace('Ду20', 'Ду 20').replace('Ду15', 'Ду 15')
            arms.append((nm2, A, '', '', 'шт.', n, ''))
        elif kind in ('vent', 'drain', 'mano', 'therm'):
            arms.append((KIND_NAME[kind], A, '', '', 'шт.', n, ''))
        else:
            arms.append((f'{KIND_NAME[kind]} Ду {dn}', A, '', '', 'шт.', n, ''))
    # ---------------------------------------------------------------- изоляция и крепления
    ins = []
    l3 = L[('galv', 25)]
    t3t4 = sum(p.length() for p in TM.PIPES if p.sys in ('Т3', 'Т4'))
    v1 = sum(p.length() for p in TM.PIPES if p.sys == 'В1')
    ins.append(('Трубка теплоизоляционная из вспененного каучука, толщина 13 мм — Т3, Т4', '', '', '', 'м', m(t3t4),
                'горячая вода и циркуляция'))
    ins.append(('Трубка теплоизоляционная из вспененного каучука, толщина 9 мм — В1', '', '', '', 'м', m(v1),
                'от конденсата'))
    sup = Counter()
    for p in TM.PIPES:
        if p.sys in ('Г', 'Д') or p.mat in ('eco', 'pp'):
            continue
        step = SUPPORT['pex'] if p.mat == 'pex' else SUPPORT['steel'][p.dn]
        sup[(p.mat, p.dn)] += math.ceil(p.length() / step) + 1
    for (mat, dn), n in sorted(sup.items(), key=lambda t: str(t[0])):
        lab = f'Ду {dn}' if mat == 'steel' else f'Ø{str(dn).split("×")[0]}'
        ins.append((f'Хомут трубный с резиновым вкладышем, {lab}, со шпилькой и анкером', '', '', '', 'шт.', n,
                    'шаг по СП 73.13330'))
    ins.append(('Гильза для прохода труб через стену топочной (в тамбур 1.7) с заделкой негорючим материалом', '', '',
                '', 'шт.', 6, 'Н3, Н4, Н2 — Т1/Т11 и Т2/Т21; ТЗ-1'))
    secs = [('1. Оборудование', equip), ('2. Трубопроводы (по 3D-модели)', pipes), ('3. Фасонные части', fits),
            ('4. Арматура и приборы (по 3D-модели)', arms), ('5. Изоляция и крепления', ins),
            ('6. Не входит в ТМ.СО', [
                ('Газопровод, краны газовые, счётчик, сигнализатор загазованности — по проекту ГСВ', '', '', '', '',
                 '', 'ТЗ-4'),
                ('Трубы Ecoflex Quattro (Н6, ввод в баню) — И05.09.26-ОВ.СО, раздел 4', '', '', '', '', '', ''),
                ('Магистрали PE-Xa от стены топочной до шкафов — И05.09.26-ОВ.СО, раздел 2', '', '', '', '', '', '')])]
    out, n = [], 1
    for title, items in secs:
        out.append(('section', title))
        for it in items:
            out.append(('item', n) + tuple(it))
            n += 1
    return out


if __name__ == '__main__':
    rows = rows_tm()
    pdf, xl = render(rows, CODE_TM + '.СО', 'Спецификация оборудования, изделий и материалов', OUT,
                     'И05.09.26-ТМ.СО Спецификация', sheet_title='Спецификация ТМ', bld=BLD_TM)
    print(pdf, xl, len([r for r in rows if r[0] == 'item']), 'позиций')
