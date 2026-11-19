"""Zone Interdite - enterable house interiors (bourg house, longère, café) + reusable furniture props.

Usage (from repo root):
  "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" --background --factory-startup \
      --python-exit-code 1 --python tools/blender/interiors/build_interiors.py -- [names...] [--no-preview] [--force-tex]

Names: house_bourg_int, house_longere_int, house_cafe_int, props (or a single prop name:
lit_clos, table_bench, dresser, fireplace, bar_counter). No names = everything.
Outputs: game/assets/models/env/<house>.glb, game/assets/models/props/<prop>.glb, previews in
tools/blender/interiors/previews/. Every glb is passed through tools/glb_strip_icc.py.
"""
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.abspath(os.path.join(HERE, "..", "env"))
for p in (ENV, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import textures  # noqa: E402
import itex  # noqa: E402
import geo  # noqa: E402
import ihelp  # noqa: E402
from ihelp import Put, collision_objs, export_glb_path, multi_box_obj, strip_icc  # noqa: E402
import furniture as fu  # noqa: E402
import rooms  # noqa: E402
import render  # noqa: E402
import check_glb  # noqa: E402

PROPS = {
    "lit_clos": lambda P: fu.lit_clos(P),
    "table_bench": lambda P: fu.table_bench(P),
    "dresser": lambda P: fu.dresser(P),
    "fireplace": lambda P: fu.fireplace(P),
    "bar_counter": lambda P: fu.bar_counter(P),
}


def _fresh():
    geo.reset_scene()
    geo.clear_mat_cache()


def build_house(name, preview=True):
    t0 = time.time()
    _fresh()
    H = rooms.HOUSES[name]()
    S = H["shell"]
    shell_ob = S["mb"].build(name)
    furn_ob = H["mb"].build(name + "_furniture")
    tris_builder = S["mb"].tri_count() + H["mb"].tri_count()
    visual = [shell_ob, furn_ob]
    for d in S["doors"]:
        visual.append(d["ob"])
        tris_builder += d["tris"]
    for ob, tr in H["lamps"]:
        visual.append(ob)
        tris_builder += tr
    for o in H.get("extra", []):
        if o.type == "MESH" and not o.name.endswith("colonly"):
            visual.append(o)
    cols = collision_objs(S["cols"] + H["cols"])
    cols += S["convex"]
    for nm, boxes in H["nav"]:
        cols.append(multi_box_obj(f"{nm}-colonly", boxes))
    for nm, bm in H["ramps"]:
        cols.append(geo.obj_from_bm(f"{nm}-colonly", bm))
    cols += [o for o in H.get("extra", []) if o.name.endswith("colonly")]
    door_cols = [d["col"] for d in S["doors"]]
    empties = [geo.empty(nm, loc) for nm, loc in H["spots"]]
    empties += [geo.empty(nm, loc) for nm, loc in H.get("empties", [])]
    for c in cols + door_cols:
        c.hide_render = True
    path = os.path.join(ihelp.ENV_MODELS, f"{name}.glb")
    export_glb_path(path, visual + cols + door_cols + empties)
    strip_icc(path)
    info = geo.inspect_glb(path)
    print(f"[int] {name}: tris={info['tris']} (builder {tris_builder}) images={info['images']} size={info['size_mb']}MB "
          f"({time.time() - t0:.1f}s)")
    # doorway sweeps (Blender coords): from 1.2 m outside to 1.2 m inside through the door gap centre
    sweeps = []
    t = rooms.T_WALL
    for d in S["doors"]:
        F = S["faces"][d["face"]]
        g0, g1, gz = d["gap"]
        ac = (g0 + g1) / 2
        p_out, p_in = F.p(ac, 1.2, 0.0), F.p(ac, -t - 1.2, 0.0)
        sweeps.append(dict(name=d["name"], path=[tuple(p_out), tuple(p_in)], floor=rooms.FZ))
        print(f"[int]   {d['name']}: hinge (blender) {tuple(round(v, 3) for v in d['hinge'])} clear w={d['clear'][0]:.2f} "
              f"h={d['clear'][1]:.2f}")
    rep = check_glb.check(path, sweeps)
    print(f"[int]   storeys={H['storeys']} stairs={H.get('stairs')} ladder={H.get('ladder')}")
    if preview:
        pv = H["preview"]
        for o in cols + door_cols:
            o.hide_render = True
        geo.PREVIEW_DIR = ihelp.PREVIEW_DIR
        e = pv["ext"]
        geo.render_preview(name + "_ext", visual, elev=e["elev"], azim=e["azim"], dist_mul=e["dist_mul"],
                           ground="cobble", target=e["target"])
        for ob, _ in H["lamps"]:
            ob.visible_shadow = False
        lights = []
        for i, (nm, loc) in enumerate(H["spots"]):
            lights.append((f"PV_{nm}", loc, 70.0, (1.0, 0.6, 0.3), 0.04))
        if pv.get("hearth"):
            lights.append(("PV_hearth", pv["hearth"], 25.0, (1.0, 0.38, 0.12), 0.25))
        if pv.get("loft_light"):   # preview only: a carried lantern at the hatch
            lights.append(("PV_loft", pv["loft_light"], 60.0, (1.0, 0.6, 0.3), 0.05))
        for k, (cam, look) in enumerate(pv["shot_in"]):
            render.render_interior(f"{name}_in{k}", cam, look, lights)
        print(f"[int] {name}: previews done ({time.time() - t0:.1f}s)")
    return info, rep


def build_prop(name, preview=True):
    t0 = time.time()
    _fresh()
    mb = geo.MB()
    import random
    P = Put(mb, rng=random.Random(hash(name) & 0xFFFF))
    PROPS[name](P)
    ob = mb.build(name)
    cols = collision_objs(P.cols)
    for c in cols:
        c.hide_render = True
    path = os.path.join(ihelp.PROP_MODELS, f"{name}.glb")
    export_glb_path(path, [ob] + cols)
    strip_icc(path)
    info = geo.inspect_glb(path)
    print(f"[prop] {name}: tris={info['tris']} cols={[n for n in info['nodes'] if 'colonly' in n]} ({time.time() - t0:.1f}s)")
    if preview:
        geo.PREVIEW_DIR = ihelp.PREVIEW_DIR
        geo.render_preview("prop_" + name, [ob], elev=14.0, azim=-30.0, dist_mul=0.85, ground="cobble")
    return info


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    flags = {a for a in argv if a.startswith("--")}
    names = [a for a in argv if not a.startswith("--")]
    preview = "--no-preview" not in flags
    textures.ensure(None, force=False)
    itex.ensure(force="--force-tex" in flags)
    itex.install()
    targets = names or (list(rooms.HOUSES) + ["props"])
    summary = []
    for n in targets:
        if n in rooms.HOUSES:
            info, rep = build_house(n, preview)
            summary.append((n, info["tris"], rep["errors"]))
        elif n == "props":
            for p in PROPS:
                info = build_prop(p, preview)
                summary.append((p, info["tris"], []))
        elif n in PROPS:
            info = build_prop(n, preview)
            summary.append((n, info["tris"], []))
        else:
            raise SystemExit(f"unknown target {n}")
    print("[summary]")
    for n, tr, err in summary:
        print(f"  {n}: {tr} tris {'OK' if not err else err}")


if __name__ == "__main__":
    main()
