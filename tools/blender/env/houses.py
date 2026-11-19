"""Breton granite houses: house_bourg, house_longere, house_cafe."""
import math
import random

import bmesh
from mathutils import Matrix, Vector

import geo
from geo import MB, bm_box_minmax, bm_prism, boolean, collision_box, collision_bm, union
from parts import (FACES, Face, Frame, Opening, Roof, body_profile, chimney, cutter, damp_strip, door,
                   dormer_geom, dormer_roof, gable_coping, gable_profile, hay_door, main_roof, quoins,
                   roff, shutters, streak, string_course, surround, text, window)


def _streaks(mb, F, ops, rng):
    for op in ops:
        if op.face != F.name or op.kind not in ("window",) or op.z0 < 0.3:
            continue
        top = op.z0 - 0.1
        floor = 0.2
        for other in ops:
            if other is op or other.face != F.name:
                continue
            if other.a1 + 0.35 > op.a0 and other.a0 - 0.35 < op.a1 and other.z0 + other.h + 0.35 < top:
                floor = max(floor, other.z0 + other.h + 0.4)
        length = min(rng.uniform(0.7, 1.2), top - floor)
        if length > 0.25:
            streak(mb, F, op.a + rng.uniform(-0.04, 0.04), op.w + 0.25, top, length, rng)


def _damp(mb, faces, W, D, ops, rng, extra_skip=None):
    for name, F in faces.items():
        half = F.length / 2 - 0.3
        skip = [(op.a0 - 0.15, op.a1 + 0.15) for op in ops if op.face == name and op.z0 < 0.05]
        if extra_skip and name in extra_skip:
            skip += extra_skip[name]
        damp_strip(mb, F, -half, half, rng, skip=skip, height=rng.uniform(0.8, 1.1))


def build_house(spec):
    """spec keys: name, W, D, He, pitch, wall, seed, openings[], dormers[], chimneys(list of sx),
    cornice(bool), shopfront(callable or None)."""
    rng = random.Random(spec["seed"])
    W, D, He = spec["W"], spec["D"], spec["He"]
    R = Roof(W, D, He, spec["pitch"])
    faces = {k: Face(k, W, D) for k in FACES}
    mb = MB()
    ops = list(spec["openings"])

    # ---- dormers (body volumes + their openings)
    dms = []
    for d in spec.get("dormers", []):
        dm = dormer_geom(R, d["a"], d["wd"], He + d["zd"])
        dm.update(d)
        dms.append(dm)
        ops.append(Opening("front", d["a"], He + d["z0"], d["w"], d["h"], kind=d.get("kind", "window"),
                           shutters="none", glow=d.get("glow", False), rows=d.get("rows", 2),
                           paint=d.get("paint", "Wood_grey"), frame=d.get("frame", "Paint_cream")))

    # ---- wall body: main prism + raised gables + dormers, minus openings
    tg = R.tg
    bodies = [bm_prism(body_profile(R), -W / 2, W / 2),
              bm_prism(gable_profile(R), -W / 2, -W / 2 + tg),
              bm_prism(gable_profile(R), W / 2 - tg, W / 2)]
    for dm in dms:
        bodies += dm["bodies"]
    body = union(bodies)
    cutters = [cutter(faces[op.face], op) for op in ops]
    shop = spec.get("shopfront")
    shop_info = None
    if shop:
        shop_info = shop["cutter"](faces["front"])
        cutters.append(shop_info)
    body = boolean(body, cutters)
    mb.add_bm(body, spec["wall"], off=roff(rng))

    # ---- dressed stone
    quoins(mb, W, D, He, rng)
    if spec.get("cornice"):
        string_course(mb, W, D, He + 0.02, rng)
    for op in ops:
        F = faces[op.face]
        surround(mb, F, op, rng, lintel_h=0.3 if op.w < 1.2 else 0.36)
        if op.kind == "window":
            window(mb, F, op)
            shutters(mb, F, op, rng)
        elif op.kind in ("door", "byre"):
            door(mb, F, op, rng)
        elif op.kind == "hay":
            hay_door(mb, F, op, rng)
    if shop:
        shop["build"](mb, faces["front"], rng)

    # ---- roof
    main_roof(mb, R, rng, dormers=[dict(a0=dm["a0"], a1=dm["a1"], z_top=dm["z_top"]) for dm in dms])
    for dm in dms:
        dormer_roof(mb, R, dm, rng)
    gable_coping(mb, R, rng)
    chim_boxes = [chimney(mb, R, sx, rng) for sx in spec.get("chimneys", [-1, 1])]

    # ---- weathering decals
    _damp(mb, faces, W, D, ops, rng, extra_skip=shop.get("damp_skip") if shop else None)
    for F in faces.values():
        _streaks(mb, F, ops, rng)

    ob = mb.build(spec["name"])
    tris = mb.tri_count()

    # ---- collision
    cols = []
    front_extra = shop.get("depth", 0.0) if shop else 0.0
    cols.append(collision_box("Body", -W / 2, -D / 2 - front_extra, -0.3, W / 2, D / 2, He))
    prof = [(-D / 2 - R.ov, R.z_eave - 0.05), (D / 2 + R.ov, R.z_eave - 0.05), (0.0, R.Hr + R.rise)]
    cols.append(collision_bm("Roof", bm_prism(prof, -W / 2, W / 2)))
    for i, b in enumerate(chim_boxes):
        cols.append(collision_box(f"Chimney{i}", *b))
    for i, dm in enumerate(dms):
        cols.append(collision_box(f"Dormer{i}", dm["a0"] + 0.1, -D / 2 - 0.05, He - 0.4, dm["a1"] - 0.1,
                                  -D / 2 + dm["depth"], dm["z_top"]))
    for i, op in enumerate([o for o in ops if o.z0 < 0.05]):
        F = faces[op.face]
        p0, p1 = F.p(op.a0 - 0.12, -0.25, -0.12), F.p(op.a1 + 0.12, 0.32, 0.13)
        cols.append(collision_box(f"Step{i}", min(p0.x, p1.x), min(p0.y, p1.y), -0.12, max(p0.x, p1.x), max(p0.y, p1.y), 0.13))
    return ob, cols, tris


