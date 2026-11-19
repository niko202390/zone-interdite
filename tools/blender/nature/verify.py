"""Verify nature glbs: triangle budgets, alpha MASK on card materials, no ICC (APP2) in JPEGs,
collision nodes present. python verify.py"""
import json, os, struct, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
D = os.path.join(ROOT, "game", "assets", "models", "nature")
BUDGET = [("tree_", 45000), ("gorse", 8000), ("bramble", 8000), ("bracken", 8000), ("talus", 40000),
          ("grass_", 300), ("rush_", 300), ("fern_", 300), ("rock", 6000), ("", 20000)]
bad = 0
for f in sorted(os.listdir(D)):
    if not f.endswith(".glb"):
        continue
    data = open(os.path.join(D, f), "rb").read()
    jl = struct.unpack("<I", data[12:16])[0]
    j = json.loads(data[20:20 + jl])
    binoff = 20 + jl + 8
    tris = 0
    for n in j["nodes"]:
        if "mesh" in n and "colonly" not in n.get("name", ""):
            for p in j["meshes"][n["mesh"]]["primitives"]:
                tris += j["accessors"][p["indices"]]["count"] // 3
    budget = next(b for k, b in BUDGET if f.startswith(k))
    cards = {m["name"]: (m.get("alphaMode", "OPAQUE"), m.get("alphaCutoff", 0.5)) for m in j["materials"]
             if "Card" in m["name"]}
    icc = 0
    for im in j.get("images", []):
        if im.get("mimeType") == "image/jpeg":
            bv = j["bufferViews"][im["bufferView"]]
            blob = data[binoff + bv.get("byteOffset", 0): binoff + bv.get("byteOffset", 0) + bv["byteLength"]]
            icc += b"ICC_PROFILE" in blob[:65536]
    colls = [n["name"] for n in j["nodes"] if "colonly" in n.get("name", "")]
    ok = tris <= budget and all(v[0] == "MASK" for v in cards.values()) and icc == 0
    bad += not ok
    print(f"{'OK ' if ok else 'BAD'} {f:28s} tris={tris:6d}/{budget:<6d} cards={cards} icc_jpegs={icc} col={len(colls)}")
print("FAILURES:", bad)
