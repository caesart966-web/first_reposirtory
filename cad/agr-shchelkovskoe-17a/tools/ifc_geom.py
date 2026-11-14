"""Геометрия зон и помещений АР-модели в плане (мм, МСК)."""
import ifcopenshell, ifcopenshell.util.placement as up, ifcopenshell.util.element as ue
import numpy as np
from shapely.geometry import Polygon

def profile_pts(pd):
    oc = pd.OuterCurve
    if oc.is_a('IfcIndexedPolyCurve'):
        pts = [tuple(p) for p in oc.Points.CoordList]
        if oc.Segments:
            idx = []
            for s in oc.Segments:
                v = list(s.wrappedValue)
                assert s.is_a('IfcLineIndex'), s
                for i in v:
                    if not idx or idx[-1] != i:
                        idx.append(i)
            pts = [pts[i - 1] for i in idx]
        return pts
    if oc.is_a('IfcPolyline'):
        return [tuple(p.Coordinates) for p in oc.Points]
    raise ValueError(oc.is_a())

def spaces(f):
    out = {}
    for s in f.by_type('IfcSpace'):
        ps = ue.get_psets(s)
        nm = ps['RusSet_Common']['RUS_Name']
        M = np.array(up.get_local_placement(s.ObjectPlacement))
        it = s.Representation.Representations[0].Items[0]
        P = M @ np.array(up.get_axis2placement(it.Position))
        pts = profile_pts(it.SweptArea)
        wp = [(P @ np.array([x, y, 0, 1]))[:3] for x, y in pts]
        out[nm] = dict(space=s, poly=Polygon([(p[0], p[1]) for p in wp]), P=P, item=it, z=wp[0][2], local=pts)
    return out
