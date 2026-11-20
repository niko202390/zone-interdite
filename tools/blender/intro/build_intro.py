"""Zone Interdite opening film - entry point.

Run headless:
  blender --background --factory-startup --python-exit-code 1 --python build_intro.py -- <mode> [options]

Modes:
  still   --frames 40,130,250 [--samples 64] [--pct 50]   -> previews/still_####.png
  anim    [--shots 1,2,3,4] [--samples 48] [--force]      -> previews/frames/f####.png (resumable)
  final   [--samples 256]                                 -> game/assets/video/intro_final.png
  encode                                                  -> game/assets/video/intro.ogv (Theora)
  cues                                                    -> game/assets/video/intro_cues.json
  all     cues + anim + final + encode
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import scene_intro as S  # noqa: E402
import shots as SH  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
VIDEO = os.path.join(ROOT, 'game', 'assets', 'video')
PREV = os.path.join(HERE, 'previews')
FRAMES_DIR = os.path.join(PREV, 'frames')


def parse():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['still', 'anim', 'final', 'encode', 'cues', 'all'])
    ap.add_argument('--frames', default='')
    ap.add_argument('--shots', default='1,2,3,4')
    ap.add_argument('--samples', type=int, default=48)
    ap.add_argument('--final-samples', type=int, default=320)
    ap.add_argument('--pct', type=int, default=100)
    ap.add_argument('--threshold', type=float, default=0.03)
    ap.add_argument('--device', default='GPU')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--bitrate', type=int, default=17000)
    return ap.parse_args(argv)


def shot_of(f):
    for k, (a, b) in S.SHOTS.items():
        if a <= f <= b:
            return k
    return 4


def builder_key(f):
    return 1 if shot_of(f) == 1 else (2 if shot_of(f) == 2 else 3)


def build_for(key, a):
    S.reset()
    {1: SH.shot1, 2: SH.shot2, 3: SH.shot34}[key]()
    S.render_settings(a.samples, a.pct, a.device, a.threshold)


def render_frames(frames, a, out_fmt, tag=''):
    groups = {}
    for f in frames:
        groups.setdefault(builder_key(f), []).append(f)
    for key in sorted(groups):
        todo = [f for f in groups[key] if a.force or not os.path.exists(out_fmt % f)]
        if not todo:
            continue
        t0 = time.time()
        build_for(key, a)
        print('built shot group %d in %.1fs' % (key, time.time() - t0))
        sc = bpy.context.scene
        for f in todo:
            t1 = time.time()
            sc.frame_set(f)
            sc.render.filepath = out_fmt % f
            bpy.ops.render.render(write_still=True)
            print('FRAME %d %s %.1fs' % (f, tag, time.time() - t1), flush=True)


def write_cues():
    os.makedirs(VIDEO, exist_ok=True)
    cues = {k: round(v, 3) for k, v in S.CUES.items()}
    with open(os.path.join(VIDEO, 'intro_cues.json'), 'w') as fh:
        json.dump(cues, fh, indent=2)
        fh.write('\n')
    print('cues', cues)


def encode(a):
    S.reset()
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.sequence_editor_create()
    files = sorted(os.listdir(FRAMES_DIR))
    files = [f for f in files if f.endswith('.png')]
    assert len(files) == S.FRAMES, 'expected %d frames, found %d' % (S.FRAMES, len(files))
    strips = sc.sequence_editor.strips if hasattr(sc.sequence_editor, 'strips') else sc.sequence_editor.sequences
    st = strips.new_image('frames', os.path.join(FRAMES_DIR, files[0]), 1, 1)
    for fn in files[1:]:
        st.elements.append(fn)
    st.colorspace_settings.name = 'sRGB'
    sc.frame_start, sc.frame_end = 1, S.FRAMES
    sc.render.use_sequencer = True
    im = sc.render.image_settings
    try:
        im.media_type = 'VIDEO'
    except Exception:
        pass
    im.file_format = 'FFMPEG'
    ff = sc.render.ffmpeg
    ff.format = 'OGG'
    ff.codec = 'THEORA'
    try:
        ff.constant_rate_factor = 'NONE'
    except Exception:
        pass
    ff.video_bitrate = a.bitrate
    ff.maxrate = int(a.bitrate * 1.5)
    ff.minrate = 0
    ff.buffersize = 4096
    ff.gopsize = 12
    ff.audio_codec = 'NONE'
    out = os.path.join(VIDEO, 'intro.ogv')
    tmp = os.path.join(VIDEO, 'intro_tmp')
    sc.render.filepath = tmp
    bpy.ops.render.render(animation=True)
    produced = [f for f in os.listdir(VIDEO) if f.startswith('intro_tmp')]
    assert produced, 'encoder wrote nothing'
    if os.path.exists(out):
        os.remove(out)
    os.replace(os.path.join(VIDEO, produced[0]), out)
    print('ENCODED', out, os.path.getsize(out) / 1e6, 'MB')


def main():
    a = parse()
    os.makedirs(PREV, exist_ok=True)
    os.makedirs(VIDEO, exist_ok=True)
    t0 = time.time()
    if a.mode in ('cues', 'all'):
        write_cues()
    if a.mode == 'still':
        a.force = True
        frames = [int(x) for x in a.frames.split(',') if x]
        render_frames(frames, a, os.path.join(PREV, 'still_%04d.png'), 'still')
    if a.mode in ('anim', 'all'):
        os.makedirs(FRAMES_DIR, exist_ok=True)
        want = set(int(x) for x in a.shots.split(','))
        frames = [f for f in range(1, S.FRAMES + 1) if shot_of(f) in want]
        if a.frames:
            lo, hi = (int(x) for x in a.frames.split('-'))
            frames = [f for f in frames if lo <= f <= hi]
        render_frames(frames, a, os.path.join(FRAMES_DIR, 'f%04d.png'), 'anim')
    if a.mode in ('final', 'all'):
        a.samples = a.final_samples
        a.threshold = min(a.threshold, 0.01)
        a.force = True
        render_frames([S.FRAMES], a, os.path.join(VIDEO, 'intro_final_%04d.png'), 'final')
        src = os.path.join(VIDEO, 'intro_final_%04d.png' % S.FRAMES)
        os.replace(src, os.path.join(VIDEO, 'intro_final.png'))
    if a.mode in ('encode', 'all'):
        encode(a)
    print('DONE %s in %.1f min' % (a.mode, (time.time() - t0) / 60))


main()
