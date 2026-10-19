"""Общее для заданий смежникам по ОВ: ТЗ-2 (ЭОМ), ТЗ-3 (ВК), ТЗ-4 (ГСВ).

Модель одна на документ, планы разнесены по модели (REG, м): 1 этаж — в начале координат, 2 этаж — +40 м по y,
баня — +80 м, фрагмент топочной в М 1:50 — +40 м по x (своя копия подложки: обозначения у 1:50 и 1:100 разные).
Координаты оборудования берутся из скриптов листов РД (ov_boiler_plan, ov_heat1, ov_vent1, ov_bath),
чтобы задания не расходились с листами.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from rdbase import (new_doc as _new_doc, DPlan, RDSheet, add_underlay, UNDER, save_and_pdf,  # noqa: E402,F401
                    fmt_num, axes, HOUSE_AX, BATH_AX, OX, OY, offset_poly)
import ov_boiler_plan as BP                                   # noqa: E402
from ov_heat1 import KSH, KV_RECT, RT_RECT, ECO_UP            # noqa: E402,F401
from ov_vent1 import KU1, KU2                                 # noqa: E402
import ov_bath as BA                                          # noqa: E402

OUT = os.path.join(ROOT, 'out')
SCR = os.path.join(os.path.dirname(ROOT), 'tzpng')           # PNG для проверки (scratchpad)

REG = {'p1': (0.0, 0.0), 'p2': (0.0, 40.0), 'bath': (0.0, 80.0), 'frag': (40.0, 0.0)}

# ---------------------------------------------------------------- оборудование, которого нет в модулях листов
GX = {'Н2': 18.25, 'Н3': 18.50, 'Н4': 18.75, 'Н5': 19.00, 'Н6': 19.25, 'Н7': 19.50}   # насосы РК (лист 7)
PUMP_Y = 13.41
GS = (17.97, 13.27, 18.09, 13.58)                         # гидрострелка у западного края РК (лист 7)
KSH4 = (14.82, 9.08, 15.57, 9.23)                         # лист 5
KN = {'Кн-1': (16.42, 13.18, 19.17, 13.52), 'Кн-3': (0.30, 6.75, 0.62, 7.65)}   # лист 5
RAD2 = {'Р-1': (1.35, 1.32, 3.05, 1.48), 'Р-2': (5.65, 1.32, 6.95, 1.48), 'Р-3': (9.55, 1.32, 11.25, 1.48),
        'Р-5': (12.72, 12.45, 12.82, 13.05)}
KK = (8.20, 13.825)                                       # клапан компенсации (лист 9)
VZ = (9.14, 12.12)                                        # кухонный зонт (лист 9)
DRAIN1 = [(1.75, 7.40), (1.55, 7.40), (1.55, 7.15), (12.20, 7.15), (12.20, 5.80)]   # лист 9
DRAIN1_BR = [[(5.45, 7.40), (5.30, 7.40), (5.30, 7.15)], [(4.30, 5.90), (4.45, 5.90), (4.45, 7.15)]]
DRAIN2 = [[(0.85, 7.85), (12.55, 7.85), (12.95, 8.35)], [(14.25, 11.40), (14.25, 9.30), (14.25, 8.60)]]  # лист 10
GAS = [(20.20, 12.85), (19.75, 12.85), (19.75, 13.45), (16.05, 13.45), (16.05, 11.08)]   # лист 7, условно
BATH_FANS = {n: d['fan'] for n, d in BA.FANS.items()}   # вытяжные вентиляторы ВВ-б1, ВВ-б2 (лист 12)
ECO_BATH = BA.ECO_IN                                      # подъём Ecoflex в бане (лист 12), западнее пилона АР


def center(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


# ---------------------------------------------------------------- документ, подложки, планы
def new_doc():
    doc = _new_doc()
    for n, c, lw in (('ТЗ_ЭОМ', 1, 35), ('ТЗ_ВК', 5, 35), ('ТЗ_ВК_К', 30, 35), ('ТЗ_ГСВ', 40, 50),
                     ('ТЗ_контекст', 8, 18), ('ТЗ_зона', 8, 25), ('ОВ_Г', 40, 50), ('ОВ_дымоход', 8, 35)):
        if n not in doc.layers:
            doc.layers.add(n, color=c, lineweight=lw)
    return doc


def underlays(doc, pairs):
    """pairs: [(регион, ключ подложки)] — блок подложки один, вставок по числу регионов."""
    blocks = {}
    for reg, uk in pairs:
        if uk not in blocks:
            blocks[uk] = add_underlay(doc, UNDER[uk], 'АР_' + uk)
        dx, dy = REG[reg]
        doc.modelspace().add_blockref(blocks[uk], (-OX + dx * 1000, -OY + dy * 1000),
                                      dxfattribs={'layer': 'АР_подложка'})


def plan(doc, reg, k):
    dx, dy = REG[reg]
    return DPlan(doc, k=k, origin=(dx * 1000, dy * 1000))


def viewport(sh, reg, cx, cy, w, h, mcx, mcy, k):
    """Видовой экран: центр вида (mcx, mcy) — в координатах плана (м), регион добавляется сам."""
    dx, dy = REG[reg]
    return sh.viewport(cx, cy, w, h, mcx + dx, mcy + dy, k=k)


def house_axes(p, y_bub=-1.9, x_bub=-1.9):
    axes(p, HOUSE_AX, y_bub=y_bub, x_bub=x_bub, r=3.0, dims=False)


def frag_axes(p):
    """Оси 5, Г, Д у фрагмента топочной (как на листе 7)."""
    R = p.H(3.0) / 1000
    p.line(20.0, 8.40, 20.0, 15.40 - 2 * R, 'ОВ_размеры', ltype='ОВ_ШП')
    p.circle(20.0, 15.40 - R, 0, 'ОВ_размеры', r_paper=3.0)
    p.t(20.0, 15.40 - R, '5', 3.0, 'center', 'ОВ_размеры')
    for n, y in (('Г', 8.90), ('Д', 13.80)):
        p.line(13.55 + 2 * R, y, 14.9, y, 'ОВ_размеры', ltype='ОВ_ШП')
        p.circle(13.55 + R, y, 0, 'ОВ_размеры', r_paper=3.0)
        p.t(13.55 + R, y, n, 3.0, 'center', 'ОВ_размеры')


# ---------------------------------------------------------------- контекст ОВ (серым)
C8 = dict(color=8)


def ctx_rect(p, r, txt=None, h=1.6, rot=0, ltype=None):
    p.rect(*r, 'ТЗ_контекст', ltype=ltype)
    if txt:
        x, y = center(r)
        p.t(x, y, txt, h, 'center', 'ТЗ_контекст', rot=rot)


def ctx_p1(p, boiler=True):
    """1 этаж: шкафы, конвекторы, блоки К, Р-т; топочная — контуром или оборудованием."""
    for n, r in KSH.items():
        ctx_rect(p, r)
    for n, r in KV_RECT.items():
        ctx_rect(p, r)
    ctx_rect(p, RT_RECT)
    for n, r in KU1.items():
        ctx_rect(p, r, n, 1.4)
    if boiler:
        ctx_boiler(p, h=1.2)


def ctx_p2(p):
    ctx_rect(p, KSH4)
    for r in KN.values():
        ctx_rect(p, r)
    for r in RAD2.values():
        ctx_rect(p, r)
    for n, r in KU2.items():
        ctx_rect(p, r, n, 1.4)


def ctx_bath(p, h=1.4):
    ctx_rect(p, BA.CAB_DIR)
    ctx_rect(p, BA.CAB_UFH)
    x, y, r = BA.B2
    p.circle(x, y, r, 'ТЗ_контекст')
    p.t(x, y, 'Б2', h, 'center', 'ТЗ_контекст')
    ctx_rect(p, BA.TOD_POS, 'ТО', h * 0.8)
    for n, r in BA.DEVPOS.items():
        ctx_rect(p, r)


def ctx_boiler(p, h=1.8, labels=True):
    """Оборудование топочной (лист 7) контуром."""
    for n, r in BP.EQ.items():
        if n in ('К1', 'К2'):
            ctx_rect(p, r, n if labels else None, h, rot=90)
        elif n in ('ПК', 'БП', 'ШУ', 'КШ-3'):
            ctx_rect(p, r, n if labels and n != 'КШ-3' else None, h)
        else:
            ctx_rect(p, r)
    x, y, r = BP.B1
    p.circle(x, y, r, 'ТЗ_контекст')
    if labels:
        p.t(x - 0.08, y + 0.05, 'Б1', h, 'center', 'ТЗ_контекст')
    ctx_rect(p, GS)
    ctx_rect(p, BP.P1, 'П1 (под потолком)' if labels else None, h * 0.9, ltype='ОВ_ШТРИХ')
    ctx_rect(p, BP.NB1, 'НБ-1' if labels else None, h, rot=90)
    ctx_rect(p, BP.WASH, ltype='ОВ_ШТРИХ')
    for x in GX.values():
        p.circle(x, PUMP_Y, 0.06, 'ТЗ_контекст')
    p.circle(BP.TRAP[0], BP.TRAP[1], 0.08, 'ТЗ_контекст')
    sh = BP.SH
    p.rect(sh[0], sh[2], sh[1], sh[3], 'ТЗ_контекст')


def boiler_zone(p, txt, at_txt, anchor='left'):
    """Топочная на плане 1:100 — штриховым контуром со ссылкой на фрагмент."""
    p.rect(BP.X0, BP.Y0, BP.X1, BP.Y1, 'ТЗ_зона', ltype='ОВ_ШТРИХ', lw=35)
    lab(p, *at_txt, txt, at=(17.6, 10.6), anchor=anchor)


# ---------------------------------------------------------------- точки и подписи
def m_eom(p, x, y):
    p.circle(x, y, 0, 'ТЗ_ЭОМ', fill=1, r_paper=1.1)


def m_vk(p, x, y, layer='ТЗ_ВК'):
    s = p.H(1.05) / p.unit
    p.rect(x - s, y - s, x + s, y + s, layer, fill=5 if layer == 'ТЗ_ВК' else 30)


def lab(p, x, y, s, at=None, lines=None, anchor='left', h=2.0, more=()):
    """Полка с подписью (маска под текстом); more — дополнительные точки с выносками к той же полке.
    Положение полки задаётся как обычно (x, y, anchor), а выноска подходит к ближнему концу полки —
    иначе она перечёркивает собственный текст."""
    pts = ([at] if at else []) + list(more)
    if pts:
        w = p.tw(s, h) + p.H(1.2) / p.unit
        if lines:
            w = max(w, p.tw(lines, h) + p.H(1.2) / p.unit)
        x0 = x if anchor == 'left' else x - w
        mx = sum(q[0] for q in pts) / len(pts)
        anchor, x = ('right', x0 + w) if mx > x0 + w / 2 else ('left', x0)
    w = p.label(x, y, s, h, anchor, at=at, lines=lines, mask=True)
    for q in more:
        p.pl([q, (x, y)], 'ОВ_выноски')
        p.dot(*q)
    return w


def legend_eom(sh, x, y):
    s = sh.s
    s.text('Условные обозначения', x + 45, y, h=3.0, align='center')
    y -= 8
    sh.p.circle(x + 4, y, 0, 'ТЗ_ЭОМ', fill=1, r_paper=1.1)
    s.text('точка подключения электропотребителя ОВ', x + 10, y, h=2.2)
    y -= 6
    sh.p.line(x + 1, y, x + 7, y, 'ОВ_выноски')
    sh.p.t(x + 1.5, y + 1.0, '6. Н2', 2.0, 'bl', 'ОВ_марки')
    s.text('номер позиции по перечню (листы 4, 5) и марка', x + 10, y, h=2.2)
    y -= 6
    sh.p.rect(x + 1, y - 1.5, x + 7, y + 1.5, 'ТЗ_контекст')
    s.text('оборудование ОВ (по листам РД ОВ) — для ориентации', x + 10, y, h=2.2)
    return y - 4


# ---------------------------------------------------------------- таблица с автоматической высотой строк
def row_heights(rows, widths, h, head=None):
    out = []
    for i, r in enumerate(rows):
        n = 1
        for cell, cw in zip(r, widths):
            if not cell:
                continue
            per = max(1, int((cw - 2.4) / (h * 0.62)))
            lines = 0
            for part in str(cell).split('\\P'):
                lines += max(1, math.ceil(len(part) / per))
            n = max(n, lines)
        out.append(max(head or 0, n * h * 1.62 + 2.2) if i == 0 else n * h * 1.62 + 2.0)
    return out


# ---------------------------------------------------------------- сохранение, PDF одним файлом, PNG для проверки
def finish(doc, name, png=True, only=None):
    """DXF + PDF всех листов одним файлом. Листы печатаются render_layout.py параллельно (каждый — своим
    процессом): печать модели в видовой экран медленная, а листов с планами — по три-четыре."""
    import subprocess
    import pymupdf
    path = os.path.join(OUT, name + '.dxf')
    save_and_pdf(doc, path, pdf=False)
    lays = [l.name for l in doc.layouts if l.name != 'Model' and (only is None or l.name in only)]
    procs, order = [], []
    for ln in lays:
        f = path[:-4] + '_' + ln.replace(' ', '_') + '.pdf'
        procs.append(subprocess.Popen([sys.executable, os.path.join(ROOT, 'render_layout.py'), path, f, ln],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.PIPE))
        order.append(f)
    for pr in procs:
        _, err = pr.communicate()
        if pr.returncode:
            raise RuntimeError(err.decode()[-2000:])
    order.sort(key=lambda f: int(f.rsplit('_', 1)[1][:-4]))
    if png:
        os.makedirs(SCR, exist_ok=True)
        for f in order:
            n = f.rsplit('_', 1)[1][:-4]
            pymupdf.open(f)[0].get_pixmap(dpi=110).save(os.path.join(SCR, f'{name}_{n}.png'))
    out_pdf = os.path.join(OUT, name + '.pdf')
    if only is None:
        merged = pymupdf.open()
        for f in order:
            merged.insert_pdf(pymupdf.open(f))
        merged.save(out_pdf)
    for f in order:
        os.remove(f)
    return path, out_pdf
