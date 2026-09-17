#!/usr/bin/env python3
"""Рисунок для тёмного первого экрана: стройка в стиле чертежа.

Силуэты зданий, два башенных крана и каркас недостроенного дома тонкими
светлыми линиями на фирменном синем — как сетка чертежа в светлом варианте,
только с сюжетом. Рисунок собственный: ни фотографий, ни чужих файлов,
вопрос прав не возникает (запись — в public/img/CREDITS.md).

Почему рисунок, а не фотография: свой кадр с каской и кодексами уже стоит
под квизом, а одна сцена не должна открывать и закрывать страницу; скачать
новую фотографию из рабочей среды нельзя, а выдумывать источник — тем более.

Композиция под текст: слева здания низкие — там заголовок и кнопки, справа
выше — там кадр виден целиком. Верх кранов не выше y=230: на компьютере
секция ниже рисунка, обрезается верх (object-bottom), и оголовки кранов
должны остаться в кадре. Окна — узором (pattern), а не тысячей
прямоугольников: файл держится в десятках килобайт, а не в сотнях.

    python3 scripts/make-skyline.py            # -> public/img/skyline.svg
"""
from __future__ import annotations

import random
from pathlib import Path

W, H = 1920, 1000
GROUND = 940
LINE = "#A3B8FC"  # accent-300
LIT = "#C9D6FE"  # accent-200
FILL = "#0E1338"
FILL_BACK = "#121A4A"
rng = random.Random(17)
out: list[str] = []


def add(s: str) -> None:
    out.append(s)


