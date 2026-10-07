"""Чертёжный набор: документ, слои, блоки условных обозначений, рамки и основная надпись (ГОСТ Р 21.101-2020, ф. 3)."""
import math
import ezdxf
from ezdxf.addons.importer import Importer
from ezdxf.enums import TextEntityAlignment as TA
from ezdxf import bbox as ezbbox

FORMATS = {'A0': (1189, 841), 'A1': (841, 594), 'A2': (594, 420), 'A3': (420, 297), 'A4': (210, 297), 'A3x3': (891, 420)}
SHIFR = 'ОПР-01/24/2024-ДП1-ПТ'
OBJ = '«Современный коммерческий оптово-продовольственный рынок (ОПР) по адресу: Донецкая область, г. Макеевка, Горняцкий район»'
BLD = 'Док-павильон №23, №23.2 Рыба-Мясо. Пожаротушение (ВПВ, АУПТ, АУПП ВРУ)'
ORG = 'ООО «Технология»'

LAYERS = {
    'ПТ_В21': (1, 50), 'ПТ_В22': (6, 50), 'ПТ_В2': (3, 50), 'ПТ_В21_расп': (1, 30), 'ПТ_В22_расп': (6, 30),
    'ПТ_ввод': (5, 60), 'ПТ_оросители': (7, 25), 'ПТ_ПК': (30, 35), 'ПТ_арматура': (7, 30), 'ПТ_оборудование': (7, 35),
    'ПТ_текст': (7, 18), 'ПТ_размеры': (7, 13), 'ПТ_выноски': (7, 13), 'ПТ_штриховка': (8, 9), 'ПТ_АУПП': (4, 35),
    'ПТ_кабели': (5, 25), 'ПТ_рамка': (7, 50), 'ПТ_рамка_тонк': (7, 18), 'АР_подоснова': (8, 13), 'ПТ_оси': (8, 13),
    'ПТ_контур': (7, 35),
}

def make_doc():
    doc = ezdxf.new('R2013', setup=True, units=4)
    for name, (color, lw) in LAYERS.items():
        doc.layers.add(name, color=color, lineweight=lw)
    st = doc.styles.add('ПТ', font='arial.ttf'); st.dxf.width = 0.85
    st2 = doc.styles.add('ПТ_Ж', font='arialbd.ttf'); st2.dxf.width = 0.85
    if 'DASHED' not in doc.linetypes:
        doc.linetypes.add('DASHED', pattern=[0.6, 0.4, -0.2])
    doc.linetypes.add('ПТ_ШТРИХ', pattern=[6.0, 4.0, -2.0], description='штрих 4-2')
    doc.linetypes.add('ПТ_ШТРИХПУНКТ', pattern=[16.0, 12.0, -2.0, 0.0, -2.0], description='штрихпунктир')
    doc.header['$LTSCALE'] = 1.0
    doc.header['$PSLTSCALE'] = 0
    _blocks(doc)
    return doc

# ------------------------------------------------------------------ блоки (в мм листа, вставляются с масштабом k)
def _half_hatch(blk, r, upper, layer):
    h = blk.add_hatch(color=7, dxfattribs={'layer': layer})
    if upper:
        h.paths.add_polyline_path([(r, 0, 1), (-r, 0, 0)], is_closed=True)   # bulge=1 → полуокружность сверху
    else:
        h.paths.add_polyline_path([(-r, 0, 1), (r, 0, 0)], is_closed=True)
    h.set_solid_fill(color=7)

