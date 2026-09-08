#!/usr/bin/env python3
"""Фон секции заявки: рабочий стол сверху — чертежи, каска, блокнот, ручка.

НА СТРАНИЦЕ ЭТОТ РИСУНОК НЕ СТОИТ. Он делался, пока своей фотографии под
сцену не было, а скачать её было неоткуда: фотостоки закрыты егресс-политикой
среды. Потом заказчик прислал кадр через репозиторий, и фон секции заявки —
фотография (`public/img/desk.webp`). Рисунок и генератор оставлены на случай,
если от фотографии придётся отказаться: возврат — одна строка в `Quiz.tsx`
плюс плёнка, см. комментарий там.

Почему это вообще получается линиями. Вид сверху убирает светотень: с этой
точки блокнот, линейка и рулон — плоские фигуры, а чертёж и подавно. Поэтому
сцена берётся сверху, а не с угла, как на макете: угол потребовал бы объёма,
которого построение не даёт. Каска — единственное исключение, она в профиль:
сверху она овал в овале и не опознаётся (подробности у самого предмета).

Композиция считается от карточки квиза: она лежит по центру и закрывает
примерно среднюю треть по ширине. Поэтому все предметы разнесены по краям —
чертёж и рулон слева, каска и блокнот справа, — и в готовой секции видно не
обрезки, а целые объекты.

Линии белые, плотность задаётся в разметке: так один файл годится под любую
тёмную подложку.

Предметы не только обведены, но и залиты полупрозрачным белым — разной
плотности у разных граней. На тёмном фоне это работает как свет: залитая грань
читается освещённой, и предмет перестаёт быть чертежом самого себя. Тени для
этого не годятся — на тёмно-синем их попросту не видно.
"""

from math import cos, radians, sin
from pathlib import Path

W, H = 1600, 900
parts: list[str] = []
add = parts.append


def n(v: float) -> str:
    return f'{v:.1f}'.rstrip('0').rstrip('.')


def rot(x: float, y: float, cx: float, cy: float, deg: float) -> tuple[float, float]:
    a = radians(deg)
    dx, dy = x - cx, y - cy
    return cx + dx * cos(a) - dy * sin(a), cy + dx * sin(a) + dy * cos(a)


# ---------------------------------------------------------------- ЛИСТ ЧЕРТЕЖА
# Слева: развёрнутый лист с планом. Повёрнут на 6° — лист, брошенный на стол,
# не лежит по линейке.
LX, LY, LW, LH = 90, 210, 620, 520
add(f'<g transform="rotate(-6 {n(LX + LW / 2)} {n(LY + LH / 2)})">')
add(f'<rect x="{n(LX)}" y="{n(LY)}" width="{n(LW)}" height="{n(LH)}" stroke-width="2.4" fill="#fff" fill-opacity="0.10"/>')
add(f'<rect x="{n(LX + 16)}" y="{n(LY + 16)}" width="{n(LW - 32)}" height="{n(LH - 32)}" stroke-width="1" opacity="0.5"/>')

# План на листе: наружные стены двойной линией, перегородки, проёмы.
px, py, pw, ph = LX + 70, LY + 80, LW - 190, LH - 210
add(f'<g stroke-width="2.2">')
add(f'<rect x="{n(px)}" y="{n(py)}" width="{n(pw)}" height="{n(ph)}"/>')
add(f'<rect x="{n(px + 11)}" y="{n(py + 11)}" width="{n(pw - 22)}" height="{n(ph - 22)}"/>')
add('</g>')
add('<g stroke-width="1.6" opacity="0.85">')
add(f'<line x1="{n(px + pw * 0.42)}" y1="{n(py + 11)}" x2="{n(px + pw * 0.42)}" y2="{n(py + ph - 11)}"/>')
add(f'<line x1="{n(px + 11)}" y1="{n(py + ph * 0.55)}" x2="{n(px + pw * 0.42)}" y2="{n(py + ph * 0.55)}"/>')
add(f'<line x1="{n(px + pw * 0.42)}" y1="{n(py + ph * 0.32)}" x2="{n(px + pw - 11)}" y2="{n(py + ph * 0.32)}"/>')
add('</g>')
# Дверные дуги
for dx_, dy_, deg in ((px + pw * 0.42, py + ph * 0.18, 0), (px + pw * 0.20, py + ph * 0.55, 90)):
    d = 46
    add(f'<g transform="translate({n(dx_)},{n(dy_)}) rotate({deg})" stroke-width="1.4" opacity="0.7">'
        f'<line x1="0" y1="0" x2="0" y2="{d}"/><path d="M0 {d} A {d} {d} 0 0 0 {d} 0"/></g>')
