import yt

import yt_idv
from yt_idv.cameras.ray_table import equirectangular_rays, fisheye_rays

ds = yt.load_sample("IsolatedGalaxy")
dd = ds.all_data()

rc = yt_idv.render_context("egl", width=1024, height=512)
rc.add_scene(dd, "density", no_ghost=True)
camera = rc.scene.camera
# inside the disk, looking at the galaxy's center
camera.update(position=[0.501, 0.49, 0.501], focus=[0.5, 0.5, 0.5], up=[0.0, 0.0, 1.0])

# a full 360 degree panorama, centered on the view direction
camera.ray_table = equirectangular_rays(1024, 512)
camera.projection_type = "ray_table"
image = rc.run()
yt.write_bitmap(image, "panorama_equirectangular.png")

# a 220 degree fisheye; pixels outside the image circle have no ray
camera.ray_table = fisheye_rays(1024, 512, fov=220.0)
image = rc.run()
yt.write_bitmap(image, "panorama_fisheye.png")
