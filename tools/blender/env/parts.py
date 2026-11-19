"""Architectural parts for Breton granite houses (built into an MB mesh builder).

Conventions: house centred on origin, ground z = 0, front facade faces -Y.
A Face gives a frame per wall: a = along the wall (to the viewer's right when
looking at the wall from outside), d = outward offset from the wall plane, z up.
"""
import math

import bmesh
from mathutils import Euler, Matrix, Vector

from geo import bm_box, bm_box_minmax, bm_cyl, bm_prism, bm_quad, box_uv, text_bm

FACES = {
    "front": (Vector((0, -1, 0)), Vector((1, 0, 0))),
    "back": (Vector((0, 1, 0)), Vector((-1, 0, 0))),
    "left": (Vector((-1, 0, 0)), Vector((0, -1, 0))),
    "right": (Vector((1, 0, 0)), Vector((0, 1, 0))),
}
Z = Vector((0, 0, 1))


class Face:
    def __init__(self, name, W, D):
        self.name = name
        self.n, self.t = FACES[name]
        half = D / 2 if name in ("front", "back") else W / 2
        self.o = self.n * half
        self.length = W if name in ("front", "back") else D

    def p(self, a, d, z):
        return self.o + self.t * a + self.n * d + Z * z

    def box(self, a0, a1, d0, d1, z0, z1, bevel=0.0, segs=1):
        p0, p1 = self.p(a0, d0, z0), self.p(a1, d1, z1)
        return bm_box_minmax(min(p0.x, p1.x), min(p0.y, p1.y), min(p0.z, p1.z),
                             max(p0.x, p1.x), max(p0.y, p1.y), max(p0.z, p1.z), bevel, segs)

    def quad(self, a0, a1, z0, z1, d, uvs=None):
        return bm_quad(self.p(a0, d, z0), self.p(a1, d, z0), self.p(a1, d, z1), self.p(a0, d, z1), uvs)

    def local_matrix(self, a, d, z, ldir, ndir):
        """Matrix mapping local (x=L, y=N, z) to world, L/N given as (da, dd) in face plane."""
        L = self.t * ldir[0] + self.n * ldir[1]
        N = self.t * ndir[0] + self.n * ndir[1]
        o = self.p(a, d, z)
        return Matrix(((L.x, N.x, 0, o.x), (L.y, N.y, 0, o.y), (L.z, N.z, 1, o.z), (0, 0, 0, 1)))


def roff(rng):
    return (rng.random(), rng.random())


# ------------------------------------------------------------- openings
class Opening:
    def __init__(self, face, a, z0, w, h, kind="window", shutters="none", glow=False, rows=3,
                 paint="Paint_blue", frame="Paint_cream", leaves=2):
        self.face, self.a, self.z0, self.w, self.h = face, a, z0, w, h
        self.kind, self.shutters, self.glow, self.rows = kind, shutters, glow, rows
        self.paint, self.frame, self.leaves = paint, frame, leaves

    @property
    def a0(self):
        return self.a - self.w / 2

    @property
    def a1(self):
        return self.a + self.w / 2


def cutter(F, op, depth=0.45, margin=0.025):
    z0 = -0.3 if op.z0 <= 0.01 else op.z0 - margin
    return F.box(op.a0 - margin, op.a1 + margin, -depth, 0.3, z0, op.z0 + op.h + margin)


