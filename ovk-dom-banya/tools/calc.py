"""Принципиальные решения ОВиК: дом и баня, д. Исаково (Истринский г.о., МО).

Укрупнённый расчёт теплопотерь по помещениям (СП 50.13330.2024, СП 60.13330.2020, прил. для
полов по грунту), нагрузок охлаждения, воздухообменов, ГВС, мощности котла.
Результат — calc.json (для пояснительной записки и листов).

Ориентация по листу «Привязка» АР: верх плана (оси Д–Ж дома, ось В бани) смотрит на северо-запад,
низ (ось А) — на юго-восток, ось 1 — на юго-запад, правая ось (5 дома, 4 бани) — на северо-восток.
"""
import json
import math

# ---------------- климат: СП 131.13330.2025 ----------------
CLIMATE = dict(
    t_out=-25.0,        # Можайск, пятидневка 0,92 (табл. 5.1); Москва -23 — город, теплее
    z_hp=208, t_hp=-2.0,  # Можайск, период со средней суточной <= 8 °C
    t_summer=26.0,      # Москва, параметры Б тёплого периода (обеспеченность 0,98, табл. 6.1)
    h_summer=57.8,      # Москва, энтальпия 0,98, табл. 16.2
)

# ---------------- ограждения ----------------
def r_layers(*layers, rsi=1 / 8.7, rse=1 / 23):
    return rsi + sum(d / l for d, l in layers) + rse


R_WALL_COND = r_layers((0.02, 0.93), (0.40, 0.117), (0.02, 0.76))   # штукатурка, газобетон D400 (λБ), декор. штукатурка
R_WALL = 0.90 * R_WALL_COND                                          # r = 0,90 — швы, перемычки, армирование
R_ROOF = 0.95 * r_layers((0.20, 2.04), (0.20, 0.041))                 # ж/б плита + Руф Баттс 200 (λБ 0,041)
R_WIN = 0.68                                                          # данные Заказчика
R_DOOR = 0.80                                                         # данные Заказчика
R_GATE = 0.50                                                         # секционные ворота (принято)
R_INT = r_layers((0.20, 0.14), rse=1 / 8.7)                           # внутр. стена газобетон 200 (гараж)
R_FLOOR_GAR = r_layers((0.20, 2.04), (0.05, 0.034), (0.10, 0.93), rse=1 / 8.7)  # перекрытие над гаражом
R_INS_FLOOR = 0.10 / 0.034                                            # ЭППС 100 в полу по грунту
ZONES = [(2.0, 2.1), (4.0, 4.3), (6.0, 8.6), (1e9, 14.2)]             # зоны пола по грунту, R_нп

U = dict(wall=1 / R_WALL, roof=1 / R_ROOF, win=1 / R_WIN, door=1 / R_DOOR, gate=1 / R_GATE,
         int=1 / R_INT, flgar=1 / R_FLOOR_GAR)

# добавочные потери на ориентацию (СП 60, прил.): С, СВ, В, СЗ — 0,10; ЮВ, З — 0,05; Ю, ЮЗ — 0
ORIENT = {'up': ('СЗ', 0.10), 'down': ('ЮВ', 0.05), 'left': ('ЮЗ', 0.0), 'right': ('СВ', 0.10)}

# ---------------- окна и двери (спецификации АР) ----------------
OP = {  # марка: (ширина, высота, тип)
    'О-1': (4.2, 3.0, 'win'), 'О-2': (1.0, 3.0, 'win'), 'О-3': (6.0, 3.0, 'win'), 'О-4': (1.8, 0.75, 'win'),
    'О-6': (3.0, 2.5, 'win'), 'О-8': (3.0, 3.0, 'win'), 'О-9': (1.0, 3.0, 'win'), 'О-10': (6.0, 3.0, 'win'),
    'О-13': (2.42, 3.0, 'win'), 'Д-1': (1.1, 3.0, 'door'), 'В-1': (6.0, 3.0, 'gate'),
    # баня
    'бО-1': (4.7, 2.75, 'win'), 'бО-2': (4.16, 2.75, 'win'), 'бО-3': (1.0, 2.75, 'win'), 'бО-4': (1.0, 0.5, 'win'),
    'бО-5': (0.8, 0.75, 'win'), 'бО-6': (1.8, 0.75, 'win'), 'бД-1': (1.0, 2.75, 'door'),
}