# Размерная цепочка над планом
add('<g stroke-width="1.2" opacity="0.55">')
add(f'<line x1="{n(px)}" y1="{n(py - 34)}" x2="{n(px + pw)}" y2="{n(py - 34)}"/>')
for i in range(4):
    x = px + i * pw / 3
    add(f'<line x1="{n(x)}" y1="{n(py - 42)}" x2="{n(x)}" y2="{n(py - 26)}"/>')
add('</g>')
# Основная надпись (штамп) в правом нижнем углу листа
sx, sy, sw, sh = LX + LW - 250, LY + LH - 110, 216, 78
add(f'<g stroke-width="1.4" opacity="0.75"><rect x="{n(sx)}" y="{n(sy)}" width="{n(sw)}" height="{n(sh)}"/>')
for i in (1, 2):
    add(f'<line x1="{n(sx)}" y1="{n(sy + sh * i / 3)}" x2="{n(sx + sw)}" y2="{n(sy + sh * i / 3)}"/>')
add(f'<line x1="{n(sx + sw * 0.62)}" y1="{n(sy)}" x2="{n(sx + sw * 0.62)}" y2="{n(sy + sh)}"/></g>')
add('</g>')

# --------------------------------------------------------------------- РУЛОН
# Слева внизу: свёрнутый в трубку чертёж. Торец — эллипс со спиралью.
RX, RY, RL, RR = 105, 836, 330, 32
add(f'<g transform="rotate(-14 {n(RX)} {n(RY)})" stroke-width="2.2">')
add(f'<line x1="{n(RX)}" y1="{n(RY - RR)}" x2="{n(RX + RL)}" y2="{n(RY - RR)}"/>')
add(f'<line x1="{n(RX)}" y1="{n(RY + RR)}" x2="{n(RX + RL)}" y2="{n(RY + RR)}"/>')
add(f'<ellipse cx="{n(RX)}" cy="{n(RY)}" rx="13" ry="{n(RR)}" fill="#fff" fill-opacity="0.14"/>')
add(f'<ellipse cx="{n(RX + RL)}" cy="{n(RY)}" rx="13" ry="{n(RR)}" opacity="0.6" fill="#fff" fill-opacity="0.08"/>')
add(f'<path d="M{n(RX - 4)} {n(RY - 16)} A 9 16 0 0 0 {n(RX - 4)} {n(RY + 16)}" stroke-width="1.4" opacity="0.7"/>')
add('</g>')

# --------------------------------------------------------------------- КАСКА
# Справа сверху. Единственный предмет сцены не в плане, а в профиль, и это
# осознанно: сверху каска — овал в овале, и её последовательно принимали то за
# миску, то за крышку от банки, то за яйцо. Проверено тремя построениями.
# Узнаваемой каску делает силуэт сбоку: купол и вынесенные вперёд поля. Смена
# ракурса у одного предмета в плоской графике нормальна — так рисуют почти все
# наборы иконок, и разнобоя в сцене не читается.
HX, HY = 1285, 300
add(f'<g transform="rotate(-4 {n(HX)} {n(HY)})">')
# Поля: у каски это не шляпные поля, а короткий козырёк — сзади лишь лип,
# спереди заметный вынос. Толщина обязательна: тонким серпом поля читались
# полем шляпы.
add(
    f'<path d="M{n(HX - 118)} {n(HY - 10)}'
    f' Q{n(HX + 14)} {n(HY + 10)} {n(HX + 142)} {n(HY + 8)}'
    f' L{n(HX + 148)} {n(HY + 20)}'
    f' Q{n(HX + 14)} {n(HY + 32)} {n(HX - 120)} {n(HY)} Z" '
    f'stroke-width="2.2" fill="#fff" fill-opacity="0.11"/>'
)
# Купол: бока у основания почти отвесные, а не полукруг, — иначе котелок.
# Залит плотнее полей: на тёмном это читается как освещённая макушка.
add(
    f'<path d="M{n(HX - 98)} {n(HY + 2)}'
    f' C{n(HX - 102)} {n(HY - 72)} {n(HX - 66)} {n(HY - 116)} {n(HX - 4)} {n(HY - 116)}'
    f' C{n(HX + 58)} {n(HY - 116)} {n(HX + 90)} {n(HY - 72)} {n(HX + 88)} {n(HY + 2)} Z" '
    f'stroke-width="2.6" fill="#fff" fill-opacity="0.15"/>'
)
# Нижняя кромка скорлупы над полями
add(f'<path d="M{n(HX - 94)} {n(HY - 24)} Q{n(HX - 6)} {n(HY - 10)} {n(HX + 84)} {n(HY - 24)}" stroke-width="1.4" opacity="0.55"/>')
# Гребень жёсткости: идёт по макушке, поэтому в профиль виден полосой у верха.
add(f'<path d="M{n(HX - 76)} {n(HY - 58)} C{n(HX - 72)} {n(HY - 100)} {n(HX + 58)} {n(HY - 100)} {n(HX + 62)} {n(HY - 58)}" stroke-width="1.4" opacity="0.5"/>')
# Вентиляционные прорези на боку
for i in range(2):
    x = HX - 26 + i * 40
    add(f'<line x1="{n(x)}" y1="{n(HY - 84)}" x2="{n(x)}" y2="{n(HY - 58)}" stroke-width="1.6" opacity="0.6"/>')
