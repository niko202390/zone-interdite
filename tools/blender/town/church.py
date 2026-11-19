"""Église Saint-Pierre de Plouzennec: Breton granite parish church with an open-work spire (clocher à jour).

Built in a church-local frame with the long axis on X (west = -X, south = -Y) so the kit's house parts
(Roof, slate courses, gable coping) apply directly, then rotated +90 deg about Z so the west front faces
Blender -Y (south porch -> +X) and shifted so the 30 x 14 m footprint is centred on the origin.
Separate node: Door (west door, origin on the hinge). Empty: BellTower (belfry centre)."""
import math
import random

import bmesh
from mathutils import Matrix, Vector

import geo
from geo import MB, bm_box_minmax, bm_cyl, bm_prism, boolean, union
from parts import Face, Roof, body_profile, damp_strip, gable_coping, gable_profile, main_roof, quoins, roff, text
from common import (Cols, WFace, arch_opening_poly, arch_ring, cyl_between, face_poly, face_prism, lathe, mb_merge,
                    mb_transform, offset_arch, pivot_object, pointed_arch, tube)
import block
import shell

PI = math.pi
TOWER_C = Vector((-12.2, 0.0))
TH = 2.8                      # tower half width (stage 1)
NAVE = (-9.4, 12.0)           # x range
NAVE_HD = 5.5                 # half depth (y)
NAVE_HE = 5.0
CH = (11.6, 15.0)             # chancel x range
CH_HD = 4.0
PORCH_X = -5.6                # porch centre (church-local x) on the south (-Y) side
SPIRE_Z0, SPIRE_Z1 = 25.9, 38.7


