import numpy as np
import traitlets
from OpenGL import GL

from yt_idv.scene_annotations.base_annotation import SceneAnnotation
from yt_idv.scene_data.block_collection import BlockCollection


class BlockOutline(SceneAnnotation):
    """
    A class that renders outlines of block data.
    """

    name = "block_outline"
    data = traitlets.Instance(BlockCollection)
    box_width = traitlets.CFloat(0.1)
    box_color = traitlets.Tuple((1.0, 1.0, 1.0), trait=traitlets.CFloat())
    box_alpha = traitlets.CFloat(1.0)

    def draw(self, scene, program):
        each = self.data.vertex_array.each
        for tex_ind, _tex, _bitmap_tex in self.data.viewpoint_iter(scene.camera):
            GL.glDrawArrays(GL.GL_TRIANGLES, tex_ind * each, each)

    def render_gui(self, imgui, renderer):
        changed = super(BlockOutline, self).render_gui(imgui, renderer)
        _, bw = imgui.slider_float("Width", self.box_width, 0.001, 0.250)
        if _:
            self.box_width = bw
        changed = changed or _
        _, (r, g, b) = imgui.color_edit3("Color", *self.box_color)
        if _:
            self.box_color = (r, g, b)
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
        shader_program._set_uniform("box_color", np.array(self.box_color))
        shader_program._set_uniform("box_alpha", self.box_alpha)
