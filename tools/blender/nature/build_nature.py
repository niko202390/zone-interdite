"""Zone Interdite - nature & vegetation kit builder (Breton bocage, February 1944).

Usage (from repo root):
  "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" --background --factory-startup \
      --python-exit-code 1 --python tools/blender/nature/build_nature.py -- [assets...] [--no-preview] [--force-tex]

With no asset names everything is rebuilt. Group names: trees, bushes, ground, rocks, water, talus.
Outputs game/assets/models/nature/<name>.glb (ICC-stripped), previews in tools/blender/nature/previews/.
"""
import importlib
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import ntex    # noqa: E402
import nlib    # noqa: E402
import trees   # noqa: E402
import plants  # noqa: E402
import land    # noqa: E402

GROUPS = {
    "trees": list(trees.SPECIES),
    "bushes": list(plants.BUSHES),
    "ground": list(plants.GROUND),
    "rocks": list(land.ROCKS),
    "talus": list(land.TALUS),
    "water": list(land.WATER) + list(plants.WATER),
}
ALL = [n for g in GROUPS.values() for n in g]
BUDGET = {"trees": 45000, "bushes": 8000, "ground": 300, "rocks": 6000, "talus": 40000, "water": 20000}


def group_of(name):
    for g, names in GROUPS.items():
        if name in names:
            return g
    raise KeyError(name)


def build_asset(name, preview=True):
    t0 = time.time()
    nlib.reset()
    g = group_of(name)
    mod = trees if g == "trees" else plants if name in plants.ALL else land
    vis, cols, stats, pv = mod.build(name)
    for c in cols:
        c.hide_render = True
    path = nlib.export(name, vis + cols)
    info = nlib.geo.inspect_glb(path)
    am = nlib.alpha_info(path)
    over = " OVER BUDGET!" if info["tris"] > BUDGET[g] else ""
    print(f"[asset] {name}: tris={info['tris']} (budget {BUDGET[g]}){over} {stats} images={info['images']} "
          f"mime={info['mime']} size={info['size_mb']}MB ({time.time() - t0:.1f}s)")
    print(f"[asset] {name}: materials={am} collision={[n for n in info['nodes'] if 'colonly' in n]}")
    if preview:
        pvs = pv if isinstance(pv, list) else [pv]
        for k, p in enumerate(pvs):
            p = dict(p)
            suffix = p.pop("suffix", "" if k == 0 else f"_{k}")
            nlib.preview(name + suffix, vis, **p)
    return info


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    flags = {a for a in argv if a.startswith("--")}
    names = [a for a in argv if not a.startswith("--")]
    ntex.ensure(None, force="--force-tex" in flags)
    targets = []
    for n in names or ALL:
        targets += GROUPS.get(n, [n])
    for n in targets:
        if n not in ALL:
            raise SystemExit(f"unknown asset {n}; choose from {ALL} or groups {list(GROUPS)}")
    for n in targets:
        build_asset(n, "--no-preview" not in flags)


if __name__ == "__main__":
    main()
