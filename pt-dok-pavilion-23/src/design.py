"""Модель систем ПТ: оросители, трубопроводы, ПК, стояки.
Координаты — мм в системе DWG АР (ось 1: x=0, ось А: y=0), отметки — м.
"""
import json, math, os
from geom import rooms, FREEZERS, z_roof_beam_top, GROUPS, bb, pip

HERE = os.path.dirname(os.path.abspath(__file__))
F1 = rooms('f1'); F2 = rooms('f2')

# ------------------------------------------------------------------ отметки
Z1_BR = 3.360      # ось распределительных трубопроводов 1 этажа — между балками, 0,11 м ниже профлиста +3,470
Z1_SPR = 3.250     # розетка оросителя (розеткой вниз): 0,22 м от низа профлиста, на 0,05 м ниже низа балок +3,300
Z1_MAIN = 2.900    # ось питающих трубопроводов 1 этажа (под балками)
Z2_MAIN = 6.850    # ось питающих трубопроводов 2 этажа (под балками покрытия, низ балок у питающих ≥ +7,02)
def z2_br(y):      # ось распределительного трубопровода 2 этажа: под прогонами, по уклону покрытия
    return round(z_roof_beam_top(y) - 0.06, 3)
def z2_spr(y):     # розетка оросителя розеткой вверх: между прогонами, 0,18 м до низа профлиста
    return round(z2_br(y) + 0.10, 3)
ZB_RING = -0.450   # кольцо ВПВ в техническом подвале (под балками −0,248, вдоль стены коридора)
Z_PK = 1.35        # ось клапана ПК над полом

Y_MAIN_N1, Y_MAIN_S1 = 24600, 15400      # питающие 1 этажа (в зонах подготовки)
Y_MAIN_N2, Y_MAIN_S2 = 27500, 12500      # питающие 2 этажа (в холлах)
X_SRC = 2000                              # стояк В21 от УУ-1 (насосная в подвале, проход в пом. 05)
X_SRC2 = 3200                             # стояк В22 от УУ-2
Y_SRC = 23000
Z_UU_OUT = -0.600                         # выход узлов управления

sprinklers = []   # dict(x,y,z,sec,room,floor,grp,kind)
pipes = []        # dict(a:[x,y,z], b:[x,y,z], sys, sec, role)
pk = []           # пожарные краны
notes = []

def spr(x, y, sec, room, floor, grp, kind):
    if floor == 1:
        z = Z1_SPR
    else:
        z = z2_spr(y)
    sprinklers.append(dict(x=round(x), y=round(y), z=z, sec=sec, room=room, floor=floor, grp=grp, kind=kind))
    return sprinklers[-1]

def pipe(a, b, sys, sec, role):
    if tuple(a) == tuple(b):
        return
    pipes.append(dict(a=[round(a[0]), round(a[1]), round(a[2], 3)], b=[round(b[0]), round(b[1]), round(b[2], 3)],
                      sys=sys, sec=sec, role=role))

def frz_in(xa, ya, xb, yb):
    return [f for f in FREEZERS if f[0] >= xa - 200 and f[2] <= xb + 200 and f[1] >= ya - 200 and f[3] <= yb + 200]

def even(a, b, n):
    w = (b - a) / n
    return [a + w * (i + 0.5) for i in range(n)]

# ================================================================= 1 ЭТАЖ (секция 1)
SEC1 = 1
def branch1(x, ys_n, ys_s, y_main, rooms_n, rooms_s, route=None):
    """Колонка-ответвление 1 этажа: от питающего (x, y_main) по оси y.
    ys_n — оросители по одну сторону, ys_s — по другую. route — обход (список точек в плане)"""
    zs = Z1_BR
    start = (x, y_main, Z1_MAIN)
    up = (x, y_main, zs)
    pipe(start, up, 'В21', SEC1, 'подъём')
    for ys, rms in ((ys_n, rooms_n), (ys_s, rooms_s)):
        if not ys:
            continue
        prev = up
        for y, rm in zip(ys, rms):
            s = spr(x, y, SEC1, rm[0], 1, 2, rm[1])
            cur = (x, y, zs)
            pipe(prev, cur, 'В21', SEC1, 'распределительный')
            pipe(cur, (x, y, Z1_SPR), 'В21', SEC1, 'спуск')
            prev = cur

