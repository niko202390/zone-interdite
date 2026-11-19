"""House specs + furnishing for the three enterable houses."""
import math
import random

import bmesh
from mathutils import Matrix, Vector

import geo
from geo import MB, bm_box_minmax, bm_cyl, bm_prism, collision_bm
import houses
import props as envprops
import furniture as fu
from furniture import T, Rx, Ry, Rz
from ihelp import Put, place, lathe, tube, cyl_x, cyl_y, multi_box_obj, IFace
import shell

T_WALL = 0.55
FZ = 0.13


def _box_cav(bb):
    return lambda: bm_box_minmax(*bb)


# ===================================================================== lamps
def _lamp_object(name, build, at):
    mb = MB()
    build(Put(mb, Matrix.Translation(at)))
    ob = mb.build(name)
    ob.data.transform(Matrix.Translation(-Vector(at)))
    ob.location = at
    return ob, mb.tri_count()


def hanging_oil_lamp(P, drop=0.6):
    """Suspension lamp: chain from the ceiling hook, brass font, glass chimney, opal shade.
    Origin = flame. Chain goes up `drop` metres."""
    P.bm(tube([(0, 0, 0.32), (0, 0, drop)], 0.006, 4), "Iron", scale=2.0)
    for k in range(3):                               # three-arm gallery
        a = 2 * math.pi * k / 3
        P.bm(tube([(0, 0, 0.32), (math.cos(a) * 0.17, math.sin(a) * 0.17, 0.08)], 0.004, 4), "Brass", scale=2.0)
    P.bm(lathe([(0.0, -0.12), (0.03, -0.12), (0.075, -0.07), (0.08, -0.03), (0.05, -0.01), (0.02, 0.0), (0.0, 0.0)],
               segs=16), "Brass", smooth=True, scale=2.0)
    P.bm(lathe([(0.025, 0.0), (0.03, 0.04), (0.02, 0.09), (0.017, 0.2), (0.0, 0.2)], segs=12, cap_top=False),
         "LampGlow", smooth=True)
    P.bm(lathe([(0.04, 0.06), (0.11, 0.1), (0.19, 0.08), (0.19, 0.072), (0.11, 0.09), (0.04, 0.05)], segs=20,
               cap_top=False, cap_bottom=False), "EnamelWhite", smooth=True, scale=2.0)
    P.bm(lathe([(0.08, 0.3), (0.06, 0.34), (0.0, 0.35)], segs=12, cap_bottom=True), "Brass", scale=2.0)   # smoke bell


def hurricane_lantern(P):
    """Lampe tempete standing on a shelf. Origin = flame (about 0.13 above its base)."""
    P.bm(lathe([(0.0, -0.13), (0.07, -0.13), (0.075, -0.09), (0.05, -0.06), (0.03, -0.05), (0.0, -0.05)], segs=14),
         "Iron", smooth=True, scale=2.0)
    P.bm(lathe([(0.03, -0.05), (0.06, 0.0), (0.065, 0.05), (0.04, 0.11), (0.0, 0.11)], segs=14, cap_top=False),
         "LampGlow", smooth=True)
    P.bm(lathe([(0.0, 0.12), (0.05, 0.11), (0.06, 0.13), (0.03, 0.16), (0.0, 0.17)], segs=12), "Iron", scale=2.0)
    for sx in (-1, 1):
        P.bm(tube([(sx * 0.075, 0, -0.1), (sx * 0.085, 0, 0.05), (sx * 0.05, 0, 0.13)], 0.005, 4), "Iron", scale=2.0)
    P.bm(tube([(-0.05, 0, 0.17), (0, 0, 0.24), (0.05, 0, 0.17)], 0.004, 4), "Iron", scale=2.0)


def table_oil_lamp(P):
    """Small brass oil lamp with glass chimney (lampe Pigeon type). Origin = flame (0.17 above base)."""
    P.bm(lathe([(0.0, -0.17), (0.055, -0.17), (0.055, -0.155), (0.025, -0.14), (0.02, -0.1), (0.05, -0.07),
                (0.05, -0.03), (0.02, -0.01), (0.0, -0.01)], segs=14), "Brass", smooth=True, scale=2.0)
    P.bm(lathe([(0.02, -0.01), (0.03, 0.03), (0.018, 0.07), (0.016, 0.15), (0.0, 0.15)], segs=12, cap_top=False),
         "LampGlow", smooth=True)


def cafe_pendant(P, drop=0.7):
    """Enamelled conical shade with a bulb (electric). Origin = bulb."""
    P.bm(tube([(0, 0, 0.06), (0, 0, drop)], 0.004, 4), "BlackPaint", scale=2.0)
    P.bm(lathe([(0.03, 0.09), (0.04, 0.06), (0.16, -0.04), (0.2, -0.07)], segs=20, cap_top=False, cap_bottom=False),
         "EnamelGreen", smooth=True)
    P.bm(lathe([(0.197, -0.068), (0.157, -0.038), (0.037, 0.057), (0.027, 0.087)], segs=20, cap_top=False,
               cap_bottom=False), "EnamelWhite", smooth=True)
    P.bm(lathe([(0.0, -0.06), (0.025, -0.055), (0.032, -0.03), (0.02, 0.0), (0.015, 0.03), (0.0, 0.03)], segs=12),
         "LampGlow", smooth=True)


