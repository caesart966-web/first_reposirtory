"""И05.09.26-ВК, лист 13. Схемы коллекторных шкафов ШВК-1, ШВК-2, ШВК-Б (без масштаба) и таблицы выходов —
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
    'ШВК-1': ('ШВК-1В', 'ШВК-1Т', 'на западной стене гаража, накладной шкаф 950×700×200, низ +0,400',
              'коллекторы 1" (В1) и 3/4" (Т3), выходы 3/4" «евроконус» с шаровыми кранами'),
    'ШВК-2': ('ШВК-2В', 'ШВК-2Т', 'в коробе под потолком гаража, ось +3,050, люк 600×600',
              'проходные коллекторы 1¼" (В1) и 1" (Т3), выходы 3/4" с шаровыми кранами'),
    'ШВК-Б': ('ШВК-БВ', 'ШВК-БТ', 'баня, раздевалка б4, накладной шкаф 1100×650×180 на перегородке б3/б4',
              'коллекторы 1" (В1) и 3/4" (Т3), выходы 3/4" с шаровыми кранами'),
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
    fx = [s for s in pp.serves if s in VK.FIXT]
    if fx:
        return ', '.join(fx)
    if pp.sys == 'Т4':
        return 'циркуляция Т4'
    if pp.serves == ['Б2']:
        return 'Б2 (через ГБ 6 бар)'
    return {'*1эт': 'ШВК-1', '*дом': 'дом', '*баня': 'баня'}.get(pp.serves[0] if pp.serves else '', pp.name)


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
            p.t(x1 + 11, y - 1, f'от {pp.name.split("от ")[-1] if "от " in pp.name else pp.name}'[:34], 1.6,
                'tl', 'ТМ_текст')
        step = (width - 10) / max(n, 1)
        for i, (s, pp) in enumerate(outs):
            xo = x0 + 5 + step * (i + 0.5)
            ly = 'ВК_Т4' if pp.sys == 'Т4' else lay
            p.pl([(xo, y - 2), (xo, y - 24)], ly, ltype='ОВ_ШТРИХ' if pp.sys == 'Т4' else None)
            sym(p, 'balance' if pp.sys == 'Т4' else 'ball', (xo, y - 8), (0, 1), scale=1.0)
            no = f'{col.sys}-{i + 1}'
            p.t(xo + 1.2, y - 13, no, 1.6, 'bl', 'ТМ_марки', rot=90)
            x_ = CALC['network'].get(pp.id, {})
            q = x_.get('q')
            rows.append([no, pp.sys, target(pp), pp.dn, fmt_num(pp.length(), 1), fmt_num(q, 3) if q else '—'])
    return rows


def build():
    doc = new_doc()
    setup(doc)
    sh = RDSheet(doc, 'Лист', VK_LIST[SHEET_NO], SHEET_NO, VK_TOTAL, fmt='А2', code=CODE_VK, bld=BLD_VK)
    p = PP(doc, sh.lay)
    y = 385.0
    for cid in ('ШВК-2', 'ШВК-1', 'ШВК-Б'):
        sh.s.text(f'{cid} — {COLL[cid][2]}', 30, y + 10, h=2.6, align='left')
        sh.s.text(COLL[cid][3], 30, y + 5.5, h=2.0, align='left')
        rows = draw_coll(p, 40, y - 6, cid)
        rows = [['Выход', 'Сист.', 'Прибор', 'Труба PE-Xa', 'L, м', 'q, л/с']] + rows
        sh.table(330, y + 8, [14, 11, 34, 20, 12, 14], rows, row_h=4.6, head_h=5.5, h=1.8,
                 aligns=['center', 'center', 'left', 'center', 'center', 'center'])
        y -= 112.0 if cid != 'ШВК-1' else 104.0
    sh.notes(470, 400, 115, NOTES, h=1.8, spacing=1.0)
    finish_layers(doc)
    return doc


NOTES = [
    'Схемы — без масштаба; порядок выходов — как на коллекторах в 3D-модели (листы 4, 5, 8): трубы одной системы '
    'от соседних выходов не пересекаются.',
    'Длины L — по модели от выхода до точки присоединения прибора; в спецификации — с запасом 10 %.',
    'Каждый выход — с шаровым краном и биркой назначения (прибор); Т4 — с ручным балансировочным клапаном, '
    'настройка расхода — П4 (дом 76 л/ч, баня 121 л/ч).',
    'В шкафах — спускные краны с воздухоотводчиками на концах коллекторов; поддон с отводом не требуется '
    '(шкафы — над полом, в сухих помещениях).',
    'Коллекторы — латунь никелированная или нержавеющая сталь, PN10, 95 °С; подключение труб PE-Xa — '
    'фитингами «евроконус» под свою трубу.',
]

if __name__ == '__main__':
    print(save_and_pdf(build(), os.path.join(OUT, 'vk_coll.dxf')))
