"""Geometry helpers for the character builders (Blender Python).

Parts are built as separate Blender mesh objects with metric UVs ("UVMap"), material slots,
optional float vertex attributes and vertex-group skin weights, then joined into one mesh.
"""
import math
from math import cos, pi, sin, sqrt

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


def V(*a):
    return Vector(a[0]) if len(a) == 1 else Vector(a)


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def sstep(e0, e1, x):
    if e1 == e0:
        return 1.0 if x >= e1 else 0.0
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def interp_table(table, z):
    """Piecewise-linear interpolation of rows (z, v0, v1, ...) sorted by z; returns tuple."""
    if z <= table[0][0]:
        return table[0][1:]
    if z >= table[-1][0]:
        return table[-1][1:]
    for i in range(len(table) - 1):
        z0, z1 = table[i][0], table[i + 1][0]
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            t = t * t * (3 - 2 * t) * 0.35 + t * 0.65  # soften the corners a little
            return tuple(lerp(a, b, t) for a, b in zip(table[i][1:], table[i + 1][1:]))
    return table[-1][1:]


def catmull(pts, n=8, closed=False):
    """Catmull-Rom resample through pts, n samples per span."""
    P = [Vector(p) for p in pts]
    if closed:
        P = [P[-1]] + P + [P[0], P[1]]
    else:
        P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(P[-2].copy())
    return out


def resample(pts, step):
    """Resample a polyline at roughly uniform spacing."""
    pts = [Vector(p) for p in pts]
    L = [0.0]
    for i in range(1, len(pts)):
        L.append(L[-1] + (pts[i] - pts[i - 1]).length)
    n = max(2, int(round(L[-1] / step)) + 1)
    out = []
    j = 0
    for k in range(n):
        s = L[-1] * k / (n - 1)
        while j < len(pts) - 2 and L[j + 1] < s:
            j += 1
        seg = max(1e-9, L[j + 1] - L[j])
        out.append(pts[j].lerp(pts[j + 1], (s - L[j]) / seg))
    return out


def superellipse_pt(theta, a_r, a_l, b_f, b_b, n):
    """theta measured from the front (-Y) toward +X. Returns (x, y) offset."""
    s, c = sin(theta), cos(theta)
    e = 2.0 / n
    sx = math.copysign(abs(s) ** e, s)
    cy = math.copysign(abs(c) ** e, c)
    a = a_l if s >= 0 else a_r
    b = b_f if c >= 0 else b_b
    return a * sx, -b * cy


