"""И05.09.26-НВК, листы 4–7: продольные профили (из модели nvk_model).

4 — К1: выпуск бани → КК-1 → КК-2 → КК-3 → ДК5-018; выпуск дома → ДК5-018.
5 — Др и К2 дома: Др-1 → Др-2 → Др-3 → КЛ-1; Др-1 → Др-4 → Др-3.
6 — Др и К2 бани: ДрБ-1 → ДрБ-2 → ДрБ-3 → Др-2 (транзит); ДрБ-1 → ДрБ-4 → ДрБ-3; КЛ-1 → выпуск ЛК; К2-1.
7 — В1: выпуск ВК → ЗУ-1 → ввод; КХ-8 → КП-1.

python3 sheets/nvk_prof.py 4|5|6|7
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from rdbase import new_doc, RDSheet, save_and_pdf  # noqa: E402
import nvk_model as M  # noqa: E402
from nvk_draw import (CODE_NVK, BLD_NVK, NVK_LIST, NVK_TOTAL, setup, finish, alev, PP, Profile)  # noqa: E402

OUT = os.path.join(ROOT, 'out')
P = {p.id: p for p in M.PIPES}
W = {w.id: w for w in M.WELLS}
for _p in M.PIPES:
    M.frost_check(_p)
CROSS = {(c['up'], c['down']): c['gap'] for c in M.crossings()}
CR = M.crossings()


def xmarks(route, other, text):
    """Пересечения трубы other с трубами трассы route: [(s по трассе, (подпись, отметка other))]."""
    out = []
    for c in CR:
        if other not in (c['up'], c['down']):
            continue
        up = c['up'] == other
        mine, s_mine = (c['down'], c['s_dn']) if up else (c['up'], c['s_up'])
        parts = [q for q in route.parts if q['pid'] == mine]
        if not parts:
            continue
        base = min(q['s0'] for q in parts)
        out.append((base + s_mine, (text.format(gap=alev(c['gap'])), c['z_up'] if up else c['z_dn'])))
    return out
DROP = {pp.id: z - M.DK.bottom for pp, z in M.DK.ins}


def drive_ids(kind):
    return ', '.join(w.id for w in M.WELLS if w.kind == kind and w.drive)


def calc():
    import json
    return json.load(open(os.path.join(M.OUT, 'nvk_calc.json')))
for _p in M.PIPES:
    M.frost_check(_p)
LAYER = {'К1': 'НВК_К1', 'К2': 'НВК_К2', 'Др': 'НВК_Др', 'В1': 'НВК_В1'}
LT = {'Др': 'ОВ_ШТРИХ'}


def f2(v):
    return f'{v:.2f}'.replace('.', ',')


class Route:
    """Трасса профиля: последовательность труб модели (по ходу), длина по плану и функция s → (x, y)."""

    def __init__(self, ids, rev=()):
        self.parts = []
        s = 0.0
        for pid in ids:
            p = P[pid]
            pts = list(p.pts)
            zs = list(p.z)
            if pid in rev:
                pts, zs = pts[::-1], zs[::-1]
            for a, b, z0, z1 in zip(pts, pts[1:], zs, zs[1:]):
                L = math.dist(a, b)
                if L < 1e-6:                    # вертикальный подъём (В1 у ввода)
                    self.parts.append(dict(pid=pid, s0=s, s1=s, a=a, b=b, z0=z0, z1=z1, p=p))
                    continue
                self.parts.append(dict(pid=pid, s0=s, s1=s + L, a=a, b=b, z0=z0, z1=z1, p=p))
                s += L
        self.L = s

    def xy(self, s):
        for q in self.parts:
            if q['s1'] > q['s0'] and q['s0'] - 1e-9 <= s <= q['s1'] + 1e-9:
                t = (s - q['s0']) / (q['s1'] - q['s0'])
                return (q['a'][0] + (q['b'][0] - q['a'][0]) * t, q['a'][1] + (q['b'][1] - q['a'][1]) * t)
        q = self.parts[-1]
        return q['b']

    def z(self, s):
        for q in self.parts:
            if q['s1'] > q['s0'] and q['s0'] - 1e-9 <= s <= q['s1'] + 1e-9:
                t = (s - q['s0']) / (q['s1'] - q['s0'])
                return q['z0'] + (q['z1'] - q['z0']) * t
        return self.parts[-1]['z1']


def node_marks(pr, nodes, route, rows_val):
    """Подписи значений в узлах (вертикальный текст)."""
    for n in nodes:
        s = n['s']
        for row, val in rows_val(n).items():
            if val:
                pr.vtext(row, s, val)
            pr.tick(row, s) if row != 'Колодец (точка)' else None


def draw_profile(p, x0, y0, title, route, nodes, Kh, Kv, sysk, second=None, zc=None, zt=None, rows=None,
                 axis=False, label_pipe=None, crossings=()):
    """Профиль трассы route; nodes — [{s, name, well?, zin, zout}], second — вторая труба в той же траншее
    (Route, система). Возвращает Profile."""
    zs = [q['z0'] for q in route.parts] + [q['z1'] for q in route.parts]
    gmax = max(max(M.g_design(*route.xy(s)), M.g_exist(*route.xy(s))) for s in [k * route.L / 40 for k in range(41)])
    if second:
        zs += [q['z0'] for q in second[0].parts] + [q['z1'] for q in second[0].parts]
    zmin = min(zs) - (0.6 if not axis else 0.3)
    zc = zc if zc is not None else math.floor(zmin * 2) / 2
    zt = zt if zt is not None else gmax + 0.25
    pr = Profile(p, x0, y0, route.L, Kh, Kv, zc, zt, rows=rows)
    pr.table()
    # земля
    gd = lambda s: M.g_design(*route.xy(s))      # noqa: E731
    ge = lambda s: M.g_exist(*route.xy(s))       # noqa: E731
    pr.ground(ge, 0, route.L, layer='НВК_грунт', ltype='ОВ_ШТРИХ', step=max(0.1, route.L / 120))
    pts = pr.ground(gd, 0, route.L, layer='НВК_земля', step=max(0.1, route.L / 120))
    # штриховка земли под проектной линией (узкая полоса)
    for (xa, ya), (xb, yb) in zip(pts[::3], pts[3::3]):
        p.line(xa, ya, xa - 1.0, ya - 1.6, 'НВК_грунт')
    # трубы
    lay = LAYER[sysk]
    for q in route.parts:
        od = q['p'].od
        if q['s1'] == q['s0']:                    # подъём
            x = pr.X(q['s0'])
            for dx in (-od / 2 * 1000 / Kv, od / 2 * 1000 / Kv):
                p.line(x + dx, pr.Y(q['z0']), x + dx, pr.Y(q['z1']), lay)
            continue
        pr.pipe_line(q['s0'], q['z0'], q['s1'], q['z1'], od, lay, ltype=LT.get(sysk), axis=axis)
    if second:
        r2, s2 = second
        for q in r2.parts:
            pr.pipe_line(q['s0'], q['z0'], q['s1'], q['z1'], q['p'].od, LAYER[s2], ltype=LT.get(s2))
    # утепление: полоса над трубой
    for q in route.parts:
        p_ = q['p']
        for a, b in p_.ins:
            for s_ in (a, b):
                pass
    for pid in {q['pid'] for q in route.parts}:
        p_ = P[pid]
        if not p_.ins:
            continue
        # участки утепления по длине трубы → по трассе
        base = min(q['s0'] for q in route.parts if q['pid'] == pid)
        for a, b in p_.ins:
            sa, sb = base + a, base + min(b, p_.length())
            za, zb = route.z(sa) + (p_.od if not axis else p_.od / 2) + 0.15, route.z(sb) + (p_.od if not axis else p_.od / 2) + 0.15
            p.pl([(pr.X(sa), pr.Y(za)), (pr.X(sb), pr.Y(zb))], 'НВК_утепл', lw=70)
            p.t((pr.X(sa) + pr.X(sb)) / 2, pr.Y(max(za, zb)) + 1.2, 'ЭППС 50', 1.6, 'bc', 'НВК_утепл')
    # пересечения
    for s_, txt in crossings:
        p.circle(pr.X(s_), pr.Y(txt[1]), 0, 'НВК_марки', r_paper=1.0)
        p.t(pr.X(s_) + 1.5, pr.Y(txt[1]) + 1.5, txt[0], 1.7, 'bl', 'НВК_марки')
    # колодцы и узлы
    for n in nodes:
        w = n.get('well')
        if w is not None:
            zb = w.bottom if w.bottom else min(n.get('zin') or 9e9, n.get('zout') or 9e9) - 0.10
            cov = w.cover
            pr.well(n['s'], cov, zb, min(w.dn, 1500), label=n['name'], exist=w.exist)
        else:
            x = pr.X(n['s'])
            p.line(x, pr.yt, x, pr.Y(gd(n['s'])), 'НВК_профиль', ltype='ОВ_ШП')
            if n.get('top', True):
                p.t(x, pr.Y(gd(n['s'])) + 3.0, n['name'], 2.0, 'bc', 'НВК_марки')
    # таблица: значения
    for n in nodes:
        s = n['s']
        pr.vtext('Отметка земли проектная', s, f2(gd(s)))
        pr.vtext('Отметка земли фактическая', s, f2(ge(s)))
        zin, zout = n.get('zin'), n.get('zout')
        zt_ = f2(zin) if zin is not None else ''
        if zout is not None and (zin is None or abs(zout - zin) > 0.004):
            zt_ = (zt_ + ' / ' if zt_ else '') + f2(zout)
        cand = [r for r, _ in pr.rows if r == f'Отметка лотка {sysk}']
        rowz = cand[0] if cand else [r for r, _ in pr.rows if r.startswith('Отметка лотка') or
                                     r.startswith('Отметка оси')][0]
        pr.vtext(rowz, s, zt_)
        if n.get('z2') is not None:
            rows2 = [r for r, _ in pr.rows if r.startswith('Отметка лотка К2')]
            if rows2:
                pr.vtext(rows2[0], s, f2(n['z2']))
        zref = min(v for v in (zin, zout) if v is not None)
        drow = [r for r, _ in pr.rows if r.startswith('Глубина')][0]
        pr.vtext(drow, s, f2(gd(s) - zref))
        for r, _ in pr.rows:
            if r != 'Колодец (точка)' and not r.startswith('Материал'):
                pr.tick(r, s)
        y0_, y1_ = pr.row_y('Колодец (точка)')
        p.t(pr.X(s) + 0.8, (y0_ + y1_) / 2, n['name'], 1.7, 'center', 'НВК_текст', rot=90)
        pr.tick('Колодец (точка)', s)
    # уклоны и длины, расстояния
    ss = [n['s'] for n in nodes]
    for a, b in zip(ss, ss[1:]):
        if b - a < 0.05:
            continue
        mid = [q for q in route.parts if q['s0'] - 1e-6 <= (a + b) / 2 <= q['s1'] + 1e-6 and q['s1'] > q['s0']]
        q = mid[0]
        i = q['p'].i if q['p'].i is not None else (q['z0'] - q['z1']) / (q['s1'] - q['s0'])
        y0_, y1_ = pr.row_y('Уклон, ‰ / длина, м')
        xa, xb = pr.X(a), pr.X(b)
        if abs(i) < 1e-4:
            p.line(xa, (y0_ + y1_) / 2, xb, (y0_ + y1_) / 2, 'НВК_профиль')
        elif i > 0:
            p.line(xa, y1_, xb, y0_, 'НВК_профиль')
        else:
            p.line(xa, y0_, xb, y1_, 'НВК_профиль')
        txt_i = f'{abs(i) * 1000:.0f}' if not axis else (f'{abs(i) * 1000:.0f}' if abs(i) > 0.0005 else '0')
        if xb - xa > 12:
            p.t((xa + xb) / 2, y1_ - 2.2, txt_i, 1.8, 'center', 'НВК_текст')
            p.t((xa + xb) / 2, y0_ + 2.2, f2(b - a), 1.8, 'center', 'НВК_текст')
        else:
            p.t((xa + xb) / 2, (y0_ + y1_) / 2, f'{txt_i}/{f2(b - a)}', 1.5, 'center', 'НВК_текст', rot=90)
        pr.ctext('Расстояние, м', a, b, f2(b - a), h=1.8 if xb - xa > 9 else 1.4)
        pr.tick('Расстояние, м', a)
        pr.tick('Расстояние, м', b)
    if label_pipe:
        y0_, y1_ = pr.row_y('Материал, диаметр, основание')
        p.t((pr.X(0) + pr.X(route.L)) / 2, (y0_ + y1_) / 2, label_pipe, 1.9, 'center', 'НВК_текст')
    p.t(x0 + (pr.HEAD_W + route.L * 1000 / Kh) / 2, pr.Y(zt) + 6.0, title, 2.8, 'center', 'НВК_текст')
    return pr


ROWS_K1 = [('Материал, диаметр, основание', 7.0), ('Отметка земли проектная', 10.0),
           ('Отметка земли фактическая', 10.0), ('Отметка лотка трубы', 14.0), ('Глубина заложения лотка', 9.0),
           ('Уклон, ‰ / длина, м', 8.0), ('Расстояние, м', 6.0), ('Колодец (точка)', 13.0)]
ROWS_DR = [('Материал, диаметр, основание', 7.0), ('Отметка земли проектная', 9.0),
           ('Отметка земли фактическая', 9.0), ('Отметка лотка К2', 10.0), ('Отметка лотка Др', 12.0),
           ('Глубина заложения Др', 9.0), ('Уклон, ‰ / длина, м', 8.0), ('Расстояние, м', 6.0),
           ('Колодец (точка)', 13.0)]
ROWS_V = [('Материал, диаметр, основание', 7.0), ('Отметка земли проектная', 10.0),
          ('Отметка земли фактическая', 10.0), ('Отметка оси трубы', 13.0), ('Глубина до низа трубы', 9.0),
          ('Уклон, ‰ / длина, м', 8.0), ('Расстояние, м', 6.0), ('Колодец (точка)', 13.0)]
ROWS_S = ROWS_K1


def well_node(route, s, w, zin=None, zout=None, z2=None):
    return dict(s=s, name=w.id, well=w, zin=zin, zout=zout, z2=z2)


def sheet4(sh, p):
    r = Route(['К1-бн', 'К1-б1', 'К1-б2', 'К1-б3'])
    s1 = P['К1-бн'].length()
    s2 = s1 + P['К1-б1'].length()
    s3 = s2 + P['К1-б2'].length()
    s4 = s3 + P['К1-б3'].length()
    nodes = [dict(s=0.0, name='вып. К1-б', zout=P['К1-бн'].z[0]),
             well_node(r, s1, W['КК-1'], P['К1-бн'].z[-1], P['К1-б1'].z[0]),
             well_node(r, s2, W['КК-2'], P['К1-б1'].z[-1], P['К1-б2'].z[0]),
             well_node(r, s3, W['КК-3'], P['К1-б2'].z[-1], P['К1-б3'].z[0]),
             well_node(r, s4, W['ДК5-018'], P['К1-б3'].z[-1], None)]
    nodes[-1]['zout'] = W['ДК5-018'].bottom
    draw_profile(p, 28, 150, 'Профиль сети К1: выпуск бани → КК-1 → КК-2 → КК-3 → ДК5-018. '
                 'Масштабы: гор. 1:200, верт. 1:50', r, nodes, 200, 50, 'К1', rows=ROWS_K1,
                 label_pipe='ПП SN8: Ø110 до КК-1, далее Ø160; песчаное основание 100 мм, обсыпка 300 мм',
                 crossings=xmarks(r, 'В1-Бс', 'В1-Бс выше на {gap} м — в футляре ПНД Ø63'))
    r2 = Route(['К1-1н'])
    n2 = [dict(s=0.0, name='вып. К1-1', zout=P['К1-1н'].z[0]),
          well_node(r2, r2.L, W['ДК5-018'], P['К1-1н'].z[-1], W['ДК5-018'].bottom)]
    draw_profile(p, 28, 12, 'Выпуск дома К1-1 → ДК5-018. Гор. 1:50, верт. 1:50', r2, n2, 50, 50, 'К1',
                 rows=ROWS_K1, label_pipe='ПП SN8 Ø110',
                 crossings=[(0.20, (f'Др, К2 ниже: {alev(CROSS[("К1-1н", "Др-4/3")])} / '
                                    f'{alev(CROSS[("К1-1н", "К2-Б")])} м', P['К1-1н'].z[0] - 0.12))])
    k1_ins = any(P[i].ins for i in ('К1-1н', 'К1-бн', 'К1-б1', 'К1-б2', 'К1-б3'))
    notes = [f'Отметки — абсолютные (Балтийская система). ±0,000 дома и бани — {alev(M.H0)}; земля проектная — '
             f'планировка участка {alev(M.PLAN_Z)} (Заказчик), фактическая — по топосъёмке.',
             f'Входы в ДК5-018: выпуск дома — с перепадом {alev(DROP["К1-1н"])} м, сеть бани — {alev(DROP["К1-б3"])} м '
             '(по лотку-водосливу). Врезка в существующий колодец — через герметичные проходы (манжеты), по месту.',
             'Колодцы КК-1…КК-3 — полимерные Ø630 с проточным лотком, шахтой и люком; дно — на песчаном основании '
             f'200 мм. {drive_ids("КК")} — в зоне заезда вдоль западного забора: люки Т (C250), засыпка траншеи '
             'песком на всю глубину. ' + ('Участки, где глубина меньше нормы (п. 6.2.4 СП 32.13330.2018), — с '
                                          'утеплением ЭППС 50 мм.' if k1_ins else
                                          'Глубина сети — не меньше нормы (п. 6.2.4 СП 32.13330.2018), утепление '
                                          'не требуется.'),
             'До начала работ — шурф у ДК5-018: проверить отметку лотка (184,98 по съёмке, 185,019 по ИС).']
    sh.notes(162, 140, 238, notes, h=2.0, spacing=1.0)


def ring_route(ids):
    return Route(ids)


def storm_z_at_corner(sid, k):
    """Лоток К2 в вершине k кольца (sid — труба К2)."""
    return P[sid].z[k]


def sheet5(sh, p):
    rA = Route(['Др-1/2', 'Др-2/3', 'Др-К'])
    a1 = P['Др-1/2'].length()
    a2 = a1 + P['Др-2/3'].length()
    a3 = a2 + P['Др-К'].length()
    # К2 по той же трассе (вершины колец К2 — в 0,25 м снаружи; длины сторон пересчитаны пропорционально)
    sA, sK = P['К2-А'], P['К2-К']
    r2 = Route(['К2-А', 'К2-К'])
    k = rA.L / r2.L
    for q in r2.parts:
        q['s0'] *= k
        q['s1'] *= k
    nodes = [well_node(rA, 0.0, W['Др-1'], None, P['Др-1/2'].z[0], z2=sA.z[0]),
             well_node(rA, a1, W['Др-2'], P['Др-1/2'].z[-1], P['Др-2/3'].z[0], z2=sA.z[1]),
             well_node(rA, a2, W['Др-3'], P['Др-2/3'].z[-1], P['Др-К'].z[0], z2=sA.z[2]),
             well_node(rA, a3, W['КЛ-1'], P['Др-К'].z[-1], None, z2=sK.z[-1])]
    draw_profile(p, 28, 262, 'Профиль Др и К2 дома, ветвь А: Др-1 → Др-2 → Др-3 → КЛ-1 (север и восток). '
                 'Гор. 1:200, верт. 1:50', rA, nodes, 200, 50, 'Др', second=(r2, 'К2'), rows=ROWS_DR,
                 label_pipe='Др — перфор. Ø110 в геотекстиле в щебне; К2 — ПП SN8 Ø110; общая траншея',
                 crossings=xmarks(rA, 'ТС-ОВ', 'теплотрасса ОВ ниже Др на {gap} м'))
    rB = Route(['Др-1/4', 'Др-4/3', 'Др-К'])
    b1 = P['Др-1/4'].length()
    b2 = b1 + P['Др-4/3'].length()
    b3 = b2 + P['Др-К'].length()
    rB2 = Route(['К2-Б'])
    k = rB.L / rB2.L
    for q in rB2.parts:
        q['s0'] *= k
        q['s1'] *= k
    sB = P['К2-Б']
    nodes = [well_node(rB, 0.0, W['Др-1'], None, P['Др-1/4'].z[0], z2=sB.z[0]),
             well_node(rB, b1, W['Др-4'], P['Др-1/4'].z[-1], P['Др-4/3'].z[0], z2=sB.z[1]),
             well_node(rB, b2, W['Др-3'], P['Др-4/3'].z[-1], P['Др-К'].z[0], z2=sB.z[2]),
             well_node(rB, b3, W['КЛ-1'], P['Др-К'].z[-1], None, z2=sB.z[-1])]
    # пересечение с выпуском К1-1 (южная сторона)
    sx = b1 + (10.48 - M.RD[0])
    draw_profile(p, 28, 115, 'Профиль Др и К2 дома, ветвь Б: Др-1 → Др-4 → Др-3 → КЛ-1 (запад и юг). '
                 'Гор. 1:200, верт. 1:50', rB, nodes, 200, 50, 'Др', second=(rB2, 'К2'), rows=ROWS_DR,
                 label_pipe='Др — перфор. Ø110 в геотекстиле в щебне; К2 — ПП SN8 Ø110; общая траншея',
                 crossings=[(sx, ('К1-1 Ø110 (выпуск дома) — выше', P['К1-1н'].z[0] - 0.02))])
    ds = [P[a].z[0] - P[b].z[0] for a, b in (('К2-А', 'Др-1/2'), ('К2-Б', 'Др-1/4'))] + \
        [P['К2-Б'].z[2] - P['Др-К'].z[0], P['К2-А'].z[-1] - P['Др-К'].z[0]]
    notes = [f'Дренаж и К2 — в одной траншее: К2 снаружи и выше дренажа на {alev(min(ds))}–{alev(max(ds))} м, '
             'у колодцев Др — обход по месту (узел 8). В КЛ-1 К2-Б входит с севера, К2-К — с востока, выход '
             'дренажа Др-К — между ними, без пересечения с К2.',
             f'Уклон дренажа дома — {alev(M.I_DH, 3)}: выход в КЛ-1 выше лотка выпуска; К2 — {alev(M.I_D, 3)}.',
             'Дренаж — под утеплённой отмосткой здания (ЭППС по КР/АР), промерзание не учитывается.',
             'Выпуски К2 из стен (стояки внутренних водостоков) — косыми тройниками 45° в кольцо К2 '
             'по привязке воронок (выдаёт Заказчик), узел 9.',
             f'Колодцы Др — полимерные Ø315 с отстойной частью 0,3 м и крышкой; промывка — через них. '
             f'{drive_ids("ДрК")} — в зоне заезда: люки Т (C250) на опорном кольце.']
    sh.notes(330, 395, 250, notes, h=2.2, spacing=1.0)
    from nvk_nodes import node_trench, node_roofdrain
    node_trench(p, 392, 248, 8)
    node_roofdrain(p, 515, 118, 9)


def sheet6(sh, p):
    rC = Route(['ДрБ-1/2', 'ДрБ-2/3', 'Др-Т'])
    c1 = P['ДрБ-1/2'].length()
    c2 = c1 + P['ДрБ-2/3'].length()
    c3 = c2 + P['Др-Т'].length()
    r2 = Route(['К2-БА', 'К2-Т'])
    k = rC.L / r2.L
    for q in r2.parts:
        q['s0'] *= k
        q['s1'] *= k
    sCA, sT = P['К2-БА'], P['К2-Т']
    nodes = [well_node(rC, 0.0, W['ДрБ-1'], None, P['ДрБ-1/2'].z[0], z2=sCA.z[0]),
             well_node(rC, c1, W['ДрБ-2'], P['ДрБ-1/2'].z[-1], P['ДрБ-2/3'].z[0], z2=sCA.z[1]),
             well_node(rC, c2, W['ДрБ-3'], P['ДрБ-2/3'].z[-1], P['Др-Т'].z[0], z2=sCA.z[2]),
             well_node(rC, c3, W['Др-2'], P['Др-Т'].z[-1], None, z2=sT.z[-1])]
    draw_profile(p, 28, 152, 'Профиль Др и К2 бани, ветвь А и транзит: ДрБ-1 → ДрБ-2 → ДрБ-3 → Др-2. '
                 'Гор. 1:200, верт. 1:50', rC, nodes, 200, 50, 'Др', second=(r2, 'К2'), rows=ROWS_DR,
                 label_pipe='Др — перфор. Ø110 (транзит — ПП SN8 без перфорации); К2 — ПП SN8 Ø110',
                 crossings=xmarks(rC, 'ТС-ОВ', 'теплотрасса ОВ ниже Др на {gap} м')[:1])
    rD = Route(['ДрБ-1/4', 'ДрБ-4/3'])
    d1 = P['ДрБ-1/4'].length()
    d2 = d1 + P['ДрБ-4/3'].length()
    rD2 = Route(['К2-ББ'])
    k = rD.L / rD2.L
    for q in rD2.parts:
        q['s0'] *= k
        q['s1'] *= k
    sCB = P['К2-ББ']
    nodes = [well_node(rD, 0.0, W['ДрБ-1'], None, P['ДрБ-1/4'].z[0], z2=sCB.z[0]),
             well_node(rD, d1, W['ДрБ-4'], P['ДрБ-1/4'].z[-1], P['ДрБ-4/3'].z[0], z2=sCB.z[1]),
             well_node(rD, d2, W['ДрБ-3'], P['ДрБ-4/3'].z[-1], None, z2=sCB.z[2])]
    sx = d1 + (19.33 - M.BD[0])
    draw_profile(p, 28, 10, 'Профиль Др и К2 бани, ветвь Б: ДрБ-1 → ДрБ-4 → ДрБ-3. Гор. 1:200, верт. 1:50', rD,
                 nodes, 200, 50, 'Др', second=(rD2, 'К2'), rows=ROWS_DR,
                 label_pipe='Др — перфор. Ø110 в геотекстиле в щебне; К2 — ПП SN8 Ø110; общая траншея',
                 crossings=[(sx, ('К1-б Ø110 (выпуск бани) — выше', P['К1-бн'].z[0] - 0.02))] +
                 xmarks(rD, 'ТС-ОВ', 'теплотрасса ОВ ниже Др на {gap} м'))
    # КЛ-1 → выпуск ЛК
    rE = Route(['К2-ЛК'])
    nE = [well_node(rE, 0.0, W['КЛ-1'], None, P['К2-ЛК'].z[0]),
          dict(s=rE.L, name='вып. ЛК Ø63', zin=P['К2-ЛК'].z[-1])]
    draw_profile(p, 290, 66, 'КЛ-1 → выпуск ЛК Ø63. Гор. 1:50, верт. 1:50', rE, nE, 50, 50, 'К2', rows=ROWS_K1,
                 label_pipe='ПЭ 100 SDR17 63×3,8')


def sheet7(sh, p):
    r = Route(['В1-н'])
    v = P['В1-н']
    ss = [0.0]
    for a, b in zip(v.pts, v.pts[1:]):
        ss.append(ss[-1] + math.dist(a, b))
    names = ['вып. ВК Ø32', 'угол 1', 'угол 2', 'подъём', '', 'ввод (ВК)']
    nodes = []
    for k, (s, nm) in enumerate(zip(ss, names)):
        if not nm:
            continue
        nodes.append(dict(s=s, name=nm, zin=v.z[k] if k else None, zout=v.z[k] if not k else None,
                          top=nm in ('вып. ВК Ø32', 'ввод (ВК)', 'угол 2')))
    sv = math.dist(v.pts[0], v.pts[1]) + abs(M.v1.valve[1] - v.pts[1][1])
    nodes.insert(2, dict(s=sv, name='ЗУ-1', zin=r.z(sv), top=True))
    for n in nodes:
        if n['zin'] is None and n['zout'] is None:
            n['zin'] = r.z(n['s'])
    # подъём — отдельной точкой: ось внизу и вверху
    nodes[-2]['zin'] = v.z[3]
    nodes[-2]['zout'] = v.z[4]
    draw_profile(p, 28, 150, 'Профиль ввода В1: выпуск ВК Ø32 → ЗУ-1 → ввод в 1.6. Гор. 1:100, верт. 1:50', r, nodes,
                 100, 50, 'В1', rows=ROWS_V, axis=True,
                 label_pipe='ПЭ 100 SDR11 32×3,0 питьевая, на песчаном основании 100 мм')
    rk = Route(['КХ-8н'])
    nk = [dict(s=0.0, name='КХ-8 (ВК)', zout=P['КХ-8н'].z[0]),
          dict(s=rk.L, name='КП-1', zin=P['КХ-8н'].z[-1], well=W['КП-1'])]
    draw_profile(p, 28, 10, 'Подводка полива КХ-8 → КП-1. Гор. 1:50, верт. 1:50', rk, nk, 50, 50, 'В1', rows=ROWS_V,
                 axis=True, label_pipe='ПЭ 100 SDR11 25×2,3')
    notes = [f'Глубина ввода — не менее {f2(M.FROST + 0.5)} м до низа трубы (промерзание {f2(M.FROST)} + 0,5 м, '
             'п. 11.40 СП 31.13330.2021); у фундамента — подъём к вводу на −0,850 в скорлупе ППУ 40 мм с '
             'греющим кабелем 10 Вт/м (лист 8, узел 1).',
             'Под крыльцом 1.6 — в футляре ПНД Ø110 (L = 2,0 м).',
             'Перед засыпкой — гидравлическое испытание 1,5 Pраб, но не менее 1,0 МПа (СП 129.13330.2019), '
             'промывка и дезинфекция.',
             'Подводка полива КХ-8 — сезонная, с уклоном 0,01 к КП-1, в футляре ПНД Ø63 на всю длину (над К2-А с '
             f'зазором {alev(CROSS[("КХ-8н", "К2-А")])} м); от КП-1 — сезонная линия В1-Бс ПЭ 25 к садовой колонке КБ '
             f'у беседки (L = {alev(M.kb_line.length(), 0)} м, выход из КП-1 на оси {alev(M.Z_KB0)}, уклон 0,003 к КП-1, '
             f'глубина до верха {alev(min(M.PLAN_Z - M.kb_line.top(s_) for s_ in (0, M.kb_line.length())))}–'
             f'{alev(max(M.PLAN_Z - M.kb_line.top(s_) for s_ in (0, M.kb_line.length())))} м; в футляре ПНД Ø63 — от '
             'КП-1 до перемычки за теплотрассой и над К1-б1, лист 3). На зиму — перекрыть кран КХ-8 в 1.6, открыть '
             'кран колонки КБ и спускной кран в КП-1.',
             f'Требуемый напор в точке подключения — {alev(calc()["p4"]["H_stub"], 1)} м (П4); гарантированный напор поселковой сети '
             '— по ТУ (запросить у эксплуатирующей организации).']
    sh.notes(150, 134, 250, notes, h=2.0, spacing=1.0)


SHEETS = {4: (sheet4, 'nvk_prof_4'), 5: (sheet5, 'nvk_prof_5'), 6: (sheet6, 'nvk_prof_6'), 7: (sheet7, 'nvk_prof_7')}
FMT = {5: 'А2'}

if __name__ == '__main__':
    no = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    fn, base = SHEETS[no]
    doc = new_doc()
    setup(doc)
    sh = RDSheet(doc, 'Лист', NVK_LIST[no], no, NVK_TOTAL, fmt=FMT.get(no, 'А3'), code=CODE_NVK, bld=BLD_NVK)
    p = PP(doc, sh.lay)
    fn(sh, p)
    finish(doc)
    print(save_and_pdf(doc, os.path.join(OUT, base + '.dxf')))
