import numpy as np
import pytest
import yt


@pytest.fixture()
def sphere_ds():
    n = 32
    x = (np.arange(n) + 0.5) / n
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    r = np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2 + (Z - 0.5) ** 2)
    density = np.where(r < 0.3, 1.0, 1e-3)
    return yt.load_uniform_grid(
        {"density": (density, "g/cm**3")},
        density.shape,
        nprocs=8,
        bbox=np.array([[0.0, 1.0]] * 3),
    )


@pytest.mark.parametrize("width, height", [(96, 64), (64, 96)])
def test_non_square_render_keeps_proportions(make_rc, sphere_ds, width, height):
    rc = make_rc(width=width, height=height)
    rc.add_scene(sphere_ds, "density", no_ghost=True)
    component = rc.scene.components[0]
    component.render_method = "max_intensity"
    component.store_first_pass_fb = True
    rc.scene.camera.update(
        position=[0.5, 0.5, 2.5],
        focus=[0.5, 0.5, 0.5],
        up=[0.0, 1.0, 0.0],
        aspect_ratio=width / height,
    )
    image = np.array(rc.run())
    assert image.shape == (height, width, 4)
    assert component.first_pass_fb_rgba.shape == (height, width, 4)

    # the sphere renders as a centered disk
    lit = image[..., :3].max(axis=-1) > 0.5 * image[..., :3].max()
    rows, cols = np.nonzero(lit)
    disk_width = cols.max() - cols.min() + 1
    disk_height = rows.max() - rows.min() + 1
    assert abs(disk_width - disk_height) <= 1
    assert abs((cols.max() + cols.min()) / 2 - (width - 1) / 2) <= 1
    assert abs((rows.max() + rows.min()) / 2 - (height - 1) / 2) <= 1
