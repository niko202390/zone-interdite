"""Hôtel de la Plage: Belle Époque seafront hotel, requisitioned by the Kriegsmarine (signals post).

Footprint 26 x 14 m: the hotel block is 23 x 14 (world x -13..10) and the coal yard fills the east
3 m (x 10..13, y -3..7). Three storeys + slate attic with dormers, rendered façade over a granite
ashlar ground storey, cast-iron balconies on the first floor, painted name frieze under the cornice.
Separate nodes: Door (front entrance, origin on the hinge) and CoalChute (cellar hatch, origin on its
hinge line along the east wall; rotate about Blender +Y / Godot +X... see note in build())."""
import math
import random

import bmesh
from mathutils import Matrix, Vector

import geo
from geo import MB, bm_box_minmax, bm_cyl
from parts import Face, Opening, roff, text
from common import Cols, WFace, door_node, lathe, pivot_object, sandbag_run, tube, T, R as Rot
import block

W, D, He = 23.0, 14.0, 10.8
XC = -1.5                      # block centre in world x (yard on the east)
BAYS = [-9.0, -6.0, -3.0, 0.0, 3.0, 6.0, 9.0]
Z1, Z2 = 4.35, 7.6             # first / second floor window sills


def _openings():
    o = []
    sh = "Paint_blue"
    st = ["closed", "open", "half", None, "open", "closed", "halfl"]
    for i, a in enumerate(BAYS):
        if a == 0.0:
            o.append(Opening("front", 0.0, 0.0, 1.3, 2.95, kind="entry"))
        else:
            o.append(Opening("front", a, 0.75, 1.2, 2.3, shutters="none", rows=4, glow=(a == 6.0)))
        o.append(Opening("front", a, Z1, 1.1, 2.4, shutters=["open", "closed", "open", "none", "halfl", "open", "closed"][i],
                         paint=sh, rows=4))
        o.append(Opening("front", a, Z2, 1.0, 1.85, shutters=["closed", "open", "closed", "open", "closed", "half", "open"][i],
                         paint=sh, rows=3, glow=(a == -3.0)))
    # back (north): service door, fewer windows
    for a in (-7.5, -3.0, 3.0, 7.5):
        o.append(Opening("back", a, 1.0, 1.0, 1.6, shutters="closed", paint=sh))
        o.append(Opening("back", a, Z1 + 0.4, 1.0, 1.8, shutters="open" if a < 0 else "closed", paint=sh))
        o.append(Opening("back", a, Z2, 0.95, 1.7, shutters="closed", paint=sh))
    o.append(Opening("back", 0.0, 0.0, 1.0, 2.1, kind="door", paint="Paint_green", leaves=1))
    # west gable
    for a in (-3.5, 3.5):
        o.append(Opening("left", a, 0.9, 1.0, 1.8, shutters="closed", paint=sh))
        o.append(Opening("left", a, Z1 + 0.3, 1.0, 1.9, shutters="open", paint=sh))
        o.append(Opening("left", a, Z2, 0.95, 1.7, shutters="closed", paint=sh))
    o.append(Opening("left", 0.0, 12.2, 0.7, 0.9, shutters="none", rows=2, leaves=1))
    # east side (coal yard): service door, small windows
    o.append(Opening("right", 1.5, 0.0, 1.0, 2.1, kind="door", paint="Wood_grey", leaves=1))
    o.append(Opening("right", 4.6, 1.1, 0.8, 1.1, shutters="none", rows=2))
    o.append(Opening("right", -5.0, 1.0, 0.9, 1.5, shutters="closed", paint=sh))
    for a in (-3.5, 3.5):
        o.append(Opening("right", a, Z1 + 0.3, 1.0, 1.9, shutters="closed", paint=sh))
        o.append(Opening("right", a, Z2, 0.95, 1.7, shutters="open", paint=sh))
    return o


