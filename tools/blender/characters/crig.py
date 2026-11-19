"""Humanoid armature, skin weighting and procedurally authored animation for the soldier.

Blender space: Z up, character faces -Y, his left is +X. Bone names follow Godot's
SkeletonProfileHumanoid so retargeting maps automatically; the greatcoat skirt has six two-bone
chains (Skirt<Pos>1/2). Animations are computed per frame with our own FK + analytic two-bone IK in
armature space, then written as quaternion keys (Hips also gets location). Walk/Run are in place:
planted feet travel backward at exactly the locomotion speed, so there is no foot slide when the
game moves the root at that speed.
"""
import math
from math import acos, cos, pi, radians, sin, sqrt

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector
from mathutils.kdtree import KDTree

from cgeo import V, link, sstep, lerp

FPS = 30

# ------------------------------------------------------------------------------------------ layout
ARM_DOWN = radians(50.0)          # A-pose: upper arm 50 deg below horizontal
UA_LEN, FA_LEN = 0.295, 0.255
SH_JOINT = V(0.180, 0.012, 1.437)  # left glenohumeral joint
HIP_J = V(0.088, 0.0, 0.935)
KNEE = V(0.094, -0.014, 0.515)
ANKLE = V(0.098, 0.010, 0.095)
BALL = V(0.100, -0.122, 0.026)
TOE = V(0.100, -0.205, 0.022)
HEEL_GROUND = V(0.098, 0.085, 0.0)
BALL_GROUND = V(0.100, -0.122, 0.0)

SKIRT_ANG = {"FrontL": 35, "SideL": 95, "BackL": 150, "BackR": 210, "SideR": 265, "FrontR": 325}
SKIRT_Z0, SKIRT_Z1, SKIRT_Z2 = 1.000, 0.700, 0.380


def arm_dirs(side):
    s = 1 if side == "L" else -1
    d_ua = V(s * cos(ARM_DOWN), 0.0, -sin(ARM_DOWN))
    d_fa = V(s * cos(ARM_DOWN), -0.10, -sin(ARM_DOWN)).normalized()
    palm = V(-s * sin(ARM_DOWN), 0.0, -cos(ARM_DOWN))
    return d_ua, d_fa, palm


def joints():
    """All joint positions (left side computed, right mirrored)."""
    J = {}
    J['hips'] = V(0, 0.0, 0.98)
    J['spine'] = V(0, 0.0, 1.08)
    J['chest'] = V(0, -0.004, 1.20)
    J['uchest'] = V(0, -0.004, 1.33)
    J['neck'] = V(0, 0.002, 1.475)
    J['head'] = V(0, -0.008, 1.585)
    J['head_top'] = V(0, -0.008, 1.775)
    for side, s in (("L", 1), ("R", -1)):
        m = lambda p: V(p.x * s, p.y, p.z)
        d_ua, d_fa, palm = arm_dirs(side)
        sh = m(SH_JOINT)
        el = sh + d_ua * UA_LEN + V(0, 0.012, 0)
        wr = el + d_fa * FA_LEN
        J['clav' + side] = V(0.025 * s, -0.012, 1.430)
        J['sh' + side] = sh
        J['el' + side] = el
        J['wr' + side] = wr
        J['palm' + side] = palm
        J['hand_dir' + side] = d_fa
        J['hip' + side] = m(HIP_J)
        J['knee' + side] = m(KNEE)
        J['ankle' + side] = m(ANKLE)
        J['ball' + side] = m(BALL)
        J['toe' + side] = m(TOE)
    return J


