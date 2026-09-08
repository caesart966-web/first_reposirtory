#!/usr/bin/env python3
"""Фон тёмной секции заявки: план этажа языком рабочего чертежа.

Почему рисуем, а не берём фотографию. Фотостоки из этой среды недоступны, но
дело не только в этом: все три снимка сайта уже заняты карточками видов СРО,
и любой из них в фоне повторял бы карточку, стоящую выше по странице. Нужен
мотив, которого на сайте ещё нет.

План этажа выбран потому, что он узнаётся всеми тремя аудиториями сразу —
строителем, проектировщиком и изыскателем, — и при этом не повторяет ни один
из уже занятых мотивов: разрез здания (карточка проектировщиков), сетку
чертежа (герой), силуэт города (низ этой же секции), весы (фон страницы).

Рисуем генератором, а не руками: план собран из повторяющихся элементов —
оси, проёмы, размерные цепочки, — и в коде их проще держать согласованными,
чем в разметке SVG.

Все линии белые: цвет задаётся прозрачностью в разметке, чтобы один файл
годился под любую тёмную подложку.
"""

W, H = 1600, 900
# Модульная сетка: шаг координационных осей в пикселях.
STEP_X, STEP_Y = 190, 165
X0, Y0 = 250, 170          # левый верхний угол здания
COLS, ROWS = 6, 4          # пролётов по горизонтали и вертикали

LETTERS = 'АБВГДЕ'


def esc(v: float) -> str:
    """Короткая запись координаты: 3 знака хватает, файл легче."""
    return f'{v:.1f}'.rstrip('0').rstrip('.')


parts: list[str] = []
add = parts.append

right = X0 + COLS * STEP_X
bottom = Y0 + ROWS * STEP_Y

# --- Координационные оси: штрихпунктир с кружком и подписью на конце --------
add('<g stroke="#fff" stroke-width="1" opacity="0.5" stroke-dasharray="14 5 3 5">')
for c in range(COLS + 1):
    x = X0 + c * STEP_X
    add(f'<line x1="{esc(x)}" y1="{Y0 - 95}" x2="{esc(x)}" y2="{esc(bottom + 60)}"/>')
for r in range(ROWS + 1):
    y = Y0 + r * STEP_Y
    add(f'<line x1="{X0 - 95}" y1="{esc(y)}" x2="{esc(right + 60)}" y2="{esc(y)}"/>')
add('</g>')

add('<g fill="none" stroke="#fff" stroke-width="1.4" opacity="0.75">')
for c in range(COLS + 1):
    add(f'<circle cx="{esc(X0 + c * STEP_X)}" cy="{Y0 - 118}" r="19"/>')
for r in range(ROWS + 1):
    add(f'<circle cx="{X0 - 118}" cy="{esc(Y0 + r * STEP_Y)}" r="19"/>')
add('</g>')

add('<g fill="#fff" opacity="0.75" font-family="Inter, sans-serif" font-size="17" '
    'text-anchor="middle" dominant-baseline="central">')
for c in range(COLS + 1):
    add(f'<text x="{esc(X0 + c * STEP_X)}" y="{Y0 - 118}">{c + 1}</text>')
for r in range(ROWS + 1):
    add(f'<text x="{X0 - 118}" y="{esc(Y0 + r * STEP_Y)}">{LETTERS[r]}</text>')
add('</g>')

# --- Наружные стены: двойная линия, как на плане ----------------------------
T = 13  # толщина стены
add('<g fill="none" stroke="#fff" stroke-width="2.2" opacity="0.95">')
add(f'<rect x="{esc(X0)}" y="{esc(Y0)}" width="{esc(right - X0)}" height="{esc(bottom - Y0)}"/>')
add(f'<rect x="{esc(X0 + T)}" y="{esc(Y0 + T)}" '
    f'width="{esc(right - X0 - 2 * T)}" height="{esc(bottom - Y0 - 2 * T)}"/>')
add('</g>')

# --- Внутренние перегородки -------------------------------------------------
add('<g fill="none" stroke="#fff" stroke-width="1.6" opacity="0.8">')
walls = [
    (X0 + 2 * STEP_X, Y0 + T, X0 + 2 * STEP_X, bottom - T),
    (X0 + 4 * STEP_X, Y0 + T, X0 + 4 * STEP_X, Y0 + 2 * STEP_Y),
    (X0 + T, Y0 + 2 * STEP_Y, X0 + 2 * STEP_X, Y0 + 2 * STEP_Y),
    (X0 + 4 * STEP_X, Y0 + 2 * STEP_Y, right - T, Y0 + 2 * STEP_Y),
    (X0 + 2 * STEP_X, Y0 + 3 * STEP_Y, right - T, Y0 + 3 * STEP_Y),
]
for x1, y1, x2, y2 in walls:
    add(f'<line x1="{esc(x1)}" y1="{esc(y1)}" x2="{esc(x2)}" y2="{esc(y2)}"/>')
add('</g>')