# --------------------------------------------------------------------------------- mesh objects
class Mesh:
    """Accumulates verts / faces / per-corner UVs / per-face material names / per-vertex attrs."""

    def __init__(self, name):
        self.name = name
        self.v = []
        self.f = []
        self.uv = []
        self.fm = []
        self.attr = {}

    def add_v(self, p, **attrs):
        self.v.append(Vector(p))
        for k, val in attrs.items():
            self.attr.setdefault(k, {})[len(self.v) - 1] = val
        return len(self.v) - 1

    def add_f(self, idx, uvs, mat):
        self.f.append(tuple(idx))
        self.uv.append(tuple(tuple(u) for u in uvs))
        self.fm.append(mat)

    def grid(self, rings, mat, closed=True, flip=False, cap0=False, cap1=False, uv_off=(0.0, 0.0),
             attrs=None):
        """Loft through rings (lists of equal length). Rings CCW (seen from the side rings advance
        toward) give outward normals. attrs: fn(j, i) -> dict per vertex."""
        R, M = len(rings), len(rings[0])
        base = len(self.v)
        for j, r in enumerate(rings):
            for i, p in enumerate(r):
                self.add_v(p, **(attrs(j, i) if attrs else {}))
        us = []
        for r in rings:
            acc = [0.0]
            for i in range(1, M):
                acc.append(acc[-1] + (r[i] - r[i - 1]).length)
            acc.append(acc[-1] + ((r[0] - r[-1]).length if closed else 0.0))
            us.append(acc)
        vs = [[0.0] * M]
        for j in range(1, R):
            vs.append([vs[-1][i] + (rings[j][i] - rings[j - 1][i]).length for i in range(M)])
        nseg = M if closed else M - 1
        ou, ov = uv_off
        for j in range(R - 1):
            for i in range(nseg):
                i2 = (i + 1) % M
                idx = (base + j * M + i, base + j * M + i2, base + (j + 1) * M + i2, base + (j + 1) * M + i)
                uvs = ((us[j][i] + ou, vs[j][i] + ov), (us[j][i + 1] + ou, vs[j][i2] + ov),
                       (us[j + 1][i + 1] + ou, vs[j + 1][i2] + ov), (us[j + 1][i] + ou, vs[j + 1][i] + ov))
                if flip:
                    idx = idx[::-1]
                    uvs = uvs[::-1]
                self.add_f(idx, uvs, mat)
        for cap, j, fl in ((cap0, 0, not flip), (cap1, R - 1, flip)):
            if cap:
                self.cap(list(range(base + j * M, base + (j + 1) * M)), mat, flip=fl)
        return base

    def cap(self, idx, mat, flip=False):
        """Fan-cap a ring of vertex indices with a centre vertex; planar UVs."""
        pts = [self.v[i] for i in idx]
        c = sum(pts, Vector()) / len(pts)
        n = Vector()
        for k in range(len(pts)):
            n += (pts[k] - c).cross(pts[(k + 1) % len(pts)] - c)
        n = n.normalized() if n.length > 1e-12 else Vector((0, 0, 1))
        t = (pts[0] - c).normalized()
        b = n.cross(t)
        ci = self.add_v(c)
        for k in range(len(idx)):
            a, bb = idx[k], idx[(k + 1) % len(idx)]
            tri = (a, bb, ci)
            uv = [((self.v[q] - c).dot(t), (self.v[q] - c).dot(b)) for q in tri]
            if flip:
                tri, uv = tri[::-1], uv[::-1]
            self.add_f(tri, uv, mat)

    def to_object(self, smooth=True, recalc=True):
        me = bpy.data.meshes.new(self.name)
        me.from_pydata([tuple(p) for p in self.v], [], self.f)
        mats = []
        for m in self.fm:
            if m not in mats:
                mats.append(m)
        for m in mats:
            me.materials.append(bpy.data.materials[m])
        me.polygons.foreach_set("material_index", [mats.index(m) for m in self.fm])
        uvl = me.uv_layers.new(name="UVMap")
        flat = [c for face in self.uv for uvc in face for c in uvc]
        uvl.data.foreach_set("uv", flat)
        for k, d in self.attr.items():
            at = me.attributes.new(k, 'FLOAT', 'POINT')
            vals = [0.0] * len(self.v)
            for i, x in d.items():
                vals[i] = x
            at.data.foreach_set("value", vals)
        me.update()
        ob = link(bpy.data.objects.new(self.name, me))
        if smooth:
            me.shade_smooth()
        if recalc:
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
        return ob


def ring_pts(center, U, W, radii_fn, n, t0=0.0, t1=2 * pi, closed=True):
    """Ring of n points around center in plane (U, W): p = c + U*x + W*y, (x, y) = radii_fn(theta)."""
    pts = []
    m = n if closed else n - 1
    for i in range(n):
        th = t0 + (t1 - t0) * i / m
        x, y = radii_fn(th)
        pts.append(center + U * x + W * y)
    return pts