def _blocks(doc):
    r = 1.1
    b = doc.blocks.new('SPR_DN')            # ороситель спринклерный розеткой вниз: окружность, диаметр, заливка нижней половины
    b.add_circle((0, 0), r, dxfattribs={'layer': '0'})
    b.add_line((-r, 0), (r, 0), dxfattribs={'layer': '0'})
    for i in range(1, 6):
        yy = -r * i / 6
        xx = (r * r - yy * yy) ** 0.5
        b.add_line((-xx, yy), (xx, yy), dxfattribs={'layer': '0'})
    b = doc.blocks.new('SPR_UP')            # розеткой вверх: заливка верхней половины
    b.add_circle((0, 0), r, dxfattribs={'layer': '0'})
    b.add_line((-r, 0), (r, 0), dxfattribs={'layer': '0'})
    for i in range(1, 6):
        yy = r * i / 6
        xx = (r * r - yy * yy) ** 0.5
        b.add_line((-xx, yy), (xx, yy), dxfattribs={'layer': '0'})
    b = doc.blocks.new('SPR_EXIST')         # условно: не используется
    b.add_circle((0, 0), r, dxfattribs={'layer': '0'})
    # спаренный ПК в шкафу (план): шкаф 8×2,6 мм (на листе), два клапана
    b = doc.blocks.new('PK2')
    b.add_lwpolyline([(-4, 0), (4, 0), (4, 2.6), (-4, 2.6)], close=True, dxfattribs={'layer': '0'})
    for cx in (-1.8, 1.8):
        b.add_circle((cx, 1.3), 0.8, dxfattribs={'layer': '0'})
        h = b.add_hatch(color=7); h.paths.add_polyline_path([(cx - 0.8, 1.3, 1), (cx + 0.8, 1.3, 0)], is_closed=True); h.set_solid_fill(color=7)
    # стояк (план)
    b = doc.blocks.new('RISER')
    b.add_circle((0, 0), 1.0, dxfattribs={'layer': '0'})
    b.add_circle((0, 0), 0.35, dxfattribs={'layer': '0'})
    # арматура (ось трубы — X, длина 4 мм)
    def bowtie(name, extra=None, fill_right=False):
        b = doc.blocks.new(name)
        b.add_lwpolyline([(-2, -1), (-2, 1), (2, -1), (2, 1)], close=True, dxfattribs={'layer': '0'})
        if fill_right:
            h = b.add_hatch(color=7); h.paths.add_polyline_path([(0, 0), (2, 1), (2, -1)], is_closed=True); h.set_solid_fill(color=7)
        if extra:
            extra(b)
        return b
    bowtie('V_GATE', lambda b: b.add_line((0, 0), (0, 2.2), dxfattribs={'layer': '0'}) or b.add_line((-0.8, 2.2), (0.8, 2.2), dxfattribs={'layer': '0'}))
    bowtie('V_BFLY', lambda b: b.add_circle((0, 0), 0.55, dxfattribs={'layer': '0'}) or b.add_line((0, 0.55), (0, 2.2), dxfattribs={'layer': '0'})
           or b.add_lwpolyline([(-0.6, 2.2), (0.6, 2.2), (0.6, 2.9), (-0.6, 2.9)], close=True, dxfattribs={'layer': '0'}))
    bowtie('V_CHECK', fill_right=True)
    def ball(b):
        h = b.add_hatch(color=7); h.paths.add_polyline_path([(0.5, 0, 1), (-0.5, 0, 1)], is_closed=True); h.set_solid_fill(color=7)
    bowtie('V_BALL', ball)
    bowtie('V_GLOBE', lambda b: b.add_circle((0, 0), 0.35, dxfattribs={'layer': '0'}))
    b = doc.blocks.new('V_MOTOR')           # затвор с электроприводом
    b.add_lwpolyline([(-2, -1), (-2, 1), (2, -1), (2, 1)], close=True)
    b.add_line((0, 0), (0, 1.8)); b.add_circle((0, 2.6), 0.8); b.add_text('М', dxfattribs={'height': 0.9, 'style': 'ПТ'}).set_placement((0, 2.6), align=TA.MIDDLE_CENTER)
    b = doc.blocks.new('MANOM')             # манометр с краном
    b.add_line((0, 0), (0, 2)); b.add_circle((0, 3), 1.0); b.add_line((-0.5, 2.5), (0.6, 3.6))
    b = doc.blocks.new('PSW')               # сигнализатор давления
    b.add_line((0, 0), (0, 1.6)); b.add_lwpolyline([(-1, 1.6), (1, 1.6), (1, 3.6), (-1, 3.6)], close=True)
    b.add_text('Р', dxfattribs={'height': 1.2, 'style': 'ПТ'}).set_placement((0, 2.6), align=TA.MIDDLE_CENTER)
    b = doc.blocks.new('FSW')               # сигнализатор потока жидкости
    b.add_line((0, 0), (0, 1.6)); b.add_lwpolyline([(-1, 1.6), (1, 1.6), (1, 3.6), (-1, 3.6)], close=True)
    b.add_text('F', dxfattribs={'height': 1.2, 'style': 'ПТ'}).set_placement((0, 2.6), align=TA.MIDDLE_CENTER)
    b = doc.blocks.new('PUMP')              # насос (ГОСТ 21.205: окружность с треугольником)
    b.add_circle((0, 0), 3.0); b.add_lwpolyline([(-2.1, -2.1), (3.0, 0), (-2.1, 2.1)], close=False)
    b = doc.blocks.new('TANK')              # мембранный бак
    b.add_lwpolyline([(-2, -4), (2, -4), (2, 2), (-2, 2)], close=True); b.add_arc((0, 2), 2, 0, 180); b.add_line((-2, -1), (2, -1))
    b = doc.blocks.new('UU')                # узел управления (условно)
    b.add_circle((0, 0), 2.5); b.add_text('УУ', dxfattribs={'height': 1.6, 'style': 'ПТ'}).set_placement((0, 0), align=TA.MIDDLE_CENTER)
    b = doc.blocks.new('GM80')              # головка соединительная (патрубок для пожарной техники)
    b.add_lwpolyline([(0, -1.5), (0, 1.5)]); b.add_arc((0, 0), 1.5, -90, 90)
    b = doc.blocks.new('DRAIN')             # трап / слив
    b.add_circle((0, 0), 1.5); b.add_line((-1.06, -1.06), (1.06, 1.06)); b.add_line((-1.06, 1.06), (1.06, -1.06))
    b = doc.blocks.new('ELEV')              # знак отметки (треугольник ▽, вершина в точке вставки)
    b.add_lwpolyline([(0, 0), (-1.2, 1.6), (1.2, 1.6)], close=True)
    b.add_line((0, 1.6), (9, 1.6))
    b = doc.blocks.new('ARROW')             # стрелка направления (остриё в 0,0, вдоль +X)
    h = b.add_hatch(color=7); h.paths.add_polyline_path([(0, 0), (-2.5, 0.6), (-2.5, -0.6)], is_closed=True); h.set_solid_fill(color=7)
    b = doc.blocks.new('MODULE')            # модуль порошкового пожаротушения (план)
    b.add_circle((0, 0), 1.6); h = b.add_hatch(color=7); h.paths.add_polyline_path([(0, 1.6, 1), (0, -1.6, 0)], is_closed=True); h.set_solid_fill(color=7)
    b = doc.blocks.new('DETS')              # извещатель дымовой (АПС, условно)
    b.add_circle((0, 0), 1.3); b.add_line((-0.9, -0.9), (0.9, 0.9))
    b = doc.blocks.new('BTN')               # устройство дистанционного пуска
    b.add_lwpolyline([(-1.3, -1.3), (1.3, -1.3), (1.3, 1.3), (-1.3, 1.3)], close=True); b.add_circle((0, 0), 0.7)
    b = doc.blocks.new('SIGN')              # табло световое
    b.add_lwpolyline([(-2.2, -1), (2.2, -1), (2.2, 1), (-2.2, 1)], close=True); b.add_line((-2.2, -1), (2.2, 1)); b.add_line((-2.2, 1), (2.2, -1))
    b = doc.blocks.new('SIREN')             # оповещатель звуковой
    b.add_lwpolyline([(-1.2, -1), (0, -1), (1.4, -2), (1.4, 2), (0, 1), (-1.2, 1)], close=True)
    b = doc.blocks.new('DOORC')             # датчик положения двери
    b.add_lwpolyline([(-1.2, -0.8), (1.2, -0.8), (1.2, 0.8), (-1.2, 0.8)], close=True); b.add_line((-1.2, -0.8), (1.2, 0.8))