def hand_layout(side, J):
    """Finger joint chains for one hand: dict finger -> list of points, plus hand frame."""
    s = 1 if side == "L" else -1
    w = J['wr' + side]
    d = J['hand_dir' + side]
    n = J['palm' + side]
    thumb_side = (V(0, -1, 0) - d * V(0, -1, 0).dot(d)).normalized()   # thumb points forward in A-pose
    k_base = w + d * 0.090
    F = {}
    spec = {"Index": (0.026, 0.0, (0.044, 0.026, 0.020)),
            "Middle": (0.008, 0.002, (0.048, 0.029, 0.021)),
            "Ring": (-0.010, -0.002, (0.045, 0.027, 0.020)),
            "Little": (-0.027, -0.010, (0.034, 0.021, 0.018))}
    for f, (off, along, lens) in spec.items():
        p0 = k_base + thumb_side * off + d * along - n * 0.002
        pts = [p0]
        for L in lens:
            pts.append(pts[-1] + d * L)
        F[f] = pts
    t0 = w + d * 0.022 + thumb_side * 0.020 + n * 0.012
    td = (d * 0.62 + thumb_side * 0.62 + n * 0.30).normalized()
    F["Thumb"] = [t0, t0 + td * 0.042, t0 + td * 0.077, t0 + td * 0.104]
    return F, d, n, thumb_side


def bone_list():
    """(name, head, tail, parent, z_axis_hint)"""
    J = joints()
    B = []
    fwd = V(0, -1, 0)
    B.append(("Hips", J['hips'], J['spine'], None, fwd))
    B.append(("Spine", J['spine'], J['chest'], "Hips", fwd))
    B.append(("Chest", J['chest'], J['uchest'], "Spine", fwd))
    B.append(("UpperChest", J['uchest'], J['neck'], "Chest", fwd))
    B.append(("Neck", J['neck'], J['head'], "UpperChest", fwd))
    B.append(("Head", J['head'], J['head_top'], "Neck", fwd))
    for side, Side in (("L", "Left"), ("R", "Right")):
        B.append((Side + "Shoulder", J['clav' + side], J['sh' + side], "UpperChest", fwd))
        B.append((Side + "UpperArm", J['sh' + side], J['el' + side], Side + "Shoulder", fwd))
        B.append((Side + "LowerArm", J['el' + side], J['wr' + side], Side + "UpperArm", fwd))
        F, d, n, ts = hand_layout(side, J)
        knuck = J['wr' + side] + d * 0.090
        B.append((Side + "Hand", J['wr' + side], knuck, Side + "LowerArm", n))
        for f, pts in F.items():
            names = (["Metacarpal", "Proximal", "Distal"] if f == "Thumb" else ["Proximal", "Intermediate", "Distal"])
            par = Side + "Hand"
            for k in range(3):
                nm = f"{Side}{f}{names[k]}"
                B.append((nm, pts[k], pts[k + 1], par, n))
                par = nm
        B.append((Side + "UpperLeg", J['hip' + side], J['knee' + side], "Hips", V(0, 1, 0)))
        B.append((Side + "LowerLeg", J['knee' + side], J['ankle' + side], Side + "UpperLeg", V(0, 1, 0)))
        B.append((Side + "Foot", J['ankle' + side], J['ball' + side], Side + "LowerLeg", V(0, 0, -1)))
        B.append((Side + "Toes", J['ball' + side], J['toe' + side], Side + "Foot", V(0, 0, -1)))
    for nm, ang in SKIRT_ANG.items():
        a = radians(ang)
        r = V(sin(a), -cos(a), 0)
        p0 = V(0, 0, SKIRT_Z0) + r * 0.150
        p1 = V(0, 0, SKIRT_Z1) + r * 0.195
        p2 = V(0, 0, SKIRT_Z2) + r * 0.225
        B.append(("Skirt" + nm + "1", p0, p1, "Hips", r))
        B.append(("Skirt" + nm + "2", p1, p2, "Skirt" + nm + "1", r))
    return B


