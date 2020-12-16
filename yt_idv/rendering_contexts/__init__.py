import os


def render_context(engine="pyglet", **kwargs):
    """
    Return the appropriate rendering context.

    At present, this accepts either "pyglet" or "egl"

    Parameters
    ----------
    engine: str, either "pyglet" or "egl"

    Returns
    -------
    RenderingContext

    """
    if engine == "pyglet":
        from .pyglet_context import PygletRenderingContext

        return PygletRenderingContext(**kwargs)
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
