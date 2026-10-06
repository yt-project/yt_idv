from collections import defaultdict

import numpy as np
import traitlets
from yt.data_objects.data_containers import YTDataContainer

from yt_idv.opengl_support import TextureAtlas, VertexArray, VertexAttribute
from yt_idv.scene_data.base_data import SceneData

try:
    from yt.utilities.lib.amr_kdtools import viewpoint_node_ids
except ImportError:
    # yt versions without the array-filling kd-tree walk fall back to
    # AMRKDTree.traverse(viewpoint=...)
    viewpoint_node_ids = None


class BlockCollection(SceneData):
    name = "block_collection"
    data_source = traitlets.Instance(YTDataContainer, allow_none=True)
    # each block's (normalized) data and bitmap, by vertex array index, which
    # are uploaded to data_atlas and bitmap_atlas
    block_data = traitlets.Dict()
    block_bitmaps = traitlets.Dict()
    data_atlas = traitlets.Instance(TextureAtlas, allow_none=True)
    bitmap_atlas = traitlets.Instance(TextureAtlas, allow_none=True)
    blocks = traitlets.Dict(default_value=())
    scale = traitlets.Bool(False).tag(config=True)
    _compute_bbox = traitlets.Bool(False).tag(
        config=True
    )  # Useful only if you want a manual bbox calculation
    blocks_by_grid = traitlets.Instance(defaultdict, (list,))
    grids_by_block = traitlets.Dict(default_value=())
    _yt_geom_str = traitlets.Unicode("cartesian").tag(config=True)
    compute_min_max = traitlets.Bool(True).tag(config=True)
    always_normalize = traitlets.Bool(False).tag(config=True)
    field = traitlets.Any(default_value=None, allow_none=True).tag(config=True)
    field_units = traitlets.Unicode(default_value=None, allow_none=True).tag(
        config=True
    )
    # The transform from unitary coordinates to the model coordinates of the
    # vertex edges: model = (unitary - offset) / ratio. scale=True sets it from
    # the bounding box, and SceneGraph.rescale composes more onto it.
    applied_scale_ratio = traitlets.CFloat(1.0, read_only=True)
    applied_scale_offset = traitlets.Tuple(
        traitlets.CFloat(),
        traitlets.CFloat(),
        traitlets.CFloat(),
        default_value=(0.0, 0.0, 0.0),
        read_only=True,
    )

    # saved copies of data_source state, used when data_source is None
    _kd_tree = None
    _axis_id = None
    _bbox = None
    # the blocks' (left_edge, right_edge, dx) in unitary coordinates, in
    # float64; the vertex edges are recomputed from these on every rescale
    _unscaled_edges = None
    # unitary units per code_length, to put the camera in the kd-tree's units
    _unitary_per_code_length = None
    # (offset x, y, z, ratio), saved because the transform traits are read-only
    _saved_scale = None
    _restoring = False

    # buffers for viewpoint_node_ids
    _order_node_ids = None
    _order_node_inds = None

    _saved_attributes = SceneData._saved_attributes + (
        "block_data",
        "block_bitmaps",
        "_kd_tree",
        "_axis_id",
        "_bbox",
        "_unscaled_edges",
        "_unitary_per_code_length",
        "_saved_scale",
        "diagonal",
        "cart_bbox_max_width",
        "cart_bbox_le",
        "cart_bbox_center",
        "cart_min_dx",
    )

    @traitlets.default("vertex_array")
    def _default_vertex_array(self):
        return VertexArray(name="block_info", each=1)

    @traitlets.observe("scale")
    def toggle_scale(self, change):
        # a loaded scene's vertex edges are already scaled, and add_data
        # applies scale itself once there are edges
        if (
            self._yt_geom_str != "cartesian"
            or self._restoring
            or self._unscaled_edges is None
        ):
            return
        if not change["new"]:
            self._set_scale((0.0, 0.0, 0.0), 1.0)
            return
        if self._compute_bbox:
            left_edge, right_edge, _ = self._get_unscaled_edges()
            left_min = left_edge.min(axis=0)
            right_max = right_edge.max(axis=0)
        else:
            # the data source's bounding box, also saved with the scene
            bbox = self.bbox
            if bbox is None:
                raise RuntimeError(
                    "Scaling needs the data source's bounding box, which this "
                    "block collection doesn't have (it was loaded from a scene "
                    "saved without one). Set _compute_bbox to scale by the "
                    "blocks' extent instead."
                )
            left_min, right_max = bbox
        self._set_scale(left_min, (right_max - left_min).max())

    def apply_scale(self, offset, ratio):
        """
        Compose a further transform onto the current one, mapping model
        coordinates x to (x - offset) / ratio. The vertex edges are recomputed
        from the unscaled float64 edges, so repeated calls don't lose precision.
        See SceneGraph.rescale, which also moves the camera.
        """
        if self._yt_geom_str != "cartesian":
            raise NotImplementedError(
                f"{self.name} can only be rescaled for cartesian geometries."
            )
        current = self.applied_scale_ratio
        offset = np.asarray(self.applied_scale_offset) + current * np.asarray(
            offset, dtype="f8"
        )
        self._set_scale(offset, current * ratio)

    def _set_scale(self, offset, ratio):
        offset = np.asarray(offset, dtype="f8")
        left_edge, right_edge, dx = self._get_unscaled_edges()
        self.diagonal *= self.applied_scale_ratio / ratio
        self.set_trait("applied_scale_ratio", ratio)
        self.set_trait("applied_scale_offset", tuple(offset))
        # float64, cast to float32 only for the GPU, so a saved scene keeps them
        va = self.vertex_array
        va["in_left_edge"].data = (left_edge - offset) / ratio
        va["in_right_edge"].data = (right_edge - offset) / ratio
        va["in_dx"].data = dx / ratio

    def _get_unscaled_edges(self):
        if self._unscaled_edges is None:
            # a scene saved without them: undo the transform on the float32
            # vertex edges
            ratio = self.applied_scale_ratio
            offset = np.asarray(self.applied_scale_offset)
            va = self.vertex_array
            self._unscaled_edges = np.array(
                [
                    va["in_left_edge"].data.astype("f8") * ratio + offset,
                    va["in_right_edge"].data.astype("f8") * ratio + offset,
                    va["in_dx"].data.astype("f8") * ratio,
                ]
            )
        return self._unscaled_edges

    def _tree_viewpoint(self, position):
        # the camera is in model coordinates, but the kd-tree is in code_length
        if self._yt_geom_str != "cartesian":
            return position
        unitary = np.asarray(position, dtype="f8") * self.applied_scale_ratio
        unitary += np.asarray(self.applied_scale_offset)
        if self._unitary_per_code_length is None:
            # a scene saved without it
            return unitary
        return unitary / self._unitary_per_code_length

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
        self.field = self.data_source._determine_fields(field)[0]

        self._yt_geom_str = str(self.data_source.ds.geometry)
        # note: casting to string for compatibility with new and old geometry
        # attributes (now an enum member in latest yt),
        # see https://github.com/yt-project/yt/pull/4244

        # Every time we change our data source, we wipe all existing ones.
        # We now set up our vertices into our current data source.
        vert, dx, le, re = [], [], [], []
        self._unscaled_edges = None
        self.set_trait("applied_scale_ratio", 1.0)
        self.set_trait("applied_scale_offset", (0.0, 0.0, 0.0))

        min_val = +np.inf
        max_val = -np.inf
        for i, block in enumerate(self.data_source.tiles.traverse()):
            if self.field_units is None:
                self.field_units = str(getattr(block.my_data[0], "units", ""))
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
        self._tag_kd_leaves()

        if self.compute_min_max:
            if hasattr(min_val, "in_units"):
                min_val = min_val.d
            if hasattr(max_val, "in_units"):
                max_val = max_val.d
            self.min_val = min_val
            self.max_val = max_val

        # Now we set up our buffer
        vert = np.array(vert, dtype="f4")
        dx = np.array(dx)
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
            self._unitary_per_code_length = ratio
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
        # the edges stay float64 (cast to float32 only for the GPU), so saved
        # scenes keep their full precision
        self.vertex_array.attributes.append(VertexAttribute(name="in_dx", data=dx))
        self.vertex_array.attributes.append(
            VertexAttribute(name="in_left_edge", data=le)
        )
        self.vertex_array.attributes.append(
            VertexAttribute(name="in_right_edge", data=re)
        )

        if self._yt_geom_str == "cartesian":
            self._unscaled_edges = np.array([le, re, dx])
            if self.scale:
                self.toggle_scale({"new": True})

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

    def _tag_kd_leaves(self):
        # viewpoint_node_ids reports each leaf's node_ind, so store the leaf's
        # block index there. add_data numbers the blocks in the order
        # tiles.traverse() yields them, which is kd_traverse() order.
        for vbo_i, node in enumerate(self.data_source.tiles.tree.trunk.kd_traverse()):
            node.node_ind = vbo_i
        self._order_node_ids = np.empty(len(self.blocks), dtype="int64")
        self._order_node_inds = np.empty(len(self.blocks), dtype="int64")

    def viewpoint_order(self, camera):
        """
        The block indices, ordered from furthest to nearest the camera.

        Returns a uint32 array that can be used directly as an index buffer.
        """
        viewpoint = self._tree_viewpoint(camera.position)
        if self.data_source is None:
            order = _kd_viewpoint_order(self._kd_tree, viewpoint)
            return np.asarray(order, dtype="uint32")
        if viewpoint_node_ids is None:
            order = [
                self.blocks[id(block)][0]
                for block in self.data_source.tiles.traverse(viewpoint=viewpoint)
            ]
            return np.asarray(order, dtype="uint32")
        n = viewpoint_node_ids(
            self.data_source.tiles.tree.trunk,
            viewpoint,
            self._order_node_ids,
            self._order_node_inds,
        )
        return self._order_node_inds[:n].astype("uint32")

    @property
    def axis_id(self):
        """The mapping from coordinate axis names to indices."""
        if self.data_source is None:
            return self._axis_id
        return self.data_source.ds.coordinates.axis_id

    @property
    def bbox(self):
        """
        The data source's bounding box as (left_edge, right_edge) arrays in
        unitary units, or None for non-cartesian data. It is saved with the
        scene, so it is also available for a scene loaded from a file (None if
        the file predates it).
        """
        if self.data_source is None:
            if self._bbox is None:
                return None
            return self._bbox[0], self._bbox[1]
        if self._yt_geom_str != "cartesian":
            return None
        left_edge, right_edge = self.data_source.get_bbox()
        return left_edge.in_units("unitary").d, right_edge.in_units("unitary").d

    def _get_state(self, writer):
        self._saved_scale = np.array(
            [*self.applied_scale_offset, self.applied_scale_ratio]
        )
        if self.data_source is not None:
            bbox = self.bbox
            self._bbox = None if bbox is None else np.array(bbox)
            self._kd_tree = _flatten_kd_tree(self.data_source.tiles.tree.trunk)
            if self._yt_geom_str != "cartesian":
                self._axis_id = {
                    ax: self.axis_id[ax]
                    for ax in self.data_source.ds.coordinates.axis_order
                }
        return super()._get_state(writer)

    def _set_state(self, state, reader):
        # the saved vertex edges are already scaled, so restore the transform
        # without letting the restored scale trait re-apply it
        self._restoring = True
        try:
            super()._set_state(state, reader)
        finally:
            self._restoring = False
        if self._saved_scale is not None:
            self.set_trait("applied_scale_offset", tuple(self._saved_scale[:3]))
            self.set_trait("applied_scale_ratio", float(self._saved_scale[3]))
        if isinstance(self.field, list):
            self.field = tuple(self.field)
        # scenes saved before the texture atlas have a texture per block
        for old, new in (
            ("texture_objects", "block_data"),
            ("bitmap_objects", "block_bitmaps"),
        ):
            textures = self.__dict__.pop(old, None)
            if textures is not None:
                setattr(self, new, {i: tex.data for i, tex in textures.items()})
                for tex in textures.values():
                    tex.release()
        self._build_atlases()

    def _require_data_source(self, what):
        if self.data_source is None:
            raise RuntimeError(
                f"{what} requires the yt data source, which is not available "
                "for a block collection loaded from a saved scene."
            )

    def filter_callback(self, callback):
        self._require_data_source("filter_callback")
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
                self.block_bitmaps[vbo_i] = new_bitmap[sl]
                self.bitmap_atlas[vbo_i] = new_bitmap[sl]

    def _load_textures(self):
        self.block_data = {}
        self.block_bitmaps = {}
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

            self.block_data[vbo_i] = n_data
            self.block_bitmaps[vbo_i] = (block.source_mask * 255).astype("uint8")
        self._build_atlases()

    def _build_atlases(self):
        # Pack every block's data and bitmap into one texture each. The data
        # holds n + 1 vertex-centered values and the bitmap n cells, so they're
        # laid out separately. One texel of edge padding keeps interpolation
        # (and the bitmap's half-texel shift) inside each block.
        for atlas in (self.data_atlas, self.bitmap_atlas):
            if atlas is not None:
                atlas.release()
        n_blocks = len(self.block_data)
        atlases = {}
        for name, arrays, kwargs in (
            ("data", self.block_data, {}),
            (
                "bitmap",
                self.block_bitmaps,
                {"dtype": "uint8", "min_filter": "nearest", "mag_filter": "nearest"},
            ),
        ):
            sizes = [arrays[i].shape[:3] for i in range(n_blocks)]
            atlas = TextureAtlas(
                sizes,
                padding=1,
                vertex_array=self.vertex_array,
                offset_attribute_name=f"in_{name}_offset",
                size_attribute_name=f"in_{name}_size",
                **kwargs,
            )
            for i in range(n_blocks):
                atlas[i] = arrays[i]
            atlases[name] = atlas
        self.data_atlas = atlases["data"]
        self.bitmap_atlas = atlases["bitmap"]

    def release(self):
        for atlas in (self.data_atlas, self.bitmap_atlas):
            if atlas is not None:
                atlas.release()
        self.data_atlas = None
        self.bitmap_atlas = None
        self.vertex_array.release()

    @property
    def _textures_are_normalized(self) -> bool:
        # whether or not _load_textures min/max normalized the 3D textures
        return self.max_val != self.min_val or self.always_normalize

    @property
    def internal_length_unit(self):
        """
        The physical length of a single unit of the internal coordinate system.

        Block edges and spacings are rescaled before being handed to the shaders
        (to unitary units for cartesian data, to fractions of the maximum radius
        for spherical data), so any length measured in the rendered scene --
        camera offsets, ray path lengths -- must be multiplied by this value to
        get a physical length.
        """
        self._require_data_source("internal_length_unit")
        ds = self.data_source.ds
        if self._yt_geom_str == "cartesian":
            return ds.quan(self.applied_scale_ratio, "unitary").in_units("code_length")
        elif self._yt_geom_str == "spherical":
            rad_index = ds.coordinates.axis_id["r"]
            return ds.domain_right_edge[rad_index].in_units("code_length")
        raise NotImplementedError(
            f"{self.name} does not implement {self._yt_geom_str} geometries."
        )

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
        self._require_data_source("intersected_grids")
        return [self.data_source.ds.index.grids[gid] for gid in self.grid_id_list]


