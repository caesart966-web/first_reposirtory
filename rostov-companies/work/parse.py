import sys, openpyxl, json, collections
def load(path, src):
    ws=openpyxl.load_workbook(path,read_only=True,data_only=True).worksheets[0]
    rows=list(ws.iter_rows(values_only=True))
    hi=next(i for i,r in enumerate(rows) if r[0] and str(r[0]).strip()=='N п/п')
    hdr=[(h or '').strip() for h in rows[hi]]
    out=[]
    for r in rows[hi+1:]:
        if r[1] or (len(r)>8 and r[8]):
            d={hdr[i]:(str(v).strip() if v is not None else '') for i,v in enumerate(r) if i<len(hdr)}
            d['_src']=src
            out.append(d)
    return out
a=load('../input/register-1-500.xlsx','файл 1 (1–500)')
b=load('../input/register-501-988.xlsx','файл 2 (501–988)')
print(len(a),len(b))
print(collections.Counter(x.get('Дата прекращения членства','')!='' for x in b))
print([x['N п/п'] for x in b][:3],[x['N п/п'] for x in b][-3:])
inn=lambda x:x['ИНН']
print('overlap',len({*map(inn,a)}&{*map(inn,b)}),'uniq',len({*map(inn,a+b)}), 'empty inn', sum(1 for x in a+b if not x['ИНН']))
print(collections.Counter(len(x['ИНН']) for x in a+b))
print(b[0])
json.dump(a+b,open('all.json','w'),ensure_ascii=False)
