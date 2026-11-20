"""Per-shot set dressing, lighting, cameras and animation for the intro film."""
import math
import bpy
import numpy as np
from mathutils import Vector, Matrix, Euler

import lettering as LT
import scene_intro as S

WARM = (1.0, 0.62, 0.33)      # ~2700 K tungsten
FLAME = (1.0, 0.56, 0.24)


def _noise1(t, seed, octaves=3):
    """Deterministic smooth 1D noise in [-1, 1]."""
    rng = np.random.default_rng(seed)
    v = 0.0
    amp = 1.0
    tot = 0.0
    for o in range(octaves):
        fr = rng.uniform(1.5, 2.5) * (2 ** o)
        ph = rng.uniform(0, 6.28, 2)
        v += amp * (0.6 * math.sin(fr * t * 6.283 + ph[0]) + 0.4 * math.sin(1.37 * fr * t * 6.283 + ph[1]))
        tot += amp
        amp *= 0.5
    return v / tot


def common(paper_mode):
    ink_img, box = S.ink_image()
    fib = S.fibre_image()
    pm, fxn = S.mat_paper(ink_img, box, fib)
    S.build_desk(S.mat_wood())
    paper = S.build_paper(pm, paper_mode)
    brass = S.mat_metal('Brass', (0.80, 0.55, 0.24), 0.24, 0.16, 500.0, tarnish=(0.30, 0.18, 0.07))
    return dict(paper=paper, paper_mat=pm, flamex=fxn, brass=brass)


def lamp_prop(pos, brass, bulb_strength=40.0, light_w=30.0):
    shade = S.mat_metal('LampShade', (0.10, 0.22, 0.12), 0.35, 0.1, 200.0)
    bulb = S.mat_emit('Bulb', (1.0, 0.66, 0.36), bulb_strength)
    objs, bulbpos = S.build_lamp(pos, (brass, shade, bulb))
    L = S.light('LampLight', 'POINT', bulbpos, light_w, WARM, size=0.03)
    return objs, L


# --------------------------------------------------------------------------- shot 1

def shot1():
    c = common('flat')
    td = S.text_data()
    st, tm = td['strokes'], td['times']
    gold = S.mat_metal('NibGold', (1.0, 0.72, 0.36), 0.12, 0.10, 2000.0,
                       aniso_stretch=(1.0, 1.0, 0.05))
    ebon = S.mat_ebonite()
    pen, nib = S.build_pen(gold, ebon)
    tipe = S.empty('NibTip')
    # pen orientation: nib edge at NIB_ANGLE, axis tilted 47 deg up toward the writer
    e = Vector((math.cos(LT.NIB_ANGLE), math.sin(LT.NIB_ANGLE), 0))
    hdir = Vector((math.sin(LT.NIB_ANGLE), -math.cos(LT.NIB_ANGLE), 0))
    tilt = math.radians(47)
    Z = (hdir * math.cos(tilt) + Vector((0, 0, math.sin(tilt)))).normalized()
    X = e.copy()
    Y = Z.cross(X)
    if Y.z < 0:
        X, Y = -X, -Y
    base = Matrix((X, Y, Z)).transposed().to_4x4()
    pen.rotation_mode = 'QUATERNION'

    d = Vector((0.55, 0.83, 0)).normalized()
    yc = LT.BASELINE_Y + 0.008
    xs_all = np.concatenate([s[:, 0] for s in st])
    xmid = float(0.5 * (xs_all.min() + xs_all.max()))
    # lamp far across the desk, on the camera axis so the varnish and the wet ink mirror it
    lamp_pos = Vector((xmid, yc, 0)) + d * 1.15
    lamp_objs, lamp_light = lamp_prop(lamp_pos, c['brass'], 30.0, 40.0)
    ink = S.build_inkwell(Vector((xs_all.min(), yc, 0)) + d * 0.30 + Vector((-0.10, 0.05, 0)), c['brass'], S.mat_glass())
    # second, cooler and dimmer practical far off (window glow) for a second bokeh shape
    S.light('Fill', 'AREA', Vector((xmid - 0.35, -0.25, 0.45)), 0.18, (0.95, 0.9, 0.85), size=0.5)
    S.aim(bpy.context.scene.objects['Fill'], (xmid, yc, 0))
    # low warm raking light from the left: fibre relief and the cream of the sheet
    rake = S.light('Rake', 'AREA', Vector((xmid - 0.42, yc + 0.12, 0.05)), 0.7, WARM, size=0.12)
    S.aim(rake, (xmid, yc, 0))
    S.world(1.0)
    bpy.context.scene.view_settings.exposure = 3.0

    cam = S.camera('Cam1', 85.0, 3.2, tipe)
    tgt = S.empty('Cam1Target')
    S.track(cam, tgt)

    f0, f1 = S.SHOTS[1]
    frames = list(range(f0, f1 + 2))
    tips = [LT.pen_tip(S.t_of(f), st, tm, t_enter=0.0) for f in frames]
    # smoothed camera follow of nib x
    tx = np.array([p[0] for p in tips])
    sig = 0.35 * S.FPS
    k = np.exp(-0.5 * (np.arange(-40, 41) / sig) ** 2); k /= k.sum()
    txs = np.convolve(np.pad(tx, 40, mode='edge'), k, 'valid')
    for i, f in enumerate(frames):
        t = S.t_of(f)
        x, y, z = tips[i]
        loc = Vector((x, y, 0.00035 + z))
        tipe.location = loc
        tipe.keyframe_insert('location', frame=f)
        wob = Euler((math.radians(1.6 * _noise1(t * 0.7, 1)), math.radians(1.2 * _noise1(t * 0.6, 2)),
                     math.radians(1.5 * _noise1(t * 0.5, 3))))
        m = Matrix.Translation(loc) @ base @ wob.to_matrix().to_4x4()
        pen.location = loc
        pen.rotation_quaternion = m.to_quaternion()
        pen.keyframe_insert('location', frame=f)
        pen.keyframe_insert('rotation_quaternion', frame=f)
        xc = float(txs[i])
        drift = Vector((0.002 * _noise1(t * 0.3, 7), 0.0015 * _noise1(t * 0.3, 8), 0.001 * _noise1(t * 0.35, 9)))
        ctr = Vector((xc + 0.004, yc, 0.0))
        cam.location = ctr - d * 0.19 + Vector((0, 0, 0.046)) + drift
        cam.keyframe_insert('location', frame=f)
        tgt.location = ctr + Vector((0, 0, 0.003))
        tgt.keyframe_insert('location', frame=f)
    return dict(camera=cam)


