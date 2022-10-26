import numpy as np
import requests
import yt
from PIL import Image

import yt_idv
from yt_idv.scene_annotations.grid_outlines import GridOutlines  # NOQA
from yt_idv.scene_components.plane import Plane
from yt_idv.scene_data.grid_positions import GridPositions  # NOQA
from yt_idv.scene_data.plane import BasePlane

# create a volume rendering
ds = yt.load("IsolatedGalaxy/galaxy0030/galaxy0030")
rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, "density", no_ghost=True)

# pull in an image file, convert to greyscale and ignore resulting alpha channel
im_url = "https://raw.githubusercontent.com/yt-project/website/master/img/yt_logo.png"
im = np.array(Image.open(requests.get(im_url, stream=True).raw).convert("LA"))[:, :, 0]

# create a plane for our 2d data, add the data
image_plane = BasePlane(
    normal=np.array([1.0, 0.0, 0.0]),
    center=np.array([0.5, 0.0, 0.0]),
    data=im,
    width=1,
    height=1,
)
image_plane.east_vec = np.array([0.0, 1.0, 0.0])
image_plane.north_vec = np.array([0.0, 0.0, 1.0])
image_plane.add_data()

# add the rendering object, data to the scene
plane_render = Plane(data=image_plane, cmap_log=False)
rc.scene.data_objects.append(image_plane)
rc.scene.components.append(plane_render)

# add grids
grids = ds.index.grids.tolist()
gp = GridPositions(grid_list=grids)
rc.scene.data_objects.append(gp)
go = GridOutlines(data=gp)
rc.scene.components.append(go)


rc.run()
