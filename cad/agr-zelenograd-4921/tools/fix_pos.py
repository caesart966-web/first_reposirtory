"""fix_pos.py ПОС_КОРР2.pdf ВЫХОД.pdf — Корректировка №3 раздела ПОС (СМ-3104.22-ПОС) для продления РнС.

* «КОРР.2» -> «КОРР.3» в штампах всех листов, «Корректировка №2» -> «№3» на обложке и титуле;
* лист изменений: строки 5 (л. 63 ТЧ — продолжительность) и 6 (л. 2 ГЧ — календарный график), тем же
  шрифтом GOST-Common; в его урезанной копии нет «5» — знак добавляется в сам встроенный шрифт из ISOCPEUR
  (контуры цифр у шрифтов совпадают знак в знак, номера глифов сдвинуты на GID_SHIFT);
* л. 63 ТЧ: продолжительность 47 -> MONTHS месяцев, метка изменения «3» -> «5»;
* л. 2 ГЧ: календарный график — новая картинка (pos_graph.py) на место старой, «47 месяцев» -> MONTHS,
  метка «4» -> «6».
Даты и подписи в штампах не трогаются: их ставит ГИП. Нужны pikepdf, fontTools, Pillow.
"""
import copy
import io
import sys
import zlib

import pikepdf
from fontTools.ttLib import TTFont

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from pdftext import Font, fonts_of  # noqa: E402
from pdfrepl import PageText  # noqa: E402
import pos_graph  # noqa: E402

OLD_MONTHS, MONTHS = 47, 58
ISO = '/root/.fonts/isocpeur.ttf'
GID_SHIFT = 17                                  # GOST-Common GID = ISOCPEUR GID + 17 для цифр (0–4, 6, 9 совпали до точки)
P_COVER, P_TITLE, P_CHANGES, P_DURATION, P_GRAPH = 1, 2, 3, 65, 67