def build_armature(name="Armature"):
    arm = bpy.data.armatures.new(name)
    ob = link(bpy.data.objects.new(name, arm))
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.view_layer.objects:
        o.select_set(o == ob)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = {}
    for nm, h, t, par, zh in bone_list():
        b = arm.edit_bones.new(nm)
        b.head, b.tail = h, t
        b.align_roll(zh)
        if par:
            b.parent = eb[par]
            b.use_connect = (eb[par].tail - b.head).length < 1e-5
        eb[nm] = b
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in ob.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    arm.display_type = 'STICK'
    return ob


# ------------------------------------------------------------------------------------------ skinning
SPINE = ["Hips", "Spine", "Chest", "UpperChest", "Neck", "Head"]


class Skel:
    """Rest-pose bone segments for weighting."""

    def __init__(self, arm_ob):
        self.seg = {}
        for b in arm_ob.data.bones:
            self.seg[b.name] = (b.head_local.copy(), b.tail_local.copy())

    def chain_w(self, p, chain, blends, pre=None, pre_blend=0.0):
        """Weights from projecting p onto the polyline made of the chain's bones.
        blends[i] = half-width of the blend at the joint between chain[i] and chain[i+1].
        pre: optional bone that takes the region before the chain start (blend pre_blend)."""
        pts = [self.seg[chain[0]][0]] + [self.seg[b][1] for b in chain]
        L = [0.0]
        for i in range(1, len(pts)):
            L.append(L[-1] + (pts[i] - pts[i - 1]).length)
        best, bs = 1e9, 0.0
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            ab = b - a
            t = max(-0.5 if i == 0 else 0.0, min(1.5 if i == len(pts) - 2 else 1.0, (p - a).dot(ab) / ab.length_squared))
            d = (a + ab * t - p).length
            if d < best:
                best, bs = d, L[i] + t * ab.length
        w = {}
        # piecewise: bone i owns [L[i], L[i+1]] with smooth blends at the joints
        for i, bn in enumerate(chain):
            lo = sstep(L[i] - blends[i - 1], L[i] + blends[i - 1], bs) if i > 0 else 1.0
            hi = 1.0 - sstep(L[i + 1] - blends[i], L[i + 1] + blends[i], bs) if i < len(chain) - 1 else 1.0
            v = lo * hi
            if v > 1e-4:
                w[bn] = w.get(bn, 0.0) + v
        if pre and pre_blend > 0:
            k = 1.0 - sstep(-pre_blend, pre_blend, bs)
            if k > 1e-4:
                w = {b: x * (1 - k) for b, x in w.items()}
                w[pre] = w.get(pre, 0.0) + k
        return w

    def spine_w(self, z, upto="Neck"):
        chain = SPINE[:SPINE.index(upto) + 1]
        zs = [self.seg[b][0].z for b in chain] + [self.seg[chain[-1]][1].z]
        w = {}
        bl = 0.05
        for i, bn in enumerate(chain):
            lo = sstep(zs[i] - bl, zs[i] + bl, z) if i > 0 else 1.0
            hi = 1.0 - sstep(zs[i + 1] - bl, zs[i + 1] + bl, z) if i < len(chain) - 1 else 1.0
            if lo * hi > 1e-4:
                w[bn] = lo * hi
        return w


def normalize_w(w, k=4):
    items = sorted(((b, x) for b, x in w.items() if x > 1e-4), key=lambda q: -q[1])[:k]
    s = sum(x for _, x in items) or 1.0
    return {b: x / s for b, x in items}


def mixw(*pairs):
    out = {}
    for f, w in pairs:
        for b, x in w.items():
            out[b] = out.get(b, 0.0) + f * x
    return out


