"""Briefing pages: four photoreal typed sheets of "SOE Operation Instruction No. 31".

Run headless:
  blender --background --factory-startup --python-exit-code 1 --python build_briefing.py -- [--pages 1,2,3,4] [--samples 160] [--pct 100]
Output: game/assets/briefing/page_N.png

Text is read verbatim from game/scripts/ui/title.gd (PAGES).  Each page's type, handwriting and
rubber stamp are typeset as per-character jittered text objects, rendered top-down with Workbench
into ink masks, then baked into the paper shader so the ink sits in the fibres.  Seeded throughout.
"""
import argparse
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
import scene_intro as S  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(ROOT, 'game', 'assets', 'briefing')
TITLE_GD = os.path.join(ROOT, 'game', 'scripts', 'ui', 'title.gd')
CACHE = os.path.join(HERE, 'previews', 'cache')
FONTS = 'C:/Windows/Fonts/'

PW, PH = 0.203, 0.254           # quarto sheet
PX = 16000                      # mask px per metre (16 px/mm)
FONT_SCALE = 1.0 / 0.53       # Blender text size -> em
PITCH = 0.00254                 # 10 cpi pica
LEAD = 0.00423                  # 6 lines per inch
LEFT = 0.024                    # left margin
TOP = 0.020                     # head line from top edge

# typing slips: (page, original, replacement); text between \x01 \x02 is mistyped and x'd out
SLIPS = [
    (2, 'run up the main street.', 'run up the \x01mian\x02 main street.'),
    (3, 'rather than remove.', 'rather than \x01remvoe\x02 remove.'),
]


def parse_pages():
    src = open(TITLE_GD, encoding='utf-8').read()
    pat = re.compile(r'\{"head":\s*"(.*?)",\s*"body":\s*"""(.*?)""",\s*"note":\s*"(.*?)"\}', re.S)
    pages = [dict(head=h, body=b, note=n) for h, b, n in pat.findall(src)]
    assert len(pages) == 4, 'expected 4 pages in title.gd, found %d' % len(pages)
    return pages


# --------------------------------------------------------------------------- typesetting

def _font(name):
    return bpy.data.fonts.load(FONTS + name, check_existing=True)


def _char(body, font, size, x, y, rot=0.0, val=1.0, shear=0.0):
    cu = bpy.data.curves.new('ch', 'FONT')
    cu.body = body
    cu.font = font
    cu.size = size * FONT_SCALE
    cu.shear = shear
    ob = bpy.data.objects.new('ch', cu)
    ob.location = (x, y, 0)
    ob.rotation_euler = (0, 0, rot)
    ob.color = (val, val, val, 1)
    S.link(ob)
    return ob


