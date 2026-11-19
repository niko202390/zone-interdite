"""Enterable house shell: the exterior of tools/blender/env/houses.py (same parts, same materials,
same footprint) with a hollow interior cut out of the wall body, through-openings with glass, a
separate swinging Door object, interior wall finishes and box collision per wall."""
import contextlib
import math
import random

import bmesh
from mathutils import Matrix, Vector

import geo
from geo import MB, bm_box_minmax, bm_prism, boolean, collision_bm, union
from parts import (FACES, Face, Frame, Opening, Roof, body_profile, chimney, cutter, door, dormer_geom,
                   dormer_roof, gable_coping, gable_profile, hay_door, main_roof, quoins, roff, shutters,
                   string_course, surround, text, window)
import houses
from ihelp import IFace, fbox, split_by, cyl_x

EPS = 0.006


class IMB(MB):
    """MB that can temporarily drop geometry of given materials (used to strip the fake dark
    'Interior' backing quads that parts.window()/door() add behind openings)."""

    def __init__(self):
        super().__init__()
        self._drop = set()

    @contextlib.contextmanager
    def dropping(self, *mats):
        old = set(self._drop)
        self._drop |= set(mats)
        try:
            yield self
        finally:
            self._drop = old

    def add_bm(self, bm, mat, **kw):
        if mat in self._drop:
            bm.free()
            return
        super().add_bm(bm, mat, **kw)


def through_cutter(F, op, t, margin=0.025):
    z0 = -0.35 if op.z0 <= 0.01 else op.z0 - margin
    return F.box(op.a0 - margin, op.a1 + margin, -(t + 0.25), 0.3, z0, op.z0 + op.h + margin)


