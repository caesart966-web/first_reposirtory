"""Изм. 4 ВК 140-1/2026: дренажный приямок котельной (пом. 134) с насосом Н2.

izm4_dxf.py ВХОД_DXF ВЫХОД_DXF — правит листы 1, 4, 5 и задания ТЗ-1, ТЗ-2 (остальные не трогает).
Координаты плана — в мм модели листа 2/ТЗ (у листа 4 сдвиг DX4 = 97260 по x).
"""
import math
import os
import sys

import ezdxf
from ezdxf import bbox
from ezdxf.enums import TextEntityAlignment as TA
from ezdxf.fonts import fonts

SRC, DST = sys.argv[1], sys.argv[2]
os.makedirs(DST, exist_ok=True)
FONT = fonts.make_font('isocpeur.ttf', 1.0)


def tw(s, h):
    return FONT.text_width(s) * h


# --- приямок в плане (координаты листа 2 / ТЗ) ---------------------------------------------------------------------
PIT_OUT = (20423, 42700, 21423, 43700)        # наружный контур 1000×1000, 100 мм от внутренней грани стены по оси 3
PIT_IN = (20623, 42900, 21223, 43500)         # в свету 600×600
PUMP = (21073, 43300)                         # насос Н2 и подъемный участок напорного трубопровода
DOWN = (21073, 43850)                         # опуск петли в раструб трубы d 50
K1_Y = 44465                                  # ось трубопровода К1-1 в пом. 134
TEE = (20873, K1_Y)                           # тройник 110/50×45°
D50 = [DOWN, (20673, 43850), (20673, 44265), TEE]
WALL3 = 21523                                 # внутренняя грань наружной стены по оси 3
DX4 = 97260


def txt(msp, s, x, y, h, layer='Текст', style='GOST', align=TA.BOTTOM_LEFT, rot=0.0, color=256):
    t = msp.add_text(s, dxfattribs={'layer': layer, 'style': style, 'height': h, 'rotation': rot, 'color': color})
    t.set_placement((x, y), align=align)
    return t


def line(msp, a, b, layer, **kw):
    return msp.add_line(a, b, dxfattribs=dict(layer=layer, **kw))


def pline(msp, pts, layer, closed=False, **kw):
    return msp.add_lwpolyline(pts, close=closed, dxfattribs=dict(layer=layer, **kw))


def rect(msp, x0, y0, x1, y1, layer, **kw):
    return pline(msp, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, closed=True, **kw)


def hatch(msp, pts, layer, pattern, scale, angle=0.0, color=256):
    h = msp.add_hatch(color=color, dxfattribs={'layer': layer})
    if pattern == 'SOLID':
        h.set_solid_fill(color=color)
    else:
        h.set_pattern_fill(pattern, scale=scale, angle=angle, color=color)
    h.paths.add_polyline_path(pts, is_closed=True)
    return h


def mtext_insert(e, marker, add):
    """Вставить текст add в MTEXT после первого вхождения marker (по исходному тексту с кодами)."""
    s = e.text
    i = s.index(marker) + len(marker)
    e.text = s[:i] + add + s[i:]


def mtext_replace(e, old, new):
    assert e.text.count(old) == 1, (old, e.text[:80])
    e.text = e.text.replace(old, new)


def find_text(msp, pred):
    out = [e for e in msp.query('TEXT MTEXT') if pred(e.plain_text() if e.dxftype() == 'MTEXT' else e.dxf.text)]
    return out


def one(lst):
    assert len(lst) == 1, [(e.dxftype(), e.dxf.insert) for e in lst]
    return lst[0]


def move_region(msp, x0, y0, x1, y1, dy, keep=()):
    """Сдвинуть по y все объекты, рамка которых целиком в прямоугольнике."""
    n = 0
    for e in list(msp):
        if e in keep:
            continue
        try:
            b = bbox.extents([e], fast=True)
        except Exception:
            continue
        if b.has_data and b.extmin.x >= x0 and b.extmax.x <= x1 and b.extmin.y >= y0 and b.extmax.y <= y1:
            e.translate(0, dy, 0)
            n += 1
    return n


def save(doc, name):
    doc.saveas(os.path.join(DST, name))
    print('saved', name)