def add_glyph(fontdict, ch, src=ISO):
    """Добавить знак ch во встроенный CID TrueType-шрифт (Identity) и вернуть его код."""
    df = fontdict.DescendantFonts[0]
    fd = df.FontDescriptor
    tt = TTFont(io.BytesIO(fd.FontFile2.read_bytes()))
    iso = TTFont(src)
    gname = iso.getBestCmap()[ord(ch)]
    gid = iso.getGlyphID(gname) + GID_SHIFT
    # проверка сдвига и рисунка на соседних цифрах (порядок контуров может отличаться — сравнивается набор точек)
    for c in '012346':
        a = tt['glyf'][tt.getGlyphOrder()[iso.getGlyphID(iso.getBestCmap()[ord(c)]) + GID_SHIFT]]
        b = iso['glyf'][iso.getBestCmap()[ord(c)]]
        assert sorted(map(tuple, a.getCoordinates(tt['glyf'])[0])) == sorted(map(tuple, b.getCoordinates(iso['glyf'])[0])), c
    tname = tt.getGlyphOrder()[gid]
    assert tt['glyf'][tname].numberOfContours == 0, 'знак уже есть'
    g = copy.deepcopy(iso['glyf'][gname])
    tt['glyf'][tname] = g
    g.recalcBounds(tt['glyf'])
    tt['hmtx'][tname] = iso['hmtx'][gname]
    b = io.BytesIO()
    tt.save(b)
    raw = b.getvalue()
    fd.FontFile2.write(zlib.compress(raw), filter=pikepdf.Name.FlateDecode)
    fd.FontFile2.Length1 = len(raw)
    upem = tt['head'].unitsPerEm
    df.W.append(gid)
    df.W.append(pikepdf.Array([round(tt['hmtx'][tname][0] * 1000 / upem)]))
    if '/CIDSet' in fd:
        cs = bytearray(fd.CIDSet.read_bytes())
        cs[gid // 8] |= 0x80 >> (gid % 8)
        fd.CIDSet.write(bytes(cs))
    tu = fontdict.ToUnicode.read_bytes()
    add = b'1 beginbfchar\n<%04X> <%04X>\nendbfchar\n' % (gid, ord(ch))
    fontdict.ToUnicode.write(tu.replace(b'endcmap', add + b'endcmap', 1))
    return gid.to_bytes(2, 'big')


def add_rows(pdf, page):
    """Строки 5 и 6 листа изменений — копии строк 1 и 2 со сдвигом на четыре строки вниз."""
    fd = page.obj.Resources.Font['/F0']
    f = Font(fd)
    if '5' not in f.rev:
        f.rev['5'] = add_glyph(fd, '5')
    X0, Y1 = float(page.obj.MediaBox[0]), float(page.obj.MediaBox[3])   # у этого листа начало координат в центре
    step = (225.45 - 157.02) / 3                # шаг строк по базовым линиям строк 1–4
    rows = [  # (базовая линия строки 1/2 + 4 шага, [(x, текст)])
        (157.02 + 4 * step, [(76.49, '5'), (107.74, 'л. 63 ТЧ'), (144.92, 'Измена продолжительность проведения работ'),
                             (444.65, '3')]),
        (179.70 + 4 * step, [(76.02, '6'), (109.83, 'л. 2 ГЧ'),
                             (144.70, 'Изменен календарный график работ в соответствии с новым сроком'), (444.65, '3')]),
    ]
    ops = b''
    for y, cells in rows:
        for x, s in cells:
            ops += b'BT /F0 10.0032 Tf 80 Tz 0 Tc 0 Tw 0 g 1 0 0 1 %.2f %.2f Tm <%s> Tj ET\n' % (
                X0 + x, Y1 - y, f.encode(s).hex().encode())
    page.contents_add(pdf.make_stream(b'q\n'), prepend=True)
    page.contents_add(pdf.make_stream(b'Q\nq\n' + ops + b'Q\n'))


def red_label(pt, old, new):
    """Метка изменения: единственный кусок текста old красного цвета."""
    fill, hits = None, []
    for i, (o, op) in enumerate(pt.ops):
        s = str(op)
        if s in ('rg', 'g', 'sc', 'scn'):
            fill = [float(x) for x in o]
        for j, p in enumerate(pt.pieces):
            if p[0] == i and p[3] == old and fill and len(fill) == 3 and fill[0] > 0.9 and fill[1] < 0.1:
                hits.append(j)
    assert len(hits) == 1, (old, hits)
    pt.pieces[hits[0]][3] = new
    pt.dirty.add(hits[0])


def replace_graph(pdf, page, png):
    xo = [v for v in page.obj.Resources.XObject.values()
          if v.get('/Subtype') == '/Image' and int(v.Width) == 1318 and int(v.Height) == 383]
    assert len(xo) == 1
    from PIL import Image
    im = Image.open(png).convert('RGB')
    x = xo[0]
    x.write(zlib.compress(im.tobytes()), filter=pikepdf.Name.FlateDecode)
    x.Width, x.Height = im.width, im.height
    x.ColorSpace, x.BitsPerComponent = pikepdf.Name.DeviceRGB, 8
    for k in ('/DecodeParms', '/SMask', '/Decode'):
        if k in x:
            del x[k]


def main(src, dst, graph_png=None):
    pdf = pikepdf.open(src)
    n = 0
    for no, page in enumerate(pdf.pages, 1):
        pt = PageText(page)
        k = pt.replace('КОРР.2', 'КОРР.3')
        if no in (P_COVER, P_TITLE):
            assert pt.replace('Корректировка №2', 'Корректировка №3') == 1
        if no == P_DURATION:
            assert pt.replace('%d месяц' % OLD_MONTHS, '%d месяц' % MONTHS) == 1
            red_label(pt, '3', '5')
        if no == P_GRAPH:
            assert pt.replace('составляет %d' % OLD_MONTHS, 'составляет %d' % MONTHS) == 1
            red_label(pt, '4', '6')
        n += k
        pt.write(pdf)
    assert n >= 60, n
    add_rows(pdf, pdf.pages[P_CHANGES - 1])
    if graph_png is None:
        graph_png = dst + '.graph.png'
        pos_graph.draw(months=MONTHS).save(graph_png)
    replace_graph(pdf, pdf.pages[P_GRAPH - 1], graph_png)
    pdf.save(dst, deterministic_id=True)
    print('КОРР.2 -> КОРР.3 на', n, 'листах; срок', OLD_MONTHS, '->', MONTHS, 'мес.')


if __name__ == '__main__':
    main(*sys.argv[1:4])
