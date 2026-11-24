"""Транспортный раздел АГР, части 2–4: расчет интенсивности и загрузки УДС в зоне влияния объекта
и картограммы (без масштаба): потоки, уровень загрузки, изменение размеров движения.

    python3 cartograms.py <выход>

Исходные данные (согласовано с заказчиком 24.11.2026):
* загрузка дублёра Щёлковского шоссе и основного хода — по «Схеме существующего уровня загрузки УДС» из
  исходных данных ДГП (дата формирования 11.11.2026): дублёр — средний уровень 0,75–0,90, основной ход
  в центр — высокий (более 0,9), в область — низкий (до 0,75). Для расчета дублёра взята середина интервала;
* интенсивность на местном проезде перед магазином — оценка заказчика: 60 авт/ч в 08:00–09:00 и 80 авт/ч
  в 18:00–19:00 (до получения данных ЦОДД, ответ ожидается 15.12.2026).
Пишет calc.json (все величины для пояснительной записки) и PNG картограмм.
"""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle, FancyArrowPatch

for f_ in ('Montserrat-Regular.ttf', 'Montserrat-Medium.ttf', 'Montserrat-SemiBold.ttf', 'Montserrat-Bold.ttf'):
    p_ = '/usr/share/fonts/truetype/montserrat/' + f_
    if os.path.exists(p_):
        fm.fontManager.addfont(p_)
plt.rcParams['font.family'] = 'Montserrat'
HALO = [pe.withStroke(linewidth=2.0, foreground='white')]

# --- исходные величины -----------------------------------------------------------------------------------------
YEAR0, YEAR1 = 2026, 2028                # существующее положение и расчетный срок (ввод объекта)
GROWTH = 0.015                           # фоновый прирост интенсивности, в год
Z_DUBLER = 0.83                          # середина интервала 0,75–0,90 по схеме ДГП
LANES_DUBLER, P_LANE_DUBLER = 2, 600     # дублёр 7,0 м — две полосы; регулируемое движение, пр. ед./ч на полосу
P_LOCAL = 400                            # местный проезд 3,5 м с разъездом, пр. ед./ч в обоих направлениях
LOCAL = {'am': 60, 'pm': 80}             # оценка заказчика, авт/ч (легковые, коэффициент приведения 1,0)
PARKING = 3                              # машино-мест приобъектной парковки
TURNOVER = {'am': 1.0, 'pm': 2.0}        # оборачиваемость места в час пик, раз в час
PEAKS = {'am': 'утренний час пик 08:00–09:00', 'pm': 'вечерний час пик 18:00–19:00'}


def zclass(z):
    return 'низкий' if z < 0.75 else 'средний' if z <= 0.90 else 'высокий'


def calc():
    k = (1 + GROWTH) ** (YEAR1 - YEAR0)
    P_d = LANES_DUBLER * P_LANE_DUBLER
    N_d0 = round(Z_DUBLER * P_d / 10) * 10
    out = dict(k=round(k, 3), P_dubler=P_d, P_local=P_LOCAL, z_dubler0=Z_DUBLER, N_dubler0=N_d0, peaks={})
    for pk in ('am', 'pm'):
        arr = dep = int(round(PARKING * TURNOVER[pk]))
        L0 = LOCAL[pk]
        # участки: d_e — дублёр восточнее въезда (подход), d_w — западнее (после выезда), ent — въезд/выезд,
        # loc_w — местный проезд от въезда до парковки, loc_e — восточнее парковки
        exist = dict(d_e=N_d0, d_w=N_d0, ent=L0, loc_w=L0, loc_e=L0, gruz=0)
        base = {s: round(v * k) for s, v in exist.items()}
        obj = dict(d_e=arr, d_w=dep, ent=arr + dep, loc_w=arr + dep, loc_e=0, gruz=0)
        calc_ = {s: base[s] + obj[s] for s in exist}
        cap = dict(d_e=P_d, d_w=P_d, ent=P_LOCAL, loc_w=P_LOCAL, loc_e=P_LOCAL, gruz=P_LOCAL)
        z0 = {s: round(exist[s] / cap[s], 2) for s in exist}
        z1 = {s: round(calc_[s] / cap[s], 2) for s in exist}
        out['peaks'][pk] = dict(name=PEAKS[pk], arr=arr, dep=dep, exist=exist, base=base, obj=obj, calc=calc_,
                                cap=cap, z0=z0, z1=z1, dz={s: round(calc_[s] / cap[s] - exist[s] / cap[s], 3)
                                                             for s in exist})
    return out


