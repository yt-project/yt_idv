import bisect
import itertools
import os

import numpy as np
import pytest
import yt
from numpy.testing import assert_allclose

from yt_idv.cameras.trackball_camera import TrackballCamera
from yt_idv.opengl_support import Texture2D
from yt_idv.scene_components.blocks import BlockRendering
from yt_idv.scene_components.octree_blocks import OctreeBlockRendering
from yt_idv.scene_data.block_collection import _kd_viewpoint_order
from yt_idv.scene_data.octree_block_collection import (
    OctreeBlockCollection,
    _blocks_from_leaf_cells,
    _morton_keys,
    _octree_viewpoint_order,
)
from yt_idv.scene_graph import SceneGraph


def _random_octree(seed, size=16):
    """The integer lower corners and sizes of the leaves of a random octree."""
    rng = np.random.default_rng(seed)
    leaves = []

    def refine(lo, n, depth):
        if n > 1 and (depth < 1 or rng.random() < 0.45):
            for d in itertools.product((0, 1), repeat=3):
                refine(lo + n // 2 * np.array(d), n // 2, depth + 1)
        else:
            leaves.append((lo, n))

    refine(np.zeros(3, "int64"), size, 0)
    return np.array([lo for lo, _ in leaves]), np.array([n for _, n in leaves])


def _reference_kd_tree(lo):
    """
    A kd-tree, flattened as _kd_viewpoint_order takes it, that splits each oct
    at its center, over blocks with lower corners lo in Morton order.
    """
    keys = _morton_keys(lo).tolist()
    left, right, split_dim, split_pos, block = [], [], [], [], []

    def build(start, end):
        node = len(left)
        for column, value in zip(
            (left, right, split_dim, split_pos, block),
            (-1, -1, -1, np.nan, -1),
            strict=True,
        ):
            column.append(value)
        if end - start == 1:
            block[node] = start
            return node
        bit = (keys[start] ^ keys[end - 1]).bit_length() - 1
        mid = bisect.bisect_left(keys, keys[end - 1] >> bit << bit, start, end)
        axis, level = 2 - bit % 3, bit // 3
        split_dim[node] = axis
        split_pos[node] = lo[mid][axis] >> level << level
        left[node] = build(start, mid)
        right[node] = build(mid, end)
        return node

    build(0, len(lo))
    return {
        "left": np.array(left),
        "right": np.array(right),
        "split_dim": np.array(split_dim),
        "split_pos": np.array(split_pos),
        "block": np.array(block),
    }


def _leaf_cells(lo, n, values, size=16):
    # cell centers and widths in a unit domain, for _blocks_from_leaf_cells
    width = np.repeat(n[:, None] / size, 3, axis=1).astype("float64")
    return lo / size + width / 2, width, np.asarray(values, dtype="float64")


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_viewpoint_order_matches_kd_walk(seed):
    lo, _ = _random_octree(seed)
    lo = lo[np.argsort(_morton_keys(lo), kind="stable")]
    kd_tree = _reference_kd_tree(lo)
    rng = np.random.default_rng(seed)
    # inside and outside the domain, and exactly on split planes
    viewpoints = np.concatenate(
        [
            rng.uniform(-8, 24, size=(200, 3)),
            rng.integers(-2, 18, size=(50, 3)).astype("float64"),
        ]
    )
    for viewpoint in viewpoints:
        np.testing.assert_array_equal(
            _octree_viewpoint_order(lo, np.ceil(viewpoint)),
            _kd_viewpoint_order(kd_tree, viewpoint),
        )


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_blocks_tile_the_leaf_cells(seed):
    lo, n = _random_octree(seed)
    octs, cells = _blocks_from_leaf_cells(*_leaf_cells(lo, n, np.ones(len(n))), 0.0)

    # every leaf cell is covered by exactly one block
    coverage = np.zeros((16, 16, 16), dtype="int64")
    for blocks, n_cells in ((octs, 2), (cells, 1)):
        for left_edge, dx in zip(blocks["left_edge"], blocks["dx"], strict=True):
            a = np.rint(left_edge * 16).astype("int64")
            b = a + np.rint(dx * 16 * n_cells).astype("int64")
            coverage[a[0] : b[0], a[1] : b[1], a[2] : b[2]] += 1
    assert (coverage == 1).all()

    # and the octs are exactly the parents with eight leaf children
    parents = {}
    for corner, size in zip(lo.tolist(), n.tolist(), strict=True):
        key = (size, *(c // (2 * size) for c in corner))
        parents[key] = parents.get(key, 0) + 1
    assert len(octs["dx"]) == sum(count == 8 for count in parents.values())
    assert octs["data"].shape[1:] == (3, 3, 3)
    assert cells["data"].shape[1:] == (2, 2, 2)


def test_block_data_is_indexed_x_y_z():
    # 4x4x4 cells holding their own x position: within each oct, the vertex
    # values have to change along the first axis only
    lo = np.array(list(itertools.product(range(0, 16, 4), repeat=3)))
    n = np.full(len(lo), 4)
    center, width, _ = _leaf_cells(lo, n, np.zeros(len(n)))
    octs, cells = _blocks_from_leaf_cells(center, width, center[:, 0], 0.0)
    assert len(octs["dx"]) == 8
    assert len(cells["dx"]) == 0
    data = octs["data"]
    assert (data[:, 2, 0, 0] > data[:, 0, 0, 0]).all()
    assert_allclose(data[:, 0, 2, 0], data[:, 0, 0, 0])
    assert_allclose(data[:, 0, 0, 2], data[:, 0, 0, 0])


def _octree_scene(make_rc, values=None, seed=0, size=128):
    # a random octree in the unit cube, with values (by default, random ones),
    # rendered looking down the z axis with an orthographic camera
    rc = make_rc(width=size, height=size)
    lo, n = _random_octree(seed)
    if values is None:
        values = np.random.default_rng(seed).uniform(1.0, 10.0, len(n))
    octs, cells = _blocks_from_leaf_cells(
        *_leaf_cells(lo, n, np.broadcast_to(values, len(n))), 0.0
    )
    collection = OctreeBlockCollection()
    collection._set_blocks(octs, cells, origin=np.zeros(3), unitary_per_code_length=1)
    camera = TrackballCamera(
        position=[0.5, 0.5, 3.0],
        focus=[0.5, 0.5, 0.5],
        up=[0.0, 1.0, 0.0],
        fov=30.0,
        near_plane=0.1,
        far_plane=10.0,
        projection_type="orthographic",
    )
    scene = SceneGraph(camera=camera)
    rc.scene = scene
    scene.data_objects.append(collection)
    component = OctreeBlockRendering(data=collection, store_first_pass_fb=True)
    scene.components.append(component)
    return rc, scene, component


@pytest.mark.image_test
def test_uniform_octree_values(make_rc):
    rc, scene, component = _octree_scene(make_rc, values=3.0)
    assert component.name == "block_rendering"
    assert not component.data._textures_are_normalized

    component.render_method = "max_intensity"
    scene.render()
    fb = component.first_pass_fb_rgba
    drawn = fb[..., 3] > 0
    # the domain fills the middle of the view
    assert drawn[48:80, 48:80].all()
    assert_allclose(fb[drawn, 0], 3.0, rtol=1e-6)

    component.render_method = "projection"
    scene.render()
    fb = component.first_pass_fb_rgba
    path_length = fb[48:80, 48:80, 1]
    # each ray crosses the unit depth once, overshooting by up to one step
    assert_allclose(path_length, 1.0, atol=1.5 / 16)
    assert_allclose(fb[48:80, 48:80, 0], 3.0 * path_length, rtol=1e-5)


@pytest.mark.image_test
def test_octree_transfer_function_renders(make_rc):
    rc, scene, component = _octree_scene(make_rc)
    component.render_method = "transfer_function"
    image = rc.run()
    assert (image[..., 3] > 0).sum() > 0


@pytest.mark.image_test
def test_octree_depth_buffer_and_external_clip(make_rc):
    rc, scene, component = _octree_scene(make_rc)
    component.render_method = "max_intensity"
    # compared against the background itself, since not every backend's
    # framebuffer has an alpha channel to show where nothing was drawn
    component.visible = False
    background = np.array(rc.run())
    component.visible = True
    image = np.array(rc.run())
    drawn = np.any(image != background, axis=-1)
    assert drawn.any()
    # the volume writes its depth, which Blender composites against
    depth = np.asarray(scene.depth)
    assert (depth[drawn] < 1.0).all()

    # an external depth at the near plane clips every ray, and one at the far
    # plane none of them
    for clip_depth, expected in ((0.0, background), (1.0, image)):
        component.external_depth_texture = Texture2D(
            data=np.full(image.shape[1::-1], clip_depth, dtype="f4")
        )
        component.use_external_depth_clip = True
        assert_allclose(np.array(rc.run()), expected)


@pytest.mark.image_test
def test_save_load_octree_scene(make_rc, tmp_path):
    rc, scene, component = _octree_scene(make_rc)
    component.render_method = "transfer_function"
    scene.camera.set_position([1.6, 1.3, 2.2])
    original = np.array(rc.run())

    fn = tmp_path / "octree.zip"
    scene.save(fn)
    loaded = SceneGraph.load(fn)
    data = loaded.components[0].data
    assert isinstance(data, OctreeBlockCollection)
    np.testing.assert_array_equal(data._block_lo, component.data._block_lo)
    rc.scene = loaded
    assert_allclose(np.array(rc.run()), original)


@pytest.mark.image_test
def test_rescale_keeps_the_octree_view(make_rc):
    rc, scene, component = _octree_scene(make_rc)
    # inside the domain along x and y, where the order depends on exactly
    # where the camera is
    scene.camera.set_position([0.7, 0.4, 2.2])
    order = component.data.viewpoint_order(scene.camera)
    component.render_method = "max_intensity"
    scene.render()
    before = component.first_pass_fb_rgba.copy()

    scene.rescale([0.45, 0.5, 0.55], 0.2)
    # the camera moves with the blocks, so it sees them in the same order
    np.testing.assert_array_equal(component.data.viewpoint_order(scene.camera), order)
    scene.render()
    after = component.first_pass_fb_rgba
    lit = before[..., 3] > 0
    assert lit.any()
    assert np.array_equal(lit, after[..., 3] > 0)
    # as for grid data, a few pixels can change with float32 rounding near
    # block faces, which moves with the coordinates
    values, rescaled = before[..., 0][lit], after[..., 0][lit]
    differs = np.abs(rescaled - values) > 1e-3 * values + 1e-6
    assert differs.mean() < 0.05
    assert_allclose(rescaled[~differs], values[~differs], rtol=1e-3, atol=1e-6)


@pytest.fixture(scope="module")
def ramses_region():
    pytest.importorskip("scipy")  # the RAMSES frontend needs it for cosmology
    path = os.path.join(
        yt.config.ytcfg.get("yt", "test_data_dir"), "output_00080", "info_00080.txt"
    )
    if not os.path.exists(path):
        pytest.skip(f"{path} is not available")
    ds = yt.load(path)
    # the densest gas, which is refined over eight levels, with the region's
    # faces on oct boundaries
    center = ds.arr([0.7578125, 0.7734375, 0.8046875], "unitary")
    half = ds.quan(1 / 128, "unitary")
    # yield (not return) so this frame's ds survives: data objects only hold
    # a weak reference to their dataset
    yield ds.box(center - half, center + half)


@pytest.mark.image_test
@pytest.mark.parametrize("no_ghost", [True, False])
def test_ramses_matches_yt(make_rc, ramses_region, no_ghost):
    region, field = ramses_region, ("gas", "density")
    ds = region.ds
    rc = make_rc(width=256, height=256)
    scene = rc.add_scene(region, field, no_ghost=no_ghost)
    component = scene.components[0]
    # what Blender (cycles-yt) looks for in a scene
    assert component.name == "block_rendering"
    assert isinstance(component, BlockRendering)
    assert isinstance(component.data, OctreeBlockCollection)

    # the blocks cover exactly the region's leaf cells
    edges = component.data._unscaled_edges
    block_volume = np.prod(edges[1] - edges[0], axis=1).sum()
    cell_volume = region["index", "cell_volume"].to("unitary**3").d.sum()
    assert_allclose(block_volume, cell_volume, rtol=1e-6)

    component.store_first_pass_fb = True
    center = (region.left_edge + region.right_edge) / 2
    c = center.to("unitary").d
    scene.camera.update(
        position=c + [0.0, 0.0, 0.2],
        focus=c,
        up=[0.0, 1.0, 0.0],
        fov=7.2,
        near_plane=0.01,
        far_plane=1.0,
        projection_type="orthographic",
    )
    # pixel by pixel, both match yt's projections, which sample the same
    # rays; refined cells drawn along with their children would make the
    # projection several times too large
    for render_method, method in (
        ("projection", "integrate"),
        ("max_intensity", "max"),
    ):
        component.render_method = render_method
        scene.render()
        image = component.rendered_image_plane()
        width = ds.quan(float(image.width.to("code_length").d), "code_length")
        reference = ds.proj(field, "z", method=method, data_source=region)
        reference = reference.to_frb(width, image.data.shape[::-1], center=center)
        reference = np.asarray(reference[field].to(str(image.data.units)))
        values = np.asarray(image.data)
        compared = np.isfinite(values) & (values > 0) & (reference > 0)
        assert compared.mean() > 0.3
        ratio = values[compared] / reference[compared]
        assert 0.95 < np.median(ratio) < 1.05
        assert 0.75 < np.quantile(ratio, 0.1)
        assert np.quantile(ratio, 0.9) < 1.25


@pytest.mark.image_test
def test_ramses_ghost_zone_data_is_indexed_x_y_z(empty_rc, ramses_region):
    # The across-oct gradient along each axis has to agree between vertex
    # data from ghost zones and from the octs' own cells, whose orientation
    # comes from the cell positions. Swapping two of yt's axes makes those
    # two gradients unrelated.
    collections = {}
    for no_ghost in (True, False):
        collections[no_ghost] = OctreeBlockCollection(data_source=ramses_region)
        collections[no_ghost].add_data(("gas", "density"), no_ghost=no_ghost)
    own, ghost = collections[True], collections[False]
    np.testing.assert_array_equal(own._block_lo, ghost._block_lo)
    octs = [i for i, d in own.block_data.items() if d.shape == (3, 3, 3)]
    assert len(octs) > 1000
    for axis in range(3):
        low, high = [1, 1, 1], [1, 1, 1]
        low[axis], high[axis] = 0, 2
        gradients = [
            np.log(
                [
                    c.block_data[i][tuple(low)] / c.block_data[i][tuple(high)]
                    for i in octs
                ]
            )
            for c in (own, ghost)
        ]
        assert np.corrcoef(*gradients)[0, 1] > 0.6


def _stream_octree(seed=0):
    # an in-memory octree refined to between three and six levels, holding a
    # smooth function of position
    rng = np.random.default_rng(seed)
    mask = []

    def node(depth):
        if depth < 3 or (depth < 6 and rng.random() < 0.2):
            mask.append(8)
            for _ in range(8):
                node(depth + 1)
        else:
            mask.append(0)

    node(0)
    mask = np.array(mask, dtype="uint8")
    n_leaves = int((mask == 0).sum())

    def load(values):
        # the data has to be shaped (n_leaves, 1)
        return yt.load_octree(
            octree_mask=mask,
            data={("gas", "density"): values.reshape(-1, 1)},
            bbox=np.array([[0.0, 1.0]] * 3),
            num_zones=1,
            partial_coverage=0,
        )

    # find where yt places each leaf, to set its value from its position
    probe = load(np.arange(n_leaves, dtype="float64")).all_data()
    position = np.empty((n_leaves, 3))
    position[probe["gas", "density"].d.astype(int)] = np.stack(
        [probe["index", ax].d for ax in "xyz"], axis=1
    )
    x, y, z = position.T
    return load(np.exp(0.3 * np.sin(2 * np.pi * x) * np.cos(2 * np.pi * y) + 0.3 * z))


@pytest.mark.image_test
@pytest.mark.parametrize(
    "render_method, method, median_tol, spread",
    [
        ("projection", "integrate", 0.01, (0.95, 1.05)),
        ("max_intensity", "max", 0.03, (0.95, 1.3)),
    ],
)
def test_stream_octree_matches_yt(make_rc, render_method, method, median_tol, spread):
    ds = _stream_octree()
    field = ("gas", "density")
    rc = make_rc(width=128, height=128)
    # the camera is explicit, as the stream octree index has no max_level for
    # TrackballCamera.from_dataset to use
    scene = SceneGraph(
        camera=TrackballCamera(
            position=[0.5, 0.5, 3.0],
            focus=[0.5, 0.5, 0.5],
            up=[0.0, 1.0, 0.0],
            fov=30.0,
            near_plane=0.1,
            far_plane=10.0,
            projection_type="orthographic",
        )
    )
    rc.scene = scene
    # ghost zones aren't available for stream octrees
    component = scene.add_volume(ds.all_data(), field, no_ghost=True)
    assert isinstance(component.data, OctreeBlockCollection)
    component.store_first_pass_fb = True
    component.render_method = render_method
    scene.render()

    image = component.rendered_image_plane()
    width = ds.quan(float(image.width.to("code_length").d), "code_length")
    center = ds.arr([0.5, 0.5, 0.5], "code_length")
    reference = ds.proj(field, "z", method=method).to_frb(
        width, image.data.shape[::-1], center=center
    )
    reference = np.asarray(reference[field].to(str(image.data.units)))
    values = np.asarray(image.data)
    compared = np.isfinite(values) & (values > 0) & (reference > 0)
    assert compared.mean() > 0.5
    ratio = values[compared] / reference[compared]
    assert abs(np.median(ratio) - 1) < median_tol
    assert spread[0] < np.quantile(ratio, 0.1)
    assert np.quantile(ratio, 0.9) < spread[1]