def apply_weights(ob, fn, rigid=False):
    """fn(p_world) -> weight dict. rigid: evaluate once at the bounding-box centre."""
    me = ob.data
    groups = {}
    if rigid:
        c = sum((v.co for v in me.vertices), Vector()) / max(1, len(me.vertices))
        w = normalize_w(fn(ob.matrix_world @ c))
        for b, x in w.items():
            g = ob.vertex_groups.get(b) or ob.vertex_groups.new(name=b)
            g.add(list(range(len(me.vertices))), x, 'REPLACE')
        return
    per = {}
    for v in me.vertices:
        w = normalize_w(fn(ob.matrix_world @ v.co))
        for b, x in w.items():
            per.setdefault(b, {}).setdefault(round(x, 4), []).append(v.index)
    for b, d in per.items():
        g = ob.vertex_groups.get(b) or ob.vertex_groups.new(name=b)
        for x, idx in d.items():
            g.add(idx, x, 'REPLACE')


class WeightSource:
    """Copy weights from an already-weighted mesh (nearest vertices)."""

    def __init__(self, ob):
        me = ob.data
        self.kd = KDTree(len(me.vertices))
        names = [g.name for g in ob.vertex_groups]
        self.w = []
        for v in me.vertices:
            self.kd.insert(ob.matrix_world @ v.co, v.index)
            self.w.append({names[g.group]: g.weight for g in v.groups})
        self.kd.balance()

    def __call__(self, p, k=6):
        out = {}
        tot = 0.0
        for co, i, d in self.kd.find_n(p, k):
            f = 1.0 / (d + 0.004)
            tot += f
            for b, x in self.w[i].items():
                out[b] = out.get(b, 0.0) + f * x
        return {b: x / tot for b, x in out.items()}


# ------------------------------------------------------------------------------------------ FK / IK
def rot_local(pitch=0.0, yaw=0.0, roll=0.0):
    """Basis rotation in a bone's local frame: X pitch (+ forward for spine), Y twist (+ left), Z roll."""
    return (Matrix.Rotation(yaw, 4, 'Y') @ Matrix.Rotation(pitch, 4, 'X') @ Matrix.Rotation(roll, 4, 'Z'))


def rot_world(yaw=0.0, pitch=0.0, roll_right=0.0):
    """Armature-space rotation: yaw + = turn left, pitch + = lean forward, roll + = lean right."""
    return (Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(pitch, 4, 'X') @ Matrix.Rotation(-roll_right, 4, 'Y'))


def frame_matrix(head, ydir, xhint):
    Y = Vector(ydir).normalized()
    X = Vector(xhint)
    X = (X - Y * X.dot(Y))
    if X.length < 1e-6:
        X = Y.orthogonal()
    X.normalize()
    Z = X.cross(Y)
    M = Matrix.Identity(4)
    for i in range(3):
        M[i][0], M[i][1], M[i][2], M[i][3] = X[i], Y[i], Z[i], head[i]
    return M


class Pose:
    def __init__(self, rig):
        self.rig = rig
        self.basis = {}
        self.M = {}

    def local(self, name, R):
        self.basis[name] = R

    def mat(self, name):
        if name in self.M:
            return self.M[name]
        r = self.rig
        par = r.parent[name]
        inh = (self.mat(par) @ r.rel[name]) if par else r.rest[name].copy()
        M = inh @ self.basis.get(name, Matrix.Identity(4))
        self.M[name] = M
        return M

    def inherited(self, name):
        r = self.rig
        par = r.parent[name]
        return (self.mat(par) @ r.rel[name]) if par else r.rest[name].copy()

    def set(self, name, M):
        self.M[name] = M

    def rotate_world(self, name, R):
        """Rotate a bone (about its own head) by an armature-space rotation on top of its inherited pose."""
        M = self.inherited(name) @ self.basis.get(name, Matrix.Identity(4))
        h = M.translation.copy()
        self.M[name] = Matrix.Translation(h) @ R @ Matrix.Translation(-h) @ M

    def head(self, name):
        return self.mat(name).translation.copy()

    def tail(self, name):
        return self.mat(name) @ Vector((0, self.rig.length[name], 0))

    def axis(self, name, i):
        M = self.mat(name)
        return Vector((M[0][i], M[1][i], M[2][i]))


