import yt

import yt_idv
from yt_idv.scene_annotations.block_histogram import BlockHistogram

ds = yt.load_sample("IsolatedGalaxy")

rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, "density", no_ghost=True)
bh = BlockHistogram(data=sg.data_objects[0], bins=64)
sg.annotations = sg.annotations + [bh]
# rc.run()
