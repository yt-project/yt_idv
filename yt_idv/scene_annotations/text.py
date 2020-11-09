import numpy as np
import traitlets
from OpenGL import GL

from yt_idv.scene_annotations.base_annotation import SceneAnnotation
from yt_idv.scene_data.text_characters import TextCharacters

# This is drawn in part from
#  https://learnopengl.com/#!In-Practice/Text-Rendering


class TextAnnotation(SceneAnnotation):

    name = "text_annotation"
    data = traitlets.Instance(TextCharacters)
    text = traitlets.CUnicode()
    draw_instructions = traitlets.List()
    origin = traitlets.Tuple(
        traitlets.CFloat(), traitlets.CFloat(), default_value=(-1, -1)
    )
    scale = traitlets.CFloat(1.0)

    @traitlets.observe("text")
    def _observe_text(self, change):
        text = change["new"]
        lines = text.split("\n")
        draw_instructions = []
        y = 0
        for line in reversed(lines):
            x = 0
            dy = 0
            for c in line:
                e = self.data.characters[c]
                draw_instructions.append((x, y, e.texture, e.vbo_offset))
                dy = max(dy, e.vert_advance)
                x += e.hori_advance
            y += dy
        self.draw_instructions = draw_instructions

    def _set_uniforms(self, scene, shader_program):
        pass

    def draw(self, scene, program):
        viewport = np.array(GL.glGetIntegerv(GL.GL_VIEWPORT), dtype="f4")
        program._set_uniform("viewport", viewport)
        each = self.data.vertex_array.each
        for x, y, tex, vbo_offset in self.draw_instructions:
            with tex.bind(0):
                program._set_uniform("x_offset", float(x))
                program._set_uniform("y_offset", float(y))
                program._set_uniform("x_origin", self.origin[0])
                program._set_uniform("y_origin", self.origin[1])
                program._set_uniform("scale", self.scale)
                GL.glDrawArrays(GL.GL_TRIANGLES, vbo_offset * each, each)
