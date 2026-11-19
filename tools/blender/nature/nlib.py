"""Blender helpers for the nature kit: materials (incl. alpha-clip cards), mesh builder, tubes,
cards, collision, export (+ ICC strip), glb inspection and dusk preview renders."""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.abspath(os.path.join(HERE, "..", "env"))
TOOLS = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (HERE, ENV, TOOLS):
    if p not in sys.path:
        sys.path.insert(0, p)
import geo            # noqa: E402  (env kit helpers: primitives, inspect_glb, dusk world)
import glb_strip_icc  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
NTEX = os.path.join(HERE, "out", "tex")
ENVTEX = os.path.join(ENV, "out", "tex")
GROUND = os.path.join(ROOT, "game", "assets", "textures", "ground")
MODEL_DIR = os.path.join(ROOT, "game", "assets", "models", "nature")
PREVIEW_DIR = os.path.join(HERE, "previews")

ALPHA_CUTOFF = 0.5


# ============================================================ materials
_MATS = {}


def reset():
    geo.reset_scene()
    _MATS.clear()


def _img(path, srgb):
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    return img


def mat(name, tex, folder=NTEX, alpha=False, normal=True, orm=True, rough=0.85, nstrength=1.0, tint=None,
        cutoff=ALPHA_CUTOFF, ntex=None, otex=None):
    """Principled material from '<tex>_albedo/_normal/_orm.png'.
    alpha=True wires albedo alpha through  1 - (a < cutoff)  which the glTF exporter writes as
    alphaMode MASK with alphaCutoff = cutoff. Cards are double-sided (no backface culling)."""
    key = name
    if key in _MATS:
        return _MATS[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    b = N["Principled BSDF"]
    ta = N.new("ShaderNodeTexImage")
    ta.image = _img(os.path.join(folder, f"{tex}_albedo.png"), True)
    ta.location = (-900, 300)
    if tint is not None:
        mx = N.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = "MULTIPLY"
        mx.inputs["Factor"].default_value = 1.0
        mx.inputs[7].default_value = (*tint, 1.0)
        L.new(ta.outputs["Color"], mx.inputs[6])
        L.new(mx.outputs[2], b.inputs["Base Color"])
    else:
        L.new(ta.outputs["Color"], b.inputs["Base Color"])
    if alpha:
        lt = N.new("ShaderNodeMath")
        lt.operation = "LESS_THAN"
        lt.inputs[1].default_value = cutoff
        sub = N.new("ShaderNodeMath")
        sub.operation = "SUBTRACT"
        sub.inputs[0].default_value = 1.0
        L.new(ta.outputs["Alpha"], lt.inputs[0])
        L.new(lt.outputs[0], sub.inputs[1])
        L.new(sub.outputs[0], b.inputs["Alpha"])
        m.surface_render_method = "DITHERED"
        m.use_backface_culling = False
        b.inputs["Subsurface Weight"].default_value = 0.0
    ntex, otex = ntex or tex, otex or tex
    if normal and os.path.exists(os.path.join(folder, f"{ntex}_normal.png")):
        tn = N.new("ShaderNodeTexImage")
        tn.image = _img(os.path.join(folder, f"{ntex}_normal.png"), False)
        tn.location = (-900, -300)
        nm = N.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = nstrength
        L.new(tn.outputs["Color"], nm.inputs["Color"])
        L.new(nm.outputs["Normal"], b.inputs["Normal"])
    if orm and os.path.exists(os.path.join(folder, f"{otex}_orm.png")):
        to = N.new("ShaderNodeTexImage")
        to.image = _img(os.path.join(folder, f"{otex}_orm.png"), False)
        to.location = (-900, 0)
        sep = N.new("ShaderNodeSeparateColor")
        L.new(to.outputs["Color"], sep.inputs["Color"])
        L.new(sep.outputs["Green"], b.inputs["Roughness"])
        L.new(sep.outputs["Blue"], b.inputs["Metallic"])
        grp = N.new("ShaderNodeGroup")
        grp.node_tree = geo._gltf_group()
        L.new(sep.outputs["Red"], grp.inputs["Occlusion"])
    else:
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = 0.0
    if not alpha:
        m.use_backface_culling = True
    _MATS[key] = m
    return m


def flat(name, color, rough=0.8):
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    _MATS[name] = m
    return m


# ========================================================= mesh builder
class MB:
    """Accumulates polygons (with per-corner UVs and a material) into one mesh object."""

    def __init__(self):
        self.verts, self.faces, self.uvs, self.mi, self.smooth = [], [], [], [], []
        self.mats = []

    def m(self, material):
        if material not in self.mats:
            self.mats.append(material)
        return self.mats.index(material)

    def add_verts(self, vs):
        base = len(self.verts)
        self.verts.extend(vs)
        return base

    def face(self, idx, uvs, material, smooth=True):
        self.faces.append(list(idx))
        self.uvs.append(list(uvs))
        self.mi.append(self.m(material))
        self.smooth.append(smooth)

    def add_bm(self, bm, material, uv="box", scale=0.5, smooth=False, matrix=None, uvfn=None):
        if matrix is not None:
            bmesh.ops.transform(bm, matrix=matrix, verts=bm.verts)
        bm.normal_update()
        bm.verts.index_update()
        base = self.add_verts([v.co.copy() for v in bm.verts])
        uvl = bm.loops.layers.uv.active if uv == "keep" else None
        for f in bm.faces:
            n = f.normal
            if uv == "keep":
                uvs = [tuple(l[uvl].uv) for l in f.loops]
            elif uvfn is not None:
                uvs = [uvfn(l.vert.co, n) for l in f.loops]
            else:
                uvs = [geo.box_uv(l.vert.co, n, scale) for l in f.loops]
            mat_ = material(f) if callable(material) else material
            self.face([base + v.index for v in f.verts], uvs, mat_, smooth)
        bm.free()

    def tris(self):
        return sum(len(f) - 2 for f in self.faces)

    def build(self, name):
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in self.verts], [], self.faces)
        for mt in self.mats:
            me.materials.append(mt)
        me.polygons.foreach_set("material_index", self.mi)
        me.polygons.foreach_set("use_smooth", self.smooth)
        uvl = me.uv_layers.new(name="UVMap")
        uvl.data.foreach_set("uv", [c for f in self.uvs for uv in f for c in uv])
        me.validate(clean_customdata=False)
        me.update()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