# --------------------------------------------------------------------------- shot 2

def spark_paths(origin, seed=5, n=18, t0=0.0):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        birth = t0 + rng.uniform(0.0, 0.06)
        life = rng.uniform(0.07, 0.32)
        sp = rng.uniform(0.25, 0.9)
        az = rng.normal(math.pi, 0.6)          # toward the chimney (-x)
        el = rng.uniform(0.15, 1.1)
        v = np.array([math.cos(az) * math.cos(el), rng.normal(0, 0.45), math.sin(el)]) * sp
        out.append((birth, life, v, rng.uniform(0.6, 1.0)))
    return out


def shot2():
    c = common('flat')
    crackle = S.mat_crackle()
    steel = S.mat_metal('Steel', (0.56, 0.56, 0.58), 0.32, 0.12, 900.0)
    flame_mat, fstrength = S.mat_flame(0.034)
    spark_mat = S.mat_emit('Spark', (1.0, 0.45, 0.12), 900.0, use_objcolor=True)
    lt = S.build_lighter((crackle, c['brass'], steel, S.mat_wick(), flame_mat, spark_mat))
    L = S.LIGHTER_POS
    d = Vector((0.33, 1.0, 0)).normalized()
    lamp_objs, lamp_light = lamp_prop(L + d * 1.1 + Vector((0.12, 0, 0)), c['brass'], 30.0, 14.0)
    rim = S.light('Rim', 'AREA', L + Vector((0.16, 0.18, 0.11)), 0.6, WARM, size=0.08)
    S.aim(rim, L + Vector((0, 0, 0.045)))
    kick = S.light('Kick', 'AREA', L + Vector((-0.20, 0.10, 0.12)), 0.12, (0.7, 0.8, 1.0), size=0.15)
    S.aim(kick, L + Vector((0, 0, 0.045)))
    S.world(1.0)
    fl = S.light('FlameLight', 'POINT', lt['flame_base'] + Vector((0, 0, 0.011)), 0.0, FLAME, size=0.005)

    focus = S.empty('Focus2', lt['flame_base'] + Vector((0.004, -0.004, 0.002)))
    cam = S.camera('Cam2', 100.0, 7.0, focus)
    tgt = S.empty('Cam2Target')
    S.track(cam, tgt)

    sparks = []
    sp_origin = lt['wheel_pos'] + Vector((-0.0025, -0.0005, -0.0024))
    paths = spark_paths(sp_origin, t0=S.CUES['strike'] + 0.01)
    for i, (b, life, v, br) in enumerate(paths):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6, radius=0.00006)
        o = bpy.context.active_object
        o.name = 'Spark%02d' % i
        o.data.materials.append(spark_mat)
        o.visible_shadow = False
        sparks.append(o)

    f0, f1 = S.SHOTS[2]
    lo, st_, fo = S.CUES['lid_open'], S.CUES['strike'], S.CUES['flame_on']
    hinge, wheel, fp, flow = lt['lid_hinge'], lt['wheel'], lt['flame_pivot'], lt['flow']
    for f in range(f0 - 1, f1 + 2):
        t = S.t_of(f)
        # lid: thumb pressure creep, flick past the cam, settle
        if t < lo - 0.12:
            a = 0.0
        elif t < lo:
            a = 3.0 * S.smoothstep(lo - 0.12, lo, t)
        elif t < lo + 0.075:
            u = (t - lo) / 0.075
            a = 3.0 + (114 - 3.0) * (1 - (1 - u) ** 2)
        else:
            u = t - lo - 0.075
            a = 104 + 10 * math.exp(-u / 0.05) * math.cos(u * 55)
        hinge.rotation_euler = (0, math.radians(a), 0)
        hinge.keyframe_insert('rotation_euler', frame=f)
        # wheel strike
        w = -125.0 * S.smoothstep(st_ - 0.01, st_ + 0.07, t) - 8 * S.smoothstep(st_ + 0.07, st_ + 0.5, t)
        wheel.rotation_euler = (0, math.radians(w), 0)
        wheel.keyframe_insert('rotation_euler', frame=f)
        # flame
        if t < fo:
            g, s_ = 0.0, 0.001
        else:
            u = t - fo
            g = min(1.0, u / 0.12) * (1.0 + 0.5 * math.exp(-u / 0.12))
            s_ = 0.25 + 0.75 * S.smoothstep(0.0, 0.22, u) + 0.12 * math.exp(-((u - 0.18) / 0.08) ** 2)
        fl_n = _noise1(t * 2.2, 21)
        sway = _noise1(t * 1.3, 22)
        fp.scale = (s_ * (1 + 0.03 * fl_n), s_, max(0.001, s_ * (1 + 0.07 * _noise1(t * 3.1, 23))))
        fp.rotation_euler = (math.radians(2.5 * _noise1(t * 1.1, 24)), math.radians(4 * sway), 0)
        fp.keyframe_insert('scale', frame=f)
        fp.keyframe_insert('rotation_euler', frame=f)
        flow.location = (0.0, 0.0, t * 0.30)
        flow.keyframe_insert('location', frame=f)
        fstrength.outputs[0].default_value = g * (1 + 0.08 * fl_n)
        fstrength.outputs[0].keyframe_insert('default_value', frame=f)
        fl.data.energy = 4.0 * g * (1 + 0.12 * fl_n) * min(1.0, s_)
        fl.data.keyframe_insert('energy', frame=f)
        # sparks
        for o, (b, life, v, br) in zip(sparks, paths):
            age = t - b
            a_ = min(max(age, 0.0), life)
            o.location = sp_origin + Vector(v) * a_ + Vector((0, 0, -4.9 * a_ * a_))
            o.color = ((br * (1 - age / life) ** 1.5 + 0.02) if 0 <= age <= life else 0.0, 0, 0, 1)
            o.keyframe_insert('location', frame=f)
            o.keyframe_insert('color', frame=f)
        # camera: slow push in and slight rise
        u = S.smoothstep(S.t_of(f0), S.t_of(f1), t)
        cam.location = L + Vector((-0.085, -0.255, 0.058)) * (1 - 0.10 * u) + Vector((0, 0, 0.004 * u)) \
            + Vector((0.0006 * _noise1(t * 0.4, 31), 0, 0.0005 * _noise1(t * 0.4, 32)))
        cam.keyframe_insert('location', frame=f)
        tgt.location = L + Vector((0.004, 0.0, 0.054 + 0.004 * u))
        tgt.keyframe_insert('location', frame=f)
    # light linking would be ideal; keep the sparks out of the light path instead
    return dict(camera=cam)


