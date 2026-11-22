"""Hôtel de la Plage, enterable: the Kriegsmarine signals post inside the seafront hotel (February 1944).

Same exterior, origin, orientation and front as hotel_de_la_plage.glb (hotel.build), so the game can swap one
for the other. Differences you can see from outside: the ground- and first-floor windows are real openings
(dark panes, blackout curtains behind them) and no longer glow; the quay-side service door is 0.2 m wider
(1.2 m) so the doorway clears 1.0 m; the coal-chute throat is a real shaft.

Blender coordinates below are BEFORE the final XC shift (block centred on x = 0); Godot local = (x + XC, z, -y).

Levels (Blender z = Godot y):
  ground floor 0.16, ground ceiling 3.85 | first floor 4.20, first ceiling 7.10 | coal store (cellar) -2.00.
  Second floor and attic stay solid.
Ground floor: entrance hall + reception + dog-leg stair (x -4.4..4.4, y -6.4..1.4); guard room/salon front west;
  mess front east; rear corridor (x 4.4..10.9, y -0.4..1.4) joining hall, mess, coal store and kitchen; kitchen
  rear west with the back door onto the quay; pantry behind the salon; coal store rear east, sunk to -2.0, reached
  from the yard by the CoalChute hatch (2.1 m drop down a shaft, under the wall, onto the coal) and left by a
  stone stair up to a door into the corridor.
First floor: landing over the stair, corridor; signals room front east; Brenner's office and bedroom front west;
  dormitory, washroom/WC and store at the rear.
Doors: DoorNode_<Room> meshes (origin on the hinge, +90 deg about Blender Z / Godot +Y swings them into the room),
  each with a DoorNode_<Room>_col-colonly child; the front door keeps its name "Door". Door_<Room> empties mark
  every hinge."""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

import geo
from geo import MB, bm_box_minmax, bm_prism, boolean, union
from parts import (Face, Roof, body_profile, cutter, dormer_geom, dormer_roof, door, gable_coping, gable_profile,
                   main_roof, quoins, roff, shutters, string_course, surround, window)
import houses
import block
import hotel as H
from common import Cols, WFace, door_node, pivot_object, sandbag_run
from shell import IMB, plank_door_leaf, through_cutter
from ihelp import Put, place, lathe, tube, cyl_x, cyl_y, multi_box_obj
import furniture as fu
import hotel_furn as hf
from hotel_furn import T, Rx, Ry, Rz

W, D, He = H.W, H.D, H.He
XC = H.XC
TW = 0.6                       # outer wall thickness
XI, YI = W / 2 - TW, D / 2 - TW
G0, C0 = 0.16, 3.85            # ground floor / ground ceiling
F1, C1 = 4.20, 7.10            # first floor / first ceiling
CS = -2.0                      # coal store floor
PW = 0.2                       # partition thickness
CH_Y0, CH_Y1 = 2.56, 3.44      # coal chute shaft / passage (y)
EPS = 0.006
DOOR_H = 2.15                  # room door clear height
ALL_EXT = ("Wood_dark", "Paint_green", "Iron", "Interior")

# stair: 23 risers 0.1757, going 0.28, dog-leg against the hall/mess partition
NR = 23
RISE = (F1 - G0) / NR
GO = 0.28
SA_X = (3.3, 4.4)              # flight A (rises toward the front, -y)
SB_X = (2.12, 3.3)             # flight B (rises back toward the corridor, +y)
SA_Y0 = -2.12                  # first riser of flight A
LAND_Y = SA_Y0 - 11 * GO       # -5.2: half landing y[-6.4, -5.2]
Z_LAND = G0 + 12 * RISE
SB_TOP = LAND_Y + 10 * GO      # -2.4: flight B arrives on the first floor
HOLE = (2.0, -YI, 4.4, SB_TOP)  # stair hole in the first floor slab
# coal store stair: 12 risers of 0.18 from the corridor landing down to the cellar floor
CR = (G0 - CS) / 12
CG = 0.27
CL_X = (4.6, 5.9)              # top landing x
CL_Y = (1.6, 2.6)              # stair width / landing depth (y)
CS_FOOT = CL_X[1] + 11 * CG    # 8.87


def _openings():
    ops = H._openings()
    for op in ops:
        op.through = False
        op.enter = None
        if op.kind == "window" and op.z0 < 7.0 and op.face in ("front", "back", "left", "right"):
            if not (op.face == "front" and op.z0 < 1.0 and op.a == 3.0):     # behind the stair landing: stays blind
                op.through = True
                op.glow = False
        if op.face == "back" and op.kind == "door":
            op.w = 1.2
            op.enter = "DoorNode_Kitchen"
    return ops


# ======================================================================== exterior shell + cavity
def _inb(c, bb, e=EPS):
    return bb[0] - e <= c.x <= bb[3] + e and bb[1] - e <= c.y <= bb[4] + e and bb[2] - e <= c.z <= bb[5] + e


def _shell(mb, rng_in):
    """block._build_block with real openings, the two storeys hollowed out, a sunk coal store and its chute
    passage. Keeps the exterior rng sequence so shutters, stones and decals match hotel_de_la_plage."""
    dormers = [dict(a=a, wd=1.9, zd=1.75, z0=0.05, w=1.0, h=1.3, glow=(a == 3.0)) for a in (-9.0, -3.0, 3.0, 9.0)]
    Ff = Face("front", W, D)
    vest = Ff.box(-0.68, 0.68, -1.6, 0.3, -0.3, 2.97)
    spec = dict(W=W, D=D, He=He, pitch=40.0, wall="RenderPale", seed=1944, openings=_openings(), dormers=dormers,
                chimneys=[-1, 1], ridge_chimneys=[-4.5, 4.5], cornice=True, bands=[(3.92, 0.18), (7.2, 0.12)],
                lower=(4.0, "Ashlar"), damp_skip={"front": [(-1.6, 1.6)]})
    with block.single_seg_bevels():
        rng = random.Random(spec["seed"])
        R = Roof(W, D, He, spec["pitch"])
        faces = {k: Face(k, W, D) for k in ("front", "back", "left", "right")}
        ops = list(spec["openings"])
        dms = []
        for d in dormers:
            dm = dormer_geom(R, d["a"], d["wd"], He + d["zd"])
            dm.update(d)
            dms.append(dm)
            from parts import Opening
            op = Opening("front", d["a"], He + d["z0"], d["w"], d["h"], kind="window", shutters="none",
                         glow=d.get("glow", False), rows=2, paint="Wood_grey", frame="Paint_cream")
            op.through, op.enter = False, None
            ops.append(op)
        tg = R.tg
        bodies = [bm_prism(body_profile(R), -W / 2, W / 2), bm_prism(gable_profile(R), -W / 2, -W / 2 + tg),
                  bm_prism(gable_profile(R), W / 2 - tg, W / 2)]
        for dm in dms:
            bodies += dm["bodies"]
        bodies.append(bm_box_minmax(4.3, 1.3, CS - 0.35, W / 2 + 0.05, D / 2 + 0.05, -0.2))     # coal store foundation
        body = union(bodies)
        cutters = [through_cutter(faces[op.face], op, TW) if op.through or op.enter else cutter(faces[op.face], op)
                   for op in ops]
        body = boolean(body, cutters)
        body = boolean(body, [vest])
        zones = dict(
            ground=(-XI, -YI, G0, XI, YI, C0),
            first=(-XI, -YI, F1, XI, YI, C1),
            hole=(HOLE[0], HOLE[1], C0 - 0.05, HOLE[2], HOLE[3], F1 + 0.05),
            coal=(4.6, 1.6, CS, XI, YI, G0 + 0.05),
            passage=(XI - 0.05, CH_Y0, CS, W / 2 + 0.12, CH_Y1, -0.12))
        cav = union([bm_box_minmax(*bb) for bb in zones.values()])
        body = boolean(body, [cav])

        def key(f):
            c, n = f.calc_center_median(), f.normal
            if _inb(c, zones["coal"]) or _inb(c, zones["passage"]):
                return "Flags" if n.z > 0.5 else ("PlasterSoot" if n.z < -0.5 else "Rubble")
            if _inb(c, zones["hole"]):
                return "Plaster"
            if _inb(c, zones["ground"]):
                return "Flags" if n.z > 0.5 else "Plaster"
            if _inb(c, zones["first"]):
                return "Wood_oak" if n.z > 0.5 else "Plaster"
            return "EXT"

        from ihelp import split_by
        parts_ = split_by(body, key)
        ext = parts_.pop("EXT")
        for bm, mat in block.split_mat_by_z(ext, 4.0, "Ashlar", spec["wall"]):
            if bm is not None:
                mb.add_bm(bm, mat, off=roff(rng))
        for mat, bm in parts_.items():
            mb.add_bm(bm, mat, off=roff(rng_in), scale=0.5 if mat != "Wood_oak" else 0.6)
        quoins(mb, W, D, He, rng)
        string_course(mb, W, D, He + 0.02, rng)
        for (z, h) in spec["bands"]:
            block.band(mb, W, D, z, h, rng)
        doors = []
        for op in ops:
            F = faces[op.face]
            lh = 0.3 if (op.w < 1.2 or op.enter) else 0.36
            surround(mb, F, op, rng, lintel_h=lh)
            if op.kind == "window":
                if op.through:
                    with mb.dropping("Interior"):
                        window(mb, F, op)
                    _reveal(mb, F, op, rng_in)
                else:
                    window(mb, F, op)
                shutters(mb, F, op, rng)
            elif op.kind in ("door", "byre"):
                if op.enter:
                    with mb.dropping(*ALL_EXT):
                        door(mb, F, op, rng)                     # consumes the same rng as the solid version
                    doors.append(_back_door(mb, F, op, rng_in))
                else:
                    door(mb, F, op, rng)
        main_roof(mb, R, rng, dormers=[dict(a0=dm["a0"], a1=dm["a1"], z_top=dm["z_top"]) for dm in dms])
        for dm in dms:
            dormer_roof(mb, R, dm, rng)
        gable_coping(mb, R, rng)
        cols = Cols()
        from parts import chimney
        for sx in spec["chimneys"]:
            cols.box("Chimney", *chimney(mb, R, sx, rng))
        for x in spec["ridge_chimneys"]:
            cols.box("Chimney", *block.ridge_chimney(mb, R, x, rng))
        houses._damp(mb, faces, W, D, ops, rng, extra_skip=spec["damp_skip"])
        for F in faces.values():
            houses._streaks(mb, F, ops, rng)
        prof = [(-D / 2 - R.ov, R.z_eave - 0.05), (D / 2 + R.ov, R.z_eave - 0.05), (0.0, R.Hr + R.rise)]
        cols.prism("Roof", prof, -W / 2, W / 2)
        for dm in dms:
            cols.box("Dormer", dm["a0"] + 0.1, -D / 2 - 0.05, He - 0.4, dm["a1"] - 0.1, -D / 2 + dm["depth"], dm["z_top"])
    return dict(R=R, faces=faces, ops=ops, cols=cols, doors=doors)