def frames_along(path, up_hint):
    """Parallel-transport frames (T, N, B) along a polyline; N starts near up_hint."""
    P = [Vector(p) for p in path]
    T = []
    for i in range(len(P)):
        a = P[max(0, i - 1)]
        b = P[min(len(P) - 1, i + 1)]
        T.append((b - a).normalized())
    N0 = Vector(up_hint)
    N0 = (N0 - T[0] * N0.dot(T[0])).normalized()
    out = [(T[0], N0, T[0].cross(N0))]
    for i in range(1, len(P)):
        t_prev, n_prev, _ = out[-1]
        q = t_prev.rotation_difference(T[i])
        n = q @ n_prev
        n = (n - T[i] * n.dot(T[i])).normalized()
        out.append((T[i], n, T[i].cross(n)))
    return out


def sweep(m, path, section_fn, n, mat, up_hint=(0, 0, 1), closed=True, cap0=False, cap1=False,
          t0=0.0, t1=2 * pi, attrs=None, flip=False):
    """Sweep a cross-section along path. section_fn(k, s, theta) -> (x, y) in the (N, B) plane,
    where s in [0, 1] is the normalised path position. Returns base index and ring count."""
    fr = frames_along(path, up_hint)
    rings = []
    K = len(path)
    for k, (P, (T, N, B)) in enumerate(zip(path, fr)):
        s = k / (K - 1)
        rings.append(ring_pts(Vector(P), N, B, lambda th, k=k, s=s: section_fn(k, s, th), n, t0, t1, closed))
    # make rings CCW about T: x along N, y along B, with B = T x N -> CCW about T. Advancing along T => outward
    base = m.grid(rings, mat, closed=closed, cap0=cap0, cap1=cap1, attrs=attrs, flip=flip)
    return base, rings


def rrect(hx, hy, r, n_per_corner=4):
    """Rounded rectangle outline (CCW), centre origin."""
    pts = []
    r = min(r, hx * 0.999, hy * 0.999)
    for cx, cy, a0 in ((hx - r, hy - r, 0), (-hx + r, hy - r, 90), (-hx + r, -hy + r, 180), (hx - r, -hy + r, 270)):
        for k in range(n_per_corner + 1):
            a = math.radians(a0 + 90 * k / n_per_corner)
            pts.append((cx + r * cos(a), cy + r * sin(a)))
    return pts


def prism(m, outline, origin, U, W, D, depth, mat, bevel=0.0, bevel_steps=0, attrs=None):
    """Extrude a CCW 2D outline (in U/W plane) along D by depth, with optional rounded edge bevel.
    Builds as a loft of scaled/offset copies of the outline, capped at both ends."""
    origin = Vector(origin)
    c2 = (sum(p[0] for p in outline) / len(outline), sum(p[1] for p in outline) / len(outline))
    rings = []
    profile = []
    if bevel > 0 and bevel_steps > 0:
        for k in range(bevel_steps + 1):
            a = (pi / 2) * k / bevel_steps
            profile.append((bevel * (1 - cos(a)), -bevel * (1 - sin(a))))  # (depth pos, inset)
        prof = [(d, ins) for d, ins in profile]
        back = [(depth - d, ins) for d, ins in reversed(profile)]
        profile = prof + back
    else:
        profile = [(0.0, 0.0), (depth, 0.0)]
    for d, ins in profile:
        ring = []
        for (x, y) in outline:
            dx, dy = x - c2[0], y - c2[1]
            L = sqrt(dx * dx + dy * dy) or 1.0
            k = (L + ins) / L
            ring.append(origin + U * (c2[0] + dx * k) + W * (c2[1] + dy * k) + D * d)
        rings.append(ring)
    # outline CCW in (U, W) with D = U x W gives outward normals advancing along D
    return m.grid(rings, mat, closed=True, cap0=True, cap1=True, attrs=attrs)


def lathe(m, profile, center, axis_u, axis_v, axis_w, n, mat, closed_ring=True, attrs=None, cap0=False, cap1=False):
    """Revolve a (radius, height) profile around axis_w through center. Rings advance along profile."""
    rings = []
    for (r, h) in profile:
        rings.append([Vector(center) + axis_w * h + (axis_u * cos(2 * pi * i / n) + axis_v * sin(2 * pi * i / n)) * r
                      for i in range(n)])
    return m.grid(rings, mat, closed=closed_ring, attrs=attrs, cap0=cap0, cap1=cap1)


