"""Замена текста в PDF, когда Word разбил строку на куски (отдельные Tj/TJ, элементы TJ с кернингом).

Куски текста страницы склеиваются в одну строку с картой «знак -> (оператор, элемент, позиция)»;
найденное вхождение меняется по знакам: одинаковая длина — знак в знак, лишнее дописывается в кусок
с последним знаком старого текста. Каждый измененный кусок перекодируется своим шрифтом; знака нет —
ошибка (подменять шрифт не будем). Нужен pikepdf.
"""
import re
import pikepdf
from pdftext import fonts_of


class PageText:
    def __init__(self, page):
        self.page = page
        self.ops = pikepdf.parse_content_stream(page)
        fonts = fonts_of(page.obj.get('/Resources'))
        self.pieces = []                       # [op, elem|None, font, text]
        cur = None
        for i, (o, op) in enumerate(self.ops):
            s = str(op)
            if s == 'Tf':
                cur = fonts.get(str(o[0]))
            elif s == 'TJ' and cur is not None:
                for k, x in enumerate(o[0]):
                    if isinstance(x, pikepdf.String):
                        self.pieces.append([i, k, cur, cur.decode(bytes(x))])
            elif s in ('Tj', "'", '"') and cur is not None:
                self.pieces.append([i, None, cur, cur.decode(bytes(o[-1]))])
        self.dirty = set()

    def text(self):
        return ''.join(p[3] for p in self.pieces)

    def _locate(self, pos):
        n = 0
        for j, p in enumerate(self.pieces):
            if pos < n + len(p[3]):
                return j, pos - n
            n += len(p[3])
        raise IndexError(pos)

    def replace(self, old, new, count=None, regex=False):
        """Заменить old на new (regex — old это шаблон, new — строка той же длины, что совпадение, или длиннее)."""
        done = 0
        while True:
            t = self.text()
            m = re.search(old if regex else re.escape(old), t)
            if not m or (count is not None and done >= count):
                break
            a, b = m.span()
            o = t[a:b]
            for q in range(min(len(o), len(new))):
                if o[q] != new[q]:
                    j, off = self._locate(a + q)
                    s = self.pieces[j][3]
                    self.pieces[j][3] = s[:off] + new[q] + s[off + 1:]
                    self.dirty.add(j)
            if len(new) > len(o):
                j, off = self._locate(b - 1)
                s = self.pieces[j][3]
                self.pieces[j][3] = s[:off + 1] + new[len(o):] + s[off + 1:]
                self.dirty.add(j)
            elif len(new) < len(o):
                raise ValueError('укорачивание не поддерживается: %r' % old)
            done += 1
            if not regex and old in new:
                break
        return done

    def write(self, pdf):
        for j in sorted(self.dirty):
            i, k, font, s = self.pieces[j]
            operands, op = self.ops[i]
            enc = pikepdf.String(font.encode(s))
            if k is None:
                operands = list(operands)
                operands[-1] = enc
            else:
                arr = operands[0]
                arr[k] = enc
            self.ops[i] = pikepdf.ContentStreamInstruction(operands, op)
        if self.dirty:
            self.page.obj.Contents = pdf.make_stream(pikepdf.unparse_content_stream(self.ops))
        return len(self.dirty)