def _reveal(mb, F, op, rng):
    """Plastered inner reveals and an oak sill board behind a real window (as shell._reveal_lining)."""
    m = 0.025
    a0, a1, z0, z1 = op.a0 - m, op.a1 + m, op.z0 - m, op.z0 + op.h + m
    d0, d1 = -TW - 0.005, -0.31
    lt = 0.012
    mb.add_bm(F.box(a0, a0 + lt, d0, d1, z0, z1), "Plaster", off=roff(rng))
    mb.add_bm(F.box(a1 - lt, a1, d0, d1, z0, z1), "Plaster", off=roff(rng))
    mb.add_bm(F.box(a0, a1, d0, d1, z1 - lt, z1), "Plaster", off=roff(rng))
    floor = G0 if op.z0 < 4.0 else F1
    if op.z0 - floor > 0.3:
        mb.add_bm(F.box(a0 - 0.05, a1 + 0.05, d0 - 0.035, d1, z0, z0 + 0.035), "Furn_oak", scale=1.0, off=roff(rng))
    else:
        mb.add_bm(F.box(a0, a1, d0, d1, z0, z0 + 0.012), "Furn_oak", scale=1.0, off=roff(rng))


def _back_door(mb, F, op, rng):
    """Kitchen back door onto the quay: frame near the outside face as on the solid hotel, threshold through the
    wall, plastered reveal inside, the planked leaf as its own node."""
    a0, a1 = op.a0, op.a1
    z1 = op.z0 + op.h
    dd = -0.17
    for bm in (F.box(a0, a0 + 0.07, dd - 0.05, dd + 0.04, 0.12, z1), F.box(a1 - 0.07, a1, dd - 0.05, dd + 0.04, 0.12, z1),
               F.box(a0, a1, dd - 0.05, dd + 0.04, z1 - 0.07, z1)):
        mb.add_bm(bm, "Wood_dark", scale=1.0)
    mb.add_bm(F.box(a0 - 0.03, a1 + 0.03, -TW - 0.27, -0.25, -0.3, G0), "Granite", off=roff(rng))       # threshold
    m = 0.025
    for (b0, b1) in ((a0 - m, a0 - m + 0.012), (a1 + m - 0.012, a1 + m)):
        mb.add_bm(F.box(b0, b1, -TW - 0.005, dd - 0.05, G0, z1 + m), "Plaster", off=roff(rng))
    mb.add_bm(F.box(a0 - m, a1 + m, -TW - 0.005, dd - 0.05, z1 - 0.012 + m, z1 + m), "Plaster", off=roff(rng))
    la0, la1 = a0 + 0.075, a1 - 0.075
    d_in, d_out = dd - 0.04, dd + 0.01
    dmb = MB()
    plank_door_leaf(dmb, F, la0, la1, d_in, d_out, G0 + 0.01, z1 - 0.075, op.paint, rng)
    hinge = F.p(la0, d_in, G0 + 0.01)
    p0, p1 = F.p(la0, d_in - 0.005, 0), F.p(la1, d_out + 0.005, 0)
    bb = (min(p0.x, p1.x), min(p0.y, p1.y), G0 + 0.01, max(p0.x, p1.x), max(p0.y, p1.y), z1 - 0.075)
    tris = dmb.tri_count()
    objs = pivot_object(op.enter, dmb, hinge, [bb])
    gx = sorted((F.p(a0 + 0.07, 0, 0).x, F.p(a1 - 0.07, 0, 0).x))
    return dict(name=op.enter, objs=objs, tris=tris, hinge=hinge, gap_x=gx, top=z1 - 0.07)


# ======================================================================== interior builder
class Interior:
    """Partitions, skirting, door frames, doors, collision for the interior (Blender coords, pre-shift)."""

    def __init__(self, mb, cols, rng):
        self.mb, self.cols, self.rng = mb, cols, rng
        self.doors = []
        self.tris = 0

    def box(self, bb, mat, scale=0.5, **kw):
        x0, y0, z0, x1, y1, z1 = bb
        self.mb.add_bm(bm_box_minmax(min(x0, x1), min(y0, y1), min(z0, z1), max(x0, x1), max(y0, y1), max(z0, z1)), mat,
                       scale=scale, off=roff(self.rng), **kw)

    @staticmethod
    def _bb(axis, c, wt, s0, s1, z0, z1):
        if axis == "x":
            return (s0, c - wt / 2, z0, s1, c + wt / 2, z1)
        return (c - wt / 2, s0, z0, c + wt / 2, s1, z1)

    def wall(self, name, axis, c, s0, s1, z0, z1, gaps=(), wt=PW, mat="Plaster", skirt=(True, True), skirt_z=None):
        """Partition along `axis` ('x' = runs along x at y=c) from s0 to s1, floor z0 to ceiling z1.
        gaps: (g0, g1, height). Builds boxes, lintels, cream architraves on both faces, skirting, collision."""
        sz = z0 if skirt_z is None else skirt_z
        pos = s0
        segs = []
        for (g0, g1, gh) in sorted(gaps):
            segs.append((pos, g0))
            self.box(self._bb(axis, c, wt, g0, g1, z0 + gh, z1), mat)
            self.cols.box(f"{name}_lintel", *self._bb(axis, c, wt, g0, g1, z0 + gh, z1))
            for side in (-1, 1):
                dlo = c + side * wt / 2
                dhi = dlo + side * 0.025
                for (j0, j1) in ((g0 - 0.08, g0), (g1, g1 + 0.08)):
                    self._face_box(axis, dlo, dhi, j0, j1, z0, z0 + gh + 0.08, "Paint_cream")
                self._face_box(axis, dlo, dhi, g0 - 0.08, g1 + 0.08, z0 + gh, z0 + gh + 0.08, "Paint_cream")
            pos = g1
        segs.append((pos, s1))
        for k, (a, b) in enumerate(segs):
            if b - a < 0.01:
                continue
            self.box(self._bb(axis, c, wt, a, b, z0, z1), mat)
            self.cols.box(name, *self._bb(axis, c, wt, a, b, z0, z1))
            ia = a + (0.08 if k > 0 else 0.0)
            ib = b - (0.08 if k < len(segs) - 1 else 0.0)
            for side, on in zip((-1, 1), skirt):
                if on and ib - ia > 0.05:
                    dlo = c + side * wt / 2
                    self._face_box(axis, dlo, dlo + side * 0.02, ia, ib, sz, sz + 0.17, "Furn_chestnut")

    def _face_box(self, axis, d0, d1, s0, s1, z0, z1, mat):
        lo, hi = min(d0, d1), max(d0, d1)
        bb = (s0, lo, z0, s1, hi, z1) if axis == "x" else (lo, s0, z0, hi, s1, z1)
        self.box(bb, mat, scale=1.0)

    def skirting(self, axis, c, side, s0, s1, z, skip=()):
        """Skirting along an outer wall's inner face (c = face coordinate, side = +1/-1 toward the room)."""
        spans = [(s0, s1)]
        for (k0, k1) in skip:
            new = []
            for (x, y) in spans:
                if k1 <= x or k0 >= y:
                    new.append((x, y))
                else:
                    if k0 > x:
                        new.append((x, k0))
                    if k1 < y:
                        new.append((k1, y))
            spans = new
        for (a, b) in spans:
            if b - a > 0.05:
                self._face_box(axis, c, c + side * 0.02, a, b, z, z + 0.17, "Furn_chestnut")

    def door(self, room, axis, c, g0, g1, z0, room_sign, paint="Paint_cream"):
        """Room door in a partition: hinge on the room-side face so +90 deg about Z swings it into the room."""
        if axis == "x":
            n = Vector((0, -room_sign, 0))
            o = (0.0, c - room_sign * PW / 2, 0.0)
        else:
            n = Vector((-room_sign, 0, 0))
            o = (c - room_sign * PW / 2, 0.0, 0.0)
        F = WFace(o, n)
        to_a = lambda s: (Vector((s, 0, 0)) if axis == "x" else Vector((0, s, 0))).dot(F.t) - Vector(o).dot(F.t)
        aa = sorted((to_a(g0), to_a(g1)))
        la0, la1 = aa[0] + 0.01, aa[1] - 0.01
        d_in, d_out = -PW, -PW + 0.045
        zb, zt = z0 + 0.008, z0 + DOOR_H - 0.02
        dmb = MB()
        panel_leaf(dmb, F, la0, la1, d_in, d_out, zb, zt, paint, self.rng)
        hinge = F.p(la0, d_in, zb)
        p0, p1 = F.p(la0, d_in - 0.004, 0), F.p(la1, d_out + 0.004, 0)
        bb = (min(p0.x, p1.x), min(p0.y, p1.y), zb, max(p0.x, p1.x), max(p0.y, p1.y), zt)
        name = f"DoorNode_{room}"
        self.tris += dmb.tri_count()
        objs = pivot_object(name, dmb, hinge, [bb])
        self.doors.append(dict(name=name, room=room, objs=objs, hinge=hinge, axis=axis, gap=(g0, g1), z0=z0,
                               into=(-n).to_tuple(), clear=(g1 - g0) - 0.01 - 0.045))
        return objs


