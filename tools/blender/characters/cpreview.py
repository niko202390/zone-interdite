"""Preview renders: dim dusk lighting (Cycles) and fast Workbench animation contact sheets."""
import os
import time
from math import radians

import bpy
import numpy as np
from mathutils import Vector

from cgeo import link
from cmats import setup_cycles


def log(*a):
    print("[preview]", *a, flush=True)


def dusk_world(strength=1.0):
    sc = bpy.context.scene
    w = sc.world or bpy.data.worlds.new("World")
    sc.world = w
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs[1].default_value = -0.05
    mr.inputs[2].default_value = 0.6
    nt.links.new(sep.outputs['Z'], mr.inputs[0])
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    ins = {s.identifier: s for s in mix.inputs}
    ins['A_Color'].default_value = (0.055, 0.035, 0.03, 1)   # warm afterglow at the horizon
    ins['B_Color'].default_value = (0.012, 0.018, 0.035, 1)  # deep blue zenith
    nt.links.new(mr.outputs[0], ins['Factor_Float'])
    nt.links.new({s.identifier: s for s in mix.outputs}['Result_Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = strength
    nt.links.new(bg.outputs[0], out.inputs['Surface'])


def ground():
    me = bpy.data.meshes.new("ground")
    s = 6
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    ob = link(bpy.data.objects.new("ground", me))
    mat = bpy.data.materials.new("ground_mat")
    mat.use_nodes = True
    b = mat.node_tree.nodes.get("Principled BSDF")
    b.inputs['Base Color'].default_value = (0.035, 0.032, 0.028, 1)
    b.inputs['Roughness'].default_value = 0.85
    me.materials.append(mat)
    return ob


def sun(name, rot, energy, color):
    ld = bpy.data.lights.new(name, 'SUN')
    ld.energy = energy
    ld.color = color
    ld.angle = radians(3)
    ob = link(bpy.data.objects.new(name, ld))
    ob.rotation_euler = rot
    return ob


def area(name, loc, target, energy, size, color):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = energy
    ld.size = size
    ld.color = color
    ob = link(bpy.data.objects.new(name, ld))
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return ob


def camera(name, loc, target, lens=50, ortho=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    if ortho:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho
    ob = link(bpy.data.objects.new(name, cd))
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return ob


def render_dusk(tag, out_dir, samples=48, views=None, res=(1200, 1500), exposure=0.0, extra_light=True):
    sc = bpy.context.scene
    setup_cycles(samples)
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = exposure
    dusk_world(1.0)
    tmp = [ground()]
    tmp.append(sun("dusk_sun", (radians(84), 0, radians(-130)), 0.35, (1.0, 0.62, 0.38)))
    if extra_light:
        tmp.append(area("lamp", (2.2, -2.5, 2.6), (0, 0, 1.2), 60.0, 1.0, (1.0, 0.85, 0.65)))
        tmp.append(area("rim", (-1.5, 2.5, 2.0), (0, 0, 1.3), 40.0, 1.0, (0.6, 0.7, 1.0)))
    views = views or [
        ("front34", (1.9, -3.4, 1.35), (0, 0, 0.95), 50),
        ("side", (3.8, 0.0, 1.1), (0, 0, 0.92), 50),
        ("back34", (-2.0, 3.3, 1.45), (0, 0, 0.95), 50),
        ("front", (0.0, -3.9, 1.1), (0, 0, 0.92), 50),
    ]
    paths = []
    os.makedirs(out_dir, exist_ok=True)
    for nm, loc, tgt, lens in views:
        cam = camera("cam_" + nm, loc, tgt, lens)
        sc.camera = cam
        p = os.path.join(out_dir, f"{tag}_{nm}.png")
        sc.render.filepath = p
        t = time.time()
        bpy.ops.render.render(write_still=True)
        log(f"rendered {p} in {time.time()-t:.1f}s")
        paths.append(p)
        bpy.data.objects.remove(cam, do_unlink=True)
    for o in tmp:
        bpy.data.objects.remove(o, do_unlink=True)
    return paths


def render_workbench(path, cam_loc, cam_tgt, res=(480, 600), lens=50, ortho=None, color='TEXTURE'):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = 'STUDIO'
    sh.color_type = color
    sh.show_shadows = True
    sh.show_cavity = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.exposure = 0.0
    cam = camera("wb_cam", cam_loc, cam_tgt, lens, ortho)
    sc.camera = cam
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    return path


def contact_sheet(out, cols, files, tw=360, th=450):
    tiles = []
    for f in files:
        im = bpy.data.images.load(f)
        w, h = im.size
        px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, im.channels)[..., :3]
        ys = (np.arange(th) * h / th).astype(int)
        xs = (np.arange(tw) * w / tw).astype(int)
        tiles.append(px[ys][:, xs])
        bpy.data.images.remove(im)
    rows = (len(tiles) + cols - 1) // cols
    sheet = np.zeros((rows * th, cols * tw, 4), np.float32)
    sheet[..., 3] = 1
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        sheet[(rows - 1 - r) * th:(rows - r) * th, c * tw:(c + 1) * tw, :3] = t
        sheet[(rows - 1 - r) * th:(rows - r) * th, c * tw:c * tw + 2, :3] = 0.5
    img = bpy.data.images.new("sheet", cols * tw, rows * th)
    img.pixels.foreach_set(sheet.ravel())
    img.filepath_raw = out
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    for f in files:
        try:
            os.remove(f)
        except OSError:
            pass
    log("sheet", out)