def surround(mb, F, op, rng, lintel_h=0.32):
    """Dressed granite jambs, lintel and sill/threshold."""
    w, h, a, z0 = op.w, op.h, op.a, op.z0
    n = max(2, int(round(h / 0.33)))
    bh = h / n
    for side in (-1, 1):
        ae = a + side * w / 2
        for i in range(n):
            wd = 0.24 if (i + (side > 0)) % 2 == 0 else 0.36
            a0, a1 = (ae, ae + wd) if side > 0 else (ae - wd, ae)
            bm = F.box(a0, a1, -0.36, 0.015, z0 + i * bh + 0.003, z0 + (i + 1) * bh - 0.003, bevel=0.012, segs=2)
            mb.add_bm(bm, "Granite", off=roff(rng))
    ext = 0.3 if op.kind != "byre" else 0.4
    bm = F.box(a - w / 2 - ext, a + w / 2 + ext, -0.36, 0.015, z0 + h, z0 + h + lintel_h, bevel=0.014, segs=2)
    mb.add_bm(bm, "Granite", off=roff(rng))
    if z0 > 0.01:
        bm = F.box(a - w / 2 - 0.1, a + w / 2 + 0.1, -0.36, 0.065, z0 - 0.1, z0, bevel=0.012, segs=2)
        mb.add_bm(bm, "Granite", off=roff(rng))
    else:
        bm = F.box(a - w / 2 - 0.12, a + w / 2 + 0.12, -0.25, 0.32, -0.12, 0.13, bevel=0.015, segs=2)
        mb.add_bm(bm, "Granite", off=roff(rng))


def window(mb, F, op, df=-0.27):
    """Casement window: dormant frame, two leaves with glazing bars, glass, dark interior."""
    a0, a1, z0, z1 = op.a0, op.a1, op.z0, op.z0 + op.h
    fw, ld = 0.065, 0.05
    fm = op.frame
    # dormant frame
    for bm in (F.box(a0, a0 + fw, df - 0.035, df + 0.035, z0, z1), F.box(a1 - fw, a1, df - 0.035, df + 0.035, z0, z1),
               F.box(a0, a1, df - 0.035, df + 0.035, z0, z0 + fw), F.box(a0, a1, df - 0.035, df + 0.035, z1 - fw, z1)):
        mb.add_bm(bm, fm, scale=1.0)
    ia0, ia1, iz0, iz1 = a0 + fw, a1 - fw, z0 + fw, z1 - fw
    leaves = []
    if op.leaves == 2:
        mid = (ia0 + ia1) / 2
        leaves = [(ia0, mid), (mid, ia1)]
    else:
        leaves = [(ia0, ia1)]
    for la0, la1 in leaves:
        for bm in (F.box(la0, la0 + ld, df - 0.025, df + 0.025, iz0, iz1), F.box(la1 - ld, la1, df - 0.025, df + 0.025, iz0, iz1),
                   F.box(la0, la1, df - 0.025, df + 0.025, iz0, iz0 + ld * 1.4), F.box(la0, la1, df - 0.025, df + 0.025, iz1 - ld, iz1)):
            mb.add_bm(bm, fm, scale=1.0)
        gz0, gz1 = iz0 + ld * 1.4, iz1 - ld
        for r in range(1, op.rows):
            zc = gz0 + (gz1 - gz0) * r / op.rows
            mb.add_bm(F.box(la0 + ld, la1 - ld, df - 0.017, df + 0.017, zc - 0.011, zc + 0.011), fm, scale=1.0)
    mb.add_bm(F.quad(ia0, ia1, iz0, iz1, df), "WindowGlow" if op.glow else "WindowGlass")
    mb.add_bm(F.quad(a0 - 0.03, a1 + 0.03, z0 - 0.03, z1 + 0.03, -0.40), "Interior")


def _leaf(mb, F, hinge_a, hinge_d, z0, lw, lh, side, theta, paint, rng, battens=True):
    """One planked shutter leaf; side=+1 hinge on right of opening, -1 on left."""
    c, s = math.cos(theta), math.sin(theta)
    if side > 0:
        ldir, ndir = (-c, s), (s, c)
    else:
        ldir, ndir = (c, s), (-s, c)
    M = F.local_matrix(hinge_a, hinge_d, z0, ldir, ndir)
    t = 0.032
    mb.add_bm(bm_box_minmax(0.0, -t, 0.0, lw, 0.0, lh), paint, matrix=M)
    if battens:
        bt = 0.022
        zs = [0.12, lh / 2, lh - 0.12]
        for zc in zs:
            mb.add_bm(bm_box_minmax(0.03, -t - bt, zc - 0.06, lw - 0.03, -t, zc + 0.06), paint, matrix=M)
        for zi in range(2):
            za, zb = zs[zi] + 0.06, zs[zi + 1] - 0.06
            ln = math.hypot(lw - 0.12, zb - za)
            ang = math.atan2(zb - za, lw - 0.12)
            bm = bm_box((lw) / 2, -t - bt / 2, (za + zb) / 2, ln, bt, 0.1, rot=(0, -ang, 0))
            mb.add_bm(bm, paint, matrix=M)
        for zc in (zs[0], zs[-1]):     # strap hinges (pentures)
            mb.add_bm(bm_box_minmax(0.0, -t - bt - 0.007, zc - 0.02, lw * 0.78, -t - bt, zc + 0.02), "Iron", scale=2.0, matrix=M)


