"""Планы систем ПТ (М 1:100): подвал, 1 этаж, 2 этаж."""
import json, math, os
from collections import defaultdict
import ezdxf
from dxfkit import txt, mtxt, line, rect, ins, frame, table, import_ar
from geom import rooms, FREEZERS, bb

HERE = os.path.dirname(os.path.abspath(__file__))
DXF_AR = os.path.join(HERE, '..', 'dxf')
M = json.load(open(os.path.join(HERE, 'model_sized.json')))
K = 100   # масштаб 1:100

AX_X = {'1': 0, '2': 4000, '3': 10000, '4': 16000, '5': 22000, '6': 28000, '7': 34000, '8': 40000, '9': 46000,
        '10': 52000, '11': 58000, '12': 64000, '13': 70000, '14': 76000, '15': 82000, '16': 88000, '17': 94000, '18': 98000}
AX_Y = {'А': 0, 'Б': 6000, 'В': 12000, 'Г': 18000, 'Д': 22000, 'Е': 28000, 'Ж': 34000, 'И': 40000}

def setup_dimstyle(doc):
    if 'ПТ100' in doc.dimstyles:
        return
    ds = doc.dimstyles.new('ПТ100')
    ds.dxf.dimtxsty = 'ПТ'
    ds.dxf.dimscale = 100
    ds.dxf.dimtxt = 2.5
    ds.dxf.dimasz = 1.2
    ds.dxf.dimtsz = 1.2          # засечки вместо стрелок
    ds.dxf.dimexe = 1.0
    ds.dxf.dimexo = 0.0
    ds.dxf.dimgap = 0.6
    ds.dxf.dimdec = 0
    ds.dxf.dimtad = 1
    ds.dxf.dimtih = 0
    ds.dxf.dimtoh = 0
    ds.dxf.dimlfac = 1.0
    ds.dxf.dimclrd = 7; ds.dxf.dimclre = 7; ds.dxf.dimclrt = 7
    ds.dxf.dimlwd = 13; ds.dxf.dimlwe = 13
    ds.dxf.dimdsep = ord(',')
    ds.dxf.dimzin = 8

def dim_chain(msp, pts, base, horizontal=True, layer='ПТ_размеры'):
    pts = sorted(set(round(p) for p in pts))
    for a, b in zip(pts, pts[1:]):
        if b - a < 1:
            continue
        if horizontal:
            d = msp.add_linear_dim(base=(a, base), p1=(a, base), p2=(b, base), dimstyle='ПТ100', dxfattribs={'layer': layer})
        else:
            d = msp.add_linear_dim(base=(base, a), p1=(base, a), p2=(base, b), angle=90, dimstyle='ПТ100', dxfattribs={'layer': layer})
        d.render()

class Shifted:
    """Обёртка, сдвигающая координаты здания в позицию листа."""
    def __init__(self, msp, dx, dy):
        self.msp, self.dx, self.dy = msp, dx, dy
    def p(self, x, y):
        return (x + self.dx, y + self.dy)

def runs_of(pipes):
    """Слияние горизонтальных сегментов одного Ду в прямые участки."""
    segs = defaultdict(list)
    for p in pipes:
        a, b = p['a'], p['b']
        if abs(a[2] - b[2]) > 0.02 and (abs(a[0] - b[0]) < 1 and abs(a[1] - b[1]) < 1):
            continue
        if abs(a[1] - b[1]) < 1:       # вдоль x
            segs[('x', round(a[1]), p['sys'], p.get('dn'), p['role'] in ('питающий', 'кольцо ВПВ', 'стояк'))].append(sorted([a[0], b[0]]))
        elif abs(a[0] - b[0]) < 1:
            segs[('y', round(a[0]), p['sys'], p.get('dn'), p['role'] in ('питающий', 'кольцо ВПВ', 'стояк'))].append(sorted([a[1], b[1]]))
    out = []
    for kk, lst in segs.items():
        lst.sort()
        cur = list(lst[0])
        for s in lst[1:]:
            if s[0] <= cur[1] + 1:
                cur[1] = max(cur[1], s[1])
            else:
                out.append((kk, cur)); cur = list(s)
        out.append((kk, cur))
    return out