H1, H2, HV, HB = 3.65, 3.5, 3.4, 3.2   # высота наружной стены: 1 эт., 2 эт., верх второго света, баня

# Наружные стены по грунту — для зон пола (оси, м). Дом: начало — пересечение осей 1/А.
EXT_HOUSE = [((0, 0), (12.6, 0)), ((0, 0), (0, 13.8)), ((0, 13.8), (9.5, 13.8)), ((9.5, 13.8), (9.5, 16.7)),
             ((9.5, 16.7), (12.6, 16.7)), ((12.6, 16.7), (12.6, 13.8)), ((12.6, 13.8), (20, 13.8)),
             ((20, 8.9), (20, 13.8))]
EXT_GARAGE = [((12.6, 1.1), (20, 1.1)), ((20, 1.1), (20, 8.9))]
EXT_BATH = [((0, 0), (5.4, 0)), ((5.4, 0), (5.4, 2.0)), ((5.4, 2.0), (10.5, 2.0)), ((10.5, 2.0), (10.5, 0)),
            ((10.5, 0), (15.9, 0)), ((15.9, 0), (15.9, 6.6)), ((15.9, 6.6), (0, 6.6)), ((0, 6.6), (0, 0))]


def seg_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def ground_zones(rect, segs, area):
    """Площади зон I–IV пола по грунту в помещении (сетка 0,1 м), приведённые к площади помещения."""
    x0, y0, x1, y1 = rect
    n = [0, 0, 0, 0]
    step = 0.1
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    for i in range(nx):
        for j in range(ny):
            p = (x0 + (i + 0.5) * step, y0 + (j + 0.5) * step)
            d = min(seg_dist(p, a, b) for a, b in segs)
            for k, (lim, _) in enumerate(ZONES):
                if d < lim:
                    n[k] += 1
                    break
    tot = sum(n)
    return [area * c / tot for c in n]


# ---------------- помещения ----------------
# walls: (сторона плана, длина по наружному обмеру, высота, [марки проёмов])
# other: (что, площадь, U, ti - t_граница)  — потери в неотапливаемые/холодные помещения
R = []


def room(**k):
    k.setdefault('walls', []); k.setdefault('roof', 0.0); k.setdefault('other', [])
    k.setdefault('ground', None); k.setdefault('n_inf', 0.0); k.setdefault('L_vent', 0.0)
    k.setdefault('extra', 0.0); k.setdefault('h', 3.4)
    R.append(k)


T_LIV, T_HALL, T_WET, T_GAR = 23, 22, 25, 10
# ---- дом, 1 этаж ----
room(bld='Дом', fl=1, no='1.2', name='Прихожая', area=15.52, ti=T_HALL, h=3.35,
     walls=[('down', 3.4, H1, ['Д-1'])], roof=3.4 * 1.1, ground=((6.1, 0, 9.5, 4.6), EXT_HOUSE), n_inf=0.5,
     heat='ТП', cool=False)
room(bld='Дом', fl=1, no='1.3', name='Тамбур', area=11.07, ti=T_HALL, h=3.35,
     walls=[('down', 2.9, H1, [])], roof=2.9 * 0.8, ground=((9.7, 0.3, 12.6, 4.4), EXT_HOUSE),
     other=[('стена к гаражу', 4.1 * H1, U['int'], T_HALL - T_GAR)], heat='ТП', cool=False)
