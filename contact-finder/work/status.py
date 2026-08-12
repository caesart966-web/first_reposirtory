"""Состояние пробива — единственный источник правды по цифрам.

Очередь не ведётся вручную и не «дополняется»: она каждый раз выводится
из полного реестра минус уже проверенное. Поэтому пропустить компанию или
пробить её дважды нельзя по построению — расхождение сразу видно в строке
«сходится».
"""
import json

recs = json.load(open('nostroy.json'))
res = json.load(open('nostroy_results.json'))

act = [r for r in recs if r['status'] == 'Является членом']
done = set(res)


def name(r):
    return r.get('short') or r.get('full') or ''


todo = [r for r in act if r['inn'] not in done]
ul = sorted((r for r in todo if r['typ'] != 'ИП'), key=lambda r: name(r).lower())
ip = sorted((r for r in todo if r['typ'] == 'ИП'), key=lambda r: name(r).lower())

# ИП уходят в конец очереди по указанию заказчика.
json.dump([{'inn': r['inn'], 'name': name(r), 'typ': r['typ']} for r in ul + ip],
          open('recheck.json', 'w'), ensure_ascii=False, indent=1)

phones = sum(1 for v in res.values() if v['phone'])
print(f'действующих членов СРО-410 : {len(act)}')
print(f'проверено                  : {len(done)}  (телефон найден у {phones})')
print(f'осталось                   : {len(todo)}  = {len(ul)} ЮЛ + {len(ip)} ИП')
print(f'сходится ({len(done)}+{len(todo)}={len(act)})    : {len(done) + len(todo) == len(act)}')

extra = done - {r['inn'] for r in act}
if extra:
    print(f'ВНИМАНИЕ: {len(extra)} проверенных ИНН нет среди действующих членов')
