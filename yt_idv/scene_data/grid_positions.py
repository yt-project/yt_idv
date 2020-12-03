import numpy as np
import traitlets

from yt_idv.opengl_support import VertexArray, VertexAttribute
from yt_idv.scene_data.base_data import SceneData


class GridPositions(SceneData):
    name = "grid_positions"
    grid_list = traitlets.List()

    @traitlets.default("vertex_array")
    def _default_vertex_array(self):
        va = VertexArray(name="grid_bounds")
        positions = []
        dx = []
        le = []
        re = []
        for g in self.grid_list:
            dx.append(g.dds.tolist())
            le.append(g.LeftEdge.tolist())
            re.append(g.RightEdge.tolist())
        positions = np.ones((len(self.grid_list), 4), dtype="f4")
        dx = np.array(dx).astype("f4")
        le = np.array(le).astype("f4")
        re = np.array(re).astype("f4")
        va.attributes.append(VertexAttribute(name="model_vertex", data=positions))
        va.attributes.append(VertexAttribute(name="in_left_edge", data=le))
        va.attributes.append(VertexAttribute(name="in_dx", data=dx))
        va.attributes.append(VertexAttribute(name="in_right_edge", data=re))
        return va