# ============================================================ floors / beams
def beams_y(P, xs, y0, y1, zb, zt, w=0.24, mat="Wood_dark"):
    for x in xs:
        P.box(x - w / 2, y0, zb, x + w / 2, y1, zt, mat, bevel=0.012, segs=1, scale=1.0)


def joists_x(P, x0, x1, ys, zb, zt, w=0.1, mat="Wood_dark"):
    for y in ys:
        P.box(x0, y - w / 2, zb, x1, y + w / 2, zt, mat, scale=1.0)


def joists_y(P, y0, y1, xs, zb, zt, w=0.1, mat="Wood_dark"):
    for x in xs:
        P.box(x - w / 2, y0, zb, x + w / 2, y1, zt, mat, scale=1.0)


def holed_boxes(bb, hole):
    """Split slab bb (x0,y0,z0,x1,y1,z1) around rectangular hole (hx0,hy0,hx1,hy1) into boxes."""
    x0, y0, z0, x1, y1, z1 = bb
    hx0, hy0, hx1, hy1 = hole
    out = []
    if hx0 > x0:
        out.append((x0, y0, z0, hx0, y1, z1))
    if hx1 < x1:
        out.append((hx1, y0, z0, x1, y1, z1))
    if hy0 > y0:
        out.append((hx0, y0, z0, hx1, hy0, z1))
    if hy1 < y1:
        out.append((hx0, hy1, z0, hx1, y1, z1))
    return out


def damp_patch(P, IF, a, z, w, h):
    bm = IF.quad(a - w / 2, a + w / 2, z, z + h, 0.01, [(0, 0), (1, 0), (1, 1), (0, 1)])
    P.mb.add_bm(bm, "DecalDampPatch", uv="keep")


def env_prop(name, fn, M):
    """Instance an exterior-kit prop (barrel, crate) as its own mesh, with its collision."""
    vis, cols, _, tris, _ = fn()
    out = []
    for o in vis:
        o.name = name
        o.matrix_world = M
    for c in cols:
        c.name = f"{name}-colonly" if c.name.endswith("-colonly") else c.name.replace("Barrel", name)
        c.matrix_world = M
    return vis + cols, tris


