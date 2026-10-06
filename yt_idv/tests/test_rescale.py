import numpy as np
import pytest
import yt
from numpy.testing import assert_allclose
from yt.testing import fake_amr_ds

from yt_idv.scene_graph import SceneGraph

LEFT, RIGHT = [0.25, 0.3, 0.35], [0.65, 0.7, 0.75]


@pytest.fixture()
def region_rc(make_rc):
    rc = make_rc(width=64, height=64)
    ds = fake_amr_ds()
    rc.add_scene(ds.region([0.5, 0.5, 0.5], LEFT, RIGHT), "Density", no_ghost=True)
    component = rc.scene.components[0]
    component.render_method = "max_intensity"
    component.store_first_pass_fb = True
    rc.scene.camera.update(position=[1.5, 1.2, 2.0], focus=[0.5, 0.5, 0.5])
    rc.ds = ds
    return rc


def _edges(data):
    va = data.vertex_array
    return [np.array(va[name].data) for name in ("in_left_edge", "in_right_edge")]


def _first_pass(rc):
    rc.run()
    return np.array(rc.scene.components[0].first_pass_fb_rgba)


def _corners_in_ndc(scene):
    # every block corner, projected to normalized device coordinates
    left_edge, right_edge = _edges(scene.components[0].data)
    corners = np.concatenate(
        [
            np.where(np.array(bits, dtype=bool), right_edge, left_edge)
            for bits in np.ndindex(2, 2, 2)
        ]
    ).astype("f8")
    camera = scene.camera
    clip = (
        np.hstack([corners, np.ones((len(corners), 1))])
        @ (camera.projection_matrix.astype("f8") @ camera.view_matrix.astype("f8")).T
    )
    return clip[:, :3] / clip[:, 3:]


def test_rescale_keeps_the_view(region_rc):
    scene = region_rc.scene
    ndc = _corners_in_ndc(scene)
    before = _first_pass(region_rc)
    scene.rescale([0.45, 0.5, 0.55], 0.2)
    # the data and the camera move together, so everything projects to the
    # same place on screen
    assert_allclose(_corners_in_ndc(scene)[:, :2], ndc[:, :2], atol=1e-5)

    after = _first_pass(region_rc)
    assert np.any(before != 0)
    lit = before[..., 3] > 0
    assert np.array_equal(lit, after[..., 3] > 0)
    # A few pixels' maxima can change: decisions near block faces and cell
    # boundaries depend on float32 rounding, which moves with the coordinates.
    values, rescaled = before[..., 0][lit], after[..., 0][lit]
    differs = np.abs(rescaled - values) > 1e-3 * values + 1e-6
    assert differs.mean() < 0.05
    assert_allclose(rescaled[~differs], values[~differs], rtol=1e-3, atol=1e-6)


def test_rescales_compose(region_rc, make_rc):
    scene = region_rc.scene
    scene.rescale([0.4, 0.5, 0.6], 0.5)
    scene.rescale([0.1, -0.2, 0.3], 0.25)
    data = scene.components[0].data
    assert data.applied_scale_ratio == pytest.approx(0.125)
    assert_allclose(data.applied_scale_offset, [0.45, 0.4, 0.75])

    once = make_rc(width=64, height=64)
    ds = fake_amr_ds()
    once.add_scene(ds.region([0.5, 0.5, 0.5], LEFT, RIGHT), "Density", no_ghost=True)
    once.scene.camera.update(position=[1.5, 1.2, 2.0], focus=[0.5, 0.5, 0.5])
    once.scene.rescale([0.45, 0.4, 0.75], 0.125)
    for a, b in zip(_edges(data), _edges(once.scene.components[0].data), strict=True):
        assert_allclose(a, b, rtol=1e-6)
    assert_allclose(scene.camera.position, once.scene.camera.position, rtol=1e-6)
    assert scene.camera.near_plane == pytest.approx(once.scene.camera.near_plane)


def test_rescale_recomputes_edges_from_float64(region_rc):
    data = region_rc.scene.components[0].data
    left_edge = data._unscaled_edges[0]
    center = left_edge[0] + 1e-7
    for _ in range(3):
        region_rc.scene.rescale(
            (center - np.array(data.applied_scale_offset)) / data.applied_scale_ratio,
            0.01,
        )
    ratio = data.applied_scale_ratio
    offset = np.array(data.applied_scale_offset)
    assert ratio == pytest.approx(1e-6)
    # kept in float64 (cast to float32 only for the GPU)
    expected = (left_edge - offset) / ratio
    assert np.array_equal(data.vertex_array["in_left_edge"].data, expected)


