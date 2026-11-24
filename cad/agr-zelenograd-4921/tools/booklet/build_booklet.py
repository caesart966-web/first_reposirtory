"""Буклет АГР по официальному шаблону ДГП: «Производственное здание», г. Москва, Зеленоград,
Восточная коммунальная зона, пр. 4921 (корректировка САГР № 466-5-22/С).

    python3 build_booklet.py <img> <assets> <куда.pptx>

<img> — картинки из prep_images.py, sit_map.py, district_map.py, zoning_axo.py, render_persp.py;
<assets> — логотипы и обложка шаблона (те же, что у буклета Щелковского ш., 17А).
Каркас листа (шапка, плашки разделов, рамки, таблицы) — из build_booklet.py Щелковского ш., 17А:
геометрия снята с PDF шаблона ДГП. Числа — из сведенных ТЭП (fix_models.py, README).
"""
import importlib.util
import json
import os
import sys

from pptx.enum.dml import MSO_LINE_DASH_STYLE as DASH
from pptx.enum.shapes import MSO_SHAPE

HERE = os.path.dirname(os.path.abspath(__file__))
AGR1 = os.path.join(HERE, '..', '..', '..', 'agr-shchelkovskoe-17a', 'tools', 'booklet')
sys.path.insert(0, AGR1)
from pptkit import MONT, CG  # noqa: E402

_spec = importlib.util.spec_from_file_location('agr1_booklet', os.path.join(AGR1, 'build_booklet.py'))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

base.OBJ1 = 'Производственное здание'
base.OBJ2 = 'по адресу: г. Москва, Зеленоград, Восточная коммунальная зона, пр. 4921'
base.DIST = 'ЗелАО | Савёлки'
GREY_BAR, DARK, FRAME, PINK, CELL = base.GREY_BAR, base.DARK, base.FRAME, base.PINK, base.CELL
NB = ' '

# сведенные показатели (README, «Сведение ТЭП»)
TEP = dict(site_ha='0,3293', site_m2='3 293', build='1 226,90', total='1 470,50', spp='1 461,98', dens='4,44',
           pct='37,26', h='11,94', habs='207,96', zero='196,02', floors='2', cars='8')

RAL = {'7012': '#575D5E', '7042': '#8E9291', '7035': '#CBD0CC', '7038': '#B0B0A9', '7024': '#474A50'}

# ведомость отделки фасада авторов (позиции как на чертежах фасадов; 6 и 16 у авторов нет)
FACADE = [
    (1, 'Наружные стены — стеновая сэндвич-панель 150 мм', '7012'),
    (2, 'Наружные стены — стеновая сэндвич-панель 150 мм', '7042'),
    (3, 'Наружные стены — стеновая сэндвич-панель 150 мм', '7035'),
    (4, 'Фасонные элементы — металл', '7012'),
    (5, 'Фасонные элементы — металл', '7038'),
    (7, 'Промышленные ворота «АЛЮТЕХ» (или аналог) 3600×3700', '7012'),
    (8, 'Двери «АЛЮТЕХ» (или аналог) 900×2100', '7012'),
    (9, 'Двери остекленные «АЛЮТЕХ» (или аналог) 1600×2400', '7012'),
    (10, 'Двери «АЛЮТЕХ» (или аналог) 1300×2100', '7012'),
    (11, 'Цоколь — декоративная штукатурка', '7012'),
    (12, 'Пожарная лестница — металл', None),
    (13, 'Водосточная система «Металл Профиль» (или аналог)', '7024'),
    (14, 'Светильник светодиодный Feron (или аналог)', None),
    (15, 'Козырек «МГ-СтеклоПроект» (или аналог), стекло с тонировкой', 'glass'),
    (17, 'Светильник 7117/12WL NATURE ODL25 667 (или аналог)', None),
    (18, 'Прожектор светодиодный с камерой Smart OUTD WIFI Camera 830 (или аналог)', None),
]

ROOMS1 = [('1', 'Лестничная клетка', 20.53), ('2', 'Производственное помещение', 1129.86), ('3', 'Санузел', 1.39),
          ('4', 'КУИ', 1.82), ('5', 'Электрощитовая', 5.06), ('6', 'ИТП', 7.88), ('7', 'Кладовая', 4.96)]
ROOMS2 = [('8', 'Антресоль (административная зона)', 273.98), ('9', 'Лестничная клетка', 16.50)]


def f2(v):
    s = '{:,.2f}'.format(v).replace(',', NB).replace('.', ',')
    return s