class Rig:
    def __init__(self, ob):
        self.ob = ob
        arm = ob.data
        self.order = []
        self.parent, self.rest, self.rel, self.length = {}, {}, {}, {}
        for b in arm.bones:
            self.rest[b.name] = b.matrix_local.copy()
            self.parent[b.name] = b.parent.name if b.parent else None
            self.length[b.name] = b.length
        for b in arm.bones:
            self.rel[b.name] = (self.rest[b.parent.name].inverted() @ self.rest[b.name]) if b.parent else self.rest[b.name]
            self.order.append(b.name)
        self.J = joints()
        self.hinge_sign = {}
        for Side in ("Left", "Right"):
            self._hinge_sign(Side + "UpperLeg", Side + "LowerLeg", V(0, -1, 0))
            self._hinge_sign(Side + "UpperArm", Side + "LowerArm", V(0, 1, 0))

    def _hinge_sign(self, a, b, pole):
        h, k = self.rest[a].translation, self.rest[b].translation
        e = self.rest[b] @ Vector((0, self.length[b], 0))
        u = (e - h).normalized()
        pp = (pole - u * pole.dot(u)).normalized()
        n = u.cross(pp)
        X = Vector((self.rest[a][0][0], self.rest[a][1][0], self.rest[a][2][0]))
        self.hinge_sign[a] = 1.0 if n.dot(X) >= 0 else -1.0

    def basis_of(self, P, name):
        par = self.parent[name]
        inh = (P.mat(par) @ self.rel[name]) if par else self.rest[name]
        return inh.inverted() @ P.mat(name)


def two_bone_ik(P, upper, lower, target, pole, end_dir=None, end_xhint=None, end_bone=None):
    """Analytic two-bone IK in armature space. Sets upper / lower (and optionally end) matrices."""
    r = P.rig
    H = P.head(upper)
    L1, L2 = r.length[upper], r.length[lower]
    d = Vector(target) - H
    dist = d.length
    over = max(0.0, dist - (L1 + L2) * 0.9995)
    dist = min(max(dist, abs(L1 - L2) + 1e-4), (L1 + L2) * 0.9995)
    u = d.normalized()
    pp = Vector(pole) - u * Vector(pole).dot(u)
    pp = pp.normalized() if pp.length > 1e-6 else u.orthogonal().normalized()
    cosA = (L1 * L1 + dist * dist - L2 * L2) / (2 * L1 * dist)
    A = acos(max(-1.0, min(1.0, cosA)))
    K = H + (u * cos(A) + pp * sin(A)) * L1
    E = H + u * dist
    n = u.cross(pp) * r.hinge_sign[upper]
    P.set(upper, frame_matrix(H, K - H, n))
    P.set(lower, frame_matrix(K, E - K, n))
    if end_bone:
        P.set(end_bone, frame_matrix(E, end_dir, end_xhint))
    return over


# ------------------------------------------------------------------------------------------ helpers
def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def hermite(p0, p1, m0, m1, s):
    s2, s3 = s * s, s * s * s
    return ((2 * s3 - 3 * s2 + 1) * p0 + (s3 - 2 * s2 + s) * m0 + (-2 * s3 + 3 * s2) * p1 + (s3 - s2) * m1)


def foot_from_pivot(pivot_world, pitch_up, yaw, pivot='heel', side_x=0.0):
    """Returns ankle position and foot (ankle->ball) direction for a foot pitched by pitch_up (toe up +)
    pivoting on its heel / ball ground point which is at pivot_world."""
    R = Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(-pitch_up, 3, 'X')
    ank = V(0, ANKLE.y, ANKLE.z)
    off = (V(0, HEEL_GROUND.y, 0) if pivot == 'heel' else V(0, BALL_GROUND.y, 0)) - ank
    a = Vector(pivot_world) - R @ off
    fdir = R @ (V(0, BALL.y, BALL.z) - ank)
    return a, fdir, R