def shutters(mb, F, op, rng):
    if op.shutters == "none":
        return
    lw = op.w / 2 + 0.012
    lh = op.h + 0.02
    states = {"open": (1, 1), "closed": (0, 0), "half": (0, 1), "halfl": (1, 0)}[op.shutters]
    for side, st in zip((-1, 1), states):
        theta = math.radians(172 + rng.uniform(-6, 4)) if st else 0.0
        if not st and op.shutters != "closed":
            theta = math.radians(rng.uniform(0, 4))
        ha = op.a + side * (op.w / 2 + 0.012)
        _leaf(mb, F, ha, 0.02, op.z0 - 0.01, lw, lh, side, theta, op.paint, rng)


def door(mb, F, op, rng, glazed=False):
    a0, a1, z1 = op.a0, op.a1, op.z0 + op.h
    dd = -0.17
    for bm in (F.box(a0, a0 + 0.07, dd - 0.05, dd + 0.04, 0.12, z1), F.box(a1 - 0.07, a1, dd - 0.05, dd + 0.04, 0.12, z1),
               F.box(a0, a1, dd - 0.05, dd + 0.04, z1 - 0.07, z1)):
        mb.add_bm(bm, "Wood_dark", scale=1.0)
    if op.leaves == 2:
        mid = op.a
        spans = [(a0 + 0.07, mid - 0.003), (mid + 0.003, a1 - 0.07)]
    else:
        spans = [(a0 + 0.07, a1 - 0.07)]
    for la0, la1 in spans:
        mb.add_bm(F.box(la0, la1, dd - 0.03, dd + 0.02, 0.13, z1 - 0.07), op.paint, scale=1.0, off=roff(rng))
        for zc in (0.45, z1 - 0.45):
            hinge_left = (la0 == a0 + 0.07)
            s0, s1 = (la0, la0 + (la1 - la0) * 0.75) if hinge_left else (la1 - (la1 - la0) * 0.75, la1)
            mb.add_bm(F.box(s0, s1, dd + 0.02, dd + 0.028, zc - 0.022, zc + 0.022), "Iron", scale=2.0)
    # latch + ring
    la = (a1 - 0.2) if op.leaves == 1 else (op.a - 0.12)
    mb.add_bm(F.box(la - 0.03, la + 0.03, dd + 0.02, dd + 0.035, 0.98, 1.1), "Iron", scale=2.0)
    ring = bm_cyl(0.045, 0.045, 0.012, segs=12)
    bmesh.ops.rotate(ring, verts=ring.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "X"))
    mb.add_bm(ring, "Iron", scale=2.0, matrix=Matrix.Translation(F.p(la, dd + 0.05, 0.98)) @ _face_rot(F))
    mb.add_bm(F.quad(a0 - 0.03, a1 + 0.03, 0.0, z1 + 0.03, -0.40), "Interior")


def _face_rot(F):
    ang = math.atan2(F.n.y, F.n.x) + math.pi / 2
    return Matrix.Rotation(ang, 4, "Z")


def hay_door(mb, F, op, rng):
    """Planked loft door in a gerbiere dormer (instead of a window)."""
    mb.add_bm(F.box(op.a0 + 0.02, op.a1 - 0.02, -0.16, -0.11, op.z0 + 0.02, op.z0 + op.h - 0.02), op.paint, scale=1.0)
    for zc in (op.z0 + 0.25, op.z0 + op.h - 0.25):
        mb.add_bm(F.box(op.a0 + 0.05, op.a1 - 0.25, -0.11, -0.103, zc - 0.02, zc + 0.02), "Iron", scale=2.0)
    mb.add_bm(F.quad(op.a0 - 0.03, op.a1 + 0.03, op.z0 - 0.03, op.z0 + op.h + 0.03, -0.40), "Interior")


