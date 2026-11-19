"""
build_p38.py -- Walther P38 (Walther-made, "ac 43") first-person viewmodel + gloved FP hands.

Everything here is generated from scratch: geometry, procedural materials, baked textures.

Run (from anywhere):
  "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" --background --factory-startup \
      --python-exit-code 1 --python tools/blender/weapons/build_p38.py -- [options]

Options:
  --no-bake       skip baking + export (previews use the live procedural materials)
  --res N         baked texture size (default 4096)
  --samples N     preview samples (default 64)
  --no-previews   skip preview renders
  --cpu           force CPU for Cycles

Conventions (docs/ASSET_PIPELINE.md): real-world scale, Blender +Y = muzzle (= Godot -Z),
origin on the bore axis directly above the trigger. All dimensions below are in millimetres.
"""
import bpy, bmesh, math, os, sys, json, struct, time
import numpy as np
from mathutils import Vector, Matrix
from math import radians, sin, cos, tan, atan2, sqrt, pi

T0 = time.time()
MM = 0.001
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT_GLB = os.path.join(ROOT, "game", "assets", "models", "weapons", "p38.glb")
PREV_DIR = os.path.join(HERE, "previews")
TEX_DIR = os.path.join(HERE, "out", "p38_tex")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def _flag(n): return n in argv
def _opt(n, d):
    return type(d)(argv[argv.index(n) + 1]) if n in argv else d
BAKE = not _flag("--no-bake")
RES = _opt("--res", 4096)
SAMPLES = _opt("--samples", 64)
PREVIEWS = not _flag("--no-previews")
FORCE_CPU = _flag("--cpu")

def log(*a):
    print(f"[p38 {time.time()-T0:7.1f}s]", *a, flush=True)

# ----------------------------------------------------------------------------------------------
# generic helpers
# ----------------------------------------------------------------------------------------------
def V(*a):
    return Vector(a[0]) if len(a) == 1 else Vector(a)

def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob

def obj_from_bm(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))

def apply_mods(ob):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    for m in list(ob.modifiers):
        ob.modifiers.remove(m)
    ob.data = me
    nm = old.name
    if old.users == 0:
        bpy.data.meshes.remove(old)
    me.name = nm

def clean_pts(pts, eps=1e-5):
    out = []
    for p in pts:
        if not out or (Vector(p) - Vector(out[-1])).length > eps:
            out.append(tuple(p))
    if len(out) > 2 and (Vector(out[0]) - Vector(out[-1])).length <= eps:
        out.pop()
    return out

def rounded_poly(pts, radii, seg=6):
    """Fillet each corner of a closed 2D polygon. radii: float or per-vertex list (mm)."""
    n = len(pts)
    out = []
    for i in range(n):
        P = Vector(pts[i]); A = Vector(pts[i - 1]); B = Vector(pts[(i + 1) % n])
        r = radii[i] if isinstance(radii, (list, tuple)) else radii
        if r <= 0:
            out.append(tuple(P)); continue
        u = (A - P); v = (B - P)
        if u.length < 1e-9 or v.length < 1e-9:
            out.append(tuple(P)); continue
        u.normalize(); v.normalize()
        ang = math.acos(max(-1.0, min(1.0, u.dot(v))))
        if ang < 1e-3 or ang > pi - 1e-3:
            out.append(tuple(P)); continue
        t = r / tan(ang / 2)
        t = min(t, (A - P).length * 0.48, (B - P).length * 0.48)
        re = t * tan(ang / 2)
        T1 = P + u * t; T2 = P + v * t
        C = P + (u + v).normalized() * (re / sin(ang / 2))
        a1 = atan2(T1.y - C.y, T1.x - C.x); a2 = atan2(T2.y - C.y, T2.x - C.x)
        da = a2 - a1
        while da > pi: da -= 2 * pi
        while da < -pi: da += 2 * pi
        for k in range(seg + 1):
            a = a1 + da * k / seg
            out.append((C.x + re * cos(a), C.y + re * sin(a)))
    return clean_pts(out)

def rrect(u0, v0, u1, v1, r, seg=6):
    rr = r if isinstance(r, (list, tuple)) else [r] * 4
    return rounded_poly([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], rr, seg)

def catmull(pts, n=8):
    P = [Vector(p) for p in pts]
    out = []
    for i in range(len(P) - 1):
        p0 = P[i - 1] if i > 0 else P[i] * 2 - P[i + 1]
        p1 = P[i]; p2 = P[i + 1]
        p3 = P[i + 2] if i + 2 < len(P) else P[i + 1] * 2 - P[i]
        for k in range(n):
            t = k / n; t2 = t * t; t3 = t2 * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    return out

def band(center, half, n=8, cap_end=False, cap_seg=6):
    """Closed polygon of a thick 2D stroke along a Catmull-Rom centre line. half: float or f(t)."""
    C = catmull(center, n)
    m = len(C)
    L, R = [], []
    for i in range(m):
        a = C[max(i - 1, 0)]; b = C[min(i + 1, m - 1)]
        t = (b - a).normalized(); nr = Vector((-t.y, t.x))
        h = half(i / (m - 1)) if callable(half) else half
        L.append(C[i] + nr * h); R.append(C[i] - nr * h)
    pts = [tuple(p) for p in L]
    if cap_end:
        t = (C[-1] - C[-2]).normalized(); nr = Vector((-t.y, t.x))
        h = half(1.0) if callable(half) else half
        for k in range(1, cap_seg):
            a = pi * k / cap_seg
            pts.append(tuple(C[-1] + nr * h * cos(a) + t * h * sin(a)))
    pts += [tuple(p) for p in reversed(R)]
    return clean_pts(pts)

def extrude_section(name, pts, origin, U, Vv, W, w0, w1):
    """Prism: 2D section pts (u,v) placed at origin + U*u + V*v, extruded along W from w0 to w1 (mm)."""
    pts = clean_pts(pts)
    O = Vector(origin); U = Vector(U); Vv = Vector(Vv); W = Vector(W)
    bm = bmesh.new()
    r0 = [bm.verts.new((O + U * u + Vv * v + W * w0) * MM) for u, v in pts]
    r1 = [bm.verts.new((O + U * u + Vv * v + W * w1) * MM) for u, v in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new(r0)
    bm.faces.new(list(reversed(r1)))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return obj_from_bm(name, bm)

AX = Vector((1, 0, 0)); AY = Vector((0, 1, 0)); AZ = Vector((0, 0, 1))

def prism_x(name, pts_yz, x0, x1):
    return extrude_section(name, pts_yz, (0, 0, 0), AY, AZ, AX, x0, x1)

def prism_y(name, pts_xz, y0, y1):
    return extrude_section(name, pts_xz, (0, 0, 0), AX, AZ, AY, y0, y1)

def lathe_y(name, prof, segs=48, cx=0.0, cz=0.0, closed=True):
    """Revolve a profile of (radius, y) around a Y-parallel axis through (cx, cz)."""
    bm = bmesh.new()
    rings = []
    for r, y in prof:
        rings.append([bm.verts.new(((cx + r * cos(2 * pi * k / segs)) * MM, y * MM,
                                    (cz + r * sin(2 * pi * k / segs)) * MM)) for k in range(segs)])
    n = len(rings)
    for i in (range(n) if closed else range(n - 1)):
        i2 = (i + 1) % n
        for k in range(segs):
            k2 = (k + 1) % segs
            bm.faces.new((rings[i][k], rings[i][k2], rings[i2][k2], rings[i2][k]))
    if not closed:
        bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return obj_from_bm(name, bm)

def cylinder(name, p0, p1, r, segs=32):
    p0 = Vector(p0); p1 = Vector(p1)
    d = p1 - p0
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r * MM, radius2=r * MM,
                          depth=d.length * MM)
    ob = obj_from_bm(name, bm)
    rot = AZ.rotation_difference(d.normalized()).to_matrix().to_4x4()
    ob.matrix_world = Matrix.Translation(((p0 + p1) / 2) * MM) @ rot
    bake_xform(ob)
    return ob

def box(name, mn, mx):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    ob = obj_from_bm(name, bm)
    mn = Vector(mn); mx = Vector(mx)
    sz = (mx - mn) * MM
    ob.matrix_world = Matrix.Translation((mn + mx) / 2 * MM) @ Matrix.Diagonal((sz.x, sz.y, sz.z, 1.0))
    bake_xform(ob)
    return ob

def bake_xform(ob):
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)

def booleans(target, cutters, op='DIFFERENCE', solver='EXACT'):
    for c in cutters:
        m = target.modifiers.new("bool", 'BOOLEAN')
        m.operation = op; m.solver = solver; m.object = c
    apply_mods(target)
    for c in cutters:
        bpy.data.objects.remove(c, do_unlink=True)

def bevel(ob, width, segs=2, angle=30, profile=0.5):
    b = ob.modifiers.new("bevel", 'BEVEL')
    b.width = width * MM; b.segments = segs; b.limit_method = 'ANGLE'
    b.angle_limit = radians(angle); b.profile = profile; b.use_clamp_overlap = True
    apply_mods(ob)

def shade(ob, angle=38, weighted=True):
    me = ob.data
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.set_sharp_from_angle(angle=radians(angle))
    if weighted:
        w = ob.modifiers.new("wn", 'WEIGHTED_NORMAL')
        w.keep_sharp = True; w.weight = 50; w.mode = 'FACE_AREA'
        apply_mods(ob)

def join(objs, name=None):
    objs = [o for o in objs if o is not None]
    base = objs[0]
    if len(objs) > 1:
        with bpy.context.temp_override(active_object=base, object=base, selected_objects=objs,
                                       selected_editable_objects=objs):
            bpy.ops.object.join()
    if name:
        base.name = name; base.data.name = name
    return base

def set_origin(ob, p_mm):
    p = Vector(p_mm) * MM
    ob.data.transform(Matrix.Translation(-p))
    ob.location = p

