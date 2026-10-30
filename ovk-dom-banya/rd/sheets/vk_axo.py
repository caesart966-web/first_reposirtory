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
EQS = ('ШВК-1', 'ШВК-2', 'ШВК-Б1', 'ШВК-Б2', 'КХ', 'Б2', 'РБ-Б2')
NO_END = {'В1-баня', 'В1-ШВК-Б1', 'Т3-ШВК-Б1', 'Т3-Б2', 'В1-гараж', 'Т3-гараж', 'В1-ШВК1', 'Т3-ШВК1', 'КХ-4'}   # магистрали


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
        if not fx or pp.sys not in ('В1', 'Т3') or pp.id.startswith('ШВК') or pp.id in NO_END:
            continue
        end = pp.pts[-1]
        near = min(fx, key=lambda k: math.hypot(VK.FIXT[k].pos[0] - end[0], VK.FIXT[k].pos[1] - end[1]))
        others = [k for k in fx if k != near]
        if 'Т4' in pp.serves:                          # кольцо ГВС через смеситель (тройник петли)
            others = []
            near += ' (тройник кольца Т3–Т4)'
        t = f'{pp.sys} {SHORT.get(pp.dn, pp.dn)} → {near}' + (f' ({", ".join(others)})' if others else '')
        E_, Q_ = V.P(end), V.P(pp.pts[-2])
        alt = [(E_[0] + (Q_[0] - E_[0]) * tt, E_[1] + (Q_[1] - E_[1]) * tt) for tt in (0.25, 0.5)]   # у конца трубы
        for a2, b2 in list(zip(pp.pts, pp.pts[1:]))[::-1][1:]:                # затем — другие участки трубы
            A2, B2 = V.P(a2), V.P(b2)
            if math.dist(A2, B2) >= 6.0:
                alt += [(A2[0] + (B2[0] - A2[0]) * tt, A2[1] + (B2[1] - A2[1]) * tt) for tt in (0.5, 0.25, 0.75)]
        if not any(L.shelf(q, t, h, sub=lev(end[2]), strict=True) for q in [E_] + alt):
            L.shelf(E_, t, h, sub=lev(end[2]))
    # циркуляция: насос, балансировочный клапан, полотенцесушители
    pump_done = set()
    for f in VK.FITS:
        if f.pipe not in pipes:
            continue
        if f.kind == 'pump':
            mk = [w for w in f.name.split() if w.startswith('Н') and w[1:].isdigit()]
            L.shelf(V.P(f.pos), f'{mk[0] if mk else "Н"} — насос циркуляционный', h, sub='клапан обратный (П4)')
        elif f.kind == 'balance':
            L.shelf(V.P(f.pos), 'Клапан балансировочный Ду15', h, sub='настройка — П4')
        elif f.kind == 'mvalve':
            mk = [w for w in f.name.split() if w.startswith('КЭ-')]
            L.shelf(V.P(f.pos), f'{mk[0] if mk else "КЭ"} — кран с электроприводом', h, sub='защита от протечек')
        elif f.kind == 'ball' and ' у Пс' in f.name:
            mk = f.name.split(' у ')[-1]
            if mk not in pump_done:
                pump_done.add(mk)
                L.shelf(V.P(f.pos), f'{mk} — полотенцесушитель (Т4)', h)


