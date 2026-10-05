"""Общие помощники для сцен Blender: сброс, Cycles, меш из numpy, материалы."""
import bpy, bmesh, math
import numpy as np
from mathutils import Vector


def reset(samples=64, res=(960, 400), transparent=False, look='AgX - Medium High Contrast', exposure=0.0, view='AgX'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 6
    sc.cycles.transparent_max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    sc.render.image_settings.color_depth = '8'
    sc.view_settings.view_transform = view
    try:
        sc.view_settings.look = look
    except Exception as e:
        print('look fail', e)
    sc.view_settings.exposure = exposure
    sc.render.threads_mode = 'AUTO'
    return sc


def mesh_from_grid(name, X, Y, Z, attrs=None, smooth=True):
    """Сетка ny×nx: вершины из массивов, грани — квадраты."""
    ny, nx = Z.shape
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], -1).astype(np.float32)
    idx = np.arange(nx * ny).reshape(ny, nx)
    a = idx[:-1, :-1].ravel(); b = idx[:-1, 1:].ravel(); c = idx[1:, 1:].ravel(); d = idx[1:, :-1].ravel()
    quads = np.stack([a, b, c, d], -1).astype(np.int32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set('co', verts.ravel())
    nq = len(quads)
    me.loops.add(nq * 4)
    me.loops.foreach_set('vertex_index', quads.ravel())
    me.polygons.add(nq)
    me.polygons.foreach_set('loop_start', np.arange(0, nq * 4, 4, dtype=np.int32))
    me.polygons.foreach_set('loop_total', np.full(nq, 4, dtype=np.int32))
    me.update(calc_edges=True)
    me.validate(verbose=False)
    if smooth:
        me.polygons.foreach_set('use_smooth', np.ones(nq, dtype=bool))
    if attrs:
        for k, v in attrs.items():
            at = me.attributes.new(k, 'FLOAT', 'POINT')
            at.data.foreach_set('value', np.asarray(v, dtype=np.float32).ravel())
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def node(nt, typ, loc=(0, 0), **kw):
    n = nt.nodes.new(typ)
    n.location = loc
    for k, v in kw.items():
        if k.startswith('i_'):
            n.inputs[k[2:].replace('_', ' ')].default_value = v
        else:
            setattr(n, k, v)
    return n


def principled(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, **extra):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    for k, v in extra.items():
        p.inputs[k].default_value = v
    return m


def assign(ob, mat):
    if ob.data.materials:
        ob.data.materials[0] = mat
    else:
        ob.data.materials.append(mat)


def render(path):
    sc = bpy.context.scene
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