def block_columns(xa, xb, ch):
    cx0, cy0, cx1, cy1 = ch
    w = cx1 - cx0
    c_ch = [cx0 + w / 4, cx0 + 3 * w / 4]
    if (xb - cx1) > (cx0 - xa):
        aisle = (cx1 + xb) / 2
        return c_ch, aisle, [c_ch[0], aisle]   # для фронтальной и выставочной зон — крайние
    aisle = (xa + cx0) / 2
    return c_ch, aisle, [aisle, c_ch[1]]

def std_block(vest, prep, disp, north):
    rv = F1[vest]; xa, ya, xb, yb = bb(rv['poly'])
    ch = frz_in(xa, ya, xb, yb)[0]
    c_ch, aisle, outer = block_columns(xa, xb, ch)
    rp = bb(F1[prep]['poly']); rd = bb(F1[disp]['poly'])
    y_prep = (rp[1] + rp[3]) / 2
    y_disp = (rd[1] + rd[3]) / 2
    h = ch[3] - ch[1]
    rows_ch = [ch[1] + h / 6, ch[1] + h / 2, ch[1] + 5 * h / 6]
    if north:
        y_front = (ch[3] + yb) / 2; y_main = Y_MAIN_N1
    else:
        y_front = (ya + ch[1]) / 2; y_main = Y_MAIN_S1
    cols = sorted(c_ch + [aisle])
    for x in cols:
        is_aisle = abs(x - aisle) < 1
        ys = [y_prep] + rows_ch
        rms = [(prep, 'зона подготовки')] + [(vest, 'проход у камеры' if is_aisle else 'над камерой')] * 3
        if any(abs(x - o) < 1 for o in outer):
            ys.append(y_front); rms.append((vest, 'у ворот'))
        if not north:
            order = sorted(zip(ys, rms), key=lambda t: -t[0])
        else:
            order = sorted(zip(ys, rms), key=lambda t: t[0])
        ys_far = [t[0] for t in order]; rms_far = [t[1] for t in order]
        ys_near, rms_near = [], []
        if any(abs(x - o) < 1 for o in outer):
            ys_near = [y_disp]; rms_near = [(disp, 'выставочная зона')]
        branch1(x, ys_far, ys_near, y_main, rms_far, rms_near)
    return cols

NORTH = [('09', '37', '65'), ('10', '38', '66'), ('11', '39', '67'), ('12', '40', '68'), ('13', '41', '69'), ('14', '42', '70'),
         ('15', '43', '71'), ('16', '44', '72'), ('17', '45', '73'), ('18', '46', '74'), ('19', '47', '75'), ('20', '48', '76')]
SOUTH = [('23', '51', '79'), ('24', '52', '80'), ('25', '53', '81'), ('26', '54', '82'), ('27', '55', '83'), ('28', '56', '84'),
         ('29', '57', '85'), ('30', '58', '86'), ('31', '59', '87'), ('32', '60', '88'), ('33', '61', '89'), ('34', '62', '90')]
for v, p, d in NORTH:
    std_block(v, p, d, True)
for v, p, d in SOUTH:
    std_block(v, p, d, False)