# ===================================================================== BOURG
def bourg():
    sp = houses.spec_bourg()
    W, D, He = sp["W"], sp["D"], sp["He"]
    t = T_WALL
    xi, yi = W / 2 - t, D / 2 - t
    ops = sp["openings"]
    for i in (0, 1, 2, 3, 4, 5, 7, 8, 9):
        ops[i].through = True
        ops[i].glow = False
    ops[1].enter = "Door"
    ops[1].door_paint = "Door_bleu"
    ztop = 5.6
    z1 = 2.95                        # upper floor level
    sp.update(t=t, floor_z=FZ, cavity=[_box_cav((-xi, -yi, 0.0, xi, yi, ztop))], cavity_aabb=(-xi, -yi, 0.0, xi, yi, ztop),
              ceil_mat="Wood_oak", door_paint="Door_bleu", roof_col="solid",
              damp_skip_in={"right": [(-1.3, 1.3)]})
    S = shell.build_shell(sp)
    rng = random.Random(7101)
    mb = MB()
    P = Put(mb, rng=rng)
    cols = P.cols
    # ---- floors, beams, ceilings
    P.box(-xi, -yi, 0.0, xi, yi, FZ, "Flags", scale=0.5)
    P.box(-0.55, -D / 2 + 0.2, -0.05, 0.55, -yi, FZ, "Flags", scale=0.5)     # doorway flags (under the threshold)
    hole = (-xi, -1.45, -2.48, 1.25)
    for bb in holed_boxes((-xi, -yi, 2.82, xi, yi, z1), hole):
        P.box(*bb, "Wood_oak", scale=1.0)
    beams_y(P, (-1.6, 0.4, 2.2), -yi - 0.05, yi + 0.05, 2.52, 2.82)
    ys = [-yi + 0.3 + 0.5 * k for k in range(12)]
    for (xa, xb) in ((-xi, -1.72), (-1.48, 0.28), (0.52, 2.08), (2.32, xi)):
        for y in ys:
            if xa < -2.5 and hole[1] - 0.05 < y < hole[3] + 0.05:
                P.box(-2.48, y - 0.05, 2.70, xb, y + 0.05, 2.82, "Wood_dark", scale=1.0)
            else:
                P.box(xa, y - 0.05, 2.70, xb, y + 0.05, 2.82, "Wood_dark", scale=1.0)
    P.box(-2.6, hole[1], 2.64, -2.48, hole[3], 2.82, "Wood_dark", scale=1.0)        # trimmer
    P.box(-xi, hole[1] - 0.12, 2.64, -2.48, hole[1], 2.82, "Wood_dark", scale=1.0)
    beams_y(P, (-1.6, 0.4, 2.2), -yi - 0.05, yi + 0.05, 5.32, ztop)
    for (xa, xb) in ((-xi, -1.72), (-1.48, 0.28), (0.52, 2.08), (2.32, xi)):
        joists_x(P, xa, xb, ys, 5.48, ztop)
    # ---- staircase (left gable wall), 14 risers
    N = 14
    rise = (z1 - FZ) / N
    g = 0.25
    sx0, sx1 = -xi + 0.02, -2.6
    y0 = -2.0
    for i in range(1, N):
        ya, yb = y0 + (i - 1) * g - 0.03, y0 + i * g
        P.box(sx0 + 0.03, ya, FZ + i * rise - 0.04, sx1 - 0.03, yb, FZ + i * rise, "Wood_oak", bevel=0.006, scale=1.0)
        P.box(sx0 + 0.03, yb - 0.02, FZ + (i - 1) * rise, sx1 - 0.03, yb, FZ + i * rise - 0.04, "Wood_oak", scale=1.0)
    L = math.hypot(N * g, z1 - FZ)
    ang = math.atan2(z1 - FZ, N * g)
    for x in (sx0 + 0.03, sx1 - 0.03):
        prof = [(y0 - 0.05, FZ), (y0 + (N - 1) * g, z1 - 0.32), (y0 + (N - 1) * g, z1 - 0.05), (y0 - 0.05, FZ + 0.32)]
        P.bm(bm_prism(prof, x - 0.03, x + 0.03), "Wood_dark", scale=1.0)
    # handrail + balusters on the open side, newel posts
    def zs(y):
        return FZ + (y - (y0 - g)) * (z1 - FZ) / (N * g)
    hx = sx1 - 0.03
    P.box(hx - 0.04, y0 - 0.04, FZ, hx + 0.04, y0 + 0.04, FZ + 1.05, "Wood_dark", bevel=0.01)
    for i in range(1, N):
        y = y0 + (i - 0.5) * g
        P.box(hx - 0.016, y - 0.016, FZ + i * rise, hx + 0.016, y + 0.016, zs(y) + 0.9, "Wood_dark")
    ya, yb = y0, y0 + (N - 1) * g
    rail = bm_prism([(ya, zs(ya) + 0.92), (yb, zs(yb) + 0.92), (yb, zs(yb) + 0.98), (ya, zs(ya) + 0.98)], hx - 0.03, hx + 0.03)
    P.bm(rail, "Wood_dark", scale=1.0)
    # balustrade around the stairwell upstairs
    bz = z1
    P.box(-2.52, hole[1] - 0.02, bz + 0.9, -2.44, hole[3] + 0.0, bz + 0.96, "Wood_dark", bevel=0.01)
    P.box(-xi, hole[1] - 0.06, bz + 0.9, -2.44, hole[1] + 0.02, bz + 0.96, "Wood_dark", bevel=0.01)
    for y in [hole[1] + 0.12 * k for k in range(int((hole[3] - hole[1]) / 0.12) + 1)]:
        P.box(-2.5, y - 0.015, bz, -2.47, y + 0.015, bz + 0.9, "Wood_dark")
    for x in [-xi + 0.12 * k for k in range(1, 8)]:
        P.box(x - 0.015, hole[1] - 0.035, bz, x + 0.015, hole[1] - 0.005, bz + 0.9, "Wood_dark")
    P.box(-2.54, hole[1] - 0.06, bz, -2.44, hole[1] + 0.04, bz + 1.05, "Wood_dark", bevel=0.01)
    cols += [("Balustrade", (-2.54, hole[1], bz, -2.44, hole[3], bz + 1.0)),
             ("Balustrade", (-xi, hole[1] - 0.06, bz, -2.44, hole[1] + 0.04, bz + 1.0))]
    # ---- ground floor furniture
    fu.fireplace(P.sub(place(xi - 0.31, 0.0, FZ, -90)), Wf=1.5, Dp=0.62, Hj=1.3, hood_top=2.82 - FZ)
    fu.lit_clos(P.sub(place(-0.2, yi - 0.41, FZ, 0)))
    fu.table(P.sub(place(-0.2, 0.95, FZ, 0)), L=1.9, W=0.8)
    fu.bench(P.sub(place(-0.2, 0.33, FZ, 0)), L=1.8)
    fu.dresser(P.sub(place(1.3, -yi + 0.26, FZ, 180)), W=1.3)
    fu.longcase_clock(P.sub(place(2.72, yi - 0.17, FZ, 0)))
    fu.kneading_trough(P.sub(place(-1.55, -yi + 0.3, FZ, 180)))
    fu.chair_breton(P.sub(place(2.2, -1.55, FZ, -60)))
    fu.chair_breton(P.sub(place(1.0, 1.55, FZ, 170)))
    fu.stool(P.sub(place(2.25, 1.6, FZ, 0)))
    tz = FZ + 0.76
    fu.loaf(P, -0.6, 1.05, tz)
    fu.bowl(P, 0.15, 0.8, tz, r=0.06, h=0.05)
    fu.bowl(P, -0.25, 0.75, tz, r=0.06, h=0.05)
    fu.jug(P, 0.4, 1.1, tz, h=0.22, mat="Faience", rot=40)
    fu.bottle(P, 0.0, 1.15, tz, kind=3)
    mz = FZ + 1.3 + 0.24 + 0.06
    fu.candle(P, xi - 0.55, -0.85, mz)
    fu.jug(P, xi - 0.55, 0.75, mz, h=0.18, mat="Copper", rot=90)
    # damp patches
    IF = S["ifaces"]
    damp_patch(P, IF["front"], 2.6, FZ + 0.1, 1.1, 0.9)
    damp_patch(P, IF["back"], -2.4, FZ + 0.6, 0.8, 0.7)
    damp_patch(P, IF["left"], 2.2, FZ + 1.4, 1.0, 1.1)
    damp_patch(P, IF["back"], 0.3, z1 + 1.8, 1.3, 0.8)
    damp_patch(P, IF["front"], -1.2, z1 + 0.2, 0.9, 0.8)
    # ---- upper floor bedroom
    fu.bed(P.sub(place(xi - 1.0, 0.8, z1, -90)))
    fu.armoire(P.sub(place(-0.2, yi - 0.31, z1, 0)))
    fu.chest(P.sub(place(1.15, 0.8, z1, -90)), L=1.0, D=0.48, H=0.55)
    fu.washstand(P.sub(place(1.3, -yi + 0.22, z1, 180)))
    fu.chair_breton(P.sub(place(-1.2, -1.9, z1, 200)))
    fu.chair_breton(P.sub(place(2.6, -1.3, z1, 120)))
    # ---- lamps + light spots
    lamps = []
    lamps.append(_lamp_object("Lamp_0", lambda Q: hanging_oil_lamp(Q, drop=2.70 - 1.95), (-0.2, 0.95, 1.95)))
    lamps.append(_lamp_object("Lamp_1", table_oil_lamp, (1.15, 0.65, z1 + 0.55 + 0.17)))
    spots = [("LightSpot_0", (-0.2, 0.95, 1.95 + 0.06)), ("LightSpot_1", (1.15, 0.65, z1 + 0.55 + 0.17 + 0.05))]
    # ---- collision: floors, ramp, ceilings
    nav = [("NavFloor_0", [(-xi, -yi, FZ - 0.1, xi, yi, FZ), (-0.5, -D / 2 + 0.25, FZ - 0.1, 0.5, -yi, FZ)]),
           ("NavFloor_1", holed_boxes((-xi, -yi, 2.82, xi, yi, z1), hole))]
    ramp = [(y0 - g, FZ), (y0 + (N - 1) * g, z1), (y0 + (N - 1) * g, FZ)]
    ramps = [("Stairs", bm_prism(ramp, sx0, sx1))]
    cols.append(("Ceiling_1", (-xi, -yi, ztop, xi, yi, ztop + 0.1)))
    cols.append(("StairNewel", (hx - 0.04, y0 - 0.04, FZ, hx + 0.04, y0 + 0.04, FZ + 1.05)))
    storeys = [("ground", FZ), ("upper", z1)]
    probe = dict(shot_in=[((-0.3, -2.3, FZ + 1.6), (1.2, 2.0, FZ + 1.0)), ((-2.0, 1.6, FZ + 1.6), (3.0, -0.5, FZ + 0.9)),
                          ((2.4, -2.4, FZ + 1.6), (-2.5, 1.5, FZ + 1.0)), ((-2.9, 1.9, z1 + 1.6), (2.5, -0.5, z1 + 0.8))],
                 ext=dict(elev=6.0, azim=-20.0, dist_mul=0.6, target=(0.0, -3.0, 2.2)),
                 hearth=(xi - 0.35, 0.0, FZ + 0.3))
    return dict(name="house_bourg_int", shell=S, mb=mb, cols=cols, nav=nav, ramps=ramps, lamps=lamps, spots=spots,
                extra=[], storeys=storeys, preview=probe, stairs=dict(x=(sx0, sx1), y=(y0 - g, y0 + (N - 1) * g),
                                                                      z=(FZ, z1), angle=math.degrees(ang)))


