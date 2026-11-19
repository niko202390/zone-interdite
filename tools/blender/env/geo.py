"""Blender geometry helpers for the environment kit: mesh builder, primitives,
UV projection, booleans, collision, materials, export, preview rendering."""
import json
import math
import os
import struct

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TEX_DIR = os.path.join(HERE, "out", "tex")
GROUND_DIR = os.path.join(ROOT, "game", "assets", "textures", "ground")
MODEL_DIR = os.path.join(ROOT, "game", "assets", "models", "env")
PREVIEW_DIR = os.path.join(HERE, "previews")


# ================================================================ scene
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.curves):
        for item in list(coll):
            coll.remove(item)


# ============================================================ materials
def _img(path, srgb):
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    return img


def _gltf_group():
    name = "glTF Material Output"
    g = bpy.data.node_groups.get(name)
    if g is None:
        g = bpy.data.node_groups.new(name, "ShaderNodeTree")
        g.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    return g


_MATS = {}


def tex_mat(name, albedo, normal=None, orm=None, folder=TEX_DIR, alpha=False, nstrength=1.0,
            rough=None, emission=None, estrength=0.0, tint=None):
    """Principled material from texture-set file names (without folder)."""
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    b = N["Principled BSDF"]
    ta = N.new("ShaderNodeTexImage")
    ta.image = _img(os.path.join(folder, albedo), True)
    ta.location = (-700, 300)
    if tint is not None:
        mixn = N.new("ShaderNodeMix")
        mixn.data_type = "RGBA"
        mixn.blend_type = "MULTIPLY"
        mixn.inputs["Factor"].default_value = 1.0
        mixn.inputs[7].default_value = (*tint, 1.0)
        L.new(ta.outputs["Color"], mixn.inputs[6])
        L.new(mixn.outputs[2], b.inputs["Base Color"])
    else:
        L.new(ta.outputs["Color"], b.inputs["Base Color"])
    if alpha:
        L.new(ta.outputs["Alpha"], b.inputs["Alpha"])
        m.surface_render_method = "BLENDED"
    if normal:
        tn = N.new("ShaderNodeTexImage")
        tn.image = _img(os.path.join(folder, normal), False)
        tn.location = (-700, -300)
        nm = N.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = nstrength
        L.new(tn.outputs["Color"], nm.inputs["Color"])
        L.new(nm.outputs["Normal"], b.inputs["Normal"])
    if orm:
        to = N.new("ShaderNodeTexImage")
        to.image = _img(os.path.join(folder, orm), False)
        to.location = (-700, 0)
        sep = N.new("ShaderNodeSeparateColor")
        L.new(to.outputs["Color"], sep.inputs["Color"])
        L.new(sep.outputs["Green"], b.inputs["Roughness"])
        L.new(sep.outputs["Blue"], b.inputs["Metallic"])
        grp = N.new("ShaderNodeGroup")
        grp.node_tree = _gltf_group()
        grp.location = (0, -500)
        L.new(sep.outputs["Red"], grp.inputs["Occlusion"])
    elif rough is not None:
        b.inputs["Roughness"].default_value = rough
    if emission is not None:
        b.inputs["Emission Color"].default_value = (*emission, 1.0)
        b.inputs["Emission Strength"].default_value = estrength
    _MATS[name] = m
    return m


def flat_mat(name, color, rough=0.5, metal=0.0, emission=None, estrength=0.0, alpha=None):
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emission is not None:
        b.inputs["Emission Color"].default_value = (*emission, 1.0)
        b.inputs["Emission Strength"].default_value = estrength
    if alpha is not None:
        b.inputs["Alpha"].default_value = alpha
        m.surface_render_method = "BLENDED"
    _MATS[name] = m
    return m


def clear_mat_cache():
    _MATS.clear()


