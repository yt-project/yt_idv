import numpy as np
import yt

import yt_idv
from yt_idv.scene_components.curves import CurveRendering  # NOQA
from yt_idv.scene_data.curve import CurveData  # NOQA

ds = yt.load_sample("IsolatedGalaxy")

rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, "density", no_ghost=True)

# circle in the x-y plane in model space
r = 0.25
c = np.array([0.5, 0.5, 0.5])
theta = np.linspace(0, 2*np.pi, 20)
x = r * np.cos(theta) + c[0]
y = r * np.sin(theta) + c[1]
z = np.full(x.shape, c[2])
curve = np.column_stack([x,y,z])

curved = CurveData()
curved.add_data(curve)
curver = CurveRendering(data=curved, curve_rgba=(1.,0., 0., 1.))
rc.scene.data_objects.append(curved)
rc.scene.components.append(curver)
rc.run()


rc.run()
