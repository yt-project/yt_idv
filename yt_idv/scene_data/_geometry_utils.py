import numpy as np


def phi_normal_planes(edge_coordinates, axis_id, cast_type: str = None):
    # for spherical geometries, calculates the cartesian normals and constants
    # defining the planes normal to a fixed-phi value. The phi normal plane for
    # a given spherical coordinate (r, theta, phi) will contain the given
    # coordinate and the z-axis.
    #
    # edge_coordinates: 3D array of shape (N, 3) containing the spherical
    #                   coordinates for which we want the phi-normal.
    # axis_id: dictionary that maps the spherical coordinate axis names to the
    #          index number.

    phi = edge_coordinates[:, axis_id["phi"]]
    theta = edge_coordinates[:, axis_id["theta"]]
    r = edge_coordinates[:, axis_id["r"]]

    # get the cartesian values of the coordinates
    z = r * np.cos(theta)
    r_xy = r * np.sin(theta)
    x = r_xy * np.cos(phi)
    y = r_xy * np.sin(phi)
    xyz = np.column_stack([x, y, z])

    # construct the planes
    z_hat = np.array([0, 0, 1])
    # cross product is vectorized, result is shape (N, 3):
    normal_vec = np.cross(xyz, z_hat)
    # dot product is not vectorized, do it manually via an elemntwise multiplication
    # then summation. result will have shape (N,)
    d = (normal_vec * xyz).sum(axis=1)  # manual dot product

    normals_d = np.column_stack([normal_vec, d])
    if cast_type is not None:
        normals_d = normals_d.astype(cast_type)
    return normals_d