add('</g>')

# ------------------------------------------------------------------- БЛОКНОТ
# Справа снизу: блокнот на пружине со строками.
BX, BY, BW, BH = 1150, 560, 330, 290
add(f'<g transform="rotate(-8 {n(BX + BW / 2)} {n(BY + BH / 2)})">')
add(f'<rect x="{n(BX)}" y="{n(BY)}" width="{n(BW)}" height="{n(BH)}" rx="6" stroke-width="2.4" fill="#fff" fill-opacity="0.11"/>')
add(f'<line x1="{n(BX + 52)}" y1="{n(BY)}" x2="{n(BX + 52)}" y2="{n(BY + BH)}" stroke-width="1.4" opacity="0.6"/>')
# Пружина
add('<g stroke-width="1.8" opacity="0.8">')
for i in range(9):
    y = BY + 20 + i * (BH - 40) / 8
    add(f'<path d="M{n(BX + 16)} {n(y)} A 13 9 0 0 1 {n(BX + 42)} {n(y)}"/>')
add('</g>')
# Строки
add('<g stroke-width="1.2" opacity="0.45">')
for i in range(7):
    y = BY + 46 + i * 32
    add(f'<line x1="{n(BX + 74)}" y1="{n(y)}" x2="{n(BX + BW - 28)}" y2="{n(y)}"/>')
add('</g>')
add('</g>')

# --------------------------------------------------------------------- РУЧКА
# По диагонали поверх блокнота: корпус, конус пера, клип.
PX, PY, PL = 1080, 470, 300
add(f'<g transform="rotate(36 {n(PX)} {n(PY)})" stroke-width="2.2">')
add(f'<rect x="{n(PX)}" y="{n(PY - 11)}" width="{n(PL - 46)}" height="22" rx="8" fill="#fff" fill-opacity="0.16"/>')
add(f'<path d="M{n(PX + PL - 46)} {n(PY - 11)} L{n(PX + PL)} {n(PY)} L{n(PX + PL - 46)} {n(PY + 11)} Z" fill="#fff" fill-opacity="0.16"/>')
add(f'<line x1="{n(PX + PL - 14)}" y1="{n(PY)}" x2="{n(PX + PL)}" y2="{n(PY)}" stroke-width="1.4"/>')
add(f'<rect x="{n(PX + 22)}" y="{n(PY - 20)}" width="10" height="40" rx="4" stroke-width="1.4" opacity="0.75"/>')
add('</g>')

# ------------------------------------------------------------------ ЛИНЕЙКА
# Внизу по центру-слева: масштабная линейка с делениями.
SX, SY, SL = 560, 830, 300
add(f'<g transform="rotate(9 {n(SX)} {n(SY)})" stroke-width="2">')
add(f'<rect x="{n(SX)}" y="{n(SY - 20)}" width="{n(SL)}" height="40" rx="3" fill="#fff" fill-opacity="0.12"/>')
add('<g stroke-width="1.2" opacity="0.6">')
for i in range(1, 15):
    x = SX + i * SL / 15
    long = i % 5 == 0
    add(f'<line x1="{n(x)}" y1="{n(SY - 20)}" x2="{n(x)}" y2="{n(SY - 20 + (26 if long else 15))}"/>')
add('</g></g>')

svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" fill="none" '
    f'stroke="#fff" stroke-linecap="round" stroke-linejoin="round">'
    + ''.join(parts)
    + '</svg>'
)
out = Path('assets-src/desk-drawing.svg')
out.write_text(svg, encoding='utf-8')
print(f'{out}: {len(svg) / 1024:.1f} КБ')
