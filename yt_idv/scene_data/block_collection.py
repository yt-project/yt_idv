from collections import defaultdict

import numpy as np
import traitlets
from yt.data_objects.data_containers import YTDataContainer

from yt_idv.opengl_support import Texture3D, VertexArray, VertexAttribute
from yt_idv.scene_data.base_data import SceneData


class BlockCollection(SceneData):
    name = "block_collection"
    data_source = traitlets.Instance(YTDataContainer)
    texture_objects = traitlets.Dict(value_trait=traitlets.Instance(Texture3D))
    bitmap_objects = traitlets.Dict(value_trait=traitlets.Instance(Texture3D))
    blocks = traitlets.Dict(default_value=())
    scale = traitlets.Bool(False)
    blocks_by_grid = traitlets.Instance(defaultdict, (list,))
    grids_by_block = traitlets.Dict(default_value=())

    @traitlets.default("vertex_array")
    def _default_vertex_array(self):
        return VertexArray(name="block_info", each=1)

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
        if self.scale and self._yt_geom_str == "cartesian":
            left_min = np.ones(3, "f8") * np.inf
            right_max = np.ones(3, "f8") * -np.inf
            for block in self.data_source.tiles.traverse():
                np.minimum(left_min, block.LeftEdge, left_min)
                np.maximum(right_max, block.LeftEdge, right_max)
            scale = right_max.max() - left_min.min()
            for block in self.data_source.tiles.traverse():
                block.LeftEdge -= left_min
                block.LeftEdge /= scale
                block.RightEdge -= left_min
                block.RightEdge /= scale
        for i, block in enumerate(self.data_source.tiles.traverse()):
            self.min_val = min(self.min_val, np.nanmin(np.abs(block.my_data[0])).min())
            self.max_val = max(self.max_val, np.nanmax(np.abs(block.my_data[0])).max())
            self.blocks[id(block)] = (i, block)
            vert.append([1.0, 1.0, 1.0, 1.0])
            dds = (block.RightEdge - block.LeftEdge) / block.source_mask.shape
            dx.append(dds.tolist())
            le.append(block.LeftEdge.tolist())
            re.append(block.RightEdge.tolist())
        for g, node, (sl, _dims, _gi) in self.data_source.tiles.slice_traverse():
            block = node.data
            self.blocks_by_grid[g.id - g._id_offset].append((id(block), i))
            self.grids_by_block[id(node.data)] = (g.id - g._id_offset, sl)

        if hasattr(self.min_val, "in_units"):
            self.min_val = self.min_val.d
        if hasattr(self.max_val, "in_units"):
            self.max_val = self.max_val.d

        # Now we set up our buffer
        vert = np.array(vert, dtype="f4")
        dx = np.array(dx, dtype="f4")
        le = np.array(le)
        re = np.array(re)
        if self._yt_geom_str == "cartesian":
            units = self.data_source.ds.units
            ratio = (units.code_length / units.unitary).base_value
            dx = dx * ratio
            le = le * ratio
            re = re * ratio
            LE = np.array([b.LeftEdge for i, b in self.blocks.values()]).min(axis=0)
            RE = np.array([b.RightEdge for i, b in self.blocks.values()]).max(axis=0)
            self.diagonal = np.sqrt(((RE - LE) ** 2).sum())

        self._set_geometry_attributes(le, re)
        self.vertex_array.attributes.append(
            VertexAttribute(name="model_vertex", data=vert)
        )
        self.vertex_array.attributes.append(VertexAttribute(name="in_dx", data=dx))
        self.vertex_array.attributes.append(
            VertexAttribute(name="in_left_edge", data=le.astype("f4"))
        )
        self.vertex_array.attributes.append(
            VertexAttribute(name="in_right_edge", data=re.astype("f4"))
        )

        # Now we set up our textures
        self._load_textures()

    @property
    def _yt_geom_str(self):
        # note: casting to string for compatibility with new and old geometry
        # attributes (now an enum member in latest yt),
        # see https://github.com/yt-project/yt/pull/4244
        return str(self.data_source.ds.geometry)

    def _set_geometry_attributes(self, le, re):
        # set any vertex_array attributes that depend on the yt geometry type

        if self._yt_geom_str == "cartesian":
            return
        elif self._yt_geom_str == "spherical":
            from yt_idv.coordinate_utilities import (
                SphericalMixedCoordBBox,
                cartesian_bboxes,
            )

            axis_id = self.data_source.ds.coordinates.axis_id
            # cartesian bbox calcualtions
            # TODO: clean this up by rewriting the cython a bit...
            widths = re - le
            centers = (le + re) / 2.0
            bbox_handler = SphericalMixedCoordBBox()
            r = centers[:, axis_id["r"]].astype("float64")
            theta = centers[:, axis_id["theta"]].astype("float64")
            phi = centers[:, axis_id["phi"]].astype("float64")
            dr = widths[:, axis_id["r"]].astype("float64")
            dtheta = widths[:, axis_id["theta"]].astype("float64")
            dphi = widths[:, axis_id["phi"]].astype("float64")
            x = np.full(r.shape, np.nan, dtype="float64")
            y = np.full(r.shape, np.nan, dtype="float64")
            z = np.full(r.shape, np.nan, dtype="float64")
            dx = np.full(r.shape, np.nan, dtype="float64")
            dy = np.full(r.shape, np.nan, dtype="float64")
            dz = np.full(r.shape, np.nan, dtype="float64")
            cartesian_bboxes(
                bbox_handler, r, theta, phi, dr, dtheta, dphi, x, y, z, dx, dy, dz
            )
            le_cart = np.column_stack([x - dx / 2.0, y - dy / 2.0, z - dz / 2.0])
            re_cart = np.column_stack([x + dx / 2.0, y + dy / 2.0, z + dz / 2.0])

            # cartesian le, re, width of whole domain
            domain_le = []
            domain_re = []
            domain_wid = []
            for idim in range(3):
                domain_le.append(le_cart[:, idim].min())
                domain_re.append(re_cart[:, idim].max())
                domain_wid.append(domain_re[idim] - domain_le[idim])

            # normalize to viewport in (0, 1), preserving ratio of the bounding box
            max_wid = np.max(domain_wid)
            for idim in range(3):
                le_cart[:, idim] = (le_cart[:, idim] - domain_le[idim]) / max_wid
                re_cart[:, idim] = (re_cart[:, idim] - domain_le[idim]) / max_wid

            le_cart = np.asarray(le_cart)
            re_cart = np.asarray(re_cart)

            # these will get passed down as uniforms to go from screen coords of
            # 0,1 to cartesian coords of domain_le to domain_re from which full
            # spherical coords can be calculated.
            self.cart_bbox_max_width = max_wid
            self.cart_bbox_le = np.array(domain_le).astype("f4")

            self.vertex_array.attributes.append(
                VertexAttribute(name="le_cart", data=le_cart.astype("f4"))
            )
            self.vertex_array.attributes.append(
                VertexAttribute(name="re_cart", data=re_cart.astype("f4"))
            )

            # does not seem that diagonal is used anywhere, but recalculating to
            # be safe...
            self.diagonal = np.sqrt(((re_cart - le_cart) ** 2).sum())
        else:
            raise NotImplementedError(
                f"{self.name} does not implement {self._yt_geom_str} geometries."
            )

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
            # Avoid setting to NaNs
            if self.max_val != self.min_val:
                n_data = self._normalize_by_min_max(n_data)

            data_tex = Texture3D(data=n_data)
            bitmap_tex = Texture3D(
                data=block.source_mask * 255, min_filter="nearest", mag_filter="nearest"
            )
            self.texture_objects[vbo_i] = data_tex
            self.bitmap_objects[vbo_i] = bitmap_tex
