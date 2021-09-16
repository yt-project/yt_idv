import yt

import yt_idv
from yt_idv.scene_components.disk_slice import DiskSlice
from yt_idv.scene_data.sliced_values import SlicedData

ds = yt.load_sample("IsolatedGalaxy")
dd = ds.all_data()

rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, None, no_ghost=True)

sdata = SlicedData(data_source=dd)
sren = DiskSlice(data=sdata)

sg.data_objects.append(sdata)
sdata.vertex_array
sg.components.append(sren)

print(sg.camera.near_plane, sg.camera.far_plane)
# sg.camera.far_plane = 0.1
rc.run()
