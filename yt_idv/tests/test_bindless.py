import numpy as np
import pytest
from yt.testing import fake_amr_ds

import yt_idv.scene_data.block_collection as block_collection_module
from yt_idv.opengl_support import bindless_textures_supported

ALL_METHODS = (
    "max_intensity",
    "projection",
    "transfer_function",
    "isocontours",
    "slice",
    "constant",
)

VIEWPOINTS = (
    [0.1, 0.2, 0.3],
    [0.9, 0.5, 0.1],
    [3.0, -1.0, 0.7],
    [0.5, 2.0, 3.0],
)


@pytest.fixture()
def amr_rc(make_rc):
    rc = make_rc(width=64, height=64)
    ds = fake_amr_ds()
    rc.add_scene(ds, "radius", no_ghost=False)
    return rc


@pytest.fixture()
def require_bindless(amr_rc):
    if not bindless_textures_supported():
        pytest.skip("GL_ARB_bindless_texture is not supported by this context")


def _traverse_order(block_collection, camera):
    tiles = block_collection.data_source.tiles
    return [
        block_collection.blocks[id(block)][0]
        for block in tiles.traverse(viewpoint=camera.position)
    ]


def test_viewpoint_order_matches_traverse(amr_rc):
    camera = amr_rc.scene.camera
    block_collection = amr_rc.scene.components[0].data
    for viewpoint in VIEWPOINTS:
        camera.update(position=viewpoint, focus=[0.5, 0.5, 0.5])
        order = block_collection.viewpoint_order(camera)
        assert order.dtype == np.uint32
        np.testing.assert_array_equal(order, _traverse_order(block_collection, camera))


def test_viewpoint_order_without_yt_walk(amr_rc, monkeypatch):
    # yt versions without viewpoint_node_ids use AMRKDTree.traverse
    monkeypatch.setattr(block_collection_module, "viewpoint_node_ids", None)
    camera = amr_rc.scene.camera
    block_collection = amr_rc.scene.components[0].data
    camera.update(position=VIEWPOINTS[0], focus=[0.5, 0.5, 0.5])
    np.testing.assert_array_equal(
        block_collection.viewpoint_order(camera),
        _traverse_order(block_collection, camera),
    )


def test_bindless_preprocessor_definition(amr_rc):
    component = amr_rc.scene.components[0]
    for enabled in (True, False):
        component.use_bindless_textures = enabled
        for shader_type in ("vertex", "geometry", "fragment"):
            defs = dict(component._program1_pp_defs[shader_type])
            assert ("BINDLESS_TEXTURES" in defs) is enabled


def test_bound_draw_without_bindless(amr_rc):
    # the per-block path that's used where the extension is unavailable
    component = amr_rc.scene.components[0]
    component.use_bindless_textures = False
    component.store_first_pass_fb = True
    for method in ALL_METHODS:
        component.render_method = method
        amr_rc.run()
        assert component.first_pass_fb_rgba is not None


def test_bindless_matches_bound(amr_rc, require_bindless):
    component = amr_rc.scene.components[0]
    component.store_first_pass_fb = True
    amr_rc.scene.camera.update(position=[1.6, 1.3, 2.0], focus=[0.5, 0.5, 0.5])
    for method in ALL_METHODS:
        component.render_method = method
        images = {}
        for bindless in (False, True):
            component.use_bindless_textures = bindless
            amr_rc.run()
            images[bindless] = np.array(component.first_pass_fb_rgba)
        assert np.any(images[False] != 0), method
        np.testing.assert_array_equal(images[True], images[False], err_msg=method)


def test_texture_handles(amr_rc, require_bindless):
    block_collection = amr_rc.scene.components[0].data
    handles = block_collection.texture_handles()
    n_blocks = len(block_collection.texture_objects)
    assert handles.shape == (2, n_blocks)
    assert handles.dtype == np.uint64
    for vbo_i in range(n_blocks):
        data_handle, bitmap_handle = handles[:, vbo_i]
        assert data_handle == block_collection.texture_objects[vbo_i].handle != 0
        assert bitmap_handle == block_collection.bitmap_objects[vbo_i].handle != 0

    textures = list(block_collection.texture_objects.values())
    block_collection.release()
    assert all(tex.handle == 0 for tex in textures)
    assert block_collection._texture_handles is None
