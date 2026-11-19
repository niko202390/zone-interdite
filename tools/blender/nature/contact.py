"""Contact sheet of previews: blender --background --python contact.py -- out.png cols name1 name2 ..."""
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PV = os.path.join(HERE, "previews")
argv = sys.argv[sys.argv.index("--") + 1:]
out, ncol, names = argv[0], int(argv[1]), argv[2:]
tiles = []
for n in names:
    im = bpy.data.images.load(os.path.join(PV, f"{n}.png"))
    w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, 4)
    tiles.append(a[::2, ::2])
th, tw = tiles[0].shape[:2]
nrow = (len(tiles) + ncol - 1) // ncol
sheet = np.zeros((nrow * th, ncol * tw, 4), np.float32)
sheet[..., 3] = 1
for i, t in enumerate(tiles):
    r, c = divmod(i, ncol)
    y0 = (nrow - 1 - r) * th          # blender pixel rows start at the bottom
    sheet[y0:y0 + t.shape[0], c * tw:c * tw + t.shape[1]] = t[:th, :tw]
img = bpy.data.images.new("sheet", ncol * tw, nrow * th)
img.pixels[:] = sheet.ravel()
img.filepath_raw = os.path.join(PV, out)
img.file_format = "PNG"
img.save()
