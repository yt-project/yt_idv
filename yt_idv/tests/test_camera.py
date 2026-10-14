import numpy as np
import pytest
from numpy.testing import assert_allclose

from yt_idv.cameras.trackball_camera import TrackballCamera


@pytest.fixture()
def camera():
    cam = TrackballCamera(
        position=np.array([0.5, 0.5, 2.5]), focus=np.array([0.5, 0.5, 0.5])
    )
    cam.update_matrices()
    return cam


@pytest.mark.parametrize(
    "trait, value",
    [("fov", 20.0), ("near_plane", 0.5), ("far_plane", 5.0), ("aspect_ratio", 2.0)],
)
def test_projection_traits_rebuild_projection(camera, trait, value):
    p0 = camera.projection_matrix.copy()
    v0 = camera.view_matrix.copy()
    o0 = camera.orientation.copy()

    setattr(camera, trait, value)

    assert not np.allclose(p0, camera.projection_matrix)
    assert np.array_equal(v0, camera.view_matrix)
    assert np.array_equal(o0, camera.orientation)


def test_trait_set_after_drag_keeps_trackball_rotation(camera):
    camera.update_orientation(0.0, 0.0, 0.3, 0.2)
    v0 = camera.view_matrix.copy()
    o0 = camera.orientation.copy()
    pos0 = camera.position.copy()

    camera.fov = 30.0
    camera.near_plane = 0.1

    assert np.array_equal(v0, camera.view_matrix)
    assert np.array_equal(o0, camera.orientation)
    assert np.array_equal(pos0, camera.position)


def test_position_moves_leave_orientation_alone(camera):
    camera.update_orientation(0.0, 0.0, 0.3, 0.2)
    o0 = camera.orientation.copy()

    camera.move_forward(0.1)
    assert np.array_equal(o0, camera.orientation)

    camera.offset_position(np.array([0.05, 0.0, 0.0]))
    assert np.array_equal(o0, camera.orientation)


def test_update_rebuilds_projection_once(camera):
    calls = []
    original = camera._compute_matrices

    def counting():
        calls.append(1)
        original()

    camera._compute_matrices = counting
    p0 = camera.projection_matrix.copy()

    camera.update(fov=30.0, near_plane=0.1, far_plane=10.0)

    assert len(calls) == 1
    assert not np.allclose(p0, camera.projection_matrix)
    assert camera.fov == 30.0 and camera.near_plane == 0.1 and camera.far_plane == 10.0
    assert not camera.held


def test_update_matrices_rebuilds_view_from_lookat(camera):
    camera.update_orientation(0.0, 0.0, 0.3, 0.2)
    v_dragged = camera.view_matrix.copy()

    camera.focus = np.array([0.6, 0.4, 0.5])
    assert np.array_equal(v_dragged, camera.view_matrix)

    camera.update_matrices()
    v_lookat = camera.view_matrix.copy()
    assert not np.allclose(v_dragged, v_lookat)

    camera.view_matrix = v_dragged
    camera._update_matrices()
    assert np.array_equal(camera.view_matrix, v_lookat)


def test_set_orientation_syncs_position_up_and_view(camera):
    focus0 = camera.focus.copy()
    dist0 = np.linalg.norm(camera.position - camera.focus)

    camera.update_orientation(0.0, 0.0, 0.3, 0.2)
    q = camera.orientation.copy()
    expected = {k: getattr(camera, k).copy() for k in ("position", "up", "view_matrix")}

    camera.update_matrices()
    camera.set_orientation(q)

    assert np.array_equal(camera.orientation, q)
    assert np.array_equal(camera.focus, focus0)
    assert np.isclose(np.linalg.norm(camera.position - camera.focus), dist0)
    for k, v in expected.items():
        assert np.allclose(getattr(camera, k), v), k


def test_update_always_rebuilds_view(camera):
    camera.update_orientation(0.0, 0.0, 0.3, 0.2)
    q = camera.orientation.copy()
    v0 = camera.view_matrix.copy()

    # projection-only change: the view is re-derived from position, focus and
    # up, which set_orientation kept in sync with the dragged quaternion
    camera.update(fov=30.0)
    assert np.allclose(camera.orientation, q)
    assert np.allclose(camera.view_matrix, v0)
    assert camera.fov == 30.0

    camera.update(focus=np.array([0.6, 0.4, 0.5]), fov=35.0)
    assert not np.allclose(camera.view_matrix, v0)
    assert not np.allclose(camera.orientation, q)
    assert camera.fov == 35.0
    assert not camera.held


def test_update_rejects_orientation_and_typos(camera):
    with pytest.raises(TypeError):
        camera.update(orientation=camera.orientation)
    with pytest.raises(TypeError):
        camera.update(postion=np.array([0.5, 0.5, 3.0]))


