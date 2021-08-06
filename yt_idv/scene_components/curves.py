from math import ceil, floor

import numpy as np
import traitlets
from OpenGL import GL

from yt_idv.opengl_support import TransferFunctionTexture
from yt_idv.scene_components.base_component import SceneComponent
from yt_idv.scene_data.line import CurveData
from yt_idv.shader_objects import component_shaders


class CurveRendering(SceneComponent):
    """
    A class that renders block data.  It may do this in one of several ways,
    including mesh outline.  This allows us to render a single collection of
    blocks multiple times in a single scene and to separate out the memory
    handling from the display.
    """

    name = "curve_rendering"
    data = traitlets.Instance(CurveData)
    line_width = traitlets.CFloat(1.)
    priority = 10

    def render_gui(self, imgui, renderer, scene):
        changed = super(CurveRendering, self).render_gui(imgui, renderer, scene)
        _, line_width = imgui.slider_float(
            "Line Width", self.line_width, 1.0, 2.0
        )
        if _:
            self.line_width = line_width

        changed = changed or _

        return changed

    def draw(self, scene, program):
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glCullFace(GL.GL_BACK)
        GL.glDrawArrays(GL.GL_LINE_LOOP, 0, self.data.n_vertices)

    def _set_uniforms(self, scene, shader_program):
        pass #shader_program._set_uniform("line_width", self.line_width)

