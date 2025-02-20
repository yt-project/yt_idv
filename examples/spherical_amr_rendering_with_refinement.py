import argparse

import numpy as np
import yt

import yt_idv

# yt reminder: phi is the azimuthal angle (0 to 2pi)
# theta is the co-latitude, the angle from north (0 to pi)
# coord ordering here will be r, phi, theta

ax_order = ("r", "phi", "theta")

bbox_options = {
    "partial": np.array([[0.5, 1.0], [0.0, np.pi / 3], [np.pi / 4, np.pi / 2]]),
    "whole": np.array([[0.0, 1.0], [0.0, 2 * np.pi], [0, np.pi]]),
    "shell": np.array([[0.5, 1.0], [0.0, 2 * np.pi], [0, np.pi]]),
    "north_hemi": np.array([[0.0, 1.0], [0.0, 2 * np.pi], [0, 0.5 * np.pi]]),
    "north_shell": np.array([[0.5, 1.0], [0.0, 2 * np.pi], [0, 0.5 * np.pi]]),
    "south_hemi": np.array([[0.0, 1.0], [0.0, 2 * np.pi], [0.5 * np.pi, np.pi]]),
    "ew_hemi": np.array([[0.0, 1.0], [0.0, np.pi], [0.0, np.pi]]),
}

max_levs = {
    "partial": 4,
    "whole": 5,
    "shell": 4,
    "north_hemi": 5,
    "north_shell": 2,
    "south_hemi": 5,
    "ew_hemi": 5,
}


def _build_ds(bbox_key):
    bbox = bbox_options[bbox_key]

    bbox_wid = bbox[:, 1] - bbox[:, 0]
    bbox_c = np.mean(bbox, axis=1)
    sz_0 = np.array((64, 64, 64))
    max_lev = max_levs[bbox_key]

    # divide grid by 2 every time
    dd0 = bbox_wid / sz_0
    sz_i = sz_0.copy()
    grids = []
    for lev in range(max_lev):

        box_wid_factor = 2.0 * int(lev > 0) + int(lev == 0) * 1.0
        bbox_wid = bbox_wid / box_wid_factor
        le_i = bbox_c - bbox_wid / 2.0
        re_i = bbox_c + bbox_wid / 2.0

        # find closest start/end index in lev 0 grid
        start_i = np.round(le_i / dd0).astype(int)
        end_i = np.round(re_i / dd0).astype(int)
        sz_0 = end_i - start_i

        # recompute for rounding errors
        le_i = start_i * dd0
        re_i = le_i + sz_0 * dd0

        sz_i = sz_0 * 2**lev

        levp1 = np.full(sz_i, lev + 1.0)
        grid = {
            "left_edge": le_i,
            "right_edge": re_i,
            "dimensions": sz_i,
            "level": lev,
            ("stream", "density"): np.random.random(sz_i) * (lev + 1),
            ("stream", "lev_p1"): levp1,
        }
        grids.append(grid)

    ds = yt.load_amr_grids(
        grids,
        sz_0,
        bbox=bbox,
        length_unit=1,
        geometry="spherical",
        axis_order=ax_order,
    )

    return ds


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog="spherical_amr_rendering_with_refinement",
        description="Loads an example spherical dataset with grid refinement in yt_idv",
    )

    msg = f"The geometry subset to generate: one of {list(bbox_options.keys())}"
    parser.add_argument("-d", "--domain", default="partial", help=msg)

    msg = (
        "The field to plot. Provide a comma-separated string with field_type,field "
        "e.g., to plot the field tuple ('index', 'phi'): \n "
        "    $ python amr_spherical_volume_rendering.py -f index,x "
        "\nIf a single string is provided, a field type of gas is assumed."
    )
    parser.add_argument("-f", "--field", default="stream,density", help=msg)

    parser.add_argument(
        "--listfields", action=argparse.BooleanOptionalAction, default=True
    )

    args = parser.parse_args()

    if args.domain not in bbox_options:
        raise RuntimeError(
            f"domain must be one of {list(bbox_options.keys())}, found {args.domain}"
        )

    ds = _build_ds(args.domain)

    if args.listfields:
        print("available fields:")
        print(ds.field_list)

    fld = tuple(str(args.field).split(","))

    rc = yt_idv.render_context(height=800, width=800, gui=True)
    sg = rc.add_scene(ds, fld, no_ghost=True)
    rc.scene.components[0].cmap_log = False
    rc.scene.components[0].sample_factor = 25

    rc.run()
