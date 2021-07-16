import yt

import yt_idv

ds = yt.load_sample("IsolatedGalaxy")
dd = ds.all_data()

rc = yt_idv.render_context("osmesa", width=1024, height=1024)
rc.add_scene(dd, "density", no_ghost=True)

image = rc.run()
yt.write_bitmap(image, "step1.png")

rc.scene.camera.move_forward(1.5)

image = rc.run()
yt.write_bitmap(image, "step2.png")