# --- схема сети (местные координаты u — вдоль шоссе на восток, v — к северу; без масштаба) ------------------------
V_D, V_C, V_O = -41.0, -63.0, -80.0      # дублёр, основной ход в центр, в область
U_ENT, U_P0, U_P1, U_E = -31.0, 8.0, 27.0, 56.0
SEG = {
    'd_e': [(150.0, V_D), (U_ENT + 4, V_D)],
    'd_w': [(U_ENT - 4, V_D), (-150.0, V_D)],
    'ent': [(U_ENT, V_D + 3), (U_ENT, -4.0)],
    'loc_w': [(U_ENT + 3, -4.0), (U_P1, -4.0)],
    'loc_e': [(U_P1, -4.0), (U_E - 3, -4.0)],
    'gruz': [(U_E, -1.0), (U_E, 22.0)],
}
SEG_NAME = {'d_e': 'дублёр Щёлковского ш. до въезда', 'd_w': 'дублёр Щёлковского ш. после выезда',
            'ent': 'въезд и выезд с дублёра (существующий)', 'loc_w': 'местный проезд: въезд — парковка',
            'loc_e': 'местный проезд восточнее парковки', 'gruz': 'проезд между домами 17 и 19 (грузовой)'}
ZCOL = {'низкий': '#2E9E44', 'средний': '#F29C1F', 'высокий': '#D7262C'}


def base_scheme(ax, title):
    ax.set_xlim(-160, 160); ax.set_ylim(-100, 48); ax.set_aspect('equal'); ax.axis('off')
    for v, lab, d in ((V_C, 'Щёлковское шоссе, основной ход — в центр', -1), (V_O, 'Щёлковское шоссе, основной ход — в область', 1)):
        ax.plot([-155, 155], [v, v], color='#C9C9C9', lw=7, solid_capstyle='butt', zorder=1)
        ax.text(-150, v + 5.5, lab, fontsize=5.8, color='#555', ha='left', va='center')
        for u in (-100, 0, 100):
            ax.annotate('', xy=(u + 9 * d, v), xytext=(u - 9 * d, v),
                        arrowprops=dict(arrowstyle='-|>', lw=1.0, color='#777', mutation_scale=8), zorder=2)
    ax.plot([-155, 155], [V_D, V_D], color='#E0E0E0', lw=5, solid_capstyle='butt', zorder=1)
    ax.text(150, V_D - 6.0, 'дублёр Щёлковского шоссе — в центр', fontsize=5.8, color='#555', ha='right',
            va='center')
    for u in (-120, 40):
        ax.annotate('', xy=(u - 9, V_D - 6.0), xytext=(u + 9, V_D - 6.0),
                    arrowprops=dict(arrowstyle='-|>', lw=1.0, color='#777', mutation_scale=8), zorder=2)
    ax.plot([U_ENT, U_ENT], [V_D, -4], color='#E0E0E0', lw=3.5, zorder=1)
    ax.plot([U_ENT, U_E], [-4, -4], color='#E0E0E0', lw=3.5, zorder=1)
    ax.plot([U_E, U_E], [-4, 22], color='#E0E0E0', lw=3.5, zorder=1)
    ax.add_patch(Rectangle((-3, 0), 22, 26, fc='#F58220', ec='#B45309', lw=0.6, zorder=3))
    ax.text(8, 13, 'магазин', fontsize=6, ha='center', va='center', color='#3a1500', fontweight='semibold',
            zorder=4)
    for (u0, v0, w, h, t) in ((-110, 4, 70, 12, '15'), (28, 4, 22, 14, '17'), (66, 4, 80, 12, '19')):
        ax.add_patch(Rectangle((u0, v0), w, h, fc='#E6E6E6', ec='#BDBDBD', lw=0.4, zorder=1))
        ax.text(u0 + w / 2, v0 + h / 2, t, fontsize=5.5, ha='center', va='center', color='#777')
    ax.add_patch(Rectangle((U_P0, -11.5), U_P1 - U_P0, 5, fc='white', ec='#0070C0', lw=0.6, zorder=3))
    ax.text((U_P0 + U_P1) / 2, -9, 'P 3 м/м', fontsize=4.8, ha='center', va='center', color='#0070C0', zorder=4)
    ax.text(-158, 45, title, fontsize=7.5, fontweight='semibold', ha='left', va='top')
    # север: местные оси повернуты на 25,2° против часовой от востока
    a = np.radians(90 - 25.2)
    c = np.array([150.0, 34.0])
    ax.annotate('', xy=c + 9 * np.array([np.cos(a), np.sin(a)]), xytext=c,
                arrowprops=dict(arrowstyle='-|>', lw=1.0, color='#111', mutation_scale=8))
    ax.text(*(c + 13 * np.array([np.cos(a), np.sin(a)])), 'С', fontsize=6.5, ha='center', va='center',
            fontweight='bold')


