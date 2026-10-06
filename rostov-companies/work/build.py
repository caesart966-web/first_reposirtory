"""Сборка итоговой таблицы.

Источники:
  all.json           — обе выгрузки реестра СРО (parse.py);
  out/batch_*.json,
  out/r*.json        — веб-поиск по ИНН (по каждому ИНН берётся лучший результат);
  out/checko.json    — ЕГРЮЛ/ЕГРИП через API Checko (checko_status.py).

Статус из Checko важнее статуса из поиска: это выписка из реестра, а не
пересказ выдачи. Почты из обоих источников объединяются.

python build.py "Строители_РО_статус_и_почты.xlsx"
"""
import collections
import glob
import json
import os
import re
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(errors='replace')
    except Exception:  # noqa: BLE001
        pass

OUT = sys.argv[1] if len(sys.argv) > 1 else 'result.xlsx'


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def score(r):
    return 2 * (r.get('status', 'Не установлено') != 'Не установлено') + bool(r.get('email'))


src = load('all.json')
res = {}
for f in sorted(glob.glob('out/batch_*.json')) + sorted(glob.glob('out/r*.json')):
    for r in load(f):
        if (r.get('searches') or 0) > 0 and (r['inn'] not in res or score(r) >= score(res[r['inn']])):
            res[r['inn']] = r
chk = {r['inn']: r for r in load('out/checko.json')} if os.path.exists('out/checko.json') else {}

GROUP = {
    'Действует': 'Действует',
    'В процессе ликвидации': 'Закрывается',
    'Банкротство': 'Закрывается',
    'Предстоящее исключение': 'Закрывается',
    'Ликвидирована': 'Не существует',
    'Исключена ФНС': 'Не существует',
    'Реорганизована': 'Не существует',
    'ИП прекратил деятельность': 'Не существует',
    'Не установлено': 'Не найдено',
    'Ещё не проверялась': 'Не проверялась',
}
ORDER = ['Действует', 'Закрывается', 'Не существует', 'Не найдено', 'Не проверялась']
FILL = {'Действует': 'E2F0D9', 'Закрывается': 'FFF2CC', 'Не существует': 'F8D7DA',
        'Не найдено': 'EDEDED', 'Не проверялась': 'FFFFFF'}

# дубли по ИНН (одна компания есть в обоих файлах) сливаются в одну строку
rows = {}
for x in src:
    inn = x['ИНН']
    file_ = '1' if x['_src'].startswith('файл 1') else '2'
    if 'Статус права' in x:
        m = {'Действует': 'член СРО', 'Прекращено': 'прекращено',
             'Приостановлено': 'приостановлено', '': 'нет данных'}.get(x['Статус права'], x['Статус права'])
    else:
        d = x.get('Дата прекращения членства', '')
        m = f'прекращено {d}' if d else 'член СРО'
    where = f'файл {file_}, № {x["N п/п"]}'
    extra = dict(  # остальные столбцы исходных файлов — переносятся как есть
        full=x.get('Полное наименование', ''), sro_reg=x.get('Регистрационный номер в реестре СРО', ''),
        sro_date=x.get('Дата регистрации в реестре СРО', ''), gos_date=x.get('Дата государственной регистрации', ''),
        kf=x.get('КФ', ''), decision=x.get('Решение', ''), file_email=x.get('электронная почта', ''),
    )
    if inn in rows:  # компания есть в обоих файлах — различающиеся значения через «; »
        rows[inn]['where'] += '; ' + where
        rows[inn]['sro'] += '; ' + m
        for k, v in extra.items():
            if v and v not in rows[inn][k].split('; '):
                rows[inn][k] = f'{rows[inn][k]}; {v}' if rows[inn][k] else v
        continue
    rows[inn] = dict(
        inn=inn, ogrn=x['ОГРН/ОГРНИП'],
        name=x['Сокращенное наименование'] or x['Полное наименование'],
        phone=x.get('Контактные телефоны', ''),
        addr=x.get('юр адрес') or x.get('Адрес места нахождения юридического лица', ''),
        head=x.get('ФИО') or x.get('Фамилия, имя, отчество (при наличии) для ИП', ''),
        sro=m, where=where, **extra,
    )