# ======================================================================================================================
# Лист 1 — общие данные
def sheet1():
    name = '140-1-2026-VK-list1.dxf'
    doc = ezdxf.readfile(os.path.join(SRC, name))
    msp = doc.modelspace()
    c1 = one([e for e in msp.query('MTEXT') if round(e.dxf.insert.x) == 25])
    c2 = one([e for e in msp.query('MTEXT') if round(e.dxf.insert.x) == 214])
    mtext_replace(c1, 'К1 — канализация бытовая.\\P',
                  'К1 — канализация бытовая; К1Н — канализация бытовая напорная (от дренажного насоса Н2).\\P')
    mtext_replace(c2, 'отводные трубопроводы — в конструкции пола и за облицовкой.\\P',
                  'отводные трубопроводы — в конструкции пола и за облицовкой.\\P'
                  '3.8 Для опорожнения систем В1, Т3, Т4, систем отопления и ИТП (разделы ОВ, ИТП) в котельной '
                  '(пом. 134) предусмотрен дренажный приямок 600×600 мм глубиной 600 мм с погружным насосом Н2 '
                  '(поз. 97), включаемым поплавковым выключателем (узел 5, лист 4). Стоки отводятся напорным '
                  'трубопроводом К1Н через обратный клапан и петлю на отм. +0,700 в трубопровод К1-1. Слив — '
                  'шлангами от спускных кранов с расходом не более 3 м³/ч, температура сбрасываемой воды — не выше '
                  '40 °С. Теплоноситель на основе гликолей в канализацию не сбрасывается.\\P')
    row = one(find_text(msp, lambda t: t == 'Система К1. План 1 этажа. План 2 этажа'))
    row.text = 'Система К1. План 1 этажа. План 2 этажа. Узел 5'
    # условные обозначения: строка К1Н после К1, гильза — ниже на строку
    assert move_region(msp, 400, 133.5, 545, 138.5, -6) == 3
    line(msp, (406, 136), (417.6, 136), 'К1', lineweight=35)
    line(msp, (426.4, 136), (438, 136), 'К1', lineweight=35)
    txt(msp, 'К1Н', 422, 136, 2.5, align=TA.MIDDLE_CENTER)
    txt(msp, '— Трубопровод напорной канализации от дренажного насоса Н2', 442, 136, 2.5, align=TA.MIDDLE_LEFT)
    save(doc, name)


# ======================================================================================================================
# Лист 4 — план К1, узел 5
F = 3.0                    # узел: единиц модели на 1 мм натуры (на листе А1 около 1:27,5)
X0 = 96542                 # левый край внешней рамки листа 4


def plan_pit(msp, dx, layer_out, layer_in, hatch_walls=True, hatch_layer='Штриховка'):
    x0, y0, x1, y1 = PIT_OUT
    a0, b0, a1, b1 = PIT_IN
    rect(msp, x0 + dx, y0, x1 + dx, y1, layer_out)
    rect(msp, a0 + dx, b0, a1 + dx, b1, layer_in)
    if hatch_walls:
        h = msp.add_hatch(dxfattribs={'layer': hatch_layer})
        h.set_pattern_fill('AR-CONC', scale=2.0)
        h.paths.add_polyline_path([(x0 + dx, y0), (x1 + dx, y0), (x1 + dx, y1), (x0 + dx, y1)], is_closed=True,
                                  flags=1)
        h.paths.add_polyline_path([(a0 + dx, b0), (a1 + dx, b0), (a1 + dx, b1), (a0 + dx, b1)], is_closed=True,
                                  flags=0)