room(bld='Дом', fl=1, no='1.4', name='С/у', area=4.46, ti=T_WET, h=3.0,
     ground=((9.7, 4.4, 12.6, 6.3), EXT_HOUSE), other=[('стена к гаражу', 1.9 * H1, U['int'], T_WET - T_GAR)],
     heat='ТП', cool=False)
room(bld='Дом', fl=1, no='1.5', name='Гараж', area=52.90, ti=T_GAR, h=3.4,
     walls=[('down', 7.6, H1, ['В-1']), ('right', 8.0, H1, ['О-4', 'О-4'])], roof=7.4 * 5.2,
     ground=((12.6, 1.1, 20, 8.9), EXT_GARAGE), n_inf=0.5, heat='ТП (дежурный)', cool=False)
room(bld='Дом', fl=1, no='1.6', name='Топочная', area=18.20, ti=15, h=3.45,
     walls=[('right', 5.1, H1, ['О-2', 'Д-1']), ('up', 4.6, H1, [])], ground=((15.6, 8.9, 20, 13.8), EXT_HOUSE),
     other=[('стена к гаражу', 4.4 * H1, U['int'], 15 - T_GAR)], L_vent=3 * 18.20 * 3.45,
     heat='ТП + радиатор', cool=False)
room(bld='Дом', fl=1, no='1.7', name='Тамбур', area=5.66, ti=20, h=3.35,
     ground=((12.6, 8.9, 15.6, 11.4), EXT_HOUSE), other=[('стена к гаражу', 3.0 * H1, U['int'], 20 - T_GAR)],
     heat='ТП', cool=False)
room(bld='Дом', fl=1, no='1.8', name='Кладовая', area=6.96, ti=18, h=3.35,
     walls=[('up', 3.0, H1, [])], ground=((12.6, 11.4, 15.6, 13.8), EXT_HOUSE), heat='ТП', cool=False)
room(bld='Дом', fl=1, no='1.9', name='Лестница-холл', area=23.90, ti=T_HALL, h=3.4,
     walls=[('up', 3.5, H1, ['О-13']), ('left', 2.9, H1, []), ('right', 2.9, H1, [])],
     ground=((9.5, 6.3, 12.6, 16.7), EXT_HOUSE), n_inf=0.3, heat='ТП', cool=False)
room(bld='Дом', fl=1, no='1.10', name='Кухня-гостиная (второй свет)', area=65.78, ti=T_LIV, h=7.05,
     walls=[('left', 7.5, H1, ['О-2', 'О-2']), ('up', 9.7, H1, ['О-3']),
            ('left', 6.1, HV, ['О-9']), ('up', 9.7, HV, ['О-10'])],
     roof=9.5 * 5.9, ground=((0, 6.3, 9.5, 13.8), EXT_HOUSE), n_inf=0.3, extra=0.06,
     heat='ТП + внутрипольные конвекторы', cool=True, people=7, equip=1500)
room(bld='Дом', fl=1, no='1.11', name='Бильярдная', area=33.92, ti=T_LIV, h=3.35,
     walls=[('left', 6.5, H1, []), ('down', 6.3, H1, ['О-1'])], roof=6.1 * 1.1,
     ground=((0, 0, 6.1, 6.3), EXT_HOUSE), n_inf=0.3, heat='ТП + внутрипольные конвекторы', cool=True,
     people=4, equip=300)
# ---- дом, 2 этаж ----
room(bld='Дом', fl=2, no='2.1', name='Лестница-холл', area=25.11, ti=T_HALL, h=3.2,
     walls=[('up', 3.5, H2, ['О-13']), ('left', 2.9, H2, []), ('right', 1.7, H2, [])], roof=30.0, n_inf=0.3,
     heat='радиатор', cool=False)
room(bld='Дом', fl=2, no='2.2', name='Галерея', area=13.34, ti=T_HALL, h=3.2,
     walls=[('left', 1.6, H2, ['О-9'])], roof=9.5 * 1.6, n_inf=0.3, heat='радиатор', cool=False)
