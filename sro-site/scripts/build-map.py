# -*- coding: utf-8 -*-
"""Генератор карты регионов для src/content/mapData.ts.

Раньше контур России был нарисован от руки по опорным точкам. Он был
узнаваемым, но регионы на нём показать было нечем — только точки-булавки.
Здесь карта строится из настоящих границ субъектов, поэтому регион, где
заказчик помогает вступить, можно закрасить целиком.

Источник границ (с 20.10.2026) — Natural Earth, слой «Admin 1 – States,
Provinces», масштаб 1:10 млн, общественное достояние
(https://www.naturalearthdata.com, копия на GitHub:
nvkelso/natural-earth-vector). Субъектов на карте 89, как в Конституции РФ:
85 записей набора с кодом страны RUS (в их числе Республика Крым
и Севастополь) и четыре субъекта, принятых в 2022 году, — их набор ведёт
под кодами UA-14, UA-09, UA-23, UA-65 и берётся по коду. Москва — в нынешних
границах, с Новой Москвой и Зеленоградом.

До 20.10.2026 карта строилась из click_that_hood (Code for America) — это
границы 2013 года: 83 субъекта, Москва без Новой Москвы, Крым дорисован
от руки по опорным точкам, четырёх новых субъектов не было вовсе.

Субъекты выбираются по коду ISO 3166-2 из набора, а не по имени: русские
имена там с ошибками (у Алтайского края стоит «Республика Алтай»).
У Москвы и Московской области коды в наборе перепутаны местами
(RU-MOS — город), но обе идут одним пятном, и на карте это не видно.

Проекция — равновеликая коническая Альберса со стандартными параллелями
52° и 64° и осевым меридианом 100° в. д.: именно она даёт узнаваемую
«арку» России, где Калининград и Чукотка опускаются к краям.

Запуск (нужен интернет, файл границ — 40 МБ — в репозитории не хранится):

    curl -sSL -o /tmp/ne1.geojson \\
      https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson
    python3 scripts/build-map.py /tmp/ne1.geojson > src/content/mapData.ts
"""
import json
import math
import sys

# Стандартные параллели и осевой меридиан.
LAT1, LAT2, LON0, LAT0 = 52.0, 64.0, 100.0, 30.0
VIEW_W = 1000.0          # ширина viewBox
PAD = 6.0                # поля, чтобы обводка не срезалась по краю
TOLERANCE = 1.1          # упрощение Дугласа–Пейкера, в пикселях итоговой карты
MIN_RING = 3.5           # кольца мельче этого (в пикселях) выбрасываем

_n = (math.sin(math.radians(LAT1)) + math.sin(math.radians(LAT2))) / 2
_C = math.cos(math.radians(LAT1)) ** 2 + 2 * _n * math.sin(math.radians(LAT1))
_rho0 = math.sqrt(_C - 2 * _n * math.sin(math.radians(LAT0))) / _n


def project(lon, lat):
    """Альберс. Долготу западнее нуля переносим за 180° — иначе Чукотка,
    которая переходит через антимеридиан, улетает на другой край карты."""
    if lon < 0:
        lon += 360
    rho = math.sqrt(max(_C - 2 * _n * math.sin(math.radians(lat)), 0.0)) / _n
    theta = math.radians(_n * (lon - LON0))
    return rho * math.sin(theta), _rho0 - rho * math.cos(theta)


