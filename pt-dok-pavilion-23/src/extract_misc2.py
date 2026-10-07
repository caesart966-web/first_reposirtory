import sys, ezdxf, collections
from ezdxf import recover, bbox
d=sys.argv[1]
doc,_=recover.readfile(f'{d}/2 этаж.dxf'); msp=doc.modelspace()
print(collections.Counter(e.dxf.layer for e in msp).most_common(30))
for e in msp:
    try: b=bbox.extents([e])
    except Exception: continue
    if not b.has_data: continue
    if 17000<b.extmin.y<23000 and 17000<b.extmax.y<23000 and b.size.x>3000:
        print(e.dxftype(), e.dxf.layer, e.dxf.get('name','') if e.dxftype()=='INSERT' else '', round(b.extmin.x),round(b.extmin.y),round(b.extmax.x),round(b.extmax.y))
doc,_=recover.readfile(f'{d}/1 этаж с морозильными камерами.dxf'); msp=doc.modelspace()
c=collections.Counter()
for e in msp:
    if e.dxf.layer.startswith('Мебель'):
        c[(e.dxftype(), e.dxf.name if e.dxftype()=='INSERT' else '')]+=1
print(c.most_common(20))
boxes=[]
for e in msp:
    if e.dxf.layer.startswith('Мебель') and e.dxftype() in ('INSERT','LWPOLYLINE'):
        b=bbox.extents([e])
        if b.size.x>1500 and b.size.y>1500:
            boxes.append((e.dxftype(), e.dxf.name if e.dxftype()=='INSERT' else '', round(b.extmin.x),round(b.extmin.y),round(b.extmax.x),round(b.extmax.y)))
for b in sorted(boxes, key=lambda t:(t[3],t[2])): print('frz', *b)