# ===================================================================== specs
def spec_bourg():
    W, D, He = 8.0, 7.0, 6.0
    sh = "Paint_blue"
    o = []
    # ground floor: window, door, window
    o.append(Opening("front", -2.55, 0.85, 0.95, 1.35, shutters="open", paint=sh))
    o.append(Opening("front", 0.0, 0.0, 1.0, 2.1, kind="door", paint="Paint_oxblood", leaves=1))
    o.append(Opening("front", 2.55, 0.85, 0.95, 1.35, shutters="closed", paint=sh))
    # first floor
    o.append(Opening("front", -2.55, 3.55, 0.95, 1.45, shutters="open", paint=sh))
    o.append(Opening("front", 0.0, 3.55, 0.95, 1.45, shutters="half", paint=sh, glow=True))
    o.append(Opening("front", 2.55, 3.55, 0.95, 1.45, shutters="open", paint=sh))
    # back
    o.append(Opening("back", -1.6, 0.0, 0.95, 2.0, kind="door", paint="Paint_blue", leaves=1))
    o.append(Opening("back", 1.8, 0.95, 0.85, 1.2, shutters="closed", paint=sh))
    o.append(Opening("back", -1.6, 3.6, 0.85, 1.3, shutters="none"))
    o.append(Opening("back", 1.8, 3.6, 0.85, 1.3, shutters="open", paint=sh))
    # gables: small attic light on the left
    o.append(Opening("left", 0.0, 6.6, 0.55, 0.7, shutters="none", rows=2, leaves=1))
    dormers = [dict(a=-1.6, wd=1.6, zd=1.2, z0=-0.1, w=0.78, h=0.95),
               dict(a=1.6, wd=1.6, zd=1.2, z0=-0.1, w=0.78, h=0.95, glow=True)]
    return dict(name="house_bourg", W=W, D=D, He=He, pitch=46.0, wall="Rubble", seed=101,
                openings=o, dormers=dormers, chimneys=[-1, 1], cornice=True)


def spec_longere():
    W, D, He = 14.0, 6.5, 2.75
    o = []
    o.append(Opening("front", -5.3, 0.8, 0.85, 1.15, shutters="none", rows=3))
    o.append(Opening("front", -3.6, 0.0, 0.95, 1.95, kind="door", paint="Paint_green", leaves=1))
    o.append(Opening("front", -1.7, 0.8, 0.85, 1.15, shutters="closed", paint="Paint_green", glow=False))
    o.append(Opening("front", 3.0, 0.0, 1.7, 2.05, kind="byre", paint="Wood_grey", leaves=2))
    o.append(Opening("front", 5.6, 1.2, 0.4, 0.55, shutters="none", rows=1, leaves=1))
    o.append(Opening("back", 4.5, 0.85, 0.7, 0.9, shutters="none", rows=2))
    o.append(Opening("back", -4.0, 0.85, 0.7, 0.9, shutters="none", rows=2, glow=True))
    o.append(Opening("left", 0.0, 3.4, 0.5, 0.65, shutters="none", rows=2, leaves=1))
    dormers = [dict(a=-3.6, wd=1.5, zd=1.15, z0=-0.1, w=0.72, h=0.9),
               dict(a=3.0, wd=1.7, zd=1.35, z0=-0.2, w=0.95, h=1.2, kind="hay", paint="Wood_grey")]
    return dict(name="house_longere", W=W, D=D, He=He, pitch=47.0, wall="Rubble", seed=202,
                openings=o, dormers=dormers, chimneys=[-1], cornice=False)


