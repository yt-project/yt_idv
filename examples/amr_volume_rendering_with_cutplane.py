# example showing how to add a static cutting plane to an amr rendering
import yt
import numpy as np
import yt_idv

from yt_idv.scene_components.planes import Plane  # NOQA
from yt_idv.scene_data.plane import PlaneData  # NOQA

ds = yt.load_sample("IsolatedGalaxy")

# add the volume rendering to the scene
rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, "density", no_ghost=True)

# add a static cutting plane (independent of the volume rendering)
normal = np.array([1., 1., 0.], dtype='float64')
center = ds.domain_center.to('code_length').value
cut = ds.cutting(normal, center)
cut_data = PlaneData(data_source=cut)
cut_data.add_data(("enzo", "Density"), 1., (400, 400))
cut_render = Plane(data=cut_data, cmap_log=True)
rc.scene.data_objects.append(cut_data)
rc.scene.components.append(cut_render)

rc.run()
