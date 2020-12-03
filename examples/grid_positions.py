import yt

import yt_idv

ds = yt.load_sample("IsolatedGalaxy")
dd = ds.all_data()

rc = yt_idv.render_context("egl", width=1024, height=1024)
rc.add_scene(dd, "density", no_ghost=True)
rc.scene.components[0].visible = False

from yt_idv.scene_annotations.grid_outlines import GridOutlines  # NOQA
from yt_idv.scene_data.grid_positions import GridPositions  # NOQA

grids = ds.index.grids.tolist()

gp = GridPositions(grid_list=grids)
rc.scene.data_objects.append(gp)
go = GridOutlines(data=gp)
rc.scene.components.append(go)

image = rc.run()
yt.write_bitmap(image, "grid_outline.png")