def assign(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.material_index = 0

def text_mesh(name, body, size, depth):
    cu = bpy.data.curves.new(name + "_cu", 'FONT')
    cu.body = body; cu.size = size * MM; cu.extrude = depth * MM / 2
    cu.align_x = 'LEFT'; cu.align_y = 'CENTER'; cu.resolution_u = 3
    tmp = link(bpy.data.objects.new(name + "_tmp", cu))
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.curves.remove(cu)
    return link(bpy.data.objects.new(name, me))

# text lying on the LEFT (-X) face, reading muzzle -> rear: local x -> -Y, local y -> +Z, local z -> -X
R_LEFT = Matrix(((0, 0, -1), (-1, 0, 0), (0, 1, 0))).to_4x4()

def engrave(target, items, depth=0.45):
    """items: list of (text, size_mm, x_face, y_start, z_center)."""
    cutters = []
    for i, (txt, size, xf, y0, zc) in enumerate(items):
        t = text_mesh(f"eng{i}", txt, size, depth)
        t.matrix_world = Matrix.Translation(Vector((xf, y0, zc)) * MM) @ R_LEFT
        bake_xform(t)
        cutters.append(t)
    booleans(target, cutters)

def torus(name, C, a, b, R, r, su=40, sv=12):
    C = Vector(C); a = Vector(a).normalized(); b = Vector(b).normalized(); n = a.cross(b).normalized()
    bm = bmesh.new()
    rings = []
    for i in range(su):
        u = 2 * pi * i / su
        d = a * cos(u) + b * sin(u)
        rings.append([bm.verts.new((C + d * (R + r * cos(2 * pi * j / sv)) + n * r * sin(2 * pi * j / sv)) * MM)
                      for j in range(sv)])
    for i in range(su):
        for j in range(sv):
            bm.faces.new((rings[i][j], rings[(i + 1) % su][j], rings[(i + 1) % su][(j + 1) % sv],
                          rings[i][(j + 1) % sv]))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return obj_from_bm(name, bm)

def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)

# ----------------------------------------------------------------------------------------------
# grip frame: the grip is raked 16 deg; GP(s, fo, xo) = point at distance s down the grip axis,
# fo toward the front strap, xo toward +X (right).
# ----------------------------------------------------------------------------------------------
RAKE = radians(16.0)
G = Vector((0, -sin(RAKE), -cos(RAKE)))
F = Vector((0, cos(RAKE), -sin(RAKE)))
P0 = Vector((0, -45.0, -45.0))

def GP(s, fo, xo=0.0):
    return P0 + G * s + F * fo + AX * xo

def grip_prism(name, pts_fx, s0, s1):
    return extrude_section(name, pts_fx, P0, F, AX, G, s0, s1)

# ----------------------------------------------------------------------------------------------
# MATERIALS (procedural; baked later)
# ----------------------------------------------------------------------------------------------
class NB:
    def __init__(self, mat):
        self.nt = mat.node_tree; self.N = self.nt.nodes; self.L = self.nt.links
    def new(self, t, **kw):
        nd = self.N.new(t)
        for k, v in kw.items():
            setattr(nd, k, v)
        return nd
    def put(self, sock, val):
        if val is None: return
        if isinstance(val, bpy.types.NodeSocket):
            self.L.new(val, sock)
        else:
            sock.default_value = val
    def math(self, op, a, b=None, c=None, clamp=False):
        nd = self.new('ShaderNodeMath', operation=op, use_clamp=clamp)
        for i, x in enumerate((a, b, c)):
            self.put(nd.inputs[i], x)
        return nd.outputs[0]
    def vmath(self, op, a, b=None, scale=None):
        nd = self.new('ShaderNodeVectorMath', operation=op)
        self.put(nd.inputs[0], a)
        if b is not None: self.put(nd.inputs[1], b)
        if scale is not None: self.put(nd.inputs[3], scale)
        return nd.outputs[1] if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else nd.outputs[0]
    def mix(self, t, a, b):
        nd = self.new('ShaderNodeMix', data_type='RGBA', clamp_factor=True)
        ins = {s.identifier: s for s in nd.inputs}
        self.put(ins['Factor_Float'], t); self.put(ins['A_Color'], a); self.put(ins['B_Color'], b)
        return {s.identifier: s for s in nd.outputs}['Result_Color']
    def mixf(self, t, a, b):
        nd = self.new('ShaderNodeMix', data_type='FLOAT', clamp_factor=True)
        ins = {s.identifier: s for s in nd.inputs}
        self.put(ins['Factor_Float'], t); self.put(ins['A_Float'], a); self.put(ins['B_Float'], b)
        return {s.identifier: s for s in nd.outputs}['Result_Float']
    def maprange(self, x, a, b, c=0.0, d=1.0, smooth=False):
        nd = self.new('ShaderNodeMapRange', clamp=True)
        if smooth: nd.interpolation_type = 'SMOOTHSTEP'
        self.put(nd.inputs[0], x); nd.inputs[1].default_value = a; nd.inputs[2].default_value = b
        nd.inputs[3].default_value = c; nd.inputs[4].default_value = d
        return nd.outputs[0]
    def noise(self, vec, scale, detail=4.0, rough=0.55, dist=0.0, out='Fac'):
        nd = self.new('ShaderNodeTexNoise')
        self.put(nd.inputs['Vector'], vec); nd.inputs['Scale'].default_value = scale
        nd.inputs['Detail'].default_value = detail; nd.inputs['Roughness'].default_value = rough
        nd.inputs['Distortion'].default_value = dist
        return nd.outputs[out]
    def voronoi(self, vec, scale, rand=1.0, out='Distance', feature='F1'):
        nd = self.new('ShaderNodeTexVoronoi', feature=feature)
        self.put(nd.inputs['Vector'], vec); nd.inputs['Scale'].default_value = scale
        nd.inputs['Randomness'].default_value = rand
        return nd.outputs[out]
    def mapping(self, vec, scale=(1, 1, 1), loc=(0, 0, 0)):
        nd = self.new('ShaderNodeMapping')
        self.put(nd.inputs['Vector'], vec)
        nd.inputs['Scale'].default_value = scale; nd.inputs['Location'].default_value = loc
        return nd.outputs[0]
    def value(self, v):
        nd = self.new('ShaderNodeValue'); nd.outputs[0].default_value = v
        return nd.outputs[0]
    def rgb(self, c):
        nd = self.new('ShaderNodeRGB'); nd.outputs[0].default_value = (c[0], c[1], c[2], 1.0)
        return nd.outputs[0]
    def attr(self, name):
        nd = self.new('ShaderNodeAttribute', attribute_name=name, attribute_type='GEOMETRY')
        return nd.outputs['Fac']
    def bump(self, height, dist, strength=1.0, normal=None):
        nd = self.new('ShaderNodeBump')
        self.put(nd.inputs['Height'], height); nd.inputs['Distance'].default_value = dist
        nd.inputs['Strength'].default_value = strength
        if normal is not None: self.put(nd.inputs['Normal'], normal)
        return nd.outputs['Normal']


def new_material(name):
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except Exception:
        pass
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return mat


def finish_proc(mat, nb, color, rough, metal, normal):
    """Wire a procedural material: Principled for viewing/normal bake + emission + bake image node."""
    out = nb.new('ShaderNodeOutputMaterial')
    bsdf = nb.new('ShaderNodeBsdfPrincipled')
    nb.put(bsdf.inputs['Base Color'], color); nb.put(bsdf.inputs['Roughness'], rough)
    nb.put(bsdf.inputs['Metallic'], metal)
    if normal is not None: nb.put(bsdf.inputs['Normal'], normal)
    nb.L.new(bsdf.outputs[0], out.inputs['Surface'])
    emit = nb.new('ShaderNodeEmission')
    img = nb.new('ShaderNodeTexImage')
    mat["_sock"] = 0
    return dict(mat=mat, nb=nb, out=out, bsdf=bsdf, emit=emit, img=img,
                sock=dict(color=color, rough=rough, metal=metal))


def mat_steel(name="m_steel", magazine=False):
    mat = new_material(name); nb = NB(mat)
    tc = nb.new('ShaderNodeTexCoord').outputs['Object']
    geo = nb.new('ShaderNodeNewGeometry')
    bev = nb.new('ShaderNodeBevel', samples=8); bev.inputs['Radius'].default_value = 0.0008
    edge = nb.maprange(nb.math('SUBTRACT', 1.0, nb.vmath('DOT_PRODUCT', bev.outputs[0], geo.outputs['Normal'])),
                       0.002, 0.07)
    n_big = nb.noise(tc, 70.0, 6.0, 0.62)
    n_mid = nb.noise(tc, 260.0, 5.0, 0.6)
    n_fine = nb.noise(tc, 1600.0, 3.0, 0.5)
    # holster wear: muzzle end, slide front, frame front, trigger-guard front, high spots
    sep = nb.new('ShaderNodeSeparateXYZ'); nb.put(sep.inputs[0], tc)
    zone_front = nb.maprange(sep.outputs['Y'], 0.085, 0.130)
    wear_e = nb.math('MULTIPLY', edge, nb.maprange(n_big, 0.38, 0.62, 0.15, 1.3))
    wear_z = nb.math('MULTIPLY', nb.math('MULTIPLY', zone_front, nb.maprange(n_mid, 0.45, 0.65)), 0.55)
    wear = nb.math('ADD', wear_e, wear_z, clamp=True)
    wear = nb.maprange(wear, 0.35, 0.75, smooth=True)
    # fine longitudinal polishing marks / scratches
    scr = nb.noise(nb.mapping(tc, (2800.0, 40.0, 2800.0)), 1.0, 2.0, 0.5)
    scr = nb.math('MULTIPLY', nb.maprange(scr, 0.66, 0.74), nb.maprange(n_big, 0.45, 0.7))
    blue_a = nb.rgb((0.0085, 0.0098, 0.0135))
    blue_b = nb.rgb((0.0145, 0.0150, 0.0185))
    if magazine:
        blue_a = nb.rgb((0.011, 0.011, 0.012)); blue_b = nb.rgb((0.017, 0.017, 0.018))
    blue = nb.mix(n_mid, blue_a, blue_b)
    bare = nb.mix(n_fine, nb.rgb((0.36, 0.355, 0.35)), nb.rgb((0.47, 0.46, 0.45)))
    col = nb.mix(wear, blue, bare)
    col = nb.mix(nb.math('MULTIPLY', scr, 0.35), col, nb.rgb((0.20, 0.20, 0.21)))
    rough = nb.math('ADD', 0.30, nb.math('MULTIPLY', n_mid, 0.14))
    rough = nb.mixf(wear, rough, 0.21)
    rough = nb.mixf(nb.math('MULTIPLY', scr, 0.6), rough, 0.36)
    h = nb.math('ADD', nb.math('MULTIPLY', n_fine, 0.35), nb.math('MULTIPLY', scr, 0.5))
    nrm = nb.bump(h, 0.00003, 1.0)
    return finish_proc(mat, nb, col, rough, nb.value(1.0), nrm)


