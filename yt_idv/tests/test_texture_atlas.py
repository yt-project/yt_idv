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