def building(x: float, w: float, h: float, *, back: bool = False, roof: str = "flat") -> None:
    """Дом с окнами. back — задний ряд: бледнее и без подсветки окон."""
    y = GROUND - h
    fill = FILL_BACK if back else FILL
    op = 0.55 if back else 0.9
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{LINE}" stroke-opacity="{op * 0.45:.2f}" stroke-width="1.5"/>')
    # окна — узор; поля по 10px с краёв и сверху
    add(f'<rect x="{x + 10}" y="{y + 12}" width="{w - 20}" height="{h - 20}" fill="url(#win)" opacity="{0.5 if back else 1}"/>')
    if roof == "step":
        add(f'<rect x="{x + w * 0.3}" y="{y - 26}" width="{w * 0.4}" height="26" fill="{fill}" stroke="{LINE}" stroke-opacity="{op * 0.45:.2f}" stroke-width="1.5"/>')
    if roof == "mast":
        add(f'<line x1="{x + w / 2}" y1="{y}" x2="{x + w / 2}" y2="{y - 70}" stroke="{LINE}" stroke-opacity="0.6" stroke-width="1.5"/>')
        add(f'<circle cx="{x + w / 2}" cy="{y - 74}" r="3" fill="{LIT}" opacity="0.9"/>')
    if not back:
        # несколько горящих окон — случайно, но с фиксированным зерном
        cols = int((w - 20) // 16)
        rows = int((h - 20) // 22)
        for _ in range(max(2, (cols * rows) // 9)):
            c, r = rng.randrange(cols), rng.randrange(rows)
            add(f'<rect x="{x + 12 + c * 16}" y="{y + 14 + r * 22}" width="8" height="12" fill="{LIT}" opacity="{rng.uniform(0.35, 0.7):.2f}"/>')


def frame_building(x: float, w: float, h_done: float, h_frame: float) -> None:
    """Недострой: нижние этажи готовы, верхние — открытый каркас из колонн и плит."""
    building(x, w, h_done)
    y_top = GROUND - h_done - h_frame
    cols = 5
    step = w / (cols - 1)
    for i in range(cols):
        cx = x + i * step
        add(f'<line x1="{cx}" y1="{y_top}" x2="{cx}" y2="{GROUND - h_done}" stroke="{LINE}" stroke-opacity="0.55" stroke-width="1.5"/>')
    floors = int(h_frame // 34)
    for f in range(floors + 1):
        fy = GROUND - h_done - f * 34
        add(f'<line x1="{x - 6}" y1="{fy}" x2="{x + w + 6}" y2="{fy}" stroke="{LINE}" stroke-opacity="0.7" stroke-width="2"/>')
    # диагональные связи на верхнем этаже — читается как стройка
    fy = GROUND - h_done - floors * 34
    add(f'<line x1="{x}" y1="{fy + 34}" x2="{x + step}" y2="{fy}" stroke="{LINE}" stroke-opacity="0.45" stroke-width="1"/>')
    add(f'<line x1="{x + w}" y1="{fy + 34}" x2="{x + w - step}" y2="{fy}" stroke="{LINE}" stroke-opacity="0.45" stroke-width="1"/>')


def lattice(x1: float, y1: float, x2: float, y2: float, depth: float, n: int, op: float) -> None:
    """Решётчатый пояс: два хорда на расстоянии depth и зигзаг между ними (вдоль оси x или y)."""
    if x1 == x2:  # вертикальная мачта
        add(f'<line x1="{x1 - depth / 2}" y1="{y1}" x2="{x1 - depth / 2}" y2="{y2}" stroke="{LINE}" stroke-opacity="{op}" stroke-width="2"/>')
        add(f'<line x1="{x1 + depth / 2}" y1="{y1}" x2="{x1 + depth / 2}" y2="{y2}" stroke="{LINE}" stroke-opacity="{op}" stroke-width="2"/>')
        pts = []
        for i in range(n + 1):
            yy = y1 + (y2 - y1) * i / n
            pts.append(f"{x1 - depth / 2 if i % 2 == 0 else x1 + depth / 2},{yy}")
        add(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{LINE}" stroke-opacity="{op * 0.7:.2f}" stroke-width="1"/>')
    else:  # горизонтальная стрела
        add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y1}" stroke="{LINE}" stroke-opacity="{op}" stroke-width="2"/>')
        add(f'<line x1="{x1}" y1="{y1 + depth}" x2="{x2}" y2="{y1 + depth}" stroke="{LINE}" stroke-opacity="{op}" stroke-width="2"/>')
        pts = []
        for i in range(n + 1):
            xx = x1 + (x2 - x1) * i / n
            pts.append(f"{xx},{y1 if i % 2 == 0 else y1 + depth}")
        add(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{LINE}" stroke-opacity="{op * 0.7:.2f}" stroke-width="1"/>')


def crane(x: float, height: float, jib: float, counter: float, direction: int, *, op: float = 0.85, load: bool = True) -> None:
    """Башенный кран: мачта, оголовок, стрела с тележкой и крюком, противовес, растяжки."""
    top = GROUND - height
    lattice(x, GROUND, x, top, 22, int(height // 22), op)
    # оголовок
    add(f'<polygon points="{x - 11},{top} {x + 11},{top} {x},{top - 70}" fill="none" stroke="{LINE}" stroke-opacity="{op}" stroke-width="2"/>')
    # стрела и противовесная консоль
    jx = x + direction * jib
    cx = x - direction * counter
    lattice(min(x, jx), top, max(x, jx), top, 16, int(jib // 18), op)
    lattice(min(x, cx), top, max(x, cx), top, 16, int(counter // 18), op)
    # растяжки
    add(f'<line x1="{x}" y1="{top - 70}" x2="{x + direction * jib * 0.62}" y2="{top}" stroke="{LINE}" stroke-opacity="{op * 0.8:.2f}" stroke-width="1.2"/>')
    add(f'<line x1="{x}" y1="{top - 70}" x2="{cx}" y2="{top}" stroke="{LINE}" stroke-opacity="{op * 0.8:.2f}" stroke-width="1.2"/>')
    # противовес и кабина
    add(f'<rect x="{min(cx, cx + direction * 34)}" y="{top + 16}" width="34" height="22" fill="{FILL}" stroke="{LINE}" stroke-opacity="{op}" stroke-width="1.5"/>')
    add(f'<rect x="{x + direction * 14 - (12 if direction < 0 else 0)}" y="{top + 8}" width="14" height="18" fill="{FILL}" stroke="{LINE}" stroke-opacity="{op}" stroke-width="1.5"/>')
    # тележка, трос, крюк, груз
    tx = x + direction * jib * 0.7
    add(f'<rect x="{tx - 8}" y="{top + 14}" width="16" height="8" fill="{LINE}" opacity="{op}"/>')
    drop = height * 0.42
    add(f'<line x1="{tx}" y1="{top + 22}" x2="{tx}" y2="{top + 22 + drop}" stroke="{LINE}" stroke-opacity="{op * 0.8:.2f}" stroke-width="1.2"/>')
    hy = top + 22 + drop
    add(f'<path d="M{tx},{hy} v10 a7,7 0 1,0 7,-7" fill="none" stroke="{LINE}" stroke-opacity="{op}" stroke-width="2"/>')
    if load:
        add(f'<line x1="{tx - 26}" y1="{hy + 30}" x2="{tx + 26}" y2="{hy + 30}" stroke="{LINE}" stroke-opacity="{op}" stroke-width="2"/>')
        add(f'<line x1="{tx - 26}" y1="{hy + 30}" x2="{tx}" y2="{hy + 10}" stroke="{LINE}" stroke-opacity="{op * 0.7:.2f}" stroke-width="1"/>')
        add(f'<line x1="{tx + 26}" y1="{hy + 30}" x2="{tx}" y2="{hy + 10}" stroke="{LINE}" stroke-opacity="{op * 0.7:.2f}" stroke-width="1"/>')
        add(f'<rect x="{tx - 26}" y="{hy + 30}" width="52" height="14" fill="{FILL}" stroke="{LINE}" stroke-opacity="{op}" stroke-width="1.5"/>')


# ---- сцена ----
add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
add('<defs>')
add('<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#141A45"/><stop offset="1" stop-color="#1B2468"/></linearGradient>')
add('<linearGradient id="glow" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2F4BDE" stop-opacity="0"/><stop offset="1" stop-color="#2F4BDE" stop-opacity="0.28"/></linearGradient>')
add(f'<pattern id="win" width="16" height="22" patternUnits="userSpaceOnUse"><rect x="2" y="2" width="8" height="12" fill="{LIT}" opacity="0.13"/></pattern>')
add(f'<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{LINE}" stroke-opacity="0.06" stroke-width="1"/></pattern>')
add(f'<pattern id="grid2" width="200" height="200" patternUnits="userSpaceOnUse"><path d="M200 0H0V200" fill="none" stroke="{LINE}" stroke-opacity="0.09" stroke-width="1"/></pattern>')
add('</defs>')
add(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')
add(f'<rect width="{W}" height="{H}" fill="url(#grid)"/>')
add(f'<rect width="{W}" height="{H}" fill="url(#grid2)"/>')
add(f'<rect x="0" y="{GROUND - 320}" width="{W}" height="320" fill="url(#glow)"/>')

# задний ряд — бледнее, ниже по контрасту
for x, w, h in [(60, 120, 150), (330, 150, 210), (620, 130, 250), (880, 170, 330), (1140, 150, 420), (1330, 130, 380), (1560, 140, 470), (1770, 150, 400)]:
    building(x, w, h, back=True)

# передний ряд: слева низко (под текстом), справа высоко
building(0, 130, 120)
building(170, 110, 170, roof="step")
building(420, 150, 150)
building(700, 120, 230)
building(960, 150, 300, roof="mast")
building(1240, 120, 360)
frame_building(1400, 190, 260, 240)
building(1650, 130, 520, roof="step")
building(1800, 160, 300)

crane(1140, 540, 330, 110, +1)          # средний, стрела вправо над недостроем
crane(1590, 660, 420, 130, -1, op=0.95)  # главный, стрела влево над недостроем
crane(560, 380, 220, 80, -1, op=0.5, load=False)  # дальний, слева, бледнее

# земля
add(f'<rect x="0" y="{GROUND}" width="{W}" height="{H - GROUND}" fill="#0B0F2E"/>')
add(f'<line x1="0" y1="{GROUND}" x2="{W}" y2="{GROUND}" stroke="{LINE}" stroke-opacity="0.35" stroke-width="1.5"/>')
add('</svg>')

target = Path(__file__).resolve().parent.parent / "public" / "img" / "skyline.svg"
target.write_text("\n".join(out), encoding="utf-8")
print(f"{target.relative_to(target.parents[2])}: {target.stat().st_size / 1024:.1f} КБ")
