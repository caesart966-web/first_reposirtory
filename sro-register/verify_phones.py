# -*- coding: utf-8 -*-
"""Контроль: цифры нормализованных номеров идут в том же порядке, что в источнике,
допускается только пропуск кода страны (7/8/07/08) и повтор кода города."""
import json, re
rows = json.load(open('rows.json'))

def check(raw, out):
    src = re.sub(r'\D', '', raw)
    pos = 0
    for num in out.split(', '):
        num = re.sub(r'\s*доб\..*$', '', num)
        m = re.match(r'\+7 \((\d{3,5})\) (.+)$', num)
        area, local = m.group(1), re.sub(r'\D', '', m.group(2))
        for skip in (0, 1, 2):                     # код страны в источнике
            p = pos + skip
            if src.startswith(area + local, p):    # код города указан у этого номера
                pos = p + len(area) + len(local); break
            if src.startswith(local, p):           # код города унаследован
                pos = p + len(local); break
        else:
            return 'номер %s не найден в исходной строке с позиции %d' % (num, pos)
    tail = src[pos:]
    if tail and tail not in ('7', '8'):
        return 'неразобранный остаток цифр: %r' % tail
    return None

bad = 0
for x in rows:
    out = x['phone_n']
    if not out or not out.startswith('+7 ('):      # пусто или оставлено как в источнике
        continue
    err = check(x['phone'], out)
    if err:
        bad += 1
        print('№%-5d %-55r -> %-55r  %s' % (x['n'], x['phone'], out, err))
print('проверено:', sum(1 for x in rows if x['phone_n'].startswith('+7 (')), '| расхождений:', bad)
