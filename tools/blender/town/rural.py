"""Countryside pieces: watermill (granite mill with an undershot wheel on the east side) and
soe_container (CLE Mk I parachute supply container, half-buried, lid ajar)."""
import math
import random

import bmesh
from mathutils import Matrix, Vector

import geo
from geo import MB, bm_box, bm_box_minmax, bm_cyl
from parts import Face, Opening, roff, text
from common import Cols, WFace, cyl_between, lathe, mb_merge, mb_transform, tube
import block

PI = math.pi


# =================================================================== watermill
def watermill():
    """~10 x 7 m: rubble mill house 7.6 x 7 m (x -5..2.6), stone-lined race along its east wall (x 2.6..5)
    with a timber undershot wheel (3.6 m) on an iron-bound shaft entering the wall; sluice gate upstream."""
    rng = random.Random(1820)
    W, D, He = 7.6, 7.0, 5.0
    XC = -1.2
    o = []
    o.append(Opening("front", -1.2, 0.0, 1.1, 2.1, kind="door", paint="Paint_oxblood", leaves=1))
    o.append(Opening("front", 1.6, 0.9, 0.8, 1.0, shutters="closed", paint="Paint_oxblood"))
    o.append(Opening("front", -2.6, 2.9, 0.75, 0.95, shutters="open", paint="Paint_oxblood"))
    o.append(Opening("front", 1.3, 2.9, 0.75, 0.95, shutters="none", rows=2))
    o.append(Opening("back", 0.0, 0.0, 1.6, 2.0, kind="byre", paint="Wood_grey", leaves=2))
    o.append(Opening("back", -2.4, 3.0, 0.7, 0.9, shutters="closed", paint="Paint_oxblood"))
    o.append(Opening("left", 0.0, 5.75, 0.9, 1.2, kind="hay", paint="Wood_grey"))        # sack-hoist door in the west gable
    o.append(Opening("left", -1.5, 1.0, 0.7, 0.9, shutters="none", rows=2, glow=True))
    o.append(Opening("right", -1.6, 2.8, 0.6, 0.8, shutters="none", rows=2))
    mb = MB()
    spec = dict(W=W, D=D, He=He, pitch=48.0, wall="Rubble", seed=1820, openings=o, dormers=[], chimneys=[1], cornice=False,
                mb=mb, quoins=True)
    B = block.build_block(spec)
    cols_b = B["cols"]
    cols_b.box("Body", -W / 2, -D / 2, -0.3, W / 2, D / 2, He)
    block.step_cols(cols_b, B["faces"], B["ops"])
    # sack hoist beam with pulley at the west gable
    Rf = B["R"]
    zt = He + 0.12 + 7.2 * 0
    zhb = 7.35
    mb.add_bm(bm_box_minmax(-W / 2 - 1.1, -0.1, zhb - 0.1, -W / 2 + 0.3, 0.1, zhb + 0.1), "Wood_dark", scale=1.0)
    mb.add_bm(cyl_between(Vector((-W / 2 - 0.95, -0.05, zhb - 0.22)), Vector((-W / 2 - 0.95, 0.05, zhb - 0.22)), 0.1, 10), "Wood_oak", scale=1.0)
    mb.add_bm(tube([(-W / 2 - 0.95, 0.0, zhb - 0.3), (-W / 2 - 0.95, 0.0, 3.2)], 0.012, 4), "Rope", scale=2.0)
    mb.add_bm(bm_box_minmax(-W / 2 - 1.02, -0.06, 3.0, -W / 2 - 0.88, 0.06, 3.2), "Iron", scale=2.0)
    mb_transform(mb, Matrix.Translation((XC, 0, 0)))
    col_objs = cols_b.build()
    for c in col_objs:
        c.data.transform(Matrix.Translation((XC, 0, 0)))
    # ---- race and wheel (world coordinates)
    wm = MB()
    cols = Cols()
    xw = XC + W / 2                       # east wall face (x = 2.6)
    x_out = 5.0
    zf = -1.35
    L = 9.0
    # race floor and the outer retaining wall (granite coping), inner face lined against the mill
    wm.add_bm(bm_box_minmax(xw, -L / 2, zf - 0.3, x_out - 0.45, L / 2, zf), "Rubble", off=roff(rng))
    wm.add_bm(bm_box_minmax(x_out - 0.45, -L / 2, zf - 0.3, x_out, L / 2, 0.15), "Rubble", off=roff(rng))
    wm.add_bm(bm_box_minmax(x_out - 0.5, -L / 2, 0.15, x_out + 0.05, L / 2, 0.32, bevel=0.015), "Granite", off=roff(rng))
    for yy in (-L / 2, L / 2):           # inner lining beyond the building
        y0, y1 = sorted((yy, yy - math.copysign(L / 2 - D / 2, yy)))
        wm.add_bm(bm_box_minmax(xw - 0.4, y0, zf, xw, y1, 0.15), "Rubble", off=roff(rng))
        wm.add_bm(bm_box_minmax(xw - 0.45, y0, 0.15, xw + 0.05, y1, 0.32, bevel=0.015), "Granite", off=roff(rng))
    wm.add_bm(bm_box_minmax(xw - 0.01, -D / 2, zf, xw + 0.06, D / 2, 0.0), "GraniteWet", off=roff(rng))
    # weed / wet band on the race walls
    wm.add_bm(geo.bm_quad((x_out - 0.451, L / 2, zf), (x_out - 0.451, -L / 2, zf), (x_out - 0.451, -L / 2, zf + 0.7),
                          (x_out - 0.451, L / 2, zf + 0.7)), "Weed")
    cols.box("RaceWall", x_out - 0.5, -L / 2, zf - 0.3, x_out + 0.05, L / 2, 0.32)
    cols.box("RaceFloor", xw, -L / 2, zf - 0.3, x_out - 0.45, L / 2, zf)
    # wheel
    Rw = 1.8
    ax = Vector((0, 0.3, zf + Rw + 0.12))
    x0, x1 = xw + 0.35, x_out - 0.65
    for xr in (x0, x1):
        for k in range(16):           # rim of 16 felloe segments
            a0 = 2 * PI * k / 16
            a1 = 2 * PI * (k + 1) / 16
            for (rr, th) in ((Rw - 0.02, 0.12),):
                p0 = Vector((xr, ax.y + rr * math.cos(a0), ax.z + rr * math.sin(a0)))
                p1 = Vector((xr, ax.y + rr * math.cos(a1), ax.z + rr * math.sin(a1)))
                c = (p0 + p1) / 2
                ln = (p1 - p0).length + 0.02
                bm = bm_box(0, 0, 0, 0.09, ln, 0.18)
                ang = math.atan2(p1.z - p0.z, p1.y - p0.y)
                wm.add_bm(bm, "Wood_dark", scale=1.0, matrix=Matrix.Translation(c) @ Matrix.Rotation(ang, 4, "X"), off=roff(rng))
        for k in range(8):            # spokes
            a = 2 * PI * k / 8 + PI / 16
            p = Vector((xr, ax.y + (Rw - 0.1) * math.cos(a), ax.z + (Rw - 0.1) * math.sin(a)))
            wm.add_bm(cyl_between(Vector((xr, ax.y, ax.z)), p, 0.06, 4), "Wood_dark", scale=1.0)
    for k in range(24):               # paddles (floats)
        a = 2 * PI * k / 24
        c = Vector(((x0 + x1) / 2, ax.y + (Rw + 0.05) * math.cos(a), ax.z + (Rw + 0.05) * math.sin(a)))
        bm = bm_box(0, 0, 0, x1 - x0 + 0.16, 0.035, 0.42)
        wm.add_bm(bm, "Wood_grey", scale=1.0, matrix=Matrix.Translation(c) @ Matrix.Rotation(a - PI / 2, 4, "X"), off=roff(rng))
        wm.add_bm(cyl_between(Vector((x0, ax.y + (Rw - 0.12) * math.cos(a), ax.z + (Rw - 0.12) * math.sin(a))),
                              Vector((x1, ax.y + (Rw - 0.12) * math.cos(a), ax.z + (Rw - 0.12) * math.sin(a))), 0.025, 4), "Wood_dark", scale=1.0)
    wm.add_bm(cyl_between(Vector((xw - 0.1, ax.y, ax.z)), Vector((x_out - 0.3, ax.y, ax.z)), 0.13, 12), "Wood_oak", scale=1.0)
    for xr in (x0, x1, xw + 0.05, x_out - 0.35):
        wm.add_bm(cyl_between(Vector((xr - 0.04, ax.y, ax.z)), Vector((xr + 0.04, ax.y, ax.z)), 0.16, 12), "Iron", scale=2.0)
    for xr in (x0, x1):
        wm.add_bm(cyl_between(Vector((xr - 0.12, ax.y, ax.z)), Vector((xr + 0.12, ax.y, ax.z)), 0.3, 8), "Wood_dark", scale=1.0)
    # bearing block on a pier rising from the outer race wall
    wm.add_bm(bm_box_minmax(x_out - 0.5, ax.y - 0.35, 0.32, x_out + 0.05, ax.y + 0.35, ax.z - 0.15, bevel=0.015), "Granite", off=roff(rng))
    wm.add_bm(bm_box_minmax(x_out - 0.45, ax.y - 0.2, ax.z - 0.15, x_out - 0.15, ax.y + 0.2, ax.z - 0.08), "Iron", scale=2.0)
    cols.hull("Wheel", [Vector((x, ax.y + (Rw + 0.3) * math.cos(a), ax.z + (Rw + 0.3) * math.sin(a))) for x in (x0 - 0.1, x1 + 0.1)
                        for a in [2 * PI * k / 12 for k in range(12)]])
    cols.box("Pier", x_out - 0.5, ax.y - 0.35, 0.32, x_out + 0.05, ax.y + 0.35, ax.z)
    # sluice gate upstream (north end): two grooved posts, a planked gate raised on a rack, a walk plank
    ys = -L / 2 + 0.6
    for xp in (xw - 0.1, x_out - 0.35):
        wm.add_bm(bm_box_minmax(xp - 0.12, ys - 0.12, zf, xp + 0.12, ys + 0.12, 1.9), "Wood_dark", scale=1.0)
    wm.add_bm(bm_box_minmax(xw - 0.2, ys - 0.15, 1.9, x_out - 0.25, ys + 0.15, 2.1), "Wood_dark", scale=1.0)
    for k in range(5):
        wm.add_bm(bm_box_minmax(xw + 0.02, ys - 0.04, zf + 0.55 + k * 0.24, x_out - 0.47, ys + 0.04, zf + 0.77 + k * 0.24), "Wood_grey", scale=1.0,
                  off=roff(rng))
    wm.add_bm(bm_box_minmax((xw + x_out) / 2 - 0.05, ys - 0.05, zf + 1.7, (xw + x_out) / 2 + 0.05, ys + 0.05, 2.6), "Iron", scale=2.0)
    wm.add_bm(bm_box_minmax(xw - 0.3, ys + 0.18, 0.3, x_out + 0.05, ys + 0.5, 0.36), "Wood_grey", scale=1.0)
    cols.box("Sluice", xw - 0.3, ys - 0.15, zf, x_out + 0.05, ys + 0.5, 2.1)
    mb_merge(mb, wm)
    ob = mb.build("Watermill")
    pv = [dict(elev=14.0, azim=40.0, dist_mul=0.75, ground="grass_winter"), dict(suffix="_front", elev=8.0, azim=-30.0, dist_mul=0.75,
                                                                            ground="grass_winter")]
    return dict(visual=[ob], cols=col_objs + cols.build(), tris=mb.tri_count(), pv=pv,
                note="race floor z=-1.35 along x 2.6..4.55; terrain must be cut there")