def panel_leaf(dmb, F, la0, la1, d_in, d_out, z0, z1, paint, rng):
    """Interior four-panel door leaf, mouldings on both faces, brass knobs at 1.0 m above z0."""
    dmb.add_bm(F.box(la0, la1, d_in, d_out, z0, z1), paint, scale=1.0, off=roff(rng))
    lw, h = la1 - la0, z1 - z0
    st = 0.1
    for (d, s) in ((d_in, -1), (d_out, 1)):
        dd = d + s * 0.012
        for (p0, p1, q0, q1) in ((la0 + st + 0.03, la0 + lw / 2 - 0.04, z0 + 0.15, z0 + h * 0.42),
                                 (la0 + lw / 2 + 0.04, la1 - st - 0.03, z0 + 0.15, z0 + h * 0.42),
                                 (la0 + st + 0.03, la0 + lw / 2 - 0.04, z0 + h * 0.5, z1 - 0.12),
                                 (la0 + lw / 2 + 0.04, la1 - st - 0.03, z0 + h * 0.5, z1 - 0.12)):
            dmb.add_bm(F.box(p0, p1, min(d, dd), max(d, dd), q0, q1, bevel=0.006, segs=1), paint, scale=1.0)
        ka = la1 - 0.065
        kd = d + s * 0.05
        dmb.add_bm(F.box(ka - 0.022, ka + 0.022, min(d, d + s * 0.006), max(d, d + s * 0.006), z0 + 0.92, z0 + 1.1),
                   "Brass", scale=2.0)
        p = F.p(ka, kd, z0 + 1.0)
        q = F.p(ka, d, z0 + 1.0)
        dmb.add_bm(tube([q, p], 0.008, 6), "Brass", scale=2.0)
        dmb.add_bm(geo.bm_box(p.x, p.y, p.z, 0.04, 0.04, 0.04, bevel=0.015, segs=1), "Brass", scale=2.0)


# ======================================================================== curtains, stairs, cellar
def _curtains(mb, F, op, rng, board=False):
    """Blackout curtains on a rod across a real window (inside face), closed with a small gap; or a painted
    blackout board in the coal store."""
    a0, a1 = op.a0 - 0.12, op.a1 + 0.12
    z1 = op.z0 + op.h + 0.14
    floor = G0 if op.z0 < 4.0 else F1
    if board:
        mb.add_bm(F.box(op.a0 - 0.05, op.a1 + 0.05, -TW - 0.03, -TW - 0.005, op.z0 - 0.05, op.z0 + op.h + 0.05), "BlackPaint")
        return
    low = op.z0 - floor < 0.3
    zb = floor + 0.03 if low else op.z0 - 0.12
    d_rod = -TW - 0.07
    mb.add_bm(tube([F.p(a0 - 0.05, d_rod, z1), F.p(a1 + 0.05, d_rod, z1)], 0.012, 6), "Brass", scale=2.0)
    for a in (a0 - 0.06, a1 + 0.06):
        mb.add_bm(lathe([(0.0, 0.0), (0.02, 0.01), (0.022, 0.03), (0.0, 0.045)], segs=8), "Brass", scale=2.0,
                  matrix=Matrix.Translation(F.p(a, d_rod, z1)) @ Matrix.Rotation(math.pi / 2, 4, "Y" if abs(F.t.x) > 0.5 else "X"))
    mid = (a0 + a1) / 2 + rng.uniform(-0.05, 0.05)
    gap = rng.uniform(0.0, 0.03)
    for (pa, pb) in ((a0, mid - gap / 2), (mid + gap / 2, a1)):
        bm = bmesh.new()
        n = max(4, int((pb - pa) / 0.055))
        ph = rng.uniform(0, 6.28)
        top, bot = [], []
        for k in range(n + 1):
            a = pa + (pb - pa) * k / n
            d = -TW - 0.045 - 0.028 * (0.5 + 0.5 * math.sin(k * math.pi + ph * 0.1))
            db = d - 0.01 * math.sin(k * 0.7 + ph)
            top.append(bm.verts.new(F.p(a, d, z1 - 0.01)))
            bot.append(bm.verts.new(F.p(a + 0.01 * math.sin(k + ph), db, zb)))
        for k in range(n):
            bm.faces.new((bot[k], bot[k + 1], top[k + 1], top[k]))
        bm.normal_update()
        if sum((f.normal.dot(F.n) for f in bm.faces)) > 0:
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
        mb.add_bm(bm, "Blackout", scale=1.0, off=roff(rng))


