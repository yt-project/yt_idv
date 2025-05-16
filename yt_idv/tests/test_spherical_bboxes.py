import numpy as np
import pytest

from yt_idv.coordinate_utilities import (
    SphericalMixedCoordBBox,
    cartesian_bboxes,
    cartesian_bboxes_edges,
    cartesian_to_spherical,
    spherical_to_cartesian,
)


def test_cartesian_bboxes_for_spherical():

    # this test checks the special cases where
    # a spherical volume element crosses an axis
    # or when an element edge is lined up with an axis

    # check element that includes theta=0 as an edge
    r = np.array([0.95])
    dr = np.array([0.1])
    theta = np.array([0.05])
    dtheta = np.array([0.1])
    phi = np.array([0.05])
    dphi = np.array([0.05])

    bbox_handler = SphericalMixedCoordBBox()

    xyz, dxyz = cartesian_bboxes(bbox_handler, r, theta, phi, dr, dtheta, dphi)
    assert xyz[2] + dxyz[2] / 2 == 1.0
    assert np.allclose(xyz[0] - dxyz[0] / 2, 0.0)
    assert np.allclose(xyz[1] - dxyz[1] / 2, 0.0)

    # now theta = np.pi
    theta = np.array([np.pi - dtheta[0] / 2])
    xyz, dxyz = cartesian_bboxes(bbox_handler, r, theta, phi, dr, dtheta, dphi)
    assert xyz[2] - dxyz[2] / 2 == -1.0
    assert np.allclose(xyz[0] - dxyz[0] / 2, 0.0)
    assert np.allclose(xyz[1] - dxyz[1] / 2, 0.0)

    # element at equator, overlapping the +y axis
    theta = np.array([np.pi / 2])
    phi = np.array([np.pi / 2])
    xyz, dxyz = cartesian_bboxes(bbox_handler, r, theta, phi, dr, dtheta, dphi)

    assert xyz[1] + dxyz[1] / 2 == 1.0
    assert np.allclose(xyz[0], 0.0)
    assert np.allclose(xyz[2], 0.0)

    # element at equator, overlapping the -x axis
    phi = np.array([np.pi])
    xyz, dxyz = cartesian_bboxes(bbox_handler, r, theta, phi, dr, dtheta, dphi)

    assert xyz[0] - dxyz[0] / 2 == -1.0
    assert np.allclose(xyz[1], 0.0)
    assert np.allclose(xyz[2], 0.0)

    # element at equator, overlapping the -y axis
    phi = np.array([3 * np.pi / 2])
    xyz, dxyz = cartesian_bboxes(bbox_handler, r, theta, phi, dr, dtheta, dphi)

    assert xyz[1] - dxyz[1] / 2 == -1.0
    assert np.allclose(xyz[0], 0.0)
    assert np.allclose(xyz[2], 0.0)

    # element at equator, overlapping +x axis
    phi = dphi / 2.0
    xyz, dxyz = cartesian_bboxes(bbox_handler, r, theta, phi, dr, dtheta, dphi)
    assert xyz[0] + dxyz[0] / 2 == 1.0

    # element with edge on +x axis in -theta direction
    theta = np.pi / 2 - dtheta / 2
    xyz, dxyz = cartesian_bboxes(bbox_handler, r, theta, phi, dr, dtheta, dphi)
    assert xyz[0] + dxyz[0] / 2 == 1.0

    # element with edge on +x axis in +theta direction
    theta = np.pi / 2 + dtheta / 2
    xyz, dxyz = cartesian_bboxes(bbox_handler, r, theta, phi, dr, dtheta, dphi)
    assert xyz[0] + dxyz[0] / 2 == 1.0

    # finally, check that things work OK with a wide range of
    # angles

    r_edges = np.linspace(0.4, 1.0, 10, dtype="float64")
    theta_edges = np.linspace(0, np.pi, 10, dtype="float64")
    phi_edges = np.linspace(0.0, 2 * np.pi, 10, dtype="float64")

    r = (r_edges[0:-1] + r_edges[1:]) / 2.0
    theta = (theta_edges[0:-1] + theta_edges[1:]) / 2.0
    phi = (phi_edges[0:-1] + phi_edges[1:]) / 2.0

    dr = r_edges[1:] - r_edges[:-1]
    dtheta = theta_edges[1:] - theta_edges[:-1]
    dphi = phi_edges[1:] - phi_edges[:-1]

    r_th_ph = np.meshgrid(r, theta, phi)
    d_r_th_ph = np.meshgrid(dr, dtheta, dphi)
    r_th_ph = [r_th_ph[i].ravel() for i in range(3)]
    d_r_th_ph = [d_r_th_ph[i].ravel() for i in range(3)]

    x_y_z, d_x_y_z = cartesian_bboxes(
        bbox_handler,
        r_th_ph[0],
        r_th_ph[1],
        r_th_ph[2],
        d_r_th_ph[0],
        d_r_th_ph[1],
        d_r_th_ph[2],
    )

    assert np.all(np.isfinite(x_y_z))
    assert np.all(np.isfinite(d_x_y_z))

    # and check the extents again for completeness...
    for i in range(3):
        max_val = np.max(x_y_z[i] + d_x_y_z[i] / 2.0)
        min_val = np.min(x_y_z[i] - d_x_y_z[i] / 2.0)
        assert max_val == 1.0
        assert min_val == -1.0