# =================================================================== helpers
def buttress(mb, F, a, width, steps, rng, mat="Ashlar", d_base=0.0):
    """Stepped buttress against wall frame F at position a. steps: [(projection, z_top), ...] from the
    base up; each set-off has a sloped weathering 0.35 high."""
    a0, a1 = a - width / 2, a + width / 2
    z = -0.3
    for k, (proj, zt) in enumerate(steps):
        mb.add_bm(F.box(a0, a1, d_base - 0.1, proj, z, zt), mat, off=roff(rng))
        nxt = steps[k + 1][0] if k + 1 < len(steps) else 0.0
        # weathering: prism from proj down to nxt over 0.35 (top slopes back into the wall)
        poly = [(proj, zt), (nxt, zt + (0.35 if nxt > 0 else 0.6)), (nxt - 0.1 if nxt > 0 else -0.1,
                                                                     zt + (0.35 if nxt > 0 else 0.6)), (-0.1, zt)]
        bm = bmesh.new()
        A = [bm.verts.new(F.p(a0, d, zz)) for (d, zz) in poly]
        B = [bm.verts.new(F.p(a1, d, zz)) for (d, zz) in poly]
        bm.faces.new(A)
        bm.faces.new(list(reversed(B)))
        for i in range(len(poly)):
            j = (i + 1) % len(poly)
            bm.faces.new((A[i], A[j], B[j], B[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mb.add_bm(bm, "AshlarDark", off=roff(rng))
        z = zt
    return F.p(a0, -0.1, -0.3), F.p(a1, steps[0][0], steps[-1][1] + 0.4)


def lancet(mb, F, ac, w, z0, zs, rng, lights=2, glass_d=-0.22, ring=0.2, kind="pointed", rise_k=1.0, cut=None,
           glow=False):
    """Pointed window: voussoir ring, jamb stones, sill, tracery (mullions, sub-arches, oculus), leaded glass.
    Adds its cutter to `cut` (list)."""
    poly, zt = arch_opening_poly(ac, z0, w, zs, kind, rise_k, n=10)
    if cut is not None:
        cut.append(face_prism(F, poly, -0.9, 0.3))
    arch_ring(mb, F, ac, zs, w, ring, -0.4, 0.02, "Ashlar", rng, kind, rise_k, n=10)
    nj = max(2, int(round((zs - z0) / 0.4)))
    for side in (-1, 1):
        ae = ac + side * w / 2
        for i in range(nj):
            wd = 0.22 if (i + (side > 0)) % 2 == 0 else 0.32
            aa, bb = (ae, ae + wd) if side > 0 else (ae - wd, ae)
            mb.add_bm(F.box(aa, bb, -0.4, 0.02, z0 + (zs - z0) * i / nj + 0.004, z0 + (zs - z0) * (i + 1) / nj - 0.004,
                            bevel=0.01), "Ashlar", off=roff(rng))
    mb.add_bm(F.box(ac - w / 2 - 0.12, ac + w / 2 + 0.12, -0.4, 0.08, z0 - 0.14, z0, bevel=0.01), "Granite", off=roff(rng))
    # hood mould (larmier) over the ring
    outer = offset_arch(ac, zs, w, ring + 0.02, kind, rise_k, n=10)
    mb.add_bm(tube([F.p(a, 0.06, z) for (a, z) in outer], 0.055, 5), "Granite", scale=1.0)
    # glass
    mb.add_bm(face_poly(F, poly, glass_d - 0.01), "WindowGlow" if glow else "LeadGlass")
    # tracery: chamfered stone bars (square tubes)
    tr = 0.045
    d = glass_d + 0.03
    if lights >= 2:
        lw = w / lights
        for k in range(1, lights):
            a = ac - w / 2 + lw * k
            mb.add_bm(F.box(a - tr, a + tr, d - 0.05, d + 0.05, z0, zs + 0.05), "Granite", off=roff(rng))
        for k in range(lights):
            la = ac - w / 2 + lw * (k + 0.5)
            pts, _ = pointed_arch(la, zs, lw, 1.0, 6)
            mb.add_bm(tube([F.p(a, d, z) for (a, z) in pts], tr, 4), "Granite", scale=1.0)
        # oculus / quatrefoil in the head
        zc = zs + (zt - zs) * 0.62
        rr = min(lw * 0.42, (zt - zs) * 0.3)
        q = []
        for i in range(25):
            t = 2 * PI * i / 24
            r = rr * (0.7 + 0.3 * abs(math.cos(2 * t)))
            q.append(F.p(ac + r * math.cos(t), d, zc + r * math.sin(t)))
        mb.add_bm(tube(q, tr * 0.8, 4), "Granite", scale=1.0)
    # lead cames
    for k in range(1, int((zs - z0) / 0.35)):
        z = z0 + k * 0.35
        mb.add_bm(F.box(ac - w / 2, ac + w / 2, glass_d - 0.005, glass_d + 0.005, z - 0.006, z + 0.006), "Iron", scale=2.0)
    return zt


def portal(mb, F, ac, w, zs, orders, rng, depth_step=0.16, kind="pointed", rise_k=1.0, cut=None, carved=True,
           cut_depth=None):
    """Splayed portal: `orders` concentric moulded arch rings stepping out towards the face, jamb
    colonnettes with capitals and bases, hood mould with label stops, crocketed outer ring."""
    tot = orders * depth_step
    outer_poly, _ = arch_opening_poly(ac, -0.3, w + 2 * (tot + 0.02), zs, kind, rise_k * w / (w + 2 * tot) * 1.0 + 0.0, n=12)
    outer_poly = [(ac - w / 2 - tot - 0.02, -0.3)] + offset_arch(ac, zs, w, tot + 0.02, kind, rise_k, 12) + \
                 [(ac + w / 2 + tot + 0.02, -0.3)]
    if cut is not None:
        cut.append(face_prism(F, outer_poly, -(cut_depth or tot + 0.02), 0.3))
    for k in range(orders):
        o0, o1 = k * depth_step, (k + 1) * depth_step
        dback = -tot - 0.05
        dfront = -(orders - 1 - k) * depth_step - 0.02
        mat = "Ashlar" if k % 2 == 0 else "Granite"
        # arch order: ring between offsets o0..o1, rounded with a roll moulding (tube) on its arris
        inner = offset_arch(ac, zs, w, o0, kind, rise_k, 12)
        outer = offset_arch(ac, zs, w, o1, kind, rise_k, 12)
        for i in range(0, len(inner) - 1, 2):
            j = min(i + 2, len(inner) - 1)
            poly = inner[i:j + 1] + list(reversed(outer[i:j + 1]))
            mb.add_bm(face_prism(F, poly, dback, dfront), mat, off=roff(rng))
        mb.add_bm(tube([F.p(a, dfront, z) for (a, z) in offset_arch(ac, zs, w, o0 + 0.01, kind, rise_k, 12)], 0.045, 6),
                  "Granite", scale=1.0)
        # jambs + colonnettes
        for s in (-1, 1):
            aa = ac + s * (w / 2 + (o0 + o1) / 2)
            ja, jb = sorted((ac + s * (w / 2 + o0), ac + s * (w / 2 + o1)))
            mb.add_bm(F.box(ja, jb, dback, dfront - 0.07, -0.05, zs), mat, off=roff(rng))
            col = cyl_between(F.p(aa, dfront - 0.05, 0.45), F.p(aa, dfront - 0.05, zs - 0.28), 0.055, 10)
            mb.add_bm(col, "Granite", scale=1.0, smooth=True, smooth_angle=50)
            mb.add_bm(F.box(aa - 0.09, aa + 0.09, dfront - 0.14, dfront + 0.03, zs - 0.28, zs, bevel=0.015), "Granite",
                      off=roff(rng))                                         # capital
            mb.add_bm(F.box(aa - 0.085, aa + 0.085, dfront - 0.13, dfront + 0.02, 0.15, 0.45, bevel=0.015), "Granite",
                      off=roff(rng))                                         # base
        mb.add_bm(F.box(ac - w / 2 - tot, ac + w / 2 + tot, dback, 0.02, -0.3, 0.15), "Granite", off=roff(rng))  # plinth/step
    hood = offset_arch(ac, zs, w, tot + 0.08, kind, rise_k, 12)
    mb.add_bm(tube([F.p(a, 0.08, z) for (a, z) in hood], 0.07, 6), "Granite", scale=1.0)
    for s in (0, -1):          # label stops (carved heads, blocky)
        a, z = hood[s]
        mb.add_bm(F.box(a - 0.12, a + 0.12, 0.0, 0.2, z - 0.28, z + 0.02, bevel=0.03, segs=2), "Granite", off=roff(rng))
    if carved:                 # crockets (leaf knobs) climbing the hood
        for i in range(2, len(hood) - 2, 2):
            a, z = hood[i]
            leaf = lathe([(0.0, 0.0), (0.07, 0.02), (0.06, 0.09), (0.0, 0.13)], segs=6)
            mb.add_bm(leaf, "Granite", scale=1.0, matrix=Matrix.Translation(F.p(a, 0.12, z + 0.03)))
        a, z = hood[len(hood) // 2]
        fin = lathe([(0.0, 0.0), (0.1, 0.05), (0.08, 0.3), (0.12, 0.35), (0.0, 0.62)], segs=8)
        mb.add_bm(fin, "Granite", scale=1.0, matrix=Matrix.Translation(F.p(a, 0.1, z)))       # finial


def tympanum(mb, F, ac, w, zs, d, rng, kind="pointed"):
    pts, zt = pointed_arch(ac, zs, w, 1.0, 10)
    poly = [(ac - w / 2, zs)] + pts[1:-1] + [(ac + w / 2, zs)]
    mb.add_bm(face_prism(F, poly, d - 0.12, d), "Ashlar", off=roff(rng))
    mb.add_bm(F.box(ac - w / 2, ac + w / 2, d - 0.12, d + 0.05, zs - 0.18, zs, bevel=0.01), "Granite", off=roff(rng))  # lintel
    # carved: an incised cross in a trefoil roundel
    zc = zs + (zt - zs) * 0.45
    ring = [F.p(ac + 0.32 * math.cos(2 * PI * i / 20), d + 0.01, zc + 0.32 * math.sin(2 * PI * i / 20)) for i in range(21)]
    mb.add_bm(tube(ring, 0.03, 4), "Granite", scale=1.0)
    mb.add_bm(F.box(ac - 0.035, ac + 0.035, d - 0.005, d + 0.02, zc - 0.24, zc + 0.24), "GraniteDark")
    mb.add_bm(F.box(ac - 0.17, ac + 0.17, d - 0.005, d + 0.02, zc + 0.04, zc + 0.11), "GraniteDark")


def stone_cross(mb, p, rng, h=1.0, mat="Granite"):
    x, y, z = p
    mb.add_bm(bm_box_minmax(x - 0.07, y - 0.07, z, x + 0.07, y + 0.07, z + h, bevel=0.012), mat, off=roff(rng))
    mb.add_bm(bm_box_minmax(x - 0.07, y - 0.32, z + h * 0.62, x + 0.07, y + 0.32, z + h * 0.62 + 0.13, bevel=0.012), mat,
              off=roff(rng))


def oct_pts(r, z, rot=PI / 8):
    return [Vector((TOWER_C.x + r * math.cos(rot + i * PI / 4), TOWER_C.y + r * math.sin(rot + i * PI / 4), z))
            for i in range(8)]


def pierced_panel(mb, corners, hole_frac, thick, mat, rng, n=24, lobes=True):
    """Planar quad panel (bl, br, tr, tl) with a quatrefoil hole. Front + back faces + hole reveal."""
    bl, br, tr, tl = [Vector(c) for c in corners]
    u = (br - bl).normalized()
    up = ((tl + tr) / 2 - (bl + br) / 2)
    v = (up - u * up.dot(u)).normalized()
    nrm = u.cross(v).normalized()
    c3 = (bl + br + tr + tl) / 4
    loc = lambda p: Vector(((p - c3).dot(u), (p - c3).dot(v)))
    poly2 = [loc(p) for p in (bl, br, tr, tl)]
    hw = min(abs(poly2[0].x), abs(poly2[1].x), abs(poly2[2].x), abs(poly2[3].x))
    hh = abs(poly2[2].y)
    rr = min(hw, hh) * hole_frac

    def ray_hit(d):
        best = 1e9
        for i in range(4):
            a, b = poly2[i], poly2[(i + 1) % 4]
            e = b - a
            den = d.x * (-e.y) - d.y * (-e.x)
            if abs(den) < 1e-9:
                continue
            t = (a.x * (-e.y) - a.y * (-e.x)) / den
            s = (d.x * a.y - d.y * a.x) / den
            if t > 0 and -1e-6 <= s <= 1 + 1e-6:
                best = min(best, t)
        return d * best

    outer, inner = [], []
    for i in range(n):
        t = 2 * PI * i / n + PI / 4
        d = Vector((math.cos(t), math.sin(t)))
        outer.append(ray_hit(d))
        r = rr * ((0.68 + 0.32 * abs(math.cos(2 * (t - PI / 4)))) if lobes else 1.0)
        inner.append(d * r)
    to3 = lambda p2, off: c3 + u * p2.x + v * p2.y + nrm * off
    bm = bmesh.new()
    of = [bm.verts.new(to3(p, 0.0)) for p in outer]
    if_ = [bm.verts.new(to3(p, 0.0)) for p in inner]
    ob = [bm.verts.new(to3(p, -thick)) for p in outer]
    ib = [bm.verts.new(to3(p, -thick)) for p in inner]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((of[i], of[j], if_[j], if_[i]))
        bm.faces.new((ob[j], ob[i], ib[i], ib[j]))
        bm.faces.new((if_[i], if_[j], ib[j], ib[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mb.add_bm(bm, mat, off=roff(rng))


# ==================================================================== tower
def tower(mb, cols, rng):
    cx, cy = TOWER_C
    x0, x1 = cx - TH, cx + TH
    cut = []
    # stage 1 (0..11) and 2 (11..18.5): solid ashlar with a vestibule behind the west door
    st1 = bm_box_minmax(x0, -TH, -0.3, x1, TH, 11.0)
    st2 = bm_box_minmax(x0 + 0.15, -TH + 0.15, 10.9, x1 - 0.15, TH - 0.15, 18.6)
    body = union([st1, st2])
    Fw = WFace((x0, 0, 0), (-1, 0, 0), name="west")
    ws, ww = 2.45, 1.5
    portal_cut = []
    portal(mb, Fw, 0.0, ww, ws, 3, rng, cut=portal_cut)
    tympanum(mb, Fw, 0.0, ww, ws, -0.52, rng)
    vest = Fw.box(-ww / 2 - 0.05, ww / 2 + 0.05, -2.5, -0.3, -0.3, ws + 0.02)
    body = boolean(body, portal_cut)
    body = boolean(body, [vest])
    # small lancets / slits higher on the tower
    small = []
    faces = {"west": Fw, "north": WFace((cx, TH, 0), (0, 1, 0)), "south": WFace((cx, -TH, 0), (0, -1, 0)),
             "east": WFace((x1, 0, 0), (1, 0, 0))}
    for nm, F in faces.items():
        if nm != "east":
            lancet(mb, F, 0.0, 0.32, 7.2, 8.4, rng, lights=1, ring=0.14, cut=small, glass_d=-0.3)
        F2 = WFace(F.o - F.n * 0.15, F.n)
        lancet(mb, F2, 0.0, 0.7, 13.6, 15.4, rng, lights=1, ring=0.16, cut=small, glass_d=-0.3)
    lancet(mb, Fw, 0.0, 1.0, 5.0, 6.3, rng, lights=2, ring=0.18, cut=small, glass_d=-0.3)
    body = boolean(body, small)
    mb.add_bm(body, "Ashlar", off=roff(rng))
    # vestibule lining
    mb.add_bm(Fw.quad(-ww / 2, ww / 2, 0.0, ws, -2.45), "Interior")
    mb.add_bm(geo.bm_quad(Fw.p(-ww / 2 - 0.05, -0.3, 0.01), Fw.p(ww / 2 + 0.05, -0.3, 0.01), Fw.p(ww / 2 + 0.05, -2.5, 0.01),
                          Fw.p(-ww / 2 - 0.05, -2.5, 0.01)), "Flags")
    # string courses
    for z, half in ((11.0, TH + 0.08), (18.6, TH - 0.05)):
        mb.add_bm(bm_box_minmax(cx - half, -half, z - 0.05, cx + half, half, z + 0.16, bevel=0.02), "Granite", off=roff(rng))
    # clasping buttresses at the west corners and the east corners (beside the nave)
    steps = [(0.95, 4.0), (0.7, 7.5), (0.45, 10.4)]
    for sy in (-1, 1):
        Fside = faces["south" if sy < 0 else "north"]
        # on the west face near the corner (Fw.t = -Y)
        p0, p1 = buttress(mb, Fw, -sy * (TH - 0.42), 0.84, steps, rng)
        # on the side face near the west corner (side frames: south t=(1,0,0), north t=(-1,0,0))
        a_side = (x0 + 0.42 - cx) if sy < 0 else -(x0 + 0.42 - cx)
        q0, q1 = buttress(mb, Fside, a_side, 0.84, steps, rng)
        for (pa, pb) in ((p0, p1), (q0, q1)):
            cols.box("TowerButtress", min(pa.x, pb.x), min(pa.y, pb.y), 0, max(pa.x, pb.x), max(pa.y, pb.y), pb.z)
    # belfry (18.6..25.6): hollow, two tall open lancets per face, bells inside
    bz0, bz1 = 18.6, 25.6
    hb = TH - 0.15
    t = 0.7
    shells = [bm_box_minmax(cx - hb, -hb, bz0, cx + hb, hb, bz1)]
    belfry = boolean(shells[0], [bm_box_minmax(cx - hb + t, -hb + t, bz0 + 0.3, cx + hb - t, hb - t, bz1 + 0.1)])
    bcut = []
    for nm, n in (("west", (-1, 0, 0)), ("east", (1, 0, 0)), ("north", (0, 1, 0)), ("south", (0, -1, 0))):
        o = Vector((cx, 0, 0)) + Vector(n) * hb
        F = WFace(o, n)
        for ac in (-1.05, 1.05):
            poly, zt = arch_opening_poly(ac, bz0 + 0.9, 1.25, bz0 + 4.6, n=10)
            bcut.append(face_prism(F, poly, -t - 0.2, 0.3))
            arch_ring(mb, F, ac, bz0 + 4.6, 1.25, 0.2, -t + 0.05, 0.03, "Granite", rng, n=10)
            mb.add_bm(F.box(ac - 0.75, ac + 0.75, -t + 0.05, 0.1, bz0 + 0.75, bz0 + 0.9, bevel=0.01), "Granite", off=roff(rng))
            # slender colonnettes in the jambs
            for s in (-1, 1):
                mb.add_bm(cyl_between(F.p(ac + s * 0.66, 0.0, bz0 + 0.9), F.p(ac + s * 0.66, 0.0, bz0 + 4.5), 0.06, 8),
                          "Granite", scale=1.0, smooth=True)
        mb.add_bm(tube([F.p(a, 0.08, z) for (a, z) in offset_arch(-1.05, bz0 + 4.6, 1.25, 0.24, n=10)], 0.05, 5), "Granite")
        mb.add_bm(tube([F.p(a, 0.08, z) for (a, z) in offset_arch(1.05, bz0 + 4.6, 1.25, 0.24, n=10)], 0.05, 5), "Granite")
    belfry = boolean(belfry, bcut)
    mb.add_bm(belfry, "Ashlar", off=roff(rng))
    # belfry floor, bell frame, bells
    mb.add_bm(bm_box_minmax(cx - hb + t, -hb + t, bz0 + 0.1, cx + hb - t, hb - t, bz0 + 0.3), "Wood_dark", scale=1.0)
    for yy in (-0.9, 0.9):
        mb.add_bm(bm_box_minmax(cx - hb + t, yy - 0.12, bz0 + 3.6, cx + hb - t, yy + 0.12, bz0 + 3.85), "Wood_dark", scale=1.0)
        for xx in (cx - 1.3, cx + 1.3):
            mb.add_bm(bm_box_minmax(xx - 0.1, yy - 0.1, bz0 + 0.3, xx + 0.1, yy + 0.1, bz0 + 3.6), "Wood_dark", scale=1.0)
    bell_prof = [(0.0, -0.95), (0.62, -0.95), (0.6, -0.88), (0.5, -0.7), (0.4, -0.45), (0.36, -0.15), (0.33, 0.0),
                 (0.2, 0.06), (0.0, 0.08)]
    for (bx, by, s) in ((cx - 0.55, -0.0, 1.0), (cx + 0.75, 0.0, 0.7)):
        bm = lathe([(r * s, z * s) for (r, z) in bell_prof], segs=20)
        mb.add_bm(bm, "Bronze", scale=1.0, smooth=True, smooth_angle=60, matrix=Matrix.Translation((bx, by, bz0 + 3.45)))
        mb.add_bm(bm_box_minmax(bx - 0.08, -0.9, bz0 + 3.45, bx + 0.08, 0.9, bz0 + 3.62), "Wood_dark", scale=1.0)   # headstock
    # gallery: cornice + pierced balustrade + corner pinnacles
    gz = bz1
    mb.add_bm(bm_box_minmax(cx - hb - 0.35, -hb - 0.35, gz, cx + hb + 0.35, hb + 0.35, gz + 0.3, bevel=0.03, segs=2), "Granite",
              off=roff(rng))
    mb.add_bm(bm_box_minmax(cx - hb + 0.1, -hb + 0.1, gz - 0.25, cx + hb - 0.1, hb - 0.1, gz + 0.32), "Ashlar", off=roff(rng))
    gh = hb + 0.3
    for (nm, n) in (("w", (-1, 0)), ("e", (1, 0)), ("n", (0, 1)), ("s", (0, -1))):
        F = WFace((cx + n[0] * gh, n[1] * gh, gz + 0.3), (n[0], n[1], 0))
        L = gh - 0.4
        nmul = 9
        for k in range(nmul + 1):
            a = -L + 2 * L * k / nmul
            mb.add_bm(F.box(a - 0.06, a + 0.06, -0.14, 0.0, 0.0, 0.75), "Granite", off=roff(rng))
        for k in range(nmul):
            a = -L + 2 * L * (k + 0.5) / nmul
            pts, _ = pointed_arch(a, 0.45, 2 * L / nmul - 0.12, 1.0, 4)
            mb.add_bm(tube([F.p(aa, -0.07, zz) for (aa, zz) in pts], 0.03, 4), "Granite", scale=1.0)
        mb.add_bm(F.box(-gh, gh, -0.2, 0.04, 0.75, 0.88, bevel=0.015), "Granite", off=roff(rng))
    for sx in (-1, 1):
        for sy in (-1, 1):
            px, py = cx + sx * (gh - 0.25), sy * (gh - 0.25)
            mb.add_bm(bm_box_minmax(px - 0.32, py - 0.32, gz + 0.3, px + 0.32, py + 0.32, gz + 2.7, bevel=0.02), "Ashlar", off=roff(rng))
            for k in range(4):     # small gablets on the pinnacle shaft
                ang = k * PI / 2
                F = WFace((px + 0.32 * math.cos(ang), py + 0.32 * math.sin(ang), 0), (math.cos(ang), math.sin(ang), 0))
                poly = [(-0.3, gz + 2.7), (0.3, gz + 2.7), (0.0, gz + 3.25)]
                mb.add_bm(face_prism(F, poly, -0.1, 0.04), "Granite", off=roff(rng))
                mb.add_bm(face_poly(F, [(-0.16, gz + 1.4), (0.16, gz + 1.4), (0.16, gz + 2.3), (0.0, gz + 2.5), (-0.16, gz + 2.3)],
                                    0.003), "Void")
            cap = lathe([(0.46, 0.0), (0.0, 2.3)], segs=4)
            mb.add_bm(cap, "Ashlar", matrix=Matrix.Translation((px, py, gz + 2.7)) @ Matrix.Rotation(PI / 4, 4, "Z"))
            for k in range(1, 5):      # crockets
                zz = gz + 2.7 + k * 0.42
                r = 0.46 * (1 - k * 0.42 / 2.3)
                for j in range(4):
                    ang = j * PI / 2 + PI / 4
                    mb.add_bm(lathe([(0.0, 0.0), (0.05, 0.02), (0.0, 0.1)], segs=5), "Granite",
                              matrix=Matrix.Translation((px + (r * 0.72 + 0.03) * math.cos(ang) * 1.0,
                                                         py + (r * 0.72 + 0.03) * math.sin(ang), zz)))
            mb.add_bm(lathe([(0.0, 0.0), (0.08, 0.03), (0.1, 0.12), (0.0, 0.25)], segs=8), "Granite",
                      matrix=Matrix.Translation((px, py, gz + 5.0)))
    # octagonal stair turret (tourelle d'escalier) in the north-east angle of tower and nave
    tx, ty = x1 + 0.25, TH + 0.35
    tur = lathe([(0.95, -0.3), (0.95, 19.4), (1.05, 19.4), (1.05, 19.65), (0.0, 19.65)], segs=8)
    mb.add_bm(tur, "Ashlar", matrix=Matrix.Translation((tx, ty, 0)) @ Matrix.Rotation(PI / 8, 4, "Z"), off=roff(rng))
    capb = lathe([(1.0, 0.0), (0.0, 3.2)], segs=8)
    mb.add_bm(capb, "Ashlar", matrix=Matrix.Translation((tx, ty, 19.65)) @ Matrix.Rotation(PI / 8, 4, "Z"), off=roff(rng))
    mb.add_bm(lathe([(0.0, 0.0), (0.1, 0.04), (0.12, 0.16), (0.0, 0.3)], segs=8), "Granite",
              matrix=Matrix.Translation((tx, ty, 22.85)))
    for k, z in enumerate((3.0, 6.5, 10.0, 13.5, 17.0)):
        ang = PI / 4 * (1 + (k % 3))
        F = WFace((tx + 0.92 * math.cos(ang), ty + 0.92 * math.sin(ang), 0), (math.cos(ang), math.sin(ang), 0))
        mb.add_bm(F.box(-0.07, 0.07, -0.1, 0.012, z, z + 0.6), "Void")
        mb.add_bm(F.box(-0.2, 0.2, -0.05, 0.03, z + 0.6, z + 0.75), "Granite", off=roff(rng))
    cols.box("StairTurret", tx - 0.95, ty - 0.95, 0, tx + 0.95, ty + 0.95, 19.6)
    cols.box("Tower", x0 + 2.5, -TH, -0.3, x1, TH, 18.6)
    cols.box("TowerFrontS", x0, -TH, -0.3, x0 + 2.5, -ww / 2 - 0.05, 18.6)
    cols.box("TowerFrontN", x0, ww / 2 + 0.05, -0.3, x0 + 2.5, TH, 18.6)
    cols.box("TowerFrontTop", x0, -ww / 2 - 0.05, ws + 1.4, x0 + 2.5, ww / 2 + 0.05, 18.6)
    cols.box("Tympanum", x0, -ww / 2 - 0.05, ws - 0.18, x0 + 0.6, ww / 2 + 0.05, ws + 1.4)
    cols.box("Belfry", cx - hb, -hb, bz0, cx + hb, hb, gz + 0.3)
    return Fw, ws, ww


def spire(mb, cols, rng):
    """Octagonal open-work granite spire: 8 crocketed ribs, tiers of quatrefoil-pierced panels separated
    by moulded bands, a solid tip, finial and iron cross."""
    z0, z1 = SPIRE_Z0, SPIRE_Z1
    R0 = 2.25
    H = z1 - z0
    rad = lambda z: R0 * (1 - (z - z0) / H)
    # base drum
    drum = lathe([(R0 + 0.12, z0 - 0.0), (R0 + 0.12, z0 + 0.45), (R0 - 0.2, z0 + 0.45), (R0 - 0.2, z0)], segs=8)
    mb.add_bm(drum, "Granite", matrix=Matrix.Translation((TOWER_C.x, TOWER_C.y, 0)) @ Matrix.Rotation(PI / 8, 4, "Z"),
              off=roff(rng))
    tiers = [z0 + 0.45]
    hs = [1.85, 1.7, 1.5, 1.35, 1.2, 1.05]
    for h in hs:
        tiers.append(tiers[-1] + h)
    z_solid = tiers[-1]
    for k in range(len(tiers) - 1):
        za, zb = tiers[k], tiers[k + 1]
        lo, hi = oct_pts(rad(za) - 0.06, za), oct_pts(rad(zb) - 0.06, zb)
        for i in range(8):
            j = (i + 1) % 8
            corners = [lo[i], lo[j], hi[j], hi[i]]
            pierced_panel(mb, corners, 0.8 if k < 4 else 0.7, 0.12, "Ashlar", rng, n=24, lobes=(k % 2 == 0))
        # band at the top of the tier
        rb = rad(zb)
        band_bm = lathe([(rb + 0.07, zb - 0.08), (rb + 0.07, zb + 0.08), (rb - 0.18, zb + 0.08), (rb - 0.18, zb - 0.08),
                         (rb + 0.07, zb - 0.08)], segs=8, cap_top=False, cap_bottom=False)
        mb.add_bm(band_bm, "Granite", matrix=Matrix.Translation((TOWER_C.x, TOWER_C.y, 0)) @ Matrix.Rotation(PI / 8, 4, "Z"),
                  off=roff(rng))
    # solid tip
    tip = lathe([(rad(z_solid) - 0.04, z_solid), (0.12, z1 - 0.1), (0.0, z1)], segs=8)
    mb.add_bm(tip, "Ashlar", matrix=Matrix.Translation((TOWER_C.x, TOWER_C.y, 0)) @ Matrix.Rotation(PI / 8, 4, "Z"),
              off=roff(rng))
    # ribs with crockets
    for i in range(8):
        ang = PI / 8 + i * PI / 4
        dirv = Vector((math.cos(ang), math.sin(ang), 0))
        p_lo = Vector((TOWER_C.x, TOWER_C.y, z0 + 0.45)) + dirv * (rad(z0 + 0.45) + 0.02)
        p_hi = Vector((TOWER_C.x, TOWER_C.y, z1 - 0.3)) + dirv * 0.1
        mb.add_bm(cyl_between(p_lo, p_hi, 0.15, 6, r1=0.06), "Granite", scale=1.0, off=roff(rng))
        n = 11
        for k in range(1, n):
            t = k / n
            p = p_lo.lerp(p_hi, t)
            leaf = lathe([(0.0, 0.0), (0.09 * (1 - t * 0.5), 0.03), (0.06 * (1 - t * 0.5), 0.14), (0.0, 0.2)], segs=5)
            mb.add_bm(leaf, "Granite", scale=1.0,
                      matrix=Matrix.Translation(p + dirv * (0.13 * (1 - t) + 0.05)) @ Matrix.Rotation(-0.5, 4, "Y"))
    # finial knop and iron cross with a weathercock
    top = Vector((TOWER_C.x, TOWER_C.y, z1))
    mb.add_bm(lathe([(0.0, -0.1), (0.2, 0.0), (0.24, 0.2), (0.12, 0.38), (0.15, 0.45), (0.0, 0.55)], segs=10), "Granite",
              matrix=Matrix.Translation(top), smooth=True)
    mb.add_bm(bm_box_minmax(top.x - 0.03, top.y - 0.03, z1 + 0.5, top.x + 0.03, top.y + 0.03, z1 + 1.75), "Iron", scale=2.0)
    mb.add_bm(bm_box_minmax(top.x - 0.03, top.y - 0.38, z1 + 1.3, top.x + 0.03, top.y + 0.38, z1 + 1.36), "Iron", scale=2.0)
    cock = bmesh.new()
    pts2 = [(-0.25, 0.0), (0.2, 0.0), (0.28, 0.12), (0.15, 0.1), (0.1, 0.3), (-0.05, 0.12), (-0.28, 0.28)]
    A = [cock.verts.new((top.x + 0.0, top.y + a, z1 + 1.78 + b)) for a, b in pts2]
    cock.faces.new(A)
    bmesh.ops.solidify(cock, geom=list(cock.faces), thickness=0.02)
    mb.add_bm(cock, "Iron", scale=2.0)
    hull = oct_pts(R0 + 0.12, z0) + [Vector((TOWER_C.x, TOWER_C.y, z1 + 0.5))]
    cols.hull("Spire", hull)


# ===================================================================== nave
def nave(rng, cols):
    """Nave + aisles under one roof (rubble walls, ashlar dressings) built centred, merged by caller."""
    L = NAVE[1] - NAVE[0]
    D = 2 * NAVE_HD
    cxn = (NAVE[0] + NAVE[1]) / 2
    mb = MB()
    Rf = Roof(L, D, NAVE_HE, 50.0, tg=0.6, ov=0.2)
    front, back = Face("front", L, D), Face("back", L, D)
    bodies = [bm_prism(body_profile(Rf), -L / 2, L / 2), bm_prism(gable_profile(Rf), -L / 2, -L / 2 + 0.6),
              bm_prism(gable_profile(Rf), L / 2 - 0.6, L / 2)]
    body = union(bodies)
    cut = []
    porch_a = PORCH_X - cxn
    for x in (-2.0, 3.0, 8.0):              # south lancets
        lancet(mb, front, x - cxn, 1.25, 1.9, 3.4, rng, lights=2, cut=cut, glow=(x == 3.0))
    for x in (-7.0, -2.0, 3.0, 8.0):        # north lancets (back face runs the other way)
        lancet(mb, back, -(x - cxn), 1.25, 1.9, 3.4, rng, lights=2, cut=cut)
    # inner south doorway inside the porch (fake: plank door in a pointed arch)
    pdoor_poly, _ = arch_opening_poly(porch_a, -0.3, 1.3, 2.2, n=10)
    cut.append(face_prism(front, pdoor_poly, -0.35, 0.3))
    body = boolean(body, cut)
    mb.add_bm(body, "Rubble", off=roff(rng))
    arch_ring(mb, front, porch_a, 2.2, 1.3, 0.25, -0.35, 0.03, "Ashlar", rng, n=10)
    import shell as _s
    _s.plank_door_leaf(mb, front, porch_a - 0.65, porch_a + 0.65, -0.3, -0.24, 0.0, 2.2, "Wood_oak", rng)
    tympanum(mb, front, porch_a, 1.3, 2.2, -0.24, rng)
    quoins(mb, L, D, NAVE_HE, rng)
    main_roof(mb, Rf, rng)
    gable_coping(mb, Rf, rng)
    # buttresses
    steps = [(0.85, 2.2), (0.55, 4.2)]
    for x in (-4.5, 0.5, 5.5, 10.5):
        if not (x == -4.5):
            buttress(mb, front, x - cxn, 0.75, steps, rng)
        buttress(mb, back, -(x - cxn), 0.75, steps, rng)
    # granite plinth course and eaves corbel table
    for F in (front, back):
        mb.add_bm(F.box(-L / 2, L / 2, -0.05, 0.12, -0.3, 0.45, bevel=0.02), "Granite", off=roff(rng))
        n = int(L / 0.6)
        for k in range(n):
            a = -L / 2 + 0.3 + k * L / n
            mb.add_bm(F.box(a - 0.09, a + 0.09, -0.05, 0.2, NAVE_HE - 0.32, NAVE_HE + 0.02, bevel=0.015), "Granite",
                      off=roff(rng))
        mb.add_bm(F.box(-L / 2, L / 2, -0.05, 0.24, NAVE_HE + 0.02, NAVE_HE + 0.14, bevel=0.015), "Granite", off=roff(rng))
        damp_strip(mb, F, -L / 2 + 0.3, L / 2 - 0.3, rng, skip=[(porch_a - 2.4, porch_a + 2.4)] if F is front else (),
                   height=1.0)
    # gable crosses
    for sx in (-1, 1):
        stone_cross(mb, (sx * (L / 2 - 0.3), 0.0, Rf.Hr + Rf.rise + 0.1), rng)
    M = Matrix.Translation((cxn, 0, 0))
    cols.box("Nave", NAVE[0], -NAVE_HD, -0.3, NAVE[1], NAVE_HD, NAVE_HE)
    prof = [(-NAVE_HD - Rf.ov, Rf.z_eave - 0.05), (NAVE_HD + Rf.ov, Rf.z_eave - 0.05), (0.0, Rf.Hr + Rf.rise)]
    cols.prism("NaveRoof", prof, NAVE[0], NAVE[1])
    for x in (-4.5, 0.5, 5.5, 10.5):
        if x != -4.5:
            cols.box("Buttress", x - 0.38, -NAVE_HD - 0.9, 0, x + 0.38, -NAVE_HD, 4.4)
        cols.box("Buttress", x - 0.38, NAVE_HD, 0, x + 0.38, NAVE_HD + 0.9, 4.4)
    return mb, M


def chancel(rng, cols):
    L = CH[1] - CH[0]
    D = 2 * CH_HD
    cxc = (CH[0] + CH[1]) / 2
    mb = MB()
    Rc = Roof(L, D, 4.6, 52.0, tg=0.5, ov=0.18)
    bodies = [bm_prism(body_profile(Rc), -L / 2, L / 2), bm_prism(gable_profile(Rc), L / 2 - 0.5, L / 2)]
    body = union(bodies)
    east = Face("right", L, D)
    cut = []
    lancet(mb, east, 0.0, 2.5, 1.6, 4.3, rng, lights=3, ring=0.26, cut=cut, rise_k=1.0)
    for F, a in ((Face("front", L, D), 0.3), (Face("back", L, D), -0.3)):
        lancet(mb, F, a, 0.8, 1.9, 3.3, rng, lights=1, cut=cut)
    body = boolean(body, cut)
    mb.add_bm(body, "Ashlar", off=roff(rng))
    main_roof(mb, Rc, rng)
    # only the east gable is raised (west end runs into the nave gable)
    Rc_e = Rc
    gable_coping(mb, Rc_e, rng)
    stone_cross(mb, (L / 2 - 0.25, 0.0, Rc.Hr + Rc.rise + 0.1), rng, h=0.9)
    # diagonal buttresses at the east corners
    for sy in (-1, 1):
        F = WFace((L / 2, sy * D / 2, 0), (1 / math.sqrt(2), sy / math.sqrt(2), 0))
        buttress(mb, F, 0.0, 0.7, [(0.9, 2.0), (0.55, 3.8)], rng)
    for F in (Face("front", L, D), Face("back", L, D), east):
        mb.add_bm(F.box(-F.length / 2, F.length / 2, -0.05, 0.12, -0.3, 0.45, bevel=0.02), "Granite", off=roff(rng))
        damp_strip(mb, F, -F.length / 2 + 0.3, F.length / 2 - 0.3, rng, height=0.9)
    cols.box("Chancel", CH[0], -CH_HD, -0.3, CH[1], CH_HD, 4.6)
    prof = [(-CH_HD - Rc.ov, Rc.z_eave - 0.05), (CH_HD + Rc.ov, Rc.z_eave - 0.05), (0.0, Rc.Hr + Rc.rise)]
    cols.prism("ChancelRoof", prof, CH[0], CH[1])
    return mb, Matrix.Translation((cxc, 0, 0))


def porch(rng, cols):
    """South porch: built with its axis on local X (entrance on the local west gable), rotated so the
    entrance faces church-local -Y."""
    L, D, He = 3.6, 4.6, 3.5
    mb = MB()
    Rp = Roof(L, D, He, 50.0, tg=0.5, ov=0.15)
    bodies = [bm_prism(body_profile(Rp), -L / 2, L / 2), bm_prism(gable_profile(Rp), -L / 2, -L / 2 + 0.5)]
    body = union(bodies)
    inner = bm_box_minmax(-L / 2 + 0.5, -D / 2 + 0.55, -0.3, L / 2 + 0.3, D / 2 - 0.55, 3.75)
    body = boolean(body, [inner])
    Fe = Face("left", L, D)                      # the entrance gable (outward -X local)
    cut = []
    portal(mb, Fe, 0.0, 1.9, 2.25, 3, rng, depth_step=0.14, rise_k=0.85, cut=cut, cut_depth=0.75)
    body = boolean(body, cut)
    mb.add_bm(body, "Ashlar", off=roff(rng))
    # statue niche in the gable above the arch, a granite saint
    zn = 4.45
    mb.add_bm(Fe.box(-0.42, 0.42, -0.04, 0.12, zn - 0.15, zn, bevel=0.015), "Granite", off=roff(rng))
    npoly, _ = arch_opening_poly(0.0, zn, 0.6, zn + 0.85, n=8)
    mb.add_bm(face_poly(Fe, npoly, 0.005), "GraniteDark")
    arch_ring(mb, Fe, 0.0, zn + 0.85, 0.6, 0.12, -0.02, 0.1, "Granite", rng, n=8)
    saint = lathe([(0.0, 0.0), (0.16, 0.0), (0.17, 0.4), (0.13, 0.75), (0.1, 0.8), (0.07, 0.83), (0.085, 0.9), (0.08, 1.0),
                   (0.0, 1.04)], segs=10)
    mb.add_bm(saint, "Granite", smooth=True, matrix=Matrix.Translation(Fe.p(0.0, 0.12, zn)))
    # stone benches inside along both walls, flagged floor
    for sy in (-1, 1):
        y0, y1 = sorted((sy * (D / 2 - 0.55), sy * (D / 2 - 0.95)))
        mb.add_bm(bm_box_minmax(-L / 2 + 0.55, y0, 0.0, L / 2 - 0.05, y1, 0.45, bevel=0.015), "Granite", off=roff(rng))
    mb.add_bm(geo.bm_quad((-L / 2, -D / 2 + 0.55, 0.01), (L / 2 + 0.3, -D / 2 + 0.55, 0.01), (L / 2 + 0.3, D / 2 - 0.55, 0.01),
                          (-L / 2, D / 2 - 0.55, 0.01)), "Flags")
    # timber ceiling (lambris) under the roof
    mb.add_bm(bm_box_minmax(-L / 2 + 0.5, -D / 2 + 0.55, 3.72, L / 2 + 0.3, D / 2 - 0.55, 3.76), "Wood_dark", scale=1.0)
    quoins(mb, L, D, He, rng)
    main_roof(mb, Rp, rng)
    gable_coping(mb, Rp, rng)
    stone_cross(mb, (-L / 2 + 0.25, 0.0, Rp.Hr + Rp.rise + 0.1), rng, h=0.8)
    for F in (Face("front", L, D), Face("back", L, D)):
        buttress(mb, F, -(L / 2 - 0.4) * (1 if F.name == "front" else -1), 0.6, [(0.6, 1.8), (0.35, 3.0)], rng)
    M = Matrix.Translation((PORCH_X, -NAVE_HD - L / 2 + 0.15, 0)) @ Matrix.Rotation(PI / 2, 4, "Z")
    # collision (church-local): side walls, roof hull
    def W(x, y, z):
        return M @ Vector((x, y, z))
    for sy in (-1, 1):
        y0, y1 = sorted((sy * D / 2, sy * (D / 2 - 0.55)))
        cols.hull("PorchWall", [W(x, y, z) for x in (-L / 2, L / 2) for y in (y0, y1) for z in (0, He)])
        cols.hull("PorchBench", [W(x, y, z) for x in (-L / 2 + 0.55, L / 2) for y in sorted((sy * (D / 2 - 0.55), sy * (D / 2 - 0.95)))
                                 for z in (0, 0.45)])
    for sy in (-1, 1):   # the entrance wall either side of the arch + over it
        y0, y1 = sorted((sy * D / 2, sy * 1.45))
        cols.hull("PorchFront", [W(x, y, z) for x in (-L / 2, -L / 2 + 0.5) for y in (y0, y1) for z in (0, He)])
    cols.hull("PorchArchTop", [W(x, y, z) for x in (-L / 2, -L / 2 + 0.5) for y in (-1.45, 1.45) for z in (3.4, He)])
    prof = [(-D / 2 - Rp.ov, Rp.z_eave - 0.05), (D / 2 + Rp.ov, Rp.z_eave - 0.05), (0.0, Rp.Hr + Rp.rise)]
    cols.hull("PorchRoof", [W(x, y, z) for x in (-L / 2, L / 2) for (y, z) in prof])
    return mb, M


# ==================================================================== build
def build():
    rng = random.Random(1532)
    mb = MB()
    cols = Cols()
    Fw, ws, ww = tower(mb, cols, rng)
    spire(mb, cols, rng)
    for fn in (nave, chancel, porch):
        sub, M = fn(rng, cols)
        mb_merge(mb, sub, M)
    # final frame: rotate +90 about Z (west -> -Y, south -> +X) and centre the footprint
    XS = -1.07
    Mw = Matrix.Translation((XS, 0, 0)) @ Matrix.Rotation(PI / 2, 4, "Z")
    mb_transform(mb, Mw)
    ob = mb.build("ChurchPlouzennec")
    tris = mb.tri_count()
    # west door: oak plank leaf, hinge on the viewer's left, swings into the tower vestibule
    dmb = MB()
    shell.plank_door_leaf(dmb, Fw, -ww / 2, ww / 2, -0.66, -0.58, 0.01, ws - 0.18, "Wood_oak", rng)
    for k in range(6):                      # rows of iron studs
        for j in range(5):
            a = -ww / 2 + 0.15 + j * (ww - 0.3) / 4
            z = 0.3 + k * 0.38
            dmb.add_bm(Fw.box(a - 0.018, a + 0.018, -0.58, -0.565, z - 0.018, z + 0.018), "Iron", scale=2.0)
    mb_transform(dmb, Mw)
    hinge = Mw @ Fw.p(-ww / 2, -0.66, 0.01)
    p0, p1 = Mw @ Fw.p(-ww / 2, -0.665, 0.01), Mw @ Fw.p(ww / 2, -0.575, ws - 0.18)
    door_objs = pivot_object("Door", dmb, hinge, [(min(p0.x, p1.x), min(p0.y, p1.y), 0.01, max(p0.x, p1.x), max(p0.y, p1.y),
                                                    ws - 0.18)])
    tris += dmb.tri_count()
    col_objs = cols.build()
    for o in col_objs:
        o.data.transform(Mw)
    # tower collision split round the vestibule (replace the solid tower base box)
    bell = geo.empty("BellTower", Mw @ Vector((TOWER_C.x, TOWER_C.y, 18.6 + 3.4)))
    visual = [ob, door_objs[0]]
    note = f"Door hinge {tuple(round(v, 3) for v in hinge)}; BellTower {tuple(round(v, 2) for v in bell.location)}"
    pv = [dict(elev=8.0, azim=-35.0, dist_mul=0.9, ground="gravel", target=(XS, -1.0, 19.0)),
          dict(suffix="_porch", elev=8.0, azim=60.0, dist_mul=0.45, ground="gravel", target=(XS + 7.0, -5.6, 4.0)),
          dict(suffix="_spire", elev=10.0, azim=-30.0, dist_mul=0.18, ground="gravel", target=(XS, -12.2, 30.0)),
          dict(suffix="_door", elev=4.0, azim=-10.0, dist_mul=0.12, ground="gravel", target=(XS, -15.0, 2.2))]
    return dict(visual=visual, cols=col_objs + door_objs[1:], empties=[bell], tris=tris, pv=pv, note=note)
