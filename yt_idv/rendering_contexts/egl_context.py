import numpy as np
from OpenGL import GL
from yt import write_bitmap
from ctypes import pointer
from ..opengl_support import Framebuffer


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

    def __init__(self, width=1024, height=1024, scene = None, image_widget = None):
        from OpenGL import EGL
        self.image_widget = image_widget

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
                EGL.EGL_RED_SIZE,
                8,
                EGL.EGL_GREEN_SIZE,
                8,
                EGL.EGL_BLUE_SIZE,
                8,
                EGL.EGL_DEPTH_SIZE,
                24,
                EGL.EGL_STENCIL_SIZE,
                8,
                EGL.EGL_COLOR_BUFFER_TYPE,
                EGL.EGL_RGB_BUFFER,
                EGL.EGL_SURFACE_TYPE,
                EGL.EGL_PBUFFER_BIT,
                EGL.EGL_RENDERABLE_TYPE,
                EGL.EGL_OPENGL_BIT,
                EGL.EGL_CONFIG_CAVEAT,
                EGL.EGL_NONE,
                EGL.EGL_NONE
            ],
            dtype="i4",
        )
        EGL.eglChooseConfig(
            self.display, config_attribs, pointer(config), 1, num_configs
        )

        pbuffer_attribs = np.array(
            [EGL.EGL_WIDTH, width, EGL.EGL_HEIGHT, height, EGL.EGL_NONE], dtype="i4"
        )
        self.surface = EGL.eglCreatePbufferSurface(
            self.display, config, pbuffer_attribs
        )
        EGL.eglBindAPI(EGL.EGL_OPENGL_API)

        self.context = EGL.eglCreateContext(
            self.display, config, EGL.EGL_NO_CONTEXT, None
        )

        EGL.eglMakeCurrent(self.display, self.surface, self.surface, self.context)

        GL.glClearColor(0.0, 0.0, 0.0, 0.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        self.scene = scene

    def draw(self):

        if self.scene is None:
            return
        self.scene.render()
        if self.image_widget is not None:
            self.image_widget.value = write_bitmap(
                self.scene.image[:, :, :3], None
            )
        return self.scene.image
