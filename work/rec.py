import json, sys, os, re
inn, email, src = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv)>3 else "")
f = json.load(open("work/found.json")) if os.path.exists("work/found.json") else {}
d = json.load(open("work/done.json")) if os.path.exists("work/done.json") else {}
if email and email != "-":
    for e in [x.strip() for x in email.split(",") if x.strip()]:
        if not re.fullmatch(r"[^@\s,]+@[^@\s,]+\.[A-Za-z]{2,}", e):
            print(f"ОТКЛОНЕНО: '{e}' не похоже на email"); sys.exit(1)
    f[inn] = {"email": email, "source": src}
d[inn] = True
json.dump(f, open("work/found.json","w"), ensure_ascii=False, indent=1)
json.dump(d, open("work/done.json","w"))
print(f"{inn}: {'НАЙДЕНО '+email if email!='-' else 'не найдено'} | обработано {len(d)}/1199, находок {len(f)}")