def std(name):
    """Shared library of kit materials (lazy)."""
    T = lambda s: (f"{s}_albedo.png", f"{s}_normal.png", f"{s}_orm.png")
    if name == "Rubble":
        return tex_mat("Rubble", *T("rubble"))
    if name == "Granite":
        return tex_mat("Granite", *T("granite"))
    if name == "FieldStone":     # weathered, darker granite for dry walls
        return tex_mat("FieldStone", *T("granite"), tint=(0.64, 0.62, 0.58))
    if name == "Slate":
        return tex_mat("Slate", *T("slate"))
    if name == "Render":
        return tex_mat("Render", *T("render"))
    if name == "Clay":
        return tex_mat("Clay", *T("clay"))
    if name == "Iron":
        return tex_mat("Iron", *T("iron"))
    if name == "Burlap":
        return tex_mat("Burlap", *T("burlap"))
    if name == "Stripes":
        return tex_mat("Stripes", *T("stripes"))
    if name == "Paper":
        return tex_mat("Paper", *T("paper"))
    if name == "Setts":
        return tex_mat("Setts", *T("cobble"))
    if name.startswith("Paint_"):   # Paint_blue / Paint_green / Paint_oxblood / Paint_cream
        c = name.split("_", 1)[1]
        return tex_mat(name, f"wood_paint_{c}_albedo.png", "wood_paint_normal.png", "wood_paint_orm.png")
    if name.startswith("Wood_"):    # Wood_grey / Wood_dark / Wood_oak
        c = name.split("_", 1)[1]
        return tex_mat(name, f"wood_raw_{c}_albedo.png", "wood_raw_normal.png", "wood_raw_orm.png")
    if name == "DecalStreak":
        return tex_mat("DecalStreak", "decal_streak_albedo.png", alpha=True, rough=0.8)
    if name == "DecalDamp":
        return tex_mat("DecalDamp", "decal_damp_albedo.png", alpha=True, rough=0.45)
    if name == "WindowGlass":
        return flat_mat("WindowGlass", (0.015, 0.018, 0.02), rough=0.06)
    if name == "WindowGlow":
        return flat_mat("WindowGlow", (0.30, 0.20, 0.10), rough=0.2, emission=(1.0, 0.58, 0.26), estrength=2.5)
    if name == "Interior":
        return flat_mat("Interior", (0.012, 0.011, 0.010), rough=0.95)
    if name == "Zinc":
        return flat_mat("Zinc", (0.42, 0.43, 0.44), rough=0.55, metal=0.85)
    if name == "Ink":
        return flat_mat("Ink", (0.02, 0.02, 0.02), rough=0.9)
    if name == "SignPaint":
        return flat_mat("SignPaint", (0.78, 0.70, 0.48), rough=0.6)
    if name == "TabacRed":
        return flat_mat("TabacRed", (0.48, 0.05, 0.04), rough=0.45)
    if name == "InsulatorGlass":
        return flat_mat("InsulatorGlass", (0.20, 0.38, 0.32), rough=0.08)
    if name == "LampGlass":
        return flat_mat("LampGlass", (0.06, 0.065, 0.06), rough=0.25)
    if name == "BlackPaint":
        return flat_mat("BlackPaint", (0.025, 0.025, 0.025), rough=0.6)
    raise KeyError(name)


