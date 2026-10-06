"""Собирает ../checko_paket.zip — всё, что нужно для запуска проверки через Checko на своём компьютере.
Имена внутри архива латиницей: встроенный распаковщик старых Windows портит кириллицу в именах."""
import glob, os, zipfile
os.chdir(os.path.dirname(os.path.abspath(__file__)))
files = ['README.txt', 'start_windows.bat', 'run.sh', 'checko_status.py', 'build.py', 'all.json']
files += sorted(f for f in glob.glob('out/*.json') if os.path.basename(f) != 'checko.json')
dst = os.path.join('..', 'checko_paket.zip')
with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in files:
        info = zipfile.ZipInfo.from_file(f, f'checko_paket/{f}')
        info.compress_type = zipfile.ZIP_DEFLATED
        if f.endswith('.sh'):
            info.external_attr = 0o100755 << 16
        with open(f, 'rb') as fh:
            z.writestr(info, fh.read())
print(dst, os.path.getsize(dst), 'байт,', len(files), 'файлов')
