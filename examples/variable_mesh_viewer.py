import yt

import yt_idv
from yt_idv.scene_components.variable_mesh_display import VariableMeshDisplay
from yt_idv.scene_data.variable_mesh import VariableMeshContainer

ds = yt.load_sample("IsolatedGalaxy")

vm = ds.r[:, :, 0.5]

rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, None)

vmc = VariableMeshContainer(data_source=vm)
vmc.add_data("ones")
vmd = VariableMeshDisplay(data=vmc)

sg.data_objects.append(vmc)
sg.components.append(vmd)

rc.run()