def typeset(page_no, page, rng):
    """Create text objects for one page. Returns dict layer -> list of objects.
    Page coordinates: origin at sheet centre, metres."""
    cour = _font('courbd.ttf')
    script = _font('segoesc.ttf')
    bold = _font('arialbd.ttf')
    layers = {'type': [], 'note': [], 'stamp': []}
    x0 = -PW / 2 + LEFT
    ytop = PH / 2 - TOP

    def strike(ch, x, y, val):
        jx, jy = rng.normal(0, 0.00005), rng.normal(0, 0.00007)
        o = _char(ch, cour, 0.00423, x + jx, y + jy, rng.normal(0, 0.008), val)
        layers['type'].append(o)

    def type_line(text, x, y, line_fade=1.0):
        col = 0
        mist = False
        for ch in text:
            if ch == '\x01':
                mist = True
                mstart = col
                continue
            if ch == '\x02':
                mist = False
                for k in range(mstart, col):
                    strike('x', x + k * PITCH + rng.normal(0, 0.00004), y, 0.9)
                col += 1  # the typist spaces after the x-ed out word
                continue
            if ch != ' ':
                v = rng.uniform(0.72, 0.95)
                if ch in 'eoaEOs':
                    v = min(1.0, v + 0.15)
                if ch in '.,;:-':
                    v = min(1.0, v + 0.1)
                if rng.random() < 0.015:
                    v = rng.uniform(0.5, 0.62)         # a faint letter, key not struck home
                strike(ch, x + col * PITCH + rng.normal(0, 0.00006), y, v * line_fade)
            col += 1

    # header
    head = page['head']
    hx = -len(head) * PITCH / 2
    type_line(head, hx, ytop)
    type_line('_' * len(head), hx, ytop - 0.0004)
    if page_no == 1:
        ref = 'F/31/LAP'
        type_line(ref, PW / 2 - 0.022 - len(ref) * PITCH, ytop)
    # body
    body = page['body']
    for (p, a, b) in SLIPS:
        if p == page_no and a in body:
            body = body.replace(a, b)
    y = ytop - 3 * LEAD
    for line in body.split('\n'):
        drift = rng.normal(0, 0.00006)            # platen not quite square
        type_line(line, x0 + drift, y, rng.uniform(0.93, 1.0))
        y -= LEAD
    body_end = y
    # page number
    pn = '%d / 4' % page_no
    type_line(pn, -len(pn) * PITCH / 2, -PH / 2 + 0.016)
    # handwritten note
    note = page['note'].strip()
    if note:
        words = note.split()
        lines, cur = [], ''
        for w in words:
            if len(cur) + len(w) + 1 > 30 and cur:
                lines.append(cur); cur = w
            else:
                cur = (cur + ' ' + w).strip()
        lines.append(cur)
        size = 0.0052
        if page_no == 4:
            nx, ny, rot = x0 + 0.004, body_end - 0.010, math.radians(4.0)
        else:
            nx, ny, rot = x0 + 0.050, max(body_end - 0.014, -PH / 2 + 0.040 + len(lines) * 0.0075), math.radians(3.0)
        for li, ln in enumerate(lines):
            cx = nx + li * 0.006
            cy = ny - li * 0.0078
            for w in ln.split(' '):
                o = _char(w, script, size * rng.uniform(0.96, 1.04), cx, cy + rng.normal(0, 0.0003),
                          rot + rng.normal(0, 0.02), rng.uniform(0.85, 1.0), shear=0.22)
                layers['note'].append(o)
                # Advance by the word's real width (script fonts are wide), plus a word space.
                bpy.context.view_layer.update()
                ww = o.dimensions.x
                cx += (ww + size * 0.45) * math.cos(rot)
                cy += (ww + size * 0.45) * math.sin(rot)
    # rubber stamp
    word = 'MOST SECRET' if page_no == 1 else 'SECRET'
    sh = 0.0068
    sw = len(word) * sh * 0.70
    if page_no == 1:
        cx, cy, rot = 0.030, -0.035, math.radians(-7.0)
    else:
        cx, cy, rot = PW / 2 - 0.045, ytop - 0.002, math.radians(rng.uniform(-9, -4) * (1 if page_no % 2 else -0.6))
    root = S.empty('StampRoot', (cx, cy, 0))
    root.rotation_euler = (0, 0, rot)
    t = _char(word, bold, sh * 1.36 * (1.25 if page_no == 1 else 1.0), 0.0, 0.0, 0.0, 1.0)
    t.data.space_character = 1.06
    bpy.context.view_layer.update()
    tw, tht = t.dimensions.x, t.dimensions.y
    t.location = (-tw / 2, -tht / 2 + 0.0002, 0)
    t.parent = root
    layers['stamp'].append(t)
    pad, th = 0.0022, 0.00055
    for k, (ox, oy) in enumerate(((pad, pad), (pad + 0.0011, pad + 0.0011))):
        hw, hh = tw / 2 + ox, tht / 2 + oy
        tk = th if k == 0 else th * 0.6
        vs = [(-hw, -hh, 0), (hw, -hh, 0), (hw, hh, 0), (-hw, hh, 0),
              (-hw + tk, -hh + tk, 0), (hw - tk, -hh + tk, 0), (hw - tk, hh - tk, 0), (-hw + tk, hh - tk, 0)]
        fs = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        fr = S.mesh_obj('StampFrame', vs, fs, None, smooth=False)
        fr.color = (1, 1, 1, 1)
        fr.parent = root
        layers['stamp'].append(fr)
    return layers


