import yt

import yt_idv
from yt_idv.scene_components.particles import ParticleRendering
from yt_idv.scene_data.particle_positions import ParticlePositions

ds = yt.load_sample("snapshot_033")
dd = ds.all_data()

rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, None, no_ghost=True)

pos = ParticlePositions(
    data_source=dd,
    radius_field="smoothing_length",
    particle_type="gas",
    color_field="density",
    position_field="position",
)
pren = ParticleRendering(data=pos, scale=1.0, max_particle_size=0.1)

sg.data_objects.append(pos)
sg.components.append(pren)

print(sg.camera.near_plane, sg.camera.far_plane)
rc.run()