# ================================================================ tubes
def frames(pts):
    """Parallel-transport frames along a polyline -> list of (tangent, normal, binormal)."""
    out = []
    n = len(pts)
    tans = []
    for i in range(n):
        a = pts[max(0, i - 1)]
        b = pts[min(n - 1, i + 1)]
        t = (b - a)
        tans.append(t.normalized() if t.length > 1e-9 else Vector((0, 0, 1)))
    t0 = tans[0]
    ref = Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0))
    nrm = t0.cross(ref).normalized()
    for i, t in enumerate(tans):
        if i > 0:
            prev = tans[i - 1]
            ax = prev.cross(t)
            if ax.length > 1e-8:
                ang = prev.angle(t)
                nrm = (Matrix.Rotation(ang, 3, ax.normalized()) @ nrm).normalized()
        nrm = (nrm - t * nrm.dot(t)).normalized()
        out.append((t, nrm, t.cross(nrm)))
    return out


def tube(mb, pts, radii, material, segs, tile=1.0, v0=0.0, rfun=None, cap=False, material_fn=None, u_rep=None):
    """Generalised cylinder through pts with radii. rfun(i, j, angle, point) -> radius multiplier.
    UV: u wraps around (integer repeats of `tile` metres where large), v = length / tile."""
    pts = [Vector(p) for p in pts]
    fr = frames(pts)
    rmax = max(radii)
    if u_rep is None:
        circ = 2 * math.pi * radii[0]
        u_rep = max(1, round(circ / tile)) if circ > 0.6 * tile else max(circ / tile, 0.12)
    rings = []
    v = v0
    vs = []
    for i, (p, r) in enumerate(zip(pts, radii)):
        if i > 0:
            v += (pts[i] - pts[i - 1]).length / tile
        vs.append(v)
        t, n, b = fr[i]
        ring = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            rr = r * (rfun(i, j, a, p) if rfun else 1.0)
            ring.append(p + (n * math.cos(a) + b * math.sin(a)) * rr)
        rings.append(mb.add_verts(ring))
    for i in range(len(pts) - 1):
        for j in range(segs):
            j1 = (j + 1) % segs
            a, b_, c, d = rings[i] + j, rings[i] + j1, rings[i + 1] + j1, rings[i + 1] + j
            u0, u1 = j / segs * u_rep, (j + 1) / segs * u_rep
            mt = material_fn(i, j, pts[i], fr[i]) if material_fn else material
            mb.face((a, b_, c, d), ((u0, vs[i]), (u1, vs[i]), (u1, vs[i + 1]), (u0, vs[i + 1])), mt)
    if cap:
        last = rings[-1]
        c = mb.add_verts([pts[-1] + fr[-1][0] * radii[-1] * 0.3])
        for j in range(segs):
            j1 = (j + 1) % segs
            mb.face((last + j, last + j1, c), ((0, 0), (0.1, 0), (0.05, 0.1)), material)
    return vs[-1]


