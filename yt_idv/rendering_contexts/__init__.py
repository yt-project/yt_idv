import os


def prepare_platform(engine):
    """
    Set up the environment that PyOpenGL reads when it is imported.

    Must run before anything imports OpenGL: PyOpenGL binds its platform the
    first time ``OpenGL.platform`` is imported, so the engine is fixed for the
    lifetime of the process.

    Parameters
    ----------
    engine: str, "pyglet", "osmesa" or "egl"

    """
    # PYOPENGL_PLATFORM must be set before any opengl imports
    if engine in ("osmesa", "egl"):
        os.environ["PYOPENGL_PLATFORM"] = engine
    elif engine == "pyglet":
        # an inherited value would bind PyOpenGL to an offscreen platform and
        # leave the hidden window without a usable context
        os.environ.pop("PYOPENGL_PLATFORM", None)

    if engine == "egl":
        # also before the opengl imports: importing OpenGL.platform under
        # PYOPENGL_PLATFORM=egl resolves libEGL right away
        from ._darwin_egl import configure_mesa_egl

        configure_mesa_egl()


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

    prepare_platform(engine)

    import OpenGL.error

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
                    "in PyOpenGL: see https://yt-idv.readthedocs.io/en/latest/installation.html#extra-steps-for-linux"
                )
                raise Exception(extramsg) from oee
            raise oee
    elif engine == "osmesa":
        from .osmesa_context import OSMesaRenderingContext

        return OSMesaRenderingContext(**kwargs)
    elif engine == "egl":
        from .egl_context import EGLRenderingContext

        return EGLRenderingContext(**kwargs)
    else:
        raise KeyError
