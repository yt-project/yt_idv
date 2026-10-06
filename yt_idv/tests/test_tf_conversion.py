import numpy as np
import pytest
import yt
from yt.testing import fake_amr_ds

from yt_idv.tf_conversion import (
    apply_converted_transfer_function,
    convert_yt_transfer_function,
)


@pytest.fixture()
def block_collection(make_rc):
    rc = make_rc(width=32, height=32)
    rc.add_scene(fake_amr_ds(), "Density", no_ghost=True)
    return rc.scene.components[0]


def _yt_tf(data):
    lo, hi = np.log10(data.min_val), np.log10(data.max_val)
    tf = yt.ColorTransferFunction((lo, hi), grey_opacity=True)
    tf.add_gaussian(0.5 * (lo + hi), 0.01 * (hi - lo), [1.0, 0.5, 0.25, 4.0])
    return tf, lo, hi


def test_conversion_matches_yt_at_each_texel(block_collection):
    data = block_collection.data
    tf, lo, hi = _yt_tf(data)
    ray_length = 2.5
    converted = convert_yt_transfer_function(tf, data, ray_length, nbins=256)
    table = converted["transfer_function"].data[:, 0, :].astype("f8")
    assert converted["tf_log"]

    # the field value at each texel center, through yt_idv's mapping from the
    # texture coordinate (natural log of the normalized value) to the field
    u = (np.arange(256) + 0.5) / 256
    log_n = np.log(converted["tf_min"]) + u * (
        np.log(converted["tf_max"]) - np.log(converted["tf_min"])
    )
    values = np.exp(log_n) * (data.max_val - data.min_val) + data.min_val
    log_values = np.log10(values)

    r, g, b, a = (np.interp(log_values, tf.funcs[i].x, tf.funcs[i].y) for i in range(4))
    # yt weights the colors by alpha, and its dt is the path length / ray length
    expected = np.stack([r * a, g * a, b * a, a], axis=-1) / ray_length
    np.testing.assert_allclose(table, expected, rtol=1e-4, atol=1e-6)
    assert lo < log_values[table[:, 3].argmax()] < hi


def test_conversion_requires_grey_opacity(block_collection):
    data = block_collection.data
    tf = yt.ColorTransferFunction((-1.0, 1.0), grey_opacity=False)
    with pytest.raises(NotImplementedError):
        convert_yt_transfer_function(tf, data, 1.0)


def test_apply_converted_transfer_function(block_collection):
    tf, _, _ = _yt_tf(block_collection.data)
    converted = convert_yt_transfer_function(tf, block_collection.data, 1.0)
    apply_converted_transfer_function(block_collection, converted)
    assert block_collection.render_method == "transfer_function"
    assert block_collection.transfer_function is converted["transfer_function"]
    assert block_collection.tf_min == converted["tf_min"]
