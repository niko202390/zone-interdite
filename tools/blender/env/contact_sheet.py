"""Tile preview PNGs into one sheet (runs inside Blender for PNG decoding).
blender --background --factory-startup --python contact_sheet.py -- out.png cols a.png b.png ..."""
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
out, cols, files = argv[0], int(argv[1]), argv[2:]
tiles = []
TW, TH = 640, 360
for f in files:
    im = bpy.data.images.load(f)
    w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, im.channels)[..., :3]
    ys = (np.arange(TH) * h / TH).astype(int)
    xs = (np.arange(TW) * w / TW).astype(int)
    tiles.append(px[ys][:, xs])
rows = (len(tiles) + cols - 1) // cols
sheet = np.zeros((rows * TH, cols * TW, 4), np.float32)
sheet[..., 3] = 1
for i, t in enumerate(tiles):
    r, c = divmod(i, cols)
    # blender pixel rows are bottom-up: place row 0 at the top of the sheet
    sheet[(rows - 1 - r) * TH:(rows - r) * TH, c * TW:(c + 1) * TW, :3] = t
img = bpy.data.images.new("sheet", cols * TW, rows * TH)
img.pixels.foreach_set(sheet.ravel())
img.filepath_raw = out
img.file_format = "PNG"
img.save()
print("sheet", out)
