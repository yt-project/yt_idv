import yt

import yt_idv

ds = yt.load_sample("Enzo_64")

rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, ("index", "ones"), no_ghost=True)

sg.components[0].cmap_log = False
sg.components[0].render_method = "sum_projection"

rc.run()