def sheet4():
    name = '140-1-2026-VK-list4.dxf'
    doc = ezdxf.readfile(os.path.join(SRC, name))
    msp = doc.modelspace()
    dx = DX4

    # --- план: приямок, насос, К1Н, d 50 ----------------------------------------------------------------------------
    plan_pit(msp, dx, 'Узлы', 'Узлы')
    a0, b0, a1, b1 = PIT_IN
    line(msp, (a0 + dx, b0), (a1 + dx, b1), 'Тонкие')                 # решетка — тонкими диагоналями
    line(msp, (a0 + dx, b1), (a1 + dx, b0), 'Тонкие')
    px, py = PUMP[0] + dx, PUMP[1]
    msp.add_circle((px, py), 120, dxfattribs={'layer': 'К1'})       # насос Н2
    pline(msp, [(px, py - 120), (px + 104, py + 60), (px - 104, py + 60)], 'К1', closed=True)
    pline(msp, [(PUMP[0] + dx, PUMP[1] + 120), (DOWN[0] + dx, DOWN[1])], 'К1')             # К1Н — петля над полом
    pline(msp, [(x + dx, y) for x, y in D50], 'К1')                                        # d 50 в конструкции пола
    # марка трубопровода К1Н и d 50
    txt(msp, 'К1Н', DOWN[0] + dx + 50, 43715, 150, layer='Text', style='ISOCPEUR')
    # выноска приямка — во двор за стеной по оси 3
    tx, ty = 22650, 44080
    sh = max(tw(t, 150) for t in ('Приямок 600×600, h = 600 мм', 'насос дренажный Н2 (поз. 97)',
                                   'К1Н — петля на отм. +0,700; узел 5')) + 120
    lx, ly = PIT_OUT[2] - 100, PIT_OUT[3] - 300
    msp.add_circle((lx + dx, ly), 29, dxfattribs={'layer': 'Text'})
    pline(msp, [(lx + dx, ly), (tx + dx, ty), (tx + dx + sh, ty)], 'Text')
    txt(msp, 'Приямок 600×600, h = 600 мм', tx + dx + 40, ty + 50, 150, layer='Text', style='ISOCPEUR')
    txt(msp, 'насос дренажный Н2 (поз. 97)', tx + dx + 40, ty - 230, 150, layer='Text', style='ISOCPEUR')
    txt(msp, 'К1Н — петля на отм. +0,700; узел 5', tx + dx + 40, ty - 460, 150, layer='Text', style='ISOCPEUR')
    # d 50 к тройнику
    txt(msp, 'd 50', 19570 + dx, 44030, 150, layer='Text', style='ISOCPEUR')
    pline(msp, [(19540 + dx, 44000), (20005 + dx, 44000), (20673 + dx, 44100)], 'Text')

    # --- условное обозначение К1Н -------------------------------------------------------------------------------------
    yl = 21250
    line(msp, (2542 + X0, yl + 125), (3300 + X0, yl + 125), 'К1')
    line(msp, (3960 + X0, yl + 125), (4645 + X0, yl + 125), 'К1')
    txt(msp, 'К1Н', 3365 + X0, yl, 250, layer='Text', style='ISOCPEUR')
    txt(msp, 'напорный трубопровод от дренажного насоса Н2', 4705 + X0, yl + 12, 250, layer='Text', style='ISOCPEUR')

    # --- примечания 7–9 -----------------------------------------------------------------------------------------------
    notes = one([e for e in msp.query('MTEXT') if e.plain_text().startswith('Примечания') is False
                 and e.plain_text().startswith('1. Трубопроводы отнесены')])
    notes.text = notes.text.rstrip() + (
        '\\P7. Дренажный приямок в котельной (пом. 134) — узел 5: монолитный железобетонный, бетон B20 W6 F150, '
        'армирование — сетка из арматуры Ø8 А500С с шагом 150 мм, стенки и днище 200 мм, внутренние размеры '
        '600×600 мм, глубина 600 мм; гидроизоляция внутренних поверхностей обмазочная в два слоя. Проем в '
        'конструкции пола — по заданию 140-1/2026-ВК.ТЗ-1, поз. 38.'
        '\\P8. Насос Н2 (поз. 97) включается поплавковым выключателем. Напорный трубопровод К1Н — с разъемным '
        'соединителем, обратным клапаном и краном шаровым над решеткой, с петлей на отм. +0,700; присоединяется '
        'к трубопроводу К1-1 трубой d 50 через переходную манжету и косой тройник 110/50×45°. Трубопровод '
        'крепится к стене по оси 3 хомутами на кронштейнах. Электропитание — по заданию ТЗ-2 (раздел ЭОМ).'
        '\\P9. Слив систем В1, Т3, Т4 и систем отопления — шлангами от спускных кранов в приямок с расходом не более '
        '3 м³/ч; температура сбрасываемой воды — не выше 40 °С. Теплоноситель на основе гликолей в канализацию '
        'не сбрасывается.')

    # --- штамп ---------------------------------------------------------------------------------------------------------
    st = one([e for e in msp.query('MTEXT') if 'Система К1. План 1 этажа. План 2 этажа' in e.text])
    st.text = st.text.replace('Система К1. План 1 этажа. План 2 этажа', 'Система К1. План 1 этажа. План 2 этажа. Узел 5')

    node5(msp)
    save(doc, name)


