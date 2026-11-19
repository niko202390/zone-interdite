"""
build_soldier.py -- German rifleman (occupied Brittany, February 1944), Feldgendarmerie variant and
the Kar98k rifle, generated from scratch: geometry, armature, skin weights, keyframed actions,
procedural materials baked to Principled image maps, glb export (+ ICC strip) and previews.

Run:
  "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" --background --factory-startup \
      --python-exit-code 1 --python tools/blender/characters/build_soldier.py -- [assets] [options]

Assets (default: all):  kar98k  rifleman  feldgendarm
Options:
  --res N          soldier texture size (default 4096; the rifle uses N/2)
  --no-bake        skip baking/export (fast rig + animation check with workbench previews)
  --no-previews    skip preview renders
  --samples N      Cycles preview samples (default 48)
  --cpu            force CPU Cycles

Outputs: game/assets/models/characters/soldier_<variant>.glb, game/assets/models/weapons/kar98k.glb
"""
import json
import os
import struct
import subprocess
import sys
import time

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import canims  # noqa: E402
import cbody  # noqa: E402
import cmats  # noqa: E402
import cpreview  # noqa: E402
import crig  # noqa: E402
from cgeo import V, tri_count  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CHAR_DIR = os.path.join(ROOT, "game", "assets", "models", "characters")
RIFLE_GLB = os.path.join(ROOT, "game", "assets", "models", "weapons", "kar98k.glb")
PREV = os.path.join(HERE, "previews")
TEX = os.path.join(HERE, "out", "tex")
STRIP = os.path.join(ROOT, "tools", "glb_strip_icc.py")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ASSETS = [a for a in argv if a in ("kar98k", "rifleman", "feldgendarm")] or ["kar98k", "rifleman", "feldgendarm"]


def _opt(n, d):
    return type(d)(argv[argv.index(n) + 1]) if n in argv else d


RES = _opt("--res", 4096)
SAMPLES = _opt("--samples", 48)
BAKE = "--no-bake" not in argv
PREVIEWS = "--no-previews" not in argv
CPU = "--cpu" in argv
QUICK = "--quick" in argv
T0 = time.time()


