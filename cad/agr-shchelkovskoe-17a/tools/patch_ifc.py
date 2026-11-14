"""Правка ЦИМ АГР по заключению о проверке ТЭП (02.11.2026):
АР — зона «Общая площадь» по внутреннему контуру наружных стен + открытые планировочные элементы с лестницами;
ПС — IfcSpatialZone по границам земельного участка.
Правка построчная: исходный текст экспорта не переформатируется, новые сущности дописываются в конец DATA."""
import os, re, sys
import numpy as np
import ifcopenshell, ifcopenshell.geom, ifcopenshell.guid
import ifcopenshell.util.placement as up
from shapely.geometry import Polygon
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ifc_geom import spaces

SRC = sys.argv[1]; OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)


def num(v):
    """Число в записи STEP: без экспоненты, с точкой."""
    v = round(float(v), 6)
    if v == int(v):
        return f'{int(v)}.'
    return repr(v)


def clean(poly, ccw=True, tol=0.5):
    """Убрать повторы и точки на прямой; обход против часовой."""
    pts = list(poly.exterior.coords)[:-1]
    out = []
    for p in pts:
        if not out or np.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > tol:
            out.append(p)
    if np.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= tol:
        out.pop()
    res = []
    n = len(out)
    for i in range(n):
        a, b, c = out[i - 1], out[i], out[(i + 1) % n]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        d = max(np.hypot(b[0] - a[0], b[1] - a[1]), np.hypot(c[0] - b[0], c[1] - b[1]))
        if abs(cross) / max(d, 1) > 1.0:              # отклонение от прямой больше 1 мм
            res.append(b)
    p = Polygon(res)
    if p.exterior.is_ccw != ccw:
        res = res[::-1]
    return res


def rd(path):
    """Текст файла с переводами строк LF; исходные CRLF возвращаются при записи."""
    b = open(path, 'rb').read()
    assert b.count(b'\r\n') == b.count(b'\n'), 'смешанные переводы строк'
    return b.decode('utf-8').replace('\r\n', '\n')


def wr(path, text):
    open(path, 'wb').write(text.replace('\n', '\r\n').encode('utf-8'))


def pts2d(pts):
    return '(' + ','.join(f'({num(x)},{num(y)})' for x, y in pts) + ')'


def patch_lines(text, repl):
    for eid, new in repl.items():
        pat = re.compile(rf'^#{eid}=.*?;[ \t]*$', re.M)
        assert len(pat.findall(text)) == 1, eid
        text = pat.sub(lambda m: new, text, count=1)
    return text


def append_entities(text, lines):
    k = text.rindex('ENDSEC;')
    return text[:k] + ''.join(l + '\n' for l in lines) + text[k:]


# ---------------------------------------------------------------- АР
ar_path = os.path.join(SRC, 'AR.ifc')
f = ifcopenshell.open(ar_path)
S = spaces(f)
spp = S['СПП в ГНС']['poly']; old = S['Общая площадь']['poly']
rooms = [v['poly'] for k, v in S.items() if k not in ('Общая площадь', 'СПП в ГНС')]
inner = unary_union(rooms).buffer(200, join_style=2).buffer(-200, join_style=2)      # закрытие зазоров перегородок
assert inner.geom_type == 'Polygon' and not inner.interiors

st = ifcopenshell.geom.settings(); st.set(st.USE_WORLD_COORDS, True)


def footprint(e):
    sh = ifcopenshell.geom.create_shape(st, e)
    v = np.array(sh.geometry.verts).reshape(-1, 3) * 1000
    fc = np.array(sh.geometry.faces).reshape(-1, 3)
    tr = [Polygon([(v[i][0], v[i][1]) for i in t]) for t in fc]
    return unary_union([t for t in tr if t.area > 1e-3])


stair2 = [e for e in f.by_type('IfcStair') if e.Name.endswith(':474062')][0]
st2 = footprint(stair2).minimum_rotated_rectangle
# открытые планировочные элементы — выступы прежней зоны за наружный контур стен (крупнее 1 м²)
d = old.difference(spp)
parts = [g for g in (d.geoms if hasattr(d, 'geoms') else [d]) if g.area > 1e6]
assert len(parts) == 3, [round(g.area / 1e6, 3) for g in parts]
parts.sort(key=lambda g: g.centroid.y)                      # вход с пандусом, служебное крыльцо, терраса
porch = parts[0]
gap = porch.distance(st2)
joined = unary_union([porch, st2.buffer(max(gap, 0) + 1, join_style=2)]).buffer(-1, join_style=2) if gap > 0 else unary_union([porch, st2])
if joined.geom_type != 'Polygon':
    joined = None
