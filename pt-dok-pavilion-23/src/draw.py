"""Примитивы для схем и узлов (координаты — мм листа от начала листа)."""
import math
from dxfkit import txt, mtxt, line, rect, ins

class D:
    def __init__(self, msp, ox, oy, k=1.0):
        self.m, self.ox, self.oy, self.k = msp, ox, oy, k
    def P(self, x, y):
        return (self.ox + x * self.k, self.oy + y * self.k)
    # --- базовые
    def l(self, x1, y1, x2, y2, layer='ПТ_контур', lw=None, lt=None, color=None):
        a = {'layer': layer}
        if lw is not None: a['lineweight'] = lw
        if lt: a['linetype'] = lt
        if color is not None: a['color'] = color
        return self.m.add_line(self.P(x1, y1), self.P(x2, y2), dxfattribs=a)
    def pl(self, pts, layer='ПТ_контур', lw=None, close=False, lt=None):
        a = {'layer': layer}
        if lw is not None: a['lineweight'] = lw
        if lt: a['linetype'] = lt
        return self.m.add_lwpolyline([self.P(x, y) for x, y in pts], close=close, dxfattribs=a)
    def r(self, x0, y0, x1, y1, layer='ПТ_контур', lw=None, lt=None):
        return self.pl([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, lw, True, lt)
    def c(self, x, y, rr, layer='ПТ_контур', lw=None):
        a = {'layer': layer}
        if lw is not None: a['lineweight'] = lw
        return self.m.add_circle(self.P(x, y), rr * self.k, dxfattribs=a)
    def t(self, x, y, s, h=2.5, align='BL', rot=0, style='ПТ', layer='ПТ_текст'):
        return txt(self.m, *self.P(x, y), s, h, self.k, layer=layer, align=align, rot=rot, style=style)
    def mt(self, x, y, s, h=2.5, w=100, attach=1, spacing=1.0):
        return mtxt(self.m, *self.P(x, y), s.replace('\n', '\\P'), h, w, self.k, attach=attach, spacing=spacing)
    def b(self, name, x, y, sc=1.0, rot=0, layer='ПТ_арматура'):
        return ins(self.m, name, *self.P(x, y), self.k * sc, rot=rot, layer=layer)
    def hatch(self, pts, pattern='ANSI31', scale=0.5, color=8, solid=False):
        h = self.m.add_hatch(color=color, dxfattribs={'layer': 'ПТ_штриховка'})
        h.paths.add_polyline_path([self.P(x, y) for x, y in pts], is_closed=True)
        if solid:
            h.set_solid_fill(color=color)
        else:
            h.set_pattern_fill(pattern, scale=scale * self.k, color=color)
        return h
    # --- трубы на схемах (одна линия)
    def pipe(self, pts, layer='ПТ_В21', lw=50):
        return self.pl(pts, layer=layer, lw=lw)
    def valve(self, x, y, kind='V_GATE', rot=0, sc=1.0, tag=None, tag_dy=3.5):
        self.b(kind, x, y, sc, rot)
        if tag:
            if rot in (90, 270):
                self.t(x + 3.5 * sc, y, tag, 2.0, 'ML')
            else:
                self.t(x, y + tag_dy * sc, tag, 2.0, 'BC')
    def leader(self, x1, y1, x2, y2, s, h=2.2, right=True):
        self.l(x1, y1, x2, y2, 'ПТ_выноски')
        w = max(8, len(s) * h * 0.55)
        if right:
            self.l(x2, y2, x2 + w, y2, 'ПТ_выноски'); self.t(x2 + 0.5, y2 + 0.6, s, h)
        else:
            self.l(x2, y2, x2 - w, y2, 'ПТ_выноски'); self.t(x2 - w + 0.5, y2 + 0.6, s, h)
    def pos(self, x1, y1, x2, y2, n, h=2.5):
        """выноска с номером позиции в кружке"""
        self.l(x1, y1, x2, y2, 'ПТ_выноски')
        self.c(x2, y2, 2.6, 'ПТ_выноски')
        self.t(x2, y2, str(n), h, 'MC')
    def dimh(self, x1, x2, y, s=None, h=2.0, ext_from=None):
        self.l(x1, y, x2, y, 'ПТ_размеры')
        for x in (x1, x2):
            self.l(x - 0.8, y - 0.8, x + 0.8, y + 0.8, 'ПТ_размеры', lw=25)
            if ext_from is not None:
                self.l(x, ext_from, x, y + 1.5 if y > ext_from else y - 1.5, 'ПТ_размеры')
        self.t((x1 + x2) / 2, y + 0.6, s if s is not None else '', h, 'BC')
    def dimv(self, y1, y2, x, s=None, h=2.0, ext_from=None):
        self.l(x, y1, x, y2, 'ПТ_размеры')
        for y in (y1, y2):
            self.l(x - 0.8, y - 0.8, x + 0.8, y + 0.8, 'ПТ_размеры', lw=25)
            if ext_from is not None:
                self.l(ext_from, y, x + 1.5 if x > ext_from else x - 1.5, y, 'ПТ_размеры')
        self.t(x - 0.6, (y1 + y2) / 2, s if s is not None else '', h, 'BC', rot=90)
    def elev(self, x, y, s, h=2.2, left=False):
        self.pl([(x, y), (x - 1.2, y + 1.6), (x + 1.2, y + 1.6)], 'ПТ_текст', close=True)
        if left:
            self.l(x, y + 1.6, x - 14, y + 1.6, 'ПТ_текст'); self.t(x - 14, y + 2.2, s, h)
        else:
            self.l(x, y + 1.6, x + 14, y + 1.6, 'ПТ_текст'); self.t(x + 0.5, y + 2.2, s, h)
    def title(self, x, y, s, h=3.5, scale=None):
        self.t(x, y, s + (f'  М {scale}' if scale else ''), h, 'BC', style='ПТ_загл')
        w = len(s + (f'  М {scale}' if scale else '')) * h * 0.55
        self.l(x - w / 2, y - 1.2, x + w / 2, y - 1.2, 'ПТ_контур', lw=35)
    # --- двухлинейная труба (для узлов) вдоль оси
    def tube(self, x1, y1, x2, y2, d, layer='ПТ_контур', lw=35, cl=True):
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        nx, ny = -dy / L * d / 2, dx / L * d / 2
        self.l(x1 + nx, y1 + ny, x2 + nx, y2 + ny, layer, lw)
        self.l(x1 - nx, y1 - ny, x2 - nx, y2 - ny, layer, lw)
        if cl:
            self.l(x1 - dx / L * 2, y1 - dy / L * 2, x2 + dx / L * 2, y2 + dy / L * 2, 'ПТ_оси', 13, 'ПТ_ШТРИХПУНКТ')
    def wall(self, x0, y0, x1, y1, pattern='ANSI31', scale=0.6):
        self.r(x0, y0, x1, y1, 'ПТ_контур', 35)
        self.hatch([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], pattern, scale)
    def table(self, x, y_top, cols, rows, h=2.2, row_h=6, header_h=None):
        from dxfkit import table as tb
        yb = tb(self.m, self.ox + x * self.k, self.oy + y_top * self.k, cols, rows, k=self.k, h=h, row_h=row_h, header_h=header_h)
        return (yb - self.oy) / self.k