def mat_bakelite(name="m_bakelite"):
    mat = new_material(name); nb = NB(mat)
    tc = nb.new('ShaderNodeTexCoord').outputs['Object']
    geo = nb.new('ShaderNodeNewGeometry')
    # horizontal ribs: perpendicular to the grip axis, pitch 1.45 mm
    ph = nb.vmath('DOT_PRODUCT', tc, (G.x, G.y, G.z))
    ph = nb.math('MULTIPLY', ph, 2 * pi / 0.00145)
    rib = nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', ph), 0.5), 0.5)
    rib = nb.maprange(rib, 0.15, 0.85, smooth=True)
    # only on the side faces (|normal.x| high) so edges stay smooth
    sepn = nb.new('ShaderNodeSeparateXYZ'); nb.put(sepn.inputs[0], geo.outputs['Normal'])
    side = nb.maprange(nb.math('ABSOLUTE', sepn.outputs['X']), 0.55, 0.85)
    rib = nb.math('MULTIPLY', rib, side)
    bev = nb.new('ShaderNodeBevel', samples=8); bev.inputs['Radius'].default_value = 0.0007
    edge = nb.maprange(nb.math('SUBTRACT', 1.0, nb.vmath('DOT_PRODUCT', bev.outputs[0], geo.outputs['Normal'])),
                       0.004, 0.08)
    n_mot = nb.noise(tc, 90.0, 6.0, 0.7, dist=0.4)
    n_fine = nb.noise(tc, 1400.0, 3.0, 0.5)
    base = nb.mix(n_mot, nb.rgb((0.020, 0.0105, 0.0055)), nb.rgb((0.048, 0.022, 0.0095)))
    worn = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', rib, 0.45), edge), nb.maprange(n_mot, 0.35, 0.7))
    worn = nb.maprange(worn, 0.25, 0.9)
    col = nb.mix(worn, base, nb.rgb((0.075, 0.036, 0.016)))
    rough = nb.mixf(worn, nb.math('ADD', 0.42, nb.math('MULTIPLY', n_fine, 0.12)), 0.27)
    h = nb.math('ADD', rib, nb.math('MULTIPLY', n_fine, 0.04))
    nrm = nb.bump(h, 0.00028, 1.0)
    return finish_proc(mat, nb, col, rough, nb.value(0.0), nrm)


def mat_brass(name, copper=False):
    mat = new_material(name); nb = NB(mat)
    tc = nb.new('ShaderNodeTexCoord').outputs['Object']
    n = nb.noise(tc, 500.0, 4.0, 0.55)
    if copper:
        col = nb.mix(n, nb.rgb((0.50, 0.26, 0.15)), nb.rgb((0.62, 0.33, 0.20)))
    else:
        col = nb.mix(n, nb.rgb((0.56, 0.40, 0.17)), nb.rgb((0.68, 0.50, 0.22)))
    rough = nb.math('ADD', 0.26, nb.math('MULTIPLY', n, 0.15))
    nrm = nb.bump(nb.noise(tc, 2500.0, 2.0), 0.00001)
    return finish_proc(mat, nb, col, rough, nb.value(1.0), nrm)


def mat_glove(name="m_glove"):
    mat = new_material(name); nb = NB(mat)
    tc = nb.new('ShaderNodeTexCoord').outputs['Object']
    geo = nb.new('ShaderNodeNewGeometry')
    convex = nb.maprange(geo.outputs['Pointiness'], 0.505, 0.56, smooth=True)
    n_big = nb.noise(tc, 45.0, 5.0, 0.6)
    n_mid = nb.noise(tc, 220.0, 5.0, 0.6)
    grain = nb.voronoi(tc, 1500.0, 1.0)
    grain = nb.maprange(grain, 0.0, 0.9)
    pores = nb.noise(tc, 4200.0, 2.0, 0.5)
    seam_d = nb.attr("seam_d"); along = nb.attr("seam_along")
    crease_w = nb.attr("crease_w"); crease_d = nb.attr("crease_d")
    pts_d = nb.attr("points_d"); pts_al = nb.attr("points_along"); hem_d = nb.attr("hem_d")
    # side seams: a groove plus a row of stitches 1.3 mm beside it
    groove = nb.math('SUBTRACT', 1.0, nb.maprange(seam_d, 0.18, 0.62, smooth=True))
    stitch_win = nb.math('MULTIPLY', nb.maprange(seam_d, 0.85, 1.05), nb.math('SUBTRACT', 1.0, nb.maprange(seam_d, 1.55, 1.75)))
    dash = nb.math('LESS_THAN', nb.math('FRACT', nb.math('DIVIDE', along, 2.7)), 0.62)
    stitch = nb.math('MULTIPLY', stitch_win, dash)
    # "points": three raised stitched ridges on the back of the hand
    ridge = nb.math('SUBTRACT', 1.0, nb.maprange(pts_d, 0.25, 0.95, smooth=True))
    p_st_win = nb.math('MULTIPLY', nb.maprange(pts_d, 1.15, 1.35), nb.math('SUBTRACT', 1.0, nb.maprange(pts_d, 1.8, 2.0)))
    p_dash = nb.math('LESS_THAN', nb.math('FRACT', nb.math('DIVIDE', pts_al, 2.4)), 0.6)
    p_stitch = nb.math('MULTIPLY', p_st_win, p_dash)
    hem = nb.math('SUBTRACT', 1.0, nb.maprange(hem_d, 0.3, 0.8, smooth=True))
    hem_st = nb.math('MULTIPLY', nb.maprange(hem_d, 2.0, 2.2), nb.math('SUBTRACT', 1.0, nb.maprange(hem_d, 2.7, 2.9)))
    # creases near joints: rings around the finger axis, broken up with noise
    wr = nb.math('SINE', nb.math('ADD', nb.math('MULTIPLY', crease_d, 2 * pi / 1.9), nb.math('MULTIPLY', n_mid, 9.0)))
    wr = nb.maprange(wr, 0.2, 1.0, smooth=True)
    crease = nb.math('MULTIPLY', nb.math('MULTIPLY', wr, crease_w), nb.maprange(n_mid, 0.3, 0.6, 0.35, 1.0))
    # colour
    base = nb.mix(n_big, nb.rgb((0.028, 0.0175, 0.0115)), nb.rgb((0.045, 0.028, 0.018)))
    base = nb.mix(nb.math('MULTIPLY', grain, 0.35), base, nb.rgb((0.020, 0.013, 0.009)))
    worn = nb.math('MULTIPLY', convex, nb.maprange(n_mid, 0.35, 0.7, 0.3, 1.0))
    col = nb.mix(worn, base, nb.rgb((0.085, 0.060, 0.046)))
    col = nb.mix(nb.math('MULTIPLY', nb.math('ADD', groove, crease), 0.7), col, nb.rgb((0.012, 0.008, 0.006)))
    thread = nb.math('MAXIMUM', nb.math('MAXIMUM', stitch, p_stitch), hem_st)
    col = nb.mix(nb.math('MULTIPLY', thread, 0.85), col, nb.rgb((0.030, 0.022, 0.017)))
    rough = nb.math('ADD', 0.48, nb.math('MULTIPLY', grain, 0.1))
    rough = nb.mixf(worn, rough, 0.36)
    rough = nb.mixf(nb.math('ADD', groove, crease, clamp=True), rough, 0.62)
    rough = nb.mixf(thread, rough, 0.7)
    h = nb.math('MULTIPLY', grain, 0.12)
    h = nb.math('ADD', h, nb.math('MULTIPLY', pores, 0.05))
    h = nb.math('SUBTRACT', h, nb.math('MULTIPLY', groove, 0.9))
    h = nb.math('SUBTRACT', h, nb.math('MULTIPLY', hem, 0.7))
    h = nb.math('SUBTRACT', h, nb.math('MULTIPLY', crease, 0.55))
    h = nb.math('ADD', h, nb.math('MULTIPLY', ridge, 0.35))
    h = nb.math('ADD', h, nb.math('MULTIPLY', thread, 0.35))
    nrm = nb.bump(h, 0.00032, 1.0)
    return finish_proc(mat, nb, col, rough, nb.value(0.0), nrm)


def mat_wool(name="m_wool"):
    mat = new_material(name); nb = NB(mat)
    tc = nb.new('ShaderNodeTexCoord').outputs['Object']
    n_big = nb.noise(tc, 30.0, 6.0, 0.6)
    heather = nb.noise(tc, 900.0, 6.0, 0.7)
    fib = nb.noise(nb.mapping(tc, (5200.0, 5200.0, 900.0)), 1.0, 6.0, 0.75)
    # twill weave: diagonal ribs ~0.9 mm
    tw = nb.new('ShaderNodeTexWave', wave_type='BANDS', bands_direction='DIAGONAL')
    nb.put(tw.inputs['Vector'], tc); tw.inputs['Scale'].default_value = 650.0
    tw.inputs['Distortion'].default_value = 2.0; tw.inputs['Detail'].default_value = 1.0
    weave = tw.outputs['Fac']
    base = nb.mix(heather, nb.rgb((0.022, 0.022, 0.024)), nb.rgb((0.050, 0.046, 0.043)))
    base = nb.mix(nb.math('MULTIPLY', n_big, 0.5), base, nb.rgb((0.030, 0.028, 0.027)))
    col = nb.mix(nb.math('MULTIPLY', fib, 0.25), base, nb.rgb((0.07, 0.066, 0.062)))
    rough = nb.math('ADD', 0.88, nb.math('MULTIPLY', fib, 0.1))
    h = nb.math('ADD', nb.math('MULTIPLY', weave, 0.5), nb.math('MULTIPLY', fib, 0.6))
    nrm = nb.bump(h, 0.0004, 0.8)
    return finish_proc(mat, nb, col, rough, nb.value(0.0), nrm)

# ----------------------------------------------------------------------------------------------
# GUN GEOMETRY
# ----------------------------------------------------------------------------------------------
MUZZLE_Y = 131.0
BREECH_Y = MUZZLE_Y - 125.0      # 6.0 : barrel is 125 mm long
SLIDE_REAR = -74.0
SLIDE_FRONT = 127.5
SIGHT_Z = 16.5                   # top of rear notch == top of front blade

def build_barrel(mats):
    prof = [  # (radius, y) closed loop: outside rear->muzzle, then the bore back
        (6.0, BREECH_Y), (8.5, BREECH_Y + 0.6), (8.5, 34.0), (8.1, 37.0), (7.2, 44.0),
        (7.2, MUZZLE_Y - 1.2), (6.9, MUZZLE_Y), (5.2, MUZZLE_Y), (4.55, MUZZLE_Y - 0.6),
        (4.45, BREECH_Y + 9.0), (5.1, BREECH_Y + 2.0), (5.3, BREECH_Y),
    ]
    b = lathe_y("Barrel", prof, segs=64)
    # locking-block lug underneath the chamber (mostly hidden)
    lug = prism_y("lug", rrect(-6.0, -10.8, 6.0, -5.5, 1.0), BREECH_Y + 6, BREECH_Y + 26)
    shade(b, 40, weighted=False)
    bevel(lug, 0.4, 2); shade(lug, 40)
    b = join([b, lug], "Barrel")
    assign(b, mats['steel'])
    return b


