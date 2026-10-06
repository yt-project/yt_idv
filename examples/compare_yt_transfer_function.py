"""Render IsolatedGalaxy with the same transfer function in yt and yt_idv.

Uses the transfer function from the yt volume rendering docs, converted with
yt_idv.tf_conversion, for two views:

1. The docs view: plane-parallel, 15 kpc wide, normal (-0.3, -0.3, 1). yt only
   integrates through width[2] around the focus, so the depth is set to
   200 kpc to cover the disk; yt_idv approximates the parallel rays with a
   distant camera and a narrow field of view.
2. A perspective view from 30 kpc along the same normal, with the same 15 kpc
   width (a 53 degree field of view).

Writes tf_comparison.png: yt, yt_idv and their ratio for each view. Both codes
return raw accumulated RGBA; the images share one brightness scale per view.
"""

import os

os.environ.setdefault("PYOPENGL_PLATFORM", "egl")

import matplotlib.pyplot as plt
import numpy as np
import yt

import yt_idv
from yt_idv.tf_conversion import (
    apply_converted_transfer_function,
    convert_yt_transfer_function,
    yt_ray_length,
)

RESOLUTION = 256
WIDTH_KPC = 15.0
NORMAL = np.array([-0.3, -0.3, 1.0])
# yt_idv steps are dx / sample_factor; yt takes 10 samples per cell crossing.
SAMPLE_FACTOR = 10.0

ds = yt.load("IsolatedGalaxy/galaxy0030/galaxy0030")


def docs_transfer_function():
    tf = yt.ColorTransferFunction(np.log10((1e-30, 1e-23)), grey_opacity=True)

    def linramp(vals, minval, maxval):
        return (vals - vals.min()) / (vals.max() - vals.min())

    tf.map_to_colormap(
        np.log10(1e-25), np.log10(8e-24), colormap="cmyt.arbre", scale_func=linramp
    )
    return tf


def render_yt(lens_type, position=None, depth_kpc=WIDTH_KPC):
    sc = yt.create_scene(ds, ("gas", "density"), lens_type=lens_type)
    source = sc[0]
    source.transfer_function = docs_transfer_function()
    source.set_use_ghost_zones(True)
    cam = sc.camera
    cam.resolution = (RESOLUTION, RESOLUTION)
    cam.width = ds.arr([WIDTH_KPC, WIDTH_KPC, depth_kpc], "kpc")
    cam.focus = ds.domain_center
    cam.normal_vector = NORMAL
    cam.switch_orientation()
    if position is not None:
        cam.set_position(position, north_vector=cam.north_vector)
    image = np.asarray(sc.render(), dtype="f8")
    # yt indexes the image as [x, y]. Transposing gives [row, column] with
    # north at the top, matching yt_idv's framebuffer after its row flip
    # (checked with markers placed along the camera's north and east vectors).
    return image.transpose(1, 0, 2), cam


def render_yt_idv(rc, block_collection, component, yt_cam, position, fov):
    converted = convert_yt_transfer_function(
        docs_transfer_function(), block_collection, yt_ray_length(yt_cam)
    )
    apply_converted_transfer_function(component, converted)
    to_unitary = lambda v: np.asarray(ds.arr(v).to("unitary"))  # noqa: E731
    rc.scene.camera.update(
        position=to_unitary(position),
        focus=to_unitary(yt_cam.focus),
        up=np.asarray(yt_cam.north_vector),
        fov=fov,
        near_plane=1e-4,
        far_plane=10.0,
        aspect_ratio=1.0,
    )
    rc.run()
    # Row 0 of the first-pass framebuffer is the bottom of the image.
    return np.asarray(component.first_pass_fb_rgba, dtype="f8")[::-1]


def main():
    rc = yt_idv.render_context("egl", width=RESOLUTION, height=RESOLUTION)
    rc.add_scene(ds, ("gas", "density"), no_ghost=False)
    component = rc.scene.components[0]
    block_collection = component.data
    component.sample_factor = SAMPLE_FACTOR
    component.store_first_pass_fb = True

    width = ds.quan(WIDTH_KPC, "kpc")
    n_hat = NORMAL / np.linalg.norm(NORMAL)
    views = []

    # 1. Docs view (plane-parallel in yt).
    yt_img, yt_cam = render_yt("plane-parallel", depth_kpc=200.0)
    distance = 100 * width
    position = yt_cam.focus - distance * n_hat
    fov = np.degrees(2 * np.arctan(0.5 * width / distance))
    idv_img = render_yt_idv(rc, block_collection, component, yt_cam, position, fov)
    views.append(("plane-parallel (docs view, 200 kpc deep)", yt_img, idv_img))

    # 2. Perspective from 30 kpc.
    position = ds.domain_center - ds.quan(30.0, "kpc") * n_hat
    yt_img, yt_cam = render_yt("perspective", position=position)
    fov = np.degrees(2 * np.arctan(0.5))  # width / width[2] = 1
    idv_img = render_yt_idv(rc, block_collection, component, yt_cam, position, fov)
    views.append(("perspective from 30 kpc", yt_img, idv_img))

    fig, axes = plt.subplots(len(views), 3, figsize=(12, 4 * len(views)))
    for row, (title, yt_img, idv_img) in zip(axes, views, strict=True):
        scale = np.percentile(yt_img[..., :3].max(axis=-1), 99.5)
        c = RESOLUTION // 2
        print(f"{title}:")
        print(f"  center pixel rgba  yt     {np.round(yt_img[c, c], 4)}")
        print(f"  center pixel rgba  yt_idv {np.round(idv_img[c, c], 4)}")
        row[0].imshow(np.clip(yt_img[..., :3] / scale, 0, 1))
        row[0].set_title(f"yt: {title}")
        row[1].imshow(np.clip(idv_img[..., :3] / scale, 0, 1))
        row[1].set_title("yt_idv, converted TF")
        yt_lum = yt_img[..., :3].sum(axis=-1)
        idv_lum = idv_img[..., :3].sum(axis=-1)
        visible = yt_lum > 0.01 * yt_lum.max()
        ratio = np.where(visible, idv_lum / np.where(visible, yt_lum, 1.0), np.nan)
        print(
            f"  yt_idv / yt brightness over visible pixels: median "
            f"{np.nanmedian(ratio):.3f}, 5-95% {np.nanpercentile(ratio, 5):.3f}-"
            f"{np.nanpercentile(ratio, 95):.3f}"
        )
        im = row[2].imshow(ratio, cmap="RdBu_r", vmin=0.5, vmax=1.5)
        row[2].set_title("yt_idv / yt brightness")
        fig.colorbar(im, ax=row[2], fraction=0.046)
        for ax in row:
            ax.set_xticks([])
            ax.set_yticks([])
    fig.tight_layout()
    fig.savefig("tf_comparison.png", dpi=100)
    print("wrote tf_comparison.png")


if __name__ == "__main__":
    main()