class Book(base.Book):
    def __init__(self, img, assets, cache):
        super().__init__(img, img, assets, cache)

    # --- общие таблицы ------------------------------------------------------------------------------------------
    def table(self, sl, X, y, head, rows, size=8.5, hh=18, rh=16, bold_last=False, align=None):
        align = align or ['l'] * (len(X) - 1)
        sl.rect(X[0], y, X[-1], y + hh, fill=PINK, line='#FFFFFF', lw=1.0)
        for i, t in enumerate(head):
            pad = 4 if align[i] == 'l' else 0
            sl.text(X[i] + pad, y, X[i + 1] - X[i] - pad - 2, t, size=size, bold=True, align=align[i], h=hh,
                    anchor='m', y_is_glyph_top=False, spacing=0.95)
        y += hh
        for j, r in enumerate(rows):
            h = rh if not isinstance(r, tuple) or len(r) <= len(head) else r[-1]
            cells = r[:len(head)]
            last = bold_last and j == len(rows) - 1
            for i, t in enumerate(cells):
                sl.rect(X[i], y, X[i + 1], y + h, fill=PINK if last else CELL, line='#FFFFFF', lw=1.0)
                pad = 4 if align[i] == 'l' else 0
                sl.text(X[i] + pad, y, X[i + 1] - X[i] - pad - 2, t, size=size, bold=last, align=align[i], h=h,
                        anchor='m', y_is_glyph_top=False, spacing=0.95)
            y += h
        return y

    def legend_item(self, sl, x, y, kind, a=None, b=None, txt='', w=37.0, size=9.5, tx=None, h=None):
        if kind == 'line':
            sl.line(x, y + 6, x + w, y + 6, color=a, lw=b)
        elif kind == 'dash':
            sl.line(x, y + 6, x + w, y + 6, color=a, lw=b, dash=DASH.DASH)
        elif kind == 'dashdot':
            sl.line(x, y + 6, x + w, y + 6, color=a, lw=b, dash=DASH.DASH_DOT)
        elif kind == 'box':
            sl.rect(x, y, x + w, y + 12, fill=a, line=b, lw=0.6)
        elif kind == 'grid':
            sl.rect(x, y, x + w, y + 12, fill='#DCEFD6', line=FRAME, lw=0.5)
            for i in range(5):
                sl.rect(x + 2 + i * 7, y + 3, x + 7 + i * 7, y + 9, fill=None, line='#7FA77A', lw=0.4,
                        shape=MSO_SHAPE.HEXAGON)
        elif kind == 'dot':
            sl.rect(x + w / 2 - 5, y + 1, x + w / 2 + 5, y + 11, fill=a, line=b or '#555555', lw=0.5,
                    shape=MSO_SHAPE.OVAL)
        elif kind == 'arrow':
            sl.line(x, y + 6, x + w - 8, y + 6, color=a, lw=b or 1.6, dash=DASH.DASH if b and b > 1.6 else None)
            sl.tri(x + w - 5, y + 6, 7, a, rot=90)
        elif kind == 'darrow':                                  # штриховая со стрелками — движение транспорта
            sl.line(x, y + 6, x + w - 6, y + 6, color=a, lw=1.4, dash=DASH.DASH)
            sl.tri(x + w - 4, y + 6, 6, a, rot=90)
            sl.tri(x + 6, y + 6, 6, a, rot=90)
        elif kind == 'num':
            sl.rect(x + w / 2 - 7, y - 1, x + w / 2 + 7, y + 13, fill='#FFFFFF', line='#333333', lw=0.6,
                    shape=MSO_SHAPE.OVAL)
            sl.text(x + w / 2 - 7, y - 1, 14, a, size=7.5, align='c', h=14, anchor='m', y_is_glyph_top=False)
        sl.text(tx or x + w + 12, y + 0.5, 1145.2 - (tx or x + w + 12), txt, size=size, font=CG, h=h or 14,
                spacing=0.95)

    # --- 1. Титульный лист --------------------------------------------------------------------------------------
    def p_title(self):
        self.n += 1
        sl = self.d.slide()
        sl.image(os.path.join(self.assets, 'cover_art_clean.png'), 309.84, 124.8, 309.84 + 880.8, 124.8 + 717.12,
                 fmt='png', dpi=200)
        sl.image(os.path.join(self.assets, 'logos_big.png'), 43.68, 78.48, 43.68 + 803.28, 78.48 + 88.32, fmt='png')
        sl.text(45.3, 375.0, 760, 'Производственное здание', size=33, bold=True, h=50, spacing=1.0)
        sl.text(45.3, 472.8, 600, 'по адресу:', size=18, bold=True, color=0.0784)
        sl.text(45.3, 494.4, 760, ['г. Москва, Зеленоград, Восточная коммунальная зона, пр. 4921',
                                   'Зеленоградский административный округ, район Савёлки'], size=18,
                color=0.0784, h=50, spacing=1.0)
        red = (0.824, 0.137, 0.165)
        sl.text(45.3, 741.2, 400, 'Представление:', size=14.1, bold=True, font=CG, color=red)
        sl.text(45.3, 758.1, 20, '-', size=14, font=CG, color=red)
        sl.text(73.3, 758.1, 1000, 'проектных материалов АГР с низкополигональной и высокополигональной '
                                   'трехмерными цифровыми моделями', size=14, bold=True, font=CG, color=red)

    # --- 2. Сведения об объекте ---------------------------------------------------------------------------------
    def p_info(self):
        sl = self.page()
        sl.text(44.2, 132.2, 330, 'Заказчик', size=13, bold=True, font=CG)

        def row(y0, y1, label, value, x0=44.2, xm=143.4, x1=379.0, vsize=11, vfont=CG, vbold=False, unit=None,
                xu=285.8, lsize=11):
            sl.rect(x0, y0, xm, y1, fill=PINK, line='#FFFFFF', lw=1.0)
            sl.rect(xm, y0, (xu if unit is not None else x1), y1, fill=CELL, line='#FFFFFF', lw=1.0)
            sl.text(x0 + 6.8, y0, xm - x0 - 9, label, size=lsize, bold=True, font=CG, h=y1 - y0, anchor='m',
                    y_is_glyph_top=False, spacing=0.95)
            xe = xu if unit is not None else x1
            sl.text(xm + 7.0, y0, xe - xm - 10, value, size=vsize, font=vfont, bold=vbold, h=y1 - y0, anchor='m',
                    y_is_glyph_top=False, spacing=0.95)
            if unit is not None:
                sl.rect(xu, y0, x1, y1, fill=CELL, line='#FFFFFF', lw=1.0)
                sl.text(xu + 6, y0, x1 - xu - 8, unit, size=11, font=CG, bold=True, h=y1 - y0, anchor='m',
                        y_is_glyph_top=False, spacing=0.95)

        row(149.6, 170.0, 'Инвестор:', 'ООО «ВОСТОЧНАЯ»')
        row(170.0, 190.4, 'Акционер:', '–')
        row(190.4, 224.0, 'Заявитель:', 'ООО «ВОСТОЧНАЯ»')
        row(224.0, 291.2, 'Проектная\nорганизация:', 'ООО «АТРИУМ АРХИТЕКТС»')
        row(291.2, 351.2, 'Авторский\nколлектив:', ['Елисеев' + NB + 'Н.' + NB + 'П. (руководитель)',
                                                   'Клименко' + NB + 'Д., Дергунов' + NB + 'Д.,',
                                                   'Исмагилов' + NB + 'Н., Малютина' + NB + 'Е.'], vsize=10)
        sl.text(44.2, 366.6, 330, 'Тип обращения', size=13, bold=True, font=CG)
        row(384.3, 417.9, 'Проектные\nматериалы:', ['АГР, НПМ, ВПМ — корректировка', 'САГР № 466-5-22/С от '
                                                                                 '21.07.2022'], vsize=10)
        row(417.9, 464.7, 'Количество\nвариантов:', '1 вариант')
        sl.text(42.6, 480.2, 330, 'Основание для разработки', size=13, bold=True, font=CG)
        row(498.3, 518.7, 'Решение ГЗК', '–', x0=42.5, xm=141.8, x1=377.3)
        row(518.7, 539.1, 'ППТ', '–', x0=42.5, xm=141.8, x1=377.3)
        row(539.1, 559.5, 'ГПЗУ', '№' + NB + 'РФ-77-4-52-3-77-2026-08834-0 от 12.08.2026', x0=42.5, xm=141.8,
            x1=377.3, vsize=9.3)
        row(559.5, 593.1, 'ПЗЗ', 'ПП Москвы от 28.03.2017 № 120-ПП', x0=42.5, xm=141.8, x1=377.3, vsize=10)
        sl.text(42.6, 610.4, 330, 'Укрупненные ТЭП:', size=13, bold=True, font=CG)
        row(628.5, 662.1, 'Площадь\nучастка', TEP['site_ha'], x0=42.5, xm=141.8, vfont=MONT, vbold=True, unit='га')
        row(662.1, 708.9, 'Плотность\nзастройки\n(от СПП в ГНС)', TEP['dens'], x0=42.5, xm=141.8, vfont=MONT,
            vbold=True, unit='тыс. кв. м / га', lsize=10.5)
        row(708.9, 742.5, 'СПП в ГНС\nВСЕГО:', TEP['spp'], x0=42.5, xm=141.8, vfont=MONT, vbold=True, unit='кв. м')
        row(742.5, 771.3, 'СПП в ГНС\nжилых объектов', '–', x0=42.5, xm=141.8, vfont=MONT, unit='кв. м', lsize=9.5)
        row(771.3, 800.1, 'СПП в ГНС\nнежилых объектов', TEP['spp'], x0=42.5, xm=141.8, vfont=MONT, unit='кв. м',
            lsize=9.5)
        sl.line(397.9, 149.6, 397.9, 804.9, color=0.498, lw=0.25)

        sl.text(425.4, 126.8, 360, 'Фрагмент схемы расположения в районе', size=13, bold=True)
        sl.text(793.6, 126.8, 360, 'Ситуационный план', size=13, bold=True)
        self.pic(sl, 'district.png', 424.6, 149.1, 776.2, 561.9, mode='cover')
        self.pic(sl, 'situ.png', 793.6, 149.1, 1145.2, 561.9, mode='cover')
        sl.text(424.6, 575.4, 340, 'Условные обозначения:', size=12, bold=True)
        sl.text(423.3, 590.9, 340, 'к схеме расположения в районе:', size=12, italic=True)
        sl.line(424.6, 610.1, 472.5, 610.1, color=(0.753, 0.0, 0.0), lw=4.0)
        sl.text(495.8, 605.6, 270, 'граница района Савёлки', size=10)
        sl.rect(436.0, 622.6, 461.0, 643.6, fill=None, line='#C00000', lw=1.0, shape=MSO_SHAPE.OVAL,
                dash=DASH.DASH)
        sl.rect(443.0, 628.6, 454.0, 637.6, fill=(1.0, 1.0, 0.0), line=(1.0, 0.0, 0.0), lw=1.0)
        sl.text(495.8, 628.6, 270, 'участок проектирования', size=10)
        sl.text(423.3, 660.6, 340, 'к ситуационному плану:', size=12, italic=True)
        sl.line(424.4, 681.2, 475.4, 681.2, color='#2F5597', lw=3.5)
        sl.text(491.1, 675.5, 270, 'граница участка по ГПЗУ', size=10)
        sl.rect(424.4, 695.4, 475.4, 709.6, fill='#F58220', line='#B45309', lw=0.5)
        sl.text(491.1, 697.3, 270, 'проектируемое здание', size=10)
        sl.rect(424.4, 715.2, 475.4, 729.4, fill=0.84, line=0.6, lw=0.5)
        sl.text(491.1, 717.2, 270, 'существующая застройка', size=10)
        sl.rect(768.0, 582.7, 1145.2, 783.9, fill=CELL, line=(0.0902, 0.173, 0.318), lw=1.0)
        sl.text(768.0, 611.5, 377.2, ['НЕ ЗАНИМАТЬ и НЕ УДАЛЯТЬ', 'ДАННУЮ ОБЛАСТЬ.', 'ИНФОРМАЦИЯ ЗАПОЛНЯЕТСЯ',
                                      'ДЕПАРТАМЕНТОМ', 'ГРАДОСТРОИТЕЛЬНОЙ ПОЛИТИКИ', '(ДГП)'],
                size=18, bold=True, color=(1.0, 0.0, 0.0), align='c', spacing=0.98, h=130)
        sl.line(44.2, 809.4, 380.7, 809.4, color=FRAME, lw=0.5)

    # --- 3. Фотофиксация ----------------------------------------------------------------------------------------
    def p_photos(self):
        sl = self.page()
        self.bar(sl, 'Фотофиксация существующего положения')
        self.pic(sl, 'photo1.jpg', 45.2, 163.0, 583.9, 497.8, focus=(0.5, 0.45))
        self.tag(sl, 45.0, 163.0, '1', 'Вид с проезда № 4921 с юго-запада')
        self.pic(sl, 'photo2.jpg', 606.5, 163.0, 1145.2, 497.8, focus=(0.5, 0.33))
        self.tag(sl, 606.3, 163.0, '2', 'Западный и южный фасады')
        self.pic(sl, 'mini_photo.png', 45.2, 515.0, 407.4, 783.9, mode='contain')
        sl.text(430.0, 520.0, 330, 'Схема мест фотофиксации', size=12, bold=True)
        sl.text(430.0, 545.0, 330, [
            [('1', {'bold': True}), ('  — проезд № 4921 у примыкания проезда южнее участка: южный фасад 1–9 '
                                     'и западный фасад Д–А', {})],
            [('2', {'bold': True}), ('  — у юго-западной границы участка: западный фасад Д–А с входами '
                                     'и южный фасад 1–9', {})]], size=10, spacing=1.15, space_after=6, h=100)
        sl.text(430.0, 650.0, 330, ['Здание возведено по утвержденному АГР (САГР № 466-5-22/С), на фото — '
                                    'завершающий этап работ.', 'Фотомонтаж выполнен с точки 1 (лист 4).'],
                size=10, color=0.3, h=60, spacing=1.15, space_after=4)

    # --- 4. Фотомонтаж -------------------------------------------------------------------------------------------
    def p_montage(self):
        sl = self.page()
        self.bar(sl, 'Фотофиксация существующего положения / фотомонтаж с того же ракурса (точка 1)')
        self.pic(sl, 'photo1_m.jpg', 45.2, 163.0, 583.9, 474.2)
        self.tag(sl, 45.0, 163.0, '1', 'Существующее положение')
        self.pic(sl, 'image1.jpg', 606.5, 163.0, 1145.2, 474.2)
        self.tag(sl, 606.3, 163.0, '1', 'Фотомонтаж проектного решения')
        self.pic(sl, 'mini_photo1.png', 45.2, 505.0, 258.1, 711.6, mode='contain')
        sl.text(285.0, 510.0, 560, [
            'Фотомонтаж выполнен по фотографии с точки 1: проектное решение фасадов вписано в существующее '
            'окружение с сохранением ракурса, перспективы и освещения снимка.',
            'Показаны отделка фасадов по ведомости (сэндвич-панели RAL 7012, 7042, 7035), остекление, ворота '
            'и двери, благоустройство участка — асфальтобетонное покрытие, газон и газон, укрепленный '
            'георешеткой.'], size=10, spacing=1.15, space_after=8, h=200)

    # --- 5. Функциональное зонирование ---------------------------------------------------------------------------
    def p_zoning(self):
        sl = self.page()
        self.bar(sl, 'Схема функционального зонирования объекта (аксонометрия)')
        self.pic(sl, 'axo.png', 45.2, 163.0, 887.3, 783.9, mode='contain')
        sl.text(903.4, 166.2, 240, 'Условные обозначения:', size=12, bold=True, font=CG)
        y = 192.0
        items = [('#9FD3E0', 'производственная зона (2)'), ('#F4C7A2', 'административная зона, антресоль (8)'),
                 ('#E7B7D2', 'санитарно-бытовые помещения (3, 4)'), ('#BDBDBD', 'технические помещения (5, 6)'),
                 ('#EFE3A6', 'лестничные клетки (1, 9)'), ('#C9B6DE', 'кладовая (7)')]
        for col, txt in items:
            sl.rect(903.7, y, 934.9, y + 15.7, fill=col, line=0.45, lw=0.4)
            sl.text(950.0, y + 2.0, 195, txt, size=10, font=CG, h=30, spacing=0.95)
            y += 30
        for col, txt in (('#D7262C', 'входы в здание'), ('#2F5597', 'ворота: погрузка и выгрузка'),
                         ('#7A7A7A', 'запасный выход')):
            sl.line(904.0, y + 8, 926.0, y + 8, color=col, lw=2.2)
            sl.tri(929.0, y + 8, 9, col, rot=90)
            sl.text(950.0, y + 2.0, 195, txt, size=10, font=CG, h=20)
            y += 26
        y += 14
        sl.text(903.4, y, 242, 'Номера — по экспликации помещений (листы 14, 15).', size=9, color=0.3, h=30,
                spacing=1.05)
        y += 40
        sl.text(903.4, y, 242, ['Производственная зона на всю высоту здания; над осями 1–3 — антресоль '
                                'на отметке +4,090 с административной зоной.',
                                '±0,000 = абс. ' + TEP['zero'] + '.'], size=9.5, spacing=1.12, space_after=5,
                h=120)

    # --- 6–8. Перспективы ---------------------------------------------------------------------------------------
    def p_persp1(self):
        sl = self.page()
        self.bar(sl, 'Перспективное изображение №1')
        self.pic(sl, 'image5.jpg', 45.2, 163.0, 1145.2, 783.9, focus=(0.5, 0.5))
        self.tag(sl, 45.0, 163.0, '1', 'Вид с северо-запада: западный фасад с входами и северный фасад с воротами')

    def p_persp2(self):
        sl = self.page()
        self.bar(sl, 'Перспективное изображение №2')
        self.pic(sl, 'image6.jpg', 45.2, 163.0, 1145.2, 783.9, focus=(0.5, 0.5))
        self.tag(sl, 45.0, 163.0, '2', 'Вид с севера: северный фасад (9–1) с воротами')

    def p_persp34(self):
        sl = self.page()
        self.bar(sl, 'Перспективное изображение №3', x1=583.8, y0=123.2, y1=147.5)
        self.bar(sl, 'Перспективное изображение №4', x0=603.4, y0=123.4, y1=147.6)
        self.pic(sl, 'persp3.jpg', 45.8, 162.4, 583.9, 535.6, focus=(0.5, 0.5))
        self.tag(sl, 45.6, 162.4, '3', 'Вид сверху с юго-востока')
        self.pic(sl, 'persp4.jpg', 603.5, 162.4, 1144.8, 535.6, focus=(0.5, 0.5))
        self.tag(sl, 603.3, 162.4, '4', 'Вид сверху с юго-запада')
        sl.text(45.2, 560.0, 212, 'Точки обзора', size=9, bold=True)
        self.pic(sl, 'mini_views.png', 45.2, 577.3, 258.1, 783.9, mode='contain')
        sl.text(285.0, 580.0, 560, [
            'Изображения №3–№5 (№5 — лист 10) — виды высокополигональных цифровых моделей здания и благоустройства, '
            'переданных в составе материалов (ВПМ), с тем же расположением, отделкой и элементами '
            'благоустройства.',
            [('№3', {'bold': True}), (' — южный и восточный фасады, проезд вдоль южной границы участка;', {})],
            [('№4', {'bold': True}), (' — западный фасад с входами и козырьками, южный фасад, газон вдоль '
                                      'проезда № 4921.', {})]], size=10, spacing=1.15, space_after=8,
            h=200)

    # --- 9. Благоустройство --------------------------------------------------------------------------------------
    def p_blago(self):
        sl = self.page()
        self.bar(sl, 'Схема благоустройства земельного участка')
        self.pic(sl, 'spozu_plan.png', 45.2, 163.0, 861.8, 783.9, mode='contain')
        sl.text(887.3, 164.3, 250, 'Условные обозначения:', size=12, bold=True)
        x, y = 887.2, 190.0
        it = [('dashdot', '#1F3FBF', 1.6, 'граница участка 77:10:0005004:1443'),
              ('line', '#F2B36B', 1.2, 'граница благоустройства за границей участка'),
              ('box', '#FFFFFF', '#7A7A7A', 'бордюр'),
              ('box', '#E07A7A', '#7A1F1F', 'проектируемое здание'),
              ('box', '#9C9C9C', '#6E6E6E', 'асфальтобетонное покрытие'),
              ('grid', None, None, 'газон, укрепленный георешеткой'),
              ('box', '#DCEFD6', '#8DB287', 'газон'),
              ('dot', '#2F7FD8', '#1D4F86', 'опора наружного освещения h = 3–4,5 м'),
              ('dot', '#F3D9F2', '#8E5A8C', 'ландшафтный светильник'),
              ('dot', '#5B2A8E', '#3A1A5C', 'напольный наружный светильник'),
              ('dot', '#EEF5DF', '#7A8A6A', 'столб камеры видеонаблюдения h = 4 м'),
              ('num', '1', None, 'проектируемое здание'),
              ('num', '2', None, 'стоянка временного пребывания автомобилей, 8 м/м'),
              ('num', '3', None, 'площадка ТБО')]
        for kind, a, b, t in it:
            hh = 30 if len(t) > 30 else 22
            self.legend_item(sl, x, y, kind, a, b, t, h=hh)
            y += hh
        y += 10
        sl.text(887.3, y, 258, 'Условные обозначения и номера — как на СПОЗУ (лист 18).', size=8.5, color=0.35,
                h=30, spacing=1.05)

    # --- 10. Материалы благоустройства и МАФ -------------------------------------------------------------------
    def p_materials(self):
        sl = self.page()
        self.bar(sl, 'Материалы благоустройства. Сведения о МАФ и элементах благоустройства', size=12, y1=145.1)
        self.pic(sl, 'persp5.jpg', 45.2, 163.0, 735.0, 565.5, focus=(0.5, 0.6))
        self.tag(sl, 45.0, 163.0, '5', 'Парковка и площадка ТБО. Вид модели с северо-востока')
        x0, y = 45.2, 584.0
        sl.text(x0, y, 600, 'Ведомость покрытий', size=12, bold=True)
        y += 22
        rows = [('1', 'Площадь участка 77:10:0005004:1443', '3' + NB + '293'),
                ('2', 'Площадь твердых покрытий', '2' + NB + '052,24'),
                ('3', 'Асфальтобетонное покрытие', '1' + NB + '443,9'),
                ('4', 'Газон', '242,8'),
                ('5', 'Газон, укрепленный георешеткой', '394,4')]
        X = [x0, x0 + 30, x0 + 470, x0 + 580, 735.0]
        sl.rect(X[0], y, X[4], y + 18, fill=PINK, line='#FFFFFF', lw=1.0)
        for (xa, xb), t, al in zip(zip(X, X[1:]), ('№', 'Наименование', 'Площадь, м²', 'Обозначение'),
                                   ('c', 'l', 'c', 'c')):
            sl.text(xa + (4 if al == 'l' else 0), y, xb - xa - 4, t, size=8.5, bold=True, align=al, h=18,
                    anchor='m', y_is_glyph_top=False)
        y += 18
        sw = {'3': ('box', '#9C9C9C', '#6E6E6E'), '4': ('box', '#DCEFD6', '#8DB287'), '5': ('grid', None, None)}
        for n_, name, v in rows:
            for xa, xb in zip(X, X[1:]):
                sl.rect(xa, y, xb, y + 18, fill=CELL, line='#FFFFFF', lw=1.0)
            sl.text(X[0], y, X[1] - X[0], n_, size=9, align='c', h=18, anchor='m', y_is_glyph_top=False)
            sl.text(X[1] + 4, y, X[2] - X[1] - 6, name, size=9, h=18, anchor='m', y_is_glyph_top=False)
            sl.text(X[2], y, X[3] - X[2], v, size=9, align='c', h=18, anchor='m', y_is_glyph_top=False)
            if n_ in sw:
                k, a, b = sw[n_]
                xx = X[3] + (X[4] - X[3] - 37) / 2
                if k == 'grid':
                    self.legend_item(sl, xx, y + 3, 'grid', txt='', w=37)
                else:
                    sl.rect(xx, y + 3, xx + 37, y + 15, fill=a, line=b, lw=0.6)
            y += 18
        sl.text(x0, y + 5, 690, 'Покрытия и озеленение частично выходят за границу участка (благоустройство '
                                'прилегающей территории).', size=8.5, color=0.35, h=14)
        x0 = 760.0
        sl.text(x0, 164.3, 385, 'Малые архитектурные формы и переносные изделия', size=12, bold=True)
        y = 192.0
        maf = [('1', 'Контейнерная площадка', '«РОСТАЙП» (или аналог)', '1', 'maf_1.png'),
               ('2', 'Фонарь уличный, высота 3,50 м', '«Светлый город» (или аналог)', '2', 'maf_2.png'),
               ('3', 'Ландшафтный светильник', 'Denkris Nord DK9749-BK (или аналог)', '12', 'maf_3.png'),
               ('4', 'Напольный наружный светильник', 'LTD-GROUND R65-6W Warm3000 (или аналог)', '4', 'maf_4.png'),
               ('5', 'Столб для камеры видеонаблюдения', '«ИНТЕМС» (или аналог)', '4', 'maf_5.png')]
        for num, name, mk, q, im in maf:
            sl.rect(x0, y, x0 + 16.9, y + 19.4, fill=0.149)
            sl.text(x0, y, 16.9, num, size=10, bold=True, color=1.0, align='c', h=19.4, anchor='m',
                    y_is_glyph_top=False)
            self.pic(sl, im, x0 + 28, y, x0 + 118, y + 62, mode='contain', frame=False)
            sl.text(x0 + 130, y + 2, 255, [[(name, {'bold': True})], mk, 'Количество: ' + q + NB + 'шт.'],
                    size=9.5, h=70, spacing=1.08, space_after=3)
            y += 84

    # --- 11. АХО -------------------------------------------------------------------------------------------------
    def p_light(self):
        sl = self.page()
        self.bar(sl, 'Архитектурно-художественное освещение фасадов здания', size=12, y1=145.1)
        self.pic(sl, 'image9.jpg', 45.2, 163.0, 861.8, 783.9, mode='contain')
        sl.text(887.3, 164.3, 258, 'Светильники на фасадах:', size=12, bold=True)
        y = 190.0
        fx = [('14', 'Ландшафтно-архитектурный светильник', 'Feron LL-899, RGBW, 28 Вт, IP65 (или аналог)',
               'fix_14.png'),
              ('17', 'Настенный светильник', '7117/12WL NATURE ODL25 667, черный, LED 12 Вт, 3000 К, IP65 '
                                            '(или аналог)', 'fix_17.png'),
              ('18', 'Прожектор светодиодный с камерой', 'Smart OUTD WIFI Camera 830 (или аналог)',
               'fix_18.png')]
        for num, name, mk, im in fx:
            sl.rect(887.2, y, 908.0, y + 19.4, fill=0.149)
            sl.text(887.2, y, 20.8, num, size=10, bold=True, color=1.0, align='c', h=19.4, anchor='m',
                    y_is_glyph_top=False)
            sl.text(914.0, y + 3.5, 231, name, size=9, bold=True, h=16)
            self.pic(sl, im, 887.2, y + 26, 967.2, y + 106, mode='contain', frame=False)
            sl.text(977.0, y + 30, 168, mk, size=8.8, h=70, spacing=1.05)
            y += 118
        sl.text(887.3, y + 4, 258, 'Принцип освещения', size=12, bold=True)
        sl.text(887.3, y + 26, 258, ['Светильники подчеркивают членение фасада и освещают входы и ворота. '
                                     'Территорию освещают уличные фонари, ландшафтные и напольные светильники '
                                     '(лист 10).', 'Номера позиций — по ведомости отделки фасадов.'],
                size=9.5, spacing=1.12, space_after=6, h=150)

    # --- 13–14. Фасады -----------------------------------------------------------------------------------------
    def ved(self, sl, y=166.0):
        sl.text(813.5, y, 330, 'Ведомость отделки фасадов', size=12, bold=True)
        y += 24
        for num, txt, ral in FACADE:
            sl.text(813.5, y + 1.0, 18, str(num), size=8.5, bold=True, align='r')
            if ral == 'glass':
                sl.rect(838.0, y, 862.0, y + 12.0, fill='#CFE3EC', line=0.45, lw=0.4)
                sl.line(842.0, y + 10.0, 852.0, y + 2.0, color='#8DB0BF', lw=0.6)
            elif ral:
                sl.rect(838.0, y, 862.0, y + 12.0, fill=RAL[ral], line=0.45, lw=0.4)
            run = [(txt, {})]
            if ral and ral != 'glass':
                run.append((', RAL' + NB + ral, {'bold': True}))
            sl.text(870.0, y + 1.0, 275, [run], size=8.3, h=28, spacing=0.95)
            y += 32.5
        sl.text(813.5, y + 4, 330, ['Номера позиций — как на схемах фасадов. Окна — профиль Rehau Blitz, '
                                    'стеклопакет 4М1-16-4М1, откосы — металл RAL 7012 (или аналог).'],
                size=8, color=0.3, spacing=1.05, h=36)

    def p_facades(self, pair):
        sl = self.page()
        if pair == 0:
            title, files = 'Схемы фасадов (на основе М 1:200). Фасады 1–9, 9–1', ('fac_1_9.png', 'fac_9_1.png')
        else:
            title, files = 'Схемы фасадов (на основе М 1:200). Фасады А–Д, Д–А', ('fac_a_d.png', 'fac_d_a.png')
        self.bar(sl, title)
        self.frame(sl, 45.2, 163.7, 790.6, 783.5, color=0.498)
        sl.text(60.0, 172.0, 720, '±0,000 = абс. ' + TEP['zero'] + '; парапет +10,940 (абс. 206,96); верх '
                                  'пожарной лестницы +11,940 (абс. ' + TEP['habs'] + ')', size=9, color=0.3, h=14)
        slots = [(192.0, 480.0), (490.0, 778.0)]
        for (y0, y1), fl in zip(slots, files):
            self.pic(sl, fl, 55.0, y0, 780.8, y1, mode='contain', frame=False, fmt='png')
        self.ved(sl)

    # --- 15–16. Планы ------------------------------------------------------------------------------------------
    def expl(self, sl, rooms, y, title, total_label):
        sl.text(813.5, y, 330, title, size=12, bold=True)
        y += 22
        rows = [(n, nm, f2(a)) for n, nm, a in rooms]
        rows.append(('', total_label, f2(sum(a for _, _, a in rooms))))
        return self.table(sl, [813.5, 838.0, 1068.0, 1145.2], y, ['№', 'Наименование', 'Площадь, м²'], rows,
                          bold_last=True, align=['c', 'l', 'c'])

    def p_plan(self, fl):
        sl = self.page()
        if fl == 1:
            self.bar(sl, 'Схема плана 1 этажа (на основе М 1:200)')
            self.pic(sl, 'image11.png', 45.2, 163.0, 790.6, 783.5, mode='contain')
            y = self.expl(sl, ROOMS1, 166.0, 'Экспликация помещений 1 этажа', 'Итого 1 этаж')
            y += 20
            sl.text(813.5, y, 332, ['Производственное помещение — на всю высоту здания (второй свет над '
                                    'осями 3–9).', 'Вход для персонала и главная лестница — в осях 1–2 / А–Б, '
                                    'ворота — на фасаде 9–1.'], size=9, spacing=1.12, space_after=5, h=100,
                    color=0.25)
        else:
            self.bar(sl, 'Схема плана антресоли (2 этаж, на основе М 1:200)')
            self.pic(sl, 'image12.png', 45.2, 163.0, 790.6, 783.5, mode='contain')
            y = self.expl(sl, ROOMS2, 166.0, 'Экспликация помещений антресоли', 'Итого антресоль')
            y += 20
            sl.text(813.5, y, 332, [[('Итого по зданию: ', {'bold': True}),
                                     (f2(sum(a for *_, a in ROOMS1 + ROOMS2)) + ' м² — площадь помещений; общая '
                                      'площадь здания ' + TEP['total'] + ' м².', {})],
                                    'Антресоль — на отметке +4,090 (абс. 200,11) в осях 1–3.'], size=9,
                    spacing=1.12, space_after=5, h=100, color=0.25)

    # --- 17. Разрезы -------------------------------------------------------------------------------------------
    def p_sections(self):
        sl = self.page()
        self.bar(sl, 'Схемы разрезов с указанием высотных отметок (на основе М 1:200)')
        self.pic(sl, 'image17.png', 45.2, 163.0, 790.6, 783.5, mode='contain')
        sl.text(813.5, 166.0, 330, 'Высотные отметки', size=12, bold=True)
        marks = [('±0,000', TEP['zero'], 'чистый пол 1 этажа'), ('+4,090', '200,11', 'пол антресоли'),
                 ('+10,660', '206,68', 'конек кровли'), ('+10,940', '206,96', 'верх парапета'),
                 ('+11,940', TEP['habs'], 'верх пожарной лестницы — наивысшая точка')]
        y = 190.0
        for rel, ab, txt in marks:
            sl.text(813.5, y, 60, rel, size=10, bold=True)
            sl.text(872.0, y, 60, ab, size=10)
            sl.text(930.0, y, 215, txt, size=10, color=0.25, h=28, spacing=0.95)
            y += 28 if len(txt) > 26 else 18
        sl.text(813.5, y + 4, 330, 'Слева — относительная отметка, справа — абсолютная, м.', size=8.5, color=0.35)
        y += 36
        sl.text(813.5, y, 330, 'Конструкции', size=12, bold=True)
        y += 22
        sl.text(813.5, y, 330, [
            'Каркас — колонны и стальные фермы покрытия, фундаменты столбчатые монолитные железобетонные.',
            'Наружные стены — трехслойные стеновые сэндвич-панели с минераловатным утеплителем 150 мм.',
            'Кровля двускатная, неэксплуатируемая.',
            'Антресоль — на отметке +4,090 над осями 1–3.'], size=9.5, spacing=1.1, space_after=5, h=220)

    # --- 18. ТЭП ------------------------------------------------------------------------------------------------
    def p_tep(self):
        sl = self.page()
        self.bar(sl, 'Технико-экономические показатели рассматриваемой территории и проектируемого объекта')
        X = [45.2, 84.3, 503.8, 583.8, 728.3, 1145.2]
        hdr_fill, sub_fill = (0.988, 0.894, 0.902), (0.949, 0.8, 0.8)
        red = (0.753, 0.0, 0.0)
        y = 151.6

        def ctext(xa, xb, ya, yb, t, size=12, bold=True, font=CG, align='c', color=0, runs=None):
            sl.text(xa + (6 if align == 'l' else 0), ya, xb - xa - (8 if align == 'l' else 0), runs or t, size=size,
                    bold=bold, font=font, align=align, h=yb - ya, anchor='m', y_is_glyph_top=False, color=color,
                    spacing=0.95)
        sl.rect(X[0], y, X[5], y + 45.3, fill=hdr_fill, line='#FFFFFF', lw=1.0)
        for i in range(1, 5):
            sl.line(X[i], y, X[i], y + 45.3, color=1.0, lw=1.0)
        sl.line(X[4], y + 22.6, X[5], y + 22.6, color=1.0, lw=1.0)
        ctext(X[0], X[1], y, y + 45.3, '№')
        ctext(X[1], X[2], y, y + 45.3, 'Наименование показателей')
        ctext(X[2], X[3], y, y + 45.3, 'Ед. изм.')
        ctext(X[3], X[4], y, y + 45.3, '', runs=[[('ГПЗУ', {}), ('4', {'sup': True, 'size': 8})]])
        ctext(X[4], X[5], y, y + 22.6, '', runs=[[('Намерение инвестора', {}), ('1', {'sup': True, 'size': 8})]])
        ctext(X[4], X[5], y + 22.6, y + 45.3, 'Вариант 1')
        y += 45.3
        info = [[('Кадастровый номер з/у: 77:10:0005004:1443', {})],
                [('Правообладатель земельного участка: ', {}), ('ООО «ВОСТОЧНАЯ»', {'bold': True})],
                [('Основные виды разрешенного использования земельного участка: ', {}),
                 ('тяжелая, легкая, пищевая, нефтехимическая, строительная промышленность, энергетика, связь и др. '
                  '(6.2–6.11 по ГПЗУ)', {'bold': True})]]
        for r in info:
            sl.rect(X[0], y, X[5], y + 15.7, fill=sub_fill, line='#FFFFFF', lw=1.0)
            sl.text(X[0] + 11.4, y, 1080, [r], size=9, font=CG, h=15.7, anchor='m', y_is_glyph_top=False)
            y += 15.7
        D = '–'
        T = TEP
        rows = [
            ('1', [('Площадь территории', {'bold': True}), (', в т.ч.:', {'bold': True}), ('2', {'sup': True})],
             'га', D, T['site_ha'], 'main'),
            ('', 'участок под жилую застройку', 'га', D, D, 'sub'),
            ('', 'участок под нежилую застройку', 'га', D, T['site_ha'], 'sub'),
            ('2', [('Предельная плотность застройки (от СПП в ГНС)', {'bold': True}), ('5', {'sup': True})],
             'тыс. м²/га', D, T['dens'], 'main'),
            ('3', [('СПП всего:', {'bold': True}), ('2', {'sup': True})], 'м²', D, T['spp'], 'main'),
            ('3.1', [('СПП жилых зданий', {'bold': True}), ('2', {'sup': True})], 'м²', D, D, 'main'),
            ('', 'Жилая часть', 'м²', D, D, 'sub'),
            ('', 'Нежилая часть', 'м²', D, D, 'sub'),
            ('3.2', [('СПП нежилых зданий', {'bold': True}), ('2', {'sup': True})], 'м²', D, T['spp'], 'main'),
            ('4', [('Общая площадь объекта', {'bold': True})], 'м²', '5' + NB + '140', T['total'], 'main'),
            ('', 'Наземная часть', 'м²', D, T['total'], 'sub'),
            ('', 'Подземная часть', 'м²', D, D, 'sub'),
            ('5', [('Нежилая наземная площадь (ННП) ВСЕГО', {'bold': True}), ('2', {'sup': True}),
                   ('\n(встроенно-пристроенная и отдельно стоящая нежилых зданий)', {})], 'м²', D, T['total'],
             'main2'),
            ('', 'ННП встроенно-пристроенная жилых зданий', 'м²', D, D, 'sub'),
            ('', 'ННП отдельно стоящих нежилых зданий', 'м²', D, T['total'], 'sub'),
            ('6', [('Наземная площадь (НП), всего:', {'bold': True}), ('2', {'sup': True})], 'м²', D, T['total'],
             'main'),
            ('6.1', [('НП жилых зданий', {'bold': True}), ('2', {'sup': True})], 'м²', D, D, 'main'),
            ('6.2', [('НП нежилых зданий', {'bold': True}), ('2', {'sup': True}),
                     ('\n(в т.ч. площади: производственное здание)', {})], 'м²', D, T['total'], 'main2'),
            ('', 'Площадь функции: производство (строительная промышленность, 6.6)', 'м²', D, T['total'], 'sub'),
            ('', 'Площадь функции: иная', 'м²', D, D, 'sub'),
            ('7', [('Общая площадь квартир', {'bold': True}), ('2', {'sup': True})], 'м²', D, D, 'main'),
            ('8', [('Площадь квартир', {'bold': True}), ('2', {'sup': True}),
                   (' (без летних помещений, балконов и террас)', {})], 'м²', D, D, 'main'),
            ('9', [('Количество квартир', {'bold': True}), ('2', {'sup': True})], 'шт.', D, D, 'main'),
            ('10', [('Количество машино-мест', {'bold': True}), ('2', {'sup': True})], 'шт.', D, T['cars'], 'main'),
            ('11', 'Высота', 'м', 'без ограничений', T['h'], 'sub_n'),
            ('12', 'Этажность', 'эт.', D, T['floors'], 'sub_n'),
            ('13', 'Количество подземных этажей', 'эт.', D, D, 'sub_n'),
            ('14', [('Площадь территории озеленения на участке(-ах) жилой застройки', {'bold': True}),
                    ('2', {'sup': True})], 'м²', D, D, 'main'),
            ('', 'Площадь детских площадок', 'м²', D, D, 'sub'),
            ('', 'Площадь площадок для отдыха взрослых', 'м²', D, D, 'sub'),
            ('15', 'Площадь спортивных площадок', 'м²', D, D, 'sub_n'),
            ('16', [('Свободное поле', {}), ('3', {'sup': True}), (': площадь застройки', {})], 'м²', D, T['build'],
             'sub_n'),
            ('', 'процент застройки', '%', '44', T['pct'], 'sub'),
            ('', 'максимальная абсолютная отметка', 'м', D, T['habs'], 'sub'),
        ]
        total_h = 741.8 - y
        units = {'main': 15.7, 'main2': 26.4, 'sub': 14.15, 'sub_n': 14.15}
        k = total_h / sum(units[r[5]] for r in rows)
        for num, name, unit, g, val, lvl in rows:
            h = units[lvl] * k
            main = lvl in ('main', 'main2')
            numfill = sub_fill if main else red
            body = 0.851 if main else CELL
            sl.rect(X[0], y, X[1], y + h, fill=numfill, line='#FFFFFF', lw=1.0)
            for i in range(1, 5):
                sl.rect(X[i], y, X[i + 1], y + h, fill=body, line='#FFFFFF', lw=1.0)
            if num:
                ctext(X[0], X[1], y, y + h, num, size=11, bold=True, color=0 if main else 1.0)
            runs = [[(name, {})]] if isinstance(name, str) else None
            if runs is None:
                parts = [[]]
                for t, st in name:
                    if t.startswith('\n'):
                        parts.append([])
                        t = t[1:]
                    parts[-1].append((t, st))
                runs = parts
            sl.text(X[1] + 5.4, y, X[2] - X[1] - 8, runs, size=11 if lvl != 'main2' else 10.5, font=CG, h=h,
                    anchor='m', y_is_glyph_top=False, spacing=0.92)
            ctext(X[2], X[3], y, y + h, unit, size=11, bold=False)
            ctext(X[3], X[4], y, y + h, g, size=11 if len(g) < 10 else 9.5, bold=False)
            ctext(X[4], X[5], y, y + h, val, size=11, bold=lvl in ('main', 'main2'))
            y += h
        notes = [
            ('1', 'вариант один; корректировка САГР № 466-5-22/С от 21.07.2022;'),
            ('2', 'сохраняемой и сносимой застройки на участке нет, строится одно нежилое здание;'),
            ('3', 'в свободное поле внесены площадь и процент застройки и максимальная абсолютная отметка объекта;'),
            ('4', 'ГПЗУ № РФ-77-4-52-3-77-2026-08834-0 от 12.08.2026; в отсутствие показателя проставлен знак «–»;'),
            ('5', 'предельная плотность застройки ГПЗУ не установлена; 4,44 = ' + T['spp'] + ' м² / ' + T['site_ha']
             + ' га.'),
        ]
        yy = 745.7
        for n_, t in notes:
            sl.text(52.5, yy, 1080, [[(n_, {'sup': True, 'bold': True}), (' – ' + t, {})]], size=10, font=CG)
            yy += 12.4

    # --- 19. СПОЗУ ----------------------------------------------------------------------------------------------
    def p_spozu(self):
        sl = self.page()
        self.bar(sl, 'Схема планировочной организации земельного участка, совмещенная со схемой транспортной '
                     'организации', size=13)
        self.pic(sl, 'spozu_plan.png', 45.2, 163.0, 861.8, 783.9, mode='contain')
        x, y = 887.2, 166.0
        sl.text(887.3, y, 250, 'Транспортная организация:', size=12, bold=True)
        y += 24
        it = [('darrow', '#5B2A8E', None, 'движение грузовых автомобилей'),
              ('darrow', '#1C9AD6', None, 'движение легковых автомобилей'),
              ('darrow', '#D7263F', None, 'движение пожарной техники'),
              ('dash', '#707070', 1.2, 'движение пешеходов'),
              ('arrow', '#D7262C', 1.6, 'вход в здание'),
              ('arrow', '#F08A24', 1.6, 'погрузка и выгрузка'),
              ('arrow', '#7A7A7A', 1.6, 'запасный выход'),
              ('dashdot', '#1F3FBF', 1.6, 'граница участка 77:10:0005004:1443')]
        for kind, a, b, t in it:
            hh = 30 if len(t) > 30 else 22
            self.legend_item(sl, x, y, kind, a, b, t, h=hh)
            y += hh
        y += 12
        sl.text(887.3, y, 250, 'Экспликация зданий и сооружений', size=12, bold=True)
        y += 22
        y = self.table(sl, [887.2, 908.0, 1080.0, 1145.2], y, ['№', 'Наименование', 'Кол-во'],
                       [('1', 'Проектируемое здание, м²', TEP['build']),
                        ('2', 'Стоянка временного пребывания автомобилей, м/м', '8', 26),
                        ('3', 'Площадка ТБО, шт.', '1')], size=8.5, align=['c', 'l', 'c'])
        y += 14
        sl.text(887.3, y, 258, ['Въезд легкового и грузового транспорта и пожарной техники — с проезда № 4921. '
                                'Погрузка и выгрузка — через ворота на фасаде 9–1.',
                                'Расчет машино-мест — лист 20.'], size=9, spacing=1.1, space_after=5, h=120,
                color=0.25)

    # --- 20. Расчет машино-мест ---------------------------------------------------------------------------------
    def p_parking(self):
        sl = self.page()
        self.bar(sl, 'Расчет нормативного количества машино-мест приобъектной парковки')
        sl.text(45.2, 166.0, 560, [
            'Расчет выполнен по приложениям 1, 3 и 6 к нормативам градостроительного проектирования города Москвы '
            'в области транспорта, автомобильных дорог регионального или межмуниципального значения '
            '(постановление Правительства Москвы от 23.12.2015 № 945-ПП).'], size=10, spacing=1.15, h=60)
        sl.text(45.2, 226.0, 560, [[('N', {'bold': True}), ('в', {'bold': True, 'size': 9}),
                                    (' = X / X2 × K1 × K2', {'bold': True})]], size=14)
        X = [45.2, 345.0, 470.0, 583.9]
        y = 252.0
        sl.rect(X[0], y, X[3], y + 20, fill=PINK, line='#FFFFFF', lw=1.0)
        for xa, xb, t in ((X[0], X[1], 'Показатель'), (X[1], X[2], 'Обоснование'), (X[2], X[3], 'Значение')):
            sl.text(xa + 6, y, xb - xa - 8, t, size=9.5, bold=True, h=20, anchor='m', y_is_glyph_top=False)
        y += 20
        rows = [
            ('Вид использования — производственная деятельность (6.0–6.8)', 'прил. 1, п. 4.1',
             '7–10 м/м на 100 работающих'),
            ('X — работающие в двух смежных сменах', 'данные заказчика', '20 чел.'),
            ('X2 — работающих на одно машино-место (по верхнему значению 10 м/м на 100)', 'прил. 1, п. 4.1',
             '10 чел.'),
            ('K1 — пешая доступность рельсового каркаса: ближайший вход — пл. Фирсановская (МЦД-3), около 2,5 км '
             'по прямой, более 2 200 м', 'прил. 6, таблица', '1,0'),
            ('K2 — деловая активность, район Савёлки', 'прил. 3, п. 92', '0,9'),
            ('Nв = 20 / 10 × 1,0 × 0,9', 'прил. 6', '1,8'),
            ('Требуется с округлением в большую сторону', 'прил. 6, примечание 3', '2 м/м'),
            ('Предусмотрено на участке (СПОЗУ, поз. 2)', 'САГР 466-5-22/С', '8 м/м'),
        ]
        for a, b, c in rows:
            h = 34 if len(a) > 60 else 22
            bold = a.startswith('Требуется') or a.startswith('Предусмотрено')
            for (xa, xb), t in zip(((X[0], X[1]), (X[1], X[2]), (X[2], X[3])), (a, b, c)):
                sl.rect(xa, y, xb, y + h, fill=CELL if not bold else PINK, line='#FFFFFF', lw=1.0)
                sl.text(xa + 6, y, xb - xa - 9, t, size=9, bold=bold, h=h, anchor='m', y_is_glyph_top=False,
                        spacing=0.95)
            y += h
        y += 16
        sl.text(45.2, y, 538, [
            [('Размещение: ', {'bold': True}), ('стоянка временного пребывания автомобилей на 8 машино-мест — '
                                                  'в границах участка, у северного фасада; въезд с проезда '
                                                  '№ 4921. Количество мест принято как в утвержденном АГР '
                                                  '(САГР № 466-5-22/С от 21.07.2022).', {})],
            [('Зарядная инфраструктура ', {'bold': True}), ('(945-ПП, таблица 6.1, п. 3): для производственных '
                                                             'зданий — 10 % мест в 2026 году, но не менее одной '
                                                             'зарядной станции; одно машино-место оборудуется '
                                                             'зарядной станцией для электромобилей.', {})],
            [('Погрузка и выгрузка ', {'bold': True}), ('— у ворот на фасаде 9–1, на асфальтобетонной площадке '
                                                        'участка; стоянка грузового транспорта на проезде '
                                                        '№ 4921 не предусматривается.', {})]],
            size=10, spacing=1.15, space_after=7, h=300)
        sl.text(606.5, 166.0, 540, 'Фрагмент СПОЗУ: стоянка временного пребывания автомобилей (поз. 2)', size=11,
                bold=True)
        self.pic(sl, 'spozu_park.png', 606.5, 186.0, 1145.2, 783.9, mode='cover', focus=(0.5, 0.45))

    # --- 21. Пояснительная записка ------------------------------------------------------------------------------
    def p_note(self):
        sl = self.page()
        self.bar(sl, 'Пояснительная записка')
        H = lambda t: [(t, {'bold': True, 'size': 12})]  # noqa: E731
        T = TEP
        left = [
            H('1. Общие сведения'),
            'Объект — производственное здание по адресу: г. Москва, Зеленоград, Восточная коммунальная зона, '
            'пр. 4921 (ЗелАО, район Савёлки). Земельный участок с кадастровым номером 77:10:0005004:1443 '
            'площадью ' + T['site_ha'] + ' га; градостроительный план № РФ-77-4-52-3-77-2026-08834-0 от '
            '12.08.2026. Заявитель — ООО «ВОСТОЧНАЯ», проектная организация — ООО «АТРИУМ АРХИТЕКТС». '
            'Материалы — корректировка АГР, утвержденного свидетельством № 466-5-22/С от 21.07.2022. Источник '
            'финансирования — внебюджетные средства.',
            H('2. Назначение'),
            'Здание предназначено для сборки металлических дверных блоков из готовых комплектующих: хранение '
            'комплектующих, сборка, установка фурнитуры, контроль качества, упаковка и отгрузка. '
            'Металлургического, литейного, гальванического и химического производства нет. Численность '
            'персонала — 20 человек.',
            H('3. Объемно-планировочное решение'),
            'Здание двухэтажное, без подземной части, прямоугольное в плане 48,0 × 24,0 м по осям 1–9 / А–Д. '
            'На первом этаже — производственное помещение 1 129,86 м² на всю высоту здания, лестничная клетка, '
            'санузел, КУИ, электрощитовая, ИТП и кладовая; на антресоли (+4,090) в осях 1–3 — административная '
            'зона 273,98 м² и лестничная клетка.',
            'Площадь застройки — ' + T['build'] + ' м², общая (наземная) площадь — ' + T['total'] + ' м², СПП — '
            + T['spp'] + ' м². Высота — ' + T['h'] + ' м до верха пожарной лестницы (абс. ' + T['habs'] + '), '
            'парапет +10,940 (абс. 206,96); ±0,000 = абс. ' + T['zero'] + '.',
        ]
        right = [
            H('4. Архитектурное решение'),
            'Фасады — стеновые сэндвич-панели 150 мм в три тона: RAL 7012, RAL 7042 и RAL 7035, фасонные '
            'элементы RAL 7012 и RAL 7038, цоколь — декоративная штукатурка RAL 7012. Ленточное остекление, '
            'ворота и двери RAL 7012, над входами — стеклянные козырьки. Цвета и материалы по позициям — '
            'в ведомости отделки фасадов.',
            H('5. Конструктивное решение'),
            'Каркас — колонны и стальные фермы покрытия, фундаменты столбчатые монолитные железобетонные, '
            'наружные стены — трехслойные сэндвич-панели с минераловатным утеплителем 150 мм, кровля '
            'двускатная неэксплуатируемая.',
            H('6. Благоустройство и транспортное обслуживание'),
            'Въезд на участок — с проезда № 4921. Покрытия — асфальтобетон, газон и газон, укрепленный '
            'георешеткой. Стоянка временного пребывания автомобилей на 8 машино-мест, площадка ТБО, '
            'уличные фонари, ландшафтные и напольные светильники, камеры видеонаблюдения. Погрузка и выгрузка — '
            'через ворота на фасаде 9–1.',
            H('7. Архитектурное освещение'),
            'Ландшафтно-архитектурные светильники, настенные светильники у входов и прожекторы с камерами.',
            H('8. Соответствие ГПЗУ'),
            'Предельная высота не установлена — проект ' + T['h'] + ' м; процент застройки ' + T['pct']
            + ' % при максимальном 44 %; общая площадь ' + T['total'] + ' м² при предельной 5 140 м². Отметка '
            + T['habs'] + ' м ниже ограничительной поверхности приаэродромной территории (сектор 3.2.2: '
            '267–293 м).',
        ]
        sl.text(45.2, 168.0, 540, left, size=11.5, spacing=1.2, space_after=8, h=610)
        sl.text(605.0, 168.0, 540, right, size=11.5, spacing=1.2, space_after=8, h=610)

    def build(self, out):
        self.p_title()
        self.p_info()
        self.p_photos()
        self.p_montage()
        self.p_zoning()
        self.p_persp1()
        self.p_persp2()
        self.p_persp34()
        self.p_blago()
        self.p_materials()
        self.p_light()
        self.p_appendix()
        self.p_facades(0)
        self.p_facades(1)
        self.p_plan(1)
        self.p_plan(2)
        self.p_sections()
        self.p_tep()
        self.p_spozu()
        self.p_parking()
        self.p_note()
        self.d.save(out)
        print(out, self.n, 'листов')


if __name__ == '__main__':
    img, assets, out = sys.argv[1:4]
    Book(img, assets, os.path.join(os.path.dirname(os.path.abspath(out)), '_cache')).build(out)
