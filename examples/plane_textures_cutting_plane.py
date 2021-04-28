import yt
import numpy as np
from yt_idv import render_context
from yt_idv.cameras.trackball_camera import TrackballCamera
from yt_idv.scene_graph import SceneGraph


from yt_idv.scene_components.planes import Plane  # NOQA
from yt_idv.scene_data.plane import PlaneData  # NOQA


rc = render_context(height=800, width=800, gui=True)
c = TrackballCamera(position=[3.5, 3.5, 3.5], focus=[0.0, 0.0, 0.0])
rc.scene = SceneGraph(camera=c)

ds = yt.load("Enzo_64/RD0005/RedshiftOutput0005")

normal = np.array([1., 1., 0.], dtype='float64')
center = ds.domain_center.to('code_length').value
cut = ds.cutting(normal, center)
cut_data = PlaneData(data_source=cut)
cut_data.add_data(("enzo", "Density"), 1., (400, 400))
cut_render = Plane(data=cut_data, cmap_log=True)

rc.scene.data_objects.append(cut_data)
rc.scene.components.append(cut_render)

rc.run()