def test_dict_round_trip_restores_view(camera):
    camera.update_orientation(0.0, 0.0, 0.3, 0.2)
    snapshot = camera.dict()
    v0 = camera.view_matrix.copy()
    pos0 = camera.position.copy()

    camera.update_orientation(0.0, 0.0, -0.4, 0.1)
    assert not np.allclose(v0, camera.view_matrix)

    assert "orientation" in snapshot
    camera.update_from_dict(snapshot)
    assert np.array_equal(camera.position, pos0)
    assert np.allclose(camera.view_matrix, v0)


def _get_camera(projection_type: str) -> TrackballCamera:
    cam = TrackballCamera(
        position=np.array([0.5, 0.5, 2.5]),
        focus=np.array([0.5, 0.5, 0.5]),
        up=np.array([0.0, 1.0, 0.0]),
        projection_type=projection_type,
    )
    cam.update_matrices()
    return cam


def _to_ndc(cam: TrackballCamera, point: np.ndarray) -> np.ndarray:
    clip = cam.projection_matrix @ cam.view_matrix @ np.append(point, 1.0)
    return clip[:3] / clip[3]


def test_orthographic_matrix_is_affine():
    cam = _get_camera("orthographic")
    proj = cam.projection_matrix
    # no perspective divide: w must not depend on position
    assert proj[3, 0] == proj[3, 1] == proj[3, 2] == 0.0
    assert proj[3, 3] == 1.0
    ndc_focus = _to_ndc(cam, cam.focus)
    assert_allclose(ndc_focus[:2], 0.0, atol=1e-7)


@pytest.mark.parametrize("projection_type", ["perspective", "orthographic"])
def test_apparent_size_at_focal_plane(projection_type: str):
    # at aspect_ratio == 1, a point one orthographic_scale above the focus
    # lands on the top edge of the image in both projection modes, so
    # toggling projection_type preserves apparent size at the focal plane
    cam = _get_camera(projection_type)
    point = cam.focus + cam.orthographic_scale * np.array([0.0, 1.0, 0.0])
    ndc = _to_ndc(cam, point)
    assert_allclose(ndc[1], 1.0, rtol=1e-6)
    assert_allclose(ndc[0], 0.0, atol=1e-7)


@pytest.mark.parametrize("aspect", [16 / 9, 9 / 16])
@pytest.mark.parametrize("projection_type", ["perspective", "orthographic"])
def test_apparent_size_at_any_aspect(projection_type: str, aspect: float):
    # the vertical field of view is fixed and the horizontal one widens with
    # the aspect ratio, so the image stays centered and shapes keep their
    # proportions in pixels
    cam = _get_camera(projection_type)
    cam.aspect_ratio = aspect
    above = cam.focus + cam.orthographic_scale * np.array([0.0, 1.0, 0.0])
    beside = cam.focus + cam.orthographic_scale * aspect * np.array([1.0, 0.0, 0.0])
    assert_allclose(_to_ndc(cam, cam.focus)[:2], 0.0, atol=1e-7)
    assert_allclose(_to_ndc(cam, above)[:2], [0.0, 1.0], atol=1e-6)
    assert_allclose(_to_ndc(cam, beside)[:2], [1.0, 0.0], atol=1e-6)


def test_perspective_matrix_matches_yt_when_square():
    from yt.utilities.math_utils import get_perspective_matrix as yt_perspective

    from yt_idv.cameras.trackball_camera import get_perspective_matrix

    for fov in (30.0, 45.0, 70.0):
        assert_allclose(
            get_perspective_matrix(fov, 1.0, 1e-3, 20.0),
            yt_perspective(fov, 1.0, 1e-3, 20.0),
            rtol=1e-6,
        )


def test_projection_type_trait_rebuilds_projection(camera):
    p_persp = camera.projection_matrix.copy()
    v0 = camera.view_matrix.copy()

    camera.projection_type = "orthographic"
    assert camera.projection_matrix[3, 3] == 1.0
    assert not np.allclose(p_persp, camera.projection_matrix)
    assert np.array_equal(v0, camera.view_matrix)

    camera.projection_type = "perspective"
    assert_allclose(camera.projection_matrix, p_persp)


def test_dict_round_trip_orthographic():
    cam = _get_camera("orthographic")
    cdict = cam.dict()
    assert cdict["projection_type"] == "orthographic"

    cam2 = TrackballCamera()
    cam2.update_from_dict(cdict)
    assert cam2.projection_type == "orthographic"
    assert_allclose(cam2.projection_matrix, cam.projection_matrix)
    assert_allclose(cam2.view_matrix, cam.view_matrix)


def test_orthographic_zoom_rescales_projection():
    cam = _get_camera("orthographic")
    scale0 = cam.projection_matrix[0, 0]
    pos0 = cam.position.copy()
    cam.move_forward(0.5)
    assert not np.allclose(cam.position, pos0)
    # moving toward the focus shrinks the view volume (zooms in)
    assert cam.projection_matrix[0, 0] > scale0
