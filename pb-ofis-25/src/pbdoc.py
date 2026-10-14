"""Текстовая часть ПБ-25 в PDF: рамка и основная надпись как в исходном томе (ООО «Технология», AutoCAD),
шрифт ISOCPEUR курсивом — здесь свободный osifont с наклоном 15°. Разметка исходника — см. parse()."""
import math, os, re
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, '..', 'fonts')
pdfmetrics.registerFont(TTFont('F', os.path.join(FONTS, 'osifont-lgpl3fe.ttf')))

SHIFR = 'ОПР-01/24/2026-ПБ-25'
ORG = 'ООО "Технология"'
GIP = 'Выберанец П.В.'
STAGE = 'П'

INK, GREY = (0.125, 0.125, 0.125), (0.47, 0.47, 0.47)
SLANT = math.tan(math.radians(15))
BODY, PITCH = 15.34, 5.25          # кегль, пт; шаг строк, мм — как в исходном томе (шрифт 3,5 мм)
X_L, X_R, INDENT, HANG = 23.0, 202.0, 12.5, 7.0
Y_TOP, Y_BOT = 284.0, 46.0
THICK, THIN = 2.0, 0.6


def tw(s, size):
    return stringWidth(s, 'F', size) / mm


def wrap(text, size, width):
    out, line = [], ''
    for w in text.split(' '):
        if not w:
            continue
        t = (line + ' ' + w) if line else w
        if tw(t, size) <= width:
            line = t
            continue
        if line:
            out.append(line)
        while tw(w, size) > width and len(w) > 1:       # слово длиннее строки — режем
            k = len(w)
            while k > 1 and tw(w[:k], size) > width:
                k -= 1
            out.append(w[:k]); w = w[k:]
        line = w
    if line:
        out.append(line)
    return out or ['']


class Vol:
    """Листы текстовой части: рамка, основная надпись на каждом листе, курсив."""

    def __init__(self, path, first_sheet=1, total=None, title='Текстовая часть'):
        self.c = canvas.Canvas(path, pagesize=(210 * mm, 297 * mm))
        self.c.setTitle(SHIFR)
        self.c.setAuthor(ORG.replace('"', ''))
        self.c.setCreator('')
        self.c.setProducer('')
        self.path, self.sheet, self.total, self.title = path, first_sheet - 1, total, title
        self.y = None
        self.marks = {}

    # --- текст ---
    def text(self, x, y, s, size=BODY, color=INK, align='L', slant=True):
        c = self.c
        w = tw(s, size)
        if align == 'C':
            x -= w / 2
        elif align == 'R':
            x -= w
        c.saveState()
        c.setFillColorRGB(*color)
        c.setFont('F', size)
        c.transform(1, 0, SLANT if slant else 0, 1, x * mm, y * mm)
        c.drawString(0, 0, s)
        c.restoreState()

    def line(self, x1, y1, x2, y2, w=THIN):
        self.c.setLineWidth(w)
        self.c.setStrokeColorRGB(*INK)
        self.c.line(x1 * mm, y1 * mm, x2 * mm, y2 * mm)

    # --- лист ---
    def frame(self):
        self.sheet += 1
        L = self.line
        L(20, 5, 204.9, 5, THICK); L(20, 292, 204.9, 292, THICK); L(20, 5, 20, 292, THICK); L(204.9, 5, 204.9, 292, THICK)
        draw_stamp(self.text, L, 0, self.title, self.sheet, self.total)

    def new_page(self):
        if self.y is not None:
            self.c.showPage()
        self.frame()
        self.y = Y_TOP

    def need(self, h):
        if self.y is None or self.y - h < Y_BOT:
            self.new_page()

    def save(self):
        self.c.showPage()
        self.c.save()


