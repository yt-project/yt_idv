import numpy as np
import pytest

from yt_idv.utilities._vector_operations import dist_along_ray, sort_points_along_ray


@pytest.mark.parametrize("idim", range(3))
def test_projection_onto_dim(idim):

    # project along x from 0, should get the x input
    pts = (np.random.random((20, 3)) - 0.5) * 2

    ray0 = np.array([0.0, 0.0, 1.0])
    ray_dir = np.array(
        [
            0.0,
            0.0,
            0.0,
        ]
    )
    ray_dir[idim] = 1.0

    tvals = dist_along_ray(pts, ray0, ray_dir)
    expected = pts[:, idim] - ray0[idim]
    assert np.allclose(tvals, expected)

    indx = sort_points_along_ray(pts, ray0, ray_dir, back_to_front=False)
    sorted_t = tvals[indx]
    assert np.all(sorted_t[1:] >= sorted_t[:-1])

    indx = sort_points_along_ray(pts, ray0, ray_dir, back_to_front=True)
    sorted_t = tvals[indx]
    assert np.all(sorted_t[:-1] >= sorted_t[1:])


def test_general_projection():
    pts = (np.random.random((20, 3)) - 0.5) * 2

    ray0 = np.array([0.0, 0.0, 1.0])
    ray_dir = np.array(
        [
            0.1,
            0.5,
            5.0,
        ]
    )
    ray_dir = ray_dir / np.linalg.norm(ray_dir)
    tvals = dist_along_ray(pts, ray0, ray_dir)
    assert np.all(np.isreal(tvals))

    indx = sort_points_along_ray(pts, ray0, ray_dir, back_to_front=False)
    sorted_t = tvals[indx]
    assert np.all(sorted_t[1:] >= sorted_t[:-1])

    indx = sort_points_along_ray(pts, ray0, ray_dir, back_to_front=True)
    sorted_t = tvals[indx]
    assert np.all(sorted_t[:-1] >= sorted_t[1:])


def test_single_point():
    pts = np.array([5.0, 10.0, 15.0])
    ray0 = np.array([0.0, 0.0, 1.0])
    ray_dir = np.array(
        [
            0.0,
            0.0,
            1.0,
        ]
    )
    tval = dist_along_ray(pts, ray0, ray_dir)
    assert tval == pts[2] - ray0[2]


def test_dist_along_ray_edge_errors():

    pts = np.random.random((10, 3, 2))
    ray0 = np.array([0.0, 0.0, 1.0])
    ray_dir = np.array(
        [
            1.0,
            0.0,
            0.0,
        ]
    )
    with pytest.raises(ValueError, match="pts must be at most a 2D array"):
        dist_along_ray(pts, ray0, ray_dir)