# ------------------------------------------------------------------ doors
def plank_door_leaf(dmb, F, la0, la1, d_in, d_out, z0, z1, paint, rng, hinge_left=True):
    """Ledged-and-braced planked door. Outside face at d_out (straps, ring), inside at d_in (ledges)."""
    lw = la1 - la0
    dmb.add_bm(F.box(la0, la1, d_in, d_out, z0, z1), paint, scale=1.0, off=roff(rng))
    # outside strap hinges (pentures) and ring latch
    for zc in (z0 + 0.35, z1 - 0.35):
        dmb.add_bm(F.box(la0 - 0.005, la0 + lw * 0.75, d_out, d_out + 0.007, zc - 0.022, zc + 0.022), "Iron", scale=2.0)
        dmb.add_bm(F.box(la0 + lw * 0.72, la0 + lw * 0.78, d_out, d_out + 0.009, zc - 0.03, zc + 0.03), "Iron", scale=2.0)
    la = la1 - 0.13
    dmb.add_bm(F.box(la - 0.03, la + 0.03, d_out, d_out + 0.012, 0.98, 1.12), "Iron", scale=2.0)
    ring = geo.bm_cyl(0.045, 0.045, 0.012, segs=12)
    bmesh.ops.rotate(ring, verts=ring.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "X"))
    ang = math.atan2(F.n.y, F.n.x) + math.pi / 2
    dmb.add_bm(ring, "Iron", scale=2.0, matrix=Matrix.Translation(F.p(la, d_out + 0.02, 0.97)) @ Matrix.Rotation(ang, 4, "Z"))
    dmb.add_bm(F.box(la - 0.012, la + 0.012, d_out, d_out + 0.004, 1.17, 1.22), "BlackPaint")       # keyhole plate
    # inside: three ledges and two braces, thumb latch bar
    lt = 0.025
    zs = [z0 + 0.22, (z0 + z1) / 2, z1 - 0.22]
    for zc in zs:
        dmb.add_bm(F.box(la0 + 0.03, la1 - 0.03, d_in - lt, d_in, zc - 0.065, zc + 0.065), paint, scale=1.0, off=roff(rng))
    for i in range(2):
        za, zb = zs[i] + 0.065, zs[i + 1] - 0.065
        ln = math.hypot(lw - 0.16, zb - za)
        a = math.atan2(zb - za, lw - 0.16)
        bm = geo.bm_box(0, 0, 0, ln, lt, 0.11)
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(-a, 3, "Y"))
        # local x along the leaf (F.t), z up: rotate into the face frame
        ctr = F.p((la0 + la1) / 2, d_in - lt / 2, (za + zb) / 2)
        Mf = Matrix(((F.t.x, F.n.x, 0, 0), (F.t.y, F.n.y, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
        dmb.add_bm(bm, paint, scale=1.0, matrix=Matrix.Translation(ctr) @ Mf)
    dmb.add_bm(F.box(la1 - 0.3, la1 - 0.04, d_in - 0.03, d_in - 0.02, 1.02, 1.045), "Iron", scale=2.0)
    dmb.add_bm(F.box(la1 - 0.08, la1 - 0.05, d_in - 0.05, d_in, 0.98, 1.08), "Iron", scale=2.0)


def glazed_door_leaf(dmb, F, la0, la1, d_in, d_out, z0, z1, paint, rng):
    """Café door: lower panel, glazed upper with one glazing bar, brass push handle."""
    dmb.add_bm(F.box(la0, la1, d_in, d_out, z0, z0 + 1.0), paint, scale=1.0, off=roff(rng))
    dmb.add_bm(F.box(la0 + 0.09, la1 - 0.09, d_out, d_out + 0.012, z0 + 0.14, z0 + 0.86), paint, scale=1.0)
    dmb.add_bm(F.box(la0 + 0.09, la1 - 0.09, d_in - 0.012, d_in, z0 + 0.14, z0 + 0.86), paint, scale=1.0)
    for (fa, fb) in ((la0, la0 + 0.08), (la1 - 0.08, la1)):
        dmb.add_bm(F.box(fa, fb, d_in, d_out, z0 + 1.0, z1), paint, scale=1.0)
    dmb.add_bm(F.box(la0, la1, d_in, d_out, z1 - 0.09, z1), paint, scale=1.0)
    zm = (z0 + 1.0 + z1 - 0.09) / 2
    dmb.add_bm(F.box(la0 + 0.08, la1 - 0.08, d_in + 0.012, d_out - 0.012, zm - 0.02, zm + 0.02), paint, scale=1.0)
    dmb.add_bm(F.quad(la0 + 0.08, la1 - 0.08, z0 + 1.0, z1 - 0.09, (d_in + d_out) / 2), "WindowGlass")
    for d, s in ((d_out, 1), (d_in, -1)):
        dmb.add_bm(F.box(la1 - 0.16, la1 - 0.12, d + (0.0 if s > 0 else -0.035), d + (0.035 if s > 0 else 0.0), 0.95, 1.12),
                   "Brass", scale=2.0)
    dmb.add_bm(F.box(la0 + 0.1, la1 - 0.1, d_out, d_out + 0.004, z0 + 0.98, z0 + 1.0), "Brass", scale=2.0)   # kick plate rail


def build_door_object(name, F, la0, la1, d_in, d_out, z0, z1, paint, rng, glazed=False):
    """Door leaf as its own object; origin on the hinge line (la0, d_in). Rotating +90 deg about Godot +Y
    (Blender +Z) swings it into the house. Collision child `<name>_col-colonly`."""
    dmb = MB()
    if glazed:
        glazed_door_leaf(dmb, F, la0, la1, d_in, d_out, z0, z1, paint, rng)
    else:
        plank_door_leaf(dmb, F, la0, la1, d_in, d_out, z0, z1, paint, rng)
    ob = dmb.build(name)
    hinge = F.p(la0, d_in, z0)
    ob.data.transform(Matrix.Translation(-hinge))
    ob.location = hinge
    bb = fbox(F, la0, la1, d_in - 0.005, d_out + 0.005, z0, z1)
    col = geo.collision_box(f"{name}_col", *bb)
    col.data.transform(Matrix.Translation(-hinge))
    col.parent = ob
    col.matrix_parent_inverse = Matrix.Identity(4)
    col.location = (0, 0, 0)
    return ob, col, dmb.tri_count(), hinge


# --------------------------------------------------------------- café shopfront
def cafe_shopfront(W, t, door_paint):
    """houses._cafe_shopfront, rebuilt as a real shopfront: cut goes through the wall, glazing has
    no dark backing, and the glazed door leaf is a separate object."""
    x0, x1 = -W / 2 + 0.45, W / 2 - 0.45
    top = 2.55
    depth = 0.16
    door_a = 1.15
    win_spans = [(x0 + 0.28, door_a - 0.55), (door_a + 0.55, x1 - 0.28)]
    da0, da1 = door_a - 0.48, door_a + 0.48

    def cut(F):
        return F.box(x0 + 0.2, x1 - 0.2, -(t + 0.25), 0.3, -0.35, top)

    def build(mb, F, rng):
        P = "Paint_green"
        for (pa, pb) in ((x0 - 0.02, x0 + 0.26), (x1 - 0.26, x1 + 0.02)):
            mb.add_bm(F.box(pa, pb, 0.0, depth, 0.0, top), P, scale=1.0, off=roff(rng))
            mb.add_bm(F.box(pa - 0.03, pb + 0.03, 0.0, depth + 0.03, 0.0, 0.3), P, scale=1.0)
            mb.add_bm(F.box(pa - 0.03, pb + 0.03, 0.0, depth + 0.03, top - 0.12, top), P, scale=1.0)
            mb.add_bm(F.box(pa + 0.02, pb - 0.02, -t - 0.01, 0.0, 0.0, top), P, scale=1.0)        # inner pier casing
        mb.add_bm(F.box(x0 - 0.06, x1 + 0.06, 0.0, depth + 0.02, top, top + 0.5), P, scale=1.0, off=roff(rng))
        mb.add_bm(F.box(x0 - 0.12, x1 + 0.12, 0.0, depth + 0.12, top + 0.5, top + 0.58, bevel=0.02, segs=2), P, scale=1.0)
        mb.add_bm(F.box(x0 - 0.16, x1 + 0.16, 0.0, depth + 0.16, top + 0.58, top + 0.64), "Zinc", scale=1.0)
        text(mb, F, "CAFÉ DU PORT", (x0 + x1) / 2, top + 0.25, depth + 0.02, 0.34, "SignPaint", extrude=0.004, spacing=1.08)
        # oak bressummer carrying the wall over the shop opening (seen from inside)
        mb.add_bm(F.box(x0 + 0.15, x1 - 0.15, -t - 0.02, -0.06, top - 0.09, top + 0.02), "Wood_dark", scale=1.0)
        for (wa, wb) in win_spans:
            mb.add_bm(F.box(wa - 0.06, wb + 0.06, -0.06, depth - 0.02, 0.0, 0.62), P, scale=1.0)
            mb.add_bm(F.box(wa + 0.08, wb - 0.08, depth - 0.02, depth + 0.0, 0.1, 0.52), P, scale=1.0)
            mb.add_bm(F.box(wa + 0.08, wb - 0.08, -0.075, -0.06, 0.1, 0.52), P, scale=1.0)            # inside panel
            mb.add_bm(F.box(wa - 0.06, wb + 0.06, -0.06, depth + 0.03, 0.62, 0.7), P, scale=1.0)
            mb.add_bm(F.box(wa - 0.08, wb + 0.08, -0.36, -0.06, 0.6, 0.66), "Furn_oak", scale=1.0)       # display shelf
            for (fa, fb) in ((wa - 0.06, wa), (wb, wb + 0.06)):
                mb.add_bm(F.box(fa, fb, -0.06, depth - 0.02, 0.7, top), P, scale=1.0)
            mb.add_bm(F.box(wa, wb, -0.06, depth - 0.02, top - 0.08, top), P, scale=1.0)
            nb = 3
            for k in range(1, nb):
                ac = wa + (wb - wa) * k / nb
                mb.add_bm(F.box(ac - 0.018, ac + 0.018, -0.01, 0.05, 0.7, top - 0.08), P, scale=1.0)
            mb.add_bm(F.box(wa, wb, -0.01, 0.05, 1.95, 1.99), P, scale=1.0)
            mb.add_bm(F.quad(wa, wb, 0.7, top - 0.08, 0.02), "WindowGlass")
        # door frame stays with the house; the leaf is a separate object
        mb.add_bm(F.box(da0 - 0.07, da0, -0.14, depth - 0.02, 0.0, top), P, scale=1.0)
        mb.add_bm(F.box(da1, da1 + 0.07, -0.14, depth - 0.02, 0.0, top), P, scale=1.0)
        mb.add_bm(F.box(da0, da1, -0.14, depth - 0.02, top - 0.1, top), P, scale=1.0)
        mb.add_bm(F.box(da0 - 0.1, da1 + 0.1, -0.2, 0.25, -0.1, 0.06, bevel=0.012, segs=2), "Granite", off=roff(rng))
        mb.add_bm(F.box(da0 - 0.06, da1 + 0.06, -t - 0.02, -0.2, -0.3, 0.13), "Granite", off=roff(rng))   # inner sill

    door_spec = dict(la0=da0 + 0.005, la1=da1 - 0.005, d_in=-0.135, d_out=-0.08, z1=top - 0.1, glazed=True,
                     gap=(da0, da1, top - 0.1))
    return dict(cutter=cut, build=build, depth=depth + 0.2, door=door_spec,
                damp_skip={"front": [(x0 - 0.2, x1 + 0.2)]}, span=(x0 + 0.2, x1 - 0.2), top=top)


# ------------------------------------------------------------------- shell
def int_damp(mb, F, a0, a1, rng, skip=(), z0=0.13, height=0.9):
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
        if y - x < 0.15:
            continue
        h = height * rng.uniform(0.75, 1.15)
        uvs = [(x / 2 + uo, 0.0), (y / 2 + uo, 0.0), (y / 2 + uo, 1.0), (x / 2 + uo, 1.0)]
        mb.add_bm(F.quad(x, y, z0 - 0.02, z0 - 0.02 + h, 0.008, uvs), "DecalDamp", uv="keep")


def interior_faces(W, D, t, x0=None, x1=None):
    """IFace per inner wall plane. x0/x1 limit the room along X (longère cross wall)."""
    x0 = -W / 2 + t if x0 is None else x0
    x1 = W / 2 - t if x1 is None else x1
    yi = D / 2 - t
    cx = (x0 + x1) / 2
    return {
        "front": IFace((cx, -yi, 0), (0, 1, 0), x1 - x0),
        "back": IFace((cx, yi, 0), (0, -1, 0), x1 - x0),
        "left": IFace((x0, 0, 0), (1, 0, 0), 2 * yi),
        "right": IFace((x1, 0, 0), (-1, 0, 0), 2 * yi),
    }


def build_shell(spec):
    """spec keys (in addition to houses.build_house): t (wall thickness), floor_z, cavity (list of bmesh
    factory callables), cavity_aabb, ceil_mat, wall_mat_in, door_paint, room_x (x0, x1), roof_col
    ('solid' | 'loft'), solid_boxes [(name, aabb)] for non-enterable volumes.
    Openings can carry .through (real opening) and .enter (name of the door object)."""
    rng = random.Random(spec["seed"])
    W, D, He, t = spec["W"], spec["D"], spec["He"], spec["t"]
    fz = spec["floor_z"]
    R = Roof(W, D, He, spec["pitch"])
    faces = {k: Face(k, W, D) for k in FACES}
    mb = IMB()
    ops = list(spec["openings"])
    doors = []

    dms = []
    for d in spec.get("dormers", []):
        dm = dormer_geom(R, d["a"], d["wd"], He + d["zd"])
        dm.update(d)
        dms.append(dm)
        op = Opening("front", d["a"], He + d["z0"], d["w"], d["h"], kind=d.get("kind", "window"),
                     shutters="none", glow=d.get("glow", False), rows=d.get("rows", 2),
                     paint=d.get("paint", "Wood_grey"), frame=d.get("frame", "Paint_cream"))
        op.through = d.get("through", False)
        ops.append(op)

    tg = R.tg
    bodies = [bm_prism(body_profile(R), -W / 2, W / 2),
              bm_prism(gable_profile(R), -W / 2, -W / 2 + tg),
              bm_prism(gable_profile(R), W / 2 - tg, W / 2)]
    for dm in dms:
        bodies += dm["bodies"]
    body = union(bodies)
    cutters = [(through_cutter(faces[op.face], op, t) if getattr(op, "through", False) else cutter(faces[op.face], op))
               for op in ops]
    shop = spec.get("shopfront")
    if shop:
        cutters.append(shop["cutter"](faces["front"]))
    body = boolean(body, cutters)
    cav = [f() for f in spec["cavity"]]
    cav = union(cav) if len(cav) > 1 else cav[0]
    body = boolean(body, [cav])

    # material per face: outside = wall stone/render, inside the cavity = plaster / ceiling boards
    cx0, cy0, cz0, cx1, cy1, cz1 = spec["cavity_aabb"]

    def key(f):
        c = f.calc_center_median()
        if cx0 - EPS <= c.x <= cx1 + EPS and cy0 - EPS <= c.y <= cy1 + EPS and cz0 - EPS <= c.z <= cz1 + EPS:
            n = f.normal
            if n.z < -0.5:
                return spec.get("ceil_mat", "Wood_dark")
            if n.z > 0.5:
                return "Flags"
            return spec.get("wall_mat_in", "Plaster")
        return spec["wall"]

    for mat, part in split_by(body, key).items():
        mb.add_bm(part, mat, off=roff(rng))

    # ---- dressed stone + joinery
    quoins(mb, W, D, He, rng)
    if spec.get("cornice"):
        string_course(mb, W, D, He + 0.02, rng)
    for op in ops:
        F = faces[op.face]
        thr = getattr(op, "through", False)
        surround(mb, F, op, rng, lintel_h=0.3 if op.w < 1.2 else 0.36)
        if op.kind == "window":
            if thr:
                with mb.dropping("Interior"):
                    window(mb, F, op)
                _reveal_lining(mb, F, op, t, rng)
            else:
                window(mb, F, op)
            shutters(mb, F, op, rng)
        elif op.kind in ("door", "byre"):
            if getattr(op, "enter", None):
                z1 = op.z0 + op.h
                for (ja, jb) in ((op.a0 - 0.03, op.a0 + 0.07), (op.a1 - 0.07, op.a1 + 0.03)):
                    mb.add_bm(F.box(ja, jb, -t + 0.06, -t + 0.17, fz - 0.01, z1), "Wood_dark", scale=1.0)
                mb.add_bm(F.box(op.a0 - 0.03, op.a1 + 0.03, -t + 0.06, -t + 0.17, z1 - 0.07, z1 + 0.03), "Wood_dark", scale=1.0)
                mb.add_bm(F.box(op.a0 - 0.03, op.a1 + 0.03, -t - 0.02, -0.25, -0.3, fz), "Granite", off=roff(rng))
                la0, la1 = op.a0 + 0.04, op.a1 - 0.04
                ob, col, tri, hinge = build_door_object(op.enter, F, la0, la1, -t + 0.01, -t + 0.06, fz + 0.008,
                                                        z1 - 0.04, op.door_paint, rng)
                doors.append(dict(name=op.enter, ob=ob, col=col, tris=tri, hinge=hinge, face=op.face,
                                  gap=(op.a0 + 0.07, op.a1 - 0.07, z1 - 0.07), op=op, clear=(op.w - 0.16, z1 - 0.07 - fz)))
            else:
                door(mb, F, op, rng)
        elif op.kind == "hay":
            hay_door(mb, F, op, rng)
    if shop:
        shop["build"](mb, faces["front"], rng)
        ds = shop["door"]
        Ff = faces["front"]
        ob, col, tri, hinge = build_door_object("Door", Ff, ds["la0"], ds["la1"], ds["d_in"], ds["d_out"], fz + 0.008,
                                                ds["z1"], spec["door_paint"], rng, glazed=True)
        g = ds["gap"]
        doors.append(dict(name="Door", ob=ob, col=col, tris=tri, hinge=hinge, face="front", gap=g,
                          clear=(g[1] - g[0] - 0.06, g[2] - fz)))

    # ---- roof (unchanged exterior)
    main_roof(mb, R, rng, dormers=[dict(a0=dm["a0"], a1=dm["a1"], z_top=dm["z_top"]) for dm in dms])
    for dm in dms:
        dormer_roof(mb, R, dm, rng)
    gable_coping(mb, R, rng)
    chim_boxes = [chimney(mb, R, sx, rng) for sx in spec.get("chimneys", [-1, 1])]

    # ---- exterior weathering (as houses.py)
    houses._damp(mb, faces, W, D, ops, rng, extra_skip=shop.get("damp_skip") if shop else None)
    for F in faces.values():
        houses._streaks(mb, F, ops, rng)

    # ---- interior rising damp along the inner wall bases
    rx0, rx1 = spec.get("room_x", (-W / 2 + t, W / 2 - t))
    ifs = interior_faces(W, D, t, rx0, rx1)
    for name, IF in ifs.items():
        skip = []
        for op in ops:
            if op.face == name and op.z0 < 0.05 and getattr(op, "through", False):
                # interior a = -(exterior a) for front/back relative to room centre
                skip.append(_ext_to_int(IF, faces[name], op.a0 - 0.1, op.a1 + 0.1))
        if shop and name == "front":
            skip.append(_ext_to_int(IF, faces[name], *shop["span"]))
        skip += spec.get("damp_skip_in", {}).get(name, [])
        half = IF.length / 2 - 0.02
        int_damp(mb, IF, -half, half, rng, skip=[tuple(sorted(s)) for s in skip], z0=fz,
                 height=spec.get("damp_h", 0.85))

    # ---- collision
    cols = []
    for name, F in faces.items():
        L = W if name in ("front", "back") else D - 2 * t
        gaps = sorted([d["gap"] for d in doors if d["face"] == name])
        dmax = 0.0
        if shop and name == "front":
            dmax = shop["depth"]
        a = -L / 2
        top = He
        for (g0, g1, gz) in gaps:
            cols.append((f"Wall_{name}", fbox(F, a, g0, -t, dmax, -0.3, top)))
            cols.append((f"Wall_{name}_lintel", fbox(F, g0, g1, -t, dmax, gz, top)))
            a = g1
        cols.append((f"Wall_{name}", fbox(F, a, L / 2, -t, dmax, -0.3, top)))
    for nm, bb in spec.get("solid_boxes", []):
        cols.append((nm, bb))
    convex = []
    if spec.get("roof_col", "solid") == "solid":
        prof = [(-D / 2 - R.ov, R.z_eave - 0.05), (D / 2 + R.ov, R.z_eave - 0.05), (0.0, R.Hr + R.rise)]
        convex.append(collision_bm("Roof", bm_prism(prof, -W / 2, W / 2)))
    else:
        convex += spec["roof_col_fn"](R)
    for i, b in enumerate(chim_boxes):
        cols.append((f"Chimney{i}", b))
    for i, dm in enumerate(dms):
        cols.append((f"Dormer{i}", (dm["a0"] + 0.1, -D / 2 - 0.05, He - 0.4, dm["a1"] - 0.1, -D / 2 + dm["depth"] * 0.5,
                                    dm["z_top"])))
    for i, op in enumerate([o for o in ops if o.z0 < 0.05]):
        F = faces[op.face]
        p0, p1 = F.p(op.a0 - 0.12, -0.25, -0.12), F.p(op.a1 + 0.12, 0.32, 0.13)
        cols.append((f"Step{i}", (min(p0.x, p1.x), min(p0.y, p1.y), -0.12, max(p0.x, p1.x), max(p0.y, p1.y), 0.13)))
    return dict(mb=mb, doors=doors, cols=cols, convex=convex, R=R, faces=faces, ifaces=ifs, ops=ops, rng=rng)


def _ext_to_int(IF, F, a0, a1):
    p0, p1 = F.p(a0, 0, 0), F.p(a1, 0, 0)
    b0, b1 = (p0 - IF.o).dot(IF.t), (p1 - IF.o).dot(IF.t)
    return (min(b0, b1), max(b0, b1))


def _reveal_lining(mb, F, op, t, rng, margin=0.025):
    """Limewashed inner reveals and an oak sill board for a through window."""
    a0, a1, z0, z1 = op.a0 - margin, op.a1 + margin, op.z0 - margin, op.z0 + op.h + margin
    d0, d1 = -t - 0.005, -0.31
    lt = 0.012
    mb.add_bm(F.box(a0, a0 + lt, d0, d1, z0, z1), "Plaster", off=roff(rng))
    mb.add_bm(F.box(a1 - lt, a1, d0, d1, z0, z1), "Plaster", off=roff(rng))
    mb.add_bm(F.box(a0, a1, d0, d1, z1 - lt, z1), "Plaster", off=roff(rng))
    mb.add_bm(F.box(a0 - 0.05, a1 + 0.05, d0 - 0.035, d1, z0, z0 + 0.035), "Furn_oak", scale=1.0, off=roff(rng))