# ------------------------------------------------------------------ примитивы
def txt(msp, x, y, s, h, k=1, layer='ПТ_текст', align='BL', rot=0, style='ПТ', color=None):
    al = {'BL': TA.BOTTOM_LEFT, 'BC': TA.BOTTOM_CENTER, 'BR': TA.BOTTOM_RIGHT, 'ML': TA.MIDDLE_LEFT, 'MC': TA.MIDDLE_CENTER,
          'MR': TA.MIDDLE_RIGHT, 'TL': TA.TOP_LEFT, 'TC': TA.TOP_CENTER, 'TR': TA.TOP_RIGHT}[align]
    a = {'height': h * k, 'style': style, 'layer': layer, 'rotation': rot}
    if color is not None:
        a['color'] = color
    t = msp.add_text(s, dxfattribs=a)
    t.set_placement((x, y), align=al)
    return t

def mtxt(msp, x, y, s, h, width, k=1, layer='ПТ_текст', style='ПТ', attach=1, spacing=1.0):
    m = msp.add_mtext(s, dxfattribs={'char_height': h * k, 'style': style, 'layer': layer, 'width': width * k,
                                    'attachment_point': attach, 'line_spacing_factor': spacing})
    m.set_location((x, y))
    return m

def line(msp, a, b, layer='ПТ_рамка_тонк', lw=None, color=None, lt=None):
    att = {'layer': layer}
    if lw is not None:
        att['lineweight'] = lw
    if color is not None:
        att['color'] = color
    if lt:
        att['linetype'] = lt
    return msp.add_line(a, b, dxfattribs=att)

