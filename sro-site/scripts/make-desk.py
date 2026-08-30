#!/usr/bin/env python3
"""Фон секции заявки: рабочий стол сверху — чертежи, каска, блокнот, ручка.

Заказчик показал макет именно с этой сценой. Своей фотографии под неё нет, а
скачать неоткуда: фотостоки закрыты егресс-политикой среды. Поэтому сцена
нарисована.

Почему это вообще получается линиями. Вид сверху убирает светотень: с этой
точки каска, блокнот и рулон — плоские фигуры, а чертёж и подавно. Именно
поэтому сцена берётся сверху, а не с угла, как на макете: угол потребовал бы
объёма, которого построение не даёт.

Композиция считается от карточки квиза: она лежит по центру и закрывает
примерно среднюю треть по ширине. Поэтому все предметы разнесены по краям —
чертёж и рулон слева, каска и блокнот справа, — и в готовой секции видно не
обрезки, а целые объекты.

Линии белые, плотность задаётся в разметке: так один файл годится под любую
тёмную подложку.
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
add(f'<rect x="{n(LX)}" y="{n(LY)}" width="{n(LW)}" height="{n(LH)}" stroke-width="2.4"/>')
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
add(f'<ellipse cx="{n(RX)}" cy="{n(RY)}" rx="13" ry="{n(RR)}"/>')
add(f'<ellipse cx="{n(RX + RL)}" cy="{n(RY)}" rx="13" ry="{n(RR)}" opacity="0.6"/>')
add(f'<path d="M{n(RX - 4)} {n(RY - 16)} A 9 16 0 0 0 {n(RX - 4)} {n(RY + 16)}" stroke-width="1.4" opacity="0.7"/>')
add('</g>')

# --------------------------------------------------------------------- КАСКА
# Справа сверху, вид сверху: овал купола, продольный гребень, козырёк.
HX, HY = 1280, 250
add(f'<g transform="rotate(12 {n(HX)} {n(HY)})">')
add(f'<ellipse cx="{n(HX)}" cy="{n(HY)}" rx="132" ry="106" stroke-width="2.6"/>')
add(f'<ellipse cx="{n(HX)}" cy="{n(HY)}" rx="108" ry="84" stroke-width="1.3" opacity="0.5"/>')
# Козырёк. Концы дуги посажены НА овал (x=±112 при rx=132 даёт y=HY+56), а
# вершина выведена за его нижнюю кромку: иначе дуга идёт внутри купола и
# каска читается миской, а не каской.
add(f'<path d="M{n(HX - 112)} {n(HY + 56)} Q{n(HX)} {n(HY + 182)} {n(HX + 112)} {n(HY + 56)}" stroke-width="2.4"/>')
add(f'<path d="M{n(HX - 92)} {n(HY + 62)} Q{n(HX)} {n(HY + 158)} {n(HX + 92)} {n(HY + 62)}" stroke-width="1.3" opacity="0.55"/>')
# Продольный гребень жёсткости
add(f'<path d="M{n(HX)} {n(HY - 104)} L{n(HX)} {n(HY + 88)}" stroke-width="2"/>')
add(f'<path d="M{n(HX - 17)} {n(HY - 96)} L{n(HX - 17)} {n(HY + 80)}" stroke-width="1.2" opacity="0.6"/>')
add(f'<path d="M{n(HX + 17)} {n(HY - 96)} L{n(HX + 17)} {n(HY + 80)}" stroke-width="1.2" opacity="0.6"/>')
# Вентиляционные прорези
for s in (-1, 1):
    for i in range(3):
        y = HY - 44 + i * 34
        add(f'<line x1="{n(HX + s * 56)}" y1="{n(y)}" x2="{n(HX + s * 82)}" y2="{n(y)}" stroke-width="1.4" opacity="0.65"/>')
add('</g>')

# ------------------------------------------------------------------- БЛОКНОТ
# Справа снизу: блокнот на пружине со строками.
BX, BY, BW, BH = 1150, 560, 330, 290
add(f'<g transform="rotate(-8 {n(BX + BW / 2)} {n(BY + BH / 2)})">')
add(f'<rect x="{n(BX)}" y="{n(BY)}" width="{n(BW)}" height="{n(BH)}" rx="6" stroke-width="2.4"/>')
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
add(f'<rect x="{n(PX)}" y="{n(PY - 11)}" width="{n(PL - 46)}" height="22" rx="8"/>')
add(f'<path d="M{n(PX + PL - 46)} {n(PY - 11)} L{n(PX + PL)} {n(PY)} L{n(PX + PL - 46)} {n(PY + 11)} Z"/>')
add(f'<line x1="{n(PX + PL - 14)}" y1="{n(PY)}" x2="{n(PX + PL)}" y2="{n(PY)}" stroke-width="1.4"/>')
add(f'<rect x="{n(PX + 22)}" y="{n(PY - 20)}" width="10" height="40" rx="4" stroke-width="1.4" opacity="0.75"/>')
add('</g>')

# ------------------------------------------------------------------ ЛИНЕЙКА
# Внизу по центру-слева: масштабная линейка с делениями.
SX, SY, SL = 560, 830, 300
add(f'<g transform="rotate(9 {n(SX)} {n(SY)})" stroke-width="2">')
add(f'<rect x="{n(SX)}" y="{n(SY - 20)}" width="{n(SL)}" height="40" rx="3"/>')
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
out = Path('public/img/desk.svg')
out.write_text(svg, encoding='utf-8')
print(f'{out}: {len(svg) / 1024:.1f} КБ')