zone_parts = [inner] + ([joined] if joined is not None else [porch, st2]) + parts[1:]
names = ['помещения в пределах внутренних поверхностей наружных стен',
         'крыльцо главного входа с пандусом и лестницей', 'крыльцо служебного входа с лестницей', 'терраса загрузки']
areas = [g.area / 1e6 for g in zone_parts]
total = sum(areas)
for n, a in zip(names, areas):
    print(f'  {a:9.3f} м²  {n}')
print(f'  {total:9.3f} м²  зона «Общая площадь»; было {old.area / 1e6:.3f}; лестница входа {st2.area / 1e6:.3f}; зазор {gap:.1f} мм')
for i, a in enumerate(zone_parts):
    for b in zone_parts[i + 1:]:
        assert a.intersection(b).area < 1.0, 'части зоны пересекаются'

P = S['Общая площадь']['P']; Pi = np.linalg.inv(P)
old_local = S['Общая площадь']['local']
ccw = Polygon(old_local).exterior.is_ccw


def to_local(poly):
    pts = clean(poly, ccw=True)
    loc = [tuple((Pi @ np.array([x, y, S['Общая площадь']['z'], 1.0]))[:2]) for x, y in pts]
    if Polygon(loc).exterior.is_ccw != ccw:
        loc = loc[::-1]
    return loc


text = rd(ar_path)
max_id = max(int(m) for m in re.findall(r'^#(\d+)=', text, re.M))
loc0 = to_local(zone_parts[0])
new = []
item_ids = [501]
nid = max_id
for g in zone_parts[1:]:
    loc = to_local(g)
    a, b, c, s_ = nid + 1, nid + 2, nid + 3, nid + 4
    new += [f'#{a}=IFCCARTESIANPOINTLIST2D({pts2d(loc)});', f'#{b}=IFCINDEXEDPOLYCURVE(#{a},$,.F.);',
            f'#{c}=IFCARBITRARYCLOSEDPROFILEDEF(.AREA.,$,#{b});', f'#{s_}=IFCEXTRUDEDAREASOLID(#{c},#500,#32,4499.9999999999991);']
    item_ids.append(s_); nid += 4
vol = total * 3.8
repl = {497: f'#497=IFCCARTESIANPOINTLIST2D({pts2d(loc0)});',
        502: "#502=IFCSHAPEREPRESENTATION(#15,'Body','SweptSolid',(" + ','.join(f'#{i}' for i in item_ids) + '));',
        511: f"#511=IFCPROPERTYSINGLEVALUE('RUS_Volume',$,IFCREAL({repr(round(vol, 6))}),$);",
        512: f"#512=IFCPROPERTYSINGLEVALUE('RUS_Area',$,IFCREAL({repr(round(total, 6))}),$);"}
for k in (511, 512):
    assert re.search(rf"^#{k}=IFCPROPERTYSINGLEVALUE\('RUS_(Volume|Area)',\$,IFCREAL\(", text, re.M), k
text = append_entities(patch_lines(text, repl), new)
ar_out = os.path.join(OUT, 'AR.ifc')
wr(ar_out, text)

# ---------------------------------------------------------------- ПС
ps_path = os.path.join(SRC, 'PS.ifc')
g = ifcopenshell.open(ps_path)
site = g.by_type('IfcSite')[0]
fs = site.Representation.Representations[0].Items[0]
V = np.array(fs.Coordinates.CoordList)
Ms = np.array(up.get_local_placement(site.ObjectPlacement)); Msi = np.linalg.inv(Ms)
Wv = np.array([(Ms @ np.array([x, y, z, 1.0]))[:3] for x, y, z in V])
tris = []
for face in fs.Faces:
    idx = [i - 1 for i in face.CoordIndex]
    p = Polygon([(Wv[i][0], Wv[i][1]) for i in idx])
    if p.area > 1e-3:
        tris.append(p.buffer(0))
