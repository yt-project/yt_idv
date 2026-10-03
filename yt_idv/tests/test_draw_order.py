import sys

import numpy as np
import pytest
from yt.testing import fake_amr_ds


@pytest.fixture()
def amr_rc(make_rc):
    rc = make_rc(width=64, height=64)
    ds = fake_amr_ds()
    rc.add_scene(ds, "radius", no_ghost=False)
    return rc


@pytest.mark.parametrize(
    "method, order_matters",
    [
        ("max_intensity", False),
        ("projection", False),
        ("constant", False),
        ("transfer_function", True),
        ("isocontours", True),
        ("slice", True),
    ],
)
def test_draw_order_matters(amr_rc, method, order_matters):
    component = amr_rc.scene.components[0]
    component.render_method = method
    assert component._draw_order_matters is order_matters


# Maxima are exact in any order, but sums (projection and constant) round
# differently in a different order: float32 allows about 3e-6 relative here.
# macOS's OpenGL renders identical inputs with differences of up to about 1e-4
# relative, so the comparisons there are looser.
@pytest.mark.parametrize(
    "method, rtol",
    [("max_intensity", 0), ("projection", 1e-5), ("constant", 1e-5)],
)
def test_order_independent_methods_skip_viewpoint_walk(
    amr_rc, method, rtol, monkeypatch
):
    if sys.platform == "darwin":
        rtol = 1e-3
    component = amr_rc.scene.components[0]
    component.render_method = method
    component.store_first_pass_fb = True
    amr_rc.scene.camera.update(position=[1.6, 1.3, 2.0], focus=[0.5, 0.5, 0.5])

    # the image drawn in viewpoint order, as every method did before
    monkeypatch.setattr(type(component), "_draw_order_matters", True)
    amr_rc.run()
    walked = np.array(component.first_pass_fb_rgba)

    monkeypatch.undo()

    def fail(camera):
        raise AssertionError("viewpoint_iter called for an order-independent method")

    monkeypatch.setattr(component.data, "viewpoint_iter", fail)
    amr_rc.run()
    unordered = np.array(component.first_pass_fb_rgba)

    assert np.any(walked != 0)
    # the same fragments contribute either way (for projection, alpha counts
    # them), so only the rounding of the sums can differ
    np.testing.assert_array_equal(unordered[..., 3], walked[..., 3])
    np.testing.assert_allclose(unordered, walked, rtol=rtol, atol=0)
