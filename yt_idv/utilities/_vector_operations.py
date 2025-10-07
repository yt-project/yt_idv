import numpy as np
import numpy.typing as npt

# def dist_along_line(pts: npt.NDArray[], line_orgin: npt.NDArray)


def sort_centers(centers, ray_origin, ray_unit_direction, back_to_front=True):

    # project centers onto a line
    vec = centers - ray_origin
    t_vals = np.dot(vec, ray_unit_direction)
    sorted_indices = np.argsort(t_vals).tolist()
    if back_to_front:
        sorted_indices.reverse
    return sorted_indices
