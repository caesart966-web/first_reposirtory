"""Разбор выгрузки Checko в структуру.

Имена в выгрузке обрезаны по ширине колонки (~37 символов), поэтому
как название берётся не то, что в строке, а официальное из реестра
НОСТРОЙ по ИНН. Из строки нужны только ИНН и телефоны.
"""
import json
import re

# Якорь — последнее вхождение «ИНН <цифры>»: имя может само содержать
# что угодно, а вот после ИНН идут только телефоны.
ANCHOR = re.compile(r'ИНН\s+(\d{10,12})\s+')
HEAD = re.compile(r'^\[\s*(\d+)/(\d+)\]\s*(✓?)\s*(.*)$')


def parse(path):
    rows, bad = [], []
    for ln in open(path, encoding='utf-8'):
        ln = ln.rstrip('\n')
        if not ln.strip():
            continue
        h = HEAD.match(ln)
        if not h:
            bad.append(ln)
            continue
        n, total, tick, rest = h.groups()
        ms = list(ANCHOR.finditer(rest))
        if not ms:
            bad.append(ln)
            continue
        m = ms[-1]
        rows.append({
            'n': int(n),
            'total': int(total),
            'inn': m.group(1),
            'name_raw': rest[:m.start()].strip(),
            'tail': rest[m.end():].strip(),
        })
    return rows, bad


def phones(tail):
    if tail in ('—', '-', ''):
        return []
    return [p.strip() for p in tail.split(';') if p.strip()]


if __name__ == '__main__':
    rows, bad = parse('checko_raw.txt')
    print('распознано:', len(rows), '| не распознано:', len(bad))
    for b in bad:
        print('  BAD:', repr(b))
    idx = [r['n'] for r in rows]
    print('индексы:', min(idx), '..', max(idx),
          '| пропуски:', sorted(set(range(min(idx), max(idx) + 1)) - set(idx)))
    print('дубли индексов:', len(idx) - len(set(idx)))
    inns = [r['inn'] for r in rows]
    print('дубли ИНН:', len(inns) - len(set(inns)))
    ph = [r for r in rows if phones(r['tail'])]
    print('с телефоном:', len(ph), '| всего номеров:',
          sum(len(phones(r['tail'])) for r in rows))