# ---------------------------------------------------------------- walls
def quoins(mb, W, D, top, rng, proud=0.016):
    n = max(2, int(round(top / 0.31)))
    bh = top / n
    for sx in (-1, 1):
        for sy in (-1, 1):
            for i in range(n):
                la, lb = (0.46, 0.26) if (i + (sx * sy > 0)) % 2 == 0 else (0.26, 0.46)
                x0, x1 = sorted((sx * (W / 2 + proud), sx * (W / 2 - la)))
                y0, y1 = sorted((sy * (D / 2 + proud), sy * (D / 2 - lb)))
                z0 = -0.05 if i == 0 else i * bh + 0.003
                bm = bm_box_minmax(x0, y0, z0, x1, y1, (i + 1) * bh - 0.003, bevel=0.012, segs=2)
                mb.add_bm(bm, "Granite", off=roff(rng))


def string_course(mb, W, D, z, rng):
    """Granite eaves cornice along front and back."""
    for sy in (-1, 1):
        y0, y1 = sorted((sy * (D / 2 + 0.07), sy * (D / 2 - 0.2)))
        mb.add_bm(bm_box_minmax(-W / 2 + 0.02, y0, z - 0.16, W / 2 - 0.02, y1, z, bevel=0.015, segs=2), "Granite", off=roff(rng))


# ----------------------------------------------------------------- roof
class Roof:
    def __init__(self, W, D, He, pitch_deg, tg=0.6, ov=0.14, rise=0.2):
        self.W, self.D, self.He, self.tg, self.ov, self.rise = W, D, He, tg, ov, rise
        self.p = math.radians(pitch_deg)
        self.tp = math.tan(self.p)
        self.z_surf0 = He + 0.12                      # roof surface above wall-top outer edge
        self.Hr = self.z_surf0 + (D / 2) * self.tp
        self.z_eave = self.z_surf0 - ov * self.tp

    def z_at(self, y):
        return self.z_surf0 + (self.D / 2 - abs(y)) * self.tp

    def y_at(self, z, sign=-1):
        return sign * (self.D / 2 - (z - self.z_surf0) / self.tp)


def slate_rows(mb, origin, tv, sv, nv, length_t, length_s, rng, exclude=None, exposure=0.125, t=0.012,
               uv_origin_t=0.0):
    """Stepped slate courses on a plane. origin = eave start point; tv along the eave, sv up-slope,
    nv outward normal. exclude: list of (t0, t1, s_max) holes (e.g. dormers). UV v follows the slope
    so that texture rows coincide with the geometry steps (16 rows per 2 m tile)."""
    origin, tv, sv, nv = Vector(origin), Vector(tv), Vector(sv), Vector(nv)
    nrows = int(math.ceil(length_s / exposure))
    voff = rng.random()
    uoff = rng.random()

    def uvf(co, n):
        rel = co - origin
        return (rel.dot(tv) * 0.5 + uoff, rel.dot(sv) * 0.5 + voff * 0 + 0.0)

    for i in range(nrows):
        s0 = i * exposure
        s1 = min(length_s, (i + 1) * exposure + 0.025)
        spans = [(0.0, length_t)]
        if exclude:
            for (e0, e1, smax) in exclude:
                if s0 < smax:
                    new = []
                    for (a, b) in spans:
                        if e1 <= a or e0 >= b:
                            new.append((a, b))
                        else:
                            if e0 > a:
                                new.append((a, e0))
                            if e1 < b:
                                new.append((e1, b))
                    spans = new
        for (a, b) in spans:
            if b - a < 0.02:
                continue
            bm = bmesh.new()
            vs = []
            for (tt, ss, lift_u, lift_t) in ((a, s0, t, 2 * t), (b, s0, t, 2 * t), (b, s1, 0.0, t), (a, s1, 0.0, t)):
                base = origin + tv * tt + sv * ss
                vs.append((base + nv * lift_u, base + nv * lift_t))
            bot = [bm.verts.new(v[0]) for v in vs]
            top = [bm.verts.new(v[1]) for v in vs]
            bm.faces.new(top)
            bm.faces.new(list(reversed(bot)))
            for k in range(4):
                j = (k + 1) % 4
                bm.faces.new((bot[k], bot[j], top[j], top[k]))
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            # uv: v = s/2 (exact row alignment: texture row k spans s in [0.125k, 0.125(k+1)])
            mb.add_bm(bm, "Slate", uv=uvf)