def emails_of(*records):
    out = []
    for r in records:
        for e in re.split(r'[;,\s]+', (r or {}).get('email', '') or ''):
            e = e.strip().lower()
            if '@' in e and e not in out:
                out.append(e)
    return '; '.join(out)


RECHECK = re.compile(r'перепровер|не подтвержд|противореч|косвенн|реорганиз|не указал|не указана страниц'
                     r'|источник[^.;]{0,30}не указ|актуальност\w* не указ|устаревш|вероятн|ВНИМАНИЕ', re.I)
recs = []
for inn, r in rows.items():
    s, c = res.get(inn), chk.get(inn)
    if c and c['status'] != 'Не установлено':
        main, via = c, 'Checko'           # выписка из реестра
    elif s:
        main, via = s, 'поиск'
    elif c:
        main, via = c, 'Checko'           # Checko ответил, но статуса нет (не найден)
    else:
        main, via = {}, ''
    st = main.get('status') or 'Ещё не проверялась'
    if st not in GROUP:
        print('!! неизвестный статус', inn, st)
        st = 'Не установлено'
    det = main.get('status_detail', '') or ''
    if via == 'поиск' and c:
        det += f' | {c["status_detail"]}'
    recheck = ''
    if st not in ('Ещё не проверялась', 'Не установлено'):
        if RECHECK.search(det) or (via == 'поиск' and not main.get('source')):
            recheck = 'да'
    sources = [x.get('source', '') for x in (c, s) if x and x.get('source')]
    recs.append(dict(r, group=GROUP[st], status=st, date=main.get('status_date', ''), recheck=recheck,
                     email=emails_of(c, s, {'email': r['file_email']}),
                     phones=(c or {}).get('phones', ''), site=(c or {}).get('site', ''),
                     cur=main.get('current_name', '') or (s or {}).get('current_name', ''),
                     detail=det, source=' '.join(sources), via=via))
recs.sort(key=lambda r: (ORDER.index(r['group']), r['email'] == '', r['name'].lower()))

COLS = [  # заголовок, ширина, поле
    ('№', 6, None), ('Итог', 15, 'group'), ('Статус в ЕГРЮЛ / ЕГРИП', 24, 'status'),
    ('Дата события', 13, 'date'), ('Электронная почта', 32, 'email'),
    ('Телефоны (Checko)', 22, 'phones'), ('Сайт (Checko)', 20, 'site'),
    ('Наименование (из файла)', 38, 'name'), ('Текущее наименование', 26, 'cur'),
    ('ИНН', 13, 'inn'), ('ОГРН / ОГРНИП', 16, 'ogrn'), ('Телефон (из файла)', 20, 'phone'),
    ('Адрес (из файла)', 50, 'addr'), ('Руководитель (из файла)', 38, 'head'),
    ('Членство в СРО (по файлу)', 20, 'sro'), ('Рег. номер в реестре СРО', 12, 'sro_reg'),
    ('Дата вступления в СРО', 13, 'sro_date'), ('Решение СРО (по файлу)', 40, 'decision'),
    ('Взнос в КФ (по файлу)', 12, 'kf'), ('Дата гос. регистрации', 13, 'gos_date'),
    ('Полное наименование (из файла)', 50, 'full'), ('Где в исходных файлах', 20, 'where'),
    ('Откуда статус', 12, 'via'), ('Что сказано в источнике', 60, 'detail'), ('Источник', 45, 'source'),
    ('Перепроверить', 14, 'recheck'), ('Проверить самому', 16, None),
]
COL = {h: i for i, (h, _, _) in enumerate(COLS, 1)}
F = Font(name='Arial', size=10)
FB = Font(name='Arial', size=10, bold=True)
FL = Font(name='Arial', size=10, color='0563C1', underline='single')
FH = Font(name='Arial', size=10, bold=True, color='FFFFFF')
HFILL = PatternFill('solid', fgColor='404040')
thin = Side(style='thin', color='BFBFBF')
BRD = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical='top')


