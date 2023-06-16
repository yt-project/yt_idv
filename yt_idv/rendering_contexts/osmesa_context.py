import numpy as np
from OpenGL import GL, osmesa

from .base_offscreen import OffscreenRenderingContext


class OSMesaRenderingContext(OffscreenRenderingContext):
    """Offscreen rendering context using OSMesa (experimental)

    Parameters
    ----------
    width : int, optional
        The width of the off-screen buffer window.  For performance reasons it
        is recommended to use values that are natural powers of 2.

    height : int, optional
        The height of the off-screen buffer window.  For performance reasons it
        it is recommended to use values that are natural powers of 2.

    """

    def __init__(self, width=1024, height=1024, **kwargs):
        super().__init__(width, height, **kwargs)
        self.osmesa = osmesa
        # Now we create our necessary bits.
        config_attribs = np.array(
            [
                osmesa.OSMESA_DEPTH_BITS,
                24,
                osmesa.OSMESA_STENCIL_BITS,
                8,
                osmesa.OSMESA_FORMAT,
                osmesa.OSMESA_RGBA,
                osmesa.OSMESA_PROFILE,
                osmesa.OSMESA_CORE_PROFILE,
                0,
            ],
            dtype="i4",
        )
        self.context = osmesa.OSMesaCreateContextAttribs(config_attribs, None)
        self._buffer = np.zeros((self.height, self.width, 4), dtype="u1")
        osmesa.OSMesaMakeCurrent(
            self.context, self._buffer, GL.GL_UNSIGNED_BYTE, self.height, self.width
        )

        GL.glClearColor(0.0, 0.0, 0.0, 0.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