# ========================================================= mesh builder
class MB:
    """Accumulates polygons with materials and UVs, then builds one object."""

    def __init__(self):
        self.verts, self.faces, self.mats, self.uvs, self.smooth = [], [], [], [], []
        self.mat_names = []

    def _mi(self, mat):
        if mat not in self.mat_names:
            self.mat_names.append(mat)
        return self.mat_names.index(mat)

    def add_bm(self, bm, mat, uv="box", scale=0.5, off=(0.0, 0.0), smooth=False, matrix=None,
               smooth_angle=35.0):
        """uv: 'box' (world tri-planar per face), 'keep' (use bm uv layer), or callable(co, normal)->(u,v).
        scale: UV units per metre."""
        if matrix is not None:
            bmesh.ops.transform(bm, matrix=matrix, verts=bm.verts)
            if matrix.to_3x3().determinant() < 0:
                bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.normal_update()
        if smooth:
            sharp = [e for e in bm.edges if e.is_manifold and e.calc_face_angle(0) > math.radians(smooth_angle)]
            if sharp:
                bmesh.ops.split_edges(bm, edges=sharp)
            bm.normal_update()
        bm.verts.index_update()
        mi = self._mi(mat)
        base = len(self.verts)
        self.verts.extend([v.co.copy() for v in bm.verts])
        uvl = bm.loops.layers.uv.active if uv == "keep" else None
        for f in bm.faces:
            self.faces.append([base + v.index for v in f.verts])
            self.mats.append(mi)
            self.smooth.append(smooth)
            n = f.normal
            if uv == "keep":
                self.uvs.append([tuple(l[uvl].uv) for l in f.loops])
            elif uv == "box":
                self.uvs.append([box_uv(l.vert.co, n, scale, off) for l in f.loops])
            else:
                self.uvs.append([uv(l.vert.co, n) for l in f.loops])
        bm.free()

    def add_mesh_data(self, me, mat, **kw):
        bm = bmesh.new()
        bm.from_mesh(me)
        self.add_bm(bm, mat, **kw)

    def build(self, name, collection=None):
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in self.verts], [], self.faces)
        for mname in self.mat_names:
            me.materials.append(std(mname))
        me.polygons.foreach_set("material_index", self.mats)
        me.polygons.foreach_set("use_smooth", self.smooth)
        uvl = me.uv_layers.new(name="UVMap")
        flat = [c for face in self.uvs for uvp in face for c in uvp]
        uvl.data.foreach_set("uv", flat)
        me.validate(clean_customdata=False)
        me.update()
        ob = bpy.data.objects.new(name, me)
        (collection or bpy.context.scene.collection).objects.link(ob)
        return ob

    def tri_count(self):
        return sum(len(f) - 2 for f in self.faces)


def box_uv(co, n, scale=0.5, off=(0.0, 0.0)):
    ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
    if az >= ax and az >= ay:
        u, v = co.x, co.y if n.z > 0 else -co.y
    elif ax >= ay:
        u, v = (co.y if n.x > 0 else -co.y), co.z
    else:
        u, v = (-co.x if n.y > 0 else co.x), co.z
    return (u * scale + off[0], v * scale + off[1])


# ============================================================ primitives
def bm_box(cx, cy, cz, sx, sy, sz, bevel=0.0, segs=1, rot=None):
    """Axis box centred at (cx,cy,cz) with full sizes; optional bevel and rotation (Euler XYZ radians)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    if bevel > 0:
        b = min(bevel, sx * 0.45, sy * 0.45, sz * 0.45)
        bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=b, segments=segs,
                        profile=0.5, affect="EDGES", clamp_overlap=True)
    if rot is not None:
        from mathutils import Euler
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Euler(rot, "XYZ").to_matrix())
    bmesh.ops.translate(bm, vec=(cx, cy, cz), verts=bm.verts)
    return bm


def bm_box_minmax(x0, y0, z0, x1, y1, z1, bevel=0.0, segs=1):
    return bm_box((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2, x1 - x0, y1 - y0, z1 - z0, bevel, segs)


def bm_cyl(r1, r2, depth, segs=16, cap=True):
    """Cylinder/cone along +Z from z=0 to z=depth."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=segs, radius1=r1, radius2=r2, depth=depth)
    bmesh.ops.translate(bm, vec=(0, 0, depth / 2), verts=bm.verts)
    return bm


def bm_prism(profile, x0, x1):
    """Extrude a 2D profile [(y,z),...] (CCW seen from +X) along X from x0 to x1."""
    bm = bmesh.new()
    a = [bm.verts.new((x0, y, z)) for (y, z) in profile]
    b = [bm.verts.new((x1, y, z)) for (y, z) in profile]
    n = len(profile)
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_quad(p0, p1, p2, p3, uvs=None):
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in (p0, p1, p2, p3)]
    f = bm.faces.new(vs)
    if uvs:
        lay = bm.loops.layers.uv.new("UVMap")
        for l, uvp in zip(f.loops, uvs):
            l[lay].uv = uvp
    return bm


