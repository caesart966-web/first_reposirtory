import struct, zlib, hashlib, sys
def make(name, data):
    """IFCZIP как у плагина «Строим просто» (.NET ZipArchive): deflate zlib 9/8/-15, флаг 2, дата 1980-01-00."""
    c = zlib.compressobj(9, zlib.DEFLATED, -15, 8); comp = c.compress(data) + c.flush()
    crc = zlib.crc32(data) & 0xffffffff
    fn = name.encode('utf-8')          # .NET пишет имя в UTF-8, но флаг UTF-8 (0x800) не ставит
    flags = 2
    lh = struct.pack('<4sHHHHHIIIHH', b'PK\x03\x04', 20, flags, 8, 0, 0x20, crc, len(comp), len(data), len(fn), 0) + fn
    cd = struct.pack('<4sHHHHHHIIIHHHHHII', b'PK\x01\x02', 20, 20, flags, 8, 0, 0x20, crc, len(comp), len(data), len(fn), 0, 0, 0, 0, 0, 0) + fn
    end = struct.pack('<4sHHHHIIH', b'PK\x05\x06', 0, 0, 1, 1, len(cd), len(lh) + len(comp), 0)
    return lh + comp + cd + end
if __name__ == '__main__':
    print(hashlib.md5(make(sys.argv[2], open(sys.argv[1], 'rb').read())).hexdigest())