def water(doc, sh, bld, title, first=()):
    p = PP(doc, sh.lay)
    box = (28.0, 70.0, 585.0, 400.0)
    pipes = [pp for pp in VK.PIPES if pp.bld == bld and pp.sys in ('В1', 'Т3', 'Т4')]
    V = axo_view(pipes, box)
    L = VLabels(p, box)
    draw_net(p, V, pipes, box, L=L)
    for e in VK.EQUIP:
        if e.bld != bld:
            continue
        if e.id in EQS:
            draw_eq(p, V, e, layer='ТМ_оборуд_тонк', mask=False)
    for f in VK.FITS:
        if f.pipe.bld == bld and f.pipe.sys in ('В1', 'Т3', 'Т4'):
            vk_fit(p, V, f, scale=0.8)
    for e in VK.EQUIP:
        if e.bld == bld and e.id in EQS:
            bb = e.bbox()
            L.shelf(V.P(((bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, bb[5])), e.mark, 2.2)
    # подписи магистралей
    P = {pp.id: pp for pp in VK.PIPES}
    mains = ['ВВ', 'КХ-4', 'В1-гараж', 'Т3-гараж', 'Т3-1.6', 'Т4-1.6', 'В1-ШВК1', 'Т3-ШВК1', 'Т3-М-1', 'Т4-М-1',
             'Т4-ШВК2', 'Т4-ШВК1', 'КХ-1', 'КХ-3', 'КХ-2', 'КХ-6', 'КХ-7', 'КХ-5', 'КХ-8', 'КХ-9'] if bld == 'h' else \
        ['В1-баня', 'Т3-Б2', 'В1-ШВК-Б1', 'Т3-ШВК-Б1', 'Т3-Д-б1', 'Т4-Д-б1', 'Т3-М-б1', 'Т4-б6', 'Т4-ШВК-Б2',
         'В1-Б2', 'В1-ПК-3']
    SHOWN = {'ВВ': 'Ввод (без приямка, в футляре)', 'КХ-8': 'КХ-8 (автополив)'}
    DESC = {'Т3-1.6': 'от Б1 (к ШВК-2, ШВК-1, кухне)', 'Т4-1.6': 'к насосу Н8 и Б1', 'В1-гараж': 'КХ-4 → ШВК-2',
            'Т3-гараж': 'от Б1 к ШВК-2', 'В1-ШВК1': 'КХ-10 → ШВК-1', 'Т3-ШВК1': 'от Б1 к ШВК-1',
            'Т3-М-1': 'от 1.6 к мойке М-1 (кольцо кухни)', 'Т4-М-1': 'от мойки М-1 к Н8 (кольцо кухни)',
            'КХ-9': 'к мойке М-1 (кухня)', 'Т4-ШВК2': 'от ШВК-2 → Пс-2 → Пс-1 → Н8',
            'Т4-ШВК1': 'от ШВК-1 → Н8',
            'В1-баня': 'от Ecoflex к ШВК-Б2', 'Т3-Б2': 'от Б2 к ШВК-Б2', 'В1-ПК-3': 'к ПК-3 (незамерзающий)',
            'В1-Б2': 'к Б2', 'В1-ШВК-Б1': 'от ввода Ecoflex к ШВК-Б1', 'Т3-ШВК-Б1': 'от Б2 к ШВК-Б1',
            'Т3-Д-б1': 'кольцо ШВК-Б1 → смеситель душа Д-б1', 'Т4-Д-б1': 'от душа Д-б1 → под мойку М-б1',
            'Т3-М-б1': 'от Б2 к мойке М-б1 (кольцо кухни)', 'Т4-б6': 'от мойки М-б1 → Н9 (кухня и ШВК-Б1)', 'Т4-ШВК-Б2': 'от ШВК-Б2 → Пс-б1.1, Пс-б1.2, Пс-б2 → Н9 → Б2'}
    L.crossed = []                                  # магистрали, подписанные с пересечением выносок
    order = [i for i in first if i in mains] + ['end'] + [i for i in mains if i not in first]
    for i in order:
        if i == 'end':                              # концы подводок у приборов и арматура колец
            end_labels(p, L, V, pipes)
            continue
        pp = P[i]
        best = None
        for a, b in zip(pp.pts, pp.pts[1:]):
            A, B = V.P(a), V.P(b)
            Lm = math.hypot(B[0] - A[0], B[1] - A[1])
            if best is None or Lm > best[0]:
                best = (Lm, A, B, a)
        Lm, A, B, a = best
        dn = SHORT.get(pp.dn, pp.dn) if pp.mat == 'pex' else pp.label()
        t = f'{pp.sys} {dn} — {DESC[pp.id]}' if pp.id in DESC else f'{SHOWN.get(pp.id, pp.id)}: {pp.sys} {dn}'
        pts = [(A[0] + (B[0] - A[0]) * tt, A[1] + (B[1] - A[1]) * tt) for tt in (0.5, 0.3, 0.7)]
        far = [(dx * r, dy * r * 0.8) for r in (45, 55, 70, 85)
               for dx, dy in ((1, -1), (-1, -1), (1, 1), (-1, 1), (0.4, -1), (-0.4, -1))]
        sb = f'ось {lev(a[2])}'
        if any(L.shelf(q, t, 1.8, sub=sb, strict=True) for q in pts):       # сначала — без пересечений выносок
            continue
        alt = []                                    # другие горизонтальные участки трубы (по убыванию длины)
        for a2, b2 in sorted(zip(pp.pts, pp.pts[1:]), key=lambda s_: -math.dist(V.P(s_[0]), V.P(s_[1]))):
            A2, B2 = V.P(a2), V.P(b2)
            if math.dist(A2, B2) >= 8.0 and abs(a2[2] - b2[2]) < 1e-6:
                alt += [((A2[0] + (B2[0] - A2[0]) * tt, A2[1] + (B2[1] - A2[1]) * tt), f'ось {lev(a2[2])}')
                        for tt in (0.5, 0.3, 0.7)]
        if any(L.shelf(q, t, 1.8, sub=sb2, strict=True) for q, sb2 in alt):
            continue
        if any(L.shelf(q, t, 1.8, cands=far, sub=sb2, strict=True)       # далее — дальние полки от любой точки
               for q, sb2 in [(q_, sb) for q_ in pts] + alt):
            continue
        L.crossed.append(i)
        if L.soft([(q, sb) for q in pts] + alt, t, 1.8):       # меньше всего пересечений
            continue
        for q in pts:
            if L.shelf(q, t, 1.8, sub=sb):
                break
        else:
            if not L.shelf(((A[0] + B[0]) / 2, (A[1] + B[1]) / 2), t, 1.8, cands=far, sub=sb):
                print('  !! нет места для подписи', t)
    sh.title((box[0] + box[2]) / 2, box[3] + 6, f'{title}. М 1:{V.K}', h=3.5)
    return p, L, V


NOTES10 = [
    'Схема — проекция 3D-модели (фронтальная изометрия, оси без сокращения). Отметки — оси труб от ±0,000 '
    'дома; у приборов — отметки присоединения.',
    'Трубы — PE-Xa по ГОСТ 32415 (классы эксплуатации ХВ и ГВС, PN10); соединения — только в шкафах ШВК-1, '
    'ШВК-2, у гребёнки КХ и у приборов (пресс- или надвижные гильзы). Диаметры — по П2.',
    'Т3 и Т4 — в изоляции 13 мм, В1 — 9 мм; в стенах и на выходах из пола — в гофре. Коллекторы подключены '
    'независимо (Заказчица 27.10.2026): В1 — своими выходами гребёнки (КХ-4 — ШВК-2, КХ-10 — ШВК-1), Т3 — от '
    'магистрали у Б1. Кольца ГВС (П4) — от каждого коллектора отдельно: Б1 → ШВК-2 (с/у 2.9) → Т4 → Пс-2 → Пс-1 → '
    'Н8 → Б1; Б1 → ШВК-1 (с/у 1.4) → Т4 → Н8 → Б1; кухня — от топочной минуя коллекторы: Б1 → мойка М-1 → Т4 → Н8 '
    '→ Б1. Балансировочные клапаны — на Т4 в шкафах ШВК-1, ШВК-2 и под мойкой; В1 кухни — КХ-9 гребёнки.',
    'Под потолком гаража — уклон водопровода не требуется; спуск — через краны коллекторов и гребёнки.',
    'Коллекторы ШВК-1, ШВК-2 — в санузлах, схемы на листе 13; водомерный узел и гребёнка КХ на 10 выходов — '
    'лист 7. Ввод — без приямка: под краем плиты и сквозь плиту в футляре ПЭ Ø75 (лист 14, узел 1). '
    'Поливочные краны ПК-1, ПК-2 — незамерзающие, шток 350 мм через стену (лист 14, узел 8).',
]
NOTES11 = [
    'Схема — проекция 3D-модели (фронтальная изометрия). Отметки — оси труб от ±0,000 бани.',
    'Холодная вода — от КХ-3 дома (25×3,5) по санитарной трубе Ecoflex Quattro 32×4,4 (L ≈ 17 м, ОВ лист 14), '
    'в бане — 25×3,5; переходы 25/32 — на концах санитарной трубы. Коллекторы подключены независимо (Заказчица '
    '27.10.2026): В1 — тройником у подъёма Ecoflex к ШВК-Б2 и отдельной линией к ШВК-Б1 (кран КЭ-3 в ШВК-Б1), '
    'Т3 — тройником у Б2 к каждому.',
    'Кольца ГВС (П4) — от каждого коллектора: Б2 → ШВК-Б2 (с/у б3) → Т4 → Пс-б1.1 → Пс-б1.2 → Пс-б2 → Н9 → '
    'клапан обратный → Б2; Б2 → ШВК-Б1 (ниша в стене помывочной б7) → смеситель душа Д-б1 (тройник петли) → Т4 → Н9 '
    '→ Б2; кухня — своё кольцо, как в доме (Заказчица 29.10.2026): Б2 → мойка М-б1 (тройник петли с краном под '
    'мойкой) → Т4 → Н9 → Б2. Балансировочные и обратные клапаны — на Т4 в шкафу ШВК-Б2 и в шкафу мойки М-б1 (Т4 '
    'кухни и Т4 кольца ШВК-Б1 — каждый со своими, тройник после них).',
    'Группа безопасности 6 бар и мембранный бак РБ-Б2 12 л — на подводе В1 к Б2; сброс ГБ — в воронку К1-ГБ-Б2. '
    'ПК-3 — кран незамерзающий, шток 350 мм через стену (лист 14, узел 8).',
]


def sewer(doc, sh, first=()):
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
        L.crossed = []
        for pp in sorted(pipes, key=lambda q: q.id not in first):     # трудные (с прошлого прохода) — первыми
            best = None
            for a, b in zip(pp.pts, pp.pts[1:]):
                A, B = V.P(a), V.P(b)
                Lm = math.hypot(B[0] - A[0], B[1] - A[1])
                if best is None or Lm > best[0]:
                    best = (Lm, A, B, a, b)
            Lm, A, B, a, b = best
            nm = DISP.get(pp.id, pp.id)
            if pp.sys == 'К1в':
                t, sub = f'{nm} Ø{pp.dn}', f'верх {lev(pp.pts[-1][2])}'
            elif pp.id == 'Ст.К1-2':
                t = f'{nm}, Ø{pp.dn}'
                sub = f'тройник Ø110×50 87,5° на {lev(VK.Z_ST2_TEE)}, заглушка +0,200'
            elif pp.where in ('ground', 'ceil') and VK.slope(pp) is None:      # вертикальный участок (низ стояка)
                t = f'{nm}, Ø{pp.dn}'
                sub = f'ось крестовины {lev(pp.pts[-1][2])}, лоток выпуска {lev(pp.pts[0][2] - pp.od / 2)}'
            elif pp.where == 'ceil' and VK.slope(pp) > 0.2:             # унитаз над сборным — 45° по вертикали
                t = f'{nm}: Ø{pp.dn}, косой тройник 45°'
                sub = f'лоток {lev(pp.pts[0][2] - pp.od / 2)} → {lev(pp.pts[-1][2] - pp.od / 2)}'
            elif pp.where in ('ground', 'ceil') or pp.where == 'floor' and VK.slope(pp):
                t = f'{nm}: Ø{pp.dn}, ' + (f'i={VK.i_txt(pp)}' if pp.id != 'К1-Ст1' else 'отвод и тройник 45°')
                sub = f'лоток {lev(pp.pts[0][2] - pp.od / 2)} → {lev(pp.pts[-1][2] - pp.od / 2)}'
            else:
                t, sub = f'{nm}: Ø{pp.dn}', None
            pts = [(A[0] + (B[0] - A[0]) * tt, A[1] + (B[1] - A[1]) * tt) for tt in (0.5, 0.3, 0.7, 0.15)]
            alt = []                                                    # другие участки той же трубы
            for a2, b2 in sorted(zip(pp.pts, pp.pts[1:]), key=lambda s_: -math.dist(V.P(s_[0]), V.P(s_[1])))[1:]:
                A2, B2 = V.P(a2), V.P(b2)
                if math.dist(A2, B2) >= 6.0:
                    alt += [(A2[0] + (B2[0] - A2[0]) * tt, A2[1] + (B2[1] - A2[1]) * tt) for tt in (0.5, 0.3, 0.7)]
            if not any(L.shelf(q, t, 1.7, sub=sub, strict=True) for q in pts + alt):   # сначала — без пересечений
                L.crossed.append(pp.id)
                if not L.soft([(q, sub) for q in pts], t, 1.7):
                    for q in pts:
                        if L.shelf(q, t, 1.7, sub=sub):
                            break
        fx = [k for k, f in VK.FIXT.items() if f.bld == bld and f.k1]
        done = set()
        for k in fx:
            # подъём к прибору (верх) или начало отвода прибора — по трубе, обслуживающей меньше всего приборов
            st = [pp for pp in pipes if pp.id.endswith('-ст') and (k in pp.serves or pp.name.startswith(f'Выпуск от {k} '))]
            src = [pp for pp in pipes if k in pp.serves and not pp.id.endswith('-ст')]
            if st:
                st = min(st, key=lambda pp: len(pp.serves))
                at, key = st.pts[-1], st.id
            elif src:
                br = min(src, key=lambda pp: len(pp.serves))
                at, key = br.pts[0], br.id
            else:
                continue
            if key in done:
                continue
            done.add(key)
            mk = ', '.join(x for x in fx if x == k or (x in getattr(st if st else br, 'serves', []) and x != k))
            L.shelf(V.P(at), mk, 1.8, cands=[(4, 4), (-4, 4), (4, -4), (-4, -4), (7, 7), (-7, 7), (10, 4), (-10, 4),
                                            (10, -4), (-10, -4)])
        sh.s.text(f'{title}. М 1:{V.K}', (box[0] + box[2]) / 2, box[3] + 3, h=3.0, align='center')
        res.append((V, L))
    p.crossed = [c for _, L in res for c in L.crossed]
    return p


DISP = {'К1в-1': 'Ст.К1-1в', 'К1в-б': 'Ст.К1-б (О-блоки)', 'Ст.К1-б': 'низ Ст.К1-б: двухплоскостная крестовина и 2 отвода 45°',
        'К1-бв': 'Выпуск К1-бв (стояк → КК-1)', 'К1-б': 'К1-б сборный (Д-б1 → КК-1)', 'К1-СПА': 'К1 от слива СПА',
        'К1-ГБ-Б2': 'К1 от сброса ГБ Б2', 'К1-ГБ-Б2-ст': 'воронка ГБ Б2', 'К1-сиф14': 'К1 от сифона конденсата (1.4)',
        'К1-сиф14-ст': 'подъём к сифону конденсата (1.4)', 'К1-сиф29': 'К1 от сифона конденсата К-4…К-6 (2.9)',
        'К1-сиф29в': 'К1 от сифона конденсата К-7 (2.9)', 'К1-1.6': 'К1-1.6 (Т-1, СМ-1, УМ-4)',
        'К1-б-ст': 'подъём к трапу Д-б1', 'К1-1.4': 'К1-1.4 в полу 1.4 → Ст.К1-2',
        'Ст.К1-2': 'Ст.К1-2 — вывод прочистки в стене 1.4/1.9'}

NOTES12 = [
    'Схемы — проекции 3D-модели (фронтальная изометрия). Отметки — лотки труб; верх вытяжных частей — от '
    '±0,000 своего здания.',
    'Сеть 1 этажа дома и сеть бани — в грунте под плитой (решение Заказчика), кроме отводов Ø50 с/у 1.4 (УМ-1, Д-1, '
    'сифон конденсата): они — в пироге пола над плитой, через косую крестовину 45° в тройник Ø110×50 на выводе '
    'прочистки Ст.К1-2 (Заказчица 29.10.2026); К1 2 этажа — под потолком гаража к Ст.К1-1. Внутри зданий (стояки, вытяжные части, короб гаража, отводы 2 этажа и подъёмы к приборам) — '
    'бесшумные трубы и фасонные части (опросный лист, ВК.СО). Лоток гаража — в К2 (лист 6).',
    'Уклоны: Ø110 — 0,02 (сборный К1-1 — 0,015), Ø50 — 0,03 (отвод мойки М-б1 — 0,02 = 1/d), конденсат Ø32 — '
    'не менее 0,02 (П3). Отводы от приборов — с уклоном к сборным.',
    'Ст.К1-1в, Ст.К1-б — над кровлей на 0,35 м (п. 18.18), зонт и флюгарку не устанавливать (п. 18.21).',
    'Ревизии (Р) и прочистки (П) — по п. 18.26 и табл. 18.1, шаг прочисток Ø110 — не более 10 м: ревизии на стояках '
    'Ст.К1-1 и Ст.К1-б — за люками в стенах, ревизия в начале сборного под потолком гаража — люк 600×600 в '
    'подшивке, прочистки сборных в грунте — тройниками 45° с выводом в стену к люку (лист 14, узел 5), люков в полу нет.',
    'Стояки — в стенах, в газобетонных О-блоках с отверстием Ø160 (решение Заказчицы, ТЗ-1); Ст.К1-б — в '
    'перегородке б2/б3, расширенной до 250 мм. Присоединения — косыми тройниками 45° (выпуски 2 этажа к сборному под '
    'потолком гаража — тоже, Заказчица 27.10.2026); низ Ст.К1-1 — отвод 45° и косой тройник 45° (стояк над сборным); '
    'низ Ст.К1-б — двухплоскостная крестовина Ø110 (УН-б1 с востока; мойка М-б1 и сброс ГБ Б2 с севера) и два '
    'отвода 45° в выпуск К1-бв (п. 18.4).',
    'Баня — две прямые линии в КК-1: К1-б — сборный от Д-б1 с прочисткой в стене б6/б8 (О-блоки, 250 мм) и поворотом '
    '60° в б6 отводами 45° + 15°; К1-бв — выпуск от Ст.К1-б. СПА — свой выпуск Ø50 с сифоном (лист 9); К1-ГБ-Б2 — '
    'сброс группы безопасности Б2 через воронку в выгородке Б2 в отвод мойки.',
    'Выпуски К1-1 (в ДК5-018), К1-б и К1-бв (в КК-1, далее в сборный К1-1 дома) — продолжение во дворе по НВК.',
]

if __name__ == '__main__':
    no = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    doc = new_doc()
    setup(doc)
    sh = RDSheet(doc, 'Лист', VK_LIST[no], no, VK_TOTAL, fmt='А2', code=CODE_VK, bld=BLD_VK)
    if no in (10, 11):
        bld = 'h' if no == 10 else 'b'
        ttl = f'Схема систем В1, Т3, Т4 {"дома" if no == 10 else "бани"} (фронтальная изометрия)'
        d0 = new_doc()                                  # пробный проход: какие магистрали не нашли чистого места
        setup(d0)
        s0 = RDSheet(d0, 'Лист', VK_LIST[no], no, VK_TOTAL, fmt='А2', code=CODE_VK, bld=BLD_VK)
        first = water(d0, s0, bld, ttl)[1].crossed      # их подписываем первыми
        water(doc, sh, bld, ttl, first=first)
        sh.notes(28, 62, 370, NOTES10 if no == 10 else NOTES11, h=1.9, spacing=1.0)
    else:
        d0 = new_doc()
        setup(d0)
        s0 = RDSheet(d0, 'Лист', VK_LIST[no], no, VK_TOTAL, fmt='А2', code=CODE_VK, bld=BLD_VK)
        sewer(doc, sh, first=sewer(d0, s0).crossed)
        sh.notes(402, 170, 182, NOTES12, h=1.9, spacing=1.0)
    finish_layers(doc)
    print(save_and_pdf(doc, os.path.join(OUT, f'vk_axo_{no}.dxf')))
