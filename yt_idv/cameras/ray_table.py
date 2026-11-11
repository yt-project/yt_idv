"""Per-pixel ray directions for the ``"ray_table"`` projection.

A ray table is a ``(height, width, 3)`` float32 array of ray directions in
camera space (OpenGL convention: the camera looks down -z, +y is up, +x is
right), one per pixel, row 0 at the bottom of the image. A zero vector marks
a pixel with no ray. Any lens (equirectangular, fisheye, or one measured from
another renderer) can be supplied this way.
"""

import numpy as np

# grid_expand.geom.glsl keeps one bit per tile column in a uint
MAX_TILES = 32


def tile_bounds(n_pixels, n_tiles):
    """Pixel boundaries of ``n_tiles`` tiles, split as grid_expand.geom.glsl does."""
    return (np.arange(n_tiles + 1) * n_pixels) // n_tiles


def tile_cones(rays, tile_pixels=32):
    """Bounding cones of a ray table's screen tiles.

    Returns a ``(n_tiles_y, n_tiles_x, 4)`` float32 array of (unit axis,
    half-angle in radians), with a half-angle of -1 for tiles with no rays.
    At most MAX_TILES tiles are used along each axis.
    """
    rays = np.asarray(rays, dtype="f4")
    height, width = rays.shape[:2]
    ntx = int(np.clip(np.ceil(width / tile_pixels), 1, MAX_TILES))
    nty = int(np.clip(np.ceil(height / tile_pixels), 1, MAX_TILES))
    xb, yb = tile_bounds(width, ntx), tile_bounds(height, nty)

    def per_tile(values, reduce=np.add):
        return reduce.reduceat(
            reduce.reduceat(values, yb[:-1], axis=0), xb[:-1], axis=1
        )

    norm = np.sqrt(np.einsum("ijk,ijk->ij", rays, rays))
    valid = norm > 1e-6
    unit = rays / np.maximum(norm, 1e-6)[..., None]
    counts = per_tile(valid.astype("i4"))
    sums = per_tile(unit.astype("f8"))
    sum_norm = np.linalg.norm(sums, axis=-1)
    # a tile whose rays cancel out (wider than a hemisphere) gets a full cone
    degenerate = sum_norm < 1e-6 * np.maximum(counts, 1)
    axes = np.where(
        degenerate[..., None],
        (0.0, 0.0, -1.0),
        sums / np.where(degenerate, 1.0, sum_norm)[..., None],
    )

    ty = np.repeat(np.arange(nty), np.diff(yb))
    tx = np.repeat(np.arange(ntx), np.diff(xb))
    cosines = np.einsum(
        "ijk,ijk->ij", unit, axes[ty[:, None], tx[None, :]].astype("f4")
    )
    cosines[~valid] = 2.0
    min_cos = per_tile(cosines, np.minimum)

    cones = np.zeros((nty, ntx, 4), dtype="f4")
    cones[..., :3] = axes
    # float32 directions and the GPU's acos/cos: pad the cone slightly
    cones[..., 3] = np.minimum(np.arccos(np.clip(min_cos, -1.0, 1.0)) + 1e-3, np.pi)
    cones[degenerate, 3] = np.pi
    cones[counts == 0, 3] = -1.0
    return cones


def equirectangular_rays(width, height):
    """Rays of a full equirectangular panorama.

    Longitude runs from -180 degrees at the left edge to +180 at the right, with
    the view direction at the center; latitude runs from -90 at the bottom to +90.
    """
    lon = ((np.arange(width) + 0.5) / width - 0.5) * 2.0 * np.pi
    lat = ((np.arange(height) + 0.5) / height - 0.5) * np.pi
    lon, lat = np.meshgrid(lon, lat)
    rays = np.stack(
        [np.sin(lon) * np.cos(lat), np.sin(lat), -np.cos(lon) * np.cos(lat)], axis=-1
    )
    return rays.astype("f4")


def fisheye_rays(width, height, fov=180.0):
    """Rays of an equidistant fisheye whose image circle fills the shorter side.

    ``fov`` is the full field of view across the circle, in degrees; pixels
    outside the circle have no ray.
    """
    size = min(width, height)
    x = ((np.arange(width) + 0.5) - 0.5 * width) / (0.5 * size)
    y = ((np.arange(height) + 0.5) - 0.5 * height) / (0.5 * size)
    x, y = np.meshgrid(x, y)
    r = np.hypot(x, y)
    theta = r * np.radians(fov) / 2.0
    phi = np.arctan2(y, x)
    rays = np.stack(
        [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), -np.cos(theta)],
        axis=-1,
    )
    rays[r > 1.0] = 0.0
    return rays.astype("f4")