def draw_stamp(T, L, dx, title, sheet, total, sheet_text=None):
    """Основная надпись 185×35 (как в исходном томе); dx — сдвиг вправо от положения на листе А4."""
    def l(x1, y1, x2, y2, w=THIN):
        L(x1 + dx, y1, x2 + dx, y2, w)

    def t(x, y, s, size=BODY, color=INK, align='L'):
        T(x + dx, y, s, size, color, align)
    l(20, 40, 204.9, 40, THICK); l(20, 5, 20, 40, THICK); l(204.9, 5, 204.9, 40, THICK); l(20, 5, 204.9, 5, THICK)
    l(92, 5, 92, 40, THICK); l(92, 25, 204.9, 25, THICK); l(20, 25, 92, 25, THICK)
    l(154.9, 5, 154.9, 25, THICK); l(154.9, 15, 204.9, 15, THICK); l(154.9, 20, 204.9, 20)
    l(172.9, 15, 172.9, 25); l(187.9, 15, 187.9, 25)
    for y in (10, 15, 20, 30, 35):
        l(20, y, 92, y)
    for x in (30, 54):
        l(x, 25, x, 40)
    for x in (43, 67, 82):
        l(x, 5, x, 40)
    for s, x in (('Изм.', 21.7), ('Кол. уч.', 31.0), ('Лист', 44.6), ('№ док.', 55.5), ('Подп.', 70.3), ('Дата', 83.2)):
        t(x, 26.3, s, 10.2, GREY)
    for s, y in (('Разработал', 21.3), ('Проверил', 16.3), ('ГИП', 11.3), ('Н.контр.', 6.3)):
        t(21.5, y, s, 10.6, GREY)
    t(44.5, 11.3, GIP, 10.2)
    t(158.1, 21.3, 'Стадия', 10.6, GREY); t(176.5, 21.3, 'Лист', 10.6, GREY); t(190.7, 21.3, 'Листов', 10.6, GREY)
    t(163.9, 16.3, STAGE, 11.0, align='C')
    t(180.4, 16.3, sheet_text or f'{sheet:02d}', 11.0, align='C')
    if total:
        t(196.4, 16.3, str(total), 11.0, align='C')
    t(148.5, 29.0, SHIFR, 29.9, align='C')
    lines = title.split('\n')
    if len(lines) == 1:
        t(123.5, 12.5, title, 21.0, align='C')
    else:
        for k, s in enumerate(lines):
            t(123.5, 18.4 - k * 6.2, s, 15.0, align='C')
    t(179.9, 8.3, ORG, 15.0, align='C')


# ---------- разметка ----------
# # заголовок раздела        ## подраздел        ### пункт (слева)
# пустая строка — конец абзаца; "- " — перечисление; "1) " — нумерованный пункт
# "> " — строка без отступа (формулы); ">> " — по центру
# @table 20,60,40 | L,C,C   (первая строка — шапка; "!! текст" — строка-подзаголовок на всю ширину) ... @end
# @cap подпись таблицы   @page — новый лист   @gap 3 — отступ, мм
def parse(src):
    blocks, para = [], []
    lines = src.split('\n')
    i = 0

    def flush():
        if para:
            blocks.append(('p', ' '.join(s.strip() for s in para)))
            para.clear()

    while i < len(lines):
        ln = lines[i].rstrip()
        s = ln.strip()
        if s.startswith('%'):                      # комментарий
            i += 1; continue
        if not s:
            flush(); i += 1; continue
        if s.startswith('@table'):
            flush()
            spec = s[6:].strip()
            cols, _, al = spec.partition('|')
            widths = [float(x) for x in cols.split(',')]
            aligns = [a.strip() for a in al.split(',')] if al.strip() else ['L'] * len(widths)
            rows = []
            i += 1
            while not lines[i].strip().startswith('@end'):
                r = lines[i].strip()
                if r and not r.startswith('%'):
                    if r.startswith('!!'):
                        rows.append(r[2:].strip())
                    else:
                        rows.append([x.strip() for x in r.split('|')])
                i += 1
            blocks.append(('table', widths, aligns, rows))
            i += 1; continue
        m = re.match(r'^(#{1,3}) (.*)$', s)
        if m:
            flush(); blocks.append(('h%d' % len(m.group(1)), m.group(2))); i += 1; continue
        if s.startswith('@'):
            flush()
            cmd, _, arg = s[1:].partition(' ')
            blocks.append((cmd, arg))
            i += 1; continue
        m = re.match(r'^(-|\d+\)|[а-я]\))\s+(.*)$', s)
        if m:
            flush()
            item = [m.group(2)]
            i += 1
            while i < len(lines) and lines[i].strip() and lines[i].startswith('  ') and not re.match(r'^\s*(-|\d+\)|[а-я]\))\s', lines[i]):
                item.append(lines[i].strip()); i += 1
            blocks.append(('li', m.group(1), ' '.join(item)))
            continue
        if s.startswith('>> '):
            flush(); blocks.append(('center', s[3:])); i += 1; continue
        if s.startswith('> '):
            flush(); blocks.append(('flat', s[2:])); i += 1; continue
        para.append(s)
        i += 1
    flush()
    return blocks


