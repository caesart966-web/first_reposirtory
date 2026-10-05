#!/usr/bin/env python3
"""
Три варианта главной на выбор заказчику (просьба 05.10.2026: «лицевую
страницу полностью, сейчас суховата, иконки не нравятся»).

Шапка, подвал, окна и скрипты берутся из ../index.html как есть — варианты
отличаются только серединой страницы, и сравнивать заказчик будет именно её.
Середина — src/main-N.html; в ней метки {{…}}, которые этот скрипт
разворачивает в разделы каталога, подборки товаров и карточки магазинов.
Данные магазинов — те же, что в теме (template/common/home.twig).

Запуск: python3 variants/make.py   (из папки stroigeroi-site или откуда угодно)
"""
import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)

VARIANTS = [
    ('1-vitrina', 'v1', 'Вариант 1 — «Витрина»', 'onest'),
    ('2-geroi', 'v2', 'Вариант 2 — «Герой»', 'sg-display-draft'),
    ('3-kamchatka', 'v3', 'Вариант 3 — «Камчатка»', 'rubik'),
]

# Разделы каталога — как в меню сайта (порядок и названия из учётной
# системы). Значок подбирается по слову в названии так же, как в теме
# (template/common/menu.twig), только из другого набора.
CATS = [
    ('А1 САНТЕХНИКА', 'pipe'),
    ('Инструменты', 'toolbox'),
    ('Товар', 'box'),
    ('Электрика и свет', 'bulb'),
    ('Сантехника и инженерные системы', 'pipe'),
    ('Ручной инструмент', 'wrench'),
    ('Автотовары', 'car'),
    ('Всё для сада', 'sprout'),
    ('Крепёж и фурнитура', 'nut'),
    ('Отделочные и стройматериалы', 'bricks'),
    ('Офис и дом', 'house'),
    ('Спорт и туризм', 'backpack'),
    ('Станки и промкомпоненты', 'gear'),
    ('Климат, отопление и вентиляция', 'radiator'),
    ('Склад', 'shelves'),
    ('Клининг и химия', 'spray'),
    ('Строительное оборудование', 'crane'),
    ('Расходка, спецодежда и СИЗ', 'helmet'),
]
# ключ значка темы -> (3D / плоский — Microsoft Fluent Emoji, MIT; Phosphor, MIT)
ICONS = {
    'pipe': ('shower', 'shower', 'shower'),
    'toolbox': ('toolbox', 'toolbox', 'toolbox'),
    'box': ('package', 'package', 'package'),
    'bulb': ('light_bulb', 'light_bulb', 'lightbulb'),
    'wrench': ('hammer_and_wrench', 'hammer_and_wrench', 'wrench'),
    'car': ('automobile', 'automobile', 'car'),
    'sprout': ('potted_plant', 'potted_plant', 'plant'),
    'nut': ('nut_and_bolt', 'nut_and_bolt', 'nut'),
    'bricks': ('brick', 'brick', 'wall'),
    'house': ('couch_and_lamp', 'couch_and_lamp', 'armchair'),
    'backpack': ('camping', 'camping', 'tent'),
    'gear': ('gear', 'gear', 'gear-six'),
    'radiator': ('thermometer', 'thermometer', 'thermometer'),
    'shelves': ('card_file_box', 'card_file_box', 'warehouse'),
    'spray': ('sponge', 'sponge', 'spray-bottle'),
    'crane': ('building_construction', 'building_construction', 'crane-tower'),
    'helmet': ('safety_vest', 'safety_vest', 'hard-hat'),
    'sale': ('label', 'label', 'percent'),
}
# Вторая «Сантехника» в 1С — свой раздел, свой значок, чтобы два соседних
# квадрата не выглядели ошибкой.
ICON_OVERRIDE = {'Сантехника и инженерные системы': ('bathtub', 'bathtub', 'bathtub')}

