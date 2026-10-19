"""Лист чертежа в DXF: рамка, основная надпись формы 3 (ГОСТ Р 21.101-2020), таблицы и текст. Единицы — мм листа."""
import ezdxf
from ezdxf.document import Drawing
from ezdxf.enums import TextEntityAlignment as A
from rd_stamp import PEOPLE, STAGE, ORG

# без служебных словарей и regapp генератора — файл как из обычного CAD
Drawing._create_ezdxf_metadata = lambda self: None
Drawing._update_ezdxf_metadata = lambda self: None
Drawing._create_appids = lambda self: self._create_appid_if_not_exist('HATCHBACKGROUNDCOLOR', 0)

FONT = 'isocpeur.ttf'
THICK, THIN = 50, 18          # толщины линий, сотые мм


def add_italic(doc):
    """Наклонный шрифт штампа (ISOCPEUR с наклоном 15°, как ISOCPEUI в штампе Заказчика)."""
    if 'GOST_I' not in doc.styles:
        st = doc.styles.new('GOST_I', dxfattribs={'font': FONT})
        st.dxf.width = 0.8


def new_doc():
    doc = ezdxf.new('R2013', setup=False)
    doc.units = 4
    st = doc.styles.new('GOST', dxfattribs={'font': FONT})
    st.dxf.width = 0.9
    add_italic(doc)
    doc.header['$TEXTSTYLE'] = 'GOST'
    for name, color, lw in (('Рамка', 7, THICK), ('Таблицы', 7, THIN), ('Текст', 7, THIN), ('В1', 5, 35),
                            ('Т3', 1, 35), ('Т4', 6, 35), ('К1', 30, 35), ('Узлы', 7, 35), ('Тонкие', 8, 13),
                            ('Штриховка', 8, 13), ('Размеры', 7, 13)):
        doc.layers.add(name, color=color, lineweight=lw)
    return doc