# ---- торцевые блоки (оси 1–3 и 16–18): камеры №1, №2, тех. помещения 01–04
def end_block(mirror_x, north):
    """Строится для запада (оси 1–3), восток — зеркально по x относительно оси 9/10 (x'=98000-x)."""
    def X(x):
        return 98000 - x if mirror_x else x
    def Y(y):
        return y if north else 40000 - y
    vest = {(False, True): '08', (True, True): '21', (False, False): '22', (True, False): '35'}[(mirror_x, north)]
    tech = {(False, True): '01', (True, True): '03', (False, False): '02', (True, False): '04'}[(mirror_x, north)]
    prep = {(False, True): '36', (True, True): '49', (False, False): '50', (True, False): '63'}[(mirror_x, north)]
    disp = {(False, True): '64', (True, True): '77', (False, False): '78', (True, False): '91'}[(mirror_x, north)]
    y_main = Y_MAIN_N1 if north else Y_MAIN_S1
    y_prep = Y(26200); y_disp = Y(23025)
    # колонки (запад): над камерами 1175/3575/5975, проход 8562
    rows_ch = [29675, 32375, 36075]           # камера №2 — 2 ряда, №1 — 1 ряд
    defs = {
        1175: dict(rows=[(r, vest, 'над камерой') for r in rows_ch] + [(39125, tech, 'тех. помещение')]),
        3575: dict(rows=[(r, vest, 'над камерой') for r in rows_ch] + [(39125, tech, 'тех. помещение')]),
        5975: dict(rows=[(26200, prep, 'зона подготовки')] + [(r, vest, 'над камерой') for r in rows_ch] + [(39100, vest, 'у ворот')], disp=True),
        8562: dict(rows=[(26200, prep, 'зона подготовки')] + [(r, vest, 'проход у камеры') for r in rows_ch] + [(39100, vest, 'у ворот')], disp=True),
    }
    for x0, d in defs.items():
        x = X(x0)
        ys = [Y(r[0]) for r in d['rows']]; rms = [(r[1], r[2]) for r in d['rows']]
        near = [y_disp] if d.get('disp') else []
        near_r = [(disp, 'выставочная зона')] if d.get('disp') else []
        if x0 in (1175, 3575) and not north and not mirror_x:
            # юго-запад: под колонками 1175/3575 — ВРУ (пом. 06); трубопроводы через ВРУ не прокладываются.
            # Питание через гребёнку в тамбуре 22 по y=11400 от колонки 5975.
            yh = 11400
            prev = (x, yh, Z1_BR)
            pipe((X(5975), yh, Z1_BR), prev, 'В21', SEC1, 'распределительный')
            for y, rm in sorted(zip(ys, rms), key=lambda t: -t[0]):
                cur = (x, y, Z1_BR)
                spr(x, y, SEC1, rm[0], 1, 2, rm[1])
                pipe(prev, cur, 'В21', SEC1, 'распределительный')
                pipe(cur, (x, y, Z1_SPR), 'В21', SEC1, 'спуск')
                prev = cur
            continue
        order = sorted(zip(ys, rms), key=(lambda t: t[0]) if north else (lambda t: -t[0]))
        branch1(x, [t[0] for t in order], near, y_main, [t[1] for t in order], near_r)

end_block(False, True); end_block(True, True); end_block(False, False); end_block(True, False)

# ---- центральная часть, торговые залы под перекрытием, тамбуры
def grid_room(xa, ya, xb, yb, smax, amax, cols=None):
    W, H = xb - xa, yb - ya
    if cols is None:
        nx = max(1, math.ceil(W / smax))
        while True:
            sx = W / nx
            sy = min(smax, amax / sx)
            if sx <= smax and sx / 2 <= smax / 2:
                break
            nx += 1
        cols = even(xa, xb, nx)
        cw = W / nx
    else:
        edges = [xa] + [(cols[i] + cols[i + 1]) / 2 for i in range(len(cols) - 1)] + [xb]
        cw = max(edges[i + 1] - edges[i] for i in range(len(cols)))
    sy = min(smax, amax / cw)
    ny = max(1, math.ceil(H / sy - 1e-9))
    rows = even(ya, yb, ny)
    return cols, rows

# пом. 96 (центральный торговый зал под венткамерой): колонки от питающих N и S
c96, r96 = grid_room(46225, 11875, 51775, 28125, 4.0e3, 12e6)
for x in c96:
    north_rows = [r for r in r96 if r > 20000]; south_rows = [r for r in r96 if r <= 20000]
    # от северного питающего: вверх (к y>24600) и вниз
    n_up = [r for r in north_rows if r > Y_MAIN_N1]; n_dn = [r for r in north_rows if r <= Y_MAIN_N1]
    branch1(x, sorted(n_up), sorted(n_dn, reverse=True), Y_MAIN_N1, [('96', 'торговый зал')] * len(n_up), [('96', 'торговый зал')] * len(n_dn))
    s_dn = [r for r in south_rows if r < Y_MAIN_S1]; s_up = [r for r in south_rows if r >= Y_MAIN_S1]
    branch1(x, sorted(s_dn, reverse=True), sorted(s_up), Y_MAIN_S1, [('96', 'торговый зал')] * len(s_dn), [('96', 'торговый зал')] * len(s_up))
# пом. 94 под площадкой 38 (y 28225..33775) — 2×2, от северного питающего по колонкам 96
c94, r94 = grid_room(46225, 28225, 51775, 33775, 4.0e3, 12e6, cols=c96)
# оросители 94 — продолжение колонок 96 на север
for x in c94:
    prev = None
    # найти последнюю точку колонки 96 севернее питающего
    tops = [s for s in sprinklers if s['room'] == '96' and abs(s['x'] - x) < 1 and s['y'] > Y_MAIN_N1]
    ytop = max(s['y'] for s in tops) if tops else Y_MAIN_N1
    prev = (x, ytop, Z1_BR)
    for y in r94:
        spr(x, y, SEC1, '94', 1, 2, 'под площадкой лестницы')
        cur = (x, y, Z1_BR)
        pipe(prev, cur, 'В21', SEC1, 'распределительный')
        pipe(cur, (x, y, Z1_SPR), 'В21', SEC1, 'спуск')
        prev = cur
