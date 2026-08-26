import yt

import yt_idv

ds = yt.load_sample("IsolatedGalaxy")
dd = ds.all_data()

rc = yt_idv.render_context("egl", width=1024, height=1024)
rc.add_scene(dd, "density", no_ghost=True)

image = rc.run()
yt.write_bitmap(image, "offscreen_step1_egl.png")

rc.scene.camera.move_forward(1.5)

image = rc.run()
yt.write_bitmap(image, "offscreen_step2_egl.png")

rc.scene.camera.set_position([1.0, 1.5, 3.0])
image = rc.run()
yt.write_bitmap(image, "offscreen_step3_set_position_egl.png")

# report what was used to render
from OpenGL import GL  # noqa: E402

print("GL_RENDERER:", GL.glGetString(GL.GL_RENDERER).decode())
print("GL_VERSION: ", GL.glGetString(GL.GL_VERSION).decode())
