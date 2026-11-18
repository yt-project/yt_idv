import numpy as np
import pytest
import yt
from numpy.testing import assert_allclose

from yt_idv.scene_components.particles import ParticleRendering
from yt_idv.scene_components.sph_particles import SPHRendering
from yt_idv.scene_data.particle_positions import ParticlePositions

# Particles 0 and 1 overlap on screen when viewed along z; 2 and 3 are isolated.
_X = np.array([0.3, 0.3, 0.7, 0.7])
_Y = np.array([0.5, 0.5, 0.3, 0.7])
_Z = np.array([0.3, 0.7, 0.5, 0.5])
_VALUES = np.array([3.0, 7.0, 5.0, -2.0])


def _render(make_rc, render_method):
    data = {
        ("gas", "particle_position_x"): _X,
        ("gas", "particle_position_y"): _Y,
        ("gas", "particle_position_z"): _Z,
        ("gas", "smoothing_length"): np.full(4, 0.08),
        ("gas", "density"): (np.ones(4), "g/cm**3"),
        ("gas", "mass"): (np.full(4, 1e-3), "g"),
        ("gas", "val"): _VALUES,
    }
    ds = yt.load_particles(data, length_unit=1.0, bbox=np.array([[0.0, 1.0]] * 3))
    rc = make_rc(width=256, height=256)
    scene = rc.add_scene(ds, None, no_ghost=True)
    positions = ParticlePositions(
        data_source=ds.all_data(),
        particle_type="gas",
        position_field="particle_position",
        radius_field="smoothing_length",
        color_field="val",
        mass_field="mass",
        density_field="density",
    )
    component = SPHRendering(
        data=positions,
        render_method=render_method,
        max_particle_size=1.0,
        store_first_pass_fb=True,
        cmap_log=False,
    )
    scene.data_objects.append(positions)
    scene.components.append(component)

    camera = scene.camera
    camera.projection_type = "orthographic"
    camera.focus = [0.5, 0.5, 0.5]
    camera.up = [0.0, 1.0, 0.0]
    camera.set_position([0.5, 0.5, 2.0])
    image = rc.run()

    fb = component.first_pass_fb_rgba
    clip = (
        camera.projection_matrix
        @ camera.view_matrix
        @ np.stack([_X, _Y, _Z, np.ones(4)])
    )
    ny, nx = fb.shape[:2]
    cols = ((clip[0] / clip[3] + 1) / 2 * nx).astype(int)
    rows = ((clip[1] / clip[3] + 1) / 2 * ny).astype(int)
    return rc, component, fb[rows, cols, 0], image


@pytest.mark.image_test
def test_sph_max_intensity(make_rc):
    _, component, centers, _ = _render(make_rc, "max_intensity")
    assert_allclose(centers, [7.0, 7.0, 5.0, -2.0])
    # undrawn pixels hold the lowest float and must not set the bounds
    assert_allclose([component.cmap_min, component.cmap_max], [-2.0, 7.0])


@pytest.mark.image_test
def test_sph_integration(make_rc):
    _, component, centers, _ = _render(make_rc, "default")
    # identical kernels and weights, so center columns scale with the values
    reference = centers[2] / _VALUES[2]
    assert reference > 0.0
    assert_allclose(centers[0], (_VALUES[0] + _VALUES[1]) * reference, rtol=1e-5)
    assert_allclose(centers[3], _VALUES[3] * reference, rtol=1e-5)
    # undrawn pixels hold 0 and must not set the bounds
    values = component.first_pass_fb_rgba[:, :, 0]
    values = values[values != 0.0]
    assert_allclose(
        [component.cmap_min, component.cmap_max], [values.min(), values.max()]
    )


@pytest.mark.image_test
@pytest.mark.parametrize("render_method", ["default", "max_intensity"])
def test_sph_undrawn_pixels_are_background(make_rc, render_method):
    _, component, _, image = _render(make_rc, render_method)
    drawn = component._drawn_pixel_mask(component.first_pass_fb_rgba)
    assert 0 < drawn.sum() < drawn.size
    assert (image[:, :, 3] > 0).sum() == drawn.sum()


@pytest.mark.image_test
def test_sph_single_channel_framebuffer(make_rc):
    rc, component, _, _ = _render(make_rc, "default")
    assert component.fb.fb_tex.channels == 1
    component.display_bounds = (0.0, 0.5, 0.0, 0.5)
    assert component.fb.fb_tex.channels == 1
    rc.scene.reset_framebuffers()
    assert component.fb.fb_tex.channels == 1


@pytest.mark.image_test
def test_sph_coverage_definition_does_not_leak(make_rc):
    _, component, _, _ = _render(make_rc, "default")
    coverage = ("COVERAGE_FROM_VALUE", "")
    assert coverage in component.colormap_fragment.preprocessor_defs
    # another component using the same colormap shader, created afterwards
    other = ParticleRendering()
    assert other.colormap_fragment.shader_name == "apply_colormap"
    assert coverage not in other.colormap_fragment.preprocessor_defs
    assert other.fb.fb_tex.channels == 4