room(bld='Дом', fl=2, no='2.3', name='Спальня', area=19.40, ti=T_LIV, h=3.2,
     walls=[('left', 5.4, H2, []), ('down', 4.4, H2, ['О-6'])], roof=4.2 * 5.2, n_inf=0.3,
     heat='радиатор', cool=True, people=2, equip=150)
room(bld='Дом', fl=2, no='2.4', name='Кабинет', area=18.43, ti=T_LIV, h=3.2,
     walls=[('down', 3.9, H2, ['О-6'])], roof=3.9 * 5.2, n_inf=0.3, heat='радиатор', cool=True,
     people=2, equip=400)
room(bld='Дом', fl=2, no='2.5', name='Спальня', area=19.40, ti=T_LIV, h=3.2,
     walls=[('down', 4.5, H2, ['О-6']), ('right', 5.4, H2, [])], roof=4.3 * 5.2, n_inf=0.3,
     heat='радиатор', cool=True, people=2, equip=150)
room(bld='Дом', fl=2, no='2.6', name='Гардеробная', area=13.20, ti=20, h=3.2,
     walls=[('up', 3.0, H2, ['О-9'])], roof=3.0 * 4.9, n_inf=0.2, heat='радиатор', cool=False)
room(bld='Дом', fl=2, no='2.7', name='Спальня', area=18.20, ti=T_LIV, h=3.2,
     walls=[('up', 4.6, H2, ['О-8']), ('right', 5.1, H2, [])], roof=4.4 * 4.9, n_inf=0.3,
     heat='радиатор', cool=True, people=2, equip=150)
room(bld='Дом', fl=2, no='2.8', name='С/у', area=9.20, ti=T_WET, h=2.75,
     walls=[('down', 4.3, H2, ['О-4']), ('right', 2.8, H2, [])], roof=4.3 * 2.6,
     other=[('пол над гаражом', 4.3 * 2.6, U['flgar'], T_WET - T_GAR)], heat='ТП + полотенцесушитель', cool=False)
room(bld='Дом', fl=2, no='2.9', name='С/у', area=6.67, ti=T_WET, h=2.75,
     walls=[('down', 3.0, H2, ['О-4'])], roof=3.0 * 2.6,
     other=[('пол над гаражом', 3.0 * 2.6, U['flgar'], T_WET - T_GAR)], heat='ТП + полотенцесушитель', cool=False)
# ---- баня ----
room(bld='Баня', fl=1, no='б2', name='Прихожая', area=6.30, ti=T_HALL, h=3.0,
     walls=[('left', 2.0, HB, ['бД-1']), ('down', 1.9, HB, ['бО-6'])], roof=7.6,
     ground=((10.5, 0, 12.4, 4.0), EXT_BATH), L_vent=15, heat='ТП', cool=False)
room(bld='Баня', fl=1, no='б3', name='С/у', area=4.57, ti=T_WET, h=3.0,
     walls=[('down', 3.7, HB, ['бО-6']), ('right', 2.2, HB, [])], roof=7.0,
     ground=((12.4, 0, 15.9, 2.0), EXT_BATH), L_vent=25, heat='ТП', cool=False)
room(bld='Баня', fl=1, no='б4', name='Раздевалка', area=5.49, ti=24, h=3.0,
     walls=[('right', 2.0, HB, ['бО-5'])], roof=7.0, ground=((12.4, 2.0, 15.9, 4.0), EXT_BATH), L_vent=15,
     heat='ТП', cool=False)
room(bld='Баня', fl=1, no='б5', name='Спальня', area=12.75, ti=T_LIV, h=3.0,
     walls=[('up', 5.6, HB, []), ('right', 2.8, HB, ['бО-3'])], roof=14.0,
     ground=((10.5, 4.0, 15.9, 6.6), EXT_BATH), L_vent=40, heat='радиатор', cool=False)
