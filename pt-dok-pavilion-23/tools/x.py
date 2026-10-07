import sys, os, libarchive
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
with libarchive.file_reader(src) as a:
    for e in a:
        p = e.pathname
        if p.startswith('/') or '..' in p.split('/'):
            print('skip', p); continue
        out = os.path.join(dst, p)
        if e.isdir:
            os.makedirs(out, exist_ok=True); continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'wb') as f:
            for b in e.get_blocks(): f.write(b)
        print(e.size, p)
