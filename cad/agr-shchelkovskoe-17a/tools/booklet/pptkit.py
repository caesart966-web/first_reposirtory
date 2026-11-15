"""Примитивы листа А3 по шаблону буклета АГР (координаты в пунктах, начало — левый верхний угол)."""
import hashlib
import os
import re

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu

Image.MAX_IMAGE_PIXELS = None
W_PT, H_PT = 1190.52, 841.92
MONT, CG = 'Montserrat', 'Century Gothic'
# поправка «верх букв по PDF шаблона» -> «верх текстовой рамки» (доля кегля)
TOP_K = {MONT: 0.265, CG: 0.275}


_UNIT = re.compile(r'(\d)\s(мм|м²|м/м|м|га|тыс\.|шт\.|эт\.|%)(?=[\s,.;:)]|$)')


def typo(t):
    """Неразрывные пробелы: число и единица, тире не переносится в начало строки."""
    t = _UNIT.sub('\\1\u00a0\\2', t)
    t = t.replace(' — ', '\u00a0— ').replace('№ ', '№\u00a0')
    return t


def E(v):
    return Emu(int(round(v * 12700)))


def rgb(c):
    if isinstance(c, str):
        c = c.lstrip('#')
        return RGBColor.from_string(c.upper())
    if isinstance(c, (int, float)):
        v = int(round(c * 255))
        return RGBColor(v, v, v)
    return RGBColor(*[int(round(x * 255)) for x in c])


def _nostyle(sh):
    """Убрать ссылку на стиль темы (тень, обводка и шрифт по умолчанию)."""
    st = sh._element.find(qn('p:style'))
    if st is not None:
        sh._element.remove(st)


class Deck:
    def __init__(self, cache):
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = E(W_PT), E(H_PT)
        self.layout = self.prs.slide_layouts[6]
        self.cache = cache
        os.makedirs(cache, exist_ok=True)

    def slide(self):
        return Slide(self, self.prs.slides.add_slide(self.layout))

    def save(self, path):
        self.prs.save(path)


