"""
Extract data values, rather than colors, from a rendered scene.

Setting ``store_first_pass_fb`` on a component keeps the output of the first
rendering pass (which holds data values) before the colormap is applied in the
second pass. ``rendered_image_plane`` then converts that raw buffer back into
physical units and reports the physical extent of the view.
"""

import matplotlib.pyplot as plt
import numpy as np
import yt

import yt_idv

ds = yt.load_sample("IsolatedGalaxy")

rc = yt_idv.render_context(height=800, width=800, gui=False)
sg = rc.add_scene(ds, "density", no_ghost=True)

component = rc.scene.components[0]
component.store_first_pass_fb = True

for render_method in ("max_intensity", "projection", "slice"):
    component.render_method = render_method
    rc.scene.render()

    frb = component.rendered_image_plane()
    print(f"{render_method}: {frb}")
    print(f"  view is {frb.width:.3f} x {frb.height:.3f} centered on {frb.center}")

    finite = frb.data[np.isfinite(frb.data)]
    print(f"  data range: {finite.min():.3e} to {finite.max():.3e}")

    plt.figure()
    plt.imshow(
        np.log10(frb.data.d),
        origin="lower",
        extent=frb.extent.in_units("kpc").d,
        cmap="viridis",
    )
    plt.colorbar(label=f"log10({frb.data.units})")
    plt.xlabel("kpc")
    plt.ylabel("kpc")
    plt.title(render_method)

plt.show()
