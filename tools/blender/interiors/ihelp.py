"""Shared helpers for the interior builders: placement frames, interior wall frames, face
splitting by material, export to arbitrary folders, glb inspection."""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.abspath(os.path.join(HERE, "..", "env"))
for p in (ENV, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import geo  # noqa: E402
from geo import MB, bm_box, bm_box_minmax, bm_cyl, bm_quad  # noqa: E402

ROOT = geo.ROOT
ENV_MODELS = os.path.join(ROOT, "game", "assets", "models", "env")
PROP_MODELS = os.path.join(ROOT, "game", "assets", "models", "props")
PREVIEW_DIR = os.path.join(HERE, "previews")
Z = Vector((0, 0, 1))


def roff(rng):
    return (rng.random(), rng.random())


def place(x, y, z=0.0, rot_deg=0.0):
    """Placement matrix: rotate about Z (degrees, 0 = prop front faces -Y) then translate."""
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(rot_deg), 4, "Z")


class Put:
    """Adds local-space geometry to an MB through a placement matrix and collects collision AABBs."""

    def __init__(self, mb, M=None, rng=None):
        self.mb = mb
        self.M = M if M is not None else Matrix.Identity(4)
        self.rng = rng
        self.cols = []        # (name, (x0,y0,z0,x1,y1,z1)) in world space

    def sub(self, M):
        p = Put(self.mb, self.M @ M, self.rng)
        p.cols = self.cols
        return p

    def bm(self, bm, mat, **kw):
        M = self.M @ kw.pop("matrix", Matrix.Identity(4))
        if "off" not in kw and self.rng is not None and kw.get("uv", "box") == "box":
            kw["off"] = roff(self.rng)
        self.mb.add_bm(bm, mat, matrix=M, **kw)

    def box(self, x0, y0, z0, x1, y1, z1, mat, bevel=0.0, segs=1, scale=1.0, **kw):
        self.bm(bm_box_minmax(min(x0, x1), min(y0, y1), min(z0, z1), max(x0, x1), max(y0, y1), max(z0, z1),
                              bevel, segs), mat, scale=scale, **kw)

    def col(self, name, x0, y0, z0, x1, y1, z1):
        pts = [self.M @ Vector((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
        mn = [min(p[i] for p in pts) for i in range(3)]
        mx = [max(p[i] for p in pts) for i in range(3)]
        self.cols.append((name, (*mn, *mx)))

    def pt(self, x, y, z):
        return self.M @ Vector((x, y, z))


class IFace:
    """Interior wall frame (same API as parts.Face): n points into the room, t = Z x n, so 'a' runs to
    the right of a viewer standing in the room facing the wall; d = offset into the room."""

    def __init__(self, origin, n, length):
        self.o = Vector(origin)
        self.n = Vector(n)
        self.t = Z.cross(self.n)
        self.length = length

    def p(self, a, d, z):
        return self.o + self.t * a + self.n * d + Z * z

    def box(self, a0, a1, d0, d1, z0, z1, bevel=0.0, segs=1):
        p0, p1 = self.p(a0, d0, z0), self.p(a1, d1, z1)
        return bm_box_minmax(min(p0.x, p1.x), min(p0.y, p1.y), min(p0.z, p1.z),
                             max(p0.x, p1.x), max(p0.y, p1.y), max(p0.z, p1.z), bevel, segs)

    def quad(self, a0, a1, z0, z1, d, uvs=None):
        return bm_quad(self.p(a0, d, z0), self.p(a1, d, z0), self.p(a1, d, z1), self.p(a0, d, z1), uvs)


def fbox(F, a0, a1, d0, d1, z0, z1):
    """World AABB (x0,y0,z0,x1,y1,z1) of a face-frame box."""
    p0, p1 = F.p(a0, d0, z0), F.p(a1, d1, z1)
    return (min(p0.x, p1.x), min(p0.y, p1.y), min(p0.z, p1.z), max(p0.x, p1.x), max(p0.y, p1.y), max(p0.z, p1.z))


def split_by(bm, key_fn):
    """Split a bmesh into several by a per-face key. Returns {key: bmesh}. Frees the input."""
    out = {}
    maps = {}
    bm.verts.index_update()
    for f in bm.faces:
        k = key_fn(f)
        if k not in out:
            out[k] = bmesh.new()
            maps[k] = {}
        dst, vm = out[k], maps[k]
        vs = []
        for v in f.verts:
            nv = vm.get(v.index)
            if nv is None:
                nv = dst.verts.new(v.co)
                vm[v.index] = nv
            vs.append(nv)
        try:
            dst.faces.new(vs)
        except ValueError:
            pass
    bm.free()
    return out


def lathe(profile, segs=16, cap_top=True, cap_bottom=True, uv_keep=False):
    """Revolve [(r, z), ...] (bottom to top) around Z. uv_keep: add planar disc UVs (x,y in [-1,1] of
    the max radius mapped to 0..1)."""
    bm = bmesh.new()
    rings = []
    for (r, z) in profile:
        ring = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    for k in range(len(rings) - 1):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
    if cap_bottom and profile[0][0] > 1e-4:
        bm.faces.new(list(reversed(rings[0])))
    if cap_top and profile[-1][0] > 1e-4:
        bm.faces.new(rings[-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if uv_keep:
        rmax = max(r for r, _ in profile)
        lay = bm.loops.layers.uv.new("UVMap")
        for f in bm.faces:
            for l in f.loops:
                l[lay].uv = (l.vert.co.x / rmax * 0.5 + 0.5, l.vert.co.y / rmax * 0.5 + 0.5)
    return bm


def tube(points, r, segs=6):
    bm = bmesh.new()
    pts = [Vector(p) for p in points]
    rings = []
    for k, p in enumerate(pts):
        if k == 0:
            d = pts[1] - pts[0]
        elif k == len(pts) - 1:
            d = pts[-1] - pts[-2]
        else:
            d = pts[k + 1] - pts[k - 1]
        d.normalize()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        u = d.cross(up).normalized()
        v = d.cross(u).normalized()
        rings.append([bm.verts.new(p + (u * math.cos(2 * math.pi * i / segs) + v * math.sin(2 * math.pi * i / segs)) * r)
                      for i in range(segs)])
    for k in range(len(rings) - 1):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def cyl_x(r, x0, x1, segs=10):
    """Cylinder along X."""
    bm = bm_cyl(r, r, x1 - x0, segs=segs)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "Y"))
    bmesh.ops.translate(bm, vec=(x0, 0, 0), verts=bm.verts)
    return bm


def cyl_y(r, y0, y1, segs=10):
    bm = bm_cyl(r, r, y1 - y0, segs=segs)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(-math.pi / 2, 3, "X"))
    bmesh.ops.translate(bm, vec=(0, y0, 0), verts=bm.verts)
    return bm


def collision_objs(cols, suffix="-colonly"):
    """[(name, aabb)] -> collision objects; duplicate names get a numeric suffix."""
    seen = {}
    out = []
    for name, bb in cols:
        n = seen.get(name, 0)
        seen[name] = n + 1
        nm = name if n == 0 else f"{name}{n}"
        out.append(geo.collision_box(nm, *bb, suffix=suffix))
    return out


def multi_box_obj(name, boxes):
    """One mesh object made of several boxes (e.g. a floor slab with a stairwell hole)."""
    bm = bmesh.new()
    for bb in boxes:
        geo.bm_join(bm, bm_box_minmax(*bb))
    return geo.obj_from_bm(name, bm)


def export_glb_path(path, objects):
    os.makedirs(os.path.dirname(path), exist_ok=True)
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


def strip_icc(path):
    import subprocess
    script = os.path.join(ROOT, "tools", "glb_strip_icc.py")
    py = sys.executable
    r = subprocess.run([py, script, path], capture_output=True, text=True)
    print(f"[icc] {r.stdout.strip()} {r.stderr.strip()}")
    if r.returncode != 0:
        raise RuntimeError("glb_strip_icc failed")