def rect(msp, x0, y0, x1, y1, layer='ПТ_рамка_тонк', lw=None):
    att = {'layer': layer}
    if lw is not None:
        att['lineweight'] = lw
    return msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True, dxfattribs=att)

def ins(msp, name, x, y, k=1, rot=0, layer='ПТ_арматура', color=None):
    a = {'xscale': k, 'yscale': k, 'rotation': rot, 'layer': layer}
    if color is not None:
        a['color'] = color
    return msp.add_blockref(name, (x, y), dxfattribs=a)

def table(msp, x0, y_top, cols, rows, k=1, h=2.5, row_h=8, header_h=None, layer='ПТ_рамка_тонк', tlayer='ПТ_текст', wrap=True):
    """Таблица: cols — [(заголовок, ширина мм)], rows — список списков строк. Возвращает нижнюю y."""
    header_h = header_h or row_h * 1.5
    W = sum(w for _, w in cols)
    y = y_top
    # шапка
    rect(msp, x0, y - header_h * k, x0 + W * k, y, layer=layer, lw=35)
    xx = x0
    for title, w in cols:
        line(msp, (xx, y), (xx, y - header_h * k), layer=layer, lw=35)
        mtxt(msp, xx + w * k / 2, y - header_h * k / 2, title, h * 0.9, w - 1.5, k, attach=5, layer=tlayer)
        xx += w * k
    line(msp, (xx, y), (xx, y - header_h * k), layer=layer, lw=35)
    y -= header_h * k
    for r in rows:
        # высота строки по числу переносов
        nl = 1
        for (title, w), cell in zip(cols, r):
            cpl = max(1, int((w - 2) / (h * 0.62)))
            n = sum(max(1, math.ceil(len(part) / cpl)) for part in str(cell).split('\n'))
            nl = max(nl, n)
        rh = max(row_h, nl * h * 1.55 + 2.5)
        xx = x0
        for (title, w), cell in zip(cols, r):
            line(msp, (xx, y), (xx, y - rh * k), layer=layer)
            s = str(cell)
            if s:
                if len(s) * h * 0.62 < w - 2 and '\n' not in s:
                    txt(msp, xx + 1.2 * k, y - rh * k / 2, s, h, k, align='ML', layer=tlayer)
                else:
                    mtxt(msp, xx + 1.2 * k, y - 1.2 * k, s.replace('\n', '\\P'), h, w - 2.4, k, attach=1, layer=tlayer)
            xx += w * k
        line(msp, (xx, y), (xx, y - rh * k), layer=layer)
        y -= rh * k
        line(msp, (x0, y), (x0 + W * k, y), layer=layer)
    return y

