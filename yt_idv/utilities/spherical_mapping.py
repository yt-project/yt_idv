import warnings
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from unyt import unyt_quantity

from yt_idv.utilities.coordinate_utilities import spherical_to_cartesian

_GEOGRAPHIC_GEOMETRIES = ("geographic", "internal_geographic")
_SPHERICAL_GEOMETRIES = ("spherical",) + _GEOGRAPHIC_GEOMETRIES

# a length as a float in code_length, a unyt quantity or a (value, unit) tuple
Length = unyt_quantity | float | tuple[float, str]


def render_geometry(ds) -> str:
    """
    The geometry used for rendering a yt dataset.

    Geographic datasets are rendered with the spherical machinery, so
    "geographic" and "internal_geographic" both map to "spherical".
    """
    geom = str(ds.geometry)
    if geom in _SPHERICAL_GEOMETRIES:
        return "spherical"
    return geom


def validate_reference_height(ds, reference_height: Length | None) -> None:
    geom = str(ds.geometry)
    if reference_height is not None and geom not in _GEOGRAPHIC_GEOMETRIES:
        raise ValueError(
            "reference_height only applies to geographic and internal_geographic "
            f"datasets, but the dataset geometry is {geom}."
        )


def _to_code_length(ds, value: Length) -> float:
    if isinstance(value, tuple):
        value = ds.quan(*value)
    if hasattr(value, "to"):
        return float(value.to("code_length").d)
    return float(value)


def _radial_offset(data_source, reference_height: Length | None) -> tuple[float, float]:
    # returns (offset, factor) in code_length such that the physical radius is
    # factor * native_radial_coordinate + offset
    ds = data_source.ds
    ds_offset, factor = ds.coordinates._retrieve_radial_offset(data_source)
    if reference_height is not None:
        return _to_code_length(ds, reference_height), float(factor)

    offset = _to_code_length(ds, ds_offset)
    if str(ds.geometry) == "geographic" and offset == 0.0:
        warnings.warn(
            "The surface_height of this geographic dataset is 0, so altitude "
            "values will be rendered as radii. Set reference_height to the "
            "radius of the altitude=0 surface to render a shell.",
            UserWarning,
            stacklevel=4,
        )
    return offset, float(factor)


