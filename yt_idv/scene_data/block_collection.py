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
    _yt_geom_str = traitlets.Unicode("cartesian")
    compute_min_max = traitlets.Bool(True)
    always_normalize = traitlets.Bool(False)

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

        self._yt_geom_str = str(self.data_source.ds.geometry)
        # note: casting to string for compatibility with new and old geometry
        # attributes (now an enum member in latest yt),
        # see https://github.com/yt-project/yt/pull/4244

        # Every time we change our data source, we wipe all existing ones.
        # We now set up our vertices into our current data source.
        vert, dx, le, re = [], [], [], []

        min_val = +np.inf
        max_val = -np.inf
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
            min_val = min(min_val, np.nanmin(np.abs(block.my_data[0])).min())
            max_val = max(max_val, np.nanmax(np.abs(block.my_data[0])).max())
            self.blocks[id(block)] = (i, block)
            vert.append([1.0, 1.0, 1.0, 1.0])
            dds = (block.RightEdge - block.LeftEdge) / block.source_mask.shape
            dx.append(dds.tolist())
            le.append(block.LeftEdge.tolist())
            re.append(block.RightEdge.tolist())
        for g, node, (sl, _, gi) in self.data_source.tiles.slice_traverse():
            block = node.data
            self.blocks_by_grid[g.id - g._id_offset].append((id(block), gi))
            self.grids_by_block[id(node.data)] = (g.id - g._id_offset, sl)

        if self.compute_min_max:
            if hasattr(min_val, "in_units"):
                min_val = min_val.d
            if hasattr(max_val, "in_units"):
                max_val = max_val.d
            self.min_val = min_val
            self.max_val = max_val

        # Now we set up our buffer
        vert = np.array(vert, dtype="f4")
        dx = np.array(dx, dtype="f4")
        le = np.array(le)
        re = np.array(re)
        if self._yt_geom_str == "cartesian":
            # Note: the block LeftEdge and RightEdge arrays are plain np arrays in
            # units of code_length, so need to convert to unitary units (in range 0,1)
            # after the fact:
            units = self.data_source.ds.units
            ratio = (units.code_length / units.unitary).base_value
            dx = dx * ratio
            le = le * ratio
            re = re * ratio
            LE = np.array([b.LeftEdge for i, b in self.blocks.values()]).min(axis=0)
            RE = np.array([b.RightEdge for i, b in self.blocks.values()]).max(axis=0)
            self.diagonal = np.sqrt(((RE - LE) ** 2).sum())
        elif self._yt_geom_str == "spherical":
            rad_index = self.data_source.ds.coordinates.axis_id["r"]
            max_r = self.data_source.ds.domain_right_edge[rad_index]
            le[:, rad_index] = le[:, rad_index] / max_r
            re[:, rad_index] = re[:, rad_index] / max_r
            dx[:, rad_index] = dx[:, rad_index] / max_r

        self._set_geometry_attributes(le, re, dx)
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

    def _set_geometry_attributes(self, le, re, dx):
        # set any vertex_array attributes that depend on the yt geometry type
        #
        # for spherical coordinates, the radial component of le, re and dx
        # should already be normalized in the range of (0, 1)

        if self._yt_geom_str == "cartesian":
            return
        elif self._yt_geom_str == "spherical":
            from yt_idv.utilities.coordinate_utilities import (
                SphericalMixedCoordBBox,
                cartesian_bboxes_edges,
            )

            axis_id = self.data_source.ds.coordinates.axis_id

            # first, we need an approximation of the grid spacing
            # in cartesian coordinates. this is used by the
            # ray tracing engine to determine along-ray step size
            # so doesn't have to be exact. the ordering also
            # doesn't matter since it's the min value that will
            # influence step size. So here, we find some representative
            # lengths: the change in radius across the element,
            # the arc lengths of an element using average values of r
            # and theta where needed (average values avoid the edge case
            # of 0. values, which will cause the shader to crash)
            dr = dx[:, axis_id["r"]]
            rh = (le[:, axis_id["r"]] + re[:, axis_id["r"]]) / 2
            rdtheta = rh * dx[:, axis_id["theta"]]
            th = (le[:, axis_id["theta"]] + re[:, axis_id["theta"]]) / 2
            xy = rh * np.sin(th)
            rdphi = xy * dx[:, axis_id["phi"]]
            dx_cart = np.column_stack([dr, rdtheta, rdphi])

            # cartesian bbox calculations
            bbox_handler = SphericalMixedCoordBBox()
            le_cart, re_cart = cartesian_bboxes_edges(
                bbox_handler,
                le[:, axis_id["r"]],
                le[:, axis_id["theta"]],
                le[:, axis_id["phi"]],
                re[:, axis_id["r"]],
                re[:, axis_id["theta"]],
                re[:, axis_id["phi"]],
            )
            le_cart = np.column_stack(le_cart)
            re_cart = np.column_stack(re_cart)

            # cartesian le, re, width of whole domain
            domain_le = le_cart.min(axis=0)
            domain_re = re_cart.max(axis=0)
            domain_wid = domain_re - domain_le
            max_wid = np.max(domain_wid)

            # these will get passed down as uniforms to go from screen coords of
            # 0,1 to cartesian coords of domain_le to domain_re from which full
            # spherical coords can be calculated.
            self.cart_bbox_max_width = max_wid
            self.cart_bbox_le = domain_le
            self.cart_bbox_center = (domain_re + domain_le) / 2.0
            self.cart_min_dx = np.min(np.linalg.norm(dx_cart))

            self.vertex_array.attributes.append(
                VertexAttribute(name="le_cart", data=le_cart.astype("f4"))
            )
            self.vertex_array.attributes.append(
                VertexAttribute(name="re_cart", data=re_cart.astype("f4"))
            )
            self.vertex_array.attributes.append(
                VertexAttribute(name="dx_cart", data=dx_cart.astype("f4"))
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
            if self.max_val != self.min_val or self.always_normalize:
                n_data = self._normalize_by_min_max(n_data)
                # blocks filled with identically 0 values will be
                # skipped by the shader, so offset by a tiny value.
                # see https://github.com/yt-project/yt_idv/issues/171
                n_data[n_data == 0.0] += np.finfo(np.float32).eps

            data_tex = Texture3D(data=n_data)
            bitmap_tex = Texture3D(
                data=block.source_mask * 255, min_filter="nearest", mag_filter="nearest"
            )
            self.texture_objects[vbo_i] = data_tex
            self.bitmap_objects[vbo_i] = bitmap_tex

    _grid_id_list = None

    @property
    def grid_id_list(self):
        """the 0-indexed grid ids that contain all the blocks"""
        if self._grid_id_list is None:
            gl = [gid for gid, _ in self.grids_by_block.values()]
            self._grid_id_list = np.unique(gl).tolist()
        return self._grid_id_list

    @property
    def intersected_grids(self):
        return [self.data_source.ds.index.grids[gid] for gid in self.grid_id_list]


def _block_collection_outlines(
    block_collection: BlockCollection,
    display_name: str = "block outlines",
    segments_per_edge: int = 20,
    outline_type: str = "blocks",
):
    """
    Build a CurveCollection and CurveCollectionRendering from BlockCollection
    bounding boxes for non-cartesian geometries.
    """

    if outline_type not in ("blocks", "grids"):
        msg = f"outline_type must be blocks or grids, found {outline_type}"
        raise ValueError(msg)

    if block_collection._yt_geom_str not in ("spherical",):
        msg = "_curves_from_block_data is not implemented for "
        msg += f"{block_collection._yt_geom_str} geometry."
        raise NotImplementedError(msg)

    from yt_idv.scene_components.curves import CurveCollectionRendering
    from yt_idv.scene_data.curve import CurveCollection

    data_collection = CurveCollection()

    if outline_type == "blocks":
        block_iterator = block_collection.data_source.tiles.traverse()
    else:
        # note this can be simplified after
        # https://github.com/yt-project/yt_idv/pull/179
        gids = [gid for gid, _ in block_collection.grids_by_block.values()]
        gids = np.unique(gids)
        ds = block_collection.data_source.ds
        block_iterator = [ds.index.grids[gid] for gid in gids]

    if block_collection._yt_geom_str == "spherical":
        from yt_idv.utilities.coordinate_utilities import spherical_to_cartesian

        # should move this down to cython to speed it up
        axis_id = block_collection.data_source.ds.coordinates.axis_id
        n_verts = segments_per_edge + 1
        for block in block_iterator:
            le_i = block.LeftEdge
            re_i = block.RightEdge

            r_min = le_i[axis_id["r"]]
            r_max = re_i[axis_id["r"]]

            theta_min = le_i[axis_id["theta"]]
            theta_max = re_i[axis_id["theta"]]

            phi_min = le_i[axis_id["phi"]]
            phi_max = re_i[axis_id["phi"]]

            theta_vals = np.linspace(theta_min, theta_max, n_verts)
            phi_vals = np.linspace(phi_min, phi_max, n_verts)

            # the r-variation will be straight lines always, only use 2 verts
            r_vals = np.linspace(r_min, r_max, 2)

            for r_val in (r_min, r_max):
                r = np.full(theta_vals.shape, r_val)
                for phi_val in (phi_min, phi_max):
                    phi = np.full(theta_vals.shape, phi_val)
                    x, y, z = spherical_to_cartesian(r, theta_vals, phi)
                    xyz = np.column_stack([x, y, z])
                    data_collection.add_curve(xyz)

                for theta_val in (theta_min, theta_max):
                    theta = np.full(phi_vals.shape, theta_val)
                    x, y, z = spherical_to_cartesian(r, theta, phi_vals)
                    xyz = np.column_stack([x, y, z])
                    data_collection.add_curve(xyz)

            for phi_val in (phi_min, phi_max):
                phi = np.full(r_vals.shape, phi_val)
                for theta_val in (theta_min, theta_max):
                    theta = np.full(r_vals.shape, theta_val)
                    x, y, z = spherical_to_cartesian(r_vals, theta, phi)
                    xyz = np.column_stack([x, y, z])
                    data_collection.add_curve(xyz)

    data_collection.add_data()  # call add_data() after done adding curves

    data_rendering = CurveCollectionRendering(data=data_collection)
    data_rendering.display_name = display_name

    return data_collection, data_rendering
