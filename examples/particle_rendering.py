import yt

import yt_idv
from yt_idv.scene_components.particles import ParticleRendering
from yt_idv.scene_data.particle_positions import ParticlePositions

ds = yt.load_sample("IsolatedGalaxy")
dd = ds.all_data()

rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, None, no_ghost=True)

pos = ParticlePositions(data_source=dd)
pren = ParticleRendering(data=pos)

sg.data_objects.append(pos)
sg.components.append(pren)

rc.run()