# Главные разделы для крупных плиток варианта 1 — по слову в названии,
# в теме выбор делается так же, по списку слов.
FEATURED = ['тделоч', 'Инструменты', 'лектрик', 'Сантехника и', 'репёж', 'сад', 'лимат', 'пецодежд']

PASTELS = ['#e9eeff', '#ffeceb', '#fff3d6', '#e2f6ea', '#efe9ff', '#ffeadb', '#dff4f6', '#fde7f1']

STORES = [
    dict(city='Петропавловск-Камчатский', addr='ул. Чубарова, 16, корп. 40',
         phones=[('8-963-831-99-99', '+79638319999'), ('8 (4152) 31-99-99', '+74152319999')],
         wd='09:00-19:00', we='10:00-18:00', hours=('Пн–Пт 9:00–19:00', 'Сб–Вс 10:00–18:00'),
         route='https://yandex.ru/maps/?rtext=~%D0%9F%D0%B5%D1%82%D1%80%D0%BE%D0%BF%D0%B0%D0%B2%D0%BB%D0%BE%D0%B2%D1%81%D0%BA-%D0%9A%D0%B0%D0%BC%D1%87%D0%B0%D1%82%D1%81%D0%BA%D0%B8%D0%B9%2C%20%D1%83%D0%BB.%20%D0%A7%D1%83%D0%B1%D0%B0%D1%80%D0%BE%D0%B2%D0%B0%2C%2016%2C%20%D0%BA%D0%BE%D1%80%D0%BF.%2040&rtt=auto'),
    dict(city='Петропавловск-Камчатский', addr='просп. 50 лет Октября, 17А',
         phones=[('8-963-830-09-99', '+79638300999'), ('8 (4152) 400-999', '+74152400999')],
         wd='09:00-19:00', we='09:00-18:00', hours=('Пн–Пт 9:00–19:00', 'Сб–Вс 9:00–18:00'),
         route='https://yandex.ru/maps/?rtext=~%D0%9F%D0%B5%D1%82%D1%80%D0%BE%D0%BF%D0%B0%D0%B2%D0%BB%D0%BE%D0%B2%D1%81%D0%BA-%D0%9A%D0%B0%D0%BC%D1%87%D0%B0%D1%82%D1%81%D0%BA%D0%B8%D0%B9%2C%20%D0%BF%D1%80%D0%BE%D1%81%D0%BF.%2050%20%D0%BB%D0%B5%D1%82%20%D0%9E%D0%BA%D1%82%D1%8F%D0%B1%D1%80%D1%8F%2C%2017%D0%90&rtt=auto'),
    dict(city='Елизово', addr='Магистральная ул., 2/2',
         phones=[('8-963-830-03-33', '+79638300333'), ('8 (4152) 400-333', '+74152400333')],
         wd='09:00-19:00', we='09:00-18:00', hours=('Пн–Пт 9:00–19:00', 'Сб–Вс 9:00–18:00'),
         route='https://yandex.ru/maps/?rtext=~%D0%95%D0%BB%D0%B8%D0%B7%D0%BE%D0%B2%D0%BE%2C%20%D0%9C%D0%B0%D0%B3%D0%B8%D1%81%D1%82%D1%80%D0%B0%D0%BB%D1%8C%D0%BD%D0%B0%D1%8F%20%D1%83%D0%BB.%2C%202/2&rtt=auto'),
]

CALCS = ['Гипсокартон', 'Перегородка', 'Плитка', 'Обои', 'Краска и грунтовка', 'Ламинат',
         'Сухие смеси', 'Кирпич и блоки', 'Бетон', 'Утеплитель', 'Кровля', 'Потолок «Армстронг»',
         'Панели и вагонка', 'Радиаторы']

e = html.escape


def ph(name, size=24, cls=''):
    """Значок Phosphor (вариант 2) прямо в разметке — цвет берёт из currentColor."""
    with open(os.path.join(HERE, 'src', 'ph', name + '.svg'), encoding='utf-8') as f:
        svg = f.read().strip()
    attrs = f'width="{size}" height="{size}" aria-hidden="true" focusable="false"' + (f' class="{cls}"' if cls else '')
    return svg.replace('<svg ', '<svg ' + attrs + ' ', 1)


