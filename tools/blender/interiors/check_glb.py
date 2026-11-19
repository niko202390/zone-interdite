"""Parse an exported .glb and verify the enterable-house contract (pure Python + numpy, so it runs
inside Blender or with Blender's bundled python):

  - required nodes exist (Door with child Door_col-colonly, Lamp_*, LightSpot_*, NavFloor_*-colonly)
  - a 0.6 m x 1.8 m player box can be swept through each doorway with the door swung open 90 deg
    (rotation +90 deg about Godot +Y around the Door origin) without touching any collision triangle
  - triangle count of render meshes

Usage: python check_glb.py file.glb [door paths json]
"""
import json
import math
import struct
import sys

import numpy as np


def load(path):
    data = open(path, "rb").read()
    off = 12
    js, binc = None, b""
    while off < len(data):
        clen, ctype = struct.unpack_from("<II", data, off)
        chunk = data[off + 8:off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk)
        elif ctype == 0x004E4942:
            binc = chunk
        off += 8 + clen
    return js, binc


def _accessor(js, binc, idx):
    acc = js["accessors"][idx]
    bv = js["bufferViews"][acc["bufferView"]]
    comp = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}[acc["componentType"]]
    ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[acc["type"]]
    start = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = bv.get("byteStride", 0)
    n = acc["count"]
    if stride and stride != ncomp * np.dtype(comp).itemsize:
        raw = np.frombuffer(binc, np.uint8, count=stride * n, offset=start).reshape(n, stride)
        arr = raw[:, :ncomp * np.dtype(comp).itemsize].copy().view(comp).reshape(n, ncomp)
    else:
        arr = np.frombuffer(binc, comp, count=n * ncomp, offset=start).reshape(n, ncomp)
    return arr


def _local(node):
    if "matrix" in node:
        return np.array(node["matrix"], float).reshape(4, 4).T
    t = node.get("translation", [0, 0, 0])
    r = node.get("rotation", [0, 0, 0, 1])
    s = node.get("scale", [1, 1, 1])
    x, y, z, w = r
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4)
    M[:3, :3] = R * np.array(s)[None, :]
    M[:3, 3] = t
    return M


def world_mats(js):
    nodes = js["nodes"]
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i
    cache = {}

    def wm(i):
        if i not in cache:
            M = _local(nodes[i])
            cache[i] = (wm(parent[i]) @ M) if i in parent else M
        return cache[i]
    return [wm(i) for i in range(len(nodes))], parent


def mesh_tris(js, binc, mi):
    out = []
    for prim in js["meshes"][mi]["primitives"]:
        pos = _accessor(js, binc, prim["attributes"]["POSITION"]).astype(float)
        if "indices" in prim:
            idx = _accessor(js, binc, prim["indices"]).astype(np.int64).reshape(-1, 3)
        else:
            idx = np.arange(len(pos)).reshape(-1, 3)
        out.append(pos[idx])
    return np.concatenate(out) if out else np.zeros((0, 3, 3))


def tri_box_overlap(tris, c, h):
    """Vectorised Akenine-Moller triangle/AABB SAT. tris (N,3,3), box centre c, half extents h."""
    v = tris - c[None, None, :]
    e = [v[:, 1] - v[:, 0], v[:, 2] - v[:, 1], v[:, 0] - v[:, 2]]
    ok = np.ones(len(tris), bool)
    for i in range(3):                               # box face normals
        mn, mx = v[:, :, i].min(1), v[:, :, i].max(1)
        ok &= (mn <= h[i]) & (mx >= -h[i])
    n = np.cross(e[0], e[1])                         # triangle normal
    d = np.einsum("ij,ij->i", n, v[:, 0])
    r = np.abs(n) @ h
    ok &= np.abs(d) <= r
    axes = np.eye(3)
    for ei in e:                                      # 9 edge cross axes
        for a in axes:
            ax = np.cross(np.broadcast_to(a, ei.shape), ei)
            p = np.einsum("nkj,nj->nk", v, ax)
            rr = np.abs(ax) @ h
            ok &= ~((p.min(1) > rr) | (p.max(1) < -rr))
    return ok


