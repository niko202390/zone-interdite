"""Shared helpers for the town landmark builders: environment setup (paths, materials), face-frame
prisms, pointed/round arches, text, collision lists, separate swinging nodes (doors, hatches)."""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.abspath(os.path.join(HERE, "..", "env"))
INT = os.path.abspath(os.path.join(HERE, "..", "interiors"))
for p in (ENV, INT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import geo  # noqa: E402
from geo import MB, bm_box, bm_box_minmax, bm_cyl, bm_prism, bm_quad  # noqa: E402
from parts import FACES, Face, Frame, Opening, Roof, roff, text  # noqa: E402

ROOT = geo.ROOT
MODEL_DIR = os.path.join(ROOT, "game", "assets", "models", "town")
PREVIEW_DIR = os.path.join(HERE, "previews")
Z = Vector((0, 0, 1))
PI = math.pi


def setup():
    import itex
    import ttex
    geo.MODEL_DIR = MODEL_DIR
    geo.PREVIEW_DIR = PREVIEW_DIR
    itex.install()
    ttex.install()


# ------------------------------------------------------------------ frames
class WFace:
    """Wall frame anywhere: origin o on the wall plane, outward normal n (horizontal), t = n x Z
    rotated so a runs to the right of a viewer facing the wall from outside (same as parts.Face)."""

    def __init__(self, origin, n, length=0.0, name="w"):
        self.o = Vector(origin)
        self.n = Vector(n).normalized()
        self.t = Z.cross(self.n)
        self.length = length
        self.name = name

    def p(self, a, d, z):
        return self.o + self.t * a + self.n * d + Z * z

    def box(self, a0, a1, d0, d1, z0, z1, bevel=0.0, segs=1):
        p0, p1 = self.p(a0, d0, z0), self.p(a1, d1, z1)
        return bm_box_minmax(min(p0.x, p1.x), min(p0.y, p1.y), min(p0.z, p1.z),
                             max(p0.x, p1.x), max(p0.y, p1.y), max(p0.z, p1.z), bevel, segs)

    def quad(self, a0, a1, z0, z1, d, uvs=None):
        return bm_quad(self.p(a0, d, z0), self.p(a1, d, z0), self.p(a1, d, z1), self.p(a0, d, z1), uvs)


def face_prism(F, poly, d0, d1):
    """Extrude polygon [(a, z), ...] (any winding) in face frame F from depth d0 to d1."""
    bm = bmesh.new()
    A = [bm.verts.new(F.p(a, d0, z)) for (a, z) in poly]
    B = [bm.verts.new(F.p(a, d1, z)) for (a, z) in poly]
    bm.faces.new(A)
    bm.faces.new(list(reversed(B)))
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((A[i], A[j], B[j], B[i]))
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def face_poly(F, poly, d):
    bm = bmesh.new()
    vs = [bm.verts.new(F.p(a, d, z)) for (a, z) in poly]
    f = bm.faces.new(vs)
    bm.normal_update()
    if f.normal.dot(F.n) < 0:
        bmesh.ops.reverse_faces(bm, faces=[f])
    return bm


# ------------------------------------------------------------------ arches
def pointed_arch(ac, z_spring, w, rise_k=1.0, n=10):
    """Equilateral-ish pointed arch outline (open polyline) from the left springer over the apex to the
    right springer. rise_k scales the arc radius (1.0 = equilateral, radius = w)."""
    r = w * rise_k
    half = w / 2
    cl = ac - half + r
    cr = ac + half - r
    zt = z_spring + math.sqrt(max(r * r - (r - half) ** 2, 0.0))
    pts = []
    a0 = PI
    a1 = math.atan2(zt - z_spring, ac - cl)
    for i in range(n + 1):
        t = a0 + (a1 - a0) * i / n
        pts.append((cl + r * math.cos(t), z_spring + r * math.sin(t)))
    b0 = math.atan2(zt - z_spring, ac - cr)
    for i in range(1, n + 1):
        t = b0 + (0.0 - b0) * i / n
        pts.append((cr + r * math.cos(t), z_spring + r * math.sin(t)))
    return pts, zt


def round_arch(ac, z_spring, w, n=10):
    pts = []
    for i in range(n + 1):
        t = PI - PI * i / n
        pts.append((ac + w / 2 * math.cos(t), z_spring + w / 2 * math.sin(t)))
    return pts, z_spring + w / 2


def arch_opening_poly(ac, z0, w, z_spring, kind="pointed", rise_k=1.0, n=10):
    pts, zt = (pointed_arch(ac, z_spring, w, rise_k, n) if kind == "pointed" else round_arch(ac, z_spring, w, n))
    return [(ac - w / 2, z0)] + pts + [(ac + w / 2, z0)], zt


def offset_arch(ac, z_spring, w, off, kind="pointed", rise_k=1.0, n=10):
    """Arch outline offset outward by off (concentric for the same centres)."""
    if kind == "pointed":
        r = w * rise_k
        half = w / 2
        cl = ac - half + r
        cr = ac + half - r
        R = r + off
        zt = z_spring + math.sqrt(max(R * R - (ac - cl) ** 2, 0.0))
        a1 = math.atan2(zt - z_spring, ac - cl)
        pts = [(cl + R * math.cos(PI + (a1 - PI) * i / n), z_spring + R * math.sin(PI + (a1 - PI) * i / n)) for i in range(n + 1)]
        b0 = math.atan2(zt - z_spring, ac - cr)
        pts += [(cr + R * math.cos(b0 * (1 - i / n)), z_spring + R * math.sin(b0 * (1 - i / n))) for i in range(1, n + 1)]
        return pts
    R = w / 2 + off
    return [(ac + R * math.cos(PI - PI * i / n), z_spring + R * math.sin(PI - PI * i / n)) for i in range(n + 1)]


def arch_ring(mb, F, ac, z_spring, w, thick, d0, d1, mat, rng, kind="pointed", rise_k=1.0, n=10, joints=True):
    """Voussoir ring between the opening arc and an outer offset arc, as separate stones."""
    inner = offset_arch(ac, z_spring, w, 0.0, kind, rise_k, n)
    outer = offset_arch(ac, z_spring, w, thick, kind, rise_k, n)
    m = len(inner)
    step = 2 if joints else 1
    for i in range(0, m - 1, step):
        j = min(i + step, m - 1)
        seg_in = inner[i:j + 1]
        seg_out = outer[i:j + 1]
        poly = seg_in + list(reversed(seg_out))
        bm = face_prism(F, poly, d0, d1)
        if joints:
            # shrink a hair to show the joints
            c = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)
            for v in bm.verts:
                v.co = c + (v.co - c) * 0.985
        mb.add_bm(bm, mat, off=roff(rng))