# =================================================================== LONGERE
def longere():
    sp = houses.spec_longere()
    W, D, He = sp["W"], sp["D"], sp["He"]
    t = T_WALL
    yi = D / 2 - t
    ops = sp["openings"]
    rx0, rx1 = -W / 2 + t, 1.0          # living room / loft span; byre beyond the cross wall stays solid
    for i in (0, 1, 2, 5, 7):
        ops[i].through = True
        ops[i].glow = False
    ops[1].h = 2.05                       # taller door for a 1.8 m player
    ops[1].enter = "Door"
    ops[1].door_paint = "Door_bottle"
    sp["dormers"][0]["through"] = True    # loft dormer
    R = houses.Roof(W, D, He, sp["pitch"])
    zl = 2.52                             # loft floor

    def zc(y):
        return R.z_at(y) - 0.26

    prof = [(-yi, 0.0), (yi, 0.0), (yi, zc(yi)), (0.0, zc(0.0)), (-yi, zc(yi))]

    def roof_cols(R):
        out = []
        for s in (-1, 1):
            p = [(s * (D / 2 + R.ov), R.z_eave - 0.05), (0.0, R.Hr + R.rise), (0.0, zc(0.0)), (s * yi, zc(yi))]
            if s > 0:
                p = list(reversed(p))
            out.append(collision_bm(f"RoofLoft{'F' if s < 0 else 'B'}", bm_prism(p, -W / 2, rx1 + 0.05)))
        prof2 = [(-D / 2 - R.ov, R.z_eave - 0.05), (D / 2 + R.ov, R.z_eave - 0.05), (0.0, R.Hr + R.rise)]
        out.append(collision_bm("RoofByre", bm_prism(prof2, rx1, W / 2)))
        from parts import gable_profile
        out.append(collision_bm("GableLeft", bm_prism(gable_profile(R), -W / 2, -W / 2 + t)))
        return out

    sp.update(t=t, floor_z=FZ, cavity=[lambda: bm_prism(prof, rx0, rx1)],
              cavity_aabb=(rx0, -yi, 0.0, rx1, yi, zc(0.0)), ceil_mat="Wood_dark", door_paint="Door_bottle",
              roof_col="loft", roof_col_fn=roof_cols, room_x=(rx0, rx1),
              solid_boxes=[("Byre", (rx1, -yi, -0.3, W / 2 - t, yi, He + 0.6))],
              damp_skip_in={"left": [(-1.4, 1.4)]}, damp_h=1.0)
    S = shell.build_shell(sp)
    # wall collision for the loft knee walls: raise front/back wall boxes above the eaves
    S["cols"] = [(n, (bb[0], bb[1], bb[2], bb[3], bb[4], max(bb[5], zc(yi) + 0.1) if n.startswith(("Wall_front", "Wall_back")) and not n.endswith("lintel") else bb[5]))
                 for n, bb in S["cols"]]
    S["cols"] = [(n, (bb[0], bb[1], bb[2], bb[3], bb[4], max(bb[5], zc(yi) + 0.1))) if n.endswith("lintel") else (n, bb)
                 for n, bb in S["cols"]]
    rng = random.Random(7202)
    mb = MB()
    P = Put(mb, rng=rng)
    cols = P.cols
    # ---- floor, loft floor with hatch, beams
    P.box(rx0, -yi, 0.0, rx1, yi, FZ, "Flags", scale=0.5)
    P.box(-4.15, -D / 2 + 0.2, -0.05, -3.05, -yi, FZ, "Flags", scale=0.5)
    hatch = (-0.95, 1.35, -0.05, 2.15)
    for bb in holed_boxes((rx0, -yi, 2.45, rx1, yi, zl), hatch):
        P.box(*bb, "Wood_oak", scale=1.0)
    P.box(rx0 - 0.05, -0.14, 2.04, rx1 + 0.05, 0.14, 2.30, "Wood_dark", bevel=0.015, scale=1.0)       # main beam (poutre)
    xs = [rx0 + 0.25 + 0.5 * k for k in range(int((rx1 - rx0 - 0.3) / 0.5) + 1)]
    for x in xs:
        if hatch[0] - 0.06 < x < hatch[2] + 0.06:
            joists_y(P, -yi, -0.14, [x], 2.30, 2.45, w=0.11)
            joists_y(P, 0.14, hatch[1], [x], 2.30, 2.45, w=0.11)
            joists_y(P, hatch[3], yi, [x], 2.30, 2.45, w=0.11)
        else:
            joists_y(P, -yi, -0.14, [x], 2.30, 2.45, w=0.11)
            joists_y(P, 0.14, yi, [x], 2.30, 2.45, w=0.11)
    P.box(hatch[0] - 0.06, hatch[1] - 0.1, 2.30, hatch[2] + 0.06, hatch[1], 2.45, "Wood_dark", scale=1.0)
    P.box(hatch[0] - 0.06, hatch[3], 2.30, hatch[2] + 0.06, hatch[3] + 0.1, 2.45, "Wood_dark", scale=1.0)
    # hatch lid, propped open against the loft side
    P.box(hatch[2] + 0.02, hatch[1], zl, hatch[2] + 0.07, hatch[3], zl + 0.9, "Wood_grey", scale=1.0)
    # loft: rafters, purlins, ridge, collar ties; chimney breast; hay
    for s in (-1, 1):
        for x in [rx0 + 0.3 + 0.6 * k for k in range(int((rx1 - rx0 - 0.4) / 0.6) + 1)]:
            y_a, y_b = s * yi, s * 0.06
            za, zb = zc(yi) - 0.02, zc(0.0) - 0.02
            prof_r = [(y_a, za), (y_b, zb), (y_b, zb - 0.13), (y_a, za - 0.13)]
            if s > 0:
                prof_r = list(reversed(prof_r))
            P.bm(bm_prism(prof_r, x - 0.04, x + 0.04), "Wood_dark", scale=1.0)
        for f in (0.35, 0.7):
            y = s * yi * (1 - f)
            z = zc(y)
            P.box(rx0, y - 0.08, z - 0.3, rx1, y + 0.08, z - 0.1, "Wood_dark", scale=1.0)
    P.box(rx0, -0.09, zc(0) - 0.32, rx1, 0.09, zc(0) - 0.02, "Wood_dark", scale=1.0)               # ridge beam
    for x in (-5.0, -2.6, -0.3):                                                                    # trusses
        zt = zc(1.1)
        P.box(x - 0.07, -1.1, zt - 0.2, x + 0.07, 1.1, zt, "Wood_dark", scale=1.0)
        P.box(x - 0.07, -0.08, zt, x + 0.07, 0.08, zc(0) - 0.32, "Wood_dark", scale=1.0)
    P.box(rx0, -0.6, zl, rx0 + 0.62, 0.6, zc(0.6) + 0.1, "Plaster", scale=0.5)                       # chimney breast
    cols.append(("ChimneyBreast", (rx0, -0.6, zl, rx0 + 0.62, 0.6, zc(0.6))))
    fu.hay_pile(P.sub(place(-4.0, 0.6, zl, 10)), L=3.0, W=2.2, H=1.0)
    fu.hay_pile(P.sub(place(-2.0, -1.2, zl, -25)), L=1.6, W=1.2, H=0.6)
    # ---- ground floor
    fu.fireplace(P.sub(place(rx0 + 0.36, 0.0, FZ, 90)), Wf=1.9, Dp=0.72, Hj=1.4, hood_top=2.45 - FZ)
    fu.lit_clos(P.sub(place(-3.0, yi - 0.41, FZ, 0)))
    fu.table(P.sub(place(-3.0, 0.72, FZ, 0)), L=2.6, W=0.8, mat="Wood_oak")
    fu.bench(P.sub(place(-3.0, 0.1, FZ, 0)), L=2.4, mat="Wood_oak")
    fu.dresser(P.sub(place(rx1 - 0.26, -1.55, FZ, -90)), W=1.3, H=2.0)
    fu.longcase_clock(P.sub(place(-1.55, yi - 0.17, FZ, 0)))
    fu.kneading_trough(P.sub(place(-0.55, -yi + 0.3, FZ, 180)))
    fu.churn(P.sub(place(0.55, 2.25, FZ, 0)))
    fu.chair_breton(P.sub(place(-5.1, 1.6, FZ, 120)))
    fu.stool(P.sub(place(-5.2, -1.5, FZ, 0)))
    top_y = fu.ladder(P.sub(place(-0.5, 1.0, FZ, 0)), H=zl - FZ + 0.75, lean=14.0)
    tz = FZ + 0.76
    fu.loaf(P, -3.6, 0.85, tz)
    for x in (-3.9, -3.1, -2.3):
        fu.bowl(P, x, 0.5, tz, r=0.06, h=0.05)
    fu.jug(P, -2.6, 0.95, tz, h=0.24, mat="Faience", rot=10)
    fu.bottle(P, -2.0, 0.9, tz, kind=3)
    mz = FZ + 1.4 + 0.24 + 0.06
    fu.candle(P, rx0 + 0.3, -1.0, mz)
    IF = S["ifaces"]
    damp_patch(P, IF["front"], 1.0, FZ + 0.05, 1.4, 1.0)
    damp_patch(P, IF["back"], -2.3, FZ + 0.3, 1.0, 0.8)
    damp_patch(P, IF["right"], -0.2, FZ + 1.2, 1.2, 1.0)
    damp_patch(P, IF["front"], -2.0, FZ + 1.3, 0.9, 0.7)
    # barrels / crates from the exterior kit
    extra = []
    for i, (x, y, r) in enumerate(((0.6, -0.25, 0.0), (0.62, 0.45, 30.0))):
        objs, tr = env_prop(f"Barrel_{i}", envprops.barrel_wood, place(x, y, FZ, r))
        extra += objs
    objs, tr = env_prop("Crate_0", envprops.crate_wood, place(-1.0, -1.9, zl, 20))
    extra += objs
    # ---- lamps
    lamps = [_lamp_object("Lamp_0", lambda Q: hanging_oil_lamp(Q, drop=2.30 - 1.8), (-3.0, 0.72, 1.8)),
             _lamp_object("Lamp_1", hurricane_lantern, (rx0 + 0.3, 0.75, mz + 0.13))]
    spots = [("LightSpot_0", (-3.0, 0.72, 1.8 + 0.06)), ("LightSpot_1", (rx0 + 0.3, 0.75, mz + 0.13 + 0.03))]
    nav = [("NavFloor_0", [(rx0, -yi, FZ - 0.1, rx1, yi, FZ), (-4.1, -D / 2 + 0.25, FZ - 0.1, -3.1, -yi, FZ)]),
           ("NavFloor_1", holed_boxes((rx0, -yi, 2.45, rx1, yi, zl), hatch))]
    cols.append(("LadderRails", (-0.78, 0.9, FZ, -0.22, 1.1, FZ + 0.25)))
    storeys = [("ground", FZ), ("loft", zl)]
    empties = [("LadderBottom", (-0.5, 0.85, FZ)), ("LadderTop", (-0.5, 1.0 + (zl - FZ) * math.tan(math.radians(14)), zl))]
    probe = dict(shot_in=[((-4.2, -2.1, FZ + 1.6), (-3.0, 1.6, FZ + 0.9)), ((0.3, -2.0, FZ + 1.6), (-5.5, 0.6, FZ + 0.8)),
                          ((-5.3, -1.9, FZ + 1.6), (0.5, 1.2, FZ + 0.9)), ((-0.5, -1.8, zl + 1.6), (-5.0, 0.8, zl + 1.0))],
                 ext=dict(elev=6.0, azim=-15.0, dist_mul=0.55, target=(-3.4, -3.0, 1.6)),
                 hearth=(rx0 + 0.4, 0.0, FZ + 0.3))
    return dict(name="house_longere_int", shell=S, mb=mb, cols=cols, nav=nav, ramps=[], lamps=lamps, spots=spots,
                extra=extra, storeys=storeys, preview=probe, empties=empties, ladder=dict(base=(-0.5, 1.0), top_y=top_y))


