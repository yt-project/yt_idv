"""Tests for extracting data values from a rendered scene."""

import numpy as np
import pytest
import yt
from numpy.testing import assert_allclose
from unyt import Unit

import yt_idv
from yt_idv.rendered_image_plane import image_plane_extent


@pytest.fixture()
def osmesa_uniform():
    """An OSMesa context with a uniform grid whose density is in [1, 2) g/cm**3.

    The nonzero minimum matters: the 3D textures are min/max normalized, so a
    field that does not approach zero exercises the full de-normalization.
    """
    rng = np.random.default_rng(42)
    shape = (32, 32, 32)
    ds = yt.load_uniform_grid(
        {("gas", "density"): (1.0 + rng.random(shape), "g/cm**3")},
        shape,
        length_unit="kpc",
        bbox=np.array([[0.0, 1.0]] * 3),
    )
    rc = yt_idv.render_context("osmesa", width=512, height=512)
    rc.add_scene(ds.all_data(), ("gas", "density"), no_ghost=False)
    rc.scene.components[0].store_first_pass_fb = True
    yield rc
    rc.osmesa.OSMesaDestroyContext(rc.context)


def test_block_collection_field_metadata(osmesa_uniform):
    block_collection = osmesa_uniform.scene.components[0].data
    assert block_collection.field == ("gas", "density")
    assert block_collection.field_units == "g/cm**3"
    assert block_collection._textures_are_normalized
    assert block_collection.internal_length_unit == 1.0  # code_length
    assert str(block_collection.internal_length_unit.units) == "code_length"


def test_requires_stored_framebuffer(osmesa_uniform):
    component = osmesa_uniform.scene.components[0]
    component.store_first_pass_fb = False
    with pytest.raises(RuntimeError, match="store_first_pass_fb"):
        component.rendered_image_plane()


def test_unsupported_render_method(osmesa_uniform):
    component = osmesa_uniform.scene.components[0]
    component.render_method = "transfer_function"
    osmesa_uniform.scene.render()
    with pytest.raises(NotImplementedError, match="transfer_function"):
        component.rendered_image_plane()


@pytest.mark.parametrize("render_method", ["max_intensity", "slice"])
def test_values_are_denormalized(osmesa_uniform, render_method):
    component = osmesa_uniform.scene.components[0]
    component.render_method = render_method
    osmesa_uniform.scene.render()

    frb = component.rendered_image_plane()
    block_collection = component.data
    assert str(frb.data.units) == "g/cm**3"

    values = frb.data[np.isfinite(frb.data)]
    # the raw framebuffer is normalized to (0, 1); the returned values must
    # instead span the range of the data that built the textures
    assert values.min() >= block_collection.min_val
    assert values.max() <= block_collection.max_val
    assert values.max() > 1.0
    # pixels that no ray sampled should not masquerade as data
    assert np.isnan(frb.data).any()


def test_projection_path_length_and_units(osmesa_uniform):
    component = osmesa_uniform.scene.components[0]
    component.render_method = "projection"

    # look down an axis with a narrow field of view, so that rays are close to
    # parallel and pass through the full depth of the domain exactly once
    camera = osmesa_uniform.scene.camera
    camera.update(position=[0.5, 0.5, 20.0], focus=[0.5, 0.5, 0.5], up=[0.0, 1.0, 0.0])
    camera.fov = 3.0
    camera.far_plane = 100.0
    camera._update_matrices()
    osmesa_uniform.scene.render()

    frb = component.rendered_image_plane()
    # field units times a length, which unyt simplifies to a surface density
    assert frb.data.units.dimensions == Unit("g/cm**2").dimensions
    assert str(frb.path_length.units) == "code_length"

    ny, nx = frb.data.shape
    center = (ny // 2, nx // 2)
    # the domain is one code_length deep; the ray marcher can overshoot the exit
    # point by up to one step (dx = 1/32)
    assert_allclose(frb.path_length[center].d, 1.0, atol=1.5 / 32)

    # the path-averaged value has to land in the range of the data, which it
    # only does if the min/max normalization has been undone using the path
    # length: without that correction it would fall below min_val
    mean_along_ray = (frb.data / frb.path_length).to("g/cm**3")
    sampled = frb.path_length.d > 0.5
    assert mean_along_ray[sampled].min() >= component.data.min_val
    assert mean_along_ray[sampled].max() <= component.data.max_val
    assert_allclose(mean_along_ray[center].d, 1.5, atol=0.1)


def test_frb_geometry(osmesa_uniform):
    component = osmesa_uniform.scene.components[0]
    component.render_method = "slice"

    camera = osmesa_uniform.scene.camera
    camera.update(position=[0.5, 0.5, 2.5], focus=[0.5, 0.5, 0.5], up=[0.0, 1.0, 0.0])
    camera.fov = 45.0
    camera.aspect_ratio = 1.0
    camera._update_matrices()
    osmesa_uniform.scene.render()

    frb = component.rendered_image_plane()

    # for a symmetric frustum the visible extent at the focus plane is
    # 2 * distance * tan(fov / 2)
    distance = 2.0
    expected = 2 * distance * np.tan(np.radians(45.0) / 2)
    assert_allclose(frb.width.d, expected, rtol=1e-5)
    assert_allclose(frb.height.d, expected, rtol=1e-5)
    assert str(frb.width.units) == "code_length"
    assert_allclose(frb.center.d, [0.5, 0.5, 0.5], atol=1e-6)
    assert_allclose(frb.extent.d, [-expected / 2, expected / 2] * 2, rtol=1e-5)

    assert frb.data.shape == component.fb.viewport[3:1:-1]


def test_integrate(osmesa_uniform):
    component = osmesa_uniform.scene.components[0]
    component.render_method = "slice"
    osmesa_uniform.scene.render()

    frb = component.rendered_image_plane()
    ny, nx = frb.data.shape
    dx, dy = frb.pixel_size
    assert_allclose((dx * nx).d, frb.width.d, rtol=1e-12)
    assert_allclose((dy * ny).d, frb.height.d, rtol=1e-12)

    integral = frb.integrate()
    assert integral.units.dimensions == Unit("g/cm").dimensions

    # NaN pixels are skipped, so the integral is the mean of the sampled data
    # times the area those pixels cover
    sampled = np.isfinite(frb.data)
    area = sampled.sum() * dx * dy
    assert_allclose(
        integral.d, (frb.data[sampled].mean() * area).to(integral.units).d, rtol=1e-6
    )
    assert integral.d > 0


def test_image_plane_extent_round_trip():
    from yt.utilities.math_utils import get_lookat_matrix, get_perspective_matrix

    focus = np.array([0.5, 0.5, 0.5])
    position = np.array([1.0, 2.0, 3.0])
    view_matrix = get_lookat_matrix(position, focus, np.array([0.0, 1.0, 0.0]))

    for aspect in (1.0, 1.6):
        projection_matrix = get_perspective_matrix(45.0, aspect, 0.001, 20.0)
        extent, right, up = image_plane_extent(projection_matrix, view_matrix, focus)

        # the corners of the extent must map back to the corners of the
        # normalized device cube
        pmv = projection_matrix @ view_matrix
        for x, y, expected in (
            (extent[0], extent[2], [-1.0, -1.0]),
            (extent[1], extent[3], [1.0, 1.0]),
        ):
            clip = pmv @ np.append(focus + x * right + y * up, 1.0)
            assert_allclose(clip[:2] / clip[3], expected, atol=1e-5)
