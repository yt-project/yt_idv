import numpy as np
import pytest
import yt

N = 32
W = 128


def _half_zero():
    # the lower half of the domain in x is exactly zero, the upper half is not
    data = np.zeros((N, N, N), dtype="float64")
    data[N // 2 :, :, :] = np.linspace(1.0, 2.0, N // 2)[:, None, None]
    return data


def _all_zero():
    return np.zeros((N, N, N), dtype="float64")


def _render_rgb(rc, data, cmap_log):
    ds = yt.load_uniform_grid(
        {"density": data}, data.shape, bbox=np.array([[0.0, 1.0]] * 3)
    )
    rc.add_scene(ds, ("stream", "density"), no_ghost=True)
    component = rc.scene.components[0]
    component.render_method = "max_intensity"
    component.cmap_log = cmap_log
    component.colormap.colormap_name = "viridis"
    # look straight down z with an orthographic view whose half-height,
    # tan(fov / 2) * distance, is 1, so the unit domain fills exactly the
    # central quarter of the canvas
    rc.scene.camera.update(
        position=[0.5, 0.5, 1.5],
        focus=[0.5, 0.5, 0.5],
        up=[0.0, 1.0, 0.0],
        fov=90.0,
        aspect_ratio=1.0,
        projection_type="orthographic",
    )
    return np.array(rc.run())[..., :3]


@pytest.mark.image_test
@pytest.mark.parametrize("cmap_log", [False, True])
@pytest.mark.parametrize("make_data", [_half_zero, _all_zero])
def test_zero_valued_regions_are_rendered(make_rc, make_data, cmap_log):
    # https://github.com/yt-project/yt_idv/issues/302: fragments whose samples
    # are all zero were dropped from the image
    rc = make_rc(width=W, height=W)
    rgb = _render_rgb(rc, make_data(), cmap_log)
    lit = rgb.max(axis=-1) > 0

    # the domain covers pixels W/4 to 3W/4 along both axes; leave the one-pixel
    # border ring to rasterization and require everything inside it to be lit
    # and everything outside it to be dark
    lo, hi = W // 4, 3 * W // 4
    assert lit[lo + 1 : hi - 1, lo + 1 : hi - 1].all()
    outside = np.ones_like(lit)
    outside[lo:hi, lo:hi] = False
    assert not lit[outside].any()

    if make_data is _half_zero:
        # zeros at the bottom of the colormap, a gradient above: a single color
        # means the color-mapping collapsed (e.g. a log of a zero lower bound)
        assert len(np.unique(rgb[lit], axis=0)) > 1
