"""Tests for a 3D texture-atlas packer.

Assumed interface (edit `run_pack` below if yours differs):

    pack(sizes, padding=0) -> (offsets, atlas_dims)

    sizes:      (N, 3) array-like of positive ints (w, h, d)
    padding:    border voxels added on every side of each box
    offsets:    np.ndarray, shape (N, 3), integer dtype, one row per input box
                in input order, giving the corner of the box's *interior*
                (unpadded) region
    atlas_dims: np.ndarray (or sequence), shape (3,), integer: (W, H, D)

A box therefore occupies [offset - padding, offset + size + padding) on
each axis, and that whole padded region must lie inside the atlas and must
not overlap any other box's padded region.

Run fast tests only:  pytest -m "not slow"
"""

import time

import numpy as np
import pytest

from yt_idv.texture_packing import pack

# ---- knobs to tune for your implementation ---------------------------------
TIGHT_DIMS = True  # False if you round the atlas up (e.g. to powers of two)
MIN_FILL = 0.85  # minimum acceptable fill ratio on realistic inputs
TIME_LIMIT_S = 10.0  # budget for packing 200k boxes
MAX_CHECK_VOXELS = 2**30  # occupancy-grid limit for the overlap check (bytes)
# -----------------------------------------------------------------------------


def run_pack(sizes, padding=0):
    return pack(sizes, padding=padding)


# ---- helpers -----------------------------------------------------------------


def random_sizes(n, seed, lo=1, hi=9):
    return np.random.default_rng(seed).integers(lo, hi + 1, size=(n, 3))


def find_overlap(lo, hi, dims):
    """Paint each padded box into a boolean occupancy grid. Returns the first
    overlapping index pair (earlier, later) or None. Exact, and fast enough
    for 200k small boxes."""
    n_voxels = int(np.prod(dims, dtype=np.int64))
    assert n_voxels <= MAX_CHECK_VOXELS, (
        f"atlas {tuple(dims)} too large for the occupancy-grid overlap check"
    )
    occ = np.zeros(tuple(int(v) for v in dims), dtype=bool)
    for i, ((x0, y0, z0), (x1, y1, z1)) in enumerate(
        zip(lo.tolist(), hi.tolist(), strict=True)
    ):
        region = occ[x0:x1, y0:y1, z0:z1]
        if region.any():
            hits = np.flatnonzero(np.all((lo[:i] < hi[i]) & (lo[i] < hi[:i]), axis=1))
            return int(hits[0]), i
        region[...] = True
    return None


def check_valid(sizes, offsets, dims, padding=0):
    sizes = np.asarray(sizes, dtype=np.int64).reshape(-1, 3)
    n = len(sizes)

    assert isinstance(offsets, np.ndarray), (
        f"offsets must be a numpy array, got {type(offsets).__name__}"
    )
    assert offsets.shape == (n, 3), (
        f"offsets must have shape {(n, 3)}, got {offsets.shape}"
    )
    assert np.issubdtype(offsets.dtype, np.integer), (
        f"offsets must have an integer dtype, got {offsets.dtype}"
    )

    dims = np.asarray(dims)
    assert dims.shape == (3,), f"atlas dims must have shape (3,), got {dims.shape}"
    assert np.issubdtype(dims.dtype, np.integer), (
        f"atlas dims must be integers, got {dims.dtype}"
    )
    assert (dims > 0).all(), f"atlas dims must be positive, got {dims}"

    offsets = offsets.astype(np.int64)
    lo = offsets - padding
    hi = offsets + sizes + padding

    below = np.flatnonzero((lo < 0).any(axis=1))
    assert below.size == 0, (
        f"{below.size} boxes extend below 0, e.g. box {below[0]} "
        f"{sizes[below[0]]} at {offsets[below[0]]} (padding={padding})"
    )
    above = np.flatnonzero((hi > dims).any(axis=1))
    assert above.size == 0, (
        f"{above.size} boxes exceed atlas {dims}, e.g. box {above[0]} "
        f"{sizes[above[0]]} at {offsets[above[0]]} (padding={padding})"
    )

    pair = find_overlap(lo, hi, dims)
    assert pair is None, (
        f"boxes {pair[0]} {sizes[pair[0]]}@{offsets[pair[0]]} and "
        f"{pair[1]} {sizes[pair[1]]}@{offsets[pair[1]]} overlap"
    )