def simplify(pts, tol):
    """Дуглас–Пейкер без рекурсии: у Якутии колец на десятки тысяч точек,
    рекурсивная версия упирается в лимит стека."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    tol2 = tol * tol
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        ax, ay = pts[i]
        bx, by = pts[j]
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        best, best_k = -1.0, -1
        for k in range(i + 1, j):
            px, py = pts[k]
            if seg2 == 0:
                d2 = (px - ax) ** 2 + (py - ay) ** 2
            else:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
                d2 = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2
            if d2 > best:
                best, best_k = d2, k
        if best > tol2:
            keep[best_k] = True
            stack.append((i, best_k))
            stack.append((best_k, j))
    return [p for p, k in zip(pts, keep) if k]


def rings_of(geom):
    """Плоский список колец: и Polygon, и MultiPolygon, вместе с дырками."""
    t = geom['type']
    if t == 'Polygon':
        return list(geom['coordinates'])
    if t == 'MultiPolygon':
        return [ring for poly in geom['coordinates'] for ring in poly]
    return []


def area(pts):
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


# Четыре субъекта 2022 года: в наборе они под кодами UA.
ADDED_2022 = {'UA-14', 'UA-09', 'UA-23', 'UA-65'}

# Какие субъекты закрашиваем и под каким ключом. Ключи — те же, что в LABELS,
# коды — ISO 3166-2 в записи Natural Earth. «Крым» у заказчика — Республика
# Крым; Севастополь — отдельный субъект, его в списке нет, и он остаётся фоном.
HIGHLIGHT = {
    'spb': ['RU-SPE', 'RU-LEN'],
    'msk': ['RU-MOS', 'RU-MOW'],
    'kazan': ['RU-TA'],
    'nnov': ['RU-NIZ'],
    'kostroma': ['RU-KOS'],
    'ufa': ['RU-BA'],
    'ekb': ['RU-SVE'],
    'krasnodar': ['RU-KDA'],
    'rostov': ['RU-ROS'],
    'krasnoyarsk': ['RU-KYA'],
    'irkutsk': ['RU-IRK'],
    'yakutsk': ['RU-SA'],
    'crimea': ['UA-43'],
}

# Куда ставить подпись и метку. Города настоящие, координаты — их.
CITIES = {
    'spb': (30.31, 59.94), 'msk': (37.62, 55.75), 'kazan': (49.11, 55.79),
    'nnov': (44.00, 56.33), 'kostroma': (40.93, 57.77), 'ufa': (55.97, 54.74),
    'irkutsk': (104.30, 52.29), 'krasnodar': (38.98, 45.04),
    'krasnoyarsk': (92.87, 56.01), 'rostov': (39.72, 47.23),
    'yakutsk': (129.73, 62.03), 'crimea': (34.10, 45.05), 'ekb': (60.61, 56.84),
}

src = json.load(open(sys.argv[1], encoding='utf-8'))
raw = {}
for feat in src['features']:
    props = feat['properties']
    code = props['iso_3166_2']
    if props['adm0_a3'] != 'RUS' and code not in ADDED_2022:
        continue
    raw.setdefault(code, []).extend(
        [[project(lon, lat) for lon, lat in ring] for ring in rings_of(feat['geometry'])]
    )
# 85 записей с кодом RUS — это 85 субъектов и безымянный островок
# (RU-X01~, «Russia minor island»): он идёт фоном.
subjects = [code for code in raw if not code.endswith('~')]
assert len(subjects) == 89, f'субъектов {len(subjects)}, а не 89'
for key in HIGHLIGHT:
    for code in HIGHLIGHT[key]:
        assert code in raw, f'нет в наборе границ: {code}'

# Общий охват — по всем кольцам сразу, чтобы карта встала в viewBox целиком.
flat = [p for rings in raw.values() for ring in rings for p in ring]
minx = min(p[0] for p in flat)
maxx = max(p[0] for p in flat)
miny = min(p[1] for p in flat)
maxy = max(p[1] for p in flat)
scale = (VIEW_W - 2 * PAD) / (maxx - minx)
view_h = round((maxy - miny) * scale + 2 * PAD, 1)


def to_view(pts):
    # По вертикали переворачиваем: в проекции y растёт на север, в SVG — вниз.
    return [((x - minx) * scale + PAD, (maxy - y) * scale + PAD) for x, y in pts]


def d_of(rings):
    out = []
    for ring in rings:
        ring = to_view(ring)
        w = max(p[0] for p in ring) - min(p[0] for p in ring)
        h = max(p[1] for p in ring) - min(p[1] for p in ring)
        if max(w, h) < MIN_RING:
            continue
        pts = simplify(ring, TOLERANCE)
        if len(pts) < 3:
            continue
        out.append('M' + 'L'.join(f'{x:.1f} {y:.1f}' for x, y in pts) + 'Z')
    return ''.join(out)


mine = {name: key for key, names in HIGHLIGHT.items() for name in names}
base = []
active = {}
for key, names in HIGHLIGHT.items():
    rings = [r for name in names for r in raw[name]]
    active[key] = d_of(rings)
for name, rings in raw.items():
    if name in mine:
        continue
    d = d_of(rings)
    if d:
        base.append(d)

anchors = {}
for key, (lon, lat) in CITIES.items():
    x, y = to_view([project(lon, lat)])[0]
    anchors[key] = (round(x, 1), round(y, 1))

esc = lambda s: s.replace("'", "\\'")
print('// Сгенерировано scripts/build-map.py — руками не править.')
print('// Границы субъектов: Natural Earth, Admin 1, 1:10 млн (общественное достояние);')
print('// 89 субъектов РФ. Подробности — в шапке scripts/build-map.py.')
print('// Проекция Альберса, стандартные параллели 52° и 64°, меридиан 100° в. д.')
print('')
print(f'export const VIEW_BOX = \'0 0 {VIEW_W:.0f} {view_h}\'')
print('')
print('// Остальная страна одним контуром: она только фон, кликать в ней нечего.')
print(f"export const MAP_BASE = '{esc(''.join(base))}'")
print('')
print('// Регионы, где заказчик помогает вступить. Ключи совпадают с LABELS.')
print('export const MAP_ACTIVE: Record<string, string> = {')
for key in HIGHLIGHT:
    print(f"  {key}: '{esc(active[key])}',")
print('}')
print('')
print('// Куда ставить метку города и подпись при наведении.')
print('export const MAP_ANCHORS: Record<string, { x: number; y: number }> = {')
for key, (x, y) in anchors.items():
    print(f'  {key}: {{ x: {x}, y: {y} }},')
print('}')
