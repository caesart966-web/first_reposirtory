"""Строительные детали для сцен: брусья, решётки крана, поддоны, штабели."""
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix


def box(bm, center, size, rot_z=0.0, mat_index=0):
    res = bmesh.ops.create_cube(bm, size=1.0)
    m = Matrix.Translation(Vector(center)) @ Matrix.Rotation(rot_z, 4, 'Z') @ Matrix.Diagonal((*size, 1.0))
    bmesh.ops.transform(bm, matrix=m, verts=res['verts'])
    for f in {f for v in res['verts'] for f in v.link_faces}:
        f.material_index = mat_index
    return res['verts']


def strut(bm, p0, p1, r, mat_index=0):
    """Брус квадратного сечения r×r от p0 до p1."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    if L < 1e-6:
        return
    z = d.normalized()
    up = Vector((0, 0, 1)) if abs(z.z) < 0.95 else Vector((1, 0, 0))
    x = up.cross(z).normalized()
    y = z.cross(x)
    rot = Matrix((x, y, z)).transposed().to_4x4()
    res = bmesh.ops.create_cube(bm, size=1.0)
    m = Matrix.Translation((p0 + p1) / 2) @ rot @ Matrix.Diagonal((r, r, L, 1.0))
    bmesh.ops.transform(bm, matrix=m, verts=res['verts'])
    for f in {f for v in res['verts'] for f in v.link_faces}:
        f.material_index = mat_index


def lattice_mast(bm, base, side, height, seg, r_chord, r_brace, mat_index=0):
    """Четырёхгранная решётчатая башня."""
    bx, by, bz = base
    h2 = side / 2
    corners = [(-h2, -h2), (h2, -h2), (h2, h2), (-h2, h2)]
    for cx, cy in corners:
        strut(bm, (bx + cx, by + cy, bz), (bx + cx, by + cy, bz + height), r_chord, mat_index)
    n = int(height / seg)
    for i in range(n + 1):
        z = bz + i * seg
        for k in range(4):
            ax, ay = corners[k]; cx2, cy2 = corners[(k + 1) % 4]
            strut(bm, (bx + ax, by + ay, z), (bx + cx2, by + cy2, z), r_brace, mat_index)
            if i < n:
                z2 = z + seg
                if i % 2 == 0:
                    strut(bm, (bx + ax, by + ay, z), (bx + cx2, by + cy2, z2), r_brace, mat_index)
                else:
                    strut(bm, (bx + cx2, by + cy2, z), (bx + ax, by + ay, z2), r_brace, mat_index)


def lattice_jib(bm, start, length, direction, width, height, seg, r_chord, r_brace, mat_index=0):
    """Треугольная стрела: два нижних пояса и один верхний."""
    sx, sy, sz = start
    dx = direction  # +1 или -1 по оси X
    w2 = width / 2
    n = int(length / seg)
    A = lambda t: (sx + dx * t, sy - w2, sz)
    B = lambda t: (sx + dx * t, sy + w2, sz)
    C = lambda t: (sx + dx * t, sy, sz + height)
    for f in (A, B, C):
        strut(bm, f(0), f(length), r_chord, mat_index)
    for i in range(n + 1):
        t = i * seg
        strut(bm, A(t), B(t), r_brace, mat_index)
        strut(bm, A(t), C(t), r_brace, mat_index)
        strut(bm, B(t), C(t), r_brace, mat_index)
        if i < n:
            t2 = t + seg
            strut(bm, A(t), C(t2) if i % 2 == 0 else A(t2), r_brace, mat_index)
            strut(bm, B(t), C(t2) if i % 2 == 0 else B(t2), r_brace, mat_index)
            strut(bm, A(t), B(t2), r_brace, mat_index)


def to_object(bm, name, mats):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def bevel(ob, width=0.01, segments=2):
    md = ob.modifiers.new('Bevel', 'BEVEL')
    md.width = width
    md.segments = segments
    md.limit_method = 'ANGLE'
    return md
