import numpy as np
import pytest
from OpenGL import GL

from yt_idv.opengl_support import TextureAtlas, VertexArray


def _read_atlas(atlas):
    # glGetTexImage returns the texels with x varying fastest
    with atlas.bind():
        raw = GL.glGetTexImage(GL.GL_TEXTURE_3D, 0, GL.GL_RED, GL.GL_FLOAT)
    nx, ny, nz = atlas.dims
    return np.frombuffer(raw, dtype="f4").reshape(nz, ny, nx).T


@pytest.mark.parametrize("padding", [0, 1, 2])
def test_atlas_upload(empty_rc, padding):
    rng = np.random.default_rng(0)
    sizes = rng.integers(1, 9, size=(50, 3))
    va = VertexArray(name="atlas_test", each=1)
    atlas = TextureAtlas(sizes, padding=padding, vertex_array=va)
    blocks = [rng.random(tuple(s)).astype("f4") for s in sizes]
    for i, block in enumerate(blocks):
        atlas[i] = block

    assert len(atlas) == len(sizes)
    assert (atlas.dims <= GL.glGetInteger(GL.GL_MAX_3D_TEXTURE_SIZE)).all()
    texels = _read_atlas(atlas)
    for off, block in zip(atlas.offsets, blocks, strict=True):
        lo, hi = off - padding, off + np.array(block.shape) + padding
        region = texels[lo[0] : hi[0], lo[1] : hi[1], lo[2] : hi[2]]
        expected = np.pad(block, padding, mode="edge")
        np.testing.assert_array_equal(region, expected)

    for name, expected in (
        ("in_texture_offset", atlas.offsets),
        ("in_texture_size", sizes),
    ):
        attr = va[name]
        assert attr.integer
        assert attr.data.dtype == np.int32
        np.testing.assert_array_equal(attr.data, expected)
    atlas.release()
    va.release()


def test_atlas_rejects_wrong_shape(empty_rc):
    atlas = TextureAtlas([(2, 3, 4)])
    with pytest.raises(ValueError):
        atlas[0] = np.zeros((4, 3, 2), dtype="f4")
    atlas.release()


def test_atlas_too_large(empty_rc):
    max_dim = GL.glGetInteger(GL.GL_MAX_3D_TEXTURE_SIZE)
    with pytest.raises(ValueError):
        TextureAtlas([(max_dim + 1, 1, 1)])


@pytest.mark.parametrize(
    "render_method", ["max_intensity", "projection", "transfer_function"]
)
def test_unpadded_atlas_renders_as_padded(make_rc, monkeypatch, render_method):
    # The shaders clamp each block's lookups to its own texel centers, as edge
    # padding (and clamp-to-edge before the atlas) did, so blocks need no padding.
    from yt.testing import fake_amr_ds

    from yt_idv.scene_data import block_collection

    ds = fake_amr_ds(fields=[("gas", "density")], units=["g/cm**3"])
    rc = make_rc(width=256, height=256)
    atlas = block_collection.TextureAtlas
    images = []
    for padding in (1, 0):
        monkeypatch.setattr(
            block_collection,
            "TextureAtlas",
            lambda *a, _padding=padding, **kw: atlas(*a, **dict(kw, padding=_padding)),
        )
        scene = rc.add_scene(ds, ("gas", "density"), no_ghost=True)
        component = scene.components[0]
        component.render_method = render_method
        # a linear 0-1 range over the normalized texels: the default log range
        # starts at log(0), whose NaN lookups draw nothing on some platforms
        component.tf_log = False
        assert scene.data_objects[0].data_atlas.padding == padding
        images.append(np.asarray(rc.run(), dtype="float64"))
    assert images[0][..., 3].max() > 0  # something drew

    # get a 2-d bool array where pixels differ by more than 2/255 in any channel
    mismatched = (np.abs(images[1] - images[0]) > 2 / 255).any(axis=-1)

    # check that less than .1% of pixels differ: with the small difference in atlas
    # sizes between the two images, the normalized texture coordinates round slightly
    # differently, so some isolated pixels may move a couple of colormap steps. The
    # amount is also platform-dependent! So rather than checking that all pixels are
    # close within a tolerance of 2/255, we check that a small fraction are mismatched.
    n_mismatched = mismatched.sum()
    assert n_mismatched / mismatched.size < 1e-3, (
        f"{n_mismatched} of {mismatched.size} pixels differ"
    )
