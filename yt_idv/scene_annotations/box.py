import numpy as np
import traitlets
from OpenGL import GL

from yt_idv.scene_annotations.base_annotation import SceneAnnotation
from yt_idv.scene_data.box import BoxData


class BoxAnnotation(SceneAnnotation):
    name = "box_outline"
    data = traitlets.Instance(BoxData)
    box_width = traitlets.CFloat(0.05)
    box_color = traitlets.Tuple(
        traitlets.CFloat(),
        traitlets.CFloat(),
        traitlets.CFloat(),
        default_value=(1.0, 1.0, 1.0),
    )
    box_alpha = traitlets.CFloat(1.0)

    def draw(self, scene, program):
        each = self.data.vertex_array.each
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, each)

    def render_gui(self, imgui, renderer):
        changed = super(BoxAnnotation, self).render_gui(imgui, renderer)
        _, bw = imgui.slider_float("Width", self.box_width, 0.001, 0.250)
        if _:
            self.box_width = bw
        changed = changed or _
        _, ba = imgui.slider_float("Alpha", self.box_alpha, 0.0, 1.0)
        if _:
            self.box_alpha = ba
        changed = changed or _
        return changed

    def _set_uniforms(self, scene, shader_program):
        cam = scene.camera
        shader_program._set_uniform("projection", cam.projection_matrix)
        shader_program._set_uniform("modelview", cam.view_matrix)
        shader_program._set_uniform(
            "viewport", np.array(GL.glGetIntegerv(GL.GL_VIEWPORT), dtype="f4")
        )
        shader_program._set_uniform("camera_pos", cam.position)
        shader_program._set_uniform("box_width", self.box_width)
        shader_program._set_uniform("box_alpha", self.box_alpha)
        shader_program._set_uniform("box_color", np.array(self.box_color))
