import os

import OpenGL.error


def render_context(engine="pyglet", **kwargs):
    """
    Return the appropriate rendering context.

    At present, this accepts "pyglet", "osmesa" or "egl"

    Parameters
    ----------
    engine: str, "pyglet", "osmesa" or "egl"

    Returns
    -------
    RenderingContext

    """
    if engine == "pyglet":
        from .pyglet_context import PygletRenderingContext

        try:
            return PygletRenderingContext(**kwargs)
        except OpenGL.error.Error as oee:
            msg = str(oee)
            if "no valid context" in msg:
                extramsg = (
                    "It looks like you have encountered an OpenGL context error while trying to start the GUI. "
                    "If you are running headless, try specifying 'osmesa' or 'egl' with the engine argument. If you "
                    "are running a newer Ubuntu (21+) or Fedora (34+) release, you may need to enforce Xorg usage "
                    "in PyOpenGL: see https://yt-idv.readthedocs.io/en/latest/installation.html#extra-steps-for-linux."
                )
                raise Exception(extramsg) from oee
            raise oee
    elif engine == "osmesa":
        os.environ["PYOPENGL_PLATFORM"] = "osmesa"
        from .osmesa_context import OSMesaRenderingContext

        return OSMesaRenderingContext(**kwargs)
    elif engine == "egl":
        os.environ["PYOPENGL_PLATFORM"] = "egl"
        from .egl_context import EGLRenderingContext

        return EGLRenderingContext(**kwargs)
    else:
        raise KeyError
