import numpy as np
import traitlets
from yt.data_objects.data_containers import YTDataContainer
from yt.units.dimensions import length

from yt_idv.opengl_support import VertexArray, VertexAttribute
from yt_idv.scene_data.base_data import SceneData


class ParticlePositions(SceneData):
    name = "particle_positions"
    data_source = traitlets.Instance(YTDataContainer)
    particle_type = traitlets.Unicode("all")
    radius_field = traitlets.Unicode(None, allow_none=True)
    color_field = traitlets.Unicode(None, allow_none=True)
    position_field = traitlets.Unicode("particle_position")
    size = traitlets.CInt(-1)

    @traitlets.default("vertex_array")
    def _default_vertex_array(self):
        model_vertex = np.array(
            [[-1, 1], [-1, -1], [1, 1], [1, -1]], order="F", dtype="f4"
        )
        va = VertexArray(name="particle_positions")
        va.attributes.append(
            VertexAttribute(name="model_vertex", data=model_vertex, divisor=0)
        )
        for attr in ("position_field", "radius_field", "color_field"):
            if getattr(self, attr) is None:
                continue
            field = self.data_source[self.particle_type, getattr(self, attr)]
            if field.units.dimensions is length:
                field.convert_to_units("unitary")
            field = field.astype("f4").d
            if field.ndim == 1:
                field.shape = (field.size, 1)
            else:
                self.size = field.shape[0]  # for positions
            print(f"Setting {attr} to a field of shape {field.shape}")
            va.attributes.append(VertexAttribute(name=attr, data=field, divisor=1))
        print(f"Size is now: {self.size}")
        return va
