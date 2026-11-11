import numpy as np
import pytest
from yt.testing import fake_amr_ds

from yt_idv.cameras import ray_table
from yt_idv.cameras.ray_table import (
    equirectangular_rays,
    fisheye_rays,
    tile_bounds,
    tile_cones,
)


def perspective_rays(camera, width, height):
    """The ray table of the camera's own perspective projection."""
    half_h = np.tan(np.radians(camera.fov) / 2.0)
    half_w = half_h * camera.aspect_ratio
    x = ((np.arange(width) + 0.5) / width * 2.0 - 1.0) * half_w
    y = ((np.arange(height) + 0.5) / height * 2.0 - 1.0) * half_h
    x, y = np.meshgrid(x, y)
    rays = np.stack([x, y, -np.ones_like(x)], axis=-1)
    return (rays / np.linalg.norm(rays, axis=-1, keepdims=True)).astype("f4")


@pytest.fixture()
def amr_rc(make_rc):
    rc = make_rc(width=64, height=64)
    ds = fake_amr_ds()
    rc.add_scene(ds, "radius", no_ghost=False)
    return rc


def _render(rc):
    component = rc.scene.components[0]
    component.store_first_pass_fb = True
    rc.run()
    return np.array(component.first_pass_fb_rgba)


@pytest.mark.parametrize(
    "method", ["max_intensity", "projection", "transfer_function", "isocontours"]
)
def test_perspective_ray_table_matches_perspective(amr_rc, method):
    component = amr_rc.scene.components[0]
    component.render_method = method
    camera = amr_rc.scene.camera
    camera.update(position=[1.6, 1.3, 2.0], focus=[0.5, 0.5, 0.5])
    expected = _render(amr_rc)

    camera.ray_table = perspective_rays(camera, 64, 64)
    camera.projection_type = "ray_table"
    got = _render(amr_rc)

    # The perspective path takes its ray from the box's interpolated surface
    # point, good to about 1e-5 radians, and samples near block edges are that
    # sensitive; so compare the images statistically.
    assert np.any(expected[..., :3] != 0)
    coverage = (expected[..., 3] != 0) ^ (got[..., 3] != 0)
    assert coverage.sum() <= 2
    diff = np.abs(got - expected)[..., :3].max(axis=-1) / expected[..., :3].max()
    assert diff.mean() < 1e-3
    assert (diff > 0.01).mean() < 0.03


@pytest.mark.parametrize("position", [[0.5, 0.5, 0.5], [0.5, 0.5, 3.0]])
def test_tile_culling_keeps_every_pixel(amr_rc, position, monkeypatch):
    # drawing every block over the whole screen gives the same image
    component = amr_rc.scene.components[0]
    component.render_method = "max_intensity"
    camera = amr_rc.scene.camera
    camera.update(position=position, focus=[0.5, 0.5, 0.0])
    camera.ray_table = equirectangular_rays(64, 64)
    camera.projection_type = "ray_table"
    culled = _render(amr_rc)

    def no_culling(rays):
        cones = tile_cones(rays)
        cones[..., 3] = np.pi
        return cones

    monkeypatch.setattr(ray_table, "tile_cones", no_culling)
    camera.ray_table = camera.ray_table.copy()  # drops the cached textures
    full = _render(amr_rc)

    assert np.any(full[..., :3] != 0)
    np.testing.assert_array_equal(culled, full)


def test_pixels_without_rays_stay_empty(amr_rc):
    component = amr_rc.scene.components[0]
    component.render_method = "max_intensity"
    camera = amr_rc.scene.camera
    camera.update(position=[0.5, 0.5, 0.5], focus=[0.5, 0.5, 0.0])
    rays = fisheye_rays(64, 64, fov=180.0)
    camera.ray_table = rays
    camera.projection_type = "ray_table"
    image = _render(amr_rc)
    no_ray = np.linalg.norm(rays, axis=-1) == 0
    assert np.all(image[no_ray] == 0)
    assert np.any(image[~no_ray][:, :3] != 0)


