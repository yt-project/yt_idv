import numpy as np
import pytest
import yt

import yt_idv


@pytest.fixture()
def osmesa_fake_spherical():
    """Return an OSMesa context that has a "fake" AMR dataset added, with "radius"
    as the field.
    """

    sz = (32, 32, 32)
    fake_data = {"density": np.random.random(sz)}

    bbox = np.array([[0.1, 1.0], [0.0, 2 * np.pi], [0, np.pi]])

    ds = yt.load_uniform_grid(
        fake_data,
        sz,
        bbox=bbox,
        nprocs=1,
        geometry=("spherical", ("r", "phi", "theta")),
        length_unit="m",
    )
    dd = ds.all_data()
    rc = yt_idv.render_context("osmesa", width=1024, height=1024)
    rc.add_scene(dd, ("index", "phi"), no_ghost=True)
    rc.scene.components[0].sample_factor = 20.0
    yield rc
    rc.osmesa.OSMesaDestroyContext(rc.context)


def test_spherical(osmesa_fake_spherical, image_store):
    image_store(osmesa_fake_spherical)
