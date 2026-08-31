import json, sys, os
inn, note = sys.argv[1], sys.argv[2]
n = json.load(open("work/notes.json")) if os.path.exists("work/notes.json") else {}
n[inn] = note
json.dump(n, open("work/notes.json","w"), ensure_ascii=False, indent=1)