# -------------------------------------------------------------- misc mesh
def lathe(profile, segs=16, cap_top=True, cap_bottom=True):
    import ihelp
    return ihelp.lathe(profile, segs, cap_top, cap_bottom)


def tube(points, r, segs=6):
    import ihelp
    return ihelp.tube(points, r, segs)


def cyl_between(p0, p1, r, segs=8, r1=None):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    bm = bm_cyl(r, r if r1 is None else r1, L, segs=segs)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bmesh.ops.transform(bm, matrix=Matrix.Translation(p0) @ q.to_matrix().to_4x4(), verts=bm.verts)
    return bm


def T(x, y=0.0, z=0.0):
    return Matrix.Translation((x, y, z))


def R(deg, axis="Z"):
    return Matrix.Rotation(math.radians(deg), 4, axis)


def xform(bm, M):
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    if M.to_3x3().determinant() < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return bm


def text_on(mb, F, body, a, z, d, size, mat, extrude=0.003, spacing=1.0):
    text(mb, F, body, a, z, d, size, mat, extrude=extrude, spacing=spacing)


# -------------------------------------------------------------- collision
class Cols:
    def __init__(self):
        self.items = []

    def box(self, name, x0, y0, z0, x1, y1, z1):
        self.items.append((name, (min(x0, x1), min(y0, y1), min(z0, z1), max(x0, x1), max(y0, y1), max(z0, z1))))

    def fbox(self, name, F, a0, a1, d0, d1, z0, z1):
        p0, p1 = F.p(a0, d0, z0), F.p(a1, d1, z1)
        self.box(name, p0.x, p0.y, p0.z, p1.x, p1.y, p1.z)

    def hull(self, name, points):
        self.items.append((name, ("hull", [Vector(p) for p in points])))

    def prism(self, name, profile, x0, x1):
        self.items.append((name, ("prism", profile, x0, x1)))

    def build(self):
        seen = {}
        out = []
        for name, spec in self.items:
            k = seen.get(name, 0)
            seen[name] = k + 1
            nm = name if k == 0 else f"{name}{k}"
            if spec[0] == "hull":
                bm = bmesh.new()
                for p in spec[1]:
                    bm.verts.new(p)
                bmesh.ops.convex_hull(bm, input=bm.verts)
                out.append(geo.obj_from_bm(f"{nm}-convcolonly", bm))
            elif spec[0] == "prism":
                out.append(geo.obj_from_bm(f"{nm}-convcolonly", bm_prism(spec[1], spec[2], spec[3])))
            else:
                out.append(geo.collision_box(nm, *spec))
        return out