def cylinder(m, p0, p1, r, n, mat, cap=True, r1=None):
    p0, p1 = Vector(p0), Vector(p1)
    w = (p1 - p0).normalized()
    u = w.orthogonal().normalized()
    v = w.cross(u)
    return lathe(m, [(r, 0.0), (r1 if r1 is not None else r, (p1 - p0).length)], p0, u, v, w, n, mat,
                 cap0=cap, cap1=cap)


def ellipsoid(m, c, rx, ry, rz, nu, nv, mat, fn=None):
    """UV ellipsoid; fn(theta, phi, p_local) -> p_local adjust."""
    c = Vector(c)
    rings = []
    for j in range(1, nv):
        ph = -pi / 2 + pi * j / nv
        ring = []
        for i in range(nu):
            th = 2 * pi * i / nu
            p = Vector((rx * cos(ph) * sin(th), -ry * cos(ph) * cos(th), rz * sin(ph)))
            if fn:
                p = fn(th, ph, p)
            ring.append(c + p)
        rings.append(ring)
    base = m.grid(rings, mat, closed=True)
    bot = list(range(base, base + nu))
    top = list(range(base + (nv - 2) * nu, base + (nv - 1) * nu))
    # pole caps
    m.cap(bot, mat, flip=True)
    m.cap(top, mat)
    return base


# --------------------------------------------------------------------------------- bmesh-based parts
def bm_to_mesh(bm, m, mat, xform=None, uv_scale=1.0):
    """Append a bmesh into Mesh m (box-projected metric UVs)."""
    base = len(m.v)
    for v in bm.verts:
        m.add_v(xform @ v.co if xform else v.co)
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        uvs = []
        for v in f.verts:
            p = v.co
            if ax == 0:
                uvs.append((p.y * uv_scale, p.z * uv_scale))
            elif ax == 1:
                uvs.append((p.x * uv_scale, p.z * uv_scale))
            else:
                uvs.append((p.x * uv_scale, p.y * uv_scale))
        m.add_f([base + v.index for v in f.verts], uvs, mat)
    bm.free()


def rounded_box(m, center, size, rad, mat, segs=2, xform=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    if rad > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=rad, segments=segs, profile=0.5,
                        affect='EDGES', clamp_overlap=True)
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bm.normal_update()
    M = (xform or Matrix.Identity(4)) @ Matrix.Translation(Vector(center))
    bm_to_mesh(bm, m, mat, M)


def torus(m, c, axis, R, r, nu, nv, mat, ellip=1.0):
    c, axis = Vector(c), Vector(axis).normalized()
    u = axis.orthogonal().normalized()
    w = axis.cross(u)
    rings = []
    for i in range(nu):
        a = 2 * pi * i / nu
        d = u * cos(a) + w * sin(a)
        ctr = c + d * R
        rings.append([ctr + d * (r * cos(2 * pi * j / nv)) + axis * (r * ellip * sin(2 * pi * j / nv))
                      for j in range(nv)])
    rings.append(rings[0])
    base = len(m.v)
    m.grid(rings[:-1], mat, closed=True)
    # close the torus seam: connect last ring to first
    M = nv
    last = base + (nu - 1) * M
    for j in range(M):
        j2 = (j + 1) % M
        m.add_f((last + j, last + j2, base + j2, base + j), ((0, 0), (0, 0.01), (0.01, 0.01), (0.01, 0)), mat)
    return base


