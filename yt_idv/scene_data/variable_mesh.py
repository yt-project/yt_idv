import numpy as np
import traitlets
from yt.data_objects.selection_objects.data_selection_objects import (
    YTSelectionContainer2D,
)

from yt_idv.opengl_support import VertexArray, VertexAttribute
from yt_idv.scene_data.base_data import SceneData


class VariableMeshContainer(SceneData):
    name = "variable_mesh"
    data_source = traitlets.Instance(YTSelectionContainer2D)

    @traitlets.default("vertex_array")
    def _default_vertex_array(self):
        rv = VertexArray(name="vm_positions", each=1)
        return rv

    def add_data(self, field):
        if len(self.vertex_array.attributes) > 0:
            # Has already been initialized, so we just update the data
            self.vertex_array.attributes[-1].data = self.data_source[field].astype("f4")
            return
        for vfield in ("px", "py", "pdx", "pdy"):
            f = self.data_source[vfield].in_units("unitary").astype("f4")
            self.vertex_array.attributes.append(VertexAttribute(name=vfield, data=f))
        self.vertex_array.attributes.append(
            VertexAttribute(name="field", data=self.data_source[field].astype("f4"))
        )
        self.size = self.data_source["px"].size
