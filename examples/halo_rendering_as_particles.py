import os

import yt
from yt.extensions.astro_analysis.halo_analysis import HaloCatalog

import yt_idv
from yt_idv.scene_components.particles import ParticleRendering
from yt_idv.scene_data.particle_positions import ParticlePositions

# ds = yt.load_sample("Enzo_64")
ds = yt.load("Enzo_64/DD0025/data0025")

hc = HaloCatalog(data_ds=ds, finder_method="fof")
hc.create()

# set the halo file to load
files = os.listdir(hc.output_dir)
files.sort()
for fi in files:
    if hc.output_basename in fi:
        halo_file = os.path.join(hc.output_dir, fi)

# loaded as
ds_halos = yt.load(halo_file)


dd = ds_halos.all_data()

print(dd.quantities.extrema(("halos", "virial_radius")))
rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, "density", no_ghost=True)
sg.components[0].colormap.colormap_name = "pixel_blue.cmyt"

pos = ParticlePositions(
    data_source=dd,
    radius_field="virial_radius",
    particle_type="halos",
    # color_field="virial_radius",
    position_field="particle_position",
)
# pren.max_particle_size = 0.000000001
pren: ParticleRendering = ParticleRendering(
    data=pos,
    scale=1.0,
)
pren.max_particle_size = 1e3
sg.data_objects.append(pos)
sg.components.append(pren)

print(sg.camera.near_plane, sg.camera.far_plane)
rc.run()