# --------------------------------------------------------------------------------- surface tools
class Surface:
    """Closest-point projection onto a reference mesh (world space)."""

    def __init__(self, obs):
        verts, polys = [], []
        for ob in obs:
            me = ob.data
            mw = ob.matrix_world
            o = len(verts)
            verts += [mw @ v.co for v in me.vertices]
            polys += [[o + i for i in p.vertices] for p in me.polygons]
        self.bvh = BVHTree.FromPolygons(verts, polys)

    def project(self, p, offset=0.0):
        loc, nrm, idx, d = self.bvh.find_nearest(Vector(p))
        return loc + nrm * offset, nrm

    def ray(self, origin, direction, offset=0.0):
        loc, nrm, idx, d = self.bvh.ray_cast(Vector(origin), Vector(direction).normalized())
        if loc is None:
            return None, None
        return loc + nrm * offset, nrm


def strap(m, surf, ctrl, width, thick, offset, mat, step=0.012, smooth_n=3, attrs=None, closed=False,
          side_hint=None):
    """Leather strap following a surface: control points are projected, resampled and lofted into
    a flat band of width x thick lying `offset` above the surface."""
    pts = catmull(ctrl, 6, closed=closed)
    pts = resample(pts + ([pts[0]] if closed else []), step)
    if closed:
        pts = pts[:-1]
    P, Nn = [], []
    for p in pts:
        q, n = surf.project(p)
        P.append(q)
        Nn.append(n)
    # smooth the normals along the strap
    for _ in range(smooth_n):
        Nn = [((Nn[max(0, i - 1)] + Nn[i] * 2 + Nn[min(len(Nn) - 1, i + 1)]) * 0.25).normalized()
              for i in range(len(Nn))] if not closed else \
            [((Nn[i - 1] + Nn[i] * 2 + Nn[(i + 1) % len(Nn)]) * 0.25).normalized() for i in range(len(Nn))]
    P = [p + n * (offset + thick * 0.5) for p, n in zip(P, Nn)]
    rings = []
    L = len(P)
    for i in range(L):
        a = P[(i - 1) % L] if closed else P[max(0, i - 1)]
        b = P[(i + 1) % L] if closed else P[min(L - 1, i + 1)]
        t = (b - a).normalized()
        n = (Nn[i] - t * Nn[i].dot(t)).normalized()
        s = t.cross(n)  # width direction
        hw, ht = width * 0.5, thick * 0.5
        e = min(ht, hw) * 0.6
        # rounded-rect section, CCW about t (s, n basis: s x n = t)
        sec = [(hw, -ht + e), (hw, ht - e), (hw - e, ht), (-hw + e, ht), (-hw, ht - e), (-hw, -ht + e),
               (-hw + e, -ht), (hw - e, -ht)]
        rings.append([P[i] + s * x + n * y for x, y in sec])
    if closed:
        rings.append(rings[0])
        base = m.grid(rings, mat, closed=True, attrs=attrs)
        # weld last ring onto first by remap (keep simple: duplicate ring is fine, merged later)
    else:
        base = m.grid(rings, mat, closed=True, cap0=True, cap1=True, attrs=attrs)
    return P, Nn


def orient_outward(ob, axis_pt=(0, 0, 0), axis_dir=(0, 0, 1)):
    """Flip an open sheet so that, on average, its normals point away from a vertical axis."""
    me = ob.data
    a, d = Vector(axis_pt), Vector(axis_dir).normalized()
    s = 0.0
    for p in me.polygons:
        c = p.center - a
        r = c - d * c.dot(d)
        s += r.normalized().dot(p.normal) * p.area
    if s < 0:
        me.flip_normals()
    return s


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def merge_by_distance(ob, dist=1e-5):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bm.to_mesh(ob.data)
    bm.free()


def apply_modifiers(ob):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.view_layer.objects:
        o.select_set(o == ob)
    for md in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=md.name)


def solidify(ob, thick, offset=-1.0, rim=True, inner_mat_offset=0):
    md = ob.modifiers.new("solid", 'SOLIDIFY')
    md.thickness = thick
    md.offset = offset
    md.use_rim = rim
    md.use_even_offset = True
    md.material_offset = inner_mat_offset
    md.material_offset_rim = inner_mat_offset
    apply_modifiers(ob)
