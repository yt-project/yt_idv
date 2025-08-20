import numpy as np
import traitlets
from OpenGL import GL

from yt_idv.scene_components.base_component import SceneComponent
from yt_idv.scene_data.curve import CurveCollection, CurveData


class CurveRendering(SceneComponent):
    """
    A class that renders user-specified curves.
    """

    name = "curve_rendering"
    data = traitlets.Instance(CurveData, help="The curve data.")
    curve_rgba = traitlets.Tuple((1.0, 1.0, 1.0, 1.0)).tag(trait=traitlets.CFloat())
    priority = 10
    _has_colormap = False

    def render_gui(self, imgui, renderer, scene):
        changed, self.visible = imgui.checkbox("Visible", self.visible)

        _, newRGBa = imgui.input_float4("RGBa", *self.curve_rgba)
        if _:
            self.curve_rgba = tuple(newRGBa)
        changed = changed or _

        return changed

    def draw(self, scene, program):
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glCullFace(GL.GL_BACK)
        # note: line width != 1.0 is not supported on all platforms.
        # see https://github.com/yt-project/yt_idv/issues/174
        GL.glLineWidth(1.0)
        GL.glDrawArrays(GL.GL_LINE_STRIP, 0, self.data.n_vertices)

    def _set_uniforms(self, scene, shader_program):
        clr = np.array(self.curve_rgba).astype("f4")
        shader_program._set_uniform("curve_rgba", clr)


class CurveCollectionRendering(CurveRendering):
    """
    rendering a collection of curves
    """

    name = "multi_curve_rendering"
    curve_collection = traitlets.List()
    data = traitlets.Instance(CurveCollection)

    def draw(self, scene, program):
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glCullFace(GL.GL_BACK)
        GL.glLineWidth(1.0)
        GL.glDrawArrays(GL.GL_LINES, 0, self.data.n_vertices)
