import numpy as np
import traitlets

from yt_idv.opengl_support import VertexArray, VertexAttribute
from yt_idv.scene_data.base_data import SceneData


class LineData(SceneData):
    name = "line_data"
    n_values = traitlets.CInt()

    @traitlets.default("vertex_array")
    def _default_vertex_array(self):
        return VertexArray(name="vertices", each=6)

    def add_data(self, lines):
        assert lines.shape[1] == 4
        x_coord = np.mgrid[0.0 : 1.0 : lines.shape[0] * 1j].astype("f4")
        x_coord = x_coord.reshape((-1, 1))
        self.n_vertices = lines.shape[0]
        self.vertex_array.attributes.append(
            VertexAttribute(name="rgba_values", data=lines)
        )
        self.vertex_array.attributes.append(
            VertexAttribute(name="x_coord", data=x_coord)
        )
