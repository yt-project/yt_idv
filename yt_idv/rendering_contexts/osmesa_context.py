import numpy as np
from OpenGL import GL, osmesa

from .base_offscreen import OffscreenRenderingContext


class OSMesaRenderingContext(OffscreenRenderingContext):
    """Rendering context using OSMesa (experimental)"""

    def __init__(self, width=1024, height=1024, **kwargs):
        super(OSMesaRenderingContext, self).__init__(width, height, **kwargs)
        self.osmesa = osmesa
        # Now we create our necessary bits.
        config_attribs = np.array(
            [
                osmesa.OSMESA_RED_SIZE,
                8,
                osmesa.OSMESA_GREEN_SIZE,
                8,
                osmesa.OSMESA_BLUE_SIZE,
                8,
                osmesa.OSMESA_DEPTH_SIZE,
                24,
                osmesa.OSMESA_STENCIL_SIZE,
                8,
                osmesa.OSMESA_COLOR_BUFFER_TYPE,
                osmesa.OSMESA_RGB_BUFFER,
                osmesa.OSMESA_SURFACE_TYPE,
                osmesa.OSMESA_PBUFFER_BIT,
                osmesa.OSMESA_RENDERABLE_TYPE,
                osmesa.OSMESA_OPENGL_BIT,
                osmesa.OSMESA_CONFIG_CAVEAT,
                osmesa.OSMESA_NONE,
                osmesa.OSMESA_NONE,
            ],
            dtype="i4",
        )
        self.config_attribs = config_attribs

        GL.glClearColor(0.0, 0.0, 0.0, 0.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