room(bld='Баня', fl=1, no='б6', name='Комната отдыха', area=21.42, ti=T_LIV, h=3.0,
     walls=[('up', 5.1, HB, []), ('down', 5.1, HB, ['бО-1'])], roof=23.5,
     ground=((5.4, 2.0, 10.5, 6.6), EXT_BATH), L_vent=50,
     heat='ТП + внутрипольный конвектор с вентилятором', cool=False)
room(bld='Баня', fl=1, no='б7', name='Помывочная', area=22.16, ti=T_WET, h=3.0,
     walls=[('left', 7.0, HB, ['бО-3']), ('down', 5.6, HB, ['бО-2']), ('up', 2.45, HB, [])], roof=24.0,
     ground=((0, 0, 5.4, 6.6), EXT_BATH), L_vent=60, heat='ТП', cool=False)


def calc_room(r):
    ti, dt = r['ti'], r['ti'] - CLIMATE['t_out']
    items, sides = [], set()
    for side, length, h, ops in r['walls']:
        o, add = ORIENT[side]
        sides.add(side)
        a_gross = length * h
        a_op = 0
        for m in ops:
            w, hh, typ = OP[m]
            a = w * hh
            a_op += a
            items.append((f'{m} ({o})', a, U[typ], dt, add))
        items.append((f'стена ({o})', a_gross - a_op, U['wall'], dt, add))
    if r['roof']:
        items.append(('покрытие', r['roof'], U['roof'], dt, 0))
    if r['ground']:
        rect, segs = r['ground']
        for k, a in enumerate(ground_zones(rect, segs, r['area'])):
            if a > 0.05:
                items.append((f'пол по грунту, зона {"I II III IV".split()[k]}', a,
                              1 / (ZONES[k][1] + R_INS_FLOOR), dt, 0))
    corner = 0.05 if len(sides) >= 2 else 0.0
    q_tr = 0
    rows = []
    for name, a, u, d, add in items:
        is_vert = not name.startswith(('покрытие', 'пол'))
        k = 1 + (add + corner + r['extra'] if is_vert else r['extra'] if name == 'покрытие' else 0)
        q = a * u * d * k
        q_tr += q
        rows.append(dict(el=name, A=round(a, 2), U=round(u, 3), dT=d, k=round(k, 2), Q=round(q)))
    for name, a, u, d in r['other']:
        q = a * u * d
        q_tr += q
        rows.append(dict(el=name, A=round(a, 2), U=round(u, 3), dT=d, k=1.0, Q=round(q)))
    vol = r['area'] * r['h']
    L = r['L_vent'] if r['L_vent'] else r['n_inf'] * vol
    q_inf = 0.335 * L * dt          # Вт, 0,335 = ρc/3,6 Вт·ч/(м³·К)
    return dict(no=r['no'], name=r['name'], bld=r['bld'], fl=r['fl'], area=r['area'], ti=ti, vol=round(vol),
                Q_tr=round(q_tr), L=round(L), Q_inf=round(q_inf), Q=round(q_tr + q_inf),
                q_m2=round((q_tr + q_inf) / r['area']), heat=r['heat'], rows=rows)


def ufh_capacity(r, res):
    """Теплоотдача тёплого пола: q = 8,92 (tп - tв)^1,1; tп max: 29 °C жилые, 33 °C ванные, 27 °C гараж/топочная."""
    wet = r['ti'] >= 25
    tf = 33 if wet else 29
    if r['no'] in ('1.5',):
        tf = 22
    frac = 0.55 if wet else 0.65 if r['no'] in ('1.10', 'б6') else 0.75 if r['ti'] >= 23 else 0.85
    q = 8.92 * (tf - r['ti']) ** 1.1
    return round(q * r['area'] * frac), round(q), frac, tf


