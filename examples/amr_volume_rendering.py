import numpy as np
import pyglet
import yt
import yt_idv

ds = yt.load_sample("IsolatedGalaxy")

sg = yt_idv.SceneGraph.from_ds(ds, "density", no_ghost=True)
rc = yt_idv.PygletRenderingContext(always_on_top = True, gui = True, height = 800, width = 800, scene = sg)
pyglet.app.run()
