"""Preview renders for the enterable houses: interior shots at eye height under dim warm lamp
light (lights only exist in the preview; Godot places its own at LightSpot_*)."""
import math
import os

import bpy
from mathutils import Vector

from ihelp import PREVIEW_DIR


def _night_world(strength=0.02):
    w = bpy.data.worlds.new("Night")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.05, 0.07, 0.13, 1)
    bg.inputs["Strength"].default_value = strength
    return w


def _setup(res, exposure):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    try:
        sc.eevee.taa_render_samples = 64
    except Exception:
        pass
    for attr, val in (("use_shadows", True), ("use_raytracing", True), ("ray_tracing_method", "SCREEN"),
                      ("use_gtao", True), ("fast_gi_method", "GLOBAL_ILLUMINATION")):
        try:
            setattr(sc.eevee, attr, val)
        except Exception:
            pass
    try:
        sc.eevee.shadow_pool_size = "1024"
    except Exception:
        pass
    try:
        sc.eevee.ray_tracing_options.resolution_scale = "2"
    except Exception:
        pass
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = exposure
    return sc


def point(name, loc, energy, color=(1.0, 0.62, 0.32), radius=0.05):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = energy
    ld.color = color
    ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    bpy.context.scene.collection.objects.link(ob)
    return ob


def render_interior(name, cam_loc, look_at, lights, res=(1280, 720), lens=22.0, exposure=0.8, moon=True):
    sc = _setup(res, exposure)
    sc.world = _night_world()
    tmp = []
    for (nm, loc, e, col, rad) in lights:
        tmp.append(point(nm, loc, e, col, rad))
    if moon:
        sd = bpy.data.lights.new("PV_moon", "SUN")
        sd.energy = 0.15
        sd.color = (0.55, 0.65, 1.0)
        mo = bpy.data.objects.new("PV_moon", sd)
        mo.rotation_euler = (math.radians(55), 0, math.radians(200))
        sc.collection.objects.link(mo)
        tmp.append(mo)
    cd = bpy.data.cameras.new("PV_cam")
    cd.lens = lens
    cd.clip_start = 0.02
    cam = bpy.data.objects.new("PV_cam", cd)
    sc.collection.objects.link(cam)
    cam.location = cam_loc
    cam.rotation_euler = (Vector(look_at) - Vector(cam_loc)).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    tmp.append(cam)
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    sc.render.filepath = os.path.join(PREVIEW_DIR, f"{name}.png")
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    for o in tmp:
        bpy.data.objects.remove(o)
    return sc.render.filepath