def fill_ratio(sizes, dims, padding=0):
    sizes = np.asarray(sizes, dtype=np.int64).reshape(-1, 3)
    used = np.prod(sizes + 2 * padding, axis=1).sum()
    return used / np.prod(np.asarray(dims, dtype=np.int64))


# ---- return type -------------------------------------------------------------


def test_returns_numpy_arrays():
    sizes = random_sizes(100, seed=0)
    offsets, dims = run_pack(sizes)
    assert isinstance(offsets, np.ndarray)
    assert offsets.shape == (100, 3)
    assert np.issubdtype(offsets.dtype, np.integer)
    assert np.asarray(dims).shape == (3,)


def test_accepts_list_of_tuples():
    sizes = [tuple(row) for row in random_sizes(100, seed=0).tolist()]
    offsets, dims = run_pack(sizes)
    check_valid(sizes, offsets, dims)


# ---- edge cases --------------------------------------------------------------


def test_empty_input():
    offsets, _ = run_pack(np.empty((0, 3), dtype=np.int64))
    assert isinstance(offsets, np.ndarray)
    assert offsets.shape == (0, 3)


def test_single_box():
    sizes = np.array([[3, 4, 5]])
    offsets, dims = run_pack(sizes)
    check_valid(sizes, offsets, dims)
    if TIGHT_DIMS:
        np.testing.assert_array_equal(offsets, [[0, 0, 0]])
        np.testing.assert_array_equal(dims, [3, 4, 5])


def test_single_box_with_padding():
    sizes = np.array([[3, 4, 5]])
    offsets, dims = run_pack(sizes, padding=1)
    check_valid(sizes, offsets, dims, padding=1)
    if TIGHT_DIMS:
        np.testing.assert_array_equal(offsets, [[1, 1, 1]])
        np.testing.assert_array_equal(dims, [5, 6, 7])


@pytest.mark.parametrize("bad", [(0, 1, 1), (1, -2, 1), (1, 1, 0)])
def test_rejects_degenerate_sizes(bad):
    # Delete this test if you'd rather silently skip empty boxes.
    with pytest.raises(ValueError):
        pack(np.array([(2, 2, 2), bad]))


# Unconstrained, these atlases have a longest axis of 108 and 164.
@pytest.mark.parametrize("padding, max_dim", [(0, 80), (1, 120)])
def test_respects_max_dim(padding, max_dim):
    sizes = random_sizes(3000, seed=9)
    offsets, dims = pack(sizes, padding=padding, max_dim=max_dim)
    check_valid(sizes, offsets, dims, padding)
    assert (np.asarray(dims) <= max_dim).all(), f"atlas {dims} exceeds max_dim"


def test_rejects_block_larger_than_max_dim():
    with pytest.raises(ValueError):
        pack(np.array([(2, 2, 2), (5, 5, 5)]), padding=1, max_dim=6)


def test_rejects_when_atlas_too_small():
    with pytest.raises(ValueError):
        pack(np.ones((1000, 3), dtype=np.int64) * 4, max_dim=16)


def test_does_not_mutate_input():
    sizes = random_sizes(500, seed=1)
    before = sizes.copy()
    run_pack(sizes)
    np.testing.assert_array_equal(sizes, before)


def test_offsets_do_not_alias_input():
    # Writing to the result must not corrupt the caller's sizes array.
    sizes = random_sizes(500, seed=1)
    before = sizes.copy()
    offsets, _ = run_pack(sizes)
    offsets[...] = -1
    np.testing.assert_array_equal(sizes, before)


