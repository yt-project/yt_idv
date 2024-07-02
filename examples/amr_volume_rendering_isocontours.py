import yt

import yt_idv

ds = yt.load_sample("IsolatedGalaxy")

rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, "density", no_ghost=True)
sg.components[0].render_method = "isocontours"

# default behavior will treat these values as base-10 exponents
sg.components[0].iso_layers[0] = -29.0
sg.components[0].iso_tolerance[0] = 1.0  # tolerance in percent

rc.run()