def _stairs(I, P):
    """Dog-leg hall stair (solid under, oak treads), closed strings with oak balustrades, balustrades round the
    first-floor hole; collision ramps solid to the floor (32 deg) so a capsule walks straight up."""
    mb, cols = I.mb, I.cols
    # flight A: risers 1..11 treads, 12th onto the landing
    for i in range(1, 12):
        z = G0 + i * RISE
        y1 = SA_Y0 - (i - 1) * GO
        y0 = SA_Y0 - i * GO
        I.box((SA_X[0], y0, G0, SA_X[1], y1, z - 0.03), "Plaster")
        I.box((SA_X[0], y0 - 0.02, z - 0.03, SA_X[1], y1 + 0.025, z), "Wood_oak", scale=1.0)
    I.box((SB_X[0], -YI, G0, SA_X[1], LAND_Y, Z_LAND - 0.03), "Plaster")
    I.box((SB_X[0], -YI, Z_LAND - 0.03, SA_X[1], LAND_Y + 0.025, Z_LAND), "Wood_oak", scale=1.0)
    # flight B: risers 13..22 treads, 23rd onto the first floor
    for j in range(13, 23):
        z = G0 + j * RISE
        y0 = LAND_Y + (j - 13) * GO
        y1 = LAND_Y + (j - 12) * GO - (0.005 if j == 22 else 0.0)
        I.box((SB_X[0], y0, G0, SB_X[1], y1, z - 0.03), "Plaster")
        I.box((SB_X[0], y0 - 0.025, z - 0.03, SB_X[1], y1 + 0.02, z), "Wood_oak", scale=1.0)
    # strings and balustrades: west of flight B and the landing (x 2.0..2.12), east of flight B over flight A
    hpar = 0.95
    st = 0.1                                    # closed string above the tread line
    profW = [(-YI, G0), (SB_TOP, G0), (SB_TOP, F1 + st), (LAND_Y, Z_LAND + st), (-YI, Z_LAND + st)]
    mb.add_bm(bm_prism(profW, 2.0, SB_X[0]), "Plaster", off=roff(I.rng))
    capW = [(-YI, Z_LAND + st), (LAND_Y, Z_LAND + st), (SB_TOP, F1 + st), (SB_TOP, F1 + st + 0.03),
            (LAND_Y, Z_LAND + st + 0.03), (-YI, Z_LAND + st + 0.03)]
    mb.add_bm(bm_prism(capW, 1.98, SB_X[0] + 0.02), "Furn_oak", scale=1.0)
    profE = [(LAND_Y, Z_LAND), (SB_TOP, F1), (SB_TOP, F1 + st), (LAND_Y, Z_LAND + st)]
    mb.add_bm(bm_prism(profE, 3.18, SA_X[0]), "Plaster", off=roff(I.rng))
    xw, xe = (2.0 + SB_X[0]) / 2, (3.18 + SA_X[0]) / 2
    _balustrade(I, (xw, -YI + 0.05), (xw, LAND_Y), Z_LAND + st + 0.03, Z_LAND + st + 0.03, hpar - st)
    _balustrade(I, (xw, LAND_Y), (xw, SB_TOP), Z_LAND + st + 0.03, F1 + st + 0.03, hpar - st, newel_end=True)
    _balustrade(I, (xe, LAND_Y + 0.1), (xe, SB_TOP), Z_LAND + st, F1 + st, hpar - st, newel_end=True)
    # wall-mounted handrail on the partition for flight A
    za0, za1 = G0 + 0.9, Z_LAND + 0.9
    mb.add_bm(tube([(SA_X[1] - 0.06, SA_Y0 + 0.1, za0), (SA_X[1] - 0.06, LAND_Y, za1)], 0.024, 8), "Furn_oak", scale=1.0)
    for y in (SA_Y0 - 0.3, (SA_Y0 + LAND_Y) / 2, LAND_Y + 0.3):
        z = za0 + (SA_Y0 - y) / (SA_Y0 - LAND_Y) * (za1 - za0)
        mb.add_bm(tube([(SA_X[1], y, z - 0.05), (SA_X[1] - 0.06, y, z - 0.03)], 0.008, 5), "Brass", scale=2.0)
    # first floor balustrades round the hole (on the slab edge) and over flight A
    _balustrade(I, (1.94, -YI + 0.05), (1.94, SB_TOP), F1, F1, hpar, base=True)
    _balustrade(I, (SA_X[0] - 0.1, SB_TOP + 0.06), (SA_X[1] - 0.05, SB_TOP + 0.06), F1, F1, hpar, base=True)
    # newel post at the foot of flight A
    I.box((SA_X[0] - 0.05, SA_Y0 - 0.05, G0, SA_X[0] + 0.05, SA_Y0 + 0.05, G0 + 1.05), "Furn_oak", scale=1.0)
    # collision: ramps solid to the floor, the landing, parapets
    cols.prism("StairsA", [(SA_Y0, G0), (LAND_Y, Z_LAND), (LAND_Y, G0)], *SA_X)
    cols.prism("StairsB", [(LAND_Y, G0), (SB_TOP, G0), (SB_TOP, F1), (LAND_Y, Z_LAND)], SB_X[0], SB_X[1])
    cols.box("StairLanding", SB_X[0], -YI, G0, SA_X[1], LAND_Y, Z_LAND)
    cols.prism("StairParapetW", [(LAND_Y, G0), (SB_TOP, G0), (SB_TOP, F1 + 1.0), (LAND_Y, Z_LAND + 1.0)], 2.0, SB_X[0])
    cols.box("StairParapetWL", 2.0, -YI, G0, SB_X[0], LAND_Y, Z_LAND + 1.0)
    cols.prism("StairParapetE", [(LAND_Y, Z_LAND), (SB_TOP, F1), (SB_TOP, F1 + 1.0), (LAND_Y, Z_LAND + 1.0)], 3.18, SA_X[0])
    cols.box("HoleParapet", 1.88, -YI, F1, 2.0, SB_TOP, F1 + 1.0)
    cols.box("HoleParapet2", SA_X[0] - 0.12, SB_TOP, F1, SA_X[1], SB_TOP + 0.12, F1 + 1.0)
    cols.box("StairNewel", SA_X[0] - 0.05, SA_Y0 - 0.05, G0, SA_X[0] + 0.05, SA_Y0 + 0.05, G0 + 1.05)


def _balustrade(I, a, b, za, zb, h, step=0.14, base=False, newel_end=False):
    """Square oak balusters between a base line (za..zb, may slope) and a moulded handrail h above it."""
    a, b = Vector(a), Vector(b)
    L = (b - a).length
    n = max(1, int(L / step))
    for k in range(n + 1):
        p = a.lerp(b, k / n)
        z = za + (zb - za) * k / n
        w = 0.07 if (k == 0 or (newel_end and k == n)) else 0.032
        top = z + h + (0.08 if w > 0.05 else 0.0)
        I.box((p.x - w / 2, p.y - w / 2, z, p.x + w / 2, p.y + w / 2, top), "Furn_oak", scale=1.0)
    I.mb.add_bm(tube([(a.x, a.y, za + h), (b.x, b.y, zb + h)], 0.03, 6), "Furn_oak", scale=1.0)
    if base:
        I.mb.add_bm(tube([(a.x, a.y, za + 0.05), (b.x, b.y, zb + 0.05)], 0.035, 4), "Furn_oak", scale=1.0)


def _coal_store(I, P, rng):
    """Cellar stair and landing from the corridor door, iron railing, coal heaps, the chute shaft outside the east
    wall (curb and hatch are the exterior's), collision for the pit, the passage and the shaft."""
    mb, cols = I.mb, I.cols
    # landing at corridor level, stone steps down to the east
    I.box((CL_X[0], CL_Y[0], CS, CL_X[1], CL_Y[1], G0 - 0.04), "Rubble")
    I.box((CL_X[0], CL_Y[0], G0 - 0.04, CL_X[1] + 0.02, CL_Y[1] + 0.02, G0), "Granite")
    for k in range(1, 12):
        z = G0 - k * CR
        x0 = CL_X[1] + (k - 1) * CG
        I.box((x0, CL_Y[0], CS, x0 + CG, CL_Y[1], z - 0.04), "Rubble")
        I.box((x0 - 0.02, CL_Y[0], z - 0.04, x0 + CG, CL_Y[1] + 0.02, z), "Granite")
    # iron railing along the open edge (y = 2.64): posts, top rail following the pitch, mid rail
    yr = CL_Y[1] + 0.04
    def ztread(x):
        if x <= CL_X[1]:
            return G0
        return G0 - (x - CL_X[1]) / CG * CR
    xs = [CL_X[0] + 0.1, CL_X[1]] + [CL_X[1] + k * CG * 2 + CG / 2 for k in range(1, 5)]
    for x in xs:
        z = ztread(x)
        mb.add_bm(tube([(x, yr, z), (x, yr, z + 0.95)], 0.014, 6), "Iron", scale=2.0)
    xe = CL_X[1] + 9 * CG
    for dz in (0.95, 0.5):
        pts = [(CL_X[0] + 0.1, yr, G0 + dz), (CL_X[1], yr, G0 + dz), (xe, yr, ztread(xe) + dz)]
        mb.add_bm(tube(pts, 0.016 if dz > 0.9 else 0.01, 6), "Iron", scale=2.0)
    # coal: a big heap in the rear corner, a smaller one under the passage, some in the shaft bottom
    hf.coal_heap(P.sub(T(9.6, 5.3, CS)), 1.5, 1.2, 1.0, rng, 0.3)
    hf.coal_heap(P.sub(T(10.1, 3.0, CS)), 0.55, 0.5, 0.3, rng, 1.7, segs=(14, 7))
    hf.coal_heap(P.sub(T(11.9, 3.0, CS)), 0.42, 0.38, 0.22, rng, 2.9, segs=(12, 6))
    mb.add_bm(bm_box_minmax(XI, CH_Y0, CS, W / 2 + 0.85, CH_Y1, CS + 0.01), "Coal", scale=1.0)
    # the shaft outside the wall: three walls and a floor of rubble below the granite curb
    xo = 12.30
    I.box((W / 2, CH_Y0 - 0.12, CS - 0.2, xo + 0.15, CH_Y1 + 0.12, CS), "Rubble")
    I.box((xo, CH_Y0 - 0.12, CS, xo + 0.15, CH_Y1 + 0.12, -0.15), "Rubble")
    I.box((W / 2, CH_Y0 - 0.12, CS, xo, CH_Y0, -0.15), "Rubble")
    I.box((W / 2, CH_Y1, CS, xo, CH_Y1 + 0.12, -0.15), "Rubble")
    # an iron chute plate set into the passage floor (what the coal slides down)
    # collision -------------------------------------------------------------------
    cols.box("CoalLanding", CL_X[0], CL_Y[0], CS, CL_X[1], CL_Y[1], G0)
    pts = []
    for (x, z) in ((CL_X[1], G0), (CS_FOOT, CS)):
        for y in CL_Y:
            pts += [(x, y, z), (x, y, CS)]
    cols.hull("CoalStairs", pts)
    rail = []
    for (x, z) in ((CL_X[0], G0), (CL_X[1], G0), (xe, ztread(xe))):
        for y in (yr - 0.03, yr + 0.03):
            rail += [(x, y, z), (x, y, z + 1.0)]
    cols.hull("CoalRail", rail[:8])
    cols.hull("CoalRail2", rail[4:])
    cols.hull("CoalPile", [(8.2, 4.2, CS), (10.9, 4.2, CS), (10.9, YI, CS), (8.2, YI, CS), (9.9, 5.4, CS + 0.75),
                           (10.6, 5.8, CS + 0.75)])
    cols.hull("CoalHeapIn", [(9.55, 2.5, CS), (10.75, 2.5, CS), (10.75, 3.5, CS), (9.55, 3.5, CS), (10.15, 3.0, CS + 0.22)])


