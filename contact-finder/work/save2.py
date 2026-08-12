import json, os, sys
F='nostroy_results.json'
db = json.load(open(F)) if os.path.exists(F) else {}
db.update(json.load(sys.stdin))
json.dump(db, open(F,'w'), ensure_ascii=False, indent=1)
print('сохранено:', len(db), '| с телефоном:', sum(1 for v in db.values() if v['phone']))