def main_roof(mb, R, rng, dormers=()):
    """Both slopes, underlay slab, ridge tiles. dormers: list of dicts with a0,a1,z_top (front slope)."""
    W, D, tg = R.W, R.D, R.tg
    x0, x1 = -W / 2 + tg - 0.03, W / 2 - tg + 0.03
    L = x1 - x0
    cp, sp = math.cos(R.p), math.sin(R.p)
    s_len = (D / 2 + R.ov) / cp
    for sign in (-1, 1):
        origin = Vector((x0, sign * (D / 2 + R.ov), R.z_eave))
        sv = Vector((0, -sign * cp, sp))
        nv = Vector((0, sign * sp, cp))
        tv = Vector((1, 0, 0))
        excl = []
        if sign < 0:
            for dm in dormers:
                smax = (dm["z_top"] - R.z_eave) / sp
                excl.append((dm["a0"] - x0, dm["a1"] - x0, smax))
        slate_rows(mb, origin, tv, sv, nv, L, s_len + 0.02, rng, exclude=excl)
        # underlay slab (fascia/soffit + closes the roof volume), split around dormers
        pieces = [(0.0, L, 0.0, s_len)]
        if excl:
            smax = max(e[2] for e in excl)
            pieces = [(0.0, L, smax, s_len)]
            cuts = sorted((e[0], e[1]) for e in excl)
            t0 = 0.0
            for (e0, e1) in cuts:
                if e0 > t0:
                    pieces.append((t0, e0, 0.0, smax))
                t0 = max(t0, e1)
            if t0 < L:
                pieces.append((t0, L, 0.0, smax))
        for (ta, tb, sa, sb) in pieces:
            bm = bmesh.new()
            pts = [origin + sv * ss + nv * off + tv * ta for (ss, off) in ((sa, 0.0), (sb, 0.0), (sb, -0.16), (sa, -0.16))]
            a = [bm.verts.new(p) for p in pts]
            b = [bm.verts.new(p + tv * (tb - ta)) for p in pts]
            bm.faces.new(a)
            bm.faces.new(list(reversed(b)))
            for k in range(4):
                j = (k + 1) % 4
                bm.faces.new((a[k], a[j], b[j], b[k]))
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            mb.add_bm(bm, "Wood_dark", scale=1.0)
    # ridge tiles (half-round terracotta)
    zr = R.Hr + 0.01
    step = 0.38
    n = int(math.ceil(L / step))
    for i in range(n):
        xa = x0 + i * step
        xb = min(x1, xa + step + 0.04)
        prof = []
        segs = 7
        r_o, r_i = 0.115, 0.098
        for k in range(segs + 1):
            ang = math.pi * k / segs
            prof.append((math.cos(ang) * r_o, math.sin(ang) * r_o * 0.75))
        for k in range(segs, -1, -1):
            ang = math.pi * k / segs
            prof.append((math.cos(ang) * r_i, math.sin(ang) * r_i * 0.75))
        bm = bm_prism(prof, xa, xb)
        rot = Matrix.Rotation(rng.uniform(-0.03, 0.03), 4, "X")
        mb.add_bm(bm, "Clay", scale=1.0, off=roff(rng), smooth=True, smooth_angle=50,
                  matrix=Matrix.Translation((0, 0, zr - 0.02)) @ rot)