def _collision(cols):
    """Outer walls, floors, ceiling, coal pit and chute shaft (doors and partitions add their own)."""
    vx = 0.68
    cols.box("WallFront", -W / 2, -D / 2, -0.3, -vx, -YI, He)
    cols.box("WallFront", vx, -D / 2, -0.3, W / 2, -YI, He)
    cols.box("WallFrontLintel", -vx, -D / 2, 2.42, vx, -YI, He)
    bx = 0.53
    cols.box("WallBack", -W / 2, YI, -0.3, -bx, D / 2, He)
    cols.box("WallBack", bx, YI, -0.3, W / 2, D / 2, He)
    cols.box("WallBackLintel", -bx, YI, 2.06, bx, D / 2, He)          # timber head 2.03..2.10
    cols.box("WallWest", -W / 2, -YI, -0.3, -XI, YI, He)
    cols.box("WallEast", XI, -YI, -0.3, W / 2, CH_Y0, He)
    cols.box("WallEast", XI, CH_Y1, -0.3, W / 2, YI, He)
    cols.box("WallEastChute", XI, CH_Y0, -0.12, W / 2, CH_Y1, He)
    cols.box("Upper", -W / 2, -D / 2, C1, W / 2, D / 2, He)
    # coal pit
    cols.box("CoalPitW", 4.3, 1.6, CS - 0.3, 4.6, YI, G0)
    cols.box("CoalPitN", 4.6, 1.3, CS - 0.3, XI, 1.6, G0)
    cols.box("CoalPitS", 4.6, YI, CS - 0.3, XI, D / 2, -0.1)
    cols.box("CoalPitE", XI, 1.6, CS - 0.3, W / 2, CH_Y0, -0.1)
    cols.box("CoalPitE", XI, CH_Y1, CS - 0.3, W / 2, YI, -0.1)
    xo = 12.30
    # shaft walls stop under the granite curb (which, as on the solid hotel, has no collision of its own)
    cols.box("ChuteShaftOut", xo, CH_Y0 - 0.2, CS - 0.3, xo + 0.2, CH_Y1 + 0.2, -0.15)
    cols.box("ChuteShaftS", XI, CH_Y0 - 0.2, CS - 0.3, xo + 0.2, CH_Y0, -0.15)
    cols.box("ChuteShaftN", XI, CH_Y1, CS - 0.3, xo + 0.2, CH_Y1 + 0.2, -0.15)
    navs = []
    from rooms import holed_boxes
    navs.append(("NavFloor_0", holed_boxes((-W / 2 + 0.01, -D / 2 + 0.01, -0.1, W / 2 - 0.01, D / 2 - 0.01, G0),
                                          (4.6, 1.6, XI, YI))))
    navs.append(("NavFloor_1", holed_boxes((-XI, -YI, C0, XI, YI, F1), (HOLE[0], HOLE[1], HOLE[2], HOLE[3]))))
    navs.append(("NavFloor_C", [(4.6, 1.6, CS - 0.3, XI, YI, CS), (XI - 0.01, CH_Y0, CS - 0.3, xo, CH_Y1, CS)]))
    return navs