# -------------------------------------------------------- swinging nodes
def pivot_object(name, mb, pivot, col_boxes=()):
    """Build mb as its own object whose origin sits at `pivot` (world). col_boxes: world AABBs that
    become `<name>_col-colonly` children so the collision moves with the node."""
    ob = mb.build(name)
    pv = Vector(pivot)
    ob.data.transform(Matrix.Translation(-pv))
    ob.location = pv
    out = [ob]
    for i, bb in enumerate(col_boxes):
        c = geo.collision_box(f"{name}_col" + ("" if i == 0 else str(i)), *bb)
        c.data.transform(Matrix.Translation(-pv))
        c.parent = ob
        c.matrix_parent_inverse = Matrix.Identity(4)
        c.location = (0, 0, 0)
        out.append(c)
    return out


def panel_door(mb, F, la0, la1, d_in, d_out, z0, z1, paint, rng, glazed_top=False, panels=2):
    """Panelled (bourgeois) door leaf in a face frame: stiles, rails, raised panels, optional glazed
    upper with a grille, brass knob and letter plate. Built into mb in world space."""
    lw = la1 - la0
    st = 0.11
    mb.add_bm(F.box(la0, la1, d_in, d_out, z0, z1), paint, scale=1.0, off=roff(rng))
    # moulded rails/stiles proud of the slab on the outside
    for (a0, a1) in ((la0, la0 + st), (la1 - st, la1)):
        mb.add_bm(F.box(a0, a1, d_out, d_out + 0.012, z0, z1), paint, scale=1.0)
    zs = [z0, z0 + 0.22, z0 + (z1 - z0) * 0.48, z1 - 0.14, z1]
    for zc in (zs[1], zs[2], zs[3]):
        mb.add_bm(F.box(la0 + st, la1 - st, d_out, d_out + 0.012, zc - 0.06, zc + 0.06), paint, scale=1.0)
    mb.add_bm(F.box(la0 + st, la1 - st, d_out, d_out + 0.012, z0, z0 + 0.12), paint, scale=1.0)
    # lower raised panel
    mb.add_bm(F.box(la0 + st + 0.05, la1 - st - 0.05, d_out, d_out + 0.02, zs[1] + 0.11, zs[2] - 0.11, bevel=0.012, segs=1),
              paint, scale=1.0)
    if glazed_top:
        g0, g1 = zs[2] + 0.06, zs[3] - 0.06
        mb.add_bm(F.quad(la0 + st, la1 - st, g0, g1, d_out + 0.004), "WindowGlass")
        n = 4
        for k in range(1, n):
            ac = la0 + st + (lw - 2 * st) * k / n
            mb.add_bm(F.box(ac - 0.008, ac + 0.008, d_out + 0.004, d_out + 0.02, g0, g1), "Iron", scale=2.0)
        for zc in (g0 + (g1 - g0) * 0.33, g0 + (g1 - g0) * 0.66):
            mb.add_bm(F.box(la0 + st, la1 - st, d_out + 0.004, d_out + 0.02, zc - 0.008, zc + 0.008), "Iron", scale=2.0)
    else:
        mb.add_bm(F.box(la0 + st + 0.05, la1 - st - 0.05, d_out, d_out + 0.02, zs[2] + 0.11, zs[3] - 0.11, bevel=0.012, segs=1),
                  paint, scale=1.0)
    ka = la1 - 0.07
    mb.add_bm(F.box(ka - 0.025, ka + 0.025, d_out, d_out + 0.01, 0.95, 1.12), "Brass", scale=2.0)
    knob = lathe([(0.0, 0.0), (0.02, 0.0), (0.028, 0.03), (0.0, 0.05)], segs=10)
    M = Matrix.Translation(F.p(ka, d_out + 0.01, 1.04)) @ _to_face(F)
    mb.add_bm(knob, "Brass", scale=2.0, matrix=M)
    mb.add_bm(F.box(la0 + lw * 0.35, la0 + lw * 0.65, d_out + 0.012, d_out + 0.02, zs[1] - 0.03, zs[1] + 0.03), "Brass", scale=2.0)


