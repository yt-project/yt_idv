import yt
import yt_idv

from yt_idv.scene_components.mesh import MeshRendering
from yt_idv.scene_data.mesh import SliceData

ds = yt.load_sample("IsolatedGalaxy")

# add the volume rendering to the scene
rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, "density", no_ghost=True)

# create a slice and generate the slice-mesh object
slc = ds.slice(0, 0.5)
sd = SliceData(data_source=slc)
sd.add_data(("gas", "density"))

# initialize the MeshRendering and add to the scene
mr = MeshRendering(data=sd, cmap_log=True)
rc.scene.data_objects.append(sd)
rc.scene.components.append(mr)

rc.run()
