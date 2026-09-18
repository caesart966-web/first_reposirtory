# -*- coding: utf-8 -*-
"""Генератор карты России для src/config/mapdata.ts.

ЗАЧЕМ КАРТА НА САЙТЕ ПРО СРО. Единственный факт этого сайта, у которого
есть форма карты, — региональный принцип: строительная компания вправе
вступить только в СРО своего субъекта РФ (ч. 3 ст. 55.6 ГрК РФ).
Объяснять это абзацем можно, но карта показывает сразу: субъектов много,
границы настоящие, и «рядом» не значит «тот же субъект». Заодно карта —
вход на 33 городские страницы.

ПОЧЕМУ ГРАНИЦЫ НАСТОЯЩИЕ, А НЕ НАРИСОВАННЫЕ. Нарисованный от руки контур
страны узнаваем, но показать на нём субъект нечем — а показать нужно
именно субъект. Здесь берутся границы всех 83 субъектов, и регион города
закрашивается целиком.

Источник границ: https://github.com/codeforamerica/click_that_hood
(public/data/russia.geojson), лицензия MIT, имена по-русски.
Тот же набор и та же проекция, что на прошлом сайте заказчика (sro-site),
чтобы карта не спорила сама с собой между проектами.

Крым в набор не входит — данные 2013 года. Контур взят опорными точками
оттуда же, из sro-site: городской страницы в Крыму нет, ни один факт
сайта от этого контура не зависит, но карта России без него читалась бы
как ошибка вёрстки.

Проекция — равновеликая коническая Альберса, стандартные параллели 52°
и 64°, осевой меридиан 100° в. д. Она даёт узнаваемую «арку», где
Калининград и Чукотка опускаются к краям. Линейная проекция по широте
и долготе растягивает север и делает страну плоской лентой.

Запуск (нужен интернет, файл границ в репозитории не хранится):

    curl -sSL -o /tmp/russia.geojson \\
      https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/russia.geojson
    python3 scripts/build-map.py /tmp/russia.geojson > src/config/mapdata.ts

Результат коммитится, поэтому обычная сборка сайта интернета не требует.
"""
import json
import math
import re
import sys

LAT1, LAT2, LON0, LAT0 = 52.0, 64.0, 100.0, 30.0
VIEW_W = 1000.0          # ширина viewBox
PAD = 5.0                # поля, чтобы обводка не срезалась по краю
# Упрощение Дугласа–Пейкера и отсев мелких колец, в единицах viewBox.
# Карта шириной 1000 единиц рисуется в колонке около 710 px, то есть
# единица — это 0.7 px на экране. 1.8 даёт погрешность контура в 1.3 px
# и экономит 3.7 КБ в сжатом виде против 1.4; на 2.2 (ещё минус 2.7 КБ)
# мелкие субъекты начинают заметно грубеть, и это уже видно глазом.
TOLERANCE = 1.8
MIN_RING = 4.0

# Сетка: меридианы и параллели. Не украшение — это та самая проекция,
# по которой построена карта, и она объясняет, почему страна выгнута дугой.
MERIDIANS = range(20, 200, 20)
PARALLELS = range(40, 85, 10)

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


CRIMEA = [(33.60, 46.16), (33.05, 46.04), (32.55, 45.60), (32.48, 45.36),
          (33.20, 45.15), (33.55, 44.92), (33.42, 44.56), (33.80, 44.39),
          (34.40, 44.50), (35.10, 44.80), (35.50, 45.02), (36.10, 45.02),
          (36.65, 45.35), (36.10, 45.45), (35.50, 45.40), (35.30, 45.70),
          (34.80, 45.95), (34.20, 46.10)]

# Имя субъекта в наборе границ — оно отличается от того, как субъект
# называется в regions.ts: «Республика Татарстан» против «Татарстан».
# Держится здесь, а не в regions.ts: это особенность внешнего набора
# данных, а не факт о городе. Проверяется утверждением ниже — город без
# строки в этой таблице роняет генератор, а не тихо пропадает с карты.
GEO_NAME = {
    'moskva': ['Москва'],
    'sankt-peterburg': ['Санкт-Петербург'],
    'rostov-na-donu': ['Ростовская область'],
}

