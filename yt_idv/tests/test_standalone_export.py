import numpy as np
import pytest
from numpy.testing import assert_allclose
from yt.testing import fake_amr_ds

from yt_idv.scene_graph import SceneGraph
from yt_idv.standalone_export import export_block_scene

LEFT, RIGHT = [0.25, 0.3, 0.35], [0.65, 0.7, 0.75]


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
    assert next(iter(data.texture_objects.values())).data.dtype == dtype
    if float64:
        # the live scene keeps its edges in float64 too
        for name in ("in_left_edge", "in_right_edge", "in_dx"):
            assert np.array_equal(
                _attribute(data, name).data, _attribute(live_data, name).data
            )

    expected = _first_pass(live, live_scene)
    image = _first_pass(live, loaded)
    assert np.any(expected != 0)
    assert_allclose(image, expected, rtol=1e-5, atol=1e-7)


def _differences(name, live_arr, loaded_arr):
    a = np.asarray(live_arr, dtype="f4")
    b = np.asarray(loaded_arr, dtype="f4")
    if a.shape != b.shape:
        return [f"{name}: shapes differ, {a.shape} vs {b.shape}"]
    differ = a != b
    if not differ.any():
        return []
    ulp = np.abs(a - b) / np.spacing(np.maximum(np.abs(a), np.abs(b)))
    return [
        f"{name}: {differ.sum()} of {a.size} values differ, at most "
        f"{np.abs(a - b).max():.2e} ({ulp.max():.0f} ulp)"
    ]


def test_tmp_diagnostic_gpu_inputs_match_live(live, region, tmp_path):
    # TEMPORARY diagnostic for the macOS-only failure of
    # test_export_loads_and_renders[False]: are the arrays sent to the GPU
    # identical for the live scene and the float32 export? (They are on Linux.)
    live_data = live.scene.components[0].data
    filename = tmp_path / "scene.zip"
    export_block_scene(region, "Density", filename, no_ghost=True, float64=False)
    data = SceneGraph.load(filename).components[0].data

    report = []
    for a in live_data.vertex_array.attributes:
        report += _differences(a.name, a.data, _attribute(data, a.name).data)
    for kind in ("texture_objects", "bitmap_objects"):
        live_tex, loaded_tex = getattr(live_data, kind), getattr(data, kind)
        if sorted(live_tex) != sorted(loaded_tex):
            report.append(f"{kind}: different blocks")
            continue
        for vbo_i in live_tex:
            report += _differences(
                f"{kind}[{vbo_i}]", live_tex[vbo_i].data, loaded_tex[vbo_i].data
            )
    assert not report, "GPU inputs differ:\n" + "\n".join(report[:40])
