"""
Example demonstrating manual construction of a SceneGraph with a BlockCollection
"""
import yt

import yt_idv
from yt_idv.cameras.trackball_camera import TrackballCamera
from yt_idv.scene_components.blocks import BlockRendering
from yt_idv.scene_data.block_collection import BlockCollection
from yt_idv.scene_graph import SceneGraph

ds = yt.load_sample("IsolatedGalaxy")
rc = yt_idv.render_context(height=800, width=800, gui=True)

c = TrackballCamera.from_dataset(ds)
rc.scene = SceneGraph(camera=c)
block_coll = BlockCollection(data_source=ds.all_data())
block_coll.add_data(("gas", "density"), no_ghost=True)
rc.scene.data_objects.append(block_coll)
rc.scene.components.append(BlockRendering(data=block_coll))

rc.run()