def icon_of(name, kind):
    i = {'3d': 0, 'flat': 1, 'ph': 2}[kind]
    if name in ICON_OVERRIDE:
        return ICON_OVERRIDE[name][i]
    return ICONS[dict(CATS)[name]][i]


def cats_v1():
    """Крупные плитки с объёмными значками для восьми главных разделов
    и ряд остальных — в пилюлях с маленьким значком."""
    names = [n for n, _ in CATS]
    featured = []
    for word in FEATURED:
        for n in names:
            if word in n and n not in featured:
                featured.append(n)
                break
    rest = [n for n in names if n not in featured]
    tiles = []
    for i, n in enumerate(featured):
        tiles.append(
            f'<a class="v1-tile reveal" href="../catalog.html" style="--tile:{PASTELS[i % len(PASTELS)]}">'
            f'<span class="v1-tile__title">{e(n)}</span>'
            f'<img class="v1-tile__img" src="img/3d/{icon_of(n, "3d")}.webp" alt="" width="160" height="160" loading="lazy">'
            '</a>')
    chips = ''.join(
        f'<a class="v1-chip" href="../catalog.html"><img src="img/3d/{icon_of(n, "3d")}.webp" alt="" width="28" height="28" loading="lazy">{e(n)}</a>'
        for n in rest)
    chips += ('<a class="v1-chip v1-chip--sale" href="../catalog.html">'
              '<img src="img/3d/label.webp" alt="" width="28" height="28" loading="lazy">Товары со скидкой</a>')
    return (f'<div class="v1-tiles">{"".join(tiles)}</div>'
            f'<div class="v1-more"><span class="v1-more__label">Ещё разделы</span>{chips}</div>')


def cats_v2():
    cards = ''.join(
        f'<a class="v2-cat reveal" href="../catalog.html"><span class="v2-cat__badge">{ph(icon_of(n, "ph"), 28)}</span>'
        f'<span class="v2-cat__title">{e(n)}</span></a>'
        for n, _ in CATS)
    cards += (f'<a class="v2-cat v2-cat--sale reveal" href="../catalog.html"><span class="v2-cat__badge">{ph("percent", 28)}</span>'
              '<span class="v2-cat__title">Товары со скидкой</span></a>'
              f'<a class="v2-cat v2-cat--all reveal" href="../catalog.html"><span class="v2-cat__badge">{ph("toolbox", 28)}</span>'
              '<span class="v2-cat__title">Весь каталог →</span></a>')
    return f'<div class="v2-cats">{cards}</div>'


def cats_v3():
    cards = ''.join(
        f'<a class="v3-cat reveal" href="../catalog.html" style="--dot:{PASTELS[i % len(PASTELS)]}">'
        f'<span class="v3-cat__icon"><img src="img/flat/{icon_of(n, "flat")}.svg" alt="" width="48" height="48" loading="lazy"></span>'
        f'<span class="v3-cat__title">{e(n)}</span></a>'
        for i, (n, _) in enumerate(CATS))
    cards += ('<a class="v3-cat v3-cat--sale reveal" href="../catalog.html" style="--dot:#ffe1e3">'
              '<span class="v3-cat__icon"><img src="img/flat/label.svg" alt="" width="48" height="48" loading="lazy"></span>'
              '<span class="v3-cat__title">Товары со скидкой</span></a>'
              '<a class="v3-cat v3-cat--all reveal" href="../catalog.html" style="--dot:#ffffff">'
              '<span class="v3-cat__icon"><img src="img/flat/package.svg" alt="" width="48" height="48" loading="lazy"></span>'
              '<span class="v3-cat__title">Весь каталог →</span></a>')
    return f'<div class="v3-cats">{cards}</div>'