def node5(msp):
    Xc, Yc = X0 + 9700, 8390

    def P(u, z):
        return (Xc + u * F, Yc + z * F)

    def R(u0, z0, u1, z1, layer, **kw):
        return rect(msp, *P(u0, z0), *P(u1, z1), layer, **kw)

    def L(a, b, layer='Узлы', **kw):
        return line(msp, P(*a), P(*b), layer, **kw)

    def PL(pts, layer='Узлы', closed=False, **kw):
        return pline(msp, [P(*p) for p in pts], layer, closed=closed, **kw)

    def H(pts, pattern, scale, layer='Штриховка', angle=0.0):
        return hatch(msp, [P(*p) for p in pts], layer, pattern, scale, angle)

    # --- грунт, подготовка, пол ------------------------------------------------------------------------------------
    soil_l = [(-900, -1000), (-500, -1000), (-500, -200), (-900, -200)]
    soil_r = [(500, -1000), (1600, -1000), (1600, -200), (500, -200)]
    soil_b = [(-500, -1000), (500, -1000), (500, -900), (-500, -900)]
    for s in (soil_l, soil_r, soil_b):
        H(s, 'EARTH', 20.0, angle=45)
    for u0, u1 in ((-900, -500), (500, 1600)):
        H([(u0, -50), (u1, -50), (u1, 0), (u0, 0)], 'AR-SAND', 3.0)            # стяжка
        H([(u0, -200), (u1, -200), (u1, -150), (u0, -150)], 'AR-CONC', 2.4)     # бетонная подготовка
        H([(u0, -150), (u1, -150), (u1, -50), (u0, -50)], 'INSUL', 18.0)        # ЭППС
        L((u0, 0), (u1, 0))
        for z in (-50, -150, -200):
            L((u0, z), (u1, z), 'Тонкие')
    H([(-500, -900), (500, -900), (500, -800), (-500, -800)], 'GRAVEL', 6.0)    # щебень
    L((-500, -900), (500, -900), 'Тонкие')
    # линии обрыва
    for u in (-900, 1600):
        L((u, 30), (u, -1030), 'Тонкие')

    # --- приямок ---------------------------------------------------------------------------------------------------
    pit = [(-500, 0), (-500, -800), (500, -800), (500, 0), (300, 0), (300, -600), (-300, -600), (-300, 0)]
    PL(pit, closed=True)
    H(pit, 'AR-CONC', 2.4)
    PL([(-290, -35), (-290, -590), (290, -590), (290, -35)], 'Тонкие')       # гидроизоляция
    # рама из уголка и решетка
    for s in (-1, 1):
        ang = [(s * 300, 0), (s * 300, -35), (s * 250, -35), (s * 250, -30), (s * 295, -30), (s * 295, 0)]
        PL(ang, closed=True)
        H(ang, 'SOLID', 1)
    for u0, u1 in ((-295, 70), (130, 295)):            # решетка, вырез под трубопровод
        R(u0, -30, u1, 0, 'Узлы')
        k = u0 + 30
        while k < u1 - 5:
            L((k, -30), (k, 0), 'Тонкие')
            k += 30

    # --- насос -------------------------------------------------------------------------------------------------------
    PL([(0, -600), (200, -600), (200, -585), (0, -585)], closed=True)          # опорная плита
    PL([(15, -585), (185, -585), (185, -330), (15, -330)], closed=True)        # корпус
    PL([(30, -330), (170, -330), (170, -300), (30, -300)], closed=True)        # крышка
    PL([(185, -500), (215, -500), (215, -420), (185, -420)], closed=True)      # поплавковый выключатель

    # --- напорный трубопровод К1Н (PP-R 40) -------------------------------------------------------------------------
    c, r = 100, 20                                       # ось подъемного участка, радиус трубы
    d = 650                                              # ось опуска
    top = 700
    PL([(c - r, -260), (c - r, top + r), (d + r, top + r), (d + r, 190)], 'К1')
    PL([(c + r, -260), (c + r, top - r), (d - r, top - r), (d - r, 190)], 'К1')
    # фасонные части и арматура (снизу вверх)
    R(c - 28, -300, c + 28, -260, 'К1')                                        # муфта НР у насоса
    R(c - 26, 20, c + 26, 60, 'К1')                                            # муфта ВР
    R(c - 32, 60, c + 32, 130, 'К1')                                           # соединитель разъемный
    L((c - 32, 95), (c + 32, 95), 'К1')
    R(c - 14, 130, c + 14, 150, 'К1')                                          # ниппель
    for z0, z1, fill in ((150, 260, True), (280, 390, False)):                 # клапан обратный, кран шаровой
        zm = (z0 + z1) / 2
        t1 = [(c - 32, z0), (c + 32, z0), (c, zm)]
        t2 = [(c - 32, z1), (c + 32, z1), (c, zm)]
        PL(t1, 'К1', closed=True)
        PL(t2, 'К1', closed=True)
        if fill:
            H(t2, 'SOLID', 1, layer='К1')
    R(c - 14, 260, c + 14, 280, 'К1')                                          # ниппель
    msp.add_circle(P(c, 335), 9 * F, dxfattribs={'layer': 'К1'})             # шар крана
    L((c, 335), (c - 75, 335), 'К1')                                           # рукоятка
    R(c - 28, 390, c + 28, 430, 'К1')                                          # муфта НР
    for a, b in (((c - 30, top - 30), (c + 30, top + 30)), ((d - 30, top - 30), (d + 30, top + 30))):
        R(*a, *b, 'К1')                                                         # угольники 90°
    for (u, z) in ((c, 560), (d, 420)):                                       # хомуты на кронштейнах
        R(u - 30, z - 12, u + 30, z + 12, 'Узлы')
    R(375 - 12, top - 30, 375 + 12, top + 30, 'Узлы')
    # манжета 50/40 в раструбе d 50, труба d 50 в конструкции пола, К1-1
    R(d - 25, 150, d + 25, 190, 'Узлы')
    PL([(d - 29, 150), (d - 29, 80), (d - 25, 80)], 'К1')
    PL([(d + 29, 150), (d + 29, 80), (d + 25, 80)], 'К1')
    k1u, k1z = 1265, -90
    PL([(d - 25, 80), (d - 25, k1z - 25), (k1u - 50, k1z - 25)], 'К1')
    PL([(d + 25, 80), (d + 25, k1z + 25), (k1u - 50, k1z + 25)], 'К1')
    msp.add_circle(P(k1u, k1z), 55 * F, dxfattribs={'layer': 'К1'})
    L((k1u - 80, k1z), (k1u + 80, k1z), 'Тонкие')
    L((k1u, k1z - 80), (k1u, k1z + 80), 'Тонкие')

    # --- отметки ----------------------------------------------------------------------------------------------------
    def level(u, z, s, side=-1):
        h = 2.5 * 82.5 / F                               # высота знака 2,5 мм на листе (в мм натуры)
        apex = P(u, z)
        pline(msp, [apex, (apex[0] - h * F * 0.6, apex[1] + h * F), (apex[0] + h * F * 0.6, apex[1] + h * F)],
              'Размеры', closed=True)
        x_end = apex[0] + side * (tw(s, 206) + 150)
        line(msp, (apex[0], apex[1] + h * F), (x_end, apex[1] + h * F), 'Размеры')
        x_t = min(apex[0], x_end) + 60
        txt(msp, s, x_t, apex[1] + h * F + 50, 206)
    level(330, 0, '0,000', side=1)
    level(c - 20, top + 20, '+0,700')
    level(-5, -600, '-0,600')

    # --- размеры (горизонтальная цепочка под приямком) ---------------------------------------------------------------
    zd = -1130
    for u in (-500, -300, 300, 500):
        L((u, -905), (u, zd - 30), 'Размеры')
    L((-560, zd), (560, zd), 'Размеры')
    for u in (-500, -300, 300, 500):
        x, y = P(u, zd)
        line(msp, (x - 70, y - 70), (x + 70, y + 70), 'Размеры', lineweight=35)
    for u0, u1, s in ((-500, -300, '200'), (-300, 300, '600'), (300, 500, '200')):
        x, y = P((u0 + u1) / 2, zd)
        txt(msp, s, x, y + 50, 206, align=TA.BOTTOM_CENTER)
    # вертикальная цепочка у северной стенки
    ud = 570
    for z in (0, -600, -800, -900):
        L((500, z), (ud + 30, z), 'Размеры')
    L((ud, 30), (ud, -930), 'Размеры')
    for z in (0, -600, -800, -900):
        x, y = P(ud, z)
        line(msp, (x - 70, y - 70), (x + 70, y + 70), 'Размеры', lineweight=35)
    for z0, z1, s in ((0, -600, '600'), (-600, -800, '200'), (-800, -900, '100')):
        x, y = P(ud, (z0 + z1) / 2)
        txt(msp, s, x + 60, y, 206, align=TA.MIDDLE_LEFT)

    # --- выноски ------------------------------------------------------------------------------------------------------
    H_L = 165
    x_left = X0 + 1800
    x_right = P(1750, 0)[0]
    left_end = P(-950, 0)[0]
    lim_l = left_end - x_left - 80
    lim_r = X0 + 23200 - x_right - 80

    def lab_left(target, z, s):
        assert tw(s, H_L) <= lim_l, (s, tw(s, H_L), lim_l)
        y = P(0, z)[1]
        tx, ty = P(*target)
        msp.add_circle((tx, ty), 29, dxfattribs={'layer': 'Текст'})
        pline(msp, [(tx, ty), (left_end, y), (x_left, y)], 'Текст')
        txt(msp, s, x_left + 40, y + 50, H_L)

    def lab_right(target, z, s):
        assert tw(s, H_L) <= lim_r, (s, tw(s, H_L), lim_r)
        y = P(0, z)[1]
        tx, ty = P(*target)
        msp.add_circle((tx, ty), 29, dxfattribs={'layer': 'Текст'})
        x_end = x_right + tw(s, H_L) + 120
        pline(msp, [(tx, ty), (x_right, y), (x_end, y)], 'Текст')
        txt(msp, s, x_right + 40, y + 50, H_L)

    lab_left((c - 32, 335), 470, 'Кран шаровой Ду 32 (поз. 99)')
    lab_left((c - 32, 205), 340, 'Клапан обратный шаровой Ду 32 (поз. 98)')
    lab_left((c - 32, 95), 210, 'Соединитель разъемный G1¼" (поз. 100)')
    lab_left((-200, -15), 80, 'Решетка на раме из уголка 50×5 (поз. 112)')
    lab_left((-700, -100), -90, 'Пол: стяжка 50, ЭППС 100, подготовка 50 мм')
    lab_left((15, -450), -250, 'Насос Н2, поплавковый выключатель (поз. 97)')
    lab_left((-400, -400), -400, 'Бетон B20 W6 F150, сетка Ø8 А500С/150')
    lab_left((-290, -540), -540, 'Гидроизоляция обмазочная, 2 слоя')
    lab_left((-420, -850), -720, 'Щебень фр. 20–40 мм, 100 мм')
    lab_right((380, top + r), 860, 'Трубопровод К1Н PP-R 40×6,7 (поз. 104), угольники (поз. 105)')
    lab_right((d + 30, 420), 690, 'Хомут на кронштейне, крепление к стене по оси 3 (поз. 106)')
    lab_right((d + 25, 170), 300, 'Манжета переходная d 50/40 (поз. 107)')
    lab_right((d + 25, 20), 120, 'Труба ПП d 50 (поз. 108), i = 0,03')
    lab_right((k1u + 40, k1z - 40), -320, 'Трубопровод К1-1 d 110, тройник 110/50×45° (поз. 111), см. план')
    lab_right((1100, -560), -600, 'Грунт')

    # --- заголовок ----------------------------------------------------------------------------------------------------
    xt = P(350, 0)[0]
    txt(msp, 'Узел 5', xt, Yc + 1010 * F + 380, 289, align=TA.BOTTOM_CENTER)
    txt(msp, 'Дренажный приямок в котельной (пом. 134). Разрез вдоль стены по оси 3', xt, Yc + 1010 * F, 206,
        align=TA.BOTTOM_CENTER)
    txt(msp, 'Размеры — в мм, отметки — в м', P(0, 0)[0], Yc - 1250 * F, 165, align=TA.TOP_CENTER)


