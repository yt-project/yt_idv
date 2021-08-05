import yt

import yt_idv
from yt_idv.scene_components.octree_blocks import OctreeBlockRendering
from yt_idv.scene_data.octree_block_collection import OctreeBlockCollection

ds = yt.load_sample("output_00080")
dd = ds.all_data()

rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, None, no_ghost=True)

odata = OctreeBlockCollection(data_source=dd)
odata.add_data("density")
oren = OctreeBlockRendering(data=odata)

sg.data_objects.append(odata)
sg.components.append(oren)

rc.run()
