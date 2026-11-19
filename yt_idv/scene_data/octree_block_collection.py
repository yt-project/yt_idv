import numpy as np
from yt.data_objects.index_subobjects.octree_subset import OctreeSubsetBlockSlice

from yt_idv.opengl_support import VertexAttribute
from yt_idv.scene_data.block_collection import BlockCollection


class OctreeBlockCollection(BlockCollection):
    """
    The leaf cells of an octree dataset, such as RAMSES, as a block collection.

    Each oct whose eight cells are all leaves becomes a block of 2x2x2 cells,
    and each leaf cell of a partially refined oct becomes a block of its own,
    so the blocks tile the data source without overlapping. They are ordered
    as a kd-tree splitting each oct at its center orders them, and rendered by
    :class:`~yt_idv.scene_components.blocks.BlockRendering` like the blocks of
    a grid dataset.
    """

    name = "octree_block_collection"

    # the blocks' lower corners as integers, in units of _lo_cell from
    # _lo_origin (code_length), which viewpoint_order sorts by
    _block_lo = None
    _lo_origin = None
    _lo_cell = None
    # the Morton keys of _block_lo, and recent orders by the viewpoint cell
    # they are for
    _block_keys = None
    _order_cache = None

    _saved_attributes = BlockCollection._saved_attributes + (
        "_block_lo",
        "_lo_origin",
        "_lo_cell",
    )

    def add_data(self, field, no_ghost=False):
        r"""Adds a source of data for the block collection.

        Given a `data_source` and a `field` to populate from, adds the data
        to the block collection so that is able to be rendered.

        Parameters
        ----------
        field : string
            A field to populate from.
        no_ghost : bool (False)
            Should we speed things up by skipping ghost zone generation? If
            so, the vertex values of an oct are averages of its own cells, and
            a leaf cell of a partially refined oct has its own value at every
            vertex.
        """
        ds = self.data_source.ds
        if str(ds.geometry) != "cartesian":
            raise NotImplementedError(
                f"{self.name} does not implement {ds.geometry} geometries."
            )
        self.field = self.data_source._determine_fields(field)[0]
        self._yt_geom_str = "cartesian"
        self._render_geom = "cartesian"
        self._unscaled_edges = None
        self.set_trait("applied_scale_ratio", 1.0)
        self.set_trait("applied_scale_offset", (0.0, 0.0, 0.0))

        octs, cells = self._leaf_blocks_no_ghost() if no_ghost else self._leaf_blocks()
        units = ds.units
        self._set_blocks(
            octs,
            cells,
            origin=ds.domain_left_edge.to("code_length").d,
            unitary_per_code_length=(units.code_length / units.unitary).base_value,
        )

    def _set_blocks(self, octs, cells, origin, unitary_per_code_length):
        # Set up the vertex array, textures and ordering for the blocks in
        # octs and cells, as _leaf_blocks returns them. origin is the domain's
        # left edge, and their positions are in code_length.
        values = np.concatenate([octs["data"].ravel(), cells["data"].ravel()])
        if self.compute_min_max:
            self.min_val = float(np.nanmin(values))
            self.max_val = float(np.nanmax(values))

        left_edge = np.concatenate([octs["left_edge"], cells["left_edge"]])
        dx = np.concatenate([octs["dx"], cells["dx"]])
        n_cells = np.repeat([2, 1], [len(octs["dx"]), len(cells["dx"])])
        right_edge = left_edge + dx * n_cells[:, None]

        cell = dx.min()
        lo = np.rint((left_edge - origin) / cell).astype("int64")
        order = np.argsort(_morton_keys(lo), kind="stable")
        self._block_lo = lo[order]
        self._lo_origin = origin
        self._lo_cell = cell
        self._block_keys = None
        self._order_cache = None

        if self._textures_are_normalized:
            for blocks in (octs, cells):
                n_data = self._normalize_by_min_max(blocks["data"])
                # the smallest normal, rather than zero, as in BlockCollection
                n_data[n_data == 0.0] = np.finfo(np.float32).tiny
                blocks["data"] = n_data
        n_octs = len(octs["dx"])
        bitmaps = (np.full((2, 2, 2), 255, "uint8"), np.full((1, 1, 1), 255, "uint8"))
        self.block_data = {
            i: octs["data"][b] if b < n_octs else cells["data"][b - n_octs]
            for i, b in enumerate(order.tolist())
        }
        self.block_bitmaps = {
            i: bitmaps[0] if b < n_octs else bitmaps[1]
            for i, b in enumerate(order.tolist())
        }

        # Block edges are in code_length, so they are converted to unitary
        ratio = unitary_per_code_length
        self._unitary_per_code_length = ratio
        le = left_edge[order] * ratio
        re = right_edge[order] * ratio
        dx = dx[order] * ratio
        self.diagonal = np.sqrt(((re.max(axis=0) - le.min(axis=0)) ** 2).sum())

        self.vertex_array.attributes.append(
            VertexAttribute(name="model_vertex", data=np.ones((len(le), 4), "f4"))
        )
        self.vertex_array.attributes.append(VertexAttribute(name="in_dx", data=dx))
        self.vertex_array.attributes.append(
            VertexAttribute(name="in_left_edge", data=le)
        )
        self.vertex_array.attributes.append(
            VertexAttribute(name="in_right_edge", data=re)
        )
        self._unscaled_edges = np.array([le, re, dx])
        if self.scale:
            self.toggle_scale({"new": True})
        self._build_atlases()

    def _leaf_blocks(self):
        # The data, left edges (code_length) and cell widths of the octs whose
        # cells are all leaves, and of the leaf cells of the other octs.
        # yt's oct arrays are indexed [z, y, x], and the textures [x, y, z].
        ds = self.data_source.ds
        ds.index._identify_base_chunk(self.data_source)
        selector = self.data_source.selector
        corner = np.indices((2, 2, 2)).reshape(3, 1, 2, 2, 2)
        octs = {"data": [], "left_edge": [], "dx": []}
        cells = {"data": [], "left_edge": [], "dx": []}
        for obj in self.data_source._current_chunk.objs:
            leaves = obj.mask_refinement(selector).astype(bool).transpose(0, 3, 2, 1)
            if not leaves.any():
                continue
            slicer = OctreeSubsetBlockSlice(obj, ds)
            vertex_data = slicer.get_vertex_centered_data([self.field])[self.field]
            if self.field_units is None:
                self.field_units = str(vertex_data.units)
            vertex_data = np.abs(vertex_data.d).transpose(3, 2, 1, 0)
            dx = slicer._fwidth[0, 0, 0].to("code_length").d
            left_edge = slicer._fcoords[0, 0, 0].to("code_length").d - dx / 2

            full = leaves.all(axis=(1, 2, 3))
            octs["data"].append(vertex_data[full])
            octs["left_edge"].append(left_edge[full])
            octs["dx"].append(dx[full])

            o, i, j, k = np.nonzero(leaves & ~full[:, None, None, None])
            cells["data"].append(
                vertex_data[
                    o[:, None, None, None],
                    i[:, None, None, None] + corner[0],
                    j[:, None, None, None] + corner[1],
                    k[:, None, None, None] + corner[2],
                ]
            )
            cells["left_edge"].append(left_edge[o] + np.stack([i, j, k], 1) * dx[o])
            cells["dx"].append(dx[o])
        return _concatenate_blocks(octs, cells)

    def _leaf_blocks_no_ghost(self):
        # As _leaf_blocks, from the leaf cells of the data source alone
        source = self.data_source
        values = source[self.field]
        if self.field_units is None:
            self.field_units = str(values.units)
        return _blocks_from_leaf_cells(
            np.stack([source["index", ax].to("code_length").d for ax in "xyz"], 1),
            np.stack(
                [source["index", f"d{ax}"].to("code_length").d for ax in "xyz"], 1
            ),
            np.abs(values.d),
            source.ds.domain_left_edge.to("code_length").d,
        )

    def viewpoint_order(self, camera, nearest_first=False):
        """
        The block indices, ordered from furthest to nearest the camera, unless
        *nearest_first* is True, in which case it's the opposite. This is the
        order of the kd-tree, found by sorting rather than walking it.

        Returns a uint32 array that can be used directly as an index buffer.
        """
        viewpoint = self._tree_viewpoint(camera.position)
        # Every split plane is at an integer strictly inside the domain, so
        # the order only depends on the integer each viewpoint coordinate
        # rounds up to, clamped to the domain: a camera outside the domain
        # sees one order from each side of it.
        top = 1 << max(int(self._block_lo.max()).bit_length(), 1)
        cell = np.ceil((viewpoint - self._lo_origin) / self._lo_cell)
        cell = tuple(np.clip(cell, 0, top).tolist())
        if self._order_cache is None:
            self._order_cache = {}
        order = self._order_cache.pop(cell, None)
        if order is None:
            if self._block_keys is None:
                self._block_keys = _morton_keys(self._block_lo)
            order = _octree_viewpoint_order(
                self._block_lo, np.array(cell), self._block_keys
            )
            if len(self._order_cache) >= 8:
                del self._order_cache[next(iter(self._order_cache))]
        self._order_cache[cell] = order
        return order[::-1].copy() if nearest_first else order

    def _flattened_kd_tree(self):
        # viewpoint_order sorts by _block_lo instead
        return None

    def filter_callback(self, callback):
        raise NotImplementedError(f"{self.name} does not support filter_callback.")