@dataclass
class SphericalMapping:
    """
    Per-axis affine map from a dataset's native coordinates to the normalized
    spherical coordinates used by the shaders: radius divided by the maximum
    radius of the domain, co-latitude theta in (0, pi) and azimuth phi, both in
    radians.

    axis_id maps "r", "theta" and "phi" to the index of the native axis they
    are computed from. An axis with a negative scale (latitude, depth) runs in
    the opposite direction of its spherical counterpart.
    """

    axis_id: dict[str, int]
    scale: NDArray
    offset: NDArray
    phi_min: float
    max_r: unyt_quantity | float

    @classmethod
    def from_data_source(cls, data_source, reference_height: Length | None = None):
        ds = data_source.ds
        geom = str(ds.geometry)
        validate_reference_height(ds, reference_height)
        ax = ds.coordinates.axis_id
        scale = np.ones(3)
        offset = np.zeros(3)

        if geom == "spherical":
            axis_id = {name: ax[name] for name in ("r", "theta", "phi")}
            r_offset, r_factor = 0.0, 1.0
        elif geom in _GEOGRAPHIC_GEOMETRIES:
            axis_id = {
                "r": ax[ds.coordinates.radial_axis],
                "theta": ax["latitude"],
                "phi": ax["longitude"],
            }
            r_offset, r_factor = _radial_offset(data_source, reference_height)
            scale[axis_id["theta"]] = -np.pi / 180.0  # degrees to radians
            offset[axis_id["theta"]] = np.pi / 2.0  # latitude to co-latitude
            scale[axis_id["phi"]] = np.pi / 180.0  # degrees to radians
        else:
            raise NotImplementedError(
                f"No spherical mapping is available for {geom} geometries."
            )

        dle = np.asarray(ds.domain_left_edge.d, dtype="f8")
        dre = np.asarray(ds.domain_right_edge.d, dtype="f8")

        i_r = axis_id["r"]
        max_r = np.max(r_factor * np.array([dle[i_r], dre[i_r]]) + r_offset)
        if max_r <= 0.0:
            raise ValueError(
                f"The maximum radius of the domain must be positive, found {max_r}."
            )
        scale[i_r] = r_factor / max_r
        offset[i_r] = r_offset / max_r

        # phi values are wrapped into [phi_min, phi_min + 2pi) in the shaders.
        # placing the wrap in the middle of any gap in the domain's phi range
        # keeps it away from the data.
        i_phi = axis_id["phi"]
        phi_lo, phi_hi = np.sort(scale[i_phi] * np.array([dle[i_phi], dre[i_phi]]))
        phi_min = phi_lo - 0.5 * max(2.0 * np.pi - (phi_hi - phi_lo), 0.0)

        return cls(
            axis_id=axis_id,
            scale=scale,
            offset=offset,
            phi_min=float(phi_min),
            max_r=ds.quan(max_r, "code_length"),
        )

    @property
    def tex_axis_flip(self) -> NDArray:
        return (self.scale < 0).astype("f4")

    def edges(self, le: NDArray, re: NDArray) -> tuple[NDArray, NDArray]:
        """map native left/right edges (shape (..., 3)) to sorted spherical edges"""
        le_s = np.asarray(le, dtype="f8") * self.scale + self.offset
        re_s = np.asarray(re, dtype="f8") * self.scale + self.offset
        return np.minimum(le_s, re_s), np.maximum(le_s, re_s)

    def widths(self, dx: NDArray) -> NDArray:
        """map native widths (shape (..., 3)) to spherical widths"""
        return np.asarray(dx, dtype="f8") * np.abs(self.scale)

    def to_model_coords(self, points: NDArray, radius: Length | None = None) -> NDArray:
        """
        Map points in the dataset's native coordinates to the model coordinates
        the scene is rendered in: cartesian x, y, z with the maximum radius of
        the domain at 1. Use it to place annotations such as curves.

        Parameters
        ----------
        points : array of shape (N, 3) or (3,)
            Native coordinates in the dataset's axis order, e.g. (latitude,
            longitude, altitude) in degrees and code_length for a geographic
            dataset or (r, theta, phi) for a spherical one.
        radius : float, unyt quantity or (value, unit) tuple, optional
            If given, the physical radius at which to place every point, in
            place of their radial coordinate. A float is in code_length, like
            reference_height. The outer surface of the domain is at max_r.

        Returns
        -------
        array of shape (N, 3)
            x, y, z in model coordinates. One model unit is max_r, which
            BlockCollection.internal_length_unit also returns.
        """
        sph = np.atleast_2d(np.asarray(points, dtype="f8")) * self.scale + self.offset
        ax = self.axis_id
        r = sph[:, ax["r"]].copy()
        if radius is not None:
            r[:] = self._normalized_radius(radius)
        theta = sph[:, ax["theta"]].copy()
        phi = sph[:, ax["phi"]].copy()
        x, y, z = spherical_to_cartesian(r, theta, phi)
        return np.column_stack([x, y, z])

    def _normalized_radius(self, radius: Length) -> float:
        # a physical radius as a fraction of the maximum radius of the domain
        if isinstance(radius, tuple):
            radius = unyt_quantity(*radius)
        max_r = self.max_r
        if hasattr(radius, "to"):
            if not hasattr(max_r, "units"):
                raise ValueError(
                    "A radius with units needs the dataset's unit registry, "
                    "which is not available for a mapping loaded from a saved "
                    "scene. Pass the radius as a float in code_length instead."
                )
            radius = radius.to(max_r.units).d
        return float(radius) / float(getattr(max_r, "d", max_r))