class Slide:
    def __init__(self, deck, s):
        self.deck, self.s = deck, s

    # --- фигуры ---------------------------------------------------------------------------------------------------
    def rect(self, x0, y0, x1, y1, fill=None, line=None, lw=0.5, shape=MSO_SHAPE.RECTANGLE, dash=None):
        sh = self.s.shapes.add_shape(shape, E(x0), E(y0), E(x1 - x0), E(y1 - y0))
        _nostyle(sh)
        if fill is None:
            sh.fill.background()
        else:
            sh.fill.solid(); sh.fill.fore_color.rgb = rgb(fill)
        if line is None:
            sh.line.fill.background()
        else:
            sh.line.color.rgb = rgb(line); sh.line.width = E(lw)
            if dash:
                sh.line.dash_style = dash
        sh.text_frame.text = ''
        return sh

    def line(self, x0, y0, x1, y1, color=0, lw=1.0, dash=None):
        c = self.s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, E(x0), E(y0), E(x1), E(y1))
        _nostyle(c)
        c.line.color.rgb = rgb(color); c.line.width = E(lw)
        if dash:
            c.line.dash_style = dash
        return c

    def tri(self, cx, cy, size, fill, rot=0):
        sh = self.s.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE, E(cx - size / 2), E(cy - size / 2), E(size),
                                     E(size))
        _nostyle(sh)
        sh.fill.solid(); sh.fill.fore_color.rgb = rgb(fill)
        sh.line.color.rgb = rgb('#FFFFFF'); sh.line.width = E(0.5)
        sh.rotation = rot
        return sh

    # --- текст ----------------------------------------------------------------------------------------------------
    def text(self, x, y, w, paras, size=10, font=MONT, bold=False, italic=False, color=0, align='l', h=None,
             spacing=None, anchor='t', y_is_glyph_top=True, space_after=0):
        """paras: строка (абзацы через \\n) или список абзацев; абзац — строка или список прогонов
        (текст, {size, bold, italic, color, font, sup})."""
        if isinstance(paras, str):
            paras = paras.split('\n')
        top = y - TOP_K.get(font, 0.21) * size if y_is_glyph_top else y
        if h is None:
            h = size * 1.3 * max(1, len(paras))
        tb = self.s.shapes.add_textbox(E(x), E(top), E(w), E(h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.auto_size = None
        for side in ('margin_left', 'margin_right', 'margin_top', 'margin_bottom'):
            setattr(tf, side, 0)
        tf.vertical_anchor = {'t': MSO_ANCHOR.TOP, 'm': MSO_ANCHOR.MIDDLE, 'b': MSO_ANCHOR.BOTTOM}[anchor]
        for i, para in enumerate(paras):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = {'l': PP_ALIGN.LEFT, 'r': PP_ALIGN.RIGHT, 'c': PP_ALIGN.CENTER, 'j': PP_ALIGN.JUSTIFY}[align]
            if spacing:
                p.line_spacing = spacing
            if space_after:
                p.space_after = E(space_after)
            runs = [(para, {})] if isinstance(para, str) else para
            for txt, st in runs:
                r = p.add_run()
                r.text = typo(txt)
                f = r.font
                f.name = st.get('font', font)
                f.size = E(st.get('size', size))
                f.bold = st.get('bold', bold)
                f.italic = st.get('italic', italic)
                f.color.rgb = rgb(st.get('color', color))
                rPr = r._r.get_or_add_rPr()
                for tag in ('a:latin', 'a:cs'):
                    el = rPr.find(qn(tag))
                    if el is None:
                        el = rPr.makeelement(qn(tag), {})
                        rPr.append(el)
                    el.set('typeface', st.get('font', font))
                if st.get('sup'):
                    rPr.set('baseline', '30000')
        return tb

    # --- изображения ----------------------------------------------------------------------------------------------
    def image(self, path, x0, y0, x1, y1, mode='contain', focus=(0.5, 0.5), dpi=300, fmt=None, valign='m',
              halign='c', trim=0):
        """Вписать (contain) или заполнить с обрезкой (cover) прямоугольник. Возвращает фактическую рамку."""
        im = Image.open(path)
        if trim:
            import numpy as np
            a = np.asarray(im.convert('L'))
            ys, xs = np.nonzero(a < 245)
            if len(xs):
                pad = int(trim)
                im = im.crop((max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad + 1, im.size[0]),
                              min(ys.max() + pad + 1, im.size[1])))
        W, H = im.size
        fw, fh = x1 - x0, y1 - y0
        if mode == 'cover':
            k = max(fw / W, fh / H)
            cw, ch = fw / k, fh / k
            cx = min(max(focus[0] * W - cw / 2, 0), W - cw)
            cy = min(max(focus[1] * H - ch / 2, 0), H - ch)
            box = (int(round(cx)), int(round(cy)), int(round(cx + cw)), int(round(cy + ch)))
            px, py, pw, ph = x0, y0, fw, fh
        else:
            k = min(fw / W, fh / H)
            box = (0, 0, W, H)
            pw, ph = W * k, H * k
            px = x0 + {'l': 0, 'c': (fw - pw) / 2, 'r': fw - pw}[halign]
            py = y0 + {'t': 0, 'm': (fh - ph) / 2, 'b': fh - ph}[valign]
        crop = im.crop(box)
        target = (int(round(pw / 72 * dpi)), int(round(ph / 72 * dpi)))
        if crop.size[0] > target[0] * 1.05:
            crop = crop.resize(target, Image.LANCZOS)
        has_alpha = crop.mode in ('RGBA', 'LA', 'P')
        if fmt is None:
            fmt = 'png' if has_alpha or path.endswith('.png') and 'im-' not in os.path.basename(path) else 'jpg'
        key = hashlib.md5(('%s|%s|%s|%s|%s|%s' % (path, box, crop.size, fmt, os.path.getmtime(path), trim)).encode()
                          ).hexdigest()
        out = os.path.join(self.deck.cache, key + '.' + fmt)
        if not os.path.exists(out):
            if fmt == 'jpg':
                crop.convert('RGB').save(out, quality=92, subsampling=0, optimize=True)
            else:
                if crop.mode == 'RGBA':
                    bg = Image.new('RGB', crop.size, 'white')
                    bg.paste(crop, mask=crop.split()[3])
                    crop = bg
                crop.convert('RGB').save(out, optimize=True)
        self.s.shapes.add_picture(out, E(px), E(py), E(pw), E(ph))
        return px, py, px + pw, py + ph
