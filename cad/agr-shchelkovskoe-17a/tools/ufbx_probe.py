"""Независимое чтение FBX библиотекой ufbx; результат — JSON в stdout."""
import json, os, sys
import ufbx

sc = ufbx.load_file(sys.argv[1])
out = {'version': sc.metadata.version, 'warnings': len(sc.metadata.warnings), 'unit_m': sc.settings.unit_meters}
nodes = []
for n in sc.nodes:
    if n.is_root:
        continue
    m = n.mesh
    nodes.append([n.name, m.num_vertices if m else 0, m.num_faces if m else 0, m.num_triangles if m else 0])
out['nodes'] = nodes
print(json.dumps(out))
sys.stdout.flush()
os._exit(0)      # привязка ufbx падает при обычном завершении интерпретатора