# ------------------------------------------------------------------ рамка и основная надпись
def frame(msp, ox, oy, fmt, k, title, sheet, sheets=None, stage='Р', subtitle=None, first=False, extra_stamp=None):
    W, H = FORMATS[fmt]
    rect(msp, ox, oy, ox + W * k, oy + H * k, layer='ПТ_рамка_тонк', lw=13)
    x0, y0, x1, y1 = ox + 20 * k, oy + 5 * k, ox + (W - 5) * k, oy + (H - 5) * k
    rect(msp, x0, y0, x1, y1, layer='ПТ_рамка', lw=70)
    stamp3(msp, x1 - 185 * k, y0, k, title, sheet, sheets, stage, subtitle)
    side_stamp(msp, ox, oy, k)
    # формат
    txt(msp, x1 - 40 * k, oy + 1.2 * k, f'Формат {fmt}', 2.5, k, align='BL')
    return (x0, y0, x1, y1)

def stamp3(msp, x, y, k, title, sheet, sheets, stage, subtitle):
    L, T = 'ПТ_рамка', 'ПТ_текст'
    def ln(a, b, lw=50):
        line(msp, (x + a[0] * k, y + a[1] * k), (x + b[0] * k, y + b[1] * k), layer=L, lw=lw)
    rect(msp, x, y, x + 185 * k, y + 55 * k, layer=L, lw=70)
    # левая часть: 11 строк по 5 мм
    for i in range(1, 11):
        ln((0, i * 5), (65, i * 5), 50 if i in (5, 6) else 18)
    for cx in (10, 20, 30, 40, 55):
        ln((cx, 25), (cx, 55), 50)
    for cx in (20, 40, 55):
        ln((cx, 0), (cx, 25), 50)
    ln((65, 0), (65, 55), 70)
    heads = [('Изм.', 0, 10), ('Кол.уч', 10, 10), ('Лист', 20, 10), ('№ док.', 30, 10), ('Подп.', 40, 15), ('Дата', 55, 10)]
    for s, cx, w in heads:
        txt(msp, x + (cx + w / 2) * k, y + 27.5 * k, s, 1.8, k, align='MC', layer=T)
    roles = ['Разраб.', 'Пров.', '', 'Н.контр.', 'ГИП']
    for i, s in enumerate(roles):
        txt(msp, x + 1 * k, y + (22.5 - i * 5) * k, s, 1.8, k, align='ML', layer=T)
    # правая часть
    ln((65, 40), (185, 40), 70); ln((65, 30), (185, 30), 50); ln((65, 15), (185, 15), 70)
    ln((135, 0), (135, 30), 70); ln((135, 25), (185, 25), 50)
    ln((150, 15), (150, 30), 50); ln((165, 15), (165, 30), 50)
    txt(msp, x + 125 * k, y + 47.5 * k, SHIFR, 5, k, align='MC', layer=T, style='ПТ_Ж')
    mtxt(msp, x + 125 * k, y + 35 * k, OBJ, 1.9, 116, k, attach=5, layer=T)
    mtxt(msp, x + 100 * k, y + 22.5 * k, BLD, 2.2, 66, k, attach=5, layer=T)
    for s, cx, w in [('Стадия', 135, 15), ('Лист', 150, 15), ('Листов', 165, 20)]:
        txt(msp, x + (cx + w / 2) * k, y + 27.5 * k, s, 1.8, k, align='MC', layer=T)
    txt(msp, x + 142.5 * k, y + 20 * k, stage, 3, k, align='MC', layer=T)
    txt(msp, x + 157.5 * k, y + 20 * k, str(sheet), 3, k, align='MC', layer=T)
    if sheets:
        txt(msp, x + 175 * k, y + 20 * k, str(sheets), 3, k, align='MC', layer=T)
    mtxt(msp, x + 100 * k, y + 7.5 * k, title, 2.5, 66, k, attach=5, layer=T)
    txt(msp, x + 160 * k, y + 7.5 * k, ORG, 3, k, align='MC', layer=T)

