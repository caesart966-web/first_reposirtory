"""Обложка и титульный лист тома — по образцу генпроектировщика («Титул.docx», ООО «Технология»).
Сведения о СРО — из выписки из единого реестра НОПРИЗ № 5262389143-20260428-1644 от 28.04.2026."""
import os
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from docs import SHIFR, wrap

_FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fonts')
pdfmetrics.registerFont(TTFont('TS', os.path.join(_FONTS, 'LiberationSans-Regular.ttf')))
pdfmetrics.registerFont(TTFont('TSB', os.path.join(_FONTS, 'LiberationSans-Bold.ttf')))

ORG_UP = 'ООО ТЕХНОЛОГИЯ'
SRO = ['Регистрационный номер П-152-005262389143-0630 от 23.04.2026 г.',
       'в реестре членов Союза «Инновационные технологии проектирования» (СРО-П-152-30032010)']
CUSTOMER = 'Заказчик: Общество с ограниченной ответственностью «ОПР Донецкий»'
OBJ_LINES = ['Оптово-продовольственный рынок (ОПР)', 'Расположенный по адресу: г. Макеевка, Горняцкий район',
             'Док-павильон №23, №23.2 «Рыба-Мясо»']
STAGE = 'РАБОЧАЯ ДОКУМЕНТАЦИЯ'
SECTION = 'Пожаротушение'
SYSTEMS = ('Внутренний противопожарный водопровод, автоматическая установка водяного пожаротушения, '
           'установка порошкового пожаротушения ВРУ, насосная станция пожаротушения')
SIGN = [('Генеральный директор', 'Н.В. Ступалова'), ('Главный инженер проекта', 'М.Н. Хвостов')]
YEAR = '2026'


def page(c, W, H, signatures):
    """Одна страница: обложка (signatures=False) или титульный лист (True). Размеры в мм, лист А4."""
    c.setLineWidth(0.7); c.rect(20 * mm, 5 * mm, (W - 25) * mm, (H - 10) * mm)
    cx = (20 + W - 5) / 2
    xl, xr = 33, W - 15

    def y(v):           # отсчёт от верха листа
        return (H - v) * mm

    def centred(v, s, font='TSB', size=11):
        c.setFont(font, size); c.drawCentredString(cx * mm, y(v), s)

    centred(29, ORG_UP, size=26)
    c.setLineWidth(0.5); c.line(xl * mm, y(41), xr * mm, y(41))
    c.setFont('TSB', 8.5); c.drawString(xl * mm, y(55), SRO[0])
    c.setFont('TS', 8.5); c.drawString(xl * mm, y(60), SRO[1])
    c.setFont('TSB', 8.5); c.drawString(xl * mm, y(73), CUSTOMER)
    for i, s in enumerate(OBJ_LINES):
        centred(96 + i * 8, s)
    top = 132 if signatures else 140
    centred(top, STAGE)
    centred(top + 15, SECTION)
    lines = wrap(SYSTEMS, 'TS', 10.5, 140 * mm)
    for i, s in enumerate(lines):
        centred(top + 22 + i * 5.5, s, 'TS', 10.5)
    centred(top + 34 + len(lines) * 5.5, SHIFR)
    if signatures:
        c.setFont('TS', 10.5)
        for i, (role, name) in enumerate(SIGN):
            c.drawString(xl * mm, y(222 + i * 16), role)
            c.drawRightString((xr - 8) * mm, y(222 + i * 16), name)
    centred(265, YEAR, 'TS', 10.5)
    c.showPage()