out = dict(climate=CLIMATE, U={k: round(v, 3) for k, v in U.items()},
           R=dict(wall=round(R_WALL, 2), wall_cond=round(R_WALL_COND, 2), roof=round(R_ROOF, 2), win=R_WIN,
                  door=R_DOOR, gate=R_GATE), rooms=[])
for r in R:
    res = calc_room(r)
    if 'ТП' in r['heat']:
        cap, q, frac, tf = ufh_capacity(r, res)
        res.update(ufh=cap, ufh_q=q, ufh_frac=frac, ufh_tf=tf, rest=max(0, res['Q'] - cap))
    out['rooms'].append(res)

# ---------------- итоги отопления ----------------
def tot(f):
    return sum(x['Q'] for x in out['rooms'] if f(x))


Q_house = tot(lambda x: x['bld'] == 'Дом' and x['no'] != '1.5')
Q_gar = tot(lambda x: x['no'] == '1.5')
Q_bath = tot(lambda x: x['bld'] == 'Баня')

# ---------------- вентиляция дома (ПВУ с роторным рекуператором) ----------------
# СП 54.13330.2022 / СП 55.13330.2016, СП 60.13330.2020 прил. К: жилые — 30 м³/ч на чел. (не менее 3 м³/ч·м²
# для жилых до 20 м²/чел.); кухня с электроплитой — 60 м³/ч; ванная — 25, уборная — 25, совмещённый с/у — 50.
SUP = [('1.10', 'Кухня-гостиная', 210), ('1.11', 'Бильярдная', 120), ('1.2', 'Прихожая', 30),
       ('2.3', 'Спальня', 60), ('2.4', 'Кабинет', 60), ('2.5', 'Спальня', 60), ('2.7', 'Спальня', 60),
       ('2.2', 'Галерея', 30)]
EXH = [('1.10', 'Кухня (общая вытяжка, без зонта)', 90), ('1.10', 'Верхняя зона второго света', 120),
       ('1.4', 'С/у', 50), ('1.8', 'Кладовая', 30), ('1.3', 'Тамбур (гардероб)', 40), ('2.8', 'С/у', 75),
       ('2.9', 'С/у', 75), ('2.6', 'Гардеробная', 60), ('2.1', 'Лестница-холл', 90)]
L_sup = sum(x[2] for x in SUP)
L_exh = sum(x[2] for x in EXH)
ETA = 0.80                      # роторный рекуператор, температурная эффективность
t_sup = 20.0
t_after = CLIMATE['t_out'] + ETA * (T_LIV - 1 - CLIMATE['t_out'])
Q_vent_heater = 0.335 * L_sup * (t_sup - t_after)

# ---------------- ГВС ----------------
# пиковый час: ванна 180 л (40 °C) + 2 душа по 8 мин × 9 л/мин + кухня 30 л; 3 + 4 гостя
peak_40 = 180 + 2 * 8 * 9 + 30
v60_house = peak_40 * (40 - 10) / (60 - 10)
# баня: ванна 180 л + 2 душа + умывальники
peak_40_b = 180 + 2 * 8 * 9 + 20
v60_bath = peak_40_b * (40 - 10) / (60 - 10)
P_coil_house = 28.0   # кВт, змеевик бойлера 300 л
P_coil_bath = 20.0

# ---------------- котёл ----------------
Q_heat_all = Q_house + Q_gar + Q_bath + Q_vent_heater
P_boiler_need = 1.10 * Q_heat_all / 1000           # +10 % — запас на прогрев и потери трубопроводов
P_boiler = 48 if P_boiler_need <= 48 else 56   # каскад 2×24 или 2×28 кВт
gas_m3h = P_boiler / (0.95 * 9.3)                   # м³/ч при Qн = 9,3 кВт·ч/м³ (33,5 МДж/м³), КПД 95 %
gas_stove = 1.2