# ======================================================================================================================
# Лист 5 — схема К1: тройник 110/50×45° на К1-1 и ответвление от насоса Н2
def sheet5():
    name = '140-1-2026-VK-list5.dxf'
    doc = ezdxf.readfile(os.path.join(SRC, name))
    msp = doc.modelspace()
    y0 = -22780
    xt = 110500
    ux, uy = 5326, 3602
    n = math.hypot(ux, uy)
    ux, uy = ux / n, uy / n
    L = 1200
    end = (xt - ux * L, y0 - uy * L)
    line(msp, (xt, y0), end, 'К1')
    for x in (xt - 167, xt + 167):                                    # раструбы тройника
        line(msp, (x, y0 - 80), (x, y0 + 80), 'К1')
    bx, by = xt - ux * 200, y0 - uy * 200
    line(msp, (bx - uy * 80, by + ux * 80), (bx + uy * 80, by - ux * 80), 'К1')
    # подъем d 50 к манжете и подпись
    line(msp, end, (end[0], end[1] + 300), 'К1')
    line(msp, (end[0] - 80, end[1] + 300), (end[0] + 80, end[1] + 300), 'К1')
    txt(msp, '111-Тройник 110/50×45', 110040, -22262, 150, layer='Text', style='ISOCPEUR')
    pline(msp, [(xt, y0), (110000, -22300), (110000 + tw('111-Тройник 110/50×45', 150) + 80, -22300)], 'Text')
    s1, s2 = 'К1Н от дренажного насоса Н2', 'узел 5, лист 4'
    w = tw(s1, 150)
    x1 = end[0] - 60
    pline(msp, [(end[0], end[1] + 150), (x1, -23560), (x1 - w - 80, -23560)], 'Text')
    txt(msp, s1, x1 - w - 40, -23522, 150, layer='Text', style='ISOCPEUR')
    txt(msp, s2, x1 - w - 40, -23790, 150, layer='Text', style='ISOCPEUR')
    save(doc, name)