def build_slide(mats):
    sec = rrect(-12.5, -10.5, 12.5, 13.0, [0.8, 0.8, 6.5, 6.5], seg=8)
    s = prism_y("Slide", sec, SLIDE_REAR, SLIDE_FRONT)
    cutters = [
        box("c_top", (-20, BREECH_Y - 1.0, 3.0), (20, 115.5, 40)),          # open top over the barrel
        box("c_ring", (-20, 115.5, 9.8), (20, 140, 40)),                     # low front bridge
        box("c_eject", (-20, BREECH_Y - 1.0, -3.5), (-7.0, 33.5, 40)),       # ejection cut, LEFT side
        cylinder("c_ch1", (0, BREECH_Y - 1.0, 0), (0, 46, 0), 8.9, 48),       # chamber clearance
        cylinder("c_ch2", (0, BREECH_Y - 1.0, 0), (0, 140, 0), 7.6, 48),      # barrel channel
        box("c_under", (-9.5, SLIDE_REAR - 1, -12.0), (9.5, 93.0, -8.3)),    # rides on frame rails
        cylinder("c_fp", (0, SLIDE_REAR - 2, 0), (0, SLIDE_REAR + 3, 0), 1.6, 16),  # firing-pin hole
    ]
    nose = box("c_nose", (-20, 115.0, 0.0), (20, 141, 30))
    booleans(nose, [cylinder("c_nosecyl", (0, 113, 0), (0, 143, 0), 12.6, 72)])
    cutters.append(nose)
    booleans(s, cutters)
    bevel(s, 0.55, 2, 32)
    # markings on the left flank: serial, model, maker code + year
    engrave(s, [
        ("4127b", 3.1, -12.5, 110.0, -3.9),
        ("P.38", 3.7, -12.5, 88.0, -3.9),
        ("ac", 3.0, -12.5, 66.0, -1.9),
        ("43", 3.0, -12.5, 66.0, -6.6),
    ])
    shade(s, 38)
    # rear sight block with U notch
    rs = prism_x("rsight", rounded_poly([(SLIDE_REAR + 1.0, 10.0), (SLIDE_REAR + 11.5, 10.0), (SLIDE_REAR + 11.5, 13.2),
                                         (SLIDE_REAR + 8.0, SIGHT_Z), (SLIDE_REAR + 1.0, SIGHT_Z)],
                                        [0, 0, 1.5, 1.0, 0.4], 4), -5.6, 5.6)
    notch = prism_y("notch", rounded_poly([(-1.3, 30.0), (-1.3, SIGHT_Z - 1.55), (1.3, SIGHT_Z - 1.55), (1.3, 30.0)],
                                          [0, 0.5, 0.5, 0], 4), SLIDE_REAR - 5, SLIDE_REAR + 20)
    booleans(rs, [notch])
    bevel(rs, 0.35, 2); shade(rs)
    # front sight: ramp + blade on the front bridge
    ramp = prism_x("framp", rounded_poly([(116.2, 8.5), (127.0, 8.5), (126.0, 11.2), (118.0, 11.4)], [0, 0.6, 1.2, 1.2], 4),
                   -1.9, 1.9)
    blade = prism_x("fblade", rounded_poly([(119.0, 10.5), (125.2, 10.5), (125.2, 12.0), (122.6, SIGHT_Z), (119.4, SIGHT_Z)],
                                           [0, 0, 1.5, 0.5, 0.3], 4), -1.15, 1.15)
    bevel(ramp, 0.4, 2); shade(ramp); bevel(blade, 0.2, 2); shade(blade)
    # loaded-chamber indicator pin, protruding from the rear face above the hammer
    lci = cylinder("lci", (0, SLIDE_REAR - 2.2, 9.6), (0, SLIDE_REAR + 4, 9.6), 1.1, 16)
    shade(lci, 40, False)
    # safety drum end on the right flank
    drum = cylinder("drum", (12.0, -62.0, 4.0), (12.95, -62.0, 4.0), 3.9, 32)
    bevel(drum, 0.3, 2); shade(drum, 40)
    s = join([s, rs, ramp, blade, lci, drum], "Slide")
    assign(s, mats['steel'])
    return s


def build_decocker(mats):
    pv = (-62.0, 4.0)     # (y, z) pivot on the slide flank
    ang = radians(18.0)   # "fire" position: paddle points rearward, tilted slightly up
    loc = [(3.6, 3.7), (-6.0, 3.6), (-12.4, 2.6), (-14.0, 0.2), (-12.6, -2.4), (-5.0, -3.4), (2.6, -3.8), (4.2, -1.0)]
    pts = []
    for y, z in loc:
        yy = y * cos(ang) + z * sin(ang)      # rotate by -ang: the rear-pointing paddle tilts upward
        zz = -y * sin(ang) + z * cos(ang)
        pts.append((pv[0] + yy, pv[1] + zz))
    pts = rounded_poly(pts, [2.5, 0.5, 2.0, 2.2, 2.0, 0.5, 2.5, 2.5], 4)
    d = prism_x("Decocker", pts, -15.0, -12.35)
    boss = cylinder("dboss", (-15.4, pv[0], pv[1]), (-12.3, pv[0], pv[1]), 3.6, 32)
    bevel(d, 0.45, 2); shade(d); bevel(boss, 0.4, 2); shade(boss)
    d = join([d, boss], "Decocker")
    set_origin(d, (-13.7, pv[0], pv[1]))
    assign(d, mats['steel'])
    return d


HAMMER_PIVOT = (-78.0, -15.0)
TRIGGER_PIVOT = (6.0, -16.0)

def build_hammer(mats):
    pts = [(-74.3, -9.0), (-74.3, 5.0), (-75.2, 7.6), (-78.2, 8.9), (-81.8, 8.4), (-84.8, 6.1), (-86.6, 2.9),
           (-86.4, 0.2), (-84.6, -1.6), (-82.3, -2.5), (-81.4, -5.6), (-81.6, -11.0), (-81.0, -17.0),
           (-78.0, -20.6), (-75.0, -19.2), (-73.8, -14.0)]
    rad = [0.3, 1.0, 1.8, 2.5, 2.5, 2.0, 1.4, 1.2, 1.5, 1.2, 1.5, 0.5, 2.0, 3.0, 2.0, 0.5]
    h = prism_x("Hammer", rounded_poly(pts, rad, 4), -3.6, 3.6)
    # chequered grip grooves on the spur
    cuts = []
    for k, (y, z) in enumerate([(-79.6, 8.95), (-81.5, 8.55), (-83.3, 7.55), (-84.9, 6.05), (-86.0, 4.2), (-86.75, 2.3)]):
        cuts.append(cylinder(f"hg{k}", (-5, y, z), (5, y, z), 0.5, 10))
    booleans(h, cuts)
    bevel(h, 0.45, 2, 32); shade(h)
    pin = cylinder("hpin", (-3.8, HAMMER_PIVOT[0], HAMMER_PIVOT[1]), (3.8, HAMMER_PIVOT[0], HAMMER_PIVOT[1]), 2.0, 24)
    h = join([h, pin], "Hammer")
    set_origin(h, (0.0, HAMMER_PIVOT[0], HAMMER_PIVOT[1]))
    assign(h, mats['steel'])
    return h


def build_trigger(mats):
    center = [(6.4, -13.0), (6.0, -20.0), (4.9, -26.5), (3.0, -32.3), (0.6, -36.9), (-1.4, -39.3)]
    pts = band(center, lambda t: 2.7 - 0.7 * t, n=8, cap_end=True)
    t = prism_x("Trigger", pts, -3.4, 3.4)
    bevel(t, 1.1, 3, 30); shade(t, 45)
    t = join([t], "Trigger")
    set_origin(t, (0.0, TRIGGER_PIVOT[0], TRIGGER_PIVOT[1]))
    assign(t, mats['steel'])
    return t


