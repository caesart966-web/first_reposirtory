"""И05.09.26-ВК, лист 13. Схемы коллекторных шкафов ШВК-1, ШВК-2, ШВК-Б1, ШВК-Б2 (без масштаба) и таблицы выходов —
выходы, трубы, длины и расходы берутся из 3D-модели vk_model и расчёта vk_calc.

python3 sheets/vk_coll.py -> out/vk_coll.dxf + PDF
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from rdbase import new_doc, RDSheet, save_and_pdf, fmt_num  # noqa: E402
import vk_model as VK  # noqa: E402
from vk_draw import CODE_VK, BLD_VK, VK_LIST, VK_TOTAL, setup, finish_layers, PP  # noqa: E402
from vk_node import sym  # noqa: E402

OUT = os.path.join(ROOT, 'out')
SHEET_NO = 13
CALC = json.load(open(os.path.join(ROOT, 'out', 'vk', 'vk_calc.json')))
COLL = {
    'ШВК-2': ('ШВК-2В', 'ШВК-2Т', 'с/у 2.9: ниша в перегородке 2.9/2.8, встроенный шкаф ≈900×650×120, низ +0,250 '
              'от пола 2 этажа, нажимной люк под плитку',
              'коллектор 1¼" (В1, ввод от КХ-4) и проходной 1" (Т3 от Б1: последний выход — Т4 с балансировочным '
              'клапаном), выходы 3/4" «евроконус» с шаровыми кранами'),
    'ШВК-1': ('ШВК-1В', 'ШВК-1Т', 'с/у 1.4: ниша в стене 1.4/1.3 между унитазом и душем, встроенный шкаф ≈750×600×120, низ +0,250, '
              'нажимной люк под плитку',
              'коллектор 1" (В1, ввод от КХ-10) и проходной 1" (Т3 от Б1: последний выход — Т4 с балансировочным '
              'клапаном), выходы 3/4" с шаровыми кранами'),
    'ШВК-Б2': ('ШВК-Б2В', 'ШВК-Б2Т', 'баня, с/у б3: ниша в перегородке б3/б4, встроенный шкаф ≈700×600×120, низ +0,300, '
               'нажимной люк под плитку',
               'коллектор 1" (В1, на вводе кран КЭ-2) и проходной 3/4" (Т3 от Б2: последний выход — Т4 с '
               'балансировочным клапаном), выходы 3/4" с шаровыми кранами'),
    'ШВК-Б1': ('ШВК-Б1В', 'ШВК-Б1Т', 'баня, помывочная б7: ниша в восточной стене у южного угла, встроенный шкаф '
               '≈820×650×120, низ +0,250, нажимной люк под плитку со стороны б7',
               'коллектор 1" (В1, на вводе кран КЭ-3) и проходной 1" (Т3 от Б2: последний выход — кольцо через '
               'смеситель душа Д-б1 и мойку М-б1, Т4 — от мойки к Н9)'),
}


def on_pipe(pt, pp, tol=0.03):
    for a, b in zip(pp.pts, pp.pts[1:]):
        if VK.point_on_seg(pt, a, b, tol):
            return True
    return False


def outlets(cid):
    """Трубы, начинающиеся на коллекторе (выходы), и входящие в него (вводы), упорядоченные вдоль коллектора."""
    P = {pp.id: pp for pp in VK.PIPES}
    res = {}
    for key in COLL[cid][:2]:
        col = P[key]
        a, b = col.pts[0], col.pts[-1]
        L = math.dist(a, b)
        ins, outs = [], []
        for pp in VK.PIPES:
            if pp is col or pp.sys not in ('В1', 'Т3', 'Т4'):
                continue
            if on_pipe(pp.pts[0], col):
                s = sum((pp.pts[0][k] - a[k]) * (b[k] - a[k]) for k in range(3)) / L
                outs.append((s, pp))
            elif on_pipe(pp.pts[-1], col):
                s = sum((pp.pts[-1][k] - a[k]) * (b[k] - a[k]) for k in range(3)) / L
                ins.append((s, pp))
        res[key] = (col, sorted(ins, key=lambda t: t[0]), sorted(outs, key=lambda t: t[0]), L)
    return res


def target(pp):
    if pp.id in NEXT:
        return NEXT[pp.id]
    fx = [s for s in pp.serves if s in VK.FIXT]
    if fx:
        return ', '.join(fx)
    if pp.sys == 'Т4':
        return 'циркуляция Т4'
    if pp.serves == ['Б2']:
        return 'Б2 (через ГБ 6 бар)'
    return {'*1эт': 'ШВК-1', '*дом': 'дом', '*баня': 'баня'}.get(pp.serves[0] if pp.serves else '', pp.name)


SRC = {'В1-гараж': 'от КХ-4 (гребёнка КХ, 1.6)', 'Т3-гараж': 'от Б1 (Т3 из топочной 1.6)',
       'В1-ШВК1': 'от КХ-10 (гребёнка КХ, 1.6)', 'Т3-ШВК1': 'от Б1 (тройник Т3 в 1.6)',
       'В1-баня': 'от Ecoflex (КХ-3 дома), кран КЭ-2', 'Т3-Б2': 'от Б2',
       'В1-ШВК-Б1': 'от ввода Ecoflex (до ШВК-Б2), кран КЭ-3', 'Т3-ШВК-Б1': 'от Б2 (тройник у Б2)'}
NEXT = {'Т4-ШВК2': 'Т4 → Пс-2, Пс-1 → Н8', 'Т4-ШВК1': 'Т4 → Н8', 'Т4-ШВК-Б2': 'Т4 → Пс-б1.1, 1.2, б2 → Н9',
        'Т3-Д-б1': 'кольцо: Д-б1 → М-б1 → Н9'}


def draw_coll(p, x0, y0, cid, width=170.0):
    data = outlets(cid)
    (cv, insv, outv, Lv), (ct, inst, outt, Lt) = data[COLL[cid][0]], data[COLL[cid][1]]
    rows = []
    for k, (col, ins, outs, Lc) in enumerate(((cv, insv, outv, Lv), (ct, inst, outt, Lt))):
        y = y0 - k * 34.0
        lay = 'ВК_В1' if col.sys == 'В1' else 'ВК_Т3'
        n = len(outs)
        x1 = x0 + width
        p.pl([(x0, y), (x1, y)], lay, lw=70)
        p.rect(x0 - 1, y - 2, x1 + 1, y + 2, 'ТМ_оборуд')
        p.t(x0 - 2, y, col.sys, 2.5, 'right', 'ТМ_марки')
        for s, pp in ins:
            xi = x0 + width * (s / Lc) if Lc else x0
            xi = min(max(xi, x0 + 2), x1 - 2)
            p.pl([(x1, y), (x1 + 10, y)], lay, lw=50)
            p.t(x1 + 11, y + 1, f'ввод {pp.sys} {pp.dn}', 1.7, 'bl', 'ТМ_текст')
            p.t(x1 + 11, y - 1, SRC.get(pp.id, pp.name), 1.6, 'tl', 'ТМ_текст')
        step = (width - 10) / max(n, 1)
        for i, (s, pp) in enumerate(outs):
            xo = x0 + 5 + step * (i + 0.5)
            ly = 'ВК_Т4' if pp.sys == 'Т4' else lay
            p.pl([(xo, y - 2), (xo, y - 24)], ly, ltype='ОВ_ШТРИХ' if pp.sys == 'Т4' else None)
            sym(p, 'balance' if pp.sys == 'Т4' else 'ball', (xo, y - 8), (0, 1), scale=1.0)
            no = f'{col.sys}-{i + 1}'
            p.t(xo - 0.9, y - 23.5, no, 1.6, 'bl', 'ТМ_марки', rot=90)
            x_ = CALC['network'].get(pp.id, {})
            q = x_.get('q')
            rows.append([no, pp.sys, target(pp), pp.dn, fmt_num(pp.length(), 1), fmt_num(q, 3) if q else '—'])
    return rows


def build():
    doc = new_doc()
    setup(doc)
    sh = RDSheet(doc, 'Лист', VK_LIST[SHEET_NO], SHEET_NO, VK_TOTAL, fmt='А2', code=CODE_VK, bld=BLD_VK)
    p = PP(doc, sh.lay)
    for k, cid in enumerate(('ШВК-2', 'ШВК-1', 'ШВК-Б2', 'ШВК-Б1')):
        x, y = 28, 392 - k * 92
        sh.s.text(f'{cid} — {COLL[cid][2]}', x, y + 10, h=2.2, align='left')
        sh.s.text(COLL[cid][3], x, y + 5.5, h=1.9, align='left')
        rows = draw_coll(p, x + 10, y - 6, cid, width=150.0)
        rows = [['Выход', 'Сист.', 'Прибор', 'Труба PE-Xa', 'L, м', 'q, л/с']] + rows
        sh.table(x + 252, y + 2, [13, 10, 40, 19, 11, 13], rows, row_h=4.4, head_h=5.2, h=1.7,
                 aligns=['center', 'center', 'left', 'center', 'center', 'center'])
    sh.notes(402, 405, 184, NOTES, h=1.8, spacing=1.0)
    finish_layers(doc)
    return doc


NOTES = [
    'Схемы — без масштаба; порядок выходов — как на коллекторах в 3D-модели (листы 3, 4, 8): трубы одной системы '
    'от соседних выходов не пересекаются. Коллекторы — в санузлах, в нишах стен за нажимными люками под плитку '
    '(замечание Заказчицы 26.10.2026); ШВК-Б1 — в нише восточной стены помывочной б7 у южного угла (27.10.2026, ТЗ-1).',
    'Коллекторы подключены независимо (Заказчица 27.10.2026): В1 — своими выходами гребёнки КХ (ШВК-2 — КХ-4, '
    'ШВК-1 — КХ-10), в бане — тройником у подъёма Ecoflex (ШВК-Б1 — своя линия с краном КЭ-3); Т3 — тройниками у '
    'Б1 и Б2. Коллекторы Т3 проходные, Т4 — от каждого отдельно: Б1 → ШВК-2 → Пс-2, Пс-1 → Н8; Б1 → ШВК-1 → Н8 '
    '(кухня — своим кольцом от топочной); Б2 → ШВК-Б2 → Пс-б1.1, Пс-б1.2, Пс-б2 → Н9; Б2 → ШВК-Б1 → смеситель '
    'душа Д-б1 → мойка М-б1 → Н9.',
    'Длины L — по модели от выхода до точки присоединения прибора; в спецификации — с запасом 10 %.',
    'Каждый выход — с шаровым краном и биркой назначения (прибор); Т4 — с ручным балансировочным клапаном, '
    f'настройка расхода — П4 (ШВК-2 {CALC["circ"]["house"]["G"] * 3600:.0f} л/ч, ШВК-1 '
    f'{CALC["circ"]["house1"]["G"] * 3600:.0f} л/ч, ШВК-Б2 {CALC["circ"]["bath"]["G"] * 3600:.0f} л/ч, кольцо ШВК-Б1 '
    f'{CALC["circ"]["bath1"]["G"] * 3600:.0f} л/ч — клапан в шкафу мойки М-б1).',
    'В шкафах — спускные краны с воздухоотводчиками на концах коллекторов; под шкафами — датчики протечки ДП '
    '(ДП-8, ДП-9, ДП-16, ДП-19), шкафы в нишах — с поддоном.',
    'Коллекторы — латунь никелированная или нержавеющая сталь, PN10, 95 °С; подключение труб PE-Xa — '
    'фитингами «евроконус» под свою трубу.',
]

if __name__ == '__main__':
    print(save_and_pdf(build(), os.path.join(OUT, 'vk_coll.dxf')))
