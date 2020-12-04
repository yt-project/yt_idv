import yt

import yt_idv

ds = yt.load_sample("MOOSE_Sample_data", "out.e-s010")

rc = yt_idv.render_context(height=800, width=800, gui=True)

from yt_idv.cameras.trackball_camera import TrackballCamera  # NOQA
from yt_idv.scene_components.mesh import MeshRendering  # NOQA
from yt_idv.scene_data.mesh import MeshData  # NOQA
from yt_idv.scene_graph import SceneGraph  # NOQA

c = TrackballCamera(position=[3.5, 3.5, 3.5], focus=[0.0, 0.0, 0.0])
rc.scene = SceneGraph(camera=c)

dd = ds.all_data()
md = MeshData(data_source=dd)
md.add_data(("connect1", "diffused"))
mr = MeshRendering(data=md, cmap_log=False)

rc.scene.data_objects.append(md)
rc.scene.components.append(mr)
rc.run()
