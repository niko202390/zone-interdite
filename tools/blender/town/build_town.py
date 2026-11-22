"""Zone Interdite - Plouzennec town landmarks, harbour and coastal-defence pieces.

Usage (from repo root):
  (hotel_de_la_plage_int is the enterable hotel: see hotel_int.py)
  "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" --background --factory-startup \
      --python-exit-code 1 --python tools/blender/town/build_town.py -- [names...] [--no-preview] [--force-tex]

No names = everything. Outputs game/assets/models/town/<name>.glb (each passed through
tools/glb_strip_icc.py) and dusk previews in tools/blender/town/previews/.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import common  # noqa: E402  (sets sys.path for env/ and interiors/)
import geo  # noqa: E402
import textures  # noqa: E402
import itex  # noqa: E402
import ttex  # noqa: E402
from ihelp import strip_icc  # noqa: E402

import importlib  # noqa: E402

ASSETS = {
    "hotel_de_la_plage": ("hotel", "build"),
    "hotel_de_la_plage_int": ("hotel_int", "build"),
    "church_plouzennec": ("church", "build"),
    "mairie": ("mairie", "build"),
    "quay_10m": ("harbour", "quay_10m"),
    "fishing_boat_a": ("harbour", "fishing_boat_a"),
    "dinghy": ("harbour", "dinghy"),
    "fish_hall": ("harbour", "fish_hall"),
    "bunker_atlantic": ("military", "bunker_atlantic"),
    "searchlight_60cm": ("military", "searchlight_60cm"),
    "wire_fence_5m": ("military", "wire_fence_5m"),
    "minefield_sign": ("military", "minefield_sign"),
    "watermill": ("rural", "watermill"),
    "soe_container": ("rural", "soe_container"),
}


def build_asset(name, preview=True):
    t0 = time.time()
    geo.reset_scene()
    geo.clear_mat_cache()
    mod, fn = ASSETS[name]
    res = getattr(importlib.import_module(mod), fn)()
    visual, cols, empties = res["visual"], res["cols"], res.get("empties", [])
    for c in cols:
        c.hide_render = True
    path = geo.export_glb(name, visual + cols + empties)
    strip_icc(path)
    info = geo.inspect_glb(path)
    print(f"[town] {name}: tris={info['tris']} (builder {res['tris']}) images={info['images']} embedded={info['embedded']} "
          f"size={info['size_mb']}MB blend={[k for k, v in info['alpha'].items() if v != 'OPAQUE']} ({time.time() - t0:.1f}s)")
    print(f"[town] {name}: nodes={[n for n in info['nodes'] if 'colonly' not in n]}")
    print(f"[town] {name}: collision={len([n for n in info['nodes'] if 'colonly' in n])} {res.get('note', '')}")
    if preview:
        for i, pv in enumerate(res["pv"]):
            pv = dict(pv)
            suffix = pv.pop("suffix", "" if i == 0 else f"_{i}")
            geo.render_preview(name + suffix, visual, **pv)
        if res.get("previews_in"):         # enterable buildings: lamplit interior shots
            res["previews_in"]()
        print(f"[town] {name}: previews written ({time.time() - t0:.1f}s)")
    return info


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    flags = {a for a in argv if a.startswith("--")}
    names = [a for a in argv if not a.startswith("--")] or list(ASSETS)
    textures.ensure(None, force=False)
    itex.ensure(force=False)
    ttex.ensure(force="--force-tex" in flags)
    common.setup()
    for n in names:
        if n not in ASSETS:
            raise SystemExit(f"unknown asset {n}; choose from {list(ASSETS)}")
        build_asset(n, preview="--no-preview" not in flags)


if __name__ == "__main__":
    main()