def render_masks(page_no, page):
    """Render type/note/stamp layers to a float RGBA array (R type, G note, B stamp, A type blurred)."""
    S.reset()
    rng = np.random.default_rng(310 + page_no)
    layers = typeset(page_no, page, rng)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'FLAT'
    sc.display.shading.color_type = 'OBJECT'
    S._try(sc.display, 'render_aa', '16')
    w = bpy.data.worlds.new('W'); sc.world = w
    w.color = (0, 0, 0)
    sc.view_settings.view_transform = 'Standard'
    sc.render.resolution_x = int(PW * PX)
    sc.render.resolution_y = int(PH * PX)
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'BW'
    sc.render.image_settings.color_depth = '16'
    cd = bpy.data.cameras.new('Ortho')
    cd.type = 'ORTHO'
    cd.ortho_scale = PH
    cd.sensor_fit = 'VERTICAL'
    cam = bpy.data.objects.new('Ortho', cd)
    cam.location = (0, 0, 1)
    S.link(cam)
    sc.camera = cam
    planes = []
    for name in ('type', 'note', 'stamp'):
        for ln, objs in layers.items():
            for o in objs:
                o.hide_render = ln != name
        path = os.path.join(CACHE, 'brief_%d_%s.png' % (page_no, name))
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(path)
        a = np.array(img.pixels[:], np.float32).reshape(img.size[1], img.size[0], -1)[..., 0]
        bpy.data.images.remove(img)
        planes.append(a)
    # display-referred -> linear coverage
    planes = [np.where(p <= 0.04045, p / 12.92, ((p + 0.055) / 1.055) ** 2.4) for p in planes]
    blur = planes[0].copy()
    k = np.exp(-0.5 * (np.arange(-4, 5) / 1.6) ** 2); k /= k.sum()
    for ax in (0, 1):
        blur = np.apply_along_axis(lambda v: np.convolve(v, k, 'same'), ax, blur)
    return np.stack([planes[0], planes[1], planes[2], blur], -1)


# --------------------------------------------------------------------------- page scene

def mat_page(mask_img, fib_img, page_no):
    B = S.NB('Page%d' % page_no)
    uv = B.n('ShaderNodeUVMap').outputs['UV']
    u, v, _ = B.sep(uv)
    uv3 = B.comb(u, v, 0.0)
    f1 = B.image(fib_img, B.vmath('SCALE', uv, scale=1 / S.FIB_TILE))
    fh, ft, fform = B.sepc(f1.outputs['Color'])
    cloud = B.noise(uv3, 55.0, 5.0, 0.6)
    jit = B.noise(uv3, 400.0, 2.0)
    laid = B.math('POWER', B.madd(B.math('SINE', B.mul(B.madd(jit, 0.00012, v), 2 * math.pi / 0.00094)), 0.5, 0.5), 3.0)
    # masks
    mu = B.add(B.mul(u, 1 / PW), 0.5)
    mv = B.add(B.mul(v, 1 / PH), 0.5)
    m = B.image(mask_img, B.comb(mu, mv, 0.0), ext='CLIP')
    mt, mn, ms = B.sepc(m.outputs['Color'])
    mblur = m.outputs['Alpha']
    # ribbon: uneven inking along the fibres, fuzzy edge
    rib = B.maprange(B.add(B.noise(uv3, 2500.0, 3.0, 0.6), B.mul(fh, 0.5)), 0.35, 1.05, 0.55, 1.0, smooth=False)
    typ = B.clamp(B.mul(B.add(B.mul(mt, 0.85), B.mul(mblur, 0.30)), rib))
    # stamp: uneven bite, pale patch, ink heavier at the edges
    sn = B.noise(uv3, 700.0, 4.0, 0.6)
    patch = B.maprange(B.noise(uv3, 60.0, 2.0, 0.5, w=None), 0.38, 0.52, 0.22, 1.0)
    stp = B.clamp(B.mul(B.mul(ms, B.maprange(sn, 0.3, 0.7, 0.45, 1.0)), patch))
    note = B.clamp(B.mul(mn, B.maprange(B.noise(uv3, 900.0, 2.0), 0.3, 0.7, 0.75, 1.0)))
    # edges, holes, crease
    dx = B.math('MINIMUM', B.add(u, PW / 2), B.sub(PW / 2, u))
    dy = B.math('MINIMUM', B.add(v, PH / 2), B.sub(PH / 2, v))
    dedge = B.math('MINIMUM', dx, dy)
    alpha = B.maprange(B.sub(dedge, B.mul(B.noise(uv3, 900.0, 4.0), 0.00035)), 0.00005, 0.00025)
    for hy in (0.040, -0.040):
        dh = B.vmath('DISTANCE', uv3, (-PW / 2 + 0.012, hy, 0.0))
        alpha = B.mul(alpha, B.maprange(dh, 0.0029, 0.0031))
    yc = PH / 2 - PH / 3
    cr = B.math('EXPONENT', B.mul(B.math('ABSOLUTE', B.sub(v, yc)), -1 / 0.0007))
    # colour
    col = B.mix(B.clamp(B.madd(cloud, 0.6, B.mul(ft, 0.5))), (0.66, 0.58, 0.43), (0.76, 0.69, 0.54))
    col = B.mix(B.mul(B.maprange(dedge, 0.03, 0.0), 0.5), col, (0.50, 0.38, 0.21))
    fox = B.mul(B.maprange(B.noise(uv3, 160.0, 3.0, 0.6), 0.68, 0.76), B.madd(B.maprange(dedge, 0.035, 0.0), 0.8, 0.2))
    col = B.mix(B.mul(fox, 0.5), col, (0.40, 0.25, 0.10))
    col = B.mix(B.madd(fh, -0.10, 0.05), col, (0.0, 0.0, 0.0))
    col = B.mix(B.mul(cr, 0.18), col, (0.35, 0.30, 0.22))
    if page_no == 3:
        rc = B.vmath('DISTANCE', uv3, (0.035, -0.070, 0.0))
        ringn = B.noise(uv3, 140.0, 3.0)
        rr = B.add(rc, B.mul(B.sub(ringn, 0.5), 0.003))
        ring = B.mul(B.math('EXPONENT', B.mul(B.math('ABSOLUTE', B.sub(rr, 0.039)), -1 / 0.0009)), 0.55)
        fill = B.mul(B.maprange(rr, 0.039, 0.036), 0.12)
        ring = B.mul(B.add(ring, fill), B.maprange(B.noise(uv3, 35.0, 2.0), 0.3, 0.6, 0.25, 1.0))
        col = B.mix(ring, col, (0.42, 0.26, 0.11))
    if page_no == 1:
        rust = B.mul(B.maprange(B.vmath('DISTANCE', uv3, (-PW / 2 + 0.030, PH / 2 - 0.004, 0.0)), 0.016, 0.006), 0.25)
        rust = B.mul(rust, B.maprange(B.noise(uv3, 300.0, 3.0), 0.4, 0.7))
        col = B.mix(rust, col, (0.38, 0.17, 0.05))
    col = B.mix(stp, col, B.mix(sn, (0.60, 0.05, 0.04), (0.42, 0.03, 0.03)))
    col = B.mix(note, col, (0.025, 0.04, 0.11))
    col = B.mix(typ, col, (0.022, 0.020, 0.022))
    rough = B.add(B.madd(fh, 0.1, 0.7), B.mul(typ, -0.15))
    hgt = B.add(B.madd(fh, 0.7, B.mul(laid, 0.10)), B.madd(cloud, 0.3, B.mul(typ, -0.4)))
    hgt = B.add(hgt, B.mul(cr, -0.8))
    nrm = B.bump(hgt, 0.45, 0.00006)
    bsdf = B.principled(**{'Base Color': col, 'Roughness': rough, 'Normal': nrm,
                           'Sheen Weight': 0.2, 'Sheen Roughness': 0.6})
    tp = B.n('ShaderNodeBsdfTransparent')
    mx = B.n('ShaderNodeMixShader')
    B._in(mx.inputs[0], alpha); B._in(mx.inputs[1], tp.outputs[0]); B._in(mx.inputs[2], bsdf.outputs[0])
    return B.surface(mx.outputs[0])


