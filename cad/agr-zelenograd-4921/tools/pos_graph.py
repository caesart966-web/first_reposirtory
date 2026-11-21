"""Календарный график производства работ для ПОС (лист 2 ГЧ) — картинка в стиле исходной таблицы Excel.

Строки и сроки (месяцы от начала строительства, включительно) — ROWS; месяцев — MONTHS. Картинка рисуется
в 3 раза крупнее исходной (1318 x 383 пкс) с теми же пропорциями: в PDF она встает на место старой.
Шрифт Carlito (метрики Calibri, как в исходной таблице).
"""
from PIL import Image, ImageDraw, ImageFont

K = 3
W, H = 1318 * K, 383 * K
C0, C1 = 58 * K, 418 * K                       # границы столбцов «№» и «Наименование»
HEAD = 60 * K
ROW = (383 - 60) * K / 16                      # 16 строк под шапкой
FONT = '/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf'
FONTB = '/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf'
YELLOW = (255, 255, 0)
MONTHS = 58
ROWS = [  # (номер, наименование, (первый месяц, последний)) ; номер None — заголовок периода
    (None, 'Подготовительный период', None),
    (1, 'Удаление деревьев', (1, 2)),
    (2, 'Обустройство стройплощадки', (3, 4)),
    (None, 'Основной период', None),
    (3, 'Разработка котлована', (5, 10)),
    (4, 'Устройство фундаментов', (11, 14)),
    (5, 'Установка несущего каркаса', (15, 16)),
    (6, 'Устройство перекрытий', (17, 18)),
    (7, 'Устройство ограждающих конструкций', (19, 21)),
    (8, 'Устройство кровли', (22, 24)),
    (9, 'Заполнение оконных и дверных проемов', (25, 26)),
    (10, 'Монтаж внутренних инженерных систем', (27, 29)),
    (11, 'Монтаж сетей инженерно-технического обеспечения', (30, 32)),
    (12, 'Отделка фасадов', (33, 36)),
    (13, 'Внутренняя отделка', (37, 55)),
    (14, 'Планировка и благоустройство на участке.', (40, 58)),
]


def roman(n):
    out = ''
    for v, s in ((50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')):
        while n >= v:
            out += s
            n -= v
    return out


def draw(rows=ROWS, months=MONTHS):
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 15 * K)
    fb = ImageFont.truetype(FONTB, 15 * K)
    fm = ImageFont.truetype(FONT, 13 * K)
    mw = (W - C1) / months
    xs = [C1 + i * mw for i in range(months + 1)]
    ys = [HEAD + i * ROW for i in range(len(rows) + 1)]
    for r, (num, name, span) in enumerate(rows):          # заливка
        if span:
            a, b = span
            d.rectangle([xs[a - 1], ys[r], xs[b], ys[r + 1]], fill=YELLOW)
    lw = 2
    for x in [0, C0, C1] + xs[1:]:                          # сетка
        d.line([(x, 0), (x, H)], fill='black', width=lw)
    for y in [0] + ys:
        d.line([(0, y), (W, y)], fill='black', width=lw)
    for r, (num, name, span) in enumerate(rows):            # заголовки периодов без линий внутри
        if num is None:
            d.rectangle([C1 + lw, ys[r] + lw, W - lw, ys[r + 1] - lw], fill='white')
            for x in xs[1:-1]:
                d.line([(x, ys[r]), (x, ys[r + 1])], fill='black', width=lw)

    def ctext(cx, cy, s, font):
        d.text((cx, cy), s, font=font, fill='black', anchor='mm')
    ctext(C0 / 2, HEAD / 2, '№ п.п.', fb)
    ctext((C0 + C1) / 2, HEAD / 2, 'Наименование работ', fb)
    for i in range(months):                                 # месяцы — римскими, повернуты
        s = roman(i + 1)
        tw = int(d.textlength(s, font=fm)) + 4 * K
        t = Image.new('RGBA', (tw, 16 * K), (255, 255, 255, 0))
        ImageDraw.Draw(t).text((tw / 2, 8 * K), s, font=fm, fill='black', anchor='mm')
        t = t.rotate(90, expand=True)
        cx = (xs[i] + xs[i + 1]) / 2
        im.paste(t, (int(cx - t.width / 2), int(HEAD / 2 - t.height / 2)), t)
    for r, (num, name, span) in enumerate(rows):
        cy = (ys[r] + ys[r + 1]) / 2
        if num is None:
            ctext((C0 + C1) / 2, cy, name, fb)
        else:
            ctext(C0 / 2, cy, str(num), f)
            d.text((C0 + 4 * K, cy), name, font=f, fill='black', anchor='lm')
    return im


if __name__ == '__main__':
    import sys
    draw().save(sys.argv[1] if len(sys.argv) > 1 else 'graph.png')
