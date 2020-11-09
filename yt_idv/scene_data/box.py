import numpy as np
import traitlets

from yt_idv.opengl_support import VertexArray, VertexAttribute, compute_box_geometry
from yt_idv.scene_data.base_data import SceneData
from yt_idv.traitlets_support import YTPositionTrait


class BoxData(SceneData):
    name = "box_data"
    left_edge = YTPositionTrait([0.0, 0.0, 0.0])
    right_edge = YTPositionTrait([1.0, 1.0, 1.0])

    @traitlets.default("vertex_array")
    def _default_vertex_array(self):
        va = VertexArray(name="box_outline", each=36)
        data = compute_box_geometry(self.left_edge, self.right_edge).copy()
        va.attributes.append(
            VertexAttribute(name="model_vertex", data=data.astype("f4"))
        )
        N = data.size // 4
        le = np.concatenate([[self.left_edge.copy()] for _ in range(N)])
        re = np.concatenate([[self.right_edge.copy()] for _ in range(N)])
        dds = self.right_edge - self.left_edge
        dds = np.concatenate([[dds.copy()] for _ in range(N)])
        va.attributes.append(VertexAttribute(name="in_left_edge", data=le.astype("f4")))
        va.attributes.append(
            VertexAttribute(name="in_right_edge", data=re.astype("f4"))
        )
        va.attributes.append(VertexAttribute(name="in_dx", data=dds.astype("f4")))
        return va
