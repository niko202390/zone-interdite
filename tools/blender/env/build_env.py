"""Zone Interdite - environment kit builder (Breton village, winter 1943-44).

Usage (from repo root):
  "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" --background --factory-startup \
      --python-exit-code 1 --python tools/blender/env/build_env.py -- [assets...] [--no-preview] [--force-tex]

With no asset names everything is rebuilt. Asset names: textures, ground, house_bourg, house_longere,
house_cafe, street_pave_10m, and the props listed in props.PROPS.
"""
import importlib
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import textures  # noqa: E402
import geo       # noqa: E402
import houses    # noqa: E402
import props     # noqa: E402
import street    # noqa: E402

HOUSES = ["house_bourg", "house_longere", "house_cafe"]
ALL = HOUSES + ["street_pave_10m"] + list(props.PROPS)


def build_asset(name, preview=True):
    t0 = time.time()
    geo.reset_scene()
    geo.clear_mat_cache()
    if name in HOUSES:
        visual, cols, tris = houses.build(name)
        empties = []
        pv = dict(elev=8.0, azim=-32.0, dist_mul=0.78, ground="cobble")
    elif name == "street_pave_10m":
        visual, cols, tris = street.build()
        empties = []
        pv = dict(elev=22.0, azim=-25.0, dist_mul=0.7, ground="mud")
    else:
        visual, cols, empties, tris, pv = props.build(name)
    for c in cols:
        c.hide_render = True
    path = geo.export_glb(name, visual + cols + empties)
    info = geo.inspect_glb(path)
    msg = (f"[asset] {name}: tris={info['tris']} (builder {tris}) images={info['images']} embedded={info['embedded']} "
           f"mime={info['mime']} size={info['size_mb']}MB nodes={len(info['nodes'])} "
           f"blend={[k for k, v in info['alpha'].items() if v != 'OPAQUE']} ({time.time() - t0:.1f}s)")
    print(msg)
    cnames = [n for n in info["nodes"] if "colonly" in n]
    print(f"[asset] {name}: collision nodes={cnames} empties={[n for n in info['nodes'] if n.startswith('WireAttach')]}")
    if preview:
        geo.render_preview(name, visual, **pv)
        if name in HOUSES:   # close-up of the ground floor to check decals / joinery
            geo.render_preview(name + "_detail", visual, elev=4.0, azim=-18.0, dist_mul=0.22, ground="cobble",
                               target=(0.6, -4.0, 1.5))
        print(f"[asset] {name}: preview written ({time.time() - t0:.1f}s)")
    return info


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    flags = {a for a in argv if a.startswith("--")}
    names = [a for a in argv if not a.startswith("--")]
    preview = "--no-preview" not in flags
    if not names or "textures" in names or "ground" in names or "--force-tex" in flags:
        sub = list(textures.GROUND) if names == ["ground"] else None
        textures.ensure(sub, force="--force-tex" in flags)
    else:
        textures.ensure(None, force=False)    # generate only what's missing
    targets = [n for n in names if n not in ("textures", "ground")] or (ALL if not names else [])
    for n in targets:
        if n not in ALL:
            raise SystemExit(f"unknown asset {n}; choose from {ALL}")
        build_asset(n, preview)


if __name__ == "__main__":
    main()
