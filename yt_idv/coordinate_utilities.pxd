cimport numpy as np


cdef inline np.float64_t fmax(np.float64_t f0, np.float64_t f1) noexcept nogil:
    if f0 > f1: return f0
    return f1

cdef inline np.float64_t fmin(np.float64_t f0, np.float64_t f1) noexcept nogil:
    if f0 < f1: return f0
    return f1

cdef (np.float64_t, np.float64_t, np.float64_t) _spherical_to_cartesian(np.float64_t r,
                           np.float64_t theta,
                           np.float64_t phi) noexcept nogil


cdef (np.float64_t, np.float64_t, np.float64_t) _cartesian_to_spherical(np.float64_t x,
                           np.float64_t y,
                           np.float64_t z) noexcept nogil

cdef class MixedCoordBBox:
    cdef void get_cartesian_bbox(self,
                                np.float64_t pos0,
                                np.float64_t pos1,
                                np.float64_t pos2,
                                np.float64_t dpos0,
                                np.float64_t dpos1,
                                np.float64_t dpos2,
                                np.float64_t xyz_i[3],
                                np.float64_t dxyz_i[3]
                                ) noexcept nogil


cdef class SphericalMixedCoordBBox(MixedCoordBBox):
    cdef void get_cartesian_bbox(
                        self,
                        np.float64_t pos0,
                        np.float64_t pos1,
                        np.float64_t pos2,
                        np.float64_t dpos0,
                        np.float64_t dpos1,
                        np.float64_t dpos2,
                        np.float64_t xyz_i[3],
                        np.float64_t dxyz_i[3]
                        ) noexcept nogil

    cdef void _get_cartesian_bbox(
                    self,
                    np.float64_t pos0,
                    np.float64_t pos1,
                    np.float64_t pos2,
                    np.float64_t dpos0,
                    np.float64_t dpos1,
                    np.float64_t dpos2,
                    np.float64_t xyz_i[3],
                    np.float64_t dxyz_i[3]
                    ) noexcept nogil
