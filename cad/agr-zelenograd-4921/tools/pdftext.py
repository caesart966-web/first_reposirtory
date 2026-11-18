"""Разбор и правка текста в потоках содержимого PDF (pikepdf), без пересборки страниц."""
import re
import pikepdf

def hx(b):
    b = b.decode() if isinstance(b, bytes) else b
    return bytes.fromhex(b if len(b) % 2 == 0 else '0' + b)


WINANSI = {i: bytes([i]).decode('cp1252', errors='replace') for i in range(256)}


def parse_cmap(data):
    m = {}
    for blk in re.findall(rb'beginbfchar(.*?)endbfchar', data, re.S):
        for a, b in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', blk):
            m[hx(a)] = hx(b).decode('utf-16-be', errors='replace')
    for blk in re.findall(rb'beginbfrange(.*?)endbfrange', data, re.S):
        for a, b, c in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(<[0-9A-Fa-f]+>|\[[^\]]*\])', blk):
            lo, hi = int(a, 16), int(b, 16); n = (len(a) + 1) // 2
            if c.startswith(b'['):
                for i, d in enumerate(re.findall(rb'<([0-9A-Fa-f]+)>', c)):
                    m[(lo + i).to_bytes(n, 'big')] = hx(d).decode('utf-16-be', errors='replace')
            else:
                base = hx(c[1:-1]).decode('utf-16-be', errors='replace')
                for i in range(hi - lo + 1):
                    m[(lo + i).to_bytes(n, 'big')] = base[:-1] + chr(ord(base[-1]) + i)
    return m


class Font:
    def __init__(self, fobj):
        self.obj = fobj
        self.cid = fobj.get('/Subtype') == '/Type0'
        self.n = 2 if self.cid else 1
        self.map = {}
        if '/ToUnicode' in fobj:
            self.map = parse_cmap(fobj.ToUnicode.read_bytes())
        if not self.map and not self.cid:
            self.map = {bytes([i]): WINANSI[i] for i in range(256)}
        self.rev = {}
        for k, v in self.map.items():
            self.rev.setdefault(v, k)

    def decode(self, b):
        return ''.join(self.map.get(b[i:i + self.n], '�') for i in range(0, len(b), self.n))

    def encode(self, s):
        out = b''
        for ch in s:
            if ch not in self.rev:
                raise KeyError('в шрифте нет знака %r' % ch)
            out += self.rev[ch]
        return out


def fonts_of(res):
    out = {}
    if res is not None and '/Font' in res:
        for name, f in res.Font.items():
            out[name] = Font(f)
    return out


def walk(pdf, owner, res, cb, depth=0):
    """cb(owner, ops, index, font, text) для каждого Tj/TJ; возвращает True, если поток менялся."""
    ops = pikepdf.parse_content_stream(owner)
    fonts = fonts_of(res)
    cur = None
    changed = False
    for i, (operands, op) in enumerate(ops):
        o = str(op)
        if o == 'Tf':
            cur = fonts.get(str(operands[0]))
        elif o in ('Tj', 'TJ', "'", '"') and cur is not None:
            if cb(ops, i, cur):
                changed = True
        elif o == 'Do' and res is not None and '/XObject' in res:
            xo = res.XObject.get(str(operands[0]))
            if xo is not None and xo.get('/Subtype') == '/Form':
                walk(pdf, xo, xo.get('/Resources', res), cb, depth + 1)
    if changed and depth > 0:                     # форма: пишем сразу; страницу пишет вызывающий
        owner.write(pikepdf.unparse_content_stream(ops))
    return ops, changed


def op_text(ops, i, font):
    operands, op = ops[i]
    o = str(op)
    if o == 'TJ':
        return ''.join(font.decode(bytes(x)) for x in operands[0] if isinstance(x, pikepdf.String))
    return font.decode(bytes(operands[-1]))
