"""Пешеходное расстояние от главного входа до входов рельсового каркаса (по сети OpenStreetMap)."""
import sys, os, xml.etree.ElementTree as ET
import numpy as np, networkx as nx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import osm_base, frame

FOOT = {'footway', 'path', 'pedestrian', 'steps', 'living_street', 'residential', 'service', 'unclassified',
        'tertiary', 'secondary', 'primary', 'crossing', 'corridor', 'track', 'cycleway', 'platform',
        'tertiary_link', 'secondary_link', 'primary_link'}


def main(files):
    nodes, ways, tagsn = {}, {}, {}
    for p in files:
        r = ET.parse(p).getroot()
        for n in r.iter('node'):
            nodes[n.get('id')] = osm_base.to_msk(float(n.get('lon')), float(n.get('lat')))
            t = {k.get('k'): k.get('v') for k in n.findall('tag')}
            if t:
                tagsn[n.get('id')] = t
        for w in r.iter('way'):
            t = {k.get('k'): k.get('v') for k in w.findall('tag')}
            ways[w.get('id')] = ([nd.get('ref') for nd in w.findall('nd')], t)
    G = nx.Graph()
    for wid, (nds, t) in ways.items():
        hw = t.get('highway')
        if hw not in FOOT and t.get('foot') not in ('yes', 'designated'):
            continue
        if t.get('foot') == 'no' or t.get('access') == 'private' and t.get('foot') not in ('yes',):
            continue
        for a, b in zip(nds, nds[1:]):
            if a in nodes and b in nodes:
                G.add_edge(a, b, w=float(np.hypot(*(np.array(nodes[a]) - nodes[b]))))
    entr = frame.l2w(np.array([[4.3, -1.6]]))[0]          # у главного входа
    ids = [n for n in G.nodes]
    P = np.array([nodes[n] for n in ids])
    d0 = np.hypot(*(P - entr).T)
    src = ids[int(np.argmin(d0))]
    print('старт: узел в %.1f м от входа' % d0.min())
    L = nx.single_source_dijkstra_path_length(G, src, weight='w')
    out = []
    for nid, t in tagsn.items():
        if t.get('railway') in ('subway_entrance', 'train_station_entrance') or (t.get('railway') in ('station', 'halt')):
            xy = np.array(nodes[nid])
            dd = np.hypot(*(P - xy).T)
            j = int(np.argmin(dd))
            if dd[j] > 40 or ids[j] not in L:
                continue
            out.append((L[ids[j]] + dd[j] + d0.min(), t.get('name') or ('вход ' + str(t.get('ref'))), t.get('railway'),
                        float(np.hypot(*(xy - entr)))))
    for row in sorted(out)[:12]:
        print('%6.0f м пешком, %6.0f м по прямой  %s (%s)' % (row[0], row[3], row[1], row[2]))


if __name__ == '__main__':
    main(sys.argv[1:])