def render(v, blocks):
    T = v.text
    for b in blocks:
        k = b[0]
        if k in ('h1', 'h2'):
            size = 20.8 if k == 'h1' else 18.0
            pitch = 7.2 if k == 'h1' else 6.4
            ls = wrap(b[1], size, X_R - X_L - 6)
            v.need(4 + pitch * len(ls) + PITCH * 3)       # заголовок не остаётся внизу листа без текста
            v.marks.setdefault(b[1], v.sheet)
            if v.y < Y_TOP:
                v.y -= 4
            for l in ls:
                v.y -= pitch
                T((X_L + X_R) / 2, v.y, l, size, align='C')
            v.y -= 2.5
        elif k == 'h3':
            ls = wrap(b[1], BODY, X_R - X_L)
            v.need(2 + PITCH * (len(ls) + 2))
            v.marks.setdefault(b[1], v.sheet)
            v.y -= 1.5
            for l in ls:
                v.y -= PITCH; T(X_L + INDENT, v.y, l)
            v.y -= 0.5
        elif k == 'p':
            ls = wrap(b[1], BODY, X_R - X_L - INDENT)
            ls = [ls[0]] + wrap(' '.join(ls[1:]), BODY, X_R - X_L) if len(ls) > 1 else ls
            for j, l in enumerate(ls):
                v.need(PITCH)
                v.y -= PITCH
                T(X_L + (INDENT if j == 0 else 0), v.y, l)
            v.y -= 1.2
        elif k == 'li':
            lab, txt = b[1], b[2]
            ls = wrap(txt, BODY, X_R - X_L - HANG)
            for j, l in enumerate(ls):
                v.need(PITCH)
                v.y -= PITCH
                if j == 0:
                    T(X_L, v.y, lab)
                T(X_L + HANG, v.y, l)
            v.y -= 0.6
        elif k in ('flat', 'center'):
            ls = wrap(b[1], BODY, X_R - X_L)
            for l in ls:
                v.need(PITCH); v.y -= PITCH
                if k == 'center':
                    T((X_L + X_R) / 2, v.y, l, align='C')
                else:
                    T(X_L, v.y, l)
            v.y -= 1.0
        elif k == 'cap':
            ls = wrap(b[1], BODY, X_R - X_L)
            v.need(PITCH * (len(ls) + 3))
            v.y -= 1.0
            for l in ls:
                v.y -= PITCH; T(X_L, v.y, l)
            v.y -= 1.5
        elif k == 'gap':
            v.y -= float(b[1] or 3)
        elif k == 'page':
            v.y = Y_BOT - 1; v.need(1)
        elif k == 'table':
            table(v, *b[1:])
        else:
            raise ValueError(f'неизвестный блок {k}')


TS, TP = 12.0, 4.3        # кегль и шаг строк в таблицах


def table(v, widths, aligns, rows):
    head, body = rows[0], rows[1:]
    x0 = X_L - 1
    k = (X_R - x0) / sum(widths)                   # ширины в разметке — доли, таблица всегда на всю ширину поля
    widths = [w * k for w in widths]
    W = sum(widths)

    def cell_lines(r):
        return [wrap(str(t), TS, w - 2) for t, w in zip(r, widths)]

    def draw_row(r, top, h, header=False):
        x = x0
        for j, (w, ls) in enumerate(zip(widths, cell_lines(r))):
            al = 'C' if header else aligns[j] if j < len(aligns) else 'L'
            yy = top - 3.6
            for l in ls:
                if al == 'C':
                    v.text(x + w / 2, yy, l, TS, align='C')
                elif al == 'R':
                    v.text(x + w - 1, yy, l, TS, align='R')
                else:
                    v.text(x + 1, yy, l, TS)
                yy -= TP
            x += w
        v.line(x0, top - h, x0 + W, top - h)
        xx = x0
        for w in widths:
            v.line(xx, top, xx, top - h)
            xx += w
        v.line(xx, top, xx, top - h)

    def row_h(r):
        return max(len(ls) for ls in cell_lines(r)) * TP + 1.8

    def head_out():
        h = row_h(head)
        v.line(x0, v.y, x0 + W, v.y)
        draw_row(head, v.y, h, True)
        v.y -= h

    hh = row_h(head)
    v.need(hh + 12)
    v.y -= 1
    head_out()
    for r in body:
        if isinstance(r, str):                      # подзаголовок на всю ширину
            ls = wrap(r, TS, W - 2)
            h = len(ls) * TP + 1.8
            if v.y - h < Y_BOT:
                v.new_page(); v.y -= 1; head_out()
            yy = v.y - 3.6
            for l in ls:
                v.text(x0 + W / 2, yy, l, TS, align='C'); yy -= TP
            v.line(x0, v.y - h, x0 + W, v.y - h); v.line(x0, v.y, x0, v.y - h); v.line(x0 + W, v.y, x0 + W, v.y - h)
            v.y -= h
            continue
        h = row_h(r)
        if v.y - h < Y_BOT:
            v.new_page(); v.y -= 1; head_out()
        draw_row(r, v.y, h)
        v.y -= h
    v.y -= 2.5


def build(path, src, first_sheet, total, vars_=None, title='Текстовая часть'):
    if vars_:
        src = re.sub(r'\{\{(\w+)\}\}', lambda m: str(vars_[m.group(1)]), src)
    v = Vol(path, first_sheet, total, title)
    render(v, parse(src))
    v.save()
    build.marks = v.marks
    return v.sheet