def test_deterministic():
    sizes = random_sizes(2000, seed=2)
    off_a, dims_a = run_pack(sizes)
    off_b, dims_b = run_pack(sizes)
    np.testing.assert_array_equal(off_a, off_b)
    np.testing.assert_array_equal(dims_a, dims_b)


# ---- correctness on varied inputs --------------------------------------------


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("padding", [0, 1, 2])
def test_random_inputs_valid(seed, padding):
    sizes = random_sizes(3000, seed=seed)
    offsets, dims = run_pack(sizes, padding=padding)
    check_valid(sizes, offsets, dims, padding)


@pytest.mark.parametrize(
    "shape", [(1, 1, 1), (4, 4, 4), (9, 1, 1), (1, 9, 1), (1, 1, 9)]
)
def test_identical_boxes_pack_well(shape):
    sizes = np.tile(shape, (4000, 1))
    offsets, dims = run_pack(sizes)
    check_valid(sizes, offsets, dims)
    assert fill_ratio(sizes, dims) >= 0.9


def test_input_order_is_respected():
    # Wildly different shapes in alternating order: if the packer sorts
    # internally and returns offsets in sorted order, these will collide
    # or stick out of the atlas.
    base = np.array([(9, 1, 1), (1, 9, 1), (1, 1, 9), (9, 9, 9), (1, 1, 1)])
    sizes = np.tile(base, (400, 1))
    offsets, dims = run_pack(sizes)
    check_valid(sizes, offsets, dims)
    rev = sizes[::-1].copy()
    offsets_r, dims_r = run_pack(rev)
    check_valid(rev, offsets_r, dims_r)


def test_non_contiguous_input():
    # A strided view should behave the same as a contiguous copy.
    big = random_sizes(6000, seed=8)
    view = big[::2]
    off_v, dims_v = run_pack(view)
    off_c, dims_c = run_pack(np.ascontiguousarray(view))
    check_valid(view, off_v, dims_v)
    np.testing.assert_array_equal(off_v, off_c)
    np.testing.assert_array_equal(dims_v, dims_c)


def test_one_large_among_many_small():
    sizes = np.vstack([np.ones((5000, 3), dtype=np.int64), [[9, 9, 9]]])
    np.random.default_rng(3).shuffle(sizes)
    offsets, dims = run_pack(sizes)
    check_valid(sizes, offsets, dims)


# ---- quality -----------------------------------------------------------------


@pytest.mark.parametrize("padding", [0, 1])
def test_fill_ratio_realistic(padding):
    sizes = random_sizes(20000, seed=4)
    offsets, dims = run_pack(sizes, padding=padding)
    check_valid(sizes, offsets, dims, padding)
    ratio = fill_ratio(sizes, dims, padding)
    assert ratio >= MIN_FILL, f"fill {ratio:.3f} < {MIN_FILL} (atlas {dims})"


def test_skewed_size_distribution():
    # Mostly tiny boxes with a long tail, closer to real texture sets.
    rng = np.random.default_rng(5)
    sizes = np.minimum(9, 1 + rng.exponential(2.0, size=(20000, 3)).astype(np.int64))
    offsets, dims = run_pack(sizes)
    check_valid(sizes, offsets, dims)
    assert fill_ratio(sizes, dims) >= MIN_FILL


def test_atlas_not_absurdly_elongated():
    # A 1-voxel-wide strip is technically valid but useless as a texture.
    sizes = random_sizes(20000, seed=6)
    _, dims = run_pack(sizes)
    dims = np.asarray(dims)
    assert dims.max() / dims.min() <= 8, f"atlas aspect too extreme: {dims}"


# ---- scale -------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.parametrize("padding", [0, 1])
def test_200k_boxes(padding):
    sizes = random_sizes(200_000, seed=7)
    t0 = time.perf_counter()
    offsets, dims = run_pack(sizes, padding=padding)
    elapsed = time.perf_counter() - t0
    assert elapsed < TIME_LIMIT_S, f"packing took {elapsed:.1f}s"
    check_valid(sizes, offsets, dims, padding)
    assert fill_ratio(sizes, dims, padding) >= MIN_FILL