def build_frame(mats):
    fs = GP(-12, 23)          # front strap at the top of the grip
    fs0 = GP(0, 23)
    bs = GP(-5, -23)          # back strap below the hammer hump
    slab_pts = [(92.5, -10.5), (93.6, -11.8), (93.6, -19.6), (91.0, -21.5), (46.0, -21.5), (-13.0, -21.5),
                (-18.2, -27.0), (fs.y, fs.z), (-45.0, -52.0), (-62.0, -45.0), (bs.y, bs.z), (-70.5, -31.5),
                (-79.5, -26.5), (-84.0, -19.0), (-84.0, -10.5)]
    rad = [0.5, 1.0, 2.0, 1.5, 0.0, 3.5, 5.0, 0.0, 0.0, 0.0, 2.0, 4.0, 5.0, 3.0, 0.5]
    slab = prism_x("slab", rounded_poly(slab_pts, rad, 5), -10.8, 10.8)
    booleans(slab, [
        box("c_hslot", (-3.95, -88.0, -24.0), (3.95, -72.5, 2.0)),   # hammer slot
        box("c_tslot", (-3.75, -2.5, -24.0), (3.75, 10.5, -12.0)),   # trigger slot
        box("c_rail", (-9.3, -90, -11.2), (9.3, 100, -9.0)),         # rail cut under the slide
    ])
    bevel(slab, 0.6, 2, 32)
    engrave(slab, [("4127b", 2.6, -10.8, 86.0, -16.2)])
    shade(slab)
    # grip: lofted rounded box along the raked grip axis, with the magazine well opening at the bottom
    grip = grip_prism("grip", rrect(-23, -11, 23, 11, [5.0, 5.0, 5.0, 5.0], 6), -12, 74)
    mw = grip_prism("c_mw", rrect(-12.0, -5.85, 20.9, 5.85, 1.6, 4), 40, 80)
    booleans(grip, [mw])
    bevel(grip, 0.7, 2, 32); shade(grip)
    # grip panels (ribbed bakelite): wrap with front/back straps exposed
    pan = grip_prism("panels", rrect(-20.0, -16.0, 20.3, 16.0, [9.0, 10.0, 10.0, 9.0], 8), -25, 69)
    booleans(pan, [box("c_ptop", (-40, -200, -13.6), (40, 200, 60)),
                   box("c_pfront", (-40, -19.4, -70), (40, 200, 0)),
                   box("c_phump", (-40, -200, -40), (40, -59.0, 0))])
    bevel(pan, 1.3, 3, 25); shade(pan, 40)
    assign(pan, mats['bakelite'])
    screws = []
    for sx in (-1, 1):
        c = GP(30, -1.0, sx * 15.6)
        cyl = cylinder("screw", c, c + AX * sx * 1.4, 3.3, 24)
        bevel(cyl, 0.6, 3, 30); shade(cyl, 50)
        slot = box("c_slot", (c.x + sx * 0.6 - 2, c.y - 0.35, c.z - 4), (c.x + sx * 0.6 + 2, c.y + 0.35, c.z + 4))
        slot.data.transform(Matrix.Translation(-c * MM) )
        slot.data.transform(Matrix.Rotation(-RAKE, 4, 'X'))
        slot.data.transform(Matrix.Translation(c * MM))
        booleans(cyl, [slot])
        screws.append(cyl)
    # trigger guard
    tg_center = [(46.0, -19.0), (45.4, -28.0), (42.2, -36.2), (35.0, -42.6), (24.0, -46.6), (11.0, -48.1),
                 (-2.0, -47.6), (-12.0, -46.0), (-19.0, -43.4), (-24.0, -40.0)]
    tg = prism_x("tguard", band(tg_center, 2.45, 10), -4.6, 4.6)
    bevel(tg, 1.5, 3, 25); shade(tg, 45)
    # levers on the left: slide catch and takedown lever
    sc = prism_x("slidecatch", rounded_poly([(-11.5, -12.6), (6.0, -13.0), (8.6, -15.4), (6.4, -18.0), (-8.0, -17.6),
                                             (-12.0, -15.3)], [1.0, 1.2, 1.6, 1.2, 1.2, 1.4], 4), -12.2, -10.4)
    bevel(sc, 0.35, 2); shade(sc)
    tdl = prism_x("takedown", rounded_poly([(40.0, -11.8), (44.0, -14.0), (43.4, -18.4), (36.0, -19.8), (33.0, -16.5),
                                            (35.0, -12.3)], [2.0, 2.0, 1.5, 1.6, 2.2, 1.8], 4), -12.3, -10.4)
    bevel(tdl, 0.35, 2); shade(tdl)
    # pins
    pins = []
    for (y, z, r) in [(TRIGGER_PIVOT[0], TRIGGER_PIVOT[1], 1.7), (HAMMER_PIVOT[0], HAMMER_PIVOT[1], 1.9), (-9.0, -15.2, 1.4)]:
        p = cylinder("pin", (-11.15, y, z), (11.15, y, z), r, 20); shade(p, 40, False); pins.append(p)
    # heel magazine catch
    heel = grip_prism("heel", rrect(-25.2, -5.0, -19.0, 5.0, 1.2, 3), 70.0, 76.6)
    bevel(heel, 0.4, 2); shade(heel)
    # lanyard loop: stud + ring on the left side of the butt
    st = GP(70.5, -16.5, -10.9)
    stud = cylinder("stud", st, st + AX * -2.6, 2.4, 20); bevel(stud, 0.4, 2); shade(stud, 40)
    ring = torus("lanyard", st + AX * -2.9 + G * 6.2, G, F, 6.2, 1.15, 40, 12); shade(ring, 60, False)
    steel_parts = [slab, grip, tg, sc, tdl, heel, stud, ring] + screws + pins
    for o in steel_parts:
        assign(o, mats['steel'])
    fr = join(steel_parts[:1] + [pan] + steel_parts[1:], "Frame")
    return fr


def build_magazine(mats):
    body = grip_prism("magbody", rrect(-11.5, -5.4, 20.5, 5.4, 1.6, 4), -13.0, 73.2)
    bevel(body, 0.35, 2); shade(body)
    base = grip_prism("magbase", rrect(-15.2, -7.1, 22.2, 7.1, [3.0, 4.0, 4.0, 3.0], 6), 73.0, 76.3)
    notch = grip_prism("c_mn", rrect(-17, -3.0, -12.5, 3.0, 0.6, 3), 72, 77)
    booleans(base, [notch])
    bevel(base, 0.6, 2); shade(base)
    # follower lips at the top + top cartridge lying along the magazine (bullet forward)
    case = lathe_y("case", [(4.95, 0.0), (4.95, 0.9), (4.2, 1.1), (4.2, 1.7), (4.95, 2.0), (4.95, 19.1)], 32, closed=False)
    bullet_prof = [(4.51, 0.0), (4.51, 4.0)] + [(4.51 * cos(radians(a)) ** 0.55, 4.0 + 6.6 * sin(radians(a))) for a in range(8, 90, 8)] + [(0.4, 10.6)]
    bul = lathe_y("bullet", bullet_prof, 32, closed=False)
    bul.data.transform(Matrix.Translation(Vector((0, 19.1 * MM, 0))))
    shade(case, 40, False); shade(bul, 50, False)
    m_case = mats['brass']; m_bul = mats['copper']
    assign(case, m_case); assign(bul, m_bul)
    cart = join([case, bul], "cart")
    # orient cartridge: its axis (+Y) along F (forward, following the rake), base at the rear of the mag
    rot = AY.rotation_difference(F).to_matrix().to_4x4()
    pos = GP(-13.0 - 4.9, -10.4, 0.0)
    cart.matrix_world = Matrix.Translation(pos * MM) @ rot
    bake_xform(cart)
    assign(body, mats['steel_mag']); assign(base, mats['steel_mag'])
    m = join([body, base, cart], "Magazine")
    return m

# ----------------------------------------------------------------------------------------------
# HANDS
# ----------------------------------------------------------------------------------------------
FOREARM_DIR_R = Vector((0.33, -0.86, -0.39)).normalized()

def right_hand_rig():
    """Joint chains for the gripping right hand, in gun space (mm)."""
    fingers = {}
    def wrap(s, m, p, d, t, r):
        return list(zip([GP(s, *m), GP(s, *p), GP(s, *d), GP(s, *t)], r))
    fingers['middle'] = wrap(9.0, (29, 25), (33.5, -15), (13.5, -25.8), (-6, -24.6), [9.4, 8.7, 7.9, 7.1])
    fingers['ring'] = wrap(28.5, (28, 24), (32.5, -13), (12.5, -24.8), (-5, -24.0), [9.0, 8.3, 7.6, 6.8])
    fingers['pinky'] = wrap(47.0, (26, 22), (30.5, -7), (15.5, -20.8), (2, -22.4), [8.1, 7.5, 6.9, 6.2])
    mcp_i = GP(-8.0, 27, 26)
    fingers['index'] = list(zip([mcp_i, Vector((19.5, 14.0, -33.0)), Vector((5.5, -2.0, -31.0)),
                                 Vector((-4.5, -6.2, -31.2))], [9.5, 8.6, 7.8, 7.0]))
    th = [Vector((14.0, -84.0, -46.0)), Vector((-21.8, -70.0, -27.0)), Vector((-23.4, -40.0, -19.6)),
          Vector((-23.2, -16.0, -17.8))]
    fingers['thumb'] = list(zip(th[1:], [11.0, 10.2, 9.0]))
    wrist = GP(24.0, -56.0, 13.0)
    mc = []
    for name, s in (('index', -8.0), ('middle', 9.0), ('ring', 28.5), ('pinky', 47.0)):
        mcp = fingers[name][0][0]
        rr = {'index': 11.4, 'middle': 11.8, 'ring': 11.4, 'pinky': 10.2}[name]
        s_c = s * 0.35 + 19.0
        ch = [(mcp, rr - 1.6)]
        for fo, xo, dr in ((6.0, 28.0, 0.0), (-16.0, 27.0, 0.4), (-32.0, 21.5, 1.0), (-45.0, 14.0, 2.0)):
            f = (29.0 - fo) / 74.0
            ch.append((GP(s + (s_c - s) * f, fo, xo), rr + dr))
        mc.append(ch)
    thenar = [(wrist + Vector((0, 4, 6)), 20.0), (GP(10.0, -50.0, 16.0), 16.5), (th[0], 14.0), (th[1], 11.6)]
    return dict(fingers=fingers, mc=mc, thenar=thenar, wrist=wrist, fore_dir=FOREARM_DIR_R.copy(),
                dorsal=AX.copy(), fore_lat=G.copy(), grip=True)


def left_hand_rig():
    """Relaxed open left hand in its own frame: wrist at origin, fingers +Y, palm faces +X, thumb +Z."""
    def finger(mcp, lens, radii, curl):
        pts = [Vector(mcp)]
        ang = 0.0
        for L, c in zip(lens, curl):
            ang += radians(c)
            pts.append(pts[-1] + Vector((sin(ang), cos(ang), 0.0)) * L)
        return list(zip(pts, radii))
    fingers = {
        'index': finger((2.0, 86.0, 25.0), (42, 25, 20), [9.4, 8.5, 7.7, 6.9], (8, 15, 13)),
        'middle': finger((1.5, 90.0, 6.5), (46, 28, 21), [9.4, 8.6, 7.8, 7.0], (8, 17, 15)),
        'ring': finger((0.5, 87.0, -11.5), (43, 27, 20), [9.0, 8.2, 7.5, 6.7], (10, 19, 16)),
        'pinky': finger((-0.5, 80.0, -28.5), (34, 20, 17), [8.1, 7.4, 6.8, 6.1], (12, 20, 17)),
    }
    th = [Vector((7.0, 24.0, 22.0)), Vector((17.0, 46.0, 39.0)), Vector((24.0, 70.0, 45.0)), Vector((28.0, 89.0, 46.5))]
    fingers['thumb'] = list(zip(th[1:], [11.4, 10.3, 9.1]))
    mc = []
    for name in ('index', 'middle', 'ring', 'pinky'):
        mcp = fingers[name][0][0]
        rr = {'index': 11.4, 'middle': 12.0, 'ring': 11.6, 'pinky': 10.2}[name]
        mc.append([(mcp, rr - 1.6), (mcp + Vector((-1.0, -25.0, -mcp.z * 0.12)), rr),
                   (mcp + Vector((-2.0, -52.0, -mcp.z * 0.3)), rr + 0.6), (Vector((0.0, 14.0, mcp.z * 0.42)), rr + 1.6)])
    wrist = Vector((0, 0, 0))
    thenar = [(Vector((2.0, 8.0, 6.0)), 19.0), (Vector((5.0, 24.0, 16.0)), 16.0), (th[0], 14.0), (th[1], 11.6)]
    return dict(fingers=fingers, mc=mc, thenar=thenar, wrist=wrist, fore_dir=Vector((0, -1, 0)),
                dorsal=Vector((-1, 0, 0)), fore_lat=Vector((0, 0, 1)), grip=False)


