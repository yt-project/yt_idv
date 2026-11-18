import yt

import yt_idv

ds = yt.load_sample("output_00080")

rc = yt_idv.render_context(height=800, width=800, gui=True)
# octree datasets are rendered from an OctreeBlockCollection
sg = rc.add_scene(ds, ("gas", "density"), no_ghost=False)

rc.run()