def check(path, doors=(), verbose=True):
    """doors: list of dict(name, path=[(x,y,z) Blender coords...], floor=z) to sweep."""
    js, binc = load(path)
    nodes = js["nodes"]
    names = [n.get("name", "") for n in nodes]
    W, parent = world_mats(js)
    rep = {"nodes": names, "errors": []}
    tris = 0
    for i, n in enumerate(nodes):
        if "mesh" in n and "colonly" not in n["name"]:
            for prim in js["meshes"][n["mesh"]]["primitives"]:
                tris += js["accessors"][prim["indices"]]["count"] // 3
    rep["tris"] = tris
    col = [i for i, nm in enumerate(names) if nm.endswith(("-colonly", "-convcolonly")) and "mesh" in nodes[i]]
    rep["collision"] = [names[i] for i in col]
    for req in ("Door", "Door_col-colonly", "Lamp_0", "LightSpot_0", "NavFloor_0-colonly"):
        if req not in names:
            rep["errors"].append(f"missing node {req}")
    if "Door_col-colonly" in names and "Door" in names:
        if parent.get(names.index("Door_col-colonly")) != names.index("Door"):
            rep["errors"].append("Door_col-colonly is not a child of Door")
    rep["hinges"] = {}
    for dn in ("Door", "BackDoor"):
        if dn in names:
            M = W[names.index(dn)]
            g = M[:3, 3]
            rep["hinges"][dn] = dict(godot=tuple(round(float(x), 3) for x in g),
                                     blender=(round(float(g[0]), 3), round(float(-g[2]), 3), round(float(g[1]), 3)))
    # world triangles of static collision, plus door colliders swung open
    static = []
    door_cols = {}
    for i in col:
        T = mesh_tris(js, binc, nodes[i]["mesh"])
        p = parent.get(i)
        if p is not None and names[p] in ("Door", "BackDoor"):
            Pm = W[p]
            ang = math.radians(90.0)
            Ry = np.array([[math.cos(ang), 0, math.sin(ang), 0], [0, 1, 0, 0], [-math.sin(ang), 0, math.cos(ang), 0], [0, 0, 0, 1]])
            M = Pm @ Ry @ np.linalg.inv(Pm) @ W[i]
            door_cols[names[p]] = (M, T)
        else:
            M = W[i]
        Th = np.concatenate([T, np.ones(T.shape[:2] + (1,))], axis=2) @ M.T
        static.append((names[i], Th[:, :, :3]))
    for dname, (M, T) in door_cols.items():
        pass
    rep["sweeps"] = {}
    for d in doors:
        hits = set()
        pts = [np.array((x, z, -y), float) for (x, y, z) in d["path"]]
        floor = d["floor"]
        half = np.array((0.3, 0.9, 0.3))
        for k in range(len(pts) - 1):
            a, b = pts[k], pts[k + 1]
            n = max(2, int(np.linalg.norm(b - a) / 0.04))
            for s in np.linspace(0, 1, n):
                p = a + (b - a) * s
                c = np.array((p[0], floor + 0.06 + 0.9, p[2]))
                for nm, Tw in static:
                    if nm.startswith("NavFloor") or nm.startswith("Step"):
                        # floors are under the box by construction; still test them
                        pass
                    if tri_box_overlap(Tw, c, half).any():
                        hits.add(nm)
        rep["sweeps"][d["name"]] = sorted(hits)
        if hits:
            rep["errors"].append(f"doorway {d['name']} blocked by {sorted(hits)}")
    if verbose:
        print(f"[check] {path}: tris={tris} errors={rep['errors']}")
        print(f"[check]   hinges={rep['hinges']}")
        print(f"[check]   sweeps={rep['sweeps']}")
    return rep


if __name__ == "__main__":
    doors = json.loads(open(sys.argv[2]).read()) if len(sys.argv) > 2 else []
    check(sys.argv[1], doors)
