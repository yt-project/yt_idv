import numpy as np
import pytest
import yt

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


def _get_yt_ds(geometry: str):
    sz = (32, 32, 32)
    fake_data = {"density": np.random.random(sz)}
    ds = yt.load_uniform_grid(
        fake_data,
        sz,
        bbox=_bboxes_by_geom[geometry],
        nprocs=8,
        geometry=geometry,
        length_unit="m",
    )
    return ds


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


@pytest.mark.parametrize("geometry", ["cartesian", "spherical"])
@pytest.mark.parametrize("grid_type", ["arbitrary", "covering"])
def test_grid_list(osmesa_empty_rc, image_store, geometry, grid_type):

    ds = _get_yt_ds(geometry)

    if grid_type == "arbitrary":
        ags = _get_ags(ds, geometry)
    else:
        ags = _get_cgs(ds, geometry)

    c = TrackballCamera.from_dataset(ds)

    osmesa_empty_rc.scene = SceneGraph(camera=c)

    grid_coll = GridCollection(data_source=ags)
    grid_coll.add_data(_fields[geometry][0], no_ghost=True)

    osmesa_empty_rc.scene.data_objects.append(grid_coll)
    osmesa_empty_rc.scene.components.append(GridCollectionRendering(data=grid_coll))

    if _fields[geometry][1] is False:
        osmesa_empty_rc.scene.components[0].cmap_log = False

    cpos = _camera_pos.get(geometry, None)
    if cpos:
        osmesa_empty_rc.scene.camera.set_position(cpos)
    osmesa_empty_rc.scene.camera.focus = ds.domain_center.d

    image_store(osmesa_empty_rc)