def gable_coping(mb, R, rng):
    W, D, tg = R.W, R.D, R.tg
    th = 0.13
    cp = math.cos(R.p)
    for sx in (-1, 1):
        xa, xb = sorted((sx * (W / 2 + 0.04), sx * (W / 2 - tg - 0.04)))
        for sy in (-1, 1):
            y0 = sy * (D / 2 + 0.06)
            y1 = 0.0
            zb0 = R.z_at(y0) + R.rise - 0.03
            zb1 = R.z_at(y1) + R.rise - 0.03
            prof = [(y0, zb0), (y1, zb1), (y1, zb1 + th / cp), (y0, zb0 + th / cp)]
            if sy > 0:
                prof = list(reversed(prof))
            mb.add_bm(bm_prism(prof, xa, xb), "Granite", off=roff(rng))
            # kneeler / corbel stone at the foot
            ky0, ky1 = sorted((sy * (D / 2 + 0.09), sy * (D / 2 - 0.5)))
            mb.add_bm(bm_box_minmax(xa, ky0, R.He - 0.1, xb, ky1, R.z_at(sy * D / 2) + R.rise + 0.02, bevel=0.015, segs=2),
                      "Granite", off=roff(rng))


def chimney(mb, R, sx, rng, h=1.05, width=0.95):
    W, tg = R.W, R.tg
    xa, xb = sorted((sx * (W / 2 + 0.01), sx * (W / 2 - tg - 0.05)))
    z0, z1 = R.Hr - 0.9, R.Hr + R.rise + h
    nc = int(round((z1 - z0) / 0.3))
    for i in range(nc):                       # coursed granite blocks
        za = z0 + (z1 - z0) * i / nc
        zb = z0 + (z1 - z0) * (i + 1) / nc
        mb.add_bm(bm_box_minmax(xa, -width / 2, za + 0.002, xb, width / 2, zb - 0.002, bevel=0.01, segs=1),
                  "Granite", off=roff(rng))
    mb.add_bm(bm_box_minmax(xa - 0.06, -width / 2 - 0.06, z1, xb + 0.06, width / 2 + 0.06, z1 + 0.12, bevel=0.015, segs=2),
              "Granite", off=roff(rng))
    cx = (xa + xb) / 2
    for fy in (-0.2, 0.2):
        mb.add_bm(bm_quad((cx - 0.12, fy - 0.13, z1 + 0.121), (cx + 0.12, fy - 0.13, z1 + 0.121),
                          (cx + 0.12, fy + 0.13, z1 + 0.121), (cx - 0.12, fy + 0.13, z1 + 0.121)), "Interior")
    return (xa - 0.06, -width / 2 - 0.06, z0, xb + 0.06, width / 2 + 0.06, z1 + 0.12)


def body_profile(R, extra=0.0):
    """Pentagon (y,z) of the walls; top runs 0.12 under the roof surface (+extra for gables)."""
    D, He = R.D, R.He
    return [(-D / 2, -0.3), (D / 2, -0.3), (D / 2, He + extra), (0.0, R.Hr - 0.12 + extra), (-D / 2, He + extra)]


def gable_profile(R):
    D = R.D
    zc = R.z_surf0 + R.rise
    return [(-D / 2, -0.3), (D / 2, -0.3), (D / 2, zc), (0.0, R.Hr + R.rise), (-D / 2, zc)]