# ======================================================================== furnishing
def _furnish(P, rng):
    lamps = []      # (pos, kind, ceiling)
    mk = {}         # marker name -> (pos, out_dir (dx, dy))

    def lamp(x, y, ceil, drop=0.85, kind="pendant"):
        z = ceil - drop
        if kind == "pendant":
            hf.pendant(P.sub(T(x, y, z)), drop=drop)
        else:
            hf.bare_bulb(P.sub(T(x, y, z)), drop=drop)
        lamps.append((x, y, z - 0.06))

    # ----------------------------------------------------------- hall
    hf.reception_counter(P.sub(place(-2.9, -3.8, G0, 90)), L=2.4, rng=rng)
    hf.key_board(P.sub(place(-4.4, -3.8, G0 + 1.3, 90)), rng=rng)
    hf.wall_clock(P.sub(place(-4.4, -3.8, G0 + 2.55, 90)))
    hf.office_chair(P.sub(place(-3.75, -3.4, G0, -95)))
    hf.notice_board(P.sub(place(1.35, -YI, G0 + 1.25, 180)), rng=rng)
    fu.bench(P.sub(place(1.78, -4.0, G0, -90)), L=1.6, mat="Furn_oak")
    hf.wall_map(P.sub(place(0.6, 1.4, G0 + 1.3, 0)), 1.3, 0.9, uv=(0.0, 0.25, 0.65, 0.75))
    mk["Reception"] = ((-2.2, -3.8, G0), (1, 0))
    mk["Stairs_Bottom"] = ((sum(SA_X) / 2, SA_Y0 + 0.45, G0), (0, -1))
    mk["Stairs_Top"] = ((sum(SB_X) / 2, SB_TOP + 0.45, F1), (0, 1))
    lamp(-1.0, -4.2, C0, 0.9)
    lamp(-0.2, 0.4, C0, 0.9)
    # ----------------------------------------------------------- salon / guard room (front west)
    P.box(-XI, -YI, G0, -4.6, 1.4, G0 + 0.004, "Furn_oak", scale=1.0)
    fu.table(P.sub(place(-7.8, -3.2, G0, 0)), L=1.8, W=0.9, name="SalonTable")
    for (x, y, r) in ((-8.3, -3.95, 180), (-7.3, -3.98, 172), (-8.3, -2.45, 6), (-7.3, -2.42, -4)):
        hf.office_chair(P.sub(place(x, y, G0, r)))
    fu.stove(P.sub(place(-7.5, 0.95, G0, 0)), flue_to=(0.45, 2.1))
    fu.bench(P.sub(place(-10.72, -1.4, G0, 90)), L=1.8, mat="Furn_oak")
    hf.wall_map(P.sub(place(-4.6, -4.6, G0 + 1.2, -90)), 1.2, 0.85, uv=(0.3, 0.0, 1.0, 0.6))
    hf.telephone(P, -7.5, -3.0, G0 + 0.76, rot=30)
    hf.papers(P, -8.1, -3.3, G0 + 0.76, n=3, rng=rng)
    fu.bottle(P, -7.0, -3.4, G0 + 0.76, kind=1)
    fu.glass(P, -7.2, -3.0, G0 + 0.76)
    lamp(-7.8, -3.2, C0, 0.9)
    # ----------------------------------------------------------- mess (front east)
    P.box(4.6, -YI, G0, XI, -0.6, G0 + 0.004, "Furn_oak", scale=1.0)
    fu.table(P.sub(place(7.9, -3.5, G0, 0)), L=4.2, W=1.0, name="MessTable")
    for k in range(5):
        x = 6.1 + k * 0.9
        hf.office_chair(P.sub(place(x + rng.uniform(-0.05, 0.05), -4.27, G0, 180 + rng.uniform(-10, 10))))
        hf.office_chair(P.sub(place(x + rng.uniform(-0.05, 0.05), -2.73, G0, rng.uniform(-10, 10))))
    hf.sideboard(P.sub(place(4.6 + 0.26, -3.5, G0, 90)), L=1.8)
    hf.wall_map(P.sub(place(8.6, -0.6, G0 + 1.35, 0)), 1.5, 1.0)
    hf.wall_clock(P.sub(place(4.6, -1.8, G0 + 2.2, 90)))
    tz = G0 + 0.76
    for k in range(5):
        x = 6.1 + k * 0.9
        fu.bowl(P, x, -3.85, tz, r=0.08, h=0.05, mat="Faience")
        fu.bowl(P, x + 0.05, -3.15, tz, r=0.08, h=0.05, mat="Faience")
        if k % 2 == 0:
            fu.glass(P, x + 0.2, -3.8, tz)
            fu.glass(P, x - 0.2, -3.2, tz)
    fu.loaf(P, 7.3, -3.5, tz)
    fu.jug(P, 8.4, -3.45, tz, h=0.22, mat="EnamelWhite", rot=30)
    fu.bottle(P, 9.1, -3.55, tz, kind=0)
    fu.bottle(P, 6.6, -3.45, tz, kind=3)
    fu.jug(P, 4.95, -3.0, G0 + 0.95, h=0.2, mat="Pewter", rot=80)
    mk["Mess_Table"] = ((7.9, -2.3, G0), (0, 1))
    lamp(6.8, -3.5, C0, 0.95)
    lamp(9.0, -3.5, C0, 0.95)
    # ----------------------------------------------------------- rear corridor
    hf.notice_board(P.sub(place(8.2, 1.4, G0 + 1.25, 0)), rng=rng)
    lamp(7.9, 0.5, C0, 0.6)
    # ----------------------------------------------------------- kitchen (rear west)
    hf.range_stove(P.sub(place(-5.1 + 0.375, 4.6, G0, 90)), L=1.7, D=0.75, flue_h=2.4)
    for k, (y, r) in enumerate(((4.15, 0.13), (4.65, 0.11), (5.1, 0.1))):
        hf.pot(P, -4.7, y, G0 + 0.854, r=r, h=0.14 + 0.03 * k, mat="Copper" if k != 1 else "Iron")
    P.bm(cyl_y(0.012, 3.7, 5.5, segs=6), "Iron", matrix=T(-5.0, 0, G0 + 1.85))
    for k in range(4):
        y = 3.9 + k * 0.45
        P.bm(tube([(-5.0, y, G0 + 1.85), (-5.0, y, G0 + 1.72)], 0.004, 4), "Iron")
        hf.pot(P.sub(T(-5.0, y, G0 + 1.4) @ Ry(90) @ T(0, 0, -0.12)), 0, 0, 0, r=0.1, h=0.09, mat="Copper", handle=False)
    hf.scuttle(P, -4.55, 3.45, G0)
    mk["Kitchen_Stove"] = ((-3.85, 4.6, G0), (1, 0))
    fu.table(P.sub(place(-1.6, 3.9, G0, 0)), L=2.2, W=0.9, name="KitchenTable")
    for (x, y) in ((-2.3, 3.2), (-1.0, 4.65), (-2.0, 4.7)):
        fu.stool(P.sub(place(x, y, G0, 0)))
    tz = G0 + 0.76
    fu.loaf(P, -2.2, 3.8, tz)
    P.box(-1.5, 3.65, tz, -0.95, 4.0, tz + 0.03, "Wood_oak", scale=1.0)                 # chopping board
    fu.bowl(P, -0.8, 4.1, tz, r=0.12, h=0.08, mat="EnamelWhite")
    fu.jug(P, -1.9, 4.15, tz, h=0.2, mat="Faience", rot=200)
    hf.pot(P, -1.25, 4.2, tz, r=0.1, h=0.1, mat="Iron")
    mk["Kitchen_Table"] = ((-1.6, 3.05, G0), (0, -1))
    hf.sink(P.sub(place(-3.0, 6.1, G0, 0)), L=1.2, D=0.6, H=0.8)
    hf.shelves(P.sub(place(4.4 - 0.17, 4.0, G0, -90)), L=3.0, D=0.32, rng=rng, items="kitchen", name="KitchenShelves")
    hf.shelves(P.sub(place(1.5, 6.4 - 0.17, G0, 0)), L=1.3, D=0.32, rng=rng, items="kitchen", name="KitchenShelves2")
    fu.table(P.sub(place(3.0, 5.98, G0, 0)), L=1.4, W=0.7, name="WorkTable", drawer=False)
    fu.churn(P.sub(place(3.9, 2.15, G0, 0)))
    hf.sack(P, 3.5, 2.2, G0, rng, rot=20)
    lamp(-2.2, 4.0, C0, 0.95)
    lamp(2.0, 4.2, C0, 0.95)
    # ----------------------------------------------------------- pantry
    hf.shelves(P.sub(place(-9.4, 6.4 - 0.2, G0, 0)), L=2.3, D=0.4, rng=rng, items="pantry", name="PantryShelves")
    hf.shelves(P.sub(place(-6.1, 6.4 - 0.2, G0, 0)), L=1.3, D=0.4, rng=rng, items="pantry", name="PantryShelves2")
    hf.shelves(P.sub(place(-XI + 0.2, 2.3, G0, 90)), L=0.9, D=0.4, rng=rng, items="pantry", name="PantryShelves3")
    for (x, y, z, r) in ((-9.2, 2.5, G0, 10), (-8.4, 2.3, G0, -20), (-8.8, 2.4, G0 + 0.27, 80), (-9.6, 4.6, G0, 95)):
        hf.sack(P, x, y, z, rng, rot=r)
    hf.crate(P, -6.2, 4.6, G0, rot=8)
    hf.crate(P, -6.2, 4.6, G0 + 0.4, sx=0.5, sy=0.35, sz=0.3, rot=-6, name="Crate")
    hf.crate(P, -6.7, 5.45, G0, sx=0.5, sy=0.5, sz=0.5, rot=30)
    lamp(-8.0, 4.0, C0, 0.6, kind="bulb")
    # ----------------------------------------------------------- coal store
    for (x, y, r) in ((5.3, 4.8, 10), (5.2, 5.6, -15), (5.35, 5.2, 70)):
        hf.sack(P, x, y, CS + (0.28 if r == 70 else 0.0), rng, rot=r)
    hf.shovel(P, 7.3, 6.25, CS, rot=180, lean=-18)
    lamp(7.5, 4.6, C0, C0 - 1.6, kind="bulb")
    mk["CoalStore_Floor"] = ((9.0, 3.45, CS), (0, -1))
    # ----------------------------------------------------------- first floor: landing + corridor
    hf.notice_board(P.sub(place(-1.5, -3.6, F1 + 1.25, 90)), rng=rng)
    fu.bench(P.sub(place(-1.28, -5.2, F1, 90)), L=1.4, mat="Furn_oak")
    lamp(0.25, -3.6, C1, 0.9)
    lamp(-6.5, 0.5, C1, 0.6)
    lamp(7.5, 0.5, C1, 0.6)
    # ----------------------------------------------------------- signals room (front east)
    sx0 = 4.6
    lamp_xy = hf.radio_bench(P.sub(place(8.65, -0.6 - 0.375, F1, 0)), L=3.0, D=0.75, rng=rng)
    hf.transmitter_rack(P.sub(place(10.52, -0.6 - 0.27, F1, 0)), W=0.62, D=0.5, H=1.3)
    hf.blackboard(P.sub(place(6.75, -0.6, F1 + 1.25, 0)), rng=rng)
    for x in (7.6, 9.8):
        hf.office_chair(P.sub(place(x + rng.uniform(-0.05, 0.05), -1.62, F1, 180 + rng.uniform(-12, 12))))
    mk["RadioBench"] = ((9.0, -2.0, F1), (0, -1))
    hf.desk(P.sub(place(7.5, -YI + 0.375, F1, 180)), L=1.4, D=0.75, name="SignalsDesk")
    dz = F1 + 0.76
    hf.typewriter(P.sub(place(7.0, -5.98, dz, 180)))
    hf.cipher_machine(P.sub(place(7.88, -5.98, dz, 180)))
    hf.papers(P, 7.98, -5.78, dz, n=2, rng=rng, rot=-10)
    hf.rotor_box(P, 7.42, -6.2, dz, rot=180)
    P.box(7.43, -5.8, dz, 7.6, -5.72, dz + 0.004, "Paper", scale=2.0)                    # today's key strip
    P.bm(geo.bm_cyl(0.004, 0.004, 0.15, segs=6), "Iron", matrix=T(7.6, -5.85, dz + 0.003) @ Ry(90) @ Rx(-20))
    hf.office_chair(P.sub(place(7.5, -5.42, F1, 0)))
    mk["Desk_Signals"] = ((7.5, -5.08, F1), (0, 1))
    mk["CipherMachine"] = ((7.88, -5.98, dz), (0, 1))
    hf.steel_cabinet(P.sub(place(sx0 + 0.31, -4.0, F1, 90)), W=0.82, D=0.62, H=1.6)
    mk["Cabinet"] = ((sx0 + 0.62, -4.0, F1), (1, 0))
    hf.wall_map(P.sub(place(sx0, -2.0, F1 + 1.15, 90)), 1.7, 1.15)
    hf.wall_map(P.sub(place(XI, -5.3, F1 + 1.2, -90)), 1.15, 0.85, uv=(0.4, 0.2, 1.0, 0.85))
    hf.wall_clock(P.sub(place(8.7, -0.6, F1 + 2.35, 0)))
    hf.filing_cabinet(P.sub(place(sx0 + 0.32, -5.6, F1, 90)), name="SignalsFiles")
    lamp(7.5, -5.2, C1, 0.95)
    lamp(8.7, -1.7, C1, 0.95)
    # ----------------------------------------------------------- Brenner's office
    hf.rug(P.sub(place(-4.5, -3.6, F1 + 0.001, 0)), L=2.6, W=1.8)
    hf.desk(P.sub(place(-4.5, -3.6, F1, 180)), L=1.6, D=0.8, mat="Furn_chestnut", name="BrennerDesk")
    hf.office_chair(P.sub(place(-4.5, -4.38, F1, 180)))
    hf.office_chair(P.sub(place(-4.25, -2.6, F1, 12)))
    bz = F1 + 0.76
    blamp = hf.desk_lamp(P.sub(place(-5.05, -3.7, bz, 0)))
    hf.telephone(P, -3.95, -3.5, bz, rot=160)
    hf.papers(P, -4.4, -3.65, bz, n=4, rng=rng)
    hf.book(P, -4.9, -3.35, bz, rot=12, mat="Furn_black")
    hf.filing_cabinet(P.sub(place(-7.4 + 0.32, -5.0, F1, 90)), name="BrennerFiles")
    hf.bookcase(P.sub(place(-4.5, -YI + 0.19, F1, 180)), W=1.0, rng=rng)
    hf.coat_and_cap(P.sub(place(-1.7, -2.7, F1, -90)))
    hf.wall_map(P.sub(place(-4.5, -0.6, F1 + 1.3, 0)), 1.4, 0.95, uv=(0.15, 0.1, 0.85, 0.7))
    mk["Brenner_Desk"] = ((-4.1, -5.0, F1), (0, -1))
    mk["Brenner_Coat"] = ((-2.45, -2.5, F1), (-1, 0))
    lamp(-4.5, -3.6, C1, 0.85)
    lamps.append((-5.05 + 0.0, -3.7 - 0.13, bz + 0.37))
    # ----------------------------------------------------------- Brenner's bedroom
    fu.bed(P.sub(place(-9.6, -1.63, F1, 0)))
    hf.bedside(P.sub(place(-10.6, -0.85, F1, 0)))
    fu.armoire(P.sub(place(-7.6 - 0.31, -4.9, F1, -90)))
    fu.washstand(P.sub(place(-XI + 0.21, -5.6, F1, 90)))
    hf.office_chair(P.sub(place(-9.1, -5.6, F1, 25)))
    hf.rug(P.sub(place(-8.55, -1.7, F1 + 0.001, 90)), L=1.6, W=0.7)
    fu.candle(P, -10.6, -0.85, F1 + 0.65)
    mk["Brenner_Bed"] = ((-8.52, -1.65, F1), (1, 0))
    lamp(-9.25, -3.6, C1, 0.85)
    # ----------------------------------------------------------- dormitory
    for x in (0.75, 1.75, 4.2, 5.25, 6.3, 8.75, 9.8):
        hf.bunk(P.sub(place(x, YI - 0.99, F1, 0)), rng=rng)
    for k in range(9):
        hf.locker(P.sub(place(2.45 + k * 0.62, 1.6 + 0.26, F1, 180)), name="Locker")
    fu.table(P.sub(place(5.5, 3.2, F1, 0)), L=1.6, W=0.65, name="DormTable", drawer=False)
    for (x, y) in ((4.45, 3.2), (6.55, 3.18)):
        hf.stool_sq(P.sub(place(x, y, F1, rng.uniform(-10, 10))))
    fu.glass(P, 5.3, 3.2, F1 + 0.76)
    hf.papers(P, 5.8, 3.1, F1 + 0.76, n=2, rng=rng)
    mk["Dorm_Bunks"] = ((4.2, 4.08, F1), (0, -1))
    lamp(3.0, 3.8, C1, 0.85)
    lamp(8.0, 3.8, C1, 0.85)
    # ----------------------------------------------------------- washroom / WC
    P.box(-4.4, 1.6, F1, -0.1, YI, F1 + 0.004, "Flags", scale=0.5)
    hf.bathtub(P.sub(place(-4.4 + 0.37, 3.2, F1, 90)))
    hf.wc(P.sub(place(-1.2, YI - 0.42, F1, 0)))
    for y in (4.0, 5.0):
        hf.washbasin(P.sub(place(-0.1 - 0.22, y, F1, -90)))
    lamp(-2.2, 4.0, C1, 0.7)
    # ----------------------------------------------------------- store
    hf.shelves(P.sub(place(-9.4, YI - 0.2, F1, 0)), L=2.3, D=0.4, rng=rng, items="store", name="StoreShelves")
    hf.shelves(P.sub(place(-5.85, YI - 0.2, F1, 0)), L=1.8, D=0.4, rng=rng, items="store", name="StoreShelves2")
    hf.shelves(P.sub(place(-XI + 0.2, 5.1, F1, 90)), L=1.6, D=0.4, rng=rng, items="store", name="StoreShelves3")
    for (x, y, z, r, s) in ((-5.15, 4.3, F1, 90, (0.6, 0.4, 0.4)), (-5.15, 4.3, F1 + 0.4, 84, (0.5, 0.35, 0.3)),
                            (-5.1, 5.0, F1, 92, (0.6, 0.4, 0.4)), (-9.7, 4.3, F1, -12, (0.45, 0.45, 0.45))):
        hf.crate(P, x, y, z, *s, rot=r)
    for (x, y) in ((-7.7, 2.05), (-8.4, 2.05)):
        P.bm(lathe([(0.0, 0.0), (0.3, 0.0), (0.3, 0.05), (0.18, 0.05), (0.18, 0.4), (0.3, 0.4), (0.3, 0.45), (0.0, 0.45)],
                   segs=14), "Wood_grey", matrix=T(x, y, F1))
        P.bm(lathe([(0.19, 0.05), (0.27, 0.06), (0.27, 0.39), (0.19, 0.4)], segs=14, cap_top=False, cap_bottom=False),
             "Bakelite", matrix=T(x, y, F1))
        P.col("CableDrum", x - 0.3, y - 0.3, F1, x + 0.3, y + 0.3, F1 + 0.45)
    lamp(-7.5, 4.0, C1, 0.6, kind="bulb")
    return lamps, mk


