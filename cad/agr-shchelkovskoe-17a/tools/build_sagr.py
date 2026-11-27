"""Сборка комплекта САГР из исходного комплекта с заменой моделей и ТЭП.

    python3 build_sagr.py <распакованный исходный комплект> <папка с AR/PS/BiO.ifc> <куда> <площадь> <ГПЗУ> [<trm.zip>]

Структура комплекта, идентификаторы документов и имена файлов сохраняются.
"""
import datetime
import os
import re
import shutil
import sys
import zipfile

MSK = datetime.timezone(datetime.timedelta(hours=3))
IFC = {'c0228dc0-12d9-4a61-9be6-21c5ae78933d': 'AR.ifc',
       'a7213da6-fc22-42c0-8f55-4e1111962c11': 'PS.ifc',
       'b34c5aed-3fc7-45b2-8451-d936b220e013': 'BiO.ifc'}
TEP = '3354b151-021c-449d-9ce5-693855f1dfdf'
TRM = '48b2721b-15fe-495f-96ed-04e353845312'
HEIGHT = '6.3'   # НН_К01_С01_АР_АГР_TRM/trm.zip
ORDER = ['c684722c-d2d3-4291-a5d0-9e32aab4b61b', 'a7213da6-fc22-42c0-8f55-4e1111962c11',
         'b34c5aed-3fc7-45b2-8451-d936b220e013', 'c0228dc0-12d9-4a61-9be6-21c5ae78933d',
         '48b2721b-15fe-495f-96ed-04e353845312', TEP, 'info.xml']


def sub1(text, pattern, repl):
    new, n = re.subn(pattern, repl, text)
    assert n == 1, (pattern, n)
    return new


def tep(text, area, gpzu):
    text = sub1(text, r'<ObjectName>[^<]*</ObjectName>', '<ObjectName>Магазин</ObjectName>')
    text = sub1(text, r'<GPZUNumber>[^<]*</GPZUNumber>', '<GPZUNumber>ГПЗУ № %s</GPZUNumber>' % gpzu)
    for tag in ('TotalObjectArea', 'AboveGroundArea', 'NonResidentialAboveGroundAreaNonResidentialObjects'):
        text = sub1(text, r'<%s>[^<]*</%s>' % (tag, tag), '<%s>%s</%s>' % (tag, area, tag))
    text = sub1(text, r'<ApartmentsCount>[^<]*</ApartmentsCount>', '<ApartmentsCount>0</ApartmentsCount>')
    # высота от отметки земли у здания 154,350 до верха ограждения кровли 160,650 (проверка 27.11.2026)
    for tag in ('BuildingHeight', 'ObjectHeight'):
        text = sub1(text, r'<%s>[^<]*</%s>' % (tag, tag), '<%s>%s</%s>' % (tag, HEIGHT, tag))
    return text


def main(src, ifc_dir, out, area, gpzu, trm=None):
    """trm — новый trm.zip из той же выгрузки плагина, что и AR.ifc (иначе остаётся прежний)."""
    now = datetime.datetime.now(MSK).replace(microsecond=0)
    stamp = now.isoformat()
    kit = os.path.join(out, 'kit')
    shutil.rmtree(kit, ignore_errors=True)
    os.makedirs(kit)
    changed = []
    for name in ORDER:
        a, b = os.path.join(src, name), os.path.join(kit, name)
        if name in IFC:
            shutil.copyfile(os.path.join(ifc_dir, IFC[name]), b)
        elif name == TRM and trm:
            shutil.copyfile(trm, b)
        elif name == TEP:
            raw = open(a, 'rb').read()
            crlf = b'\r\n' in raw
            new = tep(raw.decode('utf-8'), area, gpzu)
            open(b, 'wb').write(new.encode('utf-8'))
            assert (b'\r\n' in open(b, 'rb').read()) == crlf
        else:
            shutil.copyfile(a, b)
            continue
        if open(a, 'rb').read() != open(b, 'rb').read():
            changed.append(name)
    info = open(os.path.join(kit, 'info.xml'), 'rb').read().decode('utf-8')
    info = sub1(info, r'(<Package Created=")[^"]*(")', r'\g<1>%s\g<2>' % stamp)
    for name in changed:
        info = sub1(info, r'(<Document TypeName="Document" Id="%s" ParentId="[^"]*" Created=")[^"]*(" Modified=")[^"]*(")'
                    % name, r'\g<1>%s\g<2>%s\g<3>' % (stamp, stamp))
    open(os.path.join(kit, 'info.xml'), 'wb').write(info.encode('utf-8'))

    zname = now.strftime('%Y_%m_%dT%H_%M_%S') + '+03_00_TRM_Проект_Комплект_САГР.zip'
    zpath = os.path.join(out, zname)
    for old in os.listdir(out):
        if old.endswith('_TRM_Проект_Комплект_САГР.zip'):
            os.remove(os.path.join(out, old))
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in ORDER:
            zi = zipfile.ZipInfo(name, date_time=now.astimezone(datetime.timezone.utc).timetuple()[:6])
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.create_system = 0
            z.writestr(zi, open(os.path.join(kit, name), 'rb').read())

    # те же файлы россыпью, под своими именами
    loose = os.path.join(out, 'Комплект САГР')
    shutil.rmtree(loose, ignore_errors=True)
    for m in re.finditer(r'<Document TypeName="Document" Id="([^"]+)"[^>]*FileName="([^"]+)"', info):
        dst = os.path.join(out, m.group(2))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(kit, m.group(1)), dst)
    shutil.rmtree(kit)
    print(zname)
    print('заменены:', ', '.join(changed))


if __name__ == '__main__':
    main(*sys.argv[1:7])
