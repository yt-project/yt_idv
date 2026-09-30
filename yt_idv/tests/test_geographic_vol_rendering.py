import warnings

import numpy as np
import pytest
import yt

from yt_idv.utilities.coordinate_utilities import spherical_to_cartesian
from yt_idv.utilities.spherical_mapping import SphericalMapping

_LAT = (-30.0, 60.0)
_LON = (20.0, 200.0)
_SHAPE = (24, 20, 16)


def _geo_ds(geometry="geographic", lon=_LON, radial=(0.0, 0.5), data=None):
    if data is None:
        data = np.random.default_rng(0).random(_SHAPE)
    return yt.load_uniform_grid(
        {"density": data},
        data.shape,
        bbox=np.array([_LAT, lon, radial]),
        nprocs=4,
        geometry=geometry,
        length_unit="m",
    )


def _native_points(ds, n=50):
    rng = np.random.default_rng(1)
    dle = ds.domain_left_edge.d
    dre = ds.domain_right_edge.d
    return dle + rng.random((n, 3)) * (dre - dle)


def _mapped_cartesian(mapping, points):
    sph, _ = mapping.edges(points, points)
    ax = mapping.axis_id
    xyz = spherical_to_cartesian(
        sph[:, ax["r"]].copy(), sph[:, ax["theta"]].copy(), sph[:, ax["phi"]].copy()
    )
    return np.column_stack(xyz) * mapping.max_r.d


@pytest.mark.parametrize(
    "geometry, ds_attr",
    [("geographic", "surface_height"), ("internal_geographic", "outer_radius")],
)
def test_mapping_matches_yt(geometry, ds_attr):
    ds = _geo_ds(geometry=geometry)
    # a plain float (code_length) so that convert_to_cartesian can add it to
    # the unitless native coordinates
    setattr(ds, ds_attr, 1.5)
    points = _native_points(ds)
    expected = ds.coordinates.convert_to_cartesian(points)

    mapping = SphericalMapping.from_data_source(ds.all_data())
    assert np.allclose(_mapped_cartesian(mapping, points), expected)
    assert mapping.tex_axis_flip[ds.coordinates.axis_id["latitude"]] == 1.0
    radial_flip = mapping.tex_axis_flip[
        ds.coordinates.axis_id[ds.coordinates.radial_axis]
    ]
    assert radial_flip == (1.0 if geometry == "internal_geographic" else 0.0)


@pytest.mark.parametrize(
    "geometry, ds_attr",
    [("geographic", "surface_height"), ("internal_geographic", "outer_radius")],
)
@pytest.mark.parametrize("reference_height", [(150.0, "cm"), 1.5])
def test_reference_height_overrides_dataset(geometry, ds_attr, reference_height):
    ds = _geo_ds(geometry=geometry)
    setattr(ds, ds_attr, ds.quan(10.0, "m"))
    mapping = SphericalMapping.from_data_source(ds.all_data(), reference_height)

    setattr(ds, ds_attr, 1.5)
    points = _native_points(ds)
    expected = ds.coordinates.convert_to_cartesian(points)
    assert np.allclose(_mapped_cartesian(mapping, points), expected)


@pytest.mark.parametrize("geometry", ["cartesian", "spherical"])
def test_reference_height_rejected(geometry):
    bbox = np.array([[0.1, 1.0], [0.0, np.pi], [0.0, 2 * np.pi]])
    ds = yt.load_uniform_grid(
        {"density": np.ones((8, 8, 8))}, (8, 8, 8), bbox=bbox, geometry=geometry
    )
    from yt_idv.scene_data.block_collection import BlockCollection

    bc = BlockCollection(data_source=ds.all_data(), reference_height=(1.0, "m"))
    with pytest.raises(ValueError, match="reference_height"):
        bc.add_data(("stream", "density"), no_ghost=True)


def test_zero_surface_height_warns():
    ds = _geo_ds()
    with pytest.warns(UserWarning, match="reference_height"):
        SphericalMapping.from_data_source(ds.all_data())

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        SphericalMapping.from_data_source(ds.all_data(), (1.0, "m"))


def test_phi_min_centers_wrap_in_domain_gap():
    ds = _geo_ds(lon=(-60.0, 60.0))
    mapping = SphericalMapping.from_data_source(ds.all_data(), (1.0, "m"))
    # the 240 degree gap is centered on 180 degrees
    assert np.isclose(mapping.phi_min, -np.pi)

    ds = _geo_ds(lon=(20.0, 200.0))
    mapping = SphericalMapping.from_data_source(ds.all_data(), (1.0, "m"))
    assert np.isclose(mapping.phi_min, -70.0 * np.pi / 180)

    ds = _geo_ds(lon=(0.0, 360.0))
    mapping = SphericalMapping.from_data_source(ds.all_data(), (1.0, "m"))
    assert np.isclose(mapping.phi_min, 0.0)


def _render(rc, ds, **kwargs):
    rc.add_scene(ds, ("stream", "density"), no_ghost=True, **kwargs)
    rc.scene.components[0].sample_factor = -0.5  # log10(eta)
    rc.scene.components[0].cmap_log = False
    return np.asarray(rc.run()).copy()


@pytest.mark.parametrize("geometry", ["geographic", "internal_geographic"])
def test_geographic_matches_spherical(make_rc, image_store, geometry):
    # the same data loaded as geographic and as spherical, with latitude (and
    # depth) reversed to match theta (and r), must render identically.
    rc = make_rc(width=256, height=256)
    data = np.random.default_rng(0).random(_SHAPE)
    ref = 1.5
    radial = (0.0, 0.5)

    img_geo = _render(
        rc, _geo_ds(geometry=geometry, radial=radial, data=data), reference_height=ref
    )

    d2r = np.pi / 180
    if geometry == "geographic":
        r_edges = [ref + radial[0], ref + radial[1]]
        sph_data = data[::-1, :, :]
    else:
        r_edges = [ref - radial[1], ref - radial[0]]
        sph_data = data[::-1, :, ::-1]
    sph_bbox = np.array(
        [
            [(90 - _LAT[1]) * d2r, (90 - _LAT[0]) * d2r],
            [_LON[0] * d2r, _LON[1] * d2r],
            r_edges,
        ]
    )
    ds_sph = yt.load_uniform_grid(
        {"density": sph_data.copy()},
        _SHAPE,
        bbox=sph_bbox,
        nprocs=4,
        geometry="spherical",
        axis_order=("theta", "phi", "r"),
        length_unit="m",
    )
    img_sph = _render(rc, ds_sph)

    assert (img_geo[..., 3] > 0).mean() > 0.05
    assert np.allclose(img_geo, img_sph, atol=2.0 / 255)
    image_store(rc)


def test_longitude_wrap(make_rc):
    # longitudes of (-180, 180) and the same data rolled onto (0, 360)
    rc = make_rc(width=256, height=256)
    data = np.random.default_rng(0).random(_SHAPE)
    img_neg = _render(rc, _geo_ds(lon=(-180.0, 180.0), data=data), reference_height=1.0)
    rolled = np.roll(data, -_SHAPE[1] // 2, axis=1)
    img_pos = _render(rc, _geo_ds(lon=(0.0, 360.0), data=rolled), reference_height=1.0)

    assert (img_neg[..., 3] > 0).mean() > 0.05
    assert np.allclose(img_neg, img_pos, atol=2.0 / 255)
