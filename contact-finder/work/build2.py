import json, openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

recs = json.load(open('nostroy.json'))
res  = json.load(open('nostroy_results.json'))
by_inn = {r['inn']: r for r in recs}

wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Телефоны СРО-410'
ws.append(['№','Организация (реестр НОСТРОЙ)','ИНН','Телефон(ы)','Доп. контакты / реквизиты',
           'Источник','Достоверность','Рег.№ в СРО','Статус в СРО','КФ ВВ, ₽'])
hf = PatternFill('solid', fgColor='1F4E79'); thin = Side(style='thin', color='BFBFBF')
bd = Border(left=thin,right=thin,top=thin,bottom=thin)
for c in ws[1]:
    c.font=Font(bold=True,color='FFFFFF',size=11); c.fill=hf
    c.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True); c.border=bd

ok=PatternFill('solid',fgColor='E2EFDA'); mid=PatternFill('solid',fgColor='FFF2CC'); no=PatternFill('solid',fgColor='FCE4E4')

# сначала найденные, потом остальные
items = sorted(res.items(), key=lambda kv: (not kv[1]['phone'], kv[1]['name']))
n=0
for inn, r in items:
    n+=1; src = by_inn.get(inn, {})
    kf = src.get('kf_vv') or ''
    ws.append([n, r['name'], inn, r['phone'], r['extra'], r['src'], r['conf'],
               src.get('reg',''), src.get('status',''), kf])
    row=ws.max_row
    fill = ok if r['phone'] and r['conf'].startswith('высокая') else (mid if r['phone'] else no)
    for col in range(1,11):
        cell=ws.cell(row=row,column=col); cell.border=bd
        cell.alignment=Alignment(vertical='top',wrap_text=(col in (2,4,5,6,7)))
        cell.fill=fill
        if col==4: cell.font=Font(bold=bool(r['phone']))
    ws.cell(row=row,column=3).number_format='@'
for col,w in zip('ABCDEFGHIJ',[5,44,14,34,52,42,26,10,16,14]):
    ws.column_dimensions[col].width=w
ws.freeze_panes='A2'; ws.auto_filter.ref=f"A1:J{ws.max_row}"

found=sum(1 for v in res.values() if v['phone'])
act=sum(1 for r in recs if r['status']=='Является членом')
s=wb.create_sheet('Сводка')
for row in [
 ['Показатель','Значение'],
 ['Источник','Реестр НОСТРОЙ, СРО № 410 — Ассоциация «ПОС», Санкт-Петербург'],
 ['Всего записей в реестре', len(recs)],
 ['Из них действующих членов', act],
 ['Исключённых', len(recs)-act],
 ['','' ],
 ['Обработано в этой сессии', len(res)],
 ['Телефон найден', found],
 ['Телефон не найден', len(res)-found],
 ['Как отбирали','Проверены ВСЕ действующие члены СРО, без исключений'],
 ['','' ],
 ['ВАЖНО: телефонов в самом реестре НЕТ','В выгрузке 37 столбцов: ИНН, ОГРН, наименование, статус, уровни ответственности, взносы. Полей телефона и e-mail нет вообще'],
 ['Как искали','Поисковая выдача — единственный доступный канал сети в этой среде'],
 ['Проверка','Телефон записан только там, где в источнике совпал ИНН'],
 ['ИП в реестре (29 шт.)','Проверены; телефонов ИП в открытых бизнес-реестрах нет ни у одного'],
 ['Если нужно добрать ещё','Прогнать программой contact-finder с ключом Checko API — она берёт контакты из платного источника'],
 ['Самый быстрый путь ко всем 972','СРО «ПОС» (Ассоциация «Петровское объединение строителей»), +7 812 335-36-86, office@sropos.ru — у СРО контакты всех своих членов'],
]:
    s.append(row)
for c in s[1]: c.font=Font(bold=True,color='FFFFFF'); c.fill=hf
s.column_dimensions['A'].width=42; s.column_dimensions['B'].width=100
for r in s.iter_rows(min_row=2): r[1].alignment=Alignment(wrap_text=True,vertical='top')

wb.save('/home/user/first_reposirtory/Телефоны_СРО410_НОСТРОЙ.xlsx')
print('found',found,'of',len(res))