SYS_LAYER = {'В21': ('ПТ_В21', 'ПТ_В21_расп'), 'В22': ('ПТ_В22', 'ПТ_В22_расп'), 'В2': ('ПТ_В2', 'ПТ_В2')}

def hatch_rect(msp, S, x0, y0, x1, y1, pattern='ANSI31', scale=60):
    h = msp.add_hatch(color=8, dxfattribs={'layer': 'ПТ_штриховка'})
    h.paths.add_polyline_path([S.p(x0, y0), S.p(x1, y0), S.p(x1, y1), S.p(x0, y1)], is_closed=True)
    h.set_pattern_fill(pattern, scale=scale, color=8)
    return h

def plan_sheet(doc, msp, ox, oy, floor, sheet_no, sheets_total, title, notes, legend_rows, head=None):
    """floor: 0 — подвал, 1, 2."""
    frame(msp, ox, oy, 'A0', K, title, sheet_no, sheets_total)
    dx, dy = ox + 80 * K, oy + 80 * K + 16000
    S = Shifted(msp, dx, dy)
    src = {0: 'Технический подвал', 1: '1 этаж с морозильными камерами', 2: '2 этаж'}[floor]
    bname = {0: 'AR_B', 1: 'AR_F1', 2: 'AR_F2'}[floor]
    if bname not in doc.blocks:
        import_ar(doc, os.path.join(DXF_AR, src + '.dxf'), bname,
                  drop_layers=('Отделочный', 'Мебель и', 'Технолог'), clip=(-4800, -17000, 103500, 53000))
    msp.add_blockref(bname, S.p(0, 0), dxfattribs={'layer': 'АР_подоснова'})
    lvl_name = {0: 'отм. −2,200', 1: 'отм. 0,000', 2: 'отм. +3,700'}[floor]
    txt(msp, *S.p(46000, 55500), (head or title) + '. М 1:100', 5, K, align='BC', style='ПТ_загл')
    # марки осей рядов (у подосновы они за пределами листа и обрезаны)
    for name, y in AX_Y.items():
        msp.add_circle(S.p(-5200, y), 400, dxfattribs={'layer': 'ПТ_оси', 'color': 7})
        txt(msp, *S.p(-5200, y), name, 3.5, K, align='MC')

    # ---- помещения без АУП (штриховка) и подписи
    R1 = rooms('f1')
    if floor == 1:
        for f in FREEZERS:
            hatch_rect(msp, S, f[0], f[1], f[2], f[3])
        for num, lab in (('06', 'ВРУ — АУПП\nсм. лист 13'), ('99', 'СУ'), ('100', 'СУ')):
            x0, y0, x1, y1 = bb(R1[num]['poly'])
            hatch_rect(msp, S, x0, y0, x1, y1, 'ANSI37' if num == '06' else 'ANSI31', 80)
        x0, y0, x1, y1 = bb(R1['06']['poly'])
        mtxt(msp, *S.p((x0 + x1) / 2, (y0 + y1) / 2), 'ВРУ\\PАУПП\\Pсм. л. 13', 2.0, 30, K, attach=5)
        x0, y0, x1, y1 = bb(R1['05']['poly'])
        mtxt(msp, *S.p(x0 + 200, y1 - 250), 'Пом. 05\\Pстояки из\\Pнасосной', 1.8, 14, K, attach=1)
    if floor == 2:
        R2 = rooms('f2')
        x0, y0, x1, y1 = bb(R2['35']['poly'])
        hatch_rect(msp, S, x0, y0, x1, y1, 'ANSI31', 80)
        mtxt(msp, *S.p((x0 + x1) / 2, (y0 + y1) / 2), 'Венткамера\\P(п. 4.4 б\\PСП 486)\\Pбез АУП', 2.0, 40, K, attach=5)

    # ---- трубопроводы
    def on_floor(p):
        za, zb = p['a'][2], p['b'][2]
        if p['sys'] == 'В2':
            if floor == 0:
                return max(za, zb) <= 0.01
            if floor == 1:
                return 0.5 < za < 3.6 and 0.5 < zb < 3.6
            return za > 3.6 and zb > 3.6
        return (floor == 1 and p['sec'] == 1) or (floor == 2 and p['sec'] == 2)
    fl_pipes = [p for p in M['pipes'] if on_floor(p)]
    for p in fl_pipes:
        a, b = p['a'], p['b']
        if abs(a[0] - b[0]) < 1 and abs(a[1] - b[1]) < 1:
            continue
        main = p['role'] in ('питающий', 'кольцо ВПВ', 'стояк', 'перемычка ВПВ', 'подводка ВПВ')
        lay = SYS_LAYER[p['sys']][0 if main else 1]
        col = {'В21': 1, 'В22': 6, 'В2': 3}[p['sys']]
        msp.add_line(S.p(a[0], a[1]), S.p(b[0], b[1]), dxfattribs={'layer': lay})
    # подписи Ду по участкам
    for (ori, c, sysn, dn, main), (u0, u1) in runs_of(fl_pipes):
        L = u1 - u0
        if dn is None or L < 1300:
            continue
        lab = f'Ду{dn}'
        if ori == 'x':
            x, y, rot = (u0 + u1) / 2, c + 130, 0
            al = 'BC'
        else:
            x, y, rot = c - 130, (u0 + u1) / 2, 90
            al = 'BC'
        txt(msp, *S.p(x, y), lab, 1.8 if not main else 2.2, K, align=al, rot=rot)
    # ---- оросители
    for s in M['sprinklers']:
        if s['floor'] == floor:
            ins(msp, 'SPR_DN' if floor == 1 else 'SPR_UP', *S.p(s['x'], s['y']), K, layer='ПТ_оросители')
    # ---- ПК и стояки ВПВ
    risers = [(k, (k['rx'], k['ry'])) for k in M['pk']]
    for k, (rx, ry) in risers:
        # стояк виден на всех этажах между подвалом и своим этажом
        if ry is not None and floor <= k['floor']:
            ins(msp, 'RISER', *S.p(rx, ry), K, layer='ПТ_В2')
            if floor != k['floor']:
                txt(msp, *S.p(rx + 250, ry + 250), k['riser'], 1.8, K)
        if k['floor'] == floor:
            rot = {'S': 0, 'N': 180}[k['face']]
            ins(msp, 'PK2', *S.p(k['x'], k['y']), K, rot=rot, layer='ПТ_ПК')
            ty = k['y'] - 650 if k['face'] == 'S' else k['y'] + 650
            txt(msp, *S.p(k['x'], ty), f"{k['name']} (2×Ду65)", 1.8, K, align='TC' if k['face'] == 'S' else 'BC')
            if ry is not None:
                txt(msp, *S.p(rx + 300, ry + (250 if k['face'] == 'S' else -250)), k['riser'], 1.8, K,
                    align='BL' if k['face'] == 'S' else 'TL')
    # ---- стояки АУПТ от УУ
    if floor in (1, 2):
        for sec, (sx, sy, sz) in M['src'].items():
            if floor == 1 or int(sec) == 2:
                ins(msp, 'RISER', *S.p(sx, sy), K, layer='ПТ_В21' if sec == '1' else 'ПТ_В22')
                txt(msp, *S.p(sx + (-250 if sec == '1' else 250), sy - 300), f"Ст.В2{sec}-1", 2.0, K, align='TR' if sec == '1' else 'TL')
    # ---- подписи систем на питающих
    def sys_tags(y, x_from, x_to, tag, step=12000):
        x = x_from + 3000
        while x < x_to - 2000:
            txt(msp, *S.p(x, y - 150), tag, 2.2, K, align='TC')
            x += step
    if floor == 1:
        sys_tags(24600, 4000, 93000, 'В21'); sys_tags(15400, 7000, 93000, 'В21')
    if floor == 2:
        sys_tags(27500, 3000, 96000, 'В22'); sys_tags(12500, 3000, 96000, 'В22')
    if floor == 0:
        sys_tags(M['levels']['Y_RING1'], 9000, 97000, 'В2'); sys_tags(M['levels']['Y_RING2'], 5000, 97000, 'В2')

    # ---- отметки
    def elev(x, y, s):
        ins(msp, 'ELEV', *S.p(x, y), K, layer='ПТ_текст')
        txt(msp, *S.p(x + 150, y + 220), s, 2.0, K)
    if floor == 1:
        for x in (12000, 60000, 92000):
            elev(x, 24600, '+2,900 (ось В21)')
            elev(x - 1500, 15400, '+2,900 (ось В21)')
    if floor == 2:
        for x in (12000, 60000, 92000):
            elev(x, 27500, '+6,850 (ось В22)')
            elev(x - 1500, 12500, '+6,850 (ось В22)')
    if floor == 0:
        for x in (12000, 60000):
            elev(x, M['levels']['Y_RING1'] + 300, '−0,450 (ось В2)')
            elev(x, M['levels']['Y_RING2'] - 900, '−0,450 (ось В2)')

    # ---- размерные цепочки: оси + колонки оросителей (по северу и югу), ряды (запад/восток)
    ax = sorted(AX_X.values())
    sp = [s for s in M['sprinklers'] if s['floor'] == floor]
    if sp:
        north_cols = sorted({s['x'] for s in sp if s['y'] > 28225}); south_cols = sorted({s['x'] for s in sp if s['y'] < 11775})
        y_top = 40125 + 3000; y_bot = -125 - 3000
        dim_chain(msp, [S.p(x, 0)[0] for x in ax + north_cols], S.p(0, y_top)[1], True)
        dim_chain(msp, [S.p(x, 0)[0] for x in ax + south_cols], S.p(0, y_bot)[1], True)
        west_rows = sorted({s['y'] for s in sp if s['x'] < 4300})
        east_rows = sorted({s['y'] for s in sp if s['x'] > 93700})
        dim_chain(msp, [S.p(0, y)[1] for y in list(AX_Y.values()) + west_rows], S.p(-4000, 0)[0], False)
        mid_rows = sorted({s['y'] for s in sp if 10000 < s['x'] < 16000})
        dim_chain(msp, [S.p(0, y)[1] for y in list(AX_Y.values()) + mid_rows], S.p(101500, 0)[0], False)
    # привязки питающих
    if floor == 1:
        dim_chain(msp, [S.p(0, y)[1] for y in (22000, 24600)], S.p(30500, 0)[0], False)
        dim_chain(msp, [S.p(0, y)[1] for y in (15400, 18000)], S.p(30500, 0)[0], False)
    if floor == 2:
        dim_chain(msp, [S.p(0, y)[1] for y in (27500, 28000)], S.p(30500, 0)[0], False)
        dim_chain(msp, [S.p(0, y)[1] for y in (12000, 12500)], S.p(30500, 0)[0], False)
    if floor == 0:
        dim_chain(msp, [S.p(0, y)[1] for y in (22000, M['levels']['Y_RING1'])], S.p(30500, 0)[0], False)
        dim_chain(msp, [S.p(0, y)[1] for y in (M['levels']['Y_RING2'], 18000)], S.p(30500, 0)[0], False)

    # ---- примечания и условные обозначения (справа)
    nx = ox + 1072 * K; ny = oy + 812 * K
    txt(msp, nx, ny, 'Условные обозначения', 2.5, K, style='ПТ_загл')
    yy = ny - 6 * K
    for blk, lab, lay in legend_rows:
        if blk.startswith('LINE:'):
            l = blk[5:]
            msp.add_line((nx, yy + 1 * K), (nx + 10 * K, yy + 1 * K), dxfattribs={'layer': l})
        elif blk.startswith('HATCH:'):
            h = msp.add_hatch(color=8, dxfattribs={'layer': 'ПТ_штриховка'})
            h.paths.add_polyline_path([(nx, yy - 1 * K), (nx + 10 * K, yy - 1 * K), (nx + 10 * K, yy + 3 * K), (nx, yy + 3 * K)], is_closed=True)
            h.set_pattern_fill(blk[6:], scale=60, color=8)
            rect(msp, nx, yy - 1 * K, nx + 10 * K, yy + 3 * K)
        else:
            ins(msp, blk, nx + 5 * K, yy + 1 * K, K, layer=lay)
        mtxt(msp, nx + 13 * K, yy + 2.5 * K, lab, 2.0, 95, K, attach=1)
        yy -= 9 * K
    yy -= 4 * K
    txt(msp, nx, yy, 'Примечания', 2.5, K, style='ПТ_загл')
    mtxt(msp, nx, yy - 3 * K, '\\P'.join(f'{i + 1}. {n}' for i, n in enumerate(notes)), 2.0, 108, K, attach=1, spacing=1.0)
    return S
