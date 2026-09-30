import argparse

import numpy as np
import yt

import yt_idv

# a regional shell in geographic coordinates: latitude, longitude, altitude
# (or depth for internal_geographic). The radial extent is given in km.
lat_range = (-30.0, 60.0)
lon_range = (-120.0, 60.0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="geographic_rendering",
        description="Loads an example geographic dataset in yt_idv",
    )
    parser.add_argument(
        "-g",
        "--geometry",
        default="geographic",
        choices=["geographic", "internal_geographic"],
    )
    parser.add_argument(
        "-rh",
        "--reference-height",
        default=2000.0,
        type=float,
        help="surface height (geographic) or outer radius (internal_geographic), in km",
    )
    parser.add_argument(
        "-rw",
        "--radial-width",
        default=1000.0,
        type=float,
        help="radial extent of the domain in km",
    )
    parser.add_argument(
        "-sz", "--size", default=64, type=int, help="dimensions, will be (size,)*3"
    )
    parser.add_argument("-np", "--nprocs", default=16, type=int, help="number of grids")
    args = parser.parse_args()

    sz = (args.size,) * 3
    lat, lon, rad = np.meshgrid(
        np.linspace(*lat_range, sz[0]),
        np.linspace(*lon_range, sz[1]),
        np.linspace(0.0, 1.0, sz[2]),
        indexing="ij",
    )
    # a blob centered in the domain that varies with the radial coordinate
    lat_c = np.mean(lat_range)
    lon_c = np.mean(lon_range)
    blob = np.exp(-(((lat - lat_c) / 15.0) ** 2 + ((lon - lon_c) / 25.0) ** 2))
    density = blob * (0.2 + rad) + 0.05

    bbox = np.array([lat_range, lon_range, [0.0, args.radial_width]])
    ds = yt.load_uniform_grid(
        {"density": density},
        sz,
        bbox=bbox,
        nprocs=args.nprocs,
        geometry=args.geometry,
        length_unit="km",
    )

    rc = yt_idv.render_context(height=800, width=800, gui=True)
    rc.add_scene(
        ds,
        ("stream", "density"),
        no_ghost=True,
        reference_height=(args.reference_height, "km"),
    )
    rc.scene.components[0].sample_factor = 0.0  # log10(eta)
    rc.scene.components[0].cmap_log = False
    rc.scene.components[0]._reset_cmap_bounds()

    rc.run()