def card(mb, base, up, side, w, h, rect, material, bend=0.0, segs=1, lift=None):
    """Quad (or bent strip) whose bottom-centre sits at base, extending along `up` by h, width w
    along `side`. rect=(u0,v0,u1,v1) atlas region. bend: droop of the tip (m) along -Z or `lift`."""
    base, up, side = Vector(base), Vector(up).normalized(), Vector(side).normalized()
    u0, v0, u1, v1 = rect
    droop = Vector(lift) if lift is not None else Vector((0, 0, -1))
    rows = []
    for k in range(segs + 1):
        t = k / segs
        c = base + up * h * t + droop * bend * t * t
        rows.append(mb.add_verts([c - side * w / 2, c + side * w / 2]))
    for k in range(segs):
        ta, tb = k / segs, (k + 1) / segs
        va, vb = v0 + (v1 - v0) * ta, v0 + (v1 - v0) * tb
        a, b = rows[k], rows[k + 1]
        mb.face((a, a + 1, b + 1, b), ((u0, va), (u1, va), (u1, vb), (u0, vb)), material, smooth=False)


# ============================================================ collision
def col_cylinder(name, x, y, r, z0, z1, segs=8, suffix="-convcolonly", tilt=None):
    bm = geo.bm_cyl(r, r, z1 - z0, segs)
    bmesh.ops.translate(bm, vec=(0, 0, z0), verts=bm.verts)
    if tilt is not None:
        bmesh.ops.transform(bm, matrix=tilt, verts=bm.verts)
    bmesh.ops.translate(bm, vec=(x, y, 0), verts=bm.verts)
    return geo.obj_from_bm(f"{name}{suffix}", bm)


def col_hull(name, points, suffix="-convcolonly"):
    bm = bmesh.new()
    for p in points:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    return geo.obj_from_bm(f"{name}{suffix}", bm)


# ================================================================ export
def export(name, objects):
    os.makedirs(MODEL_DIR, exist_ok=True)
    path = os.path.join(MODEL_DIR, f"{name}.glb")
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True, export_apply=True,
        export_image_format="JPEG", export_jpeg_quality=90, export_cameras=False, export_lights=False,
        export_yup=True, export_materials="EXPORT", export_extras=False, export_animations=False,
        export_skins=False, export_morph=False, export_texcoords=True, export_normals=True)
    glb_strip_icc.process(path)        # mandatory: Godot rejects Blender's ICC JPEG segment
    return path


