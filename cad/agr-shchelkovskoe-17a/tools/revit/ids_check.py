import json, re, sys, ifcopenshell, ifcopenshell.util.element as ue
m = ifcopenshell.open(sys.argv[1]); d = json.load(open(sys.argv[2]))
bad = 0
for rule in d['rulesDetails']:
    if 'IDS' not in rule['ruleName'][0]:
        continue
    for e in rule['elements']:
        cls = re.findall(r'IFC[A-Z]+', e['additionalText'])
        filt = re.findall(r"набор[а-я]* параметров '([^']+)' параметр '([^']+)'(?: со значением '([^']+)')?", e['additionalText'])
        objs = [o for o in m.by_type('IfcProduct') if o.is_a().upper() in cls]
        ps = ue.get_psets
        for pn, k, v in filt:
            objs = [o for o in objs if k in ps(o).get(pn, {}) and (not v or str(ps(o)[pn][k]) == v)]
        nf = 0
        for q in e['elements']:
            t = q['title']
            mm = re.search(r"'([^']+)' должен быть параметр '([^']+)'(?: со значением (.*))?", t)
            pn, k, val = mm.group(1), mm.group(2), mm.group(3)
            allowed = None
            if val:
                if 'enumeration' in val:
                    allowed = re.findall(r"'([^']*)'", val[val.index('['):])
                else:
                    allowed = [val.strip()]
            for o in objs:
                p = ps(o).get(pn, {})
                if k not in p or p[k] is None or (allowed and str(p[k]) not in allowed):
                    nf += 1
                    if nf <= 3:
                        print('   НАРУШЕНИЕ', o.Name, pn, k, repr(p.get(k)), allowed)
        bad += nf
        print('%-72s объектов %3d, нарушений %d' % (e['title'][:72], len(objs), nf))
print('ИТОГО нарушений IDS:', bad)