def _cafe_shopfront(W):
    x0, x1 = -W / 2 + 0.45, W / 2 - 0.45
    top = 2.55
    depth = 0.16
    door_a = 1.15
    win_spans = [(x0 + 0.28, door_a - 0.55), (door_a + 0.55, x1 - 0.28)]

    def cut(F):
        return F.box(x0 + 0.2, x1 - 0.2, -0.45, 0.3, -0.3, top)

    def build(mb, F, rng):
        P = "Paint_green"
        # pilasters with plinth and capital
        for (pa, pb) in ((x0 - 0.02, x0 + 0.26), (x1 - 0.26, x1 + 0.02)):
            mb.add_bm(F.box(pa, pb, 0.0, depth, 0.0, top), P, scale=1.0, off=roff(rng))
            mb.add_bm(F.box(pa - 0.03, pb + 0.03, 0.0, depth + 0.03, 0.0, 0.3), P, scale=1.0)
            mb.add_bm(F.box(pa - 0.03, pb + 0.03, 0.0, depth + 0.03, top - 0.12, top), P, scale=1.0)
        # fascia + cornice
        mb.add_bm(F.box(x0 - 0.06, x1 + 0.06, 0.0, depth + 0.02, top, top + 0.5), P, scale=1.0, off=roff(rng))
        mb.add_bm(F.box(x0 - 0.12, x1 + 0.12, 0.0, depth + 0.12, top + 0.5, top + 0.58, bevel=0.02, segs=2), P, scale=1.0)
        mb.add_bm(F.box(x0 - 0.16, x1 + 0.16, 0.0, depth + 0.16, top + 0.58, top + 0.64), "Zinc", scale=1.0)
        text(mb, F, "CAFÉ DU PORT", (x0 + x1) / 2, top + 0.25, depth + 0.02, 0.34, "SignPaint", extrude=0.004, spacing=1.08)
        # shop windows: stall riser, frame, glazing bars, glass, interior
        for (wa, wb) in win_spans:
            mb.add_bm(F.box(wa - 0.06, wb + 0.06, -0.06, depth - 0.02, 0.0, 0.62), P, scale=1.0)
            mb.add_bm(F.box(wa + 0.08, wb - 0.08, depth - 0.02, depth + 0.0, 0.1, 0.52), P, scale=1.0)     # raised panel
            mb.add_bm(F.box(wa - 0.06, wb + 0.06, -0.06, depth + 0.03, 0.62, 0.7), P, scale=1.0)           # sill
            for (fa, fb) in ((wa - 0.06, wa), (wb, wb + 0.06)):
                mb.add_bm(F.box(fa, fb, -0.06, depth - 0.02, 0.7, top), P, scale=1.0)
            mb.add_bm(F.box(wa, wb, -0.06, depth - 0.02, top - 0.08, top), P, scale=1.0)
            nb = 3
            for k in range(1, nb):
                ac = wa + (wb - wa) * k / nb
                mb.add_bm(F.box(ac - 0.018, ac + 0.018, 0.0, 0.05, 0.7, top - 0.08), P, scale=1.0)
            mb.add_bm(F.box(wa, wb, 0.0, 0.05, 1.95, 1.99), P, scale=1.0)
            mb.add_bm(F.quad(wa, wb, 0.7, top - 0.08, 0.02), "WindowGlow" if wa > 0 else "WindowGlass")
            mb.add_bm(F.quad(wa - 0.1, wb + 0.1, 0.0, top, -0.40), "Interior")
        # glazed door
        da0, da1 = door_a - 0.48, door_a + 0.48
        mb.add_bm(F.box(da0 - 0.07, da0, -0.1, depth - 0.02, 0.0, top), P, scale=1.0)
        mb.add_bm(F.box(da1, da1 + 0.07, -0.1, depth - 0.02, 0.0, top), P, scale=1.0)
        mb.add_bm(F.box(da0, da1, -0.1, depth - 0.02, top - 0.1, top), P, scale=1.0)
        mb.add_bm(F.box(da0, da1, -0.12, -0.06, 0.02, 1.05), P, scale=1.0)          # lower door panel
        for (fa, fb) in ((da0, da0 + 0.08), (da1 - 0.08, da1)):
            mb.add_bm(F.box(fa, fb, -0.12, -0.06, 1.05, top - 0.1), P, scale=1.0)
        mb.add_bm(F.box(da0, da1, -0.12, -0.06, 1.95, 2.02), P, scale=1.0)
        mb.add_bm(F.quad(da0 + 0.08, da1 - 0.08, 1.05, top - 0.1, -0.09), "WindowGlass")
        mb.add_bm(F.box(da1 - 0.2, da1 - 0.14, -0.06, -0.03, 1.0, 1.12), "Zinc", scale=2.0)          # handle
        mb.add_bm(F.box(da0 - 0.1, da1 + 0.1, -0.2, 0.25, -0.1, 0.06, bevel=0.012, segs=2), "Granite", off=roff(rng))  # step
        mb.add_bm(F.quad(da0 - 0.1, da1 + 0.1, 0.0, top, -0.40), "Interior")

    return dict(cutter=cut, build=build, depth=depth + 0.2,
                damp_skip={"front": [(x0 - 0.2, x1 + 0.2)]})