# Города и их координаты читаются из regions.ts: там единая точка правды
# про города, и заводить вторую здесь нельзя — списки разошлись бы молча.
SRC_TS = 'src/config/regions.ts'
blocks = open(SRC_TS, encoding='utf-8').read().split("\n  {\n")[1:]
CITIES = {}
for b in blocks:
    slug = re.search(r"slug: '([^']+)'", b)
    lon = re.search(r"\n    lon: (-?[\d.]+)", b)
    lat = re.search(r"\n    lat: (-?[\d.]+)", b)
    assert slug, f'в {SRC_TS} блок без slug'
    assert lon and lat, f'у города {slug.group(1)} нет lon/lat в {SRC_TS}'
    CITIES[slug.group(1)] = (float(lon.group(1)), float(lat.group(1)))
assert CITIES, f'не разобрал ни одного города из {SRC_TS}'
for slug in CITIES:
    assert slug in GEO_NAME, (
        f'город {slug} есть в {SRC_TS}, но для него не написано, '
        f'как его субъект называется в наборе границ (GEO_NAME)'
    )

src = json.load(open(sys.argv[1], encoding='utf-8'))
raw = {}
for feat in src['features']:
    name = feat['properties']['name']
    raw.setdefault(name, []).extend(
        [[project(lon, lat) for lon, lat in ring] for ring in rings_of(feat['geometry'])]
    )
raw['Крым'] = [[project(lon, lat) for lon, lat in CRIMEA]]
for slug, names in GEO_NAME.items():
    for name in names:
        assert name in raw, f'нет в наборе границ: {name} (город {slug})'

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


mine = {name: slug for slug, names in GEO_NAME.items() for name in names}
city_d = {slug: d_of([r for name in names for r in raw[name]])
          for slug, names in GEO_NAME.items()}
base = [d for name, rings in raw.items() if name not in mine
        for d in [d_of(rings)] if d]

anchors = {slug: to_view([project(lon, lat)])[0] for slug, (lon, lat) in CITIES.items()}

# Сетка строится по той же проекции, что и границы, поэтому меридианы
# на ней действительно сходятся, а параллели действительно дуги.
grid = []
for lon in MERIDIANS:
    pts = to_view([project(lon, lat) for lat in range(38, 83)])
    grid.append('M' + 'L'.join(f'{x:.1f} {y:.1f}' for x, y in pts))
for lat in PARALLELS:
    pts = to_view([project(lon, lat) for lon in range(18, 192, 2)])
    grid.append('M' + 'L'.join(f'{x:.1f} {y:.1f}' for x, y in pts))

esc = lambda s: s.replace("'", "\\'")
w = sys.stdout.write
w('// Сгенерировано scripts/build-map.py — руками не править.\n')
w('// Границы субъектов: github.com/codeforamerica/click_that_hood (MIT).\n')
w('// Проекция Альберса, стандартные параллели 52° и 64°, меридиан 100° в. д.\n')
w('// Пересобрать: см. шапку scripts/build-map.py.\n')
w('\n')
w(f"export const VIEW_BOX = '0 0 {VIEW_W:.0f} {view_h}'\n")
w('\n')
w('// Субъекты, у которых на сайте нет своей городской страницы: одним\n')
w('// контуром. Каждое кольцо — отдельный подконтур, поэтому обводка рисует\n')
w('// границы всех субъектов, а не только внешний край страны.\n')
w(f"export const MAP_BASE = '{esc(''.join(base))}'\n")
w('\n')
w('// Субъект города — по slug из regions.ts.\n')
w('export const MAP_CITY: Record<string, string> = {\n')
for slug in GEO_NAME:
    w(f"  '{slug}': '{esc(city_d[slug])}',\n")
w('}\n')
w('\n')
w('// Куда ставить метку города.\n')
w('export const MAP_ANCHOR: Record<string, { x: number; y: number }> = {\n')
for slug, (x, y) in anchors.items():
    w(f"  '{slug}': {{ x: {x:.1f}, y: {y:.1f} }},\n")
w('}\n')
w('\n')
w('// Координаты, ПО КОТОРЫМ карта построена. Метки выше уже спроецированы,\n')
w('// и сравнить их с regions.ts глазами нельзя. Правку координат без\n')
w('// пересборки карты ловит scripts/test-geomap.mjs: он сверяет эти числа\n')
w('// с regions.ts и требует перегенерации, если они разошлись.\n')
w('export const MAP_SOURCE: Record<string, { lon: number; lat: number }> = {\n')
for slug, (lon, lat) in CITIES.items():
    w(f"  '{slug}': {{ lon: {lon}, lat: {lat} }},\n")
w('}\n')
w('\n')
w(f'// Меридианы через {MERIDIANS.step}° и параллели через {PARALLELS.step}°.\n')
w('export const MAP_GRID: string[] = [\n')
for d in grid:
    w(f"  '{esc(d)}',\n")
w(']\n')
