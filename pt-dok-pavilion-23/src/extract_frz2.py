import sys, json, ezdxf
from ezdxf import recover
doc,_=recover.readfile(sys.argv[1]); msp=doc.modelspace()
out=[]
for e in msp:
    if e.dxf.layer.startswith('Зоны морозильные') and e.dxftype()=='LWPOLYLINE':
        pts=[(round(x),round(y)) for x,y in e.get_points('xy')]
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        out.append(dict(poly=pts, bb=[min(xs),min(ys),max(xs),max(ys)]))
for e in msp.query('INSERT'):
    if e.dxf.layer.startswith('Зоны морозильные'):
        print('ins', e.dxf.name, round(e.dxf.insert.x), round(e.dxf.insert.y), {a.dxf.tag:a.dxf.text for a in e.attribs})
for o in sorted(out,key=lambda o:(o['bb'][1],o['bb'][0])): print(o['bb'], len(o['poly']), round((o['bb'][2]-o['bb'][0])*(o['bb'][3]-o['bb'][1])/1e6,2))
json.dump(out,open(sys.argv[2],'w'))