def bm_from_object(ob):
    """Evaluated (modifiers applied) mesh of an object as bmesh in world space."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    me.transform(ob.matrix_world)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    return bm


def obj_from_bm(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def boolean(base_bm, cutters, op="DIFFERENCE"):
    """Apply EXACT boolean of base against a list of bmesh cutters. Returns new bmesh."""
    base = obj_from_bm("__bool_base", base_bm)
    cut_bm = bmesh.new()
    for c in cutters:
        bm_join(cut_bm, c)
        c.free()
    cut = obj_from_bm("__bool_cut", cut_bm)
    mod = base.modifiers.new("b", "BOOLEAN")
    mod.operation = op
    mod.solver = "EXACT"
    mod.object = cut
    out = bm_from_object(base)
    for o in (base, cut):
        me = o.data
        bpy.data.objects.remove(o)
        bpy.data.meshes.remove(me)
    return out


def bm_join(dst, src):
    """Append geometry of bmesh src into dst."""
    src.verts.index_update()
    vmap = [dst.verts.new(v.co) for v in src.verts]
    for f in src.faces:
        try:
            dst.faces.new([vmap[v.index] for v in f.verts])
        except ValueError:
            pass
    return dst


def union(bms):
    """Union several closed bmeshes with EXACT boolean (sequential)."""
    acc = bms[0]
    for other in bms[1:]:
        acc = boolean(acc, [other], "UNION")
    return acc


def text_bm(body, size, extrude=0.0, align="CENTER", font=None, spacing=1.0, res=3):
    """Text as a flat mesh in the XY plane (reading along +X, up +Y), centred."""
    cu = bpy.data.curves.new("__txt", type="FONT")
    cu.resolution_u = res
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.space_character = spacing
    if font:
        cu.font = font
    ob = bpy.data.objects.new("__txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    bm = bm_from_object(ob)
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    return bm


# ============================================================ collision
def collision_box(name, x0, y0, z0, x1, y1, z1, suffix="-colonly"):
    bm = bm_box_minmax(x0, y0, z0, x1, y1, z1)
    return obj_from_bm(f"{name}{suffix}", bm)


def collision_bm(name, bm, suffix="-convcolonly"):
    return obj_from_bm(f"{name}{suffix}", bm)


def empty(name, loc):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "PLAIN_AXES"
    e.empty_display_size = 0.1
    e.location = loc
    bpy.context.scene.collection.objects.link(e)
    return e


# ================================================================ export
def export_glb(name, objects):
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
    return path


def inspect_glb(path):
    """Return dict: triangles (render meshes only), node names, images embedded?, alpha modes."""
    with open(path, "rb") as fh:
        data = fh.read()
    jlen = struct.unpack("<I", data[12:16])[0]
    j = json.loads(data[20:20 + jlen])
    tris = 0
    nodes = [n.get("name", "") for n in j.get("nodes", [])]
    for node in j.get("nodes", []):
        if "mesh" not in node or node.get("name", "").endswith(("colonly", "convcolonly")):
            continue
        for prim in j["meshes"][node["mesh"]]["primitives"]:
            acc = j["accessors"][prim["indices"]] if "indices" in prim else j["accessors"][prim["attributes"]["POSITION"]]
            tris += acc["count"] // 3
    imgs = j.get("images", [])
    embedded = all("bufferView" in im for im in imgs)
    alpha = {m.get("name"): m.get("alphaMode", "OPAQUE") for m in j.get("materials", [])}
    return dict(tris=tris, nodes=nodes, images=len(imgs), embedded=embedded,
                mime=sorted({im.get("mimeType", "?") for im in imgs}), alpha=alpha,
                size_mb=round(len(data) / 1e6, 1))


# =============================================================== preview
def _dusk_world():
    w = bpy.data.worlds.new("Dusk")
    w.use_nodes = True
    nt = w.node_tree
    N, L = nt.nodes, nt.links
    bg = N["Background"]
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    ramp = N.new("ShaderNodeValToRGB")
    L.new(tc.outputs["Generated"], sep.inputs[0])
    # 'Generated' on world = view direction; z in [-1,1]
    mp = N.new("ShaderNodeMapRange")
    mp.inputs["From Min"].default_value = -0.1
    mp.inputs["From Max"].default_value = 0.6
    L.new(sep.outputs["Z"], mp.inputs["Value"])
    L.new(mp.outputs["Result"], ramp.inputs["Fac"])
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.55, 0.32, 0.20, 1)
    cr.elements[1].position = 1.0
    cr.elements[1].color = (0.05, 0.08, 0.16, 1)
    mid = cr.elements.new(0.25)
    mid.color = (0.28, 0.25, 0.30, 1)
    L.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.6
    return w


def render_preview(name, objects, ground="cobble", dist_mul=1.0, elev=12.0, azim=-35.0, res=(1280, 720),
                   target=None, lens=35.0, extra=None):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    try:
        sc.eevee.taa_render_samples = 48
    except Exception:
        pass
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.exposure = 0.6
    except Exception:
        pass
    sc.world = _dusk_world()
    # bounds
    mn = Vector((1e9, 1e9, 1e9))
    mx = Vector((-1e9, -1e9, -1e9))
    for o in objects:
        if o.type != "MESH" or o.name.endswith(("colonly", "convcolonly")):
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mn = Vector(map(min, mn, w))
            mx = Vector(map(max, mx, w))
    ctr = (mn + mx) / 2 if target is None else Vector(target)
    size = (mx - mn).length
    radius = size / 2
    # ground plane
    tmp = []
    if ground:
        gm = tex_mat(f"PV_{ground}", f"{ground}_albedo.png", f"{ground}_normal.png", f"{ground}_orm.png", folder=GROUND_DIR)
        gs = max(8.0, size * 3)
        bm = bm_quad((-gs, -gs, 0), (gs, -gs, 0), (gs, gs, 0), (-gs, gs, 0))
        lay = bm.loops.layers.uv.new("UVMap")
        for f in bm.faces:
            for l in f.loops:
                l[lay].uv = (l.vert.co.x / 2.0, l.vert.co.y / 2.0)
        g = obj_from_bm("PV_ground", bm)
        g.data.materials.append(gm)
        g.location.z = -0.005
        tmp.append(g)
    # sun
    sun_d = bpy.data.lights.new("PV_sun", "SUN")
    sun_d.energy = 2.2
    sun_d.color = (1.0, 0.62, 0.38)
    sun_d.angle = math.radians(2.0)
    sun = bpy.data.objects.new("PV_sun", sun_d)
    sun.rotation_euler = (math.radians(84), 0, math.radians(-140))
    sc.collection.objects.link(sun)
    tmp.append(sun)
    if extra:
        tmp += extra()
    # camera
    cam_d = bpy.data.cameras.new("PV_cam")
    cam_d.lens = lens
    cam_d.clip_start = 0.02
    cam = bpy.data.objects.new("PV_cam", cam_d)
    sc.collection.objects.link(cam)
    vfov = 2 * math.atan((36.0 * res[1] / res[0]) / 2 / lens)
    d = dist_mul * radius / math.sin(vfov / 2) + 0.3
    a, e = math.radians(azim), math.radians(elev)
    cam.location = ctr + Vector((math.sin(a) * math.cos(e) * d, -math.cos(a) * math.cos(e) * d, math.sin(e) * d))
    direction = ctr - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    tmp.append(cam)
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    sc.render.filepath = os.path.join(PREVIEW_DIR, f"{name}.png")
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    for o in tmp:
        bpy.data.objects.remove(o)
    return sc.render.filepath