def products(title, link='Смотреть все', badges=('', 'Хит', '', 'Скидка', '')):
    """Подборка как в макете: на живом сайте её рисует модуль OpenCart
    с настоящими товарами, здесь — пустые места вместо выдуманных."""
    cards = []
    for b in badges:
        badge = ''
        if b:
            kind = 'sale' if b == 'Скидка' else 'hit'
            badge = f'<span class="vp-card__badge vp-card__badge--{kind}">{b}</span>'
        cards.append(
            '<article class="vp-card">'
            f'<a class="vp-card__media" href="../product.html">{badge}<span class="vp-card__ph">фото товара</span></a>'
            '<div class="vp-card__body"><a class="vp-card__title" href="../product.html">Название товара из каталога</a>'
            '<p class="vp-card__meta">артикул · в наличии</p></div>'
            '<div class="vp-card__bottom"><span class="vp-card__price">цена, ₽</span>'
            '<button class="vp-card__buy" type="button" data-add="cart">В корзину</button></div>'
            '</article>')
    return (f'<section class="vp"><div class="container"><div class="vp__head"><h2 class="vp__title">{e(title)}</h2>'
            f'<a class="vp__link" href="../catalog.html">{e(link)}</a></div>'
            f'<div class="vp__row">{"".join(cards)}</div></div></section>')


def store_rows(s, cls):
    phones = ''.join(f'<a href="tel:{t}">{e(p)}</a>' for p, t in s['phones'])
    return (f'<p class="{cls}__row {cls}__phones">{phones}</p>'
            f'<p class="{cls}__row {cls}__hours" data-hours-weekday="{s["wd"]}" data-hours-weekend="{s["we"]}">'
            f'<span>{e(s["hours"][0])}</span><span>{e(s["hours"][1])}</span>'
            '<span class="shop-card__now" data-hours-now hidden></span></p>')


def stores_v1():
    cards = ''.join(
        '<article class="v1-shop reveal">'
        '<img class="v1-shop__pin" src="img/3d/round_pushpin.webp" alt="" width="64" height="64" loading="lazy">'
        f'<p class="v1-shop__city">{e(s["city"])}</p><h3 class="v1-shop__addr">{e(s["addr"])}</h3>'
        + store_rows(s, 'v1-shop') +
        f'<a class="v1-shop__route" href="{e(s["route"])}" target="_blank" rel="noopener">Построить маршрут</a>'
        '</article>'
        for s in STORES)
    return f'<div class="v1-shops">{cards}</div>'


def stores_v2():
    cards = ''.join(
        '<article class="v2-shop reveal">'
        f'<span class="v2-shop__num">0{i + 1}</span>'
        f'<p class="v2-shop__city">{e(s["city"])}</p><h3 class="v2-shop__addr">{e(s["addr"])}</h3>'
        + store_rows(s, 'v2-shop') +
        f'<a class="v2-shop__route" href="{e(s["route"])}" target="_blank" rel="noopener">{ph("map-pin", 18)} Маршрут</a>'
        '</article>'
        for i, s in enumerate(STORES))
    return f'<div class="v2-shops">{cards}</div>'


def stores_v3():
    rows = ''.join(
        '<article class="v3-shop reveal">'
        f'<span class="v3-shop__pin">{i + 1}</span>'
        f'<div><p class="v3-shop__city">{e(s["city"])}</p><h3 class="v3-shop__addr">{e(s["addr"])}</h3>'
        + store_rows(s, 'v3-shop') +
        f'<a class="v3-shop__route" href="{e(s["route"])}" target="_blank" rel="noopener">Как доехать →</a></div>'
        '</article>'
        for i, s in enumerate(STORES))
    return f'<div class="v3-shops"><div class="v3-map">{svg("map")}</div><div class="v3-shops__list">{rows}</div></div>'


def calc_chips(cls, n=None):
    names = CALCS if n is None else CALCS[:n]
    return ''.join(f'<a class="{cls}" href="../calculator.html">{e(c)}</a>' for c in names)


def svg(name):
    with open(os.path.join(HERE, 'src', name + '.svg'), encoding='utf-8') as f:
        return f.read().strip()


