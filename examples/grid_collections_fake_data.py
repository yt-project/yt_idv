import argparse

import numpy as np
import yt

import yt_idv
from yt_idv.cameras.trackball_camera import TrackballCamera
from yt_idv.scene_components.blocks import GridCollectionRendering
from yt_idv.scene_data.block_collection import GridCollection
from yt_idv.scene_graph import SceneGraph

_bboxes_by_geom = {
    "cartesian": np.array([[-1, 1], [-1, 1], [-1, 1]]),
    "spherical": np.array([[0, 1], [0, np.pi], [0, 2 * np.pi]]),
}

_camera_pos = {
    "cartesian": [-0.13453812897205353, -1.2374168634414673, 2.3244969844818115],
    "spherical": [2.618459939956665, 3.529810905456543, -2.2845287322998047],
}

_fields = {
    "cartesian": (("stream", "density"), False),
    "spherical": (("index", "theta"), False),
}


def _get_ags(ds, geom):
    ags = []
    if geom == "spherical":
        le = ds.domain_center.copy()
        le[0] = le[0] + ds.domain_width[0] / 4
        ags.append(ds.arbitrary_grid(le, ds.domain_right_edge, [64, 64, 64]))

        hwid = ds.domain_width / 2
        le = ds.domain_left_edge + hwid * np.array([0.0, 0.0, 1.0])
        re = le + hwid
        ags.append(ds.arbitrary_grid(le, re, [32, 32, 32]))
    else:
        ags.append(
            ds.arbitrary_grid(ds.domain_center, ds.domain_right_edge, [64, 64, 64])
        )
        ags.append(
            ds.arbitrary_grid(ds.domain_left_edge, ds.domain_center, [32, 32, 32])
        )
    return ags


def _get_cgs(ds, geom):
    cgs = []
    if geom == "spherical":
        le = ds.domain_center.copy()
        le[0] = le[0] + ds.domain_width[0] / 4
        cgs.append(ds.covering_grid(0, le, 8))

        hwid = ds.domain_width / 2
        le = ds.domain_left_edge + hwid * np.array([0.0, 0.0, 1.0])
        cgs.append(ds.covering_grid(0, le, [16, 16, 16]))
    else:
        cgs.append(ds.covering_grid(0, ds.domain_left_edge, [16, 16, 16]))
        cgs.append(ds.covering_grid(0, ds.domain_center, [16, 16, 16]))
    return cgs


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog="grid_collections",
        description="Methods of loading lists of covering or arbitrary grids",
    )

    msg = "The geometry to use: cartesian (default) or spherical"
    parser.add_argument("-g", "--geometry", default="cartesian", help=msg)
    msg = "arbitrary (default) or covering"
    parser.add_argument("--grid_type", default="arbitrary", help=msg)

    args = parser.parse_args()
    geometry = args.geometry

    sz = (32, 32, 32)
    fake_data = {"density": np.random.random(sz)}
    ds = yt.load_uniform_grid(
        fake_data,
        sz,
        bbox=_bboxes_by_geom[geometry],
        geometry=geometry,
        length_unit="m",
    )

    if args.grid_type == "arbitrary":
        grids = _get_ags(ds, geometry)
    else:
        grids = _get_cgs(ds, geometry)

    rc = yt_idv.render_context(height=800, width=800, gui=True)

    c = TrackballCamera.from_dataset(ds)
    rc.scene = SceneGraph(camera=c)
    grid_coll = GridCollection(data_source=grids)
    grid_coll.add_data(_fields[geometry][0], no_ghost=True)
    rc.scene.data_objects.append(grid_coll)
    rc.scene.components.append(GridCollectionRendering(data=grid_coll))

    if _fields[geometry][1] is False:
        rc.scene.components[0].cmap_log = False

    cpos = _camera_pos.get(geometry, None)
    if cpos:
        rc.scene.camera.set_position(cpos)

    rc.scene.camera.focus = (
        0,
        0,
        0,
    )

    rc.run()