def _blocks_from_leaf_cells(center, dx, values, origin):
    """
    The octs and cells of ``OctreeBlockCollection._leaf_blocks``, from the
    centers, widths and values of the leaf cells of an octree with its origin
    at ``origin``.

    The cells are grouped into octs by their parents. An oct whose eight
    cells are all leaves is a block, with vertex values that are averages of
    its cells, padded at its faces with copies of them; any other leaf cell is
    a block of its own, with its value at every vertex.
    """
    # each cell's position in units of its own width, and its parent's
    index = np.rint((center - dx / 2 - origin) / dx).astype("int64")
    level = np.rint(np.log2(dx[:, 0].max() / dx[:, 0])).astype("int64")
    parent = np.column_stack([level, index >> 1])
    # number the octs by grouping the cells with equal parents
    order = np.lexsort(parent.T[::-1])
    starts = np.ones(len(order), dtype=bool)
    starts[1:] = (parent[order[1:]] != parent[order[:-1]]).any(axis=1)
    oct_id = np.empty(len(order), dtype="int64")
    oct_id[order] = np.cumsum(starts) - 1
    n_children = np.bincount(oct_id)
    full = n_children[oct_id] == 8

    cell_values = np.zeros((len(n_children), 2, 2, 2), dtype="float64")
    child = index & 1
    cell_values[oct_id[full], child[full, 0], child[full, 1], child[full, 2]] = values[
        full
    ]
    oct_ids, first = np.unique(oct_id[full], return_index=True)
    padded = np.pad(cell_values[oct_ids], ((0, 0), (1, 1), (1, 1), (1, 1)), "edge")
    corner = np.indices((2, 2, 2)).reshape(3, -1).T
    vertex_data = sum(
        padded[:, i : i + 3, j : j + 3, k : k + 3] for i, j, k in corner
    ) / len(corner)
    full_cells = np.flatnonzero(full)[first]
    partial = ~full
    octs = {
        "data": [vertex_data],
        "left_edge": [origin + (index[full_cells] >> 1 << 1) * dx[full_cells]],
        "dx": [dx[full_cells]],
    }
    cells = {
        "data": [
            np.broadcast_to(values[partial, None, None, None], (partial.sum(), 2, 2, 2))
        ],
        "left_edge": [origin + index[partial] * dx[partial]],
        "dx": [dx[partial]],
    }
    return _concatenate_blocks(octs, cells)


