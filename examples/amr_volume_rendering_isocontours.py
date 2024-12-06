import yt

import yt_idv
from yt_idv.scene_components.isolayers import Isolayers

ds = yt.load_sample("IsolatedGalaxy")

rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, "density", no_ghost=True)

iso = Isolayers(data=sg.components[0].data)
sg.components.append(iso)


# default behavior will treat these values as base-10 exponents
sg.components[1].iso_layers[0] = -27.0
sg.components[1].iso_tolerance[0] = 1.2  # tolerance in percent

rc.run()