def resample_chain(ch, n):
    pts = [Vector(p) for p, r in ch]; rs = [r for p, r in ch]
    cum = [0.0]
    for a, b in zip(pts[:-1], pts[1:]):
        cum.append(cum[-1] + (b - a).length)
    out = []
    for k in range(n):
        d = cum[-1] * k / (n - 1)
        i = len(cum) - 2
        for j in range(len(cum) - 1):
            if cum[j + 1] >= d:
                i = j
                break
        t = (d - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
        out.append((pts[i].lerp(pts[i + 1], t), rs[i] + (rs[i + 1] - rs[i]) * t))
    return out


def blend_chains(a, b, t, rscale=1.0):
    return [(pa.lerp(pb, t), (ra + (rb - ra) * t) * rscale) for (pa, ra), (pb, rb) in zip(a, b)]


def loft_tube(name, centers, radii, lat_hint, dorsal_dir, n_around=28, per_seg=10, wfac=1.0, hfac=0.88,
              knuckle=0.045, pad=1.07, cap_tip=True, ext_base=0.0):
    """Organic tube along a smoothed centre line. Elliptical section (lateral = wfac*r, dorsal = hfac*r),
    a fuller palmar pad, knuckle bulges at the joints and a rounded tip."""
    cs = [Vector(c) for c in centers]
    radii = list(radii)
    if ext_base > 0:
        cs = [cs[0] - (cs[1] - cs[0]).normalized() * ext_base] + cs
        radii = [radii[0]] + radii
    C = catmull(cs, per_seg)
    m = len(C); nj = len(cs)
    R = []
    for k in range(m):
        seg = min(k // per_seg, nj - 2); fr = (k - seg * per_seg) / per_seg
        if k == m - 1:
            seg, fr = nj - 2, 1.0
        r = radii[seg] + (radii[seg + 1] - radii[seg]) * fr
        r *= 1.0 + knuckle * cos(2 * pi * fr)
        R.append(r)
    lat_hint = Vector(lat_hint).normalized()
    dorsal_dir = Vector(dorsal_dir).normalized()
    frames = []
    for k in range(m):
        T = (C[min(k + 1, m - 1)] - C[max(k - 1, 0)]).normalized()
        L = (lat_hint - T * lat_hint.dot(T))
        if L.length < 1e-6:
            L = T.orthogonal()
        L.normalize()
        frames.append([T, L, T.cross(L)])
    kref = min(per_seg * (2 if ext_base > 0 else 1), m - 1)
    sgn = 1.0 if frames[kref][2].dot(dorsal_dir) >= 0 else -1.0
    bm = bmesh.new()

    def ring_at(c, T, L, D, r, scale=1.0):
        out = []
        for j in range(n_around):
            th = 2 * pi * j / n_around
            x = cos(th); y = sin(th)
            y *= (hfac * 0.94) if y > 0 else (hfac * pad)
            out.append(bm.verts.new((c + L * (r * wfac * x * scale) + D * (sgn * r * y * scale)) * MM))
        return out
    rings = [ring_at(C[k], *frames[k], R[k]) for k in range(m)]
    pole = None
    if cap_tip:
        T, L, D = frames[-1]; r = R[-1]
        steps = 6
        for s_ in range(1, steps):
            ph = (s_ / steps) * (pi / 2)
            rings.append(ring_at(C[-1] + T * (r * 0.92 * sin(ph)), T, L, D, r, cos(ph) ** 0.8))
        pole = bm.verts.new((C[-1] + T * r * 0.92) * MM)
    for i in range(len(rings) - 1):
        for j in range(n_around):
            j2 = (j + 1) % n_around
            bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]))
    if pole is not None:
        for j in range(n_around):
            bm.faces.new((rings[-1][j], rings[-1][(j + 1) % n_around], pole))
    else:
        bm.faces.new(list(reversed(rings[-1])))
    bm.faces.new(rings[0])
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return obj_from_bm(name, bm)


def skin_chain_obj(name, chains, sub_levels=1):
    bm = bmesh.new()
    info = []
    for ch in chains:
        prev = None
        for k, (p, r) in enumerate(ch):
            v = bm.verts.new(Vector(p) * MM)
            info.append((r, k == 0))
            if prev is not None:
                bm.edges.new((prev, v))
            prev = v
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    ob = link(bpy.data.objects.new(name, me))
    sk = ob.modifiers.new("skin", 'SKIN')
    sk.branch_smoothing = 0.5
    sv = me.skin_vertices[0].data
    for i, (r, root) in enumerate(info):
        sv[i].radius = (r * MM, r * MM)
        sv[i].use_root = root
    sub = ob.modifiers.new("sub", 'SUBSURF'); sub.levels = sub_levels; sub.render_levels = sub_levels
    apply_mods(ob)
    return ob


def densify(chain, step=5.0):
    out = [chain[0]]
    for (p0, r0), (p1, r1) in zip(chain[:-1], chain[1:]):
        L = (Vector(p1) - Vector(p0)).length
        n = max(1, int(L // step))
        for k in range(1, n + 1):
            t = k / n
            out.append((Vector(p0).lerp(Vector(p1), t), r0 + (r1 - r0) * t))
    return out


def finger_dorsal(ch):
    a, b, c = [Vector(p) for p, r in ch[:3]]
    return (b - (a + c) * 0.5).normalized()


def finger_lateral(ch, dorsal_hint):
    a, b, c = [Vector(p) for p, r in ch[:3]]
    lat = (b - a).cross(c - b)
    if lat.length < 1e-4:
        lat = (b - a).cross(Vector(dorsal_hint))
    return lat.normalized()


def build_glove(name, rig, target_tris):
    parts = []
    # palm: dense set of interpolated metacarpal chains -> a smooth slab after the voxel union
    mcs = [resample_chain(densify(c), 14) for c in rig['mc']]
    chains = []
    for i in range(len(mcs) - 1):
        chains.append(mcs[i])
        for t in (1 / 6, 2 / 6, 3 / 6, 4 / 6, 5 / 6):
            chains.append(blend_chains(mcs[i], mcs[i + 1], t))
    chains.append(mcs[-1])
    th = resample_chain(densify(rig['thenar']), 14)
    for t in (0.0, 0.2, 0.4, 0.6, 0.8):
        chains.append(blend_chains(th, mcs[0], t, rscale=1.0 - 0.25 * t))
    parts.append(skin_chain_obj(f"{name}_palm", chains, sub_levels=2))
    # fingers + thumb: lofted
    for fname, ch in rig['fingers'].items():
        pts = [p for p, r in ch]; rs = [r for p, r in ch]
        dors = finger_dorsal(ch)
        lat = finger_lateral(ch, rig['dorsal'])
        parts.append(loft_tube(f"{name}_{fname}", pts, rs, lat, dors, n_around=30, per_seg=12,
                               wfac=1.09 if fname != 'thumb' else 1.08, hfac=0.86, ext_base=6.0))
    # wrist / glove cuff
    w = Vector(rig['wrist']); fd = Vector(rig['fore_dir'])
    parts.append(loft_tube(f"{name}_wrist", [w - fd * 14.0, w, w + fd * 30.0, w + fd * 62.0], [21.5, 22.5, 23.0, 24.5],
                           rig['fore_lat'], rig['dorsal'], n_around=36, per_seg=8, wfac=1.17, hfac=0.80,
                           knuckle=0.0, pad=1.0, cap_tip=False))
    g = join(parts, name)
    rm = g.modifiers.new("rm", 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.42 * MM; rm.adaptivity = 0.0
    sm = g.modifiers.new("sm", 'SMOOTH'); sm.factor = 0.65; sm.iterations = 14
    apply_mods(g)
    bm = bmesh.new(); bm.from_mesh(g.data)
    cut_c = (w + fd * 52.0) * MM
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-7,
                           plane_co=cut_c, plane_no=fd, clear_outer=True)
    bm.to_mesh(g.data); bm.free()
    cur = len(g.data.polygons) * 2
    dc = g.modifiers.new("dc", 'DECIMATE'); dc.ratio = min(1.0, target_tris / max(cur, 1))
    apply_mods(g)
    g.data.polygons.foreach_set("use_smooth", [True] * len(g.data.polygons))
    log(f"{name}: glove tris {tri_count(g)}")
    return g


def seg_frame(a, b):
    t = (b - a); L = t.length
    return t / max(L, 1e-9), L


def compute_glove_attributes(g, rig):
    """Seam / stitch / crease / hem fields as point attributes (mm), used by the glove shader."""
    me = g.data
    n = len(me.vertices)
    P = np.empty(n * 3, np.float32); me.vertices.foreach_get("co", P); P = P.reshape(n, 3) / MM
    seam_d = np.full(n, 99.0, np.float32); along = np.zeros(n, np.float32)
    crease_w = np.zeros(n, np.float32); crease_d = np.zeros(n, np.float32)
    best = np.full(n, 1e9, np.float32)
    for fname, ch in rig['fingers'].items():
        pts = [np.array(p, np.float32) for p, r in ch]
        rads = [r for p, r in ch]
        # curl-plane normal -> lateral direction; dorsal-palmar direction d = t x lateral
        a, b, c = pts[0], pts[1], pts[2]
        lat = np.cross(b - a, c - b)
        if np.linalg.norm(lat) < 1e-3:
            lat = np.cross(b - a, np.array(rig['dorsal'], np.float32))
        lat /= np.linalg.norm(lat)
        acc = 0.0
        for i in range(len(pts) - 1):
            p0, p1 = pts[i], pts[i + 1]
            t = p1 - p0; L = float(np.linalg.norm(t)); t /= max(L, 1e-6)
            rel = P - p0
            s = rel @ t
            sc = np.clip(s, 0, L)
            perp = rel - np.outer(sc, t)
            dist = np.linalg.norm(perp, axis=1)
            r = rads[i] + (rads[i + 1] - rads[i]) * (sc / max(L, 1e-6))
            near = (dist < r * 1.45) & (s > -2.0) & (s < L + 2.0) & (dist < best)
            dvec = np.cross(t, lat)
            sd = np.abs(rel @ dvec)
            seam_d = np.where(near, sd, seam_d)
            along = np.where(near, acc + s, along)
            best = np.where(near, dist, best)
            acc += L
        # creases at PIP / DIP (and MCP for fingers)
        for j in range(1, len(pts) - 1):
            tj = pts[j + 1] - pts[j - 1]; tj /= np.linalg.norm(tj)
            rel = P - pts[j]
            dd = rel @ tj
            dist = np.linalg.norm(rel - np.outer(dd, tj), axis=1)
            w = np.exp(-(dd / 3.4) ** 2) * (dist < rads[j] * 1.5)
            upd = w > crease_w
            crease_w = np.where(upd, w, crease_w); crease_d = np.where(upd, dd, crease_d)
    # points on the back of the hand: three straight ridges between the knuckles toward the wrist
    pts_d = np.full(n, 99.0, np.float32); pts_al = np.zeros(n, np.float32)
    dors = np.array(rig['dorsal'], np.float32)
    mcps = [np.array(rig['fingers'][f][0][0], np.float32) for f in ('index', 'middle', 'ring', 'pinky')]
    w = np.array(rig['wrist'], np.float32)
    mids = [(mcps[i] + mcps[i + 1]) * 0.5 for i in range(3)]
    tdir = w - sum(mids) / 3.0
    tlen = float(np.linalg.norm(tdir)); tdir = tdir / tlen
    for i in range(3):
        m = mids[i]
        a = m + tdir * (tlen * 0.16)
        b = m + tdir * (tlen * 0.50)
        t = b - a; L = float(np.linalg.norm(t)); t /= L
        nrm = dors - t * float(dors @ t); nrm /= np.linalg.norm(nrm)
        plane_n = np.cross(t, nrm)
        rel = P - a
        s = rel @ t
        h = rel @ nrm
        ok = (s > 0) & (s < L) & (h > 0)
        d = np.abs(rel @ plane_n)
        taper = 1.0 + 1.2 * np.clip((s - L * 0.75) / (L * 0.25), 0, 1)  # ends fade
        upd = ok & (d * taper < pts_d)
        pts_d = np.where(upd, d * taper, pts_d); pts_al = np.where(upd, s, pts_al)
    # cuff hem: ring around the forearm
    fd = np.array(rig['fore_dir'], np.float32)
    hem_c = w + fd * 34.0
    hem_d = np.abs((P - hem_c) @ fd).astype(np.float32)
    for nm, arr in (("seam_d", seam_d), ("seam_along", along), ("crease_w", crease_w), ("crease_d", crease_d),
                    ("points_d", pts_d), ("points_along", pts_al), ("hem_d", hem_d)):
        if nm in me.attributes:
            me.attributes.remove(me.attributes[nm])
        at = me.attributes.new(nm, 'FLOAT', 'POINT')
        at.data.foreach_set("value", arr.astype(np.float32))


def build_sleeve(name, wrist, fdir, seed):
    """Dark wool overcoat sleeve from just past the wrist to mid-forearm, with folds and a turned cuff."""
    rng = np.random.default_rng(seed)
    fdir = Vector(fdir).normalized()
    up = Vector((0, 0, 1)) if abs(fdir.z) < 0.9 else Vector((1, 0, 0))
    u = fdir.cross(up).normalized(); v = fdir.cross(u).normalized()
    nr, ns = 70, 64
    t0, t1 = 8.0, 430.0
    ph = rng.uniform(0, 2 * pi, 6)
    bm = bmesh.new()
    rings = []
    for i in range(nr + 1):
        t = t0 + (t1 - t0) * i / nr
        ring = []
        for j in range(ns):
            a = 2 * pi * j / ns
            base = 36.5 + 0.022 * (t - t0)
            cuff = 2.0 * math.exp(-((t - t0 - 8.0) / 9.0) ** 2)   # turned-back cuff bulge
            fade = max(0.25, 1.0 - (t - t0) / 260.0)
            fold = 1.7 * sin(t / 13.0 + ph[0] + 1.3 * sin(a * 2 + ph[1])) * (0.4 + 0.6 * sin(a + ph[2]) ** 2)
            fold += 0.9 * sin(t / 6.5 + ph[3] + 2.0 * sin(a * 3 + ph[4]))
            fold *= fade
            fold += 2.2 * sin(t / 41.0 + ph[5] + 0.8 * sin(a + ph[1]))
            sag = 2.0 * max(0.0, -cos(a - 0.4))   # fabric hangs a bit lower
            r = base + cuff + fold * min(1.0, (t - t0) / 25.0) + sag
            p = Vector(wrist) + fdir * t + (u * cos(a) + v * sin(a)) * r
            ring.append(bm.verts.new(p * MM))
        rings.append(ring)
    for i in range(nr):
        for j in range(ns):
            j2 = (j + 1) % ns
            bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    ob = obj_from_bm(name, bm)
    # normals should point outward
    so = ob.modifiers.new("sol", 'SOLIDIFY'); so.thickness = 3.2 * MM; so.offset = -1.0; so.use_even_offset = True
    apply_mods(ob)
    ob.data.polygons.foreach_set("use_smooth", [True] * len(ob.data.polygons))
    return ob


def build_hand(name, rig, mats, seed, target_tris=24000):
    g = build_glove(name, rig, target_tris)
    compute_glove_attributes(g, rig)
    assign(g, mats['glove'])
    s = build_sleeve(name + "_sleeve", rig['wrist'], rig['fore_dir'], seed)
    assign(s, mats['wool'])
    h = join([g, s], name)
    return h

# ----------------------------------------------------------------------------------------------
# UV + BAKE + FINAL MATERIALS
# ----------------------------------------------------------------------------------------------
def select_only(objs, active=None):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]


def unwrap_pack(objs, angle=62, scale_mats=None):
    select_only(objs)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=radians(angle), island_margin=0.0015, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode='OBJECT')
    if scale_mats:
        for o in objs:
            me = o.data
            uv = me.uv_layers.active.data
            for p in me.polygons:
                mname = me.materials[p.material_index].name if me.materials else ""
                if mname in scale_mats:
                    k = scale_mats[mname]
                    for li in p.loop_indices:
                        uv[li].uv = uv[li].uv * k
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin=0.0016)
    bpy.ops.object.mode_set(mode='OBJECT')


