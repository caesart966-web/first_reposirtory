"""И05.09.26-ВК, листы 10–12. Аксонометрические схемы — фронтальная изометрия (ГОСТ 2.317: x вправо, y под 45°
вправо-вверх, z вверх, коэффициенты 1) — проекции 3D-модели vk_model.

10 — В1, Т3, Т4 дома (А2, М 1:50); 11 — В1, Т3, Т4 бани (А2, М 1:50); 12 — К1 дома и бани (А2, М 1:50).
python3 sheets/vk_axo.py [10|11|12]
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from rdbase import new_doc, RDSheet, save_and_pdf  # noqa: E402
import vk_model as VK  # noqa: E402
from vk_draw import (CODE_VK, BLD_VK, VK_LIST, VK_TOTAL, setup, finish_layers, PP, View, VLabels, draw_net,  # noqa
                     vk_fit, draw_eq, level_mark, lev, f1, STYLE)
from tm_draw import C45  # noqa: E402

OUT = os.path.join(ROOT, 'out')
SHORT = {'16×2,2': '16', '20×2,8': '20', '25×3,5': '25', '32×4,4': '32'}


def axo_view(pipes, box, K=None, margin=0.80):
    """Вид по центру окна; K=None — крупнейший стандартный масштаб, при котором схема помещается в окно."""
    us, vs = [], []
    for pp in pipes:
        if pp.sys == 'К1в':
            continue
        for x, y, z in pp.pts:
            us.append(x + y * C45)
            vs.append(z + y * C45)
    u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
    if K is None:
        w, h = (box[2] - box[0]) * margin, (box[3] - box[1]) * margin
        K = next(k for k in (20, 25, 30, 40, 50, 75, 100) if (u1 - u0) * 1000 / k <= w and (v1 - v0) * 1000 / k <= h)
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return View('axo', K, (cx, cy), ((u0 + u1) / 2, (v0 + v1) / 2))


def end_labels(p, L, V, pipes, h=1.7):
    """Концы подводок у приборов: марка прибора, Ø, отметка присоединения."""
    for pp in pipes:
        fx = [s for s in pp.serves if s in VK.FIXT]
        if len(fx) != 1 or pp.sys not in ('В1', 'Т3'):
            continue
        end = pp.pts[-1]
        t = f'{pp.sys} {SHORT.get(pp.dn, pp.dn)} → {fx[0]}'
        L.shelf(V.P(end), t, h, sub=lev(end[2]) if pp.where != 'floor' or True else None)


def water(doc, sh, bld, title):
    p = PP(doc, sh.lay)
    box = (28.0, 70.0, 585.0, 400.0)
    pipes = [pp for pp in VK.PIPES if pp.bld == bld and pp.sys in ('В1', 'Т3', 'Т4')]
    V = axo_view(pipes, box)
    L = VLabels(p, box)
    draw_net(p, V, pipes, box, L=L)
    for e in VK.EQUIP:
        if e.bld != bld or e.id in ('ПРВ',):
            continue
        if e.id in ('ШВК-1', 'ШВК-2', 'ШВК-Б', 'КХ', 'Б2', 'РБ-Б2'):
            draw_eq(p, V, e, layer='ТМ_оборуд_тонк', mask=False)
    for f in VK.FITS:
        if f.pipe.bld == bld and f.pipe.sys in ('В1', 'Т3', 'Т4'):
            vk_fit(p, V, f, scale=0.8)
    for e in VK.EQUIP:
        if e.bld == bld and e.id in ('ШВК-1', 'ШВК-2', 'ШВК-Б', 'КХ', 'Б2', 'РБ-Б2'):
            bb = e.bbox()
            L.shelf(V.P(((bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, bb[5])), e.mark, 2.2)
    end_labels(p, L, V, pipes)
    # подписи магистралей
    P = {pp.id: pp for pp in VK.PIPES}
    mains = ['ВВ', 'КХ-4', 'В1-гараж', 'Т3-гараж', 'Т3-1.6', 'Т4-1.6', 'В1-ШВК1', 'Т3-ШВК1', 'Т4-дом', 'КХ-1', 'КХ-3',
             'КХ-2', 'КХ-6', 'КХ-7', 'КХ-5'] if bld == 'h' else ['В1-баня', 'Т3-Б2', 'Т4-баня', 'В1-Б2', 'В1-ПК-3']
    for i in mains:
        pp = P[i]
        best = None
        for a, b in zip(pp.pts, pp.pts[1:]):
            A, B = V.P(a), V.P(b)
            Lm = math.hypot(B[0] - A[0], B[1] - A[1])
            if best is None or Lm > best[0]:
                best = (Lm, A, B, a)
        Lm, A, B, a = best
        dn = SHORT.get(pp.dn, pp.dn) if pp.mat == 'pex' else pp.label()
        t = f'{pp.id}: {pp.sys} {dn}'
        for tt in (0.5, 0.3, 0.7):
            if L.shelf((A[0] + (B[0] - A[0]) * tt, A[1] + (B[1] - A[1]) * tt), t, 1.8, sub=f'ось {lev(a[2])}'):
                break
    sh.title((box[0] + box[2]) / 2, box[3] + 6, f'{title}. М 1:{V.K}', h=3.5)
    return p, L, V


NOTES10 = [
    'Схема — проекция 3D-модели (фронтальная изометрия, оси без сокращения). Отметки — оси труб от ±0,000 '
    'дома; у приборов — отметки присоединения.',
    'Трубы — PE-Xa по ГОСТ 32415 (классы эксплуатации ХВ и ГВС, PN10); соединения — только в шкафах ШВК-1, '
    'ШВК-2, у гребёнки КХ и у приборов (пресс- или надвижные гильзы). Диаметры — по П2.',
    'Т3 и Т4 — в изоляции 13 мм, В1 — 9 мм; в стенах и на выходах из пола — в гофре. Циркуляция Т4: ШВК-1 → Пс-2 → Пс-1 → Н8 → Б1 '
    '(П4); балансировочный клапан на выходе Т4 из ШВК-1 — настройка по П4.',
    'Под потолком гаража — уклон водопровода не требуется; спуск — через краны коллекторов и гребёнки.',
    'Коллекторы ШВК-1, ШВК-2 — схемы на листе 13; водомерный узел и гребёнка КХ — лист 7.',
]
NOTES11 = [
    'Схема — проекция 3D-модели (фронтальная изометрия). Отметки — оси труб от ±0,000 бани.',
    'Холодная вода — от КХ-3 дома по санитарной трубе Ecoflex Quattro 32×4,4 (L ≈ 17 м, ОВ лист 14) к ШВК-Б.',
    'Т4: из конца коллектора Т3 ШВК-Б → Пс-б1.1 → Пс-б1.2 → Пс-б2 → Н9 → клапан обратный → Б2 (П4).',
    'Группа безопасности 6 бар и мембранный бак РБ-Б2 12 л — на подводе В1 к Б2; сброс ГБ — в воронку К1-Б2.',
]


def sewer(doc, sh):
    p = PP(doc, sh.lay)
    res = []
    for bld, box, title in (('h', (28.0, 185.0, 585.0, 400.0), 'Схема К1 дома'),
                            ('b', (28.0, 15.0, 395.0, 170.0), 'Схема К1 бани')):
        pipes = [pp for pp in VK.PIPES if pp.bld == bld and pp.sys in ('К1', 'К1в')]
        V = axo_view(pipes, box)
        L = VLabels(p, box)
        draw_net(p, V, pipes, box, L=L)
        for f in VK.FITS:
            if f.pipe in pipes:
                vk_fit(p, V, f, scale=0.9)
        for pp in pipes:
            best = None
            for a, b in zip(pp.pts, pp.pts[1:]):
                A, B = V.P(a), V.P(b)
                Lm = math.hypot(B[0] - A[0], B[1] - A[1])
                if best is None or Lm > best[0]:
                    best = (Lm, A, B, a, b)
            Lm, A, B, a, b = best
            if pp.sys == 'К1в':
                t, sub = f'{pp.id} Ø{pp.dn}', f'верх {lev(pp.pts[-1][2])}'
            elif pp.where in ('ground', 'ceil'):
                i_ = 0.02 if pp.dn == 110 else 0.03
                t = f'{pp.id}: Ø{pp.dn}, i={f1(i_, 2)}'
                sub = f'лоток {lev(pp.pts[0][2] - pp.od / 2)} → {lev(pp.pts[-1][2] - pp.od / 2)}'
            else:
                t, sub = f'{pp.id}: Ø{pp.dn}', None
            for tt in (0.5, 0.3, 0.7, 0.15):
                if L.shelf((A[0] + (B[0] - A[0]) * tt, A[1] + (B[1] - A[1]) * tt), t, 1.7, sub=sub):
                    break
        fx = [k for k, f in VK.FIXT.items() if f.bld == bld and f.k1]
        for k in fx:
            # начало отвода прибора
            src = [pp for pp in pipes if k in pp.serves]
            if not src:
                continue
            L.shelf(V.P(src[0].pts[0]), k, 1.8, cands=[(4, 4), (-4, 4), (4, -4), (-4, -4), (7, 7), (-7, 7)])
        sh.s.text(f'{title}. М 1:{V.K}', (box[0] + box[2]) / 2, box[3] + 3, h=3.0, align='center')
        res.append((V, L))
    return p


NOTES12 = [
    'Схемы — проекции 3D-модели (фронтальная изометрия). Отметки — лотки труб; верх вытяжных частей — от '
    '±0,000 своего здания.',
    'Сеть 1 этажа дома и сеть бани — в грунте под плитой (решение Заказчика); К1 2 этажа — под потолком гаража '
    'к Ст.К1-1. Внутри зданий (стояки, вытяжные части, короб гаража, отводы 2 этажа и подъёмы к приборам) — '
    'бесшумные трубы и фасонные части (опросный лист, ВК.СО). Лоток гаража — в К2 (лист 4).',
    'Уклоны: Ø110 — 0,02, Ø50 — 0,03, конденсат Ø32 — не менее 0,02 (П3). Отводы от приборов — с уклоном к сборным.',
    'Ст.К1-1в, Ст.К1-б — над кровлей на 0,35 м (п. 18.18), с зонтом-флюгаркой не устанавливать (п. 18.21).',
    'Ревизии (Р) и прочистки (П) — по п. 18.26 и табл. 18.1; у ревизий в коробах — люки 300×400 (ТЗ-1).',
]

if __name__ == '__main__':
    no = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    doc = new_doc()
    setup(doc)
    sh = RDSheet(doc, 'Лист', VK_LIST[no], no, VK_TOTAL, fmt='А2', code=CODE_VK, bld=BLD_VK)
    if no == 10:
        water(doc, sh, 'h', 'Схема систем В1, Т3, Т4 дома (фронтальная изометрия)')
        sh.notes(28, 62, 370, NOTES10, h=1.9, spacing=1.0)
    elif no == 11:
        water(doc, sh, 'b', 'Схема систем В1, Т3, Т4 бани (фронтальная изометрия)')
        sh.notes(28, 62, 370, NOTES11, h=1.9, spacing=1.0)
    else:
        sewer(doc, sh)
        sh.notes(402, 170, 182, NOTES12, h=1.9, spacing=1.0)
    finish_layers(doc)
    print(save_and_pdf(doc, os.path.join(OUT, f'vk_axo_{no}.dxf')))
