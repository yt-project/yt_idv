import numpy as np
import traitlets
from traittypes import Array

from yt_idv.opengl_support import VertexArray, VertexAttribute
from yt_idv.scene_data.base_data import SceneData


class CurveData(SceneData):
    name = "curve_data"
    data = Array()
    n_vertices = traitlets.CInt()

    @traitlets.default("vertex_array")
    def _default_vertex_array(self):
        va = VertexArray(name="vertices")
        return va

    def add_data(self, curve):
        # curve is a collection of ndarray of points
        assert curve.shape[0] > 1  # a curve needs at least 2 points
        assert curve.shape[1] == 3  # a curve needs at least 3 dimensions

        # add the singleton 4th dim
        data = np.ones((curve.shape[0], 4))
        data[:, 0:3] = curve

        self.n_vertices = curve.shape[0]
        self.data = data

        self.vertex_array.attributes.append(
            VertexAttribute(name="model_vertex", data=data.astype("f4"))
        )

        self.vertex_array.indices = np.arange(0, self.n_vertices).astype("uint32")
        self.size = self.n_vertices


class CurveCollection(CurveData):
    name = "curve_collection"
    data = Array()
    n_vertices = traitlets.CInt()

    def add_curve(self, curve):
        # curve is a collection of ndarray of points
        assert curve.shape[0] > 1  # a curve needs at least 2 points
        assert curve.shape[1] == 3  # a curve needs at least 3 dimensions

        # double up the indices to use GL_LINES
        index_range = np.arange(0, curve.shape[0])
        line_indices = np.column_stack([index_range, index_range]).ravel()[1:-1]
        data = curve[line_indices]
        data = np.column_stack([data, np.ones((data.shape[0],))])

        if self.data.shape:
            self.data = np.concatenate([self.data, data])
        else:
            self.data = data

    def add_data(self):
        self.n_vertices = self.data.shape[0]

        self.vertex_array.attributes.append(
            VertexAttribute(name="model_vertex", data=self.data.astype("f4"))
        )

        self.vertex_array.indices = np.arange(0, self.n_vertices).astype("uint32")
        self.size = self.n_vertices
