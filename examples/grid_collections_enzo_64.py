import yt

import yt_idv
from yt_idv.cameras.trackball_camera import TrackballCamera
from yt_idv.scene_components.blocks import GridCollectionRendering
from yt_idv.scene_data.block_collection import GridCollection
from yt_idv.scene_graph import SceneGraph

ds = yt.load_sample("Enzo_64")

# define a couple of arbitrary grids. the selected field will be sampled on
# each grid then loaded in as 3D textures (without any refinement).
le = ds.domain_center - ds.domain_width / 4
re = ds.domain_center + ds.domain_width / 4
ag1 = ds.arbitrary_grid(le, re, [64, 64, 64])
ag2 = ds.arbitrary_grid(re, ds.domain_right_edge, [32, 32, 32])

rc = yt_idv.render_context(height=800, width=800, gui=True)

c = TrackballCamera.from_dataset(ds)
rc.scene = SceneGraph(camera=c)
grid_coll = GridCollection(data_source=[ag1, ag2])
grid_coll.add_data(("gas", "density"), no_ghost=True)
rc.scene.data_objects.append(grid_coll)
rc.scene.components.append(GridCollectionRendering(data=grid_coll))
c.set_position([-1.0727880001068115, 1.6017001867294312, 2.250051736831665])
rc.run()