def setup_cycles(samples):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.device = 'CPU'
    if FORCE_CPU:
        return
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'ONEAPI'
        prefs.get_devices()
        got = False
        for d in prefs.devices:
            d.use = (d.type == 'ONEAPI')
            got = got or d.use
        if got:
            sc.cycles.device = 'GPU'
    except Exception as e:
        log("GPU setup failed, CPU:", e)


def bake_atlas(objs, infos, prefix, res, channels, hide=()):
    sc = bpy.context.scene
    setup_cycles(8)
    sc.render.bake.margin = 24
    sc.render.bake.margin_type = 'EXTEND'
    sc.render.bake.use_clear = True
    sc.render.bake.normal_space = 'TANGENT'
    sc.render.bake.normal_r = 'POS_X'; sc.render.bake.normal_g = 'POS_Y'; sc.render.bake.normal_b = 'POS_Z'
    for o in hide:
        o.hide_render = True
    os.makedirs(TEX_DIR, exist_ok=True)
    results = {}
    for ch in channels:
        img = bpy.data.images.new(f"{prefix}_{ch}", res, res, alpha=False, float_buffer=(ch == 'normal'))
        img.colorspace_settings.name = 'sRGB' if ch == 'color' else 'Non-Color'
        for inf in infos:
            nb = inf['nb']
            inf['img'].image = img
            nb.nt.nodes.active = inf['img']
            for l in list(inf['out'].inputs['Surface'].links):
                nb.L.remove(l)
            if ch in ('color', 'rough', 'metal'):
                for l in list(inf['emit'].inputs['Color'].links):
                    nb.L.remove(l)
                nb.put(inf['emit'].inputs['Color'], inf['sock'][ch])
                nb.L.new(inf['emit'].outputs[0], inf['out'].inputs['Surface'])
            else:
                nb.L.new(inf['bsdf'].outputs[0], inf['out'].inputs['Surface'])
        btype = {'color': 'EMIT', 'rough': 'EMIT', 'metal': 'EMIT', 'normal': 'NORMAL', 'ao': 'AO'}[ch]
        sc.cycles.samples = 64 if ch == 'ao' else (8 if ch == 'normal' else 4)
        select_only(objs)
        t = time.time()
        bpy.ops.object.bake(type=btype, margin=24, use_clear=True)
        log(f"baked {prefix}_{ch} ({btype}) in {time.time()-t:.1f}s")
        path = os.path.join(TEX_DIR, f"{prefix}_{ch}.png")
        img.filepath_raw = path; img.file_format = 'PNG'
        img.save()
        results[ch] = img
    for inf in infos:  # restore viewing wiring
        nb = inf['nb']
        for l in list(inf['out'].inputs['Surface'].links):
            nb.L.remove(l)
        nb.L.new(inf['bsdf'].outputs[0], inf['out'].inputs['Surface'])
    for o in hide:
        o.hide_render = False
    return results


def combine_ao(color_img, ao_img, strength):
    n = color_img.size[0] * color_img.size[1] * 4
    c = np.empty(n, np.float32); color_img.pixels.foreach_get(c)
    a = np.empty(n, np.float32); ao_img.pixels.foreach_get(a)
    c = c.reshape(-1, 4); a = a.reshape(-1, 4)
    k = 1.0 - strength * (1.0 - a[:, :1])
    c[:, :3] *= k
    color_img.pixels.foreach_set(c.ravel())
    color_img.update()
    color_img.save()


def final_material(name, imgs, metal_value=None):
    mat = new_material(name); nb = NB(mat)
    out = nb.new('ShaderNodeOutputMaterial'); bsdf = nb.new('ShaderNodeBsdfPrincipled')
    nb.L.new(bsdf.outputs[0], out.inputs['Surface'])
    def tex(img, noncolor):
        t = nb.new('ShaderNodeTexImage'); t.image = img
        img.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
        return t
    nb.L.new(tex(imgs['color'], False).outputs['Color'], bsdf.inputs['Base Color'])
    nb.L.new(tex(imgs['rough'], True).outputs['Color'], bsdf.inputs['Roughness'])
    if 'metal' in imgs:
        nb.L.new(tex(imgs['metal'], True).outputs['Color'], bsdf.inputs['Metallic'])
    else:
        bsdf.inputs['Metallic'].default_value = metal_value or 0.0
    nm = nb.new('ShaderNodeNormalMap')
    nb.L.new(tex(imgs['normal'], True).outputs['Color'], nm.inputs['Color'])
    nb.L.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


def replace_materials(objs, mat):
    for o in objs:
        o.data.materials.clear()
        o.data.materials.append(mat)
        o.data.polygons.foreach_set("material_index", [0] * len(o.data.polygons))

