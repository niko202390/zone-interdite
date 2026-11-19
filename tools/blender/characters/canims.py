"""The soldier's animations, authored procedurally (see crig for the solver).

Idle        4.0 s loop   breathing, weight shift
Walk        1.0 s loop   in place, 1.3 m/s (planted foot travels back at exactly 1.3 m/s)
Run         0.733 s loop in place, 4.0 m/s
LookAround  6.0 s        head/torso scan left and right from the idle stance (starts/ends at Idle)
AimRifle    3.0 s loop   Kar98k shouldered, breathing sway
Death       2.4 s        hit, knees buckle, falls backwards, lies still
"""
from math import cos, exp, pi, sin, sqrt

from mathutils import Matrix, Vector

import crig
from crig import (ANKLE, BALL, FPS, Gait, V, ease, foot_from_pivot, rot_world, solve)

J = crig.joints()
LEG_L = 0.841


def drot(P, bone):
    """Rotation of a bone relative to its rest orientation (armature space)."""
    return P.mat(bone).to_3x3() @ P.rig.rest[bone].to_3x3().inverted()


def flat_foot(x, y, yaw):
    R = Matrix.Rotation(yaw, 3, 'Z')
    ank = V(x, y, ANKLE.z)
    fd = R @ (V(0, BALL.y, BALL.z) - V(0, ANKLE.y, ANKLE.z))
    toe = R @ V(0, -1, -0.04)
    return ank, fd, toe


def knee_pole(yaw=0.0, out=0.0):
    return (Matrix.Rotation(yaw, 3, 'Z') @ V(out, -1.0, 0.0)).normalized()


def stand_feet():
    out = {}
    for side, s in (("L", 1), ("R", -1)):
        a, fd, toe = flat_foot(0.105 * s, 0.0, 0.13 * s)
        out[side] = (a, fd, toe, knee_pole(0.13 * s, 0.15 * s))
    return out


def hang_hand(side, swing=0.0, out=0.035, down=0.50, fwd=0.0, bend=0.0):
    """Hand hanging beside the thigh, relative to the posed shoulder joint and chest."""
    s = 1 if side == "L" else -1
    Side = "Left" if side == "L" else "Right"

    def f(P):
        sh = P.head(Side + "UpperArm")
        C = drot(P, "UpperChest")
        Hm = drot(P, "Hips")
        R = Matrix.Rotation(swing, 3, 'X')
        off = R @ V(s * out, 0.02 + fwd, -down)
        tgt = sh + (Hm @ off) * 0.5 + (C @ off) * 0.5
        fdir = (tgt - sh).normalized()
        hd = (fdir + V(0, -0.15 - bend, 0)).normalized()
        palm = (Hm @ V(-s, -0.25, 0.0))
        palm = (palm - hd * palm.dot(hd)).normalized()
        pole = (Hm @ V(s * 0.35, 1.0, 0.0)).normalized()
        return tgt, hd, palm, pole
    return f


RELAX = {"L": dict(curl=[0.35, 0.42, 0.48, 0.55], thumb=(0.15, 0.2, 0.25)),
         "R": dict(curl=[0.35, 0.42, 0.48, 0.55], thumb=(0.15, 0.2, 0.25))}


