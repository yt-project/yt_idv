# plots arbitrary data on a plane

import numpy as np
from yt_idv import render_context
from yt_idv.cameras.trackball_camera import TrackballCamera
from yt_idv.scene_graph import SceneGraph
from yt_idv.scene_components.planes import Plane
from yt_idv.scene_data.plane import BasePlane

# create an empty scene with a camera
rc = render_context(height=800, width=800, gui=True)
c = TrackballCamera(position=[3.5, 3.5, 3.5], focus=[0.0, 0.0, 0.0])
rc.scene = SceneGraph(camera=c)

# create some arbitrary 2d data
x, y = np.meshgrid(np.linspace(0, 1, 200), np.linspace(0, 1, 300))
dist = np.sqrt((x-0.5)**2 + (y-0.5)**2)
test_data = np.exp(-(dist/0.25) ** 2)

# create a plane for our 2d data, add the data
image_plane = BasePlane(
    normal=np.array([1., 0., 0.]),
    center=np.array([0., 0., 0.]),
    data=test_data,
    width=1,
    height=1,
)
image_plane.east_vec = np.array([0., 1., 0.])
image_plane.north_vec = np.array([0., 0., 1.])
image_plane.add_data()

# add the rendering object, data to the scene
plane_render = Plane(data=image_plane, cmap_log=False)
rc.scene.data_objects.append(image_plane)
rc.scene.components.append(plane_render)

rc.run()