def ground_pivot_y(pivot):
    return HEEL_GROUND.y if pivot == 'heel' else BALL_GROUND.y


def stance_foot(g, ph, duty, hs_pitch, to_pitch, h1=0.12, h2=0.5):
    """g = heel ground y when the foot is flat (moves backward with the ground). ph in [0, duty)."""
    if ph < h1 * duty:
        p = hs_pitch * (1 - ease(ph / (h1 * duty)))
        return 'heel', p, g
    if ph < h2 * duty:
        return 'heel', 0.0, g
    s = (ph - h2 * duty) / ((1 - h2) * duty)
    p = -to_pitch * (s ** 1.6)
    return 'ball', p, g + (BALL_GROUND.y - HEEL_GROUND.y)


class Gait:
    def __init__(self, v, T, duty, y_land, lift, hs_pitch, to_pitch, h1=0.12, h2=0.5, swing_toe=0.0):
        self.v, self.T, self.duty, self.y_land = v, T, duty, y_land
        self.lift, self.hs, self.to, self.h1, self.h2 = lift, hs_pitch, to_pitch, h1, h2
        self.swing_toe = swing_toe

    def foot(self, ph, x):
        """Returns ankle pos, foot dir, toe dir, contact flag for leg phase ph (0 = heel strike)."""
        ph %= 1.0
        v, T = self.v, self.T
        if ph < self.duty:
            g = self.y_land + v * T * ph
            pv, pitch, gy = stance_foot(g, ph, self.duty, self.hs, self.to, self.h1, self.h2)
            a, fd, R = foot_from_pivot(V(x, gy, 0.0), pitch, 0.0, pv)
            toe = V(0, -1, 0) if pv == 'ball' else (R @ V(0, -1, -0.05)).normalized()
            return a, fd, toe, True
        # swing: from toe-off pose to the next heel strike
        s = (ph - self.duty) / (1 - self.duty)
        g0 = self.y_land + v * T * self.duty
        pv0, p0, gy0 = stance_foot(g0, self.duty - 1e-6, self.duty, self.hs, self.to, self.h1, self.h2)
        a0, fd0, _ = foot_from_pivot(V(x, gy0, 0), p0, 0.0, pv0)
        a1, fd1, _ = foot_from_pivot(V(x, self.y_land, 0), self.hs, 0.0, 'heel')
        dur = T * (1 - self.duty)
        y = hermite(a0.y, a1.y, v * dur * 1.0, v * dur * 0.15, s)
        z = lerp(a0.z, a1.z, s) + self.lift * (sin(pi * min(1.0, s ** 0.75)) ** 1.0)
        pitch = lerp(p0, self.hs, ease(s * 1.15)) + self.swing_toe * sin(pi * s)
        R = Matrix.Rotation(-pitch, 3, 'X')
        fd = R @ (V(0, BALL.y, BALL.z) - V(0, ANKLE.y, ANKLE.z))
        toe = (R @ V(0, -1, -0.05)).normalized()
        if s < 0.25:  # toes still bent up from the push-off
            toe = V(0, -1, 0).lerp(toe, s / 0.25).normalized()
        return V(x, y, z), fd, toe, False


# ------------------------------------------------------------------------------------------ pose solve
FINGERS = ["Index", "Middle", "Ring", "Little"]


def apply_fingers(P, Side, curl, spread=0.0, thumb=(0.2, 0.2, 0.2), thumb_in=0.0):
    for i, f in enumerate(FINGERS):
        c = curl[i] if isinstance(curl, (list, tuple)) else curl
        for k, seg in enumerate(("Proximal", "Intermediate", "Distal")):
            P.local(f"{Side}{f}{seg}", rot_local(pitch=c * (1.0, 1.1, 0.8)[k], roll=(spread * (i - 1.5) * 0.1 if k == 0 else 0)))
    for k, seg in enumerate(("Metacarpal", "Proximal", "Distal")):
        P.local(f"{Side}Thumb{seg}", rot_local(pitch=thumb[k], roll=(thumb_in if k == 0 else 0.0)))


