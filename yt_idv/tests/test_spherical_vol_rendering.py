import numpy as np
import pytest
import yt

import yt_idv


@pytest.fixture()
def osmesa_empty_rc():
    """yield an OSMesa empy context then destroy"""

    rc = yt_idv.render_context("osmesa", width=1024, height=1024)
    yield rc
    rc.osmesa.OSMesaDestroyContext(rc.context)


bbox_options = {
    "partial": {
        "bbox": np.array([[0.5, 1.0], [0.0, np.pi / 3], [np.pi / 4, np.pi / 2]]),
        "field": ("index", "r"),
        "camera_position": [-0.5, -1, 2.5],
    },
    "whole": {
        "bbox": np.array([[0.0, 1.0], [0.0, 2 * np.pi], [0, np.pi]]),
        "field": ("index", "phi"),
        "camera_position": [0.5, 0.5, 2],
    },
    "quadrant_shell": {
        "bbox": np.array([[0.6, 1.0], [0.0, np.pi / 2], [0.0, np.pi / 2]]),
        "field": ("index", "theta"),
    },
}


@pytest.mark.parametrize("bbox_option", bbox_options.keys())
def test_spherical_bounds(osmesa_empty_rc, image_store, bbox_option):

    sz = (32, 32, 32)
    fake_data = {"density": np.random.random(sz)}

    bbox = bbox_options[bbox_option]["bbox"]

    ds = yt.load_uniform_grid(
        fake_data,
        sz,
        bbox=bbox,
        nprocs=8,
        geometry=("spherical", ("r", "phi", "theta")),
        length_unit="m",
    )
    dd = ds.all_data()

    field = bbox_options[bbox_option]["field"]
    osmesa_empty_rc.add_scene(dd, field, no_ghost=True)
    osmesa_empty_rc.scene.components[0].sample_factor = 20.0
    osmesa_empty_rc.scene.components[0].cmap_log = False
    cpos = bbox_options[bbox_option].get("camera_position", None)
    if cpos:
        osmesa_empty_rc.scene.camera.set_position(cpos)

    image_store(osmesa_empty_rc)


@pytest.mark.parametrize("nprocs", [1, 2, 4, 16])
def test_spherical_nprocs(osmesa_empty_rc, image_store, nprocs):

    sz = (32, 32, 32)
    fake_data = {"density": np.random.random(sz)}

    bbox_option = "whole"
    bbox = bbox_options[bbox_option]["bbox"]

    ds = yt.load_uniform_grid(
        fake_data,
        sz,
        bbox=bbox,
        nprocs=nprocs,
        geometry=("spherical", ("r", "phi", "theta")),
        length_unit="m",
    )
    dd = ds.all_data()

    field = bbox_options[bbox_option]["field"]
    osmesa_empty_rc.add_scene(dd, field, no_ghost=True)
    osmesa_empty_rc.scene.components[0].sample_factor = 20.0
    osmesa_empty_rc.scene.components[0].cmap_log = False
    osmesa_empty_rc.scene.components[0]._reset_cmap_bounds()
    cpos = bbox_options[bbox_option].get("camera_position", None)
    if cpos:
        osmesa_empty_rc.scene.camera.set_position(cpos)

    image_store(osmesa_empty_rc)