def log(*a):
    print(f"[soldier {time.time()-T0:7.1f}s]", *a, flush=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.world = bpy.data.worlds.new("World")
    bpy.context.scene.render.fps = crig.FPS


# ------------------------------------------------------------------------------------------ skinning
class MultiSource:
    def __init__(self, obs):
        self.srcs = [crig.WeightSource(o) for o in obs]

    def __call__(self, p):
        best = None
        for s in self.srcs:
            co, i, d = s.kd.find(p)
            if best is None or d < best[0]:
                best = (d, s)
        return best[1](p)


def skin_parts(parts, arm_ob):
    sk = crig.Skel(arm_ob)

    def torso_w(p):
        w = sk.spine_w(p.z, "Neck")
        ax = abs(p.x)
        Side = "Left" if p.x > 0 else "Right"
        f_cl = crig.sstep(0.05, 0.15, ax) * crig.sstep(1.37, 1.46, p.z) * 0.55
        f_ua = crig.sstep(0.15, 0.20, ax) * crig.sstep(1.30, 1.43, p.z) * 0.55
        b = max(0.1, 1 - f_cl - f_ua)
        return crig.mixw((b, w), (f_cl, {Side + "Shoulder": 1}), (f_ua, {Side + "UpperArm": 1}))

    def skirt_w(p, th):
        chains = [(35, "FrontL"), (95, "SideL"), (150, "BackL"), (210, "BackR"), (265, "SideR"), (325, "FrontR")]
        if th <= chains[0][0]:
            cw = {chains[0][1]: 1.0}
        elif th >= chains[-1][0]:
            cw = {chains[-1][1]: 1.0}
        else:
            cw = {}
            for (a0, n0), (a1, n1) in zip(chains, chains[1:]):
                if a0 <= th <= a1:
                    t = crig.ease((th - a0) / (a1 - a0))
                    cw = {n0: 1 - t, n1: t}
        z = p.z
        top = 1 - crig.sstep(0.92, 1.00, z)          # 1 below the hips
        lower = crig.sstep(0.74, 0.64, z)
        w = {}
        for nm, x in cw.items():
            w["Skirt" + nm + "1"] = x * top * (1 - lower)
            w["Skirt" + nm + "2"] = x * top * lower
        hips = 1 - top
        w["Hips"] = hips * (1 - crig.sstep(1.03, 1.07, z) * 0.4)
        w["Spine"] = hips * crig.sstep(1.03, 1.07, z) * 0.4
        return w

    def arm_w(p, side):
        Side = "Left" if side == "L" else "Right"
        w = sk.chain_w(p, [Side + "Shoulder", Side + "UpperArm", Side + "LowerArm", Side + "Hand"], [0.05, 0.05, 0.03])
        near = 1 - crig.sstep(0.13, 0.17, abs(p.x))
        return crig.mixw((1 - near * 0.4, w), (near * 0.4, {"UpperChest": 1}))

    def leg_w(p, side):
        Side = "Left" if side == "L" else "Right"
        return sk.chain_w(p, [Side + "UpperLeg", Side + "LowerLeg", Side + "Foot", Side + "Toes"], [0.05, 0.035, 0.02],
                          pre="Hips", pre_blend=0.05)

    def foot_w(p, side):
        Side = "Left" if side == "L" else "Right"
        ball = sk.seg[Side + "Toes"][0]
        fdir = (sk.seg[Side + "Foot"][1] - sk.seg[Side + "Foot"][0]).normalized()
        if p.z > 0.16:
            return sk.chain_w(p, [Side + "UpperLeg", Side + "LowerLeg"], [0.05])
        along = (p - ball).dot(V(0, -1, 0))
        toes = crig.sstep(-0.025, 0.015, along)
        shin = crig.sstep(0.10, 0.16, p.z)
        return {Side + "Toes": toes * (1 - shin), Side + "Foot": (1 - toes) * (1 - shin), Side + "LowerLeg": shin}

    def hand_w(p, side):
        Side = "Left" if side == "L" else "Right"
        F, d, n, ts = crig.hand_layout(side, crig.joints())
        wr = crig.joints()['wr' + side]
        best, bw = 1e9, None
        for f, pts in F.items():
            names = (["Metacarpal", "Proximal", "Distal"] if f == "Thumb" else ["Proximal", "Intermediate", "Distal"])
            chain = [f"{Side}{f}{x}" for x in names]
            # distance to the finger polyline
            dd = min(((p - a) - (b - a) * max(0, min(1, (p - a).dot(b - a) / (b - a).length_squared))).length
                     for a, b in zip(pts, pts[1:]))
            if dd < best:
                best, bw = dd, (chain, pts)
        along = (p - wr).dot(d)
        palm_w = {Side + "Hand": 1.0}
        if along < 0.01:
            k = crig.sstep(0.01, -0.03, along)
            palm_w = {Side + "Hand": 1 - k, Side + "LowerArm": k}
        if best < 0.016:
            chain, pts = bw
            fw = sk.chain_w(p, chain, [0.008, 0.006], pre=Side + "Hand", pre_blend=0.008)
            if "Thumb" in chain[0]:
                fw = sk.chain_w(p, chain, [0.012, 0.008], pre=Side + "Hand", pre_blend=0.012)
            # only if outside the palm body
            k_out = crig.sstep(0.084, 0.096, along) if "Thumb" not in chain[0] else 1.0
            return crig.mixw((k_out, fw), (1 - k_out, palm_w))
        return palm_w

    torso = [o for o in parts if o["skin"] == "torso"]
    skirt = [o for o in parts if o["skin"] == "skirt"]
    for o in torso:
        crig.apply_weights(o, torso_w)
    for o in skirt:
        at = o.data.attributes["sk_th"].data
        th = [a.value for a in at]
        me = o.data
        per = {}
        for v in me.vertices:
            w = crig.normalize_w(skirt_w(o.matrix_world @ v.co, th[v.index]))
            for b, x in w.items():
                per.setdefault(b, []).append((v.index, x))
        for b, lst in per.items():
            g = o.vertex_groups.new(name=b)
            for i, x in lst:
                g.add([i], x, 'REPLACE')
    src = MultiSource(torso + skirt)
    for o in parts:
        mode = o["skin"]
        side = o.get("side", "L")
        if mode in ("torso", "skirt"):
            continue
        if mode == "copy":
            crig.apply_weights(o, src)
        elif mode == "copy_rigid":
            crig.apply_weights(o, src, rigid=True)
        elif mode == "copy_rigid_each":
            # rigid per connected island (buttons, pouch cells)
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(o.data)
            bm.verts.ensure_lookup_table()
            seen = set()
            groups = {}
            for v in bm.verts:
                if v.index in seen:
                    continue
                stack, isl = [v], []
                seen.add(v.index)
                while stack:
                    q = stack.pop()
                    isl.append(q.index)
                    for e in q.link_edges:
                        u = e.other_vert(q)
                        if u.index not in seen:
                            seen.add(u.index)
                            stack.append(u)
                c = sum((bm.verts[i].co for i in isl), Vector()) / len(isl)
                w = crig.normalize_w(src(o.matrix_world @ c))
                for b, x in w.items():
                    groups.setdefault(b, []).append((isl, x))
            bm.free()
            for b, lst in groups.items():
                g = o.vertex_groups.get(b) or o.vertex_groups.new(name=b)
                for isl, x in lst:
                    g.add(isl, x, 'REPLACE')
        elif mode == "arm":
            crig.apply_weights(o, lambda p: arm_w(p, side))
        elif mode == "leg":
            crig.apply_weights(o, lambda p: leg_w(p, side))
        elif mode == "foot":
            crig.apply_weights(o, lambda p: foot_w(p, side))
        elif mode == "hand":
            crig.apply_weights(o, lambda p: hand_w(p, side))
        elif mode == "head":
            crig.apply_weights(o, lambda p: sk.spine_w(p.z, "Head"))
        elif mode == "rigid":
            g = o.vertex_groups.new(name=o["bone"])
            g.add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')


def join(parts, name):
    cmats.select_only(parts, parts[0])
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    for k in ("skin", "side", "bone"):
        if k in ob:
            del ob[k]
    return ob


# ------------------------------------------------------------------------------------------ animation
def author_actions(rig):
    acts = {}
    info = {}
    fr = canims.make_idle(rig)
    acts["Idle"] = crig.key_action(rig, "Idle", [p for p, o in fr], loop=True)
    info["Idle"] = max(o for p, o in fr)
    fr, T, v = canims.locomotion(rig, "Walk")
    acts["Walk"] = crig.key_action(rig, "Walk", [p for p, o in fr], loop=True)
    info["Walk"] = max(o for p, o in fr)
    fr, T, v = canims.locomotion(rig, "Run")
    acts["Run"] = crig.key_action(rig, "Run", [p for p, o in fr], loop=True)
    info["Run"] = max(o for p, o in fr)
    fr = canims.make_lookaround(rig)
    acts["LookAround"] = crig.key_action(rig, "LookAround", [p for p, o in fr])
    info["LookAround"] = max(o for p, o in fr)
    fr, R0 = canims.make_aim(rig)
    acts["AimRifle"] = crig.key_action(rig, "AimRifle", [p for p, o in fr], loop=True)
    info["AimRifle"] = max(o for p, o in fr)
    aim0 = fr[0][0]
    fr = canims.make_death(rig)
    acts["Death"] = crig.key_action(rig, "Death", [p for p, o in fr])
    info["Death"] = max(o for p, o in fr)
    for k, v in info.items():
        log(f"  action {k}: frames {int(acts[k].frame_range[1]) + 1}, max IK overreach {v*100:.1f} cm")
    rig.ob.animation_data.action = None
    return acts, aim0, R0


def add_empty(name, size=0.05):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.empty_display_type = 'ARROWS'
    e.empty_display_size = size
    return e


def make_sockets(rig, aim0, R0, torch_pos):
    arm = rig.ob
    E = {}

    def bone_parent(e, bone, M_bone_arm, desired):
        e.parent = arm
        e.parent_type = 'BONE'
        e.parent_bone = bone
        L = (M_bone_arm @ Matrix.Translation((0, rig.length[bone], 0))).inverted() @ desired
        e.matrix_parent_inverse = Matrix.Identity(4)
        e.matrix_basis = L
    e = add_empty("RifleSocket_Hands")
    bone_parent(e, "RightHand", aim0.mat("RightHand"), R0)
    E[e.name] = e
    # slung: muzzle up behind the right shoulder, sling side toward the body
    Y = V(0.06, 0.16, 1.0).normalized()
    Z = V(0.0, 1.0, -0.16)
    Z = (Z - Y * Z.dot(Y)).normalized()
    X = Y.cross(Z)
    M = Matrix.Identity(4)
    org = V(-0.235, 0.165, 1.10)
    for i in range(3):
        M[i][0], M[i][1], M[i][2], M[i][3] = X[i], Y[i], Z[i], org[i]
    e = add_empty("RifleSocket_Shoulder")
    bone_parent(e, "UpperChest", rig.rest["UpperChest"], M)
    E[e.name] = e
    e = add_empty("TorchMount", 0.03)
    bone_parent(e, "UpperChest", rig.rest["UpperChest"], Matrix.Translation(torch_pos))
    E[e.name] = e
    return E


# ------------------------------------------------------------------------------------------ export / verify
def strip_icc(path):
    py = os.path.join(os.path.dirname(bpy.app.binary_path), "%d.%d" % bpy.app.version[:2], "python", "bin", "python.exe")
    if not os.path.exists(py):
        py = sys.executable
    r = subprocess.run([py, STRIP, path], capture_output=True, text=True)
    log("strip_icc:", (r.stdout + r.stderr).strip().replace("\n", " | "))
    if r.returncode != 0:
        raise RuntimeError("glb_strip_icc failed")


def inspect_glb(path):
    with open(path, 'rb') as f:
        data = f.read()
    clen = struct.unpack_from('<I', data, 12)[0]
    js = json.loads(data[20:20 + clen])
    nodes = js['nodes']
    names = [n.get('name') for n in nodes]
    tris = 0
    for m in js.get('meshes', []):
        for p in m['primitives']:
            tris += js['accessors'][p['indices']]['count'] // 3
    anims = []
    for a in js.get('animations', []):
        tmax = 0.0
        for s in a['samplers']:
            acc = js['accessors'][s['input']]
            tmax = max(tmax, acc.get('max', [0])[0])
        anims.append((a['name'], round(tmax, 3)))
    skins = [(s.get('name'), len(s['joints'])) for s in js.get('skins', [])]
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get('children', []):
            parent[c] = i
    par_of = {names[i]: names[parent[i]] if i in parent else None for i in range(len(nodes))}
    imgs = [(im.get('name'), im.get('mimeType'), js['bufferViews'][im['bufferView']]['byteLength']) for im in js.get('images', [])]
    # JPEG ICC check
    icc = 0
    binstart = 20 + clen + 8
    for im in js.get('images', []):
        bv = js['bufferViews'][im['bufferView']]
        blob = data[binstart + bv.get('byteOffset', 0): binstart + bv.get('byteOffset', 0) + bv['byteLength']]
        if blob[:2] == b"\xff\xd8" and b"ICC_PROFILE" in blob[:65536]:
            icc += 1
    return dict(names=names, tris=tris, anims=anims, skins=skins, parent=par_of, images=imgs, size=len(data), icc=icc)


def export_glb(path, objs, animations):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cmats.select_only(objs, objs[0])
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_apply=True,
              export_image_format='JPEG', export_jpeg_quality=90, export_cameras=False, export_lights=False,
              export_yup=True, export_texcoords=True, export_normals=True, export_materials='EXPORT',
              export_extras=False)
    if animations:
        kw.update(export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
                  export_skins=True, export_morph=False, export_anim_slide_to_zero=True)
    else:
        kw.update(export_animations=False)
    bpy.ops.export_scene.gltf(**kw)
    strip_icc(path)