def _to_face(F):
    """Rotation taking local +Z to the face normal (for knobs, rings)."""
    q = Vector((0, 0, 1)).rotation_difference(F.n)
    return q.to_matrix().to_4x4()


def door_node(name, F, la0, la1, d_in, d_out, z0, z1, paint, rng, kind="plank", glazed_top=False):
    """Separate Door object, origin on the hinge (la0 edge, inner face). Rotating +90 deg about Blender +Z
    (Godot +Y) swings it inward. Returns (objects, tris, hinge)."""
    import shell
    dmb = MB()
    if kind == "plank":
        shell.plank_door_leaf(dmb, F, la0, la1, d_in, d_out, z0, z1, paint, rng)
    else:
        panel_door(dmb, F, la0, la1, d_in, d_out, z0, z1, paint, rng, glazed_top=glazed_top)
    hinge = F.p(la0, d_in, z0)
    p0, p1 = F.p(la0, d_in - 0.005, z0), F.p(la1, d_out + 0.005, z1)
    bb = (min(p0.x, p1.x), min(p0.y, p1.y), z0, max(p0.x, p1.x), max(p0.y, p1.y), z1)
    tris = dmb.tri_count()
    objs = pivot_object(name, dmb, hinge, [bb])
    return objs, tris, hinge


# -------------------------------------------------------------- sandbags
def sandbag_run(mb, cols, p0, p1, rows, rng, name="Sandbags", double=True):
    """Stacked sandbag wall from p0 to p1 (ground points)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    ang = math.atan2(d.y, d.x)
    Mw = Matrix.Translation(p0) @ Matrix.Rotation(ang, 4, "Z")
    bl, bw, bh = 0.56, 0.32, 0.15
    z = bh / 2 - 0.02
    for r in range(rows):
        depth_rows = 2 if (double and r < rows - 1) else 1
        for dr in range(depth_rows):
            y = (dr - 0.5) * bw * 0.95 if depth_rows == 2 else 0.0
            x = bl / 2 - (bl / 2 if r % 2 else 0.0)
            while x - bl / 2 < L - 0.05:
                xa, xb = max(x - bl / 2, 0.0), min(x + bl / 2, L)
                if xb - xa > 0.16:
                    bm = _bag((xb - xa) * rng.uniform(0.96, 1.0), bw * rng.uniform(0.95, 1.05), bh * rng.uniform(0.9, 1.1), rng)
                    M = (Mw @ Matrix.Translation(((xa + xb) / 2 + rng.uniform(-0.01, 0.01), y + rng.uniform(-0.02, 0.02), z))
                         @ Matrix.Rotation(rng.uniform(-0.06, 0.06), 4, "Z") @ Matrix.Rotation(rng.uniform(-0.04, 0.04), 4, "X"))
                    mb.add_bm(bm, "Burlap", scale=2.0, off=roff(rng), smooth=True, smooth_angle=70, matrix=M)
                x += bl * 0.98
        z += bh * 0.82
    w = bw if double else bw / 2
    pts = [Mw @ Vector((x, y, zz)) for x in (0, L) for y in (-w, w) for zz in (0, z + 0.03)]
    cols.hull(name, pts)


def _bag(sx, sy, sz, rng, cuts=2):
    """Lighter version of props._bag (sandbag pillow) for long runs."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=cuts, use_grid_fill=True)
    ph = rng.uniform(0, 6.28)
    for v in bm.verts:
        co = v.co * 2.0
        r = co.length
        sph = co.normalized() * 0.92 if r > 0 else co
        co = co.lerp(sph, 0.45)
        co.z *= 0.75 + 0.25 * (1 - co.x * co.x)
        co.y *= 0.85 + 0.15 * (1 - co.x * co.x)
        co.z += 0.06 * math.sin(co.x * 3 + ph)
        v.co = Vector((co.x * sx / 2, co.y * sy / 2, co.z * sz / 2))
    return bm


