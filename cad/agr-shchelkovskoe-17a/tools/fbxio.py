"""Чтение и запись двоичного FBX 7.x без потерь.

Свойства, которые не меняются, пишутся обратно теми же байтами, что были в
исходном файле (в том числе сжатые массивы), поэтому файл без правок
собирается побайтно одинаковым с исходным.
"""
import struct
import zlib

MAGIC = b'Kaydara FBX Binary  \x00\x1a\x00'
SCALAR = {'Y': '<h', 'C': '<?', 'I': '<i', 'F': '<f', 'D': '<d', 'L': '<q'}
ARRAY = {'f': 'f', 'd': 'd', 'l': 'q', 'i': 'i', 'b': '?'}


class Prop:
    __slots__ = ('t', 'raw', '_v', 'enc')

    def __init__(self, t, raw, enc=0):
        self.t, self.raw, self.enc, self._v = t, raw, enc, None

    @property
    def value(self):
        if self._v is None:
            t, raw = self.t, self.raw
            if t in SCALAR:
                self._v = struct.unpack(SCALAR[t], raw)[0]
            elif t in ARRAY:
                n, enc, cl = struct.unpack_from('<III', raw, 0)
                data = raw[12:12 + cl]
                if enc:
                    data = zlib.decompress(data)
                self._v = list(struct.unpack('<%d%s' % (n, ARRAY[t]), data))
            elif t == 'S':
                self._v = raw[4:].decode('utf-8')
            else:
                self._v = raw[4:]
        return self._v

    def set(self, v):
        t = self.t
        if t in SCALAR:
            self.raw = struct.pack(SCALAR[t], v)
        elif t in ARRAY:
            data = struct.pack('<%d%s' % (len(v), ARRAY[t]), *v)
            enc = self.enc
            if enc:
                data = zlib.compress(data, 1)
            self.raw = struct.pack('<III', len(v), enc, len(data)) + data
        elif t == 'S':
            b = v.encode('utf-8')
            self.raw = struct.pack('<I', len(b)) + b
        else:
            self.raw = struct.pack('<I', len(v)) + v
        self._v = v


class Node:
    __slots__ = ('name', 'props', 'kids', 'sentinel')

    def __init__(self, name, props, kids, sentinel):
        self.name, self.props, self.kids, self.sentinel = name, props, kids, sentinel

    def find(self, name):
        return [k for k in self.kids if k.name == name]

    def one(self, name):
        r = self.find(name)
        assert len(r) == 1, (self.name, name, len(r))
        return r[0]

    def vals(self):
        return [p.value for p in self.props]


class Fbx:
    def __init__(self, path):
        b = open(path, 'rb').read()
        assert b[:23] == MAGIC, b[:23]
        self.version = struct.unpack_from('<I', b, 23)[0]
        self.wide = self.version >= 7500
        self.hdr = '<QQQ' if self.wide else '<III'
        self.hsz = 24 if self.wide else 12
        self.b = b
        self.top = []
        pos = 27
        while True:
            n, pos = self._node(pos)
            if n is None:
                break
            self.top.append(n)
        tail = b[pos:]
        # подвал: 16 байт кода, нули выравнивания, версия, 120 нулей, 16 байт метки.
        # Число нулей у экспортёров разное: «std» — (16 - pos % 16) + 4 (файл кратен 16),
        # «sdk» — дополнение pos до кратного 16, не меньше 4 байт (длина файла дает остаток 12).
        self.footer_id = tail[:16]
        z = len(tail) - 16 - 4 - 120 - 16
        assert z >= 0 and tail[16:16 + z] == b'\0' * z, 'подвал файла устроен иначе'
        assert tail[16 + z:20 + z] == struct.pack('<I', self.version) and tail[20 + z:140 + z] == b'\0' * 120, \
            'подвал файла устроен иначе'
        self.footer_magic = tail[140 + z:]
        assert len(self.footer_magic) == 16
        self.footer_rule = next((r for r in ('std', 'sdk') if self._footer_zeros(r, pos) == z), None)
        assert self.footer_rule, ('неизвестное выравнивание подвала', pos % 16, z)
        del self.b

    @staticmethod
    def _footer_zeros(rule, pos):
        if rule == 'std':
            return 16 - pos % 16 + 4
        z = -pos % 16
        return z + 16 if z < 4 else z

    def _node(self, pos):
        b = self.b
        end, nprop, plen = struct.unpack_from(self.hdr, b, pos)
        pos += self.hsz
        nl = b[pos]
        pos += 1
        name = b[pos:pos + nl].decode('ascii')
        pos += nl
        if end == 0:
            return None, pos
        props = []
        p0 = pos
        for _ in range(nprop):
            t = chr(b[pos])
            pos += 1
            if t in SCALAR:
                n = struct.calcsize(SCALAR[t])
                props.append(Prop(t, b[pos:pos + n]))
                pos += n
            elif t in ARRAY:
                cnt, enc, cl = struct.unpack_from('<III', b, pos)
                props.append(Prop(t, b[pos:pos + 12 + cl], enc))
                pos += 12 + cl
            elif t in 'SR':
                n = struct.unpack_from('<I', b, pos)[0]
                props.append(Prop(t, b[pos:pos + 4 + n]))
                pos += 4 + n
            else:
                raise ValueError('неизвестный тип свойства %r' % t)
        assert pos - p0 == plen
        kids = []
        sentinel = False
        while pos < end:
            k, pos = self._node(pos)
            if k is None:
                sentinel = True
                break
            kids.append(k)
        assert pos == end, (name, pos, end)
        return Node(name, props, kids, sentinel), end

    def _write(self, n, out, pos):
        nb = n.name.encode('ascii')
        pbytes = b''.join(p.t.encode('ascii') + p.raw for p in n.props)
        start = pos
        pos += self.hsz + 1 + len(nb) + len(pbytes)
        body = []
        for k in n.kids:
            pos = self._write(k, body, pos)
        if n.sentinel:
            body.append(b'\0' * (self.hsz + 1))
            pos += self.hsz + 1
        out.append(struct.pack(self.hdr, pos, len(n.props), len(pbytes)) + bytes([len(nb)]) + nb + pbytes)
        out.extend(body)
        assert start + sum(map(len, out[-(len(body) + 1):])) == pos
        return pos

    def dumps(self):
        out = [MAGIC + struct.pack('<I', self.version)]
        pos = 27
        for n in self.top:
            pos = self._write(n, out, pos)
        out.append(b'\0' * (self.hsz + 1))
        pos += self.hsz + 1
        z = self._footer_zeros(self.footer_rule, pos)
        out.append(self.footer_id + b'\0' * z + struct.pack('<I', self.version)
                   + b'\0' * 120 + self.footer_magic)
        return b''.join(out)

    def one(self, name):
        r = [n for n in self.top if n.name == name]
        assert len(r) == 1, name
        return r[0]

    def walk(self):
        st = list(reversed(self.top))
        while st:
            n = st.pop()
            yield n
            st.extend(reversed(n.kids))
