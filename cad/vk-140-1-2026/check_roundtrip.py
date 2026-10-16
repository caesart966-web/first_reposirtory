"""Сверка DWG с исходными DXF: DWG, записанный ODA File Converter, читается обратно в DXF тем же
конвертером, и состав чертежа сравнивается с исходником — типы и число объектов, слои, надписи, шрифты.

python check_roundtrip.py ПАПКА_DXF ПАПКА_ОБРАТНОЙ_КОНВЕРТАЦИИ
Код возврата 1, если в каком-то листе пропали объекты или надписи."""
import collections
import pathlib
import sys

from ezdxf import recover

SRC, RT = map(pathlib.Path, sys.argv[1:3])
bad = 0


def load(path):
    doc, auditor = recover.readfile(path)
    msp = doc.modelspace()
    types = collections.Counter(e.dxftype() for e in msp)
    texts = collections.Counter()
    for e in msp.query('TEXT MTEXT'):
        t = e.dxf.text if e.dxftype() == 'TEXT' else e.text
        texts[t.strip()] += 1
    layers = {layer.dxf.name for layer in doc.layers}
    fonts = {st.dxf.name: (st.dxf.get('font', '') or '').lower() for st in doc.styles}
    return doc, auditor, types, texts, layers, fonts


for src in sorted(SRC.glob('*.dxf')):
    rt = RT / src.name
    print(f'=== {src.name}')
    if not rt.exists():
        print('  НЕТ обратной конвертации — DWG не прочитан')
        bad += 1
        continue
    d1, a1, t1, x1, l1, f1 = load(src)
    d2, a2, t2, x2, l2, f2 = load(rt)
    print(f'  версия DWG/DXF после ODA: {d2.dxfversion}; ошибок чтения: {len(a2.errors)}, исправлений: {len(a2.fixes)}')
    print(f'  объектов: исходник {sum(t1.values())}, после DWG {sum(t2.values())}')
    for k in sorted(set(t1) | set(t2)):
        if t1[k] != t2[k]:
            print(f'    {k}: {t1[k]} -> {t2[k]}')
    lost_text = [t for t in x1 if x2[t] < x1[t]]
    print(f'  надписей: {sum(x1.values())} -> {sum(x2.values())}; пропало: {len(lost_text)}')
    for t in lost_text[:10]:
        print(f'    - {t[:80]}')
    if l1 - l2:
        print(f'  пропали слои: {sorted(l1 - l2)}')
    changed = {k: (f1[k], f2.get(k)) for k in f1 if f2.get(k) not in (f1[k], None)}
    if changed:
        print(f'  шрифты изменились: {changed}')
    fonts_used = sorted({v for v in f2.values() if v})
    print(f'  шрифты стилей: {fonts_used}')
    lost = sum(max(0, t1[k] - t2[k]) for k in t1 if k not in ('POINT',))
    if lost_text or lost > 0.01 * sum(t1.values()):
        bad += 1
        print('  ВНИМАНИЕ: состав листа изменился')
    else:
        print('  OK')
sys.exit(1 if bad else 0)