# ----------------------------------------------------------------------------------------- Idle
def idle_spec(t, T=4.0, scan=None):
    w = 2 * pi * t / T
    b = 0.5 - 0.5 * cos(w)                 # breath: 0 exhaled .. 1 inhaled
    sway = sin(w)
    spec = dict(
        hips_pos=V(0.010 * sway, 0.004 * sin(w * 2), -0.014 + 0.002 * cos(2 * w)),
        hips_rot=rot_world(yaw=0.015 * sway, pitch=0.02, roll_right=-0.018 * sway).to_4x4(),
        spine={"Spine": (0.03, 0.0, 0.010 * sway), "Chest": (0.02 - 0.012 * b, 0.0, 0.006 * sway),
               "UpperChest": (-0.015 - 0.018 * b, 0.0, 0.0), "Neck": (0.10, 0.0, 0.0),
               "Head": (-0.05 + 0.01 * sin(w + 1.0), 0.03 * sin(w * 0.5 + 0.3), -0.01 * sway)},
        clav={"L": (0.03 * b, 0.0), "R": (0.03 * b, 0.0)},
        feet=stand_feet(),
        hands={"L": hang_hand("L", 0.03 + 0.01 * b), "R": hang_hand("R", 0.05 + 0.01 * b, fwd=0.02)},
        fingers=RELAX,
    )
    if scan is not None:
        y, p = scan
        sp = spec["spine"]
        sp["Chest"] = (sp["Chest"][0], y * 0.12, sp["Chest"][2])
        sp["UpperChest"] = (sp["UpperChest"][0], y * 0.14, sp["UpperChest"][2])
        sp["Neck"] = (0.10 + p * 0.3, y * 0.24, 0.0)
        sp["Head"] = (sp["Head"][0] + p * 0.7, y * 0.50, sp["Head"][2])
        hr = spec["hips_rot"]
        spec["hips_rot"] = rot_world(yaw=0.015 * sway + y * 0.06, pitch=0.02, roll_right=-0.018 * sway).to_4x4()
    return spec


def make_idle(rig):
    T = 4.0
    n = int(T * FPS)
    return [solve(rig, idle_spec(i / FPS, T)) for i in range(n + 1)]


def make_lookaround(rig):
    T = 6.0
    n = int(T * FPS)
    # yaw (rad, + = his left) and pitch keys
    keys = [(0.0, 0.0, 0.0), (0.35, 0.0, 0.0), (1.25, 1.0, -0.05), (2.25, 1.0, 0.05), (3.0, 0.0, 0.0),
            (3.15, 0.0, 0.0), (4.1, -0.95, -0.04), (5.1, -0.95, 0.06), (5.85, 0.0, 0.0), (6.0, 0.0, 0.0)]

    def at(t):
        for i in range(len(keys) - 1):
            t0, y0, p0 = keys[i]
            t1, y1, p1 = keys[i + 1]
            if t0 <= t <= t1:
                k = ease((t - t0) / (t1 - t0))
                return y0 + (y1 - y0) * k, p0 + (p1 - p0) * k
        return 0.0, 0.0
    frames = []
    for i in range(n + 1):
        t = i / FPS
        y, p = at(t)
        frames.append(solve(rig, idle_spec(t, 3.0 if False else 6.0, scan=(y * 0.9, p))))
    return frames


# ----------------------------------------------------------------------------------------- locomotion
def hip_limit(spec_feet, hips_pos, contact, margin=0.995):
    """Highest the pelvis can be so that every planted foot is reachable."""
    zmax = 9.0
    for side, s in (("L", 1), ("R", -1)):
        a = spec_feet[side][0]
        hip = V(J['hip' + side].x, J['hip' + side].y + hips_pos.y, 0)
        dx, dy = a.x - hip.x, a.y - hip.y
        reach = LEG_L * (margin if contact[side] else 0.985)
        h2 = reach * reach - dx * dx - dy * dy
        if h2 > 0:
            # hip joint z = J.z + dz -> dz <= a.z + sqrt(h2) - J.z
            zmax = min(zmax, a.z + sqrt(h2) - J['hip' + side].z)
        else:
            zmax = min(zmax, -0.3)
    return zmax


