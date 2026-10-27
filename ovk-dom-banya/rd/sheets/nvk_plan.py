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
                      draw_well, flow_arrow, north_arrow, alev, data, msk, well_r, VLabels, PP, unit, in_box)

OUT = os.path.join(ROOT, 'out')
K = 200
MX, MY = 13.0, 7.0
BX = (30.0, 120.0, 250.0, 400.0)               # окно плана на листе, мм (44 × 56 м)
EXIST = {   # существующие поселковые сети (ИС ООО «Лика» в осях дома)
    'К1': {'pts': [(-9.0, -16.76), (1.39, -16.74), (10.40, -16.66), (34.0, -16.62)], 'mark': 'К1',
           'name': 'К1 сущ. Корсис Ø160 (ИС-3КК)'},
    'К1в': {'pts': [(9.42, -3.85), (10.40, -16.66)], 'mark': 'К1', 'name': 'Ø110 (ИС-3КК)'},
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
            p.pipe(part, 'НВК_сущ', mark=e['mark'], every=34.0, h=1.6, ltype='ОВ_ШТРИХ')
            for a, b in zip(part, part[1:]):
                L.segs.append((a, b))
    for nm, (x, y), sub in EXIST_WELLS:
        c = V.P((x, y, 0))
        if not in_box(c, box):
            continue
        p.circle(c[0], c[1], 0, 'НВК_сущ', r_paper=2.5)
        p.circle(c[0], c[1], 0, 'НВК_сущ', r_paper=1.1)


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
    # подписи зданий и ±0,000
    for (x, y), t, sub in (((10.0, 8.3), 'Жилой дом', f'±0,000 = {alev(M.H0)}'),
                           ((11.0, 28.2), 'Баня', f'±0,000 = {alev(M.H0B)}')):
        c = V.P((x, y, 0))
        p.t(c[0], c[1] + 1.5, t, 3.0, 'center', 'НВК_марки')
        p.t(c[0], c[1] - 2.5, sub, 2.2, 'center', 'НВК_марки')
        L.block((c[0] - 14, c[1] - 4.5, c[0] + 14, c[1] + 4.5))
    pipes = net(p, V, box, L, D)
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
    L.shelf(kb, 'КБ — колонка садовая с краном', 1.9, sub='сезонная, слив через КП-1')
    # подписи колодцев
    for w in D['wells']:
        c = V.P((w['x'], w['y'], 0))
        r = well_r(w, V)
        cands = [(r + 2, r + 2), (-r - 2, r + 2), (r + 2, -r - 2), (-r - 2, -r - 2), (r + 5, 0.5), (-r - 5, 0.5),
                 (r + 8, r + 7), (-r - 8, r + 7), (r + 8, -r - 7), (-r - 8, -r - 7)]
        sub = f'к {alev(w["cover"])}' if w['cover'] else None
        L.shelf(c, w['id'] + (' (сущ.)' if w['exist'] else ''), 2.0, cands=cands, sub=sub)
    for nm, (x, y), sub in EXIST_WELLS:
        c = V.P((x, y, 0))
        if in_box(c, box):
            L.shelf(c, f'{nm} (сущ.)', 1.8, sub=sub)
    # подписи участков
    drop = {pid: z - M.DK.bottom for pid, z in [(pp_.id, z_) for pp_, z_ in M.DK.ins]}
    kbt = [M.PLAN_Z - M.kb_line.top(s_) for s_ in (0.0, M.kb_line.length())]
    KB_D = (alev(min(kbt), 2), alev(max(kbt), 2))
    LBL = {
        'К1-1н': (f'К1-1 Ø110 ПП SN8, i=0,02, L={alev(M.k1h.length(), 1)} м', f'перепад в ДК5-018 {alev(drop["К1-1н"])} м'),
        'К1-бн': ('К1-б и К1-бв Ø110 ПП SN8, i=0,015',
                  f'от бани в КК-1, L={alev(M.k1b.length(), 1)} и {alev(M.k1be.length(), 1)} м'),
        'К1-б1': (f'К1 Ø110 ПП SN8, i=0,015, L={alev(M.k12.length(), 1)} м', 'от КК-1 к вводу в дом (ВК)'),
        'В1-н': (f'В1 ПЭ 100 SDR11 32×3,0, L={alev(M.v1.length(), 1)} м', 'глубина 1,6 м, у ввода — утепл. и кабель'),
        'КХ-8н': ('В1 (КХ-8) ПЭ 25, L=2,5 м', 'сезонная, слив в КП-1'),
        'К2-ЛК': (f'К2 ПЭ Ø63, i=0,02, L={alev(M.s_out.length(), 2)} м', 'врезка в сущ. выпуск ЛК Ø63'),
        'Др-1/2': ('Др Ø110 перф. i=0,003 + К2 Ø110 i=0,005', 'в общей траншее, К2 выше'),
        'Др-1/4': ('Др Ø110 перф. i=0,003 + К2 Ø110 i=0,005', None),
        'ДрБ-1/2': ('Др Ø110 перф. + К2 Ø110, i=0,005', 'вокруг бани'),
        'Др-Т': ('Др и К2 Ø110 — транзит от бани', 'i=0,005, L=6,3 м'),
        'К2-1н': ('К2 Ø110 от лотка гаража', 'утеплить, присоед. к кольцу К2'),
        'В1-Бс': (f'В1 ПЭ 25 от КП-1 к колонке КБ, L={alev(M.kb_line.length(), 0)} м',
                  f'сезонная, i=0,003 к КП-1, гл. {KB_D[0]}–{KB_D[1]} м до верха'),
    }
    for pp in pipes:
        if pp['id'] not in LBL:
            continue
        txt, sub = LBL[pp['id']]
        # точка подписи — середина самого длинного звена в окне
        best = None
        for a, b in zip(pp['pts'], pp['pts'][1:]):
            A, B = V.P((a[0], a[1], 0)), V.P((b[0], b[1], 0))
            Lm = math.dist(A, B)
            if best is None or Lm > best[0]:
                best = (Lm, ((A[0] + B[0]) / 2, (A[1] + B[1]) / 2))
        at = best[1]
        cands = None
        if pp['id'] == 'К1-б1':
            cands = [(-6, 0.3), (-14, 0.3), (-24, 0.3), (-30, 4), (-30, -4), (8, -6), (8, 6)]
        if pp['id'] == 'К1-бн':
            cands = [(dx, dy) for dy in (-4, -7, 4, 8, 12) for dx in (-10, -16, -22, 10, 16, 22)]
        if pp['id'] == 'В1-Бс':
            L.shelf(V.P((M.KB[0], 26.3, 0)), txt, 1.9, sub=sub, force=(6, 2))
            continue
        r_ = L.shelf(at, txt, 1.9, sub=sub, cands=cands) if cands else L.shelf(at, txt, 1.9, sub=sub)
        if r_ is None:
            print('  !! нет места для подписи', pp['id'], at)
    # теплотрасса ОВ и футляры — подписи
    for e in D.get('ext', []):
        a_, b_ = e['pts'][1], e['pts'][2]
        grid = sorted(((dx, dy) for dx in range(-40, 41, 3) for dy in range(-16, 17, 2) if abs(dx) >= 4),
                      key=lambda d: abs(d[0]) + 1.5 * abs(d[1]))
        for t in (0.62, 0.5, 0.75, 0.4, 0.85, 0.3):
            c = V.P((a_[0] + (b_[0] - a_[0]) * t, a_[1] + (b_[1] - a_[1]) * t, 0))
            if L.shelf(c, 'Т1, Т2 — теплотрасса Ecoflex (ОВ, лист 14)', 1.9,
                       sub=f'прямая, ниже Др: верх ≤ {alev(M.ECO_TOP)}', cands=grid) is not None:
                break
        else:
            print('  !! нет места для подписи теплотрассы')
    for sx in M.cross_s(M.kb_line, M.k12):
        q = M.kb_line.at(sx)
        if L.shelf(V.P((q[0], q[1], 0)), 'В1-Бс над К1-б1 — в футляре', 1.9, sub='ПНД Ø63, по 2 м в стороны',
                   cands=[(-14, 4), (-18, 4)] + [(dx, dy) for dy in (-3, -8, -14, -20, 8, 14) for dx in (6, 12, 20, -6, -12, -30, -45)]) is None:
            print('  !! нет места для подписи футляра над К1-б1')
    # граница участка
    c = V.P((-4.2, 26.0, 0))
    L.shelf(c, 'Граница з/у 50:08:0050209:1600', 1.9, sub='(з/у 19, ул. Лесная)', cands=[(6, 6), (6, -6), (8, 14)])
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
                ['К1', 'ДК5-018 (дворовый колодец з/у)', 'к 186,750 / 186,78; лоток 185,019 / 184,98',
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
        'К1-бв — от стояка Ст.К1-б) через колодец КК-1 в сборный дома К1-1 (ВК) с уклоном 0,015, выпуск К1-1 (дом '
        'и баня) в ДК5-018 — 0,02 (П1). КК-1 — полимерный Ø630 с двумя входами '
        f'с лотком и телескопической шахтой. Заезды вдоль западного и восточного заборов (Заказчик): в полосе '
        f'{alev(M.DRIVE_W, 1)} м и перед гаражом — люки Т (C250), засыпка песком на всю глубину (Купл ≥ 0,95).',
        'Др — перфорированная труба Ø110 в геотекстиле в щебне 20–40 под утеплённой отмосткой зданий, колодцы '
        'Ø315; К2 — ПП SN8 Ø110 в той же траншее выше дренажа (лотки — листы 5, 6). Выпуски К2 из стен (стояки '
        'внутренних водостоков) присоединяются к кольцу К2 косыми тройниками — места по привязке воронок.',
        'Дренаж и К2 — в КЛ-1 (ж/б Ø1500, отстойная часть 0,5 м, регулирующий объём — П2): К2-Б с запада, К2-К '
        'с севера, дренаж Др-К — с северо-запада, между ними, без пересечения с К2, через обратный клапан. КЛ-1 — '
        'восточнее пандуса гаража, у южной границы участка, на существующем выпуске ЛК Ø63 (Заказчица 27.10.2026): '
        'выпуск КЛ-1 — врезка в существующую трубу электросварной муфтой Ø63 за южной стенкой колодца, существующий '
        f'выпуск севернее врезки (≈{alev(M.LK_DEMO, 1)} м, в котловане КЛ-1) — демонтировать. Колодец — в зоне площадки '
        'перед гаражом: дорожная плита и чугунный люк тяжёлого типа Т (C250), крышка в уровне покрытия.',
        'Утепление — плиты ЭППС 50 мм шириной 1,2 м над трубой, где глубина меньше нормы (п. 6.2.4 '
        'СП 32.13330.2018): ' + ', '.join(pp_.id for pp_ in M.PIPES if pp_.ins and pp_.sys != 'В1') +
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
    w2, h2 = (FB[2] - FB[0]) / 10.0, (FB[3] - FB[1]) / 10.0
    a, c = V0.P((FM[0] - w2 / 2, FM[1] - h2 / 2, 0)), V0.P((FM[0] + w2 / 2, FM[1] + h2 / 2, 0))
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
    for w in D['wells']:
        cc = V.P((w['x'], w['y'], 0))
        if not in_box(cc, b):
            continue
        r = well_r(w, V)
        ins = ', '.join(sorted(set(alev(z) for _, z in w['ins'])))
        outs = ', '.join(sorted(set(alev(z) for _, z in w['outs'])))
        sub = (f'вх. {ins}' if ins else '') + (f'; вых. {outs}' if outs else '')
        if w['exist']:
            sub = f'к 186,78; лоток {alev(w["bottom"])}'
        cands = [(r + 3, r + 4), (-r - 3, r + 4), (r + 3, -r - 4), (-r - 3, -r - 4), (r + 10, r + 12),
                 (-r - 10, r + 12), (r + 10, -r - 12), (-r - 10, -r - 12)]
        if w['id'] == 'КЛ-1':                     # справа внизу, правее линии сущ. выпуска ВК (выше — размер)
            cands = [(16.5, -3.0), (17.0, -3.4), (19.5, -8.2)] + cands
        L.shelf(cc, f'{w["id"]}' + (' (сущ.)' if w['exist'] else f', к {alev(w["cover"])}'), 1.9, sub=sub or None,
                cands=cands)
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
           (DR_IN, 'Ввод Др в КЛ-1 —', 'через обратный клапан', [(-12, 0), (-12, -2), (-12, 2)]),
           (next(c['xy'] for c in M.crossings() if c['up'] == 'К1-1н'), 'К1 над Др и К2:', 'зазоры ' + ' и '.join(
               alev(c['gap']) for c in M.crossings() if c['up'] == 'К1-1н') + ' м'),
           ((M.vk_end('К1-1')[0], M.vk_end('К1-1')[1]), 'Выпуск К1-1 (ВК)', f'лоток {alev(M.vk_end("К1-1")[2])}')]
    for (x, y), t, sub, *cn in det:
        cc = V.P((x, y, 0))
        if L.shelf(cc, t, 1.8, sub=sub, cands=(cn[0] + default_cands()) if cn else None) is None:
            raise SystemExit(f'НВК лист 3, фрагмент: нет места для выноски «{t}»')
    # привязки к осям 5 и А
    kl = V.P((M.KL1.x, M.KL1.y, 0))
    ax5 = V.P((20.0, 0.0, 0))
    yb = b[3] - 9
    dim_h(p, ax5[0], kl[0], yb - 7, yref0=None, yref1=None, txt=f'{int(round((M.KL1.x - 20.0) * 1000))}')
    wx = V.P((M.X_W, -1.0, 0))
    dim_h(p, ax5[0], wx[0], yb, txt=f'{int(round((M.X_W - 20.0) * 1000))}')
    dk = V.P((9.42, -3.85, 0))
    dim_v(p, ax5[1], kl[1], b[2] - 2.5, txt=f'{int(round(-M.KL1.y * 1000))}')
    dim_v(p, ax5[1], dk[1], b[0] + 10, txt='3850')
    p.t(FB[0], FB[3] + 4.0, 'Фрагмент 1. Южная часть участка. М 1:100', 2.8, 'left', 'НВК_текст')   # правее — кружок оси 5


if __name__ == '__main__':
    print(main())
