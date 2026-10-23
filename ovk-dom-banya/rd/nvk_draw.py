"""И05.09.26-НВК: общая часть листов — перечень, слои, подложка (топосъёмка + ГП01), знаки сетей и колодцев,
профили. Сети и колодцы берутся из модели nvk_model и рисуются на листе (мм листа) поверх видового экрана подложки.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'sheets'))
import ezdxf  # noqa: E402
from ezdxf import recover  # noqa: E402
from ezdxf.addons import importer  # noqa: E402
from rdbase import fmt_num  # noqa: E402
import tm_draw as TD  # noqa: E402
from tm_draw import PP, View, Labels, lev, f1, unit, dim_h  # noqa: E402,F401
from vk_draw import VLabels, clip2, in_box, fix_glyphs  # noqa: E402,F401
import nvk_model as M  # noqa: E402

CODE_NVK = 'И05.09.26-НВК'
BLD_NVK = 'Наружные сети водопровода и канализации'
NVK_LIST = {
    1: 'Общие данные (начало)',
    2: 'Общие данные (окончание). Условные обозначения',
    3: 'План наружных сетей В1, К1, К2, Др. М 1:200',
    4: 'Профиль сети К1',
    5: 'Профили дренажа Др и ливневой сети К2 дома',
    6: 'Профили Др и К2 бани. Выпуск в ливневую сеть',
    7: 'Профиль ввода В1. Подводка полива КХ-8',
    8: 'Колодцы. Узлы и детали',
}
NVK_TOTAL = len(NVK_LIST)
NVK_OUT = os.path.join(HERE, 'out', 'nvk')
LAYERS_NVK = {
    'НВК_В1': (5, 50), 'НВК_К1': (34, 50), 'НВК_К2': (4, 50), 'НВК_Др': (3, 35), 'НВК_колодцы': (7, 35),
    'НВК_сущ': (8, 25), 'НВК_сущ_текст': (8, 13), 'НВК_утепл': (6, 13), 'НВК_марки': (7, 18), 'НВК_текст': (7, 18),
    'НВК_размеры': (7, 13), 'НВК_топо': (9, 9), 'НВК_ГП': (8, 18), 'НВК_профиль': (7, 18), 'НВК_земля': (7, 35),
    'НВК_грунт': (8, 13), 'НВК_оси': (7, 13), 'НВК_граница': (6, 35),
}
STYLE = {   # система: (слой, тип линии, обозначение в разрывах)
    'В1': ('НВК_В1', None, 'В1'), 'К1': ('НВК_К1', None, 'К1'), 'К2': ('НВК_К2', None, 'К2'),
    'Др': ('НВК_Др', 'ОВ_ШТРИХ', 'Др'),
}
DATA = None


def setup(doc):
    TD.setup_layers(doc)
    for n, (c, lw) in LAYERS_NVK.items():
        if n not in doc.layers:
            doc.layers.add(n, color=c, lineweight=lw)


def finish(doc):
    fix_glyphs(doc)


def alev(z, d=2):
    """Абсолютная отметка: 185,39."""
    return f'{z:.{d}f}'.replace('.', ',')


def data():
    global DATA
    if DATA is None:
        DATA = json.load(open(os.path.join(NVK_OUT, 'nvk.json')))
    return DATA


def msk(x, y):
    """Оси дома -> МСК-50 (X — север, Y — восток), м."""
    t = json.load(open(os.path.join(NVK_OUT, 'house2msk.json')))
    R, mA, mQ = t['R'], t['mA'], t['mQ']
    dx, dy = x - mA[0], y - mA[1]
    E = mQ[0] + R[0][0] * dx + R[0][1] * dy
    N = mQ[1] + R[1][0] * dx + R[1][1] * dy
    return N, E


NORTH = None


def north_dir():
    """Направление на север в осях дома (единичный вектор)."""
    t = json.load(open(os.path.join(NVK_OUT, 'house2msk.json')))
    R = t['R']
    # R·d = (0, 1) -> d = Rᵀ(0, 1)
    return (R[1][0], R[1][1])


# ====================================================================================== подложка
def site_underlay(doc, box=(-30, -30, 50, 50)):
    """Топосъёмка (оси дома, м -> мм модели) и ГП01 (стены дома и бани, граница участка) в модели."""
    if 'ТОПО' in doc.blocks:
        return
    blk = doc.blocks.new('ТОПО')
    src = ezdxf.readfile(os.path.join(NVK_OUT, 'topo_house_axes.dxf'))
    x0, y0, x1, y1 = box

    def inside(p):
        return x0 <= p[0] <= x1 and y0 <= p[1] <= y1
    for e in src.modelspace():
        if e.dxftype() == 'LINE':
            a, b = e.dxf.start, e.dxf.end
            if inside(a) or inside(b):
                lay = 'НВК_граница' if e.dxf.layer == 'ТОПО_границы' else 'НВК_топо'
                blk.add_line((a.x * 1000, a.y * 1000), (b.x * 1000, b.y * 1000), dxfattribs={'layer': lay})
        elif e.dxftype() == 'LWPOLYLINE':
            pts = [(p[0], p[1]) for p in e.get_points()]
            if any(inside(p) for p in pts):
                lay = 'НВК_граница' if e.dxf.layer == 'ТОПО_границы' else 'НВК_топо'
                blk.add_lwpolyline([(p[0] * 1000, p[1] * 1000) for p in pts], close=e.closed,
                                   dxfattribs={'layer': lay})
    doc.modelspace().add_blockref('ТОПО', (0, 0), dxfattribs={'layer': 'НВК_топо'})
    # ГП01: стены, проёмы, крыльца; без антуража и разметки Revit
    sdoc, _ = recover.readfile(os.path.join(HERE, '..', 'gp01', 'gp01.dxf'))
    keep = ('A-WALL', 'A-WALL-PATT', 'A-GLAZ', 'A-GLAZ-CWMG', 'A-DOOR', 'A-FLOR', 'S-STRS', 'S-GRID')
    ents = [e for e in sdoc.modelspace() if e.dxf.layer in keep and not (
        e.dxftype() == 'INSERT' and any(k in e.dxf.name for k in ('Enscape', 'Антураж', 'Машиноместо')))]
    imp = importer.Importer(sdoc, doc)
    gblk = doc.blocks.new('ГП01')
    imp.import_entities(ents, gblk)
    imp.finalize()
    for lay in list(doc.layers):
        n = lay.dxf.name
        if n.startswith(('A-', 'S-')):
            lay.color = 8
            lay.dxf.lineweight = 18 if n == 'A-WALL' else 9
    from underlay import OX, OY
    doc.modelspace().add_blockref('ГП01', (-OX, -OY), dxfattribs={'layer': 'НВК_ГП'})


def plan_view(doc, sh, cx, cy, w, h, mx, my, K):
    site_underlay(doc)
    vp = sh.viewport(cx, cy, w, h, mx, my, k=K)
    vp.dxf.layer = 'ОВ_видовые'
    V = View('plan', K, (cx, cy), (mx, my))
    return V, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


# ====================================================================================== сети на плане
def clip_poly(pts, box):
    """Полилиния (мм листа), обрезанная рамкой — список кусков."""
    out, cur = [], []
    for a, b in zip(pts, pts[1:]):
        c = clip2(a, b, box)
        if c is None:
            if len(cur) > 1:
                out.append(cur)
            cur = []
            continue
        A, B = c
        if cur and math.dist(cur[-1], A) < 1e-6:
            cur.append(B)
        else:
            if len(cur) > 1:
                out.append(cur)
            cur = [A, B]
        if math.dist(B, b) > 1e-6:
            out.append(cur)
            cur = []
    if len(cur) > 1:
        out.append(cur)
    return out


def draw_pipe(p, V, pp, box, every=38.0, lw=None, L=None):
    lay, lt, mark = STYLE[pp['sys']]
    pts = [V.P((x, y, 0)) for x, y in pp['pts']]
    for part in clip_poly(pts, box):
        p.pipe(part, lay, mark=mark, every=every, h=1.8, ltype=lt, lw=lw)
        if L is not None:
            for a, b in zip(part, part[1:]):
                L.segs.append((a, b))


def well_r(w, V):
    """Радиус знака колодца на листе: по размеру, но не меньше 1,1 мм."""
    return max(1.1, w['dn'] / 2000 * V.s)


def draw_well(p, V, w):
    c = V.P((w['x'], w['y'], 0))
    r = well_r(w, V)
    if w.get('exist'):
        p.circle(c[0], c[1], 0, 'НВК_сущ', r_paper=r)
        p.circle(c[0], c[1], 0, 'НВК_сущ', r_paper=r * 0.45)
    else:
        lay = {'К1': 'НВК_К1', 'К2': 'НВК_К2', 'Др': 'НВК_Др', 'В1': 'НВК_В1'}[w['sys']]
        p.m.add_wipeout([(c[0] - r * 0.7, c[1] - r * 0.7), (c[0] + r * 0.7, c[1] + r * 0.7)],
                        dxfattribs={'layer': 'НВК_колодцы'})
        p.circle(c[0], c[1], 0, lay, r_paper=r, lw=50)
    return c, r


def flow_arrow(p, V, a, b, lay, size=2.4, at=0.5):
    """Стрелка направления стока на участке a→b (м)."""
    A, B = V.P((a[0], a[1], 0)), V.P((b[0], b[1], 0))
    if math.dist(A, B) < 8:
        return
    d = unit(A, B)
    c = (A[0] + (B[0] - A[0]) * at, A[1] + (B[1] - A[1]) * at)
    n = (-d[1], d[0])
    off = 1.6
    t = (c[0] + n[0] * off + d[0] * size / 2, c[1] + n[1] * off + d[1] * size / 2)
    s = (c[0] + n[0] * off - d[0] * size / 2, c[1] + n[1] * off - d[1] * size / 2)
    p.pl([s, t], lay)
    p.poly([t, (t[0] - d[0] * 1.1 + n[0] * 0.45, t[1] - d[1] * 1.1 + n[1] * 0.45),
            (t[0] - d[0] * 1.1 - n[0] * 0.45, t[1] - d[1] * 1.1 - n[1] * 0.45)], lay, fill=7, outline=False)


def north_arrow(p, x, y, size=16.0):
    """Стрелка «север» (С): по направлению на север в осях дома, половина острия залита."""
    d = north_dir()
    a = math.atan2(d[1], d[0])
    u = (math.cos(a), math.sin(a))
    n = (-u[1], u[0])
    tip = (x + u[0] * size / 2, y + u[1] * size / 2)
    tail = (x - u[0] * size / 2, y - u[1] * size / 2)
    base = (tip[0] - u[0] * size * 0.45, tip[1] - u[1] * size * 0.45)
    p.pl([tail, tip], 'НВК_марки', lw=35)
    w = size * 0.13
    p.poly([tip, (base[0] + n[0] * w, base[1] + n[1] * w), base], 'НВК_марки', fill=7)
    p.pl([tip, (base[0] - n[0] * w, base[1] - n[1] * w), base], 'НВК_марки')
    p.t(tip[0] + u[0] * 3.2, tip[1] + u[1] * 3.2, 'С', 3.5, 'center', 'НВК_марки')


# ====================================================================================== профиль
class Profile:
    """Продольный профиль: горизонталь 1:Kh, вертикаль 1:Kv; низ таблицы — (x0, y0) мм листа.

    rows — строки таблицы (подпись, высота мм); узлы — точки по длине s (м) с подписями.
    Условный горизонт zc — отметка линии верха таблицы."""

    ROWS = [('Материал, диаметр, основание', 9.0), ('Отметка земли проектная', 12.0),
            ('Отметка земли фактическая', 12.0), ('Отметка лотка трубы', 12.0), ('Глубина заложения лотка', 10.0),
            ('Уклон, ‰ / длина, м', 9.0), ('Расстояние, м', 7.0), ('Колодец (точка)', 9.0)]
    HEAD_W = 42.0

    def __init__(self, p, x0, y0, L, Kh, Kv, zc, ztop, rows=None):
        self.p, self.x0, self.y0, self.L, self.Kh, self.Kv, self.zc, self.ztop = p, x0, y0, L, Kh, Kv, zc, ztop
        self.rows = rows or self.ROWS
        self.H = sum(h for _, h in self.rows)
        self.X0 = x0 + self.HEAD_W                   # начало шкалы длин
        self.yt = y0 + self.H                        # верх таблицы = условный горизонт

    def X(self, s):
        return self.X0 + s * 1000 / self.Kh

    def Y(self, z):
        return self.yt + (z - self.zc) * 1000 / self.Kv

    def row_y(self, name):
        y = self.yt
        for n, h in self.rows:
            if n == name:
                return y - h, y
            y -= h
        raise KeyError(name)

    def table(self):
        p = self.p
        xr = self.X(self.L) + 6
        y = self.yt
        p.line(self.x0, y, xr, y, 'НВК_профиль', lw=35)
        for n, h in self.rows:
            p.line(self.x0, y - h, xr, y - h, 'НВК_профиль', lw=35 if n == self.rows[-1][0] else 18)
            p.t(self.x0 + 1.2, y - h / 2, n, 1.9, 'left', 'НВК_текст')
            y -= h
        p.line(self.x0, self.y0, self.x0, self.yt, 'НВК_профиль', lw=35)
        p.line(self.X0, self.y0, self.X0, self.yt, 'НВК_профиль', lw=35)
        p.line(xr, self.y0, xr, self.yt, 'НВК_профиль', lw=35)
        # условный горизонт
        p.t(self.x0 + 1.2, self.yt + 2.0, f'Усл. горизонт {alev(self.zc)}', 2.0, 'bl', 'НВК_текст')

    def vtext(self, row, s, txt, h=1.9):
        """Вертикальная надпись в строке row в точке s."""
        y0, y1 = self.row_y(row)
        self.p.t(self.X(s) + 0.8, (y0 + y1) / 2, txt, h, 'center', 'НВК_текст', rot=90)

    def ctext(self, row, s0, s1, txt, h=1.9):
        y0, y1 = self.row_y(row)
        self.p.t((self.X(s0) + self.X(s1)) / 2, (y0 + y1) / 2, txt, h, 'center', 'НВК_текст')

    def tick(self, row, s):
        y0, y1 = self.row_y(row)
        self.p.line(self.X(s), y0, self.X(s), y1, 'НВК_профиль')

    def ground(self, fn, s0, s1, layer='НВК_земля', ltype=None, step=0.25):
        pts = []
        s = s0
        while s <= s1 + 1e-9:
            pts.append((self.X(s), self.Y(fn(s))))
            s += step
        self.p.pl(pts, layer, ltype=ltype)
        return pts

    def pipe_line(self, s0, z0, s1, z1, od, layer, ltype=None, axis=False):
        """Труба: лоток и шелыга (или ось ± od/2 при axis)."""
        p = self.p
        if axis:
            for dz in (-od / 2, od / 2):
                p.pl([(self.X(s0), self.Y(z0 + dz)), (self.X(s1), self.Y(z1 + dz))], layer, ltype=ltype)
        else:
            p.pl([(self.X(s0), self.Y(z0)), (self.X(s1), self.Y(z1))], layer, ltype=ltype, lw=35)
            p.pl([(self.X(s0), self.Y(z0 + od)), (self.X(s1), self.Y(z1 + od))], layer, ltype=ltype, lw=18)

    def well(self, s, ztop, zbot, dn, label=None, exist=False):
        p = self.p
        w = max(1.6, dn / 1000 * 1000 / self.Kh)
        x = self.X(s)
        lay = 'НВК_сущ' if exist else 'НВК_колодцы'
        p.pl([(x - w / 2, self.Y(ztop)), (x - w / 2, self.Y(zbot)), (x + w / 2, self.Y(zbot)),
              (x + w / 2, self.Y(ztop))], lay, lw=35)
        p.line(x - w / 2 - 0.6, self.Y(ztop), x + w / 2 + 0.6, self.Y(ztop), lay, lw=50)
        p.line(x, self.Y(zbot), x, self.yt, 'НВК_профиль', ltype='ОВ_ШП')
        if label:
            p.t(x, self.Y(ztop) + 3.0, label, 2.2, 'bc', 'НВК_марки')