# пом. 95 — полоса под площадкой 39 (y 10555..11775): 1 ряд, продолжение колонок 96 на юг
for x in c96:
    bots = [s for s in sprinklers if s['room'] == '96' and abs(s['x'] - x) < 1 and s['y'] < Y_MAIN_S1]
    ybot = min(s['y'] for s in bots) if bots else Y_MAIN_S1
    y = (10555 + 11775) / 2
    spr(x, y, SEC1, '95', 1, 2, 'под площадкой лестницы')
    pipe((x, ybot, Z1_BR), (x, y, Z1_BR), 'В21', SEC1, 'распределительный')
    pipe((x, y, Z1_BR), (x, y, Z1_SPR), 'В21', SEC1, 'спуск')

# торговые залы 97/98 под перекрытием 2 этажа (вне проёма «второго света»): 1 ряд y=20000
def hall_part(xa, xb, feed_x, room):
    cols, rows = grid_room(xa, 18125, xb, 21875, 4.0e3, 12e6)
    y = rows[0]
    # подводка от северного питающего по x=feed_x через выставочную зону, затем вдоль y=20000
    pipe((feed_x, Y_MAIN_N1, Z1_MAIN), (feed_x, Y_MAIN_N1, Z1_BR), 'В21', SEC1, 'подъём')
    pipe((feed_x, Y_MAIN_N1, Z1_BR), (feed_x, y, Z1_BR), 'В21', SEC1, 'распределительный')
    for x in cols:
        spr(x, y, SEC1, room, 1, 2, 'торговый зал')
        pipe((feed_x, y, Z1_BR), (x, y, Z1_BR), 'В21', SEC1, 'распределительный')
        pipe((x, y, Z1_BR), (x, y, Z1_SPR), 'В21', SEC1, 'спуск')
hall_part(39875, 46125, 43000, '97')
hall_part(51875, 58125, 55000, '98')
hall_part(87875, 93775, 90800, '98')
# западная часть 97 (4225..10125) — от перемычки N–S (x=7200)
X_CROSS1 = 7200
cols, rows = grid_room(4225, 18125, 10125, 21875, 4.0e3, 12e6)
for x in cols:
    spr(x, 20000, SEC1, '97', 1, 2, 'торговый зал')
    pipe((X_CROSS1, 20000, Z1_MAIN), (X_CROSS1, 20000, Z1_BR), 'В21', SEC1, 'подъём')
    pipe((X_CROSS1, 20000, Z1_BR), (x, 20000, Z1_BR), 'В21', SEC1, 'распределительный')
    pipe((x, 20000, Z1_BR), (x, 20000, Z1_SPR), 'В21', SEC1, 'спуск')

# тамбуры 92 и 93: 2×2
def tambour(xa, ya, xb, yb, feed, room, kind='тамбур'):
    cols, rows = grid_room(xa, ya, xb, yb, 4.0e3, 12e6)
    if len(cols) * len(rows) < 4 and ((xb - xa) / 2 > 2000 or (yb - ya) / 2 > 2000):
        cols = even(xa, xb, 2); rows = even(ya, yb, 2)
    fx, fy = feed
    ym = (ya + yb) / 2
    pipe((fx, fy, Z1_MAIN), (fx, fy, Z1_BR), 'В21', SEC1, 'подъём')
    pipe((fx, fy, Z1_BR), (fx, ym, Z1_BR), 'В21', SEC1, 'распределительный')
    for x in cols:
        pipe((fx, ym, Z1_BR), (x, ym, Z1_BR), 'В21', SEC1, 'распределительный')
        for y in rows:
            spr(x, y, SEC1, room, 1, 2, kind)
            pipe((x, ym, Z1_BR), (x, y, Z1_BR), 'В21', SEC1, 'распределительный')
            pipe((x, y, Z1_BR), (x, y, Z1_SPR), 'В21', SEC1, 'спуск')
