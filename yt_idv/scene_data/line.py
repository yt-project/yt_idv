import numpy as np
import traitlets
from traittypes import Array

from yt_idv.opengl_support import VertexArray, VertexAttribute
from yt_idv.scene_data.base_data import SceneData

from typing import Union

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
        assert curve.shape[0] > 1 # a curve needs at least 2 points
        assert curve.shape[1] == 3  # a curve needs at least 2 points

        # add the singleton 4th dim
        data = np.ones((curve.shape[0], 4))
        data[:,0:3] = curve

        self.n_vertices = curve.shape[0]
        self.data = data

        self.vertex_array.attributes.append(
            VertexAttribute(name="model_vertex", data=data.astype("f4"))
        )

        self.vertex_array.indices = np.arange(0,self.n_vertices).astype("uint32")
        self.size = self.n_vertices

