import numpy as np
from OpenGL import GL
from yt import write_bitmap

class EGLRenderingContext:
    """Rendering context using EGL (experimental)

    Parameters
    ----------
    width : int, optional
        The width of the off-screen buffer window.  For performance reasons it
        is recommended to use values that are natural powers of 2.

    height : int, optional
        The height of the off-screen buffer window.  For performance reasons it
        it is recommended to use values that are natural powers of 2.

    """

    def __init__(self, width=1024, height=1024):
        from OpenGL import EGL

        self.EGL = EGL
        self.display = EGL.eglGetDisplay(EGL.EGL_DEFAULT_DISPLAY)
        major = np.zeros(1, "i4")
        minor = np.zeros(1, "i4")
        EGL.eglInitialize(self.display, major, minor)
        num_configs = np.zeros(1, "i4")
        config = EGL.EGLConfig()
        # Now we create our necessary bits.
        config_attribs = np.array(
            [
                EGL.EGL_SURFACE_TYPE,
                EGL.EGL_PBUFFER_BIT,
                EGL.EGL_BLUE_SIZE,
                8,
                EGL.EGL_GREEN_SIZE,
                8,
                EGL.EGL_RED_SIZE,
                8,
                EGL.EGL_DEPTH_SIZE,
                8,
                EGL.EGL_RENDERABLE_TYPE,
                EGL.EGL_OPENGL_BIT,
                EGL.EGL_NONE,
            ],
            dtype="i4",
        )
        self.config = EGL.eglChooseConfig(
            self.display, config_attribs, config, 1, num_configs
        )

        pbuffer_attribs = np.array(
            [EGL.EGL_WIDTH, width, EGL.EGL_HEIGHT, height, EGL.EGL_NONE], dtype="i4"
        )
        self.surface = EGL.eglCreatePbufferSurface(
            self.display, self.config, pbuffer_attribs
        )
        EGL.eglBindAPI(EGL.EGL_OPENGL_API)

        self.context = EGL.eglCreateContext(
            self.display, self.config, EGL.EGL_NO_CONTEXT, None
        )

        EGL.eglMakeCurrent(self.display, self.surface, self.surface, self.context)

        GL.glClearColor(0.0, 0.0, 0.0, 0.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

    def setup_loop(self, scene, camera):
        scene.set_camera(camera)
        scene.update_minmax()
        camera.compute_matrices()
        callbacks = EventCollection(scene, camera)
        callbacks.draw = True
        return callbacks

    def start_loop(self, scene, camera):
        self.setup_loop(scene, camera)

    def __call__(self, scene, camera, callbacks):
        camera.compute_matrices()
        scene.set_camera(camera)
        scene.render()
        arr = scene._retrieve_framebuffer()
        write_bitmap(arr, "test.png")
