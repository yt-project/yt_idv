import numpy as np
cimport libc.math as math
cimport numpy as np

def update_orientation(np.ndarray[np.float64_t, ndim=1] q1,
                        np.float64_t start_x, np.float64_t start_y,
                        np.float64_t end_x, np.float64_t end_y):
    # This is a Cython implementation of the TrackballCamera implementation of:
    #  1. map_to_surface(start_x, start_y)
    #  2. map_to_surface(end_x, end_y)
    #  3. Constructing w, x, y, z
    #  4. Normalizing this quaternion
    #  5. Multiplying by the existing orientation quaternion

    cdef np.float64_t w, x, y, z, q2[4]
    cdef np.float64_t old_map[3], new_map[3], mag
    cdef np.float64_t start_z, end_z
    cdef np.float64_t mag_start = (start_x * start_x + start_y * start_y)
    cdef np.float64_t mag_end = (end_x * end_x + end_y * end_y)

    if mag_start > 1.0:
        mag_start = mag_start**0.5
        start_x /= mag_start
        start_y /= mag_start
        start_z = 0.0
    else:
        start_z = (1.0 - mag_start)**0.5
    old_map[0] = start_x
    old_map[1] = -start_y
    old_map[2] = start_z

    if mag_end > 1.0:
        mag_end = mag_end**0.5
        end_x /= mag_end
        end_y /= mag_end
        end_z = 0.0
    else:
        end_z = (1.0 - mag_end)**0.5
    new_map[0] = end_x
    new_map[1] = -end_y
    new_map[2] = end_z
    w = old_map[0] * new_map[0] + old_map[1] * new_map[1] + old_map[2] * new_map[2]
    x = old_map[1] * new_map[2] - old_map[2] * new_map[1]
    y = old_map[2] * new_map[0] - old_map[0] * new_map[2]
    z = old_map[0] * new_map[1] - old_map[1] * new_map[0]

    mag = (w*w + x*x + y*y + z*z)**0.5

    q2[0] = w/mag
    q2[1] = x/mag
    q2[2] = y/mag
    q2[3] = z/mag

    # Now we multiply our quaternion

    w = q1[0]*q2[0] - q1[1]*q2[1] - q1[2]*q2[2] - q1[3]*q2[3]
    x = q1[0]*q2[1] + q1[1]*q2[0] + q1[2]*q2[3] - q1[3]*q2[2]
    y = q1[0]*q2[2] + q1[2]*q2[0] + q1[3]*q2[1] - q1[1]*q2[3]
    z = q1[0]*q2[3] + q1[3]*q2[0] + q1[1]*q2[2] - q1[2]*q2[1]

    q2[0] = w
    q2[1] = x
    q2[2] = y
    q2[3] = z
    return np.asarray(<np.float64_t[:4]> q2).copy()