tambour(-125, 17875, 4125, 22125, (X_SRC, Y_MAIN_N1), '92')
# пом. 05 (КУИ): насосная перенесена в подвал, помещение защищается АУПТ (группа 2), через него проходят стояки
tambour(-125, 22225, 4125, 28125, (X_SRC, Y_MAIN_N1), '05', 'КУИ')
tambour(93875, 17875, 98125, 22125, (96000, Y_MAIN_N1), '93')

# ---- питающие трубопроводы секции 1 (по оси, сегменты строятся по точкам врезок)
def main_line(y, x_from, x_to, z, sec, sys):
    taps = sorted({round(p['a'][0]) for p in pipes if p['sec'] == sec and p['role'] == 'подъём' and abs(p['a'][1] - y) < 1 and abs(p['a'][2] - z) < 1e-3})
    taps = [t for t in taps if x_from - 1 <= t <= x_to + 1] if x_to > x_from else taps
    xs = sorted(set([x_from, x_to] + taps))
    for i in range(len(xs) - 1):
        pipe((xs[i], y, z), (xs[i + 1], y, z), sys, sec, 'питающий')

# врезки перемычки: на северном и южном питающих в x=X_CROSS1
pipe((X_CROSS1, Y_MAIN_N1, Z1_MAIN), (X_CROSS1, 20000, Z1_MAIN), 'В21', SEC1, 'питающий')
pipe((X_CROSS1, 20000, Z1_MAIN), (X_CROSS1, Y_MAIN_S1, Z1_MAIN), 'В21', SEC1, 'питающий')
# фиктивные «подъёмы» для учёта точек врезки
xs_n = [X_SRC, X_CROSS1] + [round(p['a'][0]) for p in pipes if p['role'] == 'подъём' and abs(p['a'][1] - Y_MAIN_N1) < 1]
xs_s = [X_CROSS1] + [round(p['a'][0]) for p in pipes if p['role'] == 'подъём' and abs(p['a'][1] - Y_MAIN_S1) < 1]
# южные колонки торцевого блока юго-запада (1175/3575) питаются гребёнкой — их врезки нет
def seg_main(y, xs, z, sys, sec):
    xs = sorted(set(xs))
    for i in range(len(xs) - 1):
        pipe((xs[i], y, z), (xs[i + 1], y, z), sys, sec, 'питающий')
seg_main(Y_MAIN_N1, xs_n, Z1_MAIN, 'В21', SEC1)
seg_main(Y_MAIN_S1, xs_s, Z1_MAIN, 'В21', SEC1)
# стояк секции 1 от УУ-1 (отм. +1,200 — выход УУ) до питающего
SRC1 = (X_SRC, Y_SRC, Z_UU_OUT)
pipe(SRC1, (X_SRC, Y_SRC, Z1_MAIN), 'В21', SEC1, 'стояк')
pipe((X_SRC, Y_SRC, Z1_MAIN), (X_SRC, Y_MAIN_N1, Z1_MAIN), 'В21', SEC1, 'питающий')

# ================================================================= 2 ЭТАЖ (секция 2)
SEC2 = 2
def branch2(x, y_main, far, near):
    """far/near: списки (y, room, grp, kind) — по разные стороны от питающего"""
    zm = Z2_MAIN
    zb0 = z2_br(y_main)
    pipe((x, y_main, zm), (x, y_main, zb0), 'В22', SEC2, 'подъём')
    for lst in (far, near):
        prev = (x, y_main, zb0)
        for (y, rm, g, kind) in sorted(lst, key=lambda t: abs(t[0] - y_main)):
            cur = (x, y, z2_br(y))
            spr(x, y, SEC2, rm, 2, g, kind)
            pipe(prev, cur, 'В22', SEC2, 'распределительный')
            pipe(cur, (x, y, z2_spr(y)), 'В22', SEC2, 'спуск')
            prev = cur

def bay_cols(xa, xb, smax):
    n = max(1, math.ceil((xb - xa) / smax - 1e-9))
    return even(xa, xb, n)

def store_rows(ya, yb):
    g = GROUPS[5]
    return grid_room(0, ya, 2950, yb, g['smax'] * 1000, g['Amax'] * 1e6, cols=[1475])[1]

ROWS_N_STORE = store_rows(28225, 40125)
ROWS_S_STORE = store_rows(-125, 11775)
ROWS_N_HOLL = even(21875, 28125, 2)
ROWS_S_HOLL = even(11875, 18125, 2)
VOID = [(10125, 39875), (58125, 87875)]
def in_void(x):
    return any(a < x < b for a, b in VOID)

