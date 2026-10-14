from collections.abc import Iterator
from typing import TYPE_CHECKING

import numpy as np
import yt
from numpy.typing import NDArray

import yt_idv
from yt_idv.scene_components.blocks import BlockRendering
from yt_idv.scene_components.curves import CurveCollectionRendering
from yt_idv.scene_data.curve import CurveCollection
from yt_idv.utilities.logger import ytidv_log

if TYPE_CHECKING:
    from shapely.geometry.base import BaseGeometry

try:
    from cartopy import feature as cfeature
    from shapely.geometry import box

    has_geo_deps = True
except ImportError:
    has_geo_deps = False
    ytidv_log.info(
        "Missing optional dependencies, no surface features will be added. To install, run `pip install yt_idv[examples]`"
    )


# a regional shell in geographic coordinates: latitude, longitude, altitude
# (or depth for internal_geographic). The radial extent is given in km.
geometry = "geographic"  # or "internal_geographic"
lat_range = (-30.0, 60.0)
lon_range = (-120.0, 60.0)
# surface height (geographic) or outer radius (internal_geographic), in km

radial_width = 2000.0  # radial extent of the domain in km
reference_height = 6371 - radial_width
size = 128  # dimensions, will be (size,)*3
nprocs = 32  # number of grids

default_camera = {
    "position": [4.11211633682251, -2.990974187850952, 0.1937132030725479],
    "focus": [0.2505352795124054, -0.06791441142559052, 0.1830127090215683],
    "up": [0.08545706367214534, 0.11651746737055091, 0.989505292120624],
    "orientation": [
        0.6550179591361343,
        0.6080173659397979,
        0.35945817605664643,
        0.26843276445015873,
    ],
    "fov": 45.0,
    "near_plane": 0.3652014238264269,
    "far_plane": 20.0,
    "aspect_ratio": 1.0,
    "projection_type": "perspective",
}


def geometry_traces(geom: "BaseGeometry") -> Iterator[tuple[NDArray, NDArray]]:
    """yield (lat, lon) arrays for each line of a shapely geometry"""
    if hasattr(geom, "geoms"):  # Multi* geometries
        for part in geom.geoms:
            yield from geometry_traces(part)
        return
    if hasattr(geom, "exterior"):  # polygons
        geom = geom.exterior
    lon, lat = np.asarray(geom.coords).T[:2]
    yield lat, lon


if __name__ == "__main__":
    sz = (size,) * 3
    lat, lon, rad = np.meshgrid(
        np.linspace(*lat_range, sz[0]),
        np.linspace(*lon_range, sz[1]),
        np.linspace(0.0, 1.0, sz[2]),
        indexing="ij",
    )
    # a linear decrease with the radial coordinate (0 at the inner surface, 1
    # at the outer), with a blob centered in the domain on top of it
    lat_c = np.mean(lat_range)
    lon_c = np.mean(lon_range)
    blob = np.exp(-(((lat - lat_c) / 15.0) ** 2 + ((lon - lon_c) / 25.0) ** 2))
    density = 0.5 - 0.4 * rad + blob

    bbox = np.array([lat_range, lon_range, [0.0, radial_width]])
    ds = yt.load_uniform_grid(
        {"density": density},
        sz,
        bbox=bbox,
        nprocs=nprocs,
        geometry=geometry,
        length_unit="km",
    )

    rc = yt_idv.render_context(height=800, width=800, gui=True)
    rc.add_scene(
        ds,
        ("stream", "density"),
        no_ghost=True,
        reference_height=(reference_height, "km"),
    )
    blocks = rc.scene.components[0]
    assert isinstance(blocks, BlockRendering)

    blocks.sample_factor = 0.0  # log10(eta)
    blocks.cmap_log = False
    blocks.colormap.colormap_name = "doom"
    blocks._reset_cmap_bounds()

    # add coastlines on the outer surface. The curve objects allocate GPU
    # buffers, so this needs the render context.
    if has_geo_deps:
        nef = cfeature.NaturalEarthFeature("physical", "coastline", "10m")
        # a single box covering the lat/lon extent of the scene (x=lon, y=lat)
        scene_box = box(lon_range[0], lat_range[0], lon_range[1], lat_range[1])
        # the same native -> scene coordinate mapping the renderer uses
        mapping = blocks.data.spherical_mapping
        outer_radius = reference_height + radial_width  # km

        coastlines = CurveCollection()
        for geom in nef.geometries():
            if not geom.intersects(scene_box):
                continue
            for lat_i, lon_i in geometry_traces(geom):
                native = np.column_stack([lat_i, lon_i, np.zeros_like(lat_i)])
                coastlines.add_curve(
                    mapping.to_model_coords(native, radius=outer_radius)
                )
        coastlines.add_data()  # call add_data() after done adding curves
        coastlines_render = CurveCollectionRendering(data=coastlines)
        coastlines_render.display_name = "coastlines"

        rc.scene.data_objects.append(coastlines)
        rc.scene.components.append(coastlines_render)

    rc.scene.camera.update_from_dict(default_camera)

    rc.run()
