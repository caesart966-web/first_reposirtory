"""Очередь непроверенных компаний -> входные файлы для очередного хода.
python3 -I make_round.py <номер_хода> <агентов> <компаний_на_агента>"""
import json, glob, sys
rnd, agents, per = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
items = []
for f in sorted(glob.glob('batches/batch_[0-9][0-9].json')):
    items += json.load(open(f))
done = set()
for f in glob.glob('out/*.json'):
    for r in json.load(open(f)):
        if (r.get('searches') or 0) > 0:
            done.add(r['inn'])
queue = [x for x in items if x['inn'] not in done]
print('в очереди', len(queue))
for a in range(agents):
    part = queue[a * per:(a + 1) * per]
    if not part:
        break
    fn = f'batches/r{rnd:02d}_{a + 1:02d}.json'
    json.dump(part, open(fn, 'w'), ensure_ascii=False, indent=1)
    print(fn, len(part))