# ----------------------------------------------------------------------------------------------
# PREVIEWS
# ----------------------------------------------------------------------------------------------
def preview_world():
    sc = bpy.context.scene
    w = sc.world or bpy.data.worlds.new("World")
    sc.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputWorld'); bg = nt.nodes.new('ShaderNodeBackground')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs[1].default_value = -0.3; mr.inputs[2].default_value = 0.9
    nt.links.new(sep.outputs['Z'], mr.inputs[0])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    ins = {s.identifier: s for s in mix.inputs}
    ins['A_Color'].default_value = (0.012, 0.011, 0.010, 1); ins['B_Color'].default_value = (0.07, 0.08, 0.095, 1)
    nt.links.new(mr.outputs[0], ins['Factor_Float'])
    # a soft-box strip for metal reflections
    dp = nt.nodes.new('ShaderNodeVectorMath'); dp.operation = 'DOT_PRODUCT'
    nt.links.new(tc.outputs['Generated'], dp.inputs[0]); dp.inputs[1].default_value = Vector((-0.55, -0.35, 0.76)).normalized()
    sb = nt.nodes.new('ShaderNodeMapRange'); sb.inputs[1].default_value = 0.93; sb.inputs[2].default_value = 0.985
    sb.inputs[4].default_value = 4.0
    nt.links.new(dp.outputs[1], sb.inputs[0])
    add = nt.nodes.new('ShaderNodeVectorMath'); add.operation = 'ADD'
    nt.links.new({s.identifier: s for s in mix.outputs}['Result_Color'], add.inputs[0])
    nt.links.new(sb.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 1.0
    nt.links.new(bg.outputs[0], out.inputs['Surface'])
    w.light_settings.distance = 0.012


def area_light(name, loc, target, energy, size, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = energy; ld.size = size; ld.color = color
    ob = link(bpy.data.objects.new(name, ld))
    ob.location = loc
    d = (Vector(target) - Vector(loc)).normalized()
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob


def camera(name, loc, target=None, direction=None, fov_v=60.0, ortho=None):
    cd = bpy.data.cameras.new(name)
    cd.sensor_fit = 'VERTICAL'
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho
    else:
        cd.angle_y = radians(fov_v)
    cd.clip_start = 0.005
    ob = link(bpy.data.objects.new(name, cd))
    ob.location = loc
    d = direction if direction is not None else (Vector(target) - Vector(loc))
    ob.rotation_euler = Vector(d).normalized().to_track_quat('-Z', 'Y').to_euler()
    return ob


def render_previews(tag, samples, empties):
    sc = bpy.context.scene
    setup_cycles(samples)
    sc.render.resolution_x = 1600; sc.render.resolution_y = 900; sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.exposure = 0.0
    preview_world()
    tgt = Vector((0.0, 0.02, -0.04))
    lights = [area_light("key", (-0.35, 0.25, 0.32), tgt, 7.0, 0.35, (1.0, 0.95, 0.88)),
              area_light("fill", (0.4, -0.2, 0.12), tgt, 1.6, 0.5, (0.85, 0.9, 1.0)),
              area_light("rim", (0.05, 0.45, 0.2), tgt, 4.0, 0.25)]
    os.makedirs(PREV_DIR, exist_ok=True)
    sr = empties['SightRear'].location.copy(); sf = empties['SightFront'].location.copy()
    sdir = (sf - sr).normalized()
    cams = [
        ("beauty_left34", camera("c1", (-0.30, 0.20, 0.06), target=(0.0, 0.02, -0.045), fov_v=26)),
        ("side_right", camera("c2", (0.6, 0.025, -0.045), target=(0.0, 0.025, -0.045), ortho=0.30)),
        ("side_left", camera("c2b", (-0.6, 0.025, -0.045), target=(0.0, 0.025, -0.045), ortho=0.30)),
        ("fp_hip", camera("c3", (0.0, -0.62, 0.11), direction=(0, 1, 0), fov_v=70)),
        ("fp_ads", camera("c4", tuple(sr - sdir * 0.42), direction=tuple(sdir), fov_v=45)),
    ]
    hl = bpy.data.objects.get("Hand_L")
    if hl is not None:
        c = hl.matrix_world.translation
        cams.append(("hand_left", camera("c5", tuple(c + Vector((-0.12, 0.30, 0.22))), target=tuple(c), fov_v=40)))
    paths = []
    for nm, cam in cams:
        sc.camera = cam
        p = os.path.join(PREV_DIR, f"{tag}_{nm}.png")
        sc.render.filepath = p
        t = time.time()
        bpy.ops.render.render(write_still=True)
        log(f"rendered {nm} in {time.time()-t:.1f}s")
        paths.append(p)
    for o in lights + [c for _, c in cams]:
        bpy.data.objects.remove(o, do_unlink=True)
    return paths

# ----------------------------------------------------------------------------------------------
# VERIFY
# ----------------------------------------------------------------------------------------------
def inspect_glb(path):
    with open(path, 'rb') as f:
        data = f.read()
    clen, ctype = struct.unpack_from('<II', data, 12)
    js = json.loads(data[20:20 + clen])
    nodes = js['nodes']
    names = [n.get('name') for n in nodes]
    tris = 0
    for m in js.get('meshes', []):
        for p in m['primitives']:
            tris += js['accessors'][p['indices']]['count'] // 3
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get('children', []):
            parent[c] = i
    def world_t(i):
        t = Vector(nodes[i].get('translation', (0, 0, 0)))
        while i in parent:
            i = parent[i]
            t = t + Vector(nodes[i].get('translation', (0, 0, 0)))  # parents carry no rotation here
        return t
    pos = {nm: tuple(round(x, 5) for x in world_t(i)) for i, nm in enumerate(names)}
    hier = {names[i]: [names[c] for c in n.get('children', [])] for i, n in enumerate(nodes) if n.get('children')}
    imgs = [(im.get('mimeType'), js['bufferViews'][im['bufferView']]['byteLength']) for im in js.get('images', [])]
    return dict(names=names, tris=tris, pos=pos, hier=hier, images=imgs, size=len(data))

# ----------------------------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------------------------
def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    log("building materials")
    mats_info = {
        'steel': mat_steel("m_steel"), 'steel_mag': mat_steel("m_steel_mag", magazine=True),
        'bakelite': mat_bakelite(), 'brass': mat_brass("m_brass"), 'copper': mat_brass("m_copper", copper=True),
        'glove': mat_glove(), 'wool': mat_wool(),
    }
    mats = {k: v['mat'] for k, v in mats_info.items()}
    log("building gun")
    barrel = build_barrel(mats)
    slide = build_slide(mats)
    deco = build_decocker(mats)
    hammer = build_hammer(mats)
    trig = build_trigger(mats)
    frame = build_frame(mats)
    mag = build_magazine(mats)
    deco.parent = slide  # slide is at the origin, so local == world
    gun = [frame, slide, barrel, hammer, trig, mag, deco]
    for o in gun:
        log(f"  {o.name}: {tri_count(o)} tris")
    log("building hands")
    hand_r = build_hand("Hand_R", right_hand_rig(), mats, seed=3)
    lrig = left_hand_rig()
    hand_l = build_hand("Hand_L", lrig, mats, seed=7)
    # Hand_L origin at its palm centre; posed palm-up/right, fingers forward, parked out of view down-left
    palm_c = Vector((0.0, 45.0, 0.0))
    set_origin(hand_l, palm_c)
    hand_l.rotation_euler = (radians(10.0), radians(-60.0), 0.0)   # palm turned up/right toward the mag well
    hand_l.location = Vector((-170.0, -210.0, -340.0)) * MM
    hands = [hand_r, hand_l]
    log(f"  Hand_R {tri_count(hand_r)} tris, Hand_L {tri_count(hand_l)} tris")
    # empties
    empties = {}
    for nm, p in (("Muzzle", (0, MUZZLE_Y, 0)), ("EjectPort", (-9.0, BREECH_Y + 13.0, 5.0)),
                  ("SightRear", (0, SLIDE_REAR + 5.5, SIGHT_Z)), ("SightFront", (0, 121.0, SIGHT_Z))):
        e = link(bpy.data.objects.new(nm, None))
        e.empty_display_type = 'PLAIN_AXES'; e.empty_display_size = 0.01
        e.location = Vector(p) * MM
        empties[nm] = e
    total = sum(tri_count(o) for o in gun + hands)
    log(f"TOTAL tris {total}")

    if PREVIEWS and not BAKE:
        render_previews("proc", SAMPLES, empties)

    if BAKE:
        log("unwrap")
        unwrap_pack(gun, 60)
        unwrap_pack(hands, 66, scale_mats={'m_wool': 0.5})
        gun_infos = [mats_info[k] for k in ('steel', 'steel_mag', 'bakelite', 'brass', 'copper')]
        hand_infos = [mats_info['glove'], mats_info['wool']]
        log("bake gun")
        gi = bake_atlas(gun, gun_infos, "p38", RES, ['color', 'rough', 'metal', 'normal', 'ao'], hide=hands)
        combine_ao(gi['color'], gi['ao'], 0.75)
        log("bake hands")
        hi = bake_atlas(hands, hand_infos, "fp_hands", RES, ['color', 'rough', 'normal', 'ao'], hide=[])
        combine_ao(hi['color'], hi['ao'], 0.6)
        m_gun = final_material("P38", gi)
        m_hands = final_material("FP_Hands_Leather_Wool", hi, metal_value=0.0)
        replace_materials(gun, m_gun)
        replace_materials(hands, m_hands)
        log("export glb")
        os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
        select_only(gun + hands + list(empties.values()))
        bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', use_selection=True, export_apply=True,
                                  export_image_format='JPEG', export_jpeg_quality=92, export_cameras=False,
                                  export_lights=False, export_yup=True, export_texcoords=True, export_normals=True,
                                  export_materials='EXPORT', export_animations=False)
        info = inspect_glb(OUT_GLB)
        log("GLB nodes:", info['names'])
        log("GLB hierarchy:", info['hier'])
        log("GLB tris:", info['tris'], " size MB:", round(info['size'] / 1e6, 2), " images:", info['images'])
        for nm in ("Muzzle", "EjectPort", "SightRear", "SightFront", "Slide", "Hammer", "Trigger", "Decocker", "Hand_L"):
            log(f"  {nm} godot pos (m): {info['pos'].get(nm)}")
        need = ["Frame", "Slide", "Barrel", "Hammer", "Trigger", "Magazine", "Decocker", "Muzzle", "EjectPort",
                "SightRear", "SightFront", "Hand_R", "Hand_L"]
        missing = [n for n in need if n not in info['names']]
        log("MISSING:", missing if missing else "none")
        if PREVIEWS:
            render_previews("baked", SAMPLES, empties)
    log("done")


main()
