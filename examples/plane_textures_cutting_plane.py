import numpy as np
import yt

from yt_idv import render_context
from yt_idv.cameras.trackball_camera import TrackballCamera
from yt_idv.scene_annotations.grid_outlines import GridOutlines  # NOQA
from yt_idv.scene_components.plane import Plane  # NOQA
from yt_idv.scene_data.grid_positions import GridPositions  # NOQA
from yt_idv.scene_data.plane import PlaneData  # NOQA
from yt_idv.scene_graph import SceneGraph

rc = render_context(height=800, width=800, gui=True)
c = TrackballCamera(position=[3.5, 3.5, 3.5], focus=[0.0, 0.0, 0.0])
rc.scene = SceneGraph(camera=c)

ds = yt.load("Enzo_64/RD0005/RedshiftOutput0005")

normal = np.array([1.0, 1.0, 0.0], dtype="float64")
center = ds.domain_center.to("code_length").value
cut = ds.cutting(normal, center)
cut_data = PlaneData(data_source=cut)
cut_data.add_data(("enzo", "Density"), 1.0, (400, 400))
cut_render = Plane(data=cut_data, cmap_log=True)

rc.scene.data_objects.append(cut_data)
rc.scene.components.append(cut_render)

# add grids
grids = ds.index.grids.tolist()
gp = GridPositions(grid_list=grids)
rc.scene.data_objects.append(gp)
go = GridOutlines(data=gp)
rc.scene.components.append(go)

rc.run()
