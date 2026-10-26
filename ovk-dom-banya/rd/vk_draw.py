"""И05.09.26-ВК: общая часть листов — перечень листов, слои, стили труб, условные знаки, план из 3D-модели.

Все трубы, арматура и приборы берутся из модели vk_model и проецируются на лист (как в разделе ТМ):
подложка АР — видовой экран модели, сети ВК — в пространстве листа тем же масштабом и с тем же центром.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'sheets'))
import tm_draw as TD  # noqa: E402
from tm_draw import PP, View, Labels, sym_fit, draw_eq, unit, lev, f1, level_mark, bow, poly_wipe  # noqa: E402,F401
from rdbase import add_underlay, insert_underlay, UNDER  # noqa: E402
import vk_model as VK  # noqa: E402

CODE_VK = 'И05.09.26-ВК'
BLD_VK = 'Водопровод и канализация'
VK_LIST = {
    1: 'Общие данные (начало)',
    2: 'Общие данные (окончание). Условные обозначения',
    3: 'План 1 этажа. Водопровод В1, Т3, Т4',
    4: 'План 2 этажа: с/у 2.8, 2.9. Водопровод и канализация К1',
    5: 'Сети под потолком гаража: В1, Т3, Т4, К1',
    6: 'План 1 этажа. Канализация К1',
    7: 'Топочная 1.6. Ввод, водомерный узел, гребёнка КХ',
    8: 'Баня. План водопровода В1, Т3, Т4',
    9: 'Баня. План канализации К1',
    10: 'Схема систем В1, Т3, Т4 дома',
    11: 'Схема систем В1, Т3, Т4 бани',
    12: 'Схема системы К1',
    13: 'Схемы коллекторных шкафов ШВК-1, ШВК-2, ШВК-Б1, ШВК-Б2',
    14: 'Узлы и детали',
}
VK_TOTAL = len(VK_LIST)
LAYERS_VK = {
    'ВК_В1': (150, 35), 'ВК_Т3': (1, 35), 'ВК_Т4': (30, 35), 'ВК_К1': (34, 50), 'ВК_К1в': (34, 35),
    'ВК_Кд': (8, 25), 'ВК_ввод': (150, 50), 'ВК_К2': (5, 50), 'ВК_защита': (6, 25),
}
STYLE = {   # система: (слой, тип линии)
    'В1': ('ВК_В1', None), 'Т3': ('ВК_Т3', None), 'Т4': ('ВК_Т4', 'ОВ_ШТРИХ'), 'К1': ('ВК_К1', None),
    'К1в': ('ВК_К1в', 'ОВ_ШП'), 'Кд': ('ВК_Кд', 'ОВ_ПУНКТ'), 'К2': ('ВК_К2', 'ОВ_ШП'),
}
TD.PIPE_STYLE.update(STYLE)          # sym_fit/draw_pipes берут стиль отсюда
WHERE = {'floor': 'в полу', 'ceil': 'под потолком', 'wall': 'по стене', 'ground': 'в грунте', 'riser': 'стояк'}
DN_SHORT = {'16×2,2': '16', '20×2,8': '20', '25×3,5': '25', '32×4,4': '32'}


def setup(doc):
    TD.setup_layers(doc)
    for n, (c, lw) in LAYERS_VK.items():
        if n not in doc.layers:
            doc.layers.add(n, color=c, lineweight=lw)


def fix_glyphs(doc):
    """В ISOCPEUR нет знака минус U+2212 — заменить дефисом во всех надписях."""
    spaces = [doc.modelspace()] + [l for l in doc.layouts if l.name != 'Model'] + list(doc.blocks)
    for sp in spaces:
        for e in sp:
            t = e.dxftype()
            if t == 'TEXT' and '−' in e.dxf.text:
                e.dxf.text = e.dxf.text.replace('−', '-')
            elif t == 'MTEXT' and '−' in e.text:
                e.text = e.text.replace('−', '-')


def finish_layers(doc):
    """Служебные слои рисования ТМ_* -> ВК_* (в DWG — слои раздела ВК); замена неотображаемых знаков."""
    fix_glyphs(doc)
    for lay in list(doc.layers):
        n = lay.dxf.name
        if n.startswith('ТМ_'):
            new = 'ВК_' + n[3:]
            if new in doc.layers:
                continue
            try:
                lay.rename(new)
            except Exception:
                pass


def pid(i):
    return {p.id: p for p in VK.PIPES}[i]


def fits_of(pipes):
    ids = {p.id for p in pipes}
    return [f for f in VK.FITS if f.pipe.id in ids]


# ====================================================================================== знаки ВК
def vk_fit(p, V, f, scale=0.9):
    """Знаки арматуры ВК: общие — по sym_fit (ТМ), особые — счётчик, фильтр тонкой очистки, кран-водоразборный,
    ревизия, прочистка, вакуумный клапан."""
    k = f.kind
    if k in ('ball', 'check', 'balance', 'pump', 'filter', 'reducer', 'safety', 'mano'):
        return sym_fit(p, V, f, scale)
    if k == 'mvalve':                                  # кран шаровой с электроприводом: знак крана + привод «М»
        f.kind = 'ball'
        r = sym_fit(p, V, f, scale)
        f.kind = 'mvalve'
        a, b = TD._seg_of(f)
        c = V.P(f.pos)
        pa, pb = V.P(a), V.P(b)
        if math.hypot(pb[0] - pa[0], pb[1] - pa[1]) < 1e-6:
            d = (1.0, 0.0)
        else:
            d = unit(pa, pb)
        n = (-d[1], d[0])
        m = (c[0] + n[0] * 2.6, c[1] + n[1] * 2.6)
        p.line(c[0], c[1], c[0] + n[0] * 1.5, c[1] + n[1] * 1.5, 'ТМ_арматура')
        q = [(m[0] - 1.1, m[1] - 1.1), (m[0] + 1.1, m[1] - 1.1), (m[0] + 1.1, m[1] + 1.1), (m[0] - 1.1, m[1] + 1.1)]
        poly_wipe(p, q)
        p.poly(q, 'ТМ_арматура')
        p.t(m[0], m[1], 'М', 1.3, 'center', 'ТМ_арматура')
        return r
    if k == 'filter_fine':                             # фильтр тонкой очистки: знак фильтра с двумя диагоналями
        f.kind = 'filter'
        r = sym_fit(p, V, f, scale)
        f.kind = 'filter_fine'
        if r is not False:
            a, b = TD._seg_of(f)
            c, pa, pb = V.P(f.pos), V.P(a), V.P(b)
            d = unit(pa, pb)
            n = (-d[1], d[0])
            p.line(c[0] + d[0] * 1.6 - n[0] * 1.1, c[1] + d[1] * 1.6 - n[1] * 1.1,
                   c[0] - d[0] * 1.6 + n[0] * 1.1, c[1] - d[1] * 1.6 + n[1] * 1.1, 'ТМ_арматура')
        return r
    if k == 'air':
        f.kind = 'vent'
        r = sym_fit(p, V, f, scale)
        f.kind = 'air'
        return r
    a, b = TD._seg_of(f)
    c = V.P(f.pos)
    pa, pb = V.P(a), V.P(b)
    if math.hypot(pb[0] - pa[0], pb[1] - pa[1]) < 1e-6:
        d = (1.0, 0.0)
    else:
        d = unit(pa, pb)
    n = (-d[1], d[0])
    if k == 'meter':                                   # счётчик: прямоугольник с диагональю (ГОСТ 21.205)
        q = [(c[0] - d[0] * 2.0 - n[0] * 1.3, c[1] - d[1] * 2.0 - n[1] * 1.3),
             (c[0] + d[0] * 2.0 - n[0] * 1.3, c[1] + d[1] * 2.0 - n[1] * 1.3),
             (c[0] + d[0] * 2.0 + n[0] * 1.3, c[1] + d[1] * 2.0 + n[1] * 1.3),
             (c[0] - d[0] * 2.0 + n[0] * 1.3, c[1] - d[1] * 2.0 + n[1] * 1.3)]
        poly_wipe(p, q)
        p.poly(q, 'ТМ_арматура')
        p.line(q[0][0], q[0][1], q[2][0], q[2][1], 'ТМ_арматура')
        return True
    if k == 'tap':                                     # водоразборный кран: точка + короткий носик
        p.circle(c[0], c[1], 0, 'ТМ_арматура', fill=7, r_paper=0.6)
        p.line(c[0], c[1], c[0] + n[0] * 1.8, c[1] + n[1] * 1.8, 'ТМ_арматура')
        p.line(c[0] + n[0] * 1.8, c[1] + n[1] * 1.8, c[0] + n[0] * 1.8 + d[0] * 1.0,
               c[1] + n[1] * 1.8 + d[1] * 1.0, 'ТМ_арматура')
        return True
    if k == 'revision' and f.name.startswith('Прочистка'):  # прочистка в грунте с выводом в стену к люку — знак П
        k = 'cleanout'
    if k == 'revision':                                # ревизия: прямоугольник на трубе с буквой Р
        q = [(c[0] - 1.4, c[1] - 1.4), (c[0] + 1.4, c[1] - 1.4), (c[0] + 1.4, c[1] + 1.4), (c[0] - 1.4, c[1] + 1.4)]
        poly_wipe(p, q)
        p.poly(q, 'ТМ_арматура')
        p.t(c[0], c[1], 'Р', 1.6, 'center', 'ТМ_арматура')
        return True
    if k == 'cleanout':                                # прочистка: кружок с П
        p.m.add_wipeout([(c[0] - 1.4, c[1] - 1.4), (c[0] + 1.4, c[1] + 1.4)], dxfattribs={'layer': 'ТМ_арматура'})
        p.circle(c[0], c[1], 0, 'ТМ_арматура', r_paper=1.4)
        p.t(c[0], c[1], 'П', 1.5, 'center', 'ТМ_арматура')
        return True
    if k == 'aav':                                     # клапан воздушный (вакуумный)
        q = [(c[0] - 1.2, c[1]), (c[0] + 1.2, c[1]), (c[0] + 1.2, c[1] + 2.2), (c[0] - 1.2, c[1] + 2.2)]
        poly_wipe(p, q)
        p.poly(q, 'ТМ_арматура')
        p.t(c[0], c[1] + 1.1, 'КВ', 1.2, 'center', 'ТМ_арматура')
        return True
    return sym_fit(p, V, f, scale)


# ====================================================================================== план
UNDER_DY = {'plan1': 0.0, 'plan2': 60.0, 'bath': 120.0, 'roof': 180.0}   # сдвиг подложек в модели, м


def strip_revit_dots(doc):
    """Точки подключений приборов из Revit (красная, синяя, зелёная заливка в блоках сантехники АР) — не ВК,
    на листах ВК только закрывают стояки и подписи."""
    for b in doc.blocks:
        if b.name.startswith('*'):
            continue
        for e in list(b):
            if (e.dxftype() == 'HATCH' and e.dxf.layer == 'A-DETL-GENF' and e.dxf.solid_fill
                    and e.dxf.get('color', 256) in (1, 5, 96)):
                b.delete_entity(e)


def ensure_underlay(doc, under):
    name = 'АР_' + under
    if name not in doc.blocks:
        blk = add_underlay(doc, UNDER[under], name)
        strip_revit_dots(doc)
        ref = insert_underlay(doc.modelspace(), blk)
        dy = UNDER_DY.get(under, 0.0) * 1000
        ref.dxf.insert = (ref.dxf.insert[0], ref.dxf.insert[1] + dy, 0)
    return name


def plan_doc(doc, sh, under, cx, cy, w, h, mx, my, K, frame=None):
    """Видовой экран подложки АР на листе и вид плана для рисования сетей ВК в пространстве листа.
    frame — диапазон отметок (zlo, zhi) для отсечения вида плана. Подложки разнесены в модели по UNDER_DY."""
    ensure_underlay(doc, under)
    sh.viewport(cx, cy, w, h, mx, my + UNDER_DY.get(under, 0.0), k=K)
    V = View('plan', K, (cx, cy), (mx, my), zr=frame)
    return V, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def clip2(a, b, box):
    """Отсечение отрезка a-b (мм листа) рамкой box (Лианг — Барски)."""
    x0, y0, x1, y1 = box
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p_, q_ in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if abs(p_) < 1e-12:
            if q_ < 0:
                return None
            continue
        t = q_ / p_
        if p_ < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return None
    return (a[0] + dx * t0, a[1] + dy * t0), (a[0] + dx * t1, a[1] + dy * t1)


def in_box(pt, box):
    return box[0] <= pt[0] <= box[2] and box[1] <= pt[1] <= box[3]


def draw_net(p, V, pipes, box, lw=None, zr=None, L=None):
    lab = L
    """Трубы на плане в пределах окна box (мм листа): горизонтальные — линией, вертикальные — кружком стояка."""
    out = []
    for pp in pipes:
        lay, lt = STYLE[pp.sys]
        for a, b in zip(pp.pts, pp.pts[1:]):
            c = (a, b) if zr is None else V.clip(a, b)
            if c is None or c[0] is None:
                continue
            A, B = V.P(c[0]), V.P(c[1])
            cc = clip2(A, B, box)
            if cc is None:
                continue
            A, B = cc
            L = math.hypot(B[0] - A[0], B[1] - A[1])
            if L < 0.05:
                if math.dist(c[0], c[1]) > 0.02:
                    p.circle(A[0], A[1], 0, lay, r_paper=max(0.7, pp.od * V.s / 2))
                continue
            p.pl([A, B], lay, ltype=lt, lw=lw or (50 if pp.sys in ('К1', 'К1в') else 35))
            out.append((pp, c, A, B))
            if lab is not None and hasattr(lab, 'segs'):
                lab.segs.append((A, B))
    return out


def longest_seg(V, pp, box, zr=None, horiz=True):
    best = None
    for a, b in zip(pp.pts, pp.pts[1:]):
        c = (a, b) if zr is None else V.clip(a, b)
        if c is None or c[0] is None:
            continue
        if horiz and abs(c[0][2] - c[1][2]) > 1e-6:
            continue
        A, B = V.P(c[0]), V.P(c[1])
        if not (in_box(A, box) and in_box(B, box)):
            continue
        L = math.hypot(B[0] - A[0], B[1] - A[1])
        if best is None or L > best[0]:
            best = (L, c, A, B)
    return best


def fixture_marks(p, L, V, box, bld='h', floor=None, h=2.0, skip=()):
    """Марки приборов по модели: рядом с прибором, без наложений."""
    for k, fx in VK.FIXT.items():
        if fx.bld != bld or k in skip or (floor is not None and fx.floor != floor):
            continue
        at = V.P((fx.pos[0], fx.pos[1], 0))
        if not in_box(at, box):
            continue
        L.shelf(at, k, h, cands=[(3, 3), (-3, 3), (3, -3), (-3, -3), (5, 5), (-5, 5), (5, -5), (-5, -5),
                                 (8, 6), (-8, 6), (8, -6), (-8, -6)])


def leak_sym(p, c, r=1.3):
    """Датчик протечки: квадрат с волной (знак условный, расшифрован в общих данных)."""
    q = [(c[0] - r, c[1] - r), (c[0] + r, c[1] - r), (c[0] + r, c[1] + r), (c[0] - r, c[1] + r)]
    poly_wipe(p, q)
    p.poly(q, 'ВК_защита')
    w = [(c[0] - r * 0.7 + i * r * 0.35, c[1] + (0.45 if i % 2 else -0.45) * r * 0.6) for i in range(5)]
    p.pl(w, 'ВК_защита')


def leak_marks(p, L, V, box, bld='h', level=1, h=1.7, label=True):
    """Датчики протечки ДП и контроллеры КЗП по модели (VK.LEAK, оборудование КЗП-*)."""
    for lid, b, lev_, (x, y), place in VK.LEAK:
        if b != bld or lev_ != level:
            continue
        at = V.P((x, y, 0))
        if not in_box(at, box):
            continue
        leak_sym(p, at)
        if label:
            L.shelf(at, lid, h, cands=[(3, 3), (-3, 3), (3, -3), (-3, -3), (5, 5), (-5, 5), (5, -5), (-5, -5),
                                       (8, 4), (-8, 4), (8, -4), (-8, -4), (10, 8), (-10, 8), (10, -8), (-10, -8),
                                       (14, 3), (-14, 3), (14, -3), (-14, -3)])


# ====================================================================================== подписи в обход труб
def _seg_rect(a, b, r):
    """Отрезок a-b пересекает прямоугольник r = (x0, y0, x1, y1)?"""
    x0, y0, x1, y1 = r
    if max(a[0], b[0]) < x0 or min(a[0], b[0]) > x1 or max(a[1], b[1]) < y0 or min(a[1], b[1]) > y1:
        return False
    if x0 <= a[0] <= x1 and y0 <= a[1] <= y1 or x0 <= b[0] <= x1 and y0 <= b[1] <= y1:
        return True
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p_, q_ in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if abs(p_) < 1e-12:
            if q_ < 0:
                return False
            continue
        t = q_ / p_
        if p_ < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return False
    return True


class VLabels(Labels):
    """Полки без наложений на другие полки, на трубы (segs) и на надписи подложки (busy)."""

    def __init__(self, p, frame):
        super().__init__(p, frame)
        self.segs = []

    def add_segs(self, segs):
        self.segs.extend(segs)

    def free(self, r, pad=0.6):
        if not super().free(r, pad):
            return False
        rr = (r[0] - 0.4, r[1] - 0.4, r[2] + 0.4, r[3] + 0.4)
        for a, b in self.segs:
            if _seg_rect(a, b, rr):
                return False
        return True


def leak_block(L, V, box, bld='h', level=1, r=1.6):
    """Места знаков датчиков протечки — заняты заранее, чтобы марки приборов не ложились на знаки."""
    for lid, b, lev_, (x, y), place in VK.LEAK:
        if b != bld or lev_ != level:
            continue
        c = V.P((x, y, 0))
        if in_box(c, box):
            L.block((c[0] - r, c[1] - r, c[0] + r, c[1] + r))


def under_solids(src, V, box):
    """Сплошные заливки остекления подложки АР (тёмные на листе) — занятые места для полок."""
    from ezdxf import recover, bbox
    from underlay import OX, OY
    sdoc, _ = recover.readfile(src)
    out = []

    def add(h):
        if 'GLAZ' not in h.dxf.layer or not h.dxf.solid_fill:
            return
        e = bbox.extents([h], fast=True)
        if not e.has_data:
            return
        a = V.P(((e.extmin.x - OX) / 1000, (e.extmin.y - OY) / 1000, 0))
        b = V.P(((e.extmax.x - OX) / 1000, (e.extmax.y - OY) / 1000, 0))
        r = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
        if r[2] >= box[0] and r[0] <= box[2] and r[3] >= box[1] and r[1] <= box[3]:
            out.append(r)
    for e in sdoc.modelspace():
        if e.dxftype() == 'HATCH':
            add(e)
        elif e.dxftype() == 'INSERT':
            try:
                for ve in e.virtual_entities():
                    if ve.dxftype() == 'HATCH':
                        add(ve)
            except Exception:
                continue
    return out


def under_texts(src, V, box, scale_h=1.0):
    """Прямоугольники надписей подложки АР на листе (номера помещений, марки) — занятые места для полок."""
    from ezdxf import recover
    from underlay import OX, OY
    sdoc, _ = recover.readfile(src)
    out = []
    for e in sdoc.modelspace():
        if e.dxftype() not in ('TEXT', 'MTEXT'):
            continue
        try:
            ins = e.dxf.insert
            h = e.dxf.char_height if e.dxftype() == 'MTEXT' else e.dxf.height
            s = e.plain_text() if e.dxftype() == 'MTEXT' else e.dxf.text
        except Exception:
            continue
        x, y = (ins.x - OX) / 1000, (ins.y - OY) / 1000
        c = V.P((x, y, 0))
        hh = h / 1000 * V.s * scale_h
        w = max(1, len(s)) * hh * 0.7
        r = (c[0] - w * 0.6, c[1] - hh * 0.8, c[0] + w * 0.6, c[1] + hh * 0.8)
        if box[0] <= c[0] <= box[2] and box[1] <= c[1] <= box[3]:
            out.append(r)
    return out + under_solids(src, V, box)
