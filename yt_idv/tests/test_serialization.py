import json
import zipfile

import numpy as np
import pytest
import yt
import yt.testing
from numpy.testing import assert_allclose

from yt_idv.scene_data.block_collection import _flatten_kd_tree, _kd_viewpoint_order
from yt_idv.scene_graph import SceneGraph


def test_kd_viewpoint_order_matches_yt():
    ds = yt.testing.fake_amr_ds()
    tiles = ds.all_data().tiles
    kd_tree = _flatten_kd_tree(tiles.tree.trunk)
    depth_order = [id(node) for node in tiles.tree.trunk.kd_traverse()]
    rng = np.random.default_rng(0)
    for viewpoint in rng.uniform(-1.0, 2.0, size=(10, 3)):
        expected = [
            depth_order.index(id(node))
            for node in tiles.tree.trunk.kd_traverse(viewpoint=viewpoint)
        ]
        assert _kd_viewpoint_order(kd_tree, viewpoint) == expected


def _render(rc):
    # the first frame can differ, as some components leave GL state behind
    rc.run()
    return np.array(rc.run())


@pytest.mark.image_test
def test_save_load_block_scene(make_rc, tmp_path):
    ds = yt.testing.fake_amr_ds()
    rc = make_rc()
    scene = rc.add_scene(ds, "Density", no_ghost=True)
    component = scene.components[0]
    component.render_method = "transfer_function"
    component.colormap.colormap_name = "viridis"
    component.cmap_log = False
    tf = component.transfer_function.data.copy()
    tf[:128, 0, 3] = 0
    component.transfer_function.data = tf
    scene.camera.set_position([1.5, 2.0, 2.5])
    scene.add_text("hello", origin=(0.1, 0.1))
    scene.add_box([0.25, 0.25, 0.25], [0.75, 0.75, 0.75])
    original = _render(rc)

    fn = tmp_path / "scene.zip"
    scene.save(fn)
    with zipfile.ZipFile(fn) as zf:
        state = json.loads(zf.read("scene.json"))
    assert state["components"][0]["traits"]["render_method"] == "transfer_function"

    loaded = SceneGraph.load(fn)
    loaded_component = loaded.components[0]
    assert loaded_component.data.data_source is None
    assert loaded_component.render_method == "transfer_function"
    assert loaded_component.colormap.colormap_name == "viridis"
    assert loaded_component.cmap_log is False
    np.testing.assert_equal(loaded_component.transfer_function.data, tf)
    np.testing.assert_allclose(loaded.camera.position, scene.camera.position)
    assert loaded.annotations[0].text == "hello"
    assert len(loaded.data_objects) == len(scene.data_objects)

    bc, loaded_bc = component.data, loaded_component.data
    assert set(loaded_bc.block_data) == set(bc.block_data)
    for i, arr in bc.block_data.items():
        np.testing.assert_equal(loaded_bc.block_data[i], arr)
        np.testing.assert_equal(loaded_bc.block_bitmaps[i], bc.block_bitmaps[i])
    np.testing.assert_equal(loaded_bc.data_atlas.offsets, bc.data_atlas.offsets)

    rc.scene = loaded
    np.testing.assert_allclose(_render(rc), original)

    # a loaded scene can be saved again
    fn2 = tmp_path / "scene2.zip"
    loaded.save(fn2, compress=True)
    rc.scene = SceneGraph.load(fn2)
    np.testing.assert_allclose(_render(rc), original)


@pytest.mark.image_test
def test_save_load_spherical_scene(make_rc, tmp_path):
    shp = (16, 16, 16)
    bbox = np.array([[0.1, 1.0], [0.0, np.pi], [0.0, 2 * np.pi]])
    data = {"density": np.random.default_rng(0).random(shp)}
    ds = yt.load_uniform_grid(data, shp, bbox=bbox, geometry="spherical")
    rc = make_rc()
    scene = rc.add_scene(ds, "density", no_ghost=True)
    scene.components[0].render_method = "max_intensity"
    original = _render(rc)

    fn = tmp_path / "spherical.zip"
    scene.save(fn)
    loaded = SceneGraph.load(fn)
    assert loaded.components[0].data._yt_geom_str == "spherical"
    rc.scene = loaded
    np.testing.assert_allclose(_render(rc), original)


def test_bbox_survives_save_and_load(make_rc, tmp_path):
    ds = yt.testing.fake_amr_ds()
    region = ds.region([0.5, 0.5, 0.5], [0.3, 0.35, 0.4], [0.6, 0.7, 0.8])
    rc = make_rc()
    scene = rc.add_scene(region, "Density", no_ghost=True)
    left_edge, right_edge = scene.components[0].data.bbox
    assert_allclose(left_edge, [0.3, 0.35, 0.4])
    assert_allclose(right_edge, [0.6, 0.7, 0.8])

    filename = tmp_path / "scene.zip"
    scene.save(filename)
    loaded = SceneGraph.load(filename)
    data = loaded.components[0].data
    assert data.data_source is None
    assert_allclose(data.bbox[0], left_edge)
    assert_allclose(data.bbox[1], right_edge)


def test_standalone_export_saves_bbox(make_rc, tmp_path):
    from yt_idv.standalone_export import export_block_scene

    ds = yt.testing.fake_amr_ds()
    region = ds.region([0.5, 0.5, 0.5], [0.3, 0.35, 0.4], [0.6, 0.7, 0.8])
    make_rc()
    filename = tmp_path / "exported.zip"
    export_block_scene(region, "Density", filename, no_ghost=True)
    data = SceneGraph.load(filename).components[0].data
    assert_allclose(data.bbox[0], [0.3, 0.35, 0.4])
    assert_allclose(data.bbox[1], [0.6, 0.7, 0.8])