def _balcony(mb, F, a0, a1, z, depth, rng, consoles):
    """Granite slab on consoles with a cast-iron railing (balusters, rails, scrolled panels)."""
    t = 0.13
    mb.add_bm(F.box(a0, a1, -0.05, depth, z - t, z, bevel=0.02, segs=2), "Granite", off=roff(rng))
    for ac in consoles:
        for k, (dd, zz) in enumerate(((depth - 0.08, 0.14), (depth * 0.65, 0.3), (depth * 0.35, 0.42))):
            mb.add_bm(F.box(ac - 0.11, ac + 0.11, 0.0, dd, z - t - zz, z - t - (zz - 0.14 if k else 0.0) + 0.001,
                            bevel=0.01), "Granite", off=roff(rng))
    h = 1.0
    i0 = 0.06
    d = depth - 0.07
    pts = lambda aa, dd, zz: F.p(aa, dd, zz)
    # rails: top handrail, middle and bottom bars, running round three sides
    path = [pts(a0 + i0, 0.02, 0), pts(a0 + i0, d, 0), pts(a1 - i0, d, 0), pts(a1 - i0, 0.02, 0)]
    for zz, r in ((h, 0.022), (h - 0.12, 0.009), (0.09, 0.011)):
        mb.add_bm(tube([p + Vector((0, 0, z + zz)) for p in path], r, 6), "Iron", scale=2.0)
    # balusters
    def run(pa, pb):
        L = (pb - pa).length
        n = max(2, int(L / 0.115))
        for k in range(n + 1):
            p = pa.lerp(pb, k / n)
            mb.add_bm(tube([p + Vector((0, 0, z + 0.09)), p + Vector((0, 0, z + h))], 0.0075, 4), "Iron", scale=2.0)
    run(path[0], path[1])
    run(path[1], path[2])
    run(path[2], path[3])
    # scrolled ornament: pairs of C-scrolls in the band under the handrail along the front
    L = (a1 - a0) - 2 * i0
    nmot = max(1, int(L / 0.45))
    for k in range(nmot):
        ac = a0 + i0 + L * (k + 0.5) / nmot
        zc = z + h - 0.06 - 0.06
        for s in (-1, 1):
            ring = []
            for j in range(11):
                ang = math.pi * 0.5 + s * j / 10 * math.pi * 1.4
                ring.append(F.p(ac + s * 0.1 + 0.08 * math.cos(ang) * -s, d, zc - 0.03 + 0.05 * math.sin(ang)))
            mb.add_bm(tube(ring, 0.006, 4), "Iron", scale=2.0)
    # finials on the front corners
    for aa in (a0 + i0, a1 - i0):
        mb.add_bm(lathe([(0.0, 0), (0.03, 0.0), (0.035, 0.04), (0.0, 0.1)], segs=8), "Iron", scale=2.0,
                  matrix=Matrix.Translation(pts(aa, d, z + h)))


def _sign_board(mb, F, a, z, rng):
    """Small white Kriegsmarine office board, black lettering, no insignia."""
    w, h = 1.0, 0.34
    mb.add_bm(F.box(a - w / 2, a + w / 2, 0.0, 0.025, z, z + h, bevel=0.006), "SignWhite", scale=1.0)
    for (a0, a1, z0, z1) in ((a - w / 2, a + w / 2, z, z + 0.018), (a - w / 2, a + w / 2, z + h - 0.018, z + h),
                             (a - w / 2, a - w / 2 + 0.018, z, z + h), (a + w / 2 - 0.018, a + w / 2, z, z + h)):
        mb.add_bm(F.box(a0, a1, 0.025, 0.028, z0, z1), "SignBlack")
    text(mb, F, "MARINENACHRICHTENSTELLE", a, z + 0.20, 0.026, 0.062, "SignBlack", extrude=0.001, spacing=1.0)
    text(mb, F, "PLOUZENNEC", a, z + 0.09, 0.026, 0.05, "SignBlack", extrude=0.001, spacing=1.15)
    for aa in (a - w / 2 + 0.05, a + w / 2 - 0.05):
        mb.add_bm(F.box(aa - 0.01, aa + 0.01, 0.025, 0.035, z + h / 2 - 0.01, z + h / 2 + 0.01), "Iron", scale=2.0)


