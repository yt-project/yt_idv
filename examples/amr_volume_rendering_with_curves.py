import yt
import numpy as np
import yt_idv

from yt_idv.scene_components.curves import CurveRendering  # NOQA
from yt_idv.scene_data.line import CurveData  # NOQA

ds = yt.load_sample("IsolatedGalaxy")

rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, "density", no_ghost=True)




npcurve = np.array([(0,0,0), (0.5,0.5,0.24), (.8,.8,.8)])
curved = CurveData()
curved.add_data(npcurve)
curver = CurveRendering(data=curved)
rc.scene.data_objects.append(curved)
rc.scene.components.append(curver)
rc.run()


rc.run()
