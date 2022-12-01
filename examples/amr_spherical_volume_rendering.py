import numpy as np
import yt
import unyt
import yt_idv

# yt reminder: phi is the polar angle (0 to 2pi)
# theta is the angle from north (0 to pi)

bbox = np.array([[0.0, 1.0],  # r
                 [0.0, np.pi],  # theta
                 [0.0, 2*np.pi]])  # phi
sz = (256, 256, 256)
fake_data = {"density": np.random.random(sz)}
ds = yt.load_uniform_grid(
    fake_data,
    sz,
    bbox=bbox,
    nprocs=4096,
    geometry=("spherical", ("r", "theta", "phi")),
    length_unit="m",
)

def _shell_fragment(field, data):
    center_phi = unyt.unyt_quantity(np.pi/2, "")
    center_theta = unyt.unyt_quantity(np.pi/2, "")
    center_r = unyt.unyt_quantity(0.5, "m")

    dr = np.abs(data["index", "r"] - center_r)
    shell = np.exp(-(dr / 0.2))
    minval = 0.01
    shell[shell < 0.1] = minval

    # neglecting the periodicity in phi here!
    phi = data["index", "phi"] # polar 0:2pi angle
    theta = data["index", "theta"]  # azimuthal  0:pi angle
    dphi = np.abs(phi - center_phi)
    dtheta = np.abs(theta - center_theta)
    dist = 45 * np.pi / 180.
    shell[dphi > dist / 2.] = 0.05
    shell[dtheta > dist / 2.] = 0.05

    return shell


yt.add_field(
    name=("stream", "shell_fragment"),
    function=_shell_fragment,
    sampling_type="local",
    units="",
)

rc = yt_idv.render_context(height=800, width=800, gui=True)
dd = ds.all_data()
dd.max_level = 1
# sg = rc.add_scene(ds, ("index", "r"), no_ghost=True)
# sg = rc.add_scene(ds, ("index", "theta"), no_ghost=True)
# sg = rc.add_scene(ds, ("index", "phi"), no_ghost=True)
sg = rc.add_scene(ds, ("stream", "shell_fragment"), no_ghost=True)
rc.run()
