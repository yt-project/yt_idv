import os
os.environ["PYOPENGL_PLATFORM"] = "egl"
import numpy as np
import yt
import yt_idv

ds = yt.load_sample("IsolatedGalaxy")
dd = ds.all_data()

rc = yt_idv.EGLRenderingContext()
sg = yt_idv.SceneGraph.from_ds(dd, "density", no_ghost=True)
rc.scene = sg

image = rc.draw()
yt.write_bitmap(image, "step1.png")

sg.camera.move_forward(1.5)

image = rc.draw()
yt.write_bitmap(image, "step2.png")
