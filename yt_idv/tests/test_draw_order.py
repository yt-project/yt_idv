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


@pytest.mark.parametrize("method", ["max_intensity", "projection", "constant"])
def test_order_independent_methods_skip_viewpoint_walk(amr_rc, method, monkeypatch):
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
    # sums in a different order can round differently
    np.testing.assert_allclose(unordered, walked, rtol=1e-6, atol=0)