# --------------------------------------------------------------- dormer
def dormer_geom(R, a, wd, z_d, pitch_deg=52.0):
    """Returns dict with body bmeshes (for union), z_top, depth, and the roof builder data."""
    D = R.D
    pd = math.radians(pitch_deg)
    half = wd / 2 + 0.1
    z_top = z_d + half * math.tan(pd)
    depth = (z_top + 0.1 - R.z_surf0) / R.tp + 0.2
    y_front = -D / 2
    x0, x1 = a - wd / 2, a + wd / 2
    box = bm_box_minmax(x0, y_front, R.He - 0.4, x1, y_front + depth, z_d)
    # gable triangle prism along Y
    bm = bmesh.new()
    pts = [(x0, z_d), (x1, z_d), (a, z_top - 0.1)]
    fa = [bm.verts.new((px, y_front, pz)) for (px, pz) in pts]
    fb = [bm.verts.new((px, y_front + depth, pz)) for (px, pz) in pts]
    bm.faces.new(fa)
    bm.faces.new(list(reversed(fb)))
    for k in range(3):
        j = (k + 1) % 3
        bm.faces.new((fa[k], fa[j], fb[j], fb[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return dict(bodies=[box, bm], a0=x0 + 0.01, a1=x1 - 0.01, z_top=z_top, depth=depth, pd=pd,
                a=a, wd=wd, z_d=z_d, half=half)


def dormer_roof(mb, R, dm, rng):
    y_front = -R.D / 2
    length = dm["depth"] + 0.12
    cp, sp = math.cos(dm["pd"]), math.sin(dm["pd"])
    s_len = dm["half"] / cp + 0.02
    for side in (-1, 1):
        ex = dm["a"] + side * dm["half"]
        origin = Vector((ex, y_front - 0.12, dm["z_d"] - 0.02))
        if side < 0:
            tv, sv, nv = Vector((0, 1, 0)), Vector((cp, 0, sp)), Vector((-sp, 0, cp))
        else:
            origin = Vector((ex, y_front - 0.12 + length, dm["z_d"] - 0.02))
            tv, sv, nv = Vector((0, -1, 0)), Vector((-cp, 0, sp)), Vector((sp, 0, cp))
        slate_rows(mb, origin, tv, sv, nv, length, s_len, rng)
    # small ridge cap
    zr = dm["z_top"] + 0.005
    mb.add_bm(bm_box_minmax(dm["a"] - 0.06, y_front - 0.13, zr - 0.04, dm["a"] + 0.06, y_front - 0.12 + length, zr + 0.03,
                            bevel=0.02, segs=2), "Clay", scale=1.0)


# --------------------------------------------------------------- decals
def damp_strip(mb, F, a0, a1, rng, skip=(), height=1.0):
    """Rising-damp decal along a wall base, broken around doors (skip = [(a0,a1),...])."""
    spans = [(a0, a1)]
    for (s0, s1) in skip:
        new = []
        for (x, y) in spans:
            if s1 <= x or s0 >= y:
                new.append((x, y))
            else:
                if s0 > x:
                    new.append((x, s0))
                if s1 < y:
                    new.append((s1, y))
        spans = new
    uo = rng.random()
    for (x, y) in spans:
        if y - x < 0.1:
            continue
        uvs = [((x) / 2 + uo, 0.0), ((y) / 2 + uo, 0.0), ((y) / 2 + uo, 1.0), ((x) / 2 + uo, 1.0)]
        mb.add_bm(F.quad(x, y, -0.03, height - 0.03, 0.012, uvs), "DecalDamp", uv="keep")


def streak(mb, F, a, width, z_top, length, rng):
    u0 = rng.random() * 0.5
    uvs = [(u0, 0.0), (u0 + 1.0, 0.0), (u0 + 1.0, 1.0), (u0, 1.0)]
    mb.add_bm(F.quad(a - width / 2, a + width / 2, z_top - length, z_top, 0.012, uvs), "DecalStreak", uv="keep")


class Frame:
    """Arbitrary vertical frame (t along, n outward) for text placement."""
    def __init__(self, origin, t, n):
        self.o, self.t, self.n = Vector(origin), Vector(t), Vector(n)

    def p(self, a, d, z):
        return self.o + self.t * a + self.n * d + Z * z


def text(mb, F, body, a, z, d, size, mat, extrude=0.002, spacing=1.0, res=6):
    bm = text_bm(body, size, extrude=extrude, spacing=spacing, res=res)
    # text is in XY (reading +X, up +Y), extruded along Z: map X->t, Y->z, Z->n
    t, n = F.t, F.n
    o = F.p(a, d + extrude, z)
    M = Matrix(((t.x, 0, n.x, o.x), (t.y, 0, n.y, o.y), (t.z, 1, n.z, o.z), (0, 0, 0, 1)))
    # swap: local Y (text up) must map to world Z
    M = Matrix(((t.x, n.x * 0, n.x, o.x), (t.y, 0, n.y, o.y), (0, 1, 0, o.z), (0, 0, 0, 1)))
    mb.add_bm(bm, mat, matrix=M, scale=2.0)
