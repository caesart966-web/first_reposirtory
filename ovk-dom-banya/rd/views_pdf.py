"""PDF с видами 3D-модели (снимки просмотрщика): python3 views_pdf.py ПАПКА_СНИМКОВ ВЫХОД.pdf"""
import io
import sys

import fitz
from PIL import Image, ImageChops

SRC, OUT = sys.argv[1:3]
WITH_BATH = '--bath' in sys.argv          # страницы «Баня» и «Дом и баня» — только для модели с баней
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
PAGES = [
    ('iso', 'Общий вид с юго-запада', 'Стены — по АР03 и АР09 (полупрозрачно), подписи — расходы у решёток, м³/ч.'),
    ('nowalls', 'Общий вид без стен', 'Сети П1 (приток — синий, вытяжка — оранжевый, наружный воздух — зелёный, выброс — '
                'серый), ВЗ, В2, кондиционирование (сиреневый), фреон (розовый).'),
    ('iso2', 'Вид с востока', 'Топочная с П1, шахты Ш-1 и Ш-2, стояки на 2 этаж.'),
    ('f1', '1 этаж', 'Подшивки П-1…П-5: К-1…К-3 с КСД и щелевыми диффузорами, магистрали П1, пересечения у Ш-1 '
           'разведены по высоте (лист 11).'),
    ('f2', '2 этаж', 'К-4…К-6: ЩП и ЩВ в подшивке над шкафами спален через КСД, воздуховоды 250×150 через стену; '
           'К-7 — решётки в стене 2.6/2.7; приток и вытяжка П1.'),
    ('topo', 'Топочная 1.6', 'П1 Turkov Zenit 750 Heco W, шумоглушители, клапан КВ-Н, наружный воздух от Н1, выброс в Ш-2.'),
    ('top', 'Вид сверху', 'Начало координат — пересечение осей 1/А.'),
    ('bath', 'Баня', 'ВВ-б1 (с/у б3) и ВВ-б2 (помывочная б7): решётка под потолком, канальный вентилятор Ø100, проход в '
             'наружной стене, ось +2,200 (лист 12). Стены — по АР4.'),
    ('site', 'Дом и баня', 'Баня — по ГП01: оси 1/А бани в 7,132 м восточнее и 25,000 м севернее осей 1/А дома.'),
]


def trim(path, pad=40):
    im = Image.open(path).convert('RGB')
    bg = Image.new('RGB', im.size, (255, 255, 255))
    box = ImageChops.difference(im, bg).getbbox()
    if box:
        x0, y0, x1, y1 = box
        im = im.crop((max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + pad), min(im.height, y1 + pad)))
    b = io.BytesIO()
    im.save(b, 'PNG')
    return b.getvalue(), im.size


doc = fitz.open()
MM = 72 / 25.4
W, H = 420 * MM, 297 * MM
for key, title, note in PAGES:
    if key in ('bath', 'site') and not WITH_BATH:
        continue
    png, (iw, ih) = trim(f'{SRC}/{key}.png')
    pg = doc.new_page(width=W, height=H)
    pg.insert_font(fontname='dj', fontfile=FONT)
    pg.insert_text((15 * MM, 16 * MM), f'И05.09.26-ОВ. Вентиляция и кондиционирование дома. 3D-модель — {title}',
                   fontname='dj', fontsize=13)
    pg.insert_text((15 * MM, 285 * MM), note, fontname='dj', fontsize=9, color=(0.3, 0.3, 0.3))
    pg.insert_text((15 * MM, 290.5 * MM), 'Модель по трассам листов 9–11; файлы И05.09.26-ОВ 3D (DWG, IFC, просмотр в '
                   'браузере). Дренаж конденсата — по листам 9, 10.', fontname='dj', fontsize=8, color=(0.45, 0.45, 0.45))
    area = fitz.Rect(15 * MM, 22 * MM, W - 15 * MM, 278 * MM)
    k = min(area.width / iw, area.height / ih)
    w, h = iw * k, ih * k
    r = fitz.Rect(area.x0 + (area.width - w) / 2, area.y0 + (area.height - h) / 2, 0, 0)
    r.x1, r.y1 = r.x0 + w, r.y0 + h
    pg.insert_image(r, stream=png)
doc.save(OUT, deflate=True, garbage=3)
print(OUT, len(doc), 'стр.')
