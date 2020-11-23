from collections import defaultdict

import numpy as np
import traitlets
from yt.data_objects.data_containers import YTDataContainer

from yt_idv.opengl_support import (
    Texture3D,
    VertexArray,
    VertexAttribute,
    compute_box_geometry,
)
from yt_idv.scene_data.base_data import SceneData


class BlockCollection(SceneData):
    name = "block_collection"
    data_source = traitlets.Instance(YTDataContainer)
    texture_objects = traitlets.Dict(trait=traitlets.Instance(Texture3D))
    bitmap_objects = traitlets.Dict(trait=traitlets.Instance(Texture3D))
    blocks = traitlets.Dict(default_value=())
    scale = traitlets.Bool(False)
    blocks_by_grid = traitlets.Instance(defaultdict, (list,))
    grids_by_block = traitlets.Dict(default_value=())
    scale_matrix = traitlets.Instance(np.ndarray)

    @traitlets.default("scale_matrix")
    def _default_scale_matrix(self):
        return np.eye(4)

    @traitlets.default("vertex_array")
    def _default_vertex_array(self):
        return VertexArray(name="block_info", each=36)

    def add_data(self, field, no_ghost=False):
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
        self.data_source.tiles.set_fields([field], [False], no_ghost=no_ghost)
        # Every time we change our data source, we wipe all existing ones.
        # We now set up our vertices into our current data source.
        vert, dx, le, re = [], [], [], []
        self.min_val = +np.inf
        self.max_val = -np.inf
        left_min = np.ones(3, "f8") * np.inf
        right_max = np.ones(3, "f8") * -np.inf
        for i, block in enumerate(self.data_source.tiles.traverse()):
            np.minimum(left_min, block.LeftEdge, left_min)
            np.maximum(right_max, block.RightEdge, right_max)
            self.min_val = min(self.min_val, np.nanmin(np.abs(block.my_data[0]).min()))
            self.max_val = max(self.max_val, np.nanmax(np.abs(block.my_data[0]).max()))
            self.blocks[id(block)] = (i, block)
            vert.append(compute_box_geometry(block.LeftEdge, block.RightEdge))
            dds = (block.RightEdge - block.LeftEdge) / block.my_data[0].shape
            n = int(vert[-1].size) // 4
            dx.append([dds.astype("f4") for _ in range(n)])
            le.append([block.LeftEdge.astype("f4") for _ in range(n)])
            re.append([block.RightEdge.astype("f4") for _ in range(n)])
        for (g, node, (sl, _dims, _gi)) in self.data_source.tiles.slice_traverse():
            block = node.data
            self.blocks_by_grid[g.id - g._id_offset].append((id(block), i))
            self.grids_by_block[id(node.data)] = (g.id - g._id_offset, sl)

        if hasattr(self.min_val, "in_units"):
            self.min_val = self.min_val.d
        if hasattr(self.max_val, "in_units"):
            self.max_val = self.max_val.d

        LE = np.array([b.LeftEdge for i, b in self.blocks.values()]).min(axis=0)
        RE = np.array([b.RightEdge for i, b in self.blocks.values()]).max(axis=0)
        self.diagonal = np.sqrt(((RE - LE) ** 2).sum())
        # Now we set up our buffer
        vert = np.concatenate(vert)
        dx = np.concatenate(dx)
        le = np.concatenate(le)
        re = np.concatenate(re)
        scale = np.ones(4)
        scale[:3] = 1.0 / (right_max - left_min).max()
        translate = np.eye(4)
        translate[:3, 3] = (right_max + left_min) / 2.0
        self.scale_matrix = (np.eye(4) * scale) @ translate

        self.vertex_array.attributes.append(
            VertexAttribute(name="model_vertex", data=vert)
        )
        self.vertex_array.attributes.append(VertexAttribute(name="in_dx", data=dx))
        self.vertex_array.attributes.append(
            VertexAttribute(name="in_left_edge", data=le)
        )
        self.vertex_array.attributes.append(
            VertexAttribute(name="in_right_edge", data=re)
        )

        # Now we set up our textures
        self._load_textures()

    def viewpoint_iter(self, camera):
        for block in self.data_source.tiles.traverse(viewpoint=camera.position):
            vbo_i, _ = self.blocks[id(block)]
            yield (vbo_i, self.texture_objects[vbo_i], self.bitmap_objects[vbo_i])

    def filter_callback(self, callback):
        # This is not efficient.  It calls it once for each node in a grid.
        # We do this the slow way because of the problem of ordering the way we
        # iterate over the grids and nodes.  This can be fixed at some point.
        for g_ind in self.blocks_by_grid:
            blocks = self.blocks_by_grid[g_ind]
            # Does this need an offset?
            grid = self.data_source.index.grids[g_ind]
            new_bitmap = callback(grid).astype("uint8")
            for b_id, _ in blocks:
                _, sl = self.grids_by_block[b_id]
                vbo_i, _ = self.blocks[b_id]
                self.bitmap_objects[vbo_i].data = new_bitmap[sl]

    def _load_textures(self):
        for block_id in sorted(self.blocks):
            vbo_i, block = self.blocks[block_id]
            n_data = np.abs(block.my_data[0]).copy(order="F").astype("float32").d
            n_data = (n_data - self.min_val) / (
                (self.max_val - self.min_val)
            )  # * self.diagonal)
            data_tex = Texture3D(data=n_data)
            bitmap_tex = Texture3D(
                data=block.source_mask * 255, min_filter="nearest", mag_filter="nearest"
            )
            self.texture_objects[vbo_i] = data_tex
            self.bitmap_objects[vbo_i] = bitmap_tex