topo = unary_union(tris)
# рельеф в модели построен без пятна застройки: граница участка — внешний контур рельефа вместе с пятном
u = unary_union([topo, old]).buffer(60, join_style=2).buffer(-60, join_style=2)
assert u.geom_type == 'Polygon', u.geom_type
boundary = Polygon(u.exterior)
print(f'  участок: рельеф {topo.area / 1e6:.3f} м² + пятно застройки {old.area / 1e6:.3f} м²; контур участка {boundary.area / 1e6:.3f} м²; атрибут 1057.277')
bw = clean(boundary, ccw=True, tol=5.0)
bl = [tuple((Msi @ np.array([x, y, 0.0, 1.0]))[:2]) for x, y in bw]
if not Polygon(bl).exterior.is_ccw:
    bl = bl[::-1]
area_site = Polygon(bl).area / 1e6
assert abs(area_site - 1057.277) < 0.5, area_site
ptext = rd(ps_path)
m0 = max(int(m) for m in re.findall(r'^#(\d+)=', ptext, re.M))
ids = {k: m0 + i + 1 for i, k in enumerate(['pl', 'pc', 'pd', 'pt', 'ax', 'sol', 'rep', 'pds', 'lp', 'zone', 'pset', 'rel', 'agg'])}
gid = ifcopenshell.guid.new; nm = lambda s: ifcopenshell.util_escape(s) if hasattr(ifcopenshell, 'util_escape') else s


def step(s):
    out = ''
    buf = ''
    for ch in s:
        if ord(ch) < 128:
            if buf:
                out += '\\X2\\' + ''.join(f'{ord(c):04X}' for c in buf) + '\\X0\\'; buf = ''
            out += ch
        else:
            buf += ch
    if buf:
        out += '\\X2\\' + ''.join(f'{ord(c):04X}' for c in buf) + '\\X0\\'
    return out


zname = step('Участок застройки'); ztype = step('Границы земельного участка')
ps_new = [
    f"#{ids['pl']}=IFCCARTESIANPOINTLIST2D({pts2d(bl)});",
    f"#{ids['pc']}=IFCINDEXEDPOLYCURVE(#{ids['pl']},$,.F.);",
    f"#{ids['pd']}=IFCARBITRARYCLOSEDPROFILEDEF(.AREA.,$,#{ids['pc']});",
    f"#{ids['pt']}=IFCCARTESIANPOINT((0.,0.,153850.));",
    f"#{ids['ax']}=IFCAXIS2PLACEMENT3D(#{ids['pt']},$,$);",
    f"#{ids['sol']}=IFCEXTRUDEDAREASOLID(#{ids['pd']},#{ids['ax']},#153,100.);",
    f"#{ids['rep']}=IFCSHAPEREPRESENTATION(#15,'Body','SweptSolid',(#{ids['sol']}));",
    f"#{ids['pds']}=IFCPRODUCTDEFINITIONSHAPE($,$,(#{ids['rep']}));",
    f"#{ids['lp']}=IFCLOCALPLACEMENT(#156,#20);",
    f"#{ids['zone']}=IFCSPATIALZONE('{gid()}',#6,'{zname}',$,'{ztype}',#{ids['lp']},#{ids['pds']},'{zname}',.USERDEFINED.);",
    f"#{ids['pset']}=IFCPROPERTYSET('{gid()}',#6,'RusSet_AGR','',(#160,#161));",
    f"#{ids['rel']}=IFCRELDEFINESBYPROPERTIES('{gid()}',#6,$,$,(#{ids['zone']}),#{ids['pset']});",
    f"#{ids['agg']}=IFCRELAGGREGATES('{gid()}',#6,$,$,#157,(#22,#{ids['zone']}));",
]
# здание и зона участка — в одной декомпозиции площадки: в связи #170 дополняется перечень объектов
pat170 = re.compile(r"^(#170=IFCRELAGGREGATES\(.*#157,\()#22(\)\);)[ \t]*$", re.M)
assert len(pat170.findall(ptext)) == 1
ptext = pat170.sub(lambda m: f"{m.group(1)}#22,#{ids['zone']}{m.group(2)}", ptext, count=1)
ps_new.pop()
ptext = append_entities(ptext, ps_new)
wr(os.path.join(OUT, 'PS.ifc'), ptext)
print(f'  зона участка: {area_site:.3f} м², вершин {len(bl)}')
import json
json.dump(dict(parts=dict(zip(names, areas)), total=total, old=old.area / 1e6, stair=st2.area / 1e6, site=area_site,
               inner_world=clean(inner), parts_world=[clean(p) for p in zone_parts], site_world=bw, site_local=bl), open(os.path.join(OUT, 'areas.json'), 'w'), ensure_ascii=False, indent=1)
