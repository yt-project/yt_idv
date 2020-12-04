import numpy as np
import traitlets
from OpenGL import GL

from yt_idv.scene_components.base_component import SceneComponent
from yt_idv.scene_data.line import LineData
from yt_idv.scene_data.rgba import RGBAData


class RGBADisplay(SceneComponent):
    name = "rgba_display"
    data = traitlets.Instance(RGBAData)
    priority = 20

    def _set_uniforms(self, scene, shader_program):
        shader_program._set_uniform("cm_tex", 0)

    def draw(self, scene, program):
        with self.data.colormap_texture.bind(0):
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, 6)


class RGBALinePlot(SceneComponent):
    name = "rgba_line_plot"
    data = traitlets.Instance(LineData)
    priority = 20

    def draw(self, scene, program):
        for i, _channel in enumerate("rgba"):
            program._set_uniform("channel", i)
            GL.glDrawArrays(GL.GL_LINE_STRIP, 0, self.data.n_vertices)

    def _set_uniforms(self, scene, shader_program):
        shader_program._set_uniform(
            "viewport", np.array(GL.glGetIntegerv(GL.GL_VIEWPORT), dtype="f4")
        )
