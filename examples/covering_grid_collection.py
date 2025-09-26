import yt

import yt_idv
from yt_idv.cameras.trackball_camera import TrackballCamera
from yt_idv.scene_components.blocks import GridCollectionRendering
from yt_idv.scene_data.block_collection import GridCollection
from yt_idv.scene_graph import SceneGraph

ds = yt.load_sample("IsolatedGalaxy")


ag1 = ds.arbitrary_grid(ds.domain_center, ds.domain_right_edge, [64, 64, 64])
ag2 = ds.arbitrary_grid(ds.domain_left_edge, ds.domain_center, [32, 32, 32])

rc = yt_idv.render_context(height=800, width=800, gui=True)

c = TrackballCamera.from_dataset(ds)
rc.scene = SceneGraph(camera=c)
grid_coll = GridCollection(data_source=[ag1, ag2])
grid_coll.add_data(("gas", "density"), no_ghost=True)
rc.scene.data_objects.append(grid_coll)
rc.scene.components.append(GridCollectionRendering(data=grid_coll))

rc.run()
