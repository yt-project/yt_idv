import numpy as np
import pytest

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
