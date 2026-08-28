from yt import write_bitmap

from .base_context import BaseContext


def offscreen_render_to_scene(rc):
    """renders a rendering context and writes the image to scene.image

    Parameters
    ----------
    rc :
        the RenderingContext

    Returns
    -------
    image array
        rc.scene.image
    """

    if rc.scene is None:
        return
    rc.scene.render()
    if rc.image_widget is not None:
        rc.image_widget.value = write_bitmap(rc.scene.image[:, :, :3], None)
        return
    return rc.scene.image


class OffscreenRenderingContext(BaseContext):
    """Base class for offscreen rendering."""

    def run(self):
        return offscreen_render_to_scene(self)

    def snap(self, *args, **kwargs):
        if self.scene is None:
            return
        self.scene.render()
        super().snap(*args, **kwargs)

    def close(self):
        """Release the underlying rendering context. Safe to call twice."""
        raise NotImplementedError
