import yt

import yt_idv
from yt_idv.scene_components.particles import ParticleRendering
from yt_idv.scene_data.particle_positions import ParticlePositions

ds = yt.load_sample("IsolatedGalaxy")

rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, "density", no_ghost=True)

sg.components[0].display_bounds = (0.0, 0.5, 0.0, 1.0)

dd = ds.all_data()
pos = ParticlePositions(data_source=dd)
pren = ParticleRendering(data=pos)

pren.display_bounds = (0.5, 1.0, 0.0, 1.0)

sg.data_objects.append(pos)
sg.components.append(pren)

rc.run()