# ---------------- охлаждение ----------------
# Солнечный поток через остекление (пик для ориентации, 56° с.ш., июль) × g_eff 0,40 (2-кам. с i-стеклом,
# светлые шторы); трансмиссия окон и покрытия; люди 130 Вт (явн.+скр.); освещение 6 Вт/м²; оборудование.
I_SOL = {'СЗ': 400, 'ЮВ': 420, 'ЮЗ': 480, 'СВ': 380}
G_EFF = 0.40
cool = []
for r in R:
    if not r.get('cool'):
        continue
    qs = 0
    a_win = 0
    for side, length, h, ops in r['walls']:
        o, _ = ORIENT[side]
        for m in ops:
            w, hh, typ = OP[m]
            if typ == 'win':
                qs += w * hh * I_SOL[o] * G_EFF
                a_win += w * hh
    dts = CLIMATE['t_summer'] - r['ti']
    q_tr = a_win * U['win'] * dts + r['roof'] * U['roof'] * 25
    q_p = r.get('people', 2) * 130
    q_l = 6 * r['area']
    q = qs + q_tr + q_p + q_l + r.get('equip', 0)
    cool.append(dict(no=r['no'], name=r['name'], area=r['area'], A_win=round(a_win, 1), Q_sol=round(qs),
                     Q=round(q), q_m2=round(q / r['area'])))
Q_cool = sum(c['Q'] for c in cool)

out.update(Q_house=Q_house, Q_gar=Q_gar, Q_bath=Q_bath, Q_vent_heater=round(Q_vent_heater),
           t_after_rec=round(t_after, 1), L_sup=L_sup, L_exh=L_exh, SUP=SUP, EXH=EXH,
           v60_house=round(v60_house), v60_bath=round(v60_bath), P_coil_house=P_coil_house,
           P_coil_bath=P_coil_bath, Q_heat_all=round(Q_heat_all), P_boiler_need=round(P_boiler_need, 1),
           P_boiler=P_boiler, gas_m3h=round(gas_m3h, 2), gas_total=round(gas_m3h + gas_stove, 1),
           cool=cool, Q_cool=Q_cool)
json.dump(out, open('calc.json', 'w'), ensure_ascii=False, indent=1)

print(f"R стены {R_WALL:.2f} (усл. {R_WALL_COND:.2f}), R покрытия {R_ROOF:.2f}; U: " +
      ', '.join(f'{k} {v:.3f}' for k, v in U.items()))
print(f"{'№':5} {'помещение':32} {'S':>6} {'tв':>3} {'Qогр':>6} {'L':>5} {'Qинф':>5} {'Q':>6} {'Вт/м²':>5} {'ТП max':>6} {'доп.':>5}  приборы")
for x in out['rooms']:
    print(f"{x['no']:5} {x['name'][:32]:32} {x['area']:6.2f} {x['ti']:3} {x['Q_tr']:6} {x['L']:5} {x['Q_inf']:5} "
          f"{x['Q']:6} {x['q_m2']:5} {x.get('ufh', ''):>6} {x.get('rest', ''):>5}  {x['heat']}")
print(f"Дом (без гаража) {Q_house} Вт, гараж {Q_gar}, баня {Q_bath}, догрев ПВУ {Q_vent_heater:.0f} "
      f"(после рекуператора {t_after:.1f} °C, L={L_sup}/{L_exh})")
print(f"Всего {Q_heat_all/1000:.1f} кВт ×1,1 = {P_boiler_need:.1f} → котёл {P_boiler} кВт, газ {gas_m3h:.2f} м³/ч")
print(f"ГВС: дом {v60_house:.0f} л при 60 °C в пиковый час, баня {v60_bath:.0f} л")
for c in cool:
    print(f"  холод {c['no']:5} {c['name'][:28]:28} {c['area']:6.1f} м², окна {c['A_win']:5} м², "
          f"Qсол {c['Q_sol']:5}, Q {c['Q']:5} Вт ({c['q_m2']} Вт/м²)")
print(f"Холод всего {Q_cool/1000:.1f} кВт")
