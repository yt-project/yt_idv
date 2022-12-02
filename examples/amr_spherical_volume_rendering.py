import numpy as np
import yt

import yt_idv

# yt reminder: phi is the polar angle (0 to 2pi)
# theta is the angle from north (0 to pi)

# coord ordering here will be r, phi, theta
bbox = np.array([[0.5, 1.0], [0.0, np.pi / 4], [np.pi / 4, np.pi / 2]])
sz = (256, 256, 256)
fake_data = {"density": np.random.random(sz)}
ds = yt.load_uniform_grid(
    fake_data,
    sz,
    bbox=bbox,
    nprocs=4096,
    geometry=("spherical", ("r", "phi", "theta")),
    length_unit="m",
)

rc = yt_idv.render_context(height=800, width=800, gui=True)
dd = ds.all_data()
dd.max_level = 1
sg = rc.add_scene(ds, ("index", "r"), no_ghost=True)
# sg = rc.add_scene(ds, ("index", "theta"), no_ghost=True)
# sg = rc.add_scene(ds, ("index", "phi"), no_ghost=True)
rc.run()