# ------------------------------------------------------------------ slates
def slate_plane(mb, origin, tv, sv, length_t, length_s, rng, exclude=None):
    """Slate courses on an arbitrary plane (origin at eave start, tv along eave, sv up-slope)."""
    from parts import slate_rows
    tv, sv = Vector(tv).normalized(), Vector(sv).normalized()
    nv = tv.cross(sv).normalized()
    if nv.z < 0:
        nv = -nv
    slate_rows(mb, origin, tv, sv, nv, length_t, length_s, rng, exclude=exclude)
    return nv


def gable_roof(mb, x0, x1, y_c, half_span, z_eave, pitch_deg, rng, ov_end=0.15, ridge=True, under=True,
               axis="x"):
    """Simple slate gable roof running along X (axis='x') or Y; eaves at z_eave, ridge over y_c.
    Returns (ridge_z, collision profile prism args)."""
    p = math.radians(pitch_deg)
    cp, sp = math.cos(p), math.sin(p)
    s_len = half_span / cp
    zr = z_eave + half_span * math.tan(p)
    L = (x1 - x0) + 2 * ov_end
    for sign in (-1, 1):
        if axis == "x":
            origin = Vector((x0 - ov_end, y_c + sign * half_span, z_eave))
            tv = Vector((1, 0, 0))
            sv = Vector((0, -sign * cp, sp))
        else:
            origin = Vector((y_c + sign * half_span, x0 - ov_end, z_eave))
            tv = Vector((0, 1, 0))
            sv = Vector((-sign * cp, 0, sp))
        nv = slate_plane(mb, origin, tv, sv, L, s_len + 0.03, rng)
        if under:
            bm = bmesh.new()
            pts = [origin + sv * ss + nv * off for (ss, off) in ((0, 0.0), (s_len, 0.0), (s_len, -0.12), (0, -0.12))]
            A = [bm.verts.new(q) for q in pts]
            B = [bm.verts.new(q + tv * L) for q in pts]
            bm.faces.new(A)
            bm.faces.new(list(reversed(B)))
            for k in range(4):
                j = (k + 1) % 4
                bm.faces.new((A[k], A[j], B[j], B[k]))
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            mb.add_bm(bm, "Wood_dark", scale=1.0)
    if ridge:
        if axis == "x":
            mb.add_bm(bm_box_minmax(x0 - ov_end, y_c - 0.09, zr - 0.02, x1 + ov_end, y_c + 0.09, zr + 0.07, bevel=0.03, segs=2), "Zinc")
        else:
            mb.add_bm(bm_box_minmax(y_c - 0.09, x0 - ov_end, zr - 0.02, y_c + 0.09, x1 + ov_end, zr + 0.07, bevel=0.03, segs=2), "Zinc")
    return zr


# ------------------------------------------------------------- MB merging
def mb_merge(dst, src, M=None):
    """Append all polygons of MB src into MB dst, transforming vertices by M (rotation/translation)."""
    base = len(dst.verts)
    if M is None:
        dst.verts.extend([v.copy() for v in src.verts])
    else:
        dst.verts.extend([M @ v for v in src.verts])
    remap = [dst._mi(m) for m in src.mat_names]
    for f, mi, uv, sm in zip(src.faces, src.mats, src.uvs, src.smooth):
        dst.faces.append([base + i for i in f])
        dst.mats.append(remap[mi])
        dst.uvs.append(uv)
        dst.smooth.append(sm)
    return dst


def mb_transform(mb, M):
    mb.verts = [M @ v for v in mb.verts]
    return mb