@pytest.mark.parametrize(
    "rays",
    [equirectangular_rays(200, 100), fisheye_rays(90, 70, fov=220.0)],
    ids=["equirectangular", "fisheye"],
)
def test_tile_cones_hold_their_rays(rays):
    cones = tile_cones(rays, tile_pixels=16)
    nty, ntx = cones.shape[:2]
    xb, yb = tile_bounds(rays.shape[1], ntx), tile_bounds(rays.shape[0], nty)
    for ty in range(nty):
        for tx in range(ntx):
            d = rays[yb[ty] : yb[ty + 1], xb[tx] : xb[tx + 1]].reshape(-1, 3)
            d = d[np.linalg.norm(d, axis=-1) > 0]
            if len(d) == 0:
                assert cones[ty, tx, 3] < 0
                continue
            d = d / np.linalg.norm(d, axis=-1, keepdims=True)
            angles = np.arccos(np.clip(d @ cones[ty, tx, :3], -1, 1))
            assert angles.max() <= cones[ty, tx, 3]


def test_equirectangular_directions():
    rays = equirectangular_rays(4, 2)
    np.testing.assert_allclose(np.linalg.norm(rays, axis=-1), 1.0, rtol=1e-6)
    # the two center columns straddle the view direction, -z
    center = rays[:, 1:3].mean(axis=(0, 1))
    np.testing.assert_allclose(center / np.linalg.norm(center), [0, 0, -1], atol=1e-6)
    # the top row looks up
    assert np.all(rays[1, :, 1] > 0) and np.all(rays[0, :, 1] < 0)


def _stereo_origins(rays, half_ipd):
    # omnidirectional stereo: each column's eye sits sideways to its direction
    horizontal = rays * np.array([1.0, 0.0, 1.0], dtype="f4")
    horizontal /= np.linalg.norm(horizontal, axis=-1, keepdims=True)
    return (
        half_ipd
        * np.stack(
            [horizontal[..., 2], 0 * horizontal[..., 0], -horizontal[..., 0]], -1
        )
    ).astype("f4")


@pytest.mark.parametrize("scale", [1.0, 2.0])
def test_constant_ray_origin_matches_moving_the_camera(amr_rc, scale):
    component = amr_rc.scene.components[0]
    component.render_method = "max_intensity"
    camera = amr_rc.scene.camera
    rays = equirectangular_rays(64, 32)
    offset = np.array([0.05, -0.03, 0.02], dtype="f4")  # camera space

    camera.update(position=[0.5, 0.45, 0.5], focus=[0.5, 0.45, 0.0])
    camera.ray_table = rays
    camera.projection_type = "ray_table"
    camera.ray_origins = np.broadcast_to(offset / scale, rays.shape).copy()
    camera.ray_origin_scale = scale
    shifted_rays = _render(amr_rc)

    to_model = np.linalg.inv(np.asarray(camera.view_matrix, dtype="f8")[:3, :3])
    moved = np.asarray(camera.position, dtype="f8") + to_model @ offset
    camera.ray_origins = None
    camera.ray_origin_scale = 1.0
    camera.update(position=moved, focus=moved - [0.0, 0.0, 0.5])
    moved_camera = _render(amr_rc)

    assert np.any(moved_camera[..., :3] != 0)
    np.testing.assert_allclose(shifted_rays, moved_camera, rtol=1e-5, atol=1e-6)


def test_tile_culling_keeps_every_pixel_with_ray_origins(amr_rc, monkeypatch):
    component = amr_rc.scene.components[0]
    component.render_method = "max_intensity"
    camera = amr_rc.scene.camera
    camera.update(position=[0.5, 0.5, 0.5], focus=[0.5, 0.5, 0.0])
    rays = equirectangular_rays(64, 32)
    camera.ray_table = rays
    camera.ray_origins = _stereo_origins(rays, 0.2)
    camera.projection_type = "ray_table"
    culled = _render(amr_rc)

    def no_culling(rays):
        cones = tile_cones(rays)
        cones[..., 3] = np.pi
        return cones

    monkeypatch.setattr(ray_table, "tile_cones", no_culling)
    camera.ray_table = camera.ray_table.copy()
    full = _render(amr_rc)

    assert np.any(full[..., :3] != 0)
    np.testing.assert_array_equal(culled, full)


def test_alternating_ray_tables_reuse_their_textures(amr_rc):
    camera = amr_rc.scene.camera
    camera.projection_type = "ray_table"
    rays = equirectangular_rays(64, 32)
    left, right = _stereo_origins(rays, -0.03), _stereo_origins(rays, 0.03)
    camera.ray_table = rays
    seen = []
    for origins in (left, right, left, right):
        camera.ray_origins = origins
        amr_rc.run()
        seen.append(camera._ray_table_entry()["textures"][0].texture_name)
    assert seen[0] == seen[2] and seen[1] == seen[3] and seen[0] != seen[1]