# ============================================================== SOE container
def _half_shell(a0, a1, r, t, x0, x1, n=16, ends=True):
    """Half (or partial) cylinder shell about the X axis between angles a0..a1 (phi: y=r cos, z=r sin)."""
    bm = bmesh.new()
    ring = lambda rr, x: [bm.verts.new((x, rr * math.cos(a0 + (a1 - a0) * i / n), rr * math.sin(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
    oa, ob_ = ring(r, x0), ring(r, x1)
    ia, ib = ring(r - t, x0), ring(r - t, x1)
    for i in range(n):
        bm.faces.new((oa[i], ob_[i], ob_[i + 1], oa[i + 1]))
        bm.faces.new((ia[i + 1], ib[i + 1], ib[i], ia[i]))
        bm.faces.new((oa[i + 1], ia[i + 1], ia[i], oa[i]))
        bm.faces.new((ob_[i], ib[i], ib[i + 1], ob_[i + 1]))
    for (o, i_) in ((oa, ia), (ob_, ib)):
        pass
    for k in (0, n):                 # the long edges
        bm.faces.new((oa[k], ia[k], ib[k], ob_[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def soe_container():
    """CLE Mk I container (1.7 m, khaki): lower half shell with four carrying handles, upper half (lid) hinged
    along one side and lifted ajar, crushable buffer dome at the nose, parachute compartment at the tail with
    torn canopy; three canvas-wrapped cells inside. Half-buried in a scar of thrown-up earth. Empty: Contents."""
    rng = random.Random(1943)
    mb = MB()
    r, t = 0.19, 0.012
    x0, x1 = -0.6, 0.62
    P = "Metal_olive"
    mb.add_bm(_half_shell(PI, 2 * PI, r, t, x0, x1, 16), P, scale=2.0, smooth=True, smooth_angle=40)
    # end bulkheads of the body
    for x in (x0, x1):
        mb.add_bm(cyl_between(Vector((x - 0.006, 0, 0)), Vector((x + 0.006, 0, 0)), r - t, 20), P, scale=2.0)
    # lid hinged along y = +r, z = 0, lifted 32 degrees
    lid = MB()
    lid.add_bm(_half_shell(0.0, PI, r + 0.004, t, x0 + 0.01, x1 - 0.01, 16), P, scale=2.0, smooth=True, smooth_angle=40)
    for x in (-0.35, 0.05, 0.45):          # latch straps on the free edge
        lid.add_bm(bm_box_minmax(x - 0.025, -r - 0.012, -0.03, x + 0.025, -r + 0.004, 0.04), "Iron", scale=2.0)
    th = math.radians(55)
    Mlid = Matrix.Translation((0, r, 0)) @ Matrix.Rotation(-th, 4, "X") @ Matrix.Translation((0, -r, 0))
    mb_merge(mb, lid, Mlid)
    for x in (-0.45, 0.0, 0.45):           # hinge knuckles
        mb.add_bm(cyl_between(Vector((x - 0.04, r + 0.008, 0)), Vector((x + 0.04, r + 0.008, 0)), 0.012, 8), "Iron", scale=2.0)
    # crushable buffer dome (nose) and the parachute compartment (tail)
    nose = lathe([(r, 0.0), (r, 0.04), (r * 0.9, 0.11), (r * 0.62, 0.17), (0.0, 0.2)], segs=20)
    for v in nose.verts:                   # dented on impact
        if v.co.z > 0.1:
            v.co.z -= 0.03 * max(0.0, math.cos(math.atan2(v.co.y, v.co.x) - 0.6))
    mb.add_bm(nose, P, scale=2.0, smooth=True, matrix=Matrix.Translation((x1, 0, 0)) @ Matrix.Rotation(PI / 2, 4, "Y"))
    tail = lathe([(r, 0.0), (r, 0.26), (r - 0.02, 0.28), (0.0, 0.28)], segs=20)
    mb.add_bm(tail, P, scale=2.0, smooth=True, matrix=Matrix.Translation((x0, 0, 0)) @ Matrix.Rotation(-PI / 2, 4, "Y"))
    for x in (x0 - 0.02, x0 - 0.26):
        mb.add_bm(cyl_between(Vector((x - 0.012, 0, 0)), Vector((x + 0.012, 0, 0)), r + 0.006, 20), "Iron", scale=2.0)
    # torn parachute spilling from the tail, shroud lines
    for k in range(3):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=1.0)
        for v in bm.verts:
            c = v.co
            v.co = Vector((c.x * 0.32, c.y * 0.22, max(c.z, -0.2) * 0.07 + 0.02 * math.sin(c.x * 9 + k)))
        mb.add_bm(bm, "Canvas", scale=2.0, smooth=True, matrix=Matrix.Translation((x0 - 0.5 - k * 0.28, 0.12 * (k - 1), -0.02)))
    for k in range(5):
        a = k * 0.5 - 1.0
        mb.add_bm(tube([Vector((x0 - 0.28, 0.1 * math.sin(a), 0.1 * math.cos(a))), Vector((x0 - 0.5, 0.15 * math.sin(a), 0.04)),
                        Vector((x0 - 0.75, 0.25 * math.sin(a), 0.0))], 0.003, 3), "Rope", scale=2.0)
    # carrying handles (two each side, on the lower half)
    for s in (-1, 1):
        for x in (-0.38, 0.38):
            pts = [Vector((x - 0.07, s * (r - 0.005), -0.05)), Vector((x - 0.06, s * (r + 0.05), -0.07)),
                   Vector((x + 0.06, s * (r + 0.05), -0.07)), Vector((x + 0.07, s * (r - 0.005), -0.05))]
            mb.add_bm(tube(pts, 0.008, 5), "Iron", scale=2.0)
    # stencilled panel marks (paint), and the three wrapped cells inside
    for x in (-0.3, 0.3):
        mb.add_bm(bm_box_minmax(x - 0.08, -r - 0.002, -0.1, x + 0.08, -r + 0.004, -0.06), "SignWhite", scale=2.0)
    for k, x in enumerate((-0.4, 0.0, 0.4)):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=2, use_grid_fill=True)
        for v in bm.verts:
            c = v.co * 2
            v.co = c.lerp(c.normalized() * 0.95, 0.4) * 0.5
        bmesh.ops.scale(bm, vec=(0.36, 0.3, 0.24), verts=bm.verts)
        mb.add_bm(bm, "Canvas", scale=2.0, smooth=True, matrix=Matrix.Translation((x, 0.0, -0.035)) @ Matrix.Rotation(0.05 * (k - 1), 4, "X"))
        mb.add_bm(tube([Vector((x - 0.05, -0.155, -0.08)), Vector((x - 0.05, -0.15, 0.09)), Vector((x - 0.05, 0.15, 0.09)),
                        Vector((x - 0.05, 0.155, -0.08))], 0.006, 4), "Rope", scale=2.0)
    # place: yawed, nose-down, sunk so the axis sits just above ground (half buried)
    M = Matrix.Translation((0, 0, 0.03)) @ Matrix.Rotation(math.radians(18), 4, "Z") @ Matrix.Rotation(math.radians(7), 4, "Y")
    mb_transform(mb, M)
    # thrown-up earth: a heightfield scar, rim of spoil round the container and a furrow behind it
    em = bmesh.new()
    Minv = M.inverted()
    nx, ny, st = 30, 16, 0.12

    def hgt(wx, wy):
        p = Minv @ Vector((wx, wy, 0.0))
        e = math.hypot(p.x / 1.05, p.y / 0.42)
        rim = 0.13 * math.exp(-((e - 1.05) / 0.28) ** 2)
        furrow = 0.06 * math.exp(-(p.y / 0.3) ** 2) * (1.0 if -2.4 < p.x < -0.9 else 0.0) * (1 - (abs(p.x + 1.65) / 0.75))
        n = 0.02 * math.sin(wx * 9.0 + wy * 4.0) * math.sin(wy * 7.0 - wx * 3.0)
        return rim + max(furrow, 0.0) + n * (rim > 0.02) - (0.06 if e < 0.9 else 0.0)

    V = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            wx, wy = -1.9 + i * st * 1.05, -1.0 + j * st
            V[i, j] = em.verts.new((wx, wy, hgt(wx, wy) - 0.015))
    for i in range(nx):
        for j in range(ny):
            q = [V[i, j], V[i + 1, j], V[i + 1, j + 1], V[i, j + 1]]
            if max(v.co.z for v in q) < 0.0:
                continue
            em.faces.new(q)
    loose = [v for v in em.verts if not v.link_faces]
    bmesh.ops.delete(em, geom=loose, context="VERTS")
    mb.add_bm(em, "Mud", uv=lambda co, n: (co.x * 0.5, co.y * 0.5), smooth=True, smooth_angle=70)
    ob = mb.build("SoeContainer")
    contents = geo.empty("Contents", M @ Vector((0.0, 0.0, 0.02)))
    contents.rotation_euler = M.to_euler()
    cols = Cols()
    pts = [M @ Vector((x, r * math.cos(a), r * math.sin(a))) for x in (x0 - 0.3, x1 + 0.2) for a in [PI * k / 6 for k in range(7)]]
    pts += [M @ Vector((x, 0, 0)) for x in (x0 - 0.3, x1 + 0.2)]
    cols.hull("Container", [p if p.z > 0 else Vector((p.x, p.y, 0.0)) for p in pts])
    pv = [dict(elev=28.0, azim=-35.0, dist_mul=1.0, ground="grass_winter"), dict(suffix="_side", elev=14.0, azim=60.0, dist_mul=0.9,
                                                                                ground="grass_winter")]
    return dict(visual=[ob], cols=cols.build(), empties=[contents], tris=mb.tri_count(), pv=pv,
                note=f"Contents at {tuple(round(v, 3) for v in contents.location)}")
