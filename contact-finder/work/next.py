import json,sys
q=json.load(open('recheck.json')); r=json.load(open('nostroy_results.json'))
n=int(sys.argv[1]) if len(sys.argv)>1 else 4
todo=[x for x in q if r.get(x['inn'],{}).get('conf') in (None,'НЕ ПРОВЕРЯЛОСЬ')]
for x in todo[:n]: print(f"{x['name']}|{x['inn']}")
print(f"--- в очереди: {len(todo)}", file=sys.stderr)
