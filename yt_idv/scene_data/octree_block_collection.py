import numpy as np
import OpenGL.GL as GL
import traitlets
from yt.data_objects.data_containers import YTDataContainer
from yt.data_objects.index_subobjects.octree_subset import OctreeSubsetBlockSlice

from yt_idv.constants import aabb_triangle_strip
from yt_idv.opengl_support import Texture3D, VertexArray, VertexAttribute
from yt_idv.scene_data.base_data import SceneData


class OctreeBlockCollection(SceneData):
    name = "octree_block_collection"
    data_source = traitlets.Instance(YTDataContainer)
    data_textures = traitlets.List(value_trait=traitlets.Instance(Texture3D))
    bitmap_textures = traitlets.List(value_trait=traitlets.Instance(Texture3D))
    shapes = traitlets.List(value_trait=traitlets.CInt())

    @traitlets.default("vertex_array")
    def _default_vertex_array(self):
        return VertexArray(name="octree_block_info", each=14)

    def add_data(self, field):
        r"""Adds a source of data for the block collection.

        Given a `data_source` and a `field` to populate from, adds the data
        to the block collection so that is able to be rendered.

        Parameters
        ----------
        data_source : YTRegion
            A YTRegion object to use as a data source.
        field : string
            A field to populate from.
        no_ghost : bool (False)
            Should we speed things up by skipping ghost zone generation?
        """
        ds = self.data_source.ds
        ds.index._identify_base_chunk(self.data_source)
        left_edges = []
        right_edges = []
        dx = []
        data = []

        for obj in self.data_source._current_chunk.objs:
            bs = OctreeSubsetBlockSlice(obj, ds)
            LE = bs._fcoords[0, 0, 0, :, :].d - bs._fwidth[0, 0, 0, :, :].d * 0.5
            RE = bs._fcoords[-1, -1, -1, :, :].d + bs._fwidth[-1, -1, -1, :, :].d * 0.5
            dx.append(bs._fwidth[-1, -1, -1, :, :].d)
            left_edges.append(LE)
            right_edges.append(RE)
            data.append(bs.get_vertex_centered_data([field])[field])

        # Let's reshape ...

        left_edges = np.concatenate(left_edges, axis=0).astype("f4")
        right_edges = np.concatenate(right_edges, axis=0).astype("f4")
        dx = np.concatenate(dx, axis=0).astype("f4")
        data = np.concatenate(data, axis=-1).astype("f4")
        data = data.reshape((3, 3, -1))

        self.min_val = np.nanmin(data)
        self.min_val = np.nanmax(data)

        if hasattr(self.min_val, "in_units"):
            self.min_val = self.min_val.d
        if hasattr(self.max_val, "in_units"):
            self.max_val = self.max_val.d

        self.vertex_array.attributes.append(
            VertexAttribute(name="model_vertex", data=aabb_triangle_strip, divisor=0)
        )
        self.vertex_array.attributes.append(
            VertexAttribute(name="in_dx", data=dx, divisor=1)
        )
        self.vertex_array.attributes.append(
            VertexAttribute(name="in_left_edge", data=left_edges, divisor=1)
        )
        self.vertex_array.attributes.append(
            VertexAttribute(name="in_right_edge", data=right_edges, divisor=1)
        )

        # Now we set up our textures; we need to break our texture up into
        # groups of MAX_3D_TEXTURE_SIZE
        tex_size = GL.glGetInteger(GL.GL_MAX_3D_TEXTURE_SIZE)
        # for now, use one texture for all the bitmaps
        bt = Texture3D(data=np.ones((3, 3, tex_size), dtype="u1") * 255)
        for start_index in np.mgrid[0 : data.shape[-1] : tex_size]:
            d = data[:, :, start_index : start_index + tex_size]
            self.data_textures.append(Texture3D(data=d))
            self.bitmap_textures.append(bt)
            self.shapes.append(d.shape[-1])
