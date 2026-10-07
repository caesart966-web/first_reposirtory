import sys, json, ezdxf
from ezdxf import recover
def pip(x,y,poly):
    c=False; n=len(poly)
    for i in range(n):
        x1,y1=poly[i]; x2,y2=poly[(i+1)%n]
        if (y1>y)!=(y2>y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1: c=not c
    return c
def area(p):
    return abs(sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p))))/2
out={}
for key,f in [('f1','1 этаж '),('f2','2 этаж'),('b','Технический подвал')]:
    doc,_=recover.readfile(f'{sys.argv[1]}/{f}.dxf'); msp=doc.modelspace()
    polys=[]
    for e in msp:
        if e.dxf.layer.startswith('Зоны') and e.dxftype()=='LWPOLYLINE':
            pts=[(round(x,1),round(y,1)) for x,y in e.get_points('xy')]
            polys.append(pts)
    rooms=[]
    for e in msp.query('INSERT'):
        if not e.dxf.layer.startswith('Зоны'): continue
        at={a.dxf.tag:a.dxf.text for a in e.attribs}
        if 'ROOM_NUMBER' not in at: continue
        name=e.dxf.name.rsplit('_',2)[0]
        x,y=e.dxf.insert.x,e.dxf.insert.y
        cand=[p for p in polys if pip(x,y,p)]
        cand.sort(key=area)
        poly=cand[0] if cand else None
        rooms.append(dict(num=at['ROOM_NUMBER'],name=name,area=at.get('ROOM_AREA'),pt=[round(x),round(y)],poly=poly,parea=round(area(poly)/1e6,2) if poly else None))
    out[key]=dict(rooms=rooms,npoly=len(polys))
    print(key,len(rooms),'rooms',len(polys),'polys', sum(1 for r in rooms if r['poly'] is None),'unmatched')
json.dump(out,open(sys.argv[2],'w'),ensure_ascii=False,indent=0)
