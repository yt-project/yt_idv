import numpy as np
import pytest
import yt

N = 32


def _half_zero():
    # the lower half of the domain in x is exactly zero, the upper half is not
    data = np.zeros((N, N, N), dtype="float64")
    data[N // 2 :, :, :] = np.linspace(1.0, 2.0, N // 2)[:, None, None]
    return data


def _all_zero():
    return np.zeros((N, N, N), dtype="float64")


def _lit_pixel_count(rc, data):
    ds = yt.load_uniform_grid(
        {"density": data}, data.shape, bbox=np.array([[0.0, 1.0]] * 3)
    )
    rc.add_scene(ds, ("stream", "density"), no_ghost=True)
    component = rc.scene.components[0]
    component.render_method = "max_intensity"
    component.cmap_log = False
    component.fixed_cmap_min = 0.0
    component.fixed_cmap_max = 1.0
    component.colormap.colormap_name = "viridis"
    image = np.array(rc.run())
    return int((image[..., :3].max(axis=-1) > 0).sum())


@pytest.mark.image_test
@pytest.mark.parametrize("make_data", [_half_zero, _all_zero])
def test_zero_valued_regions_are_rendered(make_rc, make_data):
    # https://github.com/yt-project/yt_idv/issues/302: fragments whose samples
    # are all zero were dropped from the image. The footprint they should fill
    # comes from rendering the same domain with data that is nonzero everywhere.
    # Textures are normalized by the data minimum, so the reference can't have
    # a region sitting at its minimum; a gradient across the whole domain works.
    rc = make_rc(width=128, height=128)
    reference = np.ones((N, N, N)) * np.linspace(1.0, 2.0, N)[:, None, None]
    expected = _lit_pixel_count(rc, reference)
    assert expected > 0
    assert _lit_pixel_count(rc, make_data()) == expected
