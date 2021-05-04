import yt
from yt_idv import render_context
from yt_idv.cameras.trackball_camera import TrackballCamera
from yt_idv.scene_graph import SceneGraph
from unyt import unyt_quantity
import numpy as np


from yt_idv.scene_components.plane import Plane  # NOQA
from yt_idv.scene_data.plane import PlaneData  # NOQA


rc = render_context(height=800, width=800, gui=True)
c = TrackballCamera(position=[3.5, 3.5, 3.5], focus=[0.0, 0.0, 0.0])
rc.scene = SceneGraph(camera=c)

ds = yt.load("Enzo_64/RD0005/RedshiftOutput0005")

for slice_axis in [0, 1]:
    slc = ds.slice(slice_axis, 0.5)
    slice_data = PlaneData(data_source=slc)
    slice_data.add_data(("enzo", "Density"), 1.0, (400, 400))
    slice_render = Plane(data=slice_data, cmap_log=True)

    rc.scene.data_objects.append(slice_data)
    rc.scene.components.append(slice_render)

# another slice covering a smaller distance
slc = ds.slice(2, 0.5)
slice_data = PlaneData(data_source=slc)
slice_data.add_data(
    ("enzo", "Density"),
    unyt_quantity(45, "Mpc"),
    (400, 400),
    height=unyt_quantity(45, "Mpc"),
)
slice_render = Plane(data=slice_data, cmap_log=True)
rc.scene.data_objects.append(slice_data)
rc.scene.components.append(slice_render)

# another small slice, at a different center
slc = ds.slice(2, 0.25)
slice_data = PlaneData(data_source=slc)
slice_data.add_data(
    ("enzo", "Density"),
    unyt_quantity(45, "Mpc"),
    (400, 400),
    height=unyt_quantity(45, "Mpc"),
    center=np.array([0.75, 0.75, 0.25]),
)
slice_render = Plane(data=slice_data, cmap_log=True)
rc.scene.data_objects.append(slice_data)
rc.scene.components.append(slice_render)

rc.run()