# ------------------------------------------------------------------------------------------ previews
def import_rifle_to(socket):
    if not os.path.exists(RIFLE_GLB):
        return []
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=RIFLE_GLB)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.parent is None:
            mw = o.matrix_world.copy()
            o.parent = socket
            o.matrix_parent_inverse = Matrix.Identity(4)
            o.matrix_basis = mw
    return new


def set_action(arm, act, frame):
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    bpy.context.scene.frame_set(int(frame))


def anim_sheet(tag, arm, acts, body):
    files = []
    rows = [("Idle", [0, 30, 60, 90], (2.6, -3.4, 1.3)), ("Walk", [0, 7, 15, 22], (3.6, -0.6, 1.1)),
            ("Run", [0, 5, 11, 16], (3.6, -0.6, 1.1)), ("LookAround", [0, 50, 80, 140], (1.2, -3.6, 1.4)),
            ("AimRifle", [0, 45, 0, 0], (2.0, -2.6, 1.5)), ("Death", [8, 20, 30, 70], (3.8, -1.2, 1.2))]
    for nm, fs, cam in rows:
        for k, f in enumerate(fs):
            set_action(arm, acts[nm], f)
            c = cam
            if nm == "AimRifle" and k == 2:
                c = (-2.4, -1.6, 1.6)
            if nm == "AimRifle" and k == 3:
                c = (0.25, -2.6, 1.6)
            p = os.path.join(PREV, f"_tmp_{nm}_{k}.png")
            cpreview.render_workbench(p, c, (0, 0.15 if nm == "Death" else 0, 0.9 if nm != "Death" else 0.35),
                                      (360, 450), 40, color='TEXTURE' if BAKE else 'MATERIAL')
            files.append(p)
    cpreview.contact_sheet(os.path.join(PREV, f"{tag}_anim_sheet.png"), 4, files, 360, 450)


