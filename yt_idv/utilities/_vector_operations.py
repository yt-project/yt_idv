from typing import List

import numpy as np
import numpy.typing as npt


def dist_along_ray(
    pts: npt.NDArray[np.float_],
    ray_orgin: npt.NDArray[np.float_],
    ray_unit_dir: npt.NDArray[np.float_],
) -> npt.NDArray[np.float_]:
    """Project an array of 3D points onto an arbitrary ray

    Parameters
    ----------
    pts : npt.NDArray[np.float_]
        The points to project, shape (3, N) where N is the number of
        points.
    ray_orgin : npt.NDArray[np.float_]
        The 3D ray origin
    ray_unit_dir : npt.NDArray[np.float_]
        The ray direction vector, already a unit normal vector

    Returns
    -------
    npt.NDArray[np.float_]
        the scalar distance of each point from the ray origin, of
        shape (N,) where N is the number of points
    """
    if pts.ndim > 2:
        raise ValueError(
            f"pts must be at most a 2D array of shape (N, 3), found {pts.shape}"
        )

    if pts.ndim == 2:
        assert pts.shape[1] == 3
        npts = pts.shape[0]
    else:
        assert pts.size == 3
        npts = 1

    vec = pts - ray_orgin
    assert vec.shape == pts.shape

    if pts.ndim == 1:
        t_vals = np.dot(vec, ray_unit_dir)
    else:
        t_vals = np.inner(vec, ray_unit_dir)

    if pts.ndim > 1:
        assert t_vals.shape == (npts,)

    return t_vals


def sort_points_along_ray(
    pts: npt.NDArray[np.float_],
    ray_orgin: npt.NDArray[np.float_],
    ray_unit_dir: npt.NDArray[np.float_],
    back_to_front: bool = True,
) -> List[int]:
    """Project and sort an array of 3D locations along a given ray

    Parameters
    ----------
    pts : npt.NDArray[np.float_]
        The points to project, shape (3, N) where N is the number of
        points.
    ray_orgin : npt.NDArray[np.float_]
        The 3D ray origin
    ray_unit_dir : npt.NDArray[np.float_]
        The ray direction vector, already a unit normal vector
    back_to_front : bool
        If True (default), then points are sorted in reverse order


    Returns
    -------
    List[int]
        the indices of the pts array sorted by the distance along
        the provided ray.
    """

    # project centers onto a ray
    t_vals = dist_along_ray(pts, ray_orgin, ray_unit_dir)
    sorted_indices = np.argsort(t_vals).tolist()
    if back_to_front:
        sorted_indices.reverse()
    return sorted_indices
