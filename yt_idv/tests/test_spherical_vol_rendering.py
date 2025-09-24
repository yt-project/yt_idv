import numpy as np
import pytest
import yt

from yt_idv.cameras.trackball_camera import TrackballCamera
from yt_idv.scene_components.blocks import BlockRendering
from yt_idv.scene_components.curves import CurveCollectionRendering
from yt_idv.scene_data.block_collection import (
    BlockCollection,
    _block_collection_outlines,
)
from yt_idv.scene_data.curve import CurveCollection
from yt_idv.scene_graph import SceneGraph

bbox_options = {
    "partial": {
        "bbox": np.array([[0.5, 1.0], [0.0, np.pi / 3], [np.pi / 4, np.pi / 2]]),
        "field": ("index", "r"),
        "camera_position": [-0.5, -1, 2.5],
    },
    "whole": {
        "bbox": np.array([[0.0, 1.0], [0.0, 2 * np.pi], [0, np.pi]]),
        "field": ("index", "phi"),
    },
    "quadrant_shell": {
        "bbox": np.array([[0.6, 1.0], [0.0, np.pi / 2], [0.0, np.pi / 2]]),
        "field": ("index", "theta"),
    },
    "big_r": {
        "bbox": np.array([[0.0, 100.0], [0.0, 2 * np.pi], [0, np.pi]]),
        "field": ("index", "phi"),
    },
}


def _get_sph_yt_ds(bbox_option: str):
    sz = (32, 32, 32)
    fake_data = {"density": np.random.random(sz)}

    bbox = bbox_options[bbox_option]["bbox"]

    ds = yt.load_uniform_grid(
        fake_data,
        sz,
        bbox=bbox,
        nprocs=8,
        geometry="spherical",
        axis_order=("r", "phi", "theta"),
        length_unit="m",
    )
    return ds


@pytest.mark.parametrize("bbox_option", bbox_options.keys())
def test_spherical_bounds(osmesa_empty_rc, image_store, bbox_option):

    ds = _get_sph_yt_ds(bbox_option)
    dd = ds.all_data()

    field = bbox_options[bbox_option]["field"]
    osmesa_empty_rc.add_scene(dd, field, no_ghost=True)
    osmesa_empty_rc.scene.components[0].sample_factor = 5.0
    osmesa_empty_rc.scene.components[0].cmap_log = False
    cpos = bbox_options[bbox_option].get("camera_position", None)
    if cpos:
        osmesa_empty_rc.scene.camera.set_position(cpos)

    image_store(osmesa_empty_rc)


@pytest.mark.parametrize("nprocs", [1, 2, 4, 16])
def test_spherical_nprocs(osmesa_empty_rc, image_store, nprocs):

    bbox_option = "whole"
    ds = _get_sph_yt_ds(bbox_option)
    dd = ds.all_data()

    field = bbox_options[bbox_option]["field"]
    osmesa_empty_rc.add_scene(dd, field, no_ghost=True)
    osmesa_empty_rc.scene.components[0].sample_factor = 5.0
    osmesa_empty_rc.scene.components[0].cmap_log = False
    osmesa_empty_rc.scene.components[0]._reset_cmap_bounds()
    cpos = bbox_options[bbox_option].get("camera_position", None)
    if cpos:
        osmesa_empty_rc.scene.camera.set_position(cpos)

    image_store(osmesa_empty_rc)


@pytest.mark.parametrize("bbox_option", ["partial", "big_r"])
def test_block_collection_outlines(osmesa_empty_rc, image_store, bbox_option):

    ds = _get_sph_yt_ds(bbox_option)
    block_coll: BlockCollection = BlockCollection(
        data_source=ds.all_data(),
    )
    block_coll.add_data(("stream", "density"), no_ghost=True)

    block_rendering: BlockRendering = BlockRendering(
        data=block_coll,
        cmap_log=False,
    )

    curve_coll, curve_render = _block_collection_outlines(block_coll)

    assert isinstance(curve_coll, CurveCollection)
    assert isinstance(curve_render, CurveCollectionRendering)
    assert curve_coll.n_curves > 0

    c = TrackballCamera.from_dataset(ds)
    osmesa_empty_rc.scene = SceneGraph(camera=c)
    osmesa_empty_rc.scene.data_objects.append(block_coll)
    osmesa_empty_rc.scene.components.append(block_rendering)

    osmesa_empty_rc.scene.data_objects.append(curve_coll)
    osmesa_empty_rc.scene.components.append(curve_render)

    image_store(osmesa_empty_rc)