def foot_slide_report(arm, body, acts):
    """Measure the speed of the lowest boot-sole points during stance (should match the gait speed)."""
    dg = bpy.context.evaluated_depsgraph_get()
    me0 = body.data
    sole = [v.index for v in me0.vertices if v.co.z < 0.004 and abs(v.co.y) < 0.2]
    for nm, spd in (("Walk", 1.3), ("Run", 4.0)):
        act = acts[nm]
        n = int(act.frame_range[1])
        speeds = []
        prev = None
        for f in range(n + 1):
            set_action(arm, act, f)
            ev = body.evaluated_get(dg)
            m = ev.to_mesh()
            pts = [m.vertices[i].co.copy() for i in sole]
            ev.to_mesh_clear()
            low = [p for p in pts if p.z < 0.008]
            if prev is not None and low:
                # mean y velocity of ground-contact points (same vertex indices)
                vs = []
                for i, p in enumerate(pts):
                    if p.z < 0.008 and prev[i].z < 0.008:
                        vs.append((p.y - prev[i].y) * crig.FPS)
                if vs:
                    speeds.append(sum(vs) / len(vs))
            prev = pts
        if speeds:
            log(f"  {nm}: contact-point speed {sum(speeds)/len(speeds):.2f} m/s (target {spd}), "
                f"min {min(speeds):.2f} max {max(speeds):.2f}")