# --------------------------------------------------------------------------- shots 3 + 4

def flame_x(t):
    t0, t1 = S.CUES['flame_under_paper'] - 0.2, 11.75
    u = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
    e = u * u * (3 - 2 * u) * 0.35 + u * 0.65
    return -0.122 + 0.244 * e


def shot34():
    c = common('held')
    yc = LT.BASELINE_Y + 0.008
    lamp = S.light('Lamp', 'SPOT', Vector((-0.45, 0.40, 0.70)), 5.0, (1.0, 0.74, 0.50), size=0.06)
    lamp.data.spot_size = math.radians(24)
    lamp.data.spot_blend = 1.0
    S.aim(lamp, (-0.05, 0.05, S.Z_HELD))
    S.world(1.0, (0.0012, 0.0011, 0.001))
    fl = S.light('FlameLight', 'POINT', (0, yc, S.Z_HELD - 0.03), 0.0, FLAME, size=0.007)
    # smoke wisps above the scorching letters
    smoke_mat, smokex, smoke_amt = S.mat_smoke(S.Z_HELD)
    x0, x1, y0, y1, z0, z1 = -0.05, 0.04, 0.005, 0.06, S.Z_HELD - 0.004, S.Z_HELD + 0.07
    vs = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    fs = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    smoke = S.mesh_obj('Smoke', vs, fs, smoke_mat, smooth=False)
    smoke_light = S.light('SmokeGlow', 'POINT', (0, yc, S.Z_HELD + 0.01), 0.0, FLAME, size=0.03)
    try:
        coll = bpy.data.collections.new('SmokeOnly')
        coll.objects.link(smoke)
        smoke_light.light_linking.receiver_collection = coll
    except Exception as e:
        print('light linking unavailable:', e)

    focus = S.empty('Focus3', (0.0, yc, S.Z_HELD - 0.001))
    cam = S.camera('Cam3', 50.0, 4.0, focus)
    tgt = S.empty('Cam3Target')
    S.track(cam, tgt)
    sc = bpy.context.scene
    f0 = S.SHOTS[3][0]
    f1 = S.SHOTS[4][1]
    off = S.CUES['flame_off']
    fxs = c['flamex']
    for f in range(f0 - 1, f1 + 2):
        t = S.t_of(f)
        fx = flame_x(t)
        sag = -0.010 * (fx / (S.PW / 2)) ** 2
        n1, n2 = _noise1(t * 0.8, 41), _noise1(t * 2.7, 42)
        fl.location = (fx + 0.002 * n1, yc - 0.003 + 0.004 * _noise1(t * 0.6, 43),
                       S.Z_HELD + sag - 0.028 + 0.003 * _noise1(t * 0.9, 44))
        fl.keyframe_insert('location', frame=f)
        alive = 1.0 - S.smoothstep(off - 0.01, off + 0.10, t)
        fl.data.energy = 2.2 * alive * (1 + 0.10 * n2 + 0.05 * _noise1(t * 6.0, 45))
        fl.data.keyframe_insert('energy', frame=f)
        fxs.outputs[0].default_value = fx + 0.008
        fxs.outputs[0].keyframe_insert('default_value', frame=f)
        smokex.outputs[0].default_value = fx
        smokex.outputs[0].keyframe_insert('default_value', frame=f)
        smoke_amt.outputs[0].default_value = (1.0 - S.smoothstep(off + 0.2, off + 1.6, t)) * \
            S.smoothstep(7.3, 8.0, t)
        smoke_amt.outputs[0].keyframe_insert('default_value', frame=f)
        smoke.location = (fx, 0, 0)
        smoke.keyframe_insert('location', frame=f)
        smoke_light.location = (fx - 0.02, yc, S.Z_HELD + 0.012)
        smoke_light.keyframe_insert('location', frame=f)
        smoke_light.data.energy = 1.0 * alive
        smoke_light.data.keyframe_insert('energy', frame=f)
        # camera: slow push, easing to rest for the title hold
        u = S.smoothstep(7.0, 13.4, t)
        cam.location = Vector((0.006 - 0.006 * u, -0.215 + 0.012 * u, S.Z_HELD + 0.315 - 0.02 * u)) + \
            Vector((0.0008 * _noise1(t * 0.25, 51), 0.0006 * _noise1(t * 0.25, 52), 0)) * (1 - u)
        cam.keyframe_insert('location', frame=f)
        tgt.location = (0.0, 0.004 + 0.002 * u, S.Z_HELD)
        tgt.keyframe_insert('location', frame=f)
        # auto-exposure: eyes open up once the flame is gone
        sc.view_settings.exposure = -1.6 + 3.7 * S.smoothstep(off + 0.15, off + 1.35, t)
        sc.view_settings.keyframe_insert('exposure', frame=f)
    return dict(camera=cam)


BUILDERS = {1: shot1, 2: shot2, 3: shot34, 4: shot34}