class Sheet:
    def __init__(self, doc, w, h):
        self.doc, self.w, self.h = doc, w, h
        self.m = doc.modelspace()

    # --- примитивы ---
    def line(self, x1, y1, x2, y2, layer='Таблицы', lw=None):
        e = self.m.add_line((x1, y1), (x2, y2), dxfattribs={'layer': layer})
        if lw:
            e.dxf.lineweight = lw
        return e

    def rect(self, x, y, w, h, layer='Таблицы', lw=None):
        e = self.m.add_lwpolyline([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], close=True,
                                  dxfattribs={'layer': layer})
        if lw:
            e.dxf.lineweight = lw
        return e

    def text(self, s, x, y, h=2.5, align='left', layer='Текст', rot=0, style='GOST'):
        al = {'left': A.MIDDLE_LEFT, 'center': A.MIDDLE_CENTER, 'right': A.MIDDLE_RIGHT,
              'bl': A.BOTTOM_LEFT, 'bc': A.BOTTOM_CENTER}[align]
        if style == 'GOST_I':          # наклонный шрифт штампа — однострочным MTEXT с \\Q15 (наклон виден везде)
            ap = {'left': 4, 'center': 5, 'right': 6, 'bl': 7, 'bc': 8}[align]
            mt = self.m.add_mtext('{\\W0.8;\\Q15;' + s + '}', dxfattribs={
                'layer': layer, 'style': style, 'char_height': h, 'attachment_point': ap, 'rotation': rot})
            mt.dxf.insert = (x, y)
            return mt
        t = self.m.add_text(s, height=h, rotation=rot, dxfattribs={'layer': layer, 'style': style})
        t.set_placement((x, y), align=al)
        return t

    def mtext(self, s, x, y, width, h=2.5, layer='Текст', attach=1, spacing=1.0, style='GOST'):
        if style == 'GOST_I':
            s = '{\\W0.8;\\Q15;' + s + '}'
        mt = self.m.add_mtext(s, dxfattribs={'layer': layer, 'style': style, 'char_height': h, 'width': width,
                                             'attachment_point': attach})
        mt.dxf.insert = (x, y)
        mt.dxf.line_spacing_factor = spacing
        return mt

    # --- рамка листа (поле подшивки и «Согласовано» — по листам Заказчика) ---
    def frame(self, fmt_label):
        add_italic(self.doc)
        I = dict(style='GOST_I')
        self.rect(0, 0, self.w, self.h, layer='Тонкие')
        self.rect(20, 5, self.w - 25, self.h - 10, layer='Рамка', lw=THICK)
        # Инв.№ подл. (25), Подпись и дата (35), Взам.инв.№ (25): графа 8–20 мм, подпись графы 8–13 мм
        self.line(8, 5, 20, 5, lw=THICK)
        self.line(8, 5, 8, 90, lw=THICK)
        self.line(13, 5, 13, 90)
        for y in (30, 65):
            self.line(8, y, 20, y)
        for label, ym in (('Инв.№ подл.', 17.5), ('Подпись и дата', 47.5), ('Взам.инв.№', 77.5)):
            self.text(label, 10.5, ym, h=2.5, align='center', rot=90, **I)
        # «Согласовано»: 0–20 мм по ширине, 90–155 мм по высоте
        self.line(0, 90, 20, 90, lw=THICK)
        self.line(0, 155, 20, 155, lw=THICK)
        for x in (5, 10, 15):
            self.line(x, 90, x, 155)
        for y in (110, 130, 145):
            self.line(5, y, 20, y)
        self.text('Согласовано', 2.5, 102, h=2.5, align='center', rot=90, **I)
        self.text(fmt_label, self.w - 5, 2.0, h=2.5, align='right', **I)
        self.text('Копировал', self.w - 75, 2.0, h=2.5, align='center', **I)

    def agreed(self, *a, **k):
        """«Согласовано» рисуется в frame() на каждом листе, как у Заказчика."""

    # --- основная надпись формы 3 (185×55) — по штампу Заказчика ---
    def stamp3(self, code, obj, building, title, sheet, sheets, stage=STAGE, org=ORG):
        add_italic(self.doc)
        I = dict(style='GOST_I')
        x0, y0 = self.w - 5 - 185, 5
        L = lambda x1, y1, x2, y2, lw=THICK: self.line(x0 + x1, y0 + y1, x0 + x2, y0 + y2, lw=lw)
        self.rect(x0, y0, 185, 55, layer='Рамка', lw=THICK)
        # левая часть: над шапкой 4 строки, шапка (30–35 мм), под шапкой 6 строк
        for y in (5, 10, 15, 20, 25, 40, 45, 50):
            L(0, y, 65, y, THIN)
        L(0, 30, 185, 30)
        L(0, 35, 65, 35)
        for x in (20, 40, 55, 65):
            L(x, 0, x, 55)
        for x in (10, 30):                           # «Изм.|Кол.уч» и «Лист|№ док» делятся только выше строк фамилий
            L(x, 30, x, 55)
        heads = [('Изм.', 5), ('Кол.уч', 15), ('Лист', 25), ('№ док', 35), ('Подп.', 47.5), ('Дата', 60)]
        for t, xc in heads:
            self.text(t, x0 + xc, y0 + 32.5, h=2.5, align='center', **I)
        for i, row in enumerate(PEOPLE):
            if row:
                role, name, date = row
                yy = y0 + 27.5 - i * 5
                self.text(role, x0 + 0.8, yy, h=3.0, **I)
                self.text(name, x0 + 20.8, yy, h=3.0, **I)
                self.text(date, x0 + 55.6, yy, h=3.0, **I)
        # правая часть: шифр 45–55, объект 30–45, раздел + стадия 15–30, наименование + организация 0–15
        L(65, 45, 185, 45)
        L(65, 15, 185, 15)
        L(135, 0, 135, 30)
        L(150, 15, 150, 30)
        L(165, 15, 165, 30)
        L(135, 25, 185, 25)
        self.text(code, x0 + 125, y0 + 50, h=5.5, align='center', **I)
        self.mtext(obj, x0 + 125, y0 + 37.5, 116, h=2.5, attach=5, **I)
        self.mtext(building, x0 + 100, y0 + 22.5, 66, h=3.0, attach=5, **I)
        self.mtext(title, x0 + 100, y0 + 7.5, 66, h=3.0, attach=5, **I)
        for t, xc in (('Стадия', 142.5), ('Лист', 157.5), ('Листов', 175)):
            self.text(t, x0 + xc, y0 + 27.5, h=3.0, align='center', **I)
        for t, xc in ((stage, 142.5), (str(sheet), 157.5), (str(sheets), 175)):
            self.text(t, x0 + xc, y0 + 20, h=3.5, align='center', **I)
        if org:
            self.mtext(org, x0 + 160, y0 + 7.5, 48, h=2.8, attach=5, **I)

    def table(self, x, y, widths, rows, row_h=8, head_h=None, h=2.5, aligns=None, title=None, title_h=3.5,
              heights=None):
        """rows[0] — шапка. Возвращает y низа таблицы. Ячейки с переносом — через MTEXT."""
        if title:
            self.text(title, x + sum(widths) / 2, y + 4, h=title_h, align='center')
        aligns = aligns or ['center'] * len(widths)
        yy = y
        total_w = sum(widths)
        for ri, r in enumerate(rows):
            rh = (heights[ri] if heights else (head_h if ri == 0 and head_h else row_h))
            xx = x
            for ci, (cell, cw) in enumerate(zip(r, widths)):
                if cell is None:
                    xx += cw
                    continue
                al = 'center' if ri == 0 else aligns[ci]
                if al == 'left':
                    self.mtext(cell, xx + 1.2, yy - rh / 2, cw - 2.4, h=h, attach=4)
                else:
                    self.mtext(cell, xx + cw / 2, yy - rh / 2, cw - 2.0, h=h, attach=5)
                xx += cw
            self.line(x, yy - rh, x + total_w, yy - rh, lw=THICK if ri == 0 else THIN)
            yy -= rh
        # контур и вертикали
        self.rect(x, yy, total_w, y - yy, lw=THICK)
        xx = x
        for cw in widths[:-1]:
            xx += cw
            self.line(xx, y, xx, yy, lw=THICK)
        return yy


def save(doc, path):
    """Сохранить без служебных меток генератора."""
    doc.header['$LASTSAVEDBY'] = ''
    doc.saveas(path)
