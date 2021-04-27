
import numpy as np
from PIL import Image
import requests



# plots arbitrary data on a plane

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
im_url = "https://raw.githubusercontent.com/yt-project/website/master/img/yt_logo.png"
# load, convert to greyscale, ignore the resulting alpha channel:
im = np.array(Image.open(requests.get(im_url, stream=True).raw).convert('LA'))[:, :, 0]

# create a plane for our 2d data, add the data
image_plane = BasePlane(
    normal = np.array([1., 1., 0.]),
    center = np.array([0., 0., 0.]),
    data = im,
    width = im.shape[0],
    height = im.shape[1]
)
image_plane.add_data()

# add the rendering object, data to the scene
plane_render = Plane(data=image_plane, cmap_log=False)
rc.scene.data_objects.append(image_plane)
rc.scene.components.append(plane_render)

rc.run()
