import numpy as np
import pytest
from numpy.testing import assert_allclose

from yt_idv.cameras.trackball_camera import TrackballCamera


def _get_camera(projection_type: str) -> TrackballCamera:
    cam = TrackballCamera(
        position=np.array([0.5, 0.5, 2.5]),
        focus=np.array([0.5, 0.5, 0.5]),
        up=np.array([0.0, 1.0, 0.0]),
        projection_type=projection_type,
    )
    cam._update_matrices()
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


def test_dict_round_trip():
    cam = _get_camera("orthographic")
    cdict = cam.dict()
    assert cdict["projection_type"] == "orthographic"

    cam2 = TrackballCamera()
    cam2.update(**cdict)
    cam2._update_matrices()
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