def locomotion(rig, kind):
    if kind == "Walk":
        v, T, duty = 1.3, 1.0, 0.60
        g = Gait(v, T, duty, y_land=-0.30, lift=0.085, hs_pitch=0.30, to_pitch=0.62, h1=0.14, h2=0.52,
                 swing_toe=0.15)
        bob, base_drop, lean, arm_sw, flare = 0.012, -0.012, 0.05, 0.30, 0.0
    else:
        v, T, duty = 4.0, 22 / 30, 0.31
        g = Gait(v, T, duty, y_land=-0.22, lift=0.24, hs_pitch=0.12, to_pitch=0.85, h1=0.12, h2=0.35,
                 swing_toe=0.25)
        bob, base_drop, lean, arm_sw, flare = 0.035, -0.035, 0.20, 0.75, 0.10
    n = int(round(T * FPS))
    raw = []
    for i in range(n):
        ph = i / n
        feet, contact = {}, {}
        for side, s, off in (("L", 1, 0.0), ("R", -1, 0.5)):
            a, fd, toe, c = g.foot(ph + off, 0.100 * s)
            # small toe-out
            R = Matrix.Rotation(0.06 * s, 3, 'Z')
            feet[side] = [V(a.x, a.y, a.z), R @ fd, R @ toe, knee_pole(0.06 * s, 0.1 * s)]
            contact[side] = c
        w = 2 * pi * ph
        # pelvis: highest at mid-stance (2x per cycle) for walking, lowest at mid-stance for running
        z_nom = base_drop + (bob * cos(2 * (w - pi * duty)) if kind == "Walk" else -bob * cos(2 * (w - pi * duty * 1.0)))
        hp = V(0.018 * sin(w + 0.4) if kind == "Walk" else 0.010 * sin(w), 0.0, z_nom)
        raw.append((ph, feet, contact, hp))
    # pelvis height limited by reach, smoothed around the loop
    zl = [min(hp.z, hip_limit(feet, hp, contact)) for (ph, feet, contact, hp) in raw]
    sm = []
    for i in range(n):
        acc, ws = 0.0, 0.0
        for k in range(-3, 4):
            wgt = exp(-(k / 2.0) ** 2)
            acc += zl[(i + k) % n] * wgt
            ws += wgt
        sm.append(min(acc / ws, zl[i] + 0.004))
    frames = []
    for i in range(n + 1):
        ph, feet, contact, hp = raw[i % n]
        w = 2 * pi * ph
        hp = V(hp.x, hp.y, sm[i % n])
        swing = sin(w)    # + when left leg is behind (left stance first half)
        yaw_p = 0.09 * cos(w) if kind == "Walk" else 0.14 * cos(w)
        spec = dict(
            hips_pos=hp,
            hips_rot=rot_world(yaw=-yaw_p, pitch=lean * 0.5, roll_right=(0.035 if kind == "Walk" else 0.02) * sin(w)).to_4x4(),
            spine={"Spine": (lean * 0.3, yaw_p * 0.4, -0.015 * sin(w)), "Chest": (lean * 0.2, yaw_p * 0.5, 0.0),
                   "UpperChest": (lean * 0.1 - 0.01 * cos(2 * w), yaw_p * 0.6, 0.0),
                   "Neck": (0.08 - lean * 0.3, -yaw_p * 0.5, 0.0), "Head": (-0.06 - lean * 0.2 + 0.02 * cos(2 * w), -yaw_p * 0.4, 0.01 * sin(w))},
            clav={"L": (0.01, 0.04 * cos(w)), "R": (0.01, -0.04 * cos(w))},
            feet=feet,
            fingers=RELAX if kind == "Walk" else {"L": dict(curl=[0.9, 1.0, 1.1, 1.2], thumb=(0.4, 0.5, 0.4)),
                                                 "R": dict(curl=[0.9, 1.0, 1.1, 1.2], thumb=(0.4, 0.5, 0.4))},
            skirt_flare=flare + (0.03 * (0.5 - 0.5 * cos(2 * w)) if kind == "Run" else 0.0),
        )
        if kind == "Walk":
            spec["hands"] = {"L": hang_hand("L", -arm_sw * cos(w) * 0.9 + 0.05, out=0.05, bend=0.1 + 0.1 * max(0, -cos(w))),
                             "R": hang_hand("R", arm_sw * cos(w) * 0.9 + 0.05, out=0.05, bend=0.1 + 0.1 * max(0, cos(w)))}
        else:
            spec["hands"] = {"L": run_hand("L", -cos(w)), "R": run_hand("R", cos(w))}
        frames.append(solve(rig, spec))
    return frames, T, v


