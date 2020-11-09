"""Top-level package for interactive volume rendering for yt."""

__author__ = """Matthew Turk"""
__email__ = "matthewturk@gmail.com"
__version__ = "0.1.0"

import os
# We don't want to import this if we're just doing offscreen rendering
if os.environ.get("PYOPENGL_PLATFORM", None) != "egl":
    from .rendering_contexts.pyglet_context import PygletRenderingContext
else:
    from .rendering_contexts.egl_context import EGLRenderingContext
from .scene_graph import SceneGraph
