import yt

import yt_idv

N = 400

ds = yt.load_sample("HiresIsolatedGalaxy")
c = [0.53, 0.53, 0.53]

rc = yt_idv.render_context("egl", width=1024, height=1024)
sc = rc.add_scene(ds, "density", no_ghost=False)
sc.components[0].render_method = "projection"
sc.camera.focus = c
sc.camera.position = [0.45, 0.44, 0.43]

ds = (sc.camera.focus - sc.camera.position) / N

for _ in range(N):
    sc.components[0].cmap_min = sc.components[0].cmap_max = None
    sc.camera.position = sc.camera.position + ds
    sc.camera._update_matrices()
    rc.snap()