def run_hand(side, ph):
    s = 1 if side == "L" else -1
    Side = "Left" if side == "L" else "Right"

    def f(P):
        sh = P.head(Side + "UpperArm")
        C = drot(P, "UpperChest")
        # elbow ~90 deg; ph=+1 hand forward/up, -1 back/down
        off = V(s * 0.02 - s * 0.05 * max(0, ph), -0.10 - 0.17 * ph, -0.30 + 0.07 * max(0.0, ph) - 0.03 * max(0.0, -ph))
        tgt = sh + C @ off
        hd = (C @ V(-s * 0.35, -0.75, 0.25)).normalized()
        palm = C @ V(-s, 0.0, 0.2)
        palm = (palm - hd * palm.dot(hd)).normalized()
        pole = (C @ V(s * 0.4, 1.0, -0.6)).normalized()
        return tgt, hd, palm, pole
    return f


# ----------------------------------------------------------------------------------------- aim
RIFLE_GRIP_BELOW_BORE = 0.045
RIFLE_BUTT = -0.270
RIFLE_FORE = 0.300


def rifle_world0():
    """Rifle origin frame in the shouldered pose (bore along -Y world)."""
    X = V(-1, 0, 0)
    Y = V(0, -1, 0)
    Z = V(0, 0, 1)
    R = Matrix.Rotation(0.035, 3, 'X')      # muzzle very slightly down
    M = Matrix.Identity(4)
    Xr, Yr, Zr = R @ X, R @ Y, R @ Z
    org = V(-0.070, -0.245, 1.552 - RIFLE_GRIP_BELOW_BORE)
    for i in range(3):
        M[i][0], M[i][1], M[i][2], M[i][3] = Xr[i], Yr[i], Zr[i], org[i]
    return M


def aim_spec(t, T, rifle_follow):
    w = 2 * pi * t / T
    b = 0.5 - 0.5 * cos(w)
    feet = {}
    for side, x, y, yaw in (("L", 0.075, -0.17, -0.22), ("R", -0.19, 0.19, -0.95)):
        a, fd, toe = flat_foot(x, y, yaw)
        feet[side] = (a, fd, toe, knee_pole(yaw * 0.6, 0.15 if side == "L" else -0.2))
    spec = dict(
        hips_pos=V(0.0, 0.015, -0.022),
        hips_rot=rot_world(yaw=-0.50, pitch=0.04, roll_right=0.02).to_4x4(),
        spine={"Spine": (0.06, 0.06, 0.02), "Chest": (0.05 - 0.01 * b, 0.10, 0.03),
               "UpperChest": (0.03 - 0.015 * b, 0.12, 0.05), "Neck": (0.06, 0.10, 0.06),
               "Head": (0.10, 0.10, 0.10)},
        clav={"L": (0.05, 0.28), "R": (0.10, 0.20)},
        feet=feet,
        fingers={"L": dict(curl=[0.85, 0.95, 1.05, 1.15], thumb=(0.35, 0.3, 0.2)),
                 "R": dict(curl=[0.45, 1.25, 1.3, 1.35], thumb=(0.55, 0.5, 0.35))},
    )

    def rifle(P):
        return rifle_follow(P)

    def rh(P):
        M = rifle(P)
        R3 = M.to_3x3()
        grip = M.translation
        hd = (R3 @ V(0.15, 0.55, -0.80)).normalized()   # in rifle space: forward-down, wrapping left
        palm = (R3 @ V(-1.0, 0.0, 0.0))                  # palm against the right side of the wrist
        palm = (palm - hd * palm.dot(hd)).normalized()
        wrist = grip - hd * 0.050 + palm * -0.022 + (R3 @ V(0, 0, 0.012))
        pole = V(-0.75, 0.35, -0.85).normalized()
        return wrist, hd, palm, pole

    def lh(P):
        M = rifle(P)
        R3 = M.to_3x3()
        fore = M @ V(0.0, RIFLE_FORE, 0.010)
        hd = (R3 @ V(-0.45, 0.80, 0.25)).normalized()
        palm = R3 @ V(0.0, 0.0, 1.0)
        palm = (palm - hd * palm.dot(hd)).normalized()
        wrist = fore - hd * 0.050 - palm * 0.032
        pole = V(0.35, 0.1, -1.0).normalized()
        return wrist, hd, palm, pole
    spec["hands"] = {"R": rh, "L": lh}
    return spec