def _tabac(mb, W, D, rng):
    """Red tabac 'carotte' lozenge on an iron bracket, perpendicular to the facade."""
    a_c = W / 2 - 0.7
    zc = 3.95
    dc = 0.62
    y_wall = -D / 2
    # bracket
    mb.add_bm(bm_box_minmax(a_c - 0.02, y_wall - dc - 0.05, zc + 0.43, a_c + 0.02, y_wall + 0.01, zc + 0.47), "Iron", scale=2.0)
    mb.add_bm(bm_box_minmax(a_c - 0.05, y_wall - 0.012, zc + 0.3, a_c + 0.05, y_wall + 0.01, zc + 0.6), "Iron", scale=2.0)
    for yy in (y_wall - dc - 0.04,):
        mb.add_bm(bm_box_minmax(a_c - 0.008, yy - 0.008, zc + 0.36, a_c + 0.008, yy + 0.008, zc + 0.44), "Iron", scale=2.0)
    # lozenge: diamond profile in (y,z), extruded along x
    hw, hh, th = 0.19, 0.36, 0.13
    prof = [(y_wall - dc + hw, zc), (y_wall - dc, zc - hh), (y_wall - dc - hw, zc), (y_wall - dc, zc + hh)]
    bm = bm_prism(prof, a_c - th / 2, a_c + th / 2)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.012, segments=2, profile=0.5, affect="EDGES", clamp_overlap=True)
    mb.add_bm(bm, "TabacRed", scale=1.0)
    for sgn in (-1, 1):
        n = Vector((sgn, 0, 0))
        t = Vector((0, sgn, 0))
        fr = Frame((a_c, y_wall - dc, 0.0), t, n)
        text(mb, fr, "TABAC", 0.0, zc, th / 2, 0.085, "SignPaint", extrude=0.002, spacing=1.05)


def spec_cafe():
    W, D, He = 7.0, 7.0, 6.1
    sh = "Paint_green"
    o = []
    o.append(Opening("front", -2.2, 3.6, 0.9, 1.45, shutters="open", paint=sh))
    o.append(Opening("front", 0.0, 3.6, 0.9, 1.45, shutters="closed", paint=sh))
    o.append(Opening("front", 2.2, 3.6, 0.9, 1.45, shutters="halfl", paint=sh, glow=True))
    o.append(Opening("back", -1.5, 0.0, 0.95, 2.0, kind="door", paint="Paint_green", leaves=1))
    o.append(Opening("back", 1.6, 0.9, 0.85, 1.2, shutters="closed", paint=sh))
    o.append(Opening("back", 0.0, 3.6, 0.85, 1.3, shutters="open", paint=sh))
    o.append(Opening("right", -1.2, 3.7, 0.7, 1.1, shutters="closed", paint=sh))
    dormers = [dict(a=0.0, wd=1.6, zd=1.2, z0=-0.1, w=0.78, h=0.95)]
    return dict(name="house_cafe", W=W, D=D, He=He, pitch=46.0, wall="Render", seed=303,
                openings=o, dormers=dormers, chimneys=[-1, 1], cornice=True, shopfront=_cafe_shopfront(W),
                extras=_tabac)


def build(name):
    spec = {"house_bourg": spec_bourg, "house_longere": spec_longere, "house_cafe": spec_cafe}[name]()
    if "extras" in spec:
        extras = spec.pop("extras")
        # extras are built into a second builder and merged as its own object
        ob, cols, tris = build_house(spec)
        mb = MB()
        extras(mb, spec["W"], spec["D"], random.Random(spec["seed"] + 1))
        ob2 = mb.build(spec["name"] + "_sign")
        return [ob, ob2], cols, tris + mb.tri_count()
    ob, cols, tris = build_house(spec)
    return [ob], cols, tris