# ====================================================================== CAFE
def cafe():
    sp = houses.spec_cafe()
    W, D, He = sp["W"], sp["D"], sp["He"]
    t = T_WALL
    xi, yi = W / 2 - t, D / 2 - t
    ops = sp["openings"]
    ops[3].through = True
    ops[3].h = 2.05
    ops[3].enter = "BackDoor"
    ops[3].door_paint = "Paint_green"
    ops[4].through = True
    ops[4].glow = False
    ztop = 3.0
    extras = sp.pop("extras")
    sp.pop("shopfront")
    sp.update(t=t, floor_z=FZ, cavity=[_box_cav((-xi, -yi, 0.0, xi, yi, ztop))], cavity_aabb=(-xi, -yi, 0.0, xi, yi, ztop),
              ceil_mat="PlasterSoot", wall_mat_in="Plaster", door_paint="Door_oxblood", roof_col="solid",
              shopfront=shell.cafe_shopfront(W, t, "Door_oxblood"), damp_skip_in={"left": [(-1.0, 0.0)]})
    S = shell.build_shell(sp)
    rng = random.Random(7303)
    mb = MB()
    P = Put(mb, rng=rng)
    cols = P.cols
    P.box(-xi, -yi, 0.0, xi, yi, FZ, "Wood_oak", scale=1.0)
    P.box(-2.85, -D / 2 + 0.06, -0.05, 2.85, -yi, FZ, "Wood_oak", scale=1.0)        # floor into the shopfront
    P.box(1.0, yi, -0.05, 2.0, D / 2 - 0.25, FZ, "Flags", scale=0.5)               # back door threshold
    beams_y(P, (-1.5, 0.0, 1.5), -yi - 0.05, yi + 0.05, 2.72, ztop, w=0.22)
    # skirting / dado: brown-painted boarding to 1 m, typical of a café
    IF = S["ifaces"]
    # ---- bar
    fu.bar_counter(P.sub(place(1.91, 0.2, FZ, -90)), L=2.8)
    fu.bottle_shelf(P.sub(place(xi - 0.12, 0.2, FZ, -90)), L=2.4, rng=random.Random(5))
    for i, y in enumerate((-0.9, -0.3, 0.5, 1.2)):
        fu.glass(P, 1.95, y, FZ + 1.06, h=0.1) if i % 2 == 0 else fu.bottle(P, 1.9, y, FZ + 1.06, kind=1 if i == 1 else 0)
    fu.glass(P, 1.85, 0.0, FZ + 1.06, h=0.09)
    fu.jug(P, 2.05, 1.4, FZ + 1.06, h=0.2, mat="Pewter", rot=90)
    for y in (-0.6, 0.5):
        fu.stool(P.sub(place(1.25, y, FZ, 0)))
    # ---- room
    fu.stove(P.sub(place(-xi + 0.45, 0.4, FZ, 90)), flue_to=(0.45, 2.2))
    tables = [(-1.7, -1.6), (-0.3, -0.5), (-1.8, 0.95), (-0.2, 2.1)]
    for i, (x, y) in enumerate(tables):
        fu.bistro_table(P.sub(place(x, y, FZ, 0)))
        fu.bentwood_chair(P.sub(place(x - 0.5, y + 0.1, FZ, -80 + i * 7)))
        fu.bentwood_chair(P.sub(place(x + 0.48, y - 0.15, FZ, 95 - i * 11)))
        fu.glass(P, x + 0.1, y + 0.05, FZ + 0.74, h=0.09)
    fu.bottle(P, -0.4, -0.45, FZ + 0.74, kind=0)
    fu.bottle(P, -1.8, 1.0, FZ + 0.74, kind=2)
    # posters (text-free), a blank menu slate, coat hooks
    fu.poster(P.sub(place(-xi + 0.003, -1.5, 0, 90)), 0, FZ + 1.35, 0.55, 0.82, "Poster_a", y=0.0)
    fu.poster(P.sub(place(0.35, yi - 0.003, 0, 0)), 0, FZ + 1.3, 0.5, 0.75, "Poster_b", y=0.0, rot=2)
    Pq = P.sub(place(-1.0, yi, 0, 0))
    Pq.box(-0.4, -0.03, FZ + 1.2, 0.4, 0.0, FZ + 1.75, "Wood_dark")
    Pq.box(-0.36, -0.035, FZ + 1.24, 0.36, -0.03, FZ + 1.71, "BlackPaint")
    Pl = P.sub(place(-xi, 1.9, 0, 90))
    Pl.box(-0.6, -0.03, FZ + 1.6, 0.6, 0.0, FZ + 1.7, "Wood_dark")
    for x in (-0.45, -0.15, 0.15, 0.45):
        Pl.bm(tube([(x, -0.03, FZ + 1.65), (x, -0.09, FZ + 1.66), (x, -0.1, FZ + 1.7)], 0.006, 4), "Iron", scale=2.0)
    # wainscot (lambris) on the side walls
    for nm in ("left", "back"):
        F = IF[nm]
        half = F.length / 2
        if nm == "back":
            spans = [(-half, -2.0), (-1.1, 0.95)]      # skip back door (int a = -x) and window
        else:
            spans = [(-half, half)]
        for (a0, a1) in spans:
            mb.add_bm(F.box(a0, a1, 0.0, 0.02, FZ, FZ + 1.0), "Wood_dark", scale=1.0)
            mb.add_bm(F.box(a0, a1, 0.0, 0.04, FZ + 0.97, FZ + 1.02), "Wood_dark", scale=1.0)
    damp_patch(P, IF["back"], 1.9, FZ + 1.05, 0.9, 0.8)
    damp_patch(P, IF["left"], 2.0, FZ + 1.4, 1.0, 0.9)
    # ---- lamps
    lamps = [_lamp_object("Lamp_0", lambda Q: cafe_pendant(Q, drop=ztop - 2.25), (-1.0, -0.4, 2.25)),
             _lamp_object("Lamp_1", lambda Q: cafe_pendant(Q, drop=ztop - 2.3), (2.0, 0.3, 2.3))]
    spots = [("LightSpot_0", (-1.0, -0.4, 2.25)), ("LightSpot_1", (2.0, 0.3, 2.3))]
    nav = [("NavFloor_0", [(-xi, -yi, FZ - 0.1, xi, yi, FZ), (-2.85, -D / 2 + 0.06, FZ - 0.1, 2.85, -yi, FZ),
                           (1.0, yi, FZ - 0.1, 2.0, D / 2 - 0.25, FZ)])]
    cols.append(("Ceiling_0", (-xi, -yi, ztop, xi, yi, ztop + 0.1)))
    # sign (tabac lozenge) from the exterior kit
    smb = MB()
    extras(smb, W, D, random.Random(sp["seed"] + 1))
    sign = smb.build("house_cafe_int_sign")
    storeys = [("ground", FZ)]
    probe = dict(shot_in=[((-2.3, -2.4, FZ + 1.6), (1.8, 1.0, FZ + 1.0)), ((0.9, 2.4, FZ + 1.6), (-1.2, -2.0, FZ + 0.9)),
                          ((-2.2, 2.3, FZ + 1.6), (2.0, -0.8, FZ + 1.1))],
                 ext=dict(elev=5.0, azim=-12.0, dist_mul=0.55, target=(0.6, -3.2, 1.8)), hearth=None)
    return dict(name="house_cafe_int", shell=S, mb=mb, cols=cols, nav=nav, ramps=[], lamps=lamps, spots=spots,
                extra=[sign], extra_tris=smb.tri_count(), storeys=storeys, preview=probe)


HOUSES = {"house_bourg_int": bourg, "house_longere_int": longere, "house_cafe_int": cafe}
