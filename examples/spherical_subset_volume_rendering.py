import numpy as np
import yt

import yt_idv

# Spherical Test (to line 20)

NDIM = 32

bbox = np.array(
    [[0.0, 0.5], [np.pi / 8, 2 * np.pi / 8], [2 * np.pi / 8, 3 * np.pi / 8]]
)

fake_data = {"density": np.random.random((NDIM, NDIM, NDIM))}
ds = yt.load_uniform_grid(
    fake_data,
    [NDIM, NDIM, NDIM],
    bbox=bbox,
    geometry="spherical",
)

rc = yt_idv.render_context(height=800, width=800, gui=True)
dd = ds.all_data()
dd.max_level = 1
sg = rc.add_scene(ds, ("index", "r"), no_ghost=True)
sg.camera.focus = [0.0, 0.0, 0.0]
rc.run()

# Cartesian Test (to line 25)
# ds = yt.load_sample("IsolatedGalaxy")
# rc = yt_idv.render_context(height=800, width=800, gui=True)
# sg = rc.add_scene(ds, "density", no_ghost=True)
# rc.run()