def _entrance(mb, F, rng):
    """Granite steps, door frame, fanlight, the deep vestibule lining behind the Door node."""
    a0, a1 = -0.65, 0.65
    zt = 2.95
    # two granite steps in front
    mb.add_bm(F.box(a0 - 0.9, a1 + 0.9, -0.2, 0.75, -0.2, 0.0, bevel=0.015, segs=2), "Granite", off=roff(rng))
    mb.add_bm(F.box(a0 - 0.6, a1 + 0.6, -0.2, 0.4, 0.0, 0.16, bevel=0.015, segs=2), "Granite", off=roff(rng))
    # timber frame in the reveal
    P = "Paint_cream"
    dd0, dd1 = -0.3, -0.17
    mb.add_bm(F.box(a0, a0 + 0.06, dd0, dd1, 0.16, zt), P, scale=1.0)
    mb.add_bm(F.box(a1 - 0.06, a1, dd0, dd1, 0.16, zt), P, scale=1.0)
    mb.add_bm(F.box(a0, a1, dd0, dd1, 2.42, 2.52), P, scale=1.0)            # transom
    mb.add_bm(F.box(a0, a1, dd0, dd1, zt - 0.06, zt), P, scale=1.0)
    # fanlight with radial glazing bars
    mb.add_bm(F.quad(a0 + 0.06, a1 - 0.06, 2.52, zt - 0.06, -0.24), "WindowGlass")
    for k in range(1, 6):
        ang = math.pi * k / 6
        c = Vector((0.0, 2.52))
        e = c + Vector((math.cos(ang) * 0.6, math.sin(ang) * 0.37))
        mb.add_bm(tube([F.p(c.x, -0.22, c.y), F.p(e.x, -0.22, e.y)], 0.008, 4), "Paint_cream", scale=1.0)
    # vestibule: floor tiles, dark inner door at the back
    dv = -1.55
    mb.add_bm(F.quad(a0, a1, 0.16, 2.42, dv + 0.02), "Interior")
    mb.add_bm(geo.bm_quad(F.p(a0, -0.3, 0.161), F.p(a1, -0.3, 0.161), F.p(a1, dv, 0.161), F.p(a0, dv, 0.161)), "Flags")
    mb.add_bm(F.box(a0 - 0.05, a1 + 0.05, dv - 0.05, -0.3, -0.3, 0.16), "Granite", off=roff(rng))


def _marquise(mb, F, rng):
    """Glazed cast-iron canopy (marquise) over the entrance, scalloped zinc fringe."""
    a0, a1 = -1.3, 1.3
    zw, zf, dep = 3.62, 3.38, 1.35
    for a in (a0, a1, 0.0):
        mb.add_bm(tube([F.p(a, 0.0, zw - 0.75), F.p(a, dep * 0.55, zf - 0.08), F.p(a, dep, zf)], 0.022, 6), "Iron", scale=2.0)
        mb.add_bm(tube([F.p(a, 0.0, zw), F.p(a, dep, zf)], 0.02, 6), "Iron", scale=2.0)
        ring = [F.p(a, 0.32 + 0.16 * math.cos(2 * math.pi * k / 12), zw - 0.38 + 0.16 * math.sin(2 * math.pi * k / 12))
                for k in range(13)]
        mb.add_bm(tube(ring, 0.01, 4), "Iron", scale=2.0)
    mb.add_bm(tube([F.p(a0, dep, zf), F.p(a1, dep, zf)], 0.03, 6), "Iron", scale=2.0)
    mb.add_bm(tube([F.p(a0, 0.02, zw), F.p(a1, 0.02, zw)], 0.03, 6), "Iron", scale=2.0)
    g = geo.bm_quad(F.p(a0, 0.02, zw + 0.02), F.p(a1, 0.02, zw + 0.02), F.p(a1, dep, zf + 0.02), F.p(a0, dep, zf + 0.02))
    mb.add_bm(g, "WindowGlass")
    n = 20
    for k in range(n):          # scalloped fringe
        aa = a0 + (a1 - a0) * k / n
        ab = a0 + (a1 - a0) * (k + 1) / n
        poly = [(aa, zf), (ab, zf), (ab, zf - 0.12), ((aa + ab) / 2, zf - 0.2), (aa, zf - 0.12)]
        from common import face_poly
        bm = face_poly(F, poly, dep + 0.03)
        bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=0.006)
        mb.add_bm(bm, "Zinc", scale=1.0)


def _frieze(mb, F, rng):
    """Painted name across the frieze below the cornice: oxide-red letters on a cream band."""
    z0, z1 = 9.98, 10.62
    mb.add_bm(F.quad(-8.6, 8.6, z0, z1, 0.004), "Paint_cream", uv=lambda co, n: (co.x * 0.5, co.z * 0.5))
    for (za, zb) in ((z0, z0 + 0.03), (z1 - 0.03, z1)):
        mb.add_bm(F.quad(-8.6, 8.6, za, zb, 0.006), "HotelLetter")
    text(mb, F, "HÔTEL  DE  LA  PLAGE", 0.0, (z0 + z1) / 2, 0.006, 0.46, "HotelLetter", extrude=0.002, spacing=1.12)


