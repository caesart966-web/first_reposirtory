import sys, ezdxf, collections
from ezdxf import recover, bbox
doc,_=recover.readfile(sys.argv[1]); msp=doc.modelspace()
c=collections.Counter()
res=[]
for e in msp:
    try: b=bbox.extents([e], fast=True)
    except Exception: continue
    if not b.has_data: continue
    if 28225<=b.extmin.y and b.extmax.y<=40200 and 10000<b.extmin.x<16000 and b.size.x>2000 and b.size.y>2000:
        res.append((e.dxftype(), e.dxf.layer, e.dxf.name if e.dxftype()=='INSERT' else '', round(b.extmin.x),round(b.extmin.y),round(b.extmax.x),round(b.extmax.y)))
for r in res: print(*r)