def alpha_info(path):
    import json
    import struct
    with open(path, "rb") as fh:
        data = fh.read()
    jlen = struct.unpack("<I", data[12:16])[0]
    j = json.loads(data[20:20 + jlen])
    return {m.get("name"): (m.get("alphaMode", "OPAQUE"), m.get("alphaCutoff"), m.get("doubleSided", False))
            for m in j.get("materials", [])}


# =============================================================== preview
def _world():
    w = geo._dusk_world()
    return w


def preview(name, objects, elev=6.0, azim=-30.0, dist_mul=1.0, target=None, lens=35.0, res=(1280, 960),
            ground="grass_winter", sun_elev=6.0, sun_azim=-150.0, fill=0.0):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    try:
        sc.eevee.taa_render_samples = 16
    except Exception:
        pass
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = 0.9
    sc.world = _world()
    mn = Vector((1e9, 1e9, 1e9))
    mx = Vector((-1e9, -1e9, -1e9))
    for o in objects:
        if o.type != "MESH" or "colonly" in o.name:
            continue
        for c in o.bound_box:
            wv = o.matrix_world @ Vector(c)
            mn = Vector(map(min, mn, wv))
            mx = Vector(map(max, mx, wv))
    ctr = (mn + mx) / 2 if target is None else Vector(target)
    radius = (mx - mn).length / 2
    tmp = []
    if ground:
        gs = max(10.0, radius * 6)
        bm = geo.bm_quad((-gs, -gs, 0), (gs, -gs, 0), (gs, gs, 0), (-gs, gs, 0))
        lay = bm.loops.layers.uv.new("UVMap")
        for f in bm.faces:
            for l in f.loops:
                l[lay].uv = (l.vert.co.x / 2.0, l.vert.co.y / 2.0)
        g = geo.obj_from_bm("PV_ground", bm)
        g.data.materials.append(mat("PV_" + ground, ground, folder=GROUND))
        g.location.z = -0.01
        tmp.append(g)
    sun_d = bpy.data.lights.new("PV_sun", "SUN")
    sun_d.energy = 3.0
    sun_d.color = (1.0, 0.62, 0.40)
    sun_d.angle = math.radians(1.0)
    sun = bpy.data.objects.new("PV_sun", sun_d)
    sun.rotation_euler = (math.radians(90 - sun_elev), 0, math.radians(sun_azim))
    sc.collection.objects.link(sun)
    tmp.append(sun)
    if fill > 0:
        fd = bpy.data.lights.new("PV_fill", "SUN")
        fd.energy = fill
        fd.color = (0.6, 0.7, 1.0)
        f = bpy.data.objects.new("PV_fill", fd)
        f.rotation_euler = (math.radians(40), 0, math.radians(azim + 20))
        sc.collection.objects.link(f)
        tmp.append(f)
    cam_d = bpy.data.cameras.new("PV_cam")
    cam_d.lens = lens
    cam_d.clip_start = 0.05
    cam_d.clip_end = 500
    cam = bpy.data.objects.new("PV_cam", cam_d)
    sc.collection.objects.link(cam)
    vfov = 2 * math.atan((36.0 * min(res) / max(res)) / 2 / lens)
    d = dist_mul * radius / math.sin(vfov / 2) + 0.3
    a, e = math.radians(azim), math.radians(elev)
    cam.location = ctr + Vector((math.sin(a) * math.cos(e) * d, -math.cos(a) * math.cos(e) * d, math.sin(e) * d))
    cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    tmp.append(cam)
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    sc.render.filepath = os.path.join(PREVIEW_DIR, f"{name}.png")
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    for o in tmp:
        bpy.data.objects.remove(o)
    return sc.render.filepath
