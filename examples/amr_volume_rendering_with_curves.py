import numpy as np
import yt

import yt_idv
from yt_idv.scene_components.curves import (  # NOQA
    CurveCollectionRendering,
    CurveRendering,
)
from yt_idv.scene_data.curve import CurveCollection, CurveData  # NOQA

ds = yt.load_sample("IsolatedGalaxy")

rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, "density", no_ghost=True)

# partial circle in the x-y plane in model space
r = 0.25
c = np.array([0.5, 0.5, 0.5])
theta = np.linspace(0, 2 * np.pi * 0.75, 50)
x = r * np.cos(theta) + c[0]
y = r * np.sin(theta) + c[1]
z = np.full(x.shape, c[2])
curve = np.column_stack([x, y, z])

curved = CurveData()
curved.add_data(curve)
curver = CurveRendering(data=curved, curve_rgba=(1.0, 0.0, 0.0, 1.0))
rc.scene.data_objects.append(curved)
rc.scene.components.append(curver)

# a collection of curves
curve_collection = CurveCollection()
curve_collection.add_curve(np.column_stack([x - 0.25, y - 0.25, z - 0.25]))
curve_collection.add_curve(np.column_stack([x + 0.25, y + 0.25, z + 0.25]))
curve_collection.add_data()

cc_render = CurveCollectionRendering(data=curve_collection)

rc.scene.data_objects.append(curve_collection)
rc.scene.components.append(cc_render)

rc.run()
