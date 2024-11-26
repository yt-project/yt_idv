import sys

import numpy as np
import yt

import yt_idv

# yt reminder: phi is the polar angle (0 to 2pi)
# theta is the angle from north (0 to pi)


# coord ordering here will be r, phi, theta

bbox_options = {
    "partial": np.array([[0.5, 1.0], [0.0, np.pi / 3], [np.pi / 4, np.pi / 2]]),
    "whole": np.array([[0., 1.0], [0.0, 2 * np.pi], [0, np.pi]]),
    "north_hemi": np.array([[0.1, 1.0], [0.0, 2 * np.pi], [0, 0.5 * np.pi]]),
    "south_hemi": np.array([[0.1, 1.0], [0.0, 2 * np.pi], [0.5 * np.pi, np.pi]]),
    "ew_hemi": np.array([[0.1, 1.0], [0.0, np.pi], [0.0, np.pi]]),
}


sz = (256, 256, 256)
fake_data = {"density": np.random.random(sz)}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        bbox_type = sys.argv[1]
    else:
        bbox_type = "partial"

    bbox = bbox_options[bbox_type]

    ds = yt.load_uniform_grid(
        fake_data,
        sz,
        bbox=bbox,
        nprocs=64,
        geometry=("spherical", ("r", "phi", "theta")),
        length_unit="m",
    )

    rc = yt_idv.render_context(height=800, width=800, gui=True)
    dd = ds.all_data()
    dd.max_level = 1
    # sg = rc.add_scene(ds, ("index", "r"), no_ghost=True)
    # sg = rc.add_scene(ds, ("index", "theta"), no_ghost=True)
    sg = rc.add_scene(ds, ("index", "phi"), no_ghost=True)
    # sg = rc.add_scene(ds, ("stream", "density"), no_ghost=True)
    sg.camera.focus = [0.0, 0.0, 0.0]
    rc.run()