# пролёты 2 этажа (по кладовым севера): (кладовая N, кладовая S, xa, xb)
BAYS2 = []
for n_r, s_r in [('01', '14'), ('02', '15'), ('03', '16'), ('04', '17'), ('05', '18'), ('06', '19'),
                 ('07', '21'), ('08', '22'), ('09', '23'), ('10', '24'), ('11', '25'), ('12', '26'), ('13', '27')]:
    xa, _, xb, _ = bb(F2[n_r]['poly'])
    BAYS2.append((n_r, s_r, xa, xb))
for n_r, s_r, xa, xb in BAYS2:
    cols = bay_cols(xa, xb, 3000)
    for x in cols:
        far = [(y, n_r, 5, 'кладовая') for y in ROWS_N_STORE]
        near = []
        if 4225 <= x <= 93775:
            near = [(y, '36' if x < 49000 else '37', 2, 'холл') for y in ROWS_N_HOLL]
            near.append((20000, '97' if x < 49000 else '98', 2, 'второй свет (покрытие)') if in_void(x) else (20000, '36' if x < 49000 else '37', 2, 'холл'))
        else:
            # тех. помещения 31/33 (x<4125 или x>93875): 3 ряда
            r = '31' if x < 49000 else '33'
            rows = even(20050, 28125, 3)
            near = [(y, r, 2, 'тех. помещение') for y in rows]
        branch2(x, Y_MAIN_N2, far, near)
        # юг
        xa_s, _, xb_s, _ = bb(F2[s_r]['poly'])
        if abs(xa_s - xa) < 300 and abs(xb_s - xb) < 300:
            far_s = [(y, s_r, 5, 'кладовая') for y in ROWS_S_STORE]
        else:
            far_s = []
        if 4225 <= x <= 93775:
            near_s = [(y, '36' if x < 49000 else '37', 2, 'холл') for y in ROWS_S_HOLL]
        else:
            r = '32' if x < 49000 else '34'
            near_s = [(y, r, 2, 'тех. помещение') for y in even(11875, 19950, 3)]
        branch2(x, Y_MAIN_S2, far_s, near_s)

# пролёт 8–9 (x 40050..46125): юг — кладовая 20, север — пом. 28/29/30; три колонки
cols89 = bay_cols(40050, 46125, 3000)
for x in cols89:
    far = []
    if x < 44525:
        far += [(29588, '29', 2, 'КУИ'), (32412, '30', 2, 'тех. помещение')]
    else:
        far += [(29588, '38', 2, 'лестничная площадка'), (32412, '38', 2, 'лестничная площадка')]
    far += [(y, '28', 2, 'рабочий кабинет') for y in even(33875, 40125, 2)]
    near = [(y, '36', 2, 'холл') for y in ROWS_N_HOLL] + [(20000, '36', 2, 'холл')]
    branch2(x, Y_MAIN_N2, far, near)
    far_s = [(y, '20', 5, 'кладовая') for y in ROWS_S_STORE]
    near_s = [(y, '36', 2, 'холл') for y in ROWS_S_HOLL]
    branch2(x, Y_MAIN_S2, far_s, near_s)
# пролёт 10–11 (x 51875..57950): север — кладовая 07 учтена в BAYS2 (её колонки), юг — 21 (тоже)

# центральный пролёт 9–10: лестничные площадки 38/39 и «второй свет» над тамбур-шлюзами
c_c = even(46225, 51775, 2)
for x in c_c:
    far = [(y, '38', 2, 'лестничная площадка') for y in even(26225, 33775, 2)]
    far += [(y, '94', 2, 'второй свет (покрытие)') for y in even(33775, 40125, 2)]
    branch2(x, Y_MAIN_N2, far, [])
    far_s = [((10555 + 13775) / 2, '39', 2, 'лестничная площадка')]
    far_s += [(y, '95', 2, 'второй свет (покрытие)') for y in even(-125, 10555, 3)]
    branch2(x, Y_MAIN_S2, far_s, [])