# ======================================================================================================================
# ТЗ-1 — проем под приямок (поз. 38)
def tz1():
    name = '140-1-2026-VK-TZ1.dxf'
    doc = ezdxf.readfile(os.path.join(SRC, name))
    msp = doc.modelspace()
    # план
    x0, y0, x1, y1 = PIT_OUT
    rect(msp, x0, y0, x1, y1, 'Отверстия')
    line(msp, (x0, y0), (x1, y1), 'Отверстия')
    line(msp, (x0, y1), (x1, y0), 'Отверстия')
    a0, b0, a1, b1 = PIT_IN
    rect(msp, a0, b0, a1, b1, 'Отверстия', linetype='DASHED', ltscale=4.0)
    cx, cy = 19907, 42850
    msp.add_circle((cx, cy), 181, dxfattribs={'layer': 'Отверстия_выноски'})
    txt(msp, '38', cx, cy, 190, layer='Отверстия_выноски', align=TA.MIDDLE_CENTER)
    txt(msp, '1000×1000', cx - 236, cy, 206, layer='Отверстия_выноски', align=TA.MIDDLE_RIGHT)
    pline(msp, [(cx + 181, cy), ((x0 + x1) / 2 - 300, (y0 + y1) / 2)], 'Отверстия_выноски')
    msp.add_circle(((x0 + x1) / 2 - 300, (y0 + y1) / 2), 29, dxfattribs={'layer': 'Отверстия_выноски'})

    # ведомость: строка 38 (таблица 1344…21557, строки по 429 вниз от 26216, низ 10344)
    rh = 429
    yb = 10344
    tb = one([e for e in msp.query('LWPOLYLINE') if e.dxf.layer == 'Таблицы'
              and [(round(p[0]), round(p[1])) for p in e.get_points()][0] == (1344, 10344)])
    keep = {tb}
    for e in msp.query('LINE'):
        if e.dxf.layer == 'Таблицы' and round(e.dxf.end.y) == yb and round(e.dxf.start.y) == 26959:
            keep.add(e)
    # сдвиг примечаний вниз на строку
    moved = move_region(msp, 1300, 4300, 22000, yb - 1, -rh, keep=keep)
    print('ТЗ-1: сдвинуто объектов', moved)
    pts = [(p[0], p[1]) for p in tb.get_points()]
    tb.set_points([(x, y - rh if round(y) == yb else y) for x, y in pts], format='xy')
    tb.close(True)
    for e in keep:
        if e.dxftype() == 'LINE':
            e.dxf.end = (e.dxf.end.x, yb - rh, 0)
    ln = line(msp, (1344, yb), (21557, yb), 'Таблицы', lineweight=18)
    assert ln
    # тексты строки — копии строки 37
    ym = yb - rh / 2
    row37 = [e for e in msp.query('MTEXT') if abs(e.dxf.insert.y - (yb + rh / 2)) < 2 and e.dxf.insert.x < 22000]
    assert len(row37) == 5, len(row37)
    vals = {1716: '38', 2912: '1000×1000', 3836: 'Конструкция пола 1 этажа, пом. 134', 9636: '-0,900',
            10353: 'дренажный приямок: монолитный ж/б, в свету 600×600 мм, глубина 600 мм (узел 5 ВК)'}
    for e in row37:
        k = round(e.dxf.insert.x)
        ne = e.copy()
        ne.text = vals[k]
        ne.dxf.insert = (e.dxf.insert.x, ym, 0)
        msp.add_entity(ne)
    # примечание 8
    notes = one([e for e in msp.query('MTEXT') if e.plain_text().startswith('1. Задание разделам АР и КР')])
    notes.text = notes.text.rstrip() + (
        '\\P8. Проем поз. 38 — под дренажный приямок котельной: монолитный железобетонный, стенки и днище 200 мм, '
        'бетон B20 W6 F150 (узел 5 листа 4 ВК; устройство приямка учтено в ВОР раздела ВК). Приямок — у наружной '
        'стены по оси 3 с зазором 100 мм от ее внутренней грани; при выступе фундамента внутрь помещения приямок '
        'смещается в сторону помещения по согласованию с КР. Положение проверить по размещению оборудования '
        'котельной (разделы ОВ, ИТП).')
    # условное обозначение
    yc = 25335 - 537
    rect(msp, 62394, yc - 124, 62890, yc + 124, 'Отверстия')
    line(msp, (62394, yc - 124), (62890, yc + 124), 'Отверстия')
    line(msp, (62394, yc + 124), (62890, yc - 124), 'Отверстия')
    rect(msp, 62542, yc - 70, 62742, yc + 70, 'Отверстия')
    tmpl = one([e for e in msp.query('TEXT') if e.dxf.text == 'позиция по ведомости и размер'])
    nt = tmpl.copy()
    nt.dxf.text = 'проем в конструкции пола (приямок)'
    nt.translate(0, -537, 0)
    msp.add_entity(nt)
    save(doc, name)


