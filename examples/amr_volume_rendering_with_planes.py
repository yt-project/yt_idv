# example showing how to add a static cutting plane to an amr rendering
import yt
import numpy as np
import yt_idv
from unyt import unyt_quantity
from yt_idv.scene_components.planes import Plane  # NOQA
from yt_idv.scene_data.plane import PlaneData  # NOQA

ds = yt.load_sample("IsolatedGalaxy")

# add the volume rendering to the scene
rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds, "density", no_ghost=True)

# add some planes (these are independent objects, not linked to the volume rendering)

# slice
slc = ds.slice(0, 0.5)
slc_data = PlaneData(data_source=slc)
slc_data.add_data("density", 1., (400, 400))
slc_render = Plane(data=slc_data, cmap_log=True)
rc.scene.data_objects.append(slc_data)
rc.scene.components.append(slc_render)

# a second slice, off-center
slc = ds.slice(1, 0.5)
slc_data = PlaneData(data_source=slc)
slc_data.add_data("density",
                  unyt_quantity(400, 'kpc'),
                  (400, 400),
                  center=np.array([0.65, slc.coord, 0.5])
                  )
slc_render = Plane(data=slc_data, cmap_log=True)
rc.scene.data_objects.append(slc_data)
rc.scene.components.append(slc_render)

# another slice, lower width
slc = ds.slice(2, 0.5)
slc_data = PlaneData(data_source=slc)
slc_data.add_data("density",
                  unyt_quantity(400, 'kpc'),
                  (400, 400),
                  )
slc_render = Plane(data=slc_data, cmap_log=True)
rc.scene.data_objects.append(slc_data)
rc.scene.components.append(slc_render)

# cutting plane
normal = np.array([1., 1., 0.], dtype='float64')
center = ds.domain_center.to('code_length').value
cut = ds.cutting(normal, center)
cut_data = PlaneData(data_source=cut)
cut_data.add_data("density", 1., (400, 400))
cut_render = Plane(data=cut_data, cmap_log=True)
rc.scene.data_objects.append(cut_data)
rc.scene.components.append(cut_render)

# projection
proj = ds.proj("density", 0)
proj_data = PlaneData(data_source=proj)
proj_data.add_data("density", 1., (400, 400))
proj_render = Plane(data=proj_data, cmap_log=True)
rc.scene.data_objects.append(proj_data)
rc.scene.components.append(proj_render)

rc.run()
