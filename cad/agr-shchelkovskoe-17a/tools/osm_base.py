"""Основа из OpenStreetMap в координатах МСК Москвы (метры)."""
import json
import xml.etree.ElementTree as ET

import numpy as np
from pyproj import Transformer

# МСК Москвы (МГГТ): поперечная Меркатора на эллипсоиде Бесселя
MSK = ('+proj=tmerc +lat_0=55.66666666667 +lon_0=37.5 +k=1 +x_0=16.098 +y_0=14.512 '
       '+ellps=bessel +towgs84=316.151,78.924,589.65,-1.57273,2.69209,2.34693,8.4507 +units=m +no_defs')
_T = Transformer.from_crs('EPSG:4326', MSK, always_xy=True)


def to_msk(lon, lat):
    return _T.transform(lon, lat)


def load(path):
    root = ET.parse(path).getroot()
    nodes, ways, rels = {}, {}, {}
    for n in root.iter('node'):
        x, y = to_msk(float(n.get('lon')), float(n.get('lat')))
        nodes[n.get('id')] = {'xy': (x, y), 'tags': {t.get('k'): t.get('v') for t in n.findall('tag')}}
    for w in root.iter('way'):
        ways[w.get('id')] = {'nd': [d.get('ref') for d in w.findall('nd')],
                             'tags': {t.get('k'): t.get('v') for t in w.findall('tag')}}
    for r in root.iter('relation'):
        rels[r.get('id')] = {'members': [(m.get('type'), m.get('ref'), m.get('role')) for m in r.findall('member')],
                             'tags': {t.get('k'): t.get('v') for t in r.findall('tag')}}
    return nodes, ways, rels


def coords(nodes, way):
    return np.array([nodes[i]['xy'] for i in way['nd'] if i in nodes])