def sheet(ws, items):
    ws.append([h for h, _, _ in COLS])
    for c in ws[1]:
        c.font = FH
        c.fill = HFILL
        c.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
        c.border = BRD
    for i, r in enumerate(items, 1):
        ws.append([i] + [r[k] if k else '' for _, _, k in COLS[1:-1]] + ['Rusprofile'])
        row = ws.max_row
        fill = PatternFill('solid', fgColor=FILL[r['group']])
        for c in ws[row]:
            c.font = F
            c.alignment = WRAP
            c.border = BRD
        for h in ('Итог', 'Статус в ЕГРЮЛ / ЕГРИП', 'Дата события'):
            ws.cell(row, COL[h]).fill = fill
        ws.cell(row, COL['Итог']).font = FB
        link = ws.cell(row, COL['Проверить самому'])
        link.hyperlink = f'https://www.rusprofile.ru/search?query={r["inn"]}'
        link.font = FL
        if r['recheck']:
            ws.cell(row, COL['Перепроверить']).font = Font(name='Arial', size=10, bold=True, color='C00000')
        for h in ('ИНН', 'ОГРН / ОГРНИП'):
            ws.cell(row, COL[h]).number_format = '@'
    for i, (_, w, _) in enumerate(COLS, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = ws.cell(2, COL['Наименование (из файла)'])
    ws.auto_filter.ref = f'A1:{get_column_letter(len(COLS))}{max(ws.max_row, 2)}'
    ws.row_dimensions[1].height = 32


wb = Workbook()
sv = wb.active
sv.title = 'Сводка'
wa = wb.create_sheet('Все компании')
sheet(wa, recs)
names = {'Действует': 'Действуют', 'Закрывается': 'Закрываются', 'Не существует': 'Не существуют',
         'Не найдено': 'Не найдены', 'Не проверялась': 'Ещё не проверены'}
for g in ORDER:
    sheet(wb.create_sheet(names[g]), [r for r in recs if r['group'] == g])

# --- Сводка: формулы по листу «Все компании» (Итог — B, Статус — C, Почта — E)
assert (COL['Итог'], COL['Статус в ЕГРЮЛ / ЕГРИП'], COL['Электронная почта']) == (2, 3, 5)
N = wa.max_row
A = f"'Все компании'!$B$2:$B${N}"
S = f"'Все компании'!$C$2:$C${N}"
E = f"'Все компании'!$E$2:$E${N}"
by_via = collections.Counter(r['via'] for r in recs if r['group'] != 'Не проверялась')
sv['A1'] = 'Строительные компании Ростовской области: статус и электронная почта'
sv['A1'].font = Font(name='Arial', size=14, bold=True)
sv['A2'] = ('Исходные файлы: register-1-500.xlsx и register-501-988.xlsx (реестр Союза «Строители Ростовской '
            f'области»), {len(recs)} компаний. Статус взят из ЕГРЮЛ/ЕГРИП через API Checko — '
            f'{by_via.get("Checko", 0)} компаний; по выдаче веб-поиска по ИНН (Rusprofile, Checko, List-org, '
            f'ЗаЧестныйБизнес, РБК Компании, Audit-it и др.) — {by_via.get("поиск", 0)}. Проверка — октябрь 2026.')
sv['A2'].font = F
sv['A2'].alignment = WRAP
sv.merge_cells('A2:E2')
sv.row_dimensions[2].height = 66

for i, h in enumerate(['Итог', 'Что это значит', 'Компаний', 'Из них с почтой', 'Доля от всех'], 1):
    c = sv.cell(4, i, h)
    c.font, c.fill, c.border, c.alignment = FH, HFILL, BRD, WRAP
MEAN = {
    'Действует': 'Компания работает, в реестре налоговой значится действующей',
    'Закрывается': 'Ещё в реестре, но идёт ликвидация, банкротство или налоговая готовит исключение',
    'Не существует': 'Ликвидирована, исключена налоговой как недействующая, присоединена к другой или ИП закрыт',
    'Не найдено': 'Сведений о статусе по этому ИНН не нашлось — проверить вручную по ссылке в последнем столбце',
    'Не проверялась': 'До компании ещё не дошла очередь (ни поиск, ни Checko)',
}
r0 = 5
rt = r0 + len(ORDER)
for k, g in enumerate(ORDER):
    r = r0 + k
    sv.cell(r, 1, g).font = FB
    sv.cell(r, 1).fill = PatternFill('solid', fgColor=FILL[g])
    sv.cell(r, 2, MEAN[g]).font = F
    sv.cell(r, 3, f'=COUNTIF({A},A{r})')
    sv.cell(r, 4, f'=COUNTIFS({A},A{r},{E},"?*")')
    sv.cell(r, 5, f'=IF($C${rt}=0,0,C{r}/$C${rt})')
    sv.cell(r, 5).number_format = '0.0%'
    for col in range(1, 6):
        sv.cell(r, col).border = BRD
        sv.cell(r, col).alignment = WRAP
        if col > 2:
            sv.cell(r, col).font = F
sv.cell(rt, 1, 'Всего').font = FB
sv.cell(rt, 3, f'=SUM(C{r0}:C{rt - 1})').font = FB
sv.cell(rt, 4, f'=SUM(D{r0}:D{rt - 1})').font = FB
sv.cell(rt, 5, f'=IF(C{rt}=0,0,C{rt}/C{rt})').font = FB
sv.cell(rt, 5).number_format = '0.0%'
for col in range(1, 6):
    sv.cell(rt, col).border = BRD

rd = rt + 2
sv.cell(rd, 1, 'Подробно по статусам').font = Font(name='Arial', size=11, bold=True)
for i, h in enumerate(['Статус в ЕГРЮЛ / ЕГРИП', 'Итог', 'Компаний', 'Из них с почтой'], 1):
    c = sv.cell(rd + 1, i, h)
    c.font, c.fill, c.border = FH, HFILL, BRD
for k, st in enumerate(GROUP):
    r = rd + 2 + k
    sv.cell(r, 1, st)
    sv.cell(r, 2, GROUP[st]).fill = PatternFill('solid', fgColor=FILL[GROUP[st]])
    sv.cell(r, 3, f'=COUNTIF({S},A{r})')
    sv.cell(r, 4, f'=COUNTIFS({S},A{r},{E},"?*")')
    for col in range(1, 5):
        sv.cell(r, col).border = BRD
        sv.cell(r, col).font = F

rn = rd + 2 + len(GROUP) + 1
notes = [
    'Как читать:',
    '• «Итог» — главное: действует компания или её уже нет. «Членство в СРО» — отдельная вещь: компания могла выйти из СРО и продолжать работать.',
    '• «Откуда статус»: Checko — выписка из ЕГРЮЛ/ЕГРИП через API Checko (надёжнее); поиск — пересказ выдачи поисковика по ИНН.',
    '• Почта — из блока контактов Checko и со страниц справочников (ЕГРЮЛ, госзакупки, реестр СРО), только с совпадением ИНН. У многих компаний почта нигде не опубликована.',
    '• В листах компании отсортированы: сначала с почтой, затем по названию. Фильтр стоит на каждом листе.',
    '• «Не найдено» не значит «не существует»: сведений нет в источниках. Ссылка «Rusprofile» в последнем столбце открывает карточку по ИНН.',
    '• «Перепроверить = да» — статус взят из одного источника без даты, косвенно (по выручке) или компания в процессе реорганизации.',
    '• «Дата события» — дата ликвидации, исключения, начала банкротства или ликвидации, если источник её назвал.',
    '• Перед рассылкой проверьте почту выборочно: справочники обновляются с задержкой, адрес мог смениться.',
]
for k, t in enumerate(notes):
    c = sv.cell(rn + k, 1, t)
    c.font = FB if k == 0 else F
    sv.merge_cells(start_row=rn + k, start_column=1, end_row=rn + k, end_column=5)
    c.alignment = WRAP
    sv.row_dimensions[rn + k].height = 30 if k else 16
for col, w in zip('ABCDE', [26, 70, 12, 16, 13]):
    sv.column_dimensions[col].width = w

wb.save(OUT)
print('Таблица:', OUT, '| компаний:', len(recs), '| с почтой:', sum(1 for r in recs if r['email']))
print(' ', dict(collections.Counter(r['group'] for r in recs)), '| статус из Checko:', by_via.get('Checko', 0),
      '| из поиска:', by_via.get('поиск', 0))
