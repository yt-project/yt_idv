"""Containers and helpers for extracting data values from a rendered scene."""

from dataclasses import dataclass
from typing import Optional

import numpy as np
from unyt import unyt_array, unyt_quantity


@dataclass(eq=False)
class RenderedImagePlane:
    """
    A rendered image in data values rather than colors.

    Attributes
    ----------
    data : unyt_array
        The (ny, nx) image in physical units. Element ``[j, i]`` is the pixel at
        row ``j`` (increasing along ``up``) and column ``i`` (increasing along
        ``right``), i.e. the array is oriented for
        ``imshow(plane.data, origin="lower", extent=plane.extent)``.
    extent : unyt_array
        ``(xmin, xmax, ymin, ymax)`` of the image plane, measured from ``center``
        along the camera's right and up vectors.
    center : unyt_array
        The world-space position that the image is centered on (the camera focus).
    right, up : np.ndarray
        Unit vectors spanning the image plane, in the internal (rendering)
        coordinate system.
    path_length : unyt_array or None
        For integrating render methods, the (ny, nx) distance each pixel's ray
        traveled through the data. ``None`` for non-integrating methods.
    """

    data: unyt_array
    extent: unyt_array
    center: unyt_array
    right: np.ndarray
    up: np.ndarray
    path_length: Optional[unyt_array] = None

    @property
    def width(self) -> unyt_quantity:
        """The physical width of the image plane."""
        return self.extent[1] - self.extent[0]

    @property
    def height(self) -> unyt_quantity:
        """The physical height of the image plane."""
        return self.extent[3] - self.extent[2]

    @property
    def dimensions(self) -> tuple:
        """The physical ``(width, height)`` of the image plane."""
        return (self.width, self.height)

    @property
    def pixel_size(self) -> tuple:
        """The physical ``(dx, dy)`` of a single pixel."""
        ny, nx = self.data.shape
        return (self.width / nx, self.height / ny)

    def integrate(self) -> unyt_quantity:
        """
        Integrate the image over the plane, treating pixels as rectangles.

        Pixels that no ray sampled (NaN) are skipped rather than treated as
        zeros, so the result is the integral over the rendered data alone.

        Returns
        -------
        unyt_quantity
            The integral, in the units of ``data`` times an area.
        """
        dx, dy = self.pixel_size
        return np.nansum(self.data) * dx * dy

    def __repr__(self):
        ny, nx = self.data.shape
        return (
            f"RenderedImagePlane({nx} x {ny} pixels, "
            f"{self.width} x {self.height}, units={self.data.units})"
        )


def image_plane_extent(projection_matrix, view_matrix, focus):
    """
    The extent of the viewport in the plane that contains the camera focus.

    Because the camera uses a perspective projection, the region of space that
    the image covers depends on distance from the camera: this returns the
    extent in the plane through ``focus`` that is normal to the view direction.

    Parameters
    ----------
    projection_matrix, view_matrix : (4, 4) arrays
        The camera matrices, in the same row-major convention used when they are
        handed to the shaders (``clip = projection @ view @ position``).
    focus : (3,) array
        The camera focus, in the internal (rendering) coordinate system.

    Returns
    -------
    extent : (4,) np.ndarray
        ``(xmin, xmax, ymin, ymax)`` relative to ``focus``, along the camera
        right and up vectors.
    right, up : (3,) np.ndarray
        The camera right and up unit vectors.
    """
    view_matrix = np.asarray(view_matrix, dtype="f8")
    pmv = np.asarray(projection_matrix, dtype="f8") @ view_matrix
    inv_pmv = np.linalg.inv(pmv)
    focus = np.asarray(focus, dtype="f8")

    # every point in the plane normal to the view direction through the focus
    # shares the focus values of the clip-space w and z, so the plane's corners
    # can be found by un-projecting the corners of the normalized device cube at
    # those values.
    clip = pmv @ np.append(focus, 1.0)
    w, z = clip[3], clip[2]

    corners = []
    for ndc_x in (-1.0, 1.0):
        for ndc_y in (-1.0, 1.0):
            corner = inv_pmv @ np.array([ndc_x * w, ndc_y * w, z, w])
            corners.append(corner[:3] / corner[3] - focus)
    corners = np.array(corners)

    # rows 0 and 1 of the look-at matrix are the camera right and up vectors
    right = view_matrix[0, :3]
    up = view_matrix[1, :3]

    x = corners @ right
    y = corners @ up
    extent = np.array([x.min(), x.max(), y.min(), y.max()])
    return extent, right, up