# питающие секции 2
xs_n2 = [round(p['a'][0]) for p in pipes if p['sec'] == SEC2 and p['role'] == 'подъём' and abs(p['a'][1] - Y_MAIN_N2) < 1]
xs_s2 = [round(p['a'][0]) for p in pipes if p['sec'] == SEC2 and p['role'] == 'подъём' and abs(p['a'][1] - Y_MAIN_S2) < 1]
X_CROSS2 = 2400
seg_main(Y_MAIN_N2, xs_n2 + [X_CROSS2, X_SRC2], Z2_MAIN, 'В22', SEC2)
seg_main(Y_MAIN_S2, xs_s2 + [X_CROSS2], Z2_MAIN, 'В22', SEC2)
pipe((X_CROSS2, Y_MAIN_N2, Z2_MAIN), (X_CROSS2, Y_MAIN_S2, Z2_MAIN), 'В22', SEC2, 'питающий')
SRC2 = (X_SRC2, Y_SRC, Z_UU_OUT)
pipe(SRC2, (X_SRC2, Y_SRC, Z2_MAIN), 'В22', SEC2, 'стояк')
pipe((X_SRC2, Y_SRC, Z2_MAIN), (X_SRC2, Y_MAIN_N2, Z2_MAIN), 'В22', SEC2, 'питающий')

# ================================================================= ВПВ (В2)
Y_RING1, Y_RING2 = 22750, 17250     # кольца у внутренних стен коридоров (коридоры y 22300–27700 и 12300–17700)
PK_AX_1 = ['3', '5', '7', '9', '10', '12', '14', '16']
PK_AX_2 = ['3', '7', '12', '16']
PK_AX_B = [16000, 44000, 82000]
AXX = {'1': 0, '2': 4000, '3': 10000, '4': 16000, '5': 22000, '6': 28000, '7': 34000, '8': 40000, '9': 46000,
       '10': 52000, '11': 58000, '12': 64000, '13': 70000, '14': 76000, '15': 82000, '16': 88000, '17': 94000, '18': 98000}
ring_taps = {1: [], 2: []}
n_pk = 0
def add_pk(x, y, z_floor, floor, riser_from, ring, face):
    global n_pk
    n_pk += 1
    name = f'ПК-{n_pk}'
    rx, ry = riser_from
    pk.append(dict(name=name, x=round(x), y=round(y), floor=floor, z=round(z_floor + Z_PK, 3), face=face, n=2,
                   rx=round(rx), ry=round(ry), riser=f'Ст.В2-{n_pk}', ring=ring))
    yr = Y_RING1 if ring == 1 else Y_RING2
    # отвод от кольца к стояку, стояк, подводка к шкафу
    pipe((rx, yr, ZB_RING), (rx, ry, ZB_RING), 'В2', 0, 'подводка ВПВ')
    pipe((rx, ry, ZB_RING), (rx, ry, z_floor + Z_PK), 'В2', 0, 'стояк ВПВ')
    pipe((rx, ry, z_floor + Z_PK), (x, y, z_floor + Z_PK), 'В2', 0, 'подводка ВПВ')
    ring_taps[ring].append(rx)
for a in PK_AX_1:
    dx = -600 if a == '9' else 600
    x = AXX[a] + dx
    add_pk(x, 21950, 0.0, 1, (x, 22500), 1, 'S')
    add_pk(x, 18050, 0.0, 1, (x, 17500), 2, 'N')
for a in PK_AX_2:
    x = AXX[a] + 1500
    add_pk(x, 28000, 3.7, 2, (x, 27850), 1, 'S')
    add_pk(x, 12000, 3.7, 2, (x, 12150), 2, 'N')
for x in PK_AX_B:
    add_pk(x, 22350, -2.2, 0, (x, 22350), 1, 'N')
for x in [16000, 54000, 82000]:
    add_pk(x, 17650, -2.2, 0, (x, 17650), 2, 'S')
# кольца в коридорах и перемычки
X_R0, X_R1 = 3700, 97400          # кольцо 1 начинается в насосной (x 300–8300), кольцо 2 — у перемычки x=4700
X_VPV_TAP = 5200                  # врезка кольца 1 в напорный коллектор насосной
X_HDR, Y_HDR, Z_HDR = 4400, 23600, -1.750   # напорный коллектор (точка отбора на ВПВ)
for ring, yr in ((1, Y_RING1), (2, Y_RING2)):
    x0 = X_R0 if ring == 1 else 4700
    xs = sorted(set([x0, X_R1] + ring_taps[ring] + [7000, 28000, 49000, 70000, 91000] + ([X_VPV_TAP] if ring == 1 else [])))
    for i in range(len(xs) - 1):
        pipe((xs[i], yr, ZB_RING), (xs[i + 1], yr, ZB_RING), 'В2', 0, 'кольцо ВПВ')
