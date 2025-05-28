"""
Sometimes you want more control over data normalization and color-mapping. This
example demonstrates how to do that with BlockCollection data.
"""

import numpy as np
import yt

import yt_idv
from yt_idv.cameras.trackball_camera import TrackballCamera
from yt_idv.scene_components.blocks import BlockRendering
from yt_idv.scene_data.block_collection import BlockCollection
from yt_idv.scene_graph import SceneGraph

# create some data
shp = (32, 32, 32)
data = {"constant_field": np.full(shape=shp, fill_value=5.0)}
ds = yt.load_uniform_grid(data, shp, length_unit=1)


rc = yt_idv.render_context(height=800, width=800, gui=True)
c = TrackballCamera.from_dataset(ds)
rc.scene = SceneGraph(camera=c)

# the following BlockCollection initialization does the following:
#  1. sets the min, max values to be used for data normalization when
#     loading textures
#  2. specifies that those min, max vals should not be re-computed
#     (compute_min_max=False)
#  3. specifies that the data should always be normalized -- usually
#     normalization is skipped for constant fields.
block_coll = BlockCollection(
    data_source=ds.all_data(),
    min_val=0.0,
    max_val=10.0,
    compute_min_max=False,
    always_normalize=True,
)
block_coll.add_data(("stream", "constant_field"), no_ghost=True)
rc.scene.data_objects.append(block_coll)

# set fixed cmap ranges. Data are in normalized space. A constant data value of 5.
# (the fill value used above) with [min val, max val] of [0., 10.] normalizes to 0.5.
# So setting the fixed cmap min and max to 0 and 1 will result in a constant color
# at the middle of whatever colormap is selected.
block_rendering = BlockRendering(
    data=block_coll,
    fixed_cmap_min=0.0,
    fixed_cmap_max=1.0,
    cmap_log=False,
)

rc.scene.components.append(block_rendering)

rc.run()