def side_stamp(msp, ox, oy, k):
    """Дополнительные графы слева: Инв. № подл., Подп. и дата, Взам. инв. №"""
    x0 = ox + 8 * k
    y = oy + 5 * k
    for s, h in [('Инв. № подл.', 25), ('Подп. и дата', 35), ('Взам. инв. №', 25)]:
        rect(msp, x0, y, x0 + 12 * k, y + h * k, layer='ПТ_рамка', lw=50)
        line(msp, (x0 + 5 * k, y), (x0 + 5 * k, y + h * k), layer='ПТ_рамка', lw=50)
        txt(msp, x0 + 2.5 * k, y + h * k / 2, s, 1.8, k, align='MC', rot=90)
        y += h * k

# ------------------------------------------------------------------ подоснова АР
def _clip_seg(p, q, c):
    """Отрезок, обрезанный прямоугольником c = (x0, y0, x1, y1) (Лианг — Барски)."""
    x0, y0 = p; dx, dy = q[0] - x0, q[1] - y0
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, x0 - c[0]), (dx, c[2] - x0), (-dy, y0 - c[1]), (dy, c[3] - y0)):
        if pp == 0:
            if qq < 0:
                return None
            continue
        t = qq / pp
        if pp < 0:
            if t > t1: return None
            t0 = max(t0, t)
        else:
            if t < t0: return None
            t1 = min(t1, t)
    return (x0 + t0 * dx, y0 + t0 * dy), (x0 + t1 * dx, y0 + t1 * dy)

def _prims(e, depth=0):
    if e.dxftype() in ('INSERT', 'DIMENSION') and depth < 8:
        try:
            for v in e.virtual_entities():
                yield from _prims(v, depth + 1)
        except Exception:
            return
    else:
        yield e