def death_floor_check(arm, body, acts):
    dg = bpy.context.evaluated_depsgraph_get()
    act = acts["Death"]
    for f in (40, 50, int(act.frame_range[1])):
        set_action(arm, act, f)
        ev = body.evaluated_get(dg)
        m = ev.to_mesh()
        zs = sorted((v.co.z, v.index) for v in m.vertices)
        low = m.vertices[zs[0][1]].co.copy()
        ev.to_mesh_clear()
        mats = {}
        for p in body.data.polygons:
            for vi in p.vertices:
                if vi == zs[0][1]:
                    mats[body.data.materials[p.material_index].name] = 1
        below = [i for z, i in zs if z < -0.01]
        log(f"  Death frame {f}: lowest vertex z = {zs[0][0]*100:.1f} cm at {tuple(round(x,2) for x in low)} "
            f"({list(mats)}), {len(below)} verts below -1 cm, 1% = {zs[len(zs)//100][0]*100:.1f} cm")


# ------------------------------------------------------------------------------------------ soldier
def build_soldier(variant):
    reset()
    log(f"=== soldier {variant}")
    M = cmats.build_soldier_mats(variant)
    parts, torch_pos = cbody.build_all(M, variant)
    log(f"  parts: {len(parts)}  tris: {sum(tri_count(p) for p in parts)}")
    arm = crig.build_armature("Armature")
    skin_parts(parts, arm)
    body = join(parts, "Soldier_" + variant)
    log(f"  joined: {tri_count(body)} tris, {len(body.data.vertices)} verts, groups {len(body.vertex_groups)}")
    rig = crig.Rig(arm)
    if BAKE:
        used = {m.name for m in body.data.materials}
        cmats.unwrap_pack(body, None, {'wool_coat_in': 0.3, 'helmet_in': 0.45, 'sole': 0.6, 'steel': 0.6})
        infos = [M[k] for k in M if M[k]['mat'].name in used]
        imgs = cmats.bake_atlas([body], infos, f"soldier_{variant}", RES, ['color', 'rough', 'metal', 'normal', 'ao'],
                                TEX, ao_samples=48, force_cpu=CPU)
        cmats.combine_ao(imgs['color'], imgs['ao'], 0.7)
        fm = cmats.final_material(f"Soldier_{variant}", imgs)
        cmats.replace_materials([body], fm)
        for a in ("edge_d", "rim", "sk_th"):
            if a in body.data.attributes:
                body.data.attributes.remove(body.data.attributes[a])
    body.parent = arm
    md = body.modifiers.new("Armature", 'ARMATURE')
    md.object = arm
    acts, aim0, R0 = author_actions(rig)
    E = make_sockets(rig, aim0, R0, torch_pos)
    foot_slide_report(arm, body, acts)
    death_floor_check(arm, body, acts)
    set_action(arm, acts["Idle"], 0)
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    out = os.path.join(CHAR_DIR, f"soldier_{variant}.glb")
    if BAKE:
        export_glb(out, [arm, body] + list(E.values()), True)
        info = inspect_glb(out)
        log(f"  GLB {os.path.basename(out)}: {info['size']/1e6:.1f} MB, tris {info['tris']}, skins {info['skins']}, "
            f"ICC left {info['icc']}")
        log(f"  animations: {info['anims']}")
        for nm in E:
            log(f"  empty {nm}: present={nm in info['names']} parent={info['parent'].get(nm)}")
        log(f"  images: {info['images']}")
    if PREVIEWS:
        os.makedirs(PREV, exist_ok=True)
        rifle_objs = import_rifle_to(E["RifleSocket_Shoulder"])
        set_action(arm, acts["Idle"], 0)
        if not QUICK:
            render_beauty(variant, E, rifle_objs, arm, acts)
        anim_sheet(variant, arm, acts, body)
    log(f"=== {variant} done")


