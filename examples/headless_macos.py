"""
Off-screen rendering on macOS, both ways.

There are two options on macOS, and which one you want depends entirely on
whether the machine has a window server session:

``hidden`` (default)
    A pyglet window created with ``visible=False``.  This still gets a real
    Apple OpenGL context, so rendering runs on the GPU -- on an M2 Max this is
    GL 4.1 and roughly 13 ms/frame at 512x512.  Needs a logged-in GUI session,
    so it will not work over a bare ssh connection.

``egl``
    Mesa's EGL on the surfaceless platform.  Pure software rendering, but it
    needs no window server at all.  Requires a Mesa install; see
    docs/installation.rst.

Run with::

    python headless_macos.py            # hidden window, GPU
    python headless_macos.py egl        # Mesa EGL, software
"""

import sys

import yt
from yt.testing import fake_amr_ds

import yt_idv

mode = sys.argv[1] if len(sys.argv) > 1 else "hidden"

if mode == "hidden":
    rc = yt_idv.render_context(
        "pyglet", width=800, height=800, visible=False, gui=False
    )
elif mode == "egl":
    rc = yt_idv.render_context("egl", width=800, height=800)
else:
    raise SystemExit(f"unknown mode {mode!r}; use 'hidden' or 'egl'")

# any yt dataset works here; fake_amr_ds keeps the example self-contained
ds = fake_amr_ds(fields=("Density",), units=("g/cm**3",))
rc.add_scene(ds, ("stream", "Density"), no_ghost=True)

image = rc.run()
yt.write_bitmap(image, f"headless_macos_{mode}.png")

rc.scene.camera.move_forward(1.5)
image = rc.run()
yt.write_bitmap(image, f"headless_macos_{mode}_zoomed.png")

# report what actually did the rendering -- "Apple M2 Max" means the GPU,
# "llvmpipe" is fast software, "softpipe" is slow software
from OpenGL import GL  # noqa: E402

print("GL_RENDERER:", GL.glGetString(GL.GL_RENDERER).decode())
print("GL_VERSION: ", GL.glGetString(GL.GL_VERSION).decode())
