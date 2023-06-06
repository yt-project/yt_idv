import numpy as np
import yt
from yt.units import Mpc
from yt.visualization.api import Streamlines

import yt_idv
from yt_idv.scene_components.curves import (  # NOQA
    CurveCollectionRendering,
    CurveRendering,
)
from yt_idv.scene_data.curve import CurveCollection, CurveData  # NOQA

ds = yt.load_sample("IsolatedGalaxy")

# generate some streamlines
# (see https://yt-project.org/doc/visualizing/streamlines.html)
c = ds.domain_center  # the center of the box
N = 10  # number of streamlines
scale = ds.domain_width[0]  # scale of streamlines relative to boxsize
pos_dx = np.random.random((N, 3)) * scale - scale / 2.0
pos = c + pos_dx  # starting positions

streamlines = Streamlines(
    ds,
    pos,
    ("gas", "velocity_x"),
    ("gas", "velocity_y"),
    ("gas", "velocity_z"),
    length=1.0 * Mpc,
    get_magnitude=True,
)

streamlines.integrate_through_volume()

# initialize the rendering context and scene
rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, "density", no_ghost=True)


# add a single streamline as a single curve
curved = CurveData()
curved.add_data(streamlines.streamlines[0])
curve_render = CurveRendering(data=curved, curve_rgba=(1.0, 0.0, 0.0, 1.0))
curve_render.display_name = "single streamline"
rc.scene.data_objects.append(curved)
rc.scene.components.append(curve_render)

# add the remaining streamlines as a collection of curves
curve_collection = CurveCollection()
for stream in streamlines.streamlines[1:]:
    stream = stream[np.all(stream != 0.0, axis=1)]
    curve_collection.add_curve(stream)
curve_collection.add_data()  # call add_data() after done adding curves

cc_render = CurveCollectionRendering(data=curve_collection)
cc_render.display_name = "multiple streamlines"
rc.scene.data_objects.append(curve_collection)
rc.scene.components.append(cc_render)

rc.run()