def test_spherical_cartesian_roundtrip():
    xyz = [np.linspace(0, 1, 10) for _ in range(3)]
    xyz = np.meshgrid(*xyz)
    xyz = [xyzi.ravel() for xyzi in xyz]
    x, y, z = xyz

    r, theta, phi = cartesian_to_spherical(x, y, z)
    x_out, y_out, z_out = spherical_to_cartesian(r, theta, phi)

    assert np.allclose(x_out, x)
    assert np.allclose(y_out, y)
    assert np.allclose(z_out, z)
    assert np.max(r) == np.sqrt(3.0)


@pytest.mark.parametrize("n_angles", (2, 4, 8, 16))
def test_large_elements(n_angles):

    bbox_handler = SphericalMixedCoordBBox()

    r_edges = np.linspace(0.4, 1.0, 10, dtype="float64")
    theta_edges = np.linspace(0, np.pi, n_angles, dtype="float64")
    phi_edges = np.linspace(0.0, 2 * np.pi, n_angles, dtype="float64")

    r = (r_edges[0:-1] + r_edges[1:]) / 2.0
    theta = (theta_edges[0:-1] + theta_edges[1:]) / 2.0
    phi = (phi_edges[0:-1] + phi_edges[1:]) / 2.0

    dr = r_edges[1:] - r_edges[:-1]
    dtheta = theta_edges[1:] - theta_edges[:-1]
    dphi = phi_edges[1:] - phi_edges[:-1]

    r_th_ph = np.meshgrid(r, theta, phi)
    d_r_th_ph = np.meshgrid(dr, dtheta, dphi)
    r_th_ph = [r_th_ph[i].ravel() for i in range(3)]
    d_r_th_ph = [d_r_th_ph[i].ravel() for i in range(3)]

    x_y_z, d_x_y_z = cartesian_bboxes(
        bbox_handler,
        r_th_ph[0],
        r_th_ph[1],
        r_th_ph[2],
        d_r_th_ph[0],
        d_r_th_ph[1],
        d_r_th_ph[2],
    )

    x_y_z = np.column_stack(x_y_z)
    d_x_y_z = np.column_stack(d_x_y_z)

    assert np.all(np.isfinite(x_y_z))
    assert np.all(np.isfinite(d_x_y_z))

    le = np.min(x_y_z - d_x_y_z / 2.0, axis=0)
    re = np.max(x_y_z + d_x_y_z / 2.0, axis=0)

    assert np.all(le == -1.0)
    assert np.all(re == 1.0)


def test_spherical_boxes_edges():
    # check that you get the same result from supplying centers
    # vs edges.

    bbox_handler = SphericalMixedCoordBBox()

    r_edges = np.linspace(0.0, 10.0, 20, dtype="float64")
    theta_edges = np.linspace(0, np.pi, 20, dtype="float64")
    phi_edges = np.linspace(0.0, 2 * np.pi, 20, dtype="float64")

    r = (r_edges[0:-1] + r_edges[1:]) / 2.0
    theta = (theta_edges[0:-1] + theta_edges[1:]) / 2.0
    phi = (phi_edges[0:-1] + phi_edges[1:]) / 2.0

    dr = r_edges[1:] - r_edges[:-1]
    dtheta = theta_edges[1:] - theta_edges[:-1]
    dphi = phi_edges[1:] - phi_edges[:-1]

    r_th_ph = np.meshgrid(r, theta, phi)
    d_r_th_ph = np.meshgrid(dr, dtheta, dphi)
    r_th_ph = [r_th_ph[i].ravel() for i in range(3)]
    d_r_th_ph = [d_r_th_ph[i].ravel() for i in range(3)]

    x_y_z, d_x_y_z = cartesian_bboxes(
        bbox_handler,
        r_th_ph[0],
        r_th_ph[1],
        r_th_ph[2],
        d_r_th_ph[0],
        d_r_th_ph[1],
        d_r_th_ph[2],
    )
    x_y_z = np.column_stack(x_y_z)
    d_x_y_z = np.column_stack(d_x_y_z)

    le = [r_th_ph[i] - d_r_th_ph[i] / 2.0 for i in range(3)]
    re = [r_th_ph[i] + d_r_th_ph[i] / 2.0 for i in range(3)]
    xyz_le, xyz_re = cartesian_bboxes_edges(
        bbox_handler,
        le[0],
        le[1],
        le[2],
        re[0],
        re[1],
        re[2],
    )
    xyz_le = np.column_stack(xyz_le)
    xyz_re = np.column_stack(xyz_re)

    centers = (xyz_le + xyz_re) / 2.0
    widths = xyz_re - xyz_le

    assert np.allclose(centers, x_y_z)
    assert np.allclose(widths, d_x_y_z)