def label(ax, xy, txt, color='#111', size=6.2):
    ax.text(xy[0], xy[1], txt, fontsize=size, ha='center', va='center', color=color, fontweight='semibold',
            zorder=8, bbox=dict(boxstyle='round,pad=0.25', fc='white', ec=color, lw=0.6))


LABEL_AT = {'d_e': (95.0, V_D + 9), 'd_w': (-95.0, V_D + 9), 'ent': (U_ENT - 14, -22.0), 'loc_w': (-8.0, -16.0),
            'loc_e': (42.0, -10.5), 'gruz': (U_E + 9, 28.0)}


def flows(ax, vals, unit_w=0.012, color='#1F6FD1'):
    for s, pts in SEG.items():
        v = vals[s]
        xy = np.array(pts)
        if v > 0:
            ax.plot(xy[:, 0], xy[:, 1], color=color, lw=1.0 + np.sqrt(v) * 0.25, alpha=0.75, zorder=5,
                    solid_capstyle='butt')
        label(ax, LABEL_AT[s], str(v), color=color if v else '#888')


def loads(ax, z):
    for s, pts in SEG.items():
        xy = np.array(pts)
        cl = zclass(z[s])
        ax.plot(xy[:, 0], xy[:, 1], color=ZCOL[cl], lw=4.0, zorder=5, solid_capstyle='butt')
        label(ax, LABEL_AT[s], ('%.2f' % z[s]).replace('.', ','), color=ZCOL[cl])
    for v, cl, t in ((V_C, 'высокий', 'более 0,9'), (V_O, 'низкий', 'до 0,75')):
        ax.plot([-155, 155], [v, v], color=ZCOL[cl], lw=4.0, zorder=2, solid_capstyle='butt', alpha=0.9)
        label(ax, (60, v), t + ' (ДГП)', color=ZCOL[cl], size=5.6)


def delta(ax, d):
    for s, pts in SEG.items():
        xy = np.array(pts)
        v = d[s]
        if v:
            ax.plot(xy[:, 0], xy[:, 1], color='#7B2D8E', lw=1.0 + v * 0.35, zorder=5, solid_capstyle='butt')
        label(ax, LABEL_AT[s], ('+%d' % v) if v else '0', color='#7B2D8E' if v else '#888')
    label(ax, (60, V_C), '0', color='#888', size=5.6)
    label(ax, (60, V_O), '0', color='#888', size=5.6)


def fig2(path, fn, *panels, size=(1080, 300)):
    W, H = size
    fig = plt.figure(figsize=(W / 72, H / 72), dpi=300)
    n = len(panels)
    for i, (title, draw) in enumerate(panels):
        ax = fig.add_axes([i / n + 0.005, 0.0, 1 / n - 0.01, 1.0])
        base_scheme(ax, title)
        draw(ax)
    fig.savefig(os.path.join(path, fn), dpi=300, facecolor='white')
    plt.close(fig)


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    R = calc()
    json.dump(R, open(os.path.join(outdir, 'calc.json'), 'w'), ensure_ascii=False, indent=1)
    pm, am = R['peaks']['pm'], R['peaks']['am']
    for pk, P in (('pm', pm), ('am', am)):
        fig2(outdir, 'flows_%s.png' % pk,
             ('Существующее положение, %d г.' % YEAR0, lambda ax: flows(ax, P['exist'])),
             ('Расчетный срок, %d г. (с объектом)' % YEAR1, lambda ax: flows(ax, P['calc'])))
        fig2(outdir, 'loads_%s.png' % pk,
             ('Существующее положение, %d г.' % YEAR0, lambda ax: loads(ax, P['z0'])),
             ('Расчетный срок, %d г. (с объектом)' % YEAR1, lambda ax: loads(ax, P['z1'])))
    fig2(outdir, 'delta.png',
         ('Утренний час пик 08:00–09:00', lambda ax: delta(ax, am['obj'])),
         ('Вечерний час пик 18:00–19:00', lambda ax: delta(ax, pm['obj'])))
    print(json.dumps({pk: dict(exist=P['exist'], calc=P['calc'], z0=P['z0'], z1=P['z1']) for pk, P in
                      R['peaks'].items()}, ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1])