BLOCKS = {
    'cats-v1': cats_v1, 'cats-v2': cats_v2, 'cats-v3': cats_v3,
    'stores-v1': stores_v1, 'stores-v2': stores_v2, 'stores-v3': stores_v3,
    'volcano': lambda: svg('volcano'),
}


def expand(text):
    def repl(m):
        key = m.group(1).strip()
        if key in BLOCKS:
            return BLOCKS[key]()
        if key.startswith('ph '):
            parts = key.split()
            return ph(parts[1], int(parts[2]) if len(parts) > 2 else 24)
        if key.startswith('products '):
            return products(key[len('products '):])
        if key.startswith('calcs '):
            parts = key.split()
            return calc_chips(parts[1], int(parts[2]) if len(parts) > 2 else None)
        raise KeyError(key)
    return re.sub(r'\{\{(.+?)\}\}', repl, text)


SHORT = 'а|в|и|к|о|с|у|я|во|до|за|из|на|не|ни|но|об|от|по|со|для|при|под|про|без'
NBSP = '\u00a0'


def typo(text):
    """Неразрывные пробелы, как в build.mjs для страниц макета: предлог
    не висит в конце строки, число не отрывается от единицы и тире —
    от слова перед ним. Только в тексте, атрибуты не трогаются."""
    def fix(chunk):
        for _ in range(2):
            chunk = re.sub(r'(^|[\s(«"' + NBSP + r'])(' + SHORT + r') +(?=\S)', r'\1\2' + NBSP, chunk, flags=re.I)
        chunk = re.sub(r'(\S) +—', r'\1' + NBSP + '—', chunk)
        chunk = re.sub(r'(\d) +(₽|%|м²|м|кг|л|шт\.)(?![\w])', r'\1' + NBSP + r'\2', chunk)
        return chunk
    parts = re.split(r'(<[^>]+>)', text)
    skip = False
    for i, part in enumerate(parts):
        if part.startswith('<'):
            low = part.lower()
            if low.startswith('<svg') or low.startswith('<style') or low.startswith('<script'):
                skip = True
            elif low.startswith('</svg') or low.startswith('</style') or low.startswith('</script'):
                skip = False
            continue
        if not skip:
            parts[i] = fix(part)
    return ''.join(parts)


def page(slug, cls, title, font):
    with open(os.path.join(SITE, 'index.html'), encoding='utf-8') as f:
        src = f.read()
    head, rest = src.split('<main id="main">', 1)
    _, tail = rest.split('</main>', 1)
    with open(os.path.join(HERE, 'src', f'main-{slug[0]}.html'), encoding='utf-8') as f:
        main = typo(expand(f.read()))
    out = head + '<main id="main">\n' + main + '\n</main>' + tail

    # Страница лежит во вложенной папке: адреса страниц и файлов макета — уровнем выше.
    pages = r'(?:index|catalog|product|cart|calculator|delivery|contacts|checkout|order-done|favourites|compare|login|policy|terms|404)\.html'
    out = re.sub(r'(href|src|action)="(?=assets/|' + pages + r')', r'\1="../', out)
    out = re.sub(r'(srcset="[^"]*)', lambda m: m.group(1).replace('assets/', '../assets/'), out)
    out = out.replace('<link rel="canonical" href="../index.html">', '<meta name="robots" content="noindex">')
    out = re.sub(r'<title>[^<]*</title>', f'<title>{e(title)} — главная Строй-Героя</title>', out, count=1)
    css = (f'<link rel="preload" href="fonts/{font}.woff2" as="font" type="font/woff2" crossorigin>\n'
           '<link rel="stylesheet" href="variants.css">\n')
    out = out.replace('</head>', css + '</head>', 1)
    out = out.replace('<body>', f'<body class="vv {cls}">', 1)
    with open(os.path.join(HERE, f'{slug}.html'), 'w', encoding='utf-8') as f:
        f.write(out)
    print('написан', f'{slug}.html')


if __name__ == '__main__':
    for v in VARIANTS:
        page(*v)
