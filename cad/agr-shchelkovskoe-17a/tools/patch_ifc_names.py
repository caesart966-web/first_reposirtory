"""Заглушки шаблона Revit в трёх моделях -> наименование объекта; число этажей в АР.

    python3 patch_ifc_names.py <папка с AR.ifc, PS.ifc, BiO.ifc>

Правка построчная, по байтам: остальной файл остаётся без изменений (CRLF, порядок строк).
"""
import os
import re
import sys


def enc(s):
    """Строка в кодировке IFC: кириллица блоками \\X2\\...\\X0\\."""
    out, buf = [], []
    for ch in s:
        if ord(ch) < 128:
            if buf:
                out.append('\\X2\\' + ''.join(buf) + '\\X0\\'); buf = []
            out.append(ch)
        else:
            buf.append('%04X' % ord(ch))
    if buf:
        out.append('\\X2\\' + ''.join(buf) + '\\X0\\')
    return ''.join(out)


NAME = enc('Магазин')
OLD = {enc('Жилой дом'), enc('Наименование проекта'), enc('Наименование здания')}
ADDRESS = 'г. Москва, внутригородское муниципальное образование Гольяново, Щёлковское шоссе, земельный участок, 17А/1'
# точные замены строк: опечатка в названии помещения и заглушки сведений о проекте
EXACT = {
    "'" + enc('Памещение главной кассы') + "'": "'" + enc('Помещение главной кассы') + "'",
    "IFCORGANIZATION($,'" + enc('Название организации') + "','" + enc('Сведения об организации') + "',$,$)":
        "IFCORGANIZATION($,'" + enc('ООО «СК СТРАТЕГИЯ»') + "','" + enc('Проектная организация') + "',$,$)",
    "('" + enc('Адрес проекта') + "')": "('" + enc(ADDRESS) + "')",
}


def patch(path, storeys=None):
    b = open(path, 'rb').read()
    lines = b.split(b'\r\n')
    n = {'project': 0, 'building': 0, 'pname': 0, 'storeys': 0, 'exact': 0}
    for i, raw in enumerate(lines):
        s = raw.decode('ascii')
        for old, new in EXACT.items():
            if old in s:
                s = s.replace(old, new); n['exact'] += 1
        m = re.match(r"^(#\d+=IFCPROJECT\('[^']+',#\d+,'[^']*',\$,\$,)'([^']*)'(,.*)$", s)
        if m and m.group(2) in OLD:
            s = m.group(1) + "'" + NAME + "'" + m.group(3); n['project'] += 1
        m = re.match(r"^(#\d+=IFCBUILDING\('[^']+',#\d+,)'([^']*)'(,\$,\$,#\d+,\$,)'([^']*)'(,.*)$", s)
        if m and m.group(2) in OLD and m.group(4) in OLD:
            s = m.group(1) + "'" + NAME + "'" + m.group(3) + "'" + NAME + "'" + m.group(5); n['building'] += 1
        m = re.match(r"^(#\d+=IFCPROPERTYSINGLEVALUE\('RUS_ProjectName',\$,IFCTEXT\()'([^']*)'(\),\$\);)$", s)
        if m and m.group(2) in OLD:
            s = m.group(1) + "'" + NAME + "'" + m.group(3); n['pname'] += 1
        if storeys is not None:
            m = re.match(r"^(#\d+=IFCPROPERTYSINGLEVALUE\('NumberOfStoreys',\$,IFCINTEGER\()(\d+)(\),\$\);)$", s)
            if m and int(m.group(2)) != storeys:
                s = m.group(1) + str(storeys) + m.group(3); n['storeys'] += 1
        lines[i] = s.encode('ascii')
    open(path, 'wb').write(b'\r\n'.join(lines))
    return n


if __name__ == '__main__':
    d = sys.argv[1]
    print('AR ', patch(os.path.join(d, 'AR.ifc'), storeys=1))
    print('PS ', patch(os.path.join(d, 'PS.ifc')))
    print('BiO', patch(os.path.join(d, 'BiO.ifc')))