def test_scale_survives_save_and_load(region_rc, tmp_path):
    data = region_rc.scene.components[0].data
    data.scale = True
    assert data.applied_scale_ratio == pytest.approx(0.4)
    assert_allclose(data.applied_scale_offset, LEFT)
    edges = _edges(data)
    filename = tmp_path / "scene.zip"
    region_rc.scene.save(filename)

    region_rc.scene = SceneGraph.load(filename)
    loaded = region_rc.scene.components[0].data
    assert loaded.data_source is None
    assert loaded.scale
    # restored, not scaled a second time
    assert loaded.applied_scale_ratio == pytest.approx(0.4)
    assert_allclose(loaded.applied_scale_offset, LEFT)
    for a, b in zip(edges, _edges(loaded), strict=True):
        assert np.array_equal(a, b)
    assert_allclose(loaded._unscaled_edges, data._unscaled_edges)

    # and it can be rescaled further without the data source
    region_rc.scene.rescale([0.5, 0.5, 0.5], 0.5)
    assert loaded.applied_scale_ratio == pytest.approx(0.2)


def test_scale_twice_on_one_data_source(make_rc):
    # scaling no longer edits the data source's block edges in place
    ds = fake_amr_ds()
    region = ds.region([0.5, 0.5, 0.5], LEFT, RIGHT)
    rc = make_rc(width=64, height=64)
    first = rc.add_scene(region, "Density", no_ghost=True).components[0].data
    first.scale = True
    second = rc.add_scene(region, "Density", no_ghost=True).components[0].data
    second.scale = True
    for a, b in zip(_edges(first), _edges(second), strict=True):
        assert np.array_equal(a, b)


@pytest.mark.parametrize("saved", [False, True])
def test_viewpoint_order_in_tree_coordinates(make_rc, tmp_path, saved):
    # code_length is half the unitary length here, so the kd-tree (code_length)
    # and the camera (unitary model coordinates) disagree unless converted
    n = 32
    ds = yt.load_uniform_grid(
        {"density": (np.random.default_rng(0).random((n, n, n)), "g/cm**3")},
        (n, n, n),
        nprocs=64,
        bbox=np.array([[0.0, 2.0]] * 3),
    )
    rc = make_rc(width=64, height=64)
    scene = rc.add_scene(ds, "density", no_ghost=True)
    data = scene.components[0].data
    data.scale = True
    scene.rescale([0.4, 0.5, 0.6], 0.5)
    scene.camera.update(position=[0.3, 0.8, 0.45], focus=[0.5, 0.5, 0.5])
    unitary = scene.camera.position * data.applied_scale_ratio + np.array(
        data.applied_scale_offset
    )
    expected = [
        data.blocks[id(block)][0]
        for block in data.data_source.tiles.traverse(viewpoint=unitary * 2.0)
    ]
    if saved:
        filename = tmp_path / "scene.zip"
        scene.save(filename)
        rc.scene = scene = SceneGraph.load(filename)
        data = scene.components[0].data
    order = data.viewpoint_order(scene.camera).tolist()
    assert order == expected


def test_internal_length_unit_follows_scale(region_rc):
    data = region_rc.scene.components[0].data
    unscaled = data.internal_length_unit
    data.scale = True
    assert float(data.internal_length_unit / unscaled) == pytest.approx(0.4)


def test_standalone_export_rescales_exactly(region_rc, tmp_path):
    from yt_idv.standalone_export import export_block_scene

    live = region_rc.scene.components[0].data
    filename = tmp_path / "exported.zip"
    export_block_scene(live.data_source, "Density", filename, no_ghost=True)
    loaded = SceneGraph.load(filename)
    data = loaded.components[0].data
    assert np.array_equal(data._unscaled_edges, live._unscaled_edges)
    assert data._unitary_per_code_length == live._unitary_per_code_length

    center = live._unscaled_edges[0, 0] + 1e-7
    loaded.rescale(center, 1e-6)
    region_rc.scene.rescale(center, 1e-6)
    assert np.array_equal(
        data.vertex_array["in_left_edge"].data,
        live.vertex_array["in_left_edge"].data,
    )


def test_scale_loaded_scene_with_saved_bbox(region_rc, tmp_path):
    filename = tmp_path / "scene.zip"
    region_rc.scene.save(filename)
    data = SceneGraph.load(filename).components[0].data
    edges = np.array(data._unscaled_edges[0])
    data.scale = True
    # the saved bounding box, not the blocks' extent, maps to [0, 1]
    assert data.applied_scale_ratio == pytest.approx(0.4)
    assert_allclose(data.applied_scale_offset, LEFT)
    assert_allclose(data.vertex_array["in_left_edge"].data, (edges - LEFT) / 0.4)
