import yt
import yt_idv

from yt_idv.scene_components.mesh import MeshRendering
from yt_idv.scene_data.mesh import SliceData, SliceComposite

ds = yt.load_sample("IsolatedGalaxy")

# add the volume rendering to the scene
rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, "density", no_ghost=True)

# create a slice and generate the slice-mesh object
slc = ds.slice(0, 0.5)
sd = SliceData(data_source=slc)
sd.add_data(("gas", "density"))

# create a second slice and generate the slice-mesh object
slc2 = ds.slice(1, 0.4)
sd2 = SliceData(data_source=slc2)
sd2.add_data(("gas", "density"))

# combine the slices into a composite:
composite = SliceComposite()
composite.add_data([sd, sd2])

# initialize the MeshRendering and add to the scene
mr = MeshRendering(data=composite, cmap_log=True)
rc.scene.data_objects.append(composite)
rc.scene.components.append(mr)

rc.run()


