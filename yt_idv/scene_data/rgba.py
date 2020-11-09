import traitlets

from yt_idv.constants import FULLSCREEN_QUAD
from yt_idv.opengl_support import Texture1D, VertexArray, VertexAttribute
from yt_idv.scene_data.base_data import SceneData


class RGBAData(SceneData):
    name = "rgba_data"
    colormap_texture = traitlets.Instance(Texture1D)

    @traitlets.default("vertex_array")
    def _default_vertex_array(self):
        va = VertexArray(name="tri", each=6)
        fq = FULLSCREEN_QUAD.reshape((6, 3), order="C")
        va.attributes.append(VertexAttribute(name="vertexPosition_modelspace", data=fq))
        return va

    def add_data(self, lines):
        assert lines.shape[1] == 4
        self.colormap_texture = Texture1D(boundary_x="clamp", data=lines)