def solve(rig, spec):
    """spec keys:
      hips_pos (Vector offset), hips_rot (Matrix 4x4 armature space)
      spine: {bone: (pitch, yaw, roll)}  local
      clav: {"L": (up, fwd), "R": ...}
      feet: {"L": (ankle, foot_dir, toe_dir, pole), ...}
      hands: {"L": (target, hand_dir, palm_normal, pole), ...}
      fingers: {"L": dict(curl=..., thumb=...)}
    """
    P = Pose(rig)
    R = spec.get('hips_rot', Matrix.Identity(4))
    rest = rig.rest['Hips']
    h0 = rest.translation
    M = Matrix.Translation(h0 + spec.get('hips_pos', Vector())) @ R @ Matrix.Translation(-h0) @ rest
    P.set('Hips', M)
    for b, (p, y, r) in spec.get('spine', {}).items():
        P.local(b, rot_local(p, y, r))
    for side, Side in (("L", "Left"), ("R", "Right")):
        up, fwd = spec.get('clav', {}).get(side, (0.0, 0.0))
        s = 1 if side == "L" else -1
        # clavicle points along +-X: raise = rotate about its forward axis, protract = about up
        P.local(Side + "Shoulder", Matrix.Rotation(up * s, 4, 'Z') @ Matrix.Rotation(fwd, 4, 'X'))
    # legs
    over = 0.0
    for side, Side in (("L", "Left"), ("R", "Right")):
        f = spec.get('feet', {}).get(side)
        if f:
            ank, fd, toe, pole = f[:4]
            hipR = P.mat('Hips')
            lat = Vector((hipR[0][0], hipR[1][0], hipR[2][0]))
            fdn = Vector(fd).normalized()
            fx = f[4] if len(f) > 4 else V(0, 0, 1).cross(fdn)   # lateral axis of the foot (+X at rest)
            if fx.length < 0.2:
                fx = lat
            over = max(over, two_bone_ik(P, Side + "UpperLeg", Side + "LowerLeg", ank, pole,
                                         fd, fx.normalized(), Side + "Foot"))
            Mf = P.mat(Side + "Foot")
            xf = Vector((Mf[0][0], Mf[1][0], Mf[2][0]))
            P.set(Side + "Toes", frame_matrix(P.tail(Side + "Foot"), toe, xf))
    # arms
    for side, Side in (("L", "Left"), ("R", "Right")):
        h = spec.get('hands', {}).get(side)
        if h:
            tgt, hd, palm, pole = h
            hd = Vector(hd).normalized()
            palm = Vector(palm)
            X = hd.cross(palm)  # X = Y x Z
            over = max(over, two_bone_ik(P, Side + "UpperArm", Side + "LowerArm", tgt, pole))
            P.set(Side + "Hand", frame_matrix(P.tail(Side + "LowerArm"), hd, X))
        fg = spec.get('fingers', {}).get(side, {})
        apply_fingers(P, Side, fg.get('curl', 0.25), fg.get('spread', 0.0), fg.get('thumb', (0.15, 0.15, 0.15)),
                      fg.get('thumb_in', 0.0))
    for b, (p, y, r) in spec.get('extra', {}).items():
        P.local(b, rot_local(p, y, r))
    skirt_solve(P, spec.get('skirt_flare', 0.0), spec.get('ground', True))
    for b in rig.order:
        P.mat(b)
    return P, over


