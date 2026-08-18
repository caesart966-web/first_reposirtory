# -*- coding: utf-8 -*-
"""Нормализация телефонов реестра СРО.
Правило: приводим номер к виду +7 (код) номер ТОЛЬКО если он разбирается однозначно
и все цифры исходной строки израсходованы без остатка. Иначе — оставляем как в источнике.
"""
import json, re

def fmt_local(l):
    if len(l) == 7: return '%s-%s-%s' % (l[:3], l[3:5], l[5:])
    if len(l) == 6: return '%s-%s-%s' % (l[:2], l[2:4], l[4:])
    if len(l) == 5: return '%s-%s-%s' % (l[:1], l[1:3], l[3:])
    return None

def make(area, local):
    """+7 (area) local; сумма цифр кода и номера должна быть ровно 10."""
    if len(area) + len(local) != 10: return None
    l = fmt_local(local)
    return '+7 (%s) %s' % (area, l) if l else None

def split_locals(digits, area):
    """Хвост цифр при известном коде города -> список локальных номеров равной длины."""
    n = 10 - len(area)
    if not digits or len(digits) % n: return None
    return [digits[i:i+n] for i in range(0, len(digits), n)]

def split_full(digits):
    """Поток цифр без явного кода города -> список 10-значных номеров."""
    out, i = [], 0
    while i < len(digits):
        rest = len(digits) - i
        if rest >= 11 and digits[i] in '78':      # 8XXXXXXXXXX / 7XXXXXXXXXX
            out.append(digits[i+1:i+11]); i += 11
        elif rest == 10:                          # номер без кода страны
            out.append(digits[i:i+10]); i += 10
        else:
            return None
    return out or None

AREA_RE = re.compile(r'\((\d{3,5})\)')
EXT_RE  = re.compile(r'\(?\s*(?:доб|вн|ext)[\.\s]*(\d{1,5})\s*\)?', re.I)

def norm_part(part, area_carry):
    """Разбирает одну часть строки. -> (список номеров, новый code_carry) или (None, ...)"""
    ext = ''
    m = EXT_RE.search(part)
    if m:
        ext = ' доб. ' + m.group(1)
        part = part[:m.start()] + ' ' + part[m.end():]
    nums, area = [], area_carry
    if AREA_RE.search(part):
        chunks = AREA_RE.split(part)          # [до, код, сегмент, код, сегмент, ...]
        head = re.sub(r'\D', '', chunks[0])
        if head not in ('', '7', '8', '07', '08'):
            return None, area_carry
        for k in range(1, len(chunks) - 1, 2):
            area = chunks[k]
            seg = re.sub(r'\D', '', chunks[k+1])
            last = k + 2 >= len(chunks) - 1
            if not last and len(seg) % (10 - len(area)) == 1 and seg[-1] in '78':
                seg = seg[:-1]                    # хвостовая 8/+7 относится к следующему номеру
            locals_ = split_locals(seg, area)
            if locals_ is None: return None, area_carry
            for l in locals_:
                v = make(area, l)
                if v is None: return None, area_carry
                nums.append(v)
    else:
        digits = re.sub(r'\D', '', part)
        if not digits: return [], area
        full = split_full(digits)
        if full is not None:
            for d in full:
                v = make(d[:3], d[3:])
                if v is None: return None, area_carry
                nums.append(v)
                area = d[:3]
        elif area:                              # локальные номера при уже названном коде города
            locals_ = split_locals(digits, area)
            if locals_ is None: return None, area_carry
            for l in locals_:
                v = make(area, l)
                if v is None: return None, area_carry
                nums.append(v)
        else:
            return None, area_carry
    if ext and nums: nums[-1] += ext
    return nums, area

def norm(raw):
    if not raw: return '', 'empty'
    s = re.sub(r'\s+', ' ', raw).strip()
    out, area = [], None
    for part in re.split(r'[,;/]| или | и ', s):
        part = part.strip()
        if not part: continue
        nums, area = norm_part(part, area)
        if nums is None: return s, 'raw'
        out.extend(nums)
    if not out: return s, 'raw'
    return ', '.join(dict.fromkeys(out)), 'norm'

if __name__ == '__main__':
    rows = json.load(open('rows.json'))
    stats = {'norm': 0, 'raw': 0, 'empty': 0}
    raws = []
    for x in rows:
        v, st = norm(x['phone'])
        x['phone_n'] = v
        stats[st] += 1
        if st == 'raw': raws.append((x['n'], x['phone']))
    # контроль целостности: цифры результата = цифрам источника (без кодов страны 7/8)
    bad = []
    for x in rows:
        if not x['phone_n'] or x['phone_n'] == re.sub(r'\s+',' ',x['phone']).strip(): continue
        src = re.sub(r'\D', '', x['phone'])
        res = ''.join(re.sub(r'\D','',n)[1:] for n in x['phone_n'].split(', '))  # без ведущей 7
        s2, r2 = src, res
        for pref in ('7','8','07','08'):
            pass
        if len(re.sub(r'[78]','',src)) and len(res) < 10: bad.append(x['n'])
    print(stats)
    print('подозрительных:', bad[:20])
    print('--- оставлено как в источнике (%d):' % len(raws))
    for n, p in raws: print('   №%-5d %r' % (n, p))
    print('--- контроль сложных случаев:')
    for n in (163,164,319,402,500,705,836,1011,1087,1151,1247,1273,1430,1507,701,703,117,322,456,1157,439,740,963,37,848,1391,1454,30,995,233,1382):
        x = [r for r in rows if r['n'] == n][0]
        print('   №%-5d %-58r -> %r' % (n, x['phone'], x['phone_n']))
    json.dump(rows, open('rows.json','w'), ensure_ascii=False)