def _downpipes(mb, rng):
    for x in (-W / 2 + 0.25, W / 2 - 0.25):
        for y in (-D / 2 - 0.12, D / 2 + 0.12):
            mb.add_bm(tube([(x, y, 0.05), (x, y, He - 0.3), (x, y + (0.25 if y < 0 else -0.25) * 0, He + 0.05)], 0.05, 8),
                      "Zinc", scale=1.0)
            mb.add_bm(lathe([(0.0, He), (0.12, He + 0.02), (0.13, He + 0.22), (0.0, He + 0.22)], segs=8), "Zinc",
                      matrix=Matrix.Translation((x, y, 0)))
    for y in (-D / 2 - 0.12, D / 2 + 0.12):     # gutters along the eaves
        mb.add_bm(tube([(-W / 2 + 0.25, y, He + 0.2), (W / 2 - 0.25, y, He + 0.2)], 0.075, 8), "Zinc")


def _coal_yard(mb, cols, rng):
    """Rubble yard walls with granite coping and a planked gate; coal heap, sacks; chute curb."""
    x0, x1 = W / 2, W / 2 + 3.0
    y0, y1 = -3.0, D / 2
    t, h = 0.4, 2.2
    walls = [("front", x0, y0 - t / 2, x1, y0 + t / 2), ("side", x1 - t, y0 - t / 2, x1, y1), ("back", x0, y1 - t, x1, y1)]
    for nm, a, b, c, d in walls:
        if nm == "front":           # gate opening 1.5 m in the front wall
            segs = [(a, a + 0.55), (a + 2.05, c)]
            for (sa, sb) in segs:
                mb.add_bm(bm_box_minmax(sa, b, -0.2, sb, d, h), "Rubble", off=roff(rng))
                mb.add_bm(bm_box_minmax(sa - 0.04, b - 0.05, h, sb + 0.04, d + 0.05, h + 0.14, bevel=0.015), "Granite", off=roff(rng))
                cols.box("YardWall", sa, b, 0, sb, d, h + 0.14)
            for ga in (a + 0.55, a + 2.05):   # gate piers
                mb.add_bm(bm_box_minmax(ga - 0.22, b - 0.05, -0.2, ga + 0.22, d + 0.05, h + 0.25, bevel=0.015), "Granite", off=roff(rng))
            F = WFace((a + 1.3, y0, 0), (0, -1, 0))
            for k in range(7):
                pa = -0.73 + k * 0.21
                mb.add_bm(F.box(pa, pa + 0.2, 0.02, 0.05, 0.08, 1.9 + 0.08 * math.sin(k)), "Wood_grey", scale=1.0, off=roff(rng))
            for zc in (0.4, 1.55):
                mb.add_bm(F.box(-0.73, 0.73, 0.05, 0.08, zc - 0.07, zc + 0.07), "Wood_grey", scale=1.0)
            cols.box("YardGate", a + 0.55, y0 - 0.1, 0, a + 2.05, y0 + 0.1, 2.0)
        else:
            mb.add_bm(bm_box_minmax(a, b, -0.2, c, d, h), "Rubble", off=roff(rng))
            mb.add_bm(bm_box_minmax(a - 0.05, b - 0.05, h, c + 0.05, d + 0.05, h + 0.14, bevel=0.015), "Granite", off=roff(rng))
            cols.box("YardWall", a, b, 0, c, d, h + 0.14)
    # coal heap in the north-east corner
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=1.0)
    for v in bm.verts:
        c = v.co
        n = 0.12 * math.sin(c.x * 7.1) * math.sin(c.y * 6.3) + 0.08 * math.sin(c.z * 11 + c.x * 5)
        v.co = Vector((c.x * 1.3 * (1 + n), c.y * 1.6 * (1 + n), max(c.z, -0.05) * 0.8 * (1 + n)))
    mb.add_bm(bm, "Coal", scale=1.0, matrix=Matrix.Translation((x1 - 1.4, y1 - 1.9, 0.0)))
    cols.box("CoalHeap", x1 - 2.6, y1 - 3.5, 0, x1 - 0.2, y1 - 0.3, 0.7)
    from props import _bag
    for k, (bx, by, rz) in enumerate(((x0 + 0.6, 1.2, 0.3), (x0 + 0.65, 1.9, -0.2), (x0 + 0.7, 1.55, 0.1))):
        bm = _bag(0.75, 0.45, 0.3 if k < 2 else 0.28, rng)
        mb.add_bm(bm, "Burlap", scale=2.0, off=roff(rng), smooth=True, smooth_angle=70,
                  matrix=Matrix.Translation((bx, by, 0.14 + (0.25 if k == 2 else 0))) @ Matrix.Rotation(rz + 1.57, 4, "Z"))


