import numpy as np
import pytest
import yt

from yt_idv.cameras.trackball_camera import TrackballCamera
from yt_idv.scene_components.blocks import BlockRendering
from yt_idv.scene_data.block_collection import BlockCollection
from yt_idv.scene_graph import SceneGraph


@pytest.fixture()
def ds_yt_ugrid():
    # create some data
    shp = (8, 8, 8)
    data = {"constant_field": np.full(shape=shp, fill_value=5.0)}
    ds = yt.load_uniform_grid(data, shp, length_unit=1)
    return ds


def test_block_collection_normalization(osmesa_empty_rc, ds_yt_ugrid):

    block_coll: BlockCollection = BlockCollection(
        data_source=ds_yt_ugrid.all_data(),
        min_val=0.0,
        max_val=10.0,
        compute_min_max=False,
        always_normalize=True,
    )
    block_coll.add_data(("stream", "constant_field"), no_ghost=True)

    assert np.allclose(block_coll.texture_objects[0].data, 0.5)


def test_block_rendering_cmap_norms(osmesa_empty_rc, ds_yt_ugrid, image_store):

    block_coll: BlockCollection = BlockCollection(
        data_source=ds_yt_ugrid.all_data(),
        min_val=0.0,
        max_val=10.0,
        compute_min_max=False,
        always_normalize=True,
    )
    block_coll.add_data(("stream", "constant_field"), no_ghost=True)

    block_rendering: BlockRendering = BlockRendering(
        data=block_coll,
        fixed_cmap_min=0.2,
        fixed_cmap_max=0.8,
        cmap_log=False,
    )

    block_rendering._reset_cmap_bounds()

    assert block_rendering.cmap_min == 0.2
    assert block_rendering.cmap_max == 0.8

    block_rendering.fixed_cmap_min = 0.0
    block_rendering.fixed_cmap_max = 1.0
    block_rendering._reset_cmap_bounds()
    assert block_rendering.cmap_min == 0.0
    assert block_rendering.cmap_max == 1.0

    c = TrackballCamera.from_dataset(ds_yt_ugrid)
    osmesa_empty_rc.scene = SceneGraph(camera=c)
    osmesa_empty_rc.scene.data_objects.append(block_coll)
    osmesa_empty_rc.scene.components.append(block_rendering)

    image_store(osmesa_empty_rc)
