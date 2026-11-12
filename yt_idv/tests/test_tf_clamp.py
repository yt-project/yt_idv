import numpy as np
import pytest
from yt.testing import fake_amr_ds


@pytest.fixture()
def tf_render(make_rc):
    rc = make_rc(width=64, height=64)
    ds = fake_amr_ds(fields=[("gas", "density")], units=["g/cm**3"])
    rc.add_scene(ds, ("gas", "density"), no_ghost=True)
    component = rc.scene.components[0]
    component.render_method = "transfer_function"
    # linear over the normalized texels, most of which lie in 0.05-0.3
    component.tf_log = False
    component.store_first_pass_fb = True

    def render(tf_min, tf_max, clamp_low=False, clamp_high=False, tf=None):
        component.tf_min, component.tf_max = tf_min, tf_max
        component.tf_clamp_low, component.tf_clamp_high = clamp_low, clamp_high
        if tf is not None:
            component.transfer_function.data = tf
        rc.run()
        return np.array(component.first_pass_fb_rgba)

    return render


@pytest.mark.parametrize(
    "clamp_low, clamp_high, covering_range",
    [
        (True, True, (-10.0, 10.0)),
        (True, False, (-10.0, 0.2)),
        (False, True, (0.1, 10.0)),
    ],
)
def test_clamping_draws_values_outside_the_range(
    tf_render, clamp_low, clamp_high, covering_range
):
    # with a constant transfer function, a clamped sample looks like any other,
    # so clamping a side matches a range that covers every value on that side
    clamped = tf_render(0.1, 0.2, clamp_low, clamp_high)
    covered = tf_render(*covering_range)
    assert covered[..., 3].max() > 0
    np.testing.assert_array_equal(clamped, covered)
    assert np.any(tf_render(0.1, 0.2) != covered)


def test_clamped_samples_take_the_end_value(tf_render):
    # transparent in the lower half of the table and opaque in the upper half
    tf = np.full((256, 1, 4), 255, dtype="u1")
    tf[:128] = 0
    unclamped = tf_render(0.1, 0.2, tf=tf)
    assert unclamped[..., 3].max() > 0
    # clamped low samples take the transparent lower end, so nothing changes
    np.testing.assert_array_equal(tf_render(0.1, 0.2, clamp_low=True), unclamped)
    # clamped high samples take the opaque upper end
    clamped_high = tf_render(0.1, 0.2, clamp_high=True)
    assert np.all(clamped_high[..., 3] >= unclamped[..., 3])
    assert np.any(clamped_high[..., 3] > unclamped[..., 3])
