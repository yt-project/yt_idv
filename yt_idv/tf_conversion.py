"""Convert a yt ColorTransferFunction into an equivalent yt_idv transfer function.

yt and yt_idv use the same per-sample compositing step,

    ta = max(1 - dt * a, 0);  rgba = dt * tf + ta * rgba

but they feed it different things (see transfer-function-comparison.md):

* yt weights the RGB tables by the alpha table, so its emission is rgb * alpha.
* yt's dt is path length / |v_dir|, where |v_dir| depends on the lens and the
  camera; yt_idv's dt is the path length in unitary units.
* yt looks the table up in log10 of the field; yt_idv looks it up in the
  natural log (or the value) of the min/max-normalized texture value.
* yt tables are float64 and unbounded; yt_idv's default table is uint8.

The conversion samples the yt table at every yt_idv texel center, going through
yt_idv's own mapping from texture coordinate to field value, so the data axis
is exact up to the texel resolution.
"""

import numpy as np

from yt_idv.opengl_support import TransferFunctionTexture


def yt_ray_length(camera):
    """Return |v_dir| for the central ray of a yt camera, in unitary units.

    yt's sampler parameterizes each ray from t = 0 to 1 along v_dir, so yt's
    dt is the path length divided by this value. For a perspective lens the
    off-axis rays are longer by 1 / cos(angle to the axis), so off-axis pixels
    are dimmer in yt than in yt_idv; only the central ray is matched.
    """
    lens_type = type(camera.lens).__name__
    if lens_type == "PlaneParallelLens":
        return float(camera.width[2].to("unitary"))
    if lens_type == "PerspectiveLens":
        # Same expression as PerspectiveLens._get_sampler_params.
        offset = (camera.position - camera._domain_center).to("unitary").d
        width = camera._domain_width.to("unitary").d
        return float(np.linalg.norm(offset) + 0.5 * np.linalg.norm(width))
    raise NotImplementedError(f"no ray length for yt lens {lens_type}")


def _eval_yt_tf(tf, log_values):
    """Evaluate a yt ColorTransferFunction the way FIT_eval_transfer does.

    Returns an (N, 4) array of the rgba that yt feeds to the compositing step,
    i.e. after the RGB tables have been weighted by the alpha table.
    """
    tables = []
    for table in tf.tables:
        lo, hi = table.x_bounds
        vals = np.interp(log_values, table.x, table.y)
        # FIT_get_value returns 0 on and outside the bounds.
        vals[(log_values <= lo) | (log_values >= hi)] = 0.0
        tables.append(vals)
    weighted = list(tables)
    for i, wid in enumerate(tf.weight_table_ids):
        if wid != -1:
            weighted[i] = weighted[i] * tables[wid]
    return np.stack([weighted[tf.field_table_ids[c]] for c in range(4)], axis=-1)


def convert_yt_transfer_function(tf, block_collection, ray_length, nbins=1024):
    """Convert a yt ColorTransferFunction for use by a yt_idv BlockRendering.

    Parameters
    ----------
    tf : yt.ColorTransferFunction
        A grey-opacity transfer function over log10 of the field (the usual
        setup for a logged field such as density).
    block_collection : yt_idv.scene_data.block_collection.BlockCollection
        The data the table will be used with. Its min_val/max_val define the
        normalization of the textures.
    ray_length : float
        |v_dir| of the yt camera being matched, in unitary units; see
        yt_ray_length.
    nbins : int
        Number of texels in the output table.

    Returns
    -------
    dict with ``transfer_function`` (a float32 TransferFunctionTexture),
    ``tf_min``, ``tf_max`` and ``tf_log``, ready to set on the component (see
    apply_converted_transfer_function).
    """
    if not tf.grey_opacity:
        raise NotImplementedError(
            "yt_idv only composites with grey opacity; build the yt transfer "
            "function with grey_opacity=True"
        )
    if any(fid != 0 for fid in tf.field_ids) or any(
        wid != -1 for wid in tf.weight_field_ids
    ):
        raise NotImplementedError("only single-field transfer functions are supported")

    lo, hi = tf.x_bounds
    # Trim to where the table is non-zero, so the texels aren't spent on a
    # range that contributes nothing.
    probe = np.linspace(lo, hi, 16 * tf.nbins)
    support = np.nonzero(_eval_yt_tf(tf, probe).max(axis=1) > 0)[0]
    if support.size == 0:
        raise ValueError("the transfer function is zero everywhere")
    step = probe[1] - probe[0]
    lo = max(lo, probe[support[0]] - step)
    hi = min(hi, probe[support[-1]] + step)

    # yt_idv's textures hold (|v| - min) / (max - min), with exact zeros bumped
    # to float32 eps, unless all the data is a single value.
    eps = np.finfo(np.float32).eps
    if block_collection._textures_are_normalized:
        vmin = block_collection.min_val
        vrange = block_collection.val_range
    else:
        vmin, vrange = 0.0, 1.0

    def to_texture(v):
        return (v - vmin) / vrange

    def from_texture(n):
        return n * vrange + vmin

    tf_min = max(to_texture(10.0**lo), eps)
    tf_max = to_texture(10.0**hi)
    if tf_max <= tf_min:
        raise ValueError("the transfer function doesn't overlap the data range")

    # The shader maps u = (log(n) - log(tf_min)) / (log(tf_max) - log(tf_min))
    # and GL puts texel i at u = (i + 0.5) / nbins.
    u = (np.arange(nbins) + 0.5) / nbins
    n = np.exp(np.log(tf_min) + u * (np.log(tf_max) - np.log(tf_min)))
    log_values = np.log10(from_texture(n))

    rgba = _eval_yt_tf(tf, log_values) / ray_length
    table = rgba.astype("float32").reshape(nbins, 1, 4)
    return {
        "transfer_function": TransferFunctionTexture(data=table),
        "tf_min": float(tf_min),
        "tf_max": float(tf_max),
        "tf_log": True,
    }


def apply_converted_transfer_function(component, converted):
    """Set the result of convert_yt_transfer_function on a BlockRendering."""
    component.render_method = "transfer_function"
    component.transfer_function = converted["transfer_function"]
    component.tf_min = converted["tf_min"]
    component.tf_max = converted["tf_max"]
    component.tf_log = converted["tf_log"]
