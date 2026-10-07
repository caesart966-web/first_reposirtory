import sys, ezdxf, collections
from ezdxf import recover, bbox
d=sys.argv[1]
doc,_=recover.readfile(f'{d}/2 этаж.dxf'); msp=doc.modelspace()
for e in msp:
    if e.dxf.layer.startswith('Зоны') and e.dxftype()=='LWPOLYLINE':
        pts=list(e.get_points('xy'))
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        a=abs(sum(pts[i][0]*pts[(i+1)%len(pts)][1]-pts[(i+1)%len(pts)][0]*pts[i][1] for i in range(len(pts))))/2e6
        if a>500 or a<12: print('f2poly', e.dxf.layer, round(min(xs)),round(min(ys)),round(max(xs)),round(max(ys)), round(a,2), len(pts))
# voids: look for text 'Второй свет' positions on f2
for e in msp.query('TEXT MTEXT'):
    s=e.dxf.text if e.dxftype()=='TEXT' else e.plain_text()
    if 'свет' in s: print('f2text', round(e.dxf.insert.x), round(e.dxf.insert.y), s)
doc,_=recover.readfile(f'{d}/1 этаж с морозильными камерами.dxf'); msp=doc.modelspace()
c=collections.Counter()
for e in msp:
    if e.dxf.layer.startswith('Мебель'):
        c[(e.dxftype(), e.dxf.get('name',''))]+=1
print(c.most_common(20))
# bounding boxes of inserts on furniture layer
boxes=[]
for e in msp.query('INSERT'):
    if e.dxf.layer.startswith('Мебель'):
        b=bbox.extents([e])
        boxes.append((e.dxf.name, round(b.extmin.x),round(b.extmin.y),round(b.extmax.x),round(b.extmax.y)))
for b in sorted(boxes, key=lambda t:(t[2],t[1]))[:80]: print('frz', *b)
