import numpy as np
import traitlets

from yt_idv.opengl_support import VertexArray, VertexAttribute
from yt_idv.scene_data.base_data import SceneData


class GridPositions(SceneData):
    name = "grid_positions"
    grid_list = traitlets.List()

    @traitlets.default("vertex_array")
    def _default_vertex_array(self):
        va = VertexArray(name="grid_bounds", each=2)
        positions = []
        for g in self.grid_list:
            positions.append(g.LeftEdge.tolist() + [1.0])
            positions.append(g.RightEdge.tolist() + [1.0])
        positions = np.array(positions, dtype="f4")
        va.attributes.append(VertexAttribute(name="model_vertex", data=positions))
        return va