def _clip_into(blk, e, c, src, doc):
    """Элемент подосновы, выходящий за лист: разбирается на примитивы, линии обрезаются по границе."""
    from ezdxf import path as ezpath
    inside = lambda x, y: c[0] <= x <= c[2] and c[1] <= y <= c[3]
    for v in _prims(e):
        t = v.dxftype()
        if t in ('HATCH', 'SOLID', 'WIPEOUT', 'IMAGE', 'POINT', 'ATTDEF', 'LEADER', 'MULTILEADER', 'MPOLYGON', 'OLE2FRAME'):
            continue
        if t in ('TEXT', 'ATTRIB'):
            ip = v.dxf.insert
            if inside(ip.x, ip.y):
                blk.add_text(v.dxf.text, dxfattribs={'insert': (ip.x, ip.y), 'height': v.dxf.height,
                                                    'rotation': v.dxf.get('rotation', 0), 'layer': 'АР_подоснова'})
            continue
        if t == 'MTEXT':
            ip = v.dxf.insert
            if inside(ip.x, ip.y):
                blk.add_mtext(v.text, dxfattribs={'insert': (ip.x, ip.y), 'char_height': v.dxf.char_height,
                                                 'attachment_point': v.dxf.get('attachment_point', 1),
                                                 'rotation': v.dxf.get('rotation', 0), 'layer': 'АР_подоснова'})
            continue
        lt = v.dxf.get('linetype', 'BYLAYER')
        if lt.upper() in ('BYLAYER', 'BYBLOCK'):
            try:
                lt = src.layers.get(v.dxf.layer).dxf.linetype
            except Exception:
                lt = 'Continuous'
        if lt.upper() != 'CONTINUOUS' and lt not in doc.linetypes:
            lt = 'ПТ_ШТРИХПУНКТ'
        att = {'layer': 'АР_подоснова'}
        if lt.upper() != 'CONTINUOUS':
            att['linetype'] = lt
            if lt == 'ПТ_ШТРИХПУНКТ':
                att['ltscale'] = 100
        try:
            pts = list(ezpath.make_path(v).flattening(20))
        except Exception:
            continue
        for a, b in zip(pts, pts[1:]):
            r = _clip_seg((a.x, a.y), (b.x, b.y), c)
            if r and (abs(r[0][0] - r[1][0]) + abs(r[0][1] - r[1][1])) > 1:
                blk.add_line(r[0], r[1], dxfattribs=att)

KEEP_TYPES = {'LINE', 'LWPOLYLINE', 'POLYLINE', 'ARC', 'CIRCLE', 'INSERT', 'TEXT', 'MTEXT', 'ELLIPSE', 'SPLINE'}
def import_ar(doc, src_path, block_name, drop_layers=(), clip=None):
    from ezdxf import recover
    src, _ = recover.readfile(src_path)
    blk = doc.blocks.new(block_name)
    ents, cross = [], []
    for e in src.modelspace():
        if e.dxftype() not in KEEP_TYPES:
            continue
        if any(e.dxf.layer.startswith(d) for d in drop_layers):
            continue
        if clip:
            try:
                b = ezbbox.extents([e], fast=True)
                if b.has_data and (b.extmax.x < clip[0] or b.extmin.x > clip[2] or b.extmax.y < clip[1] or b.extmin.y > clip[3]):
                    continue
                if b.has_data and (b.extmin.x < clip[0] or b.extmax.x > clip[2] or b.extmin.y < clip[1] or b.extmax.y > clip[3]):
                    cross.append(e)     # пересекает границу листа — разбираем и обрезаем
                    continue
            except Exception:
                pass
        ents.append(e)
    imp = Importer(src, doc)
    imp.import_entities(ents, target_layout=blk)
    imp.finalize()
    for e in cross:
        _clip_into(blk, e, clip, src, doc)
    # всё — серым на слое подосновы; штриховки и сплошные заливки убираем
    seen = set()
    def clean(layout):
        if layout.name in seen:
            return
        seen.add(layout.name)
        dead = []
        for e in layout:
            if e.dxftype() in ('HATCH', 'SOLID', 'WIPEOUT', 'IMAGE', 'OLE2FRAME', 'MPOLYGON'):
                dead.append(e); continue
            try:
                if e.dxf.hasattr('true_color'):
                    e.dxf.discard('true_color')
                e.dxf.layer = '0' if layout.name != block_name else 'АР_подоснова'
                e.dxf.color = 0 if layout.name != block_name else 256
                e.dxf.lineweight = -2 if layout.name != block_name else -1
            except Exception:
                pass
            if e.dxftype() == 'INSERT':
                for a in e.attribs:
                    a.dxf.layer = '0'; a.dxf.color = 0
                    if a.dxf.hasattr('true_color'):
                        a.dxf.discard('true_color')
                if e.dxf.name in doc.blocks:
                    clean(doc.blocks.get(e.dxf.name))
        for e in dead:
            layout.delete_entity(e)
    clean(blk)
    return blk