def render_beauty(variant, E, rifle_objs, arm, acts):
    if True:
        cpreview.render_dusk(f"{variant}_idle", PREV, SAMPLES)
        cpreview.render_dusk(f"{variant}_close", PREV, SAMPLES, views=[
            ("head", (0.75, -1.25, 1.62), (0, 0, 1.45), 60), ("belt", (0.6, -1.3, 1.1), (0, 0, 1.05), 55),
            ("backkit", (-0.9, 1.3, 1.1), (0, 0, 0.98), 50)], res=(1200, 1000))
        for o in rifle_objs:
            o.parent = E["RifleSocket_Hands"]
            o.matrix_parent_inverse = Matrix.Identity(4)
        set_action(arm, acts["AimRifle"], 0)
        cpreview.render_dusk(f"{variant}_aim", PREV, SAMPLES, views=[
            ("aim34", (2.0, -2.8, 1.6), (0, -0.2, 1.2), 50), ("aimside", (-3.2, -0.3, 1.5), (0, -0.2, 1.2), 50),
            ("aimback", (-1.4, 2.6, 1.8), (0, -0.2, 1.3), 50)], res=(1200, 1000))
        set_action(arm, acts["Idle"], 0)
        for o in rifle_objs:
            o.parent = E["RifleSocket_Shoulder"]
            o.matrix_parent_inverse = Matrix.Identity(4)


def main():
    for a in ASSETS:
        if a == "kar98k":
            import ckar98k
            reset()
            ckar98k.build(RIFLE_GLB, max(1024, RES // 2), BAKE, PREVIEWS, SAMPLES, PREV, TEX, CPU,
                          export_glb, inspect_glb, log)
        else:
            build_soldier(a)
    log("all done")


main()
