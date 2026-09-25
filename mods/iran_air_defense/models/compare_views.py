import sys
import bpy

sys.path.insert(0, sys.argv[-1])
from irad_kit import render

out = sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=f"{out}/IRAD_Bavar373_LN.blend")
scn = bpy.context.scene
for frame, name, kw in (
    (
        100,
        "cmp_side",
        dict(target=(0, -1.0, 3.2), dist=21, az=92, elev=3, res=(1100, 740)),
    ),
    (
        0,
        "cmp_travel",
        dict(target=(0, 0.0, 2.2), dist=17, az=55, elev=6, res=(1100, 620)),
    ),
    (
        100,
        "cmp_erect",
        dict(target=(0, -1.5, 3.4), dist=19, az=60, elev=6, res=(1100, 620)),
    ),
):
    scn.frame_set(frame)
    render(f"{out}/{name}.png", **kw)