def _coal_chute(rng):
    """Cast-iron cellar hatch on a granite curb against the east wall. Returns (objects, curb into mb fn)."""
    yc = 4.6 - 1.6          # hatch centre along the wall (y), clear of the service door
    hw, out = 0.42, 0.62
    xw = W / 2
    zt = 0.12
    hmb = MB()
    hmb.add_bm(bm_box_minmax(xw + 0.02, yc - hw, zt, xw + 0.02 + out, yc + hw, zt + 0.025), "Iron", scale=2.0)
    for k in range(5):          # cast diamond-tread ribs
        yy = yc - hw + 0.1 + k * (2 * hw - 0.2) / 4
        hmb.add_bm(bm_box_minmax(xw + 0.06, yy - 0.012, zt + 0.025, xw + out - 0.02, yy + 0.012, zt + 0.035), "Iron", scale=2.0)
    hmb.add_bm(bm_box_minmax(xw + out - 0.08, yc - 0.06, zt + 0.025, xw + out - 0.03, yc + 0.06, zt + 0.06), "Iron", scale=2.0)
    for yy in (yc - hw + 0.08, yc + hw - 0.08):      # hinge knuckles on the wall side
        hmb.add_bm(geo.bm_cyl(0.022, 0.022, 0.1, segs=8), "Iron", scale=2.0,
                   matrix=Matrix.Translation((xw + 0.03, yy + 0.05, zt + 0.02)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    pivot = (xw + 0.03, yc, zt + 0.02)
    objs = pivot_object("CoalChute", hmb, pivot, [(xw + 0.02, yc - hw, zt, xw + 0.02 + out, yc + hw, zt + 0.035)])

    def curb(mb):
        for (a, b, c, d) in ((xw, yc - hw - 0.12, xw + out + 0.14, yc - hw), (xw, yc + hw, xw + out + 0.14, yc + hw + 0.12),
                             (xw + out + 0.02, yc - hw, xw + out + 0.14, yc + hw)):
            mb.add_bm(bm_box_minmax(a, b, -0.15, c, d, zt, bevel=0.012), "Granite", off=roff(rng))
        # dark chute throat under the hatch (visible when it is lifted)
        mb.add_bm(geo.bm_quad((xw, yc - hw, -0.5), (xw + out + 0.02, yc - hw, -0.3), (xw + out + 0.02, yc + hw, -0.3),
                              (xw, yc + hw, -0.5)), "Void")
        for s in (-1, 1):
            y = yc + s * hw
            mb.add_bm(geo.bm_quad((xw, y, -0.5), (xw + out + 0.02, y, -0.3), (xw + out + 0.02, y, zt), (xw, y, zt)), "Void")
        mb.add_bm(geo.bm_quad((xw + out + 0.02, yc - hw, -0.3), (xw + out + 0.02, yc + hw, -0.3),
                              (xw + out + 0.02, yc + hw, zt), (xw + out + 0.02, yc - hw, zt)), "Void")
    return objs, curb, pivot


def build():
    rng = random.Random(1944)
    mb = MB()
    Ff = Face("front", W, D)
    # the vestibule behind the entrance (1.55 m deep) so the Door can swing in
    vest = Ff.box(-0.68, 0.68, -1.6, 0.3, -0.3, 2.97)
    dormers = [dict(a=a, wd=1.9, zd=1.75, z0=0.05, w=1.0, h=1.3, glow=(a == 3.0)) for a in (-9.0, -3.0, 3.0, 9.0)]
    spec = dict(W=W, D=D, He=He, pitch=40.0, wall="RenderPale", seed=1944, openings=_openings(), dormers=dormers,
                chimneys=[-1, 1], ridge_chimneys=[-4.5, 4.5], cornice=True, bands=[(3.92, 0.18), (7.2, 0.12)],
                lower=(4.0, "Ashlar"), extra_cuts=[vest], mb=mb,
                damp_skip={"front": [(-1.6, 1.6)]})
    B = block.build_block(spec)
    cols = B["cols"]
    F = B["faces"]["front"]
    # balconies: one long central balcony over the entrance, singles on the other first-floor bays
    for a in BAYS:
        if abs(a) < 4:
            continue
        _balcony(mb, F, a - 0.85, a + 0.85, Z1, 0.62, rng, consoles=(a - 0.6, a + 0.6))
    _balcony(mb, F, -3.9, 3.9, Z1, 0.85, rng, consoles=(-3.6, -2.4, -0.6, 0.6, 2.4, 3.6))
    _entrance(mb, F, rng)
    _frieze(mb, F, rng)
    _marquise(mb, F, rng)
    _sign_board(mb, F, 1.72, 1.45, rng)
    _downpipes(mb, rng)
    # sandbag blast walls flanking the entrance (an L each side, gap in the middle)
    y = -D / 2
    sandbag_run(mb, cols, (-2.0, y - 0.35, 0), (-2.0, y - 2.6, 0), 8, rng, "SandbagsW")
    sandbag_run(mb, cols, (-2.0, y - 2.6, 0), (-0.9, y - 2.6, 0), 8, rng, "SandbagsW2")
    sandbag_run(mb, cols, (2.0, y - 0.35, 0), (2.0, y - 2.6, 0), 8, rng, "SandbagsE")
    sandbag_run(mb, cols, (2.0, y - 2.6, 0), (0.9, y - 2.6, 0), 8, rng, "SandbagsE2")
    _coal_yard(mb, cols, rng)
    chute_objs, curb, chute_pivot = _coal_chute(rng)
    curb(mb)
    # collision: block body split round the vestibule, steps
    dv = -1.6
    cols.box("Body", -W / 2, -D / 2 + 1.6, -0.3, W / 2, D / 2, He)
    cols.box("FrontW", -W / 2, -D / 2, -0.3, -0.68, -D / 2 + 1.6, He)
    cols.box("FrontE", 0.68, -D / 2, -0.3, W / 2, -D / 2 + 1.6, He)
    cols.box("FrontTop", -0.68, -D / 2, 2.97, 0.68, -D / 2 + 1.6, He)
    cols.box("Steps", -1.55, -D / 2 - 0.75, -0.2, 1.55, -D / 2, 0.0)
    cols.box("Steps2", -1.25, -D / 2 - 0.4, 0.0, 1.25, -D / 2, 0.16)
    cols.box("Balcony", -3.9, -D / 2 - 0.85, Z1 - 0.13, 3.9, -D / 2, Z1 + 1.0)
    block.step_cols(cols, B["faces"], [o for o in B["ops"] if o.kind != "entry"])
    ob = mb.build("HotelDeLaPlage")
    tris = mb.tri_count()
    door_objs, dtris, hinge = door_node("Door", F, -0.59, 0.59, -0.26, -0.2, 0.16, 2.42, "Door_bleu", rng,
                                        kind="panel", glazed_top=True)
    col_objs = cols.build()
    # shift everything so the 26 x 14 footprint (block + yard) is centred on the origin
    shift = Matrix.Translation((XC, 0, 0))
    for o in [ob] + col_objs:
        o.data.transform(shift)
    for o in (door_objs[0], chute_objs[0]):
        o.location.x += XC
    hinge_w = (hinge.x + XC, hinge.y, hinge.z)
    chute_w = (chute_pivot[0] + XC, chute_pivot[1], chute_pivot[2])
    note = f"Door hinge {tuple(round(v, 3) for v in hinge_w)}; CoalChute pivot {tuple(round(v, 3) for v in chute_w)}"
    visual = [ob, door_objs[0], chute_objs[0]]
    cols_all = col_objs + door_objs[1:] + chute_objs[1:]
    pv = [dict(elev=10.0, azim=-28.0, dist_mul=0.62, ground="cobble"),
          dict(suffix="_detail", elev=6.0, azim=-14.0, dist_mul=0.2, ground="cobble", target=(XC + 0.5, -7.0, 2.6)),
          dict(suffix="_yard", elev=45.0, azim=70.0, dist_mul=0.3, ground="cobble", target=(XC + 13.0, 1.0, 1.0))]
    return dict(visual=visual, cols=cols_all, empties=[], tris=tris + dtris, pv=pv, note=note)