# ======================================================================================================================
# ТЗ-2 — насос Н2
def tz2():
    name = '140-1-2026-VK-TZ2.dxf'
    doc = ezdxf.readfile(os.path.join(SRC, name))
    msp = doc.modelspace()
    # точка подключения на плане
    px, py = PUMP
    h = msp.add_hatch(color=1, dxfattribs={'layer': 'Электро'})
    h.set_solid_fill(color=1)
    h.paths.add_edge_path().add_arc((px, py), 170, 0, 360)
    sx, sy = 22800, 44300
    pline(msp, [(px + 120, py + 120), (sx, sy), (sx + 7600, sy)], 'Электро', color=256)
    txt(msp, 'Н2 — насос дренажный в приямке котельной (К1Н)', sx + 80, sy + 182, 231, align=TA.MIDDLE_LEFT)
    txt(msp, '1×230 В, 50 Гц, Р не более 0,4 кВт, автоматический режим', sx + 80, sy - 215, 206,
        align=TA.MIDDLE_LEFT)
    # таблица: строка Н2 (рамка 24032…53732, строка 990 вниз от 23659)
    rh = 990
    yb = 23659
    tb = one([e for e in msp.query('LWPOLYLINE') if e.dxf.layer == 'Таблицы'])
    vlines = [e for e in msp.query('LINE') if e.dxf.layer == 'Таблицы' and round(e.dxf.end.y) == yb
              and round(e.dxf.start.y) == 25474]
    assert len(vlines) == 7, len(vlines)
    keep = {tb, *vlines}
    moved = move_region(msp, 23500, 16000, 55000, yb - 1, -rh, keep=keep)
    print('ТЗ-2: сдвинуто объектов', moved)
    tb.set_points([(x, y - rh if round(y) == yb else y) for x, y in [(p[0], p[1]) for p in tb.get_points()]],
                  format='xy')
    tb.close(True)
    for e in vlines:
        e.dxf.end = (e.dxf.end.x, yb - rh, 0)
    ym = yb - rh / 2
    row = [e for e in msp.query('MTEXT') if round(e.dxf.insert.y) == 24154]
    assert len(row) == 8, len(row)
    vals = {24610: 'Н2', 25286: 'Насос дренажный погружной в приямке (К1Н): Q = 3 м³/ч, Н не менее 3 м, '
            'поплавковый выключатель', 35582: '134 (котельная)', 37397: '1', 39047: '1×230, 50 Гц',
            41192: 'не более 0,4', 43667: 'автоматический, по уровню в приямке',
            45251: 'мощность — по паспорту выбранного насоса (поз. 97 ВК.СО); розетка IP44, УЗО 30 мА'}
    for e in row:
        ne = e.copy()
        ne.text = vals[round(e.dxf.insert.x)]
        ne.dxf.insert = (e.dxf.insert.x, ym, 0)
        msp.add_entity(ne)
    notes = one([e for e in msp.query('MTEXT') if e.plain_text().startswith('1. Задание разделу ЭОМ')])
    mtext_replace(notes, '2. Насос Н1 подключить отдельной группой; место подключения — розетка',
                  '2. Насосы Н1 и Н2 подключить отдельными группами. Н1 — розетка')
    mtext_replace(notes, 'Защитные аппараты — по решению ЭОМ.',
                  'Н2 — розетка с заземляющим контактом со степенью защиты не ниже IP44 на стене по оси 3 у приямка, '
                  'на высоте не менее 1,0 м от пола; группа — с устройством защитного отключения (УЗО) с током '
                  'срабатывания 30 мА. Защитные аппараты — по решению ЭОМ.')
    save(doc, name)


sheet1()
sheet4()
sheet5()
tz1()
tz2()