def make_aim(rig):
    T = 3.0
    n = int(T * FPS)
    R0 = rifle_world0()
    base = solve(rig, aim_spec(0.0, T, lambda P: R0))[0]
    UC0 = base.mat("UpperChest").copy()

    def follow(P):
        return P.mat("UpperChest") @ UC0.inverted() @ R0
    frames = [solve(rig, aim_spec(i / FPS, T, follow)) for i in range(n + 1)]
    return frames, R0


# ----------------------------------------------------------------------------------------- death
def make_death(rig):
    T = 2.4
    n = int(T * FPS)
    # key: t, hips (x, y, z), hips (yaw, pitch, roll), spine pitch, head (pitch, yaw), heel L/R (y), foot pitch, hands L/R
    K = [
        dict(t=0.00, hp=(0, 0.0, -0.014), hr=(0.0, 0.02, 0.0), sp=0.02, hd=(-0.05, 0.0), fy=(0.0, 0.0), fp=0.0, fz=0.0,
             hl=None, hrr=None),
        dict(t=0.10, hp=(0, 0.035, -0.02), hr=(0.04, -0.10, 0.02), sp=-0.10, hd=(-0.35, 0.05), fy=(0.0, 0.0), fp=0.0, fz=0.0,
             hl=(0.30, -0.15, 1.05), hrr=(-0.28, -0.20, 1.10)),
        dict(t=0.45, hp=(0.01, 0.10, -0.22), hr=(0.08, -0.30, 0.05), sp=-0.14, hd=(-0.20, 0.12), fy=(-0.02, 0.0), fp=0.05, fz=0.0,
             hl=(0.42, -0.05, 0.95), hrr=(-0.40, -0.02, 0.95)),
        dict(t=0.85, hp=(0.02, 0.36, -0.50), hr=(0.12, -0.95, 0.12), sp=-0.08, hd=(0.25, 0.10), fy=(-0.18, -0.12), fp=0.35, fz=0.0,
             hl=(0.60, 0.45, 0.75), hrr=(-0.55, 0.45, 0.70)),
        dict(t=1.10, hp=(0.03, 0.52, -0.70), hr=(0.14, -1.55, 0.26), sp=0.0, hd=(0.15, 0.30), fy=(-0.36, -0.30), fp=1.05, fz=0.0,
             hl=(0.62, 1.05, 0.10), hrr=(-0.62, 0.78, 0.10)),
        dict(t=1.28, hp=(0.03, 0.53, -0.67), hr=(0.14, -1.49, 0.26), sp=-0.03, hd=(0.05, 0.38), fy=(-0.37, -0.31), fp=1.1, fz=0.0,
             hl=(0.64, 1.06, 0.12), hrr=(-0.64, 0.80, 0.12)),
        dict(t=1.62, hp=(0.03, 0.53, -0.70), hr=(0.14, -1.555, 0.28), sp=0.0, hd=(0.10, 0.45), fy=(-0.37, -0.31), fp=1.15, fz=0.0,
             hl=(0.64, 1.06, 0.05), hrr=(-0.64, 0.80, 0.05)),
        dict(t=2.40, hp=(0.03, 0.53, -0.70), hr=(0.14, -1.555, 0.28), sp=0.0, hd=(0.10, 0.45), fy=(-0.37, -0.31), fp=1.15, fz=0.0,
             hl=(0.64, 1.06, 0.05), hrr=(-0.64, 0.80, 0.05)),
    ]
    idle0 = idle_spec(0.0)

    def lerpv(a, b, k):
        return tuple(x + (y - x) * k for x, y in zip(a, b))

    def sample(t):
        for i in range(len(K) - 1):
            a, b = K[i], K[i + 1]
            if a['t'] <= t <= b['t']:
                u = (t - a['t']) / (b['t'] - a['t'])
                # falling segments accelerate (gravity), others ease
                k = u * u if a['t'] in (0.45, 0.85) else ease(u)
                out = {}
                for key in a:
                    if key == 't':
                        continue
                    va, vb = a[key], b[key]
                    if va is None or vb is None:
                        out[key] = (va, vb, k)
                    elif isinstance(va, tuple):
                        out[key] = lerpv(va, vb, k)
                    else:
                        out[key] = va + (vb - va) * k
                return out
        return {k: v for k, v in K[-1].items() if k != 't'}

    frames = []
    for i in range(n + 1):
        t = i / FPS
        s = sample(t)
        hp = V(*s['hp'])
        yaw, pitch, roll = s['hr']
        feet = {}
        for side, sg, fy in (("L", 1, s['fy'][0]), ("R", -1, s['fy'][1])):
            yaw_f = 0.13 * sg + 0.45 * sg * min(1.0, s['fp'])
            heel = V(0.105 * sg + 0.05 * sg * min(1.0, s['fp']), fy + 0.085, 0.0)
            a, fd, R = foot_from_pivot(heel, s['fp'], yaw_f, 'heel')
            toe = R @ V(0, -1, -0.04)
            pole = (V(0.25 * sg, -1.0, 0.3 + 1.2 * min(1.0, s['fp']))).normalized()
            feet[side] = (a, fd, toe, pole)
        spec = dict(
            hips_pos=hp, hips_rot=rot_world(yaw=yaw, pitch=pitch, roll_right=roll).to_4x4(),
            spine={"Spine": (s['sp'], 0.03, 0.0), "Chest": (s['sp'], 0.03, 0.02), "UpperChest": (s['sp'] * 0.8, 0.02, 0.0),
                   "Neck": (s['hd'][0] * 0.4 + 0.05, s['hd'][1] * 0.4, 0.0), "Head": (s['hd'][0] * 0.6, s['hd'][1] * 0.6, 0.05)},
            clav={"L": (0.05, 0.0), "R": (0.05, 0.0)},
            feet=feet,
            fingers={"L": dict(curl=[0.25, 0.3, 0.38, 0.45], thumb=(0.1, 0.1, 0.1)),
                     "R": dict(curl=[0.25, 0.3, 0.38, 0.45], thumb=(0.1, 0.1, 0.1))},
        )
        hands = {}
        for side, key in (("L", 'hl'), ("R", 'hrr')):
            val = s[key]
            hh = idle0['hands'][side]
            if isinstance(val, tuple) and len(val) == 3 and val[0] is None:
                # blend from the idle hang into the first world target
                _, tgt, k = val
                hands[side] = blend_hand(hh, V(*tgt), k, side)
            elif isinstance(val, tuple) and len(val) == 3 and isinstance(val[0], float) is False and val[0] is not None:
                hands[side] = world_hand(V(*val), side)
            else:
                hands[side] = world_hand(V(*val), side)
        spec['hands'] = hands
        frames.append(solve(rig, spec))
    return frames


def world_hand(tgt, side):
    s = 1 if side == "L" else -1
    Side = "Left" if side == "L" else "Right"

    def f(P):
        sh = P.head(Side + "UpperArm")
        hd = (tgt - sh).normalized()
        C = drot(P, "UpperChest")
        palm = C @ V(0, 0.3, 1.0) if tgt.z < 0.3 else C @ V(-s, 0.0, 0.0)
        palm = (palm - hd * palm.dot(hd)).normalized()
        pole = (C @ V(s * 0.5, 1.0, -0.3)).normalized()
        return tgt, hd, palm, pole
    return f


def blend_hand(hang_fn, tgt, k, side):
    wf = world_hand(tgt, side)

    def f(P):
        a = hang_fn(P)
        b = wf(P)
        t = a[0].lerp(b[0], k)
        hd = a[1].lerp(b[1], k).normalized()
        palm = a[2].lerp(b[2], k).normalized()
        palm = (palm - hd * palm.dot(hd)).normalized()
        return t, hd, palm, a[3].lerp(b[3], k).normalized()
    return f
