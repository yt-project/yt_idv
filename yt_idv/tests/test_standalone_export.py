import sys

import numpy as np
import pytest
from numpy.testing import assert_allclose
from yt.testing import fake_amr_ds

from yt_idv.scene_graph import SceneGraph
from yt_idv.standalone_export import export_block_scene

LEFT, RIGHT = [0.25, 0.3, 0.35], [0.65, 0.7, 0.75]

# macOS's OpenGL renders identical inputs (vertices and textures) with
# differences of up to about 1e-4 relative, so render comparisons are looser
# there
RENDER_RTOL = 1e-3 if sys.platform == "darwin" else 1e-5


@pytest.fixture()
def region():
    ds = fake_amr_ds()
    # the region holds only a weak reference to its dataset
    region = ds.region([0.5, 0.5, 0.5], LEFT, RIGHT)
    region._test_ds = ds
    return region


@pytest.fixture()
def live(make_rc, region):
    rc = make_rc(width=64, height=64)
    rc.add_scene(region, "Density", no_ghost=True)
    return rc


def _attribute(data, name):
    return next(a for a in data.vertex_array.attributes if a.name == name)


def _first_pass(rc, scene):
    rc.scene = scene
    component = scene.components[0]
    component.render_method = "max_intensity"
    component.store_first_pass_fb = True
    # the exported camera has its own up vector and near plane
    scene.camera.update(
        position=[1.5, 1.2, 2.0],
        focus=[0.5, 0.5, 0.5],
        up=[0.0, 0.0, 1.0],
        fov=45.0,
        near_plane=1e-3,
        far_plane=20.0,
        aspect_ratio=1.0,
    )
    # the first frame can differ, as some components leave GL state behind
    # (see test_serialization._render)
    rc.run()
    rc.run()
    return np.array(component.first_pass_fb_rgba)


@pytest.mark.parametrize("float64", [False, True])
def test_export_loads_and_renders(live, region, tmp_path, float64):
    live_scene = live.scene
    live_data = live_scene.components[0].data
    filename = tmp_path / "scene.zip"
    export_block_scene(region, "Density", filename, no_ghost=True, float64=float64)
    loaded = SceneGraph.load(filename)
    data = loaded.components[0].data

    dtype = np.float64 if float64 else np.float32
    for name in ("in_left_edge", "in_right_edge", "in_dx"):
        assert _attribute(data, name).data.dtype == dtype
    assert next(iter(data.block_data.values())).dtype == dtype
    if float64:
        # the live scene keeps its edges in float64 too
        for name in ("in_left_edge", "in_right_edge", "in_dx"):
            assert np.array_equal(
                _attribute(data, name).data, _attribute(live_data, name).data
            )

    expected = _first_pass(live, live_scene)
    image = _first_pass(live, loaded)
    assert np.any(expected != 0)
    assert_allclose(image, expected, rtol=RENDER_RTOL, atol=1e-7)
