import numpy as np
import yt

import yt_idv

# Spherical Test (to line 20)
fake_data = {"density": np.random.random((256, 256, 256))}
ds = yt.load_uniform_grid(
    fake_data,
    [256, 256, 256],
    bbox=np.array([[0.0, 1.0], [0.0, np.pi], [0.0, 2 * np.pi]]),
    nprocs=4096,
    geometry="spherical",
)

rc = yt_idv.render_context(height=800, width=800, gui=True)
dd = ds.all_data()
dd.max_level = 1
sg = rc.add_scene(ds, ("index", "r"), no_ghost=True)
rc.run()

# Cartesian Test (to line 25)
# ds = yt.load_sample("IsolatedGalaxy")
# rc = yt_idv.render_context(height=800, width=800, gui=True)
# sg = rc.add_scene(ds, "density", no_ghost=True)
# rc.run()
