# -*- coding: utf-8 -*-
"""Сборка презентации «Исследование текстильного рынка Индии».

Запуск:  python3 build_deck.py
Результат: Текстильный_рынок_Индии_презентация.pptx
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
import copy

# ---------------------------------------------------------------- палитра
INK        = RGBColor(0x12, 0x15, 0x1A)   # тёмный фон, основной текст
INK_SOFT   = RGBColor(0x52, 0x51, 0x4E)   # вторичный текст
MUTED      = RGBColor(0x8A, 0x88, 0x80)   # подписи, сноски
PAPER      = RGBColor(0xFF, 0xFF, 0xFF)
CARD       = RGBColor(0xF5, 0xF4, 0xF1)   # заливка карточек
HAIRLINE   = RGBColor(0xE2, 0xE0, 0xDA)   # тонкие линейки и рамки
INDIA      = RGBColor(0xEB, 0x68, 0x34)   # слот 2 палитры (оранжевый)
TURKEY     = RGBColor(0x2A, 0x78, 0xD6)   # слот 1 палитры (синий)
NEUTRAL    = RGBColor(0xC9, 0xC7, 0xC0)   # бары «контекста»
GOOD       = RGBColor(0x1B, 0xAF, 0x7A)
BAD        = RGBColor(0xE3, 0x49, 0x48)
ON_DARK    = RGBColor(0xFF, 0xFF, 0xFF)
ON_DARK_2  = RGBColor(0xB5, 0xB3, 0xAC)

FONT = "Segoe UI"

# ---------------------------------------------------------------- геометрия
SW, SH = 13.333, 7.5           # дюймы, 16:9
ML, MR = 0.85, 0.85            # поля
CW = SW - ML - MR              # ширина контентной колонки
Y_KICKER, Y_TITLE, Y_RULE, Y_BODY = 0.50, 0.80, 1.63, 1.92
Y_FOOT = 6.92

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(SW), Inches(SH)
BLANK = prs.slide_layouts[6]


# ---------------------------------------------------------------- примитивы
def _set_font_name(run, name):
    """Задаём гарнитуру и для латиницы/кириллицы, и для сложных письменностей."""
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:latin", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            rPr.append(el)
        el.set("typeface", name)


def add_slide():
    return prs.slides.add_slide(BLANK)


def bg(slide, color):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0,
                               prs.slide_width, prs.slide_height)
    s.fill.solid()
    s.fill.fore_color.rgb = color
    s.line.fill.background()
    s.shadow.inherit = False
    return s


def rect(slide, l, t, w, h, fill=None, line=None, radius=None, lw=1.0):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    s = slide.shapes.add_shape(shape_type, Inches(l), Inches(t),
                               Inches(w), Inches(h))
    if radius:
        s.adjustments[0] = radius
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(lw)
    s.shadow.inherit = False
    return s


def txt(slide, l, t, w, h, text, size=14, bold=False, color=INK,
        align=PP_ALIGN.LEFT, spacing=1.15, anchor=MSO_ANCHOR.TOP,
        space_after=0, italic=False):
    """text — строка или список строк (каждая = абзац)."""
    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    lines = text if isinstance(text, (list, tuple)) else [text]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        if space_after:
            p.space_after = Pt(space_after)
        r = p.add_run()
        r.text = line
        f = r.font
        f.size, f.bold, f.italic = Pt(size), bold, italic
        f.color.rgb = color
        f.name = FONT
        _set_font_name(r, FONT)
    return box


def rich(slide, l, t, w, h, parts, size=14, spacing=1.25, align=PP_ALIGN.LEFT,
         space_after=6, anchor=MSO_ANCHOR.TOP):
    """parts — список абзацев; абзац = список кортежей (текст, bold, color[, size])."""
    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, para in enumerate(parts):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        p.space_after = Pt(space_after)
        for chunk in para:
            text, bold, color = chunk[0], chunk[1], chunk[2]
            sz = chunk[3] if len(chunk) > 3 else size
            r = p.add_run()
            r.text = text
            r.font.size, r.font.bold = Pt(sz), bold
            r.font.color.rgb = color
            r.font.name = FONT
            _set_font_name(r, FONT)
    return box


def head(slide, kicker, title, rule_color=INDIA, title_size=31):
    txt(slide, ML, Y_KICKER, CW, 0.26, kicker.upper(), size=10.5, bold=True,
        color=MUTED, spacing=1.0)
    txt(slide, ML, Y_TITLE, CW, 0.8, title, size=title_size, bold=True,
        color=INK, spacing=1.02)
    rect(slide, ML, Y_RULE, 1.45, 0.045, fill=rule_color)


def foot(slide, note=None, page=None):
    if note:
        txt(slide, ML, Y_FOOT, CW - 0.6, 0.35, note, size=9.5, color=MUTED,
            spacing=1.25)
    if page is not None:
        txt(slide, SW - MR - 0.6, Y_FOOT, 0.6, 0.25, str(page), size=9.5,
            color=MUTED, align=PP_ALIGN.RIGHT)


def stat(slide, l, t, w, h, value, unit, label, accent=INDIA, vsize=30,
         usize=15, lsize=11.5):
    """Плитка показателя: крупное число + единица измерения + подпись."""
    rect(slide, l, t, w, h, fill=CARD, radius=0.07)
    rect(slide, l, t, 0.055, h, fill=accent)
    rich(slide, l + 0.34, t + 0.34, w - 0.48, 0.62,
         [[(value, True, INK, vsize), (" " + unit, True, INK_SOFT, usize)]],
         spacing=1.0, space_after=0)
    txt(slide, l + 0.34, t + 1.10, w - 0.58, h - 1.24, label, size=lsize,
        color=INK_SOFT, spacing=1.30)


def chip(slide, l, t, text, color, w=0.86, h=0.29, size=10.5):
    rect(slide, l, t, w, h, fill=color, radius=0.42)
    txt(slide, l, t + 0.045, w, h, text, size=size, bold=True, color=PAPER,
        align=PP_ALIGN.CENTER, spacing=1.0)


def hbars(slide, l, t, w, rows, label_w=3.5, bar_h=0.34, gap=0.30,
          value_w=1.35, max_val=None):
    """rows: (подпись, значение, текст значения, цвет, пометка|None, цвет пометки)"""
    mx = max_val or max(r[1] for r in rows)
    track = w - label_w - value_w - 0.25
    y = t
    for row in rows:
        name, val, vtext, color = row[0], row[1], row[2], row[3]
        mark = row[4] if len(row) > 4 else None
        mcolor = row[5] if len(row) > 5 else MUTED
        txt(slide, l, y + 0.015, label_w - 0.2, bar_h, name, size=12.5,
            color=INK, spacing=1.12, anchor=MSO_ANCHOR.MIDDLE)
        rect(slide, l + label_w, y, track, bar_h, fill=RGBColor(0xEF, 0xEE, 0xEA))
        bw = max(track * val / mx, 0.06)
        rect(slide, l + label_w, y, bw, bar_h, fill=color, radius=0.13)
        txt(slide, l + label_w + track + 0.16, y + 0.015, value_w, bar_h, vtext,
            size=13.5, bold=True, color=INK, spacing=1.0,
            anchor=MSO_ANCHOR.MIDDLE)
        if mark:
            txt(slide, l + label_w, y + bar_h + 0.015, track, 0.24, mark,
                size=10, color=mcolor, spacing=1.0)
        y += bar_h + gap
    return y


# ================================================================== СЛАЙД 1
s = add_slide()
bg(s, INK)
rect(s, 0, 0, 0.22, SH, fill=INDIA)
# геометрический акцент справа
rect(s, SW - 3.5, -1.2, 4.6, 4.6, fill=RGBColor(0x1B, 0x1F, 0x26), radius=0.5)
rect(s, SW - 2.35, 4.35, 2.1, 2.1, fill=RGBColor(0x1B, 0x1F, 0x26), radius=0.5)
rect(s, SW - 2.9, 0.95, 1.5, 0.05, fill=INDIA)

txt(s, 1.25, 1.60, 9.5, 0.3, "ИССЛЕДОВАНИЕ ОТРАСЛЕВОГО РЫНКА · 2026",
    size=12, bold=True, color=INDIA, spacing=1.0)
txt(s, 1.25, 2.10, 9.6, 1.9, ["Текстильный рынок", "Индии"],
    size=54, bold=True, color=ON_DARK, spacing=0.98)
rect(s, 1.25, 4.18, 1.6, 0.05, fill=ON_DARK_2)
txt(s, 1.25, 4.50, 8.6, 0.9,
    "Масштаб, структура экспорта, точки роста\nи сравнение с текстильной отраслью Турции",
    size=15.5, color=ON_DARK_2, spacing=1.35)
txt(s, 1.25, 6.05, 8.0, 0.3, "ДОКЛАД ПОДГОТОВИЛИ", size=10, bold=True,
    color=MUTED, spacing=1.0)
txt(s, 1.25, 6.38, 9.0, 0.45, "Багишев Алихан   ·   Тимофеева Александра",
    size=17, bold=True, color=ON_DARK, spacing=1.0)

# ================================================================== СЛАЙД 2
s = add_slide()
bg(s, PAPER)
head(s, "О чём доклад", "Три вопроса")
cards = [
    ("01", "Что такое текстильная отрасль Индии в цифрах",
     "Масштаб, структура экспорта, сырьевая база, государственные программы."),
    ("02", "Что изменилось для неё в 2025–2026 годах",
     "Тарифы США, соглашения с Великобританией и ЕС, разворот к химволокну."),
    ("03", "Чем Индия отличается от Турции",
     "Две разные модели конкуренции — и кто выигрывает на рынке ЕС."),
]
cw = (CW - 0.6) / 3
for i, (num, title, sub) in enumerate(cards):
    x = ML + i * (cw + 0.3)
    rect(s, x, Y_BODY, cw, 3.55, fill=CARD, radius=0.06)
    txt(s, x + 0.42, Y_BODY + 0.40, 1.2, 0.6, num, size=34, bold=True,
        color=INDIA, spacing=1.0)
    txt(s, x + 0.42, Y_BODY + 1.20, cw - 0.84, 1.1, title, size=16.5,
        bold=True, color=INK, spacing=1.18)
    txt(s, x + 0.42, Y_BODY + 2.35, cw - 0.84, 1.0, sub, size=12.5,
        color=INK_SOFT, spacing=1.3)
foot(s, "Источники данных: Министерство текстиля Индии (PIB), GTRI, IBEF, "
        "USDA FAS, Евростат, Türkiye Today, Fibre2Fashion, ВТО. "
        "Полный список — на последнем слайде.", 2)

# ================================================================== СЛАЙД 3
s = add_slide()
bg(s, PAPER)
head(s, "Индия · масштаб", "Отрасль в четырёх цифрах")
tw = (CW - 0.66) / 4
tiles = [
    ("$225", "млрд", "Внутренний рынок текстиля\nи одежды, 2025 год.\nРост 10–12% в год"),
    ("45", "млн", "Занятых напрямую.\nВторой работодатель страны\nпосле сельского хозяйства"),
    ("~11", "%", "Доля в добавленной стоимости\nобрабатывающей промышленности.\nВ ВВП — около 2%"),
    ("4,6", "%", "Доля в мировой торговле\nтекстилем и одеждой.\n2-й производитель, 3-й экспортёр"),
]
for i, (v, u, lab) in enumerate(tiles):
    stat(s, ML + i * (tw + 0.22), Y_BODY, tw, 2.80, v, u, lab, vsize=31)

rect(s, ML, 5.05, CW, 1.28, fill=INK, radius=0.05)
rich(s, ML + 0.45, 5.33, CW - 0.9, 0.85, [[
    ("Внутренний рынок в 6 раз больше экспорта.", True, ON_DARK, 17),
    ("  Индия — прежде всего собственный потребитель, а не экспортная "
     "витрина. Цель правительства — $350 млрд к 2030 году.", False, ON_DARK_2, 14.5),
]], spacing=1.3)
foot(s, "IBEF, «Indian Textiles and Apparel Industry Analysis», февраль 2026.", 3)

# ================================================================== СЛАЙД 4
s = add_slide()
bg(s, PAPER)
head(s, "Индия · экспорт", "Структура экспорта, 2025–26 фин. год")
txt(s, ML, Y_RULE + 0.22, CW, 0.35,
    "Всего 3,16 трлн рупий ≈ $35,8 млрд. Под столбцами — доля и рост за год в рупиях",
    size=13, color=INK_SOFT, spacing=1.0)
rows = [
    ("Готовая одежда", 15.8, "$15,8 млрд", INDIA, "44% экспорта   ·   +2,9%", MUTED),
    ("Хлопок: пряжа, ткани,\nготовые изделия", 11.6, "$11,6 млрд", INDIA,
     "32%   ·   +0,4% — почти остановка", MUTED),
    ("Химволокно: пряжа,\nткани, изделия", 4.8, "$4,8 млрд", INDIA,
     "13%   ·   +3,6% — самый быстрый сегмент", GOOD),
    ("Ремёсла", 1.8, "$1,8 млрд", NEUTRAL, "5%   ·   +6,1%", MUTED),
    ("Прочее: ковры, джут,\nшёлк, шерсть", 1.8, "$1,8 млрд", NEUTRAL, "5%", MUTED),
]
hbars(s, ML, Y_BODY + 0.35, CW, rows, label_w=3.4, bar_h=0.40, gap=0.36,
      value_w=1.5)
rect(s, ML, 6.10, CW, 0.62, fill=CARD, radius=0.08)
rich(s, ML + 0.35, 6.26, CW - 0.7, 0.4, [[
    ("Главный рынок — США: ", True, INK, 13),
    ("33% экспорта готовой одежды, $5,33 млрд. Рост зафиксирован "
     "более чем в 120 странах.", False, INK_SOFT, 13),
]], spacing=1.0)
foot(s, "PIB, Министерство текстиля Индии, апрель 2026; GTRI. "
        "Пересчёт рупий в доллары по курсу ≈ 88 рупий за доллар.", 4)

# ================================================================== СЛАЙД 5
s = add_slide()
bg(s, PAPER)
head(s, "Индия · 2025–26", "Главный парадокс года")

rect(s, ML, Y_BODY, 5.55, 2.05, fill=CARD, radius=0.06)
rect(s, ML, Y_BODY, 0.055, 2.05, fill=GOOD)
txt(s, ML + 0.42, Y_BODY + 0.36, 4.6, 0.85, "+2,1%", size=46, bold=True,
    color=GOOD, spacing=1.0)
txt(s, ML + 0.42, Y_BODY + 1.22, 4.8, 0.7,
    "в рупиях. Официальный релиз\nМинистерства текстиля Индии",
    size=13, color=INK_SOFT, spacing=1.28)

rect(s, ML + 5.88, Y_BODY, 5.75, 2.05, fill=CARD, radius=0.06)
rect(s, ML + 5.88, Y_BODY, 0.055, 2.05, fill=BAD)
txt(s, ML + 6.30, Y_BODY + 0.36, 4.6, 0.85, "−2,2%", size=46, bold=True,
    color=BAD, spacing=1.0)
txt(s, ML + 6.30, Y_BODY + 1.22, 5.0, 0.7,
    "в долларах, до $35,8 млрд.\nОценка GTRI по тем же данным",
    size=13, color=INK_SOFT, spacing=1.28)

rich(s, ML, 4.22, CW, 0.45, [[
    ("Оба утверждения верны. ", True, INK, 16),
    ("Разницу съела девальвация рупии. Причина падения — тарифы США.",
     False, INK_SOFT, 16),
]], spacing=1.2)

# лента событий
ty = 5.00
rect(s, ML, ty + 0.30, CW, 0.03, fill=HAIRLINE)
events = [
    ("7 авг. 2025", "Пошлина США\n+25%", MUTED),
    ("27 авг. 2025", "Ещё +25%.\nИтого 50%", BAD),
    ("3 фев. 2026", "Сделка:\nтариф 18%", GOOD),
]
step = CW / 3
for i, (date, what, col) in enumerate(events):
    x = ML + i * step
    rect(s, x, ty + 0.19, 0.25, 0.25, fill=col, radius=0.5)
    txt(s, x + 0.40, ty + 0.12, step - 0.6, 0.3, date, size=12, bold=True,
        color=INK, spacing=1.0)
    txt(s, x + 0.40, ty + 0.44, step - 0.6, 0.6, what, size=11.5, color=INK_SOFT,
        spacing=1.25)
foot(s, "США — 28% экспорта текстиля и одежды Индии, более $10 млрд в год. "
        "Текстиль пострадал от тарифов сильнее других отраслей: "
        "отдельные экспортёры теряли до половины оборота.", 5)

# ================================================================== СЛАЙД 6
s = add_slide()
bg(s, PAPER)
head(s, "Индия · сырьё", "Хлопок: сила и ловушка")
half = (CW - 0.4) / 2

rect(s, ML, Y_BODY, half, 3.62, fill=CARD, radius=0.06)
rect(s, ML, Y_BODY, half, 0.055, fill=GOOD)
txt(s, ML + 0.45, Y_BODY + 0.38, half - 0.9, 0.35, "СИЛА", size=11, bold=True,
    color=GOOD, spacing=1.0)
rich(s, ML + 0.45, Y_BODY + 0.95, half - 0.9, 2.2, [
    [("36%", True, INK, 30)],
    [("мировых посевных площадей под хлопком — 11,4 млн га. "
      "Первое место в мире", False, INK_SOFT, 13.5)],
    [("5,4 млн т", True, INK, 22)],
    [("сбор сезона 2025/26 — около 21% мирового производства",
      False, INK_SOFT, 13.5)],
], spacing=1.25, space_after=7)

rect(s, ML + half + 0.4, Y_BODY, half, 3.62, fill=CARD, radius=0.06)
rect(s, ML + half + 0.4, Y_BODY, half, 0.055, fill=BAD)
txt(s, ML + half + 0.85, Y_BODY + 0.38, half - 0.9, 0.35, "ЛОВУШКА",
    size=11, bold=True, color=BAD, spacing=1.0)
rich(s, ML + half + 0.85, Y_BODY + 0.95, half - 0.9, 2.2, [
    [("60 : 40", True, INK, 30)],
    [("соотношение хлопок : химволокно в Индии. В мире — ровно наоборот, "
      "25 : 75", False, INK_SOFT, 13.5)],
    [("9,2%", True, INK, 22)],
    [("доля Индии в мировом производстве химических волокон",
      False, INK_SOFT, 13.5)],
], spacing=1.25, space_after=7)

rect(s, ML, 5.76, CW, 0.92, fill=INK, radius=0.05)
rich(s, ML + 0.45, 5.96, CW - 0.9, 0.6, [[
    ("Индия сильна в том сырье, спрос на которое растёт медленнее всего.",
     True, ON_DARK, 15),
    ("  В 2024 году химволокно дало 77% мирового потребления волокна, "
     "хлопок — 22%.", False, ON_DARK_2, 13.5),
]], spacing=1.25)
foot(s, "USDA FAS, Cotton and Products Update — India, 2025/26; "
        "Минтекстиля Индии, концепция National Fibre Mission 2030–31.", 6)

# ================================================================== СЛАЙД 7
s = add_slide()
bg(s, PAPER)
head(s, "Индия · политика", "Что делает государство")
progs = [
    ("PLI", "≈ $1,2 млрд",
     "Субсидия за результат: одежда и ткани из химволокна плюс 10 сегментов "
     "технического текстиля.",
     "Факт на 31.03.2026: вложено ≈ $0,9 млрд, создано 33 427 рабочих мест."),
    ("PM MITRA", "≈ $5,0 млрд",
     "Семь мегапарков полного цикла — от волокна до готового изделия. "
     "Бюджет до 2027–28 года.",
     "Цель: привлечь ≈ $7,9 млрд инвестиций и около 2 млн рабочих мест."),
    ("Миссия по волокнам", "до 2030–31",
     "Перевернуть соотношение волокон на 60 : 40 в пользу химических.",
     "Производство волокна +50%, до 22,8 млн т. Импорт волокна −22% к 2031 году."),
]
cw3 = (CW - 0.56) / 3
for i, (name, money, what, fact) in enumerate(progs):
    x = ML + i * (cw3 + 0.28)
    rect(s, x, Y_BODY, cw3, 4.42, fill=PAPER, line=HAIRLINE, radius=0.05, lw=1.1)
    rect(s, x, Y_BODY, cw3, 0.05, fill=INDIA)
    txt(s, x + 0.40, Y_BODY + 0.42, cw3 - 0.8, 0.62, name, size=18, bold=True,
        color=INK, spacing=1.08)
    txt(s, x + 0.40, Y_BODY + 1.14, cw3 - 0.8, 0.45, money, size=25, bold=True,
        color=INDIA, spacing=1.0)
    txt(s, x + 0.40, Y_BODY + 1.82, cw3 - 0.8, 1.30, what, size=12.5,
        color=INK_SOFT, spacing=1.3)
    rect(s, x + 0.40, Y_BODY + 3.20, cw3 - 0.8, 0.02, fill=HAIRLINE)
    txt(s, x + 0.40, Y_BODY + 3.38, cw3 - 0.8, 0.95, fact, size=12,
        color=INK, spacing=1.3)
foot(s, "PIB и Министерство текстиля Индии, 2026. "
        "Пересчёт по курсу ≈ 88 рупий за доллар.", 7)

# ================================================================== СЛАЙД 8
s = add_slide()
bg(s, PAPER)
head(s, "Индия · внешняя торговля", "Торговая дипломатия — главный рычаг")
deals = [
    ("США", "50% → 18%", GOOD,
     "3 февраля 2026 года — промежуточное торговое соглашение. "
     "Пошлина на текстиль и одежду снижена с 50 до 18 процентов.",
     "Действует"),
    ("Великобритания", "0% по 1143 линиям", GOOD,
     "Соглашение CETA вступило в силу 15 июля 2026 года. Пошлины были до 12%. "
     "Ожидаемый прирост экспорта — $1,6 млрд в год.",
     "Действует"),
    ("Европейский союз", "обнуление >90% линий", INDIA,
     "Переговоры завершены 27 января 2026 года — после 18 лет. "
     "Сейчас пошлины 8–12%. В силу — после ратификации, ориентир — середина 2027.",
     "Ожидает ратификации"),
]
y = Y_BODY
for name, headline, col, body, status in deals:
    rect(s, ML, y, CW, 1.28, fill=CARD, radius=0.06)
    rect(s, ML, y, 0.055, 1.28, fill=col)
    txt(s, ML + 0.42, y + 0.24, 2.9, 0.4, name, size=17, bold=True, color=INK,
        spacing=1.0)
    txt(s, ML + 0.42, y + 0.68, 3.2, 0.4, headline, size=15.5, bold=True,
        color=col, spacing=1.0)
    txt(s, ML + 3.85, y + 0.26, CW - 6.55, 0.90, body, size=12.5,
        color=INK_SOFT, spacing=1.32)
    chip(s, SW - MR - 2.35, y + 0.49, status, col, w=2.15, h=0.32, size=10)
    y += 1.48
rich(s, ML, 6.50, CW, 0.4, [[
    ("Именно соглашение с ЕС меняет расстановку сил в Европе — ",
     True, INK, 14),
    ("и именно там Индия напрямую пересекается с Турцией.", False, INK_SOFT, 14),
]], spacing=1.1)
foot(s, None, 8)

# ================================================================== СЛАЙД 9
s = add_slide()
bg(s, PAPER)
head(s, "Индия · ограничения", "Чего Индии не хватает")
weak = [
    ("Фрагментация",
     "Основная масса производств — малые и средние предприятия со старым "
     "оборудованием. Сквозной цепочки «волокно → готовое изделие» почти нет."),
    ("Производительность труда",
     "Высокая текучесть кадров, тонкий слой линейных руководителей, "
     "слабая отраслевая подготовка рабочих."),
    ("Сырьевой перекос",
     "Ставка на хлопок при мировом спросе на химволокно. "
     "Доля Индии в мировом производстве химволокна — 9,2%."),
    ("Сроки поставки",
     "Морем до Европы 3–4 недели. Для заказчика, которому нужна коллекция "
     "за три недели, Индия географически далеко."),
]
cw2 = (CW - 0.35) / 2
for i, (t_, b_) in enumerate(weak):
    x = ML + (i % 2) * (cw2 + 0.35)
    y = Y_BODY + (i // 2) * 2.25
    rect(s, x, y, cw2, 2.00, fill=PAPER, line=HAIRLINE, radius=0.05, lw=1.1)
    txt(s, x + 0.40, y + 0.30, 0.5, 0.4, "0" + str(i + 1), size=15, bold=True,
        color=INDIA, spacing=1.0)
    txt(s, x + 1.05, y + 0.28, cw2 - 1.5, 0.4, t_, size=16, bold=True,
        color=INK, spacing=1.0)
    txt(s, x + 1.05, y + 0.78, cw2 - 1.5, 1.10, b_, size=12.5, color=INK_SOFT,
        spacing=1.3)
foot(s, None, 9)

# ================================================================== СЛАЙД 10
s = add_slide()
bg(s, PAPER)
head(s, "Турция · профиль", "Турция: вторая модель", rule_color=TURKEY)
tw = (CW - 0.66) / 4
tiles = [
    ("$26,2", "млрд", "Экспорт текстиля и одежды\nза 2025 год.\nСнижение на 4,4%"),
    ("$16,8", "млрд", "Одежда, −6,3%.\nТекстиль — $9,4 млрд, −0,8%.\nСальдо: +$17 млрд"),
    ("~2", "млн", "Занятых в отрасли.\nОколо 44 000 компаний,\n95% — частные"),
    ("~70", "%", "Экспорта идёт в ЕС.\nТурция — 3-й поставщик\nодежды в Евросоюз"),
]
for i, (v, u, lab) in enumerate(tiles):
    stat(s, ML + i * (tw + 0.22), Y_BODY, tw, 2.80, v, u, lab, accent=TURKEY,
         vsize=31)
rect(s, ML, 5.10, CW, 1.30, fill=CARD, radius=0.05)
rich(s, ML + 0.45, 5.36, CW - 0.9, 0.9, [[
    ("Сильные стороны: ", True, INK, 15),
    ("полная вертикальная интеграция — пряжа, ткань, крашение, пошив и отделка "
     "внутри одной страны; мировое лидерство в дениме и трикотаже; "
     "домашний текстиль; 3–5 дней доставки до Европы против 3–4 недель у Индии.",
     False, INK_SOFT, 14),
]], spacing=1.32)
foot(s, "Türkiye Today, январь 2026; Fibre2Fashion; Textilegence.", 10)

# ================================================================== СЛАЙД 11
s = add_slide()
bg(s, PAPER)
head(s, "Турция · причины", "Издержки съели преимущество",
     rule_color=TURKEY)
txt(s, ML, Y_RULE + 0.22, CW, 0.3,
    "Минимальная зарплата в отрасли, долларов в месяц",
    size=13, color=INK_SOFT, spacing=1.0)
rows = [
    ("Турция, 2026", 655, "$655", TURKEY, "28 075 лир нетто   ·   +27% за год", BAD),
    ("Индия, Бангладеш,\nЕгипет", 150, "$100–150", NEUTRAL,
     "устойчиво в этом диапазоне", MUTED),
]
hbars(s, ML, Y_BODY + 0.32, CW, rows, label_w=3.0, bar_h=0.46, gap=0.48,
      value_w=1.5)

bullets = [
    "Инфляция около 30% в год, волатильность лиры, дорогая энергия.",
    "Хлопок: сбор 2025/26 — около 665 тыс. т, импорт — 825–900 тыс. т. "
    "Турция ввозит хлопка больше, чем выращивает.",
    "Фабрики закрываются, производство переносят в Египет и Марокко: "
    "там ниже издержки и есть свои соглашения о свободной торговле.",
]
y = 4.35
for b in bullets:
    rect(s, ML, y + 0.10, 0.10, 0.10, fill=TURKEY, radius=0.5)
    txt(s, ML + 0.38, y, CW - 0.5, 0.65, b, size=13.5, color=INK, spacing=1.32)
    y += 0.82
foot(s, "Fibre2Fashion, декабрь 2025; USDA FAS, Cotton and Products Update — "
        "Türkiye, 2025/26; Textilegence.", 11)

# ================================================================== СЛАЙД 12
s = add_slide()
bg(s, PAPER)
head(s, "Сравнение", "Индия и Турция: лобовое сравнение")

table_rows = [
    ("Экспорт текстиля и одежды", "$35,8 млрд", "$26,2 млрд"),
    ("Динамика за год", "−2,2% — тарифы США", "−4,4% — издержки"),
    ("Занятость в отрасли", "45 млн человек", "около 2 млн человек"),
    ("Хлопок", "крупнейший производитель", "нетто-импортёр"),
    ("Минимальная зарплата", "$100–150 в месяц", "$655 в месяц"),
    ("Главный рынок сбыта", "США — 33% экспорта одежды", "ЕС — около 70% экспорта"),
    ("Доставка в Европу", "3–4 недели морем", "3–5 дней"),
    ("Цепочка создания", "фрагментирована", "вертикально интегрирована"),
]
col1, col2 = 4.3, (CW - 4.3) / 2
rh = 0.505
ty = Y_BODY + 0.02

# шапка
txt(s, ML + 0.25, ty + 0.10, col1 - 0.3, 0.32, "ПОКАЗАТЕЛЬ", size=10.5,
    bold=True, color=MUTED, spacing=1.0)
for cx, name, col, period in (
        (ML + col1, "ИНДИЯ", INDIA, "2025–26 фин. год"),
        (ML + col1 + col2, "ТУРЦИЯ", TURKEY, "2025 календарный год")):
    rect(s, cx, ty + 0.045, 0.11, 0.11, fill=col, radius=0.5)
    txt(s, cx + 0.28, ty, col2 - 0.3, 0.3, name, size=12.5, bold=True,
        color=col, spacing=1.0)
    txt(s, cx + 0.28, ty + 0.27, col2 - 0.3, 0.28, period, size=9.5,
        color=MUTED, spacing=1.0)
ty += 0.62
rect(s, ML, ty, CW, 0.025, fill=INK)
ty += 0.10

for i, (k, a, b) in enumerate(table_rows):
    if i % 2 == 0:
        rect(s, ML, ty, CW, rh, fill=CARD)
    txt(s, ML + 0.25, ty, col1 - 0.35, rh, k, size=12.5, color=INK_SOFT,
        spacing=1.0, anchor=MSO_ANCHOR.MIDDLE)
    txt(s, ML + col1 + 0.28, ty, col2 - 0.4, rh, a, size=13, bold=True,
        color=INK, spacing=1.0, anchor=MSO_ANCHOR.MIDDLE)
    txt(s, ML + col1 + col2 + 0.28, ty, col2 - 0.4, rh, b, size=13, bold=True,
        color=INK, spacing=1.0, anchor=MSO_ANCHOR.MIDDLE)
    ty += rh
rect(s, ML, ty, CW, 0.02, fill=HAIRLINE)
foot(s, "Обозначение цветом: оранжевый — Индия, синий — Турция; "
        "тот же код используется на следующем слайде.", 12)

# ================================================================== СЛАЙД 13
s = add_slide()
bg(s, PAPER)
head(s, "Сравнение · рынок ЕС", "Битва за рынок Евросоюза")
txt(s, ML, Y_RULE + 0.22, CW, 0.3,
    "Импорт одежды в ЕС, январь–ноябрь 2025: $96,4 млрд, рост на 3,9%",
    size=13, color=INK_SOFT, spacing=1.0)
rows = [
    ("Китай", 28.4, "$28,4 млрд", NEUTRAL, "+6,6%", MUTED),
    ("Бангладеш", 21.0, "$21,0 млрд", NEUTRAL, "рост с $19,5 млрд", MUTED),
    ("Турция", 8.9, "$8,9 млрд", TURKEY, "−11,3% — двузначное падение", BAD),
    ("Индия", 4.1, "≈ $4,1 млрд", INDIA,
     "+10,6% в деньгах и +16,0% в объёме", GOOD),
]
hbars(s, ML, Y_BODY + 0.40, CW, rows, label_w=2.3, bar_h=0.40, gap=0.36,
      value_w=1.7)
rect(s, ML, 5.30, CW, 1.15, fill=INK, radius=0.05)
rich(s, ML + 0.45, 5.52, CW - 0.9, 0.75, [[
    ("Турция пока вдвое больше Индии — но падает, а Индия растёт. ",
     True, ON_DARK, 15),
    ("Объём у Индии растёт быстрее выручки: значит, рынок она берёт ценой, "
     "а не premium-продуктом.", False, ON_DARK_2, 14),
]], spacing=1.3)
foot(s, "Евростат; EmergingTextiles, обзор импорта одежды в ЕС по странам "
        "происхождения. Данные по Индии пересчитаны из евро (€3,76 млрд).", 13)

# ================================================================== СЛАЙД 14
s = add_slide()
bg(s, PAPER)
head(s, "Вывод из сравнения", "Две модели, а не два конкурента")
half = (CW - 0.4) / 2
blocks = [
    (TURKEY, "ТУРЦИЯ", "Продаёт скорость и близость",
     ["3–5 дней до Европы, полный производственный цикл внутри страны",
      "Деним, трикотаж, домашний текстиль, технический текстиль",
      "Теряет рынок ровно потому, что цена этой скорости выросла"]),
    (INDIA, "ИНДИЯ", "Продаёт масштаб и сырьё",
     ["Собственный хлопок, 45 млн рабочих рук, низкая себестоимость",
      "Растущий внутренний рынок и новые соглашения о свободной торговле",
      "Слабое место — сроки поставки и сложность изделия"]),
]
for i, (col, name, claim, items) in enumerate(blocks):
    x = ML + i * (half + 0.4)
    rect(s, x, Y_BODY, half, 3.55, fill=PAPER, line=HAIRLINE, radius=0.05, lw=1.1)
    rect(s, x, Y_BODY, half, 0.055, fill=col)
    txt(s, x + 0.45, Y_BODY + 0.38, half - 0.9, 0.3, name, size=11, bold=True,
        color=col, spacing=1.0)
    txt(s, x + 0.45, Y_BODY + 0.78, half - 0.9, 0.5, claim, size=19, bold=True,
        color=INK, spacing=1.1)
    yy = Y_BODY + 1.55
    for it in items:
        rect(s, x + 0.45, yy + 0.09, 0.09, 0.09, fill=col, radius=0.5)
        txt(s, x + 0.78, yy, half - 1.3, 0.62, it, size=13, color=INK_SOFT,
            spacing=1.3)
        yy += 0.66
rect(s, ML, 5.82, CW, 0.85, fill=CARD, radius=0.05)
rich(s, ML + 0.45, 6.02, CW - 0.9, 0.5, [[
    ("Прямая конкуренция — в узком сегменте: ", True, INK, 14.5),
    ("базовый хлопковый трикотаж и домашний текстиль средней ценовой "
     "категории.", False, INK_SOFT, 14.5),
]], spacing=1.2)
foot(s, None, 14)

# ================================================================== СЛАЙД 15
s = add_slide()
bg(s, INK)
txt(s, ML, Y_KICKER, CW, 0.26, "ИТОГ", size=10.5, bold=True, color=INDIA,
    spacing=1.0)
txt(s, ML, Y_TITLE, CW, 0.8, "Четыре вывода", size=31, bold=True,
    color=ON_DARK, spacing=1.02)
rect(s, ML, Y_RULE, 1.45, 0.045, fill=INDIA)

concl = [
    ("Индия — прежде всего внутренний рынок.",
     "$225 млрд внутреннего потребления против $36 млрд экспорта. "
     "Экспортная статистика описывает лишь шестую часть отрасли."),
    ("Итог года определили тарифы, а не заводы.",
     "50-процентная пошлина США дала −2,2% по году. Её снижение до 18% "
     "в феврале 2026 — главный фактор роста в 2026–27."),
    ("Отставание Индия закрывает дипломатией.",
     "Соглашение с Великобританией уже работает, соглашение с ЕС ждёт "
     "ратификации. У Турции этого рычага нет: она в таможенном союзе с ЕС "
     "с 1996 года и выжала из него всё."),
    ("Главный риск — собственное волокно.",
     "Пока соотношение 60 : 40 в пользу хлопка при мировом 25 : 75, "
     "цель в $350 млрд недостижима. Результат Миссии по волокнам "
     "будет виден к 2030 году."),
]
y = Y_BODY
for i, (t_, b_) in enumerate(concl):
    txt(s, ML, y, 0.6, 0.4, str(i + 1), size=20, bold=True, color=INDIA,
        spacing=1.0)
    txt(s, ML + 0.62, y - 0.02, CW - 0.7, 0.35, t_, size=17, bold=True,
        color=ON_DARK, spacing=1.05)
    txt(s, ML + 0.62, y + 0.38, CW - 0.9, 0.7, b_, size=13, color=ON_DARK_2,
        spacing=1.32)
    y += 1.20
foot(s, None, 15)

# ================================================================== СЛАЙД 16
s = add_slide()
bg(s, PAPER)
head(s, "Проверяемость", "Источники")
src = [
    "Press Information Bureau, Министерство текстиля Индии. India's Textile "
    "Exports Register Growth of 2.1% in FY 2025–26. Апрель 2026. pib.gov.in",
    "Global Trade Research Initiative (GTRI) / Business Standard. Textiles and "
    "garment exports fall 2.2% to $35.8 bn in FY26. 25.04.2026.",
    "IBEF. Indian Textiles and Apparel Industry Analysis. Февраль 2026. "
    "ibef.org/industry/textiles",
    "Министерство текстиля Индии. National Fibre Mission 2030–31, концепция. "
    "texmin.gov.in",
    "PIB. PM MITRA Parks; PLI Scheme for Textiles — статус на 31.03.2026.",
    "USDA Foreign Agricultural Service. Cotton and Products Update: India "
    "(IN2025-0047) и Türkiye (TU2025-0063). 2025–2026.",
    "Türkiye Today. Textile exports still vital to Türkiye's trade despite "
    "4.4% drop to $26.18B in 2025. Январь 2026.",
    "Fibre2Fashion. Türkiye's apparel exports drop 6% to $16.3 bn in 2025; "
    "Türkiye raises monthly minimum wage by 27% for 2026.",
    "Евростат / EmergingTextiles. EU clothing imports by origin, "
    "январь–ноябрь 2025.",
    "FashionUnited, Just-Style. India-UK CETA comes into force. 15.07.2026.",
    "Министерство торговли и промышленности Индии. India–EU Free Trade "
    "Agreement Concluded. 27.01.2026. commerce.gov.in",
    "Textilegence; Hertzman Global Intelligence — обзоры турецкой текстильной "
    "отрасли, 2025–2026.",
]
cw2 = (CW - 0.5) / 2
per = (len(src) + 1) // 2
for i, item in enumerate(src):
    x = ML + (i // per) * (cw2 + 0.5)
    y = Y_BODY + (i % per) * 0.70
    txt(s, x, y, 0.42, 0.3, str(i + 1) + ".", size=11.5, bold=True, color=INDIA,
        spacing=1.0)
    txt(s, x + 0.42, y, cw2 - 0.5, 0.62, item, size=11, color=INK_SOFT,
        spacing=1.28)
foot(s, "Все цифры в докладе приведены по состоянию на сентябрь 2026 года. "
        "Финансовый год Индии: с 1 апреля по 31 марта.", 16)

prs.save("Текстильный_рынок_Индии_презентация.pptx")
print("OK:", len(prs.slides.__iter__.__self__._sldIdLst), "слайдов")