# ======================================================================== build
def build():
    hf.install_materials()
    rng = random.Random(1944)          # hotel.build's exterior extras rng
    rng_in = random.Random(19440211)   # everything new inside
    mb = IMB()
    S = _shell(mb, rng_in)
    F = S["faces"]["front"]
    cols = S["cols"]
    ops = S["ops"]
    # exterior extras exactly as hotel.build (balconies, entrance, frieze, marquise, sign, pipes, sandbags, yard)
    for a in H.BAYS:
        if abs(a) < 4:
            continue
        H._balcony(mb, F, a - 0.85, a + 0.85, H.Z1, 0.62, rng, consoles=(a - 0.6, a + 0.6))
    H._balcony(mb, F, -3.9, 3.9, H.Z1, 0.85, rng, consoles=(-3.6, -2.4, -0.6, 0.6, 2.4, 3.6))
    with mb.dropping("Interior"):
        H._entrance(mb, F, rng)
    H._frieze(mb, F, rng)
    H._marquise(mb, F, rng)
    H._sign_board(mb, F, 1.72, 1.45, rng)
    H._downpipes(mb, rng)
    y = -D / 2
    sandbag_run(mb, cols, (-2.0, y - 0.35, 0), (-2.0, y - 2.6, 0), 8, rng, "SandbagsW")
    sandbag_run(mb, cols, (-2.0, y - 2.6, 0), (-0.9, y - 2.6, 0), 8, rng, "SandbagsW2")
    sandbag_run(mb, cols, (2.0, y - 0.35, 0), (2.0, y - 2.6, 0), 8, rng, "SandbagsE")
    sandbag_run(mb, cols, (2.0, y - 2.6, 0), (0.9, y - 2.6, 0), 8, rng, "SandbagsE2")
    H._coal_yard(mb, cols, rng)
    chute_objs, curb, chute_pivot = H._coal_chute(rng)
    with mb.dropping("Void"):
        curb(mb)
    cols.box("Steps", -1.55, -D / 2 - 0.75, -0.2, 1.55, -D / 2, 0.0)
    cols.box("Steps2", -1.25, -D / 2 - 0.4, 0.0, 1.25, -D / 2, 0.16)
    cols.box("Balcony", -3.9, -D / 2 - 0.85, H.Z1 - 0.13, 3.9, -D / 2, H.Z1 + 1.0)
    block.step_cols(cols, S["faces"], [o for o in ops if o.kind != "entry"])

    # ---------------------------------------------------------------- interior
    I = Interior(mb, cols, rng_in)
    navs = _collision(cols)
    # entrance: cream architrave round the vestibule's inner end, flags under it
    for (j0, j1) in ((-0.76, -0.68), (0.68, 0.76)):
        I.box((j0, -YI, G0, j1, -YI + 0.025, 3.05), "Paint_cream", scale=1.0)
    I.box((-0.76, -YI, 2.97, 0.76, -YI + 0.025, 3.05), "Paint_cream", scale=1.0)
    # ground floor partitions
    I.wall("WallMessN", "x", -0.5, 4.6, XI, G0, C0, gaps=[(5.2, 6.2, DOOR_H)])
    I.wall("WallHallMess", "y", 4.5, -YI, -0.4, G0, C0)
    I.wall("WallHallSalon", "y", -4.5, -YI, 1.4, G0, C0, gaps=[(-2.0, -0.6, 2.3)])
    I.wall("WallRear0", "x", 1.5, -XI, XI, G0, C0, gaps=[(-2.6, -1.4, 2.3), (4.75, 5.75, DOOR_H)], skirt=(True, False))
    I.wall("WallKitchenCoal", "y", 4.5, 1.6, YI, G0, C0, skirt=(True, False))
    I.wall("WallPantry", "y", -5.2, 1.6, YI, G0, C0, gaps=[(2.0, 3.1, 2.3)])
    # rear wall's kitchen/pantry face skirting (the coal store side has none)
    I.skirting("x", 1.6, 1, -XI, 4.4, G0, skip=[(-2.68, -1.32)])
    # first floor partitions
    I.wall("WallFront1", "x", -0.5, -XI, -1.5, F1, C1, gaps=[(-2.9, -1.9, DOOR_H)])
    I.wall("WallFront1", "x", -0.5, 4.4, XI, F1, C1, gaps=[(5.2, 6.2, DOOR_H)])
    I.wall("WallLanding", "y", -1.6, -YI, -0.6, F1, C1)
    I.wall("WallBedroom", "y", -7.5, -YI, -0.6, F1, C1, gaps=[(-2.1, -1.1, 2.3)])
    I.wall("WallSignals", "y", 4.5, -YI, -0.6, F1, C1)
    I.wall("WallRear1", "x", 1.5, -XI, XI, F1, C1, gaps=[(-6.4, -5.4, DOOR_H), (-1.4, -0.4, DOOR_H), (0.5, 1.5, DOOR_H)])
    I.wall("WallStoreWC", "y", -4.5, 1.6, YI, F1, C1)
    I.wall("WallWCDorm", "y", 0.0, 1.6, YI, F1, C1)
    # doors (room on the + or - side of the wall)
    I.door("Mess", "x", -0.5, 5.2, 6.2, G0, -1)
    I.door("CoalStore", "x", 1.5, 4.75, 5.75, G0, +1)
    I.door("Signals", "x", -0.5, 5.2, 6.2, F1, -1)
    I.door("Brenner", "x", -0.5, -2.9, -1.9, F1, -1)
    I.door("Dorm", "x", 1.5, 0.5, 1.5, F1, +1)
    I.door("WC", "x", 1.5, -1.4, -0.4, F1, +1)
    I.door("Store", "x", 1.5, -6.4, -5.4, F1, +1)
    # skirting on the outer walls' inner faces
    lowwin = {}
    for op in ops:
        if op.through and op.kind == "window":
            Fo = S["faces"][op.face]
            p0, p1 = Fo.p(op.a0, 0, 0), Fo.p(op.a1, 0, 0)
            axis = "x" if op.face in ("front", "back") else "y"
            s = sorted((p0.x, p1.x)) if axis == "x" else sorted((p0.y, p1.y))
            floor = G0 if op.z0 < 4.0 else F1
            if op.z0 - floor < 0.25:
                lowwin.setdefault((op.face, floor), []).append((s[0] - 0.06, s[1] + 0.06))
    for floor in (G0, F1):
        front_skip = [(-0.78, 0.78)] if floor == G0 else []
        I.skirting("x", -YI, 1, -XI, XI, floor, skip=front_skip + lowwin.get(("front", floor), []) + [(2.0, 4.4)])
        back_skip = [(-0.66, 0.66), (4.6, XI)] if floor == G0 else []
        I.skirting("x", YI, -1, -XI, XI, floor, skip=back_skip + lowwin.get(("back", floor), []))
        I.skirting("y", -XI, 1, -YI, YI, floor, skip=lowwin.get(("left", floor), []))
        I.skirting("y", XI, -1, -YI, YI, floor, skip=([(1.6, YI)] if floor == G0 else []) + lowwin.get(("right", floor), []))
    # curtains / blackout boards on every real window
    for op in ops:
        if op.through and op.kind == "window":
            Fo = S["faces"][op.face]
            board = op.z0 < 4.0 and ((op.face == "back" and op.a == -7.5) or (op.face == "right" and op.a == 4.6))
            _curtains(mb, Fo, op, rng_in, board=board)
    # stairs and coal store
    fmb = MB()
    P = Put(fmb, rng=random.Random(7404))
    _stairs(I, P)
    _coal_store(I, P, rng_in)
    lamps, mk = _furnish(P, random.Random(7405))
    for name, bb in P.cols:
        cols.box(name, *bb)
    # doors: front (unchanged), kitchen back door, room doors
    door_objs, dtris, hinge = door_node("Door", F, -0.59, 0.59, -0.26, -0.2, 0.16, 2.42, "Door_bleu", rng,
                                        kind="panel", glazed_top=True)
    kd = S["doors"][0]
    room_doors = I.doors

    # ---------------------------------------------------------------- objects, shift, empties
    ob = mb.build("HotelDeLaPlage")
    furn = fmb.build("HotelDeLaPlage_furniture")
    tris = mb.tri_count() + fmb.tri_count() + dtris + kd["tris"] + I.tris
    col_objs = cols.build()
    for nm, boxes in navs:
        col_objs.append(multi_box_obj(f"{nm}-colonly", boxes))
    shift = Matrix.Translation((XC, 0, 0))
    for o in [ob, furn] + col_objs:
        o.data.transform(shift)
    movers = [door_objs[0], chute_objs[0], kd["objs"][0]] + [d["objs"][0] for d in room_doors]
    for o in movers:
        o.location.x += XC
    sh = lambda p: (p[0] + XC, p[1], p[2])
    empties = []

    def empty(name, p, out=None):
        e = geo.empty(name, sh(p))
        if out is not None:
            e.rotation_euler = (0.0, 0.0, math.atan2(-out[0], out[1]))
        empties.append(e)
        return e

    empty("Door_Front", tuple(hinge))
    empty("Door_Kitchen", tuple(kd["hinge"]))
    for d in room_doors:
        empty(f"Door_{d['room']}", tuple(d["hinge"]))
    for name, (p, out) in mk.items():
        empty(name, p, out)
    for i, p in enumerate(lamps):
        empty(f"Lamp_{i}", p)
    visual = [ob, furn, door_objs[0], chute_objs[0], kd["objs"][0]] + [d["objs"][0] for d in room_doors]
    cols_all = col_objs + door_objs[1:] + chute_objs[1:] + kd["objs"][1:]
    for d in room_doors:
        cols_all += d["objs"][1:]
    info = dict(doors=[("Door (front)", tuple(hinge), (0, 1, 0), 1.12)] +
                [(kd["name"], tuple(kd["hinge"]), (0, -1, 0), kd["gap_x"][1] - kd["gap_x"][0] - 0.055)] +
                [(d["name"], tuple(d["hinge"]), d["into"], d["clear"]) for d in room_doors],
                lamps=lamps, markers=mk)
    note = (f"door hinges (blender, shifted): " +
            ", ".join(f"{n}={tuple(round(v, 3) for v in sh(h))} clear={c:.2f}" for n, h, _, c in info["doors"]))
    pv = [dict(elev=10.0, azim=-28.0, dist_mul=0.62, ground="cobble"),
          dict(suffix="_back", elev=12.0, azim=160.0, dist_mul=0.55, ground="cobble")]

    def previews_in():
        _render_interiors(visual, lamps)

    return dict(visual=visual, cols=cols_all, empties=empties, tris=tris, pv=pv, note=note, previews_in=previews_in,
                info=info)