# ------------------------------------------------------------------------------------------ skirt
def skirt_solve(P, flare=0.0, ground=True):
    """Swing each coat-skirt chain outward just enough to clear the thighs / knees / shins
    (and stay above the ground), with a little flare."""
    legs = []
    for Side in ("Left", "Right"):
        legs.append((P.head(Side + "UpperLeg"), P.head(Side + "LowerLeg"), P.tail(Side + "LowerLeg")))
    for nm, ang in SKIRT_ANG.items():
        b1, b2 = "Skirt" + nm + "1", "Skirt" + nm + "2"
        inh1 = P.inherited(b1)
        h1 = inh1.translation.copy()
        X1 = Vector((inh1[0][0], inh1[1][0], inh1[2][0]))
        L1 = P.rig.length[b1]
        L2 = P.rig.length[b2]

        def seg_pts(M, L):
            return [M @ Vector((0, L * t, 0)) for t in (0.35, 0.7, 1.0)]

        def cost(Mb, L, extra_pts=()):
            c = 0.0
            Z = Vector((Mb[0][2], Mb[1][2], Mb[2][2]))   # outward
            Y = Vector((Mb[0][1], Mb[1][1], Mb[2][1]))
            X = Vector((Mb[0][0], Mb[1][0], Mb[2][0]))
            h = Mb.translation
            for (hip, knee, ank) in legs:
                for q, r in ((hip.lerp(knee, 0.5), 0.095), (knee, 0.085), (knee.lerp(ank, 0.3), 0.075),
                             (knee.lerp(ank, 0.6), 0.07)):
                    d = q - h
                    along = d.dot(Y)
                    if along < -0.02 or along > L + 0.05:
                        continue
                    tang = abs(d.dot(X))
                    k = max(0.0, 1.0 - tang / 0.16)
                    if k <= 0:
                        continue
                    need = -r * k            # leg point must be at least r inside the skirt line
                    gap = d.dot(Z)
                    if gap > need:
                        c += (gap - need) * 40.0 * k
            if ground:
                for t in (0.5, 1.0):
                    p = Mb @ Vector((0, L * t, 0))
                    if p.z < 0.025:
                        c += (0.025 - p.z) * 60.0
            return c

        best = None
        for i in range(-18, 46):
            a = i * 0.035
            M1 = inh1 @ Matrix.Rotation(a + flare, 4, 'X')
            c = cost(M1, L1) + abs(a) * 0.08 + (0.6 if a < 0 else 0.0) * abs(a)
            if best is None or c < best[0]:
                best = (c, a)
        a1 = best[1] + flare
        P.local(b1, Matrix.Rotation(a1, 4, 'X'))
        P.M.pop(b1, None)
        P.M.pop(b2, None)
        inh2 = P.inherited(b2)
        best = None
        for i in range(-24, 40):
            a = i * 0.035
            M2 = inh2 @ Matrix.Rotation(a + flare * 0.6, 4, 'X')
            c = cost(M2, L2) + abs(a + 0.15 * a1) * 0.06
            if best is None or c < best[0]:
                best = (c, a)
        P.local(b2, Matrix.Rotation(best[1] + flare * 0.6, 4, 'X'))
        P.M.pop(b2, None)


# ------------------------------------------------------------------------------------------ keying
def key_action(rig, name, frames, loop=False):
    """frames: list of Pose. Writes an Action with quaternion keys for all bones (+ Hips location)."""
    ob = rig.ob
    if ob.animation_data is None:
        ob.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    ob.animation_data.action = act
    prevq = {}
    for fi, P in enumerate(frames):
        for b in rig.order:
            pb = ob.pose.bones[b]
            Bm = rig.basis_of(P, b)
            loc, q, _ = Bm.decompose()
            if b in prevq and q.dot(prevq[b]) < 0:
                q = -q
            prevq[b] = q
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=fi, group=b)
            if b == "Hips":
                pb.location = loc
                pb.keyframe_insert("location", frame=fi, group=b)
            else:
                pb.location = (0, 0, 0)
    act.frame_range = (0, len(frames) - 1)
    act.use_frame_range = True
    act.use_cyclic = loop
    return act
