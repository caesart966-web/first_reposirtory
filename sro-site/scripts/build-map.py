# -*- coding: utf-8 -*-
"""Генератор карты регионов для src/content/regions.ts.

Раньше контур России был нарисован от руки по опорным точкам. Он был
узнаваемым, но регионы на нём показать было нечем — только точки-булавки.
Здесь карта строится из настоящих границ субъектов, поэтому регион, где
заказчик помогает вступить, можно закрасить целиком.

Источник границ: https://github.com/codeforamerica/click_that_hood
(public/data/russia.geojson), лицензия MIT, 83 субъекта, имена по-русски.
Крым в этот набор не входит (данные 2013 года), его контур остался прежним —
по опорным точкам, они ниже в CRIMEA.

Проекция — равновеликая коническая Альберса со стандартными параллелями
52° и 64° и осевым меридианом 100° в. д.: именно она даёт узнаваемую
«арку» России, где Калининград и Чукотка опускаются к краям. Линейная
проекция по широте и долготе, которая была здесь раньше, растягивала
север и делала страну плоской лентой.

Запуск (нужен интернет, файл границ не хранится в репозитории):

    curl -sSL -o /tmp/russia.geojson \\
      https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/russia.geojson
    python3 scripts/build-map.py /tmp/russia.geojson > src/content/mapData.ts
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


# Крым: собственных границ в наборе нет, опорные точки те же, что были
# в старой карте. Список регионов у заказчика Крым включает.
CRIMEA = [(33.60, 46.16), (33.05, 46.04), (32.55, 45.60), (32.48, 45.36),
          (33.20, 45.15), (33.55, 44.92), (33.42, 44.56), (33.80, 44.39),
          (34.40, 44.50), (35.10, 44.80), (35.50, 45.02), (36.10, 45.02),
          (36.65, 45.35), (36.10, 45.45), (35.50, 45.40), (35.30, 45.70),
          (34.80, 45.95), (34.20, 46.10)]

# Какие субъекты закрашиваем и под каким ключом. Ключи — те же, что в LABELS.
HIGHLIGHT = {
    'spb': ['Санкт-Петербург', 'Ленинградская область'],
    'msk': ['Москва', 'Московская область'],
    'kazan': ['Татарстан'],
    'nnov': ['Нижегородская область'],
    'kostroma': ['Костромская область'],
    'ufa': ['Башкортостан'],
    'ekb': ['Свердловская область'],
    'krasnodar': ['Краснодарский край'],
    'rostov': ['Ростовская область'],
    'krasnoyarsk': ['Красноярский край'],
    'irkutsk': ['Иркутская область'],
    'yakutsk': ['Республика Саха (Якутия)'],
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
    name = feat['properties']['name']
    raw.setdefault(name, []).extend(
        [[project(lon, lat) for lon, lat in ring] for ring in rings_of(feat['geometry'])]
    )
raw['Крым'] = [[project(lon, lat) for lon, lat in CRIMEA]]
for key in HIGHLIGHT:
    for name in HIGHLIGHT[key]:
        assert name in raw, f'нет в наборе границ: {name}'
HIGHLIGHT['crimea'] = ['Крым']

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
print('// Границы субъектов: github.com/codeforamerica/click_that_hood (MIT).')
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
