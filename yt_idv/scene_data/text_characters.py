import string
from collections import namedtuple

import numpy as np
import traitlets
from matplotlib.ft2font import LOAD_FORCE_AUTOHINT
from OpenGL import GL

from yt_idv.opengl_support import Texture2D, VertexArray, VertexAttribute
from yt_idv.scene_data.base_data import SceneData
from yt_idv.traitlets_support import FontTrait

Character = namedtuple(
    "Character", ["texture", "vbo_offset", "hori_advance", "vert_advance"]
)


class TextCharacters(SceneData):
    characters = traitlets.Dict(value_trait=traitlets.Instance(Character))
    name = "text_overlay"
    font = FontTrait("DejaVu Sans")
    font_size = traitlets.CInt(32)

    @traitlets.default("vertex_array")
    def _default_vertex_array(self):
        return VertexArray(name="char_info", each=6)

    def build_textures(self):
        # This doesn't check if the textures have already been built
        self.font.set_size(self.font_size, 200)
        chars = [ord(_) for _ in string.printable]
        tex_ids = GL.glGenTextures(len(chars))
        vert = []
        for i, (tex_id, char_code) in enumerate(zip(tex_ids, chars)):
            self.font.clear()
            self.font.set_text(chr(char_code), flags=LOAD_FORCE_AUTOHINT)
            self.font.draw_glyphs_to_bitmap(antialiased=True)
            glyph = self.font.load_char(char_code)
            x0, y0, x1, y1 = glyph.bbox
            bitmap = self.font.get_image().astype(">f4") / 255.0
            dx = 1.0 / bitmap.shape[0]
            dy = 1.0 / bitmap.shape[1]
            triangles = np.array(
                [
                    [x0, y1, 0.0 + dx / 2.0, 0.0 + dy / 2.0],
                    [x0, y0, 0.0 + dx / 2.0, 1.0 - dy / 2.0],
                    [x1, y0, 1.0 - dx / 2.0, 1.0 - dy / 2.0],
                    [x0, y1, 0.0 + dx / 2.0, 0.0 + dy / 2.0],
                    [x1, y0, 1.0 - dx / 2.0, 1.0 - dy / 2.0],
                    [x1, y1, 1.0 - dx / 2.0, 0.0 + dy / 2.0],
                ],
                dtype="<f4",
            )
            vert.append(triangles)
            texture = Texture2D(
                texture_name=tex_id, data=bitmap, boundary_x="clamp", boundary_y="clamp"
            )
            # I can't find information as to why horiAdvance is a
            # factor of 8 larger than the other factors.  I assume it
            # is referenced somewhere, but I cannot find it.
            self.characters[chr(char_code)] = Character(
                texture, i, glyph.horiAdvance / 8.0, glyph.vertAdvance
            )
        vert = np.concatenate(vert)
        self.vertex_array.attributes.append(
            VertexAttribute(name="quad_vertex", data=vert.astype("<f4"))
        )
