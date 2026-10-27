"""И05.09.26-ТМ: чертежи из 3D-модели котельной (tm_model) — проекции, условные знаки, подписи.

Планы, разрезы и аксонометрия не рисуются руками: каждая труба, арматура и корпус берутся из модели
и проецируются на плоскость вида. Поправили модель — пересобрали листы, расхождений нет.
Рисование — прямо на листе (мм листа), масштаб вида 1:K.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'sheets'))
from rdbase import DPlan, fmt_num  # noqa: E402
import tm_model as TM  # noqa: E402

CODE_TM = 'И05.09.26-ТМ'
BLD_TM = 'Тепломеханические решения котельной'
TM_LIST = {
    1: 'Общие данные',
    2: 'Котельная. Планы на отм. 0,000 и выше +2,000',
    3: 'Котельная. Разрезы 1-1, 2-2',
    4: 'Котельная. Разрезы 3-3, 4-4',
    5: 'Котельная. Аксонометрическая схема трубопроводов',
    6: 'Котельная. 3D-виды модели',
}
TM_TOTAL = len(TM_LIST)

LAYERS_TM = {   # слой: (ACI, вес 1/100 мм)
    'ТМ_Т1': (1, 50), 'ТМ_Т2': (5, 50), 'ТМ_Т11': (30, 50), 'ТМ_Т21': (4, 50),
    'ТМ_Т3': (3, 35), 'ТМ_Т4': (82, 35), 'ТМ_В1': (150, 35), 'ТМ_Г': (42, 35), 'ТМ_Д': (8, 35),
    'ТМ_оборуд': (7, 35), 'ТМ_оборуд_тонк': (8, 18), 'ТМ_арматура': (7, 25), 'ТМ_марки': (7, 18),
    'ТМ_текст': (7, 18), 'ТМ_размеры': (7, 13), 'ТМ_стены': (7, 50), 'ТМ_штрих': (8, 13), 'ТМ_ОВ': (8, 13),
    'ТМ_оси': (7, 13), 'ТМ_разрезы': (7, 50), 'ТМ_К': (8, 25),
}
PIPE_STYLE = {  # система: (слой, тип линии)
    'Т1': ('ТМ_Т1', None), 'Т2': ('ТМ_Т2', 'ОВ_ШТРИХ'), 'Т11': ('ТМ_Т11', None), 'Т21': ('ТМ_Т21', 'ОВ_ШТРИХ'),
    'Т3': ('ТМ_Т3', None), 'Т4': ('ТМ_Т4', 'ОВ_ШТРИХ'), 'В1': ('ТМ_В1', None), 'Г': ('ТМ_Г', 'ОВ_ШП'),
    'Д': ('ТМ_Д', None), 'К': ('ТМ_К', 'ОВ_ПУНКТ'),
}
C45 = math.cos(math.radians(45))


def f1(v, d=1):
    return fmt_num(v, d)


def lev(z):
    """Отметка: +2,900 / ±0,000 / -0,100."""
    if abs(z) < 5e-4:
        return '±0,000'
    return ('+' if z > 0 else '−') + f'{abs(z):.3f}'.replace('.', ',')


def setup_layers(doc):
    for n, (c, lw) in LAYERS_TM.items():
        if n not in doc.layers:
            doc.layers.add(n, color=c, lineweight=lw)


class PP(DPlan):
    """Рисование на листе в мм; штриховые линии — в масштабе листа (как листы 7, 8 ОВ)."""

    def __init__(self, doc, lay):
        super().__init__(doc, k=1, space=lay, unit=1.0)

    def _attrs(self, layer, color=None, lw=None, ltype=None, ltscale=None):
        a = super()._attrs(layer, color, lw, None)
        if ltype:
            a['linetype'] = ltype
            a['ltscale'] = ltscale or 0.01
        return a


# ====================================================================================== вид
class View:
    """Проекция модели на лист. kind: plan — сверху; N, S, W, E — разрез с видом на север/юг/запад/восток;
    axo — фронтальная изометрия (x вправо, y под 45° вправо-вверх, z вверх, коэффициенты 1).
    (u0, v0) — точка модели (в координатах вида, м), которая встаёт в org (мм листа).
    keep(p0, p1) -> отрезок или None: отсечение вида (диапазон отметок плана, плоскость разреза)."""

    def __init__(self, kind, K, org, u0v0, zr=None, cut=None, far=None):
        self.kind, self.K, self.org, self.u0, self.v0 = kind, K, org, u0v0[0], u0v0[1]
        self.zr, self.cut, self.far = zr, cut, far
        self.s = 1000.0 / K

    def uvm(self, p):
        x, y, z = p
        k = self.kind
        if k == 'plan':
            return x, y
        if k == 'N':
            return x, z
        if k == 'S':
            return -x, z
        if k == 'W':
            return y, z
        if k == 'E':
            return -y, z
        return x + y * C45, z + y * C45

    def P(self, p):
        u, v = self.uvm(p)
        return (self.org[0] + (u - self.u0) * self.s, self.org[1] + (v - self.v0) * self.s)

    def depth(self, p):
        """Больше — дальше от смотрящего."""
        x, y, z = p
        return {'plan': -z, 'N': y, 'S': -y, 'W': -x, 'E': x, 'axo': y}[self.kind]

    def axis_vis(self, ax):
        """Ось модели ('x','y','z') видна на виде как линия (а не точка)?"""
        return {'plan': ax in 'xy', 'N': ax in 'xz', 'S': ax in 'xz', 'W': ax in 'yz', 'E': ax in 'yz',
                'axo': True}[self.kind]

    def clip(self, p0, p1):
        """Отсечение отрезка: по отметкам (план) и плоскостью разреза (оставляем часть за плоскостью)."""
        a, b = list(p0), list(p1)
        if self.zr is not None:
            lo, hi = self.zr
            a, b = _clip_axis(a, b, 2, lo, hi)
            if a is None:
                return None
        if self.cut is not None:
            k = self.kind
            far = self.far
            if k == 'N':
                a, b = _clip_axis(a, b, 1, self.cut, far if far is not None else 1e9)
            elif k == 'S':
                a, b = _clip_axis(a, b, 1, far if far is not None else -1e9, self.cut)
            elif k == 'W':
                a, b = _clip_axis(a, b, 0, far if far is not None else -1e9, self.cut)
            elif k == 'E':
                a, b = _clip_axis(a, b, 0, self.cut, far if far is not None else 1e9)
            if a is None:
                return None
        return tuple(a), tuple(b)

    def in_view_box(self, bb):
        """Корпус (x0,y0,z0,x1,y1,z1) попадает в вид (хотя бы частью)?"""
        x0, y0, z0, x1, y1, z1 = bb
        if self.zr is not None and (z1 < self.zr[0] or z0 > self.zr[1]):
            return False
        if self.cut is not None:
            k = self.kind
            if k == 'N' and y1 < self.cut or k == 'S' and y0 > self.cut or k == 'W' and x0 > self.cut or \
                    k == 'E' and x1 < self.cut:
                return False
        return True


def _clip_axis(a, b, i, lo, hi):
    if a is None:
        return None, None
    da = b[i] - a[i]
    t0, t1 = 0.0, 1.0
    if abs(da) < 1e-12:
        if a[i] < lo - 1e-9 or a[i] > hi + 1e-9:
            return None, None
        return a, b
    ta, tb = (lo - a[i]) / da, (hi - a[i]) / da
    tmin, tmax = min(ta, tb), max(ta, tb)
    t0, t1 = max(t0, tmin), min(t1, tmax)
    if t1 < t0 - 1e-9:
        return None, None
    A = [a[k] + (b[k] - a[k]) * t0 for k in range(3)]
    B = [a[k] + (b[k] - a[k]) * t1 for k in range(3)]
    return A, B


# ====================================================================================== подписи без наложений
def pair_sub(P, ids, a, b):
    """Подпись отметки для полки пары труб: «ось …» или «оси … / …», если вторая труба пары идёт рядом
    параллельно на другой высоте (Н6: подача и обратка разведены по высоте)."""
    z = a[2]
    best = None
    if len(ids) > 1 and ids[1] in P:
        ux, uy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(ux, uy)
        if L > 1e-6:
            ux, uy = ux / L, uy / L
            for c, d in zip(P[ids[1]].pts, P[ids[1]].pts[1:]):
                if abs(c[2] - d[2]) > 1e-6:
                    continue
                vx, vy = d[0] - c[0], d[1] - c[1]
                M = math.hypot(vx, vy)
                if M < 0.05 or abs(ux * vy - uy * vx) / M > 0.05:      # не параллельна
                    continue
                if abs((c[0] - a[0]) * uy - (c[1] - a[1]) * ux) > 0.20:  # дальше 0,2 м в плане
                    continue
                s0 = (c[0] - a[0]) * ux + (c[1] - a[1]) * uy
                s1 = (d[0] - a[0]) * ux + (d[1] - a[1]) * uy
                ov = min(max(s0, s1), L) - max(min(s0, s1), 0.0)
                if ov <= 0.05:                                         # не перекрываются
                    continue
                if abs(c[2] - z) <= 0.005:
                    return 'ось ' + lev(z)                             # есть соседний участок на той же высоте
                best = max(best, (ov, c[2])) if best else (ov, c[2])
        if best:
            return f'оси {lev(z)} / {lev(best[1])}'
    return 'ось ' + lev(z)


class Labels:
    """Раскладка полок-выносок без наложений: занятые прямоугольники (мм листа) и рамка вида."""

    def __init__(self, p, frame):
        self.p, self.frame, self.busy = p, frame, []

    def free(self, r, pad=0.6):
        x0, y0, x1, y1 = r
        fx0, fy0, fx1, fy1 = self.frame
        if x0 < fx0 or x1 > fx1 or y0 < fy0 or y1 > fy1:
            return False
        for b in self.busy:
            if x0 < b[2] + pad and x1 > b[0] - pad and y0 < b[3] + pad and y1 > b[1] - pad:
                return False
        return True

    def block(self, r):
        self.busy.append(r)

    def shelf(self, at, text, h=2.0, cands=None, sub=None, force=None, layer='ТМ_марки'):
        """Полка с выноской от точки at; кандидаты — смещения (dx, dy) полки от точки, мм."""
        p = self.p
        w = max(p.tw(text, h), p.tw(sub, h) if sub else 0) + 1.6
        top = h * 1.25 + 0.9
        bot = (h * 1.25 + 0.9) if sub else 0.4
        cands = force and [force] or cands or default_cands()
        for dx, dy in cands:
            x0 = at[0] + dx if dx >= 0 else at[0] + dx - w
            r = (x0, at[1] + dy - bot, x0 + w, at[1] + dy + top)
            if self.free(r) or (force is not None):
                self.block(r)
                y = at[1] + dy
                xe = x0 if dx >= 0 else x0 + w
                p.pl([at, (xe, y)], 'ТМ_марки')
                p.circle(at[0], at[1], 0, 'ТМ_марки', fill=7, r_paper=0.35)
                p.m.add_wipeout([(x0, y + 0.3), (x0 + w, y + top - 0.2)], dxfattribs={'layer': 'ТМ_марки'})
                if sub:
                    p.m.add_wipeout([(x0, y - bot + 0.2), (x0 + w, y - 0.3)], dxfattribs={'layer': 'ТМ_марки'})
                p.pl([(x0, y), (x0 + w, y)], 'ТМ_марки')
                p.t(x0 + 0.8, y + 0.8, text, h, 'bl', layer)
                if sub:
                    p.t(x0 + 0.8, y - 0.8, sub, h, 'tl', layer)
                return r
        return None


    def stack(self, at, lines, dx, dy, h=1.8, layer='ТМ_марки'):
        """Многополочная выноска: полки друг над другом (снизу вверх — порядок lines сверху вниз)."""
        p = self.p
        w = max(p.tw(t, h) for t in lines) + 1.6
        step = h * 1.25 + 1.6
        x0 = at[0] + dx if dx >= 0 else at[0] + dx - w
        y0 = at[1] + dy
        xe = x0 if dx >= 0 else x0 + w
        p.pl([at, (xe, y0)], 'ТМ_марки')
        p.circle(at[0], at[1], 0, 'ТМ_марки', fill=7, r_paper=0.35)
        n = len(lines)
        top = y0 + step * (n - 1) + h * 1.25 + 0.9
        p.m.add_wipeout([(x0, y0 + 0.3), (x0 + w, top)], dxfattribs={'layer': layer})
        p.line(xe, y0, xe, y0 + step * (n - 1), 'ТМ_марки')
        for i, t in enumerate(lines):
            y = y0 + step * (n - 1 - i)
            p.pl([(x0, y), (x0 + w, y)], 'ТМ_марки')
            p.t(x0 + 0.8, y + 0.8, t, h, 'bl', layer)
        r = (x0, y0 - 0.4, x0 + w, top)
        self.block(r)
        return r


def _seg_cross(a, b, c, d):
    def cr(o, p_, q):
        return (p_[0] - o[0]) * (q[1] - o[1]) - (p_[1] - o[1]) * (q[0] - o[0])
    return cr(c, d, a) * cr(c, d, b) < -1e-9 and cr(a, b, c) * cr(a, b, d) < -1e-9


def _seg_box(a, b, r, pad=0.2):
    """Отрезок a–b проходит через прямоугольник r (уменьшенный на pad)."""
    x0, y0, x1, y1 = r[0] + pad, r[1] + pad, r[2] - pad, r[3] - pad
    if x1 <= x0 or y1 <= y0:
        return False
    t0, t1 = 0.0, 1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    for p_, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if abs(p_) < 1e-12:
            if q < 0:
                return False
        else:
            t = q / p_
            if p_ < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
    return t0 < t1


class TMLabels(Labels):
    """Раскладка выносок листов ТМ: кроме свободной полки — выноска не пересекает другие выноски и чужие
    полки с текстом, точка выноски не попадает в чужой текст. Если так не выходит — как Labels (fallback)."""

    def __init__(self, p, frame):
        super().__init__(p, frame)
        self.texts, self.leads = [], []

    def _ok(self, at, end, r):
        for t in self.texts:
            if t[0] - 0.3 < at[0] < t[2] + 0.3 and t[1] - 0.3 < at[1] < t[3] + 0.3:
                return False
            if _seg_box(at, end, t):
                return False
        for c, d in self.leads:
            if _seg_cross(at, end, c, d):
                return False
        for c, d in self.leads:                     # чужая выноска через новую полку
            if _seg_box(c, d, r, pad=0.0):
                return False
        return True

    def shelf(self, at, text, h=2.0, cands=None, sub=None, force=None, layer='ТМ_марки', fallback=True):
        p = self.p
        w = max(p.tw(text, h), p.tw(sub, h) if sub else 0) + 1.6
        top = h * 1.25 + 0.9
        bot = (h * 1.25 + 0.9) if sub else 0.4
        pick = None
        if force is not None:
            pick = force
        else:
            for dx, dy in (cands or default_cands()):
                x0 = at[0] + dx if dx >= 0 else at[0] + dx - w
                r = (x0, at[1] + dy - bot, x0 + w, at[1] + dy + top)
                end = (x0 if dx >= 0 else x0 + w, at[1] + dy)
                if self.free(r) and self._ok(at, end, r):
                    pick = (dx, dy)
                    break
            if pick is None:
                if not fallback:
                    return None
                if fallback == 'soft' and any(t[0] - 0.3 < at[0] < t[2] + 0.3 and t[1] - 0.3 < at[1] < t[3] + 0.3
                                              for t in self.texts):
                    return None                     # точка выноски попала бы в чужой текст — пусть ищут другую
                r = super().shelf(at, text, h, cands=cands, sub=sub, layer=layer)
                if r:
                    self._note(at, r, bot)
                return r
        r = super().shelf(at, text, h, sub=sub, force=pick, layer=layer)
        dx, dy = pick
        self.texts.append(r)
        self.leads.append((tuple(at), (r[0] if dx >= 0 else r[2], at[1] + dy)))
        return r

    def _note(self, at, r, bot):
        """Учесть полку, поставленную базовым способом (fallback): выноска — к ближнему концу полки."""
        self.texts.append(r)
        xe = r[0] if abs(r[0] - at[0]) < abs(r[2] - at[0]) else r[2]
        self.leads.append((tuple(at), (xe, r[1] + bot)))

    def stack(self, at, lines, dx, dy, h=1.8, layer='ТМ_марки'):
        r = super().stack(at, lines, dx, dy, h=h, layer=layer)
        if r:
            self.texts.append(r)
            self.leads.append((tuple(at), (r[0] if dx >= 0 else r[2], r[1] + 0.4)))
        return r


def default_cands():
    out = []
    for r in (9, 14, 20, 27, 35):
        for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1), (0.4, 1), (-0.4, 1), (0.4, -1), (-0.4, -1)):
            out.append((dx * r, dy * r * 0.8))
    return out


# ====================================================================================== условные знаки
def unit(a, b):
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    return ((b[0] - a[0]) / L, (b[1] - a[1]) / L) if L > 1e-9 else (1.0, 0.0)


def bow(p, c, d, s=1.5, w=1.1, fill=None, layer='ТМ_арматура', mask=True):
    """Знак вентиля/крана: два треугольника вершинами в центре, d — направление трубы на листе."""
    n = (-d[1], d[0])
    t1 = [c, (c[0] - d[0] * s + n[0] * w, c[1] - d[1] * s + n[1] * w),
          (c[0] - d[0] * s - n[0] * w, c[1] - d[1] * s - n[1] * w)]
    t2 = [c, (c[0] + d[0] * s + n[0] * w, c[1] + d[1] * s + n[1] * w),
          (c[0] + d[0] * s - n[0] * w, c[1] + d[1] * s - n[1] * w)]
    if mask:
        poly_wipe(p, t1 + [t2[1], t2[2]][::-1])
    p.poly(t1, layer, fill=7 if fill == 1 else None)
    p.poly(t2, layer, fill=7 if fill == 2 else None)


def poly_wipe(p, pts):
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    p.m.add_wipeout([(min(xs), min(ys)), (max(xs), max(ys))], dxfattribs={'layer': 'ТМ_арматура'})


def sym_fit(p, V, f, scale=1.0):
    """Арматура на виде: знак по ГОСТ 21.205 (упрощённо), ориентирован по трубе."""
    if not V.axis_vis(f.axis):
        return False
    a, b = _seg_of(f)
    c = V.P(f.pos)
    pa, pb = V.P(a), V.P(b)
    d = unit(pa, pb)
    if math.hypot(pb[0] - pa[0], pb[1] - pa[1]) < 1e-6:
        return False
    n = (-d[1], d[0])
    s = 1.5 * scale
    k = f.kind
    side = _side_dir(V, f, n)
    if k in ('ball', 'gas'):
        bow(p, c, d, s, 1.1 * scale)
        p.circle(c[0], c[1], 0, 'ТМ_арматура', fill=7, r_paper=0.5 * scale)
    elif k == 'check':
        bow(p, c, d, s, 1.1 * scale, fill=2)
    elif k == 'balance':
        bow(p, c, d, s, 1.1 * scale)
        p.line(c[0] - d[0] * 2 - n[0] * 1.6, c[1] - d[1] * 2 - n[1] * 1.6, c[0] + d[0] * 2 + n[0] * 1.6,
               c[1] + d[1] * 2 + n[1] * 1.6, 'ТМ_арматура')
    elif k == 'three':
        bow(p, c, d, s, 1.1 * scale)
        t = [c, (c[0] + side[0] * s + d[0] * 1.1, c[1] + side[1] * s + d[1] * 1.1),
             (c[0] + side[0] * s - d[0] * 1.1, c[1] + side[1] * s - d[1] * 1.1)]
        p.poly(t, 'ТМ_арматура')
        q = (c[0] - side[0] * 2.4, c[1] - side[1] * 2.4)
        p.line(c[0], c[1], q[0], q[1], 'ТМ_арматура')
        p.circle(q[0] - side[0] * 1.0, q[1] - side[1] * 1.0, 0, 'ТМ_арматура', r_paper=1.0)
    elif k == 'pump':
        r = 2.0 * scale
        p.m.add_wipeout([(c[0] - r, c[1] - r), (c[0] + r, c[1] + r)], dxfattribs={'layer': 'ТМ_арматура'})
        p.circle(c[0], c[1], 0, 'ТМ_арматура', r_paper=r)
        fd = d if _flow_sign(f) > 0 else (-d[0], -d[1])
        tip = (c[0] + fd[0] * r, c[1] + fd[1] * r)
        b1 = (c[0] - fd[0] * r * 0.5 + n[0] * r * 0.85, c[1] - fd[1] * r * 0.5 + n[1] * r * 0.85)
        b2 = (c[0] - fd[0] * r * 0.5 - n[0] * r * 0.85, c[1] - fd[1] * r * 0.5 - n[1] * r * 0.85)
        p.pl([b1, tip, b2], 'ТМ_арматура')
    elif k == 'filter':
        q = [(c[0] - d[0] * 1.6 - n[0] * 1.1, c[1] - d[1] * 1.6 - n[1] * 1.1),
             (c[0] + d[0] * 1.6 - n[0] * 1.1, c[1] + d[1] * 1.6 - n[1] * 1.1),
             (c[0] + d[0] * 1.6 + n[0] * 1.1, c[1] + d[1] * 1.6 + n[1] * 1.1),
             (c[0] - d[0] * 1.6 + n[0] * 1.1, c[1] - d[1] * 1.6 + n[1] * 1.1)]
        poly_wipe(p, q)
        p.poly(q, 'ТМ_арматура')
        p.line(q[0][0], q[0][1], q[2][0], q[2][1], 'ТМ_арматура')
    elif k == 'reducer':
        q = [(c[0] - d[0] * 1.6 - n[0] * 1.2, c[1] - d[1] * 1.6 - n[1] * 1.2),
             (c[0] + d[0] * 1.6 - n[0] * 0.6, c[1] + d[1] * 1.6 - n[1] * 0.6),
             (c[0] + d[0] * 1.6 + n[0] * 0.6, c[1] + d[1] * 1.6 + n[1] * 0.6),
             (c[0] - d[0] * 1.6 + n[0] * 1.2, c[1] - d[1] * 1.6 + n[1] * 1.2)]
        poly_wipe(p, q)
        p.poly(q, 'ТМ_арматура')
    elif k == 'dirt':
        L = 0.28 * V.s / 2
        q = [(c[0] - d[0] * L - n[0] * 1.6, c[1] - d[1] * L - n[1] * 1.6),
             (c[0] + d[0] * L - n[0] * 1.6, c[1] + d[1] * L - n[1] * 1.6),
             (c[0] + d[0] * L + n[0] * 1.6, c[1] + d[1] * L + n[1] * 1.6),
             (c[0] - d[0] * L + n[0] * 1.6, c[1] - d[1] * L + n[1] * 1.6)]
        poly_wipe(p, q)
        p.poly(q, 'ТМ_арматура')
        p.t(c[0], c[1], 'ШО', 1.4, 'center', 'ТМ_арматура', rot=_rot(d))
    elif k == 'safety':
        bow(p, c, d, s, 1.1 * scale)
        e = (c[0] + side[0] * 2.2, c[1] + side[1] * 2.2)
        p.line(c[0], c[1], e[0], e[1], 'ТМ_арматура')
        p.pl([e, (e[0] + side[0] * 0.6 + d[0] * 0.6, e[1] + side[1] * 0.6 + d[1] * 0.6),
              (e[0] + side[0] * 1.2, e[1] + side[1] * 1.2),
              (e[0] + side[0] * 1.8 + d[0] * 0.6, e[1] + side[1] * 1.8 + d[1] * 0.6),
              (e[0] + side[0] * 2.4, e[1] + side[1] * 2.4)], 'ТМ_арматура')
    elif k == 'mano':
        e = (c[0] + side[0] * 2.0, c[1] + side[1] * 2.0)
        p.line(c[0], c[1], e[0], e[1], 'ТМ_арматура')
        p.circle(e[0] + side[0] * 1.0, e[1] + side[1] * 1.0, 0, 'ТМ_арматура', r_paper=1.0)
    elif k == 'therm':
        e = (c[0] + side[0] * 1.6, c[1] + side[1] * 1.6)
        p.line(c[0], c[1], e[0], e[1], 'ТМ_арматура')
        q = [(e[0] - d[0] * 0.5, e[1] - d[1] * 0.5), (e[0] + d[0] * 0.5, e[1] + d[1] * 0.5),
             (e[0] + d[0] * 0.5 + side[0] * 1.6, e[1] + d[1] * 0.5 + side[1] * 1.6),
             (e[0] - d[0] * 0.5 + side[0] * 1.6, e[1] - d[1] * 0.5 + side[1] * 1.6)]
        p.poly(q, 'ТМ_арматура')
    elif k == 'vent':
        e = (c[0] + side[0] * 1.6, c[1] + side[1] * 1.6)
        p.line(c[0], c[1], e[0], e[1], 'ТМ_арматура')
        q = [(e[0] - d[0] * 0.9, e[1] - d[1] * 0.9), (e[0] + d[0] * 0.9, e[1] + d[1] * 0.9),
             (e[0] + d[0] * 0.9 + side[0] * 1.4, e[1] + d[1] * 0.9 + side[1] * 1.4),
             (e[0] + side[0] * 2.2, e[1] + side[1] * 2.2),
             (e[0] - d[0] * 0.9 + side[0] * 1.4, e[1] - d[1] * 0.9 + side[1] * 1.4)]
        p.poly(q, 'ТМ_арматура')
    elif k == 'drain':
        e = (c[0] + side[0] * 1.2, c[1] + side[1] * 1.2)
        p.line(c[0], c[1], e[0], e[1], 'ТМ_арматура')
        cc = (c[0] + side[0] * 2.4, c[1] + side[1] * 2.4)
        bow(p, cc, side, 1.1, 0.8)
        p.circle(cc[0], cc[1], 0, 'ТМ_арматура', fill=7, r_paper=0.4)
    else:
        bow(p, c, d, s, 1.1 * scale)
    return True


def _rot(d):
    a = math.degrees(math.atan2(d[1], d[0]))
    if a > 90.01 or a < -89.99:
        a += 180
    return a


def _seg_of(f):
    from tm_model import point_on_seg
    for a, b in zip(f.pipe.pts, f.pipe.pts[1:]):
        if point_on_seg(f.pos, a, b):
            return a, b
    return f.pipe.pts[0], f.pipe.pts[1]


def _flow_sign(f):
    """Поток идёт по порядку точек трубы (подача — от источника, обратка — к источнику)."""
    return 1


def _side_dir(V, f, n):
    if not f.side:
        return n
    sd = {'+x': (1, 0, 0), '-x': (-1, 0, 0), '+y': (0, 1, 0), '-y': (0, -1, 0), '+z': (0, 0, 1),
          '-z': (0, 0, -1)}[f.side]
    a = V.P(f.pos)
    b = V.P(tuple(f.pos[k] + sd[k] * 0.1 for k in range(3)))
    if math.hypot(b[0] - a[0], b[1] - a[1]) < 0.3:       # «ручка» смотрит на нас — рисуем по нормали
        return n
    return unit(a, b)


# ====================================================================================== рисование вида
def draw_pipes(p, V, pipes, lw=None, ctx=False):
    """Трубы одной линией; уходящие от смотрящего (точка на виде) — кружок стояка."""
    out = []
    for pp in pipes:
        lay, lt = PIPE_STYLE[pp.sys]
        for a, b in zip(pp.pts, pp.pts[1:]):
            c = V.clip(a, b)
            if c is None:
                continue
            A, B = V.P(c[0]), V.P(c[1])
            L = math.hypot(B[0] - A[0], B[1] - A[1])
            if L < 0.05:
                if math.dist(c[0], c[1]) > 0.02:             # стояк
                    p.circle(A[0], A[1], 0, lay, r_paper=max(0.8, pp.od * V.s / 2))
                continue
            if pp.sys == 'Д':                                  # дымоходы — контуром в масштабе
                w = pp.od * V.s / 2
                d = unit(A, B)
                n = (-d[1], d[0])
                q = [(A[0] + n[0] * w, A[1] + n[1] * w), (B[0] + n[0] * w, B[1] + n[1] * w),
                     (B[0] - n[0] * w, B[1] - n[1] * w), (A[0] - n[0] * w, A[1] - n[1] * w)]
                p.m.add_wipeout([min(q), max(q)], dxfattribs={'layer': lay}) if False else None
                p.pl(q, lay, closed=True)
                p.pl([A, B], 'ТМ_оси', ltype='ОВ_ШП', lw=13)
            else:
                p.pl([A, B], lay, ltype=lt, lw=lw)
            out.append((pp, c, A, B))
    return out


def eq_outline(V, e):
    """Контур корпуса на виде: ('rect', x0, y0, x1, y1) или ('circle', cx, cy, r) в мм листа."""
    if e.kind == 'box':
        x0, y0, z0, x1, y1, z1 = e.g
        pts = [V.P((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    elif e.kind == 'cyl':
        cx, cy, r, z0, z1 = e.g
        if V.kind == 'plan':
            c = V.P((cx, cy, z1))
            return ('circle', c[0], c[1], r * V.s)
        pts = [V.P((cx + dx, cy + dy, z)) for dx in (-r, r) for dy in (-r, r) for z in (z0, z1)]
        if V.kind == 'axo':
            return ('cylv', V.P((cx, cy, z0)), V.P((cx, cy, z1)), r * V.s)
    else:
        x, ya, z, yb, r = e.g
        if V.kind in ('N', 'S'):
            c = V.P((x, ya, z))
            return ('circle', c[0], c[1], r * V.s)
        pts = [V.P((x + dx, y, z + dz)) for dx in (-r, r) for y in (ya, yb) for dz in (-r, r)]
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    if V.kind == 'axo' and e.kind == 'box':
        return ('boxaxo', e.g)
    return ('rect', min(xs), min(ys), max(xs), max(ys))


def draw_eq(p, V, e, layer='ТМ_оборуд', mask=True, ltype=None):
    o = eq_outline(V, e)
    if o[0] == 'rect':
        _, x0, y0, x1, y1 = o
        if mask:
            p.m.add_wipeout([(x0, y0), (x1, y1)], dxfattribs={'layer': layer})
        p.rect(x0, y0, x1, y1, layer, ltype=ltype)
    elif o[0] == 'circle':
        _, cx, cy, r = o
        if mask:
            p.m.add_wipeout([(cx - r * 0.7, cy - r * 0.7), (cx + r * 0.7, cy + r * 0.7)],
                            dxfattribs={'layer': layer})
        c_ = p.circle(cx, cy, 0, layer, r_paper=r, color=None)
        if ltype:
            c_.dxf.linetype = ltype
            c_.dxf.ltscale = 0.004                   # штрих ≈1,3 мм: на малом кружке иначе выходит сплошная
    elif o[0] == 'cylv':
        _, a, b, r = o
        rr = r
        p.pl([(a[0] - rr, a[1]), (b[0] - rr, b[1])], layer)
        p.pl([(a[0] + rr, a[1]), (b[0] + rr, b[1])], layer)
        ell(p, a, rr, layer, half=True)
        ell(p, b, rr, layer)
    elif o[0] == 'boxaxo':
        x0, y0, z0, x1, y1, z1 = o[1]
        P = lambda x, y, z: V.P((x, y, z))
        front = [P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), P(x0, y0, z1)]
        p.pl(front, layer, closed=True)
        p.pl([P(x0, y0, z1), P(x0, y1, z1), P(x1, y1, z1), P(x1, y0, z1)], layer)
        p.pl([P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1)], layer)
    return o


def ell(p, c, r, layer, half=False):
    """Эллипс горизонтального круга во фронтальной изометрии: оси r и r·cos45 по 45° — упрощённо окружность
    по горизонтали r, по вертикали 0,35r."""
    n = 24
    pts = []
    for i in range(n + 1):
        t = math.pi * 2 * i / n
        if half and math.sin(t) > 0.05:
            continue
        pts.append((c[0] + r * math.cos(t), c[1] + 0.35 * r * math.sin(t)))
    if len(pts) > 1:
        p.pl(pts, layer)


def walls_plan(p, V, walls):
    for wl in walls:
        pts = [V.P((x, y, 0)) for x, y in wl['outer']]
        p.poly(pts, 'ТМ_штрих', hatch=('ANSI31', 70.0, 0, 8), outline=False)
        p.pl(pts, 'ТМ_стены', closed=True)


def dim_h(p, x0, x1, y, yref0=None, yref1=None, txt=None, h=2.2):
    """Горизонтальный размер на листе: линия на высоте y, выносные от yref, засечки 45°."""
    lay = 'ТМ_размеры'
    for x, yr in ((x0, yref0), (x1, yref1)):
        if yr is not None:
            p.line(x, yr + (1.5 if y > yr else -1.5), x, y + (1.5 if y > yr else -1.5), lay)
        p.line(x - 1.0, y - 1.0, x + 1.0, y + 1.0, lay, lw=35)
    p.line(min(x0, x1) - 1.5, y, max(x0, x1) + 1.5, y, lay)
    if txt:
        p.t((x0 + x1) / 2, y + 0.8, txt, h, 'bc', 'ТМ_размеры')


def dim_v(p, y0, y1, x, xref0=None, xref1=None, txt=None, h=2.2):
    lay = 'ТМ_размеры'
    for y, xr in ((y0, xref0), (y1, xref1)):
        if xr is not None:
            p.line(xr + (1.5 if x > xr else -1.5), y, x + (1.5 if x > xr else -1.5), y, lay)
        p.line(x - 1.0, y - 1.0, x + 1.0, y + 1.0, lay, lw=35)
    p.line(x, min(y0, y1) - 1.5, x, max(y0, y1) + 1.5, lay)
    if txt:
        p.t(x - 0.8, (y0 + y1) / 2, txt, h, 'bc', 'ТМ_размеры', rot=90)


def mm(v):
    return str(int(round(v * 1000)))


def level_mark(p, x, y, z, right=True, h=2.0, L=None, layer='ТМ_размеры'):
    """Знак отметки (ГОСТ 2.307): стрелка 90° на линии, выноска вверх, полка с отметкой."""
    s = 1.3
    p.pl([(x - s, y + s), (x, y), (x + s, y + s)], layer)
    p.line(x, y, x, y + 4.0, layer)
    t = lev(z)
    w = L or p.tw(t, h) + 1.2
    x1 = x + w if right else x - w
    p.line(x, y + 4.0, x1, y + 4.0, layer)
    p.t(x + 0.6 if right else x - 0.6, y + 4.6, t, h, 'bl' if right else 'br', layer)


def axis_bubble(p, x, y, name, r=4.0):
    p.circle(x, y, 0, 'ТМ_оси', r_paper=r)
    p.t(x, y, name, 3.0, 'center', 'ТМ_оси')


def cut_mark(p, a, b, name, look, h=4.0):
    """Линия разреза (ГОСТ 2.305): штрихи на концах, стрелки взгляда, номер."""
    d = unit(a, b)
    L = 7.0
    for q, sgn in ((a, 1), (b, -1)):
        e = (q[0] + d[0] * L * sgn, q[1] + d[1] * L * sgn)
        p.pl([q, e], 'ТМ_разрезы', lw=70)
        ln = look
        tip = (q[0] + ln[0] * 6.0, q[1] + ln[1] * 6.0)
        p.line(q[0], q[1], tip[0], tip[1], 'ТМ_разрезы', lw=25)
        n = (-ln[1], ln[0])
        p.poly([tip, (tip[0] - ln[0] * 2.2 + n[0] * 0.8, tip[1] - ln[1] * 2.2 + n[1] * 0.8),
                (tip[0] - ln[0] * 2.2 - n[0] * 0.8, tip[1] - ln[1] * 2.2 - n[1] * 0.8)], 'ТМ_разрезы', fill=7)
        tx = (q[0] + ln[0] * 3.0 - d[0] * 3.0 * sgn, q[1] + ln[1] * 3.0 - d[1] * 3.0 * sgn)
        p.t(tx[0], tx[1], name, h, 'center', 'ТМ_разрезы')