# питание кольца от напорного коллектора насосной
path_hdr = [(X_HDR, Y_HDR, Z_HDR), (X_VPV_TAP, Y_HDR, Z_HDR), (X_VPV_TAP, Y_HDR, ZB_RING), (X_VPV_TAP, Y_RING1, ZB_RING)]
for a, b in zip(path_hdr, path_hdr[1:]):
    pipe(a, b, 'В2', 0, 'перемычка ВПВ')
# западная перемычка: из насосной вверх в пом. 05, через тамбур 92 и зал 97 вниз в коридор 2
path_b = [(X_R0, Y_RING1, ZB_RING), (X_R0, Y_RING1, 2.600), (X_R0, 18600, 2.600), (4700, 18600, 2.600), (4700, 16800, 2.600),
          (4700, 16800, ZB_RING), (4700, Y_RING2, ZB_RING)]
for a, b in zip(path_b, path_b[1:]):
    pipe(a, b, 'В2', 0, 'перемычка ВПВ')
# восточная перемычка через СУ М (99), тамбур 93, СУ Ж (100)
path_e = [(X_R1, Y_RING1, ZB_RING), (X_R1, Y_RING1, 2.600), (X_R1, Y_RING2, 2.600), (X_R1, Y_RING2, ZB_RING)]
for a, b in zip(path_e, path_e[1:]):
    pipe(a, b, 'В2', 0, 'перемычка ВПВ')

# ---- разбиение сегментов в точках врезок (Т-образные узлы)
def split_tees(pipes):
    pts = set()
    for p in pipes:
        pts.add(tuple(p['a'])); pts.add(tuple(p['b']))
    out = []
    for p in pipes:
        a, b = p['a'], p['b']
        inner = []
        for q in pts:
            if q == tuple(a) or q == tuple(b):
                continue
            # коллинеарность и принадлежность отрезку (оси параллельны осям координат)
            ok = True; t = None
            for k in range(3):
                lo, hi = sorted((a[k], b[k]))
                tol = 1 if k < 2 else 0.002
                if not (lo - tol <= q[k] <= hi + tol):
                    ok = False; break
            if not ok:
                continue
            # проверка коллинеарности: отклонение от прямой
            d = [b[k] - a[k] for k in range(3)]; v = [q[k] - a[k] for k in range(3)]
            L2 = sum((d[k] * (1 if k < 2 else 1000)) ** 2 for k in range(3))
            if L2 == 0:
                continue
            tt = sum(d[k] * v[k] * (1 if k < 2 else 1e6) for k in range(3)) / L2
            dev = sum(((a[k] + tt * d[k] - q[k]) * (1 if k < 2 else 1000)) ** 2 for k in range(3)) ** 0.5
            if dev < 2 and 0 < tt < 1:
                inner.append((tt, q))
        if not inner:
            out.append(p); continue
        seq = [tuple(a)] + [q for _, q in sorted(inner)] + [tuple(b)]
        for u, w in zip(seq, seq[1:]):
            out.append(dict(p, a=list(u), b=list(w)))
    return out
pipes = split_tees(pipes)
_seen = set(); _ded = []
for p in pipes:
    kk = tuple(sorted([tuple(p['a']), tuple(p['b'])]))
    if kk in _seen:
        continue
    _seen.add(kk); _ded.append(p)
pipes = _ded

model = dict(sprinklers=sprinklers, pipes=pipes, pk=pk,
             src={'1': SRC1, '2': SRC2},
             levels=dict(Z1_BR=Z1_BR, Z1_SPR=Z1_SPR, Z1_MAIN=Z1_MAIN, Z2_MAIN=Z2_MAIN, ZB_RING=ZB_RING, Z_UU_OUT=Z_UU_OUT,
                         Y_RING1=Y_RING1, Y_RING2=Y_RING2, X_R0=X_R0, X_R1=X_R1, X_VPV_TAP=X_VPV_TAP,
                         X_HDR=X_HDR, Y_HDR=Y_HDR, Z_HDR=Z_HDR, X_SRC=X_SRC, X_SRC2=X_SRC2, Y_SRC=Y_SRC))
json.dump(model, open(os.path.join(HERE, 'model.json'), 'w'), ensure_ascii=False)
from collections import Counter
print('оросители:', Counter(s['sec'] for s in sprinklers), 'всего', len(sprinklers))
print('по группам:', Counter((s['sec'], s['grp']) for s in sprinklers))
print('ПК шкафов:', len(pk), 'кранов:', sum(p['n'] for p in pk))
print('труб сегментов:', len(pipes))