def _concatenate_blocks(octs, cells):
    # each of the lists of arrays in octs and cells as a single array
    for blocks, shape in ((octs, (3, 3, 3)), (cells, (2, 2, 2))):
        for key, empty in (("data", shape), ("left_edge", (3,)), ("dx", (3,))):
            arrays = blocks[key] or [np.empty((0, *empty))]
            blocks[key] = np.concatenate(arrays).astype(
                "float32" if key == "data" else "float64"
            )
    return octs, cells


def _octree_viewpoint_order(lo, viewpoint, keys=None):
    """
    The order, from furthest to nearest an integer viewpoint, of a kd-tree
    that splits each oct at its center, as a uint32 array. ``lo`` holds the
    blocks' lower corners, which are aligned to their power-of-two sizes, and
    ``keys`` their Morton keys, if they have already been computed.

    Each bit of a block's Morton key is the side of one such split that it
    lies on. Flipping it so that it is 1 on the side nearer the viewpoint
    makes the keys sort furthest first: two blocks are ordered by the first
    split that separates them, as the kd-tree walk orders them.
    """
    lo = np.asarray(lo, dtype="int64")
    bits = max(int(lo.max()).bit_length() if len(lo) else 1, 1)
    if keys is None:
        keys = _morton_keys(lo)
    flips = np.zeros(len(lo), dtype="uint64")
    for axis in range(3):
        coord = lo[:, axis]
        # The split at bit p is at plane = (coord's bits above p) + 2**p, and
        # the left side is nearer when the viewpoint is at or below it, so the
        # key bit is flipped when that is true. Below the highest bit where
        # coord and the viewpoint differ, which side of every plane the
        # viewpoint is on follows from that bit alone; at and above it, the
        # planes are the viewpoint's own, so the flips are the same for all.
        # Every plane is strictly between 0 and 2**bits, so a viewpoint
        # outside that range orders the blocks as one on its edge does.
        view = min(max(int(viewpoint[axis]), 0), 1 << bits)
        same = 0
        for bit in range(bits):
            if view % (2 << bit) <= (1 << bit):
                same |= 1 << bit
        differ = np.frexp((coord ^ view).astype("float64"))[1]
        highest = np.maximum(differ - 1, 0)
        # the bits below the highest differing one, if coord is the higher;
        # they are flipped in their spread (Morton) positions directly
        coord_higher = ((coord >> highest) & 1).astype(bool) & (differ > 0)
        below = _SPREAD_LOW_BITS[highest]
        flip = (_spread_bits(same) & ~below) | np.where(coord_higher, below, 0)
        flips |= flip << np.uint64(2 - axis)
    # the keys are distinct, so the sort needn't be stable
    return np.argsort(keys ^ flips).astype("uint32")


def _spread_bits(x):
    # Move bit p of each value (up to 21 bits) to bit 3 * p, for Morton keys
    x = np.asarray(x).astype("uint64") & np.uint64(0x1FFFFF)
    for shift, mask in (
        (32, 0x1F00000000FFFF),
        (16, 0x1F0000FF0000FF),
        (8, 0x100F00F00F00F00F),
        (4, 0x10C30C30C30C30C3),
        (2, 0x1249249249249249),
    ):
        x = (x | (x << np.uint64(shift))) & np.uint64(mask)
    return x


# the spread (Morton) positions of the lowest q bits, for q up to 22
_SPREAD_LOW_BITS = _spread_bits((1 << np.arange(23, dtype="uint64")) - np.uint64(1))


def _morton_keys(lo):
    """Morton keys of integer coordinates, x in the highest bit of each triple."""
    lo = np.asarray(lo, dtype="int64")
    if len(lo) and (lo.min() < 0 or lo.max() >= 1 << 21):
        raise ValueError("Octree coordinates must be in [0, 2**21).")
    return (
        (_spread_bits(lo[:, 0]) << np.uint64(2))
        | (_spread_bits(lo[:, 1]) << np.uint64(1))
        | _spread_bits(lo[:, 2])
    )
