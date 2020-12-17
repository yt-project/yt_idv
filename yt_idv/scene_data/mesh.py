import numpy as np
import traitlets
from yt.data_objects.data_containers import YTDataContainer
from yt.utilities.lib.mesh_triangulation import triangulate_mesh

from yt_idv.opengl_support import Texture3D, VertexArray, VertexAttribute
from yt_idv.scene_data.base_data import SceneData


class MeshData(SceneData):
    name = "mesh"
    data_source = traitlets.Instance(YTDataContainer)
    texture_objects = traitlets.Dict(trait=traitlets.Instance(Texture3D))
    texture_objects = traitlets.Dict(trait=traitlets.Instance(Texture3D))
    blocks = traitlets.Dict(default_value=())
    scale = traitlets.Bool(False)
    size = traitlets.CInt(-1)

    def get_mesh_data(self, data_source, field):
        """

        This reads the mesh data into a form that can be fed in to OpenGL.

        """

        # get mesh information
        try:
            ftype, fname = field
            mesh_id = int(ftype[-1])
        except ValueError:
            mesh_id = 0

        mesh = data_source.ds.index.meshes[mesh_id - 1]
        offset = mesh._index_offset
        vertices = mesh.connectivity_coords
        indices = mesh.connectivity_indices - offset

        data = data_source[field]

        return triangulate_mesh(vertices, data, indices)

    def add_data(self, field):
        v, d, i = self.get_mesh_data(self.data_source, field)
        v.shape = (v.size // 3, 3)
        v = np.concatenate([v, np.ones((v.shape[0], 1))], axis=-1).astype("f4")
        d.shape = (d.size, 1)
        i.shape = (i.size, 1)
        i = i.astype("uint32")
        # d[:] = np.mgrid[0.0:1.0:1j*d.size].astype("f4")[:,None]
        self.vertex_array.attributes.append(
            VertexAttribute(name="model_vertex", data=v)
        )
        self.vertex_array.attributes.append(
            VertexAttribute(name="vertex_data", data=d.astype("f4"))
        )
        self.vertex_array.indices = i
        self.size = i.size

    @traitlets.default("vertex_array")
    def _default_vertex_array(self):
        return VertexArray(name="mesh_info", each=0)