# --- Дверные проёмы: створка отрезком и четверть-дуга хода ------------------
# (x, y, поворот в градусах) — угол задаёт, куда открывается дверь.
doors = [
    (X0 + 2 * STEP_X, Y0 + 0.55 * STEP_Y, 0),
    (X0 + 2 * STEP_X, Y0 + 2.55 * STEP_Y, 0),
    (X0 + 1.0 * STEP_X, Y0 + 2 * STEP_Y, 90),
    (X0 + 4.6 * STEP_X, Y0 + 2 * STEP_Y, 90),
    (X0 + 3.2 * STEP_X, Y0 + 3 * STEP_Y, 90),
]
D = 62
add('<g fill="none" stroke="#fff" stroke-width="1.5" opacity="0.7">')
for x, y, rot in doors:
    add(f'<g transform="translate({esc(x)},{esc(y)}) rotate({rot})">'
        f'<line x1="0" y1="0" x2="0" y2="{D}"/>'
        f'<path d="M0 {D} A {D} {D} 0 0 0 {D} 0"/></g>')
add('</g>')

# --- Оконные проёмы в наружных стенах: тройная линия ------------------------
add('<g fill="none" stroke="#fff" stroke-width="1.3" opacity="0.65">')
for c in range(COLS):
    cx = X0 + (c + 0.5) * STEP_X
    for y in (Y0, bottom):
        add(f'<line x1="{esc(cx - 52)}" y1="{esc(y)}" x2="{esc(cx + 52)}" y2="{esc(y)}" stroke-width="3"/>')
        add(f'<line x1="{esc(cx - 52)}" y1="{esc(y + (T / 2 if y == Y0 else -T / 2))}" '
            f'x2="{esc(cx + 52)}" y2="{esc(y + (T / 2 if y == Y0 else -T / 2))}"/>')
add('</g>')

# --- Лестница: марш со ступенями и стрелкой подъёма -------------------------
sx, sy = X0 + 4.25 * STEP_X, Y0 + 2.35 * STEP_Y
sw, sh = 1.5 * STEP_X, 0.5 * STEP_Y
add('<g fill="none" stroke="#fff" stroke-width="1.4" opacity="0.7">')
add(f'<rect x="{esc(sx)}" y="{esc(sy)}" width="{esc(sw)}" height="{esc(sh)}"/>')
for i in range(1, 9):
    x = sx + i * sw / 9
    add(f'<line x1="{esc(x)}" y1="{esc(sy)}" x2="{esc(x)}" y2="{esc(sy + sh)}"/>')
add(f'<line x1="{esc(sx + 14)}" y1="{esc(sy + sh / 2)}" x2="{esc(sx + sw - 14)}" y2="{esc(sy + sh / 2)}"/>')
add(f'<path d="M{esc(sx + sw - 30)} {esc(sy + sh / 2 - 7)} L{esc(sx + sw - 14)} {esc(sy + sh / 2)} '
    f'L{esc(sx + sw - 30)} {esc(sy + sh / 2 + 7)}"/>')
add('</g>')

# --- Размерные цепочки: выносные линии, засечки, числа ----------------------
def chain(axis: str, base: float, start: float, step: float, count: int, value: int) -> None:
    add('<g stroke="#fff" stroke-width="1.1" opacity="0.6" fill="none">')
    for i in range(count + 1):
        p = start + i * step
        if axis == 'x':
            add(f'<line x1="{esc(p)}" y1="{esc(base - 9)}" x2="{esc(p)}" y2="{esc(base + 9)}"/>')
        else:
            add(f'<line x1="{esc(base - 9)}" y1="{esc(p)}" x2="{esc(base + 9)}" y2="{esc(p)}"/>')
    if axis == 'x':
        add(f'<line x1="{esc(start)}" y1="{esc(base)}" x2="{esc(start + count * step)}" y2="{esc(base)}"/>')
    else:
        add(f'<line x1="{esc(base)}" y1="{esc(start)}" x2="{esc(base)}" y2="{esc(start + count * step)}"/>')
    add('</g>')
    add('<g fill="#fff" opacity="0.6" font-family="Inter, sans-serif" font-size="15" text-anchor="middle">')
    for i in range(count):
        p = start + (i + 0.5) * step
        if axis == 'x':
            add(f'<text x="{esc(p)}" y="{esc(base - 16)}">{value}</text>')
        else:
            add(f'<text x="{esc(base - 16)}" y="{esc(p)}" transform="rotate(-90 {esc(base - 16)} {esc(p)})">{value}</text>')
    add('</g>')

chain('x', Y0 - 58, X0, STEP_X, COLS, 6000)
chain('y', X0 - 58, Y0, STEP_Y, ROWS, 5400)

svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" fill="none">'
    + ''.join(parts)
    + '</svg>'
)
from pathlib import Path
out = Path('public/img/floorplan.svg')
out.write_text(svg, encoding='utf-8')
print(f'{out}: {len(svg) / 1024:.1f} КБ')