def build_page_mesh(mat, page_no):
    nx, ny = 161, 201
    xs = np.linspace(-PW / 2, PW / 2, nx)
    ys = np.linspace(-PH / 2, PH / 2, ny)
    X, Y = np.meshgrid(xs, ys)
    rng = np.random.default_rng(40 + page_no)
    yc = PH / 2 - PH / 3
    Z = 0.0003 + 0.0016 * np.exp(-np.abs(Y - yc) / 0.035) + 0.00025 * np.exp(-np.abs(Y - yc) / 0.0012)
    Z += 0.0012 * np.exp(-(PW / 2 - np.abs(X)) / 0.008) * rng.uniform(0.3, 1.0)
    for _ in range(5):
        kx, ky = rng.normal(0, 25, 2)
        Z += rng.uniform(0.00005, 0.00015) * np.sin(kx * X + ky * Y + rng.uniform(0, 6.28))
    Z = np.maximum(Z, 0.0002)   # never dip through the desk
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i)
             for j in range(ny - 1) for i in range(nx - 1)]
    uvs = [(float(a), float(b)) for a, b in zip(X.ravel(), Y.ravel())]
    return S.mesh_obj('Page', verts, faces, mat, smooth=True, uvs=uvs)


def build_clip(page):
    """Rusty gem paper clip straddling the top edge near the left corner."""
    rust = S.NB('RustySteel')
    p = rust.coord('Object')
    n = rust.noise(p, 1500.0, 4.0, 0.6)
    n2 = rust.noise(p, 300.0, 3.0)
    rf = rust.maprange(rust.add(n, rust.mul(n2, 0.6)), 0.55, 0.95)
    col = rust.mix(rf, (0.55, 0.55, 0.56), (0.30, 0.12, 0.04))
    b = rust.principled(**{'Base Color': col, 'Metallic': rust.sub(1.0, rf), 'Roughness': rust.madd(rf, 0.5, 0.3),
                           'Normal': rust.bump(n, 0.4, 0.00005)})
    mat = rust.surface(b.outputs[0])
    W, L = 0.0045, 0.032
    pts2 = [(0, -0.2 * L), (0, 0.85 * L)]
    # outer loop (behind the sheet), inner loop (in front)
    def arc(cx, cy, r, a0, a1, n=10):
        return [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in np.linspace(a0, a1, n)]
    outer = [(-W, 0.0)] + arc(0, L - W, W, 180, 0) + [(W, 0.12 * L)] + arc(-0.0002, 0.12 * L, W * 0.8, 0, -180) + [(-0.75 * W, 0.80 * L)]
    inner = arc(-0.375 * W, 0.80 * L, 0.375 * W, 0, 180)[::-1]
    path = outer + inner[1:] + [(0.0, 0.25 * L)]
    cu = bpy.data.curves.new('Clip', 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = 0.00042
    cu.bevel_resolution = 4
    sp = cu.splines.new('POLY')
    sp.points.add(len(path) - 1)
    for i, (x, y) in enumerate(path):
        z = -0.0005 if i < len(outer) - 3 and y > 0.2 * L else 0.0011
        sp.points[i].co = (x, y, z, 1)
    ob = bpy.data.objects.new('PaperClip', cu)
    ob.data.materials.append(mat)
    S.link(ob)
    ob.location = (-PW / 2 + 0.030, PH / 2 - 0.022, 0.0)
    ob.rotation_euler = (0, 0, math.radians(-6))
    ob.parent = page
    return ob


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', default='1,2,3,4')
    ap.add_argument('--samples', type=int, default=160)
    ap.add_argument('--pct', type=int, default=100)
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--masks-only', action='store_true')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)
    pages = parse_pages()
    for n in [int(x) for x in a.pages.split(',')]:
        masks = render_masks(n, pages[n - 1])
        S.reset()
        S.np_to_image('Mask%d' % n, masks, os.path.join(CACHE, 'brief_mask_%d.exr' % n))
        if a.masks_only:
            continue
        if not os.path.exists(os.path.join(CACHE, 'paper_fibre.exr')):
            S.fibre_image()
        S.reset()
        mimg = bpy.data.images.load(os.path.join(CACHE, 'brief_mask_%d.exr' % n))
        mimg.colorspace_settings.name = 'Non-Color'; mimg.alpha_mode = 'CHANNEL_PACKED'
        fib = bpy.data.images.load(os.path.join(CACHE, 'paper_fibre.exr'))
        fib.colorspace_settings.name = 'Non-Color'; fib.alpha_mode = 'CHANNEL_PACKED'
        _build_and_render(n, mimg, fib, a)


def _build_and_render(n, mimg, fib, a):
    # build without resetting (reset would drop the loaded images)
    S.build_desk(S.mat_wood())
    page = build_page_mesh(mat_page(mimg, fib, n), n)
    rng = np.random.default_rng(70 + n)
    page.rotation_euler = (0, 0, math.radians(rng.uniform(-3.0, 3.0)))
    page.location = (rng.uniform(-0.006, 0.006), rng.uniform(-0.004, 0.004), 0.0)
    if n == 1:
        build_clip(page)
    lamp = S.light('Lamp', 'SPOT', Vector((-0.90, 0.55, 0.62)), 22.0, (1.0, 0.70, 0.45), size=0.07)
    lamp.data.spot_size = math.radians(30)
    lamp.data.spot_blend = 1.0
    S.aim(lamp, (-0.02, 0.03, 0.0))
    fill = S.light('Fill', 'AREA', Vector((0.4, -0.5, 0.6)), 0.6, (0.9, 0.85, 0.8), size=0.6)
    S.aim(fill, (0, 0, 0))
    S.world(1.0)
    focus = S.empty('Focus', (0, 0, 0.0005))
    cam = S.camera('Cam', 50.0, 8.0, focus)
    cam.location = (0.0, -0.165, 0.645)
    tgt = S.empty('Tgt', (0.0, 0.002, 0.0))
    S.track(cam, tgt)
    S.render_settings(a.samples, a.pct, 'GPU', 0.01)
    sc = bpy.context.scene
    sc.render.use_motion_blur = False
    sc.view_settings.exposure = 0.6
    sc.render.filepath = os.path.join(a.out, 'page_%d.png' % n)
    bpy.ops.render.render(write_still=True)
    print('PAGE', n, 'written', flush=True)


main()