def _flatten_kd_tree(trunk):
    """
    Flatten a yt kd-tree into arrays of depth-first ordered nodes. ``block``
    is the vertex buffer index of each leaf's block, or -1.
    """
    nodes = list(trunk.depth_traverse())
    index = {id(node): i for i, node in enumerate(nodes)}
    n = len(nodes)
    left = np.full(n, -1, dtype="int64")
    right = np.full(n, -1, dtype="int64")
    split_dim = np.full(n, -1, dtype="int64")
    split_pos = np.full(n, np.nan, dtype="float64")
    block = np.full(n, -1, dtype="int64")
    n_blocks = 0
    for i, node in enumerate(nodes):
        if node.kd_is_leaf():
            if node.grid != -1:
                block[i] = n_blocks
                n_blocks += 1
            continue
        left[i] = index[id(node.left)]
        right[i] = index[id(node.right)]
        split_dim[i] = node.get_split_dim()
        split_pos[i] = node.get_split_pos()
    return {
        "left": left,
        "right": right,
        "split_dim": split_dim,
        "split_pos": split_pos,
        "block": block,
    }


def _kd_viewpoint_order(kd_tree, viewpoint):
    """
    Order the blocks of a flattened kd-tree from furthest to nearest a
    viewpoint, matching ``AMRKDTree.traverse(viewpoint=...)``.
    """
    left = kd_tree["left"]
    right = kd_tree["right"]
    split_dim = kd_tree["split_dim"]
    split_pos = kd_tree["split_pos"]
    block = kd_tree["block"]
    order = []
    stack = [0]
    while stack:
        i = stack.pop()
        if left[i] == -1:
            if block[i] != -1:
                order.append(int(block[i]))
            continue
        if viewpoint[split_dim[i]] <= split_pos[i]:
            stack.extend((left[i], right[i]))
        else:
            stack.extend((right[i], left[i]))
    return order


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

        rad_index = axis_id["r"]
        max_r = block_collection.data_source.ds.domain_right_edge[rad_index]

        for block in block_iterator:
            le_i = block.LeftEdge
            re_i = block.RightEdge

            r_min = le_i[axis_id["r"]] / max_r
            r_max = re_i[axis_id["r"]] / max_r

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
