cimport cython

import numpy as np

cimport numpy as np
from libc.math cimport acos, atan2, cos, sin, sqrt
from numpy.math cimport INFINITY as NPY_INF, PI as NPY_PI


@cython.cdivision(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cdef (np.float64_t, np.float64_t, np.float64_t) _spherical_to_cartesian(np.float64_t r,
                           np.float64_t theta,
                           np.float64_t phi) noexcept nogil:
        # transform a single point in spherical coords to cartesian
        # r : radius
        # theta: colatitude
        # phi: azimuthal (longitudinal) angle
        cdef np.float64_t x, y, xy, z

        if r == 0.0:
            return 0.0, 0.0, 0.0

        xy = r * sin(theta)
        x = xy * cos(phi)
        y = xy * sin(phi)
        z = r * cos(theta)
        return x, y, z


@cython.cdivision(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cdef (np.float64_t, np.float64_t, np.float64_t) _cartesian_to_spherical(np.float64_t x,
                           np.float64_t y,
                           np.float64_t z) noexcept nogil:
        # transform a single point in cartesian coords to spherical, returns
        # r : radius
        # theta: colatitude
        # phi: azimuthal angle in range (0, 2pi)
        cdef np.float64_t r, theta, phi
        r = sqrt(x*x + y*y + z*z)
        theta = acos(z / r)
        phi = atan2(y, x)
        # atan2 returns -pi to pi, adjust to (0, 2pi)
        if phi < 0:
            phi = phi + 2 * NPY_PI
        return r, theta, phi


@cython.cdivision(True)
@cython.boundscheck(False)
@cython.wraparound(False)
def cartesian_to_spherical(np.ndarray x,
                           np.ndarray y,
                           np.ndarray z):
        # transform an array of points in cartesian coords to spherical, returns
        # r : radius
        # theta: colatitude
        # phi: azimuthal angle in range (0, 2pi)
        cdef np.ndarray[np.float64_t, ndim=1] r1d, th1d, phi1d
        cdef np.ndarray[np.float64_t, ndim=1] x1d, y1d, z1d
        cdef int i, n_x, ndim
        cdef np.int64_t[:] shp

        ndim = x.ndim

        shp = np.zeros((ndim,), dtype=np.int64)
        for i in range(ndim):
            shp[i] = x.shape[i]

        x1d = x.reshape(-1)
        y1d = y.reshape(-1)
        z1d = z.reshape(-1)

        n_x = x1d.size
        r1d = np.zeros((n_x,), dtype=np.float64)
        th1d = np.zeros((n_x,), dtype=np.float64)
        phi1d = np.zeros((n_x,), dtype=np.float64)


        with nogil:
            for i in range(n_x):
                r1d[i], th1d[i], phi1d[i] = _cartesian_to_spherical(x1d[i], y1d[i], z1d[i])

        r = r1d.reshape(shp)
        theta = th1d.reshape(shp)
        phi = phi1d.reshape(shp)
        return r, theta, phi


@cython.cdivision(True)
@cython.boundscheck(False)
@cython.wraparound(False)
def spherical_to_cartesian(np.ndarray r,
                           np.ndarray theta,
                           np.ndarray phi):

        # transform an array of points in spherical coords to cartesian
        cdef np.ndarray[np.float64_t, ndim=1] r1d, th1d, phi1d
        cdef np.ndarray[np.float64_t, ndim=1] x1d, y1d, z1d

        cdef np.int64_t[:] shp
        cdef int i, n_r, ndim

        ndim = r.ndim

        shp = np.zeros((ndim,), dtype=np.int64)
        for i in range(ndim):
            shp[i] = r.shape[i]

        r1d = r.reshape(-1)
        th1d = theta.reshape(-1)
        phi1d = phi.reshape(-1)

        n_r = r1d.size
        x1d = np.zeros((n_r,), dtype=np.float64)
        y1d = np.zeros((n_r,), dtype=np.float64)
        z1d = np.zeros((n_r,), dtype=np.float64)


        with nogil:
            for i in range(n_r):
                x1d[i], y1d[i], z1d[i] = _spherical_to_cartesian(r1d[i], th1d[i], phi1d[i])

        x = x1d.reshape(shp)
        y = y1d.reshape(shp)
        z = z1d.reshape(shp)
        return x, y, z


cdef void _reduce_2_bboxes(np.float64_t[3] xyz_0,
                           np.float64_t[3] dxyz_0,
                           np.float64_t[3] xyz_1,
                           np.float64_t[3] dxyz_1,
                           np.float64_t[3] xyz,
                           np.float64_t[3] dxyz) noexcept nogil:

    # find the effective bounding box given 2 others
    cdef np.float64_t le_i, re_i
    cdef int idim
    cdef int ndim = 3

    for idim in range(ndim):
        le_i = fmin(xyz_0[idim] - dxyz_0[idim]/2.,
                    xyz_1[idim] - dxyz_1[idim]/2.)
        re_i = fmax(xyz_0[idim] + dxyz_0[idim]/2.,
                    xyz_1[idim] + dxyz_1[idim]/2.)
        xyz[idim] = (le_i + re_i)/2.
        dxyz[idim] = re_i - le_i


cdef class MixedCoordBBox:
    # abstract class for calculating cartesian bounding boxes
    # from non-cartesian grid elements.
    cdef int get_cartesian_bbox(self,
                                np.float64_t pos0,
                                np.float64_t pos1,
                                np.float64_t pos2,
                                np.float64_t dpos0,
                                np.float64_t dpos1,
                                np.float64_t dpos2,
                                np.float64_t xyz_i[3],
                                np.float64_t dxyz_i[3]
                                ) noexcept nogil:
        pass


cdef class SphericalMixedCoordBBox(MixedCoordBBox):
    # Cartesian bounding boxes of spherical grid elements
    cdef int get_cartesian_bbox(self,
                        np.float64_t pos0,  # r
                        np.float64_t pos1,  # theta
                        np.float64_t pos2,  # phi
                        np.float64_t dpos0, # r
                        np.float64_t dpos1, # theta
                        np.float64_t dpos2, # phi
                        np.float64_t[3] xyz_i,
                        np.float64_t[3] dxyz_i,
                        ) noexcept nogil:
        """
        Calculate the cartesian bounding box for a single spherical volume element.

        Parameters
        ----------
        pos0: float
            radius value at element center
        pos1: float
            co-latitude angle value at element center, in range (0, pi) (theta in yt)
        pos2: float
            azimuthal angle value at element center, in range (0, 2pi) (phi in yt)
        dpos0: float
            radial width of element
        dpos1: float
            co-latitude angular width of element
        pos2: float
            azimuthal anglular width of element
        xyz_i:
            3-element array to store the center of the resulting bounding box
        dxyz_i:
            3-element array to store the width of the resulting bounding box

        Returns
        -------
        int
            error code: 0 for success, 1 if something went wrong...

        Note: this function is recursive! If either angular width is above a cutoff (of
        0.2 radians or about 11 degrees), the element will be recursively divided.
        """

        cdef np.float64_t max_angle = 0.2  # about 11 degrees, if smaller, will subsample
        cdef np.float64_t dpos2_2, dpos1_2  # half-widths
        cdef np.float64_t pos2_2, pos1_2  # centers of half elements
        cdef np.float64_t[3] xyz_0, dxyz_0  # additional 1st sample point if needed
        cdef np.float64_t[3] xyz_1, dxyz_1  # additional 2nd sample point if needed

        if dpos1 < max_angle and dpos2 < max_angle:
            self._get_cartesian_bbox(
                            pos0, pos1,pos2,
                            dpos0, dpos1, dpos2,
                            xyz_i, dxyz_i
                            )
        elif dpos1 >= max_angle:
            # split into two, recursively get bbox, then get min/max of
            # the bboxes

            # first sample
            dpos1_2 = dpos1 / 2.0
            pos1_2 = pos1 - dpos1_2 / 2.
            self.get_cartesian_bbox(
                pos0, pos1_2, pos2, dpos0, dpos1_2, dpos2, xyz_0, dxyz_0
            )

            # second sample
            pos1_2 = pos1 + dpos1_2 / 2.
            self.get_cartesian_bbox(
                pos0, pos1_2, pos2, dpos0, dpos1_2, dpos2, xyz_1, dxyz_1
            )

            _reduce_2_bboxes(xyz_0, dxyz_0, xyz_1, dxyz_1, xyz_i, dxyz_i)

        elif dpos2 >= max_angle:
            # first sample
            dpos2_2 = dpos2 / 2.0
            pos2_2 = pos2 - dpos2_2 / 2.
            self.get_cartesian_bbox(
                pos0, pos1, pos2_2, dpos0, dpos1, dpos2_2, xyz_0, dxyz_0
            )

            # second sample
            pos2_2 = pos2 + dpos2_2 / 2.
            self.get_cartesian_bbox(
                pos0, pos1, pos2_2, dpos0, dpos1, dpos2_2, xyz_1, dxyz_1
            )

            _reduce_2_bboxes(xyz_0, dxyz_0, xyz_1, dxyz_1, xyz_i, dxyz_i)
        else:
            # this should be unreachable. Do not need to check for the case where
            # both dpos2 and dpos1 > max angle because of the recursive call!
            return 1
        return 0


    cdef void _get_cartesian_bbox(self,
                        np.float64_t pos0,
                        np.float64_t pos1,
                        np.float64_t pos2,
                        np.float64_t dpos0,
                        np.float64_t dpos1,
                        np.float64_t dpos2,
                        np.float64_t[3] xyz_i,
                        np.float64_t[3] dxyz_i
                        ) noexcept nogil:

        cdef np.float64_t r_i, theta_i, phi_i, dr_i, dtheta_i, dphi_i
        cdef np.float64_t h_dphi, h_dtheta, h_dr, r_r
        cdef np.float64_t xi, yi, zi, r_lr, theta_lr, phi_lr, phi_lr2, theta_lr2
        cdef np.float64_t xli, yli, zli, xri, yri, zri, r_xy, r_xy2
        cdef int isign_r, isign_ph, isign_th
        cdef np.float64_t sign_r, sign_th, sign_ph

        cdef np.float64_t NPY_PI_2 = NPY_PI / 2.0
        cdef np.float64_t NPY_PI_3_2 = 3. * NPY_PI / 2.0
        cdef np.float64_t NPY_2xPI = 2. * NPY_PI

        r_i = pos0
        theta_i = pos1
        phi_i = pos2
        dr_i = dpos0
        dtheta_i = dpos1
        dphi_i = dpos2

        # initialize the left/right values
        xli = NPY_INF
        yli = NPY_INF
        zli = NPY_INF
        xri = -1.0 * NPY_INF
        yri = -1.0 * NPY_INF
        zri = -1.0 * NPY_INF

        # find the min/max bounds over the 8 corners of the
        # spherical volume element.
        h_dphi =  dphi_i / 2.0
        h_dtheta =  dtheta_i / 2.0
        h_dr =  dr_i / 2.0
        for isign_r in range(2):
            for isign_ph in range(2):
                for isign_th in range(2):
                    sign_r = 1.0 - 2.0 * <float> isign_r
                    sign_th = 1.0 - 2.0 * <float> isign_th
                    sign_ph = 1.0 - 2.0 * <float> isign_ph
                    r_lr = r_i + sign_r * h_dr
                    theta_lr = theta_i + sign_th * h_dtheta
                    phi_lr = phi_i + sign_ph * h_dphi

                    xi, yi, zi = _spherical_to_cartesian(r_lr, theta_lr, phi_lr)

                    xli = fmin(xli, xi)
                    yli = fmin(yli, yi)
                    zli = fmin(zli, zi)
                    xri = fmax(xri, xi)
                    yri = fmax(yri, yi)
                    zri = fmax(zri, zi)

        # need to correct for special cases:
        # if polar angle, phi, spans pi/2, pi or 3pi/2 then just
        # taking the min/max of the corners will miss the cusp of the
        # element. When this condition is met, the x/y min/max will
        # equal +/- the projection of the max r in the xy plane -- in this case,
        # the theta angle that gives the max projection of r in
        # the x-y plane will change depending on the whether theta < or > pi/2,
        # so the following calculates for the min/max theta value of the element
        # and takes the max.
        # ALSO note, that the following does check for when an edge aligns with the
        # phi=0/2pi, it does not handle an element spanning the periodic boundary.
        # Oh and this may break down for large elements that span whole
        # quadrants...
        phi_lr =  phi_i - h_dphi
        phi_lr2 = phi_i + h_dphi
        theta_lr = theta_i - h_dtheta
        theta_lr2 = theta_i + h_dtheta
        r_r = r_i + h_dr
        if theta_lr < NPY_PI_2 and theta_lr2 > NPY_PI_2:
            r_xy = r_r
        else:
            r_xy = r_r * sin(theta_lr)
            r_xy2 = r_r * sin(theta_lr2)
            r_xy = fmax(r_xy, r_xy2)

        if phi_lr == 0.0 or phi_lr2 == NPY_2xPI:
            # need to re-check this, for when theta spans equator
            xri = r_xy
        elif phi_lr < NPY_PI_2 and phi_lr2  > NPY_PI_2:
            yri = r_xy
        elif phi_lr < NPY_PI and phi_lr2  > NPY_PI:
            xli = -r_xy
        elif phi_lr < NPY_PI_3_2 and phi_lr2  > NPY_PI_3_2:
            yli = -r_xy

        xyz_i[0] = (xri+xli)/2.
        xyz_i[1] = (yri+yli)/2.
        xyz_i[2] = (zri+zli)/2.
        dxyz_i[0] = xri-xli
        dxyz_i[1] = yri-yli
        dxyz_i[2] = zri-zli


@cython.cdivision(True)
@cython.boundscheck(False)
@cython.wraparound(False)
def cartesian_bboxes(MixedCoordBBox bbox_handler,
                      np.float64_t[:] pos0,
                      np.float64_t[:] pos1,
                      np.float64_t[:] pos2,
                      np.float64_t[:] dpos0,
                      np.float64_t[:] dpos1,
                      np.float64_t[:] dpos2,
                                      ):
    """
    Calculate the cartesian bounding boxes around non-cartesian volume elements

    Parameters
    ----------
    bbox_handler
        a MixedCoordBBox child instance
    pos0, pos1, pos2
        native coordinates of element centers
    dpos0, dpos1, dpos2
        element widths in native coordinates

    Returns
    -------
    x_y_z
        a 3-element tuples containing the cartesian bounding box centers
    dx_y_z
        a 3-element tuples containing the cartesian bounding box widths

    """

    cdef int i, n_pos, i_result
    cdef np.float64_t[3] xyz_i
    cdef np.float64_t[3] dxyz_i
    cdef int failure = 0
    cdef np.float64_t[:] x, y, z  # bbox centers
    cdef np.float64_t[:] dx, dy, dz  # bbox full widths

    n_pos = pos0.size
    x = np.empty_like(pos0)
    y = np.empty_like(pos0)
    z = np.empty_like(pos0)
    dx = np.empty_like(pos0)
    dy = np.empty_like(pos0)
    dz = np.empty_like(pos0)

    with nogil:
        for i in range(n_pos):

            i_result = bbox_handler.get_cartesian_bbox(pos0[i],
                                                    pos1[i],
                                                    pos2[i],
                                                    dpos0[i],
                                                    dpos1[i],
                                                    dpos2[i],
                                                    xyz_i,
                                                    dxyz_i)
            failure += i_result

            x[i] = xyz_i[0]
            y[i] = xyz_i[1]
            z[i] = xyz_i[2]
            dx[i] = dxyz_i[0]
            dy[i] = dxyz_i[1]
            dz[i] = dxyz_i[2]

    if failure > 0:
        raise RuntimeError("Unexpected error in get_cartesian_bbox.")

    x_y_z = (np.asarray(x), np.asarray(y), np.asarray(z))
    dx_y_z = (np.asarray(dx), np.asarray(dy), np.asarray(dz))
    return x_y_z, dx_y_z


@cython.cdivision(True)
@cython.boundscheck(False)
@cython.wraparound(False)
def cartesian_bboxes_edges(MixedCoordBBox bbox_handler,
                            np.float64_t[:] le0,
                            np.float64_t[:] le1,
                            np.float64_t[:] le2,
                            np.float64_t[:] re0,
                            np.float64_t[:] re1,
                            np.float64_t[:] re2,
                                      ):
    """
    Calculate the cartesian bounding boxes around non-cartesian volume elements

    Same as cartesian_bboxes, but supplying and returning element left/right edges.

    Parameters
    ----------
    bbox_handler
        a MixedCoordBBox child instance
    le0, le1, le2
        native coordinates of element left edges
    re0, re1, re2
        native coordinates of element right edges

    Returns
    -------
    xyz_le
        a 3-element tuples containing the cartesian bounding box left edges
    xyz_re
        a 3-element tuples containing the cartesian bounding box right edges

    """
    cdef int i, n_pos, i_result
    cdef np.float64_t[3] xyz_i
    cdef np.float64_t[3] dxyz_i
    cdef np.float64_t pos0, pos1, pos2, dpos0, dpos1, dpos2
    cdef int failure = 0
    cdef np.float64_t[:] x_le, y_le, z_le  # bbox left edges
    cdef np.float64_t[:] x_re, y_re, z_re  # bbox right edges

    n_pos = le0.size
    x_le = np.empty_like(le0)
    y_le = np.empty_like(le0)
    z_le = np.empty_like(le0)
    x_re = np.empty_like(le0)
    y_re = np.empty_like(le0)
    z_re = np.empty_like(le0)

    with nogil:
        for i in range(n_pos):
            pos0 = (le0[i] + re0[i]) / 2.
            pos1 = (le1[i] + re1[i]) / 2.
            pos2 = (le2[i] + re2[i]) / 2.
            dpos0 = re0[i] - le0[i]
            dpos1 = re1[i] - le1[i]
            dpos2 = re2[i] - le2[i]
            i_result = bbox_handler.get_cartesian_bbox(pos0,
                                                    pos1,
                                                    pos2,
                                                    dpos0,
                                                    dpos1,
                                                    dpos2,
                                                    xyz_i,
                                                    dxyz_i)
            failure += i_result

            x_le[i] = xyz_i[0] - dxyz_i[0] / 2.
            x_re[i] = xyz_i[0] + dxyz_i[0] / 2.
            y_le[i] = xyz_i[1] - dxyz_i[1] / 2.
            y_re[i] = xyz_i[1] + dxyz_i[1] / 2.
            z_le[i] = xyz_i[2] - dxyz_i[2] / 2.
            z_re[i] = xyz_i[2] + dxyz_i[2] / 2.


    if failure > 0:
        raise RuntimeError("Unexpected error in get_cartesian_bbox.")

    xyz_le = (np.asarray(x_le), np.asarray(y_le), np.asarray(z_le))
    xyz_re = (np.asarray(x_re), np.asarray(y_re), np.asarray(z_re))

    return xyz_le, xyz_re
