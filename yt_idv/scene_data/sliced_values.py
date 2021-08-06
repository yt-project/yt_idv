import numpy as np
import traitlets
from yt.data_objects.data_containers import YTDataContainer

from yt_idv.constants import aabb_triangle_strip
from yt_idv.opengl_support import VertexArray, VertexAttribute
from yt_idv.scene_data.base_data import SceneData


class SlicedData(SceneData):
    name = "sliced_data"
    data_source = traitlets.Instance(YTDataContainer)
    color_field = traitlets.Unicode("density", allow_none=True)
    field_type = traitlets.Unicode("gas")
    size = traitlets.CInt(-1)

    @traitlets.default("vertex_array")
    def _default_vertex_array(self):
        va = VertexArray(name="data_positions", each=14)
        va.attributes.append(
            VertexAttribute(name="model_vertex", data=aabb_triangle_strip, divisor=0)
        )
        field = self.data_source[self.field_type, self.color_field].astype("f4").d
        field.shape = (field.size, 1)
        va.attributes.append(VertexAttribute(name="color_field", data=field, divisor=1))
        self.size = field.size
        positions = np.empty((self.size, 3), dtype="f4")
        positions[:, 0] = self.data_source["index", "x"].in_units("unitary")
        positions[:, 1] = self.data_source["index", "y"].in_units("unitary")
        positions[:, 2] = self.data_source["index", "z"].in_units("unitary")
        va.attributes.append(
            VertexAttribute(name="position_field", data=positions, divisor=1)
        )
        widths = np.empty((self.size, 3), dtype="f4")
        widths[:, 0] = self.data_source["index", "dx"].in_units("unitary")
        widths[:, 1] = self.data_source["index", "dy"].in_units("unitary")
        widths[:, 2] = self.data_source["index", "dz"].in_units("unitary")
        va.attributes.append(
            VertexAttribute(name="width_field", data=widths, divisor=1)
        )
        return va