# ======================================================================== previews
SHOTS = [
    ("hall", (0.3, -5.9, G0 + 1.6), (-2.6, -1.5, G0 + 1.1), 20.0),
    ("hall_stair", (-3.4, 0.6, G0 + 1.6), (3.0, -4.6, G0 + 1.9), 20.0),
    ("mess", (5.1, -1.1, G0 + 1.65), (9.6, -5.2, G0 + 0.7), 20.0),
    ("kitchen", (3.4, 2.1, G0 + 1.65), (-4.6, 5.3, G0 + 0.8), 20.0),
    ("coalstore", (5.1, 2.2, G0 + 1.55), (10.4, 4.6, CS + 0.2), 18.0),
    ("signals", (5.25, -1.15, F1 + 1.65), (8.6, -5.6, F1 + 0.8), 18.0),
    ("signals_cabinet", (10.2, -5.7, F1 + 1.65), (4.8, -2.0, F1 + 0.9), 18.0),
    ("signals_desk", (7.75, -4.55, F1 + 1.5), (7.6, -6.05, F1 + 0.72), 30.0),
    ("brenner", (-2.1, -1.0, F1 + 1.65), (-6.2, -5.2, F1 + 0.8), 20.0),
    ("bedroom", (-8.9, -6.0, F1 + 1.6), (-9.7, -1.0, F1 + 0.5), 20.0),
    ("dorm", (1.3, 3.2, F1 + 1.65), (9.0, 5.4, F1 + 0.6), 20.0),
    ("coat", (-3.7, -3.3, F1 + 1.6), (-1.75, -2.6, F1 + 1.1), 24.0),
    ("landing", (-1.1, -0.9, F1 + 1.65), (3.2, -5.4, F1 - 0.4), 20.0),
]


def _render_interiors(visual, lamps, shots=None, samples=24, res=(1280, 720)):
    import os
    import render
    from common import PREVIEW_DIR
    render.PREVIEW_DIR = PREVIEW_DIR
    sc = bpy.context.scene
    lights = [(f"PV_L{i}", (p[0] + XC, p[1], p[2]), 45.0, (1.0, 0.62, 0.34), 0.05) for i, p in enumerate(lamps)]
    want = shots or [s[0] for s in SHOTS]
    for (nm, cam, look, lens) in SHOTS:
        if nm not in want:
            continue
        render._setup(res, 0.9)
        sc.eevee.taa_render_samples = samples
        cam_s = (cam[0] + XC, cam[1], cam[2])
        look_s = (look[0] + XC, look[1], look[2])
        # render_interior re-runs _setup (64 samples); call the pieces directly so the sample count sticks
        sc.world = render._night_world()
        tmp = [render.point(*l) for l in lights]
        cd = bpy.data.cameras.new("PV_cam")
        cd.lens = lens
        cd.clip_start = 0.02
        camo = bpy.data.objects.new("PV_cam", cd)
        sc.collection.objects.link(camo)
        camo.location = cam_s
        camo.rotation_euler = (Vector(look_s) - Vector(cam_s)).to_track_quat("-Z", "Y").to_euler()
        sc.camera = camo
        tmp.append(camo)
        os.makedirs(PREVIEW_DIR, exist_ok=True)
        sc.render.filepath = os.path.join(PREVIEW_DIR, f"hotel_int_{nm}.png")
        sc.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(write_still=True)
        for o in tmp:
            bpy.data.objects.remove(o)
        print(f"[hotel_int] preview {nm}")
